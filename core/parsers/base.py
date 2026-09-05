# -*- coding: utf-8 -*-
"""OpenFAST 风格输入文件的轻量解析工具（不依赖外部库，便于各模块独立使用）。"""
import re


def strip_comment(line):
    """去掉注释：支持 '!'（Fortran 风格）与 '#'。保留行尾空白后的内容。"""
    for ch in ('!', '#'):
        idx = line.find(ch)
        if idx >= 0:
            line = line[:idx]
    return line.rstrip()


def split_kv(line):
    """把 'value(s)   Key   - comment' 拆成 (key, value_str)。

    OpenFAST 约定：value 在前、key 是紧跟其后的单词（可含括号如 RotSpeed(1)），
    之后是可选的 '- 注释'。非数据行返回 (None, None)。
    """
    s = strip_comment(line)
    if not s.strip():
        return None, None
    s = s.strip()
    # 无注释形式：value 空格 key
    m = re.match(r'^(.+?)\s+([A-Za-z][A-Za-z0-9_()\.]*)\s*$', s)
    if m:
        return m.group(2), m.group(1).strip()
    # 带 '- 注释' 形式
    m = re.match(r'^(.+?)\s+([A-Za-z][A-Za-z0-9_()\.]*)\s+-\s*(.*)$', s)
    if m:
        return m.group(2), m.group(1).strip()
    return None, None


# ------------------------------------------------------------------ 值类型转换
def to_str(v):
    return str(v).strip().strip('"').strip("'")


def to_float(v):
    s = to_str(v)
    try:
        return float(s)
    except ValueError:
        return None


def to_int(v):
    f = to_float(v)
    return None if f is None else int(f)


def to_bool(v):
    s = to_str(v).lower()
    return s in ('true', 't', 'yes', '1')


def to_list(v, n=None):
    """把逗号分隔/空格分隔的数值串转成 float 列表。"""
    s = to_str(v)
    parts = [p for p in re.split(r'[,\s]+', s) if p != '']
    vals = []
    for p in parts:
        try:
            vals.append(float(p))
        except ValueError:
            pass
    if n is not None:
        vals = vals[:n]
        while len(vals) < n:
            vals.append(0.0)
    return vals


def is_number_line(line, min_tokens=1):
    """判断一行是否全为数字（用于识别数据表行）。"""
    parts = [p for p in re.split(r'[\s,]+', strip_comment(line).strip()) if p]
    if len(parts) < min_tokens:
        return False
    for p in parts:
        try:
            float(p)
        except ValueError:
            return False
    return True


def numbers(line):
    """提取一行中的全部数值。"""
    parts = [p for p in re.split(r'[\s,]+', strip_comment(line).strip()) if p]
    out = []
    for p in parts:
        try:
            out.append(float(p))
        except ValueError:
            continue
    return out


def read_lines(path, encoding='utf-8', errors='replace'):
    with open(path, 'r', encoding=encoding, errors=errors) as f:
        return f.readlines()
