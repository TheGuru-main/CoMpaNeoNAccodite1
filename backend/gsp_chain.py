"""
GSP name identity — SAME chain as training/tokenizer.

Source of truth: backend.tokenizer.tokenizer
  - multilingual ALPHABETS (en, yo, fr, ar, …)
  - digits → DIGIT_MARKERS expanded to letter indexes (not raw 0-9)
  - uid_sequence(token, lang) → list[int]  (0-based; A/a → 0 kept)
  - serialize_uid(seq) → string (leading 0 preserved as character)

Placement grid: 54 columns (0..53) × 64 rows (1..64).

Column mapping (lang-aware):
  detect language of the name (langdetect + script heuristics)
  first_letter_index = alphabet_index(first_char, lang)  # position in that language alphabet
  alphabet_size A = len(ALPHABETS[lang])  (often 26..~50+)
  start_col = first_letter_index % 54
  so short Latin alphabets (~26) and longer ones (fr, ar, yo, …) all land in 0..53
  without forcing English a–z only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

R_ROWS = 64
N_COLS = 54
ROW_MIN, ROW_MAX = 1, 64
COL_MIN, COL_MAX = 0, 53

_HAS_TOK = False
_TOK_ERR: Any = None

try:
    from tokenizer.tokenizer import (
        uid_sequence as _tok_uid_sequence,
        serialize_uid as _tok_serialize_uid,
        alphabet_index as _tok_alphabet_index,
        alphabet_for as _tok_alphabet_for,
        normalize_lang as _tok_normalize_lang,
    )
    try:
        from tokenizer.tokenizer import detect_lang as _tok_detect_lang
    except Exception:
        _tok_detect_lang = None  # type: ignore
    _HAS_TOK = True
except Exception:
    try:
        from tokenizer import (
            uid_sequence as _tok_uid_sequence,
            serialize_uid as _tok_serialize_uid,
            alphabet_index as _tok_alphabet_index,
            alphabet_for as _tok_alphabet_for,
            normalize_lang as _tok_normalize_lang,
        )
        try:
            from tokenizer import detect_lang as _tok_detect_lang
        except Exception:
            _tok_detect_lang = None  # type: ignore
        _HAS_TOK = True
    except Exception as _e:
        _HAS_TOK = False
        _TOK_ERR = _e
        _tok_detect_lang = None  # type: ignore



# Optional keyboard layout (canonical language column count + first letter col)
try:
    from memory.keyboard import (
        get_language_column_count as _kb_col_count,
        first_letter_index as _kb_first_letter,
        get_language_alphabet as _kb_alphabet,
        resolve_language as _kb_resolve_lang,
        ENGLISH_COLUMNS as _KB_EN_COLS,
    )
    _HAS_KB = True
except Exception:
    try:
        from keyboard import (
            get_language_column_count as _kb_col_count,
            first_letter_index as _kb_first_letter,
            get_language_alphabet as _kb_alphabet,
            resolve_language as _kb_resolve_lang,
            ENGLISH_COLUMNS as _KB_EN_COLS,
        )
        _HAS_KB = True
    except Exception:
        _HAS_KB = False
        _KB_EN_COLS = 26

def _fallback_detect_lang(text: str, fallback: str = "en") -> str:
    s = (text or "").strip()
    if not s:
        return fallback
    for ch in s:
        o = ord(ch)
        if 0x0600 <= o <= 0x06FF:
            return "ar"
        if 0x0400 <= o <= 0x04FF:
            return "ru"
        if 0x4E00 <= o <= 0x9FFF:
            return "zh"
        if 0x3040 <= o <= 0x30FF:
            return "ja"
        if 0xAC00 <= o <= 0xD7AF:
            return "ko"
        if 0x0590 <= o <= 0x05FF:
            return "he"
        if 0x0900 <= o <= 0x097F:
            return "hi"
    low = s.lower()
    if any(c in low for c in "ẹọṣń"):
        return "yo"
    try:
        from langdetect import detect as _ld
        return str(_ld(s if len(s) >= 8 else s + " text")).split("-")[0].lower()
    except Exception:
        return fallback


def detect_placement_lang(text: str, lang: Optional[str] = None) -> str:
    """Resolve language for placement. Explicit lang wins; else detect."""
    if lang and str(lang).strip() and str(lang).strip().lower() not in ("auto", "detect", ""):
        if _HAS_TOK:
            return _tok_normalize_lang(lang)
        return str(lang).strip().lower().split("-")[0]
    if _HAS_TOK and _tok_detect_lang is not None:
        try:
            return _tok_detect_lang(text, fallback="en")
        except Exception:
            pass
    return _fallback_detect_lang(text or "", "en")


def letter_chain(name: str, lang: str = "en") -> List[int]:
    """Ordered 0-based indexes — identical to training uid_sequence."""
    name = str(name or "")
    if not name:
        return []
    if not _HAS_TOK:
        raise RuntimeError(f"tokenizer unavailable for letter_chain: {_TOK_ERR!r}")
    lang = detect_placement_lang(name, lang)
    return list(_tok_uid_sequence(name, lang))


def chain_to_str(chain: Sequence[int]) -> str:
    if _HAS_TOK:
        return _tok_serialize_uid(chain)
    return "".join(str(int(x)) for x in chain)


def chain_to_compact(chain: Sequence[int]) -> str:
    return chain_to_str(chain)


def chain_sum(chain: Sequence[int]) -> int:
    return int(sum(int(x) for x in chain))


def first_letter_index(name: str, lang: str = "en") -> int:
    """
    Zero-based index of the first alphabetic character in the language alphabet.
    Used as the column seed before modulo onto the 54-col grid.
    """
    name = str(name or "")
    lang = detect_placement_lang(name, lang)
    first = ""
    for ch in name:
        if ch.isalpha():
            first = ch
            break
    if not first:
        return 0
    if _HAS_TOK:
        idx = _tok_alphabet_index(first, lang, text_context=name)
        if idx is not None:
            return int(idx)
        # Latin bridge
        folded = first.lower()
        if "a" <= folded <= "z":
            return ord(folded) - 97
        return 0
    # No tokenizer: English latin only
    ch = first.lower()
    if "a" <= ch <= "z":
        return ord(ch) - 97
    return 0


def alphabet_size(lang: str = "en") -> int:
    lang = detect_placement_lang("", lang) if lang else "en"
    if _HAS_TOK:
        try:
            return max(1, len(_tok_alphabet_for(lang)))
        except Exception:
            pass
    return 26



def effective_col_modulus(lang: str) -> int:
    """
    Column width for this language:
      C = explicit language alphabet length
          (max of keyboard layout count and tokenizer ALPHABETS[lang])
      if C >= 54: use 54 (full GSP width only when alphabet reaches it)
      else: use C (en → 26, fr/yo/ar → their real lengths — never force 54)
    """
    resolved = detect_placement_lang("", lang) if lang else "en"
    candidates = []
    if _HAS_KB:
        try:
            candidates.append(int(_kb_col_count(resolved)))
        except Exception:
            pass
        try:
            candidates.append(len(_kb_alphabet(resolved)))
        except Exception:
            pass
    if _HAS_TOK:
        try:
            candidates.append(max(1, len(_tok_alphabet_for(resolved))))
        except Exception:
            pass
    A = max(candidates) if candidates else 26
    if A < 1:
        A = 26
    if A >= N_COLS:
        return N_COLS
    return int(A)


def col_for_name(name: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """
    Map first letter of name → start_col using language alphabet length.

      A / C = effective_col_modulus(lang)   # alphabet length, or 54 if A≥54
      idx   = first letter index in that language (keyboard or tokenizer)
      start_col = idx % C

    English stays in 0..25. Longer alphabets use 0..(A-1). Only when A≥54
    do we modulo on the full 54-col GSP surface.
    """
    resolved = detect_placement_lang(name, lang)
    C = effective_col_modulus(resolved)

    # Prefer keyboard first-letter column when available
    idx = None
    if _HAS_KB:
        try:
            # keyboard expects a string; pass first alpha run
            letters = "".join(ch for ch in (name or "") if ch.isalpha())
            probe = letters or (name or "a")
            idx = int(_kb_first_letter(probe, resolved))
        except Exception:
            idx = None
    if idx is None:
        idx = first_letter_index(name, resolved)

    start_col = int(idx) % max(1, C)
    return {
        "lang": resolved,
        "alphabet_size": C if C < N_COLS else alphabet_size(resolved),
        "C": C,
        "first_letter_index": int(idx),
        "start_col": start_col,
        "c": start_col,
        "col_band": (
            "en26" if C == 26 else
            ("full54" if C >= N_COLS else f"lang{C}")
        ),
    }



def start_row_for_name(name: str, lang: str = "auto") -> Dict[str, Any]:
    name = str(name or "")
    resolved = detect_placement_lang(name, lang)
    chain = letter_chain(name, resolved)
    L = max(len(name), 1)
    S = chain_sum(chain)
    start_row = ((L + S - 1) % R_ROWS) + 1
    uid = chain_to_str(chain)
    col_info = col_for_name(name, resolved)
    return {
        "name": name,
        "lang": resolved,
        "L": L,
        "S": S,
        "chain": chain,
        "uid_str": uid,
        "uid_compact": uid,
        "uid": uid,
        "start_row": start_row,
        "start_col": col_info["start_col"],
        "c": col_info["start_col"],
        "C": col_info.get("C"),
        "first_letter_index": col_info["first_letter_index"],
        "alphabet_size": col_info.get("alphabet_size") or col_info.get("C"),
        "col_band": col_info["col_band"],
        "root_key": f"r{start_row:02d}",
        "target_cell": f"r{start_row}:c{col_info['start_col']}",
        "grid_rows": R_ROWS,
        "grid_cols": col_info.get("C") or N_COLS,  # language-effective width
        "grid_cols_max": N_COLS,
        "source": "tokenizer+keyboard+langdetect",
    }


def uid_from_name(name: str, lang: str = "auto") -> str:
    resolved = detect_placement_lang(name, lang)
    return chain_to_str(letter_chain(name, resolved))


def verify_uid_matches_name(name: str, uid: str, lang: str = "auto") -> bool:
    expected = uid_from_name(name, lang)
    u = (uid or "").strip()
    if u == expected:
        return True
    try:
        resolved = detect_placement_lang(name, lang)
        if list(letter_chain(name, resolved)) == [int(x) for x in u.split(".") if x != ""]:
            return True
    except Exception:
        pass
    return False


def validate_cell(row: int, col: int) -> Tuple[int, int]:
    row = int(row)
    col = int(col)
    if row < ROW_MIN or row > ROW_MAX:
        raise ValueError(f"row must be {ROW_MIN}..{ROW_MAX}")
    if col < COL_MIN or col > COL_MAX:
        raise ValueError(f"col must be {COL_MIN}..{COL_MAX}")
    return row, col


_NAME_OK = __import__("re").compile(r"^[A-Za-z][A-Za-z0-9_-]{0,62}$")
# Allow non-Latin starters for docs/repos that use script names
_LEADING_FORBIDDEN = set("._-+&@#$/)(+@?;*'\"\\<>|`~%^=[]{}!,:")


def validate_resource_name(name: str, *, what: str = "name") -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError(f"{what} is required")
    if name[0] in _LEADING_FORBIDDEN:
        raise ValueError(f"{what} must not start with a symbol")
    # Latin path keeps strict pattern; other scripts: first char must be letter
    if name[0].isascii():
        if not name[0].isalpha():
            raise ValueError(f"{what} must start with a letter")
        if not _NAME_OK.match(name):
            raise ValueError(
                f"{what} may only contain letters, digits, _ or - after the first letter"
            )
    elif not name[0].isalpha():
        raise ValueError(f"{what} must start with a letter")
    return name


def place_fragments(
    *,
    L: int,
    S: int,
    c: int,
    K: int,
    D: int,
    C: int = N_COLS,
    R: int = R_ROWS,
    mode: str = "standard",
) -> Dict[str, Any]:
    """
    Optional multi-fragment placement (DBase configurable / diagnostic).
    Production object place uses start_row_for_name (single cell) unless K>1 requested.
    """
    R = max(2, int(R))
    C = max(2, int(C))
    K = max(1, int(K))
    D = max(1, int(D))
    start_row = ((int(L) + int(S) - 1) % R) + 1
    cells = []
    for k in range(K):
        if mode == "progressive":
            row = ((start_row - 1 + k * D) % R) + 1
            col = (int(c) + k) % C
        elif mode == "jump":
            row = ((start_row - 1 + (2 * k) * D) % R) + 1
            col = (int(c) + 2 * k) % C
        else:
            row = ((start_row - 1 + k * D) % R) + 1
            col = (int(c) + k) % C
        cells.append({"k": k, "row": row, "col": col})
    return {
        "start_row": start_row,
        "L": int(L),
        "S": int(S),
        "c": int(c) % C,
        "K": K,
        "D": D,
        "C": C,
        "R": R,
        "mode": mode,
        "cells": cells,
    }
