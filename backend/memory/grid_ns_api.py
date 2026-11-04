"""HTTP helpers for namespace place/list on the bound owner grid."""
from __future__ import annotations
from typing import Any, Optional

def place_ns_object(
    *,
    ns: str,
    object_name: str,
    text: str = "",
    description: str = "",
    user_id: str = "",
    org_id: str = "",
    user_phone: str = "",
    org_phone: str = "",
    workspace_id: str = "",
) -> dict:
    from memory.grid_request import bind_request_grid
    from memory.grid_namespaces import place_in_owner_grid, assert_ns
    assert_ns(ns)
    grid = bind_request_grid(
        user_id=user_id or None,
        org_id=org_id or None,
        user_phone=user_phone or None,
        org_phone=org_phone or None,
    )
    if grid is None:
        return {"ok": False, "error": "owner grid unavailable"}
    owner_phone = org_phone or user_phone or ""
    doc_id = place_in_owner_grid(
        grid,
        ns=ns,
        object_name=object_name,
        text=text or description or object_name,
        description=description,
        owner_phone_uid=owner_phone,
        workspace_id=workspace_id,
    )
    return {"ok": True, "doc_id": doc_id, "ns": ns, "object_name": object_name}


def list_ns(
    *,
    ns: str,
    user_id: str = "",
    org_id: str = "",
    user_phone: str = "",
    org_phone: str = "",
    workspace_id: str = "",
) -> dict:
    from memory.grid_request import bind_request_grid
    from memory.grid_namespaces import list_namespace, monitor_workflow, assert_ns
    grid = bind_request_grid(
        user_id=user_id or None,
        org_id=org_id or None,
        user_phone=user_phone or None,
        org_phone=org_phone or None,
    )
    if grid is None:
        return {"ok": False, "error": "owner grid unavailable", "items": []}
    if ns in ("*", "all", "monitor"):
        return {"ok": True, "monitor": monitor_workflow(grid, workspace_id=workspace_id)}
    assert_ns(ns)
    return {"ok": True, "ns": ns, "items": list_namespace(grid, ns, workspace_id=workspace_id)}
