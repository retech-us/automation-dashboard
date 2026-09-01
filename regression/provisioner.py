"""Slice 3 — Provisioner skeleton (catalog-matched images + task create/select)."""

from __future__ import annotations

import ssl
import time
import uuid
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from regression.auth import AuthCredentials, load_credentials, _http_json
from regression.env import resolve_base_url
from regression.image_catalog import ImageCatalog, ImageCatalogError, ImageResolution

REPO_ROOT = Path(__file__).resolve().parents[1]
_SSL_CTX = ssl._create_unverified_context()


class ProvisionerError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class PlannedScan:
    bay: int
    stage: str
    category: str
    image_id: str
    file: str
    absolute_path: str
    exists: bool

    @classmethod
    def from_resolution(cls, res: ImageResolution) -> "PlannedScan":
        return cls(
            bay=res.bay,
            stage=res.stage,
            category=res.category,
            image_id=res.entry.id,
            file=res.entry.file,
            absolute_path=str(res.entry.absolute_path),
            exists=res.entry.absolute_path.is_file(),
        )


@dataclass
class ProvisionPlan:
    env: str
    base_url: str
    category: str
    stage: str
    bays: List[int]
    store_id: Optional[int]
    task_id: Optional[int]
    pog_id: Optional[int]
    mode: str
    scans: List[PlannedScan] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvisionResult:
    ok: bool
    dry_run: bool
    plan: ProvisionPlan
    task_def_id: Optional[int] = None
    task_id: Optional[int] = None
    uploads: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "dry_run": self.dry_run,
            "plan": self.plan.as_dict(),
            "task_def_id": self.task_def_id,
            "task_id": self.task_id,
            "uploads": self.uploads,
            "error": self.error,
        }


def build_provision_plan(
    *,
    env: str,
    category: str,
    bays: Sequence[int],
    stage: str = "pre_photo",
    store_id: Optional[int] = None,
    task_id: Optional[int] = None,
    pog_id: Optional[int] = None,
    base_url_override: Optional[str] = None,
    catalog: Optional[ImageCatalog] = None,
    mode: str = "dry_run",
) -> ProvisionPlan:
    resolved = resolve_base_url(env, base_url_override=base_url_override)
    cat = catalog or ImageCatalog.load(repo_root=REPO_ROOT)
    resolutions = cat.resolve_bays(category=category, bays=list(bays), stage=stage)
    scans = [PlannedScan.from_resolution(r) for r in resolutions]
    missing = [s for s in scans if not s.exists]
    if missing:
        raise ProvisionerError(
            "Catalog matched but file(s) missing on disk: "
            + ", ".join(s.absolute_path for s in missing)
        )

    notes: List[str] = [
        "Images selected by planogram category + bay + stage only",
        "No global bay_1_scan.jpg fallback",
    ]
    if mode == "dry_run":
        notes.append("dry_run=true — no backend mutations")
    if task_id:
        notes.append(f"Will use existing task_id={task_id}")
    elif mode == "create":
        notes.append("Will create IR task definition + poll occurrence")

    return ProvisionPlan(
        env=resolved.env,
        base_url=resolved.base_url,
        category=category.strip().lower(),
        stage=stage.strip().lower(),
        bays=[int(b) for b in bays],
        store_id=store_id,
        task_id=task_id,
        pog_id=pog_id,
        mode=mode,
        scans=scans,
        notes=notes,
    )


def _auth_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Store Intelligence Regression Provisioner/0.1",
        "Authorization": f"Token {token}",
    }


def _login_token(
    env: str, *, base_url_override: Optional[str], credentials: AuthCredentials
) -> tuple[str, str]:
    resolved = resolve_base_url(env, base_url_override=base_url_override)
    status, payload, _ = _http_json(
        "POST",
        f"{resolved.base_url}/api/v1/2fa/verify/",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Store Intelligence Regression Provisioner/0.1",
        },
        body={
            "username": credentials.username,
            "password": credentials.password,
            "device_id": credentials.device_id,
            "token_type": credentials.token_type,
        },
    )
    token = payload.get("token") or payload.get("access")
    if status >= 400 or not token:
        raise ProvisionerError(f"Could not obtain token HTTP {status}: {payload}")
    return resolved.base_url, str(token)


def fetch_task(base_url: str, token: str, task_id: int) -> Dict[str, Any]:
    status, payload, _ = _http_json(
        "GET",
        f"{base_url}/api/v1/tasks/{task_id}/",
        headers=_auth_headers(token),
    )
    if status >= 400:
        status, payload, _ = _http_json(
            "GET",
            f"{base_url}/api/v4/tasks/{task_id}/",
            headers=_auth_headers(token),
        )
    if status >= 400:
        raise ProvisionerError(f"Task #{task_id} not found HTTP {status}: {payload}")
    return payload


def create_ir_task_definition(
    base_url: str,
    token: str,
    *,
    store_id: int,
    category_id: int,
    category_name: str,
    category_custom_id: str = "0",
    pog_id: Optional[int] = None,
) -> int:
    payload: Dict[str, Any] = {
        "title": f"Regression Provision {uuid.uuid4().hex[:8]}",
        "type": {"id": 2480, "name": "Intelligent Reset"},
        "status": {"id": "not_started", "name": "Not started"},
        "schedule": {
            "start": time.strftime("%Y-%m-%d"),
            "end": time.strftime("%Y-%m-%d", time.gmtime(time.time() + 14 * 86400)),
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
    if pog_id:
        payload["store_planograms"] = [pog_id]

    status, body, _ = _http_json(
        "POST",
        f"{base_url}/api/v1/tasks/defs/",
        headers=_auth_headers(token),
        body=payload,
    )
    if status >= 400 or not body.get("id"):
        raise ProvisionerError(f"Task def create failed HTTP {status}: {body}")
    return int(body["id"])


def poll_task_occurrence(
    base_url: str,
    token: str,
    *,
    task_def_id: int,
    store_id: Optional[int] = None,
    max_attempts: int = 15,
    sleep_s: float = 1.5,
) -> int:
    urls = [f"{base_url}/api/v1/tasks/?task_def={task_def_id}&ordering=-id"]
    if store_id:
        urls.append(
            f"{base_url}/api/v1/tasks/?store={store_id}&task_def={task_def_id}&ordering=-id"
        )
    for _ in range(max_attempts):
        for url in urls:
            status, body, _ = _http_json("GET", url, headers=_auth_headers(token))
            if status < 400:
                results = body.get("results") or []
                if results:
                    return int(results[0]["id"])
        time.sleep(sleep_s)
    raise ProvisionerError(f"No task occurrence spawned for task_def={task_def_id}")


def upload_catalog_scan(
    base_url: str,
    token: str,
    *,
    store_id: int,
    pog_id: int,
    task_id: int,
    planned: PlannedScan,
    section_id: Optional[int] = None,
    category_id: int = 0,
) -> Dict[str, Any]:
    image_path = Path(planned.absolute_path)
    image_bytes = image_path.read_bytes()
    headers = _auth_headers(token)

    status, upload_info, _ = _http_json(
        "POST",
        f"{base_url}/api/v4/processing/upload/request/",
        headers=headers,
        body={
            "filename": Path(planned.file).name,
            "input_type": "image",
            "store": store_id,
        },
    )
    if status >= 400:
        raise ProvisionerError(f"Upload request failed HTTP {status}: {upload_info}")

    upload_id = upload_info.get("id")
    dest = upload_info.get("destination") or {}
    s3_url = dest.get("url")
    fields = dest.get("fields") or {}
    fields_order = upload_info.get("fields_order") or list(fields.keys())

    if s3_url and fields:
        boundary = "----WebKitFormBoundaryRegressionSlice3"
        body = bytearray()
        for key in fields_order:
            if key in fields:
                body.extend(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{fields[key]}\r\n".encode()
                )
        fname = Path(planned.file).name
        body.extend(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fname}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode()
        )
        body.extend(image_bytes)
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        req = urllib.request.Request(
            s3_url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            if resp.status not in (200, 201, 204):
                raise ProvisionerError(f"S3 upload rejected HTTP {resp.status}")

    fin_status, fin_body, _ = _http_json(
        "POST",
        f"{base_url}/api/v4/processing/upload/request/{upload_id}/finish/",
        headers=headers,
        body={},
    )
    if fin_status >= 400:
        raise ProvisionerError(f"Upload finish failed HTTP {fin_status}: {fin_body}")
    file_id = fin_body.get("id", upload_id)

    act_payload = {
        "store": store_id,
        "files": [file_id],
        "input_type": "image",
        "input_source": "camera",
        "store_planogram": pog_id,
        "section": str(planned.bay),
        "section_id": section_id or planned.bay,
        "category_id": category_id,
        "aisle": "1",
        "task_id": task_id,
        "is_additional_section": False,
        "client_platform": "android",
        "client_version": "4.35.0",
        "client_model": "Regression Provisioner",
        "client_type": "phone",
        "parent_type": "store_planogram",
    }
    act_status, act_body, _ = _http_json(
        "POST",
        f"{base_url}/api/v4/processing/actions/",
        headers=headers,
        body=act_payload,
    )
    if act_status >= 400:
        raise ProvisionerError(f"Processing action failed HTTP {act_status}: {act_body}")

    return {
        "bay": planned.bay,
        "image_id": planned.image_id,
        "upload_id": upload_id,
        "file_id": file_id,
        "action_id": act_body.get("id"),
        "file": planned.file,
    }


def run_provision(
    *,
    env: str,
    category: str,
    bays: Sequence[int],
    stage: str = "pre_photo",
    store_id: Optional[int] = None,
    task_id: Optional[int] = None,
    pog_id: Optional[int] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    base_url_override: Optional[str] = None,
    dry_run: bool = True,
    credentials: Optional[AuthCredentials] = None,
    catalog: Optional[ImageCatalog] = None,
) -> ProvisionResult:
    mode = "dry_run"
    if not dry_run:
        mode = "select" if task_id else "create"

    try:
        plan = build_provision_plan(
            env=env,
            category=category,
            bays=bays,
            stage=stage,
            store_id=store_id,
            task_id=task_id,
            pog_id=pog_id,
            base_url_override=base_url_override,
            catalog=catalog,
            mode=mode,
        )
    except ImageCatalogError as exc:
        raise ProvisionerError(str(exc), exit_code=2) from exc

    if dry_run:
        return ProvisionResult(ok=True, dry_run=True, plan=plan, task_id=task_id)

    if store_id is None:
        raise ProvisionerError("--store-id is required for --execute", exit_code=2)
    if pog_id is None:
        raise ProvisionerError("--pog-id is required to upload bay scans", exit_code=2)

    creds = credentials or load_credentials()
    base_url, token = _login_token(env, base_url_override=base_url_override, credentials=creds)

    task_def_id = None
    resolved_task_id = task_id

    if resolved_task_id:
        fetch_task(base_url, token, resolved_task_id)
    else:
        if category_id is None:
            raise ProvisionerError("--category-id required when creating a task", exit_code=2)
        task_def_id = create_ir_task_definition(
            base_url,
            token,
            store_id=store_id,
            category_id=category_id,
            category_name=category_name or category,
            pog_id=pog_id,
        )
        resolved_task_id = poll_task_occurrence(
            base_url, token, task_def_id=task_def_id, store_id=store_id
        )

    uploads: List[Dict[str, Any]] = []
    for scan in plan.scans:
        uploads.append(
            upload_catalog_scan(
                base_url,
                token,
                store_id=store_id,
                pog_id=pog_id,
                task_id=int(resolved_task_id),
                planned=scan,
                category_id=category_id or 0,
            )
        )

    plan.task_id = resolved_task_id
    return ProvisionResult(
        ok=True,
        dry_run=False,
        plan=plan,
        task_def_id=task_def_id,
        task_id=resolved_task_id,
        uploads=uploads,
    )
