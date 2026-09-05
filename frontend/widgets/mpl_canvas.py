# -*- coding: utf-8 -*-
"""matplotlib 画布控件：用于把 core 层绘制的图嵌入 PySide6 界面。"""
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """通用 matplotlib 画布（2D/3D）。"""

    def __init__(self, width=6.0, height=4.5, dpi=100, parent=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

    def clear(self):
        self.fig.clear()
        self.draw()

    def redraw(self):
        self.fig.tight_layout()
        self.draw()

    def add_axes(self, projection=None):
        """清空并新增子图，返回 ax。"""
        self.fig.clear()
        if projection:
            return self.fig.add_subplot(111, projection=projection)
        return self.fig.add_subplot(111)

    def set_geometry(self, geom, **kwargs):
        """在画布上绘制风轮几何（3D）。"""
        from core.geometry import plot_geometry_3d
        ax = self.add_axes(projection='3d')
        plot_geometry_3d(geom, ax=ax, **kwargs)
        self.draw()

    def plot_result(self, func, *args, **kwargs):
        """用 core.postprocess.plots 的绘图函数绘制。"""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        fig, ax = func(*args, ax=ax, **kwargs)
        self.draw()
        return fig, ax
