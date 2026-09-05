# -*- coding: utf-8 -*-
"""工况设置页：单工况 / 批量工况的生成与运行。"""
import os
import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QGroupBox, QCheckBox,
                               QComboBox, QTextEdit, QFileDialog, QMessageBox,
                               QGridLayout)

from ..widgets import FilePickerRow
from ..widgets.outlist_dialog import OutListEditorDialog

DEFAULT_EXE = (r'D:\1worksfiles\github\OPENFAST\testlearn'
               r'\ad_VerticalAxis_OLAF_windspire\AeroDyn_Driver_x64.exe')


def _f(s, default=0.0):
    try:
        return float(str(s).strip())
    except Exception:
        return default


def _nums(s):
    return [x for x in re.split(r'[,\s]+', str(s).strip()) if x]


class _GridHelper:
    """在 QGroupBox 内用 QGridLayout 快速排列「标签+输入」对。"""

    def __init__(self, group, cols=4):
        self.layout = QGridLayout(group)
        self.row = 0
        self.col = 0
        self.cols = cols

    def _advance(self):
        self.col += 2
        if self.col >= self.cols * 2:
            self.col = 0
            self.row += 1

    def add(self, label, default=''):
        le = QLineEdit(str(default))
        self.layout.addWidget(QLabel(label), self.row, self.col)
        self.layout.addWidget(le, self.row, self.col + 1)
        self._advance()
        return le

    def add_widget(self, label, w):
        self.layout.addWidget(QLabel(label), self.row, self.col)
        self.layout.addWidget(w, self.row, self.col + 1)
        self._advance()

    def add_layout_row(self, hlay):
        self.layout.addLayout(hlay, self.row, 0, 1, self.cols * 2)
        self.row += 1


class CasesPage(QWidget):
    """单工况与批量工况配置、生成、运行。"""

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        lay = QVBoxLayout(self)

        # 执行文件
        g0 = QGroupBox('可执行程序（AeroDyn Driver / OpenFAST）')
        g0l = QHBoxLayout(g0)
        self.picker_exe = FilePickerRow(
            '可执行文件', 'Executables (*.exe)',
            r'D:\1worksfiles\github\OPENFAST\testlearn\ad_VerticalAxis_OLAF_windspire')
        self.picker_exe.edit.setPlaceholderText('如 AeroDyn_Driver_x64.exe / openfast.exe')
        if os.path.isfile(DEFAULT_EXE):
            self.picker_exe.set_path(DEFAULT_EXE)
        g0l.addWidget(self.picker_exe)
        lay.addWidget(g0)

        # ---------------- 单工况设置（批量以此为模板） ----------------
        g1 = QGroupBox('单工况设置（批量工况以此为模板）')
        grid = _GridHelper(g1, 4)
        self.in_U0 = grid.add('风速 U0 [m/s]', '8')
        self.in_RPM = grid.add('转速 [rpm]', '273')
        self.in_TMax = grid.add('TMax [s]', '1.0')
        self.in_DT = grid.add('DT [s]', '0.0006')
        self.in_pitch = grid.add('桨距 [deg]', '0')
        self.in_yaw = grid.add('偏航 [deg]', '0')
        self.cb_outfmt = QComboBox()
        self.cb_outfmt.addItems(['1 - text (.out)', '2 - binary (.outb)', '3 - both'])
        self.cb_vtk = QComboBox()
        self.cb_vtk.addItems(['0 - 关闭 VTK（快）', '1 - init', '2 - animation'])
        grid.add_widget('输出格式', self.cb_outfmt)
        grid.add_widget('VTK 输出', self.cb_vtk)
        self.cb_olaf_vtk = QComboBox()
        self.cb_olaf_vtk.addItems(['0 - 关闭尾迹 VTK', '1 - 按帧率输出', '2 - 初始/最终输出'])
        grid.add_widget('尾迹 VTK (OLAF)', self.cb_olaf_vtk)
        self.in_nvtk_blades = grid.add('VTK 叶片数', '0')
        self.in_vtk_fps = grid.add('VTK 帧率', '20')
        self.cb_vtk_coord = QComboBox()
        self.cb_vtk_coord.addItems(['1 - Global', '2 - Hub', '3 - Both'])
        grid.add_widget('VTK 坐标系', self.cb_vtk_coord)
        self.in_grid_out = grid.add('尾迹网格输出数', '0')
        self.cb_olaf_vtk.currentIndexChanged.connect(self._sync_olaf_vtk_controls)
        self._sync_olaf_vtk_controls()

        row_gen = QHBoxLayout()
        self.btn_gen1 = QPushButton('生成单工况目录')
        self.btn_gen1.setMinimumHeight(34)
        self.btn_gen1.clicked.connect(self.gen_single)
        row_gen.addWidget(self.btn_gen1)
        row_gen.addStretch(1)
        grid.add_layout_row(row_gen)
        lay.addWidget(g1)

        # ---------------- 输出通道（来自 AD.dat 的 OutList / OutListAD） ----------------
        g3 = QGroupBox('输出通道（来自 AD.dat 的 OutList，xlsx 仅作参考）')
        gl3 = QVBoxLayout(g3)
        row_ol = QHBoxLayout()
        self.lbl_out_src = QLabel('当前 OutList 通道：')
        self.btn_outlist = QPushButton('选择/编辑输出通道…')
        self.btn_outlist.clicked.connect(self.choose_outlist)
        row_ol.addWidget(self.lbl_out_src)
        row_ol.addWidget(self.btn_outlist)
        row_ol.addStretch(1)
        gl3.addLayout(row_ol)
        # 输出通道用 QGridLayout + QLabel 固定 3 列显示，文本完整不省略
        self.out_container = QWidget()
        self.out_grid = QGridLayout(self.out_container)
        self.out_grid.setSpacing(6)
        gl3.addWidget(self.out_container)
        self.lbl_out_hint = QLabel(
            '提示：节点级输出 OutListAD（如 Vindx / Alpha / Cl）也在上方对话框中一并编辑，'
            '生成工况时两个段都会写入 AD.dat。')
        self.lbl_out_hint.setStyleSheet('color: #666;')
        gl3.addWidget(self.lbl_out_hint)
        lay.addWidget(g3)

        # ---------------- 批量工况设置（位于输出通道之后） ----------------
        g2 = QGroupBox('批量工况设置（仅扫描风速×转速，其余继承上方单工况）')
        gl2 = QVBoxLayout(g2)
        row_f = QHBoxLayout()
        row_f.addWidget(QLabel('风速列表 [m/s]:'))
        self.in_U0s = QLineEdit('6,8,10')
        row_f.addWidget(self.in_U0s, 1)
        row_f.addWidget(QLabel('转速列表 [rpm]:'))
        self.in_RPMs = QLineEdit('200,273,340')
        row_f.addWidget(self.in_RPMs, 1)
        self.cb_combine = QCheckBox('全组合 (风速×转速)')
        row_f.addWidget(self.cb_combine)
        row_f.addStretch(1)
        gl2.addLayout(row_f)

        row2 = QHBoxLayout()
        self.btn_genB = QPushButton('生成批量工况')
        self.btn_genB.clicked.connect(self.gen_batch)
        self.btn_run = QPushButton('运行所有已生成工况')
        self.btn_run.clicked.connect(self.run_all)
        self.btn_sum = QPushButton('汇总批量结果')
        self.btn_sum.clicked.connect(self.summarize_batch)
        row2.addWidget(self.btn_genB)
        row2.addWidget(self.btn_run)
        row2.addWidget(self.btn_sum)
        row2.addStretch(1)
        gl2.addLayout(row2)
        lay.addWidget(g2)

        # 日志
        g4 = QGroupBox('运行日志')
        gl4 = QVBoxLayout(g4)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        gl4.addWidget(self.log)
        lay.addWidget(g4)

    def sync_from_model(self):
        """模型加载后，把 Driver 的实际参数同步到单工况输入框，并刷新 OutList。"""
        t = self.model.turbine
        if t is not None:
            try:
                self.in_U0.setText(f'{t.hwind_speed:g}')
                self.in_RPM.setText(f'{t.rot_speed:g}')
                if getattr(t, 'tmax', None):
                    self.in_TMax.setText(f'{t.tmax:g}')
                if getattr(t, 'dt', None):
                    self.in_DT.setText(f'{t.dt:g}')
            except Exception:
                pass
        self._sync_outlist_display()
        self._log('已同步模型参数到单工况设置（可修改后再生成）')

    # ------------------------------------------------------------------ 交互
    def _collect_single(self, name='case1'):
        from core.cases import SingleCaseConfig
        return SingleCaseConfig(
            name=name,
            U0=_f(self.in_U0.text(), 8.0),
            RPM=_f(self.in_RPM.text(), 273.0),
            TMax=_f(self.in_TMax.text(), 1.0),
            DT=_f(self.in_DT.text(), 0.0006),
            pitch_deg=_f(self.in_pitch.text(), 0.0),
            yaw_deg=_f(self.in_yaw.text(), 0.0),
            out_format=self.cb_outfmt.currentIndex() + 1,
            wr_vtk=self.cb_vtk.currentIndex(),
            olaf_wr_vtk=self.cb_olaf_vtk.currentIndex(),
            olaf_n_vtk_blades=int(_f(self.in_nvtk_blades.text(), 0)),
            olaf_vtk_coord=self.cb_vtk_coord.currentIndex() + 1,
            olaf_vtk_fps=_f(self.in_vtk_fps.text(), 20.0),
            olaf_n_grid_out=int(_f(self.in_grid_out.text(), 0)),
            use_fast_olaf_grid=True,
            nNW=488, nNWFree=65,
            outlist=self._outlist_names(),
            outlist_ad=self._outlist_names_ad(),
        )

    def _sync_olaf_vtk_controls(self):
        """关闭尾迹 VTK 时同步关闭尾迹网格和叶片 VTK 输出。"""
        enabled = self.cb_olaf_vtk.currentIndex() != 0
        if not enabled:
            self.in_nvtk_blades.setText('0')
            self.in_grid_out.setText('0')
        for widget in (self.in_nvtk_blades, self.in_vtk_fps,
                       self.cb_vtk_coord, self.in_grid_out):
            widget.setEnabled(enabled)

    def _outlist_names(self):
        """以 AD.dat 的 OutList 段为准（模型内已维护）。"""
        if self.model.ad:
            return list(self.model.ad.get('OutList', []) or [])
        # 兜底：从输出通道 grid 读取
        names = []
        for i in range(self.out_grid.count()):
            w = self.out_grid.itemAt(i).widget()
            if w is not None and isinstance(w, QLabel):
                names.append(w.text())
        return names

    def _outlist_names_ad(self):
        """以 AD.dat 的 OutListAD 段（节点输出）为准。"""
        if self.model.ad:
            return list(self.model.ad.get('OutListAD', []) or [])
        return []

    def choose_outlist(self):
        """编辑输出通道：以 AD.dat 的 OutList / OutListAD 为准，
        OutListParameters.xlsx 仅作参考搜索。"""
        from core.outlist import DEFAULT_XLSX, load_aerodyn_channels
        df = None
        ip = getattr(self.window(), 'input_page', None)
        if ip is not None and ip.outlist_df is not None:
            df = ip.outlist_df
        if df is None and os.path.isfile(DEFAULT_XLSX):
            df = load_aerodyn_channels(DEFAULT_XLSX)
        dlg = OutListEditorDialog(self.model, df=df, parent=self)
        if dlg.exec() == OutListEditorDialog.Accepted:
            res = dlg.result_maps()
            self._sync_outlist_display()
            self._log(f'已更新 OutList({len(res["OutList"])}) / '
                      f'OutListAD({len(res["OutListAD"])})，将在生成工况时写入 AD.dat')

    def _sync_outlist_display(self):
        """用 QGridLayout + QLabel 固定 3 列显示当前 OutList，文本完整不省略。"""
        ol = self.model.ad.get('OutList', []) if self.model.ad else []
        # 清空旧 label
        while self.out_grid.count():
            it = self.out_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, name in enumerate(ol):
            lbl = QLabel(name)
            lbl.setStyleSheet('border:1px solid #c5cbd3; border-radius:3px; '
                              'padding:1px 6px; background:#f5f7fa;')
            self.out_grid.addWidget(lbl, i // 3, i % 3)   # 固定 3 列

    def gen_single(self):
        if not self._check_model():
            return
        workdir = QFileDialog.getExistingDirectory(self, '选择单工况输出目录',
                                                   self.model.root or os.getcwd())
        if not workdir:
            return
        from core.cases import generate_single_case
        case = self._collect_single()
        try:
            generate_single_case(self.model, case, workdir)
            self.model.executable = self.picker_exe.path()
            self._log(f'单工况已生成 → {workdir}\n  ' + repr(case))
        except Exception as e:
            QMessageBox.critical(self, '生成失败', str(e))

    def gen_batch(self):
        if not self._check_model():
            return
        workdir = QFileDialog.getExistingDirectory(self, '选择批量工况根目录',
                                                   self.model.root or os.getcwd())
        if not workdir:
            return
        from core.cases import BatchConfig, generate_batch_cases
        u0s = [float(x) for x in _nums(self.in_U0s.text())]
        rpms = [float(x) for x in _nums(self.in_RPMs.text())]
        # 批量以单工况为模板：只扫描 U0/RPM，其余参数（TMax/DT/桨距/偏航/输出格式/
        # VTK/OutList/OutListAD/OLAF 网格）全部继承 _collect_single()
        batch = BatchConfig(U0s=u0s, RPMs=rpms, combine=self.cb_combine.isChecked(),
                            base=self._collect_single())
        try:
            pairs = generate_batch_cases(self.model, batch, workdir)
            self._log(f'批量工况已生成 {len(pairs)} 个 → {workdir}')
            for case, d in pairs:
                self._log(f'  - {case.name}  U0={case.U0} RPM={case.RPM}  → {d}')
        except Exception as e:
            QMessageBox.critical(self, '生成失败', str(e))

    def run_all(self):
        exe = self.picker_exe.path()
        if not exe:
            QMessageBox.warning(self, '提示', '请先选择可执行文件')
            return
        root = QFileDialog.getExistingDirectory(self, '选择工况根目录', os.getcwd())
        if not root:
            return
        from core.runner import run_many
        dirs = [os.path.join(root, d) for d in os.listdir(root)
                if os.path.isdir(os.path.join(root, d)) and
                os.path.isfile(os.path.join(root, d, 'ad_driver.dvr'))]
        if not dirs:
            QMessageBox.warning(self, '提示', '目录中没有找到含 ad_driver.dvr 的工况子目录')
            return
        self._log(f'开始运行 {len(dirs)} 个工况…')
        try:
            res = run_many(dirs, exe, show=False)
            ok = sum(1 for _, r in res if r.returncode == 0)
            self._log(f'完成: 成功 {ok}/{len(res)}')
        except Exception as e:
            QMessageBox.critical(self, '运行失败', str(e))

    def summarize_batch(self):
        root = QFileDialog.getExistingDirectory(self, '选择批量工况根目录', os.getcwd())
        if not root:
            return
        from core.postprocess import load_fast_output, steady_stats, calc_cp_tsr
        rows = []
        for d in sorted(os.listdir(root)):
            dd = os.path.join(root, d)
            out = os.path.join(dd, 'ad_driver.out')
            if not os.path.isfile(out):
                continue
            try:
                df = load_fast_output(out)
                st = steady_stats(df, 'RtAeroPwr_[W]')
                cp = calc_cp_tsr(st['mean'], self.model.turbine.hwind_speed,
                                 self.model.turbine.rot_speed, R=0.6, H=6.1)
                rows.append({'case': d, 'P_mean_W': st['mean'],
                             'Cp': cp['Cp'], 'TSR': cp['TSR']})
            except Exception as e:
                rows.append({'case': d, 'error': str(e)})
        import pandas as pd
        summ = pd.DataFrame(rows)
        self._log('\n==== 批量结果汇总 ====\n' + summ.to_string(index=False))
        parent = self.window()
        rp = getattr(parent, 'results_page', None)
        if rp is not None:
            rp.set_batch_summary(summ)

    # ------------------------------------------------------------------
    def _check_model(self):
        if self.model.turbine is None:
            QMessageBox.warning(self, '提示', '请先在「输入文件」页加载模型')
            return False
        return True

    def _log(self, msg):
        self.log.append(msg)
