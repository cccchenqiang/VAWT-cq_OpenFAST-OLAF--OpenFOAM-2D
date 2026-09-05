# -*- coding: utf-8 -*-
"""用 matplotlib 3D 绘制风轮几何（坐标系、叶片翼型、塔筒、转轴）。"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def _plot_axes(ax, origin, length=1.0, labels=('X', 'Y', 'Z'), color_tag='global',
               basis=None):
    """画坐标系。basis 为 3×3 列向量矩阵（每列一个轴方向，全局坐标）；默认标准基。"""
    colors = {'global': {'x': '#d64541', 'y': '#2e8b57', 'z': '#2f6fbf'},
              'hub': {'x': '#d64541', 'y': '#2e8b57', 'z': '#2f6fbf'}}
    c = colors.get(color_tag, colors['global'])
    B = np.eye(3) if basis is None else np.asarray(basis, dtype=float)
    for i, ch in enumerate(['x', 'y', 'z']):
        v = B[:, i] * length
        ax.quiver(origin[0], origin[1], origin[2],
                  v[0], v[1], v[2], color=c[ch], arrow_length_ratio=0.12, linewidth=2)
        ax.text(origin[0] + v[0] * 1.15, origin[1] + v[1] * 1.15, origin[2] + v[2] * 1.15,
                labels[i], color=c[ch], fontsize=10, fontweight='bold')


def _plot_tower(ax, tower):
    """塔筒：按 (elev, diam) 节点绘制半透明圆柱（简化：沿 z 的圆环堆叠）。"""
    if not tower:
        return
    elev = np.asarray(tower['elev'])
    diam = np.asarray(tower['diam'])
    theta = np.linspace(0, 2 * np.pi, 24)
    n = len(elev)
    for i in range(n - 1):
        z0, z1 = elev[i], elev[i + 1]
        r0, r1 = diam[i] / 2, diam[i + 1] / 2
        for j in range(len(theta) - 1):
            corners = [
                [r0 * np.cos(theta[j]), r0 * np.sin(theta[j]), z0],
                [r0 * np.cos(theta[j + 1]), r0 * np.sin(theta[j + 1]), z0],
                [r1 * np.cos(theta[j + 1]), r1 * np.sin(theta[j + 1]), z1],
                [r1 * np.cos(theta[j]), r1 * np.sin(theta[j]), z1],
            ]
            ax.add_collection3d(Poly3DCollection([corners], color='#8a8f98',
                                                 alpha=0.55, edgecolor='#5a5f68', linewidth=0.2))


def _plot_blade(ax, blade, show_airfoils=True, airfoil_scale=1.0):
    """画单支叶片：中心线 + 翼型截面多边形。

    airfoil_scale: 翼型截面放大倍数（相对弦线中心放大，便于观察翼型形状）。
    """
    cl = blade['centerline']
    ax.plot(cl[:, 0], cl[:, 1], cl[:, 2], color='#b26a00', lw=2.0)
    for sec in blade['sections']:
        poly = sec['poly']
        if airfoil_scale != 1.0:
            c = sec['pos']
            poly = c + (poly - c) * airfoil_scale
        if show_airfoils and len(poly) > 2:
            # 填充翼型截面（半透明）
            tri = []
            for i in range(len(poly) - 1):
                tri.append([poly[0], poly[i], poly[i + 1]])
            ax.add_collection3d(Poly3DCollection(tri, color='#8b5cf6',
                                                 alpha=0.35, edgecolor='#6d28d9',
                                                 linewidth=0.5))
        else:
            ax.plot(poly[:, 0], poly[:, 1], poly[:, 2], color='#6d28d9', lw=0.8)
    # 叶尖标记
    tip = cl[-1]
    ax.scatter([tip[0]], [tip[1]], [tip[2]], color='#b26a00', s=18)


def _fixed_limits(geom, airfoil_scale=1.0):
    """计算不随方位角变化的固定坐标范围（绕转轴对称化径向半径）。

    叶片绕转轴旋转时，扫掠范围是同一圆周；因此把 x/y（垂直于转轴的平面）
    固定为 ±(最大半径 + 放大弦长半宽 + 边距)，z（转轴方向）固定为数据范围。
    这样拖动方位角滑条时，坐标轴与坐标原点不再缩放跳动。
    """
    hub = np.asarray(geom['hub'], dtype=float)
    axis = np.asarray(geom['rotor_axis'], dtype=float)
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    pts = [np.asarray(geom['base_origin'], dtype=float)]
    half_chord_max = 0.0
    for b in geom['blades']:
        pts.append(np.asarray(b['origin'], dtype=float))
        pts.extend(np.asarray(b['centerline']))
        for s_ in b['sections']:
            half_chord_max = max(half_chord_max, 0.5 * float(s_.get('chord', 0.0)))
    if geom.get('tower'):
        for e in geom['tower']['elev']:
            pts.append(np.array([0.0, 0.0, float(e)]))
    P = np.asarray(pts)
    rel = P - hub
    s = rel @ axis
    r = np.linalg.norm(rel - np.outer(s, axis), axis=1)
    R = float(r.max()) + half_chord_max * airfoil_scale + 0.35
    if abs(axis[2]) > 0.9:
        # 转轴沿 z（VAWT 常见）：x/y 取 ±R，z 用全局 z 范围
        m = 0.35
        z0 = float(s.min()) + hub[2] - m
        z1 = float(s.max()) + hub[2] + m
        return (-R, R), (-R, R), (z0, z1)
    # 通用情形：用数据包围盒 + 边距（无法绕任意轴对称化到正交轴）
    m = 0.5
    return ((float(P[:, 0].min()) - m, float(P[:, 0].max()) + m),
            (float(P[:, 1].min()) - m, float(P[:, 1].max()) + m),
            (float(P[:, 2].min()) - m, float(P[:, 2].max()) + m))


def plot_geometry_3d(geom, ax=None, show_airfoils=True, show_axes=True,
                     show_rotor_axis=True, show_hub=True, equal_aspect=True,
                     airfoil_scale=1.0, fixed_limits=True):
    """绘制风轮几何。返回 (fig, ax)；若传入 ax 则不新建 fig。

    airfoil_scale: 翼型截面放大倍数（默认 1，不改动几何尺寸）。
    """
    if ax is None:
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection='3d')
    else:
        fig = ax.figure

    # 全局坐标系（global origin = base 原点，AeroDyn 惯性系 i）
    base = geom['base_origin']
    if show_axes:
        _plot_axes(ax, base, length=1.0, labels=('X', 'Y', 'Z'),
                   color_tag='global')

    # 塔筒
    _plot_tower(ax, geom['tower'])

    # 轮毂坐标系（hub 原点，x 沿转轴）
    hub = geom['hub']
    if show_hub:
        R_hub = geom.get('R_hub', np.eye(3))
        if show_axes:
            _plot_axes(ax, hub, length=0.8, labels=('x_h', 'y_h', 'z_h'),
                       color_tag='hub', basis=R_hub)
        ax.scatter([hub[0]], [hub[1]], [hub[2]], color='#1a1b1c', s=40, marker='o')
    if show_rotor_axis:
        r = geom['rotor_axis']
        L = max(2.0, np.max([np.linalg.norm(b['centerline'][-1] - hub) for b in geom['blades']]) * 0.7)
        ax.quiver(hub[0], hub[1], hub[2], r[0] * L, r[1] * L, r[2] * L,
                  color='#1a1b1c', arrow_length_ratio=0.15, linewidth=2)
        ax.text(hub[0] + r[0] * L * 1.1, hub[1] + r[1] * L * 1.1, hub[2] + r[2] * L * 1.1,
                'rotor axis', fontsize=9, color='#1a1b1c')

    # 叶片
    for b in geom['blades']:
        _plot_blade(ax, b, show_airfoils=show_airfoils, airfoil_scale=airfoil_scale)

    # 坐标等比例
    if equal_aspect:
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass
    # 固定坐标范围（不随方位角旋转而变化），避免视图缩放跳动
    if fixed_limits:
        xl, yl, zl = _fixed_limits(geom, airfoil_scale=airfoil_scale)
        ax.set_xlim(xl); ax.set_ylim(yl); ax.set_zlim(zl)
    ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
    ax.set_title(f'VAWT geometry (rotor angle = {geom["rotor_angle_deg"]:.1f} deg)')
    return fig, ax
