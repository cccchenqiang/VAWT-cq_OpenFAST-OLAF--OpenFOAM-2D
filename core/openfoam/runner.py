import shutil
import subprocess


def check_command(command):
    return shutil.which(command) is not None


def run_all(case_dir, command="bash", wait=True):
    case_dir = str(case_dir)
    if command == "bash" and not check_command(command):
        raise FileNotFoundError("未找到 bash；请配置 WSL/Linux 中的 OpenFOAM 运行命令")
    args = [command, "-lc", "./Allrun"]
    if wait:
        return subprocess.run(args, cwd=case_dir, capture_output=True, text=True)
    return subprocess.Popen(args, cwd=case_dir)
