"""
CoMpaNeoN DataFilter
====================

Training-ground admission and recognition layer.

Responsibilities
----------------
DataFilter receives internal or derived knowledge and determines whether
the material is suitable to enter background training.

It does not replace:
    - data_mixer.py
    - tokenizer.py
    - intent_analyzer.py
    - question_type_detector.py
    - directives.py
    - symbols.py
    - code_languages.py
    - memory_partition.py
    - grid_cv.py
    - word_chain.py
    - word_understanding.py
    - train.py
    - fine_tuner_and_weight_scalar.py

DataFilter recognizes and packages training-worthy material while
preserving source, provenance, language, domain, intent, directive,
symbols, code-language signals, project context, and GridCV context.

Tokenizer remains the authority for lexical identity and token/grid data.
MemoryPartition remains the authority for routing.
GridCV remains the authority for vector construction and validation.
DataFilter only passes those signals downstream.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional


# ============================================================================
# EXISTING ARCHITECTURE AUTHORITIES
# ============================================================================

try:
    from .intent_analyzer import analyze_intent
    from .question_type_detector import analyze_question
    from .directives import detect_directive
    from .symbols import recognize_symbols
    from .code_languages import (
        get_code_terms,
        get_language_list,
    )
    from .tokenizer import (
        tokenize,
        normalize_lang,
    )
    from .grid_cv import GridCV

except ImportError:

    from intent_analyzer import analyze_intent
    from question_type_detector import analyze_question
    from directives import detect_directive
    from symbols import recognize_symbols
    from code_languages import (
        get_code_terms,
        get_language_list,
    )
    from tokenizer import (
        tokenize,
        normalize_lang,
    )
    from grid_cv import GridCV


# ============================================================================
# SOURCE WEIGHTS
# ============================================================================

# Human/user material is the strongest source signal.
#
# AI-derived material is still allowed into the training ground, but carries
# a lower source factor so downstream training can distinguish it from
# primary human input and reduce self-feeding bias.

SOURCE_FACTORS = {
    "human": 1.0,
    "user": 1.0,
    "user_input": 1.0,
    "manual": 1.0,

    "research": 1.0,
    "external": 1.0,
    "crawler": 1.0,
    "web": 1.0,

    "ai": 0.4,
    "ai_generated": 0.4,
    "model": 0.4,
    "derived": 0.4,
    "synthetic": 0.4,
}


def source_factor(
    source: Any,
    metadata: Optional[Mapping[str, Any]] = None,
) -> float:
    """
    Resolve the source factor without changing the source identity.

    Explicit metadata weight/source_factor takes precedence.
    """

    metadata = metadata or {}

    explicit = metadata.get(
        "source_factor",
        metadata.get("weight"),
    )

    if isinstance(explicit, (int, float)):
        return float(explicit)

    value = str(
        source
        or metadata.get("source")
        or ""
    ).strip().lower()

    if value in SOURCE_FACTORS:
        return SOURCE_FACTORS[value]

    for key, factor in SOURCE_FACTORS.items():

        if key in value:
            return factor

    return 1.0


# ============================================================================
# HELPERS
# ============================================================================

def _clean_text(
    value: Any,
) -> str:
    """
    Normalize incoming text only at the admission boundary.
    """

    if value is None:
        return ""

    return str(value).strip()


def _metadata(
    record: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Safely extract record metadata.
    """

    value = record.get(
        "metadata",
        {},
    )

    if isinstance(value, Mapping):
        return dict(value)

    return {}


def _normalize_tokens(
    tokens: Any,
) -> List[Dict[str, Any]]:
    """
    Preserve supplied tokenizer records when they already exist.
    """

    if not isinstance(tokens, list):
        return []

    return [
        dict(token)
        for token in tokens
        if isinstance(token, Mapping)
    ]


def _recognize_code_languages(
    text: str,
) -> List[str]:
    """
    Recognize programming-language names from the existing catalogue.

    DataFilter does not create a new programming-language catalogue.
    """

    lower = text.lower()

    found: List[str] = []

    for language in get_language_list():

        name = str(language)

        if name.lower() in lower:
            found.append(name)

    return found


def _recognize_code_terms(
    text: str,
) -> List[Dict[str, str]]:
    """
    Recognize existing code terms.

    This does not replace the project's coding/symbol authorities.
    """

    lower = text.lower()

    found: List[Dict[str, str]] = []

    for term, meaning in get_code_terms().items():

        if str(term).lower() in lower:

            found.append(
                {
                    "term": str(term),
                    "meaning": str(meaning),
                }
            )

    return found


# ============================================================================
# DATA FILTER
# ============================================================================

class DataFilter:
    """
    CoMpaNeoN training-ground admission layer.

    DataFilter:

        1. receives internal/derived knowledge
        2. recognizes the material
        3. preserves contextual signals
        4. determines training-worthiness
        5. packages the material for LearnWords/background training

    DataFilter does NOT:

        - perform model training
        - perform GSP traversal
        - perform MemoryGrid placement
        - own MemoryPartition routing
        - replace DataMixer
        - replace tokenizer
        - replace GridCV
        - replace FineTuner
    """

    def __init__(
        self,
        grid_cv: Optional[GridCV] = None,
    ) -> None:

        self.grid_cv = (
            grid_cv
            if grid_cv is not None
            else GridCV()
        )

    # ========================================================================
    # RECOGNITION
    # ========================================================================

    def recognize(
        self,
        text: str,
        lang: str = "en",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Recognize one piece of knowledge.

        All recognition signals are preserved in the returned record so
        downstream layers do not need to repeatedly rediscover them.
        """

        clean_text = _clean_text(
            text
        )

        metadata = dict(
            metadata or {}
        )

        language = normalize_lang(
            metadata.get(
                "lang",
                metadata.get(
                    "language",
                    lang,
                ),
            )
        )

        # ------------------------------------------------------------------
        # TOKENIZER
        # ------------------------------------------------------------------

        tokens = (
            tokenize(
                clean_text,
                language,
            )
            if clean_text
            else []
        )

        # ------------------------------------------------------------------
        # INTENT / DOMAIN / ENTITY RECOGNITION
        # ------------------------------------------------------------------

        if clean_text:

            intent = analyze_intent(
                clean_text,
                language=language,
            )

        else:

            intent = {
                "query": "",
                "language": language,
                "domain": "general",
                "domain_matches": {},
                "intent": "general",
                "entities": {},
                "entity_counts": {},
                "has_entities": False,
                "domain_entities": [],
            }

        # ------------------------------------------------------------------
        # QUESTION RECOGNITION
        # ------------------------------------------------------------------

        if clean_text:

            question = analyze_question(
                clean_text,
                lang=language,
                include_word_chain=True,
            )

        else:

            question = {
                "query": "",
                "language": language,
                "question_type": "general",
                "domain": "general",
                "directive": None,
                "word_chain": {
                    "pairs": [],
                    "next_words": [],
                },
            }

        # ------------------------------------------------------------------
        # DOMAIN
        # ------------------------------------------------------------------

        domain = (
            metadata.get("domain")
            or intent.get("domain")
            or question.get("domain")
            or "general"
        )

        # ------------------------------------------------------------------
        # SYMBOL RECOGNITION
        # ------------------------------------------------------------------

        symbols = (
            recognize_symbols(
                clean_text,
                domain=domain,
            )
            if clean_text
            else []
        )

        # ------------------------------------------------------------------
        # CODE RECOGNITION
        # ------------------------------------------------------------------

        code_languages = (
            _recognize_code_languages(
                clean_text
            )
            if clean_text
            else []
        )

        code_terms = (
            _recognize_code_terms(
                clean_text
            )
            if clean_text
            else []
        )

        # ------------------------------------------------------------------
        # DIRECTIVE
        # ------------------------------------------------------------------

        directive = (
            detect_directive(
                clean_text
            )
            if clean_text
            else "general"
        )

        # ------------------------------------------------------------------
        # FINAL RECOGNIZED RECORD
        # ------------------------------------------------------------------

        return {

            # ================================================================
            # ORIGINAL MATERIAL
            # ================================================================

            "text": clean_text,

            "language": language,

            "lang": language,

            "tokens": tokens,

            # ================================================================
            # SOURCE / PROVENANCE
            # ================================================================

            "source": metadata.get(
                "source",
                "",
            ),

            "source_factor": source_factor(
                metadata.get(
                    "source",
                    "",
                ),
                metadata,
            ),

            # ================================================================
            # DOMAIN / INTENT
            # ================================================================

            "domain": domain,

            "domain_matches": intent.get(
                "domain_matches",
                {},
            ),

            "intent": intent.get(
                "intent",
                "general",
            ),

            "entities": intent.get(
                "entities",
                {},
            ),

            "entity_counts": intent.get(
                "entity_counts",
                {},
            ),

            "has_entities": intent.get(
                "has_entities",
                False,
            ),

            # ================================================================
            # QUESTION / DIRECTIVE
            # ================================================================

            "question_type": question.get(
                "question_type",
                "general",
            ),

            "directive": (
                question.get(
                    "directive"
                )
                or directive
            ),

            "word_chain": question.get(
                "word_chain",
                {
                    "pairs": [],
                    "next_words": [],
                },
            ),

            # ================================================================
            # RECOGNITION
            # ================================================================

            "symbols": symbols,

            "code_languages": code_languages,

            "code_terms": code_terms,

            # ================================================================
            # PROJECT CONTEXT
            # ================================================================

            "project_id": metadata.get(
                "project_id",
            ),

            "project": metadata.get(
                "project",
            ),

            "project_trace": metadata.get(
                "project_trace",
            ),

            "project_pin": metadata.get(
                "project_pin",
            ),

            "project_iteration": metadata.get(
                "project_iteration",
            ),

            "project_context_aware": metadata.get(
                "project_context_aware",
                metadata.get(
                    "project_context"
                ),
            ),

            # ================================================================
            # GRID / MEMORY CONTEXT
            # ================================================================

            "hierarchy": metadata.get(
                "hierarchy",
            ),

            "role": metadata.get(
                "role",
            ),

            "relevancy": metadata.get(
                "relevancy",
            ),

            "state": metadata.get(
                "state",
            ),

            "partition": metadata.get(
                "partition",
            ),

            # ================================================================
            # ORIGINAL METADATA
            # ================================================================

            "metadata": metadata,
        }

    # ========================================================================
    # TRAINING-WORTHINESS
    # ========================================================================

    def is_training_worthy(
        self,
        recognized: Mapping[str, Any],
    ) -> bool:
        """
        Determine whether recognized material should enter training.

        Empty material is rejected.

        Recognized lexical material, symbols, code signals, or entities
        can qualify the material for admission.

        Source factor does not itself reject material.
        """

        text = _clean_text(
            recognized.get(
                "text"
            )
        )

        if not text:
            return False

        tokens = _normalize_tokens(
            recognized.get(
                "tokens"
            )
        )

        lexical_tokens = [

            token

            for token in tokens

            if (
                token.get("normalized")
                or token.get("stem")
                or token.get("original")
            )
        ]

        if lexical_tokens:
            return True

        # ---------------------------------------------------------------
        # SYMBOL SIGNAL
        # ---------------------------------------------------------------

        if recognized.get(
            "symbols"
        ):
            return True

        # ---------------------------------------------------------------
        # CODE SIGNAL
        # ---------------------------------------------------------------

        if recognized.get(
            "code_terms"
        ):
            return True

        if recognized.get(
            "code_languages"
        ):
            return True

        # ---------------------------------------------------------------
        # ENTITY SIGNAL
        # ---------------------------------------------------------------

        entities = recognized.get(
            "entities"
        )

        if isinstance(
            entities,
            Mapping,
        ):

            if any(
                bool(value)
                for value in entities.values()
            ):
                return True

        return False

    # ========================================================================
    # GRIDCV CONTEXT
    # ========================================================================

    def build_gridcv_context(
        self,
        recognized: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Expose existing GridCV context.

        DataFilter does not invent routing or GSP values.

        If an existing partition is supplied, GridCV's own partition_vector()
        is used.

        Otherwise project context can still be represented through the
        existing GridCV project_context_vector().
        """

        project_context = (
            recognized.get(
                "project_context_aware"
            )
            or recognized.get(
                "project_context"
            )
            or recognized.get(
                "project"
            )
            or recognized.get(
                "project_id"
            )
        )

        result: Dict[str, Any] = {

            "project_context": project_context,

            "project_context_vector": (
                self.grid_cv.project_context_vector(
                    project_context
                )
                if project_context is not None
                else []
            ),
        }

        # ------------------------------------------------------------------
        # EXISTING PARTITION
        # ------------------------------------------------------------------

        partition = recognized.get(
            "partition"
        )

        if isinstance(
            partition,
            Mapping,
        ):

            partition_data = dict(
                partition
            )

            # Carry recognized contextual information into the existing
            # partition only when it is not already present.

            for key in (
                "domain",
                "hierarchy",
                "role",
                "relevancy",
                "project_trace",
                "project_pin",
                "project_iteration",
                "state",
                "project_context_aware",
            ):

                if (
                    key not in partition_data
                    and recognized.get(key) is not None
                ):

                    partition_data[key] = (
                        recognized.get(key)
                    )

            result[
                "partition"
            ] = partition_data

            result[
                "partition_vector"
            ] = self.grid_cv.partition_vector(
                partition_data
            )

        return result

    # ========================================================================
    # FILTER ONE RECORD
    # ========================================================================

    def filter_record(
        self,
        record: Mapping[str, Any],
        lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Recognize and admit one incoming knowledge record.
        """

        if not isinstance(
            record,
            Mapping,
        ):

            return {
                "accepted": False,
                "training_worthy": False,
                "reason": (
                    "record must be a mapping"
                ),
            }

        # ------------------------------------------------------------------
        # RESOLVE TEXT
        # ------------------------------------------------------------------

        text = _clean_text(
            record.get(
                "text"
            )
            or record.get(
                "content"
            )
            or record.get(
                "data"
            )
        )

        # ------------------------------------------------------------------
        # RESOLVE METADATA
        # ------------------------------------------------------------------

        metadata = _metadata(
            record
        )

        # Preserve important top-level context fields.

        context_keys = (
            "source",
            "lang",
            "language",
            "domain",
            "project_id",
            "project",
            "project_trace",
            "project_pin",
            "project_iteration",
            "project_context",
            "project_context_aware",
            "hierarchy",
            "role",
            "relevancy",
            "state",
            "partition",
            "source_factor",
            "weight",
        )

        for key in context_keys:

            if (
                key in record
                and key not in metadata
            ):

                metadata[key] = record.get(
                    key
                )

        # ------------------------------------------------------------------
        # RECOGNIZE
        # ------------------------------------------------------------------

        recognized = self.recognize(
            text=text,
            lang=lang,
            metadata=metadata,
        )

        # ------------------------------------------------------------------
        # PRESERVE PRE-EXISTING TOKENIZER OUTPUT
        # ------------------------------------------------------------------

        supplied_tokens = record.get(
            "tokens"
        )

        if (
            isinstance(
                supplied_tokens,
                list,
            )
            and supplied_tokens
        ):

            recognized[
                "tokens"
            ] = _normalize_tokens(
                supplied_tokens
            )

        # ------------------------------------------------------------------
        # ADMISSION DECISION
        # ------------------------------------------------------------------

        accepted = self.is_training_worthy(
            recognized
        )

        recognized[
            "accepted"
        ] = accepted

        recognized[
            "training_worthy"
        ] = accepted

        # ------------------------------------------------------------------
        # GRIDCV PACKAGE
        # ------------------------------------------------------------------

        if accepted:

            recognized[
                "gridcv"
            ] = self.build_gridcv_context(
                recognized
            )

            recognized[
                "filter_reason"
            ] = (
                "recognized training-worthy material"
            )

        else:

            recognized[
                "gridcv"
            ] = {}

            recognized[
                "filter_reason"
            ] = (
                "no training-worthy lexical or "
                "recognition signal"
            )

        return recognized

    # ========================================================================
    # FILTER MULTIPLE RECORDS
    # ========================================================================

    def filter_records(
        self,
        records: Iterable[Mapping[str, Any]],
        lang: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Filter a collection while preserving admission order.
        """

        accepted: List[Dict[str, Any]] = []

        for record in records:

            result = self.filter_record(
                record,
                lang=lang,
            )

            if result.get(
                "accepted"
            ):

                accepted.append(
                    result
                )

        return accepted

    # ========================================================================
    # FILTER RAW TEXT
    # ========================================================================

    def filter_text(
        self,
        text: str,
        lang: str = "en",
        metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Convenience API for filtering one text item.
        """

        return self.filter_record(
            {
                "text": text,

                "metadata": dict(
                    metadata or {}
                ),
            },
            lang=lang,
        )


# ============================================================================
# MODULE-LEVEL API
# ============================================================================

_default_filter = DataFilter()


def filter_record(
    record: Mapping[str, Any],
    lang: str = "en",
) -> Dict[str, Any]:
    """
    Module-level single-record admission helper.
    """

    return _default_filter.filter_record(
        record,
        lang=lang,
    )


def filter_records(
    records: Iterable[Mapping[str, Any]],
    lang: str = "en",
) -> List[Dict[str, Any]]:
    """
    Module-level batch admission helper.
    """

    return _default_filter.filter_records(
        records,
        lang=lang,
    )


def filter_text(
    text: str,
    lang: str = "en",
    metadata: Optional[
        Mapping[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    Module-level text admission helper.
    """

    return _default_filter.filter_text(
        text,
        lang=lang,
        metadata=metadata,
    )


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "DataFilter",
    "SOURCE_FACTORS",
    "source_factor",
    "filter_record",
    "filter_records",
    "filter_text",
]