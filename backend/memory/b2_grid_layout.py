"""
Explicit B2 key layout for platform vs instance grids.

Wizard DB / own data-center will mirror this tree.

  {prefix}/grids/platform/v{N}/grid.pkl
  {prefix}/grids/platform/v{N}/manifest.json
  {prefix}/grids/platform/latest.json          -> {version, key, sha256}

  {prefix}/grids/instances/org/{org_id}/grid.pkl
  {prefix}/grids/instances/org/{org_id}/manifest.json
  {prefix}/grids/instances/user/{user_id}/grid.pkl
  {prefix}/grids/instances/user/{user_id}/manifest.json

  {prefix}/grids/snapshots/platform/{ts}.pkl
  {prefix}/grids/snapshots/instances/{kind}/{id}/{ts}.pkl

Weights stay under models/ (not mixed into grids/).
Messages / workflow continuity can use:
  {prefix}/continuity/{kind}/{id}/...
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

def b2_prefix() -> str:
    return (os.environ.get("ACCD_B2_PREFIX") or "accodite").strip().strip("/")

def platform_grid_key(version: int = 1) -> str:
    return f"grids/platform/v{int(version)}/grid.pkl"

def platform_manifest_key(version: int = 1) -> str:
    return f"grids/platform/v{int(version)}/manifest.json"

def platform_latest_key() -> str:
    return "grids/platform/latest.json"

def instance_grid_key(kind: str, owner_id: str) -> str:
    if kind not in ("org", "user"):
        raise ValueError("kind must be org|user")
    return f"grids/instances/{kind}/{owner_id}/grid.pkl"  # owner_id = normalized phone UID

def instance_manifest_key(kind: str, owner_id: str) -> str:
    return f"grids/instances/{kind}/{owner_id}/manifest.json"

def snapshot_key(kind: str, owner_id: Optional[str] = None, ts: Optional[str] = None) -> str:
    ts = ts or time.strftime("%Y%m%d_%H%M%S")
    if kind == "platform":
        return f"grids/snapshots/platform/{ts}.pkl"
    if kind not in ("org", "user") or not owner_id:
        raise ValueError("instance snapshot needs kind org|user and owner_id")
    return f"grids/snapshots/instances/{kind}/{owner_id}/{ts}.pkl"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def publish_platform_grid_file(path: str, version: int = 1) -> dict:
    """Upload local platform grid.pkl to the platform key + latest pointer."""
    from storage.b2 import b2_put_bytes, b2_put_json, b2_enabled
    if not b2_enabled():
        return {"ok": False, "reason": "b2_disabled"}
    p = Path(path)
    data = p.read_bytes()
    key = platform_grid_key(version)
    full = b2_put_bytes(key, data, content_type="application/octet-stream")
    meta = {
        "kind": "platform",
        "version": int(version),
        "key": key,
        "full_key": full,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "at": time.time(),
    }
    b2_put_json(platform_manifest_key(version), meta)
    b2_put_json(platform_latest_key(), meta)
    print(f"[b2_grid] platform v{version} -> {full}")
    return {"ok": True, **meta}

def publish_instance_grid_file(kind: str, owner_id: str, path: str) -> dict:
    from storage.b2 import b2_put_bytes, b2_put_json, b2_enabled
    if not b2_enabled():
        return {"ok": False, "reason": "b2_disabled"}
    data = Path(path).read_bytes()
    key = instance_grid_key(kind, owner_id)
    full = b2_put_bytes(key, data, content_type="application/octet-stream")
    meta = {
        "kind": kind,
        "owner_id": owner_id,
        "key": key,
        "full_key": full,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "at": time.time(),
    }
    b2_put_json(instance_manifest_key(kind, owner_id), meta)
    print(f"[b2_grid] instance {kind}/{owner_id} -> {full}")
    return {"ok": True, **meta}


def _is_missing_b2_object(exc: Exception) -> bool:
    """Recognise missing-object responses without hiding other B2 failures."""
    name = type(exc).__name__.lower()
    if "filenotpresent" in name or "nosuchfile" in name:
        return True

    response = getattr(exc, "response", None) or {}
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    code = str(error.get("Code", "")).lower()
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    return code in ("nosuchkey", "notfound", "404") or status == 404


def _fetch_grid_key_to_path(key: str, dest: str) -> bool:
    from storage.b2 import b2_get_bytes, b2_enabled

    if not b2_enabled():
        return False

    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".download.tmp")

    try:
        data = b2_get_bytes(key)
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise RuntimeError(f"B2 returned empty or invalid grid data: {key}")

        tmp.write_bytes(bytes(data))
        os.replace(tmp, target)
        return True

    except Exception as exc:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

        if _is_missing_b2_object(exc):
            return False

        raise RuntimeError(
            f"B2 grid fetch failed for {key}: {type(exc).__name__}: {exc}"
        ) from exc



def _is_missing_b2_object(exc: Exception) -> bool:
    """Recognise missing-object responses without hiding other B2 failures."""
    name = type(exc).__name__.lower()
    if "filenotpresent" in name or "nosuchfile" in name:
        return True

    response = getattr(exc, "response", None) or {}
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    code = str(error.get("Code", "")).lower()
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    return code in ("nosuchkey", "notfound", "404") or status == 404


def _fetch_grid_key_to_path(key: str, dest: str) -> bool:
    from storage.b2 import b2_get_bytes, b2_enabled

    if not b2_enabled():
        return False

    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".download.tmp")

    try:
        data = b2_get_bytes(key)
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise RuntimeError(f"B2 returned empty or invalid grid data: {key}")

        tmp.write_bytes(bytes(data))
        os.replace(tmp, target)
        return True

    except Exception as exc:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

        if _is_missing_b2_object(exc):
            return False

        raise RuntimeError(
            f"B2 grid fetch failed for {key}: {type(exc).__name__}: {exc}"
        ) from exc


def fetch_instance_grid_to_path(kind: str, owner_id: str, dest: str) -> bool:
    return _fetch_grid_key_to_path(
        instance_grid_key(kind, owner_id),
        dest,
    )


def fetch_platform_grid_to_path(version: int, dest: str) -> bool:
    return _fetch_grid_key_to_path(
        platform_grid_key(version),
        dest,
    )
