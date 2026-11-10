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
    """Durable instance/platform-side manifest beside grid.pkl."""
    import hashlib
    import json as _json
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    grid = d / GRID_NAME
    data = dict(payload or {})
    data.setdefault("updated_at", int(time.time()))
    if grid.is_file() and "sha256" not in data:
        try:
            h = hashlib.sha256()
            with grid.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            data["sha256"] = h.hexdigest()
        except Exception as e:
            data["sha256_error"] = f"{type(e).__name__}: {e}"
    path = d / MANIFEST_NAME
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fout:
        _json.dump(data, fout, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


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
    allow_empty_if_no_platform: bool = False,
) -> Path:
    """Provision or restore one independent owner grid.

    Order:
      1) existing instance on B2
      2) existing local instance
      3) copy platform snapshot (local cache, else B2 platform, else ACCD_GRID_PATH)
      4) empty invent only if allow_empty_if_no_platform=True
    Signup must receive the platform training snapshot when available.
    """
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

    # Last chance: ACCD_GRID_PATH or published platform file on disk
    if not src.is_file():
        import os as _os
        for cand in (
            _os.environ.get("ACCD_GRID_PATH"),
            _os.environ.get("ACCD_PLATFORM_GRID_PATH"),
        ):
            if cand and Path(cand).is_file():
                src = Path(cand)
                print(f"[instance_grid] platform seed from env path {src}")
                break

    if src.is_file():
        try:
            _validate_grid_snapshot(src)
            shutil.copyfile(src, tmp)
            _validate_grid_snapshot(tmp)
            os.replace(tmp, grid)
            print(f"[instance_grid] provisioned from platform snapshot for {owner.key}")
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
            print(f"[instance_grid] empty JSON grid created for {owner.key} (no platform seed)")
        finally:
            tmp.unlink(missing_ok=True)

    else:
        raise InstanceGridError(
            f"platform grid v{platform_version} unavailable — cannot seed instance {owner.key}"
        )

    _validate_grid_snapshot(grid)

    _write_manifest(grid.parent, {
        "owner": owner.key,
        "kind": owner.kind,
        "phone_uid": owner.id,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "platform_version": int(platform_version),
        "source": "platform_snapshot",
        "last_snapshot": None,
    })

    _publish_owner_grid(owner, grid)
    return grid



def persist_owner_grid(owner: OwnerRef, grid, *, base: Optional[str] = None) -> dict:
    """
    Write the in-memory owner MemoryGrid to the durable instance path and publish to B2.

    Instance grids are permanent (signup seed + live mutations). Not /tmp sandbox.
    Platform training keys are never written here.
    """
    if not isinstance(owner, OwnerRef):
        raise InstanceGridError("owner must be OwnerRef")
    if grid is None:
        raise InstanceGridError("grid required")

    path = grid_path(owner, base)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from memory.memory_grid import save_grid
        save_grid(grid, str(path))
    except Exception:
        # Fallback: pickle/json via _grid_to_dict if save_grid path-sensitive
        from memory.memory_grid import _grid_to_dict
        import json as _json
        tmp = path.with_name(path.name + ".tmp")
        payload = _grid_to_dict(grid)
        with tmp.open("w", encoding="utf-8") as fout:
            _json.dump(payload, fout, ensure_ascii=False)
        os.replace(tmp, path)

    _write_manifest(path.parent, {
        "owner": owner.key,
        "kind": owner.kind,
        "phone_uid": owner.id,
        "updated_at": int(time.time()),
        "last_snapshot": int(time.time()),
        "source": "instance_mutate",
    })

    b2_ok = False
    b2_err = None
    try:
        _publish_owner_grid(owner, path)
        b2_ok = True
    except Exception as e:
        b2_err = f"{type(e).__name__}: {e}"
        print("[instance_grid] persist B2:", b2_err)

    return {
        "ok": True,
        "path": str(path),
        "owner": owner.key,
        "b2_ok": b2_ok,
        "b2_error": b2_err,
    }


def require_access(*, user_id: str, owner: OwnerRef, is_active_member) -> None:
    if owner.kind == "user":
        return
    if not is_active_member(user_id, owner):
        raise InstanceGridError("not an active org member")
