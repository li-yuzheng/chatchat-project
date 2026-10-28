"""只启动 API 服务（单进程，可直接打断点调试）

端口见 basic_settings.yaml 的 API_SERVER，默认 127.0.0.1:7861
文档：http://127.0.0.1:7861/docs
"""

from _env import ensure_env, require_free, API_PORT

ensure_env()  # 环境变量 / 工作目录 / 解释器自检，必须在 import chatchat 之前
require_free(API_PORT, "API")

from chatchat.startup import run_api_server

if __name__ == "__main__":
    run_api_server()
