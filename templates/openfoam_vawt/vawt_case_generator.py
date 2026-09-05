#!/usr/bin/env python3
"""Generate a self-contained OpenFOAM VAWT case using only the Python standard library."""
import argparse
import json
import math
import re
import shutil
from pathlib import Path


def positive(name):
    def convert(value):
        value = float(value)
        if value <= 0:
            raise argparse.ArgumentTypeError(name + " must be positive")
        return value
    return convert


def read_airfoil(path):
    points = []
    header_coordinate_count = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        fields = stripped.split()
        if header_coordinate_count is None and len(fields) == 1:
            try:
                header_coordinate_count = int(float(fields[0]))
                continue
            except ValueError:
                pass
        if header_coordinate_count is None and len(fields) >= 2 and fields[1].lower().startswith("numcoord"):
            try:
                header_coordinate_count = int(float(fields[0]))
                continue
            except ValueError:
                pass
        if len(fields) >= 2:
            try:
                points.append((float(fields[0]), float(fields[1])))
            except ValueError:
                pass
    if header_coordinate_count is not None and len(points) >= header_coordinate_count:
        # WEIS/AeroDyn NumCoords includes one reference point before the outline.
        points = points[1:header_coordinate_count]
    if len(points) < 3:
        raise ValueError("airfoil file must contain at least three x y coordinate pairs")
    if points[0] == points[-1]:
        points.pop()
    return points


def convert_le_te_orientation(profile):
    """Put the airfoil leading edge on the positive chordwise side.

    WEIS/AeroDyn profiles commonly start at the trailing edge and travel
    around the upper surface to the leading edge.  For positive CCW rotor
    rotation, the leading edge must face the blade's tangential motion.
    """
    return [(1.0 - x, y) for x, y in profile]


def tri(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(sum(x * x for x in n)) or 1.0
    return n[0] / length, n[1] / length, n[2] / length


def write_stl(path, name, triangles):
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("solid %s\n" % name)
        for a, b, c in triangles:
            n = tri(a, b, c)
            stream.write("  facet normal %.9g %.9g %.9g\n    outer loop\n" % n)
            for p in (a, b, c):
                stream.write("      vertex %.9g %.9g %.9g\n" % p)
            stream.write("    endloop\n  endfacet\n")
        stream.write("endsolid %s\n" % name)


def blade_triangles(profile, radius, chord, height, angle, pitch):
    theta = math.radians(angle)
    cp, sp = math.cos(theta), math.sin(theta)
    # At zero pitch the chord is tangential to the rotor and the profile
    # reference point (the supplied coordinate origin) is on the radial arm.
    radial = (cp, sp)
    tangential = (-sp, cp)
    pitch_rad = math.radians(pitch)
    chord_dir = (tangential[0] * math.cos(pitch_rad) +
                 radial[0] * math.sin(pitch_rad),
                 tangential[1] * math.cos(pitch_rad) +
                 radial[1] * math.sin(pitch_rad))
    normal_dir = (-tangential[0] * math.sin(pitch_rad) +
                  radial[0] * math.cos(pitch_rad),
                  -tangential[1] * math.sin(pitch_rad) +
                  radial[1] * math.cos(pitch_rad))
    vertices = []
    for z in (-height / 2, height / 2):
        layer = []
        for x, y in profile:
            # x is chordwise and y is normal to the chord.
            xx, yy = x * chord, y * chord
            layer.append((radius * radial[0] + xx * chord_dir[0] + yy * normal_dir[0],
                          radius * radial[1] + xx * chord_dir[1] + yy * normal_dir[1], z))
        vertices.append(layer)
    out = []
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        out.extend(((vertices[0][i], vertices[0][j], vertices[1][j]),
                    (vertices[0][i], vertices[1][j], vertices[1][i])))
    # End caps make the extrusion watertight.
    for i in range(1, n - 1):
        out.extend(((vertices[0][0], vertices[0][i + 1], vertices[0][i]),
                    (vertices[1][0], vertices[1][i], vertices[1][i + 1])))
    return out


def cylinder_triangles(radius, height, segments=96):
    out = []
    for i in range(segments):
        j = (i + 1) % segments
        a, b = 2 * math.pi * i / segments, 2 * math.pi * j / segments
        lo = [(radius * math.cos(a), radius * math.sin(a), -height / 2),
              (radius * math.cos(b), radius * math.sin(b), -height / 2)]
        hi = [(radius * math.cos(a), radius * math.sin(a), height / 2),
              (radius * math.cos(b), radius * math.sin(b), height / 2)]
        out.extend(((lo[0], lo[1], hi[1]), (lo[0], hi[1], hi[0]),
                    ((0, 0, -height / 2), lo[1], lo[0]),
                    ((0, 0, height / 2), hi[0], hi[1])))
    return out


def replace(text, pattern, value, count=0):
    return re.sub(pattern, value, text, count=count, flags=re.MULTILINE)


def generate(args):
    diameter = 2.0 * args.rotor_radius
    if args.end_time <= args.start_time:
        raise ValueError("endTime must be greater than startTime.")
    if args.delta_t <= 0 or args.write_interval <= 0:
        raise ValueError("deltaT and writeInterval must be positive.")
    if getattr(args, "ami_diameter", None) is None:
        args.ami_diameter = 1.5 * diameter
    if not getattr(args, "custom_domain", False):
        args.domain_x_min = -5.0 * diameter
        args.domain_x_max = 20.0 * diameter
        args.domain_y = 3.5 * diameter
    ami_radius = args.ami_diameter / 2.0
    blade_extent = args.rotor_radius + args.chord
    if ami_radius <= blade_extent:
        raise ValueError("AMI diameter must be larger than the blade outer extent "
                         "(rotor radius + chord).")
    domain_span = args.domain_x_max - args.domain_x_min
    if domain_span <= 0 or args.domain_y <= 0:
        raise ValueError("Computational domain dimensions are invalid.")
    margin = max(1e-9, 0.01 * diameter)
    if args.domain_x_min + margin >= -ami_radius:
        raise ValueError("Xmin is too close to the rotor for a safe locationInMesh point.")
    if args.domain_y <= ami_radius + margin:
        raise ValueError("Y half-width must exceed the AMI radius.")
    template = Path(__file__).resolve().parent
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError("output directory already exists: %s" % output)
    profile = convert_le_te_orientation(read_airfoil(args.airfoil))
    output.mkdir(parents=True)
    ignore = shutil.ignore_patterns("vawt_case_generator.py", "log*", "polyMesh",
                                    "VAWT*.stl", "SHAFT.stl", "AMI.stl")
    shutil.copytree(template, output, dirs_exist_ok=True, ignore=ignore)
    surface = output / "constant" / "triSurface"
    surface.mkdir(parents=True, exist_ok=True)
    for old in surface.glob("VAWT*.stl"):
        old.unlink()
    for old in (surface / "SHAFT.stl", surface / "AMI.stl"):
        if old.exists():
            old.unlink()
    for i in range(args.blade_count):
        triangles = blade_triangles(profile, args.rotor_radius, args.chord, args.height,
                                    i * 360.0 / args.blade_count, args.pitch_deg)
        write_stl(surface / ("VAWT%d.stl" % (i + 1)), "VAWT%d" % (i + 1), triangles)
    write_stl(surface / "SHAFT.stl", "SHAFT",
              cylinder_triangles(args.shaft_radius, args.height))
    write_stl(surface / "AMI.stl", "AMI",
              # stl_gen1203 convention: AMI diameter = 1.5 * rotor diameter.
              cylinder_triangles(args.ami_diameter / 2.0, args.height))

    dims = (output / "system" / "include" / "Dimensions")
    dtext = dims.read_text(encoding="utf-8")
    # Dimensions stores diameters; the CLI exposes radii.
    dtext = replace(dtext, r"(?m)^[ \t]*OD[ \t]+[^\r\n]*$", "OD %g;" % (2 * args.rotor_radius))
    dtext = replace(dtext, r"(?m)^[ \t]*ID[ \t]+[^\r\n]*$", "ID %g;" % (2 * args.shaft_radius))
    dtext = replace(dtext, r"(?m)^[ \t]*Xmin[ \t]+[^\r\n]*$", "Xmin %g;" % args.domain_x_min)
    dtext = replace(dtext, r"(?m)^[ \t]*Xmax[ \t]+[^\r\n]*$", "Xmax %g;" % args.domain_x_max)
    dtext = replace(dtext, r"(?m)^[ \t]*Y[ \t]+[^\r\n]*$", "Y %g;" % args.domain_y)
    dtext = replace(dtext, r"(?m)^[ \t]*Z[ \t]+[^\r\n]*$", "Z %g;" % (args.height / 2))
    dims.write_text(dtext, encoding="utf-8")

    block = output / "system" / "blockMeshDict"
    btext = block.read_text(encoding="utf-8")
    btext = re.sub(r"\(40 24 1\)", "(%d %d 1)" % (args.mesh_x, args.mesh_y), btext)
    block.write_text(btext, encoding="utf-8")
    snap = output / "system" / "snappyHexMeshDict"
    stext = snap.read_text(encoding="utf-8")
    names = "|".join("VAWT%d" % (i + 1) for i in range(args.blade_count))
    stl_entries = "\n".join("    VAWT%d.stl { type triSurfaceMesh; name VAWT%d; scale 1; }" %
                            (i + 1, i + 1) for i in range(args.blade_count))
    refine_radius = max(ami_radius, blade_extent) * 1.08
    refine_y = min(refine_radius, args.domain_y - margin)
    wake_start = min(refine_radius * 0.7, args.domain_x_max - margin)
    wake_end = args.domain_x_max - margin
    location_x = args.domain_x_min + margin
    z_extent = max(args.height / 2.0, margin)
    geometry_text = (
        "geometry\n{\n%s\n"
        "    SHAFT.stl { type triSurfaceMesh; name SHAFT; scale 1; }\n"
        "    AMI.stl { type triSurfaceMesh; name AMI; scale 1; }\n"
        "    refinementBox\n    {\n"
        "        type searchableBox;\n"
        "        min (%.12g %.12g %.12g);\n"
        "        max (%.12g %.12g %.12g);\n"
        "    }\n"
        "    refinementBoxWake\n    {\n"
        "        type searchableBox;\n"
        "        min (%.12g %.12g %.12g);\n"
        "        max (%.12g %.12g %.12g);\n"
        "    }\n"
        "};"
    ) % (stl_entries, -refine_radius, -refine_y, -z_extent,
          refine_radius, refine_y, z_extent,
          wake_start, -refine_y, -z_extent,
          wake_end, refine_y, z_extent)
    stext = re.sub(r"(?s)geometry\s*\{.*?\n\};", geometry_text, stext, count=1)
    stext = re.sub(r"\(VAWT1\|VAWT2\|VAWT3\)", "(" + names + ")", stext)
    stext = re.sub(r"\(VAWT1\|VAWT2\|VAWT3\|SHAFT\)", "(" + names + "|SHAFT)", stext)
    stext = stext.replace("level (4 4);", "level (%d %d);" % (args.blade_refinement, args.blade_refinement))
    stext = stext.replace("level (3 3);", "level (%d %d);" % (args.ami_refinement, args.ami_refinement))
    stext = re.sub(r"(?m)^\s*locationInMesh\s+\([^;]+;",
                   "    locationInMesh (%.12g 0 0); // outside AMI and blades" % location_x,
                   stext)
    snap.write_text(stext, encoding="utf-8")

    dyn = output / "constant" / "dynamicMeshDict"
    dyn.write_text(
        re.sub(
            r"(?m)^\s*omega\s+[^;]+;.*$",
            "         omega %.12g; // rad/s; positive = CCW viewed from +Z"
            % (args.rpm * 2 * math.pi / 60),
            dyn.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    extrude = output / "system" / "extrudeMeshDict"
    extrude_text = extrude.read_text(encoding="utf-8")
    extrude_text = re.sub(r"(?m)^(\s*thickness\s+)[^;]+;",
                          r"\g<1>%g;" % args.height, extrude_text)
    extrude.write_text(extrude_text, encoding="utf-8")
    control = output / "system" / "controlDict"
    ctext = control.read_text(encoding="utf-8")
    ctext = ctext.replace("startFrom       latestTime;", "startFrom       startTime;")
    ctext = replace(ctext, r"^\s*startTime\s+[^;]+;", "startTime       %.12g;" % args.start_time)
    ctext = replace(ctext, r"^\s*endTime\s+[^;]+;", "endTime         %.12g;" % args.end_time)
    ctext = replace(ctext, r"^\s*deltaT\s+[^;]+;", "deltaT          %.12g;" % args.delta_t)
    ctext = replace(ctext, r"^\s*writeInterval\s+[^;]+;", "writeInterval   %.12g;" % args.write_interval, 1)
    forces = "\n".join("    forces%d { type forces; libs (\"libforces.so\"); writeControl timeStep; writeInterval 1; patches (VAWT%d); rho rhoInf; log true; rhoInf 1; CofR (0 0 0); }" % (i + 1, i + 1) for i in range(args.blade_count))
    ctext = re.sub(r"(?s)functions\s*\{.*?\n\}", "functions\n{\n%s\n}" % forces, ctext, count=1)
    control.write_text(ctext, encoding="utf-8")
    for field in (output / "0.orig").iterdir():
        if not field.is_file():
            continue
        text = field.read_text(encoding="utf-8")
        text = text.replace("(VAWT1|VAWT2|VAWT3|SHAFT)", "(" + names + "|SHAFT)")
        text = re.sub(r"(?m)^\s*internalField1\s+uniform\s+\([^)]*\);",
                      "internalField1 uniform (%g 0 0);" % args.inlet_velocity, text)
        if field.name == "omega":
            text = re.sub(r"(?m)^\s*internalField\s+uniform\s+[^;]+;",
                          "internalField uniform %.12g;" % (args.rpm * 2 * math.pi / 60), text)
        field.write_text(text, encoding="utf-8")
    (output / "Allrun").write_text(
        "#!/bin/sh\nset -eu\ncd \"$(dirname \"$0\")\"\n"
        "blockMesh > log.blockMesh 2>&1\n"
        "snappyHexMesh -overwrite > log.snappyHexMesh 2>&1\n"
        "extrudeMesh > log.extrudeMesh 2>&1\n"
        "createPatch -overwrite > log.createPatch 2>&1\n"
        "rm -rf 0 constant/polyMesh/sets\ncp -r 0.orig 0\n"
        "pimpleDyMFoam > log.pimpleDyMFoam 2>&1\n", encoding="utf-8")
    (output / "Allclean").write_text(
        "#!/bin/sh\nset -eu\ncd \"$(dirname \"$0\")\"\n"
        "rm -rf 0 constant/polyMesh log.*\n"
        "for time in [0-9]*; do\n"
        "    [ -d \"$time\" ] || continue\n"
        "    [ \"$time\" = \"0\" ] && continue\n"
        "    rm -rf \"$time\"\n"
        "done\n",
        encoding="utf-8")
    (output / "Allrun").chmod(0o755)
    (output / "Allclean").chmod(0o755)
    manifest = vars(args).copy()
    manifest["airfoil"] = str(Path(args.airfoil).resolve())
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "README.md").write_text(
        "# Generated VAWT case\n\n"
        "Run `./Allrun` on Linux with OpenFOAM 5.x.\n"
        "Rotation is configured in `constant/dynamicMeshDict`: `omega` is rad/s, "
        "axis `(0 0 1)` means counter-clockwise when viewed from +Z; inspect times "
        "after 0 (for example 0.05 or 0.10) in paraFoam/ParaView to see motion.\n"
        "The imported airfoil chord is converted from the common TE-to-LE input "
        "orientation so its leading edge faces the positive tangential motion.\n"
        "Simulation time settings (`startTime`, `endTime`, `deltaT`, and "
        "`writeInterval`) are written from the GUI/command-line parameters.\n"
        "The AMI follows the stl_gen1203 convention: diameter = 1.5 x rotor diameter.\n"
        "Unless custom-domain is enabled, the domain is 5D upstream, 20D downstream, "
        "and 7D wide.\nParameters are recorded in `manifest.json`.\n", encoding="utf-8")
    return output


def parser():
    p = argparse.ArgumentParser(description="Generate a parameterized OpenFOAM VAWT case.")
    p.add_argument("--airfoil", required=True, help="airfoil x y coordinate file")
    p.add_argument("--output", required=True)
    p.add_argument("--rotor-radius", type=positive("rotor-radius"), required=True)
    p.add_argument("--chord", type=positive("chord"), required=True)
    p.add_argument("--blade-count", type=int, required=True)
    p.add_argument("--pitch-deg", type=float, default=0.0)
    p.add_argument("--shaft-radius", type=positive("shaft-radius"), required=True)
    p.add_argument("--height", type=positive("height"), required=True)
    p.add_argument("--rpm", type=positive("rpm"), required=True)
    p.add_argument("--inlet-velocity", "--inlet_velocity", type=float, required=True)
    p.add_argument("--start-time", type=float, default=0.0)
    p.add_argument("--end-time", type=positive("end-time"), default=2.0)
    p.add_argument("--delta-t", type=positive("delta-t"), default=1e-4)
    p.add_argument("--write-interval", type=positive("write-interval"), default=0.05)
    p.add_argument("--domain-x-min", type=float, default=-1.2)
    p.add_argument("--domain-x-max", type=float, default=2.8)
    p.add_argument("--domain-y", type=positive("domain-y"), default=1.2)
    p.add_argument("--ami-diameter", type=positive("ami-diameter"), default=None)
    p.add_argument("--custom-domain", action="store_true",
                   help="keep manually supplied domain values instead of automatic 5D/20D/7D sizing")
    p.add_argument("--mesh-x", type=int, default=40)
    p.add_argument("--mesh-y", type=int, default=24)
    p.add_argument("--blade-refinement", type=int, default=4)
    p.add_argument("--ami-refinement", type=int, default=3)
    return p


if __name__ == "__main__":
    cli = parser()
    ns = cli.parse_args()
    if ns.blade_count < 1 or ns.mesh_x < 1 or ns.mesh_y < 1:
        cli.error("blade-count and mesh dimensions must be positive integers")
    try:
        print("Generated %s" % generate(ns))
    except (OSError, ValueError) as error:
        cli.error(str(error))
