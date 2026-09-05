# -*- coding: utf-8 -*-
"""文件选择行控件：标签 + 路径输入框 + 浏览按钮。"""
import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QFileDialog)


class FilePickerRow(QWidget):
    """一行：描述标签 + 路径输入 + 浏览按钮。"""

    def __init__(self, label, filters='', default_dir='', parent=None):
        super().__init__(parent)
        self.filters = filters
        self.default_dir = default_dir
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        self.label = QLabel(label)
        self.label.setFixedWidth(110)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('请选择文件…')
        self.btn = QPushButton('浏览…')
        self.btn.setFixedWidth(70)
        self.btn.clicked.connect(self._browse)
        lay.addWidget(self.label)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.btn)

    def _browse(self):
        start = self.edit.text() or self.default_dir
        path, _ = QFileDialog.getOpenFileName(self, '选择文件', start, self.filters)
        if path:
            self.edit.setText(path)

    def path(self):
        return self.edit.text().strip()

    def set_path(self, p):
        self.edit.setText(p if p else '')

    def has(self):
        return bool(self.path())
