"""
Request-time grid bind: phone UID owner keys.

org:<org_phone_uid> | user:<user_phone_uid>
Workers never get a worker grid — only org grid if membership active.
"""
from __future__ import annotations
from typing import Any, Optional, Callable

def bind_request_grid(
    *,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_phone: Optional[str] = None,
    org_phone: Optional[str] = None,
    is_active_member: Optional[Callable[..., bool]] = None,
    prefer_platform: bool = False,
) -> Any:
    if prefer_platform:
        try:
            from memory.platform_grid import load_platform_grid
            return load_platform_grid(require_docs=False, allow_empty=True)
        except Exception as e:
            print("[grid_request] platform:", type(e).__name__, e)
            return None

    try:
        from memory.owner_identity import (
            phone_uid, resolve_user_phone, resolve_org_phone,
        )
        from memory.instance_grid import OwnerRef, grid_path
    except Exception as e:
        print("[grid_request] imports:", type(e).__name__, e)
        return None

    up = phone_uid(user_phone) if user_phone else resolve_user_phone(user_id=user_id)
    op = phone_uid(org_phone) if org_phone else resolve_org_phone(org_id=org_id)

    owner = None

    # Explicit organisation context must never downgrade to a personal grid.
    if org_id or org_phone:
        if not op:
            print("[grid_request] organisation identity unresolved")
            return None

        # Membership requires relational user and organisation IDs.
        if not user_id or not org_id:
            print("[grid_request] organisation access requires user_id and org_id")
            return None

        checker = is_active_member
        if checker is None:
            try:
                from memory.membership_access import is_active_member as checker
            except Exception as e:
                print("[grid_request] membership checker unavailable:", type(e).__name__, e)
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
        return None

    path = grid_path(owner)

    if not path.is_file():
        try:
            from memory.b2_grid_layout import fetch_instance_grid_to_path

            restored = fetch_instance_grid_to_path(
                owner.kind, owner.id, str(path)
            )
            if not restored:
                print(f"[grid_request] no grid found for {owner.key}")
                return None
        except Exception as e:
            print(
                "[grid_request] B2 restore failed:",
                type(e).__name__, e,
            )
            return None
    try:
        from memory.memory_grid import load_grid
        grid = load_grid(str(path), bind_process=False)
    except Exception as e:
        print("[grid_request] load:", type(e).__name__, e)
        return None

    # Tenant grids are returned to the caller only.
    # Never bind them to process-wide integration or partition state here.
    return grid
