# -*- coding: utf-8 -*-
"""批量工况：按风速/转速扫描（或组合）生成多个单工况并运行、汇总结果。"""
import os
import itertools

from .single import SingleCaseConfig, generate_single_case
from ..runner import run_aerodyn_driver


class BatchConfig:
    """批量工况定义。

    参数：
      U0s  : 风速列表
      RPMs : 转速列表
      combine : True=全组合 (U0×RPM)，False=按位配对（两者长度需一致）
      base : SingleCaseConfig 作为模板（其它参数沿用其默认）
    """

    def __init__(self, U0s=(8.0,), RPMs=(273.0,), combine=False, base=None,
                 TMax=None, DT=None, out_format=None, wr_vtk=None,
                 use_fast_olaf_grid=None, nNW=None, nNWFree=None,
                 olaf_wr_vtk=None, olaf_n_vtk_blades=None,
                 olaf_vtk_coord=None, olaf_vtk_fps=None,
                 olaf_n_grid_out=None):
        self.U0s = [float(u) for u in U0s]
        self.RPMs = [float(r) for r in RPMs]
        self.combine = bool(combine)
        self.base = base
        # 以下参数为 None 时表示「继承单工况 base」的对应值（批量以单工况为模板）
        self.TMax = TMax
        self.DT = DT
        self.out_format = out_format
        self.wr_vtk = wr_vtk
        self.use_fast_olaf_grid = use_fast_olaf_grid
        self.nNW = nNW
        self.nNWFree = nNWFree
        self.olaf_wr_vtk = olaf_wr_vtk
        self.olaf_n_vtk_blades = olaf_n_vtk_blades
        self.olaf_vtk_coord = olaf_vtk_coord
        self.olaf_vtk_fps = olaf_vtk_fps
        self.olaf_n_grid_out = olaf_n_grid_out

    def case_list(self):
        """展开为 SingleCaseConfig 列表（其余参数继承 base 单工况）。"""
        pairs = list(itertools.product(self.U0s, self.RPMs)) if self.combine \
            else list(zip(self.U0s, self.RPMs))
        cases = []
        for i, (u, r) in enumerate(pairs, start=1):
            base = self.base
            outlist = base.outlist if base else None
            outlist_ad = base.outlist_ad if base else None
            cases.append(SingleCaseConfig(
                name=f'U{u:g}_RPM{r:g}', U0=u, RPM=r,
                TMax=(self.TMax if self.TMax is not None
                      else (base.TMax if base else 1.0)),
                DT=(self.DT if self.DT is not None
                    else (base.DT if base else 0.0006)),
                pitch_deg=base.pitch_deg if base else 0.0,
                yaw_deg=base.yaw_deg if base else 0.0,
                out_format=(self.out_format if self.out_format is not None
                            else (base.out_format if base else 1)),
                wr_vtk=(self.wr_vtk if self.wr_vtk is not None
                        else (base.wr_vtk if base else 0)),
                use_fast_olaf_grid=(self.use_fast_olaf_grid
                                    if self.use_fast_olaf_grid is not None
                                    else (base.use_fast_olaf_grid if base else False)),
                nNW=self.nNW if self.nNW is not None else (base.nNW if base else None),
                nNWFree=(self.nNWFree if self.nNWFree is not None
                         else (base.nNWFree if base else None)),
                olaf_wr_vtk=(self.olaf_wr_vtk if self.olaf_wr_vtk is not None
                             else (base.olaf_wr_vtk if base else 0)),
                olaf_n_vtk_blades=(self.olaf_n_vtk_blades
                                   if self.olaf_n_vtk_blades is not None
                                   else (base.olaf_n_vtk_blades if base else 0)),
                olaf_vtk_coord=(self.olaf_vtk_coord if self.olaf_vtk_coord is not None
                                else (base.olaf_vtk_coord if base else 1)),
                olaf_vtk_fps=(self.olaf_vtk_fps if self.olaf_vtk_fps is not None
                              else (base.olaf_vtk_fps if base else 20)),
                olaf_n_grid_out=(self.olaf_n_grid_out
                                 if self.olaf_n_grid_out is not None
                                 else (base.olaf_n_grid_out if base else 0)),
                outlist=outlist, outlist_ad=outlist_ad))
        return cases

    def __len__(self):
        return len(self.case_list())


def generate_batch_cases(model, batch: BatchConfig, work_root):
    """为每个工况生成独立目录，返回 [(case, case_dir), ...]。"""
    dirs = []
    for case in batch.case_list():
        case_dir = os.path.join(work_root, case.name)
        generate_single_case(model, case, case_dir)
        dirs.append((case, case_dir))
    return dirs


def run_batch_cases(model, batch: BatchConfig, work_root, exe,
                    parallel=True, n_cores=None, wait=True):
    """生成并运行批量工况。返回每个工况目录的运行状态。"""
    generated = generate_batch_cases(model, batch, work_root)
    results = []
    for case, case_dir in generated:
        status = run_aerodyn_driver(case_dir, exe, parallel=parallel,
                                    n_cores=n_cores, wait=wait)
        results.append((case, case_dir, status))
    return results
