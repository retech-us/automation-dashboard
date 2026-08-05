#!/usr/bin/env python3
"""
Local dashboard server with GenAI chat proxy.

Uses the same Symphony OpenAI gateway + OPENAI_KEY as retech-web-automation.
Serves the static dashboard and POST /api/chat so the browser never needs the key.

Usage:
  export OPENAI_KEY=...   # or rely on web-automation secure.properties
  python3 scripts/dashboard-server.py
  open http://127.0.0.1:8765/
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("DASHBOARD_PORT", "8765"))
API_BASE = os.environ.get("OPENAI_API_BASE", "https://ai-api.symphonyretailai.com")
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")

WEB_AUTOMATION_SECURE = Path.home() / "sympohonyworkspace/retech-web-automation/src/test/resources/config/secure.properties"
# Also try sibling relative to this repo
SIBLING_SECURE = ROOT.parent / "retech-web-automation/src/test/resources/config/secure.properties"
LOCAL_KEY_FILE = ROOT / "data" / "local-openai.json"


def load_openai_key() -> str | None:
    key = (os.environ.get("OPENAI_KEY") or os.environ.get("openai.key") or "").strip()
    if key:
        return key

    if LOCAL_KEY_FILE.exists():
        try:
            data = json.loads(LOCAL_KEY_FILE.read_text(encoding="utf-8"))
            key = (data.get("OPENAI_KEY") or data.get("apiKey") or "").strip()
            if key and key not in {"youopenapikey", "your_key", "REPLACE_ME"}:
                return key
        except Exception:
            pass

    for props in (SIBLING_SECURE, WEB_AUTOMATION_SECURE):
        if not props.exists():
            continue
        try:
            text = props.read_text(encoding="utf-8")
            m = re.search(r"(?m)^\s*OPENAI_KEY\s*=\s*(.+?)\s*$", text)
            if m:
                key = m.group(1).strip().strip('"').strip("'")
                if key and key not in {"youopenapikey", "your_key", "REPLACE_ME"}:
                    return key
        except Exception:
            pass
    return None


def call_symphony_chat(messages: list[dict], model: str | None = None) -> dict:
    api_key = load_openai_key()
    if not api_key:
        return {
            "ok": False,
            "error": "OPENAI_KEY not found. Export OPENAI_KEY, or set it in retech-web-automation secure.properties, or data/local-openai.json.",
        }

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{API_BASE.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {"ok": False, "error": f"GenAI HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"ok": False, "error": f"GenAI request failed: {exc}"}

    try:
        content = body["choices"][0]["message"]["content"]
    except Exception:
        return {"ok": False, "error": "Unexpected GenAI response shape", "raw": body}
    return {"ok": True, "content": content, "model": payload["model"]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code: int, payload: dict):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(404)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/chat/status":
            key = load_openai_key()
            self._json(200, {
                "ok": True,
                "genaiReady": bool(key),
                "provider": "symphony-openai",
                "model": DEFAULT_MODEL,
                "apiBase": API_BASE,
                "keySource": "env-or-secure-properties" if key else None,
            })
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") if length else "{}")
        except Exception:
            self._json(400, {"ok": False, "error": "Invalid JSON body"})
            return

        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            self._json(400, {"ok": False, "error": "messages[] required"})
            return

        result = call_symphony_chat(messages, data.get("model"))
        self._json(200 if result.get("ok") else 502, result)

    def log_message(self, fmt, *args):
        # Quieter static asset noise
        if str(args[0]).startswith("GET /assets/") or str(args[0]).startswith("GET /data/"):
            return
        super().log_message(fmt, *args)


def main():
    os.chdir(ROOT)
    key = load_openai_key()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Dashboard + GenAI proxy: http://127.0.0.1:{PORT}/", flush=True)
    print(f"Model: {DEFAULT_MODEL} @ {API_BASE}", flush=True)
    print(f"OPENAI_KEY: {'found' if key else 'MISSING — set env or secure.properties'}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
