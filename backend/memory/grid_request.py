"""
Request-time grid bind: instance (org|user) for tenants; platform only when explicit.

GSP placement S is never computed here.
Token S remains tokenizer sum(uid_sequence).
"""
from __future__ import annotations
from typing import Any, Optional, Callable

def bind_request_grid(
    *,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    is_active_member: Optional[Callable[..., bool]] = None,
    prefer_platform: bool = False,
) -> Any:
    """
    Returns MemoryGrid for this request or None.
    Workers: pass org_id + membership check → org instance grid.
    Regular user solo: user_id → user instance grid.
    """
    if prefer_platform:
        try:
            from memory.platform_grid import load_platform_grid
            return load_platform_grid(require_docs=False, allow_empty=True)
        except Exception as e:
            print("[grid_request] platform:", type(e).__name__, e)
            return None

    owner = None
    try:
        from memory.instance_grid import OwnerRef, grid_path, require_access, can_access
    except Exception as e:
        print("[grid_request] instance_grid missing:", e)
        # soft: platform so app still runs
        try:
            from memory.platform_grid import load_platform_grid
            return load_platform_grid(require_docs=False, allow_empty=True)
        except Exception:
            return None

    if org_id and user_id:
        owner = OwnerRef("org", str(org_id))
        if is_active_member is not None:
            try:
                require_access(user_id=str(user_id), owner=owner, is_active_member=is_active_member)
            except Exception as e:
                print("[grid_request] access denied:", e)
                return None
    elif user_id:
        owner = OwnerRef("user", str(user_id))
    else:
        return None

    path = grid_path(owner)
    if not path.is_file():
        print(f"[grid_request] no grid yet for {owner.key}")
        return None
    try:
        from memory.memory_grid import load_grid
        grid = load_grid(str(path))
    except Exception as e:
        print("[grid_request] load:", type(e).__name__, e)
        return None

    try:
        from training.background_training import resolve_partition_for_grid
        resolve_partition_for_grid(grid, owner=owner)
    except Exception:
        try:
            from integration import get_state
            get_state()["grid"] = grid
            get_state()["grid_owner"] = owner.key
            get_state()["grid_kind"] = "instance"
        except Exception:
            pass
    return grid
