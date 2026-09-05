# -*- coding: utf-8 -*-
"""输入文件页：选择 6 个输入文件并加载解析。"""
import os
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QGroupBox, QLabel, QTextEdit, QFileDialog,
                               QMessageBox, QGridLayout, QLineEdit)

from ..widgets import FilePickerRow

# 默认演示模型（用户已有案例），可在界面中修改
DEFAULT_MODEL_DIR = r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire'


class InputPage(QWidget):
    """6 个输入文件 + 输出参数表（OutListParameters.xlsx）加载页。"""

    files_loaded = Signal()      # 模型加载完成
    outlist_loaded = Signal()    # 输出参数表加载完成

    FILE_ORDER = ['driver', 'ad', 'blade', 'naca', 'olaf', 'polars']

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.outlist_df = None
        self.outlist_path = ''
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        g = QGroupBox('1) 选择 6 个输入文件')
        gl = QVBoxLayout(g)
        row_dir = QHBoxLayout()
        self.btn_autodir = QPushButton('选择文件夹并自动匹配 6 个输入文件…')
        self.btn_autodir.clicked.connect(self.auto_match_dir)
        self.lbl_dir = QLabel('（未选择文件夹）')
        self.lbl_dir.setStyleSheet('color: #666;')
        row_dir.addWidget(self.btn_autodir)
        row_dir.addWidget(self.lbl_dir, 1)
        gl.addLayout(row_dir)
        self.pickers = {
            'driver': FilePickerRow('Driver 主输入', 'Driver files (*.dvr);;All (*)',
                                    DEFAULT_MODEL_DIR),
            'ad': FilePickerRow('AeroDyn 主输入', 'AeroDyn files (AD*.dat);;All (*)',
                                DEFAULT_MODEL_DIR),
            'blade': FilePickerRow('叶片文件', 'Blade files (*blade*.dat);;All (*)',
                                   DEFAULT_MODEL_DIR),
            'naca': FilePickerRow('翼型坐标', 'Airfoil coords (*.txt);;All (*)',
                                  DEFAULT_MODEL_DIR),
            'olaf': FilePickerRow('OLAF 控制', 'OLAF files (OLAF*.dat);;All (*)',
                                  DEFAULT_MODEL_DIR),
            'polars': FilePickerRow('翼型极线', 'Polar files (Polars*.dat);;All (*)',
                                    DEFAULT_MODEL_DIR),
        }
        for p in self.pickers.values():
            gl.addWidget(p)
        row = QHBoxLayout()
        self.btn_load = QPushButton('加载全部文件')
        self.btn_load.clicked.connect(self.load_all)
        self.btn_fill = QPushButton('填充默认模型')
        self.btn_fill.clicked.connect(self.fill_defaults)
        row.addWidget(self.btn_fill)
        row.addWidget(self.btn_load)
        row.addStretch(1)
        gl.addLayout(row)
        lay.addWidget(g)

        g2 = QGroupBox('2) 输出参数表（OutListParameters.xlsx，可选）')
        gl2 = QHBoxLayout(g2)
        self.picker_xlsx = FilePickerRow('输出参数表', 'Excel (*.xlsx)',
                                         r'D:\BaiduNetdiskDownload\OpenFast\Openfast user manual')
        self.btn_xlsx = QPushButton('加载参数表')
        self.btn_xlsx.clicked.connect(self.load_outlist_xlsx)
        gl2.addWidget(self.picker_xlsx)
        gl2.addWidget(self.btn_xlsx)
        lay.addWidget(g2)

        g3 = QGroupBox('3) OLAF 涡模型参数设置（自动带入转速 / 风速 / 半径 / 方位角步长）')
        gl3 = QVBoxLayout(g3)
        og = QGridLayout()
        og.setHorizontalSpacing(6)
        og.setVerticalSpacing(4)

        def _mk(value=''):
            le = QLineEdit(value)
            le.setFixedWidth(84)
            return le

        og.addWidget(QLabel('转速 [rpm]'), 0, 0)
        self.ol_rpm = _mk()
        og.addWidget(self.ol_rpm, 0, 1)
        og.addWidget(QLabel('风速 U0 [m/s]'), 0, 2)
        self.ol_u0 = _mk()
        og.addWidget(self.ol_u0, 0, 3)
        og.addWidget(QLabel('半径 R [m]'), 0, 4)
        self.ol_r = _mk()
        og.addWidget(self.ol_r, 0, 5)
        og.addWidget(QLabel('方位角步长 Δψ [deg]'), 0, 6)
        self.ol_dpsi = _mk('6')
        og.addWidget(self.ol_dpsi, 0, 7)

        og.addWidget(QLabel('nPerRot'), 1, 0)
        self.ol_nperrot = _mk('')
        og.addWidget(self.ol_nperrot, 1, 1)
        og.addWidget(QLabel('a'), 1, 2)
        self.ol_a = _mk('0.3')
        og.addWidget(self.ol_a, 1, 3)
        og.addWidget(QLabel('aScale'), 1, 4)
        self.ol_ascale = _mk('1.2')
        og.addWidget(self.ol_ascale, 1, 5)
        og.addWidget(QLabel('尾迹长度 [D]'), 1, 6)
        self.ol_wakeD = _mk('4')
        og.addWidget(self.ol_wakeD, 1, 7)

        og.addWidget(QLabel('nNWrot'), 2, 0)
        self.ol_nnw = _mk('8')
        og.addWidget(self.ol_nnw, 2, 1)
        og.addWidget(QLabel('nNWrotFree'), 2, 2)
        self.ol_nnwfree = _mk('1')
        og.addWidget(self.ol_nnwfree, 2, 3)
        og.addWidget(QLabel('nFWrot'), 2, 4)
        self.ol_nfw = _mk('0')
        og.addWidget(self.ol_nfw, 2, 5)
        og.addWidget(QLabel('nFWrotFree'), 2, 6)
        self.ol_nfwfree = _mk('0')
        og.addWidget(self.ol_nfwfree, 2, 7)
        gl3.addLayout(og)

        row_ol = QHBoxLayout()
        self.btn_ol_fill = QPushButton('按模型自动带入')
        self.btn_ol_fill.clicked.connect(self.fill_olaf_from_model)
        self.btn_ol_calc = QPushButton('计算 OLAF 推荐参数')
        self.btn_ol_calc.clicked.connect(self.calc_olaf)
        self.btn_ol_write = QPushButton('写入 OLAF.dat')
        self.btn_ol_write.clicked.connect(self.write_olaf)
        row_ol.addWidget(self.btn_ol_fill)
        row_ol.addWidget(self.btn_ol_calc)
        row_ol.addWidget(self.btn_ol_write)
        row_ol.addStretch(1)
        gl3.addLayout(row_ol)
        self.ol_result = QTextEdit()
        self.ol_result.setReadOnly(True)
        self.ol_result.setMinimumHeight(110)
        gl3.addWidget(self.ol_result)
        lay.addWidget(g3)

        g4 = QGroupBox('4) 解析摘要')
        gl4 = QVBoxLayout(g4)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(150)
        gl4.addWidget(self.summary)
        lay.addWidget(g4, 1)

        # 默认填充一次，方便直接演示
        self.fill_defaults()

    # -------------------------------------------------------------
    def auto_match_dir(self):
        """选择文件夹，自动匹配 6 个输入文件；匹配后仍可手动调整。"""
        start = (os.path.dirname(self.pickers['driver'].path())
                 or DEFAULT_MODEL_DIR)
        d = QFileDialog.getExistingDirectory(self, '选择输入文件所在文件夹', start)
        if not d:
            return
        result, unmatched = self.apply_auto_match(d)
        if not result:
            QMessageBox.information(self, '自动匹配',
                                    '未在所选文件夹中识别到 AeroDyn/OLAF 输入文件，请手动选择。')
            return
        lines = [f'  {k}: {os.path.basename(result[k])}'
                 for k in self.FILE_ORDER if k in result]
        msg = f'已自动匹配 {len(result)}/6 个输入文件：\n' + '\n'.join(lines)
        if unmatched:
            msg += ('\n\n以下未匹配到，请手动选择：\n'
                    + '\n'.join(f'  {k}' for k in unmatched))
        QMessageBox.information(self, '自动匹配完成', msg)

    def apply_auto_match(self, directory):
        """自动匹配并填入 pickers（无对话框，供测试/复用）。返回 (result, unmatched)。"""
        from core.parsers.auto_match import auto_match_files
        result, unmatched = auto_match_files(directory)
        for k, path in result.items():
            self.pickers[k].set_path(path)
        if result:
            self.lbl_dir.setText(directory)
        return result, unmatched

    def fill_defaults(self):
        base = DEFAULT_MODEL_DIR
        defaults = {
            'driver': os.path.join(base, 'ad_driver.dvr'),
            'ad': os.path.join(base, 'AD.dat'),
            'blade': os.path.join(base, 'AD_blade.dat'),
            'naca': os.path.join(base, 'NACA_0018_Coords.txt'),
            'olaf': os.path.join(base, 'OLAF.dat'),
            'polars': os.path.join(base, 'Polars.dat'),
        }
        for k, p in defaults.items():
            if os.path.isfile(p):
                self.pickers[k].set_path(p)
        self.picker_xlsx.set_path(
            r'D:\BaiduNetdiskDownload\OpenFast\Openfast user manual\OutListParameters.xlsx')

    def load_all(self):
        """收集 6 个文件路径并解析。"""
        file_map = {k: self.pickers[k].path() for k in self.FILE_ORDER}
        missing = [k for k, p in file_map.items() if not p]
        if missing:
            QMessageBox.warning(self, '缺少文件',
                                '请选择以下文件：\n' + '\n'.join(missing))
            return
        try:
            msgs = self.model.load_all(file_map)
            self._show_summary()
            self.fill_olaf_from_model()
            self.files_loaded.emit()
        except Exception as e:
            QMessageBox.critical(self, '加载失败', str(e))

    # -------------------------------------------------------------
    # OLAF 涡模型参数设置
    # -------------------------------------------------------------
    def _le_f(self, le, default=None):
        """QLineEdit → float（空/非法返回 default）。"""
        try:
            return float(le.text())
        except (TypeError, ValueError):
            return default

    def _le_i(self, le, default=None):
        try:
            return int(float(le.text()))
        except (TypeError, ValueError):
            return default

    def fill_olaf_from_model(self):
        """自动带入当前模拟文件的转速 / 风速 / 半径，并尽量反推方位角步长。"""
        t = self.model.turbine
        if t is None:
            QMessageBox.warning(self, '提示', '尚未加载模型，请先加载 6 个输入文件。')
            return
        self.ol_rpm.setText(f'{t.rot_speed:g}')
        self.ol_u0.setText(f'{t.hwind_speed:g}')
        R = t.rotor_radius()
        self.ol_r.setText(f'{R:.4g}')
        # 若 OLAF.dat 中能读出 DTfvw（非 default），由转速反推方位角步长
        from core.olaf_params import delta_psi_from_dt
        dt_fvw = self.model.olaf.get('DTfvw') if self.model.olaf else None
        if dt_fvw is not None:
            self.ol_dpsi.setText(f'{delta_psi_from_dt(t.rot_speed, float(dt_fvw)):.3g}')
        self.ol_result.setPlainText(
            f'已自动带入：转速 {t.rot_speed:g} rpm，U0 {t.hwind_speed:g} m/s，'
            f'R {R:.4g} m。\n点击“计算 OLAF 推荐参数”查看推荐的时间步与尾迹网格。')

    def _olaf_inputs(self):
        """读取设置区参数，返回 (kwargs, err)。"""
        omega_rpm = self._le_f(self.ol_rpm)
        U0 = self._le_f(self.ol_u0)
        R = self._le_f(self.ol_r)
        dpsi = self._le_f(self.ol_dpsi)
        nperrot = self._le_i(self.ol_nperrot)
        if omega_rpm is None or U0 is None or R is None or dpsi is None:
            return None, '请填写转速 / 风速 / 半径 / 方位角步长（数值）。'
        kwargs = dict(
            omega_rpm=omega_rpm, U0=U0, R=R, deltaPsiDeg=dpsi,
            nPerRot=nperrot,
            a=self._le_f(self.ol_a, 0.3),
            aScale=self._le_f(self.ol_ascale, 1.2),
            targetWakeLengthD=self._le_f(self.ol_wakeD, 4),
            nNWrot=self._le_i(self.ol_nnw, 8),
            nNWrotFree=self._le_i(self.ol_nnwfree, 1),
            nFWrot=self._le_i(self.ol_nfw, 0),
            nFWrotFree=self._le_i(self.ol_nfwfree, 0),
        )
        return kwargs, None

    def calc_olaf(self):
        """按附件 OLAFParams 逻辑计算 OLAF 推荐参数。"""
        from core.olaf_params import olaf_params
        kwargs, err = self._olaf_inputs()
        if err:
            QMessageBox.warning(self, '提示', err)
            return
        res = olaf_params(**kwargs)
        if res is None:
            QMessageBox.warning(self, '提示', '无法计算：请检查转速 >0、半径 >0、风速合理。')
            return
        Uc = kwargs['U0'] * (1 - kwargs['aScale'] * kwargs['a'])
        lines = [
            f'转速 ω = {kwargs["omega_rpm"]:g} rpm，U0 = {kwargs["U0"]:g} m/s，'
            f'R = {kwargs["R"]:g} m',
            f'方位角步长 Δψ = {kwargs["deltaPsiDeg"]:g} deg  →  每转 nPerRot = '
            f'{res["nPerRot"]} 步',
            f'OLAF 时间步 dt_fvw = {res["dt_fvw"]:.5f} s'
            f'（尾迹对流速度 Uc = {Uc:.2f} m/s）',
            '',
            '尾迹网格：',
            f'  nNWPanels     = {res["nNWPanels"]:d}',
            f'  nNWPanelsFree = {res["nNWPanelsFree"]:d}',
            f'  nFWPanels     = {res["nFWPanels"]:d}',
            f'  nFWPanelsFree = {res["nFWPanelsFree"]:d}',
            f'最小瞬态时间 tMin = {res["tMin"]:.2f} s'
            f'（约 {res["transient_rot"]:.1f} 转，建议 TMax 不小于该值）',
        ]
        self.ol_result.setPlainText('\n'.join(lines))

    def write_olaf(self):
        """把计算得到的 nNWPanels / nNWPanelsFree 写入当前 OLAF.dat。"""
        if not (self.model.olaf and self.model.olaf.get('path')):
            QMessageBox.warning(self, '提示', '尚未加载 OLAF.dat。')
            return
        from core.cases.template import set_olaf_panels
        from core.olaf_params import olaf_params
        kwargs, err = self._olaf_inputs()
        if err:
            QMessageBox.warning(self, '提示', err)
            return
        res = olaf_params(**kwargs)
        if res is None:
            QMessageBox.warning(self, '提示', '无法计算推荐参数，未写入。')
            return
        try:
            set_olaf_panels(self.model.olaf['path'],
                            nNW=res['nNWPanels'],
                            nNWFree=res['nNWPanelsFree'],
                            wr_vtk=0)
            self.ol_result.append(
                f'\n[已写入] OLAF.dat: nNWPanels={res["nNWPanels"]}, '
                f'nNWPanelsFree={res["nNWPanelsFree"]}, WrVTk=0')
        except Exception as e:
            QMessageBox.critical(self, '写入失败', str(e))

    def _show_summary(self):
        txt = []
        for k in self.FILE_ORDER:
            if self.model.paths.get(k):
                txt.append(f'[✓] {self.model.summary_of(k)}')
        if self.model.executable:
            txt.append(f'[可执行] {self.model.executable}')
        self.summary.setPlainText('\n'.join(txt))

    def load_outlist_xlsx(self):
        path = self.picker_xlsx.path()
        if not path:
            QMessageBox.warning(self, '提示', '请先选择 OutListParameters.xlsx')
            return
        try:
            from core.outlist import load_aerodyn_channels
            self.outlist_df = load_aerodyn_channels(path)
            self.outlist_path = path
            self._show_summary()
            self.outlist_loaded.emit()
        except Exception as e:
            QMessageBox.critical(self, '加载失败', str(e))
