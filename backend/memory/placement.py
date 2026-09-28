"""
CoMpaNeoN Placement Controller
==============================

Controls placement preparation for:

    - users
    - direct message boxes
    - room messages
    - full text
    - tokenized words
    - AI / system entries
    - training data
    - retrieved external data

Architecture
------------

                    INPUT
                      │
                      ▼
                 placement.py
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    tokenizer     keyboard.py    identity/context
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              placement decision
                      │
                      ▼
                 GSP cells
                      │
                      ▼
                MEMORY GRID


OWNERSHIP
---------

placement.py OWNS:

    - deciding placement mode
    - preparing placement metadata
    - selecting the correct S rule
    - connecting tokenizer signals to placement
    - user placement preparation
    - direct message-box placement preparation
    - full-text placement preparation
    - room-trigger placement preparation
    - placement metadata envelopes

placement.py DOES NOT OWN:

    - keyboard maps
    - language alphabet definitions
    - tokenization
    - linguistic understanding
    - intent analysis
    - GSP mathematics implementation
    - MemoryGrid storage
    - retrieval
    - ranking
    - crawling
    - STM/LTM
    - permission enforcement

Language-specific columns are supplied by tokenizer output.

IMPORTANT
---------

USER / MESSAGE-BOX PLACEMENT

    L = derived from the user's name
    S = decimal digit sum of the user's numeric uID
    c = supplied by tokenizer / language-aware token signal

FULL-TEXT PLACEMENT

    Full text is tokenized.

    L = derived from the supplied text structure
    S = randomized uID-derived S
    c = supplied by tokenizer output

ROOM MESSAGES

    Room messages are normal grid entries.

    AI reasoning is NOT automatically triggered by every room message.

    The organization AI is explicitly triggered through:

        @org

    Normal room conversation remains ordinary room chat.

ROOM TYPES

The following are all workspaces:

    - team rooms
    - department rooms
    - organization rooms
    - meeting rooms
    - video-call spaces

Direct worker-to-worker or user-to-user messaging remains outside
the room-trigger architecture and uses message-box placement.

placement.py prepares placement only.
Permission and identity validation remain downstream/upstream
responsibilities of their dedicated modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from keyboard import (
    GRID_ROWS,
    ENGLISH_COLUMNS,
    calculate_lsum,
    calculate_uid_ssum,
    calculate_full_text_s,
    first_letter_index,
    gsp_place,
    normalise,
)


# ==============================================================================
# PLACEMENT MODES
# ==============================================================================

PLACEMENT_USER = "user"

PLACEMENT_MESSAGE_BOX = "message_box"

PLACEMENT_ROOM_MESSAGE = "room_message"

PLACEMENT_FULL_TEXT = "full_text"

PLACEMENT_TOKEN = "token"

PLACEMENT_AI = "ai"

PLACEMENT_TRAINING = "training"

PLACEMENT_EXTERNAL = "external"


VALID_PLACEMENT_MODES = {
    PLACEMENT_USER,
    PLACEMENT_MESSAGE_BOX,
    PLACEMENT_ROOM_MESSAGE,
    PLACEMENT_FULL_TEXT,
    PLACEMENT_TOKEN,
    PLACEMENT_AI,
    PLACEMENT_TRAINING,
    PLACEMENT_EXTERNAL,
}


# ==============================================================================
# TOKENIZER SIGNAL
# ==============================================================================

@dataclass
class TokenPlacementSignal:
    """
    Minimal placement signal consumed from tokenizer output.

    tokenizer.py remains the owner of how these values are discovered.

    placement.py only consumes them.

    Required placement concepts:

        token
        language
        column

    Optional:

        normalized token
        token index
        token metadata
    """

    token: str

    language: str = "en"

    column: Optional[int] = None

    normalized: Optional[str] = None

    index: Optional[int] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ==============================================================================
# PLACEMENT RESULT
# ==============================================================================

@dataclass
class PlacementResult:
    """
    Standard placement envelope.

    This object is returned to the caller and can later be passed
    into the MemoryGrid layer.

    placement.py does not write to MemoryGrid.
    """

    mode: str

    L: int

    S: int

    c: int

    start_row: int

    primary_cell: Optional[Dict[str, int]]

    cells: List[Dict[str, int]]

    language: str = "en"

    source_type: str = ""

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:

        return {
            "mode": self.mode,

            "L": self.L,

            "S": self.S,

            "c": self.c,

            "start_row": self.start_row,

            "primary_cell": self.primary_cell,

            "cells": self.cells,

            "language": self.language,

            "source_type": self.source_type,

            "metadata": self.metadata,
        }


# ==============================================================================
# TOKENIZER ADAPTER
# ==============================================================================

def coerce_token_signal(
    signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ],
    fallback_text: str = "",
    fallback_language: str = "en",
) -> TokenPlacementSignal:
    """
    Convert tokenizer output into the placement signal consumed here.

    The tokenizer may return either:

        TokenPlacementSignal

    or:

        {
            "token": "...",
            "language": "...",
            "column": 12,
            ...
        }

    placement.py does not determine language-specific columns.
    """

    if isinstance(
        signal,
        TokenPlacementSignal,
    ):
        return signal

    if isinstance(
        signal,
        dict,
    ):

        return TokenPlacementSignal(
            token=str(
                signal.get(
                    "token",
                    fallback_text,
                )
            ),

            language=str(
                signal.get(
                    "language",
                    fallback_language,
                )
            ),

            column=signal.get(
                "column"
            ),

            normalized=signal.get(
                "normalized"
            ),

            index=signal.get(
                "index"
            ),

            metadata=dict(
                signal.get(
                    "metadata",
                    {},
                )
            ),
        )

    return TokenPlacementSignal(
        token=fallback_text,

        language=fallback_language,
    )


# ==============================================================================
# COLUMN RESOLUTION
# ==============================================================================

def resolve_column(
    token_signal: TokenPlacementSignal,
    fallback_text: str = "",
    columns: int = ENGLISH_COLUMNS,
) -> int:
    """
    Resolve placement column.

    Priority:

        1. tokenizer-supplied language-specific column
        2. canonical keyboard first-character fallback

    The tokenizer remains the owner of language-specific columns.
    """

    if token_signal.column is not None:

        return (
            int(
                token_signal.column
            )
            % columns
        )

    source = (
        token_signal.normalized
        or token_signal.token
        or fallback_text
    )

    return (
        first_letter_index(
            source,
            token_signal.language,
        )
        % columns
    )


# ==============================================================================
# CORE RESULT BUILDER
# ==============================================================================

def build_result(
    *,
    mode: str,
    L: int,
    S: int,
    c: int,
    language: str,
    source_type: str,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
) -> PlacementResult:
    """
    Central placement result constructor.
    """

    if mode not in VALID_PLACEMENT_MODES:

        raise ValueError(
            f"Unsupported placement mode: {mode}"
        )

    placed = gsp_place(
        Lsum=L,
        Ssum=S,
        c=c,
        K=K,
        D=D,
        C=C,
        R=R,
    )

    return PlacementResult(
        mode=mode,

        L=L,

        S=S,

        c=c,

        start_row=placed[
            "start_row"
        ],

        primary_cell=placed[
            "primary_cell"
        ],

        cells=placed[
            "cells"
        ],

        language=language,

        source_type=source_type,

        metadata=metadata or {},
    )


# ==============================================================================
# USER PLACEMENT
# ==============================================================================

def place_user(
    *,
    name: str,
    uid: Union[
        str,
        int,
    ],
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Prepare USER placement.

    Canonical rule:

        L = user's name structure
        S = decimal digit sum of numeric uID
        c = tokenizer language-specific column

    Identity is not generated here.

    The caller provides the user's established uID.
    """

    signal = coerce_token_signal(
        tokenizer_signal,
        fallback_text=name,
        fallback_language=language,
    )

    normalized_name = normalise(
        name,
        signal.language,
    )

    L = calculate_lsum(
        normalized_name,
        signal.language,
    )

    S = calculate_uid_ssum(
        uid
    )

    c = resolve_column(
        signal,
        fallback_text=normalized_name,
        columns=C,
    )

    final_metadata = {
        "name": name,

        "uid": str(uid),

        "placement_identity": (
            "user"
        ),
    }

    if metadata:
        final_metadata.update(
            metadata
        )

    return build_result(
        mode=PLACEMENT_USER,

        L=L,

        S=S,

        c=c,

        language=signal.language,

        source_type="user",

        metadata=final_metadata,

        K=K,

        D=D,

        C=C,

        R=R,
    )


# ==============================================================================
# DIRECT MESSAGE BOX PLACEMENT
# ==============================================================================

def place_message_box(
    *,
    name: str,
    uid: Union[
        str,
        int,
    ],
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Prepare direct MESSAGE-BOX placement.

    This follows the established architecture:

        L = user's name
        S = user's numeric uID digit sum
        c = tokenizer column

    This applies to normal user-to-user or worker-to-worker
    direct messaging.

    Room messaging does not use this mode.
    """

    result = place_user(
        name=name,

        uid=uid,

        tokenizer_signal=tokenizer_signal,

        language=language,

        K=K,

        D=D,

        C=C,

        R=R,

        metadata=metadata,
    )

    result.mode = PLACEMENT_MESSAGE_BOX

    result.source_type = (
        "direct_message_box"
    )

    result.metadata[
        "placement_identity"
    ] = "message_box"

    return result


# ==============================================================================
# FULL-TEXT PLACEMENT
# ==============================================================================

def place_full_text(
    *,
    text: str,
    uid: Union[
        str,
        int,
    ],
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    K: int = 0,
    D: int = 0,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Prepare FULL-TEXT placement.

    Canonical rule:

        tokenizer processes the text

        L = text structure
        S = randomized-uID-derived S
        c = tokenizer language-specific column

    S MUST NOT come from:

        - word count
        - sum of words
        - text length
        - character count
    """

    if not text or not text.strip():

        raise ValueError(
            "Full text placement requires text."
        )

    signal = coerce_token_signal(
        tokenizer_signal,
        fallback_text=text,
        fallback_language=language,
    )

    normalized_text = normalise(
        text,
        signal.language,
    )

    L = calculate_lsum(
        normalized_text,
        signal.language,
    )

    S = calculate_full_text_s(
        uid
    )

    c = resolve_column(
        signal,
        fallback_text=normalized_text,
        columns=C,
    )

    final_metadata = {
        "placement_identity": (
            "full_text"
        ),

        "uid": str(uid),

        "text_length": len(text),
    }

    if metadata:

        final_metadata.update(
            metadata
        )

    return build_result(
        mode=PLACEMENT_FULL_TEXT,

        L=L,

        S=S,

        c=c,

        language=signal.language,

        source_type="full_text",

        metadata=final_metadata,

        K=K,

        D=D,

        C=C,

        R=R,
    )


# ==============================================================================
# TOKEN PLACEMENT
# ==============================================================================

def place_token(
    *,
    token_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
    ],
    uid: Union[
        str,
        int,
    ],
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Place an individual tokenizer-produced token.

    This is useful for:

        - word understanding
        - POS processing
        - lexical relations
        - word chains
        - dictionary knowledge
        - canonical linguistic engine

    The token remains linguistically interpreted by its own modules.

    placement.py only prepares its grid location.
    """

    signal = coerce_token_signal(
        token_signal
    )

    token = (
        signal.normalized
        or signal.token
    )

    if not token:

        raise ValueError(
            "Token placement requires a token."
        )

    L = calculate_lsum(
        token,
        signal.language,
    )

    # Token entries are text-derived objects.
    # Therefore they use the full-text randomized S path.

    S = calculate_full_text_s(
        uid
    )

    c = resolve_column(
        signal,
        fallback_text=token,
        columns=C,
    )

    final_metadata = {
        "token": signal.token,

        "normalized": (
            signal.normalized
        ),

        "token_index": (
            signal.index
        ),

        "uid": str(uid),

        "placement_identity": (
            "token"
        ),
    }

    final_metadata.update(
        signal.metadata
    )

    if metadata:

        final_metadata.update(
            metadata
        )

    return build_result(
        mode=PLACEMENT_TOKEN,

        L=L,

        S=S,

        c=c,

        language=signal.language,

        source_type="token",

        metadata=final_metadata,

        K=K,

        D=D,

        C=C,

        R=R,
    )


# ==============================================================================
# ROOM MESSAGE PLACEMENT
# ==============================================================================

def place_room_message(
    *,
    message: str,
    sender_uid: Union[
        str,
        int,
    ],
    room_id: str,
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    room_type: str = "room",
    ai_trigger: bool = False,
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Prepare a ROOM MESSAGE entry.

    Important distinction:

        A room message entering the grid does NOT mean the AI
        must answer.

    AI triggering is explicit.

    Example:

        @org

    Normal team/department/meeting/video-call conversation
    remains ordinary chat.

    The message is still stored as room workspace context.
    """

    if not message or not message.strip():

        raise ValueError(
            "Room message requires content."
        )

    signal = coerce_token_signal(
        tokenizer_signal,
        fallback_text=message,
        fallback_language=language,
    )

    normalized_message = normalise(
        message,
        signal.language,
    )

    L = calculate_lsum(
        normalized_message,
        signal.language,
    )

    # Room content is text content.
    # It uses randomized text S.

    S = calculate_full_text_s(
        sender_uid
    )

    c = resolve_column(
        signal,
        fallback_text=normalized_message,
        columns=C,
    )

    final_metadata = {
        "room_id": room_id,

        "room_type": room_type,

        "sender_uid": str(
            sender_uid
        ),

        "ai_trigger": ai_trigger,

        "placement_identity": (
            "room_message"
        ),
    }

    if metadata:

        final_metadata.update(
            metadata
        )

    return build_result(
        mode=PLACEMENT_ROOM_MESSAGE,

        L=L,

        S=S,

        c=c,

        language=signal.language,

        source_type="room_message",

        metadata=final_metadata,

        K=K,

        D=D,

        C=C,

        R=R,
    )


# ==============================================================================
# AI / SYSTEM ENTRY
# ==============================================================================

def place_ai_entry(
    *,
    content: str,
    uid: Union[
        str,
        int,
    ],
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    source_type: str = "ai",
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:

    """
    Place AI-generated or system-generated content.

    This covers:

        - AI answers
        - generated summaries
        - verified corrections
        - background training outputs
        - system knowledge objects

    The entry itself remains full text.
    """

    result = place_full_text(
        text=content,

        uid=uid,

        tokenizer_signal=tokenizer_signal,

        language=language,

        K=K,

        D=D,

        C=C,

        R=R,

        metadata=metadata,
    )

    result.mode = PLACEMENT_AI

    result.source_type = source_type

    result.metadata[
        "placement_identity"
    ] = "ai"

    return result


# ==============================================================================
# TRAINING DATA PLACEMENT
# ==============================================================================

def place_training_entry(
    *,
    content: str,
    training_uid: Union[
        str,
        int,
    ],
    batch_id: str,
    model_id: str,
    model_version: str,
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Prepare training-data placement.

    This connects to the established training architecture where:

        - training data enters the grid
        - training batches are versioned
        - trained models reference training data
        - model versions are traceable

    MemoryGrid remains responsible for persistence.
    """

    final_metadata = {
        "batch_id": batch_id,

        "model_id": model_id,

        "model_version": model_version,

        "placement_identity": (
            "training"
        ),
    }

    if metadata:

        final_metadata.update(
            metadata
        )

    result = place_full_text(
        text=content,

        uid=training_uid,

        tokenizer_signal=tokenizer_signal,

        language=language,

        K=K,

        D=D,

        C=C,

        R=R,

        metadata=final_metadata,
    )

    result.mode = PLACEMENT_TRAINING

    result.source_type = (
        "training_data"
    )

    return result


# ==============================================================================
# EXTERNAL / CRAWLER ENTRY
# ==============================================================================

def place_external_entry(
    *,
    content: str,
    source_uid: Union[
        str,
        int,
    ],
    source_id: str,
    source_type: str,
    tokenizer_signal: Union[
        TokenPlacementSignal,
        Dict[str, Any],
        None,
    ] = None,
    language: str = "en",
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
) -> PlacementResult:
    """
    Prepare externally acquired knowledge for grid entry.

    Sources may originate from:

        - webcrawler.py
        - gridcrawler.py retrieval flows
        - crawler scheduler
        - approved external sources

    Crawlers own acquisition.

    placement.py only prepares grid placement.
    """

    final_metadata = {
        "source_id": source_id,

        "external_source_type": (
            source_type
        ),

        "placement_identity": (
            "external"
        ),
    }

    if metadata:

        final_metadata.update(
            metadata
        )

    result = place_full_text(
        text=content,

        uid=source_uid,

        tokenizer_signal=tokenizer_signal,

        language=language,

        K=K,

        D=D,

        C=C,

        R=R,

        metadata=final_metadata,
    )

    result.mode = PLACEMENT_EXTERNAL

    result.source_type = source_type

    return result


# ==============================================================================
# GENERIC DISPATCHER
# ==============================================================================

def prepare_placement(
    *,
    mode: str,
    **kwargs: Any,
) -> PlacementResult:
    """
    Generic placement dispatcher.

    This allows upstream systems to request placement without
    directly importing every placement function.
    """

    mode = mode.strip().lower()

    if mode == PLACEMENT_USER:

        return place_user(
            **kwargs
        )

    if mode == PLACEMENT_MESSAGE_BOX:

        return place_message_box(
            **kwargs
        )

    if mode == PLACEMENT_ROOM_MESSAGE:

        return place_room_message(
            **kwargs
        )

    if mode == PLACEMENT_FULL_TEXT:

        return place_full_text(
            **kwargs
        )

    if mode == PLACEMENT_TOKEN:

        return place_token(
            **kwargs
        )

    if mode == PLACEMENT_AI:

        return place_ai_entry(
            **kwargs
        )

    if mode == PLACEMENT_TRAINING:

        return place_training_entry(
            **kwargs
        )

    if mode == PLACEMENT_EXTERNAL:

        return place_external_entry(
            **kwargs
        )

    raise ValueError(
        f"Unsupported placement mode: {mode}"
    )