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
    """Create explicit Neon metadata and version-reference tables."""
    from sqlalchemy import text
    if engine is None:
        from database import engine as eng
        engine = eng

    statements = [
        """
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
            b2_snapshot_key TEXT NOT NULL,
            cells_json JSONB,
            owner_user_id UUID,
            org_id UUID,
            ownership_kind VARCHAR(32) NOT NULL,
            ownership_id VARCHAR(128) NOT NULL,
            b2_prefix TEXT NOT NULL,
            description TEXT,
            payload_ref TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            CONSTRAINT uq_gsp_documents_parent_name
                UNIQUE(parent_type,parent_id,doc_name)
        )
        """,
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS ownership_kind VARCHAR(32)",
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS ownership_id VARCHAR(128)",
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS b2_prefix TEXT",
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS payload_ref TEXT",
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS b2_snapshot_key TEXT",
        "ALTER TABLE gsp_documents ADD COLUMN IF NOT EXISTS cells_json JSONB",
        "ALTER TABLE gsp_documents ALTER COLUMN cells_json DROP NOT NULL",
        """
        CREATE TABLE IF NOT EXISTS gsp_document_versions (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL,
            parent_type VARCHAR(16) NOT NULL,
            parent_id VARCHAR(128) NOT NULL,
            doc_name VARCHAR(128) NOT NULL,
            doc_uid TEXT NOT NULL,
            version INTEGER NOT NULL,
            b2_snapshot_key TEXT NOT NULL,
            actor_user_id UUID,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            CONSTRAINT uq_gsp_document_versions
                UNIQUE(document_id,version)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_gsp_documents_owner ON gsp_documents(ownership_kind,ownership_id)",
        "CREATE INDEX IF NOT EXISTS ix_gsp_documents_parent ON gsp_documents(parent_type,parent_id)",
        "CREATE INDEX IF NOT EXISTS ix_gsp_documents_uid ON gsp_documents(doc_uid)",
        "CREATE INDEX IF NOT EXISTS ix_gsp_document_versions_parent ON gsp_document_versions(parent_type,parent_id,doc_name)"
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _b2_key(parent_type: str, parent_id: str, doc_uid: str, name: str = "snapshot.json",
            b2_prefix: str = "") -> str:
    safe_uid = (doc_uid or "uid")[:120]
    if b2_prefix:
        pref = b2_prefix.strip("/")
        return f"{pref}/{safe_uid}/{name}"
    safe_parent = "".join(c if c.isalnum() or c in "-_" else "_" for c in parent_id)[:80]
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
    ownership_kind: str = "user_regular",
    ownership_id: str = "",
    b2_prefix: str = "",
    description: str = "",
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
        "sheets": "sheet",
        "dbase": "xlsx",
        "collabsheet": "workspace",
        "presentations": "pptx",
    }.get(kind, kind)

    if kind not in ("sheet", "xlsx", "workspace", "pptx"):
        raise ValueError("invalid kind")

    if not b2_enabled():
        raise RuntimeError("B2 is required but is not configured")
    if not b2_prefix:
        raise ValueError("ownership B2 prefix is required")

    info = start_row_for_name(doc_name)
    start_col = info.get("start_col") if info.get("start_col") is not None else info.get("c")
    uid = uid_from_name(doc_name)

    if kind in ("sheet", "workspace"):
        cells = {
            "cells": {},
            "row_min": 1,
            "row_max": 64,
            "col_min": 0,
            "col_max": 53,
        }
        n_rows, n_cols = 64, 54
    elif kind == "pptx":
        cells = {
            "slides": [{
                "id": "s0",
                "title": doc_name,
                "body": "",
                "gradient": "g00",
                "blocks": [],
            }]
        }
    else:
        cells = {
            "cells": {},
            "sheets": {"Sheet1": {"cells": {}}},
            "active_sheet": "Sheet1",
            "n_rows": n_rows,
            "n_cols": n_cols,
            "configurable": True,
            "gsp": {},
        }

    doc_id = uuid.uuid4()
    snapshot = {
        "id": str(doc_id),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": uid,
        "chain": info["chain"],
        "start_row": info["start_row"],
        "start_col": start_col if "start_col" in dir() else info.get("start_col"),
        "kind": kind,
        "data": cells,
        "version": 1,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    # B2 write must succeed before Neon can register the document.
    relative_key = _b2_key(
        parent_type, parent_id, uid, "snapshot.v1.json", b2_prefix
    )
    stored_key = b2_put_json(relative_key, snapshot)

    db = _db()
    try:
        ensure_gsp_documents_table()
        from sqlalchemy import text

        db.execute(text("""
            INSERT INTO gsp_documents (
                id,parent_type,parent_id,scope,doc_name,doc_uid,chain,
                start_row,kind,n_rows,n_cols,cells_json,b2_snapshot_key,
                owner_user_id,org_id,ownership_kind,ownership_id,b2_prefix,
                description,payload_ref,version,created_at,updated_at
            ) VALUES (
                :id,:pt,:pid,:scope,:name,:uid,CAST(:chain AS JSONB),
                :start_row,:kind,:nr,:nc,NULL,:b2,:owner,:org,:okind,
                :oid,:prefix,:description,:payload_ref,1,NOW(),NOW()
            )
        """), {
            "id": str(doc_id),
            "pt": parent_type,
            "pid": parent_id,
            "scope": scope,
            "name": doc_name,
            "uid": uid,
            "chain": json.dumps(info["chain"]),
            "start_row": info["start_row"],
            "kind": kind,
            "nr": n_rows,
            "nc": n_cols,
            "b2": stored_key,
            "owner": str(owner_user_id) if owner_user_id else None,
            "org": str(org_id) if org_id else None,
            "okind": ownership_kind,
            "oid": str(ownership_id),
            "prefix": b2_prefix,
            "description": description,
            "payload_ref": None,
        })

        db.execute(text("""
            INSERT INTO gsp_document_versions (
                id,document_id,parent_type,parent_id,doc_name,doc_uid,
                version,b2_snapshot_key,actor_user_id
            ) VALUES (
                :id,:doc,:pt,:pid,:name,:uid,1,:b2,:actor
            )
        """), {
            "id": str(uuid.uuid4()),
            "doc": str(doc_id),
            "pt": parent_type,
            "pid": parent_id,
            "name": doc_name,
            "uid": uid,
            "b2": stored_key,
            "actor": str(owner_user_id) if owner_user_id else None,
        })

        db.commit()
    except Exception:
        db.rollback()
        # Keep the B2 object for reconciliation. Never report success.
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
        "b2_snapshot_key": stored_key,
        "ownership_kind": ownership_kind,
        "ownership_id": str(ownership_id),
        "b2_prefix": b2_prefix,
        "grid": cells if kind in ("sheet", "workspace")
        else {"n_rows": n_rows, "n_cols": n_cols},
    }


def list_documents(parent_type: str, parent_id: str) -> List[Dict[str, Any]]:
    db = _db()
    try:
        ensure_gsp_documents_table()
        from sqlalchemy import text
        rows = db.execute(
            text(
                """
                SELECT id, doc_name, doc_uid, kind, start_row, chain,
                       b2_snapshot_key, version, updated_at,
                       owner_user_id, org_id, ownership_kind,
                       ownership_id, b2_prefix
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
    if not b2_enabled():
        raise RuntimeError("B2 is required but is not configured")

    db = _db()
    try:
        ensure_gsp_documents_table()
        from sqlalchemy import text

        row = db.execute(text("""
            SELECT * FROM gsp_documents
            WHERE parent_type=:pt AND parent_id=:pid AND doc_name=:name
            LIMIT 1
        """), {
            "pt": parent_type,
            "pid": parent_id,
            "name": doc_name,
        }).mappings().first()

        if not row:
            raise KeyError("doc not found")
        meta = dict(row)
    finally:
        db.close()

    snapshot_key = meta.get("b2_snapshot_key")
    if not snapshot_key:
        raise RuntimeError("document has no B2 snapshot reference")

    snapshot = b2_get_json(snapshot_key)
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("data"), dict):
        raise RuntimeError("B2 snapshot is missing or malformed")

    expected = {
        "id": str(meta.get("id")),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": meta.get("doc_uid"),
        "version": int(meta.get("version") or 1),
    }

    for field, value in expected.items():
        if str(snapshot.get(field)) != str(value):
            raise RuntimeError(f"B2 snapshot identity/version mismatch: {field}")

    return {"meta": meta, "data": snapshot["data"]}



def write_cell(
    *,
    parent_type: str,
    parent_id: str,
    doc_name: str,
    doc_uid: str = "",
    row: int,
    col: int,
    value: str = "",
    meta_value: str = "",
    place: bool = False,
    actor_user_id=None,
) -> Dict[str, Any]:

    if not b2_enabled():
        raise RuntimeError("B2 is required but is not configured")

    if doc_uid and not verify_uid_matches_name(doc_name, doc_uid):
        raise PermissionError("doc_uid does not match name letter-chain")

    got = get_document(parent_type, parent_id, doc_name)
    meta = got["meta"]
    data = got["data"]
    kind = meta.get("kind") or "sheet"

    if kind in ("sheet", "workspace"):
        row, col = validate_cell(row, col)

    cell_key = f"{row}:{col}"
    entry = {
        "value": value,
        "meta": meta_value or "",
        "row": row,
        "col": col,
    }

    if place or kind == "workspace":
        entry["placed"] = True
        entry["placement"] = {
            "row": row,
            "col": col,
            "doc_start_row": meta.get("start_row"),
            "doc_uid": meta.get("doc_uid") or uid_from_name(doc_name),
            "doc_name": doc_name,
        }

    data.setdefault("cells", {})[cell_key] = entry

    if kind == "xlsx":
        active = data.get("active_sheet") or "Sheet1"
        data.setdefault("sheets", {}).setdefault(active, {"cells": {}})
        data["sheets"][active].setdefault("cells", {})[cell_key] = entry

    old_version = int(meta.get("version") or 1)
    new_version = old_version + 1
    uid = meta.get("doc_uid") or uid_from_name(doc_name)
    prefix = (meta.get("b2_prefix") or "").strip("/")

    if not prefix:
        raise RuntimeError("document is missing its ownership B2 prefix")

    snapshot = {
        "id": str(meta.get("id")),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": uid,
        "chain": meta.get("chain"),
        "start_row": meta.get("start_row"),
        "kind": kind,
        "data": data,
        "version": new_version,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    relative_key = _b2_key(
        parent_type, parent_id, uid, f"snapshot.v{new_version}.json", prefix
    )
    stored_key = b2_put_json(relative_key, snapshot)

    db = _db()
    try:
        from sqlalchemy import text

        result = db.execute(text("""
            UPDATE gsp_documents
            SET b2_snapshot_key=:b2,version=:new_version,updated_at=NOW()
            WHERE id=:id AND version=:old_version
        """), {
            "b2": stored_key,
            "new_version": new_version,
            "id": str(meta.get("id")),
            "old_version": old_version,
        })

        if result.rowcount != 1:
            db.rollback()
            raise RuntimeError(
                "document version conflict; B2 snapshot retained for reconciliation"
            )

        db.execute(text("""
            INSERT INTO gsp_document_versions (
                id,document_id,parent_type,parent_id,doc_name,doc_uid,
                version,b2_snapshot_key,actor_user_id
            ) VALUES (
                :id,:doc,:pt,:pid,:name,:uid,:version,:b2,:actor
            )
        """), {
            "id": str(uuid.uuid4()),
            "doc": str(meta.get("id")),
            "pt": parent_type,
            "pid": parent_id,
            "name": doc_name,
            "uid": uid,
            "version": new_version,
            "b2": stored_key,
            "actor": str(actor_user_id) if actor_user_id else None,
        })

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "ok": True,
        "key": cell_key,
        "entry": entry,
        "doc_uid": uid,
        "version": new_version,
        "b2_snapshot_key": stored_key,
    }



def save_snapshot(
    *,
    parent_type: str,
    parent_id: str,
    doc_name: str,
    doc_uid: str = "",
    data: Dict[str, Any],
    actor_user_id=None,
) -> Dict[str, Any]:
    """Persist a complete document snapshot to B2 and version it in Neon."""

    if not b2_enabled():
        raise RuntimeError("B2 is required but is not configured")

    if not isinstance(data, dict):
        raise ValueError("snapshot data must be an object")

    if doc_uid and not verify_uid_matches_name(doc_name, doc_uid):
        raise PermissionError("doc_uid does not match name letter-chain")

    current = get_document(parent_type, parent_id, doc_name)
    meta = current["meta"]

    stored_uid = meta.get("doc_uid") or uid_from_name(doc_name)
    if doc_uid and doc_uid != stored_uid:
        raise PermissionError("document UID does not match stored document")

    prefix = (meta.get("b2_prefix") or "").strip("/")
    if not prefix:
        raise RuntimeError("document is missing its ownership B2 prefix")

    old_version = int(meta.get("version") or 1)
    new_version = old_version + 1
    updated_at = datetime.utcnow().isoformat() + "Z"

    snapshot = {
        "id": str(meta.get("id")),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "doc_name": doc_name,
        "doc_uid": stored_uid,
        "chain": meta.get("chain"),
        "start_row": meta.get("start_row"),
        "kind": meta.get("kind") or "sheet",
        "data": data,
        "version": new_version,
        "updated_at": updated_at,
    }

    relative_key = _b2_key(
        parent_type,
        parent_id,
        stored_uid,
        f"snapshot.v{new_version}.json",
        prefix,
    )
    stored_key = b2_put_json(relative_key, snapshot)

    db = _db()
    try:
        from sqlalchemy import text

        result = db.execute(text("""
            UPDATE gsp_documents
            SET b2_snapshot_key=:b2,
                version=:new_version,
                updated_at=NOW()
            WHERE id=:id AND version=:old_version
        """), {
            "b2": stored_key,
            "new_version": new_version,
            "id": str(meta.get("id")),
            "old_version": old_version,
        })

        if result.rowcount != 1:
            db.rollback()
            raise RuntimeError(
                "document version conflict; B2 snapshot retained for reconciliation"
            )

        db.execute(text("""
            INSERT INTO gsp_document_versions (
                id,document_id,parent_type,parent_id,doc_name,doc_uid,
                version,b2_snapshot_key,actor_user_id
            ) VALUES (
                :id,:doc,:pt,:pid,:name,:uid,:version,:b2,:actor
            )
        """), {
            "id": str(uuid.uuid4()),
            "doc": str(meta.get("id")),
            "pt": parent_type,
            "pid": parent_id,
            "name": doc_name,
            "uid": stored_uid,
            "version": new_version,
            "b2": stored_key,
            "actor": str(actor_user_id) if actor_user_id else None,
        })

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "ok": True,
        "doc_name": doc_name,
        "doc_uid": stored_uid,
        "version": new_version,
        "b2_snapshot_key": stored_key,
        "updated_at": updated_at,
    }


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
