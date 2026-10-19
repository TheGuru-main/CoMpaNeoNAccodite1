"""
Project workspace directories and head-scope tags.

Directory is by project:

    data/workspaces/{project_id}/repo
    data/workspaces/{project_id}/ingest

Internal scopes: personal, org, room, group, meeting, dept.
Each scope is its own segment ({project}:{scope}).
Pools stay the existing four. Attention weights are not changed.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Canonical scope -> existing HeadAllocator pool kind.
SCOPE_POOL = {
    "personal": "personal",
    "org": "org",
    "dept": "org",
    "room": "room",
    "meeting": "room",
    "group": "shared",
}

_ALIASES = {
    "groups": "group",
    "department": "dept",
    "departments": "dept",
    "meetings": "meeting",
}

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_scope(value: Any) -> Optional[str]:
    raw = str(value or "").strip().lower()
    raw = _ALIASES.get(raw, raw)
    if raw in SCOPE_POOL:
        return raw
    return None


def project_id_of(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "default"
    cleaned = _SAFE.sub("-", raw).strip(".-")
    return cleaned[:80] or "default"


def workspaces_root(base: Optional[str] = None) -> Path:
    root = base or os.environ.get("ACCD_WORKSPACES") or "data/workspaces"
    return Path(root)


def project_dir(project_id: str, base: Optional[str] = None) -> Path:
    return workspaces_root(base) / project_id_of(project_id)


def ensure_project_dirs(project_id: str, base: Optional[str] = None) -> Dict[str, str]:
    root = project_dir(project_id, base)
    repo = root / "repo"
    ingest = root / "ingest"
    repo.mkdir(parents=True, exist_ok=True)
    ingest.mkdir(parents=True, exist_ok=True)
    log = root / "console.log"
    if not log.exists():
        log.write_text("", encoding="utf-8")
    return {
        "project_id": project_id_of(project_id),
        "root": str(root.resolve()),
        "repo": str(repo.resolve()),
        "ingest": str(ingest.resolve()),
        "console_log": str(log.resolve()),
    }


def stamp_document(document: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(document, dict):
        return document
    meta = document.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        document["metadata"] = meta
    scope = normalize_scope(
        document.get("scope") or meta.get("scope") or meta.get("kind")
    )
    if scope is None:
        return document
    pid = project_id_of(
        document.get("project_id") or meta.get("project_id") or "default"
    )
    document["scope"] = scope
    document["project_id"] = pid
    meta["scope"] = scope
    meta["project_id"] = pid
    meta["segment_id"] = f"{pid}:{scope}"
    meta["pool"] = SCOPE_POOL[scope]
    return document


def scope_of(document: Dict[str, Any]) -> Optional[str]:
    if not isinstance(document, dict):
        return None
    meta = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    return normalize_scope(document.get("scope") or meta.get("scope") or meta.get("kind"))


def segments_from_docs(docs: Iterable[Dict[str, Any]]):
    """One Segment per distinct project:scope. Unscoped docs are skipped."""
    from model.head_router import Segment

    seen = []
    out = []
    for doc in docs or []:
        if not isinstance(doc, dict):
            continue
        scope = scope_of(doc)
        if scope is None:
            continue
        meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        pid = project_id_of(doc.get("project_id") or meta.get("project_id") or "default")
        sid = f"{pid}:{scope}"
        if sid in seen:
            continue
        seen.append(sid)
        out.append(Segment(segment_id=sid, kind=scope))
    return out


def plan_for_docs(docs: Iterable[Dict[str, Any]]):
    from model.head_router import HeadAllocator

    alloc = HeadAllocator()
    return alloc.plan(segments_from_docs(docs))


def remember_query_plan(plan, docs: Optional[List[Dict[str, Any]]] = None) -> None:
    try:
        from integration import get_state
    except ImportError:
        return
    state = get_state()
    state["head_plan"] = plan
    state["head_segments"] = [
        {"segment_id": s.segment_id, "kind": s.kind}
        for s in segments_from_docs(docs or [])
    ]


def current_head_plan():
    try:
        from integration import get_state
    except ImportError:
        return None
    return get_state().get("head_plan")
