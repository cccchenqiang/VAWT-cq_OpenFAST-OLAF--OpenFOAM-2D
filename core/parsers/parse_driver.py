# -*- coding: utf-8 -*-
"""解析 AeroDyn Driver 主输入 (ad_driver.dvr) -> Turbine 模型。"""
import re
import os

from .base import split_kv, to_str, to_float, to_int, to_bool, to_list, read_lines


def parse_driver_file(path):
    from ..models.turbine import Turbine
    t = Turbine()
    t.path = os.path.normpath(path)
    blade_origins, blade_orients, blade_pitches = {}, {}, {}
    for line in read_lines(path):
        key, val = split_kv(line)
        if not key:
            continue
        # --- 环境 ---
        if key == 'HWindSpeed':
            v = to_float(val)
            if v is not None: t.hwind_speed = v
        elif key == 'FldDens':
            v = to_float(val)
            if v is not None: t.fld_dens = v
        elif key == 'KinVisc':
            v = to_float(val)
            if v is not None: t.kin_visc = v
        elif key == 'RefHt':
            v = to_float(val)
            if v is not None: t.ref_height = v
        elif key == 'PLExp':
            v = to_float(val)
            if v is not None: t.pl_exp = v
        elif key == 'AnalysisType':
            v = to_int(val)
            if v is not None: t.analysis_type = v
        elif key == 'TMax':
            v = to_float(val)
            if v is not None: t.tmax = v
        elif key == 'DT':
            v = to_float(val)
            if v is not None: t.dt = v
        # --- 基础几何 ---
        elif key.startswith('BaseOriginInit'):
            lst = to_list(val, 3)
            if lst: t.base_origin = lst
        elif key.startswith('BaseOrientationInit'):
            lst = to_list(val, 3)
            if lst: t.base_orientation = lst
        elif key.startswith('HasTower'):
            t.has_tower = to_bool(val)
        elif key.startswith('HAWTprojection'):
            t.hawt_projection = to_bool(val)
        elif key.startswith('TwrOrigin_t'):
            lst = to_list(val, 3)
            if lst: t.tower_origin = lst
        elif key.startswith('NacOrigin_t'):
            lst = to_list(val, 3)
            if lst: t.nacelle_origin = lst
        elif key.startswith('HubOrigin_n'):
            lst = to_list(val, 3)
            if lst: t.hub_origin = lst
        elif key.startswith('HubOrientation_n'):
            lst = to_list(val, 3)
            if lst: t.hub_orientation = lst
        # --- 叶片 ---
        elif key.startswith('NumBlades('):
            v = to_int(val)
            if v is not None: t.num_blades = v
        elif re.match(r'BldOrigin_h', key):
            idx = int(re.search(r'\((\d+)_(\d+)\)', key).group(2))
            lst = to_list(val, 3)
            if lst: blade_origins[idx] = lst
        elif re.match(r'BldOrientation_h', key):
            idx = int(re.search(r'\((\d+)_(\d+)\)', key).group(2))
            lst = to_list(val, 3)
            if lst: blade_orients[idx] = lst
        elif re.match(r'BldHubRad_bl', key):
            idx = int(re.search(r'\((\d+)_(\d+)\)', key).group(2))
            t.blade_hub_rad.append(float(to_float(val) or 0.0))
        # --- 运动/工况 ---
        elif key.startswith('RotMotionType'):
            v = to_int(val)
            if v is not None: t.rot_motion_type = v
        elif key.startswith('RotSpeed'):
            v = to_float(val)
            if v is not None: t.rot_speed = v
        elif key.startswith('BldPitch('):
            m = re.search(r'\((\d+)_(\d+)\)', key)
            if m:
                idx = int(m.group(2))
                v = to_float(val)
                if v is not None: blade_pitches[idx] = v
        elif key.startswith('NacYaw'):
            v = to_float(val)
            if v is not None: t.nac_yaw = v
    # 组装叶片列表（按序号排序，保证与文件顺序一致）
    n = t.num_blades
    t.blade_origins = [blade_origins.get(i, [0.0, 0.0, 0.0]) for i in range(1, n + 1)]
    t.blade_orientations = [blade_orients.get(i, [-90.0, 90.0, 0.0]) for i in range(1, n + 1)]
    t.blade_pitch = [blade_pitches.get(i, 0.0) for i in range(1, n + 1)]
    return t
