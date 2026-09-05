# -*- coding: utf-8 -*-
"""结果文件读取：优先用 openfast_toolbox.FASTOutputFile，失败回退 ASCII 解析。"""
import os
import numpy as np
import pandas as pd


def load_fast_output(path):
    """读取 OpenFAST / AeroDyn Driver 结果文件（.out ASCII / .outb 二进制）。

    返回 pandas DataFrame（列名含单位，如 Time_[s]、RtAeroPwr_[W]）。
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f'结果文件不存在: {path}')
    try:
        from openfast_toolbox.io import FASTOutputFile
        return FASTOutputFile(path).toDataFrame()
    except Exception as e1:
        # 回退到 ASCII 手动解析
        try:
            return _load_ascii(path)
        except Exception as e2:
            raise RuntimeError(f'无法解析结果文件: {e1} / {e2}')


def _load_ascii(path, encoding='utf-8', errors='replace'):
    """解析 ASCII 表格式结果文件（两行表头 + 数据行）。"""
    with open(path, 'r', encoding=encoding, errors=errors) as f:
        lines = f.readlines()
    # 表头通常 2 行（参数名 / 单位），但 AeroDyn 可能有额外的标题行
    data_start = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('Time') and '\t' in s or (s.startswith('Time') and '  ' in s):
            data_start = i
            break
    if data_start is None:
        # 回退：找到含 'Time' 的行
        for i, ln in enumerate(lines):
            if 'Time' in ln and ('(' in ln or '[' in ln):
                data_start = i
                break
    if data_start is None:
        raise ValueError('未找到数据表头')
    header = lines[data_start].split()
    units = lines[data_start + 1].split() if data_start + 1 < len(lines) else []
    cols = []
    for j, h in enumerate(header):
        u = units[j] if j < len(units) else ''
        # 统一列名格式为 Name_[unit]，与 openfast_toolbox.FASTOutputFile 一致
        cols.append(f'{h}_[{u}]' if u else h)
    data = []
    for ln in lines[data_start + 2:]:
        s = ln.strip()
        if not s:
            continue
        parts = s.split()
        try:
            data.append([float(p) for p in parts])
        except ValueError:
            continue
    if not data:
        raise ValueError('无数据行')
    arr = np.asarray(data)
    return pd.DataFrame(arr[:, :len(cols)], columns=cols[:arr.shape[1]])
