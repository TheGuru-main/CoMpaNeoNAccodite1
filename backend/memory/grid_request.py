"""
Request-time grid bind: phone UID owner keys.

org:<org_phone_uid> | user:<user_phone_uid>
Workers never get a worker grid — only org grid if membership active.

M2.3 restore order (tenant):
  1) local instance file at grid_path(owner)
  2) B2 grids/instances/{kind}/{phone}/…
  3) fail closed (None)

Never:
  - invent empty MemoryGrid on bind
  - load platform grid when prefer_platform is False
  - bind tenant grid into process-wide _SHARED_GRID (bind_process=False)
"""
from __future__ import annotations

from typing import Any, Callable, Optional


def bind_request_grid(
    *,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_phone: Optional[str] = None,
    org_phone: Optional[str] = None,
    is_active_member: Optional[Callable[..., bool]] = None,
    prefer_platform: bool = False,
) -> Any:
    # Explicit platform only
    if prefer_platform:
        try:
            from memory.platform_grid import load_platform_grid
            return load_platform_grid(require_docs=False, allow_empty=True)
        except Exception as e:
            print("[grid_request] platform:", type(e).__name__, e)
            return None

    try:
        from memory.owner_identity import (
            phone_uid,
            resolve_user_phone,
            resolve_org_phone,
        )
        from memory.instance_grid import OwnerRef, grid_path
    except Exception as e:
        print("[grid_request] imports:", type(e).__name__, e)
        return None

    up = phone_uid(user_phone) if user_phone else resolve_user_phone(user_id=user_id)
    op = phone_uid(org_phone) if org_phone else resolve_org_phone(org_id=org_id)

    # --- Resolve owner (fail closed) ---
    if org_id or org_phone:
        # Explicit organisation context must never downgrade to a personal grid.
        if not op:
            print("[grid_request] organisation identity unresolved")
            return None
        if not user_id or not org_id:
            print("[grid_request] organisation access requires user_id and org_id")
            return None

        checker = is_active_member
        if checker is None:
            try:
                from memory.membership_access import is_active_member as checker
            except Exception as e:
                print(
                    "[grid_request] membership checker unavailable:",
                    type(e).__name__, e,
                )
                return None
        try:
            if not checker(str(user_id), str(org_id)):
                print("[grid_request] inactive or unverified organisation membership")
                return None
        except Exception as e:
            print("[grid_request] membership check failed:", type(e).__name__, e)
            return None

        owner = OwnerRef("org", op)
    elif up:
        owner = OwnerRef("user", up)
    else:
        print("[grid_request] no user phone and no org context")
        return None

    path = grid_path(owner)
    path.parent.mkdir(parents=True, exist_ok=True)

    def _try_load(local_path) -> Any:
        from memory.memory_grid import load_grid
        return load_grid(str(local_path), bind_process=False)

    def _validate_or_unlink(local_path) -> bool:
        try:
            from memory.instance_grid import _validate_grid_snapshot
            _validate_grid_snapshot(local_path)
            return True
        except Exception as e:
            print("[grid_request] local snapshot invalid:", type(e).__name__, e)
            try:
                local_path.unlink(missing_ok=True)
            except Exception:
                pass
            return False

    # --- 1) Local instance ---
    if path.is_file():
        if _validate_or_unlink(path):
            try:
                grid = _try_load(path)
                if grid is not None:
                    return grid
            except Exception as e:
                print("[grid_request] local load failed:", type(e).__name__, e)
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
        # fall through to B2

    # --- 2) B2 instance partition only (not platform) ---
    try:
        from memory.b2_grid_layout import fetch_instance_grid_to_path

        tmp = path.with_name(path.name + ".b2.tmp")
        try:
            restored = fetch_instance_grid_to_path(
                owner.kind, owner.id, str(tmp)
            )
        except Exception as e:
            print("[grid_request] B2 restore failed:", type(e).__name__, e)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            print(f"[grid_request] fail closed — no instance for {owner.key}")
            return None

        if not restored:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            print(f"[grid_request] fail closed — no local/B2 instance for {owner.key}")
            return None

        if not _validate_or_unlink(tmp):
            print(f"[grid_request] fail closed — B2 snapshot invalid for {owner.key}")
            return None

        import os
        os.replace(tmp, path)
        print(f"[grid_request] restored B2 instance for {owner.key}")
    except Exception as e:
        print("[grid_request] B2 path error:", type(e).__name__, e)
        return None

    # --- 3) Load restored local ---
    try:
        grid = _try_load(path)
    except Exception as e:
        print("[grid_request] load after B2:", type(e).__name__, e)
        return None

    if grid is None:
        print(f"[grid_request] fail closed — load returned None for {owner.key}")
        return None

    # Tenant grids returned to caller only — never process-global bind.
    return grid
