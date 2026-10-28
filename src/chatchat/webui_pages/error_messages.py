"""中文错误提示：把底层异常翻译成「人话 + 处置建议」。

WebUI 面向用户的所有报错都走这里。上游（httpx / openai / FastAPI）抛出来的
英文异常原文人看不懂，直接 ``st.error(e.body)`` 有三类问题：

1. 只给英文细节，不给结论，用户不知道下一步该干什么；
2. ``e.body`` 并不是所有异常都有，遇到 ``TypeError`` 会二次崩溃；
3. 原始信息丢掉之后没法排障，所以这里保留一个「技术细节」折叠区。

对外只暴露三个函数：``describe`` / ``show_error`` / ``api_reachable``。
"""

from __future__ import annotations

import socket
from typing import Tuple
from urllib.parse import urlparse

import httpx
import openai
import streamlit as st

# 连接类异常的英文关键字（不同 httpx / openai 版本措辞不一致，靠关键字兜底）
_CONNECT_HINTS = (
    "connection refused",
    "no connection could be made",
    "actively refused",
    "connect error",
    "failed to establish",
    "getaddrinfo",
    "name or service not known",
    "nodename nor servname",
    "econnrefused",
    "connection reset",
    "connection aborted",
    "10061",
)

_TIMEOUT_HINTS = ("timed out", "timeout", "read timeout", "connect timeout")


def api_reachable(base_url: str, timeout: float = 1.5) -> bool:
    """探测后端 API 端口是否可连接（只做 TCP 握手，不依赖具体接口）。"""
    try:
        parsed = urlparse(base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _raw_detail(exc: Exception) -> str:
    """尽量把原始返回体挖出来，用于折叠区展示。"""
    body = getattr(exc, "body", None)
    if body not in (None, "", {}):
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("msg") or body
            return f"{exc}\n\n返回体：{detail}"
        return f"{exc}\n\n返回体：{body}"
    return str(exc)


def describe(exc: Exception, action: str = "对话") -> Tuple[str, str]:
    """返回 (中文结论, 处置建议)。"""
    status = getattr(exc, "status_code", None)
    text = f"{exc} {getattr(exc, 'body', '')}".lower()

    # 1) 依赖版本不兼容（httpx>=0.28 去掉了 proxies 参数，chatchat 仍然在传）
    if isinstance(exc, TypeError) and "proxies" in text:
        return (
            "依赖版本不兼容：httpx 与 openai 的代理参数对不上",
            "这是 httpx>=0.28 移除 `proxies` 参数导致的。项目里已内置兼容补丁，"
            "若仍出现请执行 `pip install \"httpx<0.28\"` 后重启服务。",
        )

    # 2) 连不上后端
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            openai.APIConnectionError,
            ConnectionError,  # 含 ConnectionRefusedError / ConnectionResetError
        ),
    ) or any(h in text for h in _CONNECT_HINTS):
        return (
            "连接不上后端 API 服务",
            "请确认 API 服务已启动（`python run_api.py`，默认 7861 端口），"
            "且 `configs/basic_settings.yaml` 里的 API_SERVER 与实际一致。",
        )

    # 3) 超时
    if isinstance(
        exc, (httpx.TimeoutException, openai.APITimeoutError, TimeoutError)
    ) or any(h in text for h in _TIMEOUT_HINTS):
        return (
            "请求超时",
            "模型响应太慢。可以把「匹配知识条数」调小、换更小的模型，"
            "或调大 `configs/basic_settings.yaml` 的 HTTPX_DEFAULT_TIMEOUT。",
        )

    # 4) 按 HTTP 状态码分类
    if status == 401 or isinstance(exc, openai.AuthenticationError):
        return (
            "模型鉴权失败（401）",
            "API Key 无效或已过期。检查 `.env` 里的 DEEPSEEK_API_KEY，"
            "以及 `configs/model_settings.yaml` 中对应平台的 api_key。",
        )
    if status == 403 or isinstance(exc, openai.PermissionDeniedError):
        return (
            "没有访问权限（403）",
            "当前 Key / 平台不允许调用该模型，换一个模型或检查平台权限配置。",
        )
    if status == 404 or isinstance(exc, openai.NotFoundError):
        return (
            "模型或知识库不存在（404）",
            "确认「请选择知识库」里的名字真实存在（可在「知识库管理」页查看），"
            "并确认所选模型在 `model_settings.yaml` 的 llm_models 里。",
        )
    if status == 422:
        return (
            "请求参数不合法（422）",
            "多半是知识库名不对或缺少必填参数，请重新选择知识库后重试。",
        )
    if status == 429 or isinstance(exc, openai.RateLimitError):
        return (
            "触发限流（429）",
            "请求太频繁或额度用尽。稍等再试，或改用本地 Ollama 模型。",
        )
    if status is not None and 500 <= status < 600:
        return (
            f"后端服务内部错误（{status}）",
            "查看启动 API 的终端日志定位具体堆栈；常见原因是模型服务未启动"
            "（Ollama 没跑）或知识库向量未加载。",
        )

    return (
        f"未知错误（{type(exc).__name__}）",
        "请展开下方技术细节查看原始信息，并对照 API 终端日志。",
    )


def show_error(exc: Exception, action: str = "对话") -> None:
    """在页面上展示一条中文错误，附带可展开的原始细节。"""
    title, advice = describe(exc, action)
    st.error(f"**{action}失败：{title}**\n\n{advice}")
    with st.expander("查看技术细节（排障用）", expanded=False):
        st.code(_raw_detail(exc), language="text")
