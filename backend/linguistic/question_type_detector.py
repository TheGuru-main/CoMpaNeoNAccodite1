"""
Question Type Detector

Determines what kind of question the user is asking.

Architecture position:

    tokenizer
        ↓
    question_type_detector
        ├── domain
        ├── directive
        ├── word_chain
        └── question type
                ↓
          prompts_manager

This module does NOT:
- rank documents
- retrieve memory
- modify ranking.py
- generate the final answer
- replace intent_analyzer.py
- replace directives.py
- replace word_chain.py

It interprets the question so the prompt layer can construct
the appropriate AI instruction.

The detector is deliberately deterministic and lightweight.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from intent_analyzer import detect_domain
from directives import detect_directive

try:
    from word_chain import (
        extract_word_pairs,
        extract_next_word_candidates,
    )
except ImportError:
    # Keeps the detector import-safe while word_chain.py
    # is being wired into the architecture.
    extract_word_pairs = None
    extract_next_word_candidates = None


# ---------------------------------------------------------------------------
# QUESTION TYPES
# ---------------------------------------------------------------------------

QUESTION_TYPES = {
    "what",
    "who",
    "where",
    "when",
    "why",
    "how",
    "which",
    "whose",
    "yes_no",
    "comparison",
    "calculation",
    "definition",
    "explanation",
    "instruction",
    "planning",
    "analysis",
    "recall",
    "remember",
    "recommendation",
    "prediction",
    "continuation",
    "general",
}


# ---------------------------------------------------------------------------
# QUESTION WORDS
# ---------------------------------------------------------------------------

QUESTION_WORDS = {
    "what": "what",
    "who": "who",
    "where": "where",
    "when": "when",
    "why": "why",
    "how": "how",
    "which": "which",
    "whose": "whose",
}


# ---------------------------------------------------------------------------
# PATTERNS
# ---------------------------------------------------------------------------

COMPARISON_PATTERNS = (
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bversus\b",
    r"\bvs\b",
    r"\bdifference between\b",
    r"\bbetter than\b",
    r"\bwhich is better\b",
)

CALCULATION_PATTERNS = (
    r"\bcalculate\b",
    r"\bcalculation\b",
    r"\bcompute\b",
    r"\bhow much\b",
    r"\bhow many\b",
    r"\bwhat is \d",
    r"\d+\s*[\+\-\*/x×÷]\s*\d+",
)

DEFINITION_PATTERNS = (
    r"\bdefine\b",
    r"\bdefinition\b",
    r"\bwhat does .* mean\b",
    r"\bwhat is .* meaning\b",
    r"\bmeaning of\b",
)

EXPLANATION_PATTERNS = (
    r"\bexplain\b",
    r"\bexplanation\b",
    r"\bwhy does\b",
    r"\bwhy is\b",
    r"\bwhy do\b",
)

INSTRUCTION_PATTERNS = (
    r"\bhow do i\b",
    r"\bhow can i\b",
    r"\bhow to\b",
    r"\bshow me how\b",
    r"\bsteps to\b",
    r"\bguide me\b",
)

PLANNING_PATTERNS = (
    r"\bplan\b",
    r"\bplanning\b",
    r"\bschedule\b",
    r"\broadmap\b",
    r"\bwhat should i do\b",
    r"\bwhat do i need\b",
    r"\bprepare\b",
)

ANALYSIS_PATTERNS = (
    r"\banalyze\b",
    r"\banalyse\b",
    r"\banalysis\b",
    r"\bevaluate\b",
    r"\bassess\b",
    r"\bbreak down\b",
    r"\bexamine\b",
)

RECALL_PATTERNS = (
    r"\bdo you remember\b",
    r"\bremember when\b",
    r"\bwhat did i say\b",
    r"\bwhat was my\b",
    r"\bwhat were my\b",
    r"\brecall\b",
    r"\bbring back\b",
)

REMEMBER_PATTERNS = (
    r"\bremember this\b",
    r"\bremember that\b",
    r"\bsave this\b",
    r"\bkeep this in mind\b",
    r"\bstore this\b",
)

RECOMMENDATION_PATTERNS = (
    r"\brecommend\b",
    r"\brecommendation\b",
    r"\bsuggest\b",
    r"\bsuggestion\b",
    r"\bwhat should i choose\b",
    r"\bwhat do you recommend\b",
)

PREDICTION_PATTERNS = (
    r"\bpredict\b",
    r"\bprediction\b",
    r"\bwhat will happen\b",
    r"\blikely\b",
    r"\bprobably\b",
    r"\bforecast\b",
)

CONTINUATION_PATTERNS = (
    r"\bcontinue\b",
    r"\bcontinue from\b",
    r"\bcarry on\b",
    r"\bgo on\b",
    r"\bwhat comes next\b",
    r"\bnext\b",
)


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text).strip().lower(),
    )


def _matches_any(
    text: str,
    patterns: tuple[str, ...],
) -> bool:

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def _first_question_word(
    text: str,
) -> Optional[str]:

    words = re.findall(
        r"[a-zA-Z]+",
        text.lower(),
    )

    if not words:
        return None

    return QUESTION_WORDS.get(words[0])


# ---------------------------------------------------------------------------
# WORD-CHAIN SIGNALS
# ---------------------------------------------------------------------------

def get_word_chain_signal(
    text: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Extract word-chain information without becoming responsible
    for prediction itself.

    word_chain.py remains the source of word-chain logic.
    """

    if not text:
        return {
            "pairs": [],
            "next_words": [],
        }

    pairs: List[str] = []
    next_words: List[Dict[str, Any]] = []

    if extract_word_pairs is not None:
        try:
            pairs = extract_word_pairs(text)
        except Exception:
            pairs = []

    if extract_next_word_candidates is not None:
        try:
            next_words = extract_next_word_candidates(
                text,
                limit=limit,
            )
        except Exception:
            next_words = []

    return {
        "pairs": pairs,
        "next_words": next_words,
    }


# ---------------------------------------------------------------------------
# QUESTION TYPE
# ---------------------------------------------------------------------------

def detect_question_type(
    query: str,
) -> str:
    """
    Determine the primary question type.

    Priority is intentional:
    explicit operations such as calculation, recall,
    analysis and planning are identified before generic
    interrogative words.
    """

    text = _normalize(query)

    if not text:
        return "general"

    # Explicit operations first.
    if _matches_any(text, CALCULATION_PATTERNS):
        return "calculation"

    if _matches_any(text, RECALL_PATTERNS):
        return "recall"

    if _matches_any(text, REMEMBER_PATTERNS):
        return "remember"

    if _matches_any(text, ANALYSIS_PATTERNS):
        return "analysis"

    if _matches_any(text, PLANNING_PATTERNS):
        return "planning"

    if _matches_any(text, INSTRUCTION_PATTERNS):
        return "instruction"

    if _matches_any(text, DEFINITION_PATTERNS):
        return "definition"

    if _matches_any(text, EXPLANATION_PATTERNS):
        return "explanation"

    if _matches_any(text, COMPARISON_PATTERNS):
        return "comparison"

    if _matches_any(text, RECOMMENDATION_PATTERNS):
        return "recommendation"

    if _matches_any(text, PREDICTION_PATTERNS):
        return "prediction"

    if _matches_any(text, CONTINUATION_PATTERNS):
        return "continuation"

    # Generic interrogative question.
    question_word = _first_question_word(text)

    if question_word:
        return question_word

    # Question mark without an explicit question word.
    if "?" in text:
        return "yes_no"

    return "general"


# ---------------------------------------------------------------------------
# QUESTION TYPE + DOMAIN + DIRECTIVE
# ---------------------------------------------------------------------------

def analyze_question(
    query: str,
    lang: str = "en",
    include_word_chain: bool = True,
) -> Dict[str, Any]:
    """
    Produce the complete interpretation package for prompts_manager.

    This is the main public entry point.

    It combines:
        question type
        domain
        directive
        word-chain signals

    It does not retrieve or rank documents.
    """

    if not query or not str(query).strip():
        return {
            "query": query,
            "question_type": "general",
            "domain": "general",
            "directive": None,
            "word_chain": {
                "pairs": [],
                "next_words": [],
            },
        }

    clean_query = str(query).strip()

    question_type = detect_question_type(
        clean_query
    )

    domain = detect_domain(
        clean_query
    )

    directive = detect_directive(
        clean_query
    )

    word_chain = (
        get_word_chain_signal(clean_query)
        if include_word_chain
        else {
            "pairs": [],
            "next_words": [],
        }
    )

    return {
        "query": clean_query,
        "language": lang,
        "question_type": question_type,
        "domain": domain,
        "directive": directive,
        "word_chain": word_chain,
    }


# ---------------------------------------------------------------------------
# SPECIALIZED QUESTION PROPERTIES
# ---------------------------------------------------------------------------

def is_memory_question(
    question_type: str,
) -> bool:
    return question_type in {
        "recall",
        "remember",
    }


def is_reasoning_question(
    question_type: str,
) -> bool:
    return question_type in {
        "comparison",
        "calculation",
        "analysis",
        "explanation",
        "prediction",
    }


def is_action_question(
    question_type: str,
) -> bool:
    return question_type in {
        "instruction",
        "planning",
        "recommendation",
    }


# ---------------------------------------------------------------------------
# PROMPT CONTEXT ADAPTER
# ---------------------------------------------------------------------------

def build_prompt_context(
    query: str,
    lang: str = "en",
) -> Dict[str, Any]:
    """
    Return a compact structure intended to be consumed by
    prompts_manager.py.

    prompts_manager remains responsible for constructing
    the actual prompt.
    """

    analysis = analyze_question(
        query=query,
        lang=lang,
        include_word_chain=True,
    )

    question_type = analysis["question_type"]

    return {
        "question_type": question_type,
        "domain": analysis["domain"],
        "directive": analysis["directive"],
        "word_chain": analysis["word_chain"],
        "memory_operation": (
            "recall"
            if question_type == "recall"
            else "remember"
            if question_type == "remember"
            else None
        ),
        "reasoning_required": is_reasoning_question(
            question_type
        ),
        "action_required": is_action_question(
            question_type
        ),
    }


# ---------------------------------------------------------------------------
# SIMPLE PUBLIC API
# ---------------------------------------------------------------------------

def detect(
    query: str,
    lang: str = "en",
) -> Dict[str, Any]:
    """
    Short public alias for callers that only need
    the complete question interpretation.
    """

    return analyze_question(
        query=query,
        lang=lang,
        include_word_chain=True,
    )