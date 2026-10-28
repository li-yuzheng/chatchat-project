"""一键启动 API + WebUI —— 等价于命令行 `chatchat start -a`

注意：startup 会用 multiprocessing(spawn) 起两个子进程，
所以在这个脚本里打断点只能命中启动阶段，命中不了业务代码。
调业务代码请用 run_api.py / run_webui.py。
"""

import sys

from _env import ensure_env, require_free, API_PORT, WEBUI_PORT

ensure_env()  # 环境变量 / 工作目录 / 解释器自检，必须在 import chatchat 之前
require_free(API_PORT, "API")
require_free(WEBUI_PORT, "WebUI")

from chatchat.cli import main

if __name__ == "__main__":
    sys.argv = ["chatchat", "start", "-a"]
    main()
