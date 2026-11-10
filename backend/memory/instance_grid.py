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



def _validate_grid_snapshot(path: Path) -> None:
    from memory.memory_grid import load_grid

    if not path.is_file() or path.stat().st_size == 0:
        raise InstanceGridError(f"grid snapshot missing or empty: {path}")

    try:
        load_grid(str(path), bind_process=False)
    except Exception as exc:
        raise InstanceGridError(
            f"invalid MemoryGrid snapshot at {path}: {type(exc).__name__}: {exc}"
        ) from exc


def _publish_owner_grid(owner: OwnerRef, path: Path) -> None:
    from storage.b2 import b2_enabled

    if not b2_enabled():
        return

    from memory.b2_grid_layout import publish_instance_grid_file
    result = publish_instance_grid_file(owner.kind, owner.id, str(path))

    if not result.get("ok"):
        raise InstanceGridError(
            f"B2 publication failed for {owner.key}: {result.get('reason')}"
        )


def create_instance_grid(
    owner: OwnerRef,
    platform_version: int = 1,
    *,
    base: Optional[str] = None,
    allow_empty_if_no_platform: bool = True,
) -> Path:
    """Provision or restore one independent owner grid."""
    if not isinstance(owner, OwnerRef):
        raise InstanceGridError("owner must be OwnerRef")

    if not owner.id or not str(owner.id).strip():
        raise InstanceGridError("owner phone UID required")

    grid = grid_path(owner, base)
    grid.parent.mkdir(parents=True, exist_ok=True)

    from storage.b2 import b2_enabled
    remote_enabled = b2_enabled()

    # Restore the owner's dedicated B2 partition first.
    if remote_enabled:
        from memory.b2_grid_layout import fetch_instance_grid_to_path

        remote_tmp = grid.with_name(GRID_NAME + ".b2.tmp")
        try:
            restored = fetch_instance_grid_to_path(
                owner.kind, owner.id, str(remote_tmp)
            )
        except Exception as exc:
            raise InstanceGridError(
                f"B2 restore failed for {owner.key}: {exc}"
            ) from exc

        if restored:
            try:
                _validate_grid_snapshot(remote_tmp)
                os.replace(remote_tmp, grid)
            except Exception:
                remote_tmp.unlink(missing_ok=True)
                raise

            print(f"[instance_grid] restored B2 partition for {owner.key}")
            return grid

    # A local cache may be used if no B2 object exists.
    if grid.is_file():
        _validate_grid_snapshot(grid)
        _publish_owner_grid(owner, grid)
        return grid

    # Restore platform seed from B2 if it is not cached locally.
    src = platform_cache_path(platform_version, base)

    if not src.is_file() and remote_enabled:
        from memory.b2_grid_layout import fetch_platform_grid_to_path

        src.parent.mkdir(parents=True, exist_ok=True)
        platform_tmp = src.with_name(GRID_NAME + ".b2.tmp")

        try:
            restored = fetch_platform_grid_to_path(
                platform_version, str(platform_tmp)
            )
        except Exception as exc:
            raise InstanceGridError(
                f"platform B2 restore failed for v{platform_version}: {exc}"
            ) from exc

        if restored:
            try:
                _validate_grid_snapshot(platform_tmp)
                os.replace(platform_tmp, src)
            except Exception:
                platform_tmp.unlink(missing_ok=True)
                raise
        else:
            platform_tmp.unlink(missing_ok=True)

    tmp = grid.with_name(GRID_NAME + ".tmp")

    if src.is_file():
        try:
            _validate_grid_snapshot(src)
            shutil.copyfile(src, tmp)
            _validate_grid_snapshot(tmp)
            os.replace(tmp, grid)
        finally:
            tmp.unlink(missing_ok=True)

    elif allow_empty_if_no_platform:
        from memory.memory_grid import MemoryGrid, _grid_to_dict

        try:
            payload = _grid_to_dict(MemoryGrid())
            with tmp.open("w", encoding="utf-8") as fout:
                json.dump(payload, fout, ensure_ascii=False)

            _validate_grid_snapshot(tmp)
            os.replace(tmp, grid)
            print(f"[instance_grid] empty JSON grid created for {owner.key}")
        finally:
            tmp.unlink(missing_ok=True)

    else:
        raise InstanceGridError(
            f"platform grid v{platform_version} unavailable"
        )

    _validate_grid_snapshot(grid)

    _write_manifest(grid.parent, {
        "owner": owner.key,
        "created_at": int(time.time()),
        "platform_version": int(platform_version),
        "last_snapshot": None,
    })

    _publish_owner_grid(owner, grid)
    return grid


def require_access(*, user_id: str, owner: OwnerRef, is_active_member) -> None:
    if owner.kind == "user":
        return
    if not is_active_member(user_id, owner):
        raise InstanceGridError("not an active org member")
