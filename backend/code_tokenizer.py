"""
Positional code tokenizer.

Code symbols use the canonical 250 x 1 Code Grid.
Code symbol identities are negative-prefixed: -0, -1, -2, ...
Numbers use the main tokenizer's DIGIT_MARKERS: 000 through 009.
Identifiers retain lexical letter/word placement.
"""
from __future__ import annotations

import re
from typing import Any

try:
    from code_symbol_registry import (
        CODE_GRID_COLUMNS,
        CODE_GRID_ROWS,
        CODE_SYMBOL_REGISTRY_VERSION,
        CODE_SYMBOL_TO_COLUMN,
        CODE_SYMBOL_TO_ID,
        CODE_SYMBOL_MATCH_ORDER,
        code_symbol_identity,
        match_code_symbol,
    )
except ImportError:
    from backend.code_symbol_registry import (
        CODE_GRID_COLUMNS,
        CODE_GRID_ROWS,
        CODE_SYMBOL_REGISTRY_VERSION,
        CODE_SYMBOL_TO_COLUMN,
        CODE_SYMBOL_TO_ID,
        CODE_SYMBOL_MATCH_ORDER,
        code_symbol_identity,
        match_code_symbol,
    )

try:
    from tokenizer import (
        normalize_lang,
        normalize_lexical_token,
        lexical_identity,
        letter_cells,
        word_cell,
        stem_token,
        DIGIT_MARKERS,
    )
except ImportError:
    from backend.tokenizer.tokenizer import (
        normalize_lang,
        normalize_lexical_token,
        lexical_identity,
        letter_cells,
        word_cell,
        stem_token,
        DIGIT_MARKERS,
    )


try:
    from symbols import recognize_symbols as _recognize_symbols
except ImportError:
    try:
        from memory.symbols import recognize_symbols as _recognize_symbols
    except ImportError:
        def _recognize_symbols(text, domain="general"):
            return []


KEYWORDS = {
    "def", "class", "return", "if", "elif", "else", "for", "while",
    "try", "except", "finally", "with", "as", "import", "from", "in",
    "is", "not", "and", "or", "lambda", "yield", "await", "async",
    "raise", "pass", "break", "continue", "global", "nonlocal",
    "assert", "del", "match", "case", "function", "var", "let",
    "const", "new", "typeof", "instanceof", "export", "default",
    "extends", "super", "this", "switch", "void", "public",
    "private", "protected", "static", "interface", "implements",
    "package", "throws", "fn", "impl", "trait", "use", "mod",
    "pub", "struct", "enum", "where", "loop", "mut", "ref", "dyn",
}

BUILTINS = {
    "print", "len", "range", "str", "int", "float", "bool",
    "list", "dict", "set", "tuple", "type", "self", "cls",
    "None", "True", "False", "null", "undefined", "true", "false",
}

_IDENT_START = re.compile(r"[^\W\d]|_", re.UNICODE)
_IDENT_CONTINUE = re.compile(r"[\w]", re.UNICODE)


def detect_code_language(text: str, fallback: str = "en") -> str:
    return fallback


def recognize_code_symbols(text: str, domain: str = "code") -> list:
    try:
        return _recognize_symbols(text, domain) or []
    except Exception:
        return []


def classify_code_token(token: str) -> str:
    if not token:
        return "PUNCT"
    if token.startswith(('"', "'")):
        return "STRING"
    if token.startswith(("#", "//", "/*")):
        return "COMMENT"
    if token.isdigit():
        return "NUMBER"
    if token.lower() in KEYWORDS:
        return "KEYWORD"
    if token in BUILTINS:
        return "BUILTIN"
    if token in CODE_SYMBOL_TO_COLUMN:
        return "OPERATOR"
    if _IDENT_START.match(token):
        return "IDENT"
    return "PUNCT"


def code_word_cell(token: str, lang: str = "en") -> dict:
    """Lexical identity metadata only; placement belongs to the main tokenizer."""
    normalized = normalize_lexical_token(token, lang)
    identity = lexical_identity(normalized, lang) if normalized else {}
    return {
        "L": identity.get("L", 0),
        "S": identity.get("S", 0),
        "SC": identity.get("SC", 0),
        "uid": identity.get("uid", ""),
        "uid_sequence": list(identity.get("uid_sequence", [])),
        "identity_type": "letter" if normalized else "symbol",
        "color_class": classify_code_token(token),
    }


def word_cell(token: str, lang: str = "en") -> dict:
    return code_word_cell(token, lang)


def split_code_identifiers(text: str) -> list[str]:
    return [
        m.group(0)
        for m in re.finditer(r"[^\W\d]\w*|_\w*", text or "", re.UNICODE)
    ]


def _scan_string(text: str, start: int) -> int:
    quote = text[start]
    triple = text.startswith(quote * 3, start)
    delimiter = quote * (3 if triple else 1)
    i = start + len(delimiter)

    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text.startswith(delimiter, i):
            return min(len(text), i + len(delimiter))
        i += 1

    return len(text)


def tokenize_code(text: str, lang: str = "en") -> list[dict[str, Any]]:
    """
    Scan source left-to-right. Every returned record has exact source offsets.
    Longest registered symbol wins. Numeric digits are separate typed tokens.
    """
    source = text or ""
    language = normalize_lang(lang)
    output = []
    i = 0
    occurrence = 0

    while i < len(source):
        ch = source[i]

        if ch.isspace():
            i += 1
            continue

        start = i
        record = None

        # Quoted strings are kept whole; their contents are not split.
        if ch in ("'", '"'):
            i = _scan_string(source, i)
            token = source[start:i]
            record = {
                "type": "string",
                "token": token,
                "identity_type": "string",
                "uid": None,
                "grid": None,
                "class": "STRING",
            }

        # Line comments.
        elif source.startswith("//", i) or ch == "#":
            newline = source.find("\n", i)
            i = len(source) if newline < 0 else newline
            token = source[start:i]
            record = {
                "type": "comment",
                "token": token,
                "identity_type": "comment",
                "uid": None,
                "grid": None,
                "class": "COMMENT",
            }

        # Block comments.
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = len(source) if end < 0 else end + 2
            token = source[start:i]
            record = {
                "type": "comment",
                "token": token,
                "identity_type": "comment",
                "uid": None,
                "grid": None,
                "class": "COMMENT",
            }

        # Numeric runs: each digit gets its own 000-009 identity.
        elif ch.isdigit():
            while i < len(source) and source[i].isdigit():
                i += 1
            token = source[start:i]
            digits = [
                {
                    "digit": digit,
                    "uid": DIGIT_MARKERS[digit],
                    "position": start + offset,
                }
                for offset, digit in enumerate(token)
            ]
            record = {
                "type": "number",
                "token": token,
                "identity_type": "number",
                "uid": [item["uid"] for item in digits],
                "digits": digits,
                "grid": "digit",
                "class": "NUMBER",
            }

        # Identifiers and language keywords.
        elif _IDENT_START.match(ch):
            i += 1
            while i < len(source) and _IDENT_CONTINUE.match(source[i]):
                i += 1
            token = source[start:i]
            normalized = normalize_lexical_token(token, language)
            identity = lexical_identity(normalized, language)
            kind = "keyword" if token.lower() in KEYWORDS else (
                "builtin" if token in BUILTINS else "identifier"
            )

            record = {
                "type": kind,
                "token": token,
                "original": token,
                "normalized": normalized,
                "stem": stem_token(normalized, language),
                "identity_type": "letter",
                "uid": identity.get("uid"),
                "uID": identity.get("uID"),
                "uid_sequence": list(identity.get("uid_sequence", [])),
                "uID_sequence": list(identity.get("uID_sequence", [])),
                "L": identity.get("L", 0),
                "S": identity.get("S", 0),
                "SC": identity.get("SC", 0),
                "letter": letter_cells(normalized, language),
                "word": word_cell(normalized, language),
                "grid": "word",
                "class": classify_code_token(token),
            }

        else:
            symbol = match_code_symbol(source, i)
            if symbol is not None:
                i += len(symbol)
                record = {
                    "type": "code_symbol",
                    "token": symbol,
                    **code_symbol_identity(symbol),
                    "class": "OPERATOR",
                }
            else:
                # Preserve unknown punctuation rather than silently dropping it.
                i += 1
                token = source[start:i]
                record = {
                    "type": "unregistered_symbol",
                    "token": token,
                    "identity_type": "unregistered",
                    "uid": None,
                    "grid": None,
                    "class": "PUNCT",
                }

        record.update({
            "token_index": occurrence,
            "start": start,
            "end": i,
            "source": source[start:i],
            "lang": language,
        })
        output.append(record)
        occurrence += 1

    return output


def code_grid_config() -> dict:
    return {
        "grid": "code",
        "columns": CODE_GRID_COLUMNS,
        "rows": CODE_GRID_ROWS,
        "registry_version": CODE_SYMBOL_REGISTRY_VERSION,
        "registered_symbols": len(CODE_SYMBOL_TO_COLUMN),
        "reserved_columns": CODE_GRID_COLUMNS - len(CODE_SYMBOL_TO_COLUMN),
        "identity_format": "-<zero-based-column>",
    }
