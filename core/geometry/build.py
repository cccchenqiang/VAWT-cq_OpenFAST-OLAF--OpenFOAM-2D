# -*- coding: utf-8 -*-
"""风轮几何构建：从 VAWT 模型组装 3D 几何，供可视化使用。"""
import numpy as np


def euler_matrix(thetas_deg):
    """AeroDyn/NWTC 约定：三个连续旋转 (theta_x, theta_y, theta_z) 的 1-2-3 序列。

    返回 R，v_global = R @ v_local；对列向量依次先绕 z、再绕 y、再绕 x 旋转，
    即 R = Rx(theta_x) @ Ry(theta_y) @ Rz(theta_z)。
    （AeroDyn Driver 的 BldOrientation_h/HubOrientation_n 均使用此约定；
     对 VAWT，BldOrientation=(azimuth, precone, pitch)。）
    """
    th = np.radians(np.asarray(thetas_deg, dtype=float))
    x, y, z = th
    cx, sx = np.cos(x), np.sin(x)
    cy, sy = np.cos(y), np.sin(y)
    cz, sz = np.cos(z), np.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz


def rodrigues(v, k, theta):
    """绕单位轴 k 旋转向量 v 角度 theta（Rodrigues 公式）。"""
    k = np.asarray(k, dtype=float)
    k = k / np.linalg.norm(k)
    return (v * np.cos(theta) + np.cross(k, v) * np.sin(theta)
            + k * np.dot(k, v) * (1 - np.cos(theta)))


def build_geometry(model, num_sections=None, rotor_angle_deg=0.0):
    """把 VAWT 模型转为 3D 几何字典。

    返回:
      hub, rotor_axis, blades[{origin, centerline, sections[{span,chord,pos,poly}]}],
      tower, base_origin, nacelle, num_blades
    """
    t = model.turbine
    blade = model.blade
    if t is None or blade is None:
        raise ValueError('需要先加载 driver 与 blade 文件')

    R_hub = euler_matrix(t.hub_orientation)
    hub = np.asarray(t.hub_position_global(), dtype=float)
    rotor_axis = R_hub @ np.array([1., 0., 0.])
    theta = np.radians(rotor_angle_deg)
    span = blade.span
    if num_sections is None:
        num_sections = min(8, len(span))
    idx = np.unique(np.linspace(0, len(span) - 1, num_sections).astype(int))

    blades = []
    for k in range(t.num_blades):
        origin = hub + R_hub @ np.asarray(t.blade_origins[k], dtype=float)
        R_b = R_hub @ euler_matrix(t.blade_orientations[k])
        bz = R_b[:, 2]
        # 中心线（展向）
        centerline = origin[None, :] + np.outer(span, bz)
        # 翼型截面
        sections = []
        for j in idx:
            s = float(span[j])
            c = float(blade.chord[j])
            af = blade.airfoils.get(int(blade.afid[j])) if blade.airfoils else None
            if af is None or af.num_coords == 0:
                local = np.array([[0., 0.], [0., 0.01], [-0.01, 0.], [0., -0.01]])  # 占位菱形
            else:
                local = af.scaled_coords(c, center=(0.0, 0.0))
            pos = origin + bz * s
            poly = pos[None, :] + (R_b[:, :2] @ local.T).T
            sections.append(dict(span=s, chord=c, pos=pos, poly=poly))
        blades.append(dict(index=k + 1, origin=origin, centerline=centerline,
                           sections=sections, axis=R_b, angle=rotor_angle_deg))

    # 方位角旋转（整体绕转轴）
    if abs(theta) > 1e-9:
        for b in blades:
            b['origin'] = hub + rodrigues(b['origin'] - hub, rotor_axis, theta)
            b['centerline'] = hub + np.array(
                [rodrigues(p - hub, rotor_axis, theta) for p in b['centerline']])
            for sec in b['sections']:
                sec['pos'] = hub + rodrigues(sec['pos'] - hub, rotor_axis, theta)
                sec['poly'] = hub + np.array(
                    [rodrigues(p - hub, rotor_axis, theta) for p in sec['poly']])

    # 塔筒（来自 AD.dat 塔筒表）
    tower = None
    if t.has_tower and model.ad is not None:
        nodes = model.ad.get('tower_nodes') or []
        if nodes:
            tower = dict(elev=[float(n[0]) for n in nodes],
                         diam=[float(n[1]) for n in nodes])

    return dict(hub=hub, rotor_axis=rotor_axis, blades=blades, tower=tower,
                base_origin=np.asarray(t.base_origin, dtype=float),
                nacelle=np.asarray(t.nacelle_origin, dtype=float),
                R_hub=R_hub, num_blades=t.num_blades,
                rotor_angle_deg=rotor_angle_deg)
