"""
CoMpaNeoN Keyboard / GSP Input Mapping
=======================================

Gurutech Scatter Protocol – Core Placement Layer

Purpose
-------

Provides the language-aware character/key mapping used by the
placement architecture.

This module does NOT own:

    - tokenization
    - intent analysis
    - memory storage
    - crawling
    - retrieval
    - ranking
    - STM/LTM
    - prompt orchestration
    - GSP policy decisions

placement.py consumes this module.

Architecture
------------

                    Input
                      │
                      ▼
                  tokenizer
                      │
                      ▼
                 placement.py
                      │
             ┌────────┴────────┐
             │                 │
             ▼                 ▼
       USER / MESSAGE       FULL TEXT
       PLACEMENT            PLACEMENT
             │                 │
       S = digit sum      S = randomized
       of numeric uID     uID-derived S
             │                 │
             └────────┬────────┘
                      ▼
                 GSP placement
                      │
                      ▼
                     Grid


IMPORTANT GSP RULE
------------------

User placement / direct message-box placement:

    S = decimal digit sum of numeric uID.

Full-text placement:

    S = derived from a randomized uID.

The full text must NOT calculate S from:

    - total number of words
    - sum of word counts
    - sum of all text characters

The text is tokenized independently.

Language Support
----------------

The keyboard map supports multiple alphabets/layouts.

English remains constrained to the original 26-column GSP
alphabet boundary.

Other languages may require more character positions.

The language grid may therefore expose a larger character
alphabet while GSP English placement remains C=26.

Supported layouts currently include:

    en  -> English QWERTY
    fr  -> French AZERTY
    de  -> German QWERTZ
    ar  -> Arabic
    zh  -> Chinese/Pinyin virtual layout

Additional local-language layouts can be registered without
changing the placement algorithm.
"""

from __future__ import annotations

import hashlib
import secrets
import unicodedata
from typing import Dict, Iterable, List, Optional, Tuple


# ============================================================================
# GSP GRID CONSTANTS
# ============================================================================

# English GSP remains 26 columns.
ENGLISH_COLUMNS = 26

# Existing keyboard grid.
KEYBOARD_COLUMNS = 36

# Existing GSP row count.
GRID_ROWS = 64


# ============================================================================
# MULTI-LANGUAGE KEYBOARD MAPS
# ============================================================================
#
# Each language describes its keyboard/alphabet ordering.
#
# The mapping is intentionally kept independent from GSP placement.
# get_keymap() converts the language layout into:
#
#     character -> (keyboard_row, column)
#
# English occupies the canonical first 26 alphabet columns.
#
# Additional language characters can extend beyond English's 26
# positions without changing the English GSP rule.
# ============================================================================

_KEYMAPS: Dict[str, List[str]] = {

    # ------------------------------------------------------------------------
    # English QWERTY
    # ------------------------------------------------------------------------
    "en": [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ],

    # ------------------------------------------------------------------------
    # French AZERTY
    # ------------------------------------------------------------------------
    "fr": [
        "azertyuiop",
        "qsdfghjklm",
        "wxcvbn",
    ],

    # ------------------------------------------------------------------------
    # German QWERTZ
    # ------------------------------------------------------------------------
    "de": [
        "qwertzuiop",
        "asdfghjkl",
        "yxcvbnm",
    ],

    # ------------------------------------------------------------------------
    # Arabic standard keyboard arrangement
    # ------------------------------------------------------------------------
    "ar": [
        "ضصثقفغعهخح",
        "شسيبلاتنمك",
        "ئءؤرلاىةوز",
    ],

    # ------------------------------------------------------------------------
    # Chinese Pinyin virtual arrangement
    # ------------------------------------------------------------------------
    "zh": [
        "bpmfdtnlgkhjqxz",
        "aoeiuüaieiaoouan",
        "enangengongiaiei",
    ],

    # ------------------------------------------------------------------------
    # Yoruba
    #
    # Latin base plus Yoruba-specific letters.
    # ------------------------------------------------------------------------
    "yo": [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
        "ẹọṣ",
    ],

    # ------------------------------------------------------------------------
    # Igbo
    #
    # Latin base plus Igbo-specific characters.
    # ------------------------------------------------------------------------
    "ig": [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
        "ịọụ",
    ],

    # ------------------------------------------------------------------------
    # Hausa
    #
    # Hausa primarily uses Latin characters but is retained as a
    # distinct language mapping for future language-specific expansion.
    # ------------------------------------------------------------------------
    "ha": [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ],

    # ------------------------------------------------------------------------
    # Portuguese
    # ------------------------------------------------------------------------
    "pt": [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
        "áàãâçéêíóôõúü",
    ],

    # ------------------------------------------------------------------------
    # Spanish
    # ------------------------------------------------------------------------
    "es": [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
        "ñáéíóúü",
    ],

    # ------------------------------------------------------------------------
    # German extended characters
    # ------------------------------------------------------------------------
    "de_ext": [
        "qwertzuiop",
        "asdfghjkl",
        "yxcvbnm",
        "äöüß",
    ],
}


# ============================================================================
# DIGITS
# ============================================================================

_DIGITS_ROW = "0123456789"


# ============================================================================
# LANGUAGE ALIASES
# ============================================================================

_LANGUAGE_ALIASES = {
    "english": "en",
    "french": "fr",
    "german": "de",
    "arabic": "ar",
    "chinese": "zh",
    "yoruba": "yo",
    "igbo": "ig",
    "ibo": "ig",
    "hausa": "ha",
    "spanish": "es",
    "portuguese": "pt",
}


# ============================================================================
# LANGUAGE RESOLUTION
# ============================================================================

def resolve_language(lang: str = "en") -> str:
    """
    Resolve a language name or language code to a canonical code.
    """

    if not lang:
        return "en"

    value = lang.strip().lower()

    return _LANGUAGE_ALIASES.get(
        value,
        value,
    )


# ============================================================================
# KEYMAP
# ============================================================================

def get_keymap(
    lang: str = "en",
) -> Dict[str, Tuple[int, int]]:
    """
    Return:

        character -> (keyboard_row, column)

    Digits occupy:

        row = 3
        columns = 26-35

    This preserves the existing 36-column keyboard architecture.

    For English:

        columns 0-25 = canonical GSP alphabet

    For languages containing additional characters:

        additional characters receive positions after their
        language's base layout.

    Duplicate characters are ignored after their first occurrence.
    """

    lang = resolve_language(lang)

    rows = _KEYMAPS.get(
        lang,
        _KEYMAPS["en"],
    )

    keymap: Dict[str, Tuple[int, int]] = {}

    column = 0

    for row_index, row in enumerate(rows):

        for char in row:

            char = char.lower()

            if char in keymap:
                continue

            keymap[char] = (
                row_index,
                column,
            )

            column += 1

    # ------------------------------------------------------------------------
    # Digits remain in the existing 36-column design.
    # ------------------------------------------------------------------------

    for offset, digit in enumerate(_DIGITS_ROW):

        keymap[digit] = (
            3,
            26 + offset,
        )

    return keymap


# ============================================================================
# LANGUAGE ALPHABET
# ============================================================================

def get_language_alphabet(
    lang: str = "en",
) -> List[str]:
    """
    Return the unique characters represented by a language layout.

    Digits are not included in this alphabet list.
    """

    lang = resolve_language(lang)

    rows = _KEYMAPS.get(
        lang,
        _KEYMAPS["en"],
    )

    alphabet: List[str] = []

    for row in rows:

        for char in row:

            char = char.lower()

            if char not in alphabet:
                alphabet.append(char)

    return alphabet


def get_language_column_count(
    lang: str = "en",
) -> int:
    """
    Return the number of unique language-character columns.

    English remains 26.

    Other languages may exceed 26.
    """

    return len(
        get_language_alphabet(lang)
    )


# ============================================================================
# LANGUAGE-AWARE NORMALISATION
# ============================================================================

def normalise(
    text: str,
    lang: str = "en",
) -> str:
    """
    Normalise text for language-aware processing.

    English:
        - lowercase
        - remove combining diacritics
        - apply existing lightweight suffix handling

    Other languages:
        - lowercase
        - preserve language-specific characters

    Important:
        This is NOT the tokenizer.
    """

    lang = resolve_language(lang)

    text = text.lower()

    if lang == "en":

        text = "".join(
            char
            for char in unicodedata.normalize(
                "NFKD",
                text,
            )
            if not unicodedata.combining(char)
        )

        for suffix in (
            "ing",
            "ed",
            "s",
            "ly",
            "ment",
            "ness",
        ):

            if (
                text.endswith(suffix)
                and len(text) > len(suffix) + 2
            ):

                text = text[
                    :-len(suffix)
                ]

                break

    return text


# ============================================================================
# CHARACTER LOOKUP
# ============================================================================

def character_position(
    char: str,
    lang: str = "en",
) -> Optional[Tuple[int, int]]:
    """
    Return the keyboard position of a character.

    Returns:

        (row, column)

    or:

        None
    """

    if not char:
        return None

    keymap = get_keymap(lang)

    return keymap.get(
        char.lower()
    )


# ============================================================================
# L SUM
# ============================================================================

def calculate_lsum(
    word: str,
    lang: str = "en",
) -> int:
    """
    Calculate Lsum.

    Lsum is the sum of keyboard row indices of characters.
    """

    keymap = get_keymap(lang)

    return sum(
        keymap[char][0]
        for char in word.lower()
        if char in keymap
    )


# ============================================================================
# S SUM FROM TEXT/WORD
# ============================================================================

def calculate_ssum(
    word: str,
    lang: str = "en",
) -> int:
    """
    Calculate keyboard Ssum.

    This remains available for word/character placement where
    keyboard-column mathematics is explicitly required.

    IMPORTANT:
        This function is NOT used to derive full-text S.

    Full-text S comes from randomized uID.
    """

    keymap = get_keymap(lang)

    return sum(
        keymap[char][1]
        for char in word.lower()
        if char in keymap
    )


# ============================================================================
# FIRST LETTER / C
# ============================================================================

def first_letter_index(
    word: str,
    lang: str = "en",
) -> int:
    """
    Return the column index of the first recognized character.

    c is always derived from the first character.

    English GSP:

        c ∈ 0..25
    """

    if not word:
        return 0

    keymap = get_keymap(lang)

    first = word[0].lower()

    if first in keymap:
        return keymap[first][1]

    return 0


# ============================================================================
# NUMERIC uID
# ============================================================================

def normalise_uid(
    uid: str | int,
) -> str:
    """
    Convert a uID to its numeric representation.

    Non-digit characters are ignored.

    This supports values such as:

        +2348012345678
        2348012345678
        "2348012345678"
    """

    return "".join(
        char
        for char in str(uid)
        if char.isdigit()
    )


# ============================================================================
# USER / MESSAGE S
# ============================================================================

def calculate_uid_ssum(
    uid: str | int,
) -> int:
    """
    Calculate S for USER / MESSAGE-BOX placement.

    Rule:

        S = sum of decimal digits of numeric uID

    Example:

        uID = 2348012345678

        S = 2+3+4+8+0+1+2+3+4+5+6+7+8

    This is the canonical S source for:

        - user placement
        - direct messaging placement
        - message-box placement
    """

    numeric_uid = normalise_uid(uid)

    return sum(
        int(digit)
        for digit in numeric_uid
    )


# ============================================================================
# RANDOMIZED uID
# ============================================================================

def generate_randomized_uid(
    uid: str | int,
    length: int = 32,
) -> str:
    """
    Produce a deterministic-looking but independently randomized
    identifier derived from the user's uID and fresh entropy.

    This is intended for FULL-TEXT placement.

    It does NOT replace the user's real uID.

    The original uID remains the identity.

    The randomized uID is only the placement key.
    """

    uid_string = normalise_uid(uid)

    nonce = secrets.token_hex(16)

    material = (
        f"{uid_string}:{nonce}"
    ).encode(
        "utf-8"
    )

    digest = hashlib.sha256(
        material
    ).hexdigest()

    if length <= 0:
        return digest

    return digest[:length]


# ============================================================================
# FULL-TEXT S
# ============================================================================

def calculate_full_text_s(
    uid: str | int,
) -> int:
    """
    Calculate the S source for FULL-TEXT placement.

    Rule:

        randomized uID -> S

    The full text does NOT derive S from:

        - word count
        - total words
        - total character count
        - sum of word S values

    The randomized uID is converted into a numeric digit sequence
    and its decimal digits are summed.
    """

    randomized_uid = generate_randomized_uid(
        uid
    )

    return sum(
        int(char, 16)
        for char in randomized_uid
        if char in "0123456789abcdef"
    )


# ============================================================================
# GENERIC PLACEMENT S SOURCE
# ============================================================================

def calculate_placement_s(
    uid: str | int,
    mode: str = "user",
) -> int:
    """
    Return the correct S source for the requested placement mode.

    Supported modes:

        user
        message
        message_box
        full_text

    user/message/message_box:

        S = decimal digit sum of numeric uID

    full_text:

        S = randomized-uID-derived S
    """

    mode = mode.strip().lower()

    if mode in {
        "user",
        "message",
        "message_box",
    }:

        return calculate_uid_ssum(uid)

    if mode == "full_text":

        return calculate_full_text_s(uid)

    raise ValueError(
        f"Unsupported placement mode: {mode}"
    )


# ============================================================================
# GSP PLACEMENT
# ============================================================================

def gsp_place(
    Lsum: int,
    Ssum: int,
    c: int,
    K: int = 5,
    D: int = 8,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
) -> dict:
    """
    Return start_row, primary_cell, and K GSP cells.

    Canonical formula:

        start_row = ((L + S - 1) mod R) + 1

        row_k = ((start_row - 1 + kD) mod R) + 1

        col_k = (c + k) mod C
    """

    start_row = (
        (Lsum + Ssum - 1) % R
    ) + 1

    cells = []

    for k in range(K):

        row = (
            (start_row - 1 + k * D)
            % R
        ) + 1

        col = (
            c + k
        ) % C

        cells.append(
            {
                "col": col,
                "row": row,
                "k": k,
            }
        )

    return {
        "start_row": start_row,
        "primary_cell": (
            cells[0]
            if cells
            else None
        ),
        "cells": cells,
    }


# ============================================================================
# USER PLACEMENT PARAMETERS
# ============================================================================

def user_placement_parameters(
    name: str,
    uid: str | int,
    lang: str = "en",
) -> dict:
    """
    Build the GSP input parameters for a USER.

    User identity remains external to this calculation.

    Parameters:

        L = keyboard-row sum of user's name
        S = decimal digit sum of user's numeric uID
        c = first-letter column index
    """

    normalized_name = normalise(
        name,
        lang,
    )

    L = calculate_lsum(
        normalized_name,
        lang,
    )

    S = calculate_uid_ssum(
        uid
    )

    c = first_letter_index(
        normalized_name,
        lang,
    )

    return {
        "mode": "user",
        "name": name,
        "uid": str(uid),
        "language": resolve_language(lang),
        "L": L,
        "S": S,
        "c": c,
    }


# ============================================================================
# MESSAGE-BOX PARAMETERS
# ============================================================================

def message_box_parameters(
    name: str,
    uid: str | int,
    lang: str = "en",
) -> dict:
    """
    Message-box placement uses the SAME user-placement S rule.

    Therefore:

        S = decimal digit sum of uID

    This deliberately keeps USER placement and MESSAGE-BOX
    placement in the same architectural family.
    """

    params = user_placement_parameters(
        name=name,
        uid=uid,
        lang=lang,
    )

    params["mode"] = "message_box"

    return params


# ============================================================================
# FULL-TEXT PARAMETERS
# ============================================================================

def full_text_parameters(
    text: str,
    uid: str | int,
    lang: str = "en",
) -> dict:
    """
    Build placement parameters for FULL TEXT.

    IMPORTANT:

        The text itself is not responsible for generating S.

        S comes from a randomized uID.

    L and c are still derived from the text's language-aware
    character structure.

    Tokenization remains the responsibility of tokenizer.py.
    """

    normalized_text = normalise(
        text,
        lang,
    )

    L = calculate_lsum(
        normalized_text,
        lang,
    )

    S = calculate_full_text_s(
        uid
    )

    c = first_letter_index(
        normalized_text,
        lang,
    )

    return {
        "mode": "full_text",
        "language": resolve_language(lang),
        "L": L,
        "S": S,
        "c": c,
        "randomized_uid": generate_randomized_uid(
            uid
        ),
    }


# ============================================================================
# ELASTIC CLOUD
# ============================================================================

def elastic_cloud(
    L: int,
    S: int,
    c: int,
    radius: int = 1,
    first_letter_radius: int = 1,
    C: int = ENGLISH_COLUMNS,
    R: int = GRID_ROWS,
) -> list:
    """
    Return neighbouring cells for typo-tolerant search.
    """

    cloud = set()

    for dc in range(
        -first_letter_radius,
        first_letter_radius + 1,
    ):

        c2 = (
            c + dc
        ) % C

        for dL in range(
            -radius,
            radius + 1,
        ):

            for dS in range(
                -radius,
                radius + 1,
            ):

                if (
                    dL == 0
                    and dS == 0
                    and dc == 0
                ):
                    continue

                L2 = L + dL
                S2 = S + dS

                start_row = (
                    (L2 + S2 - 1) % R
                ) + 1

                cloud.add(
                    (
                        c2,
                        start_row,
                    )
                )

    base_start_row = (
        (L + S - 1) % R
    ) + 1

    cloud.add(
        (
            c % C,
            base_start_row,
        )
    )

    return [
        {
            "col": col,
            "row": row,
        }
        for col, row in cloud
    ]