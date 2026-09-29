"""
code_tokenizer.py
=================
Code-aware tokenizer bridge.

Exposes:
    word_cell(token, lang)          -> GSP metadata
    split_code_identifiers(text)    -> identifier list
    detect_code_language(text)      -> language code
    recognize_code_symbols(text)    -> symbols via memory.symbols
    stem_token(token, lang)         -> canonical form
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

# --- langdetect (optional) ---
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

# --- code_symbols (memory.symbols) ---
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

# --- word_cell ---
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

# --- identifier splitting ---
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

def split_code_identifiers(text: str) -> List[str]:
    return _IDENT_RE.findall(text or "")

def stem_token(token: str, lang: str = "en") -> str:
    return (token or "").lower()

def tokenize_code(text: str, lang: str = "en") -> List[Dict[str, Any]]:
    """Token list with GSP metadata and language tag."""
    out = []
    lang_code = detect_code_language(text, fallback=lang)
    for tok in split_code_identifiers(text):
        meta = word_cell(tok, lang_code)
        out.append({"token": tok, "lang": lang_code, **meta})
    return out
