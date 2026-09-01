#!/usr/bin/env python3
"""
Controlled Backend Mock Server for Headless Mobile-Backend Integration Tests.
Serves predefined fixtures and records incoming requests for verification.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class MockBackendState:
    """Stores recorded requests and endpoint route rules."""
    def __init__(self):
        self.recorded_requests: List[Dict[str, Any]] = []
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.default_delay_seconds: float = 0.0
        self.lock = threading.Lock()

    def reset(self):
        with self.lock:
            self.recorded_requests.clear()
            self.routes.clear()
            self.default_delay_seconds = 0.0

    def record_request(self, req: Dict[str, Any]):
        with self.lock:
            self.recorded_requests.append(req)

    def register_route(
        self,
        path_pattern: str,
        method: str = "GET",
        status_code: int = 200,
        response_body: Optional[Any] = None,
        fixture_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        delay_seconds: float = 0.0,
    ):
        with self.lock:
            key = f"{method.upper()}:{path_pattern}"
            body = response_body
            if fixture_file:
                fixture_path = FIXTURES_DIR / fixture_file
                if fixture_path.exists():
                    body = json.loads(fixture_path.read_text(encoding="utf-8"))
                else:
                    raise FileNotFoundError(f"Fixture not found: {fixture_path}")
            self.routes[key] = {
                "statusCode": status_code,
                "body": body,
                "headers": headers or {"Content-Type": "application/json"},
                "delaySeconds": delay_seconds,
            }

    def match_route(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            # 1. Exact match
            key = f"{method.upper()}:{path.rstrip('/')}"
            if key in self.routes:
                return self.routes[key]
            
            # 2. Match with trailing slash
            key_slash = f"{method.upper()}:{path.rstrip('/')}/"
            if key_slash in self.routes:
                return self.routes[key_slash]

            # 3. Regex / Pattern match
            for route_key, config in self.routes.items():
                r_method, r_pattern = route_key.split(":", 1)
                if r_method == method.upper():
                    pattern_regex = "^" + re.sub(r"\{[^/]+\}", r"[^/]+", r_pattern) + "/?$"
                    if re.match(pattern_regex, path):
                        return config
        return None


GLOBAL_STATE = MockBackendState()


class MockRequestHandler(BaseHTTPRequestHandler):
    """Handles incoming HTTP requests against registered mock routes."""

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP logs during tests
        pass

    def _handle_request(self, method: str):
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        
        parsed_body = None
        if raw_body:
            try:
                parsed_body = json.loads(raw_body)
            except Exception:
                parsed_body = parse_qs(raw_body)

        req_record = {
            "timestamp": time.time(),
            "method": method,
            "path": path,
            "headers": dict(self.headers),
            "queryParams": query_params,
            "rawBody": raw_body,
            "body": parsed_body,
        }
        GLOBAL_STATE.record_request(req_record)

        # Check route
        route = GLOBAL_STATE.match_route(method, path)
        if not route:
            # Default auto-fixtures based on known paths
            route = self._get_default_fallback_route(method, path)

        if not route:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": f"Not found in mock: {method} {path}"}).encode("utf-8"))
            return

        if route.get("delaySeconds", 0) > 0:
            time.sleep(route["delaySeconds"])

        status_code = route.get("statusCode", 200)
        self.send_response(status_code)
        
        resp_headers = route.get("headers", {"Content-Type": "application/json"})
        for k, v in resp_headers.items():
            self.send_header(k, v)
        self.end_headers()

        resp_body = route.get("body")
        if resp_body is not None:
            if isinstance(resp_body, (dict, list)):
                self.wfile.write(json.dumps(resp_body).encode("utf-8"))
            else:
                self.wfile.write(str(resp_body).encode("utf-8"))

    def _get_default_fallback_route(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        clean_path = path.strip("/")
        if clean_path.endswith("2fa/verify"):
            fixture = FIXTURES_DIR / "auth" / "2fa_verify_success.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif clean_path == "api/v4/me":
            fixture = FIXTURES_DIR / "auth" / "me_success.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif clean_path == "api/v4/planograms/categories":
            fixture = FIXTURES_DIR / "pog_reset" / "planogram_categories.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif re.match(r"^api/v4/planograms/\d+", clean_path):
            fixture = FIXTURES_DIR / "pog_reset" / "planogram_details_complex.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif clean_path == "api/v4/tasks":
            fixture = FIXTURES_DIR / "tasks" / "tasks_list.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif re.match(r"^api/v4/tasks/\d+", clean_path):
            fixture = FIXTURES_DIR / "tasks" / "task_details_success.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif clean_path == "api/v4/processing/upload/request":
            fixture = FIXTURES_DIR / "uploads" / "pre_upload_response.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif re.match(r"^api/v4/processing/upload/request/\d+/finish", clean_path):
            fixture = FIXTURES_DIR / "uploads" / "post_upload_response.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif re.match(r"^api/v4/processing/\d+", clean_path):
            fixture = FIXTURES_DIR / "uploads" / "processing_compliance_result.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        elif "mock-s3-upload" in clean_path:
            return {"statusCode": 200, "body": {"message": "Binary image uploaded to S3 successfully"}}
        elif clean_path == "api/v1/shifts":
            fixture = FIXTURES_DIR / "shifts" / "shift_status.json"
            if fixture.exists():
                return {"statusCode": 200, "body": json.loads(fixture.read_text(encoding="utf-8"))}
        return None

    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def do_PUT(self):
        self._handle_request("PUT")

    def do_PATCH(self):
        self._handle_request("PATCH")

    def do_DELETE(self):
        self._handle_request("DELETE")


class ControlledMockServer:
    """Manages the lifecycle of the local Mock Backend HTTP Server."""
    def __init__(self, host: str = "127.0.0.1", port: int = 8089):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.state = GLOBAL_STATE

    def start(self):
        if self.server is not None:
            return
        self.server = HTTPServer((self.host, self.port), MockRequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"[*] Controlled Mock Backend running at http://{self.host}:{self.port}")

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.thread = None
            print("[*] Controlled Mock Backend stopped.")

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


if __name__ == "__main__":
    server = ControlledMockServer()
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
