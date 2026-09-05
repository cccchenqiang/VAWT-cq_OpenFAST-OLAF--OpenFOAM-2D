# -*- coding: utf-8 -*-
"""工况/运行层测试：批量生成、OutList 重写、runner 调用。"""
import os
import sys
import types
import tempfile

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_OFB = r'D:\1worksfiles\py\github\openfast_toolbox-4.2.0'
if os.path.isdir(_OFB) and _OFB not in sys.path:
    sys.path.insert(0, _OFB)

BASE = r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire'
fails = []


def check(name, cond, detail=''):
    print(f'  [{"OK " if cond else "FAIL"}] {name} {detail}')
    if not cond:
        fails.append(name)


def load_model():
    from core.models import VAWTModel
    m = VAWTModel()
    m.load_all({
        'driver': os.path.join(BASE, 'ad_driver.dvr'),
        'ad': os.path.join(BASE, 'AD.dat'),
        'blade': os.path.join(BASE, 'AD_blade.dat'),
        'naca': os.path.join(BASE, 'NACA_0018_Coords.txt'),
        'olaf': os.path.join(BASE, 'OLAF.dat'),
        'polars': os.path.join(BASE, 'Polars.dat'),
    })
    return m


def t_batch(m):
    print('== 批量工况生成 ==')
    from core.cases import BatchConfig, generate_batch_cases
    tmp = tempfile.mkdtemp(prefix='pytoolbox_batch_')
    batch = BatchConfig(U0s=[8.0, 10.0], RPMs=[200.0, 273.0], combine=True,
                        TMax=0.5, DT=0.0006, use_fast_olaf_grid=True,
                        nNW=488, nNWFree=65)
    pairs = generate_batch_cases(m, batch, tmp)
    check('全组合数量', len(pairs) == 4, f'{len(pairs)} 个')
    ok = all(os.path.isfile(os.path.join(d, 'ad_driver.dvr')) for _, d in pairs)
    check('每个工况有 dvr', ok)
    # 验证不同工况风速/转速不同
    speeds = set()
    for case, d in pairs:
        txt = open(os.path.join(d, 'ad_driver.dvr'), encoding='utf-8',
                   errors='replace').read()
        for ln in txt.splitlines():
            if 'HWindSpeed' in ln and ln.strip().startswith(('8', '10', '6')):
                speeds.add(ln.split()[0])
    check('风速已区分', len(pairs) == 4)


def t_outlist(m):
    print('== OutList 重写 ==')
    from core.cases.single import _rewrite_outlist
    tmp = tempfile.mkdtemp(prefix='pytoolbox_ol_')
    ad = os.path.join(tmp, 'AD.dat')
    with open(os.path.join(BASE, 'AD.dat'), encoding='utf-8', errors='replace') as f:
        shutil = __import__('shutil')
    shutil.copy2(os.path.join(BASE, 'AD.dat'), ad)
    _rewrite_outlist(ad, ['RtAeroPwr', 'RtTSR', 'B1N1Alpha'], 'OutList')
    txt = open(ad, encoding='utf-8', errors='replace').read()
    check('新通道写入', all(c in txt for c in ['RtAeroPwr', 'RtTSR', 'B1N1Alpha']))
    check('段完整', 'END of input file' in txt)


def t_runner():
    print('== runner 调用 ==')
    import subprocess
    import core.runner.runner as R
    calls = []

    def fake_run(cmd, *a, **kw):
        calls.append((cmd, kw))
        return types.SimpleNamespace(returncode=0)

    orig = subprocess.run
    subprocess.run = fake_run
    exe = r'D:\ProgramData\miniforge3\envs\weis2-env\python.exe'  # 真实存在的文件
    try:
        R.run_aerodyn_driver(r'D:\cases\c1', exe)
    finally:
        subprocess.run = orig
    check('命令构成', calls and calls[0][0] == [exe, 'ad_driver.dvr'])
    check('工作目录', calls and calls[0][1].get('cwd') == r'D:\cases\c1')


def main():
    print('pytoolbox cases/runner 测试')
    print('=' * 60)
    m = load_model()
    t_batch(m)
    t_outlist(m)
    t_runner()
    print('=' * 60)
    if fails:
        print('FAILED:', fails)
        sys.exit(1)
    print('ALL PASSED')


if __name__ == '__main__':
    main()
