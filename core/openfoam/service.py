from pathlib import Path

from .config import OpenFOAMCaseConfig
from .generator import generate


class OpenFOAMCaseService:
    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.template_dir = self.project_root / "templates" / "openfoam_vawt"

    def generate_case(self, config: OpenFOAMCaseConfig):
        config.validate()
        return generate(config.as_namespace(self.template_dir))

    def map_from_fast(self, model, airfoil=""):
        turbine = model.turbine
        blade = model.blade
        if turbine is None or blade is None:
            raise ValueError("OpenFAST 模型缺少 Driver 或叶片数据，无法映射 OpenFOAM 参数")
        return {
            "airfoil": airfoil or model.paths.get("naca", ""),
            "rotor_radius": float(turbine.rotor_radius()),
            "chord": float(blade.chord[0]),
            "blade_count": int(turbine.num_blades),
            "rpm": float(turbine.rot_speed),
            "inlet_velocity": float(turbine.hwind_speed),
        }
