"""
Per-worker PSTM scope for rooms and departments.

Key: (org_phone_uid | personal, worker_phone_uid, workspace_id)
Hydrates name, role, department, title, conversation path.
AI must read this scope for the speaking worker — no cross-worker bleed.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

try:
    from phone_util import normalize_phone
except ImportError:
    def normalize_phone(p, default_country="NG"):
        return (p or "").strip()


def hydrate_worker_pstm(
    *,
    user=None,
    membership=None,
    workspace_id: str = "",
    org_phone: str = "",
    room_kind: str = "",
) -> Dict[str, Any]:
    phone = normalize_phone(getattr(user, "phone", None) or "")
    name = getattr(user, "full_name", None) or ""
    role = getattr(membership, "role", None) or getattr(user, "account_type", None) or ""
    dept = getattr(membership, "department", None) or ""
    title = getattr(membership, "title", None) or ""
    start_row = getattr(user, "start_row", None)
    start_col = getattr(user, "start_col", None)
    return {
        "pstm_id": phone or str(getattr(user, "id", "") or ""),
        "phone_uid": phone,
        "org_phone_uid": normalize_phone(org_phone) if org_phone else "",
        "name": name,
        "role": role,
        "department": dept,
        "title": title,
        "workspace_id": str(workspace_id or ""),
        "room_kind": room_kind or "",
        "message_box": {"start_row": start_row, "start_col": start_col},
        "conversation_path": f"ws:{workspace_id}|phone:{phone}",
        "pattern": {},  # filled by later turns
    }


def apply_pstm_scope(pstm, room_id: str, pstm_id: str, scope: Dict[str, Any]) -> None:
    if pstm is None or not pstm_id:
        return
    try:
        for k, v in scope.items():
            pstm.set_extra(room_id, pstm_id, k, v)
    except Exception as e:
        print("[pstm_scope] apply:", type(e).__name__, e)
