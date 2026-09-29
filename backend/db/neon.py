"""
Neon Postgres engine + session factory.

Sync engine (psycopg) for scripts and CLI.
Async engine (asyncpg) for FastAPI routes.
"""
from __future__ import annotations
import os
from typing import AsyncIterator, Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# LAZY-ASYNC: async bits import on demand; greenlet may be absent on some
# runtimes (Termux w/ bleeding-edge Python). Sync path never needs it.
try:
    from sqlalchemy.ext.asyncio import (
        create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine,
    )
    ASYNC_AVAILABLE = True
except ImportError:
    create_async_engine = None
    AsyncSession = object
    async_sessionmaker = None
    AsyncEngine = object
    ASYNC_AVAILABLE = False


Base = declarative_base()


def _require(name: str, default: Optional[str] = None) -> str:
    v = os.environ.get(name, default)
    if not v:
        raise RuntimeError(f"missing required env var: {name}")
    return v


def _normalize(url: str, *, async_driver: bool) -> str:
    """
    Accepts any of:
        postgres://...
        postgresql://...
        postgresql+psycopg://...
        postgresql+asyncpg://...
    Returns a URL with the correct driver prefix for the engine type.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if async_driver:
        url = url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    else:
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if "sslmode=" not in url and "neon.tech" in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


# ---------------------------------------------------------------------------
# SYNC
# ---------------------------------------------------------------------------

_sync_engine = None
_sync_sessionmaker = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is not None:
        return _sync_engine
    url = _require("DATABASE_URL")
    url = _normalize(url, async_driver=False)
    _sync_engine = create_engine(
        url,
        pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
        future=True,
    )
    return _sync_engine


def get_sync_sessionmaker():
    global _sync_sessionmaker
    if _sync_sessionmaker is not None:
        return _sync_sessionmaker
    _sync_sessionmaker = sessionmaker(
        bind=get_sync_engine(),
        expire_on_commit=False,
        class_=Session,
    )
    return _sync_sessionmaker


def session_scope() -> Iterator[Session]:
    """Use with 'with session_scope() as s:'."""
    s = get_sync_sessionmaker()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


# ---------------------------------------------------------------------------
# ASYNC
# ---------------------------------------------------------------------------

_async_engine: Optional[AsyncEngine] = None
_async_sessionmaker = None


def get_async_engine():
    if not ASYNC_AVAILABLE:
        raise RuntimeError(
            "async SQLAlchemy unavailable: install greenlet "
            "(pip install greenlet) or use sqlalchemy[asyncio]"
        )
    global _async_engine
    if _async_engine is not None:
        return _async_engine
    url = os.environ.get("DATABASE_URL_ASYNC") or _require("DATABASE_URL")
    url = _normalize(url, async_driver=True)
    _async_engine = create_async_engine(
        url,
        pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
        connect_args={
            "timeout": 10,
            "command_timeout": 30,
            # Neon pooler-safe: disable prepared statements if behind -pooler
            "statement_cache_size": 0 if "-pooler" in url else 100,
        },
        future=True,
    )
    return _async_engine


def get_async_sessionmaker():
    if not ASYNC_AVAILABLE:
        raise RuntimeError("async SQLAlchemy unavailable: install greenlet")
    global _async_sessionmaker
    if _async_sessionmaker is not None:
        return _async_sessionmaker
    _async_sessionmaker = async_sessionmaker(
        bind=get_async_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return _async_sessionmaker


async def async_session_scope() -> AsyncIterator[AsyncSession]:
    s = get_async_sessionmaker()()
    try:
        yield s
        await s.commit()
    except Exception:
        await s.rollback()
        raise
    finally:
        await s.close()


# ---------------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------------

def ping_sync() -> bool:
    from sqlalchemy import text
    try:
        with get_sync_engine().connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def ping_async() -> bool:
    if not ASYNC_AVAILABLE:
        return False
    from sqlalchemy import text
    try:
        async with get_async_engine().connect() as c:
            await c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
