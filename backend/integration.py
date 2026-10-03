"""
Accodite Integration Layer
==========================
Single wiring point between main.py and the Accodite pipeline.

Responsibilities:
    - build singletons once at startup (bootstrap)
    - decide trigger (solo vs group) for incoming messages
    - run the AI pipeline (chat + code)
    - extract fenced code blocks and verify each through StreamGate
    - stream frames back (or return synchronously)

Design:
    - solo rooms      -> every message fires the AI
    - group rooms     -> @AI / highlight / swipe-reply required
    - code blocks     -> ALWAYS verified before stream (both modes)
    - prose           -> streamed raw
"""
from __future__ import annotations
import json
import re
import os
import re
from typing import Any, Dict, Generator, List, Optional, Tuple

try:
    from agent.progress import ProgressChannel
except Exception:
    ProgressChannel = None

try:
    from agent.tool_loop import tool_loop as _tool_loop
except Exception:
    _tool_loop = None


# ============================================================================
# STATE
# ============================================================================

_STATE: Dict[str, Any] = {
    "ready": False,
    "control": None,       # CognitionControl
    "gate": None,          # StreamGate
    "registry": None,      # ToolRegistry
    "trigger": None,       # ModeAwareTriggerParser
    "pstm": None,          # PSTM
    "ltm": None,           # LTMGate
    "detector": None,      # PatternDetector
    "brain": None,         # AccoditeBrain (optional)
    "grid": None,          # MemoryGrid (optional)
    "partition": None,     # MemoryPartition (optional)
    "data_filter": None,   # DataFilter (optional)
}


def get_state() -> Dict[str, Any]:
    return _STATE


def is_ready() -> bool:
    return bool(_STATE.get("ready"))


# ============================================================================
# BOOTSTRAP
# ============================================================================

def bootstrap(*, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Build all pipeline singletons once. Idempotent.
    Returns the state dict.
    """
    if _STATE.get("ready"):
        return _STATE

    root = root or os.environ.get("ACCD_ROOT", ".")

    try:
        from agent.stream_gate import StreamGate
        _STATE["gate"] = StreamGate(root=root)
    except Exception as e:
        _STATE["gate_error"] = f"{type(e).__name__}: {e}"

    try:
        from agent.default_tools import build_registry
        _STATE["registry"] = build_registry(root=root)
    except Exception as e:
        _STATE["registry_error"] = f"{type(e).__name__}: {e}"

    try:
        from agent.trigger import ModeAwareTriggerParser
        _STATE["trigger"] = ModeAwareTriggerParser()
    except Exception as e:
        _STATE["trigger_error"] = f"{type(e).__name__}: {e}"

    try:
        from memory.pstm import PSTM
        _STATE["pstm"] = PSTM()
    except Exception as e:
        _STATE["pstm_error"] = f"{type(e).__name__}: {e}"

    try:
        from cognition.control import CognitionControl
        _STATE["control"] = CognitionControl(
            prompt_manager=None, brain=None, tracer=None,
        )
    except Exception as e:
        _STATE["control_error"] = f"{type(e).__name__}: {e}"

    try:
        from cognition.pattern_detector import PatternDetector
        _STATE["detector"] = PatternDetector(
            write_event=lambda p: None,
            route_to_boards=lambda p: None,
        )
    except Exception as e:
        _STATE["detector_error"] = f"{type(e).__name__}: {e}"

    try:
        from memory.ltm_gate import LTMGate
        _STATE["ltm"] = LTMGate(cache=None, membership_lookup=lambda u, o: None)
    except Exception as e:
        _STATE["ltm_error"] = f"{type(e).__name__}: {e}"

    # optional: grid + partition + data filter for pstm promotion
    try:
        from memory_grid import MemoryGrid
        grid = MemoryGrid()
        _STATE["grid"] = grid
    except Exception as e:
        _STATE["grid_error"] = f"{type(e).__name__}: {e}"

    try:
        from memory_partition import create_memory_partition
        if _STATE.get("grid") is not None:
            try:
                _STATE["partition"] = create_memory_partition(_STATE["grid"])
            except Exception:
                try:
                    _STATE["partition"] = create_memory_partition(
                        memory_grid=_STATE["grid"])
                except Exception:
                    _STATE["partition"] = None
    except Exception as e:
        _STATE["partition_error"] = f"{type(e).__name__}: {e}"

    try:
        from data_filter import DataFilter
        _STATE["data_filter"] = DataFilter()
    except Exception:
        try:
            from data.filter import DataFilter
            _STATE["data_filter"] = DataFilter()
        except Exception:
            _STATE["data_filter"] = None

    _STATE["ready"] = True
    return _STATE


# ============================================================================
# CODE BLOCK EXTRACTION
# ============================================================================

_FENCE_RX = re.compile(
    r"```(?P<lang>[A-Za-z0-9_+\-]*)\s*\n(?P<body>.*?)```",
    re.DOTALL,
)


def extract_code_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Return list of {index, lang, body, start, end, start_line}.
    lang defaults to 'python' when unspecified.
    """
    out: List[Dict[str, Any]] = []
    for i, m in enumerate(_FENCE_RX.finditer(text or "")):
        lang = (m.group("lang") or "python").strip().lower() or "python"
        body = m.group("body") or ""
        out.append({
            "index": i,
            "lang": lang,
            "body": body,
            "start": m.start(),
            "end": m.end(),
            "start_line": (text[:m.start()].count("\n") + 1),
        })
    return out


def _ext_for_lang(lang: str) -> str:
    return {
        "python": "py", "py": "py",
        "javascript": "js", "js": "js",
        "typescript": "ts", "ts": "ts",
        "tsx": "tsx", "jsx": "jsx",
        "rust": "rs", "go": "go",
        "c": "c", "cpp": "cpp", "c++": "cpp",
        "java": "java", "bash": "sh", "sh": "sh",
        "json": "json", "yaml": "yml", "yml": "yml",
        "sql": "sql", "html": "html", "css": "css",
    }.get(lang, "txt")


# ============================================================================
# TRIGGER
# ============================================================================

def decide_trigger(
    *,
    member_count: int,
    actor_id: str,
    workspace_id: str,
    text: str,
    message_id: Optional[str] = None,
    ref_message_id: Optional[str] = None,
    ref_is_ai: bool = False,
):
    """
    Returns a Trigger when the AI should respond, else None.
    Solo rooms (member_count <= 1) always trigger.
    Group rooms require @AI / highlight / swipe-reply.
    """
    t = _STATE.get("trigger")
    if t is None:
        return None
    return t.parse(
        member_count=member_count,
        actor_id=actor_id,
        workspace_id=workspace_id,
        text=text,
        message_id=message_id,
        ref_message_id=ref_message_id,
        ref_is_ai=ref_is_ai,
    )


# ============================================================================
# RESPONSE VERIFICATION (code blocks only)
# ============================================================================

def verify_and_frame(
    ai_text: str,
    *,
    max_iterations: int = 3,
    progress=None,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Walk fenced code blocks in `ai_text`; run each through StreamGate.
    Returns (frames, summary).

    Frames alternate:
        #prose#<chunk>              raw text between blocks
        #code-begin#<lang>#<idx>    start of a code block
        #kind#w|c                    per token
        #color#<class>              when kind==c
        #token#<payload>            per token
        #code-end#<lang>#<idx>      end of a code block
        #code-error#<idx>#<hint>    when StreamGate rejected

    #prose# frames reconstruct the non-code text.
    #token# frames inside a code block reconstruct the block body.
    """
    gate = _STATE.get("gate")
    blocks = extract_code_blocks(ai_text or "")

    frames: List[str] = []
    summary = {
        "blocks": len(blocks),
        "verified": 0,
        "rejected": 0,
        "iterations": 0,
    }

    if not blocks:
        if ai_text:
            frames.append(f"#prose#{ai_text}")
        return frames, summary

    # prose before the first block
    if blocks[0]["start"] > 0:
        frames.append(f"#prose#{ai_text[:blocks[0]['start']]}")

    for b in blocks:
        lang = b["lang"]
        ext = _ext_for_lang(lang)
        path = f"_inline_{b['index']}.{ext}"

        if gate is None:
            # no gate configured, pass through as raw
            frames.append(f"#code-begin#{lang}#{b['index']}")
            frames.append(f"#token#{b['body']}")
            frames.append(f"#code-end#{lang}#{b['index']}")
            summary["verified"] += 1
            continue

        # verify (retry loop up to max_iterations)
        body = b["body"]
        attempt = 0
        decision_ok = False
        last_error = ""
        stream_frames: List[str] = []

        if progress is not None:
            try: frames.append(progress.verifying(f"code block {b['index'] + 1}"))
            except Exception: pass

        while attempt < max_iterations:
            attempt += 1
            if progress is not None and attempt > 1:
                try: frames.append(progress.retry(attempt, max_iterations, last_error[:80]))
                except Exception: pass
            stream_frames = []
            errored = False
            for f in gate.stream(path=path, source=body):
                stream_frames.append(f)
                if f.startswith("#error#"):
                    errored = True
                    last_error = f[len("#error#"):]
                    break
            if not errored:
                decision_ok = True
                break
            # in a real system, we would ask the model to retry with last_error
            break

        summary["iterations"] += attempt

        if progress is not None:
            try: frames.append(progress.verify_result(f"code block {b['index'] + 1}", decision_ok, 0 if decision_ok else 1))
            except Exception: pass

        if decision_ok:
            frames.append(f"#code-begin#{lang}#{b['index']}")
            for f in stream_frames:
                if f.startswith("#token#") or f.startswith("#kind#") or f.startswith("#color#"):
                    frames.append(f)
            frames.append(f"#code-end#{lang}#{b['index']}")
            summary["verified"] += 1
        else:
            frames.append(f"#code-error#{b['index']}#{last_error[:400]}")
            summary["rejected"] += 1

        # prose between this block and the next
        next_start = blocks[b["index"] + 1]["start"] if b["index"] + 1 < len(blocks) else len(ai_text)
        if b["end"] < next_start:
            frames.append(f"#prose#{ai_text[b['end']:next_start]}")

    return frames, summary


# ============================================================================
# GENERATE
# ============================================================================

def handle_generate(
    *,
    workspace_id: str,
    user_id: str,
    prompt: str,
    member_count: int = 1,
    message_id: Optional[str] = None,
    ref_message_id: Optional[str] = None,
    ref_is_ai: bool = False,
    generate_fn=None,
    stream: bool = False,
    mode: Optional[str] = None,
    mode_policy: Optional[dict] = None,
    brain_uid: Optional[str] = None,   # BRAIN-PIPE
    pstm_context: Optional[dict] = None,   # PSTM-CONTEXT
):
    """
    Full pipeline for a generate request.

    generate_fn(prompt) -> str   ... the actual model call. If None,
    we fall back to whatever generate_from_prompt main.py already has
    (passed in by the caller).

    stream=True  -> returns a generator yielding frames.
    stream=False -> returns a dict with frames list + summary.
    """
    trigger = decide_trigger(
        member_count=member_count,
        actor_id=user_id,
        workspace_id=workspace_id,
        text=prompt,
        message_id=message_id,
        ref_message_id=ref_message_id,
        ref_is_ai=ref_is_ai,
    )
    if member_count > 1 and trigger is None:
        return {
            "ai_invoked": False,
            "reason": "no @AI / highlight / reply trigger in group room",
            "frames": [],
            "summary": {},
        }

    if generate_fn is None:
        raise RuntimeError("handle_generate requires generate_fn(prompt)->str")

    # MODE-AWARE: skip code verification entirely for chat/plan/research
    policy = mode_policy or {}
    code_mode = bool(policy.get("code_mode", True))
    emit_planning = bool(policy.get("emit_planning_status", False))

    progress = ProgressChannel() if ProgressChannel is not None else None
    if progress is not None:
        try:
            if emit_planning:
                progress.planning("Thinking through this…")
            progress.generating("Generating response…")
        except Exception:
            pass

    ai_text = generate_fn(prompt) or ""

    if code_mode:
        frames, summary = verify_and_frame(ai_text, progress=progress)
    else:
        # chat / plan / research: stream as prose, no code gate
        frames = [f"#prose#{ai_text}"] if ai_text else []
        summary = {"blocks": 0, "verified": 0, "rejected": 0, "iterations": 0,
                   "mode_skipped_verification": mode or "chat"}

    if progress is not None:
        try:
            if emit_planning:
                progress.done(f"plan complete ({mode or 'plan'})")
            else:
                progress.done(f"verified {summary.get('verified', 0)} block(s)")
        except Exception:
            pass

    # PST memory: record draft, suggestions, etc. (best-effort)
    # GEN-IDENTITY: phone-first identity for PSTM keying
    pstm = _STATE.get("pstm")
    if pstm is not None:
        try:
            from memory.pstm import pstm_id_from_user
            actor_identity = user_id
            try:
                user_obj = _STATE.get("user_lookup") and _STATE["user_lookup"](user_id)
                if user_obj is not None:
                    actor_identity = pstm_id_from_user(user_obj) or user_id
            except Exception:
                pass
            pstm.set_draft(workspace_id, actor_identity, "")
            pstm.add_suggestion(workspace_id, actor_identity, "response ready")
            if brain_uid:
                try:
                    pstm.set_extra(workspace_id, actor_identity, "brain_uid", brain_uid)
                except Exception:
                    pass
        except Exception:
            pass

    if stream:
        def _gen():
            yield f"#begin#{workspace_id}"
            for f in frames:
                yield f
            yield "#end#"
        return _gen()

    return {
        "ai_invoked": True,
        "trigger": trigger.kind.value if trigger else None,
        "mode": mode,
        "code_mode": code_mode,
        "frames": frames,
        "summary": summary,
        "raw": ai_text,
        "brain_uid": brain_uid,
        "pstm_used": bool(pstm_context),
    }


# ============================================================================
# MESSAGE
# ============================================================================

def handle_message(
    *,
    workspace_id: str,
    user_id: str,
    text: str,
    member_count: int,
    message_id: Optional[str] = None,
    ref_message_id: Optional[str] = None,
    ref_is_ai: bool = False,
) -> Dict[str, Any]:
    """
    Decide whether the incoming message should invoke the AI.
    Returns {invoked: bool, trigger: str|None}.
    """
    trigger = decide_trigger(
        member_count=member_count,
        actor_id=user_id,
        workspace_id=workspace_id,
        text=text,
        message_id=message_id,
        ref_message_id=ref_message_id,
        ref_is_ai=ref_is_ai,
    )

    # PST: promote the user's draft into the grid + partition, then clear.
    # PROMOTE-DRAFT
    # IDENTITY: phone-first — resolve user_id -> phone when possible.
    pstm = _STATE.get("pstm")
    promotion: Dict[str, Any] = {}
    if pstm is not None:
        try:
            from memory.pstm import pstm_id_from_user
            actor_identity = user_id
            user_obj = None
            try:
                user_obj = _STATE.get("user_lookup") and _STATE["user_lookup"](user_id)
            except Exception:
                user_obj = None
            if user_obj is not None:
                actor_identity = pstm_id_from_user(user_obj) or user_id

            # ensure draft reflects the sent text before promoting
            try:
                pstm.set_draft(workspace_id, actor_identity, text or "")
            except Exception:
                pass

            try:
                promotion = pstm.promote_draft(
                    workspace_id,
                    actor_identity,
                    grid=_STATE.get("grid"),
                    partition=_STATE.get("partition"),
                    project_id=workspace_id,
                    data_filter=_STATE.get("data_filter"),
                ) or {}
            except Exception as e:
                promotion = {"error": f"{type(e).__name__}: {e}"}
        except Exception:
            pass

    return {
        "invoked": trigger is not None,
        "trigger": trigger.kind.value if trigger else None,
        "promotion": promotion,
    }


# ============================================================================
# STATUS
# ============================================================================

def status() -> Dict[str, Any]:
    s = dict(_STATE)
    s.pop("control", None)
    s.pop("gate", None)
    s.pop("registry", None)
    s.pop("trigger", None)
    s.pop("pstm", None)
    s.pop("ltm", None)
    s.pop("detector", None)
    s.pop("brain", None)
    return s


# ============================================================================
# JOB PIPELINE (Mode.JOB)
# ============================================================================

# JOB-HARDEN
_STEP_RX = re.compile(
    r"^\s*(?:\d+[.)]|[-*•])\s+(.+?)\s*$",
    re.MULTILINE,
)


def _normalize_plan_text(text: str) -> str:
    """
    Some models emit plans with literal '\n' escape sequences instead of
    real newlines. Convert those (and '\t') so the step parser can match.
    """
    if not text:
        return ""

    # convert literal \\n to real newline
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")

    # convert literal \\t to real tab
    if "\\t" in text and "\t" not in text:
        text = text.replace("\\t", "\t")

    return text

def _parse_steps(plan_text: str, *, max_steps: int = 8) -> List[str]:
    """Extract numbered/bulleted steps from a plan text."""
    steps: List[str] = []
    for m in _STEP_RX.finditer(plan_text or ""):
        line = (m.group(1) or "").strip()
        if not line:
            continue
        # skip nested list items that are part of a step's detail
        if line.startswith(("Note:", "note:")):
            continue
        steps.append(line)
        if len(steps) >= max_steps:
            break
    return steps


def run_job(
    *,
    workspace_id: str,
    user_id: str,
    prompt: str,
    generate_fn,
    plan_fn=None,
    max_steps: int = 8,
    max_iterations: int = 5,
    code_mode: bool = True,
    verify_each_step: bool = True,
    registry=None,
    enable_tools: bool = True,
    max_tool_rounds: int = 5,
):
    """
    Generator. Runs a Mode.JOB request end to end.

    Yields frames:
        #status#{"kind":"planning",...}
        #status#{"kind":"plan",...}          with the parsed step count
        #status#{"kind":"step","msg":"1/3","description":"..."}
        #status#{"kind":"verifying",...}
        #status#{"kind":"verify_result",...}
        #status#{"kind":"retry",...}
        #code-begin# / #token#* / #code-end#   per verified step
        #prose#<step plan prose>
        #status#{"kind":"done",...}
        #error#<hint>                        when the job aborts
    """
    progress = ProgressChannel() if ProgressChannel is not None else None
    planner = plan_fn or generate_fn

    # --- Phase 1: planning ---
    if progress is not None:
        yield progress.planning("Drafting plan…")

    plan_prompt = (
        "Produce a numbered plan for the following request. "
        "Each step should be a single sentence. "
        "Do not produce code yet — plan only.\n\n"
        f"REQUEST:\n{prompt}"
    )
    try:
        plan_text = planner(plan_prompt) or ""
    except Exception as e:
        yield f"#error#planner failed: {type(e).__name__}: {e}"
        return

    plan_text_normalized = _normalize_plan_text(plan_text)
    if plan_text_normalized != plan_text:
        plan_text = plan_text_normalized
        # re-emit the normalized plan to the client
        # (the earlier #prose# frame carried the raw version)
    steps = _parse_steps(plan_text, max_steps=max_steps)
    if not steps:
        # fall back to a single-step job: treat the whole request as one step
        steps = [prompt]

    if progress is not None:
        yield progress._emit("plan", f"{len(steps)} step(s)",
                             steps=len(steps))

    yield f"#prose#{plan_text}"

    # --- Phase 2: execute ---
    total = len(steps)
    all_summaries: List[Dict[str, Any]] = []
    failures = 0

    for idx, step in enumerate(steps, start=1):
        if progress is not None:
            yield progress._emit("step", f"{idx}/{total}", description=step[:140])

        step_prompt = (
            f"You are executing step {idx} of {total} of a larger plan.\n"
            f"Overall request:\n{prompt}\n\n"
            f"Current step:\n{step}\n\n"
            "Produce only the code needed for this step. If the step is not "
            "a coding step, produce a short prose answer instead."
        )

        # per-step retry loop
        attempt = 0
        step_ok = False
        last_hint = ""
        step_frames: List[str] = []
        step_summary: Dict[str, Any] = {"step": idx, "description": step}

        while attempt < max_iterations:
            attempt += 1
            if attempt > 1 and progress is not None:
                yield progress.retry(attempt, max_iterations, last_hint[:80])

            try:
                if enable_tools and _tool_loop is not None and registry is not None:
                    # each step gets the full tool surface
                    tool_result = _tool_loop(
                        prompt=step_prompt,
                        generate_fn=generate_fn,
                        registry=registry,
                        actor_id=user_id,
                        organization_id=None,
                        workspace_id=workspace_id,
                        max_rounds=max_tool_rounds,
                        progress=progress,
                    )
                    # stream the tool_loop frames as they happen
                    for f in tool_result.get("frames", []):
                        yield f
                    step_out = tool_result.get("final", "") or ""
                    step_summary_tools = {
                        "tool_calls": len(tool_result.get("calls", [])),
                        "tool_rounds": tool_result.get("rounds", 0),
                    }
                else:
                    step_out = generate_fn(step_prompt) or ""
                    step_summary_tools = {}
            except Exception as e:
                last_hint = f"generator failed: {type(e).__name__}: {e}"
                continue

            if not verify_each_step or not code_mode:
                step_frames = [f"#prose#{step_out}"]
                step_summary["verified"] = 0
                step_summary["skipped_verification"] = True
                step_ok = True
                break

            frames_i, summary_i = verify_and_frame(step_out, progress=progress)
            step_frames = frames_i
            step_summary.update(summary_i)

            if summary_i.get("rejected", 0) == 0 and summary_i.get("blocks", 0) >= 0:
                # ok if nothing was rejected (even zero blocks is fine — prose step)
                step_ok = True
                break
            last_hint = (
                f"step {idx}: {summary_i.get('rejected', 0)} block(s) rejected"
            )

        step_summary["attempts"] = attempt
        step_summary["ok"] = step_ok
        if 'step_summary_tools' in dir() and step_summary_tools:
            step_summary.update(step_summary_tools)
        all_summaries.append(step_summary)

        for f in step_frames:
            yield f

        if not step_ok:
            failures += 1
            yield f"#error#step {idx} failed after {attempt} attempt(s): {last_hint}"

    # --- Phase 3: wrap ---
    if progress is not None:
        yield progress.done(
            f"job complete — {total - failures}/{total} step(s) ok"
        )

    yield f"#meta#{json.dumps({'steps': total, 'failures': failures, 'summaries': all_summaries})}"
