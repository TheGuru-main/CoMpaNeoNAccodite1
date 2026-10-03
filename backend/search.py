"""
Accodite Search
===============
Tokenized full-text search across:
    - the memory grid (documents already indexed)
    - room message history
    - artifacts (documents space)

Endpoint:
    GET /search?q=...&scope=grid|messages|all&limit=20
"""
from __future__ import annotations
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_

from database import SessionLocal
from db_models import User, Message, Workspace, Artifact
from auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


def _tokenize_query(q: str) -> List[str]:
    try:
        from tokenizer import tokenize
        toks = tokenize(q, "en") or []
        out = []
        for t in toks:
            if isinstance(t, dict):
                v = t.get("stem") or t.get("original") or t.get("token")
                if v: out.append(str(v))
            elif isinstance(t, str):
                out.append(t)
        if out:
            return out
    except Exception:
        pass
    return [w for w in (q or "").split() if w]


def _search_grid(q: str, limit: int) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    try:
        from memory_grid import MemoryGrid
        grid = MemoryGrid()
        raw = None
        if hasattr(grid, "retrieve"):
            try:
                raw = grid.retrieve(q, top_k=limit)
            except TypeError:
                raw = grid.retrieve(q)
        if not raw:
            return []
        for h in (raw or [])[:limit]:
            if isinstance(h, dict):
                hits.append({
                    "source": "grid",
                    "id": str(h.get("doc_id") or h.get("id") or ""),
                    "title": (h.get("source") or "grid document")[:60],
                    "snippet": (h.get("text") or h.get("content") or "")[:180],
                    "score": float(h.get("score") or 0.0),
                })
            else:
                hits.append({
                    "source": "grid",
                    "id": "",
                    "title": "grid document",
                    "snippet": str(h)[:180],
                    "score": 0.0,
                })
    except Exception as e:
        print(f"[search] grid failed: {type(e).__name__}: {e}")
    return hits


def _search_messages(db, user, q: str, limit: int) -> List[Dict[str, Any]]:
    try:
        like = f"%{q}%"
        # messages in rooms the user is a member of
        from db.models_org import WorkspaceMember
        member_ws = db.query(WorkspaceMember.workspace_id).filter(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.removed_at.is_(None),
        )
        owned_ws = db.query(Workspace.id).filter(Workspace.user_id == user.id)
        allowed = set([r[0] for r in member_ws.all()] + [r[0] for r in owned_ws.all()])
        if not allowed:
            return []
        rows = (
            db.query(Message)
            .filter(
                Message.workspace_id.in_(list(allowed)),
                Message.content.ilike(like),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for m in rows:
            ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
            out.append({
                "source": "message",
                "id": str(m.id),
                "room_id": str(m.workspace_id),
                "title": (ws.project_name if ws else "room") + f" · {m.role}",
                "snippet": (m.content or "")[:180],
                "score": 0.5,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
        return out
    except Exception as e:
        print(f"[search] messages failed: {type(e).__name__}: {e}")
        return []


def _search_artifacts(db, user, q: str, limit: int) -> List[Dict[str, Any]]:
    try:
        like = f"%{q}%"
        rows = (
            db.query(Artifact)
            .filter(
                Artifact.user_id == user.id,
                or_(Artifact.name.ilike(like), Artifact.content.ilike(like)),
            )
            .order_by(Artifact.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "source": "artifact",
            "id": str(a.id),
            "title": a.name or a.kind,
            "snippet": (a.content or "")[:180] or f"{a.kind} · {a.size or 0} bytes",
            "score": 0.4,
            "kind": a.kind,
            "url": f"/uploads/{a.id}",
        } for a in rows]
    except Exception as e:
        print(f"[search] artifacts failed: {type(e).__name__}: {e}")
        return []


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    scope: str = Query("all"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    q = q.strip()
    results: List[Dict[str, Any]] = []
    tokens = _tokenize_query(q)

    if scope in ("grid", "all"):
        results.extend(_search_grid(q, limit))

    db = SessionLocal()
    try:
        if scope in ("messages", "all"):
            results.extend(_search_messages(db, user, q, limit))
        if scope in ("documents", "all"):
            results.extend(_search_artifacts(db, user, q, limit))
    finally:
        db.close()

    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    return {
        "query": q,
        "tokens": tokens,
        "scope": scope,
        "count": len(results),
        "results": results[:limit],
    }
