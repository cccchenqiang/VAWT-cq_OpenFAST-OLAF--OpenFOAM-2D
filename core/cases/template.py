# -*- coding: utf-8 -*-
"""OpenFAST 输入文件的通用参数更新工具（修改字段并写回）。

优先使用 openfast_toolbox 的 FASTInputFile（已验证对 dvr / AD.dat 读写可靠）；
若库不可用，则回退到轻量文本替换。OLAF.dat 必须走文本替换（含表格段）。
"""
import os
import re

from ..parsers.base import split_kv, read_lines


def _try_openfast_update(path, updates, out_path):
    """用 openfast_toolbox.FASTInputFile 更新并写回。失败返回 False。"""
    try:
        from openfast_toolbox.io import FASTInputFile
    except Exception:
        return False
    try:
        f = FASTInputFile(path)
        for k, v in updates.items():
            f[k] = v
        f.write(out_path)
        return True
    except Exception:
        return False


def _text_update(path, updates, out_path):
    """文本级替换：按行匹配 key，替换其 value 部分，保留 key 与注释。"""
    lines = read_lines(path)
    pending = dict(updates)
    out = []
    for line in lines:
        key, val = split_kv(line)
        if key in pending:
            new_val = pending.pop(key)
            # 保留行首缩进与 key 后的注释（'- ...' 或 '! ...'）
            s = line.rstrip()
            m = re.match(r'^(\s*)\S.*?\s+(' + re.escape(key) + r')(\s+[-!].*)?$', s)
            if m:
                indent, k, tail = m.group(1), m.group(2), m.group(3) or ''
                new_line = f'{indent}{new_val:<12s} {k}{tail}'
                out.append(new_line + '\n')
            else:
                out.append(line)
        else:
            out.append(line)
    if pending:
        raise KeyError(f'文件 {os.path.basename(path)} 中未找到字段: {list(pending)}')
    with open(out_path, 'w', encoding='utf-8', errors='replace') as f:
        f.writelines(out)


def update_fast_file(path, updates, out_path=None):
    """更新 OpenFAST 输入文件中的若干字段。out_path 缺省则覆盖原文件。"""
    dst = out_path or path
    if _try_openfast_update(path, updates, dst):
        return dst
    _text_update(path, updates, dst)
    return dst


def set_olaf_panels(olaf_path, nNW, nNWFree, out_path=None, wr_vtk=0,
                     n_grid_out=0, n_vtk_blades=None, vtk_coord=None,
                     vtk_fps=None):
    """更新 OLAF 尾迹网格和 VTK 输出参数（避开表格段）。"""
    dst = out_path or olaf_path
    lines = read_lines(olaf_path)
    out = []
    for line in lines:
        key, val = split_kv(line)
        if key == 'nNWPanels' and nNW is not None:
            out.append(_rewrite_value(line, key, int(nNW)))
        elif key == 'nNWPanelsFree' and nNWFree is not None:
            out.append(_rewrite_value(line, key, int(nNWFree)))
        elif key == 'WrVTk' and wr_vtk is not None:
            out.append(_rewrite_value(line, key, int(wr_vtk)))
        elif key == 'nGridOut' and n_grid_out is not None:
            out.append(_rewrite_value(line, key, int(n_grid_out)))
        elif key == 'nVTKBlades' and n_vtk_blades is not None:
            out.append(_rewrite_value(line, key, int(n_vtk_blades)))
        elif key == 'VTKCoord' and vtk_coord is not None:
            out.append(_rewrite_value(line, key, int(vtk_coord)))
        elif key == 'VTK_fps' and vtk_fps is not None:
            out.append(_rewrite_value(line, key, vtk_fps))
        else:
            out.append(line)
    with open(dst, 'w', encoding='utf-8', errors='replace') as f:
        f.writelines(out)
    return dst


def _rewrite_value(line, key, new_val):
    s = line.rstrip()
    m = re.match(r'^(\s*)\S.*?\s+(' + re.escape(key) + r')(\s+[-!].*)?$', s)
    if m:
        indent, k, tail = m.group(1), m.group(2), m.group(3) or ''
        return f'{indent}{str(new_val):<12} {k}{tail}\n'
    return line
