"""
Accodite Mode Classifier
========================
Maps a request to one of six operational modes so the pipeline can
route it correctly.

Modes:
    CHAT      conversational, no artifact expected
    PLAN      thinking/structure only, no code produced
    CODE      single-artifact code generation or patch
    JOB       end-to-end multi-step build (plan + code + verify)
    RESEARCH  external fetch + comprehension
    REVIEW    inspect/audit existing code, read-only

Design:
    - pure heuristics first (fast, deterministic, no deps)
    - optional Analyze hook for refinement
    - returns a ModeDecision with confidence + evidence

The classifier never changes the query. It only labels it.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Mode(str, Enum):
    CHAT     = "chat"
    PLAN     = "plan"
    CODE     = "code"
    JOB      = "job"
    RESEARCH = "research"
    REVIEW   = "review"


# ============================================================================
# SIGNALS
# ============================================================================

_PLAN_RX = re.compile(
    r"\b(plan|roadmap|outline|break\s+down|steps?\s+for|"
    r"how\s+would\s+you|design\s+approach|strategy|"
    r"before\s+(i|we)\s+(start|begin)|propose\s+a\s+plan)\b",
    re.IGNORECASE,
)

_JOB_RX = re.compile(
    r"\b(end[\s-]?to[\s-]?end|from\s+scratch|full\s+build|"
    r"build\s+(a|an|the|out)|scaffold|"
    r"implement\s+(the\s+)?(full|entire|complete)|"
    r"create\s+(a\s+)?(new\s+)?(project|module|service|app)|"
    r"set\s+up\s+(a|an|the)|generate\s+(a|an|the)\s+(project|service))\b",
    re.IGNORECASE,
)

_CODE_RX = re.compile(
    r"\b(code|function|method|class|module|patch|bug|error|"
    r"fix|debug|refactor|implement|write\s+a\s+function|"
    r"write\s+(a\s+)?(script|helper|routine))\b",
    re.IGNORECASE,
)

_REVIEW_RX = re.compile(
    r"\b(review|audit|inspect|check\s+(this|the|my)|"
    r"what'?s\s+wrong\s+with|find\s+(bugs|issues|problems)|"
    r"critique|evaluate\s+(this|the)\s+(code|file|module))\b",
    re.IGNORECASE,
)

_RESEARCH_RX = re.compile(
    r"\b(research|look\s+up|find\s+(out|docs|documentation)|"
    r"fetch|search\s+for|what'?s\s+the\s+latest|"
    r"compare\s+\w+\s+(vs\.?|and)\s+\w+|"
    r"read\s+(the\s+)?(docs|documentation)|"
    r"cite\s+sources|news\s+about)\b",
    re.IGNORECASE,
)

_CHAT_RX = re.compile(
    r"\b(hi|hello|hey|thanks|thank\s+you|how\s+are\s+you|"
    r"what\s+do\s+you\s+think|tell\s+me\s+about|"
    r"explain|what\s+is|who\s+is|why\s+is)\b",
    re.IGNORECASE,
)

# multi-file / multi-step markers
_MULTI_FILE_RX = re.compile(
    r"\b(files?|modules?|services?|packages?|endpoints?|"
    r"routes?|controllers?|models?|migrations?|"
    r"full\s+stack|backend\s+and\s+frontend)\b",
    re.IGNORECASE,
)

_QUESTION_COUNT_RX = re.compile(r"[?？]")


# ============================================================================
# DECISION
# ============================================================================

@dataclass
class ModeDecision:
    mode: Mode
    confidence: float                       # 0..1
    signals: List[str] = field(default_factory=list)
    analyze_hint: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "confidence": round(self.confidence, 3),
            "signals": list(self.signals),
            "analyze_hint": dict(self.analyze_hint),
            "reasons": list(self.reasons),
        }


# ============================================================================
# CLASSIFIER
# ============================================================================

_LEADING_PLAN_RX = re.compile(
    r"^\s*(please\s+)?(plan|outline|roadmap|design|propose|"
    r"sketch|draft\s+a\s+plan|strategize)\b",
    re.IGNORECASE,
)


def _has_leading_plan(text: str) -> bool:
    return bool(_LEADING_PLAN_RX.match(text or ""))


def classify(
    *,
    text: str,
    analyze=None,
    domain: Optional[str] = None,
) -> ModeDecision:
    """
    Classify a request into one Mode.

    analyze: optional cognition.analyze.Analyze instance
             if provided, its output refines the decision
    domain:  optional precomputed domain string (from intent_analyzer)
    """
    src = (text or "").strip()
    if not src:
        return ModeDecision(Mode.CHAT, 0.3, reasons=["empty"])

    signals: List[str] = []
    reasons: List[str] = []

    has_plan     = bool(_PLAN_RX.search(src))
    leading_plan = _has_leading_plan(src)
    if leading_plan:
        has_plan = True
    has_job      = bool(_JOB_RX.search(src))
    has_code     = bool(_CODE_RX.search(src))
    has_review   = bool(_REVIEW_RX.search(src))
    has_research = bool(_RESEARCH_RX.search(src))
    has_chat     = bool(_CHAT_RX.search(src))
    multi_file   = bool(_MULTI_FILE_RX.search(src))
    question     = bool(_QUESTION_COUNT_RX.search(src))
    word_count   = len(src.split())

    if has_plan:     signals.append("plan")
    if has_job:      signals.append("job")
    if has_code:     signals.append("code")
    if has_review:   signals.append("review")
    if has_research: signals.append("research")
    if has_chat:     signals.append("chat")
    if multi_file:   signals.append("multi-file")
    if question:     signals.append("question")

    # -------- optional analyze refinement --------
    analyze_hint: Dict[str, Any] = {}
    if analyze is not None:
        try:
            a = analyze.analyze(src) or {}
            analyze_hint = a
            qt = (a.get("question_type") or "").lower()
            adomain = (a.get("domain") or "").lower()
            required_tools = a.get("required_tools") or []
            if required_tools and not multi_file:
                has_code = True
                reasons.append(f"analyze.required_tools={len(required_tools)}")
            if adomain in ("code", "technology", "software"):
                has_code = True
                reasons.append(f"analyze.domain={adomain}")
            if qt in ("procedural", "how-to", "how_to"):
                has_plan = True
                reasons.append(f"analyze.question_type={qt}")
        except Exception:
            analyze_hint = {}

    if domain and isinstance(domain, str):
        d = domain.lower()
        if d in ("code", "technology", "software"):
            has_code = True
            reasons.append(f"domain={d}")

    # -------- priority rules --------
    # JOB beats everything except explicit review
    if has_review and not has_job:
        return ModeDecision(
            Mode.REVIEW,
            confidence=_score(has_review, has_job, has_code, multi_file),
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["review"],
        )

    if has_job or (has_code and multi_file and word_count > 12):
        return ModeDecision(
            Mode.JOB,
            confidence=_score(has_job, True, has_code, multi_file),
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["job" if has_job else "code+multi-file"],
        )

    if has_research and not has_code:
        return ModeDecision(
            Mode.RESEARCH,
            confidence=_score(has_research, has_job, has_code, multi_file),
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["research"],
        )

    # leading "plan/outline/roadmap …" beats code unless a job signal fired
    if leading_plan and not has_job:
        return ModeDecision(
            Mode.PLAN,
            confidence=_score(has_plan, has_job, has_code, multi_file),
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["leading-plan"],
        )

    if has_code:
        return ModeDecision(
            Mode.CODE,
            confidence=_score(has_code, has_job, has_code, multi_file),
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["code"],
        )

    if has_plan and not has_chat:
        return ModeDecision(
            Mode.PLAN,
            confidence=_score(has_plan, has_job, has_code, multi_file),
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["plan"],
        )

    if has_research:
        return ModeDecision(
            Mode.RESEARCH,
            confidence=0.6,
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["research-fallback"],
        )

    if has_plan:
        return ModeDecision(
            Mode.PLAN,
            confidence=0.55,
            signals=signals, analyze_hint=analyze_hint,
            reasons=reasons + ["plan-fallback"],
        )

    # default to chat
    return ModeDecision(
        Mode.CHAT,
        confidence=0.7 if has_chat else 0.5,
        signals=signals, analyze_hint=analyze_hint,
        reasons=reasons + ["default-chat"],
    )


# ============================================================================

def _score(primary: bool, job: bool, code: bool, multi: bool) -> float:
    s = 0.5
    if primary: s += 0.2
    if job:     s += 0.15
    if code:    s += 0.1
    if multi:   s += 0.05
    return min(1.0, s)


# ============================================================================
# MODE -> POLICY
# ============================================================================

@dataclass
class ModePolicy:
    code_mode: bool = False
    verification_level: str = "light"     # light | standard | strict
    max_iterations: int = 3
    allow_mutations: bool = True
    prompt_domain: str = "technology"     # picked by prompt_manager
    emit_planning_status: bool = False
    read_only: bool = False


def policy_for(mode: Mode) -> ModePolicy:
    if mode == Mode.JOB:
        return ModePolicy(
            code_mode=True,
            verification_level="strict",
            max_iterations=5,
            allow_mutations=True,
            emit_planning_status=True,
        )
    if mode == Mode.CODE:
        return ModePolicy(
            code_mode=True,
            verification_level="standard",
            max_iterations=3,
            allow_mutations=True,
        )
    if mode == Mode.REVIEW:
        return ModePolicy(
            code_mode=True,
            verification_level="strict",
            max_iterations=2,
            allow_mutations=False,
            read_only=True,
        )
    if mode == Mode.PLAN:
        return ModePolicy(
            code_mode=False,
            verification_level="light",
            max_iterations=1,
            allow_mutations=False,
            emit_planning_status=True,
            prompt_domain="technology",
        )
    if mode == Mode.RESEARCH:
        return ModePolicy(
            code_mode=False,
            verification_level="light",
            max_iterations=1,
            allow_mutations=False,
            prompt_domain="news",
        )
    # CHAT
    return ModePolicy(
        code_mode=False,
        verification_level="light",
        max_iterations=1,
        allow_mutations=False,
    )
