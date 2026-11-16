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
    replace_existing: bool = True,
) -> Any:
    """
    Single write path for DBase/Sheets/Collab/Pres into the owner instance grid.

    - Namespace (ns) is a surface marker only.
    - Placement ONLY via gsp_chain.content_place_from_name (full uid_chain → S=abs → start_row).
    - doc_uid = full serialized chain (letters + digit markers + code symbol ids).
    - Dedupe key: (grid_ns, doc_uid) within this owner grid.
    """
    if grid is None:
        raise RuntimeError("owner grid required")
    ns = assert_ns(ns)
    try:
        from gsp_chain import validate_resource_name
        object_name = validate_resource_name(object_name, what="object name")
    except Exception as e:
        raise ValueError(f"invalid object name: {e}") from e

    # M4.1 — single place path: content_place_from_name only (full uid_chain + abs S)
    start_row = None
    start_col = None
    doc_uid = ""
    place_info = {}
    try:
        from gsp_chain import content_place_from_name
        place_info = content_place_from_name(object_name, lang=lang) or {}
        start_row = int(place_info.get("start_row") or 0) or None
        if place_info.get("start_col") is not None:
            start_col = int(place_info["start_col"])
        elif place_info.get("c") is not None:
            start_col = int(place_info["c"])
        doc_uid = str(
            place_info.get("uid")
            or place_info.get("uid_str")
            or ""
        )
        if not doc_uid:
            raise RuntimeError("content_place returned empty uid")
    except Exception as e:
        print("[ns] gsp content_place:", type(e).__name__, e)
        raise ValueError(f"GSP place failed for {object_name!r}: {e}") from e

    body = text or description or object_name
    _extra = dict(extra or {})
    if place_info:
        _extra.setdefault("gsp_S", place_info.get("S"))
        _extra.setdefault("gsp_L", place_info.get("L"))
        _extra.setdefault("gsp_c", place_info.get("c"))
        _extra.setdefault("gsp_lang", place_info.get("lang"))
        _extra.setdefault("digit_markers", place_info.get("digit_markers") or [])
        _extra.setdefault("symbol_uids", place_info.get("symbol_uids") or [])
        _extra.setdefault("place_source", place_info.get("source") or "content_place_from_name")
    meta = build_metadata(
        ns=ns,
        object_name=object_name,
        doc_uid=str(doc_uid),
        description=description,
        owner_phone_uid=owner_phone_uid,
        workspace_id=workspace_id,
        start_row=start_row,
        start_col=start_col,
        extra=_extra,
    )
    meta["source_marker"] = MARKER_PREFIX[ns]
    meta["doc_uid"] = str(doc_uid)

    # Dedupe: same ns + doc_uid on this owner grid → update in place (or skip)
    existing_id = None
    docs = getattr(grid, "documents", None) or {}
    items = docs.items() if isinstance(docs, dict) else enumerate(docs)
    for did, doc in items:
        if not isinstance(doc, dict):
            continue
        m = doc.get("metadata") or doc.get("meta") or {}
        if m.get("grid_ns") != ns:
            continue
        if str(m.get("doc_uid") or "") == str(doc_uid) or (
            str(m.get("object_name") or "").lower() == object_name.lower()
        ):
            existing_id = did
            break

    if existing_id is not None and not replace_existing:
        return {
            "doc_id": existing_id,
            "doc_uid": doc_uid,
            "start_row": start_row,
            "start_col": start_col,
            "object_name": object_name,
            "ns": ns,
            "deduped": True,
            "replaced": False,
        }

    if hasattr(grid, "add_document"):
        if existing_id is not None and replace_existing and isinstance(docs, dict):
            # Replace body/meta; keep same id when possible
            try:
                docs[existing_id] = {
                    **(docs.get(existing_id) or {}),
                    "text": body,
                    "metadata": meta,
                    "source": MARKER_PREFIX[ns],
                }
                doc_id = existing_id
            except Exception:
                doc_id = grid.add_document(body, lang=lang, source=MARKER_PREFIX[ns], metadata=meta)
        else:
            doc_id = grid.add_document(body, lang=lang, source=MARKER_PREFIX[ns], metadata=meta)
        return {
            "doc_id": doc_id,
            "doc_uid": doc_uid,
            "start_row": start_row,
            "start_col": start_col,
            "object_name": object_name,
            "ns": ns,
            "deduped": existing_id is not None,
            "replaced": existing_id is not None and replace_existing,
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


def lookup_by_name(grid, ns: str, object_name: str, *, lang: str = "en") -> Optional[Dict[str, Any]]:
    """Resolve object by name using the same GSP identity as place."""
    ns = assert_ns(ns)
    try:
        from gsp_chain import start_row_for_name, validate_resource_name
        object_name = validate_resource_name(object_name, what="object name")
        place = start_row_for_name(object_name, lang=lang)
        doc_uid = str(place.get("uid") or place.get("uid_str") or "")
    except Exception:
        doc_uid = ""
        place = {}
    for row in list_namespace(grid, ns):
        if str(row.get("doc_uid") or "") == doc_uid or (
            str(row.get("object_name") or "").lower() == object_name.lower()
        ):
            row = dict(row)
            row["placement"] = {
                "start_row": place.get("start_row") or row.get("start_row"),
                "start_col": place.get("start_col") or row.get("start_col"),
                "doc_uid": doc_uid or row.get("doc_uid"),
            }
            return row
    return None
