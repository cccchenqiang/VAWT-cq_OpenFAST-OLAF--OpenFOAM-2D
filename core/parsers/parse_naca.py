# -*- coding: utf-8 -*-
"""解析翼型坐标文件 (NACA_*.txt) -> Airfoil（仅几何）。

文件格式（AirfoilInfo / AeroDyn 通用）：
    202   NumCoords        ! ...
    ! ... 注释/表头 ...
    0.25      0            <- 气动参考点 (x/c, y/c)
    ! 坐标表头
    1.000000 -0.000000     <- 轮廓坐标 (x/c, y/c) × 202 行
"""
import os

from .base import split_kv, to_int, is_number_line, numbers, read_lines


def parse_naca_file(path):
    from ..models.airfoil import Airfoil
    lines = read_lines(path)
    num_coords = 0
    reference = (0.25, 0.0)
    coords = []
    phase = 0  # 0=头部, 1=参考点, 2=坐标
    got_reference = False
    for line in lines:
        key, val = split_kv(line)
        if key == 'NumCoords':
            v = to_int(val)
            if v is not None:
                num_coords = v
            continue
        s = line.strip()
        if not s or s.startswith('!') or s.startswith('#'):
            continue
        # 跳过纯文字表头（含 "x/c y/c" 等）
        if not is_number_line(line, min_tokens=2):
            # 可能是 "! x/y ..." 已跳过；也可能是表头文字行
            continue
        vals = numbers(line)
        if len(vals) >= 2:
            if not got_reference:
                reference = (vals[0], vals[1])
                got_reference = True
            else:
                coords.append(vals[:2])
                if num_coords and len(coords) >= num_coords:
                    break
    airfoil = Airfoil(name=os.path.splitext(os.path.basename(path))[0],
                      coords=coords, reference=reference)
    airfoil.path = os.path.normpath(path)
    return airfoil
