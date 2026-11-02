"""
Platform grid — Accodite-owned seed/train target (not a tenant instance grid).

Rules:
  - Seed training and platform weight/LoRA publish write HERE.
  - Tenants receive a SNAPSHOT copy into instance grids (org|user) at download.
  - Workers have no grid; they use the org instance grid.
  - get_shared_grid is an alias for get_platform_grid (backward compatible).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional, Tuple

PLATFORM_DIR_NAME = "platform"
GRID_NAME = "grid.pkl"
MANIFEST_NAME = "manifest.json"
LORA_DIR_NAME = "lora"


class PlatformGridError(RuntimeError):
    pass


def platform_root(base: Optional[str] = None) -> Path:
    root = base or os.environ.get("ACCD_MEMORY_ROOT") or os.environ.get("ACCD_MODEL_DIR") or "/var/data/accd_memory"
    # Prefer dedicated platform path when set
    p = os.environ.get("ACCD_PLATFORM_GRID_DIR")
    if p:
        return Path(p)
    return Path(root) / PLATFORM_DIR_NAME


def platform_grid_path(base: Optional[str] = None) -> Path:
    override = os.environ.get("ACCD_PLATFORM_GRID_PATH") or os.environ.get("ACCD_GRID_PATH")
    if override:
        return Path(override)
    return platform_root(base) / GRID_NAME


def platform_manifest_path(base: Optional[str] = None) -> Path:
    return platform_root(base) / MANIFEST_NAME


def platform_lora_dir(base: Optional[str] = None) -> Path:
    return platform_root(base) / LORA_DIR_NAME


def _bind_platform(grid) -> Any:
    try:
        from integration import get_state
        st = get_state()
        st["platform_grid"] = grid
        st["grid"] = grid  # compat: seed/train still read state["grid"]
        st["grid_kind"] = "platform"
    except Exception:
        pass
    try:
        from memory.memory_grid import set_process_grid
        set_process_grid(grid)
    except Exception:
        try:
            from memory_grid import set_process_grid
            set_process_grid(grid)
        except Exception:
            pass
    return grid


def _doc_count(grid) -> int:
    if grid is None:
        return 0
    try:
        return len(getattr(grid, "documents", None) or {})
    except Exception:
        return 0


def load_platform_grid(*, require_docs: bool = False, allow_empty: bool = True, base: Optional[str] = None):
    """Load platform grid from disk (or process state). Does not create empty unless bootstrap."""
    # 1) state
    try:
        from integration import get_state
        st = get_state()
        g = st.get("platform_grid") or (st.get("grid") if st.get("grid_kind") == "platform" else None)
        if g is not None and (not require_docs or _doc_count(g) > 0):
            return _bind_platform(g)
    except Exception:
        pass

    path = platform_grid_path(base)
    if path.is_file():
        try:
            from memory.memory_grid import load_grid
        except Exception:
            from memory_grid import load_grid
        grid = load_grid(str(path))
        if require_docs and _doc_count(grid) == 0:
            raise PlatformGridError(f"platform grid empty at {path}")
        if not allow_empty and _doc_count(grid) == 0:
            raise PlatformGridError(f"platform grid empty at {path}")
        print(f"[platform_grid] loaded {path} docs={_doc_count(grid)}")
        return _bind_platform(grid)

    raise PlatformGridError(
        f"Platform grid not found at {path}. Run seed into platform grid and save_platform_grid."
    )


def bootstrap_platform_grid(*, create_if_missing: bool = True, base: Optional[str] = None):
    """Startup / seed only: load platform or create ONE empty platform grid for seed fill."""
    try:
        return load_platform_grid(require_docs=False, allow_empty=True, base=base)
    except PlatformGridError:
        pass
    if not create_if_missing:
        raise PlatformGridError("No platform grid and create_if_missing=False")
    try:
        from memory.memory_grid import MemoryGrid
    except Exception:
        from memory_grid import MemoryGrid
    grid = MemoryGrid()
    print("[platform_grid] bootstrap: empty platform grid for seed")
    return _bind_platform(grid)


def save_platform_grid(grid=None, base: Optional[str] = None) -> str:
    """Persist platform grid + manifest. Seed/train must call this (not a tenant path)."""
    if grid is None:
        grid = load_platform_grid(require_docs=False, allow_empty=True, base=base)
    path = platform_grid_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from memory.memory_grid import save_grid
    except Exception:
        from memory_grid import save_grid
    out = save_grid(grid, str(path))
    man = {
        "kind": "platform",
        "path": str(path),
        "docs": _doc_count(grid),
        "saved_at": time.time(),
        "version": int(os.environ.get("ACCD_PLATFORM_GRID_VERSION") or "1"),
    }
    try:
        platform_manifest_path(base).write_text(json.dumps(man, indent=2), encoding="utf-8")
    except Exception as e:
        print("[platform_grid] manifest skip:", e)
    _bind_platform(grid)
    print(f"[platform_grid] saved {out} docs={man['docs']}")
    return str(out)


def snapshot_platform_grid(*, label: Optional[str] = None, base: Optional[str] = None) -> str:
    """
    Copy platform grid.pkl to platform/snapshots/<ts>[_label].pkl for HF/B2 publish.
    Returns snapshot path.
    """
    src = platform_grid_path(base)
    if not src.is_file():
        # try save current bound grid first
        try:
            save_platform_grid(base=base)
        except Exception:
            pass
    if not src.is_file():
        raise PlatformGridError("no platform grid.pkl to snapshot")
    snap_dir = platform_root(base) / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = f"platform_grid_{ts}"
    if label:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
        name += f"_{safe}"
    dest = snap_dir / f"{name}.pkl"
    dest.write_bytes(src.read_bytes())
    meta = {
        "source": str(src),
        "snapshot": str(dest),
        "bytes": dest.stat().st_size,
        "sha256": None,
        "at": time.time(),
    }
    try:
        import hashlib
        meta["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
    except Exception:
        pass
    (snap_dir / f"{name}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[platform_grid] snapshot {dest} sha={meta.get('sha256')}")
    return str(dest)


# --- aliases used by seed/train (replace shared language) ---
def get_platform_grid(*, require_docs: bool = False, allow_empty: bool = True, base: Optional[str] = None):
    return load_platform_grid(require_docs=require_docs, allow_empty=allow_empty, base=base)
