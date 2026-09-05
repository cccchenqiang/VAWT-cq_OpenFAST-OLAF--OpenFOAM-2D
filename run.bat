@echo off
REM ============================================================
REM  pytoolbox 启动脚本（VAWT + OLAF / AeroDyn Driver 仿真工具箱）
REM  使用已有的 weis2-env 环境（无需新建 pytoolbox 环境）
REM ============================================================
setlocal
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
"D:\ProgramData\miniforge3\envs\weis2-env\python.exe" "%~dp0main.py"
endlocal
