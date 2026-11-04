"""
Surfaces inside an org|user instance MemoryGrid.

DBase, SheetS, CollabSheet, Presentations, Codespace are NOT separate global
brains. They are marked namespaces (grids-in-grid) on the owner instance grid
so members / AI can scope workflow, schedules, and monitoring by marker.

Owner key remains phone UID: org:<phone> | user:<phone>.

Markers (metadata.grid_ns):
  dbase | sheets | collabsheet | presentations | codespace | schedule | workflow

Each record should carry:
  grid_ns, object_name, doc_uid (letter-chain), description,
  owner_phone_uid, workspace_id (optional), start_row (placement if any)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

NAMESPACES = (
    "dbase",
    "sheets",
    "collabsheet",
    "presentations",
    "codespace",
    "schedule",
    "workflow",
)

MARKER_PREFIX = {
    "dbase": "ns:dbase",
    "sheets": "ns:sheets",
    "collabsheet": "ns:collab",
    "presentations": "ns:pres",
    "codespace": "ns:codespace",
    "schedule": "ns:schedule",
    "workflow": "ns:workflow",
}


def assert_ns(ns: str) -> str:
    ns = (ns or "").strip().lower()
    if ns not in NAMESPACES:
        raise ValueError(f"unknown grid namespace {ns!r}; expected one of {NAMESPACES}")
    return ns


def build_metadata(
    *,
    ns: str,
    object_name: str,
    doc_uid: str = "",
    description: str = "",
    owner_phone_uid: str = "",
    workspace_id: str = "",
    start_row: Optional[int] = None,
    start_col: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ns = assert_ns(ns)
    meta = {
        "grid_ns": ns,
        "marker": MARKER_PREFIX[ns],
        "object_name": object_name,
        "doc_uid": doc_uid,
        "description": description or "",
        "owner_phone_uid": owner_phone_uid or "",
        "workspace_id": str(workspace_id or ""),
        "start_row": start_row,
        "start_col": start_col,
    }
    if extra:
        meta.update(extra)
    return meta


def place_in_owner_grid(
    grid,
    *,
    ns: str,
    object_name: str,
    text: str,
    description: str = "",
    owner_phone_uid: str = "",
    workspace_id: str = "",
    lang: str = "en",
    extra: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Write a namespace object into the owner instance MemoryGrid.
    Uses tokenizer letter-chain for doc_uid when available.
    """
    if grid is None:
        raise RuntimeError("owner grid required")
    ns = assert_ns(ns)
    doc_uid = ""
    start_row = None
    try:
        from tokenizer.tokenizer import uid_for_token, lexical_S, lexical_L, first_letter_index
        doc_uid = uid_for_token(object_name, lang)
        # placement coords for the object name (placement uses name+rules callers may override)
        L = lexical_L(object_name, lang)
        S = lexical_S(object_name, lang)  # token-chain sum for name identity in grid meta
        # Note: GSP user placement S remains phone digit sum elsewhere
        c = first_letter_index(object_name, lang) or 0
        start_row = ((L + S - 1) % 64) + 1
    except Exception:
        try:
            from gsp_chain import uid_from_name, start_row_for_name
            doc_uid = uid_from_name(object_name)
            info = start_row_for_name(object_name)
            start_row = info.get("start_row")
        except Exception:
            doc_uid = object_name

    body = text if text else f"{object_name}\n{description}".strip()
    meta = build_metadata(
        ns=ns,
        object_name=object_name,
        doc_uid=str(doc_uid),
        description=description,
        owner_phone_uid=owner_phone_uid,
        workspace_id=workspace_id,
        start_row=start_row,
        extra=extra,
    )
    meta["source_marker"] = MARKER_PREFIX[ns]
    if hasattr(grid, "add_document"):
        return grid.add_document(body, lang=lang, source=MARKER_PREFIX[ns], metadata=meta)
    raise RuntimeError("grid has no add_document")


def list_namespace(grid, ns: str, *, workspace_id: str = "") -> List[Dict[str, Any]]:
    """List documents in a namespace on this owner grid (for member/AI monitor)."""
    ns = assert_ns(ns)
    out: List[Dict[str, Any]] = []
    docs = getattr(grid, "documents", None) or {}
    if isinstance(docs, dict):
        items = docs.values()
    else:
        items = docs
    for doc in items:
        if not isinstance(doc, dict):
            continue
        meta = doc.get("metadata") or doc.get("meta") or {}
        if meta.get("grid_ns") != ns and doc.get("source") != MARKER_PREFIX[ns]:
            # also accept source string
            if not str(doc.get("source") or "").startswith("ns:" + ns[:4]):
                if meta.get("marker") != MARKER_PREFIX[ns]:
                    continue
        if workspace_id and str(meta.get("workspace_id") or "") not in ("", str(workspace_id)):
            continue
        out.append({
            "object_name": meta.get("object_name") or doc.get("id"),
            "doc_uid": meta.get("doc_uid"),
            "description": meta.get("description") or "",
            "start_row": meta.get("start_row"),
            "workspace_id": meta.get("workspace_id"),
            "owner_phone_uid": meta.get("owner_phone_uid"),
            "grid_ns": ns,
            "text_preview": (doc.get("text") or "")[:200],
        })
    return out


def monitor_workflow(grid, *, workspace_id: str = "") -> Dict[str, List[Dict[str, Any]]]:
    """Aggregate all surface namespaces for org member / AI monitoring."""
    return {ns: list_namespace(grid, ns, workspace_id=workspace_id) for ns in NAMESPACES}
