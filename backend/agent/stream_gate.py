"""
Accodite Stream Gate
====================
The single boundary between "model produced output" and
"user sees output".
"""
from __future__ import annotations
import re as _re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from verification.pipeline import VerificationPipeline, PipelineReport
from tree_sitter.languages import lang_for


# ============================================================================
# OPTIONAL IMPORTS
# ============================================================================

try:
    from tokenizer import tokenize as _text_tokenize, normalize_lang as _norm_lang
    TEXT_TOKENIZER_AVAILABLE = True
except ImportError:
    TEXT_TOKENIZER_AVAILABLE = False
    def _text_tokenize(text, lang="en"):
        return (text or "").split()
    def _norm_lang(lang):
        return lang or "en"

try:
    from code_tokenizer import classify_code_token as _classify, code_word_cell as _cwc
    CODE_TOKENIZER_AVAILABLE = True
except ImportError:
    CODE_TOKENIZER_AVAILABLE = False
    def _classify(tok):
        return "IDENT_VAR"
    def _cwc(tok, lang="en"):
        return {"c": 0, "color_class": "IDENT_VAR"}

try:
    import memory_partition as _mp
    MEMORY_PARTITION_AVAILABLE = True
except ImportError:
    _mp = None
    MEMORY_PARTITION_AVAILABLE = False


# ============================================================================
# DECISION
# ============================================================================

@dataclass
class GateDecision:
    allowed: bool
    path: str
    lang: str
    report: Optional[PipelineReport] = None
    retry_hint: str = ""
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "path": self.path,
            "lang": self.lang,
            "retry_hint": self.retry_hint,
            "reasons": list(self.reasons),
            "report": self.report.as_dict() if self.report else None,
        }


# ============================================================================
# TOKEN FRAMING
# ============================================================================

_TOKEN_RX = _re.compile(
    r"(?P<ws>\s+)"
    r"|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<number>\d+(?:\.\d+)?)"
    r"|(?P<op>[+\-*/%=<>!&|^~@]+)"
    r"|(?P<punct>[(){}\[\],;:.])"
    r"|(?P<other>.)"
)

_CODE_KINDS = {
    "KEYWORD", "BUILTIN", "FUNC_DEF", "FUNC_CALL", "CLASS_DEF",
    "IDENT_CONST", "IDENT_DUNDER", "IDENT_PRIVATE",
    "TYPE_ANNOT", "STRING", "NUMBER", "OPERATOR", "PUNCT",
}


def _token_frames(source: str):
    buf_ws = ""
    for m in _TOKEN_RX.finditer(source or ""):
        piece = m.group(0)
        if piece.isspace():
            buf_ws += piece
            continue
        yield buf_ws + piece
        buf_ws = ""
    if buf_ws:
        yield buf_ws


def _classify_frame(frame: str) -> str:
    tk = (frame or "").strip()
    if not tk:
        return "w"
    if CODE_TOKENIZER_AVAILABLE:
        try:
            color = _classify(tk)
            if color in _CODE_KINDS:
                return "c"
        except Exception:
            pass
    return "w"


def _frame_with_kind(frame: str):
    kind = _classify_frame(frame)
    color = None
    if kind == "c" and CODE_TOKENIZER_AVAILABLE:
        try:
            color = _classify(frame.strip())
        except Exception:
            color = None
    return kind, color, frame


def stream_tokens(source: str):
    for frame in _token_frames(source or ""):
        yield f"#token#{frame}"


# ============================================================================
# GATE
# ============================================================================

class StreamGate:
    def __init__(self, *, root: str = ".", pipeline: Optional[VerificationPipeline] = None):
        self.root = root
        self.pipeline = pipeline or VerificationPipeline(
            root=root, stop_on_first_failure=True,
        )

    def check(
        self,
        *,
        path: str,
        source: str,
        lang: Optional[str] = None,
        run_tests: bool = True,
        run_security: bool = True,
    ) -> GateDecision:
        lang = lang or lang_for(path or "")

        if not source or not source.strip():
            return GateDecision(
                allowed=False, path=path, lang=lang,
                reasons=["empty patch"],
                retry_hint="the patch is empty; produce a non-empty candidate",
            )

        report = self.pipeline.verify(
            path=path, source=source, lang=lang,
            run_tests=run_tests, run_security=run_security,
        )

        if report.ok:
            return GateDecision(
                allowed=True, path=path, lang=lang,
                report=report, reasons=["all gates passed"],
            )

        reasons: List[str] = []
        hint_bits: List[str] = []
        for s in report.stages:
            if not s.ok and not s.skipped:
                reasons.append(f"{s.name}: {len(s.findings)} finding(s)")
                for f in s.findings[:3]:
                    msg = f.get("message") or f.get("pattern") or str(f)
                    line = f.get("line", "?")
                    hint_bits.append(f"  - [{s.name}] line {line}: {msg}")

        retry_hint = (
            "the patch failed verification; fix the following before retrying:\n"
            + "\n".join(hint_bits) if hint_bits else
            "the patch failed verification; inspect the report and retry"
        )

        return GateDecision(
            allowed=False, path=path, lang=lang,
            report=report, reasons=reasons, retry_hint=retry_hint,
        )

    def stream(
        self,
        *,
        path: str,
        source: str,
        lang: Optional[str] = None,
        run_tests: bool = True,
        run_security: bool = True,
        tracer=None,
        partition=None,
        project_id: Optional[str] = None,
    ):
        decision = self.check(
            path=path, source=source, lang=lang,
            run_tests=run_tests, run_security=run_security,
        )

        if not decision.allowed:
            yield f"#error#{decision.retry_hint}"
            self._trace(tracer, partition, project_id, {
                "event": "stream.rejected", "path": path,
                "reasons": decision.reasons,
            })
            return

        yield f"#begin#{path}"
        self._trace(tracer, partition, project_id, {
            "event": "stream.begin", "path": path, "lang": decision.lang,
        })

        seq = 0
        counts = {"w": 0, "c": 0}
        for frame in _token_frames(source or ""):
            kind, color, payload = _frame_with_kind(frame)
            counts[kind] = counts.get(kind, 0) + 1
            yield f"#kind#{kind}"
            if color:
                yield f"#color#{color}"
            yield f"#token#{payload}"
            seq += 1

        yield "#end#"
        self._trace(tracer, partition, project_id, {
            "event": "stream.complete", "path": path,
            "tokens": seq, "words": counts.get("w", 0),
            "codes": counts.get("c", 0),
        })

    def _trace(self, tracer, partition, project_id, payload):
        if tracer is not None:
            try:
                tracer.log_execution_step("StreamGate", "stream", payload)
            except Exception:
                pass
        if partition is not None and project_id is not None:
            try:
                partition.trace_project(project_id, payload)
            except Exception:
                pass
