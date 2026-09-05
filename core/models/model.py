# -*- coding: utf-8 -*-
"""VAWT 仿真聚合模型：把 6 个输入文件解析结果组装成一个整体，供 GUI/可视化/工况使用。

6 个输入文件：
  - AeroDyn 主输入        AD.dat             (core.parsers.parse_ad)
  - AeroDyn 叶片文件      AD_blade.dat       (core.parsers.parse_blade)
  - AeroDyn Driver 主输入 ad_driver.dvr      (core.parsers.parse_driver)
  - 翼型坐标              NACA_*.txt         (core.parsers.parse_naca)
  - OLAF 主控制           OLAF.dat           (core.parsers.parse_olaf)
  - 翼型极线              Polars.dat         (core.parsers.parse_polars)
"""
import os

from .airfoil import Airfoil
from .blade import Blade
from .turbine import Turbine
from ..parsers import (
    parse_ad_file, parse_blade_file, parse_driver_file,
    parse_naca_file, parse_olaf_file, parse_polars_file,
)


class VAWTModel:
    """聚合模型：保存 6 个输入文件路径 + 解析出的对象。"""

    FILE_KEYS = ['driver', 'ad', 'blade', 'naca', 'olaf', 'polars']

    def __init__(self):
        # 原始文件路径
        self.paths = {k: '' for k in self.FILE_KEYS}
        self.root = ''                     # 模型所在目录（用于相对引用）
        # 解析结果
        self.ad = None                     # dict: AD.dat 关键参数
        self.blade = None                  # Blade 对象
        self.turbine = None                # Turbine 对象
        self.olaf = None                   # dict: OLAF.dat 关键参数
        self.airfoil = None                # Airfoil 对象（来自 NACA 坐标）
        self.airfoil_library = {}          # {AFID: Airfoil}，来自 Polars 的翼型
        self.polar_tables = []             # 全部极线表
        # 可执行文件（AeroDyn Driver / OpenFAST）
        self.executable = ''
        self._loaded = False

    # ------------------------------------------------------------------ 加载
    def load_file(self, key, path):
        """按 key 加载单个文件，返回解析摘要。key ∈ FILE_KEYS。"""
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f'文件不存在: {path}')
        if key == 'driver':
            self.turbine = parse_driver_file(path)
        elif key == 'ad':
            self.ad = parse_ad_file(path)
        elif key == 'blade':
            self.blade = parse_blade_file(path)
        elif key == 'naca':
            self.airfoil = parse_naca_file(path)
        elif key == 'olaf':
            self.olaf = parse_olaf_file(path)
        elif key == 'polars':
            self.airfoil_library, self.polar_tables = parse_polars_file(path)
        else:
            raise ValueError(f'未知文件 key: {key}')
        self.paths[key] = path
        self.root = os.path.dirname(path)
        self._link_airfoils()
        return self.summary_of(key)

    def load_all(self, file_map):
        """file_map: {key: path}，依次加载。"""
        msgs = {}
        for k in self.FILE_KEYS:
            if k in file_map and file_map[k]:
                msgs[k] = self.load_file(k, file_map[k])
        if not self.executable:
            self._probe_executable()
        return msgs

    def _probe_executable(self):
        """在模型目录下探测 AeroDyn Driver / OpenFAST 可执行文件。"""
        if not self.root:
            return
        for fn in ['AeroDyn_Driver_x64.exe', 'AeroDyn_Driver.exe',
                   'openfast_x64.exe', 'openfast.exe']:
            p = os.path.join(self.root, fn)
            if os.path.isfile(p):
                self.executable = p
                return

    def _link_airfoils(self):
        """把叶片节点 AFID 与极线翼型库关联（没有 Polars 时用 NACA 几何）。"""
        if self.blade is None:
            return
        lib = {}
        if self.airfoil_library:
            lib = self.airfoil_library
        else:
            lib = {1: self.airfoil} if self.airfoil is not None else {}
        self.blade.airfoils = lib

    # ------------------------------------------------------------------ 摘要
    def summary_of(self, key):
        if key == 'driver' and self.turbine:
            t = self.turbine
            R = t.rotor_radius()
            geo = f', 直径 D={2*R:.3f} m, 半径 R={R:.3f} m'
            if self.blade is not None:
                c_min = float(self.blade.chord.min())
                c_max = float(self.blade.chord.max())
                geo += (f', 弦长={c_min:.3f}~{c_max:.3f} m, '
                        f'叶片长={float(self.blade.span[-1]):.2f} m')
            return t.summary() + geo
        if key == 'ad' and self.ad:
            return (f'AeroDyn: WakeMod={self.ad.get("WakeMod")} '
                    f'(3=OLAF), AFAeroMod={self.ad.get("AFAeroMod")}, '
                    f'OutList({len(self.ad.get("OutList", []))})')
        if key == 'blade' and self.blade:
            return self.blade.summary()
        if key == 'naca' and self.airfoil:
            return self.airfoil.summary()
        if key == 'olaf' and self.olaf:
            return ('OLAF: ' + ', '.join(f'{k}={v}' for k, v in
                    list(self.olaf.items())[:6]))
        if key == 'polars' and self.polar_tables:
            return f'Polars: {len(self.polar_tables)} Re-tables, airfoils={list(self.airfoil_library)}'
        return ''

    def all_summary(self):
        return {k: self.summary_of(k) for k in self.FILE_KEYS if self.paths.get(k)}

    @property
    def loaded(self):
        return self._loaded or any(self.paths.values())
