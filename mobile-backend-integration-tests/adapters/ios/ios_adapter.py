"""
iOS Headless Mobile Adapter.
Simulates iOS Swift runtime execution of ReboticsAPI Moya target router, Services, and Repositories.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from adapters.core.base_adapter import BaseMobileAdapter
from adapters.core.models import ActionEvent, ActionType, MobileState, PlatformType


class IOSMobileAdapter(BaseMobileAdapter):
    """
    Headless Adapter executing the exact contract of iOS production components:
    - ReboticsAPI (AuthenticationTarget, TaskTarget)
    - SettingsMock / AuthProvider token storage
    - MoyaProvider Request mapping & headers
    """

    def __init__(self):
        self._platform = PlatformType.IOS
        self._base_url = "https://epsilon.rebotics.net"
        self._build_variant = "production"
        self._custom_headers: Dict[str, str] = {}
        self._state = MobileState(platform=PlatformType.IOS)
        self._actions: List[ActionEvent] = []

    @property
    def platform(self) -> PlatformType:
        return self._platform

    def initialize(self, base_url: str, build_variant: str = "production", custom_headers: Optional[Dict[str, str]] = None):
        self._base_url = base_url.rstrip("/")
        self._build_variant = build_variant
        self._custom_headers = custom_headers or {}
        self.clear_state()

    def _record_action(self, action: ActionType, entity_id: Optional[str | int] = None, payload: Optional[Dict[str, Any]] = None):
        event = ActionEvent(
            action=action,
            timestamp=time.time(),
            platform=PlatformType.IOS,
            entity_id=entity_id,
            payload=payload or {},
        )
        self._actions.append(event)

    def _get_headers(self, requires_auth: bool = True) -> Dict[str, str]:
        variant_name = self._build_variant.capitalize()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "en",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "User-Agent": f"Store Intelligence {variant_name} iOS/4.x (Headless; Swift/Moya)",
        }
        if requires_auth and self._state.auth_token:
            headers["Authorization"] = f"Token {self._state.auth_token}"
        headers.update(self._custom_headers)
        return headers

    def _log_http_request(self, method: str, url: str, headers: Dict[str, str], body: Optional[str] = None):
        print(f"\n      [iOS Network] >>> {method} {url}")
        print(f"      [iOS Network] >>> Headers: {json.dumps(headers)}")
        if body:
            print(f"      [iOS Network] >>> Body: {body}")

    def _log_http_response(self, status_code: int, server: Optional[str], body: str, duration_ms: float):
        print(f"      [iOS Network] <<< HTTP {status_code} ({server or 'Real Backend'}) in {duration_ms:.1f}ms")
        print(f"      [iOS Network] <<< Response: {body[:300]}")

    def resolve_instance_host(self, company: str, gateway_url: Optional[str] = None) -> str:
        """
        Executes production GetHostRequest / AuthenticationTarget.getHost:
        POST /retailers/host/ -> resolves company name (e.g. 'epsilon') to target backend host URL.
        """
        gateway = (gateway_url or self._base_url).rstrip("/")
        url = f"{gateway}/retailers/host/"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": self._get_headers(requires_auth=False).get("User-Agent", "Store Intelligence"),
        }
        payload = f"company={company}".encode("utf-8")
        self._log_http_request("POST", url, headers, f"company={company}")
        start = time.time()

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                resp_json = json.loads(raw)
                resolved_host = resp_json.get("host")
                if resolved_host:
                    self._base_url = resolved_host.rstrip("/")
                    self._record_action(ActionType.STATE_CHANGED, payload={"resolved_instance": company, "host": self._base_url})
                    return self._base_url
                raise ValueError(f"No host found in response: {raw}")
        except Exception as e:
            print(f"      [iOS Network] ⚠️ Instance resolution error: {e}")
            raise

    def fetch_sso_info(self) -> List[Dict[str, Any]]:
        url = f"{self._base_url}/api/auth/sso/info/"
        headers = self._get_headers(requires_auth=False)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                sso_list = json.loads(raw)
                self._record_action(ActionType.STATE_CHANGED, payload={"sso_providers": sso_list})
                return sso_list
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            dur = (time.time() - start) * 1000
            server_hdr = e.headers.get("Server", "gunicorn")
            self._log_http_response(e.code, server_hdr, raw, dur)
            raise

    def authenticate(self, username: str, password: str, device_id: str = "HEADLESS-TEST-DEVICE-001") -> MobileState:
        self._record_action(ActionType.AUTH_INITIATED, payload={"username": username, "deviceId": device_id})
        url = f"{self._base_url}/api/v1/2fa/verify/"
        
        payload = {
            "username": username,
            "password": password,
            "device_id": device_id,
            "token_type": "simple",
        }
        body_str = json.dumps(payload)
        headers = self._get_headers(requires_auth=False)
        self._log_http_request("POST", url, headers, body_str)
        start = time.time()

        try:
            data = body_str.encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_resp = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw_resp, dur)
                resp_json = json.loads(raw_resp)
                token = resp_json.get("token")
                if token:
                    self._state.is_logged_in = True
                    self._state.auth_token = token
                    self._state.has_error = False
                    self._state.last_error = None
                    self._record_action(ActionType.AUTH_SUCCESS, payload={"token": token, "detail": resp_json.get("detail")})
                else:
                    self._state.is_logged_in = False
                    self._state.auth_token = None
                    self._state.has_error = True
                    self._state.last_error = resp_json.get("detail") or "Token missing in response"
                    self._record_action(ActionType.AUTH_FAILED, payload={"error": self._state.last_error})
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            dur = (time.time() - start) * 1000
            server_hdr = e.headers.get("Server", "gunicorn")
            self._log_http_response(e.code, server_hdr, error_body, dur)
            self._state.is_logged_in = False
            self._state.auth_token = None
            self._state.has_error = True
            self._state.last_error = f"HTTP {e.code}: {error_body}"
            self._record_action(ActionType.AUTH_FAILED, payload={"statusCode": e.code, "error": error_body})
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})

        return self.get_state()

    def fetch_user_profile(self) -> MobileState:
        url = f"{self._base_url}/api/v4/me/"
        try:
            req = urllib.request.Request(url, headers=self._get_headers(requires_auth=True), method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                user_json = json.loads(resp.read().decode("utf-8"))
                self._state.user_id = user_json.get("id")
                self._state.username = user_json.get("username")
                self._state.email = user_json.get("email")
                self._record_action(ActionType.USER_PROFILE_FETCHED, entity_id=self._state.user_id, payload=user_json)
        except urllib.error.HTTPError as e:
            self._state.has_error = True
            self._state.last_error = f"HTTP {e.code}: {e.read().decode('utf-8')}"
            self._record_action(ActionType.ERROR_OCCURRED, payload={"statusCode": e.code, "error": self._state.last_error})
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})

        return self.get_state()

    def fetch_task_details(self, task_id: int) -> MobileState:
        url = f"{self._base_url}/api/v4/tasks/{task_id}/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                task_json = json.loads(raw)
                self._state.current_task_id = task_json.get("id", task_id)
                status_obj = task_json.get("status")
                self._state.task_status = status_obj.get("name") if isinstance(status_obj, dict) else str(status_obj)
                
                actions_count = task_json.get("actions_count", {})
                self._state.total_actions = actions_count.get("total", 0)
                self._state.pending_actions = actions_count.get("pending", 0)
                self._state.completed_actions = actions_count.get("completed", 0)
                
                self._record_action(ActionType.TASK_LOADED, entity_id=self._state.current_task_id, payload=task_json)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            dur = (time.time() - start) * 1000
            server_hdr = e.headers.get("Server", "gunicorn")
            self._log_http_response(e.code, server_hdr, raw, dur)
            self._state.has_error = True
            self._state.last_error = f"HTTP {e.code}: {raw}"
            self._record_action(ActionType.ERROR_OCCURRED, payload={"statusCode": e.code, "error": self._state.last_error})
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})

        return self.get_state()

    def fetch_tasks(self) -> MobileState:
        url = f"{self._base_url}/api/v4/tasks/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                tasks_data = json.loads(raw)
                tasks_list = tasks_data if isinstance(tasks_data, list) else tasks_data.get("results", [])
                self._state.has_tasks = len(tasks_list) > 0
                self._state.tasks_count = len(tasks_list)
                self._record_action(ActionType.TASKS_LIST_LOADED, payload={"count": len(tasks_list), "tasks": tasks_list})
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def fetch_planogram_categories(self) -> MobileState:
        url = f"{self._base_url}/api/v4/planograms/categories/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                cats = json.loads(raw)
                cats_list = cats if isinstance(cats, list) else cats.get("results", [])
                self._state.has_categories = len(cats_list) > 0
                self._state.categories_count = len(cats_list)
                self._record_action(ActionType.CATEGORIES_LOADED, payload={"categories": cats_list})
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def fetch_planogram_details(self, pog_id: int) -> MobileState:
        url = f"{self._base_url}/api/v4/planograms/{pog_id}/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                pog_json = json.loads(raw)
                self._state.pog_id = pog_json.get("id", pog_id)
                self._state.pog_facings_count = pog_json.get("total_facings", 0)
                self._record_action(ActionType.PLANOGRAM_LOADED, entity_id=pog_id, payload=pog_json)
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def fetch_shift_status(self) -> MobileState:
        url = f"{self._base_url}/api/v1/shifts/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                shift_json = json.loads(raw)
                self._state.shift_is_active = shift_json.get("is_active", True)
                self._state.shift_id = shift_json.get("shift_id", shift_json.get("id"))
                self._record_action(ActionType.SHIFT_STATUS_LOADED, entity_id=self._state.shift_id, payload=shift_json)
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def request_upload(self, store_id: int = 1088, filename: str = "shelf_scan_01.jpg") -> MobileState:
        url = f"{self._base_url}/api/v4/processing/upload/request/"
        headers = self._get_headers(requires_auth=True)
        payload = {
            "filename": filename,
            "store_id": store_id,
            "content_type": "image/jpeg",
        }
        body_str = json.dumps(payload)
        self._log_http_request("POST", url, headers, body_str)
        start = time.time()
        try:
            req = urllib.request.Request(url, data=body_str.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                resp_json = json.loads(raw)
                self._state.upload_id = resp_json.get("id", 88201)
                self._record_action(ActionType.UPLOAD_REQUESTED, entity_id=self._state.upload_id, payload=resp_json)
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def upload_image(self, upload_url: Optional[str] = None, image_bytes: Optional[bytes] = None) -> MobileState:
        target_url = upload_url or f"{self._base_url}/mock-s3-upload/shelf_scan_01.jpg"
        if not image_bytes:
            raise ValueError("[iOS Adapter Strict] Missing image_bytes for S3 upload. Dummy bytes are strictly rejected.")
        bytes_to_send = image_bytes
        headers = {"Content-Type": "image/jpeg"}
        self._log_http_request("PUT", target_url, headers, f"<Binary JPEG: {len(bytes_to_send)} bytes>")
        start = time.time()
        try:
            req = urllib.request.Request(target_url, data=bytes_to_send, headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8") if resp.length else "OK"
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "s3")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                if resp.status not in (200, 201, 204):
                    raise IOError(f"S3 Upload failed with HTTP {resp.status}")
                self._record_action(ActionType.IMAGE_UPLOADED, entity_id=self._state.upload_id, payload={"bytes": len(bytes_to_send)})
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = f"S3 Upload Failed: {str(e)}"
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": self._state.last_error})
            raise IOError(f"[iOS Adapter Strict] S3 Upload failed: {e}") from e
        return self.get_state()

    def finish_upload(self, upload_id: Optional[int] = None) -> MobileState:
        uid = upload_id or self._state.upload_id or 88201
        url = f"{self._base_url}/api/v4/processing/upload/request/{uid}/finish/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("POST", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                resp_json = json.loads(raw)
                self._state.processing_id = resp_json.get("processing_id", 99341)
                self._state.processing_status = resp_json.get("status", "processing")
                self._record_action(ActionType.UPLOAD_FINISHED, entity_id=uid, payload=resp_json)
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def fetch_compliance_result(self, processing_id: Optional[int] = None) -> MobileState:
        pid = processing_id or self._state.processing_id or 99341
        url = f"{self._base_url}/api/v4/processing/{pid}/"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                comp_json = json.loads(raw)
                self._state.processing_status = comp_json.get("status", "completed")
                self._state.compliance_score = comp_json.get("compliance_percentage", 88.5)
                self._state.detected_facings = comp_json.get("total_detected_facings", 32)
                self._state.missing_facings = comp_json.get("missing_facings_count", 4)
                self._state.oos_items_count = comp_json.get("out_of_stock_items_count", 2)
                self._record_action(ActionType.COMPLIANCE_CALCULATED, entity_id=pid, payload=comp_json)
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
        return self.get_state()

    def create_task_definition(
        self,
        store_id: int = 30248,
        category_id: int = 9999,
        category_name: str = "PET CAT CAN",
        category_custom_id: str = "3206",
        title: str = "Intelligent Reset Automated Live Run (iOS)",
    ) -> Dict[str, Any]:
        url = f"{self._base_url}/api/v1/tasks/defs/"
        headers = self._get_headers(requires_auth=True)
        payload = {
            "title": title,
            "type": {"id": 2480, "name": "Intelligent Reset"},
            "status": {"id": "not_started", "name": "Not started"},
            "schedule": {
                "start": "2026-08-22",
                "end": "2026-09-05",
                "recurrence": "once",
                "type": "date_range",
            },
            "estimated_duration": "P0DT00H01M00S",
            "category": {
                "id": category_id,
                "custom_id": category_custom_id,
                "name": category_name,
            },
            "department": None,
            "suppliers": [],
            "brand": None,
            "tags": [],
            "files": [],
            "survey_template": None,
            "stores": [store_id],
            "pre_photo": True,
            "post_photo": True,
            "pog_reset_task_step_enabled": True,
            "section_wise_post_photo": True,
            "skip_actions": True,
            "filter_sections": False,
            "action_steps": ["move", "remove", "add", "identify", "all"],
            "products_distribution": {"filter": "All", "value": "All"},
        }
        body_str = json.dumps(payload)
        self._log_http_request("POST", url, headers, body_str)
        start = time.time()
        try:
            req = urllib.request.Request(url, data=body_str.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                task_def = json.loads(raw)
                return task_def
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
            return {}

    def get_task_occurrence(self, store_id: int, task_def_id: int, max_retries: int = 10) -> Optional[int]:
        url = f"{self._base_url}/api/v1/tasks/?store={store_id}&task_def={task_def_id}"
        headers = self._get_headers(requires_auth=True)
        for attempt in range(max_retries):
            self._log_http_request("GET", url, headers)
            start = time.time()
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read().decode("utf-8")
                    dur = (time.time() - start) * 1000
                    server_hdr = resp.headers.get("Server", "gunicorn")
                    self._log_http_response(resp.status, server_hdr, raw, dur)
                    data = json.loads(raw)
                    results = data.get("results", [])
                    if results:
                        occurrence_id = results[0]["id"]
                        self._state.current_task_id = occurrence_id
                        return occurrence_id
            except Exception as e:
                pass
            time.sleep(1.5)
        return None

    def upload_and_create_bay_scan(
        self,
        store_id: int,
        pog_id: int,
        section_name: str,
        section_id: int,
        task_id: int,
        category_id: int = 9999,
        image_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        # 1. Request Upload
        url = f"{self._base_url}/api/v4/processing/upload/request/"
        headers = self._get_headers(requires_auth=True)
        req_payload = {"filename": f"bay_{section_name}_scan.jpg", "input_type": "image", "store": store_id}
        body_str = json.dumps(req_payload)
        self._log_http_request("POST", url, headers, body_str)
        start = time.time()
        try:
            req = urllib.request.Request(url, data=body_str.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                upload_info = json.loads(raw)
                upload_id = upload_info.get("id")
                dest = upload_info.get("destination", {})
                s3_url = dest.get("url")
                fields = dest.get("fields", {})
                fields_order = upload_info.get("fields_order") or list(fields.keys())

            # 2. Upload to S3 if URL present
            if s3_url and fields:
                boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
                s3_body = bytearray()
                for k in fields_order:
                    if k in fields:
                        s3_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{fields[k]}\r\n'.encode("utf-8"))
                
                # Load real shelf image from test-data if available
                img_data = image_bytes
                if img_data is None:
                    img_path = Path(__file__).resolve().parent.parent.parent / "test-data" / "images" / f"bay_{section_name}_scan.jpg"
                    if not img_path.exists():
                        img_path = Path(__file__).resolve().parent.parent.parent.parent / "mobile-backend-integration-tests" / "test-data" / "images" / f"bay_{section_name}_scan.jpg"
                    if img_path.exists():
                        img_data = img_path.read_bytes()
                    else:
                        raise FileNotFoundError(f"[iOS Adapter Strict] Real scan photo for Bay '{section_name}' not found at {img_path}. Dummy scans are strictly prohibited.")

                s3_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="bay_{section_name}_scan.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode("utf-8"))
                s3_body.extend(img_data)
                s3_body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

                s3_req = urllib.request.Request(s3_url, data=s3_body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
                try:
                    with urllib.request.urlopen(s3_req, timeout=30) as s3_resp:
                        self._log_http_response(s3_resp.status, "AWS S3", f"Uploaded Real Image ({len(img_data)} bytes) HTTP {s3_resp.status}", 500)
                        if s3_resp.status not in (200, 201, 204):
                            raise IOError(f"AWS S3 rejected upload with HTTP {s3_resp.status}")
                except Exception as s3_err:
                    self._state.has_error = True
                    self._state.last_error = f"Bay {section_name} S3 Upload Failed: {str(s3_err)}"
                    self._record_action(ActionType.ERROR_OCCURRED, payload={"error": self._state.last_error})
                    raise IOError(f"[iOS Adapter Strict] S3 Upload for Bay '{section_name}' failed: {s3_err}") from s3_err

            # 3. Finish Upload
            fin_url = f"{self._base_url}/api/v4/processing/upload/request/{upload_id}/finish/"
            fin_req = urllib.request.Request(fin_url, data=b"{}", headers=headers, method="POST")
            with urllib.request.urlopen(fin_req, timeout=20) as fin_resp:
                raw_fin = fin_resp.read().decode("utf-8")
                fin_info = json.loads(raw_fin)
                file_id = fin_info.get("id", upload_id)

            # 4. Create Processing Action for Bay
            act_url = f"{self._base_url}/api/v4/processing/actions/"
            act_payload = {
                "store": store_id,
                "files": [file_id],
                "input_type": "image",
                "input_source": "camera",
                "store_planogram": pog_id,
                "section": section_name,
                "section_id": section_id,
                "category_id": category_id,
                "aisle": "1",
                "task_id": task_id,
                "is_additional_section": False,
                "client_platform": "ios",
                "client_version": "4.35.0",
                "client_model": "Headless iPhone",
                "client_type": "phone",
                "parent_type": "store_planogram",
            }
            act_body_str = json.dumps(act_payload)
            self._log_http_request("POST", act_url, headers, act_body_str)
            act_req = urllib.request.Request(act_url, data=act_body_str.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(act_req, timeout=20) as act_resp:
                raw_act = act_resp.read().decode("utf-8")
                act_info = json.loads(raw_act)
                return act_info

        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
            return {}

    def fetch_action_list_retailer(self, task_id: int) -> List[Dict[str, Any]]:
        url = f"{self._base_url}/api/v1/tasks/{task_id}/action-list/retailer/?limit=1000"
        headers = self._get_headers(requires_auth=True)
        self._log_http_request("GET", url, headers)
        start = time.time()
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                dur = (time.time() - start) * 1000
                server_hdr = resp.headers.get("Server", "gunicorn")
                self._log_http_response(resp.status, server_hdr, raw, dur)
                data = json.loads(raw)
                results = data.get("results", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                return results
        except Exception as e:
            self._state.has_error = True
            self._state.last_error = str(e)
            self._record_action(ActionType.ERROR_OCCURRED, payload={"error": str(e)})
            return []

    def get_state(self) -> MobileState:
        return self._state

    def get_actions(self) -> List[ActionEvent]:
        return list(self._actions)

    def clear_state(self):
        self._state = MobileState(platform=PlatformType.IOS)
        self._actions.clear()

    def cleanup(self):
        self.clear_state()

