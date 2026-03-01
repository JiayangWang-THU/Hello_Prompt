from __future__ import annotations

import argparse
import json
import threading
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any

from .cli_agent import build_clarification_service, dispatch_agent_input


@dataclass
class WebInteractionResponse:
    text: str
    done: bool
    state: dict[str, Any]


class WebSessionController:
    def __init__(self, service) -> None:
        self.service = service
        self._lock = threading.Lock()

    def message(self, user_text: str) -> WebInteractionResponse:
        with self._lock:
            result = dispatch_agent_input(self.service, user_text)
            return WebInteractionResponse(
                text=result.text,
                done=result.done,
                state=self.service.snapshot(),
            )

    def reset(self) -> WebInteractionResponse:
        with self._lock:
            result = self.service.reset()
            return WebInteractionResponse(
                text=result.text,
                done=result.done,
                state=self.service.snapshot(),
            )

    def state(self) -> dict[str, Any]:
        with self._lock:
            return self.service.snapshot()


def run_web(args: argparse.Namespace) -> None:
    try:
        service = build_clarification_service(
            templates_path=args.config,
            agent_config_path=args.agent_config,
            llm_config_path=args.llm_config,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Web UI 启动失败：{exc}")
        print("请先确认 langchain-openai 已安装，且 llm.yaml / 环境变量中的本地模型配置正确。")
        return

    controller = WebSessionController(service)
    handler_cls = _build_handler(controller)
    server = ThreadingHTTPServer((args.host, args.port), handler_cls)
    print("Hello Prompt Agent Web")
    print(f"打开浏览器访问：http://{args.host}:{args.port}")
    print("按 Ctrl+C 退出。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止 Web UI。")
    finally:
        server.server_close()


def _build_handler(controller: WebSessionController):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/state":
                self._send_json({"state": controller.state()})
                return
            if self.path in {"/", "/index.html"}:
                self._send_asset("index.html", "text/html; charset=utf-8")
                return
            if self.path == "/app.css":
                self._send_asset("app.css", "text/css; charset=utf-8")
                return
            if self.path == "/app.js":
                self._send_asset("app.js", "application/javascript; charset=utf-8")
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/api/message":
                payload = self._read_json_body()
                message = str(payload.get("message", "")).strip()
                if not message:
                    self._send_json({"error": "message is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                response = controller.message(message)
                self._send_json(asdict(response))
                return
            if self.path == "/api/reset":
                response = controller.reset()
                self._send_json(asdict(response))
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            if not raw:
                return {}
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
                raise _EarlyReturn
            if not isinstance(payload, dict):
                self._send_json({"error": "json body must be an object"}, status=HTTPStatus.BAD_REQUEST)
                raise _EarlyReturn
            return payload

        def _send_asset(self, asset_name: str, content_type: str) -> None:
            asset = resources.files("hpa.webapp").joinpath(asset_name)
            if not asset.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return
            data = asset.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def handle_one_request(self) -> None:
            try:
                super().handle_one_request()
            except _EarlyReturn:
                return

    return Handler


class _EarlyReturn(Exception):
    pass
