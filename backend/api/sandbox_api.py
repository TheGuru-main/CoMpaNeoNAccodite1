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


def _uid_digit_sum(uid: str) -> int:
    digits = [int(ch) for ch in (uid or "") if ch.isdigit()]
    if digits:
        return sum(digits)
    return sum((ord(ch) % 10) for ch in (uid or "0") if ch.isalnum()) or 0


def compute_start_row(repo_name: str, repo_uid: str) -> dict:
    L = max(len(repo_name or ""), 1)
    S = _uid_digit_sum(repo_uid)
    start_row = ((L + S - 1) % R_ROWS) + 1
    return {
        "L": L,
        "S": S,
        "start_row": start_row,
        "root_key": f"r{start_row:02d}",
        "repo": repo_name,
        "grid_rows": R_ROWS,
    }


def _new_repo_uid() -> str:
    return secrets.token_hex(16)


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
    stored = str(meta.get("repo_uid") or "")
    if not repo_uid or not secrets.compare_digest(stored, str(repo_uid)):
        raise HTTPException(403, "invalid repo key (name + uid pair required)")
    if meta.get("repo") and meta.get("repo") != repo:
        raise HTTPException(403, "repo name mismatch")
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

    runner = SandboxRunner(timeout_s=req.timeout_s, memory_mb=req.memory_mb)
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
        out.append({
            "name": d.name,
            "scope": scope,
            "files": nfiles,
            "updated_at": d.stat().st_mtime,
            "start_row": meta.get("start_row"),
            "root_key": meta.get("root_key"),
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

    repo_uid = _new_repo_uid()
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
        "note": "Save repo_uid secret. Required with repo name for push/commit.",
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
