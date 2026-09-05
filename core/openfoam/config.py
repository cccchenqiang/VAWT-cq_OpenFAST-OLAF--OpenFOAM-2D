from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class OpenFOAMCaseConfig:
    airfoil: str
    output: str
    rotor_radius: float = 0.225
    chord: float = 0.1
    blade_count: int = 3
    pitch_deg: float = 0.0
    shaft_radius: float = 0.0075
    height: float = 0.05
    rpm: float = 300.0
    inlet_velocity: float = 8.0
    start_time: float = 0.0
    end_time: float = 2.0
    delta_t: float = 0.0001
    write_interval: float = 0.05
    domain_x_min: float = -1.2
    domain_x_max: float = 2.8
    domain_y: float = 1.2
    ami_diameter: float | None = None
    custom_domain: bool = False
    mesh_x: int = 40
    mesh_y: int = 24
    blade_refinement: int = 4
    ami_refinement: int = 3

    def validate(self):
        for name in ("rotor_radius", "chord", "shaft_radius", "height",
                     "rpm", "delta_t", "write_interval"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.blade_count < 1 or self.mesh_x < 1 or self.mesh_y < 1:
            raise ValueError("blade_count and mesh dimensions must be positive integers")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        if not Path(self.airfoil).is_file():
            raise FileNotFoundError(f"翼型文件不存在: {self.airfoil}")
        if Path(self.output).exists():
            raise FileExistsError(f"输出目录已存在: {self.output}")
        if self.custom_domain and (self.domain_x_max <= self.domain_x_min or self.domain_y <= 0):
            raise ValueError("计算域尺寸无效")

    def as_namespace(self, template_dir):
        from argparse import Namespace
        values = asdict(self)
        values["template_dir"] = str(template_dir)
        return Namespace(**values)
