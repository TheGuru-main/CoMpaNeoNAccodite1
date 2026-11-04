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
        try:
            from memory.platform_grid import load_platform_grid
            return load_platform_grid(require_docs=False, allow_empty=True)
        except Exception:
            return None

    up = phone_uid(user_phone) if user_phone else resolve_user_phone(user_id=user_id)
    op = phone_uid(org_phone) if org_phone else resolve_org_phone(org_id=org_id)

    owner = None
    if op:
        # membership: prefer phone-aware check when possible
        if user_id or up:
            if is_active_member is None:
                try:
                    from memory.membership_access import is_active_member as _iam
                    if org_id and user_id and not _iam(str(user_id), str(org_id)):
                        print("[grid_request] not active member", user_id, org_id)
                        return None
                except Exception as e:
                    print("[grid_request] membership:", type(e).__name__, e)
            else:
                try:
                    if org_id and user_id and not is_active_member(str(user_id), str(org_id)):
                        return None
                except TypeError:
                    pass
        owner = OwnerRef("org", op)
    elif up:
        owner = OwnerRef("user", up)
    else:
        return None

    path = grid_path(owner)
    if not path.is_file():
        print(f"[grid_request] no grid yet for {owner.key}")
        return None
    try:
        try:
            from memory.memory_grid import load_grid
            grid = load_grid(str(path))
        except Exception:
            import pickle
            with open(path, "rb") as f:
                grid = pickle.load(f)
    except Exception as e:
        print("[grid_request] load:", type(e).__name__, e)
        return None

    try:
        from training.background_training import resolve_partition_for_grid
        resolve_partition_for_grid(grid, owner=owner)
    except Exception:
        try:
            from integration import get_state
            st = get_state()
            st["grid"] = grid
            st["grid_owner"] = owner.key
            st["grid_kind"] = "instance"
            st["owner_phone_uid"] = op or up
        except Exception:
            pass
    return grid
