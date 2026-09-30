"""Accodite external package — re-exports from external.py."""
try:
    from .external import *  # noqa: F401,F403
except Exception:
    # flat layout (external/ on sys.path): import the sibling module directly
    try:
        from external import *  # type: ignore  # noqa: F401,F403
    except Exception:
        pass
