import math
from dataclasses import fields

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QThreadPool, Qt
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTextEdit, QVBoxLayout, QWidget)

from core.openfoam.config import OpenFOAMCaseConfig
from core.openfoam.generator import convert_le_te_orientation, read_airfoil
from core.openfoam.service import OpenFOAMCaseService


class _PreviewCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.zoom = 1.0
        self.center = (0.0, 0.0)
        self.drag_start = None
        self.setMinimumHeight(260)
        self.setMouseTracking(True)

    def set_data(self, config, profile):
        self.data = (config, profile)
        self.center = ((config.domain_x_min + config.domain_x_max) / 2.0, 0.0)
        self.zoom = 1.0
        self.update()

    def wheelEvent(self, event):
        if not self.data:
            return
        pos = event.position()
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.zoom = max(0.2, min(100.0, self.zoom * factor))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.position()

    def mouseMoveEvent(self, event):
        if self.drag_start and self.data:
            dx = event.position().x() - self.drag_start.x()
            dy = event.position().y() - self.drag_start.y()
            config, _ = self.data
            scale = self._scale(config) * self.zoom
            self.center = (self.center[0] - dx / scale, self.center[1] + dy / scale)
            self.drag_start = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_start = None

    def _scale(self, config):
        return min((self.width() - 80) / (config.domain_x_max - config.domain_x_min),
                   (self.height() - 80) / (2.0 * config.domain_y))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        if not self.data:
            painter.setPen(QColor("#666666"))
            painter.drawText(12, 24, "点击“预览当前模拟”显示计算域、AMI 和叶片")
            return
        config, profile = self.data
        scale = self._scale(config) * self.zoom
        cx, cy = self.center

        def point(x, y):
            return (self.width() / 2 + (x - cx) * scale,
                    self.height() / 2 - (y - cy) * scale)

        def polygon(angle):
            theta = math.radians(angle)
            cp, sp = math.cos(theta), math.sin(theta)
            radial, tangential = (cp, sp), (-sp, cp)
            pitch = math.radians(config.pitch_deg)
            chord = (tangential[0] * math.cos(pitch) + radial[0] * math.sin(pitch),
                     tangential[1] * math.cos(pitch) + radial[1] * math.sin(pitch))
            normal = (-tangential[0] * math.sin(pitch) + radial[0] * math.cos(pitch),
                      -tangential[1] * math.sin(pitch) + radial[1] * math.cos(pitch))
            return [point(config.rotor_radius * radial[0] + x * config.chord * chord[0]
                          + y * config.chord * normal[0],
                          config.rotor_radius * radial[1] + x * config.chord * chord[1]
                          + y * config.chord * normal[1]) for x, y in profile]

        painter.setPen(QPen(QColor("#777777"), 2))
        a = point(config.domain_x_min, config.domain_y)
        b = point(config.domain_x_max, -config.domain_y)
        painter.drawRect(min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1]))
        origin = point(0, 0)
        ami = config.ami_diameter * scale / 2
        painter.setPen(QPen(QColor("#e67e22"), 2, Qt.PenStyle.DashLine))
        painter.drawEllipse(origin[0] - ami, origin[1] - ami, 2 * ami, 2 * ami)
        painter.setPen(QPen(QColor("#3498db"), 1))
        painter.drawLine(*point(config.domain_x_min, 0), *point(config.domain_x_max, 0))
        painter.setPen(QPen(QColor("#c0392b"), 2))
        for blade in range(config.blade_count):
            points = polygon(blade * 360.0 / config.blade_count)
            for first, second in zip(points, points[1:] + points[:1]):
                painter.drawLine(*first, *second)
        painter.setPen(QColor("#555555"))
        painter.drawText(12, 22, f"Xmin={config.domain_x_min:g}, Xmax={config.domain_x_max:g}, "
                                 f"Y=+/-{config.domain_y:g} m")
        painter.drawText(12, 42, f"AMI diameter={config.ami_diameter:g} m, "
                                 f"rotor diameter={2 * config.rotor_radius:g} m")


class _WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str)


class _GenerateWorker(QRunnable):
    def __init__(self, service, config):
        super().__init__()
        self.service, self.config = service, config
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        try:
            self.signals.done.emit(self.service.generate_case(self.config))
        except Exception as exc:
            self.signals.error.emit(str(exc))


class OpenFOAMPage(QWidget):
    def __init__(self, model, project_root, parent=None):
        super().__init__(parent)
        self.model = model
        self.service = OpenFOAMCaseService(project_root)
        self.thread_pool = QThreadPool.globalInstance()
        self.inputs = {}
        self._last_auto_ami = 0.675
        self._build_ui()
        self._update_automatic_domain()
        self._toggle_domain_fields(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        files = QGroupBox("文件")
        file_grid = QGridLayout(files)
        self._add_file(file_grid, 0, "翼型坐标", "airfoil", "选择翼型文件")
        self._add_file(file_grid, 1, "输出案例目录", "output", "选择输出目录", True)
        layout.addWidget(files)

        geometry = QGroupBox("风轮几何")
        grid = QGridLayout(geometry)
        defaults = [("rotor_radius", "转子半径 (m)", "0.225"),
                    ("chord", "弦长 (m)", "0.1"), ("blade_count", "叶片数", "3"),
                    ("pitch_deg", "安装角 (deg)", "0"), ("shaft_radius", "轴半径 (m)", "0.0075"),
                    ("height", "二维厚度/叶片高度 (m)", "0.05")]
        self._add_fields(grid, defaults)
        layout.addWidget(geometry)

        operation = QGroupBox("工况与时间")
        grid = QGridLayout(operation)
        self._add_fields(grid, [("rpm", "转速 (rpm)", "300"), ("inlet_velocity", "来流速度 (m/s)", "8"),
                                ("start_time", "起始时间 (s)", "0"), ("end_time", "终止时间 (s)", "2"),
                                ("delta_t", "时间步长 (s)", "0.0001"),
                                ("write_interval", "输出间隔 (s)", "0.05")])
        layout.addWidget(operation)

        mesh = QGroupBox("网格与计算域")
        grid = QGridLayout(mesh)
        self._add_fields(grid, [("domain_x_min", "计算域 Xmin (m)", "-1.2"),
                                ("domain_x_max", "计算域 Xmax (m)", "2.8"),
                                ("domain_y", "计算域半高 Y (m)", "1.2"),
                                ("ami_diameter", "AMI 区域直径 (m)", "0.675"),
                                ("mesh_x", "背景网格 X 单元数", "40"),
                                ("mesh_y", "背景网格 Y 单元数", "24"),
                                ("blade_refinement", "叶片加密等级", "4"),
                                ("ami_refinement", "AMI 加密等级", "3")])
        self.custom_domain = QCheckBox("启用自定义计算域和 AMI 直径")
        self.custom_domain.toggled.connect(self._toggle_domain_fields)
        grid.addWidget(self.custom_domain, 4, 0, 1, 4)
        layout.addWidget(mesh)

        preview_group = QGroupBox("模拟预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_info = QLabel("点击“预览当前模拟”更新图形；滚轮缩放，鼠标左键拖动平移")
        self.preview_canvas = _PreviewCanvas()
        preview_layout.addWidget(self.preview_info)
        preview_layout.addWidget(self.preview_canvas)
        layout.addWidget(preview_group, 1)

        actions = QHBoxLayout()
        for text, callback in (("从 OpenFAST 映射", self.map_from_fast),
                               ("预览当前模拟", self.preview),
                               ("生成 OpenFOAM 案例", self.generate)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(100)
        layout.addWidget(self.log)

    def _add_fields(self, grid, definitions):
        start = grid.rowCount()
        for index, (name, label, value) in enumerate(definitions):
            row, col = divmod(start + index, 4)
            grid.addWidget(QLabel(label), row, col * 2)
            edit = QLineEdit(value)
            grid.addWidget(edit, row, col * 2 + 1)
            self.inputs[name] = edit
            if name == "rotor_radius":
                edit.textChanged.connect(self._update_automatic_domain)

    def _add_file(self, grid, row, label, name, button_text, directory=False):
        grid.addWidget(QLabel(label), row, 0)
        edit = QLineEdit()
        self.inputs[name] = edit
        grid.addWidget(edit, row, 1)
        button = QPushButton(button_text)
        button.clicked.connect(lambda: self._choose(edit, directory))
        grid.addWidget(button, row, 2)

    @staticmethod
    def _choose(edit, directory):
        if directory:
            selected = QFileDialog.getExistingDirectory(None, "选择输出父目录")
            if selected:
                edit.setText(selected + "\\vawt_case")
        else:
            selected, _ = QFileDialog.getOpenFileName(
                None, "选择翼型坐标文件", "", "Coordinate files (*.txt *.dat *.csv);;All files (*)")
            if selected:
                edit.setText(selected)

    def _update_automatic_domain(self):
        if self.custom_domain.isChecked():
            return
        try:
            diameter = 2 * float(self.inputs["rotor_radius"].text())
            self.inputs["domain_x_min"].setText(f"{-5 * diameter:.6g}")
            self.inputs["domain_x_max"].setText(f"{20 * diameter:.6g}")
            self.inputs["domain_y"].setText(f"{3.5 * diameter:.6g}")
            self._last_auto_ami = 1.5 * diameter
            self.inputs["ami_diameter"].setText(f"{self._last_auto_ami:.6g}")
        except ValueError:
            pass

    def _toggle_domain_fields(self, enabled=None):
        enabled = self.custom_domain.isChecked() if enabled is None else enabled
        for name in ("domain_x_min", "domain_x_max", "domain_y", "ami_diameter"):
            self.inputs[name].setEnabled(enabled)
        if not enabled:
            self._update_automatic_domain()

    def _config(self):
        integer_fields = {"blade_count", "mesh_x", "mesh_y", "blade_refinement", "ami_refinement"}
        values = {"airfoil": self.inputs["airfoil"].text().strip(),
                  "output": self.inputs["output"].text().strip(),
                  "custom_domain": self.custom_domain.isChecked()}
        for field in fields(OpenFOAMCaseConfig):
            if field.name in ("airfoil", "output", "custom_domain"):
                continue
            raw = self.inputs[field.name].text().strip() if field.name in self.inputs else ""
            values[field.name] = int(raw) if field.name in integer_fields else float(raw)
        return OpenFOAMCaseConfig(**values)

    def preview(self):
        try:
            config = self._config()
            profile = convert_le_te_orientation(read_airfoil(config.airfoil))
            config.ami_diameter = config.ami_diameter or 1.5 * 2 * config.rotor_radius
            self.preview_canvas.set_data(config, profile)
            self.preview_info.setText(
                f"来流速度: {config.inlet_velocity:g} m/s    转速: {config.rpm:g} rpm    "
                f"AMI 直径: {config.ami_diameter:g} m")
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "无法预览", str(exc))

    def map_from_fast(self):
        try:
            values = self.service.map_from_fast(self.model)
            for key, value in values.items():
                if key in self.inputs:
                    self.inputs[key].setText(str(value))
            self.log.append("已从 OpenFAST 模型映射参数。")
        except Exception as exc:
            QMessageBox.warning(self, "映射失败", str(exc))

    def generate(self):
        try:
            config = self._config()
            if not config.airfoil or not config.output:
                raise ValueError("请先选择翼型文件和新输出目录")
            worker = _GenerateWorker(self.service, config)
            worker.signals.done.connect(lambda path: self.log.append(f"案例已生成: {path}"))
            worker.signals.error.connect(lambda msg: QMessageBox.critical(self, "生成失败", msg))
            self.thread_pool.start(worker)
            self.log.append("开始生成 OpenFOAM 案例...")
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "参数错误", str(exc))
