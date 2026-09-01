"""Impact selection: changed paths → packs/features for the PR bot."""

from __future__ import annotations

import fnmatch
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPACT_MAP = REPO_ROOT / "docs" / "regression" / "impact-map.yaml"


class ImpactError(Exception):
    def __init__(self, message: str, *, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class ImpactSelection:
    mode: str
    packs: List[str]
    features: List[str]
    matched_rules: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_impact_map(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DEFAULT_IMPACT_MAP
    if not p.is_file():
        raise ImpactError(f"Impact map not found: {p}", exit_code=2)
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _match(path: str, pattern: str) -> bool:
    # Support ** globs via fnmatch on normalized path
    norm = path.replace("\\", "/")
    pat = pattern.replace("\\", "/")
    if "**" in pat:
        # fnmatch does not treat ** specially; approximate
        parts = pat.split("**/")
        if len(parts) == 2 and parts[0] == "":
            return fnmatch.fnmatch(norm, parts[1]) or fnmatch.fnmatch(
                norm, f"*/{parts[1]}"
            ) or any(
                fnmatch.fnmatch(norm, f"{'*/' * i}{parts[1]}") for i in range(1, 8)
            )
        return fnmatch.fnmatch(norm, pat.replace("**/", "*/"))
    return fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(Path(norm).name, pat)


def select_impact(
    changed_files: Sequence[str],
    *,
    mode: str = "impacted",
    impact_map: Optional[Dict[str, Any]] = None,
) -> ImpactSelection:
    cfg = impact_map or load_impact_map()
    default_pack = str(cfg.get("default_pack") or "smoke")
    files = [f.replace("\\", "/") for f in changed_files]

    if mode in ("smoke", "full"):
        packs = [default_pack]
        if mode == "full":
            packs.append("auth_optional")
        return ImpactSelection(
            mode=mode,
            packs=list(dict.fromkeys(packs)),
            features=["FEATURE-PLATFORM"],
            matched_rules=["mode_override"],
            changed_files=files,
        )

    features: List[str] = []
    packs: List[str] = []
    matched: List[str] = []
    for idx, rule in enumerate(cfg.get("rules") or []):
        globs = list(rule.get("globs") or [])
        hit = any(_match(f, g) for f in files for g in globs)
        if not hit:
            continue
        matched.append(f"rule[{idx}]")
        for feat in rule.get("features") or []:
            if feat not in features:
                features.append(str(feat))
        for pack in rule.get("packs") or []:
            if pack not in packs:
                packs.append(str(pack))

    if not packs:
        packs = [default_pack]
        matched.append("default_pack")
        if not features:
            features = ["FEATURE-PLATFORM"]

    return ImpactSelection(
        mode="impacted",
        packs=packs,
        features=features,
        matched_rules=matched,
        changed_files=files,
    )


def expand_pack_tools(
    packs: Sequence[str],
    *,
    impact_map: Optional[Dict[str, Any]] = None,
    env: str = "epsilon",
) -> List[Dict[str, Any]]:
    cfg = impact_map or load_impact_map()
    pack_defs = cfg.get("packs") or {}
    steps: List[Dict[str, Any]] = []
    seen = set()
    for pack_name in packs:
        pack = pack_defs.get(pack_name) or {}
        for tool in pack.get("tools") or []:
            name = str(tool.get("name"))
            args = dict(tool.get("args") or {})
            # Allow env override for all tools that accept env
            if "env" in args:
                args["env"] = env
            key = (name, json_stable(args))
            if key in seen:
                continue
            seen.add(key)
            steps.append({"name": name, "args": args, "pack": pack_name})
    return steps


def json_stable(obj: Any) -> str:
    import json

    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
