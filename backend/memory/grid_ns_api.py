"""HTTP helpers for namespace place/list on the bound owner grid."""
from __future__ import annotations
import base64
import os
import uuid
from pathlib import Path
from typing import Any, Optional, Dict


def _store_blob(
    *,
    raw: bytes,
    filename: str,
    mime: str,
    owner_phone: str,
) -> str:
    """
    Persist binary on Accodite storage — never on a third-party chat host.
    Prefer B2; else local ACCD_UPLOAD_DIR. Returns payload_ref string.
    """
    safe_name = "".join(c for c in (filename or "blob") if c.isalnum() or c in "._-")[:80] or "blob"
    key = f"placements/{owner_phone or 'anon'}/{uuid.uuid4().hex[:12]}_{safe_name}"
    try:
        from storage.b2 import b2_enabled, b2_put_bytes
        if b2_enabled():
            return b2_put_bytes(key, raw, content_type=mime or "application/octet-stream")
    except Exception as e:
        print("[place] B2 put failed:", type(e).__name__, e)
    # local disk fallback (Render disk / uploads)
    root = Path(os.environ.get("ACCD_UPLOAD_DIR") or os.environ.get("ACCD_SANDBOX_ROOT") or "/tmp/accd-uploads")
    dest = root / "placements" / (owner_phone or "anon")
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{uuid.uuid4().hex[:12]}_{safe_name}"
    path.write_bytes(raw)
    return f"file://{path}"


def place_ns_object(
    *,
    ns: str,
    object_name: str,
    text: str = "",
    description: str = "",
    user_id: str = "",
    org_id: str = "",
    user_phone: str = "",
    org_phone: str = "",
    workspace_id: str = "",
    media_type: str = "",
    mime: str = "",
    filename: str = "",
    payload_ref: str = "",
    payload_b64: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Place object onto owner MemoryGrid namespace.

    Storage model:
      - Grid holds name, description, doc_uid, media meta, payload_ref (pointer).
      - Binary lives on Accodite B2 or local upload dir — NOT inline in the grid,
        NOT on any external AI host (Grok/OpenAI/etc.).
      - payload_b64 is a *transport* option from the client only; we decode, store,
        then drop b64 from permanent metadata.
    """
    from memory.grid_request import bind_request_grid
    from memory.grid_namespaces import place_in_owner_grid, assert_ns

    assert_ns(ns)
    grid = bind_request_grid(
        user_id=user_id or None,
        org_id=org_id or None,
        user_phone=user_phone or None,
        org_phone=org_phone or None,
    )
    if grid is None:
        return {"ok": False, "error": "owner grid unavailable"}

    owner_phone = org_phone or user_phone or ""

    ownership = None
    try:
        from memory.ownership_scope import resolve_ownership
        # surface from ns
        surface = {"dbase": "dbase", "sheets": "sheets", "collabsheet": "collabsheet",
                   "pres": "presentations", "presentations": "presentations"}.get(ns, ns)
        # user object minimal
        class _U:
            pass
        u = _U()
        u.id = user_id
        u.phone = user_phone
        u.account_type = "regular"
        ownership = resolve_ownership(
            user=u, surface=surface, room_id=workspace_id, org_id=org_id,
        )
    except Exception as _oe:
        print("[ns] ownership:", type(_oe).__name__, _oe)

    media_type = (media_type or "").strip().lower()
    if not media_type and filename:
        fn = filename.lower()
        if fn.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic")):
            media_type = "image"
        elif fn.endswith((".mp3", ".wav", ".m4a", ".ogg", ".aac", ".webm")):
            media_type = "voice"
        elif fn.endswith((".mp4", ".webm", ".mov")):
            media_type = "video"
        elif fn.endswith((".pdf", ".doc", ".docx", ".txt", ".md")):
            media_type = "doc"
        elif fn.endswith((".xlsx", ".xls", ".csv", ".ods")):
            media_type = "spreadsheet"
        else:
            media_type = "file"

    # Transport b64 → durable ref on Accodite storage
    if payload_b64 and not payload_ref:
        try:
            raw = base64.b64decode(payload_b64)
            if len(raw) > 25 * 1024 * 1024:
                return {"ok": False, "error": "file too large (max 25MB)"}
            payload_ref = _store_blob(
                raw=raw,
                filename=filename or "upload.bin",
                mime=mime or "application/octet-stream",
                owner_phone=owner_phone,
            )
        except Exception as e:
            return {"ok": False, "error": f"store failed: {type(e).__name__}: {e}"}

    meta_extra = dict(extra or {})
    meta_extra.update({
        "media_type": media_type or "text",
        "mime": mime or "",
        "filename": filename or "",
        "payload_ref": payload_ref or "",
        # never persist client b64
        "has_payload": bool(payload_ref),
    })

    body = (text or description or object_name or "").strip()
    about = [
        f"object: {object_name}",
        f"about: {description}" if description else "",
        f"media: {media_type}" if media_type else "",
        f"file: {filename}" if filename else "",
        f"ref: {payload_ref}" if payload_ref else "",
    ]
    body = body + "\n" + "\n".join(x for x in about if x)

    placed = place_in_owner_grid(
        grid,
        ns=ns,
        object_name=object_name,
        text=body,
        description=description,
        owner_phone_uid=owner_phone,
        workspace_id=workspace_id,
        extra=meta_extra,
    )

    # Durable instance grid (not temp): GSP already wrote into owner MemoryGrid;
    # namespace only marks sector (dbase/sheets/...). Persist local + B2 partition.
    persist_info = {"ok": False}
    try:
        from memory.instance_grid import OwnerRef, persist_owner_grid
        from memory.owner_identity import phone_uid as _puid
        kind = "user"
        phone = owner_phone
        if ownership is not None:
            kind = "org" if getattr(ownership, "kind", "") == "org" else "user"
            phone = getattr(ownership, "phone_uid", None) or getattr(ownership, "owner_id", None) or phone
        if not phone:
            phone = _puid(org_phone or user_phone) or ""
        if phone:
            persist_info = persist_owner_grid(OwnerRef(kind, str(phone)), grid)
        else:
            persist_info = {"ok": False, "error": "no owner phone for persist"}
    except Exception as _pe:
        persist_info = {"ok": False, "error": f"{type(_pe).__name__}: {_pe}"}
        print("[ns] persist_owner_grid:", persist_info["error"])

    if isinstance(placed, dict):
        placed = dict(placed)
        placed["persist"] = persist_info
        return {
            "ok": True,
            "doc_id": placed.get("doc_id"),
            "doc_uid": placed.get("doc_uid"),
            "start_row": placed.get("start_row"),
            "start_col": placed.get("start_col"),
            "ns": ns,
            "object_name": object_name,
            "description": description,
            "media_type": media_type or "text",
            "filename": filename or "",
            "payload_ref": payload_ref or "",
            "placement": {
                "start_row": placed.get("start_row"),
                "start_col": placed.get("start_col"),
                "doc_uid": placed.get("doc_uid"),
            },
        }
    return {
        "ok": True,
        "doc_id": placed,
        "ns": ns,
        "object_name": object_name,
        "description": description,
        "media_type": media_type or "text",
        "filename": filename or "",
        "payload_ref": payload_ref or "",
    }


def list_ns(
    *,
    ns: str,
    user_id: str = "",
    org_id: str = "",
    user_phone: str = "",
    org_phone: str = "",
    workspace_id: str = "",
    q: str = "",
) -> dict:
    from memory.grid_request import bind_request_grid
    from memory.grid_namespaces import list_namespace, monitor_workflow, assert_ns

    grid = bind_request_grid(
        user_id=user_id or None,
        org_id=org_id or None,
        user_phone=user_phone or None,
        org_phone=org_phone or None,
    )
    if grid is None:
        return {"ok": False, "error": "owner grid unavailable", "items": []}
    if ns in ("*", "all", "monitor"):
        return {"ok": True, "monitor": monitor_workflow(grid, workspace_id=workspace_id)}
    assert_ns(ns)
    items = list_namespace(grid, ns, workspace_id=workspace_id)
    qq = (q or "").strip().lower()
    if qq:
        def hit(it: dict) -> bool:
            blob = " ".join(
                str(it.get(k) or "")
                for k in ("object_name", "description", "doc_uid", "text_preview", "media_type", "filename")
            ).lower()
            meta = it.get("meta") or {}
            blob += " " + " ".join(str(meta.get(k) or "") for k in ("mime", "filename", "media_type", "description"))
            return qq in blob
        items = [it for it in items if hit(it)]
    return {"ok": True, "ns": ns, "items": items, "q": q}
