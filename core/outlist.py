# -*- coding: utf-8 -*-
"""读取 OutListParameters.xlsx（OpenFAST 官方输出参数表）并提供通道查询。"""
import os
import pandas as pd

DEFAULT_XLSX = r'D:\BaiduNetdiskDownload\OpenFast\Openfast user manual\OutListParameters.xlsx'

# AeroDyn 相关 sheet（OLAF 属 AeroDyn 模块）
AERODYN_SHEETS = ['AeroDyn', 'AeroDyn_Nodes']


def load_module_channels(xlsx_path, module='AeroDyn'):
    """读取指定模块 sheet 的输出通道表，返回 DataFrame(Category, Name, Description, Units...)。"""
    if not os.path.isfile(xlsx_path):
        raise FileNotFoundError(f'未找到输出参数表: {xlsx_path}')
    df = pd.read_excel(xlsx_path, sheet_name=module)
    df['Category'] = df['Category'].ffill()          # 分类向下填充
    df = df[df['Name'].notna()].copy()               # 丢弃分组行
    df['Units'] = df['Units'].astype(str).replace('nan', '')
    df['Description'] = df['Description'].astype(str).replace('nan', '')
    return df.reset_index(drop=True)


def load_aerodyn_channels(xlsx_path):
    """合并 AeroDyn 与 AeroDyn_Nodes 两个 sheet，供 GUI 展示与选择。"""
    frames = []
    for sn in AERODYN_SHEETS:
        try:
            df = load_module_channels(xlsx_path, sn)
            df['Sheet'] = sn
            frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def search_channels(df, keyword=''):
    """按关键词过滤通道（Name / Description 匹配）。"""
    if not keyword.strip():
        return df
    k = keyword.strip().lower()
    mask = (df['Name'].astype(str).str.lower().str.contains(k) |
            df['Description'].astype(str).str.lower().str.contains(k))
    return df[mask]


def get_outlist_units(df, name):
    """按通道名查单位（用于写回 AD.dat 时标注）。"""
    row = df[df['Name'] == name]
    if len(row):
        u = row.iloc[0].get('Units', '')
        return u if u and u != 'nan' else ''
    return ''
