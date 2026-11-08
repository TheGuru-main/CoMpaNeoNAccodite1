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
    Placement: GSP start_row from object name letter-chain (L+S), not token S.
    """
    if grid is None:
        raise RuntimeError("owner grid required")
    ns = assert_ns(ns)
    start_row = None
    start_col = None
    doc_uid = ""
    try:
        from gsp_chain import start_row_for_name, uid_from_name, letter_chain
        place = start_row_for_name(object_name, lang=lang)
        start_row = int(place.get("start_row") or 0) or None
        doc_uid = str(place.get("uid") or place.get("uid_str") or place.get("uid_compact") or uid_from_name(object_name, lang=lang) or "")
        chain = place.get("chain")
        if chain is None:
            try:
                chain = letter_chain(object_name, lang=lang)
            except Exception:
                chain = []
        if chain:
            start_col = int(chain[0]) % 54
    except Exception as e:
        print("[ns] gsp place:", type(e).__name__, e)
        try:
            from gsp_chain import uid_from_name
            doc_uid = uid_from_name(object_name, lang=lang)
        except Exception:
            doc_uid = object_name

    body = text or description or object_name
    meta = build_metadata(
        ns=ns,
        object_name=object_name,
        doc_uid=str(doc_uid),
        description=description,
        owner_phone_uid=owner_phone_uid,
        workspace_id=workspace_id,
        start_row=start_row,
        start_col=start_col,
        extra=extra,
    )
    meta["source_marker"] = MARKER_PREFIX[ns]
    if hasattr(grid, "add_document"):
        return {
            "doc_id": grid.add_document(body, lang=lang, source=MARKER_PREFIX[ns], metadata=meta),
            "doc_uid": doc_uid,
            "start_row": start_row,
            "start_col": start_col,
            "object_name": object_name,
            "ns": ns,
        }
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
            "media_type": meta.get("media_type") or "text",
            "mime": meta.get("mime") or "",
            "filename": meta.get("filename") or "",
            "payload_ref": meta.get("payload_ref") or "",
            "text_preview": (doc.get("text") or "")[:200],
            "meta": {
                "media_type": meta.get("media_type"),
                "mime": meta.get("mime"),
                "filename": meta.get("filename"),
                "description": meta.get("description"),
            },
        })
    return out


def monitor_workflow(grid, *, workspace_id: str = "") -> Dict[str, List[Dict[str, Any]]]:
    """Aggregate all surface namespaces for org member / AI monitoring."""
    return {ns: list_namespace(grid, ns, workspace_id=workspace_id) for ns in NAMESPACES}
