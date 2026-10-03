"""
Accodite Uploads
================
Handles image and voice-note uploads. Stores files on disk under
UPLOAD_DIR, records an Artifact row, returns the artifact id.

Endpoints:
    POST /uploads/image      multipart file
    POST /uploads/voice      multipart file (webm / ogg)
    GET  /uploads/{id}       streams the file back (auth-checked)
    GET  /uploads/{id}/meta  returns artifact metadata
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from database import SessionLocal
from db_models import User, Artifact
from auth import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path(os.environ.get("ACCD_UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 25 * 1024 * 1024      # 25 MB cap

KIND_BY_MIME = {
    "image/png":  ("image", "png"),
    "image/jpeg": ("image", "jpg"),
    "image/jpg":  ("image", "jpg"),
    "image/gif":  ("image", "gif"),
    "image/webp": ("image", "webp"),
    "audio/webm": ("voice_note", "webm"),
    "audio/ogg":  ("voice_note", "ogg"),
    "audio/mpeg": ("voice_note", "mp3"),
    "audio/mp4":  ("voice_note", "m4a"),
    "audio/wav":  ("voice_note", "wav"),
}


def _ext_for(mime: str, filename: str = "") -> tuple:
    """Return (kind, ext) — fall back to filename extension if mime unknown."""
    if mime in KIND_BY_MIME:
        return KIND_BY_MIME[mime]
    # fallback by extension
    low = (filename or "").lower()
    for k, exts in (("image", (".png", ".jpg", ".jpeg", ".gif", ".webp")),
                    ("voice_note", (".webm", ".ogg", ".mp3", ".m4a", ".wav"))):
        for e in exts:
            if low.endswith(e):
                return k, e.lstrip(".")
    return None, None


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    return await _store(file, user, expected_kind="image")


@router.post("/voice")
async def upload_voice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    return await _store(file, user, expected_kind="voice_note")


async def _store(file: UploadFile, user: User, expected_kind: str) -> dict:
    kind, ext = _ext_for(file.content_type or "", file.filename or "")
    if kind is None:
        raise HTTPException(415, f"unsupported content type: {file.content_type}")
    if kind != expected_kind:
        raise HTTPException(400, f"expected {expected_kind}, got {kind}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"file too large ({len(data)} > {MAX_BYTES})")

    artifact_id = uuid.uuid4()
    user_dir = UPLOAD_DIR / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{artifact_id}.{ext}"
    path = user_dir / filename
    path.write_bytes(data)

    db = SessionLocal()
    try:
        art = Artifact(
            id=artifact_id,
            user_id=user.id,
            workspace_id=None,     # set when the message is posted
            kind=kind,
            name=file.filename or filename,
            path=str(path),
            size=len(data),
            metadata_json={"content_type": file.content_type, "ext": ext},
        )
        db.add(art)
        db.commit()
        return {
            "id": str(artifact_id),
            "kind": kind,
            "size": len(data),
            "content_type": file.content_type,
            "url": f"/uploads/{artifact_id}",
        }
    finally:
        db.close()


@router.get("/{artifact_id}")
async def get_upload(artifact_id: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        art = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if art is None or not art.path:
            raise HTTPException(404, "not found")
        p = Path(art.path)
        if not p.exists():
            raise HTTPException(404, "file missing on disk")
        return FileResponse(
            str(p),
            media_type=(art.metadata_json or {}).get("content_type") or "application/octet-stream",
            filename=art.name,
        )
    finally:
        db.close()


@router.get("/{artifact_id}/meta")
async def get_upload_meta(artifact_id: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        art = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if art is None:
            raise HTTPException(404, "not found")
        return {
            "id": str(art.id),
            "kind": art.kind,
            "name": art.name,
            "size": art.size,
            "url": f"/uploads/{art.id}",
            "created_at": art.created_at.isoformat() if art.created_at else None,
        }
    finally:
        db.close()


# ============================================================================
# PROFILE AVATAR
# ============================================================================

AVATAR_MAX = 3 * 1024 * 1024     # 3 MB


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    kind, ext = _ext_for(file.content_type or "", file.filename or "")
    if kind != "image":
        raise HTTPException(415, "avatar must be an image (png/jpg/gif/webp)")

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > AVATAR_MAX:
        raise HTTPException(413, f"avatar too large ({len(data)} > {AVATAR_MAX})")

    user_dir = UPLOAD_DIR / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"avatar.{ext}"
    path = user_dir / filename
    path.write_bytes(data)

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user.id).first()
        if u is None:
            raise HTTPException(404, "user not found")
        u.avatar_url = f"/uploads/avatar/{user.id}"
        # register artifact for tracking
        art = Artifact(
            id=uuid.uuid4(),
            user_id=user.id,
            workspace_id=None,
            kind="image",
            name="avatar",
            path=str(path),
            size=len(data),
            metadata_json={"content_type": file.content_type, "role": "avatar"},
        )
        db.add(art)
        db.commit()
        return {"ok": True, "avatar_url": u.avatar_url}
    finally:
        db.close()


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: str):
    """Public avatar read — no auth needed so <img> tags work without headers."""
    user_dir = UPLOAD_DIR / str(user_id)
    if not user_dir.exists():
        raise HTTPException(404, "no avatar")
    for ext in ("png", "jpg", "jpeg", "gif", "webp"):
        p = user_dir / f"avatar.{ext}"
        if p.exists():
            mt = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "gif": "image/gif", "webp": "image/webp"}[ext]
            return FileResponse(str(p), media_type=mt)
    raise HTTPException(404, "no avatar file")
