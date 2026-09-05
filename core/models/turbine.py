# -*- coding: utf-8 -*-
"""风轮/塔筒数据模型：从 AeroDyn Driver 输入 (ad_driver.dvr) 解析的几何与运动配置。"""
import numpy as np


class Turbine:
    """单个风轮（含塔筒、机舱、轮毂、叶片）的几何与工况配置。"""

    def __init__(self, index=1):
        self.index = index
        # ---- 基础坐标系 ----
        self.base_origin = np.zeros(3)            # BaseOriginInit
        self.base_orientation = np.zeros(3)       # BaseOrientationInit (deg)
        self.has_tower = False                     # HasTower
        self.hawt_projection = False               # HAWTprojection
        self.tower_origin = np.zeros(3)            # TwrOrigin_t (base 系)
        self.nacelle_origin = np.array([0., 0., 3.])  # NacOrigin_t (base 系)
        self.hub_origin = np.zeros(3)              # HubOrigin_n (nacelle 系)
        self.hub_orientation = np.array([0., -90., 0.])  # HubOrientation_n (deg)
        # ---- 叶片 ----
        self.num_blades = 3
        self.blade_origins = []                    # list of Nx3 (hub 系)
        self.blade_orientations = []               # list of Nx3 (deg, hub 系->blade 系)
        self.blade_hub_rad = []                    # BldHubRad_bl
        # ---- 运动/工况 ----
        self.rot_motion_type = 0
        self.rot_speed = 273.0                     # rpm
        self.blade_pitch = []                      # deg
        self.nac_yaw = 0.0
        self.base_motion_type = 0
        # ---- 环境 ----
        self.fld_dens = 1.225
        self.kin_visc = 1.477551020408163e-05
        self.hwind_speed = 8.0
        self.ref_height = 6.0
        self.pl_exp = 0.0
        # ---- 塔筒几何（若启用，由 tower 输入填充）----
        self.tower_nodes = None                    # Nx2: (elev, diam) 塔筒节点
        self.tower_twist = 0.0

    # ---- 便捷 ----
    def has_blade_geometry(self):
        return len(self.blade_origins) > 0 and len(self.blade_orientations) > 0

    def rotor_radius(self):
        """转子半径 R [m]。

        AeroDyn 约定轮毂系 x 轴沿转轴，叶片原点 (oy, oz) 在垂直转轴的平面内，
        半径取所有叶片原点距转轴的最大横向距离 sqrt(oy^2+oz^2)。
        """
        if not self.blade_origins:
            return 0.0
        r = 0.0
        for o in self.blade_origins:
            r = max(r, float(np.hypot(float(o[1]), float(o[2]))))
        return r

    def rotor_axis(self):
        """返回轮毂坐标系 x 轴在全局（base）坐标系的单位向量（AeroDyn 约定：x 轴对齐转轴）。

        欧拉角约定与 AeroDyn/NWTC 一致：R = Rx @ Ry @ Rz（1-2-3 序列）。
        """
        thx, thy, thz = np.radians(self.hub_orientation)
        Rx = np.array([[1, 0, 0],
                       [0, np.cos(thx), -np.sin(thx)],
                       [0, np.sin(thx), np.cos(thx)]])
        Ry = np.array([[np.cos(thy), 0, np.sin(thy)],
                       [0, 1, 0],
                       [-np.sin(thy), 0, np.cos(thy)]])
        Rz = np.array([[np.cos(thz), -np.sin(thz), 0],
                       [np.sin(thz), np.cos(thz), 0],
                       [0, 0, 1]])
        R = Rx @ Ry @ Rz
        # 轮毂系 x 轴（转轴）→ 全局
        return R @ np.array([1., 0., 0.])

    def hub_position_global(self):
        """轮毂原点在全局（base）坐标系的坐标。"""
        return (np.asarray(self.base_origin, dtype=float)
                + np.asarray(self.nacelle_origin, dtype=float)
                + np.asarray(self.hub_origin, dtype=float))

    def summary(self):
        bld = f'{self.num_blades} blades' if self.has_blade_geometry() else 'no blade geometry'
        twr = 'tower=ON' if self.has_tower else 'tower=OFF'
        return (f'Turbine#{self.index}: {bld}, {twr}, '
                f'RPM={self.rot_speed:.1f}, U0={self.hwind_speed:.2f} m/s, '
                f'HubOrientation={list(self.hub_orientation)}')
