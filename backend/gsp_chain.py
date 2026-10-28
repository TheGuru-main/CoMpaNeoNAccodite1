"""
GSP name identity — SAME chain as training/tokenizer.

Source of truth: backend.tokenizer.tokenizer
  - multilingual ALPHABETS (en, yo, fr, ar, …)
  - digits → DIGIT_MARKERS expanded to letter indexes (not raw 0-9)
  - uid_sequence(token, lang) → list[int]  (0-based; A/a → 0 kept)
  - serialize_uid(seq) → string (leading 0 preserved as character)

Repo uid and doc uid MUST use this path so placement matches train vocab.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

R_ROWS = 64
N_COLS = 54
ROW_MIN, ROW_MAX = 1, 64
COL_MIN, COL_MAX = 0, 53

try:
    from tokenizer.tokenizer import (
        uid_sequence as _tok_uid_sequence,
        serialize_uid as _tok_serialize_uid,
        alphabet_index as _tok_alphabet_index,
        normalize_lang as _tok_normalize_lang,
    )
    _HAS_TOK = True
except Exception:
    try:
        from tokenizer import (
            uid_sequence as _tok_uid_sequence,
            serialize_uid as _tok_serialize_uid,
            alphabet_index as _tok_alphabet_index,
            normalize_lang as _tok_normalize_lang,
        )
        _HAS_TOK = True
    except Exception as _e:
        _HAS_TOK = False
        _TOK_ERR = _e


def letter_chain(name: str, lang: str = "en") -> List[int]:
    """Ordered 0-based indexes — identical to training uid_sequence."""
    name = str(name or "")
    if not name:
        return []
    if not _HAS_TOK:
        raise RuntimeError(f"tokenizer unavailable for letter_chain: {_TOK_ERR!r}")
    return list(_tok_uid_sequence(name, lang))


def chain_to_str(chain: Sequence[int]) -> str:
    if _HAS_TOK:
        return _tok_serialize_uid(chain)
    return "".join(str(int(x)) for x in chain)


def chain_to_compact(chain: Sequence[int]) -> str:
    """Same as serialize_uid (training identity string)."""
    return chain_to_str(chain)


def chain_sum(chain: Sequence[int]) -> int:
    return int(sum(int(x) for x in chain))


def start_row_for_name(name: str, lang: str = "en") -> Dict[str, Any]:
    name = str(name or "")
    chain = letter_chain(name, lang)
    L = max(len(name), 1)
    S = chain_sum(chain)
    start_row = ((L + S - 1) % R_ROWS) + 1
    uid = chain_to_str(chain)
    return {
        "name": name,
        "lang": lang,
        "L": L,
        "S": S,
        "chain": chain,
        "uid_str": uid,
        "uid_compact": uid,
        "start_row": start_row,
        "root_key": f"r{start_row:02d}",
        "grid_rows": R_ROWS,
        "grid_cols": N_COLS,
        "source": "tokenizer.uid_sequence",
    }


def uid_from_name(name: str, lang: str = "en") -> str:
    return chain_to_str(letter_chain(name, lang))


def verify_uid_matches_name(name: str, uid: str, lang: str = "en") -> bool:
    expected = uid_from_name(name, lang)
    u = (uid or "").strip()
    if u == expected:
        return True
    # accept list-form joined without separators only
    try:
        if list(letter_chain(name, lang)) == [int(x) for x in u.split(".") if x != ""]:
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


import re as _re
_NAME_OK = _re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,62}$")
_LEADING_FORBIDDEN = set("._-+&@#$/)(+@?;*'\"\\<>|`\~%^=[]{}!,:")

def validate_resource_name(name: str, *, what: str = "name") -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError(f"{what} is required")
    if name[0] in _LEADING_FORBIDDEN or not name[0].isalpha():
        raise ValueError(f"{what} must start with a letter (A-Z), not a digit or symbol")
    if not _NAME_OK.match(name):
        raise ValueError(
            f"{what} may only contain letters, digits, _ or - after the first letter"
        )
    return name
