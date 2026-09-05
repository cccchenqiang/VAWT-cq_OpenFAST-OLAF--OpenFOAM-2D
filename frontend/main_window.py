# -*- coding: utf-8 -*-
"""主窗口：QTabWidget 组织 OpenFAST 与 OpenFOAM 工作流。"""
import os

from PySide6.QtWidgets import QMainWindow, QTabWidget

from core.models import VAWTModel
from .pages import InputPage, GeometryPage, CasesPage, ResultsPage, OpenFOAMPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('VAWT仿真工具箱cq_OpenFAST(OLAF)-OpenFOAM 2D')
        self.resize(1280, 860)
        self.model = VAWTModel()

        self.tabs = QTabWidget()
        self.input_page = InputPage(self.model)
        self.geometry_page = GeometryPage(self.model)
        self.cases_page = CasesPage(self.model)
        self.results_page = ResultsPage(self.model)
        self.openfoam_page = OpenFOAMPage(self.model, os.path.dirname(os.path.dirname(__file__)))

        # 关联：输入页引用（供工况页读取 outlist_df）
        self.input_page.outlist_df = None
        self.cases_page._input_page = self.input_page

        self.tabs.addTab(self.input_page, '① 输入文件')
        self.tabs.addTab(self.geometry_page, '② 风轮几何')
        self.tabs.addTab(self.cases_page, '③ 工况设置')
        self.tabs.addTab(self.results_page, '④ 结果处理')
        self.tabs.addTab(self.openfoam_page, '⑤ OpenFOAM 案例')
        self.setCentralWidget(self.tabs)

        # 联动：模型加载后刷新几何/工况页
        self.input_page.files_loaded.connect(self.geometry_page.refresh)
        self.input_page.files_loaded.connect(self._on_model_loaded)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_model_loaded(self):
        # 把模型参数与 AD.dat 的 OutList 同步到工况页
        self.cases_page.sync_from_model()
        self.statusBar().showMessage('模型加载完成')

    def _on_tab_changed(self, idx):
        # 切到几何页时自动刷新
        if idx == 1:
            self.geometry_page.refresh()
