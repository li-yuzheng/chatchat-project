"""只启动 WebUI（单进程，streamlit 在主进程内执行页面脚本，可打断点）

端口见 basic_settings.yaml 的 WEBUI_SERVER，默认 127.0.0.1:8501
必须先跑 run_api.py，否则页面拿不到数据。
"""

from _env import ensure_env, require_free, warn_if_api_down, WEBUI_PORT

ensure_env()  # 环境变量 / 工作目录 / 解释器自检，必须在 import chatchat 之前
require_free(WEBUI_PORT, "WebUI")
warn_if_api_down()


class _DummyEvent:
    """run_webui 在 bootstrap.run 返回后会调用 started_event.set()，传 None 会抛异常。"""

    def set(self):
        pass


from chatchat.startup import run_webui

if __name__ == "__main__":
    run_webui(started_event=_DummyEvent())
