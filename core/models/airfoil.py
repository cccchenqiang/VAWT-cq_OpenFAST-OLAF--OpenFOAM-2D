# -*- coding: utf-8 -*-
"""翼型数据模型：几何坐标 + 气动极线（多雷诺数表）。"""
import numpy as np


class PolarTable:
    """单个雷诺数下的气动极线表。"""

    def __init__(self, re_millions=0.0, alpha=None, cl=None, cd=None, cm=None, num_alpha=0):
        self.re_millions = float(re_millions)      # 雷诺数（百万）
        self.num_alpha = int(num_alpha)
        n = max(len(alpha) if alpha is not None else 0, num_alpha)
        self.alpha = np.asarray(alpha, dtype=float) if alpha is not None else np.zeros(n)
        self.cl = np.asarray(cl, dtype=float) if cl is not None else np.zeros(n)
        self.cd = np.asarray(cd, dtype=float) if cd is not None else np.zeros(n)
        self.cm = np.asarray(cm, dtype=float) if cm is not None else np.zeros(n)

    def __len__(self):
        return len(self.alpha)


class Airfoil:
    """翼型：名称、归一化坐标（x/c, y/c）、气动参考点、多 Re 极线。"""

    def __init__(self, name='', coords=None, reference=(0.25, 0.0), polar_tables=None):
        self.name = name or 'unnamed'
        # coords: Nx2 数组，沿翼型轮廓（上表面从前缘到后缘，再下表面返回前缘）
        self.coords = np.asarray(coords, dtype=float).reshape(-1, 2) if coords is not None else np.zeros((0, 2))
        self.reference = np.asarray(reference, dtype=float)   # 气动参考点 (x/c, y/c)
        self.polar_tables = polar_tables if polar_tables is not None else []

    @property
    def num_coords(self):
        return len(self.coords)

    @property
    def chord_ref(self):
        return self.reference

    def thickness_ratio(self):
        """由坐标估计相对厚度 t/c（粗略，用上下表面最大 y 之差）。"""
        if self.num_coords < 3:
            return 0.0
        # 分成上/下表面：假设坐标从 (1,0) 前缘出发。简化：按 x 排序找最大 y 幅度
        y = self.coords[:, 1]
        return float(y.max() - y.min())

    def scaled_coords(self, chord, center=(0.0, 0.0)):
        """把归一化翼型坐标按弦长缩放并平移到给定中心。返回 Nx2。"""
        if self.num_coords == 0:
            return np.zeros((0, 2))
        x = (self.coords[:, 0] - self.reference[0]) * chord + center[0]
        y = (self.coords[:, 1] - self.reference[1]) * chord + center[1]
        return np.column_stack([x, y])

    def polar_at_re(self, re_millions):
        """按雷诺数插值选择最接近的极线表。

        传入 None 时（未指定 Re）返回第一张有数据的表；
        仅在不带 Re 的表之间比较，忽略 re_millions 为 None 的表。
        """
        if not self.polar_tables:
            return None
        tables = [t for t in self.polar_tables if t.re_millions is not None]
        if not tables:
            return self.polar_tables[0]
        if re_millions is None:
            return tables[0]
        return min(tables, key=lambda t: abs(float(t.re_millions) - float(re_millions)))

    def summary(self):
        return (f'Airfoil "{self.name}": {self.num_coords} coords, '
                f'{len(self.polar_tables)} Re-tables, '
                f't/c~{self.thickness_ratio():.3f}')
