# -*- coding: utf-8 -*-
"""解析 OLAF（自由涡尾迹）主控制文件 (OLAF.dat) -> dict。

注意：OLAF.dat 含"网格输出表"段（含字符串行），用轻量 key 解析即可跳过表格行。
"""
import os

from .base import split_kv, to_str, to_float, to_int, to_bool, read_lines


def parse_olaf_file(path):
    res = {'path': os.path.normpath(path)}
    # 关心的 key -> 转换函数
    INT_KEYS = ['nNWPanels', 'nNWPanelsFree', 'nFWPanels', 'nFWPanelsFree',
                'VelocityMethod', 'RegDeterMethod', 'GridShapeMethod',
                'nGridOut', 'WrVTk', 'WrVTk_Type', 'ReMethod', 'WakeRelax',
                'CoreSpreadMethod', 'NWPanels1', 'NWPanels2', 'NWPanels3', 'NNDesired',
                'TimeIntegr', 'Verification', 'RegMethod']
    FLOAT_KEYS = ['DTFVW', 'DTfvw', 'WrVTk_dt', 'XStart', 'XEnd', 'YStart', 'YEnd',
                  'ZStart', 'ZEnd', 'Reynolds', 'MaxDisVel',
                  'VortexRadius', 'VortexRadCon', 'ViscCore', 'WakeRlxFactor',
                  'StrtFactor', 'DtAero', 'TMaxOLAF']
    STR_KEYS = ['GridType', 'MHK', 'WrVTk_Format']
    for line in read_lines(path):
        key, val = split_kv(line)
        if not key:
            continue
        if key in INT_KEYS:
            v = to_int(val)
            if v is not None: res[key] = v
        elif key in FLOAT_KEYS:
            v = to_float(val)
            if v is not None: res[key] = v
        elif key in STR_KEYS:
            res[key] = to_str(val)
    return res
