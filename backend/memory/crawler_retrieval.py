"""
CoMpaNeoN Crawler Retrieval Layer
==================================

Retrieval orchestration layer between the MemoryGrid and the
higher-level understanding architecture.

Architecture
------------

Query
  ↓
Tokenizer
  ↓
Intent Analyzer
  ↓
Word / Letter entry points
  ↓
GridCrawler
  ↓
MemoryGrid
  ↓
Candidate documents
  ↓
Data Mixer
  ↓
Ranking
  ↓
WordChain
  ↓
WordUnderstanding


Responsibilities
----------------

CrawlerRetrieval:

    - tokenizes the query
    - obtains intent/domain analysis
    - resolves every query token to its Word Grid position
    - enters GridCrawler through every unique position
    - collects candidate documents
    - preserves retrieval provenance
    - attaches domain/entity metadata
    - sends candidates through DataMixer when available
    - ranks the resulting candidates
    - returns structured retrieval context

It does NOT:

    - calculate GSP storage placement
    - recreate MemoryGrid placement rules
    - crawl the external web
    - schedule external crawling
    - generate responses
    - generate prompts
    - replace WordChain
    - replace WordUnderstanding
    - replace Ranking
    - replace MemoryGrid


IMPORTANT
---------

There are three distinct concepts:

    Word Grid
        Query entry point.

    MemoryGrid
        Persistent knowledge storage.

    GridCrawler
        Traversal mechanism through MemoryGrid.

CrawlerRetrieval orchestrates these components.

It does not duplicate their mathematics.
"""

from __future__ import annotations

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from tokenizer import (
    tokenize,
    normalize_lang,
)

from grid_crawler import crawl as grid_crawl

from ranking import score_candidate

from intent_analyzer import (
    analyze,
    detect_domain,
)

from directives import detect_directive


# ----------------------------------------------------------------------
# Optional DataMixer
# ----------------------------------------------------------------------

try:
    from data_mixer import DataMixer
except ImportError:
    DataMixer = None


class CrawlerRetrieval:
    """
    MemoryGrid retrieval orchestrator.

    Parameters
    ----------
    memory_grid:
        Shared MemoryGrid instance.

    data_mixer:
        Optional DataMixer instance.

    ranking:
        Optional ranking implementation. By default the canonical
        ranking.score_candidate function is used.
    """

    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(
        self,
        memory_grid,
        data_mixer: Optional[Any] = None,
    ) -> None:

        self.memory = memory_grid

        # --------------------------------------------------------------
        # Data mixer
        # --------------------------------------------------------------

        if data_mixer is not None:

            self.data_mixer = data_mixer

        elif DataMixer is not None:

            try:
                self.data_mixer = DataMixer(
                    memory_grid
                )
            except TypeError:
                self.data_mixer = DataMixer()

        else:

            self.data_mixer = None

    # ==================================================================
    # TOKEN POSITION
    # ==================================================================

    def _token_position(
        self,
        token: Dict[str, Any],
    ) -> Tuple[int, int]:
        """
        Resolve a token's Word Grid position.

        The tokenizer remains the canonical authority for:

            L
            S
            word_S
            column

        CrawlerRetrieval only applies the MemoryGrid dimensions to
        the resulting coordinates.

        It does not invent a new placement system.
        """

        word = token.get(
            "word",
            {}
        ) or {}

        # --------------------------------------------------------------
        # Length
        # --------------------------------------------------------------

        L = int(
            word.get(
                "L",
                0,
            )
        )

        # --------------------------------------------------------------
        # Word S
        # --------------------------------------------------------------

        S = int(
            word.get(
                "word_S",
                word.get(
                    "S",
                    L,
                ),
            )
        )

        # --------------------------------------------------------------
        # Token column
        # --------------------------------------------------------------

        col = int(
            word.get(
                "col",
                0,
            )
        )

        # --------------------------------------------------------------
        # Memory dimensions
        # --------------------------------------------------------------

        rows = int(
            getattr(
                self.memory,
                "rows",
                64,
            )
        )

        cols = int(
            getattr(
                self.memory,
                "cols",
                26,
            )
        )

        rows = max(
            rows,
            1,
        )

        cols = max(
            cols,
            1,
        )

        # --------------------------------------------------------------
        # Word Grid → retrieval entry point
        # --------------------------------------------------------------

        row = (
            (L + S - 1)
            % rows
        ) + 1

        col = (
            col
            % cols
        )

        return row, col

    # ==================================================================
    # INTENT ANALYSIS
    # ==================================================================

    def _analyze_query(
        self,
        query: str,
        lang: str,
    ) -> Dict[str, Any]:
        """
        Run the unified intent/domain analysis layer.

        The preferred API is:

            intent_analyzer.analyze()

        A compatibility fallback to detect_domain() is retained so
        older deployments do not immediately break.
        """

        try:

            result = analyze(
                query,
                lang=lang,
            )

            if isinstance(
                result,
                dict,
            ):
                return result

        except (
            TypeError,
            AttributeError,
        ):

            pass

        # --------------------------------------------------------------
        # Compatibility fallback
        # --------------------------------------------------------------

        return {
            "domain": detect_domain(
                query
            ),
            "intent": "general",
            "entities": [],
            "language": lang,
        }

    # ==================================================================
    # QUERY POSITIONS
    # ==================================================================

    def _build_positions(
        self,
        tokens: List[
            Dict[str, Any]
        ],
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Build unique Word Grid entry points for every query token.

        Every token gets an opportunity to enter the grid.

        Duplicate coordinates are crawled only once.
        """

        positions: List[
            Dict[str, Any]
        ] = []

        seen_positions = set()

        for index, token in enumerate(
            tokens
        ):

            try:

                row, col = (
                    self._token_position(
                        token
                    )
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):

                continue

            position = (
                row,
                col,
            )

            if position in seen_positions:
                continue

            seen_positions.add(
                position
            )

            positions.append({
                "token_index": index,
                "token": token,
                "row": row,
                "col": col,
            })

        return positions

    # ==================================================================
    # GRID CRAWL
    # ==================================================================

    def _crawl_position(
        self,
        position: Dict[str, Any],
        limit: int,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Enter GridCrawler through one Word Grid position.
        """

        return grid_crawl(
            self.memory,
            position["row"],
            position["col"],
            limit=limit,
        )

    # ==================================================================
    # CANDIDATE COLLECTION
    # ==================================================================

    def _collect_candidates(
        self,
        positions: List[
            Dict[str, Any]
        ],
        per_entry_limit: int,
    ) -> Dict[
        int,
        Dict[str, Any]
    ]:
        """
        Crawl all entry points and merge documents by doc_id.

        Encounter information is preserved so Ranking/DataMixer can
        understand how strongly a document was connected to the query.
        """

        candidates: Dict[
            int,
            Dict[str, Any]
        ] = {}

        for position in positions:

            results = (
                self._crawl_position(
                    position,
                    per_entry_limit,
                )
            )

            for result in results:

                doc_id = result.get(
                    "doc_id"
                )

                if doc_id is None:
                    continue

                if doc_id not in candidates:

                    text = (
                        self.memory.get_doc(
                            doc_id
                        )
                    )

                    if not text:
                        continue

                    candidates[
                        doc_id
                    ] = {
                        "doc_id": doc_id,
                        "text": text,
                        "encounters": [],
                        "routes": set(),
                    }

                candidates[
                    doc_id
                ][
                    "routes"
                ].add(
                    "word_grid"
                )

                candidates[
                    doc_id
                ][
                    "encounters"
                ].append({
                    "token_index": (
                        position[
                            "token_index"
                        ]
                    ),
                    "token": (
                        position[
                            "token"
                        ].get(
                            "original",
                            "",
                        )
                    ),
                    "row": (
                        position[
                            "row"
                        ]
                    ),
                    "col": (
                        position[
                            "col"
                        ]
                    ),
                })

        return candidates

    # ==================================================================
    # DATA MIXING
    # ==================================================================

    def _mix_candidates(
        self,
        query: str,
        candidates: Dict[
            int,
            Dict[str, Any]
        ],
        analysis: Dict[str, Any],
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Pass retrieved candidates through DataMixer.

        DataMixer is deliberately optional at this stage so the
        retrieval layer remains usable while the mixer is being
        finalized.

        The mixer must not replace retrieval. It enriches/combines
        retrieved information before final ranking.
        """

        candidate_list = list(
            candidates.values()
        )

        if not candidate_list:
            return []

        if self.data_mixer is None:
            return candidate_list

        # --------------------------------------------------------------
        # Preferred mixer interface
        # --------------------------------------------------------------

        for method_name in (
            "mix_candidates",
            "mix",
            "combine",
        ):

            method = getattr(
                self.data_mixer,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:

                mixed = method(
                    query=query,
                    candidates=candidate_list,
                    analysis=analysis,
                )

                if mixed is not None:
                    return list(
                        mixed
                    )

            except TypeError:

                try:

                    mixed = method(
                        query,
                        candidate_list,
                        analysis,
                    )

                    if mixed is not None:
                        return list(
                            mixed
                        )

                except TypeError:
                    continue

        return candidate_list

    # ==================================================================
    # RANKING
    # ==================================================================

    def _rank_candidates(
        self,
        query: str,
        candidates: List[
            Dict[str, Any]
        ],
        lang: str,
        analysis: Dict[str, Any],
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Rank retrieved candidates using the canonical ranking layer.

        Ranking remains the model-weight layer.

        CrawlerRetrieval supplies evidence.
        Ranking decides candidate strength.
        """

        domain = analysis.get(
            "domain",
            "general",
        )

        entities = analysis.get(
            "entities",
            [],
        )

        ranked: List[
            Dict[str, Any]
        ] = []

        for candidate in candidates:

            text = candidate.get(
                "text",
                "",
            )

            if not text:
                continue

            # ----------------------------------------------------------
            # Candidate entities
            # ----------------------------------------------------------

            candidate_entities = (
                candidate.get(
                    "entities",
                    [],
                )
            )

            # ----------------------------------------------------------
            # Ranking
            # ----------------------------------------------------------

            result = score_candidate(
                query=query,
                candidate_text=text,
                query_entities=entities,
                query_hierarchy=domain,
                candidate_entities=candidate_entities,
                candidate_hierarchy=domain,
                freshness_score=float(
                    candidate.get(
                        "freshness_score",
                        0.0,
                    )
                ),
                lang=lang,
            )

            ranked.append({
                "doc_id": candidate[
                    "doc_id"
                ],

                "text": text,

                "score": result[
                    "total"
                ],

                "scores": result.get(
                    "scores",
                    {},
                ),

                "encounters": candidate.get(
                    "encounters",
                    [],
                ),

                "routes": sorted(
                    candidate.get(
                        "routes",
                        set(),
                    )
                ),

                "domain": domain,

                "intent": analysis.get(
                    "intent",
                    "general",
                ),

                "entities": entities,

                "language": lang,
            })

        # --------------------------------------------------------------
        # Final deterministic ordering
        # --------------------------------------------------------------

        ranked.sort(
            key=lambda item: (
                item["score"],
                len(
                    item.get(
                        "encounters",
                        [],
                    )
                ),
            ),
            reverse=True,
        )

        return ranked

    # ==================================================================
    # RETRIEVE
    # ==================================================================

    def retrieve(
        self,
        query: str,
        lang: str = "en",
        limit: int = 50,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Retrieve ranked candidates from MemoryGrid.

        Flow:

            query
              ↓
            tokenizer
              ↓
            intent analysis
              ↓
            every query token
              ↓
            Word Grid positions
              ↓
            GridCrawler
              ↓
            MemoryGrid
              ↓
            DataMixer
              ↓
            Ranking
              ↓
            ranked candidates
        """

        if not query or not str(
            query
        ).strip():

            return []

        lang = normalize_lang(
            lang
        )

        # --------------------------------------------------------------
        # TOKENIZATION
        # --------------------------------------------------------------

        tokens = tokenize(
            query,
            lang,
        )

        if not tokens:
            return []

        # --------------------------------------------------------------
        # INTENT / DOMAIN
        # --------------------------------------------------------------

        analysis = (
            self._analyze_query(
                query,
                lang,
            )
        )

        directive = detect_directive(
            query
        )

        analysis[
            "directive"
        ] = directive

        analysis[
            "language"
        ] = lang

        # --------------------------------------------------------------
        # ENTRY POINTS
        # --------------------------------------------------------------

        positions = (
            self._build_positions(
                tokens
            )
        )

        if not positions:
            return []

        # --------------------------------------------------------------
        # PER-ENTRY LIMIT
        # --------------------------------------------------------------

        per_entry_limit = max(
            1,
            limit
            // len(positions),
        )

        # --------------------------------------------------------------
        # MEMORYGRID / GRIDCRAWLER
        # --------------------------------------------------------------

        candidates = (
            self._collect_candidates(
                positions,
                per_entry_limit,
            )
        )

        if not candidates:
            return []

        # --------------------------------------------------------------
        # DATA MIXER
        # --------------------------------------------------------------

        mixed = (
            self._mix_candidates(
                query=query,
                candidates=candidates,
                analysis=analysis,
            )
        )

        # --------------------------------------------------------------
        # RANK
        # --------------------------------------------------------------

        ranked = (
            self._rank_candidates(
                query=query,
                candidates=mixed,
                lang=lang,
                analysis=analysis,
            )
        )

        return ranked[:limit]

    # ==================================================================
    # RETRIEVE CONTEXT
    # ==================================================================

    def retrieve_context(
        self,
        query: str,
        lang: str = "en",
        limit: int = 10,
        context_limit: int = 3,
    ) -> Dict[str, Any]:
        """
        Return retrieval together with structured query analysis.
        """

        lang = normalize_lang(
            lang
        )

        results = self.retrieve(
            query=query,
            lang=lang,
            limit=limit,
        )

        analysis = (
            self._analyze_query(
                query,
                lang,
            )
        )

        directive = detect_directive(
            query
        )

        context = "\n".join(
            result["text"]
            for result in results[
                :context_limit
            ]
        )

        return {
            "query": query,

            "language": lang,

            "intent": analysis.get(
                "intent",
                "general",
            ),

            "domain": analysis.get(
                "domain",
                "general",
            ),

            "entities": analysis.get(
                "entities",
                [],
            ),

            "directive": directive,

            "results": results,

            "context": context,
        }

    # ==================================================================
    # ENTRY POINT INSPECTION
    # ==================================================================

    def inspect_entry_points(
        self,
        query: str,
        lang: str = "en",
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Inspect where each query token enters the MemoryGrid.

        Useful for debugging the retrieval architecture.
        """

        lang = normalize_lang(
            lang
        )

        tokens = tokenize(
            query,
            lang,
        )

        positions = (
            self._build_positions(
                tokens
            )
        )

        return positions

    # ==================================================================
    # RETRIEVAL TRACE
    # ==================================================================

    def retrieval_trace(
        self,
        query: str,
        lang: str = "en",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Return the complete deterministic retrieval trace.

        This is useful for debugging, GridCV and later project-trace
        memory.
        """

        lang = normalize_lang(
            lang
        )

        tokens = tokenize(
            query,
            lang,
        )

        analysis = (
            self._analyze_query(
                query,
                lang,
            )
        )

        positions = (
            self._build_positions(
                tokens
            )
        )

        per_entry_limit = max(
            1,
            limit
            // max(
                len(positions),
                1,
            ),
        )

        candidates = (
            self._collect_candidates(
                positions,
                per_entry_limit,
            )
        )

        ranked = self._rank_candidates(
            query=query,
            candidates=list(
                candidates.values()
            ),
            lang=lang,
            analysis=analysis,
        )

        return {
            "query": query,

            "language": lang,

            "tokens": tokens,

            "analysis": analysis,

            "entry_points": positions,

            "candidate_count": len(
                candidates
            ),

            "ranked": ranked[
                :limit
            ],
        }