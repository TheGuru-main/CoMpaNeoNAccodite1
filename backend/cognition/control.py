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

        # detector is optional until write/route callbacks are provided
        self.detector: Optional[PatternDetector] = None

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

        bundle = self._compose_bundle(
            query=query,
            intent=intent,
            segments=segments,
            binding_plan=binding_plan,
            role=role,
        )

        self._trace("plan_query", {
            "segments": [s.segment_id for s in segments],
            "binding": {k: (v.segment_id if v else None)
                        for k, v in binding_plan.assignments.items()},
            "code_mode": self.cfg.code_mode,
            "verification_level": self.cfg.verification_level,
        })

        return {
            "segments": segments,
            "binding_plan": binding_plan,
            "bundle": bundle,
        }

    def _compose_bundle(
        self,
        *,
        query: str,
        intent: Optional[dict],
        segments: List[Segment],
        binding_plan,
        role: str,
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

    def _trace(self, action: str, payload: dict) -> None:
        if self.tracer is None:
            return
        try:
            self.tracer.log_execution_step("CognitionControl", action, payload)
        except Exception:
            pass
