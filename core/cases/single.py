# -*- coding: utf-8 -*-
"""单工况：定义工况参数，生成独立工况目录（复制模型 + 应用参数 + 写回）。"""
import os
import shutil

from .template import update_fast_file, set_olaf_panels

# 复制到工况目录的模型文件
MODEL_FILES = ['ad_driver.dvr', 'AD.dat', 'AD_blade.dat', 'OLAF.dat',
               'NACA_0018_Coords.txt', 'Polars.dat']


class SingleCaseConfig:
    """单个 AeroDyn Driver (OLAF) 工况参数。"""

    def __init__(self, name='case', U0=8.0, RPM=273.0, TMax=1.0, DT=0.0006,
                 pitch_deg=0.0, yaw_deg=0.0, out_format=1, wr_vtk=0,
                 olaf_wr_vtk=0, olaf_n_vtk_blades=0, olaf_vtk_coord=1,
                 olaf_vtk_fps=20, olaf_n_grid_out=0,
                 use_fast_olaf_grid=False, nNW=None, nNWFree=None,
                 outlist=None, outlist_ad=None):
        self.name = name
        self.U0 = float(U0)
        self.RPM = float(RPM)
        self.TMax = float(TMax)
        self.DT = float(DT)
        self.pitch_deg = float(pitch_deg)
        self.yaw_deg = float(yaw_deg)
        self.out_format = int(out_format)      # 1=text, 2=binary, 3=both
        self.wr_vtk = int(wr_vtk)              # 0=none, 1=init, 2=animation
        self.olaf_wr_vtk = int(olaf_wr_vtk)
        self.olaf_n_vtk_blades = int(olaf_n_vtk_blades)
        self.olaf_vtk_coord = int(olaf_vtk_coord)
        self.olaf_vtk_fps = olaf_vtk_fps
        self.olaf_n_grid_out = int(olaf_n_grid_out)
        self.use_fast_olaf_grid = bool(use_fast_olaf_grid)
        self.nNW = nNW
        self.nNWFree = nNWFree
        self.outlist = outlist or []           # AD.dat 的 OutList
        self.outlist_ad = outlist_ad or []     # AD.dat 的 OutListAD（节点输出）
        self.files = {}                        # 工况目录中关键文件路径

    def __repr__(self):
        return (f'SingleCase({self.name}, U0={self.U0}, RPM={self.RPM}, '
                f'TMax={self.TMax}, DT={self.DT})')


def generate_single_case(model, case: SingleCaseConfig, work_dir):
    """在工作目录下生成一个工况：复制模型文件、应用参数、写回。返回 case（含文件路径）。"""
    os.makedirs(work_dir, exist_ok=True)

    # 1) 复制模型文件（跳过缺失项）
    copied = {}
    for fn in MODEL_FILES:
        if fn in model.paths and model.paths[fn]:
            shutil.copy2(model.paths[fn], os.path.join(work_dir, fn))
            copied[fn] = os.path.join(work_dir, fn)
        else:
            # 从模型根目录按名匹配
            src = os.path.join(model.root, fn)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(work_dir, fn))
                copied[fn] = os.path.join(work_dir, fn)

    # 2) 修改 dvr 工况参数
    dvr_path = copied.get('ad_driver.dvr')
    if dvr_path:
        upd = {'HWindSpeed': case.U0, 'TMax': case.TMax, 'DT': case.DT,
               'WrVTK': case.wr_vtk, 'OutFileFmt': case.out_format}
        try:
            update_fast_file(dvr_path, upd)
        except KeyError as e:
            raise RuntimeError(f'修改 dvr 失败: {e}')
        # 转速 / 桨距 / 偏航（带下标）
        try:
            update_fast_file(dvr_path, {'RotSpeed(1)': case.RPM})
        except KeyError:
            update_fast_file(dvr_path, {'RotSpeed': case.RPM})
        if case.pitch_deg:
            for i in range(1, model.turbine.num_blades + 1):
                try:
                    update_fast_file(dvr_path, {f'BldPitch(1_{i})': case.pitch_deg})
                except KeyError:
                    pass
        if case.yaw_deg:
            try:
                update_fast_file(dvr_path, {'NacYaw(1)': case.yaw_deg})
            except KeyError:
                pass

    # 3) 修改 AD.dat 的 OutList（若提供）
    ad_path = copied.get('AD.dat')
    if ad_path and case.outlist:
        _rewrite_outlist(ad_path, case.outlist, 'OutList')
    if ad_path and case.outlist_ad:
        _rewrite_outlist(ad_path, case.outlist_ad, 'OutListAD')

    # 4) OLAF.dat：快速网格和独立的尾迹 VTK 输出
    olaf_path = copied.get('OLAF.dat')
    if olaf_path:
        set_olaf_panels(olaf_path,
                        nNW=(case.nNW if case.use_fast_olaf_grid else None),
                        nNWFree=(case.nNWFree if case.use_fast_olaf_grid else None),
                        wr_vtk=case.olaf_wr_vtk,
                        n_grid_out=case.olaf_n_grid_out,
                        n_vtk_blades=case.olaf_n_vtk_blades,
                        vtk_coord=case.olaf_vtk_coord,
                        vtk_fps=case.olaf_vtk_fps)

    case.files = copied
    return case


def _rewrite_outlist(ad_path, channels, section='OutList'):
    """用新通道列表重写 AD.dat 中的 OutList / OutListAD 段。

    策略：定位 `section` 起始行 → 其后的第一个 "END of input file" 行作为段结尾
    → 整段替换为：段标记行 + 通道行 + END 行。
    """
    with open(ad_path, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.readlines()

    # 定位段起始（精确匹配段名，避免误匹配 OutListAD）
    start = None
    for i, line in enumerate(raw):
        s = line.strip()
        if s == section or s.startswith(section + ' '):
            start = i
            break
    if start is None:
        return
    # 定位段内第一个 END 行
    end = None
    for i in range(start + 1, len(raw)):
        if raw[i].strip().upper().startswith('END'):
            end = i
            break
    if end is None:
        return

    block = [f'{" " * 19}{section}  - the next line(s) contains a list of output parameters.\n']
    for ch in channels:
        block.append(f'"{ch}"\n')
    block.append(raw[end])                     # 保留原 END 行
    new_raw = raw[:start] + block + raw[end + 1:]
    with open(ad_path, 'w', encoding='utf-8', errors='replace') as f:
        f.writelines(new_raw)
