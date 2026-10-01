"""
Accodite DB bootstrap
=====================
Thin re-export of the Neon engine/session layer.

Kept as `database.py` for backward compatibility with ported modules that do:

    from database import engine, SessionLocal, Base
"""
from __future__ import annotations

from db.neon import (
    Base,
    get_sync_engine,
    get_sync_sessionmaker,
    get_async_engine,
    get_async_sessionmaker,
    session_scope,
    async_session_scope,
    ping_sync,
    ping_async,    ASYNC_AVAILABLE,
)


# Lazy engine/session accessors — nothing connects until first use.
def _engine():
    return get_sync_engine()


def _async_engine():
    return get_async_engine()


def _SessionLocal():
    return get_sync_sessionmaker()


def _AsyncSessionLocal():
    return get_async_sessionmaker()


# Convenience aliases for ported code that does `from database import engine`.
# These are lazy objects — calling `.connect()` or `.begin()` triggers connect.
# REAL-ENGINE: expose the actual SQLAlchemy Engine/SessionMaker objects.
# get_sync_engine() / get_sync_sessionmaker() are themselves lazy
# (built on first call), so no extra wrapper is needed — and inspect()
# requires a real Engine, not a proxy.
engine = get_sync_engine()
async_engine = get_async_engine() if ASYNC_AVAILABLE else None
SessionLocal = get_sync_sessionmaker()
AsyncSessionLocal = get_async_sessionmaker() if ASYNC_AVAILABLE else None
