"""
Accodite LoRA Cache
===================
Per-account LoRA adapters as a cache layer.

Concept:
    base model       = shared per instance (companion_model.pth)
    lora cache       = per account (buckets/{account_id}/lora.safetensors)
    cache invalidation happens when the base model changes (hash check)

Public:
    get(account_id)          -> path or None
    put(account_id, path)    -> move adapter into cache
    invalidate(account_id)   -> drop adapter (base changed)
    invalidate_all()         -> drop every adapter
    base_hash()              -> hash of companion_model.pth
    ensure_fresh(account_id) -> invalidate if base changed
"""
from __future__ import annotations
import hashlib
import shutil
from pathlib import Path
from typing import Optional

CACHE_ROOT = Path("buckets")
BASE_PATH  = Path("companion_model.pth")


def _base_dir() -> Path:
    return BASE_PATH.parent


def base_hash() -> str:
    """Hash of the current base model file (or empty)."""
    if not BASE_PATH.exists():
        return ""
    h = hashlib.sha256()
    try:
        with BASE_PATH.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()[:16]


def _account_dir(account_id: str) -> Path:
    return CACHE_ROOT / account_id


def _adapter_path(account_id: str) -> Path:
    return _account_dir(account_id) / "lora.safetensors"


def _meta_path(account_id: str) -> Path:
    return _account_dir(account_id) / "lora.meta.json"


# ---------------------------------------------------------------------------
# GET / PUT
# ---------------------------------------------------------------------------

def get(account_id: str) -> Optional[str]:
    p = _adapter_path(account_id)
    if p.exists():
        return str(p)
    # fallback .pt for torch.save path
    pt = p.with_suffix(".pt")
    if pt.exists():
        return str(pt)
    return None


def put(account_id: str, source_path: str) -> str:
    dest = _adapter_path(account_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest)
    import json, time
    _meta_path(account_id).write_text(json.dumps({
        "account_id": account_id,
        "base_hash": base_hash(),
        "saved_at": int(time.time()),
        "size": dest.stat().st_size,
    }, indent=2))
    return str(dest)


# ---------------------------------------------------------------------------
# INVALIDATION
# ---------------------------------------------------------------------------

def ensure_fresh(account_id: str) -> bool:
    """
    Return True if the cached adapter matches the current base.
    If it doesn't, invalidate and return False.
    """
    meta = _meta_path(account_id)
    if not meta.exists():
        return False
    try:
        import json
        d = json.loads(meta.read_text())
        if d.get("base_hash") != base_hash():
            invalidate(account_id)
            return False
        return True
    except Exception:
        invalidate(account_id)
        return False


def invalidate(account_id: str) -> None:
    d = _account_dir(account_id)
    if not d.exists():
        return
    for p in (d / "lora.safetensors", d / "lora.pt", d / "lora.meta.json"):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def invalidate_all() -> int:
    n = 0
    if not CACHE_ROOT.exists():
        return 0
    for sub in CACHE_ROOT.iterdir():
        if sub.is_dir():
            invalidate(sub.name)
            n += 1
    return n


def list_cached() -> list[dict]:
    out = []
    if not CACHE_ROOT.exists():
        return out
    for sub in sorted(CACHE_ROOT.iterdir()):
        if sub.is_dir():
            meta = _meta_path(sub.name)
            if meta.exists():
                try:
                    import json
                    out.append(json.loads(meta.read_text()))
                except Exception:
                    pass
    return out
