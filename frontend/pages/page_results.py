# -*- coding: utf-8 -*-
"""结果处理页：加载结果、统计、可视化（含批量汇总）。"""
import os
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QGroupBox, QTextEdit, QMessageBox,
                               QListWidget, QListWidgetItem, QTableWidget,
                               QTableWidgetItem, QSplitter)

from ..widgets import FilePickerRow, MplCanvas


class ResultsPage(QWidget):
    """读取 AeroDyn/OpenFAST 结果并可视化。"""

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.df = None
        self.result_path = ''
        self.batch_summary = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # ---------------- 左：数据与通道 ----------------
        left = QWidget()
        ll = QVBoxLayout(left)
        g0 = QGroupBox('结果文件')
        g0l = QHBoxLayout(g0)
        self.picker_res = FilePickerRow('结果文件', 'Result files (*.out *.outb)',
                                        r'D:\1worksfiles\py\github\openfast_toolbox-4.2.0\examples_vawt')
        self.btn_load = QPushButton('加载')
        self.btn_load.clicked.connect(self.load_result)
        g0l.addWidget(self.picker_res)
        g0l.addWidget(self.btn_load)
        ll.addWidget(g0)

        self.lbl_info = QLabel('未加载')
        ll.addWidget(self.lbl_info)

        g1 = QGroupBox('通道（勾选用于绘图）')
        gl1 = QVBoxLayout(g1)
        self.list_ch = QListWidget()
        self.list_ch.itemChanged.connect(self._on_ch_checked)
        gl1.addWidget(self.list_ch)
        ll.addWidget(g1, 1)

        row = QHBoxLayout()
        self.btn_stats = QPushButton('统计 (P/Cp/TSR/DEL)')
        self.btn_stats.clicked.connect(self.compute_stats)
        row.addWidget(self.btn_stats)
        ll.addLayout(row)
        self.txt_stats = QTextEdit()
        self.txt_stats.setReadOnly(True)
        self.txt_stats.setMaximumHeight(150)
        ll.addWidget(self.txt_stats)
        splitter.addWidget(left)

        # ---------------- 右：画布 + 绘图按钮 ----------------
        right = QWidget()
        rl = QVBoxLayout(right)
        self.canvas = MplCanvas(width=6.8, height=5.2, dpi=100)
        rl.addWidget(self.canvas, 1)

        g2 = QGroupBox('绘图')
        g2l = QVBoxLayout(g2)
        r1 = QHBoxLayout()
        self.btn_ts = QPushButton('时间序列')
        self.btn_ts.clicked.connect(self.plot_timeseries)
        self.btn_alpha = QPushButton('攻角-方位角')
        self.btn_alpha.clicked.connect(self.plot_alpha)
        self.btn_span = QPushButton('展向 Cl')
        self.btn_span.clicked.connect(self.plot_spanwise)
        self.btn_polar = QPushButton('翼型极线')
        self.btn_polar.clicked.connect(self.plot_polar)
        for b in (self.btn_ts, self.btn_alpha, self.btn_span, self.btn_polar):
            r1.addWidget(b)
        g2l.addLayout(r1)
        r2 = QHBoxLayout()
        self.btn_pc = QPushButton('批量功率曲线')
        self.btn_pc.clicked.connect(self.plot_power_curve)
        r2.addWidget(self.btn_pc)
        r2.addStretch(1)
        g2l.addLayout(r2)
        rl.addWidget(g2)
        splitter.addWidget(right)

        splitter.setSizes([380, 640])
        root.addWidget(splitter, 1)

        # ---------------- 批量汇总表 ----------------
        g3 = QGroupBox('批量结果汇总')
        gl3 = QVBoxLayout(g3)
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(['工况', 'P_mean [W]', 'Cp', 'TSR'])
        gl3.addWidget(self.tbl)
        self.tbl.setMaximumHeight(150)
        root.addWidget(g3)

    # ------------------------------------------------------------------
    def load_result(self):
        path = self.picker_res.path()
        if not path:
            QMessageBox.warning(self, '提示', '请选择结果文件')
            return
        try:
            from core.postprocess import load_fast_output
            self.df = load_fast_output(path)
            self.result_path = path
            self.lbl_info.setText(f'{os.path.basename(path)}: {self.df.shape[0]}×{self.df.shape[1]}')
            self._fill_channels()
            self.canvas.clear()
        except Exception as e:
            QMessageBox.critical(self, '加载失败', str(e))

    def _fill_channels(self):
        self.list_ch.clear()
        for c in self.df.columns:
            item = QListWidgetItem(c)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, c)
            self.list_ch.addItem(item)

    def _on_ch_checked(self, item):
        pass

    def _checked_cols(self):
        return [self.list_ch.item(i).data(Qt.UserRole)
                for i in range(self.list_ch.count())
                if self.list_ch.item(i).checkState() == Qt.Checked]

    # ------------------------------------------------------------------ 统计
    def compute_stats(self):
        if self.df is None:
            QMessageBox.warning(self, '提示', '请先加载结果文件')
            return
        from core.postprocess import steady_stats, calc_cp_tsr, rainflow_equivalent_load
        lines = []
        t = self.model.turbine
        for col in ['RtAeroPwr_[W]'] + self._checked_cols():
            if col in self.df.columns:
                st = steady_stats(self.df, col)
                lines.append(f'{col}: mean={st["mean"]:.3f}, std={st["std"]:.3f}, '
                             f'[{st["min"]:.3f}, {st["max"]:.3f}]')
                if col == 'RtAeroPwr_[W]':
                    cp = calc_cp_tsr(st['mean'], t.hwind_speed, t.rot_speed,
                                     R=0.6, H=6.1)
                    lines.append(f'  → Cp={cp["Cp"]:.4f}, TSR={cp["TSR"]:.3f}, A={cp["A"]:.3f} m²')
                del_ = rainflow_equivalent_load(self.df, col, m=10)
                if del_ and not np.isnan(del_):
                    lines.append(f'  → DEL(m=10) = {del_:.3f}')
        self.txt_stats.setPlainText('\n'.join(lines))

    # ------------------------------------------------------------------ 绘图
    def _check_df(self):
        if self.df is None:
            QMessageBox.warning(self, '提示', '请先加载结果文件')
            return False
        return True

    def plot_timeseries(self):
        if not self._check_df():
            return
        cols = self._checked_cols() or ['RtAeroPwr_[W]']
        cols = [c for c in cols if c in self.df.columns]
        from core.postprocess import plot_timeseries
        self.canvas.plot_result(plot_timeseries, self.df, cols, title='Time series')

    def plot_alpha(self):
        if not self._check_df():
            return
        cols = [c for c in self.df.columns if 'Alpha' in c and 'N009' in c]
        if not cols:
            cols = [c for c in self.df.columns if 'Alpha' in c]
        if not cols or 'Azimuth_[deg]' not in self.df.columns:
            QMessageBox.warning(self, '提示', '未找到攻角/方位角通道')
            return
        from core.postprocess import plot_scatter
        self.canvas.plot_result(plot_scatter, self.df, 'Azimuth_[deg]', cols[0],
                                title='VAWT blade AoA vs azimuth')

    def plot_spanwise(self):
        if not self._check_df():
            return
        from core.postprocess import plot_spanwise_profile
        span = np.linspace(0, 6.1, 18)
        if self.model.blade is not None:
            span = self.model.blade.span
        self.canvas.plot_result(plot_spanwise_profile, self.df, 'Alpha_[deg]', span,
                                title='Blade1 spanwise Alpha')

    def plot_polar(self):
        af = None
        if self.model.blade is not None and self.model.blade.airfoils:
            af = next(iter(self.model.blade.airfoils.values()))
        elif self.model.airfoil is not None:
            af = self.model.airfoil
        if af is None:
            QMessageBox.warning(self, '提示', '未加载翼型极线')
            return
        from core.postprocess import plot_polar_curve
        self.canvas.plot_result(plot_polar_curve, af, None)

    def plot_power_curve(self):
        if self.batch_summary is None or len(self.batch_summary) == 0:
            QMessageBox.warning(self, '提示', '请先在「工况」页执行批量汇总')
            return
        from core.postprocess import plot_power_curve
        self.canvas.plot_result(plot_power_curve, self.batch_summary,
                                x='case', y='P_mean_W')

    # ------------------------------------------------------------------ 批量
    def set_batch_summary(self, summ):
        self.batch_summary = summ
        self.tbl.setRowCount(0)
        for _, r in summ.iterrows():
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)
            for j, key in enumerate(['case', 'P_mean_W', 'Cp', 'TSR']):
                v = r.get(key)
                self.tbl.setItem(i, j, QTableWidgetItem('' if v is None else f'{v:.4g}'))
