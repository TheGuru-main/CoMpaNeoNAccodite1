"""
Sandbox API — run + repo/fs + GSP start_row roots

Repo root (ONLY start_row — no K/D strides or jumps):
  start_row = ((L + S - 1) % 64) + 1
  L = len(repo_name)
  S = digit-sum of system-assigned secret repo_uid

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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sandbox.runner import SandboxRunner
from gsp_chain import (
    letter_chain, uid_from_name, start_row_for_name, verify_uid_matches_name,
    validate_cell, R_ROWS as GSP_R_ROWS, N_COLS as GSP_N_COLS,
)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

ROOT = Path(os.environ.get("ACCD_SANDBOX_ROOT", "/tmp/accd-sandbox")).resolve()
SAFE_NAME = re.compile(r"^[a-zA-Z0-9._\-]+$")
R_ROWS = 64


def _scope_root(scope: str) -> Path:
    scope = (scope or "user").strip().lower()
    if scope not in ("user", "org", "ai"):
        scope = "user"
    p = ROOT / scope
    p.mkdir(parents=True, exist_ok=True)
    return p


def _repo_dir(scope: str, repo: str) -> Path:
    if not repo or not SAFE_NAME.match(repo):
        raise HTTPException(400, "invalid repo name (use letters, numbers, . _ -)")
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


def compute_start_row(repo_name: str, repo_uid: str = "") -> dict:
    """start_row from training tokenizer letter-chain of the name."""
    info = start_row_for_name(repo_name or "")
    expected = uid_from_name(repo_name or "")
    if repo_uid and not verify_uid_matches_name(repo_name or "", repo_uid):
        raise HTTPException(400, "repo_uid does not match tokenizer letter-chain of repo name")
    return {
        "L": info["L"],
        "S": info["S"],
        "start_row": info["start_row"],
        "root_key": info["root_key"],
        "repo": repo_name,
        "repo_uid": expected,
        "chain": info["chain"],
        "grid_rows": R_ROWS,
        "grid_cols": GSP_N_COLS,
    }


def _repo_uid_from_name(name: str) -> str:
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
    files = {
        "backend/main.py": f'# {name}\nprint("Hello from {name}")\n',
        "backend/__init__.py": "",
        "frontend/index.html": (
            f"<!DOCTYPE html>\n<html><head><title>{name}</title></head>"
            f"<body><h1>{name}</h1></body></html>\n"
        ),
        "frontend/js/app.js": f"// {name}\nconsole.log('ok');\n",
        "frontend/css/style.css": "body { margin: 0; }\n",
        "public/index.html": f"<!DOCTYPE html>\n<html><body><h1>{name}</h1></body></html>\n",
        "public/js/main.js": "console.log('public');\n",
        "public/css/main.css": "body { margin: 0; }\n",
        "README.md": f"# {name}\n\nGSP start_row rooted Codespace repo.\n",
    }
    for rel, body in files.items():
        p = rdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(body, encoding="utf-8")


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
        })
    return {"repos": out}


@router.post("/repos")
async def create_repo(req: RepoCreate):
    if not SAFE_NAME.match(req.name):
        raise HTTPException(400, "invalid repo name")
    d = _repo_dir(req.scope, req.name)
    if d.exists():
        raise HTTPException(409, "repo already exists")
    d.mkdir(parents=True, exist_ok=True)

    repo_uid = _repo_uid_from_name(req.name)
    gsp = compute_start_row(req.name, repo_uid)
    meta = {
        **gsp,
        "repo_uid": repo_uid,
        "created_at": time.time(),
        "scope": req.scope,
    }
    _write_meta(d, meta)
    _scaffold_conventional(d, req.name)

    return {
        "ok": True,
        "name": req.name,
        "scope": req.scope,
        "start_row": gsp["start_row"],
        "root_key": gsp["root_key"],
        "repo_uid": repo_uid,
        "note": "repo_uid is tokenizer letter-chain of name (same as training). Required with name for push/commit.",
        "chain": letter_chain(req.name),
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
        entries.append({
            "name": child.name,
            "path": str(child.relative_to(rdir)).replace("\\", "/"),
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else 0,
        })
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
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content or "", encoding="utf-8")
    return {"ok": True, "path": rel, "size": target.stat().st_size}


@router.post("/fs/mkdir")
async def fs_mkdir(req: FsMkdir):
    rdir = _repo_dir(req.scope, req.repo)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    rel = _safe_rel(req.path)
    if not rel:
        raise HTTPException(400, "path required")
    (rdir / rel).mkdir(parents=True, exist_ok=True)
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
class DocCreate(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    parent_repo: str
    doc_name: str
    kind: str = Field("sheet", pattern="^(sheet|xlsx|workspace)$")
    n_rows: int = Field(100, ge=1, le=5000)
    n_cols: int = Field(26, ge=1, le=512)

class DocCellWrite(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    parent_repo: str
    doc_name: str
    doc_uid: str = ""
    row: int
    col: int
    value: str = ""
    place: bool = False

def _docs_dir(scope: str, repo: str) -> Path:
    return _repo_dir(scope, repo) / "docs"

def _doc_dir(scope: str, repo: str, doc_name: str) -> Path:
    if not doc_name or not SAFE_NAME.match(doc_name):
        raise HTTPException(400, "invalid doc name")
    return _docs_dir(scope, repo) / doc_name

def _doc_data_path(ddir: Path) -> Path:
    return ddir / "data.json"

@router.post("/docs")
async def create_doc(req: DocCreate):
    rdir = _repo_dir(req.scope, req.parent_repo)
    if not rdir.exists():
        raise HTTPException(404, "parent repo not found")
    ddir = _doc_dir(req.scope, req.parent_repo, req.doc_name)
    if ddir.exists():
        raise HTTPException(409, "doc already exists")
    ddir.mkdir(parents=True, exist_ok=True)
    info = start_row_for_name(req.doc_name)
    uid = uid_from_name(req.doc_name)
    meta = {
        "kind": req.kind,
        "doc_name": req.doc_name,
        "doc_uid": uid,
        "chain": info["chain"],
        "L": info["L"],
        "S": info["S"],
        "start_row": info["start_row"],
        "root_key": info["root_key"],
        "parent_repo": req.parent_repo,
        "scope": req.scope,
        "created_at": time.time(),
        "grid": {"rows": "1..64", "cols": "0..53"} if req.kind in ("sheet", "workspace") else {
            "n_rows": req.n_rows, "n_cols": req.n_cols, "configurable": True
        },
    }
    _write_meta(ddir, meta)
    if req.kind in ("sheet", "workspace"):
        data = {"cells": {}, "row_min": 1, "row_max": 64, "col_min": 0, "col_max": 53}
    else:
        data = {"cells": {}, "n_rows": req.n_rows, "n_cols": req.n_cols, "configurable": True}
    _doc_data_path(ddir).write_text(json.dumps(data), encoding="utf-8")
    return {"ok": True, **meta}

@router.get("/docs")
async def list_docs(parent_repo: str, scope: str = "user"):
    root = _docs_dir(scope, parent_repo)
    if not root.exists():
        return {"docs": [], "parent_repo": parent_repo}
    out = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        meta = _read_meta(d) or {}
        name = meta.get("doc_name") or d.name
        out.append({
            "doc_name": name,
            "doc_uid": meta.get("doc_uid") or uid_from_name(name),
            "kind": meta.get("kind") or "sheet",
            "start_row": meta.get("start_row"),
            "chain": meta.get("chain") or letter_chain(name),
            "parent_repo": parent_repo,
        })
    return {"docs": out, "parent_repo": parent_repo}

@router.get("/docs/{doc_name}")
async def get_doc(doc_name: str, parent_repo: str, scope: str = "user"):
    ddir = _doc_dir(scope, parent_repo, doc_name)
    if not ddir.exists():
        raise HTTPException(404, "doc not found")
    meta = _read_meta(ddir) or {}
    data = {}
    dp = _doc_data_path(ddir)
    if dp.is_file():
        try:
            data = json.loads(dp.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    return {"meta": meta, "data": data}

@router.post("/docs/cell")
async def write_doc_cell(req: DocCellWrite):
    ddir = _doc_dir(req.scope, req.parent_repo, req.doc_name)
    if not ddir.exists():
        raise HTTPException(404, "doc not found")
    meta = _read_meta(ddir) or {}
    expected = uid_from_name(req.doc_name)
    if req.doc_uid and not verify_uid_matches_name(req.doc_name, req.doc_uid):
        raise HTTPException(403, "doc_uid does not match tokenizer letter-chain of doc_name")
    kind = meta.get("kind") or "sheet"
    try:
        if kind in ("sheet", "workspace"):
            row, col = validate_cell(req.row, req.col)
        else:
            row, col = int(req.row), int(req.col)
    except ValueError as e:
        raise HTTPException(400, str(e))
    dp = _doc_data_path(ddir)
    data = json.loads(dp.read_text(encoding="utf-8")) if dp.is_file() else {"cells": {}}
    cells = data.setdefault("cells", {})
    key = f"{row}:{col}"
    entry = {"value": req.value, "row": row, "col": col}
    if req.place or kind == "workspace":
        entry["placed"] = True
        entry["placement"] = {
            "row": row, "col": col,
            "doc_start_row": meta.get("start_row"),
            "doc_uid": expected, "doc_name": req.doc_name,
        }
    cells[key] = entry
    dp.write_text(json.dumps(data), encoding="utf-8")
    return {"ok": True, "key": key, "entry": entry, "doc_uid": expected}

@router.get("/gsp/chain")
async def gsp_chain_preview(name: str, lang: str = "en"):
    return start_row_for_name(name, lang=lang or "en")
