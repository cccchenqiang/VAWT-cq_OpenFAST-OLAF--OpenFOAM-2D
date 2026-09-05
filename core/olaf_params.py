# -*- coding: utf-8 -*-
"""OLAF 涡模型参数推荐。

移植自 openfast_toolbox.modules.olaf.OLAFParams（v4.2.0），
用于在 GUI 中根据当前模拟文件（转速 / 风速 / 半径）快速推导
OLAF 的推荐时间步与尾迹网格参数。纯 numpy 实现，不依赖外部包。
"""
import numpy as np


def olaf_params(omega_rpm, U0, R,
                a=0.3, aScale=1.2,
                deltaPsiDeg=6, nPerRot=None,
                targetFreeWakeLengthD=1, targetWakeLengthD=4.,
                nNWrot=8, nNWrotFree=1, nFWrot=0, nFWrotFree=0,
                dt_glue_code=None):
    """计算 OLAF 推荐的时间步与尾迹网格参数。

    参数含义与 openfast_toolbox.modules.olaf.OLAFParams 一致：
      - omega_rpm      : 风轮转速 [RPM]
      - U0             : 平均风速 [m/s]
      - R              : 风轮半径 [m]
      - deltaPsiDeg    : 方位角离散步长 [deg]（默认 6，即每转 60 步）
      - nPerRot        : 每转时间步数（与 deltaPsiDeg 二选一）
      - a / aScale     : 轴向诱导因子 / 放大系数（尾迹对流速度 Uc=U0(1-aScale*a)）
      - targetFreeWakeLengthD / targetWakeLengthD : 自由近尾迹 / 总尾迹长度 [D]
      - nNWrot / nNWrotFree / nFWrot / nFWrotFree : 近尾迹 / 自由近尾迹 / 远尾迹 / 自由远尾迹圈数
      - dt_glue_code   : 胶水代码（外部）时间步，给定时会把 dt 圆整为其整数倍

    返回 dict：dt_fvw, nPerRot, nNWPanels, nNWPanelsFree, nFWPanels,
              nFWPanelsFree, tMin, transient_rot。
    若输入无法计算（R/U0 非法）返回 None。
    """
    omega_rpm = float(omega_rpm)
    U0 = float(U0)
    R = float(R)
    if omega_rpm <= 0 or R <= 0:
        return None
    Uc = U0 * (1 - aScale * a)
    if Uc <= 1e-9:
        return None

    omega = omega_rpm * 2 * np.pi / 60
    T = 2 * np.pi / omega

    # --- 时间步 ---
    if nPerRot is not None:
        dt_wanted = np.around(T / nPerRot, 5)
        deltaPsiDeg = np.around(omega * dt_wanted * 180 / np.pi, 2)
    else:
        dt_wanted = np.around(deltaPsiDeg / (6 * omega_rpm), 5)
        nPerRot = int(2 * np.pi / (deltaPsiDeg * np.pi / 180))
    if dt_glue_code is not None and dt_glue_code > 0:
        dt_rounded = round(dt_wanted / dt_glue_code) * dt_glue_code
        deltaPsiDeg = np.around(omega * dt_rounded * 180 / np.pi, 2)
        dt_fvw = dt_rounded
        nPerRot = int(2 * np.pi / (deltaPsiDeg * np.pi / 180))
    else:
        dt_fvw = dt_wanted

    # --- 尾迹长度 ---
    targetWakeLength = targetWakeLengthD * 2 * R
    nAWPanels_FromU0 = int(targetWakeLength / (Uc * dt_fvw))
    targetFreeWakeLength = targetFreeWakeLengthD * 2 * R
    nNWPanelsFree_FromU0 = int(targetFreeWakeLength / (Uc * dt_fvw))
    nNWPanelsFree_FromRot = int(nNWrotFree * nPerRot)
    nFWPanels = int(nFWrot * nPerRot)
    nFWPanelsFree = int(nFWrotFree * nPerRot)
    nAWPanels_FromRot = int(nNWrot * nPerRot)

    nAWPanels = max(nAWPanels_FromRot, nAWPanels_FromU0)
    nNWPanelsFree = max(nNWPanelsFree_FromRot, nNWPanelsFree_FromU0)
    nNWPanels = nAWPanels - nFWPanels
    if nNWPanelsFree > nNWPanels:
        nNWPanelsFree = nNWPanels
    if nNWPanelsFree < nNWPanels and nFWPanelsFree > 0:
        nFWPanelsFree = 0

    tMin = 2 * dt_fvw * nAWPanels
    return dict(dt_fvw=float(dt_fvw),
                nPerRot=int(nPerRot),
                nNWPanels=int(nNWPanels),
                nNWPanelsFree=int(nNWPanelsFree),
                nFWPanels=int(nFWPanels),
                nFWPanelsFree=int(nFWPanelsFree),
                tMin=float(tMin),
                transient_rot=float(tMin / T))


def delta_psi_from_dt(omega_rpm, dt_fvw):
    """由转速 [RPM] 与 OLAF 时间步 [s] 反推方位角步长 [deg]：
    deltaPsi = omega_rad * dt * 180/pi。"""
    if omega_rpm <= 0:
        return 0.0
    omega = omega_rpm * 2 * np.pi / 60
    return float(omega * dt_fvw * 180 / np.pi)


def dt_from_delta_psi(omega_rpm, deltaPsiDeg):
    """由转速 [RPM] 与方位角步长 [deg] 计算 OLAF 时间步 [s]：
    dt = deltaPsi / (6 * rpm)。"""
    return float(deltaPsiDeg / (6 * omega_rpm))
