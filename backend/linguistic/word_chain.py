"""
Word Chain Module
=================

CoMpaNeoN relationship, continuation, and retrieval-construction layer.

Architecture:

    MemoryGrid
        ↓
    GridCrawler
        ↓
    Ranking
        ↓
    WordChain
        ├── tokenizer.py
        ├── relation_and_alphabet_matrix.py
        ├── matrix_maths.py
        └── ranking.py
        ↓
    word_understanding.py
        ↓
    AI model

Responsibilities:
- Retrieve knowledge from MemoryGrid through GridCrawler.
- Use ranking.py to rank retrieved knowledge.
- Use tokenizer.py for language-aware tokenization.
- Build adjacent word relationships.
- Build next-word transitions.
- Build phrase continuity.
- Build word-pair relationships.
- Consume the alphabet relationship matrix.
- Consume matrix mathematical weighting.
- Preserve personal/workspace/project/external source separation.
- Support multilingual knowledge.
- Provide deterministic retrieval/construction signals.

WordChain does NOT:
- Generate the final AI response.
- Replace MemoryGrid.
- Replace GridCrawler.
- Replace Ranking.
- Replace word_understanding.py.
- Replace the AI model.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional

from langdetect import detect, LangDetectException

from tokenizer import (
    tokenize,
    normalize_lang,
)

from relation_and_alphabet_matrix import (
    get_word_relationships,
    get_word_relationship_classes,
    relationship_signature,
    relationship_score,
)

from matrix_maths import *

from ranking import score_candidate

from memory_grid import MemoryGrid


# ---------------------------------------------------------------------------
# MEMORY GRID
# ---------------------------------------------------------------------------

memory_grid = MemoryGrid()


# ---------------------------------------------------------------------------
# TOKEN / LANGUAGE HELPERS
# ---------------------------------------------------------------------------

WORD_PATTERN = re.compile(
    r"[a-zA-Z0-9_]+(?:[-'][a-zA-Z0-9_]+)*"
)


def detect_lang(text: str) -> str:
    """
    Detect the language of a text chunk.

    langdetect is intentionally used here because WordChain may receive
    mixed-language material from MemoryGrid.
    """

    if not text or not str(text).strip():
        return "en"

    try:
        detected = detect(str(text))
        return normalize_lang(detected)

    except LangDetectException:
        return "en"

    except Exception:
        return "en"


def clean_words(text: str) -> List[str]:
    """
    Lightweight compatibility word extraction.

    tokenizer.py remains authoritative for linguistic tokenization.
    """

    if not text:
        return []

    return WORD_PATTERN.findall(
        str(text).lower()
    )


def tokenize_text(
    text: str,
    language: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Tokenize text through the project's tokenizer.

    Language is detected dynamically when not supplied.
    """

    if not text:
        return []

    lang = normalize_lang(
        language or detect_lang(text)
    )

    try:
        return tokenize(
            str(text),
            lang,
        )

    except Exception:
        return []


def linguistic_words(
    text: str,
    language: Optional[str] = None,
) -> List[str]:
    """
    Return normalized linguistic units from tokenizer.py.

    Stems are preferred, with original tokens retained as fallback.
    """

    tokens = tokenize_text(
        text,
        language,
    )

    words = []

    for token in tokens:

        stem = token.get("stem")
        original = token.get("original")

        word = stem or original

        if word:
            words.append(
                str(word).strip().lower()
            )

    return words


# ---------------------------------------------------------------------------
# WORD CHAIN
# ---------------------------------------------------------------------------

class WordChain:

    def __init__(
        self,
        memory: Optional[MemoryGrid] = None,
    ):
        self.memory = memory or memory_grid

        # ---------------------------------------------------------------
        # GLOBAL WORD COUNTS
        # ---------------------------------------------------------------

        self.word_frequency: Counter = Counter()

        # ---------------------------------------------------------------
        # ADJACENT TRANSITIONS
        # ---------------------------------------------------------------

        self.transitions: Dict[
            str,
            Counter
        ] = defaultdict(Counter)

        # ---------------------------------------------------------------
        # WORD PAIRS
        # ---------------------------------------------------------------

        self.pairs: Counter = Counter()

        # ---------------------------------------------------------------
        # PHRASE CHAINS
        # ---------------------------------------------------------------

        self.phrase_chains: Dict[
            str,
            Counter
        ] = defaultdict(Counter)

        # ---------------------------------------------------------------
        # SOURCE STATISTICS
        # ---------------------------------------------------------------

        self.source_statistics: Dict[
            str,
            Counter
        ] = defaultdict(Counter)

        # ---------------------------------------------------------------
        # LANGUAGE STATISTICS
        # ---------------------------------------------------------------

        self.language_statistics: Dict[
            str,
            Counter
        ] = defaultdict(Counter)

        # ---------------------------------------------------------------
        # SOURCE-SPECIFIC CHAINS
        # ---------------------------------------------------------------

        self.source_chains: Dict[
            str,
            Dict[str, Any]
        ] = defaultdict(
            lambda: {
                "words": Counter(),
                "pairs": Counter(),
                "transitions": defaultdict(Counter),
                "phrases": defaultdict(Counter),
                "relationship_classes": Counter(),
                "languages": Counter(),
            }
        )

    # -------------------------------------------------------------------
    # SOURCE NORMALIZATION
    # -------------------------------------------------------------------

    @staticmethod
    def normalize_source(
        source: str,
    ) -> str:

        if not source:
            return "conversation"

        source = str(
            source
        ).strip().lower()

        allowed = {
            "personal",
            "workspace",
            "project",
            "conversation",
            "external",
            "dictionary",
            "ebook",
            "library",
            "crawler",
            "webcrawler",
            "gridcrawler",
            "ai_output",
            "ai_input",
        }

        return (
            source
            if source in allowed
            else "conversation"
        )

    # -------------------------------------------------------------------
    # ADD TEXT
    # -------------------------------------------------------------------

    def add_text(
        self,
        text: str,
        source: str = "conversation",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not text:
            return {
                "words_added": 0,
                "pairs_added": 0,
                "source": self.normalize_source(
                    source
                ),
            }

        source = self.normalize_source(
            source
        )

        lang = normalize_lang(
            language or detect_lang(text)
        )

        # ---------------------------------------------------------------
        # TOKENIZER IS THE PRIMARY LINGUISTIC INPUT
        # ---------------------------------------------------------------

        words = linguistic_words(
            text,
            lang,
        )

        # Compatibility fallback.
        if not words:
            words = clean_words(text)

        if not words:
            return {
                "words_added": 0,
                "pairs_added": 0,
                "source": source,
                "language": lang,
            }

        # ---------------------------------------------------------------
        # WORD FREQUENCY
        # ---------------------------------------------------------------

        for word in words:

            self.word_frequency[word] += 1

            self.source_chains[
                source
            ]["words"][word] += 1

        # ---------------------------------------------------------------
        # ALPHABET MATRIX
        # ---------------------------------------------------------------

        relationship_classes = []

        for word in words:

            try:

                classes = (
                    get_word_relationship_classes(
                        word
                    )
                )

                relationship_classes.extend(
                    classes
                )

                for class_id in classes:

                    self.source_chains[
                        source
                    ]["relationship_classes"][
                        str(class_id)
                    ] += 1

            except Exception:
                continue

        # ---------------------------------------------------------------
        # LANGUAGE STATISTICS
        # ---------------------------------------------------------------

        self.language_statistics[
            lang
        ]["words"] += len(words)

        self.source_chains[
            source
        ]["languages"][lang] += 1

        # ---------------------------------------------------------------
        # ADJACENT WORD RELATIONSHIPS
        # ---------------------------------------------------------------

        for i in range(
            len(words) - 1
        ):

            current_word = words[i]
            next_word = words[i + 1]

            pair = (
                f"{current_word}_{next_word}"
            )

            self.pairs[pair] += 1

            self.source_chains[
                source
            ]["pairs"][pair] += 1

            self.transitions[
                current_word
            ][next_word] += 1

            self.source_chains[
                source
            ]["transitions"][
                current_word
            ][next_word] += 1

        # ---------------------------------------------------------------
        # THREE-WORD PHRASE CHAINS
        # ---------------------------------------------------------------

        for i in range(
            len(words) - 2
        ):

            phrase = (
                f"{words[i]}_{words[i + 1]}"
            )

            next_word = words[i + 2]

            self.phrase_chains[
                phrase
            ][next_word] += 1

            self.source_chains[
                source
            ]["phrases"][
                phrase
            ][next_word] += 1

        # ---------------------------------------------------------------
        # SOURCE STATISTICS
        # ---------------------------------------------------------------

        self.source_statistics[
            source
        ]["documents"] += 1

        self.source_statistics[
            source
        ]["words"] += len(words)

        self.source_statistics[
            source
        ]["pairs"] += max(
            0,
            len(words) - 1,
        )

        return {
            "words_added": len(words),
            "pairs_added": max(
                0,
                len(words) - 1,
            ),
            "source": source,
            "language": lang,
            "relationship_classes": sorted(
                set(relationship_classes)
            ),
        }

    # -------------------------------------------------------------------
    # MEMORY GRID INGESTION
    # -------------------------------------------------------------------

    def add_memory(
        self,
        memory_record: Any,
        source: str = "personal",
    ) -> Dict[str, Any]:
        """
        Consume a memory record retrieved from MemoryGrid.

        Supports dictionaries and plain text records.
        """

        if memory_record is None:
            return {
                "words_added": 0,
                "source": source,
            }

        if isinstance(
            memory_record,
            str,
        ):

            return self.add_text(
                memory_record,
                source=source,
            )

        if isinstance(
            memory_record,
            dict,
        ):

            content = (
                memory_record.get("content")
                or memory_record.get("text")
                or memory_record.get("data")
                or ""
            )

            record_source = (
                memory_record.get("source")
                or source
            )

            language = (
                memory_record.get("language")
            )

            return self.add_text(
                str(content),
                source=record_source,
                language=language,
                metadata=memory_record,
            )

        return {
            "words_added": 0,
            "source": source,
        }

    # -------------------------------------------------------------------
    # MEMORY GRID BATCH INGESTION
    # -------------------------------------------------------------------

    def add_memory_records(
        self,
        records: Iterable[Any],
        source: str = "personal",
    ) -> Dict[str, Any]:

        documents = 0
        words = 0
        pairs = 0

        for record in records:

            result = self.add_memory(
                record,
                source=source,
            )

            documents += 1
            words += result.get(
                "words_added",
                0,
            )
            pairs += result.get(
                "pairs_added",
                0,
            )

        return {
            "documents_added": documents,
            "words_added": words,
            "pairs_added": pairs,
            "source": self.normalize_source(
                source
            ),
        }

    # -------------------------------------------------------------------
    # RANK MEMORY
    # -------------------------------------------------------------------

    def rank_memory(
        self,
        query: str,
        candidates: Iterable[Any],
        query_entities: Optional[
            List[str]
        ] = None,
        query_hierarchy: Optional[
            str
        ] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank MemoryGrid candidates through ranking.py.

        WordChain does not replace ranking.

        Ranking determines relevance first.
        WordChain then constructs relationships from the strongest
        retrieved knowledge.
        """

        ranked = []

        lang = normalize_lang(
            language or detect_lang(query)
        )

        for candidate in candidates:

            if isinstance(
                candidate,
                str,
            ):

                candidate_text = candidate
                metadata = {}

            elif isinstance(
                candidate,
                dict,
            ):

                candidate_text = (
                    candidate.get("content")
                    or candidate.get("text")
                    or candidate.get("data")
                    or ""
                )

                metadata = candidate

            else:
                continue

            if not candidate_text:
                continue

            result = score_candidate(
                query=query,
                candidate_text=str(
                    candidate_text
                ),
                candidate_entities=metadata.get(
                    "entities"
                ),
                candidate_hierarchy=metadata.get(
                    "hierarchy"
                ),
                query_entities=query_entities,
                query_hierarchy=query_hierarchy,
                freshness_score=metadata.get(
                    "freshness_score",
                    0.0,
                ),
                lang=lang,
            )

            ranked.append({
                "content": candidate_text,
                "metadata": metadata,
                "ranking": result,
            })

        ranked.sort(
            key=lambda item:
                item["ranking"]["total"],
            reverse=True,
        )

        return ranked

    # -------------------------------------------------------------------
    # RETRIEVE → RANK → BUILD
    # -------------------------------------------------------------------

    def build_from_ranked_memory(
        self,
        query: str,
        candidates: Iterable[Any],
        source: str = "personal",
        limit: int = 20,
        query_entities: Optional[
            List[str]
        ] = None,
        query_hierarchy: Optional[
            str
        ] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main retrieval construction pipeline.

            MemoryGrid
                 ↓
            candidates
                 ↓
             ranking
                 ↓
             WordChain
        """

        ranked = self.rank_memory(
            query=query,
            candidates=candidates,
            query_entities=query_entities,
            query_hierarchy=query_hierarchy,
            language=language,
        )

        selected = ranked[:limit]

        ingestion = []

        for item in selected:

            result = self.add_text(
                item["content"],
                source=source,
                metadata=item["metadata"],
                language=language,
            )

            ingestion.append({
                "ranking": item["ranking"],
                "ingestion": result,
            })

        return {
            "query": query,
            "ranked": selected,
            "ingestion": ingestion,
            "count": len(selected),
        }

    # -------------------------------------------------------------------
    # NEXT WORD
    # -------------------------------------------------------------------

    def next_words(
        self,
        word: str,
        limit: int = 5,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        if not word:
            return []

        word = str(
            word
        ).lower().strip()

        if source:

            source = self.normalize_source(
                source
            )

            counter = (
                self.source_chains[
                    source
                ]["transitions"].get(
                    word,
                    Counter(),
                )
            )

        else:

            counter = self.transitions.get(
                word,
                Counter(),
            )

        results = []

        total = sum(
            counter.values()
        )

        for next_word, count in (
            counter.most_common(limit)
        ):

            results.append({
                "word": next_word,
                "after": word,
                "count": count,
                "probability": self._probability(
                    count,
                    total,
                ),
                "source": source,
            })

        return result

# -------------------------------------------------------------------
    # PHRASE CONTINUATION
    # -------------------------------------------------------------------

    def next_words_from_phrase(
        self,
        phrase: str,
        limit: int = 5,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        words = linguistic_words(
            phrase
        )

        if len(words) < 2:
            words = clean_words(
                phrase
            )

        if len(words) < 2:
            return []

        key = (
            f"{words[-2]}_{words[-1]}"
        )

        if source:

            source = self.normalize_source(
                source
            )

            counter = (
                self.source_chains[
                    source
                ]["phrases"].get(
                    key,
                    Counter(),
                )
            )

        else:

            counter = (
                self.phrase_chains.get(
                    key,
                    Counter(),
                )
            )

        total = sum(
            counter.values()
        )

        return [
            {
                "word": next_word,
                "after_phrase": key,
                "count": count,
                "probability": self._probability(
                    count,
                    total,
                ),
                "source": source,
            }
            for next_word, count
            in counter.most_common(limit)
        ]

    # -------------------------------------------------------------------
    # ALPHABET MATRIX SIGNAL
    # -------------------------------------------------------------------

    def alphabet_relationship(
        self,
        word: str,
    ) -> Dict[str, Any]:
        """
        Return the relationship-matrix representation of a word.
        """

        try:

            return {
                "word": word,
                "relationships": (
                    get_word_relationships(
                        word
                    )
                ),
                "classes": (
                    get_word_relationship_classes(
                        word
                    )
                ),
                "signature": (
                    relationship_signature(
                        word
                    )
                ),
            }

        except Exception:

            return {
                "word": word,
                "relationships": [],
                "classes": [],
                "signature": (),
            }

    # -------------------------------------------------------------------
    # WORD RELATIONSHIP
    # -------------------------------------------------------------------

    def relationship_between_words(
        self,
        word_a: str,
        word_b: str,
    ) -> float:

        try:

            return relationship_score(
                word_a,
                word_b,
            )

        except Exception:

            return 0.0

    # -------------------------------------------------------------------
    # PREDICT FROM TEXT
    # -------------------------------------------------------------------

    def predict_from_text(
        self,
        text: str,
        limit: int = 5,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        words = linguistic_words(text)

        if not words:
            words = clean_words(text)

        if not words:
            return []

        if len(words) >= 2:

            results = (
                self.next_words_from_phrase(
                    f"{words[-2]} {words[-1]}",
                    limit=limit,
                    source=source,
                )
            )

            if results:
                return results

        return self.next_words(
            words[-1],
            limit=limit,
            source=source,
        )

    # -------------------------------------------------------------------
    # PHRASE CONTINUITY
    # -------------------------------------------------------------------

    def phrase_continuity(
        self,
        query: str,
        candidate_text: str,
    ) -> float:

        query_words = linguistic_words(
            query
        )

        candidate_words = linguistic_words(
            candidate_text
        )

        if not query_words:
            query_words = clean_words(
                query
            )

        if not candidate_words:
            candidate_words = clean_words(
                candidate_text
            )

        if not query_words or not candidate_words:
            return 0.0

        longest = 0

        for start in range(
            len(query_words)
        ):

            for candidate_start in range(
                len(candidate_words)
            ):

                current = 0

                while (
                    start + current
                    < len(query_words)
                    and
                    candidate_start + current
                    < len(candidate_words)
                    and
                    query_words[
                        start + current
                    ]
                    ==
                    candidate_words[
                        candidate_start + current
                    ]
                ):
                    current += 1

                longest = max(
                    longest,
                    current,
                )

        return (
            longest
            / len(query_words)
        ) * 100.0

    # -------------------------------------------------------------------
    # WORD PAIR OVERLAP
    # -------------------------------------------------------------------

    def pair_overlap(
        self,
        query: str,
        candidate_text: str,
    ) -> float:

        query_words = linguistic_words(
            query
        )

        candidate_words = linguistic_words(
            candidate_text
        )

        if len(query_words) < 2:
            query_words = clean_words(
                query
            )

        if len(candidate_words) < 2:
            candidate_words = clean_words(
                candidate_text
            )

        if len(query_words) < 2:
            return 0.0

        query_pairs = {
            f"{query_words[i]}_{query_words[i + 1]}"
            for i in range(
                len(query_words) - 1
            )
        }

        candidate_pairs = {
            f"{candidate_words[i]}_{candidate_words[i + 1]}"
            for i in range(
                len(candidate_words) - 1
            )
        }

        if not query_pairs:
            return 0.0

        matched = len(
            query_pairs
            & candidate_pairs
        )

        return (
            matched
            / len(query_pairs)
        ) * 100.0

    # -------------------------------------------------------------------
    # SOURCE COMPARISON
    # -------------------------------------------------------------------

    def compare_sources(
        self,
        word: str,
        limit: int = 5,
    ) -> Dict[str, Any]:

        result = {}

        for source in (
            self.source_chains.keys()
        ):

            result[source] = (
                self.next_words(
                    word,
                    limit=limit,
                    source=source,
                )
            )

        return result

    # -------------------------------------------------------------------
    # KNOWLEDGE PROFILE
    # -------------------------------------------------------------------

    def knowledge_profile(
        self,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:

        if source:

            source = self.normalize_source(
                source
            )

            chain = (
                self.source_chains[
                    source
                ]
            )

            return {
                "source": source,
                "unique_words": len(
                    chain["words"]
                ),
                "unique_pairs": len(
                    chain["pairs"]
                ),
                "unique_transitions": len(
                    chain["transitions"]
                ),
                "documents": (
                    self.source_statistics[
                        source
                    ]["documents"]
                ),
                "words": (
                    self.source_statistics[
                        source
                    ]["words"]
                ),
                "pairs": (
                    self.source_statistics[
                        source
                    ]["pairs"]
                ),
                "languages": dict(
                    chain["languages"]
                ),
                "relationship_classes": dict(
                    chain[
                        "relationship_classes"
                    ]
                ),
            }

        return {
            "unique_words": len(
                self.word_frequency
            ),
            "unique_pairs": len(
                self.pairs
            ),
            "unique_transitions": len(
                self.transitions
            ),
            "languages": {
                language: dict(
                    stats
                )
                for language, stats
                in self.language_statistics.items()
            },
            "sources": {
                source: dict(stats)
                for source, stats
                in self.source_statistics.items()
            },
        }

    # -------------------------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------------------------

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        source_chains = {}

        for source, chain in (
            self.source_chains.items()
        ):

            source_chains[source] = {
                "words": dict(
                    chain["words"]
                ),
                "pairs": dict(
                    chain["pairs"]
                ),
                "transitions": {
                    word: dict(counter)
                    for word, counter
                    in chain[
                        "transitions"
                    ].items()
                },
                "phrases": {
                    phrase: dict(counter)
                    for phrase, counter
                    in chain[
                        "phrases"
                    ].items()
                },
                "relationship_classes": dict(
                    chain[
                        "relationship_classes"
                    ]
                ),
                "languages": dict(
                    chain["languages"]
                ),
            }

        return {
            "word_frequency": dict(
                self.word_frequency
            ),
            "pairs": dict(
                self.pairs
            ),
            "transitions": {
                word: dict(counter)
                for word, counter
                in self.transitions.items()
            },
            "phrase_chains": {
                phrase: dict(counter)
                for phrase, counter
                in self.phrase_chains.items()
            },
            "source_statistics": {
                source: dict(stats)
                for source, stats
                in self.source_statistics.items()
            },
            "language_statistics": {
                language: dict(stats)
                for language, stats
                in self.language_statistics.items()
            },
            "source_chains": source_chains,
        }

    # -------------------------------------------------------------------
    # DESERIALIZATION
    # -------------------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "WordChain":

        chain = cls()

        chain.word_frequency.update(
            data.get(
                "word_frequency",
                {},
            )
        )

        chain.pairs.update(
            data.get(
                "pairs",
                {},
            )
        )

        for word, values in data.get(
            "transitions",
            {},
        ).items():

            chain.transitions[
                word
            ].update(values)

        for phrase, values in data.get(
            "phrase_chains",
            {},
        ).items():

            chain.phrase_chains[
                phrase
            ].update(values)

        for source, values in data.get(
            "source_statistics",
            {},
        ).items():

            chain.source_statistics[
                source
            ].update(values)

        for language, values in data.get(
            "language_statistics",
            {},
        ).items():

            chain.language_statistics[
                language
            ].update(values)

        for source, values in data.get(
            "source_chains",
            {},
        ).items():

            source_chain = (
                chain.source_chains[
                    source
                ]
            )

            source_chain[
                "words"
            ].update(
                values.get(
                    "words",
                    {},
                )
            )

            source_chain[
                "pairs"
            ].update(
                values.get(
                    "pairs",
                    {},
                )
            )

            for word, transitions in (
                values.get(
                    "transitions",
                    {},
                ).items()
            ):

                source_chain[
                    "transitions"
                ][word].update(
                    transitions
                )

            for phrase, transitions in (
                values.get(
                    "phrases",
                    {},
                ).items()
            ):

                source_chain[
                    "phrases"
                ][phrase].update(
                    transitions
                )

            source_chain[
                "relationship_classes"
            ].update(
                values.get(
                    "relationship_classes",
                    {},
                )
            )

            source_chain[
                "languages"
            ].update(
                values.get(
                    "languages",
                    {},
                )
            )

        return chain

    # -------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------

    def save(
        self,
        path: str,
    ) -> None:

        directory = os.path.dirname(
            path
        )

        if directory:
            os.makedirs(
                directory,
                exist_ok=True,
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                self.to_dict(),
                f,
                ensure_ascii=False,
                indent=2,
            )

    # -------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: str,
    ) -> "WordChain":

        if not os.path.exists(path):
            return cls()

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        return cls.from_dict(data)

    # -------------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------------

    @staticmethod
    def _probability(
        count: int,
        total: int,
    ) -> float:

        if total <= 0:
            return 0.0

        return count / total


# ---------------------------------------------------------------------------
# DEFAULT FACTORY
# ---------------------------------------------------------------------------

def create_word_chain(
    path: Optional[str] = None,
    memory: Optional[MemoryGrid] = None,
) -> WordChain:

    if path:
        chain = WordChain.load(path)
        chain.memory = memory or memory_grid
        return chain

    return WordChain(
        memory=memory
    )


# ---------------------------------------------------------------------------
# COMPATIBILITY HELPERS
# ---------------------------------------------------------------------------

def extract_word_pairs(
    text: str,
) -> List[str]:

    words = linguistic_words(text)

    if not words:
        words = clean_words(text)

    return [
        f"{words[i]}_{words[i + 1]}"
        for i in range(
            len(words) - 1
        )
    ]


def extract_next_word_candidates(
    text: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:

    chain = WordChain()

    chain.add_text(
        text,
        source="conversation",
    )

    results = []

    words = linguistic_words(text)

    if not words:
        words = clean_words(text)

    for word in words:

        candidates = chain.next_words(
            word,
            limit=limit,
        )

        results.extend(
            candidates
        )

    seen = set()
    unique = []

    for result in sorted(
        results,
        key=lambda x: x["count"],
        reverse=True,
    ):

        key = (
            result["after"],
            result["word"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(result)

        if len(unique) >= limit:
            break

    return unique


# ---------------------------------------------------------------------------
# TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    chain = WordChain()

    chain.add_text(
        "My project uses GSP for deterministic storage.",
        source="project",
    )

    chain.add_text(
        "GSP provides deterministic storage for the project.",
        source="project",
    )

    chain.add_text(
        "A deterministic system produces the same result for the same input.",
        source="dictionary",
    )

    print(
        "Detected language:"
    )

    print(
        detect_lang(
            "My project uses GSP."
        )
    )

    print(
        "\nProject continuation:"
    )

    print(
        chain.next_words(
            "gsp",
            limit=5,
            source="project",
        )
    )

    print(
        "\nAlphabet relationship:"
    )

    print(
        chain.alphabet_relationship(
            "deterministic"
        )
    )

    print(
        "\nPhrase continuation:"
    )

    print(
        chain.next_words_from_phrase(
            "deterministic storage",
            limit=5,
        )
    )

    print(
        "\nKnowledge profile:"
    )

    print(
        chain.knowledge_profile()
    )