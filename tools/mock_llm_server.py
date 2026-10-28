"""一个极简的 OpenAI 兼容桩服务，用于离线开发和联调。

用途：
- 没有可用 API Key 时，验证「平台配置 -> get_OpenAIClient -> 请求 -> 流式解析」整条链路是否通；
- 写单元测试时不必真的调用云厂商，省钱且稳定；
- 排查问题时可以确定「问题在本地链路还是在远端」。

启动：
    python tools/mock_llm_server.py --port 7999

然后在 model_settings.yaml 里加一个平台：
    - platform_name: mock
      platform_type: custom openai
      api_base_url: http://127.0.0.1:7999/v1
      api_key: EMPTY
      llm_models: [mock-chat]

支持接口：
    GET  /v1/models
    POST /v1/chat/completions   （stream=true/false 都支持）

它不会真的「思考」，只是把最后一条用户消息回显出来，并把收到的
model / 消息条数一起写进回答，方便确认参数有没有正确透传。
"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _build_reply(payload: dict) -> str:
    msgs = payload.get("messages") or []
    last = msgs[-1].get("content", "") if msgs else ""
    if isinstance(last, list):  # 多模态 content 的情况
        last = " ".join(x.get("text", "") for x in last if isinstance(x, dict))
    model = payload.get("model", "mock")
    return f"[mock:{model}] 收到 {len(msgs)} 条消息。你说的是：{last[:200]}"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 关掉默认的每请求一行日志
        pass

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("/v1/models", "/models"):
            self._json(200, {
                "object": "list",
                "data": [{"id": "mock-chat", "object": "model", "owned_by": "mock"}],
            })
        else:
            self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": {"message": "invalid json"}})
            return

        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._json(404, {"error": {"message": "not found"}})
            return

        text = _build_reply(payload)
        created = int(time.time())
        cid = "chatcmpl-mock"

        if not payload.get("stream"):
            self._json(200, {
                "id": cid,
                "object": "chat.completion",
                "created": created,
                "model": payload.get("model", "mock-chat"),
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
            return

        # 流式：按字符切片发 SSE，模拟真实模型的逐 token 输出
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def chunk(delta: dict, finish=None):
            obj = {
                "id": cid, "object": "chat.completion.chunk", "created": created,
                "model": payload.get("model", "mock-chat"),
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }
            data = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
            raw = data.encode()
            self.wfile.write(b"%x\r\n%s\r\n" % (len(raw), raw))
            self.wfile.flush()

        chunk({"role": "assistant", "content": ""})
        for ch in text:  # 逐字符
            chunk({"content": ch})
        chunk({}, finish="stop")
        end = b"data: [DONE]\n\n"
        self.wfile.write(b"%x\r\n%s\r\n" % (len(end), end))
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7999)
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("mock LLM 监听 http://%s:%d/v1  （Ctrl+C 退出）" % (args.host, args.port), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("已退出")


if __name__ == "__main__":
    main()
