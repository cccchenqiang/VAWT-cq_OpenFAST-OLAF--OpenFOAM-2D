# -*- coding: utf-8 -*-
"""自动匹配输入文件功能的测试。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parsers.auto_match import auto_match_files, CATEGORY_ORDER

BASE = r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire'

passed = 0


def check(name, ok, detail=''):
    global passed
    status = '[OK ]' if ok else '[FAIL]'
    print(f'  {status} {name}  {detail}')
    if ok:
        passed += 1


def t_windspire():
    print('== 自动匹配：windspire 案例目录 ==')
    res, un = auto_match_files(BASE)
    expect = {'driver': 'ad_driver.dvr', 'ad': 'AD.dat', 'blade': 'AD_blade.dat',
              'naca': 'NACA_0018_Coords.txt', 'olaf': 'OLAF.dat', 'polars': 'Polars.dat'}
    check('全部 6 类匹配', len(res) == 6, f'got {len(res)}')
    check('无未匹配', not un, f'unmatched={un}')
    ok = all(k in res and os.path.basename(res[k]) == v for k, v in expect.items())
    check('每类命中正确文件', ok,
          f'{ {k: os.path.basename(res[k]) for k in res} }')


def t_empty():
    print('== 自动匹配：空目录 / 无效路径 ==')
    td = tempfile.mkdtemp()
    r, u = auto_match_files(td)
    check('空目录不匹配任何文件', not r)
    check('空目录列出全部未匹配', len(u) == 6, f'unmatched={u}')
    r2, u2 = auto_match_files(r'Z:\no_such_dir')
    check('无效路径安全返回', len(u2) == 6)


def t_mixed():
    print('== 自动匹配：混合文件名（歧义） ==')
    td = tempfile.mkdtemp()
    names = ['ad_driver.dvr', 'AD.dat', 'AD_blade.dat', 'NACA_0018.txt',
             'OLAF.dat', 'Polars.dat', 'extra_notes.txt', 'README.md']
    for f in names:
        open(os.path.join(td, f), 'w').close()
    r, u = auto_match_files(td)
    check('混合目录 6/6', len(r) == 6, f'got {len(r)}')
    check('无未匹配', not u, f'unmatched={u}')
    check('每类唯一', len(set(r.values())) == len(r))


def main():
    print('pytoolbox auto-match 测试')
    print('=' * 60)
    t_windspire()
    t_empty()
    t_mixed()
    print('=' * 60)
    print(f'ALL TESTS PASSED ({passed}/9)' if passed == 9 else f'FAILED ({passed}/9)')
    sys.exit(0 if passed == 9 else 1)


if __name__ == '__main__':
    main()
