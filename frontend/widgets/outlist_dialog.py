# -*- coding: utf-8 -*-
"""输出通道编辑对话框。

输出通道以 AD.dat 中的 OutList / OutListAD 段为准；
OutListParameters.xlsx 仅作为"参考"：用于搜索可用通道名与查看单位/描述，
不直接作为输出列表。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QLabel,
                               QTabWidget, QWidget, QMessageBox, QSplitter)


class OutListEditorDialog(QDialog):
    """编辑 AD.dat 的两个输出段：OutList（全局通道）与 OutListAD（节点通道）。"""

    def __init__(self, model, df=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('编辑输出通道（来自 AD.dat 的 OutList / OutListAD）')
        self.resize(860, 620)
        self.model = model
        self.df = df          # OutListParameters.xlsx 的 AeroDyn 通道表（参考用，可为 None）
        self._current_tab = 0

        lay = QVBoxLayout(self)

        # ---------- 顶部：xlsx 参考搜索 ----------
        ref = QWidget()
        rl = QHBoxLayout(ref)
        rl.addWidget(QLabel('参考通道表 (OutListParameters.xlsx):'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('输入关键词搜索可用通道名（如 Pwr / Alpha / Cl）…')
        self.search.textChanged.connect(self._do_search)
        rl.addWidget(self.search, 1)
        self.lbl_ref = QLabel('未加载' if self.df is None else f'已加载 {len(self.df)} 通道')
        rl.addWidget(self.lbl_ref)
        lay.addWidget(ref)

        self.ref_list = QListWidget()
        self.ref_list.setMaximumHeight(150)
        self.ref_list.itemDoubleClicked.connect(lambda it: self._add_from_ref(it))
        lay.addWidget(self.ref_list)
        hint = QLabel('（双击左侧参考通道加入下方当前段；下方列表可直接增删）')
        hint.setStyleSheet('color: #666;')
        lay.addWidget(hint)

        # ---------- 中部：两个输出段 tab ----------
        self.tabs = QTabWidget()
        self.list_out = QListWidget()
        self.list_ad = QListWidget()
        self.tabs.addTab(self._make_seg(self.list_out), 'OutList  (全局输出)')
        self.tabs.addTab(self._make_seg(self.list_ad), 'OutListAD (节点输出)')
        self.tabs.currentChanged.connect(self._on_tab)
        lay.addWidget(self.tabs, 1)

        # ---------- 底部按钮 ----------
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_ok = QPushButton('确定并写回 AD.dat')
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton('取消')
        self.btn_cancel.clicked.connect(self.reject)
        row.addWidget(self.btn_ok)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        # 初始化当前段
        self._populate(self.list_out, self._get('OutList'))
        self._populate(self.list_ad, self._get('OutListAD'))
        self._do_search()

    # ------------------------------------------------------------------
    def _make_seg(self, listw):
        w = QWidget()
        lay = QVBoxLayout(w)
        h = QHBoxLayout()
        self.inp_add = QLineEdit()
        self.inp_add.setPlaceholderText('手动输入通道名后点击「添加」')
        h.addWidget(self.inp_add, 1)
        btn_add = QPushButton('添加')
        btn_add.clicked.connect(lambda: self._add_manual(listw))
        btn_del = QPushButton('删除选中')
        btn_del.clicked.connect(lambda: self._del_selected(listw))
        btn_up = QPushButton('上移')
        btn_up.clicked.connect(lambda: self._move(listw, -1))
        btn_down = QPushButton('下移')
        btn_down.clicked.connect(lambda: self._move(listw, 1))
        h.addWidget(btn_add)
        h.addWidget(btn_del)
        h.addWidget(btn_up)
        h.addWidget(btn_down)
        lay.addLayout(h)
        lay.addWidget(listw)
        return w

    # ------------------------------------------------------------------
    def _get(self, key):
        if self.model and self.model.ad:
            return list(self.model.ad.get(key, []) or [])
        return []

    def _populate(self, listw, items):
        listw.clear()
        for it in items:
            listw.addItem(QListWidgetItem(str(it)))

    def _current_list(self):
        return self.list_out if self.tabs.currentIndex() == 0 else self.list_ad

    def _on_tab(self, idx):
        self._current_tab = idx

    def _add_from_ref(self, item):
        name = item.data(Qt.UserRole) or item.text()
        self._append_unique(self._current_list(), name)

    def _add_manual(self, listw):
        name = self.inp_add.text().strip()
        if name:
            self._append_unique(listw, name)
            self.inp_add.clear()

    def _append_unique(self, listw, name):
        for i in range(listw.count()):
            if listw.item(i).text() == name:
                return
        listw.addItem(QListWidgetItem(name))

    def _del_selected(self, listw):
        for it in listw.selectedItems():
            listw.takeItem(listw.row(it))

    def _move(self, listw, d):
        row = listw.currentRow()
        new = row + d
        if row < 0 or new < 0 or new >= listw.count():
            return
        it = listw.takeItem(row)
        listw.insertItem(new, it)
        listw.setCurrentRow(new)

    def _do_search(self):
        kw = self.search.text().strip()
        self.ref_list.clear()
        if self.df is None:
            return
        from core.outlist import search_channels
        rows = search_channels(self.df, kw) if kw else self.df
        rows = rows.head(200)
        for _, r in rows.iterrows():
            name = str(r.get('Name', ''))
            if not name:
                continue
            desc = str(r.get('Description', '')) or ''
            units = str(r.get('Units', '')) or ''
            it = QListWidgetItem(f'{name}   [{desc}]  {units}'.strip())
            it.setData(Qt.UserRole, name)
            self.ref_list.addItem(it)

    # ------------------------------------------------------------------
    def accept(self):
        def collect(listw):
            return [self.listw_item_text(listw, i) for i in range(listw.count())]
        outlist = collect(self.list_out)
        outlist_ad = collect(self.list_ad)
        # 写回模型（生成工况时据此改写 AD.dat）
        if self.model and self.model.ad:
            self.model.ad['OutList'] = outlist
            self.model.ad['OutListAD'] = outlist_ad
        self._result = {'OutList': outlist, 'OutListAD': outlist_ad}
        super().accept()

    @staticmethod
    def listw_item_text(listw, i):
        return listw.item(i).text()

    def result_maps(self):
        return getattr(self, '_result', {'OutList': [], 'OutListAD': []})
