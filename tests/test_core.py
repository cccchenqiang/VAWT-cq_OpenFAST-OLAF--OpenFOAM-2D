# -*- coding: utf-8 -*-
"""core 层冒烟测试：解析 6 文件、构建几何、后处理、输出参数表。"""
import os
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# openfast_toolbox 主文件夹源码（与 main.py 入口保持一致）
_OFB = r'D:\1worksfiles\py\github\openfast_toolbox-4.2.0'
if os.path.isdir(_OFB) and _OFB not in sys.path:
    sys.path.insert(0, _OFB)

BASE = r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire'
XLSX = r'D:\BaiduNetdiskDownload\OpenFast\Openfast user manual\OutListParameters.xlsx'

fails = []


def check(name, cond, detail=''):
    status = 'OK ' if cond else 'FAIL'
    print(f'  [{status}] {name} {detail}')
    if not cond:
        fails.append(name)


def t_parsers():
    print('== 1. 解析 6 个输入文件 ==')
    from core.models import VAWTModel
    m = VAWTModel()
    file_map = {
        'driver': os.path.join(BASE, 'ad_driver.dvr'),
        'ad': os.path.join(BASE, 'AD.dat'),
        'blade': os.path.join(BASE, 'AD_blade.dat'),
        'naca': os.path.join(BASE, 'NACA_0018_Coords.txt'),
        'olaf': os.path.join(BASE, 'OLAF.dat'),
        'polars': os.path.join(BASE, 'Polars.dat'),
    }
    m.load_all(file_map)
    check('turbine 解析', m.turbine is not None, m.turbine.summary() if m.turbine else '')
    check('AD 解析', m.ad and m.ad.get('WakeMod') == 3,
          f"WakeMod={m.ad.get('WakeMod')}, OutList={len(m.ad.get('OutList', []))}")
    check('blade 解析', m.blade and m.blade.num_nodes == 18,
          m.blade.summary() if m.blade else '')
    check('naca 解析', m.airfoil and m.airfoil.num_coords > 100,
          m.airfoil.summary() if m.airfoil else '')
    check('olaf 解析', m.olaf and m.olaf.get('nNWPanels'),
          f"nNWPanels={m.olaf.get('nNWPanels')}")
    check('polars 解析', len(m.polar_tables) >= 1,
          f'{len(m.polar_tables)} Re-tables')
    check('叶片-翼型关联', m.blade.airfoils.get(1) is not None)
    return m


def t_geometry(m):
    print('== 2. 几何构建与 3D 绘图 ==')
    import numpy as np
    from core.geometry import build_geometry, plot_geometry_3d
    geom = build_geometry(m, rotor_angle_deg=45)
    check('几何构建', len(geom['blades']) == m.turbine.num_blades,
          f"{len(geom['blades'])} blades, sections/leaf={len(geom['blades'][0]['sections'])}")
    # VAWT 几何方向验证：叶片展向应竖直（沿全局 z），转子平面水平
    d = geom['blades'][0]['centerline'][-1] - geom['blades'][0]['origin']
    horiz = abs(d[2]) / (float(np.linalg.norm(d)) + 1e-12)
    check('叶片竖直', horiz > 0.99, f'展向倾角 cos≈{horiz:.3f}')
    check('转轴竖直', abs(geom['rotor_axis'][2]) > 0.99,
          f"rotor_axis={np.round(geom['rotor_axis'],3)}")
    check('叶片原点半径≈0.61', abs(float(np.linalg.norm(
        geom['blades'][0]['origin'] - geom['hub'])) - 0.61) < 1e-3)
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plot_geometry_3d(geom, show_airfoils=True)
    out = os.path.join(ROOT, 'tests', 'geom_test.png')
    fig.savefig(out, dpi=80)
    check('3D 绘图保存', os.path.isfile(out) and os.path.getsize(out) > 0, out)
    import matplotlib.pyplot as plt
    plt.close(fig)


def t_postprocess(m):
    print('== 3. 后处理（读结果 + 统计 + 绘图） ==')
    from core.postprocess import (load_fast_output, steady_stats, calc_cp_tsr,
                                  plot_timeseries)
    out = os.path.join(BASE, 'ad_driver.out')
    df = load_fast_output(out)
    check('结果读取', df.shape[0] > 100, f'{df.shape[0]}×{df.shape[1]}')
    st = steady_stats(df, 'RtAeroPwr_[W]')
    cp = calc_cp_tsr(st['mean'], 8.0, 273.0, R=0.6, H=6.1)
    check('统计', st['n'] > 0 and cp['Cp'] > 0, f"P={st['mean']:.1f} W, Cp={cp['Cp']:.4f}")
    import matplotlib
    matplotlib.use('Agg')
    fig, _ = plot_timeseries(df, ['RtAeroPwr_[W]'])
    out2 = os.path.join(ROOT, 'tests', 'result_test.png')
    fig.savefig(out2, dpi=80)
    check('结果绘图保存', os.path.isfile(out2))


def t_outlist():
    print('== 4. OutListParameters.xlsx ==')
    from core.outlist import load_aerodyn_channels, search_channels
    df = load_aerodyn_channels(XLSX)
    check('通道表加载', len(df) > 100, f'{len(df)} 通道')
    hit = search_channels(df, 'Alpha')
    check('通道搜索', len(hit) > 0, f'搜索 Alpha: {len(hit)} 条')


def main():
    print('pytoolbox core 冒烟测试')
    print('=' * 60)
    m = t_parsers()
    t_geometry(m)
    t_postprocess(m)
    t_outlist()
    print('=' * 60)
    if fails:
        print(f'FAILED: {fails}')
        sys.exit(1)
    print('ALL TESTS PASSED')


if __name__ == '__main__':
    main()
