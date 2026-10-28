"""一键启动 API + WebUI —— 但**不是**简单转调 `chatchat start -a`。

为什么不用官方那套：
`chatchat start -a` 内部用 multiprocessing(spawn) 起两个子进程。spawn 出来的
进程不继承父进程往 sys.path 里插的 src 目录，也不走我们的环境自检，结果就是
WebUI 经常起不来却一声不响（实测 8501 始终不监听，连 logs 目录都没生成），
而 API 却是好的 —— 排查成本极高。

所以这里改成显式 subprocess 起 run_api.py / run_webui.py：
  1. 两个服务是独立进程，一个挂了另一个还在，报错也看得清；
  2. 走的是同一套 ensure_env，源码模式 / 环境变量 / 端口检查完全一致；
  3. Ctrl+C（或任一进程异常退出）会把另一个一起带走，不留僵尸进程。

代价：断点仍然只挂在各自进程里。要调业务代码请直接跑 run_api.py /
run_webui.py，别用本脚本。
"""

import os
import subprocess
import sys
import time

from _env import (
    API_PORT,
    CONDA_PYTHON,
    WEBUI_PORT,
    ensure_env,
    is_listening,
    require_free,
)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WAIT_TIMEOUT = 180  # 秒；冷启动 + 首次加载 streamlit 大约 20~60 秒

ensure_env()  # 完成环境自检后，当前进程一定已经在 chatchat 环境里
require_free(API_PORT, "API")
require_free(WEBUI_PORT, "WebUI")

PYTHON = CONDA_PYTHON if os.path.isfile(CONDA_PYTHON) else sys.executable


def spawn(script):
    """在项目目录下拉起一个启动脚本，输出直接继承到当前终端。"""
    return subprocess.Popen([PYTHON, os.path.join(PROJECT_DIR, script)], cwd=PROJECT_DIR)


def stop_all(procs):
    """先 terminate 再兜底 kill，保证不留下占端口的残留进程。"""
    for p in procs.values():
        if p.poll() is None:
            p.terminate()
    for p in procs.values():
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


def wait_ports(procs, timeout=WAIT_TIMEOUT):
    """轮询端口直到两个都监听，或超时/子进程提前退出。返回是否全部就绪。"""
    pending = {"API": API_PORT, "WebUI": WEBUI_PORT}
    start = time.time()
    while pending and time.time() - start < timeout:
        for name, port in list(pending.items()):
            if is_listening(port):
                print("  [就绪] %-5s 127.0.0.1:%d（%.0f 秒）" % (name, port, time.time() - start), flush=True)
                pending.pop(name)
        if not pending:
            break
        for name, p in procs.items():
            if p.poll() is not None:
                print("[失败] %s 进程启动后退出（code=%s），请向上翻看它的报错。" % (name, p.returncode))
                return False
        time.sleep(2)
    if pending:
        print("[超时] %d 秒内未就绪：%s" % (timeout, "、".join(pending)))
        return False
    return True


def main():
    print("正在启动 Chatchat（API %d / WebUI %d）..." % (API_PORT, WEBUI_PORT), flush=True)
    procs = {"API": spawn("run_api.py"), "WebUI": spawn("run_webui.py")}

    try:
        if not wait_ports(procs):
            stop_all(procs)
            return 1
        print("=" * 68)
        print("  WebUI  ：http://127.0.0.1:%d" % WEBUI_PORT)
        print("  API 文档：http://127.0.0.1:%d/docs" % API_PORT)
        print("  停止：在本窗口按 Ctrl+C，或双击 停止-Chatchat.bat")
        print("=" * 68, flush=True)

        while True:
            for name, p in procs.items():
                rc = p.poll()
                if rc is not None:
                    print("[退出] %s 进程已结束（code=%s），正在停止另一个 ..." % (name, rc))
                    stop_all(procs)
                    return 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，正在停止 ...")
        stop_all(procs)
        print("已全部停止。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
