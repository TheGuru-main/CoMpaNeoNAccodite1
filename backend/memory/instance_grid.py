"""
Grid ownership for Accodite.

Who owns a grid (set at signup, never per request):
  regular account  -> its own personal grid        user:<id>
  org (workers)    -> one grid per org, shared     org:<id>
  worker           -> NO grid. Reads and writes the org grid through
                      an active org membership.
  admin            -> NO instance grid. Platform operations only.

Platform grid (ours) is only used for two things:
  1. seed training, which produces a new platform version
  2. the snapshot copied into a new grid at signup

Storage:
  platform snapshot  -> Hugging Face (pulled at signup, sha256-pinned)
  live grid          -> local disk on the server (working copy)
  grid snapshots     -> B2 under snapshots/instances/<kind>/<id>/ (gzip)

Nothing here pulls from a global brain. Retrieval, training, background
training and crawling all take an OwnerRef and touch only that owner's grid.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from memory.artifact_policy import check_b2_key, gzip_file, gunzip_file, sha256_file
try:
    from memory.platform_grid import platform_grid_path as _live_platform_grid_path
except Exception:
    def _live_platform_grid_path(base=None):
        import os
        from pathlib import Path
        o = os.environ.get("ACCD_PLATFORM_GRID_PATH") or os.environ.get("ACCD_GRID_PATH")
        return Path(o) if o else Path(os.environ.get("ACCD_MEMORY_ROOT", "/var/data/accd_memory")) / "platform" / "grid.pkl"


KINDS = ("org", "user")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

GRID_NAME = "grid.pkl"
MANIFEST_NAME = "manifest.json"

MembershipCheck = Callable[[str, str], bool]  # (user_id, org_id) -> active member?


class InstanceGridError(RuntimeError):
    pass


class AccessDenied(InstanceGridError):
    pass


@dataclass(frozen=True)
class OwnerRef:
    kind: str
    id: str

    def __post_init__(self):
        if self.kind not in KINDS:
            raise InstanceGridError(f"bad owner kind: {self.kind!r}")
        if not isinstance(self.id, str) or not _ID_RE.match(self.id):
            raise InstanceGridError(f"bad owner id: {self.id!r}")

    @property
    def brain_id(self) -> str:
        """Brain ID is the owner's ID (user or org). Brain scope rules come from the architecture spec."""
        return self.id

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.id}"

    @property
    def snapshot_prefix(self) -> str:
        return f"snapshots/instances/{self.kind}/{self.id}"


def memory_root(base: Optional[str] = None) -> Path:
    return Path(base or os.environ.get("ACCD_MEMORY_ROOT") or "data/memory")


# ----------------------------------------------------------------------------
# Ownership and access
# ----------------------------------------------------------------------------

def resolve_room_grid(
    *,
    room_scope: str,
    account_type: str,
    user_id: str,
    org_id: Optional[str],
    is_active_member: MembershipCheck,
) -> OwnerRef:
    """
    Which grid an activity in a room writes to and reads from.

      room_scope "org"      -> the org grid (requires active membership).
                               Any org member's org-room activity lands here.
      room_scope "personal" -> regular account: the user's own grid.
                               worker: the org grid (workers have no personal grid).
      admin accounts        -> no instance grid.

    A regular account's personal grid and its org membership are never linked:
    there is no fallback from one to the other.
    """
    uid = str(user_id)
    if account_type == "admin":
        raise AccessDenied("admin accounts do not own an instance grid")
    if room_scope == "org" or (room_scope == "personal" and account_type == "worker"):
        if not org_id or not is_active_member(uid, str(org_id)):
            raise AccessDenied("not an active member of this organization")
        return OwnerRef("org", str(org_id))
    if room_scope == "personal" and account_type == "regular":
        return OwnerRef("user", uid)
    raise AccessDenied(f"cannot resolve a grid for scope={room_scope!r} account={account_type!r}")


def can_access(
    *,
    user_id: str,
    owner: OwnerRef,
    is_active_member: MembershipCheck,
) -> bool:
    """
    user grid -> only that user.
    org grid  -> active members of that org only.
    Membership in an org never grants access to another member's personal grid.
    """
    if owner.kind == "user":
        return str(user_id) == owner.id
    return bool(is_active_member(str(user_id), owner.id))


def require_access(*, user_id: str, owner: OwnerRef, is_active_member: MembershipCheck) -> OwnerRef:
    if not can_access(user_id=user_id, owner=owner, is_active_member=is_active_member):
        raise AccessDenied(f"no access to {owner.key}")
    return owner


# ----------------------------------------------------------------------------
# Platform snapshot (from Hugging Face, pinned by sha256)
# ----------------------------------------------------------------------------

def platform_cache_path(version: int, base: Optional[str] = None) -> Path:
    return memory_root(base) / "platform" / f"platform_grid_v{int(version)}.pkl"


def fetch_platform_snapshot(
    version: int,
    *,
    expected_sha256: str,
    downloader: Callable[[int, str], None],
    base: Optional[str] = None,
) -> Path:
    """
    downloader(version, dest_path) fetches the platform grid from Hugging Face.
    The file is kept only if its sha256 matches the pinned value.
    """
    if int(version) < 1:
        raise InstanceGridError("platform version must be >= 1")
    dest = platform_cache_path(version, base)
    if dest.is_file() and sha256_file(dest) == expected_sha256:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".dl")
    downloader(int(version), str(tmp))
    if not tmp.is_file() or sha256_file(tmp) != expected_sha256:
        if tmp.exists():
            tmp.unlink()
        raise InstanceGridError("platform snapshot failed sha256 check; nothing cached")
    os.replace(tmp, dest)
    return dest


# ----------------------------------------------------------------------------
# Signup: create the grid once
# ----------------------------------------------------------------------------

def instance_dir(owner: OwnerRef, base: Optional[str] = None) -> Path:
    root = (memory_root(base) / "instances").resolve()
    d = (root / owner.kind / owner.id).resolve()
    if root not in d.parents:
        raise InstanceGridError("instance path escaped instances root")
    return d


def grid_path(owner: OwnerRef, base: Optional[str] = None) -> Path:
    return instance_dir(owner, base) / GRID_NAME


def _write_manifest(d: Path, payload: dict) -> None:
    tmp = d / (MANIFEST_NAME + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, d / MANIFEST_NAME)



def resolve_platform_source(
    platform_version: int,
    *,
    base: Optional[str] = None,
    expected_sha256: Optional[str] = None,
) -> Path:
    """
    Prefer sha-pinned HF cache; else live platform grid from seed/train on this machine.
    """
    cached = platform_cache_path(int(platform_version), base)
    if cached.is_file():
        if expected_sha256 and sha256_file(cached) != expected_sha256:
            raise InstanceGridError("cached platform snapshot sha256 mismatch")
        return cached
    try:
        live = _live_platform_grid_path(base)
    except Exception:
        live = None
    if live is not None and Path(live).is_file():
        print(f"[instance_grid] using live platform grid {live}")
        return Path(live)
    raise InstanceGridError(
        "platform snapshot not cached and no live platform grid.pkl; "
        "run platform seed or fetch_platform_snapshot before signup"
    )

def create_instance_grid(
    owner: OwnerRef,
    *,
    platform_version: int,
    base: Optional[str] = None,
) -> Path:
    """
    Signup-time only. Copies the cached platform snapshot into the owner's
    own grid. Refuses to run if the owner already has a grid.
    """
    grid = grid_path(owner, base)
    if grid.exists():
        raise InstanceGridError(f"{owner.key} already has a grid; creation is once per owner")
    src = resolve_platform_source(int(platform_version), base=base)

    d = grid.parent
    d.mkdir(parents=True, exist_ok=True)
    tmp = grid.with_name(GRID_NAME + ".tmp")
    with open(src, "rb") as fin, open(tmp, "wb") as fout:
        fout.write(fin.read())
    os.replace(tmp, grid)  # first writer wins: exists() was checked above
    _write_manifest(d, {
        "owner": owner.key,
        "created_at": int(time.time()),
        "platform_version": int(platform_version),
        "platform_sha256": sha256_file(src),
        "last_snapshot": None,
    })
    return grid


# ----------------------------------------------------------------------------
# Writes and snapshots
# ----------------------------------------------------------------------------

def write_instance_grid_bytes(owner: OwnerRef, data: bytes, base: Optional[str] = None) -> Path:
    """Atomically replace the owner's live grid. Platform cache is never touched."""
    grid = grid_path(owner, base)
    if not grid.exists():
        raise InstanceGridError(f"{owner.key} has no grid; create it at signup first")
    tmp = grid.with_name(GRID_NAME + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, grid)
    return grid


def snapshot_instance_grid(
    owner: OwnerRef,
    *,
    uploader: Callable[[str, str], None],
    base: Optional[str] = None,
) -> str:
    """
    Gzip the owner's grid and hand it to uploader(key, local_gz_path).
    The key is built from the owner and checked against the storage policy.
    Returns the B2 key.
    """
    grid = grid_path(owner, base)
    if not grid.is_file():
        raise InstanceGridError(f"{owner.key} has no grid to snapshot")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    key = check_b2_key(f"{owner.snapshot_prefix}/{stamp}-{GRID_NAME}.gz")
    gz = grid.with_name(f"snapshot-{stamp}.gz")
    sha = gzip_file(grid, gz)
    uploader(key, str(gz))
    gz.unlink()
    d = grid.parent
    manifest = json.loads((d / MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["last_snapshot"] = {"key": key, "sha256_gz": sha, "at": stamp}
    _write_manifest(d, manifest)
    return key


def restore_instance_grid(
    owner: OwnerRef,
    *,
    key: str,
    expected_sha256_gz: str,
    downloader: Callable[[str, str], None],
    base: Optional[str] = None,
) -> Path:
    """Rebuild the owner's live grid from a B2 snapshot after a server restart."""
    key = check_b2_key(key)
    if not key.startswith(owner.snapshot_prefix + "/"):
        raise AccessDenied("snapshot does not belong to this owner")
    d = instance_dir(owner, base)
    d.mkdir(parents=True, exist_ok=True)
    gz = d / "restore.gz"
    downloader(key, str(gz))
    if sha256_file(gz) != expected_sha256_gz:
        gz.unlink(missing_ok=True)
        raise InstanceGridError("snapshot failed sha256 check")
    tmp = d / "restore.pkl"
    gunzip_file(gz, tmp)
    os.replace(tmp, grid_path(owner, base))
    gz.unlink(missing_ok=True)
    return grid_path(owner, base)
