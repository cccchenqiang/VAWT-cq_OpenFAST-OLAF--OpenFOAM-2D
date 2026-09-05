# -*- coding: utf-8 -*-
"""GUI 冒烟测试：offscreen 启动、加载模型、刷新几何页。"""
import os
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_OFB = r'D:\1worksfiles\py\github\openfast_toolbox-4.2.0'
if os.path.isdir(_OFB) and _OFB not in sys.path:
    sys.path.insert(0, _OFB)

import matplotlib
matplotlib.use('QtAgg')

BASE = r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire'

fails = []


def check(name, cond, detail=''):
    print(f'  [{"OK " if cond else "FAIL"}] {name} {detail}')
    if not cond:
        fails.append(name)


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from frontend.main_window import MainWindow
    win = MainWindow()
    check('主窗口创建', win is not None)
    check('4 个标签页', win.tabs.count() == 4,
          [win.tabs.tabText(i) for i in range(win.tabs.count())])

    # 加载模型
    m = win.model
    m.load_all({
        'driver': os.path.join(BASE, 'ad_driver.dvr'),
        'ad': os.path.join(BASE, 'AD.dat'),
        'blade': os.path.join(BASE, 'AD_blade.dat'),
        'naca': os.path.join(BASE, 'NACA_0018_Coords.txt'),
        'olaf': os.path.join(BASE, 'OLAF.dat'),
        'polars': os.path.join(BASE, 'Polars.dat'),
    })
    check('模型加载', m.turbine is not None)

    # 几何页
    win.geometry_page.refresh()
    axes = win.geometry_page.canvas.fig.axes
    info = win.geometry_page.info.toPlainText()
    check('几何页绘制', len(axes) > 0, f'axes={len(axes)} info={info[:80]}')
    win.geometry_page.slider.setValue(120)
    win.geometry_page.refresh()
    check('方位角旋转', win.geometry_page.lbl_angle.text() == '120°')

    # 工况页：加载 OutList 表并生成单工况到临时目录
    import tempfile
    from core.cases import SingleCaseConfig, generate_single_case
    tmp = tempfile.mkdtemp(prefix='pytoolbox_gui_')
    case = SingleCaseConfig(name='case1', U0=8.0, RPM=273.0, TMax=0.5, DT=0.0006,
                            use_fast_olaf_grid=True, nNW=488, nNWFree=65)
    generate_single_case(m, case, tmp)
    dvr_out = os.path.join(tmp, 'ad_driver.dvr')
    check('单工况生成', os.path.isfile(dvr_out), dvr_out)
    # 验证生成文件里风速与 TMax 已改写
    txt = open(dvr_out, encoding='utf-8', errors='replace').read()
    check('工况参数改写', '8.0' in txt and '0.5' in txt)
    # 验证 OLAF 面板数文本级改写
    olaf_out = os.path.join(tmp, 'case1', 'OLAF.dat')
    if os.path.isfile(olaf_out):
        o = open(olaf_out, encoding='utf-8', errors='replace').read()
        check('OLAF 面板改写', '488' in o)

    # 结果页：加载参考结果
    win.results_page.picker_res.set_path(os.path.join(BASE, 'ad_driver.out'))
    win.results_page.load_result()
    check('结果加载', win.results_page.df is not None and
          'RtAeroPwr_[W]' in win.results_page.df.columns)
    win.results_page.compute_stats()
    check('统计输出', 'mean' in win.results_page.txt_stats.toPlainText())

    print('=' * 60)
    if fails:
        print('GUI TEST FAILED:', fails)
        sys.exit(1)
    print('GUI TEST PASSED')


if __name__ == '__main__':
    main()
