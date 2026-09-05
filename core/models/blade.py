# -*- coding: utf-8 -*-
"""叶片数据模型：AeroDyn 叶片节点表（气动分布）。"""
import numpy as np


class Blade:
    """AeroDyn 叶片气动定义（对应 AD_blade.dat 的 BldAeroNodes 表）。

    列（与 AD_blade.dat 一致）:
      BlSpn BlCrvAC BlSwpAC BlCrvAng BlTwist BlChord BlAFID BlCb BlCenBn BlCenBt
    """

    COLUMNS = ['BlSpn', 'BlCrvAC', 'BlSwpAC', 'BlCrvAng', 'BlTwist',
               'BlChord', 'BlAFID', 'BlCb', 'BlCenBn', 'BlCenBt']

    def __init__(self, nodes=None, num_nodes=0, airfoils=None):
        self.nodes = np.asarray(nodes, dtype=float).reshape(-1, len(self.COLUMNS)) \
            if nodes is not None else np.zeros((0, len(self.COLUMNS)))
        self.num_nodes = int(num_nodes) if num_nodes else len(self.nodes)
        # airfoils: {AFID: Airfoil}，由 Polars.dat 提供的翼型库按 ID 关联
        self.airfoils = airfoils if airfoils is not None else {}

    # ---- 便捷属性 ----
    @property
    def span(self):
        return self.nodes[:, 0]

    @property
    def crv_ac(self):
        return self.nodes[:, 1]

    @property
    def swp_ac(self):
        return self.nodes[:, 2]

    @property
    def crv_ang(self):
        return self.nodes[:, 3]

    @property
    def twist(self):
        return self.nodes[:, 4]

    @property
    def chord(self):
        return self.nodes[:, 5]

    @property
    def afid(self):
        return self.nodes[:, 6].astype(int)

    def airfoil_at_node(self, i):
        """返回第 i 节点的翼型对象（按 AFID 关联，缺失返回 None）。"""
        return self.airfoils.get(int(self.afid[i]))

    def summary(self):
        return (f'Blade: {len(self.span)} nodes, span 0..{self.span[-1]:.3f} m, '
                f'chord {self.chord.min():.3f}..{self.chord.max():.3f} m, '
                f'AFIDs {sorted(set(self.afid.tolist()))}')
