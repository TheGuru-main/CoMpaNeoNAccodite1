"""
CoMpaNeoN GridCV
================

GridCV is the canonical validation and vector layer for
CoMpaNeoN brain partitions.

Architecture
------------

tokenizer.py
    ↓
placement.py
    ↓
memory_grid.py
    ↓
grid_crawler.py / web_crawler.py
    ↓
crawler_retrieval.py
    ↓
memory_partition.py
    ├── GSP shard routing
    ├── XOR shard routing
    ├── quorum
    ├── domain
    ├── hierarchy
    ├── role
    ├── relevancy
    ├── project trace
    ├── project pin
    ├── project iteration
    ├── state
    ├── project comparison
    └── project-context-aware
            ↓
        grid_cv.py
            ├── partition validation
            ├── deterministic vectors
            ├── partition signatures
            ├── comparison vectors
            ├── state vectors
            └── relationship-compatible signals
            ↓
relation_and_alphabet_matrix.py
            ↓
linguistic / semantic layers
            ↓
brain constituents
            ↓
AI response


RESPONSIBILITIES
----------------

GridCV:

    - validates partition structures
    - preserves partition metadata
    - creates deterministic vectors
    - creates stable partition signatures
    - represents domain information
    - represents hierarchy information
    - represents role information
    - represents relevancy information
    - represents project traces
    - represents project pins
    - represents project iterations
    - represents project state
    - represents list / any / while-loop state
    - compares partitions
    - compares projects
    - supports cross-project comparison
    - produces project-context-aware vectors
    - exposes signals for relationship matrix analysis

GridCV does NOT own:

    - tokenization
    - language detection
    - linguistic placement
    - GSP mathematics
    - crawler traversal
    - Elastic Cloud
    - external crawling
    - document indexing
    - MemoryGrid storage
    - shard selection authority
    - ranking
    - prompt generation
    - tool execution
    - AI response generation


IMPORTANT
---------

memory_partition.py remains the owner of partition routing.

GridCV does not independently decide where memory belongs.

It validates and represents the partition result.

This prevents GridCV from contradicting:

    tokenizer.py
    placement.py
    memory_grid.py
    grid_crawler.py
    web_crawler.py
    memory_partition.py
"""

from __future__ import annotations

import hashlib
import json
import math

from collections import Counter
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

GRID_CV_VERSION = "1.0"

DEFAULT_VECTOR_SIZE = 64

DEFAULT_COMPARE_LIMIT = 64


# ============================================================================
# CANONICAL PARTITION FIELDS
# ============================================================================

PARTITION_FIELDS = (
    "domain",
    "hierarchy",
    "role",
    "relevancy",
    "project_trace",
    "project_pin",
    "project_iteration",
    "state",
    "project_context_aware",
)


# ============================================================================
# HELPERS
# ============================================================================

def _stable_json(
    value: Any,
) -> str:
    """
    Convert arbitrary supported data into a deterministic string.
    """

    try:

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            default=str,
        )

    except Exception:

        return str(
            value
        )


def _stable_hash(
    value: Any,
) -> str:
    """
    SHA-256 deterministic identity.

    GridCV uses hashes for vector generation and signatures.

    This is not a replacement for GSP/XOR partition routing.
    """

    payload = _stable_json(
        value
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


def _safe_list(
    value: Any,
) -> List[Any]:
    """
    Normalize a value into a list.
    """

    if value is None:

        return []

    if isinstance(
        value,
        list,
    ):

        return value

    if isinstance(
        value,
        tuple,
    ):

        return list(
            value
        )

    if isinstance(
        value,
        set,
    ):

        return sorted(
            value,
            key=str,
        )

    return [
        value
    ]


def _safe_dict(
    value: Any,
) -> Dict[str, Any]:
    """
    Normalize mapping-like data.
    """

    if isinstance(
        value,
        dict,
    ):

        return dict(
            value
        )

    return {}


def _normalise_text(
    value: Any,
) -> str:

    return (
        str(
            value
        )
        .strip()
        .lower()
    )


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            float(
                value
            ),
        ),
    )


# ============================================================================
# DETERMINISTIC VECTOR
# ============================================================================

def deterministic_vector(
    value: Any,
    size: int = DEFAULT_VECTOR_SIZE,
) -> List[float]:
    """
    Convert a value into a deterministic vector.

    No randomness is used.

    The same value always produces the same vector.
    """

    size = max(
        1,
        int(size),
    )

    digest = bytes.fromhex(
        _stable_hash(
            value
        )
    )

    vector = []

    for index in range(
        size
    ):

        byte = digest[
            index % len(
                digest
            )
        ]

        vector.append(
            round(
                byte / 255.0,
                8,
            )
        )

    return vector


# ============================================================================
# VECTOR OPERATIONS
# ============================================================================

def vector_magnitude(
    vector: Sequence[
        float
    ],
) -> float:

    return math.sqrt(
        sum(
            float(value)
            * float(value)
            for value in vector
        )
    )


def normalize_vector(
    vector: Sequence[
        float
    ],
) -> List[float]:

    magnitude = vector_magnitude(
        vector
    )

    if magnitude == 0:

        return [
            0.0
            for _ in vector
        ]

    return [
        float(value)
        / magnitude
        for value in vector
    ]


def cosine_similarity(
    vector_a: Sequence[
        float
    ],
    vector_b: Sequence[
        float
    ],
) -> float:
    """
    Return cosine similarity in the range:

        0.0 - 100.0
    """

    if not vector_a:
        return 0.0

    if not vector_b:
        return 0.0

    size = min(
        len(vector_a),
        len(vector_b),
    )

    if size == 0:

        return 0.0

    a = list(
        vector_a[:size]
    )

    b = list(
        vector_b[:size]
    )

    magnitude_a = vector_magnitude(
        a
    )

    magnitude_b = vector_magnitude(
        b
    )

    if (
        magnitude_a == 0
        or magnitude_b == 0
    ):

        return 0.0

    dot = sum(
        float(a[index])
        * float(b[index])
        for index in range(
            size
        )
    )

    similarity = dot / (
        magnitude_a
        * magnitude_b
    )

    return round(
        _clamp(
            similarity,
            -1.0,
            1.0,
        )
        * 100.0,
        8,
    )


def vector_average(
    vectors: Sequence[
        Sequence[float]
    ],
) -> List[float]:

    vectors = [
        list(vector)
        for vector in vectors
        if vector
    ]

    if not vectors:

        return []

    size = min(
        len(vector)
        for vector in vectors
    )

    if size == 0:

        return []

    result = []

    for index in range(
        size
    ):

        value = sum(
            float(vector[index])
            for vector in vectors
        )

        result.append(
            value
            / len(vectors)
        )

    return result


# ============================================================================
# PARTITION VALIDATION
# ============================================================================

class GridCV:
    """
    CoMpaNeoN Grid Cross-Validation and Vector layer.

    GridCV receives partition information.

    It does not independently create partition routing.
    """

    def __init__(
        self,
        vector_size: int = (
            DEFAULT_VECTOR_SIZE
        ),
    ) -> None:

        self.vector_size = max(
            1,
            int(
                vector_size
            ),
        )

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate_partition(
        self,
        partition: Mapping[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:
        """
        Validate a memory partition.

        Validation is structural.

        Routing remains the responsibility of memory_partition.py.
        """

        if not isinstance(
            partition,
            Mapping,
        ):

            return {
                "valid": False,
                "errors": [
                    "partition must be a mapping"
                ],
                "missing": list(
                    PARTITION_FIELDS
                ),
                "present": [],
            }

        errors = []

        present = []

        missing = []

        for field in PARTITION_FIELDS:

            if field in partition:

                present.append(
                    field
                )

            else:

                missing.append(
                    field
                )

        # --------------------------------------------------------------------
        # GSP ROUTING
        # --------------------------------------------------------------------

        if (
            "gsp"
            not in partition
            and
            "gsp_shard"
            not in partition
            and
            "start_row"
            not in partition
        ):

            errors.append(
                "missing GSP partition routing metadata"
            )

        # --------------------------------------------------------------------
        # XOR ROUTING
        # --------------------------------------------------------------------

        if (
            "xor"
            not in partition
            and
            "xor_shard"
            not in partition
        ):

            errors.append(
                "missing XOR partition routing metadata"
            )

        # --------------------------------------------------------------------
        # QUORUM
        # --------------------------------------------------------------------

        if (
            "quorum"
            not in partition
        ):

            errors.append(
                "missing quorum metadata"
            )

        return {
            "valid": (
                len(errors) == 0
            ),
            "errors": errors,
            "missing": missing,
            "present": present,
        }

    # ========================================================================
    # PARTITION SIGNATURE
    # ========================================================================

    def partition_signature(
        self,
        partition: Mapping[
            str,
            Any,
        ],
    ) -> str:
        """
        Stable partition identity.

        This identifies the resulting partition state.

        It does not replace GSP/XOR identity.
        """

        payload = {
            key: partition.get(
                key
            )
            for key in (
                "gsp",
                "gsp_shard",
                "start_row",
                "xor",
                "xor_shard",
                "quorum",
                "domain",
                "hierarchy",
                "role",
                "relevancy",
                "project_trace",
                "project_pin",
                "project_iteration",
                "state",
                "project_context_aware",
            )
        }

        return _stable_hash(
            payload
        )

    # ========================================================================
    # DOMAIN VECTOR
    # ========================================================================

    def domain_vector(
        self,
        domain: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "domain": domain,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # HIERARCHY VECTOR
    # ========================================================================

    def hierarchy_vector(
        self,
        hierarchy: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "hierarchy": hierarchy,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # ROLE VECTOR
    # ========================================================================

    def role_vector(
        self,
        role: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "role": role,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # RELEVANCY VECTOR
    # ========================================================================

    def relevancy_vector(
        self,
        relevancy: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "relevancy": relevancy,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # PROJECT TRACE VECTOR
    # ========================================================================

    def project_trace_vector(
        self,
        trace: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "project_trace": trace,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # PROJECT PIN VECTOR
    # ========================================================================

    def project_pin_vector(
        self,
        pin: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "project_pin": pin,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # PROJECT ITERATION VECTOR
    # ========================================================================

    def project_iteration_vector(
        self,
        iteration: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "project_iteration": iteration,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # STATE SIGNAL
    # ========================================================================

    def state_signal(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Represent project execution state.

        Includes:

            list state
            any state
            while-loop state

        These are represented as state information.

        GridCV does not execute arbitrary loops.
        """

        state_data = _safe_dict(
            state
        )

        values = _safe_list(
            state_data.get(
                "list",
                state_data.get(
                    "items",
                    [],
                ),
            )
        )

        any_value = state_data.get(
            "any"
        )

        while_state = state_data.get(
            "while"
        )

        completed = state_data.get(
            "completed"
        )

        active = state_data.get(
            "active"
        )

        return {
            "list": values,
            "list_count": len(
                values
            ),
            "any": any_value,
            "any_truthy": bool(
                any_value
            ),
            "while": while_state,
            "while_active": bool(
                while_state
            ),
            "completed": completed,
            "active": active,
        }

    # ========================================================================
    # STATE VECTOR
    # ========================================================================

    def state_vector(
        self,
        state: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "state": self.state_signal(
                    state
                ),
            },
            size=self.vector_size,
        )

    # ========================================================================
    # PROJECT CONTEXT VECTOR
    # ========================================================================

    def project_context_vector(
        self,
        context: Any,
    ) -> List[float]:

        return deterministic_vector(
            {
                "project_context_aware": context,
            },
            size=self.vector_size,
        )

    # ========================================================================
    # ROUTING VECTOR
    # ========================================================================

    def routing_vector(
        self,
        partition: Mapping[
            str,
            Any,
        ],
    ) -> List[float]:
        """
        Represent routing metadata without taking ownership of routing.
        """

        routing = {
            "gsp": (
                partition.get("gsp")
                or partition.get(
                    "gsp_shard"
                )
                or partition.get(
                    "start_row"
                )
            ),

            "xor": (
                partition.get("xor")
                or partition.get(
                    "xor_shard"
                )
            ),

            "quorum": partition.get(
                "quorum"
            ),
        }

        return deterministic_vector(
            routing,
            size=self.vector_size,
        )

 # ========================================================================
    # FULL PARTITION VECTOR
    # ========================================================================

    def partition_vector(
        self,
        partition: Mapping[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:
        """
        Build the complete GridCV representation.

        This is the primary bridge from memory_partition.py
        into downstream brain layers.
        """

        validation = self.validate_partition(
            partition
        )

        vectors = {

            "routing": self.routing_vector(
                partition
            ),

            "domain": self.domain_vector(
                partition.get(
                    "domain"
                )
            ),

            "hierarchy": self.hierarchy_vector(
                partition.get(
                    "hierarchy"
                )
            ),

            "role": self.role_vector(
                partition.get(
                    "role"
                )
            ),

            "relevancy": self.relevancy_vector(
                partition.get(
                    "relevancy"
                )
            ),

            "project_trace": (
                self.project_trace_vector(
                    partition.get(
                        "project_trace"
                    )
                )
            ),

            "project_pin": (
                self.project_pin_vector(
                    partition.get(
                        "project_pin"
                    )
                )
            ),

            "project_iteration": (
                self.project_iteration_vector(
                    partition.get(
                        "project_iteration"
                    )
                )
            ),

            "state": self.state_vector(
                partition.get(
                    "state"
                )
            ),

            "project_context_aware": (
                self.project_context_vector(
                    partition.get(
                        "project_context_aware"
                    )
                )
            ),
        }

        composite = normalize_vector(
            vector_average(
                list(
                    vectors.values()
                )
            )
        )

        signature = self.partition_signature(
            partition
        )

        return {

            "validation": validation,

            "signature": signature,

            "vector_size": self.vector_size,

            "vectors": vectors,

            "composite_vector": composite,

            "state_signal": (
                self.state_signal(
                    partition.get(
                        "state"
                    )
                )
            ),

            "partition": dict(
                partition
            ),
        }

    # ========================================================================
    # VECTOR SIMILARITY
    # ========================================================================

    def compare_vectors(
        self,
        vector_a: Sequence[
            float
        ],
        vector_b: Sequence[
            float
        ],
    ) -> float:

        return cosine_similarity(
            vector_a,
            vector_b,
        )

    # ========================================================================
    # FIELD COMPARISON
    # ========================================================================

    def compare_partition_fields(
        self,
        partition_a: Mapping[
            str,
            Any,
        ],
        partition_b: Mapping[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:

        results = {}

        for field in PARTITION_FIELDS:

            vector_a = deterministic_vector(
                partition_a.get(
                    field
                ),
                size=self.vector_size,
            )

            vector_b = deterministic_vector(
                partition_b.get(
                    field
                ),
                size=self.vector_size,
            )

            results[field] = {
                "score": self.compare_vectors(
                    vector_a,
                    vector_b,
                ),

                "a": partition_a.get(
                    field
                ),

                "b": partition_b.get(
                    field
                ),
            }

        return results

    # ========================================================================
    # PARTITION COMPARISON
    # ========================================================================

    def compare_partitions(
        self,
        partition_a: Mapping[
            str,
            Any,
        ],
        partition_b: Mapping[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:
        """
        Compare two brain partitions.

        Comparison does not alter either partition.
        """

        a = self.partition_vector(
            partition_a
        )

        b = self.partition_vector(
            partition_b
        )

        field_scores = (
            self.compare_partition_fields(
                partition_a,
                partition_b,
            )
        )

        composite_score = (
            self.compare_vectors(
                a[
                    "composite_vector"
                ],
                b[
                    "composite_vector"
                ],
            )
        )

        return {

            "partition_a": a[
                "signature"
            ],

            "partition_b": b[
                "signature"
            ],

            "same_partition": (
                a["signature"]
                == b["signature"]
            ),

            "composite_score": (
                composite_score
            ),

            "field_scores": (
                field_scores
            ),
        }

    # ========================================================================
    # PROJECT IDENTITY
    # ========================================================================

    def project_identity(
        self,
        partition: Mapping[
            str,
            Any,
        ],
    ) -> str:
        """
        Resolve project identity from the partition metadata.
        """

        for key in (
            "project_id",
            "project_pin",
            "project",
            "project_trace",
        ):

            value = partition.get(
                key
            )

            if value:

                return str(
                    value
                )

        return ""

    # ========================================================================
    # PROJECT COMPARISON
    # ========================================================================

    def compare_projects(
        self,
        project_a: Sequence[
            Mapping[str, Any]
        ],
        project_b: Sequence[
            Mapping[str, Any]
        ],
    ) -> Dict[str, Any]:
        """
        Compare two project partition collections.
        """

        vectors_a = []

        vectors_b = []

        for partition in project_a:

            result = self.partition_vector(
                partition
            )

            vectors_a.append(
                result[
                    "composite_vector"
                ]
            )

        for partition in project_b:

            result = self.partition_vector(
                partition
            )

            vectors_b.append(
                result[
                    "composite_vector"
                ]
            )

        project_vector_a = normalize_vector(
            vector_average(
                vectors_a
            )
        )

        project_vector_b = normalize_vector(
            vector_average(
                vectors_b
            )
        )

        score = self.compare_vectors(
            project_vector_a,
            project_vector_b,
        )

        return {

            "project_a_count": len(
                project_a
            ),

            "project_b_count": len(
                project_b
            ),

            "project_a_vector": (
                project_vector_a
            ),

            "project_b_vector": (
                project_vector_b
            ),

            "comparison_score": (
                score
            ),
        }

    # ========================================================================
    # CROSS-PROJECT COMPARISON
    # ========================================================================

    def cross_project_compare(
        self,
        source_project: Sequence[
            Mapping[str, Any]
        ],
        target_projects: Mapping[
            str,
            Sequence[
                Mapping[str, Any]
            ],
        ],
        limit: int = (
            DEFAULT_COMPARE_LIMIT
        ),
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Compare one project against multiple projects.
        """

        source_vectors = []

        for partition in source_project:

            result = self.partition_vector(
                partition
            )

            source_vectors.append(
                result[
                    "composite_vector"
                ]
            )

        source_vector = normalize_vector(
            vector_average(
                source_vectors
            )
        )

        results = []

        for project_id, partitions in (
            target_projects.items()
        ):

            target_vectors = []

            for partition in partitions:

                result = self.partition_vector(
                    partition
                )

                target_vectors.append(
                    result[
                        "composite_vector"
                    ]
                )

            target_vector = normalize_vector(
                vector_average(
                    target_vectors
                )
            )

            score = self.compare_vectors(
                source_vector,
                target_vector,
            )

            results.append({

                "project_id": (
                    str(project_id)
                ),

                "partition_count": (
                    len(partitions)
                ),

                "score": score,

                "vector": target_vector,
            })

        results.sort(
            key=lambda item: item[
                "score"
            ],
            reverse=True,
        )

        return results[
            :max(
                1,
                int(limit),
            )
        ]

    # ========================================================================
    # PROJECT CONTEXT AWARENESS
    # ========================================================================

    def project_context_aware(
        self,
        partition: Mapping[
            str,
            Any,
        ],
        project_partitions: Sequence[
            Mapping[str, Any]
        ],
    ) -> Dict[str, Any]:
        """
        Compare one partition against its own project context.

        This is not ranking.

        It establishes how the partition relates to the context
        of its own project.
        """

        current = self.partition_vector(
            partition
        )

        context_vectors = []

        for item in project_partitions:

            if item is partition:

                continue

            result = self.partition_vector(
                item
            )

            context_vectors.append(
                result[
                    "composite_vector"
                ]
            )

        context_vector = normalize_vector(
            vector_average(
                context_vectors
            )
        )

        context_score = (
            self.compare_vectors(
                current[
                    "composite_vector"
                ],
                context_vector,
            )
            if context_vector
            else 0.0
        )

        return {

            "partition_signature": (
                current[
                    "signature"
                ]
            ),

            "project_context_score": (
                context_score
            ),

            "context_partition_count": (
                len(context_vectors)
            ),

            "partition_vector": (
                current[
                    "composite_vector"
                ]
            ),

            "project_context_vector": (
                context_vector
            ),
        }

    # ========================================================================
    # RELATIONSHIP SIGNAL
    # ========================================================================

    def relationship_signal(
        self,
        partition: Mapping[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:
        """
        Produce a relationship-compatible signal.

        relation_and_alphabet_matrix.py can consume this without
        taking ownership away from memory_partition.py.
        """

        partition_data = (
            self.partition_vector(
                partition
            )
        )

        vectors = partition_data[
            "vectors"
        ]

        return {

            "signature": (
                partition_data[
                    "signature"
                ]
            ),

            "vector": (
                partition_data[
                    "composite_vector"
                ]
            ),

            "domain_vector": (
                vectors[
                    "domain"
                ]
            ),

            "hierarchy_vector": (
                vectors[
                    "hierarchy"
                ]
            ),

            "role_vector": (
                vectors[
                    "role"
                ]
            ),

            "relevancy_vector": (
                vectors[
                    "relevancy"
                ]
            ),

            "project_trace_vector": (
                vectors[
                    "project_trace"
                ]
            ),

            "project_pin_vector": (
                vectors[
                    "project_pin"
                ]
            ),

            "project_iteration_vector": (
                vectors[
                    "project_iteration"
                ]
            ),

            "state_vector": (
                vectors[
                    "state"
                ]
            ),

            "project_context_vector": (
                vectors[
                    "project_context_aware"
                ]
            ),

            "routing_vector": (
                vectors[
                    "routing"
                ]
            ),

            "state_signal": (
                partition_data[
                    "state_signal"
                ]
            ),
        }

    # ========================================================================
    # RELATIONSHIP COMPARISON
    # ========================================================================

    def relationship_between_partitions(
        self,
        partition_a: Mapping[
            str,
            Any,
        ],
        partition_b: Mapping[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:
        """
        Return GridCV relationship information for the relationship
        matrix layer.
        """

        signal_a = self.relationship_signal(
            partition_a
        )

        signal_b = self.relationship_signal(
            partition_b
        )

        signals = {}

        for name in (
            "vector",
            "domain_vector",
            "hierarchy_vector",
            "role_vector",
            "relevancy_vector",
            "project_trace_vector",
            "project_pin_vector",
            "project_iteration_vector",
            "state_vector",
            "project_context_vector",
            "routing_vector",
        ):

            signals[name] = (
                self.compare_vectors(
                    signal_a[name],
                    signal_b[name],
                )
            )

        overall = sum(
            signals.values()
        ) / len(
            signals
        )

        return {

            "partition_a": (
                signal_a[
                    "signature"
                ]
            ),

            "partition_b": (
                signal_b[
                    "signature"
                ]
            ),

            "signals": signals,

            "overall": round(
                overall,
                8,
            ),
        }


# ============================================================================
# FUNCTIONAL API
# ============================================================================

def validate_partition(
    partition: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:

    return GridCV().validate_partition(
        partition
    )


def partition_vector(
    partition: Mapping[
        str,
        Any,
    ],
    vector_size: int = (
        DEFAULT_VECTOR_SIZE
    ),
) -> Dict[str, Any]:

    return GridCV(
        vector_size=vector_size
    ).partition_vector(
        partition
    )


def compare_partitions(
    partition_a: Mapping[
        str,
        Any,
    ],
    partition_b: Mapping[
        str,
        Any,
    ],
    vector_size: int = (
        DEFAULT_VECTOR_SIZE
    ),
) -> Dict[str, Any]:

    return GridCV(
        vector_size=vector_size
    ).compare_partitions(
        partition_a,
        partition_b,
    )


def relationship_signal(
    partition: Mapping[
        str,
        Any,
    ],
    vector_size: int = (
        DEFAULT_VECTOR_SIZE
    ),
) -> Dict[str, Any]:

    return GridCV(
        vector_size=vector_size
    ).relationship_signal(
        partition
    )


def relationship_between_partitions(
    partition_a: Mapping[
        str,
        Any,
    ],
    partition_b: Mapping[
        str,
        Any,
    ],
    vector_size: int = (
        DEFAULT_VECTOR_SIZE
    ),
) -> Dict[str, Any]:

    return GridCV(
        vector_size=vector_size
    ).relationship_between_partitions(
        partition_a,
        partition_b,
    )

# ============================================================================
# DEVELOPMENT TEST
# ============================================================================

if __name__ == "__main__":

    partition_a = {

        "gsp": {
            "start_row": 17,
            "column": 12,
        },

        "xor": {
            "shard": 9,
        },

        "quorum": {
            "members": [
                1,
                2,
                3,
            ],
            "required": 2,
        },

        "domain": (
            "commerce"
        ),

        "hierarchy": (
            "project"
        ),

        "role": (
            "analysis"
        ),

        "relevancy": 0.91,

        "project_trace": [
            "root",
            "architecture",
            "memory",
        ],

        "project_pin": (
            "companeon"
        ),

        "project_iteration": 4,

        "state": {

            "list": [
                "memory",
                "rules",
                "prompts",
            ],

            "any": True,

            "while": (
                "architecture_active"
            ),

            "active": True,

            "completed": False,
        },

        "project_context_aware": {
            "current_project": (
                "CoMpaNeoN"
            ),
            "phase": (
                "brain_partition"
            ),
        },
    }

    partition_b = {

        **partition_a,

        "role": (
            "retrieval"
        ),

        "relevancy": 0.82,

        "project_iteration": 5,
    }

    cv = GridCV()

    print(
        "Validation:"
    )

    print(
        cv.validate_partition(
            partition_a
        )
    )

    print(
        "\nPartition signature:"
    )

    print(
        cv.partition_signature(
            partition_a
        )
    )

    print(
        "\nPartition comparison:"
    )

    print(
        json.dumps(
            cv.compare_partitions(
                partition_a,
                partition_b,
            ),
            indent=2,
        )
    )

    print(
        "\nRelationship signal:"
    )

    print(
        json.dumps(
            cv.relationship_between_partitions(
                partition_a,
                partition_b,
            ),
            indent=2,
        )
    )
            