"""
Sandbox API — run + repo/fs + GSP start_row roots

Repo root (ONLY start_row — no K/D strides or jumps):
  start_row = ((L + S - 1) % 64) + 1
  L = len(repo_name)
  S = digit-sum of content-place uid of repo name (full chain)

repo_uid is generated on create (secret to user/team).
commit / push require repo name + repo_uid.

Runner: sandbox.runner (untouched).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

try:
    from auth import get_current_user
except Exception:
    try:
        from auth.auth import get_current_user
    except Exception:
        get_current_user = None  # type: ignore

try:
    from db_models import User
except Exception:
    try:
        from database import User
    except Exception:
        User = None  # type: ignore


from sandbox.runner import SandboxRunner
try:
    from access_control import require_parent_access, AccessDenied
except Exception:
    require_parent_access = None
    class AccessDenied(Exception):
        pass

from gsp_chain import (
    validate_resource_name,
    letter_chain, uid_from_name, start_row_for_name, verify_uid_matches_name, place_fragments,
    validate_cell, R_ROWS as GSP_R_ROWS, N_COLS as GSP_N_COLS,
)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

def place_coords_for_name(name: str, lang: str = "en") -> dict:
    """
    Canonical GSP cell — ONLY via gsp_chain.content_place_from_name (M4.1).
    start_col from place dict; never chain[0]%54.
    """
    name = validate_resource_name(name or "", what="object name")
    info = start_row_for_name(name, lang=lang)
    start_col = int(info.get("start_col") if info.get("start_col") is not None else info.get("c") or 0)
    return {
        **info,
        "start_col": start_col,
        "c": start_col,
        "target_cell": info.get("target_cell") or f"r{info['start_row']}:c{start_col}",
        "object_name": name,
    }



def _optional_user(request: Request = None):
    """Resolve user from Bearer token without failing module import."""
    if request is None:
        return None
    try:
        from auth.auth import decode_access_token
        from database import SessionLocal
        auth = (request.headers.get("Authorization") or "") if request else ""
        if not auth.lower().startswith("bearer "):
            return None
        payload = decode_access_token(auth.split(" ", 1)[1])
        uid = payload.get("sub") or payload.get("user_id")
        if not uid:
            return None
        db = SessionLocal()
        try:
            from db_models import User as _User
            return db.query(_User).filter(_User.id == uid).first()
        finally:
            db.close()
    except Exception:
        return None


# Prefer persistent path; /tmp is last resort (Render ephemeral)
ROOT = Path(
    os.environ.get("ACCD_SANDBOX_ROOT")
    or os.environ.get("ACCD_DATA_DIR")
    or (Path(__file__).resolve().parents[1] / "data" / "accd-sandbox")
).resolve()
ROOT.mkdir(parents=True, exist_ok=True)

SAFE_NAME = re.compile(r"^[a-zA-Z0-9._\-]+$")
R_ROWS = 64


def _scope_root(scope: str) -> Path:
    scope = (scope or "user").strip().lower()
    if scope not in ("user", "org", "ai"):
        scope = "user"
    p = ROOT / scope
    p.mkdir(parents=True, exist_ok=True)
    return p



def _manifest_path(scope: str) -> Path:
    return _scope_root(scope) / ".accd_repos_manifest.json"


def _load_manifest(scope: str) -> list:
    p = _manifest_path(scope)
    if not p.is_file():
        return []
    try:
        import json as _json
        data = _json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_manifest(scope: str, entries: list) -> None:
    import json as _json
    p = _manifest_path(scope)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_json.dumps(entries, indent=2), encoding="utf-8")


def _manifest_upsert(scope: str, name: str, meta: dict) -> None:
    entries = [e for e in _load_manifest(scope) if e.get("name") != name]
    entries.append({
        "name": name,
        "scope": scope,
        "repo_uid": meta.get("repo_uid"),
        "start_row": meta.get("start_row"),
        "root_key": meta.get("root_key"),
        "chain": meta.get("chain"),
        "updated_at": meta.get("created_at") or meta.get("updated_at") or time.time(),
    })
    entries.sort(key=lambda e: e.get("name") or "")
    _save_manifest(scope, entries)


def _manifest_remove(scope: str, name: str) -> None:
    entries = [e for e in _load_manifest(scope) if e.get("name") != name]
    _save_manifest(scope, entries)

def _repo_dir(scope: str, repo: str) -> Path:
    try:
        repo = validate_resource_name(repo, what="repo name")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _scope_root(scope) / repo


def _safe_rel(path: str) -> str:
    path = (path or "").replace("\\", "/").lstrip("/")
    parts = []
    for part in path.split("/"):
        if not part or part == ".":
            continue
        if part == ".." or part.startswith(".."):
            raise HTTPException(400, "path traversal blocked")
        parts.append(part)
    return "/".join(parts)



def path_place_for_rel(repo_name: str, rel: str, *, repo_uid: str = "") -> dict:
    """M5.1: place one path inside a repo from relative path string."""
    rel = (rel or "").replace(chr(92), "/").lstrip("/")
    if not rel:
        raise HTTPException(400, "path required for path place")
    try:
        from gsp_chain import content_place_from_name
        info = content_place_from_name(rel) or {}
    except Exception as e:
        raise HTTPException(400, f"path GSP place failed: {e}") from e
    uid = str(info.get("uid") or "")
    if not uid or not info.get("start_row"):
        raise HTTPException(400, "path place empty uid/start_row")
    return {
        "path": rel,
        "repo": repo_name,
        "repo_uid": repo_uid or "",
        "compound_key": f"{repo_uid or repo_name}::{rel}",
        "path_uid": uid,
        "L": info.get("L"),
        "S": info.get("S"),
        "c": info.get("c") if info.get("c") is not None else info.get("start_col"),
        "start_col": info.get("start_col") if info.get("start_col") is not None else info.get("c"),
        "start_row": info["start_row"],
        "root_key": info.get("root_key") or f"r{int(info['start_row'])}",
        "chain": info.get("chain") or [],
        "digit_markers": info.get("digit_markers") or [],
        "symbol_uids": info.get("symbol_uids") or [],
        "source": "path_content_place",
    }


def _paths_index_update(rdir: Path, rel: str, place: dict) -> None:
    idx_path = rdir / ".gsp_paths.json"
    idx = {}
    if idx_path.is_file():
        try:
            idx = json.loads(idx_path.read_text(encoding="utf-8")) or {}
        except Exception:
            idx = {}
    if not isinstance(idx, dict):
        idx = {}
    paths = idx.get("paths") if isinstance(idx.get("paths"), dict) else {}
    paths[rel] = {
        "path_uid": place.get("path_uid"),
        "start_row": place.get("start_row"),
        "start_col": place.get("start_col"),
        "c": place.get("c"),
        "L": place.get("L"),
        "S": place.get("S"),
        "compound_key": place.get("compound_key"),
    }
    idx["paths"] = paths
    idx["updated_at"] = time.time()
    try:
        idx_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    except Exception as e:
        print("[sandbox] paths index:", e)


def compute_start_row(repo_name: str, repo_uid: str = "") -> dict:
    """M5.0: L,S,c then start_row via content_place_from_name (full chain)."""
    try:
        from gsp_chain import content_place_from_name
        info = content_place_from_name(repo_name or "") or {}
    except Exception as e:
        raise HTTPException(400, f"GSP place failed: {e}") from e
    expected = str(info.get("uid") or info.get("uid_str") or "")
    if not expected or not info.get("start_row"):
        raise HTTPException(400, "GSP place produced empty uid/start_row")
    if repo_uid and str(repo_uid) != expected and not verify_uid_matches_name(repo_name or "", str(repo_uid)):
        # allow underscore form vs compact if both verify
        try:
            if str(repo_uid).replace("_", "") != expected.replace("_", ""):
                raise HTTPException(400, "repo_uid does not match content place uid of repo name")
        except HTTPException:
            raise
    return {
        "L": info.get("L"),
        "S": info.get("S"),
        "c": info.get("c") if info.get("c") is not None else info.get("start_col"),
        "start_col": info.get("start_col") if info.get("start_col") is not None else info.get("c"),
        "start_row": info["start_row"],
        "root_key": info.get("root_key") or f"r{int(info['start_row'])}",
        "repo": repo_name,
        "repo_uid": expected,
        "chain": info.get("chain") or [],
        "digit_markers": info.get("digit_markers") or [],
        "symbol_uids": info.get("symbol_uids") or [],
        "grid_rows": info.get("grid_rows") or R_ROWS,
        "grid_cols": info.get("C") or info.get("grid_cols") or GSP_N_COLS,
        "source": info.get("source") or "content_place",
    }


def _repo_uid_from_name(name: str) -> str:
    """Full content-place uid (underscore chain), not letter-only collapse."""
    try:
        from gsp_chain import content_place_from_name
        info = content_place_from_name(name or "") or {}
        u = str(info.get("uid") or "")
        if u:
            return u
    except Exception:
        pass
    return uid_from_name(name)


def _write_meta(rdir: Path, meta: dict) -> None:
    (rdir / ".gsp.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _read_meta(rdir: Path) -> Optional[dict]:
    f = rdir / ".gsp.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def _verify_repo_key(rdir: Path, repo: str, repo_uid: str) -> dict:
    meta = _read_meta(rdir)
    if not meta:
        raise HTTPException(403, "repo has no GSP key metadata")
    if meta.get("repo") and meta.get("repo") != repo:
        raise HTTPException(403, "repo name mismatch")
    expected = uid_from_name(repo)
    stored = str(meta.get("repo_uid") or expected)
    if not repo_uid or not verify_uid_matches_name(repo, str(repo_uid)):
        raise HTTPException(403, "invalid repo key (uid must be tokenizer letter-chain of name)")
    if stored and not verify_uid_matches_name(repo, stored):
        meta["repo_uid"] = expected
        meta["chain"] = letter_chain(repo)
        _write_meta(rdir, meta)
    return meta


def _scaffold_conventional(rdir: Path, name: str) -> None:
    """
    One GSP-placed repo = one project root.
    Fixed top-level roots (no duplicate names). Existing paths are never overwritten.
    """
    roots = (
        "backend",
        "frontend",
        "frontend/js",
        "frontend/css",
        "public",
        "public/js",
        "public/css",
        "xml",
        "tests",
        "scripts",
        "docs",
    )
    repo_meta0 = _read_meta(rdir) or {}
    repo_uid0 = str(repo_meta0.get("repo_uid") or "")
    for rel in roots:
        d = rdir / rel
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
        elif d.is_file():
            raise HTTPException(409, f"path conflict: {rel} is a file, expected directory root")
        try:
            place = path_place_for_rel(name, rel, repo_uid=repo_uid0)
            _paths_index_update(rdir, rel, place)
        except Exception as e:
            print("[scaffold] root place", rel, type(e).__name__, e)

    files = {
        "backend/__init__.py": "",
        "backend/main.py": f'# {name} — backend entry\nprint("Hello from {name}")\n',
        "frontend/index.html": (
            f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'><title>{name}</title>"
            f"<link rel='stylesheet' href='css/style.css'></head>"
            f"<body><h1>{name}</h1><script src='js/app.js'></script></body></html>\n"
        ),
        "frontend/js/app.js": f"// {name} frontend\nconsole.log({name!r});\n",
        "frontend/css/style.css": "body { margin: 0; font-family: system-ui, sans-serif; }\n",
        "public/index.html": f"<!DOCTYPE html>\n<html><body><h1>{name} public</h1></body></html>\n",
        "public/js/main.js": "console.log('public');\n",
        "public/css/main.css": "body { margin: 0; }\n",
        "xml/manifest.xml": f'<?xml version="1.0"?><project name="{name}"/>\n',
        "tests/test_smoke.py": f'def test_smoke():\n    assert True  # {name}\n',
        "scripts/run.sh": f"#!/usr/bin/env bash\ncd \"$(dirname \"$0\")/..\"\npython3 backend/main.py\n",
        "README.md": (
            f"# {name}\n\nGSP-placed Codespace repo. Roots: backend/, frontend/, public/, xml/, tests/, scripts/.\n"
            f"Do not create a second folder with the same root name inside this repo.\n"
        ),
    }
    repo_meta = _read_meta(rdir) or {}
    repo_uid = str(repo_meta.get("repo_uid") or "")
    for rel, body in files.items():
        p = rdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            continue  # never overwrite
        p.write_text(body, encoding="utf-8")
        try:
            place = path_place_for_rel(name, rel, repo_uid=repo_uid)
            _paths_index_update(rdir, rel, place)
        except Exception as e:
            print("[scaffold] path place", rel, type(e).__name__, e)



class RunRequest(BaseModel):
    source: str = Field(..., min_length=1)
    filename: str = Field("main.py", max_length=255)
    lang: str = Field("python", max_length=32)
    context: str = Field("user", pattern="^(user|org|ai)$")
    extra_files: Optional[Dict[str, str]] = None
    timeout_s: int = Field(15, ge=1, le=60)
    memory_mb: int = Field(256, ge=64, le=1024)
    repo: Optional[str] = Field(None, max_length=64)
    network: bool = False


class RunResponse(BaseModel):
    ok: bool
    backend: str
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool
    error: Optional[str] = None
    context: str
    artifacts: Dict[str, str] = {}


@router.post("/run", response_model=RunResponse)
async def run_code(req: RunRequest):
    extra = dict(req.extra_files or {})
    if req.repo:
        try:
            rdir = _repo_dir(req.context, req.repo)
            if rdir.is_dir():
                for f in rdir.rglob("*"):
                    if f.is_file() and f.name not in (".gsp.json", ".accd_push_log", ".accd_commit_log"):
                        rel = str(f.relative_to(rdir)).replace("\\", "/")
                        if rel == req.filename:
                            continue
                        try:
                            extra[rel] = f.read_text(encoding="utf-8", errors="replace")
                        except Exception:
                            pass
        except HTTPException:
            raise
        except Exception:
            pass

    runner = SandboxRunner(timeout_s=req.timeout_s, memory_mb=req.memory_mb, network=bool(getattr(req, 'network', False)))
    result = runner.run_code(
        source=req.source,
        filename=req.filename,
        lang=req.lang,
        extra_files=extra,
    )
    return RunResponse(
        ok=result.ok,
        backend=result.backend,
        exit_code=result.exit_code,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        duration_s=result.duration_s,
        timed_out=result.timed_out,
        error=result.error,
        context=req.context,
        artifacts=result.artifacts or {},
    )


class GspResolveReq(BaseModel):
    repo_name: str = Field(..., min_length=1, max_length=64)
    repo_uid: str = Field(..., min_length=8, max_length=128)


@router.post("/gsp/resolve")
async def gsp_resolve(req: GspResolveReq):
    return compute_start_row(req.repo_name, req.repo_uid)



@router.get("/repos/{name}/rootcheck")
async def repo_rootcheck(name: str, scope: str = "user", cwd: str = ""):
    """Deep repo integrity for acd rootcheck."""
    try:
        name = validate_resource_name(name, what="repo name")
    except ValueError as e:
        raise HTTPException(400, str(e))
    rdir = _repo_dir(scope, name)
    issues = []
    ok = True
    if not rdir.exists():
        return {
            "ok": False,
            "repo": name,
            "scope": scope,
            "on_disk": False,
            "issues": ["repo directory missing — create or restore volume"],
            "root": str(rdir),
        }
    meta = _read_meta(rdir) or {}
    expected_uid = uid_from_name(name)
    info = start_row_for_name(name)
    if not (rdir / ".gsp.json").is_file():
        issues.append("missing .gsp.json")
        ok = False
    meta_uid = str(meta.get("repo_uid") or "")
    if meta_uid and meta_uid != expected_uid:
        issues.append("repo_uid mismatch vs tokenizer chain")
        ok = False
    if meta.get("start_row") is not None and int(meta.get("start_row")) != int(info.get("start_row") or 0):
        issues.append("start_row drift vs name formula")
        ok = False
    cwd_rel = (cwd or "").replace("\\", "/").lstrip("/")
    cwd_ok = True
    if cwd_rel:
        target = (rdir / cwd_rel).resolve()
        try:
            target.relative_to(rdir.resolve())
        except ValueError:
            cwd_ok = False
            ok = False
            issues.append("cwd escapes repo root")
        if cwd_ok and not target.exists():
            issues.append("cwd path does not exist")
            ok = False
    nfiles = sum(1 for f in rdir.rglob("*") if f.is_file())
    return {
        "ok": ok and not issues,
        "repo": name,
        "scope": scope,
        "on_disk": True,
        "root": str(rdir),
        "repo_uid": meta_uid or expected_uid,
        "expected_uid": expected_uid,
        "start_row": meta.get("start_row") or info.get("start_row"),
        "expected_start_row": info.get("start_row"),
        "chain": meta.get("chain") or info.get("chain"),
        "files": nfiles,
        "cwd": cwd_rel or "/",
        "cwd_ok": cwd_ok,
        "issues": issues,
        "manifest_listed": any(e.get("name") == name for e in _load_manifest(scope)),
    }

@router.get("/repos/{name}/gsp")
async def repo_gsp(name: str, scope: str = "user", reveal_uid: bool = False):
    rdir = _repo_dir(scope, name)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    meta = _read_meta(rdir)
    if not meta:
        raise HTTPException(404, "no GSP metadata")
    out = {
        "repo": meta.get("repo", name),
        "start_row": meta.get("start_row"),
        "root_key": meta.get("root_key"),
        "L": meta.get("L"),
        "S": meta.get("S"),
        "grid_rows": meta.get("grid_rows", R_ROWS),
    }
    if reveal_uid:
        out["repo_uid"] = meta.get("repo_uid")
    return out


class RepoCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    scope: str = Field("user", pattern="^(user|org|ai)$")


@router.get("/health")
async def sandbox_health():
    """Console heartbeat + persist diagnostics."""
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        probe = ROOT / ".accd_health"
        probe.write_text(str(time.time()), encoding="utf-8")
        writable = True
    except Exception as e:
        writable = False
        probe_err = str(e)
    else:
        probe_err = None
    return {
        "ok": True,
        "root": str(ROOT),
        "writable": writable,
        "probe_error": probe_err,
        "ts": time.time(),
        "ephemeral_hint": str(ROOT).startswith("/tmp"),
    }


@router.get("/repos")
async def list_repos(scope: str = "user"):
    root = _scope_root(scope)
    out: List[dict] = []
    for d in sorted(root.iterdir() if root.exists() else []):
        if not d.is_dir():
            continue
        nfiles = sum(
            1 for f in d.rglob("*")
            if f.is_file() and f.name not in (".gsp.json", ".accd_push_log", ".accd_commit_log")
        )
        meta = _read_meta(d) or {}
        uid = meta.get("repo_uid") or uid_from_name(d.name)
        out.append({
            "name": d.name,
            "scope": scope,
            "files": nfiles,
            "updated_at": d.stat().st_mtime,
            "start_row": meta.get("start_row") or start_row_for_name(d.name)["start_row"],
            "root_key": meta.get("root_key") or start_row_for_name(d.name)["root_key"],
            "repo_uid": uid,
            "chain": meta.get("chain") or letter_chain(d.name),
            "on_disk": True,
        })
    # Manifest entries not currently on disk (e.g. after volume miss)
    seen = {r["name"] for r in out}
    for e in _load_manifest(scope):
        n = e.get("name")
        if not n or n in seen:
            continue
        out.append({
            "name": n,
            "scope": scope,
            "files": 0,
            "updated_at": e.get("updated_at"),
            "start_row": e.get("start_row"),
            "root_key": e.get("root_key"),
            "repo_uid": e.get("repo_uid"),
            "chain": e.get("chain"),
            "on_disk": False,
            "note": "listed in manifest only — restore volume or re-clone",
        })
    return {"repos": out, "root": str(_scope_root(scope))}


@router.post("/repos")
async def create_repo(req: RepoCreate):
    """Create GSP-rooted repo. Idempotent: existing name returns current meta (ok=true, existed=true)."""
    try:
        req.name = validate_resource_name(req.name, what="repo name")
    except ValueError as e:
        raise HTTPException(400, str(e))

    d = _repo_dir(req.scope, req.name)
    existed = d.exists()
    if not existed:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(500, f"cannot create repo dir: {type(e).__name__}: {e}") from e

    # M5.0: GSP identity required — no invented S=0 placement
    try:
        repo_uid = _repo_uid_from_name(req.name)
        gsp = compute_start_row(req.name, repo_uid)
        repo_uid = str(gsp.get("repo_uid") or repo_uid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"repo GSP place failed: {type(e).__name__}: {e}") from e

    meta = {
        **gsp,
        "repo_uid": repo_uid,
        "created_at": time.time() if not existed else ( (_read_meta(d) or {}).get("created_at") or time.time() ),
        "scope": req.scope,
        "repo": req.name,
    }
    # Prefer existing meta if present
    old = _read_meta(d) if existed else None
    if old and old.get("repo_uid"):
        meta = {**meta, **old, "scope": req.scope, "repo": req.name}
        repo_uid = meta.get("repo_uid") or repo_uid

    try:
        _write_meta(d, meta)
    except Exception as e:
        raise HTTPException(500, f"cannot write .gsp.json: {e}") from e

    # M5.0: record repo in owner MemoryGrid namespace "codespace"
    try:
        from memory.grid_ns_api import place_ns_object
        scope = str(getattr(req, "scope", None) or "user")
        # phones optional on RepoCreate — best-effort from request state if present
        req_obj = req
        user_phone = str(getattr(req_obj, "user_phone", None) or "")
        org_phone = str(getattr(req_obj, "org_phone", None) or "")
        if user_phone or org_phone or scope in ("user", "org", "ai"):
            place_ns_object(
                ns="codespace",
                object_name=req.name,
                description="repo",
                text=req.name,
                user_phone=user_phone if scope != "org" else "",
                org_phone=org_phone if scope == "org" else "",
                extra={
                    "kind": "repo",
                    "repo_uid": repo_uid,
                    "start_row": meta.get("start_row"),
                    "start_col": meta.get("start_col") or meta.get("c"),
                    "path": str(d),
                    "scope": scope,
                },
            )
    except Exception as _pe:
        print("[sandbox] repo grid place:", type(_pe).__name__, _pe)

    try:
        _scaffold_conventional(d, req.name)
    except HTTPException:
        raise
    except Exception as e:
        print("[sandbox] scaffold:", type(e).__name__, e)

    try:
        _manifest_upsert(req.scope, req.name, meta)
    except Exception as e:
        print("[sandbox] manifest upsert:", e)

    chain = meta.get("chain") or []
    try:
        if not chain:
            chain = letter_chain(req.name)
    except Exception:
        chain = []

    return {
        "ok": True,
        "existed": existed,
        "name": req.name,
        "scope": req.scope,
        "start_row": meta.get("start_row") or gsp.get("start_row"),
        "root_key": meta.get("root_key") or gsp.get("root_key"),
        "repo_uid": repo_uid,
        "note": "repo_uid is tokenizer letter-chain of name. Required with name for push/commit.",
        "chain": chain,
    }


@router.delete("/repos/{name}")
async def delete_repo(name: str, scope: str = "user", repo_uid: str = ""):
    d = _repo_dir(scope, name)
    if not d.exists():
        raise HTTPException(404, "repo not found")
    _verify_repo_key(d, name, repo_uid)
    shutil.rmtree(d)
    return {"ok": True}


class FsWrite(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    repo: str = Field(..., min_length=1, max_length=64)
    path: str = Field(..., min_length=1, max_length=512)
    content: str = ""
    create_only: bool = False


class FsMkdir(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    repo: str = Field(..., min_length=1, max_length=64)
    path: str = Field(..., min_length=1, max_length=512)


@router.get("/fs/list")
async def fs_list(repo: str, scope: str = "user", path: str = ""):
    rdir = _repo_dir(scope, repo)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    rel = _safe_rel(path)
    target = rdir if not rel else (rdir / rel)
    if not target.exists():
        raise HTTPException(404, "path not found")
    if target.is_file():
        return {"type": "file", "path": rel, "size": target.stat().st_size}
    entries = []
    for child in sorted(target.iterdir()):
        if child.name.startswith(".gsp") or child.name.startswith(".accd"):
            continue
        rel_p = str(child.relative_to(rdir)).replace(chr(92), "/")
        ent = {
            "name": child.name,
            "path": rel_p,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else 0,
        }
        try:
            idx_path = rdir / ".gsp_paths.json"
            if idx_path.is_file():
                idx = json.loads(idx_path.read_text(encoding="utf-8")) or {}
                pl = (idx.get("paths") or {}).get(rel_p)
                if pl:
                    ent["start_row"] = pl.get("start_row")
                    ent["start_col"] = pl.get("start_col")
                    ent["path_uid"] = pl.get("path_uid")
        except Exception:
            pass
        entries.append(ent)
    return {"type": "dir", "path": rel or "", "entries": entries}


@router.get("/fs/read")
async def fs_read(repo: str, path: str, scope: str = "user"):
    rdir = _repo_dir(scope, repo)
    rel = _safe_rel(path)
    if not rel:
        raise HTTPException(400, "path required")
    target = rdir / rel
    if not target.is_file():
        raise HTTPException(404, "file not found")
    if target.stat().st_size > 2_000_000:
        raise HTTPException(413, "file too large")
    return {
        "path": rel,
        "content": target.read_text(encoding="utf-8", errors="replace"),
    }


@router.post("/fs/write")
async def fs_write(req: FsWrite):
    rdir = _repo_dir(req.scope, req.repo)
    if not rdir.exists():
        raise HTTPException(404, "repo not found — create repo first")
    rel = _safe_rel(req.path)
    if not rel:
        raise HTTPException(400, "path required")
    target = rdir / rel
    create_only = bool(getattr(req, "create_only", False))
    if create_only and target.exists():
        raise HTTPException(409, f"path already exists: {rel}")
    if target.exists() and target.is_dir():
        raise HTTPException(409, f"path is a directory: {rel}")
    # refuse name collision with existing dir of same path component under repo root
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.exists() and target.parent.is_file():
        raise HTTPException(409, "parent path is a file")
    target.write_text(req.content or "", encoding="utf-8")
    place = None
    try:
        meta = _read_meta(rdir) or {}
        place = path_place_for_rel(req.repo, rel, repo_uid=str(meta.get("repo_uid") or ""))
        _paths_index_update(rdir, rel, place)
    except Exception as e:
        print("[fs/write] path place:", type(e).__name__, e)
    out = {"ok": True, "path": rel, "size": target.stat().st_size}
    if place:
        out["place"] = place
    return out


@router.post("/fs/mkdir")
async def fs_mkdir(req: FsMkdir):
    rdir = _repo_dir(req.scope, req.repo)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    rel = _safe_rel(req.path)
    if not rel:
        raise HTTPException(400, "path required")
    # Disallow shadowing reserved top-level roots with a file-named twin
    target = rdir / rel
    if target.exists():
        raise HTTPException(409, f"path already exists: {rel}")
    # If parent path is a file, fail
    parent = target.parent
    if parent != rdir and parent.exists() and parent.is_file():
        raise HTTPException(409, f"parent is a file: {parent.relative_to(rdir)}")
    target.mkdir(parents=True, exist_ok=False)
    return {"ok": True, "path": rel}


class PushRequest(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    repo: str
    repo_uid: str = Field(..., min_length=8)
    message: str = "push from codespace"


class CommitRequest(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    repo: str
    repo_uid: str = Field(..., min_length=8)
    message: str = "commit from codespace"


@router.post("/repos/{name}/push")
async def push_repo(name: str, req: PushRequest):
    if req.repo != name:
        raise HTTPException(400, "repo name mismatch")
    rdir = _repo_dir(req.scope, name)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    meta = _verify_repo_key(rdir, name, req.repo_uid)
    log = rdir / ".accd_push_log"
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{time.time():.0f} start_row={meta.get('start_row')} {req.message.strip() or 'push'}\n")
    nfiles = sum(
        1 for f in rdir.rglob("*")
        if f.is_file() and f.name not in (".accd_push_log", ".gsp.json", ".accd_commit_log")
    )
    return {
        "ok": True,
        "repo": name,
        "files": nfiles,
        "message": req.message,
        "start_row": meta.get("start_row"),
        "root_key": meta.get("root_key"),
        "note": "push accepted (name + uid verified)",
    }


@router.post("/repos/{name}/commit")
async def commit_repo(name: str, req: CommitRequest):
    if req.repo != name:
        raise HTTPException(400, "repo name mismatch")
    rdir = _repo_dir(req.scope, name)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    meta = _verify_repo_key(rdir, name, req.repo_uid)
    log = rdir / ".accd_commit_log"
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{time.time():.0f} start_row={meta.get('start_row')} {req.message.strip() or 'commit'}\n")
    return {
        "ok": True,
        "repo": name,
        "message": req.message,
        "start_row": meta.get("start_row"),
        "root_key": meta.get("root_key"),
        "note": "commit accepted (name + uid verified)",
    }

class FsDelete(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    repo: str = Field(..., min_length=1, max_length=64)
    path: str = Field(..., min_length=1, max_length=512)

@router.post("/fs/delete")
async def fs_delete(req: FsDelete):
    rdir = _repo_dir(req.scope, req.repo)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    rel = _safe_rel(req.path)
    if not rel:
        raise HTTPException(400, "path required")
    target = rdir / rel
    if not target.exists():
        raise HTTPException(404, "path not found")
    if target.name in (".gsp.json", ".accd_push_log", ".accd_commit_log"):
        raise HTTPException(403, "protected path")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "path": rel}

_BLOCKED = __import__("re").compile(
    r"(rm\s+-rf\s+/|mkfs|dd\s+if=|shutdown|reboot|passwd\b)",
    __import__("re").I,
)

class ExecRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4000)
    scope: str = Field("user", pattern="^(user|org|ai)$")
    repo: Optional[str] = Field(None, max_length=64)
    network: bool = True
    timeout_s: int = Field(120, ge=5, le=300)
    memory_mb: int = Field(512, ge=128, le=2048)

@router.post("/exec")
async def sandbox_exec(req: ExecRequest):
    cmd = (req.command or "").strip()
    if not cmd:
        raise HTTPException(400, "empty command")
    if _BLOCKED.search(cmd):
        raise HTTPException(400, "command blocked")
    # ACCD-T2-WORKDIR: always persist — never temp+rmtree for net exec
    if req.repo:
        rdir = _repo_dir(req.scope, req.repo)
        if not rdir.exists():
            raise HTTPException(404, "repo not found — create repo first")
        workdir = str(rdir.resolve())
    else:
        # scope root (user/org/ai), not a disposable temp
        workdir = str(_scope_root(req.scope).resolve())
    runner = SandboxRunner(
        timeout_s=req.timeout_s,
        memory_mb=req.memory_mb,
        network=bool(req.network),
    )
    if not hasattr(runner, "run_shell"):
        raise HTTPException(501, "runner missing run_shell — deploy network runner.py")
    result = runner.run_shell(command=cmd, workdir=workdir)
    return {
        "ok": result.ok,
        "backend": result.backend,
        "exit_code": result.exit_code,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "duration_s": result.duration_s,
        "timed_out": result.timed_out,
        "error": result.error,
        "network": getattr(result, "network", False),
        "repo": req.repo,
        "scope": req.scope,
    }


# --- Docs (sheet/xlsx/workspace) — uid from tokenizer letter-chain ---

def _normalize_doc_kind(kind: str) -> str:
    k = (kind or "sheet").strip().lower()
    return {
        "sheets": "sheet",
        "dbase": "xlsx",
        "collabsheet": "workspace",
        "presentations": "pptx",
        "pptx": "pptx",
        "sheet": "sheet",
        "xlsx": "xlsx",
        "workspace": "workspace",
    }.get(k, k)

class DocCreate(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    parent_type: str = Field("repo", pattern="^(repo|room)$")
    parent_repo: str = ""
    parent_id: str = ""
    org_id: str = ""
    doc_name: str
    kind: str = Field("sheet", pattern="^(sheet|sheets|xlsx|dbase|workspace|collabsheet|pptx|presentations)$")
    n_rows: int = Field(100, ge=1, le=5000)
    n_cols: int = Field(54, ge=1, le=512)

class DocCellWrite(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    parent_type: str = Field("repo", pattern="^(repo|room)$")
    parent_repo: str = ""
    parent_id: str = ""
    org_id: str = ""
    doc_name: str
    doc_uid: str = ""
    row: int
    col: int
    value: str = ""
    meta: str = ""
    place: bool = False

def _docs_dir(scope: str, repo: str) -> Path:
    return _repo_dir(scope, repo) / "docs"

def _doc_dir(scope: str, repo: str, doc_name: str) -> Path:
    try:
        doc_name = validate_resource_name(doc_name, what="doc name")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _docs_dir(scope, repo) / doc_name

def _doc_data_path(ddir: Path) -> Path:
    return ddir / "data.json"


def _docs_parent(req_or_repo, parent_type=None, parent_id=None, parent_repo=None):
    pt = (parent_type or getattr(req_or_repo, "parent_type", None) or "repo")
    if hasattr(pt, "strip"):
        pt = str(pt).strip().lower()
    pid = parent_id or getattr(req_or_repo, "parent_id", None) or parent_repo or getattr(req_or_repo, "parent_repo", None) or ""
    return pt, str(pid)


def _enforce_docs_access(user, parent_type, parent_id):
    if require_parent_access is None or user is None:
        return
    try:
        require_parent_access(user, parent_type, parent_id)
    except AccessDenied as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        # fail closed for rooms
        if (parent_type or "").lower() == "room":
            raise HTTPException(403, f"room access check failed: {e}")


def _docs_surface(kind: str) -> str:
    return {
        "sheet": "sheets",
        "xlsx": "dbase",
        "workspace": "collabsheet",
        "pptx": "presentations",
    }.get(_normalize_doc_kind(kind), "sheets")


def _docs_user(request):
    user = getattr(getattr(request, "state", None), "user", None) if request else None
    if user is None and request is not None:
        user = _optional_user(request)
    if user is None:
        raise HTTPException(401, "authentication required")
    return user



def _phones_from_ownership(user, ownership):
    """M4.2: grid bind uses phone UIDs only."""
    from memory.owner_identity import phone_uid
    kind = str(getattr(ownership, "kind", "") or "")
    owner_phone = str(getattr(ownership, "phone_uid", None) or getattr(ownership, "owner_id", None) or "")
    owner_phone = phone_uid(owner_phone) or owner_phone
    # reject UUID-shaped owner_id
    if owner_phone and len(owner_phone) == 36 and owner_phone.count("-") == 4:
        raise HTTPException(403, "ownership_id must be phone UID, not SQL UUID")
    if not owner_phone:
        # last resort: user phone for personal only
        if kind != "org":
            owner_phone = phone_uid(getattr(user, "phone", None)) or ""
    if not owner_phone:
        raise HTTPException(403, "phone UID required for document ownership")
    if kind == "org":
        return "", owner_phone  # user_phone, org_phone
    return owner_phone, ""


def _resolve_docs_owner(request, parent_type, parent_id, kind, org_id=""):
    """M4.2: ownership.kind + ownership.owner_id are always phone-backed parents."""
    user = _docs_user(request)

    try:
        from memory.ownership_scope import resolve_ownership
        from memory.owner_identity import phone_uid

        ownership = resolve_ownership(
            user=user,
            surface=_docs_surface(kind),
            room_id=parent_id if parent_type == "room" else None,
            org_id=org_id or None,
            require=True,
        )
        # Normalize: owner_id / phone_uid must be phone digits, never user UUID
        ph = phone_uid(getattr(ownership, "phone_uid", None) or getattr(ownership, "owner_id", None))
        if not ph and getattr(ownership, "kind", "") != "org":
            ph = phone_uid(getattr(user, "phone", None))
        if not ph:
            raise PermissionError("phone UID unresolved for document owner")
        try:
            object.__setattr__(ownership, "owner_id", ph)
            object.__setattr__(ownership, "phone_uid", ph)
        except Exception:
            ownership.owner_id = ph  # type: ignore
            if hasattr(ownership, "phone_uid"):
                ownership.phone_uid = ph  # type: ignore
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except Exception as exc:
        raise HTTPException(403, f"ownership resolution failed: {exc}")

    _enforce_docs_access(user, parent_type, parent_id)
    return user, ownership


def _assert_docs_owner(meta, ownership):
    if not meta:
        raise HTTPException(404, "doc not found")

    exp_id = str(getattr(ownership, "owner_id", "") or "")
    # M4.2: ownership_id must match phone parent (not UUID)
    if exp_id and len(exp_id) == 36 and exp_id.count("-") == 4:
        raise HTTPException(403, "ownership partition misconfigured (UUID parent)")

    actual = (
        str(meta.get("ownership_kind") or ""),
        str(meta.get("ownership_id") or ""),
        str(meta.get("b2_prefix") or "").strip("/"),
    )

    expected = (
        str(ownership.kind),
        exp_id,
        str(getattr(ownership, "b2_prefix", None) or "").strip("/"),
    )

    if actual != expected:
        raise HTTPException(403, "document ownership partition mismatch")

    if ownership.org_id and str(meta.get("org_id") or "") != str(ownership.org_id):
        raise HTTPException(403, "document organisation ownership mismatch")


def _doc_parent(parent_type, parent_repo="", parent_id=""):
    pt = (parent_type or "repo").strip().lower()
    pid = (parent_id or parent_repo or "").strip()

    if pt not in ("repo", "room") or not pid:
        raise HTTPException(400, "valid parent_type and parent_repo/parent_id required")

    return pt, pid


def _docs_store_error(exc):
    if isinstance(exc, KeyError):
        raise HTTPException(404, "doc not found")
    if isinstance(exc, PermissionError):
        raise HTTPException(403, str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(400, str(exc))
    if isinstance(exc, RuntimeError):
        raise HTTPException(503, str(exc))

    message = str(exc).lower()
    if "unique" in message or "duplicate" in message:
        raise HTTPException(409, "document already exists")

    raise HTTPException(500, "document storage operation failed")


@router.post("/docs")
async def create_doc(req: DocCreate, request: Request = None):
    from docs_store import create_document

    pt, pid = _doc_parent(req.parent_type, req.parent_repo, req.parent_id)
    kind = _normalize_doc_kind(req.kind)

    if pt == "repo" and not _repo_dir(req.scope, pid).exists():
        raise HTTPException(404, "parent repo not found")

    user, ownership = _resolve_docs_owner(
        request, pt, pid, kind, req.org_id
    )

    try:
        doc = create_document(
            parent_type=pt,
            parent_id=pid,
            doc_name=req.doc_name,
            kind=kind,
            scope=req.scope,
            n_rows=req.n_rows,
            n_cols=req.n_cols,
            owner_user_id=getattr(user, "id", None),
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
            b2_prefix=ownership.b2_prefix,
            org_id=ownership.org_id,
        )
    except Exception as exc:
        _docs_store_error(exc)
        raise

    # Canonical MemoryGrid place (same GSP name / owner instance)
    ns = {
        "sheet": "sheets",
        "xlsx": "dbase",
        "workspace": "collabsheet",
        "pptx": "presentations",
    }.get(kind, "dbase")
    try:
        from memory.grid_ns_api import place_ns_object
        user_phone, org_phone = _phones_from_ownership(user, ownership)
        placed = place_ns_object(
            ns=ns,
            object_name=req.doc_name,
            description=getattr(req, "description", None) or "",
            text=getattr(req, "description", None) or req.doc_name,
            user_id=str(getattr(user, "id", "") or ""),
            org_id=str(
                getattr(ownership, "org_id", None)
                or getattr(req, "org_id", None)
                or ""
            ),
            user_phone=user_phone,
            org_phone=org_phone,
            workspace_id=str(pid or ""),
        )
        if isinstance(doc, dict):
            doc["ns"] = ns
            pl = (placed or {}).get("placement") or {}
            if not pl:
                pl = {
                    "start_row": (placed or {}).get("start_row"),
                    "start_col": (placed or {}).get("start_col"),
                    "doc_uid": (placed or {}).get("doc_uid"),
                }
            doc["placement"] = pl
            doc["grid_doc_id"] = (placed or {}).get("doc_id")
            if doc.get("start_col") is None and pl.get("start_col") is not None:
                doc["start_col"] = pl["start_col"]
            if not doc.get("start_row") and pl.get("start_row"):
                doc["start_row"] = pl["start_row"]
            if (placed or {}).get("ok") is False:
                doc["grid_place_error"] = (placed or {}).get("error")
    except Exception as e:
        if isinstance(doc, dict):
            doc["grid_place_error"] = f"{type(e).__name__}: {e}"
    return doc





@router.get("/docs/lookup")
async def docs_lookup(
    name: str,
    kind: str = "xlsx",
    parent_type: str = "repo",
    parent_id: str = "HomeDocs",
    parent_repo: str = "",
    org_id: str = "",
    lang: str = "en",
    request: Request = None,
):
    """M4.3: resolve object by name via content_place identity on owner grid."""
    from memory.grid_namespaces import lookup_by_name, assert_ns
    from memory.grid_request import bind_request_grid
    from gsp_chain import content_place_from_name

    pt, pid = _doc_parent(parent_type, parent_repo or parent_id, parent_id or parent_repo)
    kind_n = _normalize_doc_kind(kind)
    user, ownership = _resolve_docs_owner(request, pt, pid, kind_n, org_id)
    user_phone, org_phone = _phones_from_ownership(user, ownership)

    ns = {
        "sheet": "sheets",
        "xlsx": "dbase",
        "workspace": "collabsheet",
        "pptx": "presentations",
    }.get(kind_n, "dbase")
    try:
        assert_ns(ns)
    except Exception as e:
        raise HTTPException(400, str(e))

    place = {}
    try:
        place = content_place_from_name(name, lang=lang or "en") or {}
    except Exception as e:
        raise HTTPException(400, f"place identity failed: {e}")

    grid = bind_request_grid(
        user_id=str(getattr(user, "id", "") or ""),
        org_id=str(getattr(ownership, "org_id", None) or org_id or ""),
        user_phone=user_phone or None,
        org_phone=org_phone or None,
    )
    hit = None
    if grid is not None:
        try:
            hit = lookup_by_name(grid, ns, name, lang=lang or "en")
        except Exception as e:
            print("[docs.lookup]", type(e).__name__, e)

    # Neon meta list fallback by name under owner
    neon = None
    try:
        from docs_store import list_documents, get_document
        rows = list_documents(
            parent_type=pt,
            parent_id=pid,
            kind=kind_n,
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
        ) or []
        for row in rows:
            if str(row.get("doc_name") or row.get("name") or "").lower() == name.lower():
                neon = row
                break
        if neon is None:
            try:
                neon = get_document(
                    pt, pid, name,
                    ownership_kind=ownership.kind,
                    ownership_id=ownership.owner_id,
                )
            except Exception:
                pass
    except Exception as e:
        print("[docs.lookup neon]", type(e).__name__, e)

    return {
        "ok": bool(hit or neon),
        "name": name,
        "ns": ns,
        "place": {
            "start_row": place.get("start_row"),
            "start_col": place.get("start_col") if place.get("start_col") is not None else place.get("c"),
            "doc_uid": place.get("uid"),
            "S": place.get("S"),
            "L": place.get("L"),
            "c": place.get("c"),
        },
        "grid_hit": hit,
        "neon": neon,
        "owner": {"kind": ownership.kind, "owner_id": ownership.owner_id},
    }


@router.get("/docs")
async def list_docs(
    parent_repo: str = "",
    scope: str = "user",
    parent_type: str = "repo",
    parent_id: str = "",
    org_id: str = "",
    request: Request = None,
):
    from docs_store import list_documents

    pt, pid = _doc_parent(parent_type, parent_repo, parent_id)
    user = _docs_user(request)
    _enforce_docs_access(user, pt, pid)

    try:
        # Resolve caller ownership once (instance partition) — filter at SQL
        _, ownership = _resolve_docs_owner(
            request, pt, pid, "sheet", org_id
        )
        rows = list_documents(
            pt,
            pid,
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
        )
        visible = []

        for row in rows:
            try:
                _assert_docs_owner(row, ownership)

                name = row.get("doc_name") or ""
                updated = row.get("updated_at")

                visible.append({
                    "doc_name": name,
                    "doc_uid": row.get("doc_uid"),
                    "kind": row.get("kind") or "sheet",
                    "start_row": row.get("start_row"),
                    "chain": row.get("chain") or letter_chain(name),
                    "version": row.get("version"),
                    "updated_at": updated.isoformat() if updated else None,
                    "parent_repo": pid,
                })

            except HTTPException as exc:
                if exc.status_code not in (403, 404):
                    raise

        return {
            "docs": visible,
            "parent_repo": pid,
            "parent_type": pt,
            "parent_id": pid,
        }

    except HTTPException:
        raise
    except Exception as exc:
        _docs_store_error(exc)


# Register the static path before /docs/{doc_name}.
@router.get("/docs/get")
async def get_doc_query(
    parent_repo: str = "",
    parent_id: str = "",
    parent_type: str = "repo",
    doc_name: str = "",
    scope: str = "user",
    org_id: str = "",
    request: Request = None,
):
    from docs_store import get_document

    pt, pid = _doc_parent(parent_type, parent_repo, parent_id)

    if not doc_name:
        raise HTTPException(400, "doc_name required")

    try:
        # Parent + account scope first (personal user: vs team/org space)
        _, ownership = _resolve_docs_owner(
            request, pt, pid, "sheet", org_id
        )
        got = get_document(
            pt,
            pid,
            doc_name,
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
        )
        _assert_docs_owner(got["meta"], ownership)
        return got

    except HTTPException:
        raise
    except Exception as exc:
        _docs_store_error(exc)


@router.get("/docs/{doc_name}")
async def get_doc(
    doc_name: str,
    parent_repo: str = "",
    scope: str = "user",
    parent_type: str = "repo",
    parent_id: str = "",
    org_id: str = "",
    request: Request = None,
):
    from docs_store import get_document

    pt, pid = _doc_parent(parent_type, parent_repo, parent_id)

    try:
        _, ownership = _resolve_docs_owner(
            request, pt, pid, "sheet", org_id
        )
        got = get_document(
            pt,
            pid,
            doc_name,
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
        )
        _assert_docs_owner(got["meta"], ownership)
        return got

    except HTTPException:
        raise
    except Exception as exc:
        _docs_store_error(exc)


class DocsImportOfficeBody(BaseModel):
    scope: str = "user"
    parent_type: str = "repo"
    parent_repo: str = ""
    parent_id: str = ""
    org_id: str = ""
    doc_name: str
    description: str = ""
    payload_b64: str = ""
    payload_ref: str = ""
    url: str = ""
    filename: str = ""
    kind: str = "sheets"


@router.post("/docs/import_office")
def docs_import_office(body: DocsImportOfficeBody, request: Request = None):
    raise HTTPException(
        501,
        "Office import is not yet connected to the B2 document pipeline",
    )


@router.post("/docs/snapshot")
async def save_doc_snapshot(req: DocSnapshot, request: Request = None):
    from docs_store import get_document, save_snapshot

    pt, pid = _doc_parent(req.parent_type, req.parent_repo, req.parent_id)

    try:
        user, ownership = _resolve_docs_owner(
            request, pt, pid, "sheet", req.org_id
        )
        current = get_document(
            pt,
            pid,
            req.doc_name,
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
        )
        _assert_docs_owner(current["meta"], ownership)

        if req.doc_uid and req.doc_uid != current["meta"].get("doc_uid"):
            raise HTTPException(403, "doc_uid does not match stored document")

        return save_snapshot(
            parent_type=pt,
            parent_id=pid,
            doc_name=req.doc_name,
            doc_uid=req.doc_uid,
            data=req.data,
            actor_user_id=getattr(user, "id", None),
        )

    except HTTPException:
        raise
    except Exception as exc:
        _docs_store_error(exc)


@router.post("/docs/cell")
async def write_doc_cell(req: DocCellWrite, request: Request = None):
    from docs_store import get_document, write_cell

    pt, pid = _doc_parent(req.parent_type, req.parent_repo, req.parent_id)

    try:
        user, ownership = _resolve_docs_owner(
            request, pt, pid, "sheet", req.org_id
        )
        current = get_document(
            pt,
            pid,
            req.doc_name,
            ownership_kind=ownership.kind,
            ownership_id=ownership.owner_id,
        )
        _assert_docs_owner(current["meta"], ownership)

        if req.doc_uid and req.doc_uid != current["meta"].get("doc_uid"):
            raise HTTPException(403, "doc_uid does not match stored document")

        return write_cell(
            parent_type=pt,
            parent_id=pid,
            doc_name=req.doc_name,
            doc_uid=req.doc_uid,
            row=req.row,
            col=req.col,
            value=req.value,
            meta_value=req.meta,
            place=req.place,
            actor_user_id=getattr(user, "id", None),
        )

    except HTTPException:
        raise
    except Exception as exc:
        _docs_store_error(exc)


@router.get("/gsp/chain")
async def gsp_chain_preview(name: str, lang: str = "en"):
    return start_row_for_name(name, lang=lang or "en")
