"""
Instance MemoryGrid ownership — phone UID keys only.

  org:<normalized_org_phone>
  user:<normalized_user_phone>

Workers have no grid. Platform grid is seed/train template only.
DB UUID is never an OwnerRef id.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

GRID_NAME = "grid.pkl"
MANIFEST_NAME = "manifest.json"


class InstanceGridError(RuntimeError):
    pass


@dataclass(frozen=True)
class OwnerRef:
    kind: str  # "org" | "user"
    id: str    # normalized phone UID

    def __post_init__(self):
        if self.kind not in ("org", "user"):
            raise InstanceGridError("OwnerRef.kind must be org|user")
        if not self.id or not str(self.id).strip():
            raise InstanceGridError("OwnerRef.id (phone UID) required")

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.id}"


def _base(base: Optional[str] = None) -> Path:
    root = base or os.environ.get("ACCD_INSTANCE_GRID_ROOT") or os.environ.get("ACCD_GRID_ROOT") or "/var/data/grids"
    return Path(root)


def platform_cache_path(version: int = 1, base: Optional[str] = None) -> Path:
    return _base(base) / "platform" / f"v{int(version)}" / GRID_NAME


def instance_dir(owner: OwnerRef, base: Optional[str] = None) -> Path:
    return _base(base) / "instances" / owner.kind / owner.id


def grid_path(owner: OwnerRef, base: Optional[str] = None) -> Path:
    return instance_dir(owner, base) / GRID_NAME


def _write_manifest(d: Path, payload: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / MANIFEST_NAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_instance_grid(
    owner: OwnerRef,
    platform_version: int = 1,
    *,
    base: Optional[str] = None,
) -> Path:
    """Copy platform snapshot into owner instance path. Once per owner."""
    grid = grid_path(owner, base)
    if grid.exists():
        raise InstanceGridError(f"{owner.key} already has a grid")
    src = platform_cache_path(platform_version, base)
    d = grid.parent
    d.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        tmp = grid.with_name(GRID_NAME + ".tmp")
        shutil.copyfile(src, tmp)
        os.replace(tmp, grid)
        sha = None
        try:
            import hashlib
            sha = hashlib.sha256(src.read_bytes()).hexdigest()
        except Exception:
            pass
    else:
        # bootstrap empty pickle if platform missing — caller may seed later
        try:
            import pickle
            from memory.memory_grid import MemoryGrid
            g = MemoryGrid()
            tmp = grid.with_name(GRID_NAME + ".tmp")
            with open(tmp, "wb") as f:
                pickle.dump(g, f)
            os.replace(tmp, grid)
            sha = None
            print(f"[instance_grid] platform snapshot missing; empty grid for {owner.key}")
        except Exception as e:
            raise InstanceGridError(f"platform snapshot not cached and empty create failed: {e}") from e
    _write_manifest(d, {
        "owner": owner.key,
        "created_at": int(time.time()),
        "platform_version": int(platform_version),
        "platform_sha256": sha,
        "last_snapshot": None,
    })
    return grid


def require_access(*, user_id: str, owner: OwnerRef, is_active_member) -> None:
    if owner.kind == "user":
        return
    if not is_active_member(user_id, owner):
        raise InstanceGridError("not an active org member")
