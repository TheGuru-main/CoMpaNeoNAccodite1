"""
Sandbox API — run + repo/fs (Phase 2)
Runner isolation stays in sandbox.runner (untouched).
Persistent workspace: ACCD_SANDBOX_ROOT or /tmp/accd-sandbox
"""
from __future__ import annotations

import os
import re
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
    d = _scope_root(scope) / repo
    return d


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


# ---------------------------------------------------------------------------
# Run (Phase 1)
# ---------------------------------------------------------------------------

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
    # If repo set, merge saved files from disk into extra_files
    if req.repo:
        try:
            rdir = _repo_dir(req.context, req.repo)
            if rdir.is_dir():
                for f in rdir.rglob("*"):
                    if f.is_file():
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


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------

class RepoCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    scope: str = Field("user", pattern="^(user|org|ai)$")


class RepoInfo(BaseModel):
    name: str
    scope: str
    files: int
    updated_at: float


@router.get("/repos")
async def list_repos(scope: str = "user"):
    root = _scope_root(scope)
    out: List[dict] = []
    for d in sorted(root.iterdir() if root.exists() else []):
        if not d.is_dir():
            continue
        nfiles = sum(1 for f in d.rglob("*") if f.is_file())
        out.append({
            "name": d.name,
            "scope": scope,
            "files": nfiles,
            "updated_at": d.stat().st_mtime,
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
    (d / "README.md").write_text(f"# {req.name}\n\nAccodite Codespace repo.\n", encoding="utf-8")
    (d / "main.py").write_text(
        f'# {req.name}\nprint("Hello from {req.name}")\n',
        encoding="utf-8",
    )
    return {"ok": True, "name": req.name, "scope": req.scope}


@router.delete("/repos/{name}")
async def delete_repo(name: str, scope: str = "user"):
    d = _repo_dir(scope, name)
    if not d.exists():
        raise HTTPException(404, "repo not found")
    shutil.rmtree(d)
    return {"ok": True}


# ---------------------------------------------------------------------------
# FS
# ---------------------------------------------------------------------------

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
    message: str = "push from codespace"


@router.post("/repos/{name}/push")
async def push_repo(name: str, req: PushRequest):
    """Snapshot marker — persists repo mtime + push log (local durable store)."""
    if req.repo != name:
        raise HTTPException(400, "repo name mismatch")
    rdir = _repo_dir(req.scope, name)
    if not rdir.exists():
        raise HTTPException(404, "repo not found")
    log = rdir / ".accd_push_log"
    line = f"{time.time():.0f} {req.message.strip() or 'push'}\n"
    with log.open("a", encoding="utf-8") as f:
        f.write(line)
    nfiles = sum(1 for f in rdir.rglob("*") if f.is_file() and f.name != ".accd_push_log")
    return {
        "ok": True,
        "repo": name,
        "files": nfiles,
        "message": req.message,
        "note": "snapshot recorded (local sandbox store)",
    }
