"""HTTP helpers for namespace place/list on the bound owner grid."""
from __future__ import annotations
from typing import Any, Optional, Dict


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
    Place object (+ optional media) onto owner MemoryGrid namespace.
    Lookup uses object_name, description, metadata (media_type, filename, mime).
    Large binaries should pass payload_ref (B2/URL/path); small text/docs may use text/payload_b64.
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
    media_type = (media_type or "").strip().lower()
    if not media_type and filename:
        fn = filename.lower()
        if fn.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic")):
            media_type = "image"
        elif fn.endswith((".mp3", ".wav", ".m4a", ".ogg", ".aac")):
            media_type = "voice"
        elif fn.endswith((".mp4", ".webm", ".mov")):
            media_type = "video"
        elif fn.endswith((".pdf", ".doc", ".docx", ".txt", ".md")):
            media_type = "doc"
        else:
            media_type = "file"

    meta_extra = dict(extra or {})
    meta_extra.update({
        "media_type": media_type or "text",
        "mime": mime or "",
        "filename": filename or "",
        "payload_ref": payload_ref or "",
        "has_payload_b64": bool(payload_b64),
    })
    # Keep b64 off metadata if huge — store short marker only
    if payload_b64 and len(payload_b64) < 120_000:
        meta_extra["payload_b64_len"] = len(payload_b64)
        body_extra = f"\n[payload_b64_len={len(payload_b64)}]"
    else:
        body_extra = ""
        if payload_b64:
            meta_extra["payload_b64_len"] = len(payload_b64)
            meta_extra["payload_inline"] = False

    body = (text or description or object_name or "").strip()
    about = [
        f"object: {object_name}",
        f"about: {description}" if description else "",
        f"media: {media_type}" if media_type else "",
        f"file: {filename}" if filename else "",
        f"ref: {payload_ref}" if payload_ref else "",
    ]
    body = body + "\n" + "\n".join(x for x in about if x) + body_extra

    doc_id = place_in_owner_grid(
        grid,
        ns=ns,
        object_name=object_name,
        text=body,
        description=description,
        owner_phone_uid=owner_phone,
        workspace_id=workspace_id,
        extra=meta_extra,
    )
    return {
        "ok": True,
        "doc_id": doc_id,
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
