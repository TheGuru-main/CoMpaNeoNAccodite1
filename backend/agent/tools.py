"""Accodite Tools — audited action surface."""
import hashlib, json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class ToolSpec:
    name: str
    category: str
    description: str
    fn: Callable[..., Any]
    mutating: bool = False
    requires_role: Optional[str] = None
    domains: List[str] = field(default_factory=list)

@dataclass
class ToolCall:
    name: str
    args: dict
    actor_id: str
    organization_id: Optional[str]
    workspace_id: Optional[str]

@dataclass
class ToolResult:
    ok: bool
    value: Any = None
    error: Optional[str] = None
    hash: str = ""

class ToolRegistry:
    def __init__(self, tracer=None, verifier=None, role_lookup=None):
        self._tools: Dict[str, ToolSpec] = {}
        self._tracer = tracer
        self._verifier = verifier
        self._role_lookup = role_lookup

    def register(self, spec):
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def tool(self, *, name, category, description,
             mutating=False, requires_role=None, domains=None):
        def wrap(fn):
            self.register(ToolSpec(name, category, description, fn,
                                   mutating, requires_role, domains or []))
            return fn
        return wrap

    def dispatch(self, call):
        # ACCD-PROGRESS-DISPATCH
        import time as _t
        spec = self._tools.get(call.name)
        if spec is None:
            return ToolResult(ok=False, error=f"unknown tool: {call.name}")
        t0 = _t.time()
        if getattr(self, "_on_event", None):
            try: self._on_event("begin", call.name, True, 0.0)
            except Exception: pass
        self._trace(call, phase="call")
        try:
            value = spec.fn(**call.args)
            h = hashlib.sha256(
                json.dumps(value, default=str).encode()
            ).hexdigest()[:16]
            result = ToolResult(ok=True, value=value, hash=h)
        except Exception as e:
            result = ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
        self._trace(call, phase="result", result=result)
        if getattr(self, "_on_event", None):
            try: self._on_event("end", call.name, result.ok, (_t.time() - t0) * 1000)
            except Exception: pass
        return result

    def _trace(self, call, phase, result=None):
        if self._tracer is None:
            return
        payload = {"phase": phase, "tool": call.name, "actor": call.actor_id}
        if result is not None:
            payload["ok"] = result.ok
            payload["hash"] = result.hash
        try:
            self._tracer.log_execution_step("Tools", "dispatch", payload)
        except Exception:
            pass
