"""Minimal HTTP JSON API for regression agent tools (stdlib only)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from regression.tools import TOOLS_API_VERSION, invoke_tool, list_tools_payload


def _json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2).encode("utf-8")


class ToolsHTTPHandler(BaseHTTPRequestHandler):
    server_version = f"RegressionTools/{TOOLS_API_VERSION}"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet by default; tests assert on responses not stdout noise.
        return

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            return None, f"Invalid JSON body: {exc}"
        if data is None:
            return {}, None
        if not isinstance(data, dict):
            return None, "JSON body must be an object"
        return data, None

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in ("/v1/health", "/health"):
            resp = invoke_tool("health", {})
            self._send(200 if resp.ok else 500, resp.as_dict())
            return
        if path in ("/v1/tools", "/tools"):
            self._send(200, list_tools_payload())
            return
        self._send(
            404,
            {
                "ok": False,
                "error": f"Not found: {path}",
                "hint": "GET /v1/tools | GET /v1/health | POST /v1/tools/{name}",
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path in ("/v1/tools/call", "/tools/call"):
            body, err = self._read_json()
            if err:
                self._send(400, {"ok": False, "exit_code": 2, "error": err})
                return
            assert body is not None
            name = str(body.get("tool") or "")
            args = body.get("args") if isinstance(body.get("args"), dict) else {}
            resp = invoke_tool(name, args)
            status = 200 if resp.exit_code in (0, 1) else 400
            self._send(status, resp.as_dict())
            return

        prefix = "/v1/tools/"
        alt = "/tools/"
        name = None
        if path.startswith(prefix) and path != prefix.rstrip("/"):
            name = path[len(prefix) :]
        elif path.startswith(alt) and path != alt.rstrip("/"):
            name = path[len(alt) :]
        else:
            self._send(
                404,
                {
                    "ok": False,
                    "error": f"Not found: {path}",
                    "hint": "POST /v1/tools/{name} with JSON args object",
                },
            )
            return

        if not name or name == "call":
            self._send(
                404,
                {
                    "ok": False,
                    "error": f"Not found: {path}",
                    "hint": "POST /v1/tools/{name} or POST /v1/tools/call",
                },
            )
            return

        body, err = self._read_json()
        if err:
            self._send(400, {"ok": False, "exit_code": 2, "error": err})
            return
        resp = invoke_tool(name, body or {})
        status = 200 if resp.exit_code in (0, 1) else 400
        self._send(status, resp.as_dict())


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), ToolsHTTPHandler)


def serve_forever(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = make_server(host, port)
    print(
        json.dumps(
            {
                "ok": True,
                "serving": f"http://{host}:{port}",
                "endpoints": [
                    "GET /v1/health",
                    "GET /v1/tools",
                    "POST /v1/tools/{name}",
                    "POST /v1/tools/call",
                ],
            },
            indent=2,
        ),
        flush=True,
    )
    httpd.serve_forever()
