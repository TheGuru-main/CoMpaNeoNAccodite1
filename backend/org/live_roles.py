"""Org-configurable role catalog for worker signup toggles."""
from __future__ import annotations
from typing import Any, Dict, List

# Canonical ranks (admin may enable/disable and rename labels; keys stay stable)
CANON = [
    {"key": "ceo", "label": "CEO", "level": 1},
    {"key": "c_suite", "label": "C-Suite", "level": 2},
    {"key": "hr", "label": "HR", "level": 3},
    {"key": "dept_head", "label": "Department Head", "level": 4},
    {"key": "manager", "label": "Manager", "level": 5},
    {"key": "member", "label": "Member", "level": 6},
    {"key": "reviewer", "label": "Reviewer", "level": 7},
    {"key": "viewer", "label": "Viewer", "level": 8},
]


def default_role_catalog() -> List[Dict[str, Any]]:
    return [{**r, "enabled": True} for r in CANON]


def get_org_roles(org) -> List[Dict[str, Any]]:
    settings = getattr(org, "settings", None) or {}
    if isinstance(settings, str):
        import json
        try:
            settings = json.loads(settings)
        except Exception:
            settings = {}
    roles = settings.get("live_roles")
    if not isinstance(roles, list) or not roles:
        return default_role_catalog()
    # merge with canon so new keys appear
    by_key = {r.get("key"): r for r in roles if isinstance(r, dict) and r.get("key")}
    out = []
    for c in CANON:
        if c["key"] in by_key:
            merged = dict(c)
            merged.update(by_key[c["key"]])
            merged["enabled"] = bool(merged.get("enabled", True))
            out.append(merged)
        else:
            out.append({**c, "enabled": True})
    return out


def enabled_role_keys(org) -> List[str]:
    return [r["key"] for r in get_org_roles(org) if r.get("enabled")]


def set_org_roles(org, roles: List[Dict[str, Any]]) -> Dict[str, Any]:
    settings = getattr(org, "settings", None) or {}
    if isinstance(settings, str):
        import json
        try:
            settings = json.loads(settings)
        except Exception:
            settings = {}
    if not isinstance(settings, dict):
        settings = {}
    cleaned = []
    for r in roles or []:
        if not isinstance(r, dict) or not r.get("key"):
            continue
        cleaned.append({
            "key": str(r["key"]),
            "label": str(r.get("label") or r["key"]),
            "level": int(r.get("level") or 6),
            "enabled": bool(r.get("enabled", True)),
        })
    settings["live_roles"] = cleaned or default_role_catalog()
    org.settings = settings
    return settings
