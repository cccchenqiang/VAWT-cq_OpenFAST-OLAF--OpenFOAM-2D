# -*- coding: utf-8 -*-
"""结果统计：稳态段统计、Cp/TSR、周期平均、简化疲劳（DEL）。"""
import numpy as np
import pandas as pd


def steady_stats(df, col, frac=0.5):
    """取后 frac 时间段的均值/标准差/极值。返回 dict。"""
    if col not in df.columns:
        return {'mean': np.nan, 'std': np.nan, 'min': np.nan, 'max': np.nan, 'n': 0}
    t = df['Time_[s]'].values if 'Time_[s]' in df.columns else np.arange(len(df))
    v = df[col].values
    i0 = int((1 - frac) * len(v))
    seg = v[i0:]
    return {'mean': float(seg.mean()), 'std': float(seg.std()),
            'min': float(seg.min()), 'max': float(seg.max()), 'n': int(len(seg))}


def calc_cp_tsr(p_mean, U0, RPM, R, H=None, rho=1.225, swept_area=None):
    """由平均功率算 Cp（VAWT 扫掠面积 A=D×H）与 TSR。"""
    A = swept_area if swept_area is not None else (2 * R * H)
    TSR = 2 * np.pi * (RPM / 60.0) * R / U0
    Cp = p_mean / (0.5 * rho * A * U0 ** 3) if U0 > 0 else 0.0
    return dict(Cp=Cp, TSR=TSR, A=A)


def azimuth_average(df, col, az_col='Azimuth_[deg]', n_bins=72):
    """按方位角分桶求周期平均（VAWT 每转内的平均特性）。"""
    if col not in df.columns or az_col not in df.columns:
        return None
    az = df[az_col].values % 360.0
    v = df[col].values
    edges = np.linspace(0, 360, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    means = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (az >= lo) & (az < hi)
        means.append(v[mask].mean() if mask.any() else np.nan)
    return pd.DataFrame({'azimuth_deg': centers, col: means})


def rainflow_equivalent_load(df, col, m=10, n_equiv=1e7):
    """基于 rainflow 计数的等效疲劳载荷 DEL（简化实现）。

    无专用包时用"循环幅值 = 峰值-谷值"近似（对稳态周期信号足够）。
    """
    if col not in df.columns:
        return np.nan
    v = df[col].values
    if len(v) < 3:
        return np.nan
    # 提取峰谷
    peaks = []
    for i in range(1, len(v) - 1):
        if (v[i] >= v[i - 1] and v[i] > v[i + 1]) or (v[i] <= v[i - 1] and v[i] < v[i + 1]):
            peaks.append(v[i])
    if len(peaks) < 2:
        return np.nan
    # 相邻峰谷幅值的一半作为循环幅值
    amp = np.abs(np.diff(peaks)) / 2.0
    amp = amp[amp > 0]
    if len(amp) == 0:
        return np.nan
    n = len(amp)
    eq = (np.sum(amp ** m) / n_equiv) ** (1.0 / m)
    return float(eq)
