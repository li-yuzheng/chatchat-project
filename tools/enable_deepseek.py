"""把 DeepSeek 接入 Chatchat —— 一条命令改完配置，可重复执行。

用法：
    python tools\\enable_deepseek.py --api-key sk-xxxx        # 写入 .env 并注册平台
    python tools\\enable_deepseek.py                          # 沿用 .env 里已有的 key
    python tools\\enable_deepseek.py --set-default             # 顺便把 DeepSeek 设为默认模型
    python tools\\enable_deepseek.py --remove                  # 移除该平台

它做三件事：
1. 把 API Key 写进项目根目录的 .env（.env 已在 .gitignore 中，不会被提交）。
2. 在 D:\\chatchat-data\\model_settings.yaml 里注册 deepseek 平台，
   api_key 写的是占位符 ${DEEPSEEK_API_KEY}，由 settings.expand_env_vars 在加载时展开。
3. 可选地把 DEFAULT_LLM_MODEL 切成 deepseek-chat。

为什么不用明文写 key：model_settings.yaml 很容易被顺手提交进 git，
密钥一旦进历史就很难彻底清除。换成环境变量引用后，仓库里永远只有占位符。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 让脚本能 import 到项目根目录的 _env
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from _env import CHATCHAT_ROOT, ensure_env  # noqa: E402

ENV_FILE = PROJECT_DIR / ".env"
ENV_KEY = "DEEPSEEK_API_KEY"
CONFIG_FILE = Path(CHATCHAT_ROOT) / "model_settings.yaml"

DEEPSEEK_PLATFORM = {
    "platform_name": "deepseek",
    "platform_type": "deepseek",
    "api_base_url": "https://api.deepseek.com/v1",
    "api_key": "${%s}" % ENV_KEY,
    "api_proxy": "",
    "api_concurrencies": 5,
    "auto_detect_model": False,
    "llm_models": [
        "deepseek-chat",       # 通用对话（官方稳定别名）
        "deepseek-reasoner",   # 推理模型
        "deepseek-flash",      # 账号 /v1/models 实际返回
        "deepseek-v4-pro",
    ],
    "embed_models": [],
    "text2image_models": [],
    "image2text_models": [],
    "rerank_models": [],
    "speech2text_models": [],
    "text2speech_models": [],
}


def write_env(api_key: str) -> None:
    """把 key 写进 .env，保留文件里其它变量。"""
    lines = []
    if ENV_FILE.is_file():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    lines = [x for x in lines if not x.strip().startswith(ENV_KEY + "=")]
    lines.append("%s=%s" % (ENV_KEY, api_key))
    ENV_FILE.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print("[1/3] 已写入 %s（该文件已被 .gitignore 忽略）" % ENV_FILE)


def load_yaml():
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml, yaml.load(f)


def patch_config(set_default: bool) -> None:
    from ruamel.yaml.comments import CommentedMap

    yaml, data = load_yaml()
    platforms = [p for p in (data.get("MODEL_PLATFORMS") or []) if p.get("platform_name") != "deepseek"]
    platforms.append(CommentedMap(DEEPSEEK_PLATFORM))
    data["MODEL_PLATFORMS"] = platforms
    if set_default:
        data["DEFAULT_LLM_MODEL"] = "deepseek-chat"
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    print("[2/3] 已更新 %s" % CONFIG_FILE)
    print("      平台列表：%s" % [p.get("platform_name") for p in platforms])
    if set_default:
        print("      DEFAULT_LLM_MODEL = deepseek-chat")


def remove_platform() -> None:
    yaml, data = load_yaml()
    platforms = [p for p in (data.get("MODEL_PLATFORMS") or []) if p.get("platform_name") != "deepseek"]
    data["MODEL_PLATFORMS"] = platforms
    if data.get("DEFAULT_LLM_MODEL") in ("deepseek-chat", "deepseek-reasoner"):
        data["DEFAULT_LLM_MODEL"] = "qwen2.5:3b"
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    print("已移除 deepseek 平台，剩余：%s" % [p.get("platform_name") for p in platforms])


def verify() -> bool:
    """重新加载配置，确认模型能被解析到、key 能被展开。"""
    ensure_env()  # 补齐 sys.path / 工作目录，保证加载的是 src 里的源码

    from chatchat.server.utils import get_config_models, get_model_info

    models = list(get_config_models(model_type="llm", platform_name="deepseek").keys())
    info = get_model_info("deepseek-chat")
    key = info.get("api_key", "")
    print("[3/3] 配置自检")
    print("      可用模型：%s" % models)
    print("      base_url：%s" % info.get("api_base_url"))
    print("      api_key ：%s" % ("已展开，长度 %d" % len(key) if key else "空！请检查 .env"))
    if not models:
        print("      ✗ 没有解析到 deepseek 模型，请检查 model_settings.yaml")
        return False
    if not key:
        print("      ✗ API Key 未展开，请检查 .env 里的 %s" % ENV_KEY)
        return False
    print("      ✓ OK，重启服务后即可在 WebUI 的模型下拉框里看到 deepseek-chat")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="接入 DeepSeek")
    ap.add_argument("--api-key", default="", help="DeepSeek API Key，不填则沿用 .env 里的")
    ap.add_argument("--set-default", action="store_true", help="同时设为默认 LLM")
    ap.add_argument("--remove", action="store_true", help="移除 deepseek 平台")
    args = ap.parse_args()

    if not CONFIG_FILE.is_file():
        print("找不到配置文件 %s，请先执行 chatchat init" % CONFIG_FILE)
        return 1

    if args.remove:
        remove_platform()
        return 0

    if args.api_key:
        write_env(args.api_key)
    elif ENV_FILE.is_file() and ENV_KEY in ENV_FILE.read_text(encoding="utf-8"):
        print("[1/3] 沿用 %s 里已有的 %s" % (ENV_FILE, ENV_KEY))
    else:
        print("没有可用的 API Key。请用 --api-key sk-xxxx 传入，或先在 .env 里写 %s=..." % ENV_KEY)
        return 1

    patch_config(args.set_default)
    return 0 if verify() else 1


if __name__ == "__main__":
    sys.exit(main())
