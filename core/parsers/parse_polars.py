# -*- coding: utf-8 -*-
"""解析翼型极线文件 (Polars.dat, AirfoilInfo v1.01 格式)。

返回 (airfoil_library, polar_tables)：
  - airfoil_library : {AFID: Airfoil}（此文件中一个翼型，AFID=1）
  - polar_tables    : [PolarTable, ...] 全部雷诺数表
"""
import os

from .base import split_kv, to_str, to_float, to_int, is_number_line, numbers, read_lines


def parse_polars_file(path):
    from ..models.airfoil import Airfoil, PolarTable
    lines = read_lines(path)
    meta = {}
    tables = []
    cur_re = None
    cur = {'alpha': [], 'cl': [], 'cd': [], 'cm': []}
    pending_alpha = 0          # 待读的数据行数
    state = 'header'           # header / table_meta / ua / data
    coords_file = None

    i = 0
    while i < len(lines):
        line = lines[i]
        key, val = split_kv(line)
        if key == 'NumCoords':
            # 形如  @"NACA_0018_Coords.txt" NumCoords
            v = to_str(val)
            if v.startswith('@'):
                coords_file = v[1:]
            i += 1
            continue
        if key == 'NumTabs':
            meta['NumTabs'] = to_int(val)
            i += 1
            continue
        if key == 'Re':
            # 新表开始
            if cur_re is not None:  # 保存上一表
                _finalize_table(tables, cur, cur_re)
            cur_re = to_float(val)
            cur = {'alpha': [], 'cl': [], 'cd': [], 'cm': []}
            state = 'table_meta'
            i += 1
            continue
        if key == 'NumAlf':
            v = to_int(val)
            pending_alpha = v if v is not None else 0
            state = 'data'
            i += 1
            continue
        if state == 'data':
            # 收集数据行（alpha Cl Cd [Cm]），跳过表头
            if is_number_line(line, min_tokens=3):
                vals = numbers(line)
                if len(vals) >= 3:
                    cur['alpha'].append(vals[0])
                    cur['cl'].append(vals[1])
                    cur['cd'].append(vals[2])
                    cur['cm'].append(vals[3] if len(vals) > 3 else 0.0)
                    if pending_alpha and len(cur['alpha']) >= pending_alpha:
                        state = 'header'
            i += 1
            continue
        i += 1
    # 收尾
    if cur_re is not None:
        _finalize_table(tables, cur, cur_re)

    af_name = os.path.splitext(os.path.basename(path))[0]
    airfoil = Airfoil(name=af_name, polar_tables=tables)
    airfoil.path = os.path.normpath(path)
    airfoil.coords_file = coords_file
    return {1: airfoil}, tables


def _finalize_table(tables, cur, re_val):
    from ..models.airfoil import PolarTable
    n = min(len(cur['alpha']), len(cur['cl']), len(cur['cd']))
    if n > 0:
        tables.append(PolarTable(
            re_millions=re_val,
            alpha=cur['alpha'][:n], cl=cur['cl'][:n], cd=cur['cd'][:n],
            cm=cur['cm'][:n], num_alpha=n))
