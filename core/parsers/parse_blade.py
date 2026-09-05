# -*- coding: utf-8 -*-
"""解析 AeroDyn 叶片文件 (AD_blade.dat) -> Blade 模型。"""
import os

from .base import split_kv, to_int, is_number_line, numbers, read_lines


def parse_blade_file(path):
    from ..models.blade import Blade
    num_nodes = 0
    table_started = False   # 已越过表头，开始收集数据行
    nodes = []
    for line in read_lines(path):
        key, val = split_kv(line)
        if key == 'NumBlNds':
            v = to_int(val)
            if v is not None:
                num_nodes = v
            continue
        # 表头行：包含列名 BlSpn ...
        if not table_started and line.strip().startswith('BlSpn'):
            table_started = True
            continue
        # 单位行（(m) (m)...）与表头之间的空行
        if table_started and is_number_line(line, min_tokens=10):
            vals = numbers(line)
            if len(vals) >= 10:
                nodes.append(vals[:10])
    blade = Blade(nodes=nodes, num_nodes=num_nodes or len(nodes))
    blade.path = os.path.normpath(path)
    return blade
