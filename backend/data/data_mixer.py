"""
CoMpaNeoN Data Mixer
====================

Central data preparation layer.

Responsibilities
----------------

DataMixer receives data from:

    - WebCrawler
    - External APIs
    - User input
    - AI output
    - Documents
    - Training datasets
    - Other internal acquisition layers

It prepares those inputs for downstream processing.

Pipeline:

    External / User / AI / Dataset
                ↓
            DataMixer
                ↓
         Intent Analyzer
                ↓
       Language / Code analysis
                ↓
        Tokenizer / Word Chain
                ↓
          Memory / Training


DataMixer does NOT own:

    - domain definitions
    - intent rules
    - tokenizer mathematics
    - Word Grid placement
    - GSP placement
    - MemoryGrid storage
    - STM
    - LTM
    - project trace segmentation
    - prompt generation
    - response generation

IMPORTANT
---------

Domain knowledge has already been consolidated into:

    intent_analyzer.py

Therefore this module does NOT import:

    domain_knowledge.py

Programming-language knowledge comes from:

    code_languages.py

Language identification comes from:

    langdetect
"""

from __future__ import annotations

import os
import random
from typing import Any, Dict, Iterable, List, Optional


# ---------------------------------------------------------------------------
# LANGUAGE DETECTION
# ---------------------------------------------------------------------------

try:
    from langdetect import detect, LangDetectException
except ImportError:
    detect = None

    class LangDetectException(Exception):
        pass


# ---------------------------------------------------------------------------
# INTENT ANALYSIS
# ---------------------------------------------------------------------------

from intent_analyzer import (
    analyze_intent,
    get_domain_entities,
)


# ---------------------------------------------------------------------------
# CODE LANGUAGE KNOWLEDGE
# ---------------------------------------------------------------------------

from code_languages import (
    get_language_list,
    get_code_terms,
)


class DataMixer:
    """
    Central data preparation and mixing layer.

    DataMixer normalizes incoming information and enriches it with:

        - language
        - intent
        - domain
        - domain entities
        - programming-language matches
        - code terminology matches
        - source metadata

    STM/LTM processing is intentionally deferred to:

        project_trace_memory_layer.py
    """

    def __init__(
        self,
        data_dir: str = "data",
    ) -> None:

        self.data_dir = data_dir

        # Raw dataset text.
        self.texts: List[str] = []

        # Normalized records produced by the mixer.
        self.records: List[Dict[str, Any]] = []

        # Statistics.
        self.total_loaded = 0
        self.total_mixed = 0

        self.load()

    # ======================================================================
    # LOAD DATASET
    # ======================================================================

    def load(self) -> None:
        """
        Load .txt files from the configured data directory.

        Every non-empty line becomes one data observation.
        """

        self.texts = []

        if not os.path.isdir(
            self.data_dir
        ):
            return

        for filename in sorted(
            os.listdir(
                self.data_dir
            )
        ):

            if not filename.lower().endswith(
                ".txt"
            ):
                continue

            path = os.path.join(
                self.data_dir,
                filename,
            )

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8",
                ) as file:

                    for line in file:

                        text = line.strip()

                        if text:
                            self.texts.append(
                                text
                            )

            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

        self.total_loaded = len(
            self.texts
        )

    # ======================================================================
    # LANGUAGE DETECTION
    # ======================================================================

    def detect_language(
        self,
        text: str,
        fallback: str = "en",
    ) -> str:
        """
        Detect natural language using langdetect.

        If langdetect is unavailable or the text is too short/ambiguous,
        fallback is returned.

        Examples:

            English → en
            French  → fr
            Arabic  → ar
            Spanish → es
        """

        text = str(
            text or ""
        ).strip()

        if not text:
            return fallback

        if detect is None:
            return fallback

        try:

            language = detect(
                text
            )

            if language:
                return language.lower()

        except (
            LangDetectException,
            Exception,
        ):
            pass

        return fallback

    # ======================================================================
    # RESOLVE LANGUAGE
    # ======================================================================

    def resolve_language(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> str:
        """
        Resolve the language for an observation.

        Explicit language takes priority.

        Otherwise langdetect is used.
        """

        if lang:

            return str(
                lang
            ).strip().lower()

        return self.detect_language(
            text
        )

    # ======================================================================
    # INTENT ANALYSIS
    # ======================================================================

    def analyze(
        self,
        text: str,
    ) -> Dict[str, Any]:
        """
        Run the centralized intent analyzer.

        intent_analyzer.py is the sole authority for:

            domain
            intent
            contextual analysis
            domain entities
        """

        try:

            result = analyze_intent(
                text
            )

            if isinstance(
                result,
                dict,
            ):
                return result

            return {
                "domain": str(
                    result
                ),
            }

        except Exception as exc:

            return {
                "domain": "general",
                "error": str(exc),
            }

    # ======================================================================
    # DOMAIN
    # ======================================================================

    def get_domain(
        self,
        text: str,
    ) -> str:
        """
        Return the domain determined by intent_analyzer.py.
        """

        analysis = self.analyze(
            text
        )

        return str(
            analysis.get(
                "domain",
                "general",
            )
        )

    # ======================================================================
    # DOMAIN ENTITIES
    # ======================================================================

    def get_entities(
        self,
        domain: str,
    ) -> List[Any]:
        """
        Get domain entities from intent_analyzer.py.

        No separate domain knowledge module is used.
        """

        try:

            entities = get_domain_entities(
                domain
            )

            if entities is None:
                return []

            return list(
                entities
            )

        except Exception:

            return []

    # ======================================================================
    # CODE LANGUAGE DETECTION
    # ======================================================================

    def detect_code_languages(
        self,
        text: str,
    ) -> List[str]:
        """
        Detect programming languages, frameworks, tools, and technologies
        appearing in the text.

        Uses the canonical list supplied by code_languages.py.
        """

        text_lower = text.lower()

        detected = []

        for language in get_language_list():

            name = str(
                language
            )

            if name.lower() in text_lower:

                detected.append(
                    name
                )

        return detected

    # ======================================================================
    # CODE TERM DETECTION
    # ======================================================================

    def detect_code_terms(
        self,
        text: str,
    ) -> List[Dict[str, str]]:
        """
        Detect known programming/code terminology.

        Returns both the term and its canonical meaning.
        """

        text_lower = text.lower()

        detected = []

        for term, meaning in (
            get_code_terms().items()
        ):

            if str(
                term
            ).lower() in text_lower:

                detected.append({
                    "term": term,
                    "meaning": meaning,
                })

        return detected

    # ======================================================================
    # CODE ANALYSIS
    # ======================================================================

    def analyze_code(
        self,
        text: str,
        domain: str,
    ) -> Dict[str, Any]:
        """
        Perform code-specific enrichment.

        Code analysis is only activated when the intent analyzer places
        the observation in a code-related domain.
        """

        if domain not in {
            "code",
            "technology",
        }:

            return {
                "languages": [],
                "terms": [],
            }

        return {
            "languages": (
                self.detect_code_languages(
                    text
                )
            ),
            "terms": (
                self.detect_code_terms(
                    text
                )
            ),
        }

    # ======================================================================
    # MIX
    # ======================================================================

    def mix(
        self,
        text: str,
        source: str = "unknown",
        lang: Optional[str] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Normalize and enrich one observation.

        Output is suitable for:

            tokenizer
            Word Chain
            MemoryGrid
            training pipeline
            future STM/LTM memory layer

        This function does NOT assign memory relevance.
        """

        text = str(
            text or ""
        ).strip()

        if not text:

            return {
                "accepted": False,
                "reason": "empty_text",
            }

        # --------------------------------------------------------------
        # LANGUAGE
        # --------------------------------------------------------------

        resolved_language = (
            self.resolve_language(
                text,
                lang,
            )
        )

        # --------------------------------------------------------------
        # INTENT
        # --------------------------------------------------------------

        intent = self.analyze(
            text
        )

        domain = str(
            intent.get(
                "domain",
                "general",
            )
        )

        # --------------------------------------------------------------
        # DOMAIN ENTITIES
        # --------------------------------------------------------------

        entities = self.get_entities(
            domain
        )

        # --------------------------------------------------------------
        # CODE-SPECIFIC KNOWLEDGE
        # --------------------------------------------------------------

        code = self.analyze_code(
            text,
            domain,
        )

        # --------------------------------------------------------------
        # NORMALIZED RECORD
        # --------------------------------------------------------------

        mixed = {
            "text": text,

            "source": source,

            "language": resolved_language,

            "domain": domain,

            "intent": intent,

            "entities": entities,

            "code": code,

            "metadata": (
                metadata or {}
            ),
        }

        self.records.append(
            mixed
        )

        self.total_mixed += 1

        return mixed

    # ======================================================================
    # ADD TEXT
    # ======================================================================

    def add_text(
        self,
        text: str,
        source: str = "unknown",
        lang: Optional[str] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Add and mix one observation.
        """

        return self.mix(
            text=text,
            source=source,
            lang=lang,
            metadata=metadata,
        )

    # ======================================================================
    # ADD MANY
    # ======================================================================

    def add_many(
        self,
        items: Iterable[Any],
        source: str = "unknown",
        lang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Add multiple observations.

        Supports:

            "plain text"

        and:

            {
                "text": "...",
                "source": "...",
                "metadata": {...}
            }
        """

        results = []

        for item in items:

            if isinstance(
                item,
                str,
            ):

                result = self.mix(
                    text=item,
                    source=source,
                    lang=lang,
                )

            elif isinstance(
                item,
                dict,
            ):

                result = self.mix(
                    text=item.get(
                        "text",
                        item.get(
                            "content",
                            "",
                        ),
                    ),
                    source=item.get(
                        "source",
                        source,
                    ),
                    lang=item.get(
                        "language",
                        lang,
                    ),
                    metadata=item.get(
                        "metadata",
                        {},
                    ),
                )

            else:
                continue

            if result.get(
                "accepted",
                True,
            ):
                results.append(
                    result
                )

        return results

    # ======================================================================
    # EXTERNAL DATA
    # ======================================================================

    def mix_external(
        self,
        data: Dict[str, Any],
        source: str = "external",
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Normalize a WebCrawler/external API response.

        Common accepted fields:

            text
            content
            title
            url
            language
            content_hash
            source_type
            doc_id
            metadata
        """

        text = data.get(
            "text"
        )

        if not text:
            text = data.get(
                "content",
                "",
            )

        metadata = dict(
            data.get(
                "metadata",
                {},
            )
        )

        for key in (
            "title",
            "url",
            "content_hash",
            "source_type",
            "doc_id",
        ):

            if key in data:

                metadata[key] = data[
                    key
                ]

        detected_language = (
            data.get(
                "language"
            )
            or lang
        )

        return self.mix(
            text=text,
            source=data.get(
                "source",
                source,
            ),
            lang=detected_language,
            metadata=metadata,
        )

    # ======================================================================
    # USER INPUT
    # ======================================================================

    def mix_user_input(
        self,
        text: str,
        user_id: Optional[Any] = None,
        lang: Optional[str] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Prepare user input.

        PSTM/LTM assignment is NOT performed here.
        """

        user_metadata = dict(
            metadata or {}
        )

        if user_id is not None:

            user_metadata[
                "user_id"
            ] = user_id

        return self.mix(
            text=text,
            source="user",
            lang=lang,
            metadata=user_metadata,
        )

    # ======================================================================
    # AI OUTPUT
    # ======================================================================

    def mix_ai_output(
        self,
        text: str,
        lang: Optional[str] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Prepare AI-generated output.

        Project trace and STM/LTM routing happen later.
        """

        return self.mix(
            text=text,
            source="ai",
            lang=lang,
            metadata=metadata,
        )

    # ======================================================================
    # DATASET BATCH
    # ======================================================================

    def get_batch(
        self,
        batch_size: int,
        analyzed: bool = True,
    ) -> List[Any]:
        """
        Return a random batch from the loaded dataset.

        analyzed=True:
            Returns normalized DataMixer records.

        analyzed=False:
            Returns raw text.
        """

        if (
            batch_size <= 0
            or not self.texts
        ):
            return []

        batch = random.sample(
            self.texts,
            min(
                batch_size,
                len(self.texts),
            ),
        )

        if not analyzed:
            return batch

        return [
            self.mix(
                text=text,
                source="dataset",
            )
            for text in batch
        ]

    # ======================================================================
    # MIX DATASET
    # ======================================================================

    def mix_dataset(
        self,
        shuffle: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Mix the complete loaded dataset.
        """

        items = list(
            self.texts
        )

        if shuffle:
            random.shuffle(
                items
    )

        return [
            self.mix(
                text=text,
                source="dataset",
            )
            for text in items
            if text.strip()
        ]

    # ======================================================================
    # STATISTICS
    # ======================================================================

    def stats(
        self,
    ) -> Dict[str, Any]:
        """
        Return DataMixer statistics.
        """

        return {
            "data_dir": self.data_dir,

            "loaded_texts": len(
                self.texts
            ),

            "records": len(
                self.records
            ),

            "total_loaded": (
                self.total_loaded
            ),

            "total_mixed": (
                self.total_mixed
            ),
        }
     