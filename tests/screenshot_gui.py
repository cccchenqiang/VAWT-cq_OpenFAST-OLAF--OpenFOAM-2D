# -*- coding: utf-8 -*-
"""生成 GUI 主窗口截图（offscreen 渲染），用于交付展示。"""
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

BASE = r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire'


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from frontend.main_window import MainWindow
    win = MainWindow()
    win.model.load_all({
        'driver': os.path.join(BASE, 'ad_driver.dvr'),
        'ad': os.path.join(BASE, 'AD.dat'),
        'blade': os.path.join(BASE, 'AD_blade.dat'),
        'naca': os.path.join(BASE, 'NACA_0018_Coords.txt'),
        'olaf': os.path.join(BASE, 'OLAF.dat'),
        'polars': os.path.join(BASE, 'Polars.dat'),
    })
    win.tabs.setCurrentIndex(1)          # 几何页
    win.geometry_page.slider.setValue(30)
    win.geometry_page.slider_scale.setValue(6)
    win.geometry_page.refresh()
    win.resize(1200, 800)
    win.show()
    app.processEvents()

    def grab(idx, name):
        win.tabs.setCurrentIndex(idx)
        win.resize(1200, 800)
        win.show()
        app.processEvents()
        win.grab().save(os.path.join(ROOT, 'assets', name))

    grab(0, 'gui_1_input.png')
    grab(1, 'gui_2_geometry.png')
    grab(2, 'gui_3_cases.png')
    grab(3, 'gui_4_results.png')
    print('screenshots saved to assets/')


if __name__ == '__main__':
    main()
