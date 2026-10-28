"""运行环境自检 —— 所有 run_*.py 的第一行都先调用 ensure_env()。

作用有两件事：
1. 设好 CHATCHAT_ROOT、切换工作目录、把数据目录加进 sys.path。
2. 如果当前解释器里 import 不到 chatchat（典型情况：PyCharm 用成了系统
   Python D:\\python），自动用 conda 环境 chatchat 的解释器重新拉起本脚本，
   这样即使解释器选错也能正常跑起来。
"""

import os
import subprocess
import sys

CHATCHAT_ROOT = r"D:\chatchat-data"
CONDA_PYTHON = r"D:\miniconda\envs\chatchat\python.exe"
_REEXEC_FLAG = "CHATCHAT_REEXEC"

# 本文件所在目录 = 项目目录（run_*.py 都在这），用它定位脚本，
# 避免 ensure_env() 已经 chdir 到数据目录后 abspath 解析错地方。
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 可编辑源码目录：src\chatchat 就是运行时真正加载的代码。
# 设 CHATCHAT_USE_SRC=0 可退回 site-packages 里的原始包做对照实验。
SRC_DIR = os.path.join(_PROJECT_DIR, "src")


def _load_dotenv():
    """.env 里的 KEY=VALUE 灌进 os.environ，**覆盖**同名系统变量。

    为什么是覆盖而不是 setdefault：项目级配置应当优先于全局配置。
    典型场景是系统里留着一个过期的 DEEPSEEK_API_KEY，而项目想用新的 key——
    如果这里不覆盖，改 .env 就毫无效果，排查起来非常费劲（踩过）。

    项目里不引入 python-dotenv 依赖，这里用 20 行解析够了：支持 # 注释、
    空行、KEY=VALUE、以及两侧的引号。
    """
    path = os.path.join(_PROJECT_DIR, ".env")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k:
                    os.environ[k] = v
    except OSError:
        pass


def _bootstrap():
    """设环境变量、切目录、补 sys.path。"""
    os.environ.setdefault("CHATCHAT_ROOT", CHATCHAT_ROOT)
    _load_dotenv()
    if not os.path.isdir(CHATCHAT_ROOT):
        sys.exit(
            "[环境自检] 数据目录不存在：%s\n"
            "如果目录被移动过，请修改 _env.py 里的 CHATCHAT_ROOT。" % CHATCHAT_ROOT
        )
    # 优先加载项目里的可编辑源码（src/chatchat），这样改代码即时生效，
    # 不用重新 pip install，也不会被 site-packages 里的旧包覆盖。
    if os.environ.get("CHATCHAT_USE_SRC", "1") != "0" and os.path.isdir(os.path.join(SRC_DIR, "chatchat")):
        if SRC_DIR not in sys.path:
            sys.path.insert(0, SRC_DIR)
    try:
        os.chdir(CHATCHAT_ROOT)
    except OSError as e:
        sys.exit("[环境自检] 无法切换到数据目录 %s：%s" % (CHATCHAT_ROOT, e))
    if CHATCHAT_ROOT not in sys.path:
        sys.path.insert(0, CHATCHAT_ROOT)


def _importable():
    try:
        import chatchat  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def _same_python(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def ensure_env():
    _bootstrap()
    if _importable():
        return

    # 已经在正确解释器里却还是 import 失败 —— 说明环境被弄坏了，直接把真实报错抛出去
    if _same_python(sys.executable, CONDA_PYTHON) or os.environ.get(_REEXEC_FLAG):
        print("=" * 68, file=sys.stderr)
        print("[环境自检] 已在 chatchat 环境里运行，但仍然 import 不到 chatchat。", file=sys.stderr)
        print("解释器：%s" % sys.executable, file=sys.stderr)
        print("请重装：", file=sys.stderr)
        print('  "%s" -m pip install --reinstall --no-deps '
              '"D:\\chatchat-tmp\\langchain_chatchat-0.3.1.3-py3-none-any.whl"' % CONDA_PYTHON,
              file=sys.stderr)
        print("=" * 68, file=sys.stderr)
        import chatchat  # noqa: F401  触发原始报错，保留完整 traceback
        return

    # 解释器选错了，改用 conda 环境的 python 重启本脚本
    if not os.path.isfile(CONDA_PYTHON):
        sys.exit(
            "[环境自检] 找不到 chatchat 环境：%s\n"
            "请先创建它（详见 README.md 第一节）。" % CONDA_PYTHON
        )

    script = os.path.join(_PROJECT_DIR, os.path.basename(sys.argv[0]))
    if not os.path.isfile(script):
        script = os.path.join(_PROJECT_DIR, "run_all.py")
    debugging = sys.gettrace() is not None or any("pydevd" in m for m in sys.modules)

    print("=" * 68)
    print("[环境自检] 当前解释器里没有 chatchat，正在自动切换。")
    print("  当前解释器：%s" % sys.executable)
    print("  切换为    ：%s" % CONDA_PYTHON)
    if debugging:
        print("  注意：调试器不会跟着切换，断点将无法命中。")
        print("        要在 PyCharm 里断点调试，请按 README.md 第二节改解释器。")
    print("=" * 68, flush=True)

    env = dict(os.environ)
    env[_REEXEC_FLAG] = "1"
    env["CHATCHAT_ROOT"] = os.environ.get("CHATCHAT_ROOT", CHATCHAT_ROOT)
    env.pop("PYTHONPATH", None)
    try:
        rc = subprocess.call([CONDA_PYTHON, script] + sys.argv[1:], env=env)
    except KeyboardInterrupt:
        rc = 0
    sys.exit(rc)


# --------------------------------------------------------------------------
# 端口工具：避免再出现 "Port 8501 is already in use" 这种看不懂的报错
# --------------------------------------------------------------------------

API_PORT = 7861
WEBUI_PORT = 8501


def is_listening(port, host="127.0.0.1"):
    """端口上是否已经有服务在监听。"""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def port_owner(port):
    """查出占用端口的进程 PID（Windows 下解析 netstat）。"""
    try:
        # 注意：Windows 的 netstat 输出是 GBK，必须按字节读再容错解码，
        # 否则 text=True（UTF-8）会抛 UnicodeDecodeError 导致拿到 None。
        raw = subprocess.run(["netstat", "-ano"], capture_output=True, timeout=20).stdout or b""
        out = raw.decode("utf-8", "replace")
    except Exception:
        return None
    if out is None:
        return None
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local, pid = parts[1], parts[-1]
        if local.endswith(":%d" % port):
            return pid
    return None


def require_free(port, what):
    """端口被占时打印人话并退出。"""
    if not is_listening(port):
        return
    pid = port_owner(port)
    print("=" * 68, file=sys.stderr)
    print("[启动检查] %s 端口 %d 已被占用，无法启动。" % (what, port), file=sys.stderr)
    if pid:
        print("  占用进程 PID：%s    （查看：tasklist /FI \"PID eq %s\"）" % (pid, pid), file=sys.stderr)
    print("  处理办法（任选一条）：", file=sys.stderr)
    print("    1. 在原来那个运行窗口按红色方块 Stop", file=sys.stderr)
    print("    2. 双击 D:\\chatchat-project\\停止-Chatchat.bat", file=sys.stderr)
    print("    3. 任务管理器结束残留的 python.exe / streamlit.exe", file=sys.stderr)
    print("=" * 68, file=sys.stderr)
    sys.exit(1)


def warn_if_api_down():
    """WebUI 需要 API 提供数据，API 没起来时给个提示（不阻止启动）。"""
    if is_listening(API_PORT):
        return
    print("=" * 68, file=sys.stderr)
    print("[启动检查] API（7861）没有在运行，WebUI 页面能打开但拿不到数据。", file=sys.stderr)
    print("  请另开一个窗口先运行 run_api.py。", file=sys.stderr)
    print("=" * 68, file=sys.stderr)

