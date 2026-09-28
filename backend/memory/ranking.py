"""
Ranking Module

Ranks candidate contexts using the existing CoMpaNeoN knowledge
architecture.

Signals:
- Exact lexical match
- Same entity
- Same hierarchy / domain
- GSP relationship proximity
- Forward perturbation encounter
- Backward perturbation encounter
- 3×3 encounter
- Elastic-cloud encounter
- Freshness
- Weak lexical match
- Distant relationship
- Cloud encounter
- Word-pair relationship
- Next-word continuation
- Phrase continuity
- Unrelated hierarchy penalty

Architecture:

    tokenizer.py
        |
        +--> lexical tokenization
        |
    keyboard.py
        |
        +--> GSP start-row calculation
        +--> elastic-cloud calculation
        |
    grid_crawler.py
        |
        +--> forward perturbation
        +--> backward perturbation
        +--> elastic-cloud traversal
        |
    memory_grid.py
        |
        +--> stored candidates
        |
    ranking.py
        |
        +--> candidate scoring

Important:
- Tokenizer/grid remains independent from crawler traversal.
- Domain detection remains external to this module.
- Dictionary/synonym understanding remains external.
- No embeddings/vector search are introduced here.
- K and D are crawler concepts, not tokenizer/storage concepts.
"""

from __future__ import annotations

import re

from typing import (
    List,
    Dict,
    Any,
    Optional,
)

from tokenizer import (
    tokenize,
    normalize_lang,
    letter_score,
    word_score,
)

from keyboard import (
    calculate_lsum,
    calculate_ssum,
    first_letter_index,
    gsp_place,
    elastic_cloud,
)

from symbols import recognize_symbols
from code_languages import CODE_TERMS
from directives import detect_directive


# ============================================================================
# CRAWLER PERTURBATION CONFIGURATION
# ============================================================================

# Forward crawler perturbation.
FORWARD_D = 5

# Backward crawler perturbation.
#
# This is intentionally different from FORWARD_D.
BACKWARD_D = 1

# Number of backward perturbation steps recognized by the ranking layer.
#
# K belongs to crawler traversal.
BACKWARD_K = 5


# ============================================================================
# SCORING WEIGHTS
# ============================================================================

WEIGHTS = {
    "exact_lexical": 70,
    "same_entity": 50,
    "same_hierarchy": 50,
    "relationship": 30,
    "perturbation": 30,
    "backward_perturbation": 35,
    "three_by_three": 40,
    "elastic_cloud": 30,
    "freshness": 30,
    "weak_lexical": 20,
    "distant_relationship": 30,
    "cloud_encounter": 40,
    "unrelated_hierarchy": -20,
    "word_pair": 40,
    "next_word_prediction": 35,
    "phrase_continuity": 75,
}


# ============================================================================
# MAIN GSP CELL
# ============================================================================

def compute_gsp_cell(
    text: str,
    lang: str = "en",
) -> Optional[Dict[str, int]]:
    """
    Compute the main GSP start cell.

    Main GSP:

        L = keyboard row-index sum
        S = keyboard column-index sum
        c = first-letter index

        start_row =
            ((L + S - 1) % R) + 1

    This function calculates only the main GSP placement.

    It does NOT perform crawler traversal.

    It does NOT apply forward/backward D.

    It does NOT apply crawler K.
    """

    if not text:
        return None

    lang = normalize_lang(lang)

    clean = str(text).strip().lower()

    if not clean:
        return None

    L = calculate_lsum(
        clean,
        lang,
    )

    S = calculate_ssum(
        clean,
        lang,
    )

    c = first_letter_index(
        clean,
        lang,
    )

    placement = gsp_place(
        L,
        S,
        c,
        K=0,
        D=0,
        C=26,
        R=64,
    )

    return placement.get(
        "primary_cell"
    )


# ============================================================================
# BACKWARD PERTURBATION CELLS
# ============================================================================

def compute_backward_perturbations(
    cell: Dict[str, int],
    backward_d: int = BACKWARD_D,
    backward_k: int = BACKWARD_K,
    rows: int = 64,
) -> List[Dict[str, int]]:
    """
    Calculate the backward perturbation path from a main GSP cell.

    Backward crawler rule:

        row_k =
            ((start_row - 1 - k * backward_d) % R) + 1

    with:

        backward_d = 1
        backward_k = 5

    Therefore a start row of 20 produces:

        19
        18
        17
        16
        15

    The main start row itself is NOT included.

    This function only describes the perturbation coordinates.
    Actual crawling remains the responsibility of grid_crawler.py.
    """

    if not cell:
        return []

    start_row = int(
        cell["row"]
    )

    col = int(
        cell["col"]
    )

    backward_d = max(
        1,
        int(backward_d),
    )

    backward_k = max(
        0,
        int(backward_k),
    )

    rows = max(
        1,
        int(rows),
    )

    cells: List[Dict[str, int]] = []

    for k in range(
        1,
        backward_k + 1,
    ):

        row = (
            (
                start_row
                - 1
                - k * backward_d
            )
            % rows
        ) + 1

        cells.append({
            "col": col,
            "row": row,
            "k": k,
        })

    return cells


# ============================================================================
# FORWARD PERTURBATION CELLS
# ============================================================================

def compute_forward_perturbations(
    cell: Dict[str, int],
    forward_d: int = FORWARD_D,
    steps: int = 1,
    rows: int = 64,
) -> List[Dict[str, int]]:
    """
    Calculate forward perturbation coordinates.

    This helper exists so ranking can recognize forward crawler
    encounters without taking ownership of crawler traversal.

    Forward movement:

        row_k =
            ((start_row - 1 + k * forward_d) % R) + 1

    Default:

        forward_d = 5

    The main GSP cell is excluded.
    """

    if not cell:
        return []

    start_row = int(
        cell["row"]
    )

    col = int(
        cell["col"]
    )

    forward_d = max(
        1,
        int(forward_d),
    )

    steps = max(
        0,
        int(steps),
    )

    rows = max(
        1,
        int(rows),
    )

    cells: List[Dict[str, int]] = []

    for k in range(
        1,
        steps + 1,
    ):

        row = (
            (
                start_row
                - 1
                + k * forward_d
            )
            % rows
        ) + 1

        cells.append({
            "col": col,
            "row": row,
            "k": k,
        })

    return cells


# ============================================================================
# ELASTIC CLOUD
# ============================================================================

def compute_elastic_cloud(
    text: str,
    lang: str = "en",
) -> List[Dict[str, int]]:
    """
    Compute elastic-cloud cells using keyboard.py.

    Elastic-cloud traversal remains separate from the main GSP
    placement calculation.
    """

    if not text:
        return []

    lang = normalize_lang(lang)

    clean = str(text).strip().lower()

    if not clean:
        return []

    L = calculate_lsum(
        clean,
        lang,
    )

    S = calculate_ssum(
        clean,
        lang,
    )

    c = first_letter_index(
        clean,
        lang,
    )

    return elastic_cloud(
        L,
        S,
        c,
        radius=1,
        first_letter_radius=1,
        C=26,
        R=64,
    )


# ============================================================================
# 3×3 ENCOUNTER
# ============================================================================

def get_three_by_three(
    cell: Dict[str, int],
) -> List[Dict[str, int]]:
    """
    Return the eight surrounding cells around a GSP cell.

    The center cell is excluded.
    """

    col = int(
        cell["col"]
    )

    row = int(
        cell["row"]
    )

    cells = []

    for dr in (-1, 0, 1):

        for dc in (-1, 0, 1):

            if (
                dr == 0
                and dc == 0
            ):
                continue

            cells.append({
                "col": (
                    col + dc
                ) % 26,

                "row": (
                    (
                        row
                        - 1
                        + dr
                    ) % 64
                ) + 1,
            })

    return cells


# ============================================================================
# WORD CLEANING
# ============================================================================

def _clean_words(
    text: str,
) -> List[str]:

    return re.findall(
        r"[a-zA-Z0-9_]+",
        str(text).lower(),
    )


# ============================================================================
# WORD PAIRS
# ============================================================================

def extract_word_pairs(
    text: str,
) -> List[str]:

    words = _clean_words(
        text
    )

    return [
        f"{words[i]}_{words[i + 1]}"
        for i in range(
            len(words) - 1
        )
    ]


def word_pair_score(
    query: str,
    candidate_text: str,
) -> float:

    query_pairs = extract_word_pairs(
        query
    )

    if not query_pairs:
        return 0.0

    candidate_pairs = set(
        extract_word_pairs(
            candidate_text
        )
    )

    matched = sum(
        1
        for pair in query_pairs
        if pair in candidate_pairs
    )

    return (
        matched
        / len(query_pairs)
    ) * 100.0


# ============================================================================
# NEXT WORD
# ============================================================================

def next_word_prediction_score(
    query: str,
    candidate_text: str,
) -> float:

    query_words = _clean_words(
        query
    )

    candidate_words = _clean_words(
        candidate_text
    )

    if (
        not query_words
        or not candidate_words
    ):
        return 0.0

    q_len = len(
        query_words
    )

    if (
        len(candidate_words)
        < q_len
    ):
        return 0.0

    best_score = 0.0

    for i in range(
        len(candidate_words)
        - q_len
        + 1
    ):

        window = candidate_words[
            i:
            i + q_len
        ]

        matches = sum(
            1
            for q, c in zip(
                query_words,
                window,
            )
            if q == c
        )

        sequence_score = (
            matches
            / q_len
        )

        if sequence_score > best_score:
            best_score = sequence_score

    for i in range(
        len(candidate_words)
        - q_len
        + 1
    ):

        window = candidate_words[
            i:
            i + q_len
        ]

        if window == query_words:

            return 100.0

    return best_score * 100.0


# ============================================================================
# PHRASE CONTINUITY
# ============================================================================

def phrase_continuity_score(
    query: str,
    candidate_text: str,
) -> float:

    query_words = _clean_words(
        query
    )

    candidate_words = _clean_words(
        candidate_text
    )

    if (
        not query_words
        or not candidate_words
    ):
        return 0.0

    longest = 0

    for i in range(
        len(query_words)
    ):

        current = 0

        for j in range(
            len(candidate_words)
        ):

            q_index = (
                i + current
            )

            if (
                q_index
                < len(query_words)
                and query_words[q_index]
                == candidate_words[j]
            ):

                current += 1

                longest = max(
                    longest,
                    current,
                )

            else:

                current = 0

    return (
        longest
        / len(query_words)
    ) * 100.0


# ============================================================================
# CELL MATCH HELPER
# ============================================================================

def _same_cell(
    first: Dict[str, int],
    second: Dict[str, int],
) -> bool:

    if not first or not second:
        return False

    return (
        int(first["col"])
        == int(second["col"])
        and
        int(first["row"])
        == int(second["row"])
    )


# ============================================================================
# CANDIDATE RANKING
# ============================================================================

def score_candidate(
    query: str,
    candidate_text: str,
    candidate_entities: Optional[
        List[str]
    ] = None,
    candidate_hierarchy: Optional[
        str
    ] = None,
    query_entities: Optional[
        List[str]
    ] = None,
    query_hierarchy: Optional[
        str
    ] = None,
    freshness_score: float = 0.0,
    lang: str = "en",
    crawler_encounters: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> Dict[str, Any]:
    """
    Score one candidate.

    crawler_encounters may contain traversal information returned
    by grid_crawler.py.

    Expected encounter examples:

        {
            "row": 18,
            "col": 7,
            "type": "backward_perturbation",
            "k": 2
        }

    or:

        {
            "row": 18,
            "col": 7,
            "type": "elastic_cloud"
        }

    Ranking does not perform crawling itself.
    It only evaluates traversal information when supplied.
    """

    scores = {
        key: 0.0
        for key in WEIGHTS
    }

    if (
        not query
        or not candidate_text
    ):

        return {
            "total": 0.0,
            "scores": scores,
        }

    lang = normalize_lang(
        lang
    )

    q_tokens = tokenize(
        query,
        lang,
    )

    c_tokens = tokenize(
        candidate_text,
        lang,
    )

    if (
        not q_tokens
        or not c_tokens
    ):

        return {
            "total": 0.0,
            "scores": scores,
        }

    # ========================================================================
    # WORD RELATIONSHIPS
    # ========================================================================

    pair_score = word_pair_score(
        query,
        candidate_text,
    )

    scores["word_pair"] = (
        pair_score / 100.0
    ) * WEIGHTS[
        "word_pair"
    ]

    next_score = (
        next_word_prediction_score(
            query,
            candidate_text,
        )
    )

    scores[
        "next_word_prediction"
    ] = (
        next_score / 100.0
    ) * WEIGHTS[
        "next_word_prediction"
    ]

    phrase_score = (
        phrase_continuity_score(
            query,
            candidate_text,
        )
    )

    scores[
        "phrase_continuity"
    ] = (
        phrase_score / 100.0
    ) * WEIGHTS[
        "phrase_continuity"
    ]

    # ========================================================================
    # EXACT LEXICAL
    # ========================================================================

    exact_lex = word_score(
        q_tokens,
        candidate_text,
        lang,
    )

    scores[
        "exact_lexical"
    ] = (
        min(
            exact_lex,
            100,
        )
        * WEIGHTS[
            "exact_lexical"
        ]
        / 100
    )

    # ========================================================================
    # ENTITY
    # ========================================================================

    if (
        query_entities
        and candidate_entities
    ):

        q_entities = {
            str(entity).lower()
            for entity in query_entities
        }

        c_entities = {
            str(entity).lower()
            for entity in candidate_entities
        }

        if q_entities & c_entities:

            scores[
                "same_entity"
            ] = WEIGHTS[
                "same_entity"
            ]

    # ========================================================================
    # HIERARCHY / DOMAIN
    # ========================================================================

    if (
        query_hierarchy
        and candidate_hierarchy
    ):

        if (
            query_hierarchy
            == candidate_hierarchy
        ):

            scores[
                "same_hierarchy"
            ] = WEIGHTS[
                "same_hierarchy"
            ]

        else:

            scores[
                "unrelated_hierarchy"
            ] = WEIGHTS[
                "unrelated_hierarchy"
            ]

    # ========================================================================
    # MAIN GSP RELATIONSHIP
    # ========================================================================

    q_cell = compute_gsp_cell(
        query,
        lang,
    )

    c_cell = compute_gsp_cell(
        candidate_text,
        lang,
    )

    if (
        q_cell
        and c_cell
    ):

        row_difference = abs(
            q_cell["row"]
            - c_cell["row"]
        )

        row_distance = min(
            row_difference,
            64 - row_difference,
        )

        col_difference = abs(
            q_cell["col"]
            - c_cell["col"]
        )

        col_distance = min(
            col_difference,
            26 - col_difference,
        )

        total_distance = (
            row_distance
            + col_distance
        )

        scores[
            "relationship"
        ] = max(
            0.0,
            WEIGHTS[
                "relationship"
            ]
            * (
                1
                - total_distance
                / 90
            ),
        )

    # ========================================================================
    # FORWARD / LOCAL PERTURBATION
    # ========================================================================

    if (
        q_cell
        and c_cell
    ):

        row_difference = abs(
            q_cell["row"]
            - c_cell["row"]
        )

        col_difference = abs(
            q_cell["col"]
            - c_cell["col"]
        )

        if (
            row_difference <= 1
            and col_difference <= 1
        ):

            scores[
                "perturbation"
            ] = WEIGHTS[
                "perturbation"
            ]

    # ========================================================================
    # BACKWARD PERTURBATION
    # ========================================================================

    if (
        q_cell
        and c_cell
    ):

        backward_cells = (
            compute_backward_perturbations(
                q_cell,
                backward_d=BACKWARD_D,
                backward_k=BACKWARD_K,
                rows=64,
            )
        )

        if any(
            _same_cell(
                cell,
                c_cell,
            )
            for cell in backward_cells
        ):

            scores[
                "backward_perturbation"
            ] = WEIGHTS[
                "backward_perturbation"
            ]

    # ========================================================================
    # CRAWLER ENCOUNTER DATA
    # ========================================================================

    if crawler_encounters:

        backward_found = False
        forward_found = False
        cloud_found = False

        for encounter in crawler_encounters:

            if not isinstance(
                encounter,
                dict,
            ):
                continue

            encounter_type = str(
                encounter.get(
                    "type",
                    "",
                )
            ).lower()

            if (
                encounter_type
                in {
                    "backward",
                    "backward_perturbation",
                    "backward_d",
                }
            ):

                backward_found = True

            if (
                encounter_type
                in {
                    "forward",
                    "forward_perturbation",
                    "forward_d",
                    "perturbation",
                }
            ):

                forward_found = True

            if (
                encounter_type
                in {
                    "elastic_cloud",
                    "cloud",
                }
            ):

                cloud_found = True

        if backward_found:

            scores[
                "backward_perturbation"
            ] = max(
                scores[
                    "backward_perturbation"
                ],
                WEIGHTS[
                    "backward_perturbation"
                ],
            )

        if forward_found:

            scores[
                "perturbation"
            ] = max(
                scores[
                    "perturbation"
                ],
                WEIGHTS[
                    "perturbation"
                ],
            )

        if cloud_found:

            scores[
                "cloud_encounter"
            ] = WEIGHTS[
                "cloud_encounter"
            ]

    # ========================================================================
    # 3×3
    # ========================================================================

    if (
        q_cell
        and c_cell
    ):

        neighbors = (
            get_three_by_three(
                q_cell
            )
        )

        if any(
            _same_cell(
                cell,
                c_cell,
            )
            for cell in neighbors
        ):

            scores[
                "three_by_three"
            ] = WEIGHTS[
                "three_by_three"
            ]

    # ========================================================================
    # ELASTIC CLOUD
    # ========================================================================

    q_cloud = (
        compute_elastic_cloud(
            query,
            lang,
        )
    )

    if c_cell:

        if any(
            _same_cell(
                cell,
                c_cell,
            )
            for cell in q_cloud
        ):

            scores[
                "elastic_cloud"
            ] = WEIGHTS[
                "elastic_cloud"
            ]

    # ========================================================================
    # FRESHNESS
    # ========================================================================

    scores[
        "freshness"
    ] = (
        min(
            max(
                freshness_score,
                0.0,
            ),
            5.0,
        )
        / 5.0
    ) * WEIGHTS[
        "freshness"
    ]

    # ========================================================================
    # WEAK LEXICAL
    # ========================================================================

    weak_lex = letter_score(
        q_tokens,
        candidate_text,
        lang,
    )

    if weak_lex < 20:

        scores[
            "weak_lexical"
        ] = (
            weak_lex / 20
        ) * WEIGHTS[
            "weak_lexical"
        ]

    # ========================================================================
    # DISTANT RELATIONSHIP
    # ========================================================================

    if (
        scores[
            "relationship"
        ]
        < (
            WEIGHTS[
                "relationship"
            ]
            * 0.3
        )
    ):

        scores[
            "distant_relationship"
        ] = (
            WEIGHTS[
                "distant_relationship"
            ]
            * 0.5
        )

    # ========================================================================
    # CLOUD ENCOUNTER
    # ========================================================================

    if (
        scores[
            "elastic_cloud"
        ] > 0
    ):

        scores[
            "cloud_encounter"
        ] = max(
            scores[
                "cloud_encounter"
            ],
            WEIGHTS[
                "cloud_encounter"
            ] * 0.5,
        )

    # ========================================================================
    # TOTAL
    # ========================================================================

    total = sum(
        scores.values()
    )

    return {
        "total": total,
        "scores": scores,
    }