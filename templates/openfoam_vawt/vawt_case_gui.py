#!/usr/bin/env python3
"""Tkinter GUI for vawt_case_generator.py.

Run with the Python interpreter from weis2-env:
    python vawt_case_gui.py
"""

import argparse
import math
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from vawt_case_generator import convert_le_te_orientation, generate, read_airfoil


class VAWTGeneratorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("2D VAWT OpenFOAM Case Generator")
        self.geometry("760x700")
        self.minsize(680, 600)
        self.variables = {}
        self.widgets = {}
        self.custom_domain = tk.BooleanVar(value=False)
        self._last_auto_ami = 1.35
        self.preview_canvas = None
        self.preview_info = None
        self.preview_profile = None
        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="二维垂直轴风轮 OpenFOAM 案例生成器",
                          font=("TkDefaultFont", 14, "bold"))
        title.pack(anchor="w", pady=(0, 4))
        ttk.Label(root, text="基于现有模板，兼容目标版本：OpenFOAM Foundation 5.x"
                  ).pack(anchor="w", pady=(0, 10))

        self._add_file_row(root, "翼型坐标文件", "airfoil", "选择翼型文件")
        self._add_file_row(root, "输出案例目录", "output", "选择输出目录", directory=True)

        notebook = ttk.Notebook(root)
        self.notebook = notebook
        notebook.pack(fill="both", expand=True, pady=8)
        geometry = ttk.Frame(notebook, padding=10)
        operation = ttk.Frame(notebook, padding=10)
        mesh = ttk.Frame(notebook, padding=10)
        preview = ttk.Frame(notebook, padding=8)
        notebook.add(geometry, text="风轮几何")
        notebook.add(operation, text="工况与时间")
        notebook.add(mesh, text="网格与计算域")
        notebook.add(preview, text="模拟预览")

        self._add_fields(geometry, [
            ("rotor_radius", "转子半径 (m)", "0.225"),
            ("chord", "弦长 (m)", "0.1"),
            ("blade_count", "叶片数", "3"),
            ("pitch_deg", "安装角 (deg)", "0"),
            ("shaft_radius", "轴半径 (m)", "0.0075"),
            ("height", "二维厚度/叶片高度 (m)", "0.05"),
        ])
        self._add_fields(operation, [
            ("rpm", "转速 (rpm)", "300"),
            ("inlet_velocity", "来流速度 (m/s)", "8"),
            ("start_time", "模拟起点 startTime (s)", "0"),
            ("end_time", "模拟终点 endTime (s)", "2"),
            ("delta_t", "模拟时间步长 deltaT (s)", "0.0001"),
            ("write_interval", "结果输出间隔 writeInterval (s)", "0.05"),
        ])
        self._add_fields(mesh, [
            ("domain_x_min", "计算域 Xmin (m)", "-1.2"),
            ("domain_x_max", "计算域 Xmax (m)", "2.8"),
            ("domain_y", "计算域半高 Y (m)", "1.2"),
            ("mesh_x", "背景网格 X 单元数", "40"),
            ("mesh_y", "背景网格 Y 单元数", "24"),
            ("blade_refinement", "叶片加密等级", "4"),
            ("ami_refinement", "AMI 加密等级", "3"),
            ("ami_diameter", "AMI区域直径 (m，默认1.5D)", "1.35"),
        ])
        ttk.Checkbutton(mesh, text="启用自定义计算域（默认按上风5D、下风20D、总宽度7D自动设置）",
                        variable=self.custom_domain,
                        command=self._toggle_domain_fields).grid(
                            row=8, column=0, columnspan=2, sticky="w", pady=(12, 4))
        self._toggle_domain_fields()
        self.preview_info = ttk.Label(preview, text="点击“预览当前模拟”更新图形")
        self.preview_info.pack(anchor="w", pady=(0, 4))
        self.preview_canvas = tk.Canvas(preview, background="white")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda _event: self._draw_preview())
        self.preview_canvas.bind("<MouseWheel>", self._preview_zoom)
        self.preview_canvas.bind("<Button-4>", self._preview_zoom)
        self.preview_canvas.bind("<Button-5>", self._preview_zoom)
        self.preview_canvas.bind("<ButtonPress-1>", self._preview_box_start)
        self.preview_canvas.bind("<B1-Motion>", self._preview_box_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._preview_box_end)
        self.preview_zoom_factor = 1.0
        self.preview_center = None
        self.preview_box = None
        ttk.Button(preview, text="重置预览视图",
                   command=self._reset_preview_view).pack(anchor="e", pady=(4, 0))

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(4, 0))
        ttk.Button(bottom, text="预览当前模拟", command=self._preview).pack(side="left", padx=(0, 8))
        self.generate_button = ttk.Button(bottom, text="生成 OpenFOAM 案例",
                                           command=self._start_generation)
        self.generate_button.pack(side="left")
        self.status = ttk.Label(bottom, text="就绪")
        self.status.pack(side="left", padx=12)

        self.log = tk.Text(root, height=8, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=False, pady=(8, 0))

    def _toggle_domain_fields(self):
        editable = "normal" if self.custom_domain.get() else "disabled"
        for key in ("domain_x_min", "domain_x_max", "domain_y", "ami_diameter"):
            if key in self.widgets:
                self.widgets[key].configure(state=editable)
        if not self.custom_domain.get() and "rotor_radius" in self.variables:
            try:
                diameter = 2.0 * float(self.variables["rotor_radius"].get())
                self.variables["domain_x_min"].set("%.6g" % (-5.0 * diameter))
                self.variables["domain_x_max"].set("%.6g" % (20.0 * diameter))
                self.variables["domain_y"].set("%.6g" % (3.5 * diameter))
                self._last_auto_ami = 1.5 * diameter
                self.variables["ami_diameter"].set("%.6g" % self._last_auto_ami)
            except ValueError:
                pass

    def _add_file_row(self, parent, label, key, button_text, directory=False):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=20).pack(side="left")
        variable = tk.StringVar()
        self.variables[key] = variable
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        if directory:
            command = lambda: self._choose_directory(variable)
        else:
            command = lambda: self._choose_file(variable)
        ttk.Button(row, text=button_text, command=command).pack(side="left", padx=(6, 0))

    def _add_fields(self, parent, fields):
        for row_index, (key, label, default) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row_index, column=0, sticky="w", pady=4)
            variable = tk.StringVar(value=default)
            self.variables[key] = variable
            entry = ttk.Entry(parent, textvariable=variable, width=24)
            entry.grid(
                row=row_index, column=1, sticky="w", padx=12, pady=4)
            self.widgets[key] = entry
            if key in ("rotor_radius", "chord", "blade_count", "pitch_deg",
                       "shaft_radius", "height"):
                variable.trace_add("write", lambda *_args: self._toggle_domain_fields())

    @staticmethod
    def _choose_file(variable):
        selected = filedialog.askopenfilename(
            title="选择翼型坐标文件",
            filetypes=[("Coordinate files", "*.txt *.dat *.csv"), ("All files", "*.*")])
        if selected:
            variable.set(selected)

    @staticmethod
    def _choose_directory(variable):
        selected = filedialog.askdirectory(title="选择输出父目录")
        if selected:
            variable.set(str(Path(selected) / "vawt_case"))

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start_generation(self):
        try:
            args = self._make_args()
        except ValueError as error:
            messagebox.showerror("输入参数错误", str(error))
            return

        output = Path(args.output).expanduser()
        if output.exists():
            messagebox.showerror("输出目录已存在", "请选择一个不存在的新目录：\n%s" % output)
            return

        self.generate_button.configure(state="disabled")
        self.status.configure(text="正在生成...")
        self._append_log("开始生成：%s" % output)
        threading.Thread(target=self._generate_worker, args=(args,), daemon=True).start()

    def _preview(self):
        try:
            args = self._make_args()
            profile = convert_le_te_orientation(read_airfoil(args.airfoil))
        except (ValueError, OSError) as error:
            messagebox.showerror("无法预览", str(error))
            return

        self.preview_profile = (args, profile)
        self.notebook.select(3)
        self._reset_preview_view()
        self.preview_info.configure(text="来流速度: %.3g m/s    转速: %.3g rpm    AMI直径: %.3g m" %
                                    (args.inlet_velocity, args.rpm, args.ami_diameter))
        self._draw_preview()

    def _reset_preview_view(self):
        if self.preview_profile is not None:
            args, _profile = self.preview_profile
            self.preview_center = ((args.domain_x_min + args.domain_x_max) / 2.0, 0.0)
        else:
            self.preview_center = (0.0, 0.0)
        self.preview_zoom_factor = 1.0
        self.preview_box = None
        self._draw_preview()

    def _preview_zoom(self, event):
        if self.preview_profile is None:
            return "break"
        args, _profile = self.preview_profile
        width, height = max(self.preview_canvas.winfo_width(), 100), max(self.preview_canvas.winfo_height(), 100)
        base_scale = min((width - 80) / (args.domain_x_max - args.domain_x_min),
                         (height - 80) / (2.0 * args.domain_y))
        cursor_x, cursor_y = event.x, event.y
        old_scale = base_scale * self.preview_zoom_factor
        center_x, center_y = self.preview_center
        world_x = center_x + (cursor_x - width / 2.0) / old_scale
        world_y = center_y - (cursor_y - height / 2.0) / old_scale
        direction = getattr(event, "delta", 0)
        if direction == 0:
            direction = 120 if getattr(event, "num", 4) == 4 else -120
        factor = 1.2 if direction > 0 else 1.0 / 1.2
        self.preview_zoom_factor = min(100.0, max(0.2, self.preview_zoom_factor * factor))
        new_scale = base_scale * self.preview_zoom_factor
        self.preview_center = (world_x - (cursor_x - width / 2.0) / new_scale,
                               world_y + (cursor_y - height / 2.0) / new_scale)
        self._draw_preview()
        return "break"

    def _preview_box_start(self, event):
        if self.preview_profile is not None:
            self.preview_box = (event.x, event.y, event.x, event.y)

    def _preview_box_drag(self, event):
        if self.preview_box is not None:
            x0, y0, _x1, _y1 = self.preview_box
            self.preview_box = (x0, y0, event.x, event.y)
            self._draw_preview()

    def _preview_box_end(self, event):
        if self.preview_box is None or self.preview_profile is None:
            return
        x0, y0, x1, y1 = self.preview_box
        self.preview_box = None
        if abs(x1 - x0) < 12 or abs(y1 - y0) < 12:
            self._draw_preview()
            return
        args, _profile = self.preview_profile
        width, height = max(self.preview_canvas.winfo_width(), 100), max(self.preview_canvas.winfo_height(), 100)
        base_scale = min((width - 80) / (args.domain_x_max - args.domain_x_min),
                         (height - 80) / (2.0 * args.domain_y))
        scale = base_scale * self.preview_zoom_factor
        center_x, center_y = self.preview_center
        left = center_x + (min(x0, x1) - width / 2.0) / scale
        right = center_x + (max(x0, x1) - width / 2.0) / scale
        top = center_y - (min(y0, y1) - height / 2.0) / scale
        bottom = center_y - (max(y0, y1) - height / 2.0) / scale
        selected_width, selected_height = right - left, top - bottom
        self.preview_center = ((left + right) / 2.0, (top + bottom) / 2.0)
        self.preview_zoom_factor = min(100.0, max(0.2, 0.9 * min(
            (width - 80) / selected_width, (height - 80) / selected_height) / base_scale))
        self._draw_preview()

    def _draw_preview(self):
        if self.preview_canvas is None or self.preview_profile is None:
            return
        args, profile = self.preview_profile
        canvas = self.preview_canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        domain_x_min, domain_x_max = args.domain_x_min, args.domain_x_max
        domain_y_min, domain_y_max = -args.domain_y, args.domain_y
        base_scale = min((width - 80) / (domain_x_max - domain_x_min),
                         (height - 80) / (domain_y_max - domain_y_min))
        scale = base_scale * self.preview_zoom_factor
        center_x, center_y = self.preview_center
        def point(x, y):
            return width / 2.0 + (x - center_x) * scale, height / 2.0 - (y - center_y) * scale
        canvas.create_rectangle(*point(domain_x_min, domain_y_max),
                                *point(domain_x_max, domain_y_min), outline="#777", width=2)
        canvas.create_text(45, 45, text="Xmin=%.4g m, Xmax=%.4g m, Y=±%.4g m" %
                           (domain_x_min, domain_x_max, args.domain_y), anchor="nw", fill="#555")
        cx, cy = point(0, 0)
        ami_r = args.ami_diameter * scale / 2.0
        canvas.create_oval(cx - ami_r, cy - ami_r, cx + ami_r, cy + ami_r,
                           outline="#e67e22", width=2, dash=(5, 3))
        canvas.create_line(*point(domain_x_min, 0), *point(domain_x_max, 0),
                           fill="#3498db", arrow="last")
        canvas.create_line(*point(0, domain_y_min), *point(0, domain_y_max),
                           fill="#2c3e50", arrow="last")
        canvas.create_text(point(domain_x_max, 0), text="X / 来流方向", anchor="e", fill="#3498db")
        canvas.create_text(point(0, domain_y_max), text="Y", anchor="n", fill="#2c3e50")
        canvas.create_text(cx + ami_r + 6, cy, text="AMI Ø=%.4g m" % args.ami_diameter,
                           anchor="w", fill="#e67e22")
        canvas.create_text(cx, cy + 14, text="转子 Ø=%.4g m" % (2 * args.rotor_radius),
                           anchor="n", fill="#c0392b")

        def blade_points(angle):
            theta = math.radians(angle)
            cp, sp = math.cos(theta), math.sin(theta)
            radial = (cp, sp)
            tangential = (-sp, cp)
            pitch = math.radians(args.pitch_deg)
            chord_dir = (tangential[0] * math.cos(pitch) +
                         radial[0] * math.sin(pitch),
                         tangential[1] * math.cos(pitch) +
                         radial[1] * math.sin(pitch))
            normal_dir = (-tangential[0] * math.sin(pitch) +
                          radial[0] * math.cos(pitch),
                          -tangential[1] * math.sin(pitch) +
                          radial[1] * math.cos(pitch))
            result = []
            for x, y in profile:
                xx, yy = args.chord * x, args.chord * y
                result.append((args.rotor_radius * radial[0] +
                               xx * chord_dir[0] + yy * normal_dir[0],
                               args.rotor_radius * radial[1] +
                               xx * chord_dir[1] + yy * normal_dir[1]))
            return result

        for i in range(args.blade_count):
            blade_xy = blade_points(i * 360.0 / args.blade_count)
            blade = [point(x, y) for x, y in blade_xy]
            if len(blade) > 1:
                canvas.create_line(blade + [blade[0]], fill="#c0392b", width=3)
            if i == 0 and len(blade_xy) > 1:
                le_index = max(range(len(profile)), key=lambda index: profile[index][0])
                te_index = min(range(len(profile)), key=lambda index: profile[index][0])
                canvas.create_line(point(*blade_xy[le_index]),
                                   point(*blade_xy[te_index]), fill="#8e44ad",
                                   width=2, arrow="last")

        if self.preview_box is not None:
            canvas.create_rectangle(*self.preview_box, outline="#2980b9", width=2, dash=(4, 2))

    def _make_args(self):
        required = ("airfoil", "output")
        for key in required:
            if not self.variables[key].get().strip():
                raise ValueError("请填写%s。" % ("翼型坐标文件" if key == "airfoil" else "输出案例目录"))

        def number(key):
            try:
                return float(self.variables[key].get())
            except ValueError as error:
                raise ValueError("参数 %s 必须是数字。" % key) from error

        def integer(key):
            value = number(key)
            if value < 1 or value != int(value):
                raise ValueError("参数 %s 必须是正整数。" % key)
            return int(value)

        positive_keys = ("rotor_radius", "chord", "shaft_radius", "height", "rpm",
                         "domain_y", "ami_diameter")
        values = {key: number(key) for key in (
            "rotor_radius", "chord", "pitch_deg", "shaft_radius", "height",
            "rpm", "inlet_velocity", "start_time", "end_time", "delta_t",
            "write_interval", "domain_x_min", "domain_x_max", "domain_y",
            "ami_diameter")}
        for key in ("delta_t", "write_interval"):
            if values[key] <= 0:
                raise ValueError("参数 %s 必须大于 0。" % key)
        if values["end_time"] <= values["start_time"]:
            raise ValueError("模拟终点 endTime 必须大于模拟起点 startTime。")
        for key in positive_keys:
            if values[key] <= 0:
                raise ValueError("参数 %s 必须大于 0。" % key)
        values.update({key: integer(key) for key in (
            "blade_count", "mesh_x", "mesh_y", "blade_refinement", "ami_refinement")})
        if values["domain_x_max"] <= values["domain_x_min"]:
            raise ValueError("计算域 Xmax 必须大于 Xmin。")
        if not self.custom_domain.get():
            diameter = 2.0 * values["rotor_radius"]
            values["domain_x_min"] = -5.0 * diameter
            values["domain_x_max"] = 20.0 * diameter
            values["domain_y"] = 3.5 * diameter

        parser = argparse.Namespace(
            airfoil=self.variables["airfoil"].get().strip(),
            output=self.variables["output"].get().strip(),
            custom_domain=self.custom_domain.get(),
            **values
        )
        return parser

    def _generate_worker(self, args):
        try:
            output = generate(args)
        except Exception as error:
            self.after(0, self._generation_failed, error)
            return
        self.after(0, self._generation_succeeded, output)

    def _generation_succeeded(self, output):
        self.status.configure(text="生成完成")
        self.generate_button.configure(state="normal")
        self._append_log("完成：%s" % output)
        self._append_log("请在 Linux + OpenFOAM 5.x 中执行 ./Allrun")
        messagebox.showinfo("生成完成", "OpenFOAM 案例已生成：\n%s" % output)

    def _generation_failed(self, error):
        self.status.configure(text="生成失败")
        self.generate_button.configure(state="normal")
        self._append_log("错误：%s" % error)
        messagebox.showerror("生成失败", str(error))


if __name__ == "__main__":
    VAWTGeneratorGUI().mainloop()
