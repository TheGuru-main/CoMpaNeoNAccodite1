"""
Shared MemoryGrid is the ONLY in-process document storage.

Rules:
  - Never invent a new empty MemoryGrid() for generate / train / seed / understand
    when the shared grid is missing or empty.
  - Prefer integration._STATE["grid"], then process singleton, then load_grid()
    from ACCD_GRID_PATH / local snapshot, then optional B2 snapshot.
  - If still missing/empty and require_docs=True → raise GridUnavailable.
"""
from __future__ import annotations

import os
from typing import Any, Optional


class GridUnavailable(RuntimeError):
    """Shared grid missing or empty — do not fabricate a new one."""


def _doc_count(grid) -> int:
    if grid is None:
        return 0
    docs = getattr(grid, "documents", None) or {}
    try:
        return len(docs)
    except Exception:
        return 0


def _bind(grid) -> Any:
    if grid is None:
        return None
    try:
        from integration import get_state
        get_state()["grid"] = grid
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


def _try_load_disk():
    try:
        from memory.memory_grid import load_grid
    except Exception:
        try:
            from memory_grid import load_grid
        except Exception:
            return None
    try:
        return load_grid()
    except Exception as e:
        print("[shared_grid] load_grid failed:", type(e).__name__, e)
        return None


def _try_load_b2():
    try:
        from storage.b2 import b2_enabled, b2_get_json
        if not b2_enabled():
            return None
        data = b2_get_json("training/memory_grid/latest.json")
        if not isinstance(data, dict):
            return None
        try:
            from memory.memory_grid import _grid_from_dict, set_process_grid
        except Exception:
            from memory_grid import _grid_from_dict, set_process_grid
        grid = _grid_from_dict(data)
        set_process_grid(grid)
        return grid
    except Exception as e:
        print("[shared_grid] B2 load failed:", type(e).__name__, e)
        return None


def get_shared_grid(*, require_docs: bool = False, allow_empty: bool = True):
    """
    DEPRECATED name: means PLATFORM grid (Accodite seed/train target), not tenant instance.

    Prefer memory.platform_grid.get_platform_grid / save_platform_grid.
    Instance grids (org|user) use memory.instance_grid when wired.
    """
    # 0) platform grid first
    try:
        from memory.platform_grid import load_platform_grid, PlatformGridError
        try:
            return load_platform_grid(require_docs=require_docs, allow_empty=allow_empty)
        except PlatformGridError:
            if require_docs:
                raise GridUnavailable("platform grid missing or empty — seed platform first")
    except ImportError:
        pass
    except GridUnavailable:
        raise
    except Exception as e:
        print("[shared_grid] platform load:", type(e).__name__, e)

    grid = None
    # 1) integration state
    try:
        from integration import get_state
        grid = get_state().get("grid")
    except Exception:
        grid = None

    # 2) process singleton without creating
    if grid is None:
        try:
            from memory.memory_grid import _SHARED_GRID
            grid = _SHARED_GRID
        except Exception:
            try:
                import memory.memory_grid as mg
                grid = getattr(mg, "_SHARED_GRID", None)
            except Exception:
                grid = None

    # 3) disk snapshot
    if grid is None or (require_docs and _doc_count(grid) == 0):
        loaded = _try_load_disk()
        if loaded is not None and (not require_docs or _doc_count(loaded) > 0 or _doc_count(grid) == 0):
            if loaded is not None:
                grid = loaded
                _bind(grid)

    # 4) B2 snapshot
    if grid is None or (require_docs and _doc_count(grid) == 0):
        loaded = _try_load_b2()
        if loaded is not None:
            grid = loaded
            _bind(grid)

    if grid is None:
        raise GridUnavailable(
            "Shared MemoryGrid is not available. "
            "Load a snapshot (ACCD_GRID_PATH / B2) or run seed into the shared grid. "
            "Refusing to create a new empty MemoryGrid."
        )

    if require_docs and _doc_count(grid) == 0:
        raise GridUnavailable(
            "Shared MemoryGrid is empty (0 documents). "
            "Run seed_crawl against the shared grid and save_grid before generate/train."
        )

    if not allow_empty and _doc_count(grid) == 0:
        raise GridUnavailable("Shared MemoryGrid is empty.")

    return _bind(grid)


def bootstrap_shared_grid(*, create_if_missing: bool = True):
    """
    App startup / seed only: bind PLATFORM grid (legacy name bootstrap_shared_grid).
    Prefer bootstrap_platform_grid.
    """
    try:
        from memory.platform_grid import bootstrap_platform_grid
        return bootstrap_platform_grid(create_if_missing=create_if_missing)
    except Exception as e:
        print("[shared_grid] bootstrap_platform:", type(e).__name__, e)
    try:
        return get_shared_grid(require_docs=False, allow_empty=True)
    except GridUnavailable:
        pass
    loaded = _try_load_disk() or _try_load_b2()
    if loaded is not None:
        return _bind(loaded)
    if not create_if_missing:
        raise GridUnavailable("No shared grid snapshot to bootstrap")
    try:
        from memory.memory_grid import MemoryGrid
    except Exception:
        from memory_grid import MemoryGrid
    grid = MemoryGrid()
    print("[shared_grid] bootstrap: created single empty shared grid for seed")
    return _bind(grid)


def persist_shared_grid(grid=None) -> str:
    """Save shared grid to disk + B2."""
    if grid is None:
        grid = get_shared_grid(require_docs=False, allow_empty=True)
    try:
        from memory.memory_grid import save_grid
    except Exception:
        from memory_grid import save_grid
    return save_grid(grid)
