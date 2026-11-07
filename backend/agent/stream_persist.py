"""
Persist streamed AI replies after /generate/stream completes.
DB Message(role=ai) + B2/local snapshot under owner phone + workspace.
"""
from __future__ import annotations
import json
import os
import time
import uuid
from typing import Any, Optional


def _phone_uid(user) -> str:
    try:
        from memory.owner_identity import phone_uid
        return phone_uid(getattr(user, "phone", None)) or str(getattr(user, "id", ""))
    except Exception:
        return str(getattr(user, "id", "") or "anon")


def _org_phone(org_id: Optional[str]) -> str:
    if not org_id:
        return ""
    try:
        from memory.owner_identity import resolve_org_phone
        return resolve_org_phone(org_id=org_id) or ""
    except Exception:
        return ""


def _parse_uuid(val):
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except Exception:
        return None


def persist_stream_ai_reply(
    *,
    user,
    text: str,
    workspace_id: Optional[str] = None,
    room_id: Optional[str] = None,
    org_id: Optional[str] = None,
    ref_message_id: Optional[str] = None,
    prompt: str = "",
) -> dict:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty"}

    ws = (workspace_id or room_id or "").strip()
    msg_id = None
    b2_key = None
    owner = _org_phone(org_id) or _phone_uid(user)
    kind = "org" if org_id else "user"
    db_error = None

    if ws:
        try:
            from database import SessionLocal
            # prefer same import path as rooms.py
            try:
                from db_models import Message, Workspace
            except Exception:
                from db.db_models import Message, Workspace

            ws_uuid = _parse_uuid(ws)
            if ws_uuid is None:
                db_error = f"bad workspace_id {ws!r}"
            else:
                db = SessionLocal()
                try:
                    exists = db.query(Workspace).filter(Workspace.id == ws_uuid).first()
                    if not exists:
                        db_error = "workspace not found"
                    else:
                        ref = _parse_uuid(ref_message_id)
                        row = Message(
                            id=uuid.uuid4(),
                            workspace_id=ws_uuid,
                            user_id=user.id,
                            role="ai",
                            content=text[:50000],
                            replies_to=ref,
                            detected_domain="general",
                            keywords=[],
                            grid_cv={"source": "stream"},
                            temporal_context={
                                "source": "stream",
                                "prompt_preview": (prompt or "")[:200],
                            },
                        )
                        db.add(row)
                        db.commit()
                        db.refresh(row)
                        msg_id = str(row.id)
                finally:
                    db.close()
        except Exception as e:
            db_error = f"{type(e).__name__}: {e}"
            print("[stream_persist] db:", db_error)

    payload = {
        "role": "ai",
        "text": text[:50000],
        "workspace_id": ws,
        "org_id": org_id or "",
        "owner": owner,
        "kind": kind,
        "ref_message_id": ref_message_id or "",
        "prompt_preview": (prompt or "")[:300],
        "message_id": msg_id,
        "ts": int(time.time()),
    }
    key = f"streams/{kind}/{owner or 'anon'}/{ws or 'home'}/{int(time.time())}_{uuid.uuid4().hex[:10]}.json"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        from storage.b2 import b2_enabled, b2_put_bytes
        if b2_enabled() and os.environ.get("ACCD_B2_ENABLED", "1") not in ("0", "false", "False"):
            b2_key = b2_put_bytes(key, raw, content_type="application/json; charset=utf-8")
        else:
            raise RuntimeError("b2 off")
    except Exception as e:
        print("[stream_persist] b2:", type(e).__name__, e)
        try:
            from pathlib import Path
            root_dir = Path(os.environ.get("ACCD_UPLOAD_DIR") or "/tmp/accd-uploads")
            dest = root_dir / "streams" / kind / (owner or "anon") / (ws or "home")
            dest.mkdir(parents=True, exist_ok=True)
            path = dest / f"{int(time.time())}_{uuid.uuid4().hex[:10]}.json"
            path.write_bytes(raw)
            b2_key = f"file://{path}"
        except Exception as e2:
            print("[stream_persist] local:", type(e2).__name__, e2)

    ok = bool(msg_id) or bool(b2_key)
    return {
        "ok": ok,
        "message_id": msg_id,
        "snapshot": b2_key,
        "owner": owner,
        "kind": kind,
        "db_error": db_error,
        "workspace_id": ws,
    }
