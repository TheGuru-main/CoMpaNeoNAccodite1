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
    ping_async,
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
class _LazyEngine:
    def __getattr__(self, name):
        return getattr(_engine(), name)


class _LazySessionMaker:
    def __call__(self, *a, **k):
        return get_sync_sessionmaker()(*a, **k)

    def __getattr__(self, name):
        return getattr(get_sync_sessionmaker(), name)


class _LazyAsyncEngine:
    def __getattr__(self, name):
        return getattr(_async_engine(), name)


class _LazyAsyncSessionMaker:
    def __call__(self, *a, **k):
        return get_async_sessionmaker()(*a, **k)

    def __getattr__(self, name):
        return getattr(get_async_sessionmaker(), name)


engine = _LazyEngine()
async_engine = _LazyAsyncEngine()
SessionLocal = _LazySessionMaker()
AsyncSessionLocal = _LazyAsyncSessionMaker()
