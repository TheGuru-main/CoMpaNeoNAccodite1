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
_tok_detect_lang = None  # type: ignore
_tok_uid_sequence = None  # type: ignore
_tok_serialize_uid = None  # type: ignore
_tok_alphabet_index = None  # type: ignore
_tok_alphabet_for = None  # type: ignore
_tok_normalize_lang = None  # type: ignore


def _load_tokenizer_module():
    """
    Explicit load: never rely on ambiguous `import tokenizer`.
    Prefer package backend/tokenizer/tokenizer.py by file path, then package imports.
    """
    import importlib
    import importlib.util
    import sys
    from pathlib import Path as _P

    here = _P(__file__).resolve().parent  # backend/
    candidates = [
        here / "tokenizer" / "tokenizer.py",
        here.parent / "backend" / "tokenizer" / "tokenizer.py",
    ]
    for path in candidates:
        if path.is_file():
            # Load as a real module under a private name so we don't shadow packages
            name = "accd_tokenizer_impl"
            spec = importlib.util.spec_from_file_location(name, str(path))
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod

    # Package paths (PYTHONPATH=backend or installed package)
    for modname in ("tokenizer.tokenizer", "backend.tokenizer.tokenizer"):
        try:
            return importlib.import_module(modname)
        except Exception:
            continue

    # Last: package re-exports (tokenizer/__init__.py)
    for modname in ("tokenizer", "backend.tokenizer"):
        try:
            mod = importlib.import_module(modname)
            if hasattr(mod, "uid_sequence") and hasattr(mod, "serialize_uid"):
                return mod
        except Exception:
            continue
    raise ImportError(
        "tokenizer.tokenizer not found — expected backend/tokenizer/tokenizer.py"
    )


try:
    _tok = _load_tokenizer_module()
    _tok_uid_sequence = _tok.uid_sequence
    _tok_serialize_uid = _tok.serialize_uid
    _tok_alphabet_index = _tok.alphabet_index
    _tok_alphabet_for = _tok.alphabet_for
    _tok_normalize_lang = _tok.normalize_lang
    _tok_detect_lang = getattr(_tok, "detect_lang", None)
    _HAS_TOK = True
except Exception as _e:
    _HAS_TOK = False
    _TOK_ERR = _e



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
        _kb_gsp_place = None  # type: ignore

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

    s = str(text or "")
    # Pure basic Latin (a-z only letters) → en. langdetect mislabels
    # short product names (Accodite→ro) and breaks train-aligned chains.
    letters = [c for c in s if c.isalpha()]
    if letters and all("a" <= c.lower() <= "z" for c in letters):
        return "en"

    if _HAS_TOK and _tok_detect_lang is not None:
        try:
            return _tok_detect_lang(text, fallback="en")
        except Exception:
            pass
    return _fallback_detect_lang(s, "en")


def letter_chain(name: str, lang: str = "en") -> List[int]:
    """Ordered 0-based indexes — identical to training uid_sequence."""
    name = str(name or "")
    if not name:
        return []
    if not _HAS_TOK:
        raise RuntimeError(f"tokenizer unavailable for letter_chain: {_TOK_ERR!r}")
    # If caller already resolved lang (e.g. content_place), do not re-detect.
    if lang and str(lang).strip().lower() not in ("auto", "detect", ""):
        resolved = _tok_normalize_lang(lang) if _HAS_TOK else str(lang).strip().lower().split("-")[0]
    else:
        resolved = detect_placement_lang(name, lang)
    return list(_tok_uid_sequence(name, resolved))


def chain_to_str(chain: Sequence[int]) -> str:
    if _HAS_TOK:
        return _tok_serialize_uid(chain)
    return "_".join(str(int(x)) for x in chain)


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



def content_place_from_name(name: str, lang: str = "auto") -> Dict[str, Any]:
    """
    Content/object place. NEVER "start_row from name" as a primary step.

    1) letter chain (0-based) → uID
    2) S = sum(chain)          # not digit-sum of serialized uid
    3) L = len(normalized lexical token)  # NOT keyboard calculate_lsum
    4) c = first letter alphabet index (lang band)
    5) ONLY THEN start_row / cells via keyboard.gsp_place(L, S, c)
    """
    name = str(name or "")
    resolved = detect_placement_lang(name, lang)

    # Full chain: letters + digit markers + code symbol ids → S + uid + start_row
    chain: list = []
    digit_markers: list = []
    symbol_uids: list = []
    identity_stream_payload: list = []
    try:
        _tokm = _load_tokenizer_module()
        _uchain = getattr(_tokm, "uid_chain", None)
        _cS = getattr(_tokm, "chain_S", None)
        _ser = getattr(_tokm, "serialize_uid_chain", None)
        _id = getattr(_tokm, "identity_stream", None)
        if _id:
            identity_stream_payload = list(_id(name, resolved) or [])
        if _uchain:
            chain_full = list(_uchain(name, resolved) or [])
        else:
            chain_full = list(letter_chain(name, resolved))
        chain = [x for x in chain_full if isinstance(x, int)]
        digit_markers = [x for x in chain_full if isinstance(x, str) and not str(x).startswith("-")]
        symbol_uids = [x for x in chain_full if isinstance(x, str) and str(x).startswith("-")]
        S = int(_cS(chain_full)) if _cS else int(sum(chain))
        uid = _ser(chain_full) if _ser else chain_to_str(chain)
    except Exception:
        chain = list(letter_chain(name, resolved))
        S = chain_sum(chain)
        uid = chain_to_str(chain)
    if S < 0:
        S = 0

    # Lexical L only — full normalized surface (Accodite → 8)
    try:
        if _HAS_TOK:
            from tokenizer.tokenizer import normalize_lexical_token as _nlt
        else:
            from tokenizer import normalize_lexical_token as _nlt  # type: ignore
        norm = _nlt(name, resolved) or ""
        L = max(len(norm), 1)
    except Exception:
        L = max(len([ch for ch in name if ch.isalnum()]), 1) if name else 1

    col_info = col_for_name(name, resolved)
    c = int(col_info["start_col"])
    C = int(col_info.get("C") or effective_col_modulus(resolved))
    R = int(R_ROWS)

    # start_row only after L and S exist
    start_row = ((int(L) + int(S) - 1) % R) + 1
    cells: List[Any] = []
    primary = None
    try:
        if _HAS_KB:
            try:
                from memory.keyboard import gsp_place as _gp
            except Exception:
                from keyboard import gsp_place as _gp  # type: ignore
            placed = _gp(Lsum=L, Ssum=S, c=c, K=5, D=8, C=C, R=R)
            start_row = int(placed["start_row"])
            primary = placed.get("primary_cell")
            cells = list(placed.get("cells") or [])
    except Exception:
        cells = [{"col": c % max(C, 1), "row": start_row, "k": 0}]
        primary = cells[0]

    return {
        "name": name,
        "lang": resolved,
        "L": L,
        "S": S,
        "chain": list(chain),
        "digit_markers": digit_markers,
        "symbol_uids": symbol_uids,
        "identity_stream": identity_stream_payload,
        "uid_str": uid,
        "uid_compact": uid,
        "uid": uid,
        "start_row": start_row,
        "start_col": c,
        "c": c,
        "C": C,
        "first_letter_index": col_info.get("first_letter_index"),
        "alphabet_size": col_info.get("alphabet_size") or C,
        "col_band": col_info.get("col_band"),
        "root_key": f"r{start_row:02d}",
        "target_cell": f"r{start_row}:c{c}",
        "primary_cell": primary,
        "cells": cells,
        "grid_rows": R,
        "grid_cols": C,
        "grid_cols_max": N_COLS,
        "source": "L,S then start_row; no name→row shortcut",
    }


def start_row_for_name(name: str, lang: str = "auto") -> Dict[str, Any]:
    """Deprecated name: forwards to content_place_from_name (L,S then start_row)."""
    return content_place_from_name(name, lang)


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
