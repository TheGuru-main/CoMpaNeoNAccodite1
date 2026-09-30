"""
Accodite Tool Loop
==================
Model <-> tools round-trip.

The model emits fenced directives:

    ```tool
    {"name": "fs.read_file", "args": {"path": "backend/main.py"}}
    ```

Every call is dispatched through ToolRegistry. Results are fed back
to the model as a user message wrapped in a ```tool_result fence.
Loop until no tool fences remain or max_rounds is hit.

Emits #status# frames for every call so the frontend shows progress.

Never raises on tool failure — errors flow back to the model so it can
adapt.
"""
from __future__ import annotations
import json
import re
from typing import Any, Callable, Dict, List, Optional

try:
    from agent.tools import ToolCall
except Exception:
    ToolCall = None

try:
    from agent.progress import ProgressChannel, status_frame
except Exception:
    ProgressChannel = None
    def status_frame(kind, msg="", **extra):
        return f"#status#{json.dumps({'kind': kind, 'msg': msg, **extra})}"


# ============================================================================
# FENCE PARSING
# ============================================================================

_TOOL_FENCE_RX = re.compile(r"```tool\s*\n(.*?)\n```", re.DOTALL)
_RESULT_OPEN = "```tool_result"
_RESULT_CLOSE = "```"


def _parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for m in _TOOL_FENCE_RX.finditer(text or ""):
        body = (m.group(1) or "").strip()
        try:
            payload = json.loads(body)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        name = (payload.get("name") or "").strip()
        args = payload.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        if name:
            calls.append({"name": name, "args": args})
    return calls


def _strip_tool_fences(text: str) -> str:
    return _TOOL_FENCE_RX.sub("", text or "").strip()


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

def _tools_prompt(registry) -> str:
    if registry is None:
        return ""
    try:
        names = sorted(registry._tools.keys())
    except Exception:
        names = []
    if not names:
        return ""
    lines = ["TOOLS AVAILABLE (emit one ```tool fence per call):"]
    for n in names:
        spec = registry._tools[n]
        lines.append(f"  {n:24s} {spec.category:10s} {spec.description}")
    lines.append("")
    lines.append('Example:')
    lines.append('```tool')
    lines.append('{"name": "fs.read_file", "args": {"path": "backend/main.py"}}')
    lines.append('```')
    lines.append("")
    lines.append("When you have enough information, stop emitting tool fences "
                 "and produce your final answer.")
    return "\n".join(lines)


# ============================================================================
# LOOP
# ============================================================================

def tool_loop(
    *,
    prompt: str,
    generate_fn: Callable[[str], str],
    registry=None,
    actor_id: str = "",
    organization_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    max_rounds: int = 6,
    system_prompt: Optional[str] = None,
    progress=None,
) -> Dict[str, Any]:
    """
    Returns:
        {
          "frames":  List[str],       # #status# + #tool-result# + final prose
          "final":   str,             # model's final answer (fences stripped)
          "calls":   List[dict],      # {name, ok, value|error, ms}
          "rounds":  int,
        }
    """
    frames: List[str] = []
    calls_log: List[Dict[str, Any]] = []

    tools_block = system_prompt or _tools_prompt(registry)

    convo = prompt
    if tools_block:
        convo = f"{tools_block}\n\nUSER REQUEST:\n{prompt}"

    final_text = ""
    rounds = 0
    for rounds in range(1, int(max_rounds) + 1):
        try:
            out = generate_fn(convo) or ""
        except Exception as e:
            frames.append(f"#error#generate failed: {type(e).__name__}: {e}")
            break

        tool_calls = _parse_tool_calls(out)
        prose_only = _strip_tool_fences(out)

        if not tool_calls:
            final_text = prose_only or out
            break

        # emit any prose that accompanied the tool calls
        if prose_only:
            frames.append(f"#prose#{prose_only}")

        # dispatch each call
        results_block = []
        for call in tool_calls:
            name = call["name"]
            args = call["args"]
            if progress is not None:
                try: frames.append(progress.tool_call(name, args))
                except Exception: pass
            else:
                frames.append(status_frame("tool_call", name, args=args))

            t0 = __import__("time").time()
            ok = False
            value: Any = None
            error: Optional[str] = None

            if registry is None or ToolCall is None:
                error = "no tool registry bound"
            else:
                try:
                    result = registry.dispatch(ToolCall(
                        name=name,
                        args=args,
                        actor_id=actor_id,
                        organization_id=organization_id,
                        workspace_id=workspace_id,
                    ))
                    ok = bool(result.ok)
                    value = result.value
                    error = result.error
                except Exception as e:
                    error = f"{type(e).__name__}: {e}"

            ms = round((__import__("time").time() - t0) * 1000, 1)
            calls_log.append({"name": name, "ok": ok,
                              "value": value, "error": error, "ms": ms})

            if progress is not None:
                try: frames.append(progress.tool_result(name, ok, ms))
                except Exception: pass
            else:
                frames.append(status_frame("tool_result", name, ok=ok, ms=ms))

            # payload for the frontend
            frames.append(
                "#tool-result#" + json.dumps({
                    "name": name,
                    "ok": ok,
                    "value": _shorten(value),
                    "error": error,
                    "ms": ms,
                })
            )

            # feed back to the model
            payload = {"name": name, "ok": ok, "ms": ms}
            if ok:
                payload["value"] = _shorten(value, 4000)
            else:
                payload["error"] = error
            results_block.append(
                "```tool_result\n"
                + json.dumps(payload, default=str)
                + "\n```"
            )

        if not results_block:
            final_text = prose_only or out
            break

        # next round: append results, ask model to continue
        convo = (
            convo
            + "\n\nASSISTANT:\n" + out
            + "\n\nTOOL RESULTS:\n" + "\n".join(results_block)
            + "\n\nContinue. Emit more tool fences or produce the final answer."
        )

    return {
        "frames": frames,
        "final": final_text,
        "calls": calls_log,
        "rounds": rounds,
    }


def _shorten(value: Any, limit: int = 2000) -> Any:
    """Trim large tool outputs so the frame stays readable and small."""
    if value is None:
        return None
    s = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(s) <= limit:
        return value if not isinstance(value, str) else s
    return s[:limit] + f"... [truncated, {len(s)} total chars]"
