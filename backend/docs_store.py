"""
GSP documents: Neon + Backblaze B2.

parent_type: repo | room
parent_id: repo name or room id
doc_uid: tokenizer letter-chain of doc_name
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from gsp_chain import (
    letter_chain,
    start_row_for_name,
    uid_from_name,
    validate_cell,
    validate_resource_name,
    verify_uid_matches_name,
)

try:
    from storage.b2 import b2_enabled, b2_put_json, b2_get_json
except Exception:
    def b2_enabled():
        return False

    def b2_put_json(key, obj):
        raise RuntimeError("b2 unavailable")

    def b2_get_json(key):
        raise RuntimeError("b2 unavailable")


def _db():
    from database import SessionLocal
    return SessionLocal()


def ensure_gsp_documents_table(engine=None):
    """Create gsp_documents if missing (idempotent)."""
    from sqlalchemy import text
    if engine is None:
        from database import engine as eng
        engine = eng
    ddl = """
    CREATE TABLE IF NOT EXISTS gsp_documents (
        id UUID PRIMARY KEY,
        parent_type VARCHAR(16) NOT NULL,
        parent_id VARCHAR(128) NOT NULL,
        scope VARCHAR(16) NOT NULL DEFAULT 'user',
        doc_name VARCHAR(128) NOT NULL,
        doc_uid TEXT NOT NULL,
        chain JSONB,
        start_row INTEGER,
        kind VARCHAR(32) NOT NULL DEFAULT 'sheet',
        n_rows INTEGER,
        n_cols INTEGER,
        cells_json JSONB,
        b2_snapshot_key TEXT,
        owner_user_id UUID,
        org_id UUID,
        version INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        UNIQUE (parent_type, parent_id, doc_name)
    );
    CREATE INDEX IF NOT EXISTS ix_gsp_docs_parent ON gsp_documents (parent_type, parent_id);
    CREATE INDEX IF NOT EXISTS ix_gsp_docs_uid ON gsp_documents (doc_uid);
    """
    with engine.begin() as conn:
        for stmt in ddl.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))


def _b2_key(parent_type: str, parent_id: str, doc_uid: str, name: str = "snapshot.json") -> str:
    safe_parent = "".join(c if c.isalnum() or c in "-_" else "_" for c in parent_id)[:80]
    safe_uid = (doc_uid or "uid")[:120]
    return f"docs/{parent_type}/{safe_parent}/{safe_uid}/{name}"


def _grid_b2_key(kind: str = "memory_grid") -> str:
    return f"training/{kind}/latest.json"


def create_document(
    *,
    parent_type: str,
    parent_id: str,
    doc_name: str,
    kind: str = "sheet",
    scope: str = "user",
    n_rows: int = 100,
    n_cols: int = 26,
    owner_user_id=None,
    org_id=None,
) -> Dict[str, Any]:
    parent_type = (parent_type or "repo").strip().lower()
    if parent_type not in ("repo", "room"):
        raise ValueError("parent_type must be repo or room")
    if parent_type == "repo":
        parent_id = validate_resource_name(parent_id, what="repo name")
    else:
        parent_id = str(parent_id or "").strip()
        if not parent_id:
            raise ValueError("room id required")
    doc_name = validate_resource_name(doc_name, what="doc name")
    kind = (kind or "sheet").strip().lower()
    kind = {
        "sheets": "sheet", "dbase": "xlsx", "collabsheet": "workspace",
        "presentations": "pptx",
    }.get(kind, kind)
    if kind not in ("sheet", "sheets", "xlsx", "dbase", "workspace", "collabsheet", "pptx", "presentations"):
        raise ValueError("invalid kind")

    info = start_row_for_name(doc_name)
    uid = uid_from_name(doc_name)
    if kind in ("sheet", "workspace"):
        cells = {"cells": {}, "row_min": 1, "row_max": 64, "col_min": 0, "col_max": 53}
        n_rows, n_cols = 64, 54
    elif kind == "pptx":
        cells = {"slides": [{"id": "s0", "title": doc_name, "body": "", "gradient": "g00", "blocks": []}]}
    else:
        cells = {"cells": {}, "sheets": {"Sheet1": {"cells": {}}}, "active_sheet": "Sheet1", "n_rows": n_rows, "n_cols": n_cols, "configurable": True, "gsp": {}}

    doc_id = uuid.uuid4()
    b2_key = None
    snapshot = {
        "id": str(doc_id),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": uid,
        "chain": info["chain"],
        "start_row": info["start_row"],
        "kind": kind,
        "data": cells,
        "version": 1,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    if b2_enabled():
        try:
            b2_key = b2_put_json(_b2_key(parent_type, parent_id, uid), snapshot)
        except Exception as e:
            print(f"[docs] b2 put failed: {e}")

    db = _db()
    try:
        ensure_gsp_documents_table()
        from sqlalchemy import text
        db.execute(
            text(
                """
                INSERT INTO gsp_documents (
                    id, parent_type, parent_id, scope, doc_name, doc_uid, chain,
                    start_row, kind, n_rows, n_cols, cells_json, b2_snapshot_key,
                    owner_user_id, org_id, version, created_at, updated_at
                ) VALUES (
                    :id, :parent_type, :parent_id, :scope, :doc_name, :doc_uid,
                    CAST(:chain AS JSONB), :start_row, :kind, :n_rows, :n_cols,
                    CAST(:cells AS JSONB), :b2_key, :owner, :org, 1, NOW(), NOW()
                )
                """
            ),
            {
                "id": str(doc_id),
                "parent_type": parent_type,
                "parent_id": parent_id,
                "scope": scope,
                "doc_name": doc_name,
                "doc_uid": uid,
                "chain": json.dumps(info["chain"]),
                "start_row": info["start_row"],
                "kind": kind,
                "n_rows": n_rows,
                "n_cols": n_cols,
                "cells": json.dumps(cells),
                "b2_key": b2_key,
                "owner": str(owner_user_id) if owner_user_id else None,
                "org": str(org_id) if org_id else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "ok": True,
        "id": str(doc_id),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": uid,
        "chain": info["chain"],
        "start_row": info["start_row"],
        "kind": kind,
        "b2_snapshot_key": b2_key,
        "grid": cells if kind in ("sheet", "workspace") else {"n_rows": n_rows, "n_cols": n_cols},
    }


def list_documents(parent_type: str, parent_id: str) -> List[Dict[str, Any]]:
    db = _db()
    try:
        ensure_gsp_documents_table()
        from sqlalchemy import text
        rows = db.execute(
            text(
                """
                SELECT id, doc_name, doc_uid, kind, start_row, chain, b2_snapshot_key, version, updated_at
                FROM gsp_documents
                WHERE parent_type = :pt AND parent_id = :pid
                ORDER BY doc_name
                """
            ),
            {"pt": parent_type, "pid": parent_id},
        ).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_document(parent_type: str, parent_id: str, doc_name: str) -> Dict[str, Any]:
    db = _db()
    try:
        ensure_gsp_documents_table()
        from sqlalchemy import text
        row = db.execute(
            text(
                """
                SELECT * FROM gsp_documents
                WHERE parent_type = :pt AND parent_id = :pid AND doc_name = :n
                LIMIT 1
                """
            ),
            {"pt": parent_type, "pid": parent_id, "n": doc_name},
        ).mappings().first()
        if not row:
            raise KeyError("doc not found")
        meta = dict(row)
        data = meta.get("cells_json") or {"cells": {}}
        if isinstance(data, str):
            data = json.loads(data)
        # Prefer B2 snapshot if present
        if meta.get("b2_snapshot_key") and b2_enabled():
            try:
                snap = b2_get_json(meta["b2_snapshot_key"])
                if isinstance(snap, dict) and snap.get("data"):
                    data = snap["data"]
            except Exception as e:
                print(f"[docs] b2 get fallback to db: {e}")
        return {"meta": meta, "data": data}
    finally:
        db.close()


def write_cell(
    *,
    parent_type: str,
    parent_id: str,
    doc_name: str,
    doc_uid: str = "",
    row: int,
    col: int,
    value: str = "",
    place: bool = False,
) -> Dict[str, Any]:
    if doc_uid and not verify_uid_matches_name(doc_name, doc_uid):
        raise PermissionError("doc_uid does not match name letter-chain")
    got = get_document(parent_type, parent_id, doc_name)
    meta = got["meta"]
    data = got["data"] or {"cells": {}}
    kind = meta.get("kind") or "sheet"
    if kind in ("sheet", "workspace"):
        row, col = validate_cell(row, col)
    cells = data.setdefault("cells", {})
    key = f"{row}:{col}"
    entry = {"value": value, "row": row, "col": col}
    if place or kind == "workspace":
        entry["placed"] = True
        entry["placement"] = {
            "row": row,
            "col": col,
            "doc_start_row": meta.get("start_row"),
            "doc_uid": meta.get("doc_uid") or uid_from_name(doc_name),
            "doc_name": doc_name,
        }
    cells[key] = entry
    data["cells"] = cells
    version = int(meta.get("version") or 1) + 1
    uid = meta.get("doc_uid") or uid_from_name(doc_name)
    b2_key = meta.get("b2_snapshot_key")
    snapshot = {
        "id": str(meta.get("id")),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": uid,
        "kind": kind,
        "data": data,
        "version": version,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    if b2_enabled():
        try:
            b2_key = b2_put_json(_b2_key(parent_type, parent_id, uid), snapshot)
        except Exception as e:
            print(f"[docs] b2 put failed: {e}")

    db = _db()
    try:
        from sqlalchemy import text
        db.execute(
            text(
                """
                UPDATE gsp_documents SET
                    cells_json = CAST(:cells AS JSONB),
                    b2_snapshot_key = :b2_key,
                    version = :ver,
                    updated_at = NOW()
                WHERE parent_type = :pt AND parent_id = :pid AND doc_name = :n
                """
            ),
            {
                "cells": json.dumps(data),
                "b2_key": b2_key,
                "ver": version,
                "pt": parent_type,
                "pid": parent_id,
                "n": doc_name,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return {"ok": True, "key": key, "entry": entry, "doc_uid": uid, "version": version, "b2_snapshot_key": b2_key}


def persist_grid_snapshot(grid_obj: Any, kind: str = "memory_grid") -> Optional[str]:
    """Push training/memory grid snapshot to B2. Returns key or None."""
    if not b2_enabled():
        print("[b2] grid snapshot skipped — B2 not configured")
        return None
    payload = grid_obj
    if hasattr(grid_obj, "documents"):
        docs = getattr(grid_obj, "documents", {}) or {}
        # avoid mutating live grid; serialize light
        try:
            serial_docs = {}
            for k, v in list(docs.items())[:50000]:
                if isinstance(v, dict):
                    serial_docs[str(k)] = v
                else:
                    serial_docs[str(k)] = {"text": str(v)[:20000]}
            payload = {
                "kind": kind,
                "doc_count": len(docs),
                "documents": serial_docs,
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            payload = {"kind": kind, "error": str(e), "doc_count": len(docs)}
    key = _grid_b2_key(kind)
    return b2_put_json(key, payload)


def persist_vocab_snapshot(vocab: dict, name: str = "tokenizer_vocab") -> Optional[str]:
    if not b2_enabled():
        return None
    return b2_put_json(f"training/{name}/latest.json", vocab)
