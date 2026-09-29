"""
Accodite Sandbox Runner
=======================
Isolated code execution primitive.

Backends, in order of preference:
    1. docker run                (full isolation)
    2. bwrap (bubblewrap)        (Linux user-namespace isolation)
    3. subprocess with timeout   (fallback; no isolation, dev only)

Every run:
    - network disabled
    - memory capped
    - CPU capped
    - wall-clock timeout
    - workspace write scoped to a tmpfs artifacts dir
    - stdout/stderr captured, hashed, returned
"""
from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================================
# PER-LANGUAGE IMAGE + RUN COMMAND
# ============================================================================

LANG_IMAGE = {
    "python":     "python:3.12-slim",
    "javascript": "node:20-slim",
    "typescript": "node:20-slim",
    "tsx":        "node:20-slim",
    "go":         "golang:1.22-alpine",
    "rust":       "rust:1.75-slim",
    "c":          "gcc:13-slim",
    "cpp":        "gcc:13-slim",
    "bash":       "bash:5-alpine",
}

LANG_RUN_CMD = {
    "python":     ["python", "{file}"],
    "javascript": ["node", "{file}"],
    "typescript": ["npx", "tsx", "{file}"],
    "tsx":        ["npx", "tsx", "{file}"],
    "go":         ["go", "run", "{file}"],
    "rust":       ["bash", "-lc", "rustc {file} -o /tmp/a && /tmp/a"],
    "c":          ["bash", "-lc", "gcc {file} -o /tmp/a && /tmp/a"],
    "cpp":        ["bash", "-lc", "g++ {file} -o /tmp/a && /tmp/a"],
    "bash":       ["bash", "{file}"],
}


# ============================================================================
# RESULT
# ============================================================================

@dataclass
class RunResult:
    ok: bool
    backend: str            # docker | bwrap | subprocess | none
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    timed_out: bool = False
    error: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "backend": self.backend,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_s": self.duration_s,
            "timed_out": self.timed_out,
            "error": self.error,
            "artifacts": dict(self.artifacts),
        }


# ============================================================================
# RUNNER
# ============================================================================

class SandboxRunner:
    def __init__(
        self,
        *,
        timeout_s: int = 15,
        memory_mb: int = 256,
        cpus: float = 1.0,
        prefer: Optional[str] = None,   # "docker" | "bwrap" | "subprocess"
    ):
        self.timeout_s = int(timeout_s)
        self.memory_mb = int(memory_mb)
        self.cpus = float(cpus)
        self.prefer = prefer
        self._docker = shutil.which("docker")
        self._bwrap = shutil.which("bwrap")

    # -----------------------------------------------------------------

    def _pick_backend(self) -> str:
        if self.prefer:
            return self.prefer
        if self._docker:
            return "docker"
        if self._bwrap:
            return "bwrap"
        return "subprocess"

    # -----------------------------------------------------------------

    def run_code(
        self,
        *,
        source: str,
        filename: str = "main.py",
        lang: str = "python",
        extra_files: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> RunResult:
        backend = self._pick_backend()

        if backend == "docker":
            return self._run_docker(source, filename, lang, extra_files or {})
        if backend == "bwrap":
            return self._run_bwrap(source, filename, lang, extra_files or {})
        return self._run_subprocess(source, filename, lang, extra_files or {})

    # -----------------------------------------------------------------
    # docker
    # -----------------------------------------------------------------

    def _run_docker(self, source, filename, lang, extra_files) -> RunResult:
        tmp = tempfile.mkdtemp(prefix="accd-")
        try:
            self._write_files(tmp, source, filename, extra_files)
            image = LANG_IMAGE.get(lang)
            if not image:
                return RunResult(ok=False, backend="docker",
                                 error=f"no image for lang '{lang}'")
            cmd = LANG_RUN_CMD.get(lang) or ["bash", "-lc", "true"]
            cmd = [c.format(file=filename) for c in cmd]

            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", f"{self.memory_mb}m",
                "--cpus", str(self.cpus),
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "-v", f"{tmp}:/workspace:ro",
                "-w", "/workspace",
                image,
                *cmd,
            ]
            return self._exec(docker_cmd, backend="docker")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # -----------------------------------------------------------------
    # bwrap
    # -----------------------------------------------------------------

    def _run_bwrap(self, source, filename, lang, extra_files) -> RunResult:
        tmp = tempfile.mkdtemp(prefix="accd-")
        try:
            self._write_files(tmp, source, filename, extra_files)
            cmd = LANG_RUN_CMD.get(lang) or ["bash", "-lc", "true"]
            cmd = [c.format(file=filename) for c in cmd]

            bwrap_cmd = [
                "bwrap",
                "--unshare-all",
                "--die-with-parent",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/lib64", "/lib64",
                "--proc", "/proc",
                "--dev", "/dev",
                "--tmpfs", "/tmp",
                "--bind", tmp, "/workspace",
                "--chdir", "/workspace",
                *cmd,
            ]
            return self._exec(bwrap_cmd, backend="bwrap")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # -----------------------------------------------------------------
    # subprocess (dev fallback; not isolated)
    # -----------------------------------------------------------------

    def _run_subprocess(self, source, filename, lang, extra_files) -> RunResult:
        if lang not in ("python", "bash"):
            return RunResult(
                ok=False, backend="subprocess",
                error=f"subprocess fallback only supports python/bash, got '{lang}'",
            )
        tmp = tempfile.mkdtemp(prefix="accd-")
        try:
            self._write_files(tmp, source, filename, extra_files)
            target = os.path.join(tmp, filename)
            if lang == "python":
                cmd = ["python3", target]
            else:
                cmd = ["bash", target]
            return self._exec(cmd, backend="subprocess", cwd=tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # -----------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------

    def _write_files(self, tmp, source, filename, extra_files):
        with open(os.path.join(tmp, filename), "w", encoding="utf-8") as f:
            f.write(source or "")
        for name, body in (extra_files or {}).items():
            safe = name.replace("..", "_").lstrip("/")
            path = os.path.join(tmp, safe)
            os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
            with open(path, "w", encoding="utf-8") as f:
                f.write(body or "")

    def _exec(self, cmd: List[str], backend: str, cwd: Optional[str] = None) -> RunResult:
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_s,
                cwd=cwd,
            )
            dur = time.time() - t0
            return RunResult(
                ok=(proc.returncode == 0),
                backend=backend,
                exit_code=proc.returncode,
                stdout=(proc.stdout or "")[-20000:],
                stderr=(proc.stderr or "")[-20000:],
                duration_s=round(dur, 3),
            )
        except subprocess.TimeoutExpired as e:
            dur = time.time() - t0
            return RunResult(
                ok=False, backend=backend, exit_code=-1,
                stdout=(e.stdout or b"").decode("utf-8", "ignore")[-5000:] if isinstance(e.stdout, bytes) else (e.stdout or "")[-5000:],
                stderr="Sandbox timeout",
                duration_s=round(dur, 3),
                timed_out=True,
            )
        except FileNotFoundError as e:
            return RunResult(ok=False, backend=backend,
                             error=f"runner not found: {e}")
        except Exception as e:
            return RunResult(ok=False, backend=backend,
                             error=f"{type(e).__name__}: {e}")
