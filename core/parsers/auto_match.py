# -*- coding: utf-8 -*-
"""从文件夹自动匹配 AeroDyn Driver + OLAF (VAWT) 的 6 个输入文件。

按文件名关键词打分，逐类贪心分配（每类取最高分、一个文件只分配一次）。
匹配到的返回 {key: 绝对路径}，未匹配到的类别列出，交由用户手动选择。
"""
import os
import re

# 类别匹配顺序（决定文件占用优先级）
CATEGORY_ORDER = ['driver', 'ad', 'blade', 'naca', 'olaf', 'polars']


def _score(category, name):
    """返回文件名 name 对某类别的匹配分数（0 = 不匹配）。"""
    lower = name.lower()
    base, ext = os.path.splitext(lower)
    ext = ext.lower()

    if category == 'driver':
        if ext == '.dvr':
            s = 1
            if 'driver' in base:
                s += 3
            if base == 'ad_driver' or 'ad_driver' in base:
                s += 3          # 最典型的 ad_driver.dvr
            if base.startswith('ad'):
                s += 1
            return s
        return 0

    if category == 'ad':
        if ext in ('.dat', '.dta'):
            if ('blade' in base or 'olaf' in base or 'polar' in base
                    or 'bld' in base or 'coords' in base):
                return 0        # 排除叶片/OLAF/极线/坐标文件
            if base in ('ad', 'aerodyn'):
                return 8        # 精确 AD.dat / AeroDyn.dat
            if re.match(r'^(ad|aerodyn)[._-]', base):
                return 5
            if base.startswith('ad'):
                return 4
            return 0
        return 0

    if category == 'blade':
        if ext == '.dat' and ('blade' in base or 'bld' in base):
            s = 3 if 'blade' in base else 2
            if 'ad_blade' in base or base.startswith('ad'):
                s += 3
            return s
        return 0

    if category == 'naca':
        if ext in ('.txt', '.dat') and ('naca' in base or 'coord' in base
                                        or 'airfoil' in base):
            s = 1
            if 'naca' in base:
                s += 2
            if 'coord' in base:
                s += 2
            if re.search(r'\d{4}', base):      # NACA0018 / 0012 等数字编号
                s += 2
            return s
        return 0

    if category == 'olaf':
        if ext == '.dat' and 'olaf' in base:
            s = 3
            if base == 'olaf':
                s += 3          # 精确 OLAF.dat
            return s
        return 0

    if category == 'polars':
        if ext == '.dat':
            if 'polar' in base:
                s = 3
                if base == 'polars':
                    s += 3      # 精确 Polars.dat
                return s
            if base == 'airfoilinfo' or base.startswith('airfoilinfo'):
                return 6        # AirfoilInfo.dat 同格式
        return 0

    return 0


def auto_match_files(directory):
    """扫描 directory，自动匹配 6 个输入文件。

    返回 (result, unmatched)：
      result   : {key: 绝对路径}，仅含匹配到的类别
      unmatched: 未匹配到的类别名列表
    """
    if not os.path.isdir(directory):
        return {}, list(CATEGORY_ORDER)
    names = [f for f in os.listdir(directory)
             if os.path.isfile(os.path.join(directory, f))]
    result, used, unmatched = {}, set(), []
    for cat in CATEGORY_ORDER:
        best, best_score = None, 0
        for n in names:
            if n in used:
                continue
            s = _score(cat, n)
            if s > best_score:
                best, best_score = n, s
        if best and best_score > 0:
            result[cat] = os.path.join(directory, best)
            used.add(best)
        else:
            unmatched.append(cat)
    return result, unmatched
