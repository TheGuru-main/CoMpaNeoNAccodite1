"""
Accodite Weight Relay
=====================
Accepts trained weights from an external trainer (phone, VM, batch job)
and hot-swaps them into the live model.

Endpoints:
    POST /weights/upload     multipart upload of companion_model.pth
    POST /weights/upload_vocab   companion vocab JSON (optional)
    GET  /weights/status     current weights mtime + size
    POST /weights/reload     force a model reload from disk

Auth: PUBLIC_API_KEY header (X-API-Key) or Bearer token.
The endpoint is a no-op unless WEIGHTS_RELAY_TOKEN env var matches.
"""
from __future__ import annotations
import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/weights", tags=["weights"])

WEIGHTS_DIR = Path(os.environ.get("ACCD_WEIGHTS_DIR", os.getcwd()))
WEIGHTS_FILE = WEIGHTS_DIR / "companion_model.pth"
VOCAB_FILE = WEIGHTS_DIR / "tokenizer_vocab.json"
RELAY_TOKEN = os.environ.get("WEIGHTS_RELAY_TOKEN", "")

MAX_BYTES = 500 * 1024 * 1024   # 500 MB cap


# ============================================================================
# AUTH
# ============================================================================

def _check_auth(x_api_key: Optional[str], authorization: Optional[str]) -> None:
    """Accept either X-API-Key or Bearer token, both must match RELAY_TOKEN."""
    if not RELAY_TOKEN:
        raise HTTPException(503, "weights relay disabled: WEIGHTS_RELAY_TOKEN not set")

    presented = None
    if x_api_key:
        presented = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()

    if not presented or presented != RELAY_TOKEN:
        raise HTTPException(401, "invalid or missing relay token")


# ============================================================================
# HELPERS
# ============================================================================

def _write_atomic(target: Path, data: bytes) -> str:
    """Write bytes to target atomically. Returns sha256 hex."""
    tmp = target.with_suffix(target.suffix + ".incoming")
    tmp.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    tmp.replace(target)
    return digest


def _file_status(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    st = path.stat()
    return {
        "exists": True,
        "size": st.st_size,
        "mtime": st.st_mtime,
        "mtime_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)),
        "path": str(path),
    }


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/upload")
async def upload_weights(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """Receive companion_model.pth and swap it in."""
    _check_auth(x_api_key, authorization)

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"file too large: {len(data)} bytes > {MAX_BYTES}")

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    # keep one backup
    if WEIGHTS_FILE.exists():
        backup = WEIGHTS_FILE.with_suffix(".pth.bak")
        try:
            shutil.copy2(WEIGHTS_FILE, backup)
        except Exception:
            pass

    digest = _write_atomic(WEIGHTS_FILE, data)

    # try to hot-reload if main.py exposes a reload hook
    reload_result = _try_reload()

    return {
        "ok": True,
        "sha256": digest,
        "bytes": len(data),
        "status": _file_status(WEIGHTS_FILE),
        "reload": reload_result,
    }


@router.post("/upload_vocab")
async def upload_vocab(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """Receive tokenizer_vocab.json if training changed the vocab."""
    _check_auth(x_api_key, authorization)

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(413, "vocab too large")

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    digest = _write_atomic(VOCAB_FILE, data)

    return {
        "ok": True,
        "sha256": digest,
        "bytes": len(data),
        "status": _file_status(VOCAB_FILE),
    }


@router.get("/status")
async def weights_status():
    """Public read-only status — no auth required (no secrets leaked)."""
    return {
        "weights": _file_status(WEIGHTS_FILE),
        "vocab": _file_status(VOCAB_FILE),
        "relay_enabled": bool(RELAY_TOKEN),
    }


@router.post("/reload")
async def reload_weights(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """Force the live model to reload from disk."""
    _check_auth(x_api_key, authorization)
    return _try_reload()


# ============================================================================
# RELOAD HOOK
# ============================================================================

def _try_reload() -> dict:
    """
    Ask main.py to reload the model. main.py must expose:
        reload_model_if_exists() -> dict | None
    """
    try:
        import main as _main
    except Exception:
        try:
            from backend import main as _main  # type: ignore
        except Exception:
            return {"reloaded": False, "reason": "main module not importable"}

    for name in ("reload_model_if_exists", "load_model_if_exists"):
        fn = getattr(_main, name, None)
        if callable(fn):
            try:
                result = fn()
                return {"reloaded": True, "hook": name,
                        "result": str(result)[:200] if result else None}
            except Exception as e:
                return {"reloaded": False, "hook": name,
                        "error": f"{type(e).__name__}: {e}"}

    return {"reloaded": False, "reason": "no reload hook found on main"}
