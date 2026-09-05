# pytoolbox — VAWT + OLAF (AeroDyn Driver) 仿真工具箱（GUI）

本目录是 OpenFAST 工具与 OpenFOAM VAWT 案例生成器的隔离整合项目。它在原有
OpenFAST 四个页面之外增加“⑤ OpenFOAM 案例”页面；原始
`pytoolbox` 和 OpenFOAM 模板目录不会被运行时修改。

OpenFOAM 页面负责参数校验、翼型/STL/字典生成、模拟预览和案例日志管理。预览支持
计算域、AMI、转子/叶片显示，鼠标滚轮缩放和左键拖动平移。计算域与 AMI 默认按
转子直径自动设置；只有勾选“启用自定义计算域和 AMI 直径”后才能编辑这些字段。
生成的案例可在
Linux 或 WSL 中执行 `Allrun`；Windows 本机没有 OpenFOAM 时，程序只报告运行环境
不可用，不会把“案例生成”误报为“求解完成”。OpenFAST 与 OpenFOAM 目前通过显式
参数映射协作，不构成强耦合求解流程。

新增核心位于 `core/openfoam/`，页面位于 `frontend/pages/page_openfoam.py`，
模板位于 `templates/openfoam_vawt/`。运行整合测试：

```bat
python -m unittest tests.test_openfoam
```

面向**垂直轴风轮 (VAWT) + AeroDyn Driver + OLAF 自由涡尾迹**的轻量图形化工具：

- 输入 **6 个文件**（`ad_driver.dvr`、`AD.dat`、`AD_blade.dat`、`NACA_0018_Coords.txt`、
  `OLAF.dat`、`Polars.dat`），**支持"选择文件夹自动匹配"**（按文件名关键词自动识别
  6 类输入文件，匹配后仍可手动调整），解析并**可视化风轮几何**（坐标系、叶片翼型截面、
  转轴、塔筒、方位角旋转）；
- **单工况 / 批量工况**（风速×转速全组合或按位对应）生成与调用
  `AeroDyn_Driver_x64.exe` 运行；
- **结果处理**：读取 `.out` 结果 → 稳态统计（P / Cp / TSR / DEL）→ 多种可视化
  （时间序列、攻角-方位角、展向分布、翼型极线、批量功率曲线）；
- **输出通道以 `AD.dat` 的 `OutList` / `OutListAD` 段为准**（可增删、可上下移），
  OpenFAST 官方 **`OutListParameters.xlsx` 仅作参考**：用于按关键词检索可用通道名、
  查看单位/描述，不直接作为输出列表。

---

## 1. 环境

**直接用已有的 `weis2-env` 环境**，无需新建 `pytoolbox` 环境（条件句"没有才新建"未触发）：

```text
D:\ProgramData\miniforge3\envs\weis2-env\python.exe
```

已含：`numpy / pandas / scipy / matplotlib / openpyxl / PySide6`。

> ⚠️ **openfast_toolbox**：`weis2-env` 里只有配套包 `openfast_io`/`pyOpenFAST`，
> 没有 `openfast_toolbox` 本体（用户指定"主文件夹"源码为
> `D:\1worksfiles\py\github\openfast_toolbox-4.2.0`）。程序入口 `main.py` 已自动把该目录
> 加入 `sys.path`；若不希望依赖它，结果读取会自动回退到内置 ASCII 解析（列名格式已统一为
> `Name_[unit]`）。

> ⚠️ **OpenBLAS**：本机 `numpy` 多线程初始化会内存分配失败，入口已强制
> `OPENBLAS_NUM_THREADS=1`（须在 import numpy 之前，已在 `main.py` 顶部处理）。

## 2. 运行

双击 `run.bat`，或在命令行：

```bat
D:\ProgramData\miniforge3\envs\weis2-env\python.exe D:\1worksfiles\py\github\pytoolbox\main.py
```

## 3. 界面四个页面

| 页面 | 功能 |
|---|---|
| ① 输入文件 | **选择文件夹自动匹配 6 个输入文件**（或逐个手动选择）、加载解析；加载 `OutListParameters.xlsx` 输出参数表 |
| ② 风轮几何 | 3D 显示坐标系/翼型/转轴/轮毂/塔筒，方位角滑条旋转（**坐标轴范围固定**，旋转时视图不缩放跳动），几何参数摘要 |
| ③ 工况设置 | 单工况参数（U0/RPM/TMax/DT/桨距/偏航/输出格式/Driver VTK）→ 独立的 OLAF 尾迹 VTK（WrVTk、nVTKBlades、VTKCoord、VTK_fps、nGridOut）→ 输出通道编辑 → 批量工况 → 运行与汇总 |
| ④ 结果处理 | 加载 `.out/.outb`、通道选择、统计（P/Cp/TSR/DEL）、时间序列/攻角-方位角/展向/极线/功率曲线 |

## 4. 目录结构（模块化，前端独立）

```
pytoolbox/
├─ main.py                 # 入口（环境变量、路径注入、启动 GUI）
├─ run.bat                 # Windows 启动脚本
├─ requirements.txt
├─ core/                   # 后端核心（纯逻辑，不依赖 GUI）
│  ├─ models/              #   数据模型：Turbine / Blade / Airfoil / VAWTModel
│  ├─ parsers/             #   6 个输入文件的轻量解析器（各自独立）
│  ├─ geometry/            #   几何构建 + 3D 绘图
│  ├─ outlist.py           #   OutListParameters.xlsx 通道表读取/检索
│  ├─ cases/               #   单工况/批量工况生成（含 OLAF 文本级改写）
│  ├─ runner/              #   调用 AeroDyn Driver 可执行文件
│  └─ postprocess/         #   结果读取、统计、可视化
├─ frontend/               # GUI 层（PySide6）
│  ├─ main_window.py       #   主窗口（QTabWidget 四页共享模型）
│  ├─ pages/               #   四个页面（输入/几何/工况/结果）
│  └─ widgets/             #   可复用控件（matplotlib 画布、文件选择、通道对话框）
├─ assets/                 # 静态资源（预留）
└─ tests/                  # 测试：test_core / test_cases / test_gui
```

`core` 与 `frontend` 完全分离：前端只通过 `VAWTModel` 与 `core.*` 的公开函数交互，
可以独立替换前端（如改 Web/CLI）而不动后端。

### 4.1 批量工况与单工况的关系

**批量工况是以"单工况"参数为模板生成的**：

- 在「③ 工况设置」页先把**单工况**设好（U0、RPM、TMax、DT、桨距、偏航、输出通道、
  OLAF 快速网格开关、VTK 开关等）；
- 批量工况只**覆盖两个变量**：来流风速 `U0` 与转子转速 `RPM`（可选全组合 `U0 × RPM`
  或按位一一对应），其余全部继承单工况设置；
- 每个批量工况在独立子目录 `case_{u0}_{rpm}/` 下生成**同一套** 6 个输入文件
  （按各自风速/转速改写），并分别调用 `AeroDyn_Driver_x64.exe`；
- 批量结果可汇总出功率曲线（P–U0、Cp–TSR）。

### 4.2 几何与坐标系约定（AeroDyn Driver）

程序按 AeroDyn Driver 手册与 windspire 案例校验：

- **全局坐标系 (i)**：画在塔基 `BaseOriginInit`（惯性系，X 顺风、Y 左侧、Z 向上）；
- **轮毂坐标系 (h)**：原点在 `NacOrigin_t + HubOrigin_n`，`x_h` 对齐转轴
  （VAWT 中竖直），图中以 `x_h / y_h / z_h` 标注；
- **欧拉角统一按 AeroDyn/NWTC 的 1-2-3 序列** `R = Rx·Ry·Rz`（θx、θy、θz 依次对应
  `azimuth / precone / pitch`）；
- **叶片展向沿 blade 系 z 轴**，故 windspire 案例中三叶片竖直（沿 `z` 轴）、
  原点分布在半径 0.61 m 的圆周上、间隔 120°。

## 5. 运行与验证测试

```bat
D:\ProgramData\miniforge3\envs\weis2-env\python.exe tests\test_core.py
D:\ProgramData\miniforge3\envs\weis2-env\python.exe tests\test_cases.py
D:\ProgramData\miniforge3\envs\weis2-env\python.exe tests\test_gui.py
```

已覆盖：6 文件解析、几何构建与 3D 绘图、结果读取与统计（P=279.5W、Cp=0.1217，
与参考结果一致）、OutList 通道重写、批量工况生成、runner 调用、GUI 启动。

## 6. 已知限制

- **OLAF 计算较慢**：单核 Fortran 求解器，488 面板约 25–40 分钟/1s 仿真；建议先用
  "快速网格 + TMax 较短"验证流程，再跑正式工况。程序默认 `WrVTk=0`、`nGridOut=0` 提速。
- 塔筒仅当 `AD.dat` 中 `NumTwrNds>0` 且 driver 中 `HasTower=True` 时显示。
- 批量运行使用线程池并行，但多个 OLAF 进程同时跑会显著提高内存占用，注意 `n_cores`。
