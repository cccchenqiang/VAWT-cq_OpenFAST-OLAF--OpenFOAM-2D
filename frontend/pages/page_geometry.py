# -*- coding: utf-8 -*-
"""风轮几何可视化页：3D 显示坐标系、叶片翼型、塔筒、转轴，支持方位角旋转。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QSlider, QCheckBox, QGroupBox, QGridLayout, QTextEdit)

from ..widgets import MplCanvas


class GeometryPage(QWidget):
    """根据已加载模型绘制风轮几何。"""

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel('方位角 (deg):'))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 360)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._on_angle)
        top.addWidget(self.slider, 1)
        self.lbl_angle = QLabel('0°')
        top.addWidget(self.lbl_angle)
        lay.addLayout(top)

        opts = QHBoxLayout()
        self.cb_airfoil = QCheckBox('翼型截面')
        self.cb_airfoil.setChecked(True)
        self.cb_axis = QCheckBox('坐标系')
        self.cb_axis.setChecked(True)
        self.cb_rotor = QCheckBox('转轴')
        self.cb_rotor.setChecked(True)
        self.cb_hub = QCheckBox('轮毂')
        self.cb_hub.setChecked(True)
        for c in (self.cb_airfoil, self.cb_axis, self.cb_rotor, self.cb_hub):
            c.toggled.connect(self.refresh)
            opts.addWidget(c)
        opts.addWidget(QLabel('翼型放大:'))
        self.slider_scale = QSlider(Qt.Horizontal)
        self.slider_scale.setRange(1, 20)
        self.slider_scale.setValue(1)
        self.slider_scale.valueChanged.connect(self.refresh)
        opts.addWidget(self.slider_scale)
        self.lbl_scale = QLabel('1x')
        self.slider_scale.valueChanged.connect(lambda v: self.lbl_scale.setText(f'{v}x'))
        opts.addWidget(self.lbl_scale)
        opts.addStretch(1)
        lay.addLayout(opts)

        self.canvas = MplCanvas(width=7.5, height=6.0, dpi=100)
        lay.addWidget(self.canvas, 1)

        g = QGroupBox('几何参数')
        gl = QVBoxLayout(g)
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(110)
        gl.addWidget(self.info)
        lay.addWidget(g)

    def _on_angle(self, v):
        self.lbl_angle.setText(f'{v}°')
        self.refresh()

    def refresh(self):
        """从当前模型重建几何并绘制。"""
        if self.model.turbine is None or self.model.blade is None:
            self.canvas.clear()
            self.info.setPlainText('请先在「输入文件」页加载 Driver 与叶片文件。')
            return
        try:
            from core.geometry import build_geometry
            geom = build_geometry(self.model, rotor_angle_deg=self.slider.value())
            self.canvas.set_geometry(
                geom,
                show_airfoils=self.cb_airfoil.isChecked(),
                show_axes=self.cb_axis.isChecked(),
                show_rotor_axis=self.cb_rotor.isChecked(),
                show_hub=self.cb_hub.isChecked(),
                airfoil_scale=self.slider_scale.value())
            self._show_params(geom)
        except Exception as e:
            self.canvas.clear()
            self.info.setPlainText(f'几何绘制失败: {e}')

    def _show_params(self, geom):
        t = self.model.turbine
        b = self.model.blade
        lines = [
            f'叶片数: {t.num_blades}',
            f'转子转速: {t.rot_speed:.1f} rpm   风速: {t.hwind_speed:.1f} m/s',
            f'叶片展向: 0 ~ {b.span[-1]:.2f} m, 弦长: {b.chord.min():.3f} ~ {b.chord.max():.3f} m',
            f'轮毂位置(全局): ({geom["hub"][0]:.2f}, {geom["hub"][1]:.2f}, {geom["hub"][2]:.2f}) m',
            f'轮毂朝向: {list(t.hub_orientation)}  塔筒: {"有" if t.has_tower else "无"}',
            f'叶片原点: {[f"{o}" for o in t.blade_origins]}',
        ]
        self.info.setPlainText('\n'.join(lines))
