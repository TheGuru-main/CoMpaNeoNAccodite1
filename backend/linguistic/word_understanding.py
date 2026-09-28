"""
Word Understanding Module
=========================

CoMpaNeoN Word Understanding Layer.

Architecture:

    MemoryGrid
        │
        ▼
    GridCrawler
        │
        ▼
    Retrieval Routes
        │
        ├── Letter Grid
        ├── Word Grid
        └── Storage Grid
        │
        ▼
    Ranking
        │
        ▼
    WordChain
        │
        ▼
    WordUnderstanding
        │
        └── structured understanding
                │
                ▼
        later: neutrals / prompts / AI model


Responsibilities:
- Retrieve knowledge from MemoryGrid.
- Preserve the three retrieval routes.
- Rank retrieved candidate documents.
- Feed ranked knowledge into WordChain.
- Use WordChain to establish word relationships and continuations.
- Use tokenizer.py for linguistic tokenization.
- Use alphabet-matrix relationships through WordChain.
- Detect language dynamically.
- Attach symbols, directives and domain metadata.
- Produce a structured understanding object.

Important:

UNDERSTANDING != RESPONSE

WordUnderstanding does not generate the final AI response.

Memory ownership remains with MemoryGrid.

Word relationships remain in WordChain.

Ranking remains in ranking.py.

Deep linguistic tokenization remains in tokenizer.py.

The AI model remains separate.
"""

from __future__ import annotations

import hashlib
from typing import (
    List,
    Dict,
    Any,
    Optional,
)

from langdetect import detect, LangDetectException

from tokenizer import (
    tokenize,
    normalize_lang,
    letter_score,
    word_score,
)

from memory_grid import MemoryGrid

from symbols import recognize_symbols
from code_languages import CODE_TERMS
from directives import detect_directive

from page_cache import PageCache
from memory_cache import MemoryCache

from ranking import score_candidate
from intent_analyzer import detect_domain

from word_chain import WordChain


# =====================================================================
# LANGUAGE DETECTION
# =====================================================================

def detect_lang(text: str) -> str:
    """
    Detect the language of a query or memory document.

    normalize_lang() is applied afterward so tokenizer.py remains
    the canonical language normalization layer.
    """

    try:
        if not text or not str(text).strip():
            return "en"

        detected = detect(
            str(text)
        )

        return normalize_lang(
            detected
        )

    except (
        LangDetectException,
        Exception,
    ):
        return "en"


# =====================================================================
# WORD UNDERSTANDING
# =====================================================================

class WordUnderstanding:
    """
    CoMpaNeoN Word Understanding Layer.

    Retrieval and understanding are deliberately separated.

    Retrieval:

        MemoryGrid
            ↓
        Letter / Word / Storage
            ↓
        Candidate documents
            ↓
        Ranking

    Linguistic relationship:

        Ranked knowledge
            ↓
        WordChain
            ↓
        word relationships
            ↓
        continuation
            ↓
        understanding

    WordUnderstanding therefore acts as the bridge between
    retrieved/ranked memory and higher-level reasoning.
    """

    # =================================================================
    # INITIALIZATION
    # =================================================================

    def __init__(
        self,
        memory_grid: MemoryGrid,
        word_chain: Optional[WordChain] = None,
    ):
        self.memory = memory_grid

        # -------------------------------------------------------------
        # Local caches
        # -------------------------------------------------------------

        self.page_cache = PageCache()
        self.memory_cache = MemoryCache()

        # -------------------------------------------------------------
        # Word relationship engine
        #
        # Can be supplied by the application so that the same
        # WordChain can persist across sessions.
        # -------------------------------------------------------------

        self.word_chain = (
            word_chain
            if word_chain is not None
            else WordChain()
        )

    # =================================================================
    # HASH
    # =================================================================

    def _hash(
        self,
        text: str,
    ) -> str:
        """
        Produce a deterministic hash for text.
        """

        return hashlib.sha256(
            str(text).encode(
                "utf-8"
            )
        ).hexdigest()

    # =================================================================
    # LANGUAGE
    # =================================================================

    def _resolve_language(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> str:
        """
        Resolve language.

        Explicit language wins.

        Otherwise langdetect determines the language.
        tokenizer.py then normalizes it.
        """

        if lang:
            return normalize_lang(
                lang
            )

        return detect_lang(
            text
        )

    # =================================================================
    # LETTER ROUTE
    # =================================================================

    def _retrieve_letter_route(
        self,
        token: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candidates through the Letter Grid.
        """

        results: List[
            Dict[str, Any]
        ] = []

        seen = set()

        letters = token.get(
            "letter",
            [],
        ) or []

        for letter_index in letters:

            entries = (
                self.memory.get_tokens_at_letter(
                    letter_index
                )
            )

            for entry in entries:

                key = (
                    entry.get("doc_id"),
                    entry.get("original"),
                )

                if key in seen:
                    continue

                seen.add(key)

                result = dict(
                    entry
                )

                result[
                    "retrieval_route"
                ] = "letter"

                results.append(
                    result
                )

        return results

    # =================================================================
    # WORD ROUTE
    # =================================================================

    def _retrieve_word_route(
        self,
        token: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Retrieve a complete word through the Word Grid.

        tokenizer.py remains responsible for producing the word
        coordinate.
        """

        word = token.get(
            "word"
        )

        if not word:
            return []

        row = int(
            word.get(
                "row",
                0,
            )
        )

        col = int(
            word.get(
                "col",
                0,
            )
        )

        entries = (
            self.memory.get_tokens_at_word(
                row,
                col,
            )
        )

        results: List[
            Dict[str, Any]
        ] = []

        for entry in entries:

            result = dict(
                entry
            )

            result[
                "retrieval_route"
            ] = "word"

            results.append(
                result
            )

        return results

    # =================================================================
    # STORAGE ROUTE
    # =================================================================

    def _retrieve_storage_route(
        self,
        token: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve through MemoryGrid's independent storage route.

        WordUnderstanding does not recreate MemoryGrid's placement
        formula.
        """

        routes = (
            self.memory.retrieve_by_token(
                token
            )
        )

        entries = routes.get(
            "storage",
            [],
        )

        results: List[
            Dict[str, Any]
        ] = []

        for entry in entries[:limit]:

            result = dict(
                entry
            )

            result[
                "retrieval_route"
            ] = "storage"

            results.append(
                result
            )

        return results

    # =================================================================
    # THREE ROUTE RETRIEVAL
    # =================================================================

    def _retrieve_three_routes(
        self,
        query: str,
        lang: str,
        limit: int,
    ) -> Dict[
        str,
        List[Dict[str, Any]]
    ]:
        """
        Enter a query through all MemoryGrid retrieval routes.
        """

        tokens = tokenize(
            query,
            lang,
        )

        routes = {
            "letter": [],
            "word": [],
            "storage": [],
        }

        seen = {
            "letter": set(),
            "word": set(),
            "storage": set(),
        }

        for token in tokens:

            # ---------------------------------------------------------
            # Letter Grid
            # ---------------------------------------------------------

            letter_results = (
                self._retrieve_letter_route(
                    token
                )
            )

            for result in letter_results:

                key = (
                    result.get("doc_id"),
                    result.get("original"),
                )

                if key in seen["letter"]:
                    continue

                seen["letter"].add(
                    key
                )

                routes[
                    "letter"
                ].append(
                    result
                )

            # ---------------------------------------------------------
            # Word Grid
            # ---------------------------------------------------------

            word_results = (
                self._retrieve_word_route(
                    token
                )
            )

            for result in word_results:

                key = (
                    result.get("doc_id"),
                    result.get("original"),
                )

                if key in seen["word"]:
                    continue

                seen["word"].add(
                    key
                )

                routes[
                    "word"
                ].append(
                    result
                )

            # ---------------------------------------------------------
            # Storage Grid
            # ---------------------------------------------------------

            storage_results = (
                self._retrieve_storage_route(
                    token,
                    limit,
                )
            )

            for result in storage_results:

                key = (
                    result.get("doc_id"),
                    result.get("original"),
                )

                if key in seen["storage"]:
                    continue

                seen["storage"].add(
                    key
                )

                routes[
                    "storage"
                ].append(
                    result
                )

        return routes

    # =================================================================
    # DOCUMENT COLLECTION
    # =================================================================

    def _collect_candidate_documents(
        self,
        routes: Dict[
            str,
            List[Dict[str, Any]]
        ],
    ) -> Dict[
        Any,
        Dict[str, Any]
    ]:
        """
        Convert token-level route results into unique documents.

        Multiple routes may discover the same document.
        """

        candidate_docs: Dict[
            Any,
            Dict[str, Any]
        ] = {}

        for route_name in (
            "letter",
            "word",
            "storage",
        ):

            for result in routes.get(
                route_name,
                [],
            ):

                doc_id = result.get(
                    "doc_id"
                )

                if doc_id is None:
                    continue

                if doc_id not in candidate_docs:

                    doc_text = (
                        self.memory.get_doc(
                            doc_id
                        )
                    )

                    if not doc_text:
                        continue

                    candidate_docs[
                        doc_id
                    ] = {
                        "doc_id": doc_id,
                        "text": doc_text,
                        "routes": set(),
                    }

                candidate_docs[
                    doc_id
                ][
                    "routes"
                ].add(
                    route_name
                )

        return candidate_docs

    # =================================================================
    # WORDCHAIN INGESTION
    # =================================================================

    def _feed_word_chain(
        self,
        text: str,
        source: str = "conversation",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Feed retrieved knowledge into WordChain.

        WordChain does not replace MemoryGrid.

        It builds linguistic relationships from knowledge that has
        already been retrieved or supplied by the system.
        """

        if not text:
            return {
                "words_added": 0,
                "pairs_added": 0,
                "source": source,
            }

        return self.word_chain.add_text(
            text=text,
            source=source,
            metadata=metadata,
        )

    # =================================================================
    # FEED RANKED DOCUMENTS
    # =================================================================

    def _feed_ranked_documents(
        self,
        ranked: List[
            Dict[str, Any]
        ],
    ) -> None:
        """
        Feed ranked documents into WordChain.

        Ranking determines which retrieved knowledge is important
        enough to enter the immediate relationship-building stage.

        Higher-ranked knowledge therefore has priority over lower-ranked
        candidates.
        """

        for item in ranked:

            text = item.get(
                "text",
                "",
            )

            if not text:
                continue

            # ---------------------------------------------------------
            # Preserve source information when available.
            # ---------------------------------------------------------

            source = item.get(
                "source",
                "conversation",
            )

            self._feed_word_chain(
                text=text,
                source=source,
                metadata={
                    "doc_id": item.get(
                        "doc_id"
                    ),
                    "ranking_score": item.get(
                        "score",
                        0.0,
                    ),
                    "routes": item.get(
                        "routes",
                        [],
                    ),
                },
            )

    # =================================================================
    # WORDCHAIN QUERY
    # =================================================================

    def _query_word_chain(
        self,
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Ask WordChain for the linguistic relationships surrounding
        the query.

        Two-word phrase continuation is preferred internally by
        WordChain.
        """

        predictions = (
            self.word_chain.predict_from_text(
                query,
                limit=limit,
            )
        )

        pairs = (
            self.word_chain.get_pairs(
                word=(
                    query.split()[-1]
                    if query.split()
                    else None
                ),
                limit=limit,
            )
        )

        profile = (
            self.word_chain.knowledge_profile()
        )

        return {
            "predictions": predictions,
            "pairs": pairs,
            "profile": profile,
        }

    # =================================================================
    # CONTEXT RETRIEVAL
    # =================================================================

    def get_context(
        self,
        query: str,
        lang: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        Retrieve, rank and relationship-process contextual knowledge.

        Flow:

            Query
              │
              ├── Letter Grid
              ├── Word Grid
              └── Storage Grid
                       │
                       ▼
                Candidate Documents
                       │
                       ▼
                    Ranking
                       │
                       ▼
                   WordChain
                       │
                       ▼
                    Context
        """

        cached = self.memory_cache.get(
            query
        )

        if cached:
            return cached

        lang = self._resolve_language(
            query,
            lang,
        )

        tokens = tokenize(
            query,
            lang,
        )

        if not tokens:
            return ""

        directive = detect_directive(
            query
        )

        crawl_limit = limit

        if directive in {
            "entity_identity",
            "location",
        }:
            crawl_limit = limit + 2

        # -------------------------------------------------------------
        # RETRIEVE
        # -------------------------------------------------------------

        routes = (
            self._retrieve_three_routes(
                query=query,
                lang=lang,
                limit=crawl_limit,
            )
        )

        # -------------------------------------------------------------
        # COLLECT
        # -------------------------------------------------------------

        candidate_docs = (
            self._collect_candidate_documents(
                routes
            )
        )

        if not candidate_docs:

            self.memory_cache.set(
                query,
                "",
            )

            return ""

        # -------------------------------------------------------------
        # DOMAIN
        # -------------------------------------------------------------

        domain = detect_domain(
            query
        )

        # -------------------------------------------------------------
        # RANK
        # -------------------------------------------------------------

        ranked: List[
            Dict[str, Any]
        ] = []

        for doc in candidate_docs.values():

            route_names = sorted(
                doc.get(
                    "routes",
                    set(),
                )
            )

            score_result = score_candidate(
                query=query,
                candidate_text=doc["text"],
                query_entities=[],
                query_hierarchy=domain,
                candidate_entities=[],
                candidate_hierarchy=domain,
                freshness_score=0.0,
                lang=lang,
            )

            ranked.append({
                "doc_id": doc["doc_id"],
                "text": doc["text"],
                "score": score_result[
                    "total"
                ],
                "scores": score_result[
                    "scores"
                ],
                "routes": route_names,
            })

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        # -------------------------------------------------------------
        # WORDCHAIN
        # -------------------------------------------------------------

        self._feed_ranked_documents(
            ranked[:10]
        )

        word_chain_result = (
            self._query_word_chain(
                query=query,
                limit=5,
            )
        )

        # -------------------------------------------------------------
        # CONTEXT
        # -------------------------------------------------------------

        context = "\n".join(
            item["text"]
            for item in ranked[:3]
        )

        # -------------------------------------------------------------
        # ENRICHMENT
        # -------------------------------------------------------------

        enrichment = (
            self._build_enrichment(
                query=query,
                domain=domain,
            )
        )

        # -------------------------------------------------------------
        # RETURN
        # -------------------------------------------------------------

        return {
            "query": query,

            "context": context,

            "tokens": tokens,

            "routes": routes,

            "ranked_documents": ranked[:10],

            "word_chain": {
                "predictions": word_chain_result[
                    "predictions"
                ],
                "pairs": word_chain_result[
                    "pairs"
                ],
                "profile": word_chain_result[
                    "profile"
                ],
            },

            "symbols": enrichment[
                "symbols"
            ],

            "code_terms": enrichment[
                "code_terms"
            ],

            "directive": directive,

            "domain": domain,

            "language": lang,
        }


# =====================================================================
# FACTORY
# =====================================================================

def create_word_understanding(
    memory_grid: MemoryGrid,
    word_chain: Optional[WordChain] = None,
) -> WordUnderstanding:
    """
    Create a WordUnderstanding instance.

    A persistent WordChain can be supplied by the application so that
    personal or organization-specific linguistic knowledge remains
    available across sessions.
    """

    return WordUnderstanding(
        memory_grid=memory_grid,
        word_chain=word_chain,
    )