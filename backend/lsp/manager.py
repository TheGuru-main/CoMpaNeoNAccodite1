"""
Accodite LSP Manager
====================
Spawns and manages language servers over stdio JSON-RPC.

Features:
    - per (workspace_root, lang) server pool
    - Content-Length framed JSON-RPC 2.0
    - didOpen / didChange / diagnostics
    - graceful shutdown, idle reap
    - if the LSP binary is missing, falls back to tree_sitter + compiler_gate
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tree_sitter.languages import lsp_command, lang_for


# ============================================================================
# RESULT
# ============================================================================

@dataclass
class Diagnostic:
    line: int
    col: int
    severity: str        # "error" | "warning" | "info" | "hint"
    message: str
    source: str = "lsp"
    code: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


# ============================================================================
# LOW-LEVEL SERVER WRAPPER
# ============================================================================

class _LSPServer:
    def __init__(self, cmd: List[str], root: str):
        self.cmd = cmd
        self.root = root
        self.proc: Optional[subprocess.Popen] = None
        self._next_id = 1
        self._write_lock = threading.Lock()
        self._read_lock = threading.Lock()
        self._stderr_thread: Optional[threading.Thread] = None
        self.last_used = time.time()
        self.stderr_buf: List[str] = []

    # -----------------------------------------------------------------

    def start(self) -> bool:
        if self.proc and self.proc.poll() is None:
            return True
        if not shutil.which(self.cmd[0]):
            return False
        try:
            self.proc = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.root,
            )
        except Exception:
            return False
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True,
        )
        self._stderr_thread.start()
        self._send(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": f"file://{self.root}",
                "capabilities": {},
            },
            request=True,
        )
        try:
            self._recv()
            self._send("initialized", {}, request=False)
        except Exception:
            pass
        return True

    def _drain_stderr(self):
        try:
            for line in self.proc.stderr:  # type: ignore
                self.stderr_buf.append(line.decode("utf-8", "ignore"))
                if len(self.stderr_buf) > 200:
                    self.stderr_buf = self.stderr_buf[-100:]
        except Exception:
            pass

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self._send("shutdown", {}, request=True)
                self._send("exit", {}, request=False)
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

    # -----------------------------------------------------------------
    # framing
    # -----------------------------------------------------------------

    def _send(self, method: str, params: dict, *, request: bool):
        if not self.proc or not self.proc.stdin:
            return
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        if request:
            payload["id"] = self._next_id
            self._next_id += 1
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        with self._write_lock:
            try:
                self.proc.stdin.write(header + body)
                self.proc.stdin.flush()
            except Exception:
                pass

    def _recv(self, timeout_s: float = 5.0) -> Optional[dict]:
        if not self.proc or not self.proc.stdout:
            return None
        deadline = time.time() + timeout_s
        with self._read_lock:
            try:
                while time.time() < deadline:
                    headers = {}
                    while True:
                        line = self.proc.stdout.readline()
                        if not line:
                            return None
                        if line in (b"\r\n", b"\n"):
                            break
                        k, _, v = line.decode("ascii", "ignore").partition(":")
                        headers[k.strip().lower()] = v.strip()
                    n = int(headers.get("content-length", "0"))
                    if n <= 0:
                        continue
                    body = self.proc.stdout.read(n)
                    return json.loads(body.decode("utf-8", "ignore"))
            except Exception:
                return None
        return None

    # -----------------------------------------------------------------
    # high-level calls
    # -----------------------------------------------------------------

    def did_open(self, uri: str, text: str, lang_id: str):
        self._send("textDocument/didOpen", {
            "textDocument": {
                "uri": uri, "languageId": lang_id,
                "version": 1, "text": text,
            }
        }, request=False)

    def did_change(self, uri: str, text: str, version: int = 2):
        self._send("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": text}],
        }, request=False)

    def collect_diagnostics(self, uri: str, timeout_s: float = 3.0) -> List[Diagnostic]:
        end = time.time() + timeout_s
        out: List[Diagnostic] = []
        while time.time() < end:
            msg = self._recv(timeout_s=end - time.time())
            if msg is None:
                break
            if msg.get("method") == "textDocument/publishDiagnostics":
                params = msg.get("params", {})
                if params.get("uri") != uri:
                    continue
                for d in params.get("diagnostics", []):
                    sev = {1: "error", 2: "warning", 3: "info", 4: "hint"}.get(
                        d.get("severity", 1), "error"
                    )
                    r = d.get("range", {}).get("start", {})
                    out.append(Diagnostic(
                        line=r.get("line", 0) + 1,
                        col=r.get("character", 0),
                        severity=sev,
                        message=d.get("message", ""),
                        source=(d.get("source") or "lsp"),
                        code=str(d.get("code")) if d.get("code") is not None else None,
                    ))
        return out


# ============================================================================
# PUBLIC MANAGER
# ============================================================================

class LSPManager:
    def __init__(self, *, idle_reap_s: int = 300):
        self._servers: Dict[Tuple[str, str], _LSPServer] = {}
        self._lock = threading.Lock()
        self.idle_reap_s = int(idle_reap_s)
        self.last_backend: str = "none"

    # -----------------------------------------------------------------

    def _key(self, root: str, lang: str) -> Tuple[str, str]:
        return (os.path.abspath(root), lang)

    def _server_for(self, root: str, lang: str) -> Optional[_LSPServer]:
        cmd = lsp_command(lang)
        if not cmd:
            return None
        key = self._key(root, lang)
        with self._lock:
            srv = self._servers.get(key)
            if srv and srv.alive():
                srv.last_used = time.time()
                return srv
            srv = _LSPServer(cmd, root)
            if not srv.start():
                return None
            self._servers[key] = srv
            return srv

    # -----------------------------------------------------------------

    def diagnose(
        self,
        *,
        root: str,
        path: str,
        source: str,
    ) -> List[Diagnostic]:
        """
        Returns diagnostics for a single file.
        Falls back to compiler_gate if no LSP is available.
        """
        lang = lang_for(path or "")
        srv = self._server_for(root, lang)

        if srv is None:
            self.last_backend = "fallback-compiler-gate"
            return self._fallback_diagnose(path, source, lang)

        self.last_backend = "lsp"
        uri = f"file://{os.path.abspath(os.path.join(root, path))}"
        try:
            srv.did_open(uri, source, lang)
            srv.did_change(uri, source)
            return srv.collect_diagnostics(uri)
        except Exception as e:
            self.last_backend = "fallback-compiler-gate"
            return self._fallback_diagnose(path, source, lang) + [
                Diagnostic(line=1, col=0, severity="warning",
                           message=f"lsp error: {e}", source="lsp")
            ]

    # -----------------------------------------------------------------

    def _fallback_diagnose(self, path: str, source: str, lang: str) -> List[Diagnostic]:
        from tree_sitter.parser import parse_file
        out: List[Diagnostic] = []
        try:
            res = parse_file(path, source)
            for e in res.errors:
                out.append(Diagnostic(
                    line=e.get("line", 1),
                    col=e.get("col", 0),
                    severity=e.get("severity", "error"),
                    message=e.get("message", "syntax error"),
                    source=e.get("source", "tree-sitter"),
                ))
        except Exception:
            pass
        return out

    # -----------------------------------------------------------------

    def shutdown_all(self):
        with self._lock:
            for srv in self._servers.values():
                srv.stop()
            self._servers.clear()

    def reap_idle(self):
        now = time.time()
        with self._lock:
            dead = [k for k, s in self._servers.items()
                    if not s.alive() or (now - s.last_used) > self.idle_reap_s]
            for k in dead:
                self._servers[k].stop()
                del self._servers[k]
