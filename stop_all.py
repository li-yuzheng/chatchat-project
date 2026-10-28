"""停止 Chatchat 服务 —— 结束占用 7861 / 8501 端口的进程。

用途：解决 "Port 8501 is already in use" / "[Errno 10048] error while attempting to bind"。
"""

import subprocess
import sys

from _env import API_PORT, WEBUI_PORT, is_listening, port_owner


def kill_port(port, what):
    if not is_listening(port):
        print("  %-6s 端口 %d 空闲" % (what, port))
        return
    pid = port_owner(port)
    if not pid:
        print("  %-6s 端口 %d 被占用，但查不到 PID" % (what, port))
        return
    r = subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    if r.returncode == 0:
        print("  %-6s 端口 %d 已释放（已结束 PID %s）" % (what, port, pid))
    else:
        print("  %-6s 端口 %d 结束失败（PID %s），请用管理员权限运行" % (what, port, pid))


def main():
    print("正在停止 Chatchat 服务 ...")
    for port, what in ((API_PORT, "API"), (WEBUI_PORT, "WebUI")):
        kill_port(port, what)

    # streamlit 有时不占端口但进程残留，顺手清掉
    r = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq streamlit.exe", "/FO", "CSV"],
        capture_output=True, text=True, errors="ignore",
    )
    if "streamlit.exe" in (r.stdout or "").lower():
        subprocess.run(["taskkill", "/F", "/IM", "streamlit.exe"], capture_output=True)
        print("  已清理残留的 streamlit.exe")

    print("完成。")


if __name__ == "__main__":
    sys.exit(main())
