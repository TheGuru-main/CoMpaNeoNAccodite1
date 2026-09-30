"""
Accodite Progress Channel
=========================
Emits #status# frames during long-running AI operations so the user
sees thinking / tool / verify / retry / wait states as they happen.

Frame grammar:
    #status#{"kind":"thinking","msg":"...","at":<epoch>}
    #status#{"kind":"tool_call","msg":"fs.read_file","args":{...},...}
    #status#{"kind":"tool_result","msg":"fs.read_file","ok":true,...}
    #status#{"kind":"verifying","msg":"syntax"}
    #status#{"kind":"verify_result","msg":"syntax","ok":false,"findings":1}
    #status#{"kind":"retry","msg":"2/3","reason":"syntax error"}
    #status#{"kind":"waiting","msg":"external_fetch"}
    #status#{"kind":"generating","msg":"..."}
    #status#{"kind":"error","msg":"..."}
    #status#{"kind":"done","msg":"verified","ms":1234}
"""
from __future__ import annotations
import json
import time
from typing import Any, Dict, List, Optional


class ProgressChannel:
    def __init__(self, *, throttle_ms: int = 0):
        self._frames: List[str] = []
        self._throttle_ms = int(throttle_ms or 0)
        self._last_emit = 0.0

    def _emit(self, kind: str, msg: str = "", **extra) -> str:
        now = time.time()
        if self._throttle_ms and (now - self._last_emit) * 1000 < self._throttle_ms:
            return ""
        self._last_emit = now
        payload: Dict[str, Any] = {"kind": kind, "msg": msg, "at": now}
        if extra:
            payload.update(extra)
        frame = f"#status#{json.dumps(payload, separators=(',', ':'))}"
        self._frames.append(frame)
        return frame

    # --- semantic helpers ---

    def thinking(self, msg: str = "Thinking…") -> str:
        return self._emit("thinking", msg)

    def planning(self, msg: str = "Planning…") -> str:
        return self._emit("planning", msg)

    def tool_call(self, name: str, args: Optional[dict] = None) -> str:
        return self._emit("tool_call", name, args=args or {})

    def tool_result(self, name: str, ok: bool, ms: Optional[float] = None) -> str:
        return self._emit("tool_result", name, ok=bool(ok), ms=ms)

    def verifying(self, stage: str) -> str:
        return self._emit("verifying", stage)

    def verify_result(self, stage: str, ok: bool, findings: int = 0) -> str:
        return self._emit("verify_result", stage, ok=bool(ok), findings=findings)

    def retry(self, attempt: int, max_attempts: int, reason: str = "") -> str:
        return self._emit("retry", f"{attempt}/{max_attempts}", reason=reason)

    def waiting(self, reason: str = "network") -> str:
        return self._emit("waiting", reason)

    def generating(self, msg: str = "Generating…") -> str:
        return self._emit("generating", msg)

    def done(self, msg: str = "Done", ms: Optional[float] = None) -> str:
        return self._emit("done", msg, ms=ms)

    def error(self, msg: str) -> str:
        return self._emit("error", msg)

    # --- history ---

    def frames(self) -> List[str]:
        return list(self._frames)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "count": len(self._frames),
            "last": self._frames[-1] if self._frames else None,
        }


def status_frame(kind: str, msg: str = "", **extra) -> str:
    """One-shot helper that doesn't require an instance."""
    payload: Dict[str, Any] = {"kind": kind, "msg": msg, "at": time.time()}
    if extra:
        payload.update(extra)
    return f"#status#{json.dumps(payload, separators=(',', ':'))}"
