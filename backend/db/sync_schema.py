"""
Schema sync on startup
======================
create_all() only creates tables. It does NOT add columns to existing
tables. This module inspects the DB against the ORM models and runs
ALTER TABLE ADD COLUMN IF NOT EXISTS for any missing columns.

Safe and idempotent: run on every startup, no-op when the schema is
already current.
"""
from __future__ import annotations
import re
from typing import Iterable, List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

try:
    from db.neon import Base
except Exception:
    try:
        from neon import Base
    except Exception:
        Base = None


# ============================================================================
# TYPE MAPPING: sqlalchemy type -> postgres DDL fragment
# ============================================================================

def _pg_type(col) -> str:
    """Return a Postgres DDL type fragment for a SQLAlchemy Column."""
    try:
        t = col.type
        type_name = type(t).__name__.upper()
    except Exception:
        return "TEXT"

    # varchar(n) / char(n)
    if hasattr(t, "length") and t.length and "VARCHAR" in type_name:
        return f"VARCHAR({t.length})"
    if hasattr(t, "length") and t.length and "CHAR" in type_name:
        return f"CHAR({t.length})"

    mapping = {
        "INTEGER": "INTEGER",
        "BIGINTEGER": "BIGINT",
        "SMALLINTEGER": "SMALLINT",
        "STRING": "VARCHAR(255)",
        "TEXT": "TEXT",
        "BOOLEAN": "BOOLEAN",
        "FLOAT": "DOUBLE PRECISION",
        "NUMERIC": "NUMERIC",
        "DATETIME": "TIMESTAMP WITHOUT TIME ZONE",
        "TIMESTAMP": "TIMESTAMP WITHOUT TIME ZONE",
        "DATE": "DATE",
        "TIME": "TIME",
        "JSON": "JSONB",
        "JSONB": "JSONB",
        "UUID": "UUID",
        "ARRAY": "JSONB",
        "BYTEA": "BYTEA",
    }
    return mapping.get(type_name, "TEXT")


# ============================================================================
# SYNC
# ============================================================================

def sync_schema(engine: Engine) -> List[str]:
    """
    Ensure every ORM column exists in the DB. Returns list of added columns
    in the form "table.column".
    """
    if Base is None:
        print("[schema-sync] ORM Base not importable — skipped")
        return []

    added: List[str] = []
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        tname = table.name
        if tname not in db_tables:
            # create_all handles new tables on its own; skip
            continue

        existing = {c["name"] for c in inspector.get_columns(tname)}
        for col in table.columns:
            if col.name in existing:
                continue

            pg = _pg_type(col)
            nullable = "" if col.nullable else " NOT NULL"
            default = ""
            try:
                if col.default is not None and getattr(col.default, "arg", None) is not None:
                    arg = col.default.arg
                    if callable(arg):
                        pass  # skip callable defaults (e.g. uuid.uuid4)
                    elif isinstance(arg, str):
                        default = f" DEFAULT '{arg}'"
                    elif isinstance(arg, bool):
                        default = f" DEFAULT {'TRUE' if arg else 'FALSE'}"
                    elif isinstance(arg, (int, float)):
                        default = f" DEFAULT {arg}"
            except Exception:
                pass

            # NOT NULL with no default and non-empty table would fail;
            # downgrade to NULL-able to be safe
            if not col.nullable and not default:
                nullable = ""

            stmt = (
                f'ALTER TABLE "{tname}" '
                f'ADD COLUMN IF NOT EXISTS "{col.name}" {pg}{nullable}{default}'
            )

            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
                added.append(f"{tname}.{col.name}")
                print(f"[schema-sync] added {tname}.{col.name} {pg}")
            except Exception as e:
                print(f"[schema-sync] FAILED {tname}.{col.name}: "
                      f"{type(e).__name__}: {e}")

    if not added:
        print("[schema-sync] schema is current")
    return added


# ============================================================================
# UNIQUE CONSTRAINTS
# ============================================================================

# (table, [columns], constraint_name)
_REQUIRED_UNIQUES = [
    ("users", ["phone"], "uq_users_phone"),
    ("organization_memberships", ["user_id", "organization_id"],
     "uq_user_organization_membership"),
    ("organizations", ["slug"], "uq_organizations_slug"),
    ("organizations", ["ai_uid"], "uq_organizations_ai_uid"),
    ("ai_brains", ["ai_uid"], "uq_ai_brains_ai_uid"),
]


def ensure_unique_constraints(engine) -> List[str]:
    """
    Ensure required unique constraints exist on the target tables.

    Idempotent. Refuses to add a constraint if the table already contains
    duplicate values in that column set — logs the offending rows instead
    so you can clean them up first.
    """
    added: List[str] = []
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    for table, cols, cname in _REQUIRED_UNIQUES:
        if table not in db_tables:
            continue

        # 1) already present?
        try:
            existing_constraints = inspector.get_unique_constraints(table)
        except Exception:
            existing_constraints = []
        if any(c.get("name") == cname for c in existing_constraints):
            continue
        # also check by column set (some DBs return unnamed constraints)
        cols_set = set(cols)
        if any(set(c.get("column_names") or []) == cols_set
               for c in existing_constraints):
            continue

        # 2) any duplicates?
        col_list = ", ".join(f'"{c}"' for c in cols)
        try:
            with engine.begin() as conn:
                rows = conn.execute(text(
                    f'SELECT {col_list}, COUNT(*) AS n FROM "{table}" '
                    f'GROUP BY {col_list} HAVING COUNT(*) > 1 LIMIT 5'
                )).fetchall()
        except Exception as e:
            print(f"[unique] {table}.{cols} check failed: "
                  f"{type(e).__name__}: {e}")
            continue

        if rows:
            print(f"[unique] {table}({cols}) has duplicate rows, "
                  f"constraint not added:")
            for r in rows:
                print(f"          {dict(r._mapping)}")
            continue

        # 3) add the constraint
        stmt = (
            f'ALTER TABLE "{table}" '
            f'ADD CONSTRAINT "{cname}" UNIQUE ({col_list})'
        )
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            added.append(cname)
            print(f"[unique] added {cname} on {table}({cols})")
        except Exception as e:
            print(f"[unique] FAILED {cname}: {type(e).__name__}: {e}")

    return added
