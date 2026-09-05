# -*- coding: utf-8 -*-
"""运行器：调用 AeroDyn Driver / OpenFAST 可执行程序运行工况。"""
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor


def run_aerodyn_driver(work_dir, exe, parallel=False, n_cores=None, wait=True,
                       show=False, dvr='ad_driver.dvr'):
    """在工况目录中运行 AeroDyn Driver。返回 subprocess.CompletedProcess。"""
    if not os.path.isfile(exe):
        raise FileNotFoundError(f'AeroDyn Driver 可执行文件不存在: {exe}')
    cmd = [exe, dvr]
    if wait:
        return subprocess.run(cmd, cwd=work_dir, capture_output=not show,
                              text=True, timeout=None)
    return subprocess.Popen(cmd, cwd=work_dir)


def run_many(dirs, exe, n_cores=None, show=False):
    """并行运行多个工况目录（每个目录里调用同一 exe）。返回状态列表。"""
    n_cores = n_cores or min(len(dirs), os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=n_cores) as pool:
        futures = {pool.submit(run_aerodyn_driver, d, exe, show=show): d for d in dirs}
        results = []
        for fut in futures:
            results.append((futures[fut], fut.result()))
    return results
