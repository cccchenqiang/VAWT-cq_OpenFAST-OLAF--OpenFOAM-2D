# -*- coding: utf-8 -*-
"""解析 AeroDyn 气动主输入 (AD.dat) -> dict。

重点提取：WakeMod、AFAeroMod、OLAF 输入文件、翼型文件、OutList 通道、节点输出。
"""
import os

from .base import split_kv, to_str, to_float, to_int, to_bool, is_number_line, numbers, read_lines


def parse_ad_file(path):
    res = {
        'path': os.path.normpath(path),
        'Echo': None, 'DTAero': None, 'WakeMod': None, 'AFAeroMod': None,
        'TwrAero': False, 'OLAFInputFileName': None,
        'AFTabMod': None, 'InCol_Alfa': 1, 'InCol_Cl': 2, 'InCol_Cd': 3, 'InCol_Cm': 4,
        'NumAFfiles': 1, 'AFNames': [],
        'ADBlFile': [], 'UseBlCm': True,
        'OutList': [], 'OutListAD': [],
        'NBlOuts': 0, 'BlOutNd': [], 'BldNd_BladesOut': 0,
        'NumTwrNds': 0, 'tower_nodes': [],   # 塔筒节点 (elev, diam)
    }
    lines = read_lines(path)
    in_outlist = False
    in_outlist_ad = False
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        # ---- 段结束（END 行，大小写不敏感）----
        if s.upper().startswith('END'):
            in_outlist = False
            in_outlist_ad = False
            i += 1
            continue
        # ---- 段起始行（无 value 的段标记，split_kv 无法解析）----
        if s.startswith('OutList') and not s.startswith('OutListAD'):
            in_outlist = True
            i += 1
            continue
        if s.startswith('OutListAD'):
            in_outlist_ad = True
            i += 1
            continue
        # ---- 段内通道行 ----
        if in_outlist and s.startswith('"') and len(s.split()) == 1:
            res['OutList'].append(s.strip('"'))
            i += 1
            continue
        if in_outlist_ad and s and not s.startswith(('"', '!', '#')) \
                and len(s.split()) == 1:
            res['OutListAD'].append(s)
            i += 1
            continue

        key, val = split_kv(line)
        if not key:
            i += 1
            continue
        if key == 'OutList':
            in_outlist = True
            i += 1
            continue
        if key == 'OutListAD':
            in_outlist_ad = True
            i += 1
            continue
        if key == 'BldNd_BladesOut':
            v = to_int(val)
            if v is not None: res['BldNd_BladesOut'] = v
        if key == 'NBlOuts':
            v = to_int(val)
            if v is not None: res['NBlOuts'] = v
        elif key == 'WakeMod':
            v = to_int(val)
            if v is not None: res['WakeMod'] = v
        elif key == 'AFAeroMod':
            v = to_int(val)
            if v is not None: res['AFAeroMod'] = v
        elif key == 'DTAero':
            res['DTAero'] = to_str(val)
        elif key == 'TwrAero':
            res['TwrAero'] = to_bool(val)
        elif key == 'OLAFInputFileName':
            res['OLAFInputFileName'] = to_str(val)
        elif key == 'AFTabMod':
            v = to_int(val)
            if v is not None: res['AFTabMod'] = v
        elif key.startswith('InCol_'):
            v = to_int(val)
            if v is not None: res[key] = v
        elif key == 'NumAFfiles':
            v = to_int(val)
            if v is not None: res['NumAFfiles'] = v
        elif key == 'AFNames':
            res['AFNames'].append(to_str(val))
        elif key.startswith('ADBlFile'):
            res['ADBlFile'].append(to_str(val))
        elif key == 'UseBlCm':
            res['UseBlCm'] = to_bool(val)
        elif key == 'NumTwrNds':
            v = to_int(val)
            if v is not None: res['NumTwrNds'] = v
        elif key.startswith('BlOutNd'):
            v = to_int(val)
            if v is not None: res['BlOutNd'].append(v)
        # 塔筒表数据行（TwrElev TwrDiam TwrCd ...）——位于塔筒表头之后
        elif res.get('NumTwrNds', 0) and is_number_line(line, min_tokens=2) \
                and len(res['tower_nodes']) < res['NumTwrNds']:
            vals = numbers(line)
            if len(vals) >= 2:
                res['tower_nodes'].append((vals[0], vals[1]))
        i += 1
    return res
