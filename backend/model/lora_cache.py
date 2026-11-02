"""
Platform + instance LoRA adapter cache.

Platform adapters ship with the product (optional).
Instance adapters are trained on org|user instance grids after download.
Workers do not own adapters.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

try:
    from memory.platform_grid import platform_lora_dir, platform_root
except Exception:
    def platform_root(base=None):
        return Path(base or os.environ.get("ACCD_MEMORY_ROOT") or "/var/data/accd_memory") / "platform"
    def platform_lora_dir(base=None):
        return platform_root(base) / "lora"


class AdapterError(RuntimeError):
    pass


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def publish_platform_adapter(src_path: str, version: int, *, base: Optional[str] = None) -> dict:
    """Copy a trained LoRA file into platform/lora/v{N}/adapter.pt + manifest."""
    src = Path(src_path)
    if not src.is_file():
        raise AdapterError(f"missing adapter file {src}")
    v = int(version)
    dest_dir = platform_lora_dir(base) / f"v{v}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "adapter.pt"
    dest.write_bytes(src.read_bytes())
    meta = {"version": v, "path": str(dest), "bytes": dest.stat().st_size, "at": time.time(), "kind": "platform"}
    _write_json(dest_dir / "manifest.json", meta)
    _write_json(platform_lora_dir(base) / "CURRENT.json", {"version": v, "path": str(dest)})
    print(f"[lora] platform adapter v{v} -> {dest}")
    return meta


def current_platform_adapter(*, base: Optional[str] = None) -> Optional[str]:
    cur = platform_lora_dir(base) / "CURRENT.json"
    if not cur.is_file():
        return None
    try:
        data = json.loads(cur.read_text(encoding="utf-8"))
        p = data.get("path")
        return p if p and Path(p).is_file() else None
    except Exception:
        return None


def owner_lora_dir(kind: str, owner_id: str, base: Optional[str] = None) -> Path:
    root = Path(base or os.environ.get("ACCD_MEMORY_ROOT") or "/var/data/accd_memory")
    return root / "instances" / kind / owner_id / "lora"


def publish_instance_adapter(kind: str, owner_id: str, src_path: str, version: int, *, base: Optional[str] = None) -> dict:
    if kind not in ("org", "user"):
        raise AdapterError("instance adapter only for org|user")
    src = Path(src_path)
    if not src.is_file():
        raise AdapterError(f"missing {src}")
    dest_dir = owner_lora_dir(kind, owner_id, base) / f"v{int(version)}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "adapter.pt"
    dest.write_bytes(src.read_bytes())
    meta = {"kind": kind, "owner_id": owner_id, "version": int(version), "path": str(dest), "at": time.time()}
    _write_json(dest_dir / "manifest.json", meta)
    _write_json(owner_lora_dir(kind, owner_id, base) / "CURRENT.json", meta)
    return meta
