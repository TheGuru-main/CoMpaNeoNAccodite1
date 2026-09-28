"""
CoMpaNeoN Memory Partition
==========================

Memory partitioning and contextual memory routing layer.

ARCHITECTURE
------------

                        MemoryGrid
                            │
                            ▼
                    MemoryPartition
                            │
             ┌──────────────┼──────────────┐
             │              │              │
          Domain         Project        Context
             │              │              │
             ▼              ▼              ▼
         Hierarchy       Trace/Pins     Relevancy
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                      GSP XOR Quorum
                            │
                            ▼
                       GridCV intact
                            │
                            ▼
                    Partition Retrieval
                            │
                            ▼
                 Higher Brain Constituents


RESPONSIBILITIES
----------------

MemoryPartition owns:

    - partition construction
    - deterministic partition identity
    - GSP XOR quorum sharding
    - domain partitioning
    - hierarchy partitioning
    - role partitioning
    - relevancy partitioning
    - project traces
    - project pins
    - project iteration
    - project state inspection
    - list state
    - any state
    - while-loop state
    - state comparison
    - cross-project comparison
    - project-context awareness
    - partition retrieval
    - GridCV validation/comparison

MemoryPartition does NOT own:

    - tokenization
    - language mathematics
    - alphabet mathematics
    - word placement
    - GSP linguistic placement
    - crawler traversal
    - external acquisition
    - ranking
    - prompt generation
    - rules
    - tool execution
    - AI response generation

AUTHORITIES
-----------

tokenizer.py
    Linguistic authority.

keyboard.py / placement.py
    Canonical GSP placement authority.

MemoryGrid
    Canonical storage/indexing authority.

GridCrawler
    Grid traversal/router authority.

WebCrawler
    External knowledge acquisition authority.

GridCV
    Grid comparison/validation authority.

MemoryPartition
    Memory partitioning and contextual sharding authority.
"""

from __future__ import annotations

import hashlib
import json

from dataclasses import dataclass, field

from datetime import datetime, timezone

from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
)


# ============================================================================
# GRIDCV
# ============================================================================

try:
    from grid_cv import GridCV

except ImportError:

    GridCV = None


# ============================================================================
# MEMORYGRID
# ============================================================================

try:
    from memory_grid import MemoryGrid

except ImportError:

    MemoryGrid = Any


# ============================================================================
# GRID CRAWLER
# ============================================================================

try:
    from grid_crawler import GridCrawler

except ImportError:

    GridCrawler = None


# ============================================================================
# CRAWLER RETRIEVAL
# ============================================================================

try:
    from crawler_retrieval import CrawlerRetrieval

except ImportError:

    CrawlerRetrieval = None


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_ROWS = 64

DEFAULT_COLS = 46

DEFAULT_RELEVANCY = 0.0

DEFAULT_ROLE = "general"

DEFAULT_DOMAIN = "general"

DEFAULT_HIERARCHY = "root"

DEFAULT_PROJECT_STATE = "active"

DEFAULT_PARTITION_LIMIT = 250


# ============================================================================
# TIME
# ============================================================================

def utc_now() -> str:
    """
    Return current UTC timestamp.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_text(
    value: Any,
) -> str:
    """
    Normalize arbitrary values into deterministic strings.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


# ============================================================================
# STABLE HASH
# ============================================================================

def stable_hash(
    value: Any,
) -> str:
    """
    Create deterministic SHA-256 identity.
    """

    if isinstance(
        value,
        (
            dict,
            list,
            tuple,
            set,
        ),
    ):

        try:

            value = json.dumps(
                value,
                sort_keys=True,
                default=str,
            )

        except Exception:

            value = str(
                value
            )

    return hashlib.sha256(
        str(value)
        .encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================================
# INTEGER HASH
# ============================================================================

def stable_int(
    value: Any,
) -> int:
    """
    Deterministic integer representation.
    """

    digest = stable_hash(
        value
    )

    return int(
        digest[:16],
        16,
    )


# ============================================================================
# XOR
# ============================================================================

def xor_values(
    *values: int,
) -> int:
    """
    XOR arbitrary integer values.
    """

    result = 0

    for value in values:

        result ^= int(
            value
        )

    return result


# ============================================================================
# QUORUM
# ============================================================================

def quorum_value(
    values: Iterable[int],
) -> int:
    """
    Deterministic quorum value.

    The quorum is formed from the XOR of
    all participating values.
    """

    result = 0

    for value in values:

        result ^= int(
            value
        )

    return result


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class PartitionKey:
    """
    Canonical partition identity.
    """

    domain: str = DEFAULT_DOMAIN

    hierarchy: str = DEFAULT_HIERARCHY

    role: str = DEFAULT_ROLE

    project_id: str = ""

    project_context: str = ""

    relevancy_bucket: int = 0


@dataclass
class ProjectTrace:
    """
    Persistent project trace.

    Tracks how knowledge enters and evolves
    within a project.
    """

    project_id: str

    trace_id: str

    created_at: str = field(
        default_factory=utc_now
    )

    updated_at: str = field(
        default_factory=utc_now
    )

    events: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )


@dataclass
class ProjectPin:
    """
    Explicit persistent project memory pin.
    """

    project_id: str

    pin_id: str

    value: Any

    created_at: str = field(
        default_factory=utc_now
    )

    metadata: Dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )


@dataclass
class ProjectIteration:
    """
    Tracks iterative project development.
    """

    project_id: str

    iteration: int

    state: str

    created_at: str = field(
        default_factory=utc_now
    )

    metadata: Dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )


# ============================================================================
# MEMORY PARTITION
# ============================================================================

class MemoryPartition:
    """
    CoMpaNeoN memory partitioning layer.

    Memory enters through MemoryGrid.

    This layer does not replace MemoryGrid.

    It creates deterministic contextual
    partitions around already-indexed
    knowledge and memory.
    """

    # ======================================================================
    # INITIALIZATION
    # ======================================================================

    def __init__(
        self,
        memory_grid: MemoryGrid,
        grid_cv: Optional[
            Any
        ] = None,
        grid_crawler: Optional[
            Any
        ] = None,
        crawler_retrieval: Optional[
            Any
        ] = None,
        rows: int = DEFAULT_ROWS,
        cols: int = DEFAULT_COLS,
    ) -> None:

        self.memory = (
            memory_grid
        )

        self.rows = int(
            getattr(
                memory_grid,
                "rows",
                rows,
            )
        )

        self.cols = int(
            getattr(
                memory_grid,
                "cols",
                cols,
            )
        )

        # --------------------------------------------------------------
        # GridCV
        # --------------------------------------------------------------

        if grid_cv is not None:

            self.grid_cv = (
                grid_cv
            )

        elif GridCV is not None:

            try:

                self.grid_cv = (
                    GridCV()
                )

            except Exception:

                self.grid_cv = (
                    None
                )

        else:

            self.grid_cv = (
                None
            )

        # --------------------------------------------------------------
        # GridCrawler
        # --------------------------------------------------------------

        if grid_crawler is not None:

            self.grid_crawler = (
                grid_crawler
            )

        elif GridCrawler is not None:

            try:

                self.grid_crawler = (
                    GridCrawler(
                        memory_grid
                    )
                )

            except Exception:

                self.grid_crawler = (
                    None
                )

        else:

            self.grid_crawler = (
                None
            )

        # --------------------------------------------------------------
        # Crawler Retrieval
        # --------------------------------------------------------------

        if crawler_retrieval is not None:

            self.crawler_retrieval = (
                crawler_retrieval
            )

        elif CrawlerRetrieval is not None:

            try:

                self.crawler_retrieval = (
                    CrawlerRetrieval(
                        memory_grid
                    )
                )

            except Exception:

                self.crawler_retrieval = (
                    None
                )

        else:

            self.crawler_retrieval = (
                None
            )

        # --------------------------------------------------------------
        # PARTITION STORAGE
        # --------------------------------------------------------------

        self.partitions: Dict[
            str,
            List[
                Dict[str, Any]
            ],
        ] = {}

        self.partition_metadata: Dict[
            str,
            Dict[str, Any],
        ] = {}

        # --------------------------------------------------------------
        # PROJECTS
        # --------------------------------------------------------------

        self.project_traces: Dict[
            str,
            ProjectTrace,
        ] = {}

        self.project_pins: Dict[
            str,
            Dict[
                str,
                ProjectPin,
            ],
        ] = {}

        self.project_iterations: Dict[
            str,
            List[
                ProjectIteration
            ],
        ] = {}

        self.project_states: Dict[
            str,
            Dict[
                str,
                Any,
            ],
        ] = {}

    # ======================================================================
    # GRID DIMENSIONS
    # ======================================================================

    def grid_dimensions(
        self,
    ) -> Tuple[
        int,
        int,
    ]:
        """
        Return MemoryGrid dimensions.

        Current architecture:

            64 rows
            46 columns

        The partition layer follows
        MemoryGrid dimensions rather
        than creating its own grid.
        """

        return (
            self.rows,
            self.cols,
        )

    # ======================================================================
    # RELEVANCY BUCKET
    # ======================================================================

    def relevancy_bucket(
        self,
        relevancy: float,
        buckets: int = 10,
    ) -> int:
        """
        Convert relevancy into
        deterministic partition bucket.
        """

        value = float(
            relevancy
        )

        value = max(
            0.0,
            min(
                1.0,
                value,
            ),
        )

        return min(
            buckets - 1,
            int(
                value * buckets
            ),
        )

    # ======================================================================
    # BUILD PARTITION KEY
    # ======================================================================

    def build_partition_key(
        self,
        *,
        domain: str = DEFAULT_DOMAIN,
        hierarchy: str = DEFAULT_HIERARCHY,
        role: str = DEFAULT_ROLE,
        project_id: str = "",
        project_context: str = "",
        relevancy: float = (
            DEFAULT_RELEVANCY
        ),
    ) -> PartitionKey:
        """
        Build canonical contextual partition key.
        """

        return PartitionKey(
            domain=(
                normalize_text(
                    domain
                )
                or DEFAULT_DOMAIN
            ),

            hierarchy=(
                normalize_text(
                    hierarchy
                )
                or DEFAULT_HIERARCHY
            ),

            role=(
                normalize_text(
                    role
                )
                or DEFAULT_ROLE
            ),

            project_id=(
                normalize_text(
                    project_id
                )
            ),

            project_context=(
                normalize_text(
                    project_context
                )
            ),

            relevancy_bucket=(
                self.relevancy_bucket(
                    relevancy
                )
            ),
        )

    # ======================================================================
    # PARTITION ID
    # ======================================================================

    def partition_id(
        self,
        key: PartitionKey,
    ) -> str:
        """
        Deterministic partition identifier.
        """

        payload = {

            "domain":
                key.domain,

            "hierarchy":
                key.hierarchy,

            "role":
                key.role,

            "project_id":
                key.project_id,

            "project_context":
                key.project_context,

            "relevancy_bucket":
                key.relevancy_bucket,

        }

        return stable_hash(
            payload
        )

    # ======================================================================
    # GSP XOR QUORUM
    # ======================================================================

    def gsp_xor_quorum(
        self,
        *,
        domain: str,
        hierarchy: str,
        role: str,
        relevancy_bucket: int,
        project_id: str = "",
        project_context: str = "",
    ) -> Dict[
        str,
        int,
    ]:
        """
        Produce deterministic shard routing
        from contextual dimensions.

        This does not replace GSP placement.

        It determines which contextual
        memory partition/shard should own
        the record after MemoryGrid has
        handled canonical storage.

        Quorum dimensions:

            domain
            hierarchy
            role
            relevancy
            project
            project context

        The dimensions are XORed into a
        deterministic quorum value.
        """

        domain_value = stable_int(
            domain
        )

        hierarchy_value = stable_int(
            hierarchy
        )

        role_value = stable_int(
            role
        )

        relevancy_value = int(
            relevancy_bucket
        )

        project_value = stable_int(
            project_id
        )

        context_value = stable_int(
            project_context
        )

        quorum = quorum_value(
            [
                domain_value,
                hierarchy_value,
                role_value,
                relevancy_value,
                project_value,
                context_value,
            ]
        )

        xor = xor_values(
            domain_value,
            hierarchy_value,
            role_value,
            relevancy_value,
            project_value,
            context_value,
        )

        rows, cols = (
            self.grid_dimensions()
        )

        shard_row = (
            quorum % rows
        ) + 1

        shard_col = (
            xor % cols
        )

        return {

            "quorum":
                quorum,

            "xor":
                xor,

            "row":
                shard_row,

            "col":
                shard_col,

        }

    # ======================================================================
    # PROJECT TRACE
    # ======================================================================

    def ensure_project_trace(
        self,
        project_id: str,
    ) -> ProjectTrace:
        """
        Ensure a project trace exists.
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        if project_id not in (
            self.project_traces
        ):

            trace = ProjectTrace(

                project_id=
                    project_id,

                trace_id=
                    stable_hash(
                        {
                            "project":
                                project_id
                        }
                    ),

            )

            self.project_traces[
                project_id
            ] = trace

        return self.project_traces[
            project_id
        ]

    # ======================================================================
    # ADD PROJECT TRACE EVENT
    # ======================================================================

    def trace_project(
        self,
        project_id: str,
        event: Dict[
            str,
            Any,
        ],
    ) -> ProjectTrace:
        """
        Append deterministic project trace event.
        """

        trace = (
            self.ensure_project_trace(
                project_id
            )
        )

        trace.events.append({

            "timestamp":
                utc_now(),

            "event":
                dict(
                    event
                ),

        })

        trace.updated_at = (
            utc_now()
        )

        return trace

    # ======================================================================
    # PROJECT PIN
    # ======================================================================

    def pin_project(
        self,
        project_id: str,
        value: Any,
        pin_id: Optional[
            str
        ] = None,
        metadata: Optional[
            Dict[
                str,
                Any,
            ]
        ] = None,
    ) -> ProjectPin:
        """
        Pin persistent contextual memory
        to a project.
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        if pin_id is None:

            pin_id = stable_hash(
                {
                    "project":
                        project_id,

                    "value":
                        value,
                }
            )

        pin = ProjectPin(

            project_id=
                project_id,

            pin_id=
                pin_id,

            value=
                value,

            metadata=
                metadata
                or {},

        )

        if project_id not in (
            self.project_pins
        ):

            self.project_pins[
                project_id
            ] = {}

        self.project_pins[
            project_id
        ][
            pin_id
        ] = pin

        self.trace_project(
            project_id,
            {

                "type":
                    "pin",

                "pin_id":
                    pin_id,

            },
        )

        return pin

    # ======================================================================
    # GET PROJECT PINS
    # ======================================================================

    def get_project_pins(
        self,
        project_id: str,
    ) -> List[
        ProjectPin
    ]:
        """
        Return project pins.
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        return list(
            self.project_pins
            .get(
                project_id,
                {},
            )
            .values()
        )

    # ======================================================================
    # PROJECT ITERATION
    # ======================================================================

    def iterate_project(
        self,
        project_id: str,
        state: str,
        metadata: Optional[
            Dict[
                str,
                Any,
            ]
        ] = None,
    ) -> ProjectIteration:
        """
        Register a project iteration.
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        iterations = (
            self.project_iterations
            .setdefault(
                project_id,
                [],
            )
        )

        iteration = ProjectIteration(

            project_id=
                project_id,

            iteration=
                len(
                    iterations
                )
                + 1,

            state=
                normalize_text(
                    state
                ),

            metadata=
                metadata
                or {},

        )

        iterations.append(
            iteration
        )

        self.trace_project(
            project_id,
            {

                "type":
                    "iteration",

                "iteration":
                    iteration.iteration,

                "state":
                    iteration.state,

            },
        )

        return iteration

    # ======================================================================
    # PROJECT STATE
    # ======================================================================

    def set_project_state(
        self,
        project_id: str,
        state: Dict[
            str,
            Any,
        ],
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Set project state.
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        stored = dict(
            state
        )

        stored[
            "updated_at"
        ] = utc_now()

        self.project_states[
            project_id
        ] = stored

        self.trace_project(
            project_id,
            {

                "type":
                    "state",

                "state":
                    stored,

            },
        )

        return stored

    # ======================================================================
    # GET PROJECT STATE
    # ======================================================================

    def get_project_state(
        self,
        project_id: str,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Retrieve project state.
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        return dict(
            self.project_states
            .get(
                project_id,
                {},
            )
        )

    # ======================================================================
    # LIST STATE
    # ======================================================================

    def list_state(
        self,
        project_id: str,
        key: str,
    ) -> List[
        Any
    ]:
        """
        Return list state from project.
        """

        state = (
            self.get_project_state(
                project_id
            )
        )

        value = state.get(
            key,
            [],
        )

        if isinstance(
            value,
            list,
        ):

            return list(
                value
            )

        return []

    # ======================================================================
    # ANY STATE
    # ======================================================================

    def any_state(
        self,
        project_id: str,
        key: str,
    ) -> bool:
        """
        Determine whether a project state
        contains any active value.
        """

        state = (
            self.get_project_state(
                project_id
            )
        )

        value = state.get(
            key
        )

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
                dict,
            ),
        ):

            return any(
                value
            )

        return bool(
            value
        )

    # ======================================================================
    # WHILE LOOP STATE
    # ======================================================================

    def while_state(
        self,
        project_id: str,
        key: str,
        limit: int = 1000,
    ) -> List[
        Any
    ]:
        """
        Iterate deterministic state until
        the stored sequence is exhausted.

        This is an inspection mechanism,
        not an infinite execution loop.
        """

        values = (
            self.list_state(
                project_id,
                key,
            )
        )

        result = []

        index = 0

        while (
            index < len(
                values
            )
            and index < int(
                limit
            )
        ):

            result.append(
                values[
                    index
                ]
            )

            index += 1

        return result

    # ======================================================================
    # COMPARE STATE
    # ======================================================================

    def compare_state(
        self,
        left_project_id: str,
        right_project_id: str,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Compare two project states.
        """

        left = (
            self.get_project_state(
                left_project_id
            )
        )

        right = (
            self.get_project_state(
                right_project_id
            )
        )

        left_keys = set(
            left.keys()
        )

        right_keys = set(
            right.keys()
        )

        shared_keys = (
            left_keys
            &
            right_keys
        )

        differences = {}

        for key in (
            left_keys
            |
            right_keys
        ):

            left_value = (
                left.get(
                    key
                )
            )

            right_value = (
                right.get(
                    key
                )
            )

            if (
                left_value
                !=
                right_value
            ):

                differences[
                    key
                ] = {

                    "left":
                        left_value,

                    "right":
                        right_value,

                }

        return {

            "left_project":
                normalize_text(
                    left_project_id
                ),

            "right_project":
                normalize_text(
                    right_project_id
                ),

            "shared_keys":
                sorted(
                    shared_keys
                ),

            "left_only":
                sorted(
                    left_keys
                    -
                    right_keys
                ),

            "right_only":
                sorted(
                    right_keys
                    -
                    left_keys
                ),

            "differences":
                differences,

            "equal":
                not bool(
                    differences
                ),

        }

    # ======================================================================
    # CROSS PROJECT COMPARE
    # ======================================================================

    def cross_project_compare(
        self,
        project_ids: List[
            str
        ],
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Compare multiple projects.
        """

        normalized = [

            normalize_text(
                project_id
            )

            for project_id
            in project_ids

            if normalize_text(
                project_id
            )

        ]

        states = {

            project_id:
                self.get_project_state(
                    project_id
                )

            for project_id
            in normalized

        }

        all_keys: Set[
            str
        ] = set()

        for state in (
            states.values()
        ):

            all_keys.update(
                state.keys()
            )

        comparison = {}

        for key in all_keys:

            values = {

                project_id:
                    state.get(
                        key
                    )

                for (
                    project_id,
                    state,
                )
                in states.items()

            }

            unique_values = {

                stable_hash(
                    value
                )

                for value
                in values.values()

            }

            comparison[
                key
            ] = {

                "values":
                    values,

                "equal":
                    len(
                        unique_values
                    )
                    <= 1,

            }

        return {

            "projects":
                normalized,

            "states":
                states,

            "comparison":
                comparison,

        }

    # ======================================================================
    # PROJECT CONTEXT
    # ======================================================================

    def project_context_aware(
        self,
        project_id: str,
        context: Optional[
            str
        ] = None,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Build project-aware context.

        Combines:

            state
            pins
            trace
            latest iteration
            contextual identity
        """

        project_id = (
            normalize_text(
                project_id
            )
        )

        trace = (
            self.project_traces.get(
                project_id
            )
        )

        iterations = (
            self.project_iterations.get(
                project_id,
                [],
            )
        )

        latest_iteration = (

            iterations[-1]

            if iterations

            else None

        )

        return {

            "project_id":
                project_id,

            "project_context":
                normalize_text(
                    context
                ),

            "state":
                self.get_project_state(
                    project_id
                ),

            "pins":
                [

                    {

                        "pin_id":
                            pin.pin_id,

                        "value":
                            pin.value,

                        "metadata":
                            pin.metadata,

                    }

                    for pin
                    in self.get_project_pins(
                        project_id
                    )

                ],

            "trace":
                (

                    trace.events

                    if trace

                    else []

                ),

            "latest_iteration":
                (

                    {

                        "iteration":
                            latest_iteration.iteration,

                        "state":
                            latest_iteration.state,

                        "metadata":
                            latest_iteration.metadata,

                    }

                    if latest_iteration

                    else None

                ),

        }

    # ======================================================================
    # PARTITION MEMORY
    # ======================================================================

    def partition(
        self,
        record: Dict[
            str,
            Any,
        ],
        *,
        domain: str = DEFAULT_DOMAIN,
        hierarchy: str = DEFAULT_HIERARCHY,
        role: str = DEFAULT_ROLE,
        relevancy: float = (
            DEFAULT_RELEVANCY
        ),
        project_id: str = "",
        project_context: str = "",
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Partition a MemoryGrid record.

        MemoryGrid remains owner of the
        original indexed record.

        MemoryPartition stores contextual
        partition references.
        """

        key = (
            self.build_partition_key(

                domain=
                    domain,

                hierarchy=
                    hierarchy,

                role=
                    role,

                project_id=
                    project_id,

                project_context=
                    project_context,

                relevancy=
                    relevancy,

            )
        )

        partition_id = (
            self.partition_id(
                key
            )
        )

        shard = (
            self.gsp_xor_quorum(

                domain=
                    key.domain,

                hierarchy=
                    key.hierarchy,

                role=
                    key.role,

                relevancy_bucket=
                    key.relevancy_bucket,

                project_id=
                    key.project_id,

                project_context=
                    key.project_context,

            )
        )

        partition_record = {

            "record":
                dict(
                    record
                ),

            "partition_id":
                partition_id,

            "partition_key":
                {

                    "domain":
                        key.domain,

                    "hierarchy":
                        key.hierarchy,

                    "role":
                        key.role,

                    "project_id":
                        key.project_id,

                    "project_context":
                        key.project_context,

                    "relevancy_bucket":
                        key.relevancy_bucket,

                },

            "shard":
                shard,

            "partitioned_at":
                utc_now(),

        }

        self.partitions.setdefault(
            partition_id,
            [],
        ).append(
            partition_record
        )

        self.partition_metadata[
            partition_id
        ] = {

            "partition_key":
                partition_record[
                    "partition_key"
                ],

            "shard":
                shard,

        }

        if project_id:

            self.trace_project(
                project_id,
                {

                    "type":
                        "partition",

                    "partition_id":
                        partition_id,

                    "shard":
                        shard,

                },
            )

        return partition_record

    # ======================================================================
    # PARTITION MANY
    # ======================================================================

    def partition_many(
        self,
        records: Iterable[
            Dict[
                str,
                Any,
            ]
        ],
        **context: Any,
    ) -> List[
        Dict[
            str,
            Any,
        ]
    ]:
        """
        Partition multiple records.
        """

        results = []

        for record in records:

            results.append(
                self.partition(
                    record,
                    **context,
                )
            )

        return results

    # ======================================================================
    # RETRIEVE PARTITION
    # ======================================================================

    def get_partition(
        self,
        partition_id: str,
        limit: int = (
            DEFAULT_PARTITION_LIMIT
        ),
    ) -> List[
        Dict[
            str,
            Any,
        ]
    ]:
        """
        Retrieve partition records.
        """

        records = (
            self.partitions.get(
                partition_id,
                [],
            )
        )

        return records[
            :int(
                limit
            )
        ]

# ======================================================================
    # FIND PARTITION
    # ======================================================================

    def find_partition(
        self,
        *,
        domain: str = DEFAULT_DOMAIN,
        hierarchy: str = DEFAULT_HIERARCHY,
        role: str = DEFAULT_ROLE,
        relevancy: float = (
            DEFAULT_RELEVANCY
        ),
        project_id: str = "",
        project_context: str = "",
    ) -> Tuple[
        str,
        List[
            Dict[
                str,
                Any,
            ]
        ],
    ]:
        """
        Resolve partition identity
        and retrieve partition.
        """

        key = (
            self.build_partition_key(

                domain=
                    domain,

                hierarchy=
                    hierarchy,

                role=
                    role,

                project_id=
                    project_id,

                project_context=
                    project_context,

                relevancy=
                    relevancy,

            )
        )

        partition_id = (
            self.partition_id(
                key
            )
        )

        return (

            partition_id,

            self.get_partition(
                partition_id
            ),

        )

    # ======================================================================
    # GRIDCV
    # ======================================================================

    def validate_partition(
        self,
        partition_id: str,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Validate partition through GridCV
        without replacing GridCV.

        GridCV remains intact.

        This method only passes partition
        information into whichever
        comparison/validation interface
        the existing GridCV exposes.
        """

        records = (
            self.get_partition(
                partition_id
            )
        )

        if (
            self.grid_cv
            is None
        ):

            return {

                "partition_id":
                    partition_id,

                "validated":
                    False,

                "reason":
                    "gridcv_unavailable",

                "record_count":
                    len(
                        records
                    ),

            }

        try:

            if hasattr(
                self.grid_cv,
                "validate",
            ):

                result = (
                    self.grid_cv.validate(
                        records
                    )
                )

            elif hasattr(
                self.grid_cv,
                "compare",
            ):

                result = (
                    self.grid_cv.compare(
                        records
                    )
                )

            elif callable(
                self.grid_cv
            ):

                result = (
                    self.grid_cv(
                        records
                    )
                )

            else:

                result = (
                    None
                )

            return {

                "partition_id":
                    partition_id,

                "validated":
                    result
                    is not None,

                "result":
                    result,

                "record_count":
                    len(
                        records
                    ),

            }

        except Exception as exc:

            return {

                "partition_id":
                    partition_id,

                "validated":
                    False,

                "error":
                    str(
                        exc
                    ),

                "record_count":
                    len(
                        records
                    ),

            }

    # ======================================================================
    # CRAWLER PARTITION ROUTING
    # ======================================================================

    def partition_crawler_candidates(
        self,
        candidates: List[
            Dict[
                str,
                Any,
            ]
        ],
        **context: Any,
    ) -> List[
        Dict[
            str,
            Any,
        ]
    ]:
        """
        Receive candidates already routed
        by GridCrawler/CrawlerRetrieval.

        The partition layer does not
        recalculate crawler traversal.

        Crawlers remain routers.
        """

        return self.partition_many(
            candidates,
            **context,
        )

    # ======================================================================
    # MEMORYGRID ROUTING
    # ======================================================================

    def partition_document(
        self,
        doc_id: Any,
        **context: Any,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Partition a document already
        owned by MemoryGrid.

        The document itself remains
        in MemoryGrid.
        """

        record = {

            "doc_id":
                doc_id,

            "source":
                "memory_grid",

        }

        return self.partition(
            record,
            **context,
        )

    # ======================================================================
    # PARTITION SUMMARY
    # ======================================================================

    def summary(
        self,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Return memory partition status.
        """

        return {

            "rows":
                self.rows,

            "cols":
                self.cols,

            "partition_count":
                len(
                    self.partitions
                ),

            "partition_records":
                sum(

                    len(
                        records
                    )

                    for records
                    in self.partitions.values()

                ),

            "projects":
                len(
                    self.project_states
                ),

            "project_traces":
                len(
                    self.project_traces
                ),

            "project_pin_sets":
                len(
                    self.project_pins
                ),

            "project_iterations":
                sum(

                    len(
                        iterations
                    )

                    for iterations
                    in (
                        self.project_iterations
                        .values()
                    )

                ),

            "grid_cv":
                self.grid_cv
                is not None,

            "grid_crawler":
                self.grid_crawler
                is not None,

            "crawler_retrieval":
                self.crawler_retrieval
                is not None,

        }


# ============================================================================
# FUNCTIONAL API
# ============================================================================

def create_memory_partition(
    memory_grid: MemoryGrid,
    grid_cv: Optional[
        Any
    ] = None,
    grid_crawler: Optional[
        Any
    ] = None,
    crawler_retrieval: Optional[
        Any
    ] = None,
) -> MemoryPartition:
    """
    Create canonical MemoryPartition.
    """

    return MemoryPartition(

        memory_grid=
            memory_grid,

        grid_cv=
            grid_cv,

        grid_crawler=
            grid_crawler,

        crawler_retrieval=
            crawler_retrieval,

    )


# ============================================================================
# DEVELOPMENT TEST
# ============================================================================

if __name__ == "__main__":

    print(
        "CoMpaNeoN Memory Partition"
    )

    print(
        {

            "default_rows":
                DEFAULT_ROWS,

            "default_cols":
                DEFAULT_COLS,

            "architecture":
                [

                    "MemoryGrid",

                    "MemoryPartition",

                    "GSP XOR Quorum",

                    "GridCV",

                    "GridCrawler",

                    "CrawlerRetrieval",

                ],

        }
    )