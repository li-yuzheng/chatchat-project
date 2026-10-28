"""RAG 全链路冒烟测试 —— 不依赖任何云厂商 Key。

它验证的是这条链路是否真的能跑通：

    kb_chat()
      -> KBServiceFactory.get_service_by_name()
      -> search_docs()            # FAISS 向量 + BM25 混合检索
      -> format_reference()       # 拼引用
      -> get_prompt_template()    # 取 rag prompt
      -> get_ChatOpenAI()         # 按平台配置创建客户端
      -> chain.ainvoke()          # 流式回调
      -> OpenAIChatOutput         # 组装成 OpenAI 格式返回

LLM 用本地桩服务（tools/mock_llm_server.py）代替，其余全部是项目真实代码。

运行：
    python tests/test_rag_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from _env import ensure_env  # noqa: E402

ensure_env()

# 本地请求不要走系统代理
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
    os.environ.pop(_k, None)
os.environ["no_proxy"] = "127.0.0.1,localhost"

MOCK_PORT = 7999
KB_NAME = "samples"


def start_mock_server():
    from tools.mock_llm_server import Handler

    srv = ThreadingHTTPServer(("127.0.0.1", MOCK_PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def register_mock_platform():
    """运行期往配置里塞一个 mock 平台，不改动磁盘上的 yaml。

    注意：Settings 是 pydantic-settings + 文件 mtime 缓存，每次访问属性都可能
    重新从 yaml 加载并把运行期改动冲掉。所以要先关掉 auto_reload 再改。
    """
    from chatchat.settings import PlatformConfig, Settings

    ms = Settings.model_settings
    ms.auto_reload = False  # 关掉「按文件 mtime 自动重载」，否则下面的 append 会被丢弃
    ms.MODEL_PLATFORMS = [
        p for p in ms.MODEL_PLATFORMS if p.platform_name != "mock"
    ] + [
        PlatformConfig(**{
            "platform_name": "mock",
            "platform_type": "custom openai",
            "api_base_url": f"http://127.0.0.1:{MOCK_PORT}/v1",
            "api_key": "EMPTY",
            "llm_models": ["mock-chat"],
        })
    ]


async def run_once(query: str) -> dict:
    from chatchat.server.chat.kb_chat import kb_chat

    raw = await kb_chat(
        query=query,
        mode="local_kb",
        kb_name=KB_NAME,
        top_k=3,
        score_threshold=2.0,
        history=[],
        stream=False,
        model="mock-chat",
        temperature=0.7,
        max_tokens=200,
        prompt_name="default",
        return_direct=False,
        request=None,
    )
    return json.loads(raw)


def main() -> int:
    print("=" * 70)
    print("RAG 全链路冒烟测试")
    print("=" * 70)

    srv = start_mock_server()
    print(f"[1/4] 桩 LLM 已启动     http://127.0.0.1:{MOCK_PORT}/v1")

    register_mock_platform()
    from chatchat.server.utils import get_config_models, get_model_info

    models = list(get_config_models(model_type="llm", platform_name="mock").keys())
    info = get_model_info("mock-chat")
    print(f"[2/4] 平台注册成功      models={models} base_url={info.get('api_base_url')}")
    if not models:
        print("      ✗ 平台未生效")
        return 1

    from chatchat.server.knowledge_base.kb_service.base import KBServiceFactory

    kb = KBServiceFactory.get_service_by_name(KB_NAME)
    if kb is None:
        print(f"      ✗ 知识库 {KB_NAME} 不存在，请先执行 chatchat kb -r")
        return 1
    print(f"[3/4] 知识库就绪        {KB_NAME}  向量库={kb.vs_type()}  向量模型={kb.embed_model}")

    query = "大模型推理优化有哪些策略？"
    print(f"[4/4] 发起 RAG 查询     {query}")
    try:
        result = asyncio.run(run_once(query))
    finally:
        srv.shutdown()

    content = ""
    if result.get("choices"):
        content = result["choices"][0]["message"].get("content") or ""
    # 非流式返回不带 docs（只有首次流式分片才带），所以这里从回答里
    # 反查是否真的拼进了检索到的上下文 —— 桩服务会把 prompt 原样回显。
    docs = result.get("docs") or []
    print("-" * 70)
    print(f"返回字段：{sorted(result.keys())}")
    print(f"命中文档数（非流式不返回，属正常）：{len(docs)}")
    print(f"模型回答（前 300 字）：{content[:300]}")
    print("-" * 70)

    ok = bool(content) and "【已知信息】" in content and "BM25" in content
    if ok:
        print("✓ 通过：检索 -> 拼装 -> 调用 -> 返回 全链路正常")
        print("  说明：桩 LLM 把收到的 prompt 原样回显，能看到【已知信息】和命中的 BM25")
        print("       片段，就证明检索结果确实被拼进了提示词。")
    else:
        print("✗ 失败：回答里没有检索到的上下文")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
