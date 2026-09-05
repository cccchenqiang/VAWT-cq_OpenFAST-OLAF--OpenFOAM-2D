# -*- coding: utf-8 -*-
"""结果可视化：时间序列、方位角-攻角、展向分布、极线、功率曲线等。"""
import numpy as np
import matplotlib.pyplot as plt


def new_figure(width=8.0, height=4.5):
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax


def plot_timeseries(df, cols, title='', ax=None, x_col='Time_[s]'):
    """绘制一个或多个通道的时间序列。"""
    if ax is None:
        fig, ax = new_figure()
    else:
        fig = ax.figure
    x = df[x_col].values if x_col in df.columns else np.arange(len(df))
    colors = ['#2f6fbf', '#b26a00', '#2e8b57', '#8b5cf6', '#d64541']
    for i, c in enumerate(cols):
        if c in df.columns:
            ax.plot(x, df[c].values, lw=0.8, label=c, color=colors[i % len(colors)])
    ax.set_xlabel(x_col)
    ax.set_ylabel(' / '.join(cols) if len(cols) <= 2 else 'value')
    ax.grid(alpha=0.3)
    if cols and ax is not None and len(cols) <= 8:
        ax.legend(fontsize=7, ncol=2)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig, ax


def plot_scatter(df, x_col, y_col, title='', ax=None, color='#2e8b57', marker='.', ms=1.5):
    """散点图（如攻角随方位角）。"""
    if ax is None:
        fig, ax = new_figure()
    else:
        fig = ax.figure
    ax.plot(df[x_col].values, df[y_col].values, marker, ms=ms, color=color)
    ax.set_xlabel(x_col); ax.set_ylabel(y_col)
    ax.grid(alpha=0.3)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig, ax


def plot_spanwise_profile(df, base_name, span, ax=None, prefix='AB1N', node_prefix='N',
                          title=''):
    """展向分布：base_name 形如 'AB1N001Alpha_[deg]'，span 为展向坐标数组。"""
    if ax is None:
        fig, ax = new_figure()
    else:
        fig = ax.figure
    n = len(span)
    values = []
    for i in range(1, n + 1):
        col = f'{prefix}{i:03d}{base_name}'
        if col in df.columns:
            values.append(float(df[col].values[-1]))
        else:
            values.append(np.nan)
    ax.plot(span, values, '-o', ms=3, color='#8b5cf6')
    ax.set_xlabel('Blade span [m]'); ax.set_ylabel(base_name)
    ax.grid(alpha=0.3)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig, ax


def plot_polar_curve(airfoil, re_millions=None, ax=None):
    """绘制翼型极线（Cl/Cd vs alpha）。"""
    if ax is None:
        fig, ax = new_figure(8, 4.2)
    else:
        fig = ax.figure
    polar = airfoil.polar_at_re(re_millions) if airfoil.polar_tables else None
    if polar is None or len(polar) == 0:
        ax.text(0.5, 0.5, 'No polar data', ha='center', va='center', transform=ax.transAxes)
        fig.tight_layout()
        return fig, ax
    ax.plot(polar.alpha, polar.cl, label='Cl', color='#2f6fbf')
    ax.plot(polar.alpha, polar.cd, label='Cd', color='#d64541')
    ax.set_xlabel('Angle of attack [deg]'); ax.set_ylabel('Cl / Cd [-]')
    re_str = f'{polar.re_millions:.3f}' if polar.re_millions is not None else 'unknown'
    ax.set_title(f'Polar @ Re={re_str}M')
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout()
    return fig, ax


def plot_power_curve(summary_df, x='U0', y='P_mean', ax=None):
    """功率曲线：批量工况汇总表绘图。"""
    if ax is None:
        fig, ax = new_figure()
    else:
        fig = ax.figure
    ax.plot(summary_df[x], summary_df[y], '-o', color='#2f6fbf', ms=4)
    ax.set_xlabel(x); ax.set_ylabel(y)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig, ax
