"""
CoMpaNeoN Memory Grid
=====================

Canonical multilingual memory space for CoMpaNeoN.

ARCHITECTURE
------------

User / AI / External Text
        │
        ▼
Language Detection
        │
        ▼
tokenizer.py
        │
        ├── language normalization
        ├── language switching
        ├── alphabet mapping
        ├── Letter Grid
        ├── Word Grid
        ├── symbols
        └── tokenization
        │
        ▼
keyboard.py / placement
        │
        ├── Lsum
        ├── Ssum
        ├── c
        └── canonical GSP entry
        │
        ▼
MemoryGrid
46 Columns × 64 Rows
        │
        ├── documents
        ├── tokens
        ├── storage rows
        ├── word cells
        ├── language phases
        ├── letter information
        └── metadata
        │
        ▼
Crawler Rooters
        │
        ├── GridCrawler
        ├── WebCrawler
        ├── CrawlerScheduler
        └── CrawlerRetrieval


ARCHITECTURAL AUTHORITY
-----------------------

tokenizer.py
    Owns linguistic interpretation.

keyboard.py
    Owns canonical GSP mathematics.

MemoryGrid
    Owns canonical memory storage and indexes.

GridCrawler
    Owns:

        K = 250
        forward_d = 5
        backward_k = 5
        backward_d = 1

    plus:

        forward traversal
        backward perturbation
        Elastic Cloud
        query rooting

WebCrawler
    Owns external acquisition.

CrawlerScheduler
    Owns crawl scheduling.

CrawlerRetrieval
    Owns retrieval orchestration.

IMPORTANT
---------

MemoryGrid does NOT own crawler traversal.

K and D do NOT belong to MemoryGrid.

The crawlers are the rooters.

The canonical operational memory grid is:

    46 columns
    64 rows
"""

from __future__ import annotations

import hashlib

from datetime import (
    datetime,
    timezone,
)

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================

try:

    from langdetect import (
        detect as detect_language_code,
    )

except ImportError:

    detect_language_code = None


# ============================================================================
# TOKENIZER
# ============================================================================

from tokenizer import (
    normalize_lang,
    tokenize,
)


# ============================================================================
# KEYBOARD / CANONICAL GSP
# ============================================================================

from keyboard import (
    calculate_lsum,
    calculate_ssum,
    first_letter_index,
    gsp_place,
    normalise,
)


# ============================================================================
# CODE TOKENIZER  (code-aware placement)
# ============================================================================

try:
    from code_tokenizer import (
        code_word_cell,
        classify_code_token,
        split_code_identifiers,
        tokenize_code,
    )
    CODE_TOKENIZER_AVAILABLE = True
except ImportError:
    CODE_TOKENIZER_AVAILABLE = False
    code_word_cell = None
    classify_code_token = None
    split_code_identifiers = None
    tokenize_code = None


# ============================================================================
# GRID DIMENSIONS
# ============================================================================

GRID_ROWS = 64

GRID_COLS = 46


# ============================================================================
# HELPERS
# ============================================================================

def _utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def _content_hash(
    text: str,
) -> str:

    value = (
        str(text)
        .strip()
        .replace(
            "\r\n",
            "\n",
        )
    )

    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def _normalise_row(
    row: int,
    rows: int,
) -> int:

    return (
        (
            int(row)
            - 1
        )
        % int(rows)
    ) + 1


def _normalise_col(
    col: int,
    cols: int,
) -> int:

    return (
        int(col)
        % int(cols)
    )


# ============================================================================
# MEMORY GRID
# ============================================================================

class MemoryGrid:
    """
    Canonical multilingual spatial memory.

    MemoryGrid receives already acquired text and performs:

        language resolution
            ↓
        tokenizer.py
            ↓
        canonical GSP entry
            ↓
        document storage
            ↓
        token indexing

    It does not perform crawler traversal.

    GridCrawler remains the rooter.
    """

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

    def __init__(
        self,
        rows: int = GRID_ROWS,
        cols: int = GRID_COLS,
    ) -> None:

        self.rows = int(
            rows
        )

        self.cols = int(
            cols
        )

        if self.rows <= 0:

            raise ValueError(
                "MemoryGrid rows must be positive."
            )

        if self.cols <= 0:

            raise ValueError(
                "MemoryGrid columns must be positive."
            )

        # --------------------------------------------------------------------
        # DOCUMENT STORAGE
        # --------------------------------------------------------------------

        self.documents: Dict[
            int,
            Dict[str, Any]
        ] = {}

        # --------------------------------------------------------------------
        # CONTENT IDENTITY
        # --------------------------------------------------------------------

        self.document_hashes: Dict[
            str,
            int
        ] = {}

        # --------------------------------------------------------------------
        # DOCUMENT TOKENS
        # --------------------------------------------------------------------

        self.tokens: Dict[
            int,
            List[Dict[str, Any]]
        ] = {}

        # --------------------------------------------------------------------
        # STORAGE ROW INDEX
        #
        # Used directly by GridCrawler.
        #
        # Contains both:
        #
        #   - canonical document entries
        #   - token entries
        # --------------------------------------------------------------------

        self.storage_index: Dict[
            int,
            List[Dict[str, Any]]
        ] = {}

        # --------------------------------------------------------------------
        # WORD GRID
        #
        # (row, col)
        #
        # row:
        #
        #   tokenizer Word Grid row
        #   normalized into 1..64
        #
        # col:
        #
        #   tokenizer c / word column
        #   normalized into 0..45
        # --------------------------------------------------------------------

        self.word_index: Dict[
            Tuple[int, int],
            List[Dict[str, Any]]
        ] = {}

        # --------------------------------------------------------------------
        # LANGUAGE / MULTILINGUAL PHASE
        # --------------------------------------------------------------------

        self.phase_index: Dict[
            int,
            List[Dict[str, Any]]
        ] = {}

        # --------------------------------------------------------------------
        # LETTER INDEX
        #
        # Letter Grid information remains tokenizer-owned.
        #
        # MemoryGrid only preserves it for retrieval access.
        # --------------------------------------------------------------------

        self.letter_index: Dict[
            int,
            List[Dict[str, Any]]
        ] = {}

        # --------------------------------------------------------------------
        # DOCUMENT ID
        # --------------------------------------------------------------------

        self._next_document_id = 1

        # --------------------------------------------------------------------
        # CRAWLER ROOTERS
        #
        # Lazy initialization avoids circular imports.
        # --------------------------------------------------------------------

        self._grid_crawler = None

        self._web_crawler = None

        self._crawler_scheduler = None

        self._crawler_retrieval = None

        # --------------------------------------------------------------------
        # STATISTICS
        # --------------------------------------------------------------------

        self.documents_added = 0

        self.tokens_added = 0

        self.duplicates_detected = 0

        self.crawler_requests = 0

        self.retrieval_requests = 0

    # ========================================================================
    # GRID DIMENSIONS
    # ========================================================================

    def grid_dimensions(
        self,
    ) -> Tuple[int, int]:

        return (
            self.rows,
            self.cols,
        )

    # ------------------------------------------------------------------------

    def dimensions(
        self,
    ) -> Dict[str, int]:

        return {

            "rows":
                self.rows,

            "cols":
                self.cols,

        }

    # ========================================================================
    # LANGUAGE RESOLUTION
    # ========================================================================

    def resolve_language(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> str:
        """
        Resolve language before tokenizer entry.

        Priority:

            explicit language
                ↓
            langdetect
                ↓
            English fallback

        Final normalization remains owned by tokenizer.py.
        """

        if lang:

            return normalize_lang(
                lang
            )

        value = str(
            text
        ).strip()

        if (
            detect_language_code
            is not None
            and value
        ):

            try:

                detected = (
                    detect_language_code(
                        value
                    )
                )

                return normalize_lang(
                    detected
                )

            except Exception:

                pass

        return normalize_lang(
            "en"
        )

    # ========================================================================
    # TOKENIZER ENTRY
    # ========================================================================

    def tokenize_text(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enter canonical tokenizer.

        MemoryGrid does not reproduce:

            language switching
            alphabet mapping
            Letter Grid mathematics
            Word Grid mathematics
            symbol detection
        """

        resolved_lang = (
            self.resolve_language(
                text,
                lang,
            )
        )

        token_list = tokenize(
            text,
            resolved_lang,
        )

        return {

            "text":
                text,

            "language":
                resolved_lang,

            "tokens":
                token_list,

            "token_count":
                len(
                    token_list
                ),

        }

    # ========================================================================
    # CANONICAL FULL-TEXT ENTRY
    # ========================================================================

    def placement_for_text(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the canonical GSP entry.

        This creates the entry point.

        It does NOT traverse.

        GridCrawler subsequently applies:

            K = 250
            forward_d = 5
            backward_k = 5
            backward_d = 1
        """

        resolved_lang = (
            self.resolve_language(
                text,
                lang,
            )
        )

        normalized = normalise(
            text,
            resolved_lang,
        )

        Lsum = calculate_lsum(
            normalized,
            resolved_lang,
        )

        Ssum = calculate_ssum(
            normalized,
            resolved_lang,
        )

        c = first_letter_index(
            normalized,
            resolved_lang,
        )

        placement = gsp_place(

            Lsum=Lsum,

            Ssum=Ssum,

            c=c,

            # Entry only.
            #
            # These are not crawler traversal values.
            K=0,

            D=0,

            C=self.cols,

            R=self.rows,

        )

        start_row = (
            _normalise_row(
                placement.get(
                    "start_row",
                    1,
                ),
                self.rows,
            )
        )

        start_col = (
            _normalise_col(
                c,
                self.cols,
            )
        )

        return {

            "normalized":
                normalized,

            "language":
                resolved_lang,

            "Lsum":
                int(Lsum),

            "Ssum":
                int(Ssum),

            # Original tokenizer/keyboard linguistic c.
            "c":
                int(c),

            "start_row":
                start_row,

            # Operational MemoryGrid column.
            "start_col":
                start_col,

            "placement":
                placement,

        }

    # ========================================================================
    # DOCUMENT ID
    # ========================================================================

    def _allocate_document_id(
        self,
    ) -> int:

        document_id = (
            self._next_document_id
        )

        self._next_document_id += 1

        return document_id

    # ========================================================================
    # ADD DOCUMENT
    # ========================================================================

    def add_document(
        self,
        text: str,
        lang: Optional[str] = None,
        source: str = "memory",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> int:
        """
        Canonical document insertion.

        Pipeline:

            text
                ↓
            langdetect
                ↓
            tokenizer language switch
                ↓
            tokenizer token structure
                ↓
            keyboard canonical GSP entry
                ↓
            MemoryGrid 46 × 64
                ↓
            document + token indexes
        """

        text = str(
            text
        ).strip()

        if not text:

            raise ValueError(
                "Cannot index empty text."
            )

        checksum = (
            _content_hash(
                text
            )
        )

        # --------------------------------------------------------------------
        # DUPLICATE DETECTION
        # --------------------------------------------------------------------

        existing_id = (
            self.document_hashes.get(
                checksum
            )
        )

        if existing_id is not None:

            self.duplicates_detected += 1

            return existing_id

        # --------------------------------------------------------------------
        # TOKENIZER
        # --------------------------------------------------------------------

        token_data = (
            self.tokenize_text(
                text,
                lang,
            )
        )

        resolved_lang = (
            token_data[
                "language"
            ]
        )

        # --------------------------------------------------------------------
        # FULL-TEXT ENTRY
        # --------------------------------------------------------------------

        placement = (
            self.placement_for_text(
                text,
                resolved_lang,
            )
        )

        # --------------------------------------------------------------------
        # DOCUMENT ID
        # --------------------------------------------------------------------

        document_id = (
            self._allocate_document_id()
        )

        # --------------------------------------------------------------------
        # DOCUMENT RECORD
        # --------------------------------------------------------------------

        document = {

            "doc_id":
                document_id,

            "text":
                text,

            "original":
                text,

            "language":
                resolved_lang,

            "lang":
                resolved_lang,

            "source":
                source,

            "content_hash":
                checksum,

            "created_at":
                _utc_now(),

            "placement":
                placement,

            "metadata":
                dict(
                    metadata
                    or {}
                ),

        }

        self.documents[
            document_id
        ] = document

        self.document_hashes[
            checksum
        ] = document_id

        self.documents_added += 1

        # --------------------------------------------------------------------
        # FULL-TEXT STORAGE ENTRY
        #
        # GridCrawler roots through this row.
        # --------------------------------------------------------------------

        storage_row = (
            _normalise_row(
                placement[
                    "start_row"
                ],
                self.rows,
            )
        )

        self.storage_index.setdefault(
            storage_row,
            [],
        ).append(
            document
        )

        # --------------------------------------------------------------------
        # TOKEN STORAGE
        # --------------------------------------------------------------------

        stored_tokens: List[
            Dict[str, Any]
        ] = []

        for position, token in enumerate(
            token_data[
                "tokens"
            ]
        ):

            token_record = (
                self._build_token_record(

                    token=token,

                    position=position,

                    document=document,

                    placement=placement,

                )
            )

            stored_tokens.append(
                token_record
            )

            self._index_token(
                token_record
            )

            self.tokens_added += 1

        self.tokens[
            document_id
        ] = stored_tokens

        return document_id

    # ========================================================================
    # TOKEN RECORD
    # ========================================================================

    def _build_token_record(
        self,
        token: Dict[str, Any],
        position: int,
        document: Dict[str, Any],
        placement: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build the token record used by every MemoryGrid index route.
        """
        token_data = token if isinstance(token, dict) else {}

        original = (
            token_data.get("original")
            or token_data.get("token")
            or token_data.get("word")
            or ""
        )
        if isinstance(original, dict):
            original = original.get("text") or str(original)
        original = str(original)

        stem = (
            token_data.get("stem")
            or token_data.get("token")
            or original
        )
        if isinstance(stem, dict):
            stem = str(stem)
        stem = str(stem)

        word_data = token_data.get("word") or {}
        if not isinstance(word_data, dict):
            word_data = {}

        tokenizer_c = token_data.get("c", 0)
        try:
            tokenizer_c = int(tokenizer_c)
        except Exception:
            tokenizer_c = 0

        row = token_data.get("row") or placement.get("start_row") or 1
        try:
            row = int(row)
        except Exception:
            row = 1

        col = (
            token_data.get("col")
            or token_data.get("language_phase")
            or placement.get("start_col")
            or 0
        )
        try:
            col = int(col)
        except Exception:
            col = 0

        language_phase = token_data.get("language_phase", col)
        try:
            language_phase = int(language_phase)
        except Exception:
            language_phase = col

        normalized_letters = token_data.get("letter") or []
        if not isinstance(normalized_letters, (list, tuple)):
            normalized_letters = []

        return {

            "doc_id":
                document[
                    "doc_id"
                ],

            "token":
                stem,

            "original":
                original,

            "stem":
                stem,

            "position":
                position,

            # Operational MemoryGrid word cell.
            "row":
                row,

            "col":
                col,

            # Original tokenizer Word Grid information.
            "word":
                dict(
                    word_data
                ),

            # Original linguistic c.
            "c":
                tokenizer_c,

            # Operational 46-column phase.
            "language_phase":
                language_phase,

            "letter":
                normalized_letters,

            "symbols":
                list(
                    token_data.get(
                        "symbols"
                    )
                    or []
                ),

            "language":
                document[
                    "language"
                ],

            "lang":
                document[
                    "lang"
                ],

            "source":
                document[
                    "source"
                ],

            # Preserve complete tokenizer output.
            "tokenizer":
                token_data,

        }

    # ========================================================================
    # TOKEN INDEXING
    # ========================================================================

    def _index_token(
        self,
        token: Dict[str, Any],
    ) -> None:
        """
        Index token into every MemoryGrid route used by
        crawler rooters.
        """


        # --------------------------------------------------------------
        # ACC_CODE_BRANCH
        # Additive: code recognition + color-class routing.
        # Existing word/letter/storage/phase routes below remain unchanged.
        # --------------------------------------------------------------
        tk = token.get("token") or token.get("original") or ""
        if tk:
            try:
                from code_tokenizer import classify_code_token, code_word_cell
                color = classify_code_token(tk)
                token["color_class"] = color
                if color not in ("IDENT_VAR", "IDENT"):
                    token["kind"] = "code"
                    ccol = code_word_cell(tk)["c"]
                    token["code_col"] = ccol
                    if not hasattr(self, "code_index"):
                        self.code_index = {}
                    self.code_index.setdefault(ccol, []).append(token)
                else:
                    token["kind"] = "word"
            except Exception:
                token["kind"] = token.get("kind", "word")
        row = (
            _normalise_row(
                token[
                    "row"
                ],
                self.rows,
            )
        )

        col = (
            _normalise_col(
                token[
                    "col"
                ],
                self.cols,
            )
        )

        phase = (
            _normalise_col(
                token.get(
                    "language_phase",
                    col,
                ),
                self.cols,
            )
        )

        # --------------------------------------------------------------------
        # STORAGE ROW
        # --------------------------------------------------------------------

        self.storage_index.setdefault(
            row,
            [],
        ).append(
            token
        )

        # --------------------------------------------------------------------
        # WORD GRID
        # --------------------------------------------------------------------

        self.word_index.setdefault(
            (
                row,
                col,
            ),
            [],
        ).append(
            token
        )

        # --------------------------------------------------------------------
        # LANGUAGE PHASE
        # --------------------------------------------------------------------

        self.phase_index.setdefault(
            phase,
            [],
        ).append(
            token
        )

        # --------------------------------------------------------------------
        # LETTER INFORMATION
        # --------------------------------------------------------------------

        for letter_col in token.get(
            "letter",
            [],
        ):

            self.letter_index.setdefault(
                letter_col,
                [],
            ).append(
                token
            )

    # ========================================================================
    # STORAGE LOOKUP
    # ========================================================================

    def get_tokens_at_storage(
        self,
        row: int,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Primary full-text storage route for GridCrawler.
        """

        row = (
            _normalise_row(
                row,
                self.rows,
            )
        )

        return list(
            self.storage_index.get(
                row,
                [],
            )
        )

    # ========================================================================
    # WORD GRID LOOKUP
    # ========================================================================

    def get_tokens_at_word(
        self,
        row: int,
        col: int,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Retrieve candidates from the tokenizer Word Grid route,
        mapped into MemoryGrid's 46 × 64 operational space.
        """

        row = (
            _normalise_row(
                row,
                self.rows,
            )
        )

        col = (
            _normalise_col(
                col,
                self.cols,
            )
        )

        return list(
            self.word_index.get(
                (
                    row,
                    col,
                ),
                [],
            )
        )

    # ========================================================================
    # LANGUAGE PHASE LOOKUP
    # ========================================================================

    def get_tokens_at_phase(
        self,
        phase: int,
    ) -> List[
        Dict[str, Any]
    ]:

        phase = (
            _normalise_col(
                phase,
                self.cols,
            )
        )

        return list(
            self.phase_index.get(
                phase,
                [],
            )
        )

    # ========================================================================
    # LETTER LOOKUP
    # ========================================================================

    def get_tokens_at_letter(
        self,
        col: int,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Retrieve candidates by tokenizer Letter Grid information.
        """

        col = (
            _normalise_col(
                col,
                self.cols,
            )
        )

        return list(
            self.letter_index.get(
                col,
                [],
            )
        )

    # ========================================================================
    # LEGACY LOOKUP
    # ========================================================================

    def get_tokens_at(
        self,
        row: int,
        col: int,
    ) -> List[
        Dict[str, Any]
    ]:

        return self.get_tokens_at_word(
            row,
            col,
        )

    # ========================================================================
    # DOCUMENT LOOKUP
    # ========================================================================

    def get_document(
        self,
        doc_id: int,
    ) -> Optional[
        Dict[str, Any]
    ]:

        return self.documents.get(
            int(doc_id)
        )

    # ========================================================================
    # DOCUMENT TOKENS
    # ========================================================================

    def get_document_tokens(
        self,
        doc_id: int,
    ) -> List[
        Dict[str, Any]
    ]:

        return list(
            self.tokens.get(
                int(doc_id),
                [],
            )
        )

    # ========================================================================
    # GRID CRAWLER
    # ========================================================================

    def get_grid_crawler(
        self,
    ) -> Any:
        """
        GridCrawler remains the rooter.

        It owns:

            K = 250
            forward_d = 5
            backward_k = 5
            backward_d = 1
        """

        if self._grid_crawler is None:

            from grid_crawler import (
                GridCrawler,
            )

            self._grid_crawler = (
                GridCrawler(
                    self
                )
            )

        return self._grid_crawler

    # ========================================================================
    # CRAWLER SCHEDULER
    # ========================================================================

    def get_crawler_scheduler(
        self,
    ) -> Any:

        if self._crawler_scheduler is None:

            from crawler_scheduler import (
                CrawlerScheduler,
            )

            self._crawler_scheduler = (
                CrawlerScheduler()
            )

        return self._crawler_scheduler

    # ========================================================================
    # WEB CRAWLER
    # ========================================================================

    def get_web_crawler(
        self,
    ) -> Any:
        """
        WebCrawler receives this MemoryGrid and the shared
        CrawlerScheduler.

        External acquisition:

            WebCrawler
                ↓
            MemoryGrid.add_document()
        """

        if self._web_crawler is None:

            from web_crawler import (
                WebCrawler,
            )

            self._web_crawler = (
                WebCrawler(

                    self,

                    scheduler=(
                        self.get_crawler_scheduler()
                    ),

                )
            )

        return self._web_crawler

    # ========================================================================
    # CRAWLER RETRIEVAL
    # ========================================================================

    def get_crawler_retrieval(
        self,
    ) -> Any:
        """
        CrawlerRetrieval remains above the crawler routes.

        MemoryGrid does not perform ranking.
        """

        if self._crawler_retrieval is None:

            from crawler_retrieval import (
                CrawlerRetrieval,
            )

            self._crawler_retrieval = (
                CrawlerRetrieval(
                    self
                )
            )

        return self._crawler_retrieval

    # ========================================================================
    # ROOT TEXT
    # ========================================================================

    def crawl_text(
        self,
        text: str,
        lang: Optional[str] = None,
        limit: int = 250,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Root text through GridCrawler.

        MemoryGrid provides the multilingual entry.

        GridCrawler performs the traversal.
        """

        placement = (
            self.placement_for_text(
                text,
                lang,
            )
        )

        crawler = (
            self.get_grid_crawler()
        )

        self.crawler_requests += 1

        return crawler.crawl(

            start_row=placement[
                "start_row"
            ],

            start_col=placement[
                "start_col"
            ],

            L=placement[
                "Lsum"
            ],

            S=placement[
                "Ssum"
            ],

            c=placement[
                "c"
            ],

            limit=limit,

        )

    # ========================================================================
    # RETRIEVAL ENTRY
    # ========================================================================

    def retrieve(
        self,
        query: str,
        lang: Optional[str] = None,
        limit: int = 250,
        **kwargs: Any,
    ) -> Any:
        """
        Pass query into CrawlerRetrieval.

        MemoryGrid remains memory.

        CrawlerRetrieval orchestrates retrieval.
        """

        retrieval = (
            self.get_crawler_retrieval()
        )

        self.retrieval_requests += 1

        return retrieval.retrieve(

            query=query,

            lang=lang,

            limit=limit,

            **kwargs,

        )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def stats(
        self,
    ) -> Dict[str, Any]:

        return {

            "rows":
                self.rows,

            "cols":
                self.cols,

            "documents":
                len(
                    self.documents
                ),

            "tokens":
                self.tokens_added,

            "documents_added":
                self.documents_added,

            "duplicates_detected":
                self.duplicates_detected,

            "storage_rows":
                len(
                    self.storage_index
                ),

            "word_cells":
                len(
                    self.word_index
                ),

            "language_phases":
                len(
                    self.phase_index
                ),

            "letter_columns":
                len(
                    self.letter_index
                ),

            "crawler_requests":
                self.crawler_requests,

            "retrieval_requests":
                self.retrieval_requests,

        }


# ============================================================================
# DEVELOPMENT TEST
# ============================================================================

if __name__ == "__main__":

    memory = MemoryGrid()

    document_id = (
        memory.add_document(

            text=(
                "CoMpaNeoN is a multilingual "
                "organizational AI architecture."
            ),

            lang="en",

            source="development",

        )
    )

    print(
        "CoMpaNeoN MemoryGrid"
    )

    print(
        memory.dimensions()
    )

    print(
        {
            "document_id":
                document_id
        }
    )

    print(
        memory.stats()
    )

# ============================================================================
# PERSISTENCE + SHARED ACCESS
# ============================================================================

import json
import os
from pathlib import Path

_DEFAULT_GRID_PATH = os.environ.get(
    "ACCD_GRID_PATH",
    str(Path("data") / "memory_grid_snapshot.json"),
)

_SHARED_GRID = None


def get_process_grid():
    """
    Process-local singleton. Prefer integration.get_shared_grid()
    when the app is running; this is the fallback owner inside
    the memory package itself.
    """
    global _SHARED_GRID
    if _SHARED_GRID is not None:
        return _SHARED_GRID
    try:
        from integration import get_shared_grid
        g = get_shared_grid()
        if g is not None:
            _SHARED_GRID = g
            return _SHARED_GRID
    except Exception:
        pass
    _SHARED_GRID = MemoryGrid()
    return _SHARED_GRID


def set_process_grid(grid) -> None:
    global _SHARED_GRID
    _SHARED_GRID = grid
    try:
        from integration import get_state
        get_state()["grid"] = grid
    except Exception:
        pass


def _grid_to_dict(grid: "MemoryGrid") -> dict:
    return {
        "rows": grid.rows,
        "cols": grid.cols,
        "documents": {str(k): v for k, v in (grid.documents or {}).items()},
        "document_hashes": dict(grid.document_hashes or {}),
        "tokens": {str(k): v for k, v in (grid.tokens or {}).items()},
        "_next_document_id": getattr(grid, "_next_document_id", 1),
        "documents_added": getattr(grid, "documents_added", 0),
        "tokens_added": getattr(grid, "tokens_added", 0),
        "duplicates_detected": getattr(grid, "duplicates_detected", 0),
    }


def _grid_from_dict(data: dict) -> "MemoryGrid":
    grid = MemoryGrid(
        rows=int(data.get("rows") or GRID_ROWS),
        cols=int(data.get("cols") or GRID_COLS),
    )
    docs = data.get("documents") or {}
    grid.documents = {int(k): v for k, v in docs.items()}
    grid.document_hashes = dict(data.get("document_hashes") or {})
    toks = data.get("tokens") or {}
    grid.tokens = {int(k): v for k, v in toks.items()}
    grid._next_document_id = int(data.get("_next_document_id") or 1)
    grid.documents_added = int(data.get("documents_added") or 0)
    grid.tokens_added = int(data.get("tokens_added") or 0)
    grid.duplicates_detected = int(data.get("duplicates_detected") or 0)
    # Rebuild operational indexes from stored documents when possible
    try:
        for doc in grid.documents.values():
            placement = (doc or {}).get("placement") or {}
            start_row = placement.get("start_row") or 1
            row = _normalise_row(start_row, grid.rows)
            grid.storage_index.setdefault(row, []).append(doc)
        for doc_id, token_list in (grid.tokens or {}).items():
            for token in token_list or []:
                if isinstance(token, dict):
                    grid._index_token(token)
    except Exception:
        pass
    return grid


def save_grid(grid: "MemoryGrid" = None, path: str = None) -> str:
    grid = grid or get_process_grid()
    path = path or _DEFAULT_GRID_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_grid_to_dict(grid), f, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def load_grid(path: str = None) -> "MemoryGrid":
    path = path or _DEFAULT_GRID_PATH
    if not os.path.isfile(path):
        return get_process_grid()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    grid = _grid_from_dict(data)
    set_process_grid(grid)
    return grid


def root_query_for_context(query: str, limit: int = 32) -> str:
    """
    Central retrieval: user/AI query → GridCrawler.crawl_query →
    MemoryGrid documents → plain text context for prompt / stream.
    """
    grid = get_process_grid()
    if grid is None or not (query or "").strip():
        return ""

    q = str(query).strip()
    candidates = []

    try:
        try:
            from grid_crawler import crawl_query
        except ImportError:
            from memory.grid_crawler import crawl_query

        raw = crawl_query(grid, q, lang="en", limit=limit)
        if isinstance(raw, dict):
            candidates = raw.get("candidates") or raw.get("full_query") or []
        elif isinstance(raw, list):
            candidates = raw
    except Exception as e:
        print("[memory_grid] crawl_query failed:", type(e).__name__, e)
        candidates = []

    # Fallback: recent documents if crawl returns nothing
    if not candidates and getattr(grid, "documents", None):
        docs = list(grid.documents.values())[-limit:]
        parts = []
        for d in docs:
            t = (d or {}).get("text") or ""
            if t.strip():
                parts.append(t.strip()[:800])
        return "\n\n".join(parts)

    parts = []
    seen = set()
    for c in candidates[:limit]:
        if not isinstance(c, dict):
            continue
        text_c = c.get("text") or c.get("original") or c.get("snippet") or ""
        doc_id = c.get("doc_id")
        if doc_id is not None and hasattr(grid, "documents"):
            try:
                doc = grid.documents.get(int(doc_id))
            except Exception:
                doc = None
            if isinstance(doc, dict) and doc.get("text"):
                text_c = doc["text"]
        text_c = (text_c or "").strip()
        if text_c and text_c not in seen:
            seen.add(text_c)
            parts.append(text_c[:800])
    return "\n\n".join(parts)

