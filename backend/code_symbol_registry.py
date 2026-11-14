"""
Canonical Code Symbol Registry.
Version 1.0.0 — 250 columns x 1 row.
Identity: -<zero-based column>.
Existing column assignments must never be reordered.
"""
from __future__ import annotations

CODE_SYMBOL_REGISTRY_VERSION = "1.0.0"
CODE_GRID_COLUMNS = 310
CODE_GRID_ROWS = 1

CODE_SYMBOLS = (
    # Arithmetic and mathematical operators
    "+", "−", "±", "∓", "×", "÷", "⋅", "·", "∘",
    "√", "∛", "∜", "∑", "∏", "∐", "∫", "∬", "∭",
    "∮", "∂", "∇", "∞",

    # Comparison and approximation
    "≠", "≡", "≈", "≃", "≅", "≔", "≕",
    "<", ">", "≤", "≥", "≪", "≫",

    # Geometry and relations
    "∝", "∠", "∡", "⊥", "∥", "∦", "∣", "∤",

    # Arrows
    "→", "←", "↔", "↑", "↓", "↦", "⟶", "⟵",

    # Set operators
    "∈", "∉", "∋", "∌", "⊂", "⊃", "⊆", "⊇",
    "∪", "∩", "∖", "∅",

    # Logic and proof
    "¬", "∧", "∨", "⊻", "⊼", "⊽",
    "∀", "∃", "∄", "⇒", "⇔", "⇐", "⊢", "⊨", "⊤",

    # Shell operators
    ";;&", ";&", ";;", ";", "&&", "||", "|&",
    ">>>", ">>", ">", "<<<", "<<", "<",
    ">&", "&>", "&>>", "<&", "<>", ">|",
    "$(", "${", "$((" , "))=",

    # Programming operators
    "===", "!==", "==", "!=", "<=", ">=",
    "=>", "->", "<-", "::", "?.", "??=", "??",
    "&&=", "||=", "**=", "//=", "<<=", ">>=", ">>>=",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "++", "--", "**", "//", "...", "..", "|>", "<|",
    ":=", "=", "-", "*", "/", "%", "^", "?", ":", ".",
    "@", "!", "#", "~", "`", "\\", "$", "&", "|",

    # Delimiters and punctuation
    "(", ")", "[", "]", "{", "}", ",", ";", "'", '"',

    # Markup and comment syntax
    "<!--", "-->", "/*", "*/", "///", "##", "###",
    "__", "</", "/>",

    # Regular expression syntax
    "\\d", "\\D", "\\w", "\\W", "\\s", "\\S",
    "\\b", "\\B", "\\A", "\\Z", "\\G",
    "(?:", "(?=", "(?!", "(?<=", "(?<!", "(?P<", "(?#",

    # Additional programming-language operators
    "!!", "?:", "<=>",

    # Additional mathematical operators
    "∴", "∵", "∼", "⊕", "⊗", "⊙",
    "⊞", "⊟", "⊠", "⊡", "∔", "∸", "∹", "∺", "∻",
    "∽", "∾", "≀", "≁", "≂", "≄", "≆", "≇", "≉", "≊",
    "≋", "≌", "≍", "≎", "≏", "≐", "≑", "≒", "≓", "≖",
    "≗", "≘", "≙", "≚", "≛", "≜", "≝", "≞", "≟",
    "⊣", "⊩", "⊪", "⊫", "⊬", "⊭", "⊮", "⊯", "⊰", "⊱",
    "⊲", "⊳", "⊴", "⊵", "⊶", "⊷", "⊸", "⊹", "⊺",
    "⋀", "⋁", "⋂", "⋃", "⋄", "⋆", "⋇", "⋈", "⋉", "⋊",
    "⋋", "⋌", "⋍", "⋎", "⋏", "⋐", "⋑", "⋒", "⋓", "⋔",
    "⋕", "⋖", "⋗", "⋘", "⋙", "⋚", "⋛", "⋜", "⋝", "⋞",
    "⋟", "⋠", "⋡", "⋢", "⋣", "⋤", "⋥", "⋦", "⋧", "⋨",
    "⋩", "⋪", "⋫", "⋬", "⋭", "⋮", "⋯", "⋰", "⋱",
)

# Deduplicate without changing the first assigned column.
_seen = set()
_ordered = []
for _symbol in CODE_SYMBOLS:
    if _symbol not in _seen:
        _seen.add(_symbol)
        _ordered.append(_symbol)

CODE_SYMBOLS = tuple(_ordered)

if len(CODE_SYMBOLS) > CODE_GRID_COLUMNS:
    raise RuntimeError(
        f"Registry has {len(CODE_SYMBOLS)} symbols; "
        f"grid capacity is {CODE_GRID_COLUMNS}"
    )

CODE_SYMBOL_TO_COLUMN = {
    symbol: index for index, symbol in enumerate(CODE_SYMBOLS)
}

CODE_SYMBOL_TO_ID = {
    symbol: f"-{index}"
    for symbol, index in CODE_SYMBOL_TO_COLUMN.items()
}

CODE_SYMBOL_MATCH_ORDER = tuple(
    sorted(CODE_SYMBOLS, key=lambda s: (-len(s), CODE_SYMBOL_TO_COLUMN[s]))
)


def code_symbol_identity(symbol: str) -> dict:
    if symbol not in CODE_SYMBOL_TO_COLUMN:
        raise KeyError(f"Unregistered code symbol: {symbol!r}")

    column = CODE_SYMBOL_TO_COLUMN[symbol]

    return {
        "type": "code",
        "token": symbol,
        "uid": f"-{column}",
        "grid": "code",
        "row": 0,
        "col": column,
        "columns": CODE_GRID_COLUMNS,
        "rows": CODE_GRID_ROWS,
        "registry_version": CODE_SYMBOL_REGISTRY_VERSION,
    }


def match_code_symbol(text: str, position: int = 0):
    for symbol in CODE_SYMBOL_MATCH_ORDER:
        if text.startswith(symbol, position):
            return symbol
    return None
