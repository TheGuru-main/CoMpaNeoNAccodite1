"""
Accodite Cognition Control
==========================

Single per-instance control that ties together:

    prompt_manager      (builds the prompt bundle)
    head_allocator      (binds segment pairs at inference)
    pattern_detector    (room health monitor)
    brain               (working grid + canonical read)

It also exposes **code-agent controls** so the caller can tune
behavior per query without touching the underlying modules:

    code_mode            on/off (disable code paths for pure chat)
    verification_level   light | standard | strict
    max_iterations       how many sandbox retries before giving up
    allow_mutations      permit fs/git/shell writes
    require_approval_for set of tool names that must be user-approved
    domain_pack          general | web_api | ml_training | ...
    dialect              per-member dialect for narration
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from model.head_router import HeadAllocator, Segment
from cognition.pattern_detector import PatternDetector

from agent.mode_classifier import (
    classify as _classify_mode,
    policy_for as _policy_for,
    Mode as _Mode,
)

from model.head_wire import (
    plan_to_head_map as _plan_to_head_map,
    apply_binding_to_model as _apply_binding_to_model,
)


LTM_READERS = {"owner", "ceo", "c_suite", "hr"}


@dataclass
class CognitionConfig:
    code_mode: bool = True
    verification_level: str = "standard"
    max_iterations: int = 3
    allow_mutations: bool = True
    domain_pack: str = "general"
    dialect: Optional[str] = None
    require_approval_for: Set[str] = field(default_factory=set)


class CognitionControl:
    def __init__(
        self,
        *,
        prompt_manager=None,
        brain=None,
        tracer=None,
        config: Optional[CognitionConfig] = None,
    ):
        self.pm = prompt_manager
        self.brain = brain
        self.tracer = tracer
        self.cfg = config or CognitionConfig()

        # per-instance allocator (one brain = one allocator)
        self.allocator = HeadAllocator()

        # user/workspace preference memory (optional)
        self.preference_store = None

        # cognition routing (optional analyze hook)
        self._analyze = None
        self._current_mode = None

        # detector is optional until write/route callbacks are provided
        self.detector: Optional[PatternDetector] = None

        # head_wire state
        self._model = None
        self._last_plan = None
        self._last_seg_to_idx: dict = {}
        self._last_head_map: list = []

    # -----------------------------------------------------------------
    # DETECTOR
    # -----------------------------------------------------------------

    def attach_detector(self, write_event, route_to_boards) -> None:
        self.detector = PatternDetector(write_event, route_to_boards)

    def observe(self, *, messages, workspace_id, organization_id) -> List[Any]:
        if self.detector is None:
            return []
        return self.detector.scan(
            messages=messages,
            workspace_id=workspace_id,
            organization_id=organization_id,
        )

    # -----------------------------------------------------------------
    # QUERY PLANNING — the main wiring point
    # -----------------------------------------------------------------

    def plan_query(
        self,
        *,
        user_id: Optional[str],
        workspace_id: Optional[str],
        organization_id: Optional[str],
        role: str,
        query: str,
        intent: Optional[dict] = None,
        extra_segments: Optional[List[Segment]] = None,
    ) -> Dict[str, Any]:
        """
        Build segments -> bind head pairs -> compose prompt bundle.
        Returns {segments, binding_plan, bundle}.
        """
        # ---- mode classification ----
        try:
            _decision = _classify_mode(
                text=query,
                analyze=getattr(self, "_analyze", None),
                domain=(intent or {}).get("domain") if isinstance(intent, dict) else None,
            )
            _policy = _policy_for(_decision.mode)
            self._current_mode = _decision
            # apply policy to the live cfg (advisory; caller may override)
            self.cfg.code_mode = _policy.code_mode
            self.cfg.verification_level = _policy.verification_level
            self.cfg.max_iterations = _policy.max_iterations
            self.cfg.allow_mutations = _policy.allow_mutations
            if _policy.prompt_domain:
                self.cfg.domain_pack = _policy.prompt_domain
        except Exception as _e:
            _decision = None
            _policy = None
        # ---- /mode ----

        segments: List[Segment] = []

        if user_id:
            segments.append(Segment(f"personal:{user_id}", "personal", priority=200))

        if workspace_id:
            segments.append(Segment(f"room:{workspace_id}", "room", priority=150))

        if organization_id and role in LTM_READERS:
            segments.append(Segment(f"org:{organization_id}", "org", priority=100))

        if extra_segments:
            segments.extend(extra_segments)

        binding_plan = self.allocator.plan(segments)

        # head_wire: convert binding plan -> head map + segment index
        try:
            _head_map, _seg_to_idx = _plan_to_head_map(binding_plan)
        except Exception:
            _head_map, _seg_to_idx = [], {}
        self._last_plan = binding_plan
        self._last_head_map = _head_map
        self._last_seg_to_idx = _seg_to_idx

        # preference block (per user / workspace)
        pref_block = ""
        if self.preference_store is not None and user_id and workspace_id:
            try:
                pref_block = self.pm._preference_block(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    store=self.preference_store,
                ) if self.pm is not None else ""
            except Exception:
                pref_block = ""

        bundle = self._compose_bundle(
            query=query,
            intent=intent,
            segments=segments,
            binding_plan=binding_plan,
            role=role,
            preference_context=pref_block,
        )

        self._trace("plan_query", {
            "segments": [s.segment_id for s in segments],
            "binding": {k: (v.segment_id if v else None)
                        for k, v in binding_plan.assignments.items()},
            "code_mode": self.cfg.code_mode,
            "verification_level": self.cfg.verification_level,
        })

        try:
            bundle["mode"] = _decision.mode.value if _decision else None
            bundle["mode_confidence"] = _decision.confidence if _decision else None
            if _policy:
                bundle["mode_policy"] = {
                    "code_mode": _policy.code_mode,
                    "verification_level": _policy.verification_level,
                    "max_iterations": _policy.max_iterations,
                    "allow_mutations": _policy.allow_mutations,
                    "read_only": _policy.read_only,
                    "emit_planning_status": _policy.emit_planning_status,
                }
        except Exception:
            pass

        return {
            "segments": segments,
            "binding_plan": binding_plan,
            "bundle": bundle,
            "head_map": _head_map,
            "segment_to_idx": _seg_to_idx,
            "mode": _decision.mode.value if _decision else None,
            "mode_policy": _policy.__dict__ if _policy else None,
        }

    def _compose_bundle(
        self,
        *,
        query: str,
        intent: Optional[dict],
        segments: List[Segment],
        binding_plan,
        role: str,
        preference_context: str = "",
    ) -> Dict[str, Any]:
        """
        Prefer prompt_manager if it exposes a builder; otherwise
        return a minimal bundle that the caller can extend.
        """
        payload = {
            "query": query,
            "intent": intent or {},
            "segments": [s.segment_id for s in segments],
            "binding": {k: (v.segment_id if v else None)
                        for k, v in binding_plan.assignments.items()},
            "role": role,
            "code_mode": self.cfg.code_mode,
            "verification_level": self.cfg.verification_level,
            "max_iterations": self.cfg.max_iterations,
            "allow_mutations": self.cfg.allow_mutations,
            "domain_pack": self.cfg.domain_pack,
            "dialect": self.cfg.dialect,
            "approval_required_for": sorted(self.cfg.require_approval_for),
            "preference_context": preference_context,
        }

        if self.pm is None:
            return payload

        # try common builder names
        for name in ("build_bundle", "compose", "build", "prepare", "get_context"):
            fn = getattr(self.pm, name, None)
            if callable(fn):
                try:
                    result = fn(**payload)
                    if isinstance(result, dict):
                        return result
                    return {**payload, "prompt": result}
                except TypeError:
                    try:
                        result = fn(query)
                        return {**payload, "prompt": result}
                    except Exception:
                        continue
                except Exception:
                    continue
        return payload

    # -----------------------------------------------------------------
    # BINDING LIFECYCLE
    # -----------------------------------------------------------------

    def release(self, segment_ids: List[str]) -> None:
        for sid in segment_ids:
            self.allocator.release(sid)

    def snapshot_binding(self) -> Dict[int, Optional[str]]:
        return self.allocator.snapshot()

    # -----------------------------------------------------------------
    # CODE-AGENT CONTROLS
    # -----------------------------------------------------------------

    def set_code_mode(self, on: bool) -> None:
        self.cfg.code_mode = bool(on)

    def set_verification_level(self, level: str) -> None:
        if level not in {"light", "standard", "strict"}:
            raise ValueError("verification_level must be light|standard|strict")
        self.cfg.verification_level = level

    def set_max_iterations(self, n: int) -> None:
        self.cfg.max_iterations = max(1, int(n))

    def set_allow_mutations(self, allow: bool) -> None:
        self.cfg.allow_mutations = bool(allow)

    def set_domain_pack(self, pack: str) -> None:
        self.cfg.domain_pack = pack

    def set_dialect(self, dialect: Optional[str]) -> None:
        self.cfg.dialect = dialect

    def require_approval(self, tool_name: str) -> None:
        self.cfg.require_approval_for.add(tool_name)

    def clear_approval_requirement(self, tool_name: str) -> None:
        self.cfg.require_approval_for.discard(tool_name)

    def should_require_approval(self, tool_name: str) -> bool:
        return tool_name in self.cfg.require_approval_for

    def can_mutate(self) -> bool:
        return self.cfg.allow_mutations

    # -----------------------------------------------------------------

    # -----------------------------------------------------------------
    # HEAD WIRING
    # -----------------------------------------------------------------

    def set_model(self, model) -> None:
        """Attach the model so plan_query results can be pushed to it."""
        self._model = model

    def bind_to_model(self, model=None):
        """
        Push the last plan's head map into the model.
        Returns segment_to_idx for mask construction.
        """
        target = model if model is not None else self._model
        if target is None or self._last_plan is None:
            return {}
        try:
            seg_to_idx = _apply_binding_to_model(target, self._last_plan)
            self._last_seg_to_idx = seg_to_idx
            return seg_to_idx
        except Exception:
            return {}

    def last_head_map(self) -> list:
        return list(self._last_head_map)

    def last_segment_to_idx(self) -> dict:
        return dict(self._last_seg_to_idx)

    def set_preference_store(self, store) -> None:
        """Attach a UserWorkspacePreferenceStore for prompt injection."""
        self.preference_store = store

    def set_analyze(self, analyze) -> None:
        """Attach a cognition.analyze.Analyze instance for mode refinement."""
        self._analyze = analyze

    def last_mode(self):
        return self._current_mode

    def _trace(self, action: str, payload: dict) -> None:
        if self.tracer is None:
            return
        try:
            self.tracer.log_execution_step("CognitionControl", action, payload)
        except Exception:
            pass
