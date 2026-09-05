# -*- coding: utf-8 -*-
"""pytoolbox 程序入口。

运行（使用 weis2-env 环境）:
    D:\\ProgramData\\miniforge3\\envs\\weis2-env\\python.exe main.py
"""
import os
import sys

# OpenBLAS 在本机多线程内存分配会失败，强制单线程（须在 import numpy/matplotlib 之前）
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# openfast_toolbox 主文件夹源码（用户指定，editable 未注册到 weis2-env，需手动加入）
_OFB = r'D:\1worksfiles\py\github\openfast_toolbox-4.2.0'
if os.path.isdir(_OFB) and os.path.isdir(os.path.join(_OFB, 'openfast_toolbox')) \
        and _OFB not in sys.path:
    sys.path.insert(0, _OFB)

# ---- 依赖预检：给出生动的运行提示，避免裸 ModuleNotFoundError ----
_NEEDED = ('numpy', 'matplotlib', 'PySide6', 'pandas', 'scipy', 'openpyxl')


def _check_deps():
    missing = []
    for mod in _NEEDED:
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return missing


_missing = _check_deps()
if _missing:
    print('[pytoolbox] 缺少依赖库: ' + ', '.join(_missing))
    print('[pytoolbox] 当前解释器: ' + sys.executable)
    print('[pytoolbox] 本程序需使用 weis2-env 环境，请改用以下方式启动：')
    print('[pytoolbox]   1) 双击 run.bat；或')
    print('[pytoolbox]   2) 命令行: D:\\ProgramData\\miniforge3\\envs\\weis2-env\\python.exe main.py')
    sys.exit(1)

import matplotlib
matplotlib.use('QtAgg')

from PySide6.QtWidgets import QApplication
from frontend.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
