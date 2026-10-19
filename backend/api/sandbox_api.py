"""
Sandbox API – multi-context code execution
Contexts: user | org | ai
Uses the existing SandboxRunner. No changes to runner.py.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict

from sandbox.runner import SandboxRunner

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class RunRequest(BaseModel):
    source: str = Field(..., min_length=1)
    filename: str = Field("main.py", max_length=255)
    lang: str = Field("python", max_length=32)
    context: str = Field("user", pattern="^(user|org|ai)$")
    extra_files: Optional[Dict[str, str]] = None
    timeout_s: int = Field(15, ge=1, le=60)
    memory_mb: int = Field(256, ge=64, le=1024)


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
    """
    Execute code in an isolated sandbox.
    Each context (user / org / ai) keeps its own console identity.
    """
    runner = SandboxRunner(
        timeout_s=req.timeout_s,
        memory_mb=req.memory_mb,
    )
    result = runner.run_code(
        source=req.source,
        filename=req.filename,
        lang=req.lang,
        extra_files=req.extra_files or {},
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
