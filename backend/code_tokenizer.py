"""
code_tokenizer.py
=================
Code-aware tokenizer.

Uses the canonical tokenizer when available, then layers code
recognition on top so identifiers get a code-role column
(KEYWORD / FUNC_DEF / CLASS_DEF / BUILTIN / IDENT_*) instead of a
raw letter index.

Exposes:
    word_cell(token, lang)          -> GSP metadata (compat shim)
    code_word_cell(token, lang)     -> GSP metadata using code recognition
    split_code_identifiers(text)    -> identifiers
    classify_code_token(token)      -> color class
    detect_code_language(text)      -> language code
    recognize_code_symbols(text)    -> symbols via memory.symbols
    tokenize_code(text, lang)       -> [{token, lang, Lsum, Ssum, c, L, color_class}]
"""
from __future__ import annotations
import hashlib
import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# canonical tokenizer (optional)
# ---------------------------------------------------------------------------
try:
    from tokenizer import (
        tokenize as _tok_tokenize,
        normalize_lang as _tok_normalize_lang,
    )
    TOKENIZER_AVAILABLE = True
except Exception:
    TOKENIZER_AVAILABLE = False
    def _tok_tokenize(text, lang="en"):
        return re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text or "")
    def _tok_normalize_lang(lang):
        return lang or "en"


# ---------------------------------------------------------------------------
# langdetect (optional)
# ---------------------------------------------------------------------------
try:
    from langdetect import detect as _detect, LangDetectException
    def detect_code_language(text: str, fallback: str = "en") -> str:
        if not text or len(text.strip()) < 3:
            return fallback
        try:
            return _detect(text)
        except LangDetectException:
            return fallback
        except Exception:
            return fallback
except ImportError:
    def detect_code_language(text: str, fallback: str = "en") -> str:
        return fallback


# ---------------------------------------------------------------------------
# memory.symbols
# ---------------------------------------------------------------------------
try:
    from symbols import recognize_symbols as _recognize
    def recognize_code_symbols(text: str, domain: str = "general") -> list:
        try:
            return _recognize(text, domain) or []
        except Exception:
            return []
except ImportError:
    def recognize_code_symbols(text: str, domain: str = "general") -> list:
        return []


# ---------------------------------------------------------------------------
# code_languages.CODE_TERMS
# ---------------------------------------------------------------------------
KEYWORDS: set = set()
BUILTINS: set = set()
try:
    from code_languages import CODE_TERMS
    def _flatten(obj):
        out = set()
        if isinstance(obj, dict):
            for v in obj.values():
                out |= _flatten(v)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for v in obj:
                out |= _flatten(v)
        elif isinstance(obj, str):
            out.add(obj.lower())
        return out
    _all_terms = _flatten(CODE_TERMS)
    KEYWORDS = _all_terms
except Exception:
    pass

# base keyword supplement (safe even if CODE_TERMS missing)
KEYWORDS |= {
    "def","class","return","if","elif","else","for","while","try","except",
    "finally","with","as","import","from","in","is","not","and","or","lambda",
    "yield","await","async","raise","pass","break","continue","global",
    "nonlocal","assert","del","match","case",
    "function","var","let","const","new","typeof","instanceof","export",
    "default","extends","super","this","switch","case","break","void","do",
    "public","private","protected","static","final","interface","implements",
    "package","throws","fn","impl","trait","match","use","mod","pub","struct",
    "enum","where","loop","mut","ref","dyn","async",
}
BUILTINS |= {
    "print","len","range","str","int","float","bool","list","dict","set",
    "tuple","type","self","cls","None","True","False","null","undefined",
    "true","false","this","super",
}


# ---------------------------------------------------------------------------
# classification  (code recognition, not letter index)
# ---------------------------------------------------------------------------

_RX_DUNDER = re.compile(r"^__[A-Za-z0-9_]+__$")
_RX_PRIVATE = re.compile(r"^_[A-Za-z0-9_]+$")
_RX_CONST = re.compile(r"^[A-Z][A-Z0-9_]+$")
_RX_CAMEL = re.compile(r"^[a-z]+[A-Z]")
_RX_FUNC_CALL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(")

COLOR_CLASSES = (
    "KEYWORD", "BUILTIN", "FUNC_DEF", "FUNC_CALL", "CLASS_DEF",
    "IDENT_VAR", "IDENT_PARAM", "IDENT_CONST", "IDENT_PRIVATE",
    "IDENT_DUNDER", "TYPE_ANNOT", "STRING", "NUMBER",
    "OPERATOR", "PUNCT", "COMMENT", "ERROR", "IDENT",
)

# color class -> column band inside 46-col grid
COLOR_TO_COL_BAND = {
    "KEYWORD":        (0, 5),
    "BUILTIN":        (5, 9),
    "FUNC_DEF":       (9, 14),
    "FUNC_CALL":      (14, 19),
    "CLASS_DEF":      (19, 23),
    "IDENT_CONST":    (23, 27),
    "IDENT_DUNDER":   (27, 30),
    "IDENT_PRIVATE":  (30, 33),
    "IDENT_PARAM":    (33, 36),
    "IDENT_VAR":      (36, 39),
    "TYPE_ANNOT":     (39, 41),
    "STRING":         (41, 43),
    "NUMBER":         (43, 44),
    "OPERATOR":       (44, 45),
    "PUNCT":          (45, 46),
    "ERROR":          (0, 46),
    "IDENT":          (36, 39),
}


def classify_code_token(token: str) -> str:
    if not token:
        return "PUNCT"
    t = token.strip()
    low = t.lower()
    if low in KEYWORDS:
        return "KEYWORD"
    if low in BUILTINS:
        return "BUILTIN"
    if _RX_DUNDER.match(t):
        return "IDENT_DUNDER"
    if _RX_CONST.match(t):
        return "IDENT_CONST"
    if _RX_PRIVATE.match(t):
        return "IDENT_PRIVATE"
    if t.endswith(":"):
        return "TYPE_ANNOT"
    if t.startswith(("'", '"')):
        return "STRING"
    if t.isdigit():
        return "NUMBER"
    if any(ch in t for ch in "+-*/%=<>!&|^~"):
        return "OPERATOR"
    if t.endswith(("(", ")", "[", "]", "{", "}", ",", ";", ".", ":")):
        return "PUNCT"
    if _RX_CAMEL.match(t) or t[:1].isupper():
        return "CLASS_DEF"
    return "IDENT_VAR"


# ---------------------------------------------------------------------------
# word_cell  (canonical GSP maths, unchanged)
# ---------------------------------------------------------------------------
try:
    from placement import word_cell
except Exception:
    try:
        from keyboard import word_cell
    except Exception:
        try:
            from keyboard import (
                calculate_lsum, calculate_ssum,
                first_letter_index, normalise,
            )
            def word_cell(token, lang="en"):
                t = normalise(token) if token else ""
                L = first_letter_index(t)
                return {"Lsum": calculate_lsum(t),
                        "Ssum": calculate_ssum(t),
                        "c": L, "L": L}
        except Exception:
            def word_cell(token, lang="en"):
                t = token or ""
                L = (ord(t[0]) if t else 0) % 26
                Lsum = sum(ord(c) for c in t)
                return {"Lsum": Lsum, "Ssum": Lsum % 97, "c": L, "L": L}


def _stable_hash(text: str, mod: int) -> int:
    if mod <= 0:
        return 0
    h = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
    return h % mod


def code_word_cell(token: str, lang: str = "en") -> Dict[str, Any]:
    """
    GSP metadata whose column is driven by code recognition,
    not by first-letter index.
    """
    base = word_cell(token, lang)
    color = classify_code_token(token)
    lo, hi = COLOR_TO_COL_BAND.get(color, (0, 46))
    span = max(1, hi - lo)
    c = lo + _stable_hash(f"{color}:{token}", span)
    return {
        "Lsum": base.get("Lsum", 0),
        "Ssum": base.get("Ssum", 0),
        "c": c,
        "L": base.get("L", 0),
        "color_class": color,
    }


# ---------------------------------------------------------------------------
# identifier splitting
# ---------------------------------------------------------------------------

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def split_code_identifiers(text: str) -> List[str]:
    try:
        if TOKENIZER_AVAILABLE:
            toks = _tok_tokenize(text or "")
            if toks:
                # tokenizer may return dicts or strings
                out = []
                for t in toks:
                    if isinstance(t, dict):
                        v = t.get("token") or t.get("word") or ""
                        if v:
                            out.append(str(v))
                    elif isinstance(t, str):
                        out.append(t)
                if out:
                    return out
    except Exception:
        pass
    return _IDENT_RE.findall(text or "")


def stem_token(token: str, lang: str = "en") -> str:
    return (token or "").lower()


def tokenize_code(text: str, lang: str = "en") -> List[Dict[str, Any]]:
    lang_code = detect_code_language(text, fallback=lang)
    out: List[Dict[str, Any]] = []
    for tok in split_code_identifiers(text):
        meta = code_word_cell(tok, lang_code)
        out.append({"token": tok, "lang": lang_code, **meta})
    return out
