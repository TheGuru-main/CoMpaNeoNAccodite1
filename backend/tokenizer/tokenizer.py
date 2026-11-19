"""
CoMpaNeoN Tokenizer
===================

Multilingual lexical tokenizer and deterministic identity foundation.

The tokenizer is responsible for:

- language normalization
- multilingual character/alphabet handling
- multilingual keyboard/input metadata
- Unicode-safe tokenization
- lexical normalization
- character decomposition
- 0-based alphabet indexing
- ordered lexical UID generation
- lexical UID serialization
- lexical UID S calculation
- L / S / SC generation
- 46 × 26 word-grid placement inputs
- letter-grid indexing
- symbol recognition
- lightweight stem metadata
- lexical similarity signals
- compatibility helpers used by existing CoMpaNeoN modules

The tokenizer does NOT own:

- GSP crawler traversal
- GSP K traversal
- GSP forward/backward jumps
- XOR sharding
- quorum routing
- MemoryGrid storage
- full-text placement
- full-text UID chaining
- ranking policy
- WordChain
- WordUnderstanding
- POS analysis
- linguistic analysis
- semantic analysis
- dictionary enrichment
- prompt management
- AI response generation

IMPORTANT IDENTITY RULE
-----------------------

Alphabet indexes are ZERO-BASED.

English:

    A = 0
    B = 1
    ...
    Z = 25

Example:

    ZED -> [25, 4, 3]
    ZEE -> [25, 4, 4]

The ordered UID sequence is preserved.

Serialized UID:

    ZED -> "2543"
    ZEE -> "2544"

S is NOT the digit sum of the serialized UID.

Instead:

    S = sum(uid_sequence)

Therefore:

    ZED -> 25 + 4 + 3 = 32
    ZEE -> 25 + 4 + 4 = 33

WORD GRID
---------

The word grid remains:

    46 columns × 26 rows

Word placement uses:

    row = ((L + S - 1) % 26) + 1

where:

    L = normalized lexical token length
    S = sum(uid_sequence)

SC is:

    SC = first-letter alphabet index

SC is NOT a random value and is NOT derived from word-row math.

FULL TEXT
---------

The tokenizer preserves each word's ordered UID sequence.

The full-text placement layer may then use those UID sequences for
column-index chaining and calculate the total/full-text UID and S.

The tokenizer does not perform full-text placement.

GSP START ROW
-------------

Lexical UID identity is separate from the GSP keyboard-placement
authority.

When a GSP start row is requested, this module delegates to keyboard.py
when available.

The tokenizer does not apply crawler K/D traversal.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable


# ---------------------------------------------------------------------
# Optional GSP keyboard companion
# ---------------------------------------------------------------------

try:
    import keyboard  # type: ignore
except ImportError:
    keyboard = None


# =====================================================================
# MULTILINGUAL KEY LINES
# =====================================================================

EN_KEY_LINE = "QWERTYUIOPASDFGHJKLZXCVBNM"
FR_KEY_LINE = "AZERTYUIOPQSDFGHJKLMWXCVBN"
DE_KEY_LINE = "QWERTZUIOPASDFGHJKLYXCVBNM"

AR_KEY_LINE = "ضصثقفغعهخحجدشسيبلاتنمكطئءؤرلاىةوزظ"
HE_KEY_LINE = "קראטוןםפשדגכעיחלךףזסבהנמצתץ"
EL_KEY_LINE = ";ςερτυθιοπασδφγηξκλζχψωβνμ"
RU_KEY_LINE = "йцукенгшщзхъфывапролджэячсмитьбю"
UK_KEY_LINE = "йцукенгшщзхїфівапролдэжячсмитьбю"

HI_KEY_LINE = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
BN_KEY_LINE = "কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহ"

JA_HIRAGANA_KEY_LINE = (
    "あいうえお"
    "かきくけこ"
    "さしすせそ"
    "たちつてと"
    "なにぬねの"
    "はひふへほ"
    "まみむめも"
    "やゆよ"
    "らりるれろ"
    "わをん"
)

KO_HANGUL_KEY_LINE = (
    "ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔ"
    "ㅁㄴㅇㄹㅎㅗㅓㅏㅣ"
    "ㅋㅌㅊㅍㅠㅜㅡ"
)

ZH_PINYIN_KEY_LINE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

TR_KEY_LINE = "QWERTYUIOPĞÜASDFGHJKLŞİZXCVBNMÖÇ"
ES_KEY_LINE = "QWERTYUIOPASDFGHJKLÑZXCVBNM"
IT_KEY_LINE = "QWERTYUIOPÈASDFGHJKLÒÀZXCVBNM"
PT_KEY_LINE = "QWERTYUIOP´ASDFGHJKLÇ~ZXCVBNM"
NL_KEY_LINE = "QWERTYUIOPASDFGHJKLZXCVBNM"
PL_KEY_LINE = "QWERTYUIOPĄASDFGHJKLŚZXCVBNMĘ"
CS_KEY_LINE = "QWERTZUIOPÚASDFGHJKLÝZXCVBNM"
SV_KEY_LINE = "QWERTYUIOPÅASDFGHJKLÖZXCVBNM"
NO_KEY_LINE = "QWERTYUIOPÅASDFGHJKLØZXCVBNM"
DA_KEY_LINE = "QWERTYUIOPÅASDFGHJKLÆZXCVBNM"
FI_KEY_LINE = "QWERTYUIOPÅASDFGHJKLÖZXCVBNM"
VI_KEY_LINE = "QWERTYUIOPASDFGHJKLZXCVBNMĐ"

TH_KEY_LINE = (
    "กขคฆงจฉชซฌญฎฏฐฑฒณดตถทธน"
    "บปผฝพฟภมยรฤลฦวศษสหฬอฮ"
)


KEY_LINES: dict[str, str] = {
    "en": EN_KEY_LINE,
    "fr": FR_KEY_LINE,
    "de": DE_KEY_LINE,
    "ar": AR_KEY_LINE,
    "he": HE_KEY_LINE,
    "el": EL_KEY_LINE,
    "ru": RU_KEY_LINE,
    "uk": UK_KEY_LINE,
    "hi": HI_KEY_LINE,
    "bn": BN_KEY_LINE,
    "ja": JA_HIRAGANA_KEY_LINE,
    "ko": KO_HANGUL_KEY_LINE,
    "zh": ZH_PINYIN_KEY_LINE,
    "tr": TR_KEY_LINE,
    "es": ES_KEY_LINE,
    "it": IT_KEY_LINE,
    "pt": PT_KEY_LINE,
    "nl": NL_KEY_LINE,
    "pl": PL_KEY_LINE,
    "cs": CS_KEY_LINE,
    "sv": SV_KEY_LINE,
    "no": NO_KEY_LINE,
    "da": DA_KEY_LINE,
    "fi": FI_KEY_LINE,
    "vi": VI_KEY_LINE,
    "th": TH_KEY_LINE,
}


# =====================================================================
# LANGUAGE ALPHABETS
# =====================================================================

ALPHABETS: dict[str, str] = {
    "en": "abcdefghijklmnopqrstuvwxyz",

    "fr": "abcdefghijklmnopqrstuvwxyzàâäæçéèêëïîôœùûüÿ",
    "de": "abcdefghijklmnopqrstuvwxyzäöüß",
    "es": "abcdefghijklmnopqrstuvwxyzáéíóúüñ",
    "pt": "abcdefghijklmnopqrstuvwxyzáàâãéêíóôõúç",

    "ar": "ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأؤإئىة",

    "zh": "abcdefghijklmnopqrstuvwxyz",

    "hi": (
        "अआइईउऊऋएऐओऔ"
        "कखगघङचछजझञटठडढण"
        "तथदधनपफबभम"
        "यरलवशषसह"
        "क्षज्ञ"
    ),

    "yo": "abcdefghijklmnopqrstuvwxyzáàéèẹíìóòọúùṣń",
    "ha": "abcdefghijklmnopqrstuvwxyzɓɗƙƴ",
    "ig": "abcdefghijklmnopqrstuvwxyzịñọụ",
    "sw": "abcdefghijklmnopqrstuvwxyz",

    "tr": "abcçdefgğhıijklmnoöprsştuüvyz",
    "id": "abcdefghijklmnopqrstuvwxyz",
    "it": "abcdefghijklmnopqrstuvwxyzàèéìíîòóùú",

    "he": "אבגדהוזחטיכלמנסעפצקרשתךםןףץ",
    "el": "αβγδεζηθικλμνξοπρστυφχψω",

    "ru": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    "uk": "абвгдеєжзиіїйклмнопрстуфхцчшщьюя",

    "bn": (
        "অআইঈউঊঋএঐওঔ"
        "কখগঘঙচছজঝঞ"
        "টঠডঢণতথদধন"
        "পফবভমযরলশষসহ"
    ),

    "ja": (
        "あいうえお"
        "かきくけこ"
        "さしすせそ"
        "たちつてと"
        "なにぬねの"
        "はひふへほ"
        "まみむめも"
        "やゆよ"
        "らりるれろ"
        "わをん"
    ),

    "ko": (
        "ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔ"
        "ㅁㄴㅇㄹㅎㅗㅓㅏㅣ"
        "ㅋㅌㅊㅍㅠㅜㅡ"
    ),

    "th": (
        "กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธน"
        "บปผฝพฟภมยรลวศษสหฬอฮ"
    ),

    "vi": "abcdefghijklmnopqrstuvwxyzăâđêôơư",

    "nl": "abcdefghijklmnopqrstuvwxyz",
    "pl": "aąbcćdeęfghijklłmnńoóprsśtuwyzźż",
    "cs": "aábcčdďeéfghiíjklmnoópqrřsštťuúůvwxyýzž",
    "sv": "abcdefghijklmnopqrstuvwxyzåäö",
    "no": "abcdefghijklmnopqrstuvwxyzæøå",
    "da": "abcdefghijklmnopqrstuvwxyzæøå",
    "fi": "abcdefghijklmnopqrstuvwxyzåäö",
}

ALPHABETS["default"] = ALPHABETS["en"]

# =====================================================================
# DIGIT SPECIAL IDENTIFIERS (roman-style markers — avoid serialize collapse)
# =====================================================================
# Raw digit indexes 0-9 in uid_sequence collapse under serialize_uid
# (e.g. [4,2] == "42"). Each digit expands to letter indexes of a marker.

DIGIT_MARKERS: dict[str, str] = {
    "0": "000",
    "1": "001",
    "2": "002",
    "3": "003",
    "4": "004",
    "5": "005",
    "6": "006",
    "7": "007",
    "8": "008",
    "9": "009",
}


KEY_LINES["default"] = KEY_LINES["en"]


# =====================================================================
# LANGUAGE ALIASES
# =====================================================================

LANG_ALIASES: dict[str, str] = {
    "eng": "en",
    "fra": "fr",
    "fre": "fr",
    "deu": "de",
    "ger": "de",
    "spa": "es",
    "por": "pt",
    "ara": "ar",
    "zho": "zh",
    "cmn": "zh",
    "mandarin": "zh",
    "hin": "hi",
    "yor": "yo",
    "hau": "ha",
    "ibo": "ig",
    "swa": "sw",
    "tur": "tr",
    "ind": "id",
    "msa": "id",
    "ms": "id",
    "ita": "it",
    "heb": "he",
    "ell": "el",
    "gre": "el",
    "rus": "ru",
    "ukr": "uk",
    "ben": "bn",
    "jpn": "ja",
    "kor": "ko",
    "tha": "th",
    "vie": "vi",
    "nld": "nl",
    "dut": "nl",
    "pol": "pl",
    "ces": "cs",
    "cze": "cs",
    "swe": "sv",
    "nor": "no",
    "dan": "da",
    "fin": "fi",
    "pcm": "en",
}


# =====================================================================
# GRID CONSTANTS
# =====================================================================

# Letter grid is one row.
LETTER_GRID_R = 1

# Word placement is always reduced against 26 rows.
WORD_GRID_R = 26

# The physical word grid is 46 columns × 26 rows.
WORD_GRID_COLUMNS = 46
WORD_GRID_ROWS = 26

# These remain metadata only.
FORWARD_D = 5
BACKWARD_D = 1


# =====================================================================
# STEM METADATA
# =====================================================================

PREFIXES = (
    "un",
    "re",
    "pre",
    "mis",
    "dis",
    "over",
    "under",
    "out",
)

SUFFIXES = (
    "tions",
    "tion",
    "ings",
    "ing",
    "edly",
    "ed",
    "es",
    "s",
    "ly",
    "ness",
    "ment",
    "able",
    "ible",
    "ers",
    "er",
    "ors",
    "or",
)


# =====================================================================
# CHARACTER FOLDING
# =====================================================================

_FOLD = str.maketrans(
    {
        "à": "a",
        "á": "a",
        "â": "a",
        "ä": "a",
        "ã": "a",
        "å": "a",
        "æ": "ae",
        "ç": "c",

        "è": "e",
        "é": "e",
        "ê": "e",
        "ë": "e",

        "ì": "i",
        "í": "i",
        "î": "i",
        "ï": "i",
        "ı": "i",

        "ò": "o",
        "ó": "o",
        "ô": "o",
        "ö": "o",
        "õ": "o",
        "œ": "oe",

        "ù": "u",
        "ú": "u",
        "û": "u",
        "ü": "u",

        "ÿ": "y",
        "ñ": "n",

        "ş": "s",
        "ṣ": "s",
        "ğ": "g",
        "ß": "ss",

        "ẹ": "e",
        "ọ": "o",
        "ị": "i",
        "ụ": "u",
        "ń": "n",

        "ɓ": "b",
        "ɗ": "d",
        "ƙ": "k",
        "ƴ": "y",

        "đ": "d",
        "ơ": "o",
        "ư": "u",
        "ă": "a",
    }
)


# =====================================================================
# GLOBAL SYMBOL BOARD
# =====================================================================

GLOBAL_SYMBOLS_BOARD: dict[str, tuple[str, ...]] = {
    "punctuation": (
        ".",
        ",",
        ";",
        ":",
        "!",
        "?",
        "¿",
        "¡",
        "'",
        '"',
        "`",
        "´",
        "’",
        "‘",
        "“",
        "”",
        "…",
        "-",
        "–",
        "—",
        "_",
    ),

    "mathematical": (
        "+",
        "-",
        "*",
        "/",
        "%",
        "=",
        "<",
        ">",
        "≤",
        "≥",
        "≠",
        "≈",
        "≡",
        "×",
        "÷",
        "±",
        "√",
        "∞",
        "^",
        "|",
    ),

    "programming": (
        "#",
        "@",
        "$",
        "&",
        "~",
        "^",
        "*",
        "/",
        "\\",
        "%",
        "!",
        "?",
        ":",
        ";",
        ".",
        ",",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        "<",
        ">",
        "=",
        "_",
        "`",
    ),

    "structure": (
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        "<",
        ">",
        "/",
        "\\",
        "|",
        ":",
        ";",
        ",",
        ".",
    ),

    "currency": (
        "$",
        "€",
        "£",
        "₦",
        "¥",
        "₹",
        "₽",
        "₩",
        "₺",
        "₴",
        "₫",
        "₵",
        "₡",
        "₱",
    ),

    "logic": (
        "&",
        "|",
        "!",
        "¬",
        "∧",
        "∨",
        "→",
        "←",
        "↔",
        "⊕",
        "⊤",
        "⊥",
    ),

    "comparison": (
        "=",
        "==",
        "===",
        "!=",
        "!==",
        "<",
        ">",
        "<=",
        ">=",
        "≤",
        "≥",
    ),

    "arrows": (
        "→",
        "←",
        "↑",
        "↓",
        "↔",
        "↕",
        "⇒",
        "⇐",
        "⇔",
        "↗",
        "↘",
        "↙",
        "↖",
    ),

    "operators": (
        "+",
        "-",
        "*",
        "/",
        "%",
        "**",
        "//",
        "++",
        "--",
        "+=",
        "-=",
        "*=",
        "/=",
    ),

    "markup": (
        "#",
        "##",
        "###",
        "*",
        "**",
        "_",
        "__",
        "`",
        "```",
        ">",
        "-",
        "+",
    ),

    "social": (
        "@",
        "#",
        "&",
    ),

    "special": (
        "©",
        "®",
        "™",
        "§",
        "¶",
        "°",
        "•",
        "·",
        "†",
        "‡",
    ),
}


def _build_symbol_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}

    for category, symbols in GLOBAL_SYMBOLS_BOARD.items():
        for symbol in symbols:
            index.setdefault(symbol, [])

            if category not in index[symbol]:
                index[symbol].append(category)

    return index


GLOBAL_SYMBOL_INDEX = _build_symbol_index()


def recognize_global_symbols(text: str) -> list[dict[str, Any]]:
    """
    Return recognized symbols without altering the original text.
    """

    if not text:
        return []

    found: list[dict[str, Any]] = []

    # Longest symbols first so === is recognized before =.
    symbols = sorted(
        GLOBAL_SYMBOL_INDEX.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for symbol, categories in symbols:
        if symbol in text:
            found.append(
                {
                    "symbol": symbol,
                    "categories": list(categories),
                }
            )

    return found


def global_symbols_board() -> dict[str, tuple[str, ...]]:
    return {
        category: tuple(symbols)
        for category, symbols in GLOBAL_SYMBOLS_BOARD.items()
    }


# =====================================================================
# LANGUAGE NORMALIZATION
# =====================================================================

def normalize_lang(lang: str | None) -> str:
    """
    Normalize a language code.

    Unknown language codes are preserved as lower-case codes rather
    than forcing the text itself into English.
    """

    if not lang:
        return "en"

    code = (
        str(lang)
        .strip()
        .lower()
        .replace("_", "-")
    )

    code = code.split("-")[0]

    return LANG_ALIASES.get(code, code)



def detect_lang(text: str | None, fallback: str = "en") -> str:
    """
    Detect language for GSP placement / tokenization.

    Order:
      1) Script heuristics (Arabic, Cyrillic, CJK, Hangul, Hebrew, Thai, Devanagari, Bengali, Kana)
      2) langdetect when available and text is long enough
      3) fallback (default en)

    Result is always passed through normalize_lang / LANG_ALIASES.
    """
    s = (text or "").strip()
    if not s:
        return normalize_lang(fallback)

    # Script-first (short names / labels often too short for langdetect)
    for ch in s:
        o = ord(ch)
        if 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F:
            return normalize_lang("ar")
        if 0x0400 <= o <= 0x04FF:
            return normalize_lang("ru")
        if 0x4E00 <= o <= 0x9FFF:
            return normalize_lang("zh")
        if 0x3040 <= o <= 0x30FF:
            return normalize_lang("ja")
        if 0xAC00 <= o <= 0xD7AF:
            return normalize_lang("ko")
        if 0x0590 <= o <= 0x05FF:
            return normalize_lang("he")
        if 0x0E00 <= o <= 0x0E7F:
            return normalize_lang("th")
        if 0x0900 <= o <= 0x097F:
            return normalize_lang("hi")
        if 0x0980 <= o <= 0x09FF:
            return normalize_lang("bn")
        if 0x0370 <= o <= 0x03FF:
            return normalize_lang("el")

    # Latin extended hints (Yoruba / French diacritics common in Accodite)
    low = s.lower()
    if any(ch in low for ch in "ẹọṣń"):
        return normalize_lang("yo")
    if any(ch in low for ch in "àâäæçéèêëïîôœùûüÿ") and len(s) >= 3:
        # Prefer fr when French-heavy diacritics dominate
        fr_marks = sum(1 for ch in low if ch in "àâäæçéèêëïîôœùûüÿ")
        if fr_marks >= 1:
            return normalize_lang("fr")

    try:
        from langdetect import detect as _ld_detect
        from langdetect.lang_detect_exception import LangDetectException
        sample = s if len(s) >= 12 else (s + " " + s)  # pad short labels slightly
        code = _ld_detect(sample)
        return normalize_lang(code)
    except Exception:
        pass

    return normalize_lang(fallback)


def alphabet_for(lang: str | None) -> str:
    """
    Return the known alphabet for a language.

    Unknown languages receive the generic Unicode alphabet sentinel.
    Their actual characters are indexed deterministically through the
    fallback alphabet builder.
    """

    code = normalize_lang(lang)

    if code in ALPHABETS:
        return ALPHABETS[code]

    return ALPHABETS["default"]


def key_line_for(lang: str | None) -> str:
    code = normalize_lang(lang)
    return KEY_LINES.get(code, KEY_LINES["default"])


def _unicode_alphabet_for_text(text: str) -> str:
    """
    Build a deterministic alphabet for an unsupported script/language.

    This is intentionally based on Unicode code-point ordering rather
    than an arbitrary encounter order.

    Known language alphabets always take precedence.
    """

    chars: set[str] = set()

    for ch in text:
        if ch.isalpha():
            chars.add(ch.lower())

    return "".join(sorted(chars, key=lambda c: ord(c)))


def grid_dims(lang: str | None) -> dict[str, Any]:
    """
    Report tokenizer/grid dimensions.

    Letter-grid dimensions follow the active language alphabet.

    Word placement itself remains fixed at:

        46 × 26
    """

    code = normalize_lang(lang)
    alpha = alphabet_for(code)

    return {
        "A": len(alpha),
        "letter": f"{len(alpha)}x1",
        "word": f"{WORD_GRID_COLUMNS}x{WORD_GRID_ROWS}",
        "letter_R": LETTER_GRID_R,
        "word_R": WORD_GRID_R,
        "word_columns": WORD_GRID_COLUMNS,
        "word_rows": WORD_GRID_ROWS,
        "lang": code,
    }


# =====================================================================
# NORMALIZATION
# =====================================================================

def normalize_text(text: str | None) -> str:
    """
    Unicode-safe general text normalization.

    Keeps letters, numbers, whitespace and symbols.
    """

    if text is None:
        return ""

    text = unicodedata.normalize("NFKC", str(text))

    # Normalize whitespace without destroying non-Latin scripts.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_lexical_token(
    token: str | None,
    lang: str | None = "en",
) -> str:
    """
    Normalize a lexical token while preserving its script.

    IMPORTANT:
    - punctuation around a word is not part of lexical identity
    - Unicode letters/numbers are retained
    - the lexical UID is based on this full normalized token
    - stemming does NOT alter UID identity
    """

    if token is None:
        return ""

    text = unicodedata.normalize("NFKC", str(token)).strip().lower()

    if not text:
        return ""

    # Keep every Unicode letter/number.
    chars = []

    for ch in text:
        if ch.isalnum():
            chars.append(ch)

    return "".join(chars)


# =====================================================================
# STEM METADATA
# =====================================================================

def stem_token(token: str, lang: str = "en") -> str:
    """
    Lightweight stem metadata.

    The stem is NOT used to generate lexical UID.

    This function remains intentionally conservative for non-Latin
    languages.
    """

    code = normalize_lang(lang)
    w = normalize_lexical_token(token, code)

    if not w:
        return ""

    if code in {
        "ar",
        "hi",
        "bn",
        "ja",
        "ko",
        "th",
        "he",
        "el",
        "ru",
        "uk",
    }:
        return w

    if len(w) < 4:
        return w

    for pref in sorted(PREFIXES, key=len, reverse=True):
        if w.startswith(pref) and len(w) - len(pref) >= 3:
            w = w[len(pref):]
            break

    for suffix in sorted(SUFFIXES, key=len, reverse=True):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[: -len(suffix)]
            break

    return w or normalize_lexical_token(token, code)


# =====================================================================
# ALPHABET INDEXING
# =====================================================================

def alphabet_index(
    ch: str,
    lang: str = "en",
    text_context: str | None = None,
) -> int | None:
    """
    Return the deterministic ZERO-BASED alphabet index.

    For known languages:
        use the configured language alphabet.

    For unknown languages/scripts:
        construct a deterministic Unicode alphabet from the supplied
        text context.

    English example:

        A -> 0
        Z -> 25
    """

    if not ch:
        return None

    code = normalize_lang(lang)
    ch = str(ch)[0].lower()

    alpha = ALPHABETS.get(code)

    if alpha is not None:
        if ch in alpha:
            return alpha.index(ch)

        # Accent/code-mix bridge.
        folded = ch.translate(_FOLD)

        if folded in alpha:
            return alpha.index(folded)

        # Latin bridge to English.
        if folded in ALPHABETS["en"]:
            return ALPHABETS["en"].index(folded)

        if len(folded) > 1 and folded[0] in ALPHABETS["en"]:
            return ALPHABETS["en"].index(folded[0])

        return None

    # Unknown language/script.
    context = text_context or ch
    dynamic_alpha = _unicode_alphabet_for_text(context)

    if ch in dynamic_alpha:
        return dynamic_alpha.index(ch)

    return None


def raw_letter_index(
    ch: str,
    lang: str = "en",
    text_context: str | None = None,
) -> int | None:
    """
    Alias for the unreduced zero-based alphabet index.
    """

    return alphabet_index(ch, lang, text_context)


def letter_index(
    ch: str,
    lang: str = "en",
    text_context: str | None = None,
) -> int | None:
    """
    Letter-grid column.

    Letter grid is A × 1.

    Row is always 0.

    No K.
    No GSP traversal.
    """

    return alphabet_index(ch, lang, text_context)


def letter_cell(
    ch: str,
    lang: str = "en",
    text_context: str | None = None,
) -> dict[str, int] | None:
    col = letter_index(ch, lang, text_context)

    if col is None:
        return None

    return {
        "col": col,
        "row": 0,
        "R": LETTER_GRID_R,
    }


def letter_cells(
    token: str,
    lang: str = "en",
) -> list[int]:
    """
    Return the ordered character-index path.

    This is NOT the lexical UID helper; it is retained as a
    compatibility/letter-grid signal.
    """

    token = str(token or "")
    cells: list[int] = []

    for ch in token:
        index = letter_index(
            ch,
            lang,
            text_context=token,
        )

        if index is not None:
            cells.append(index)

    return cells


def first_letter_index(
    word: str,
    lang: str = "en",
) -> int:
    """
    SC — first-letter alphabet index.

    SC is constant for the token.

    It is not:
        - random
        - modulo 26
        - modulo word-row
        - derived from L + S
    """

    if not word:
        return 0

    normalized = normalize_lexical_token(word, lang)

    if not normalized:
        return 0

    index = alphabet_index(
        normalized[0],
        lang,
        text_context=normalized,
    )

    return 0 if index is None else index


# =====================================================================
# LEXICAL UID
# =====================================================================

def uid_sequence(
    token: str,
    lang: str = "en",
) -> list[int]:
    """
    Ordered identity sequence for train + content place.

    Letters  -> zero-based alphabet indexes (A/a -> 0 kept).
    Digits   -> DIGIT_MARKERS expanded (never stripped).
    Other alnum kept via alphabet_index when in alphabet.

    Code symbols (# / . ( ) etc.) are NOT stripped at this layer when
    present in the raw token: use uid_sequence_with_code() so registry
    markers are interleaved. Plain uid_sequence still walks the raw
    string for digits+letters without alnum-only wiping of the scan.
    """

    raw = str(token or "")
    if not raw:
        return []

    code = normalize_lang(lang)
    sequence: list[int] = []

    # Walk RAW characters so digits are not lost before marker expand.
    # Letters use alphabet_index; digits expand DIGIT_MARKERS.
    for ch in raw:
        if ch.isspace():
            continue

        if ch.isdigit() and ch in DIGIT_MARKERS:
            # Expand marker identity into the sequence (do not skip).
            marker = DIGIT_MARKERS[ch]
            for mch in marker:
                if mch.isdigit():
                    # Typed marker component: distinct from letter index 0..N
                    # Use 1000+d so serialize boundaries stay recoverable later.
                    sequence.append(1000 + int(mch))
                else:
                    idx = alphabet_index(mch, code, text_context=raw)
                    if idx is not None:
                        sequence.append(int(idx))
            continue

        if ch.isalpha():
            idx = alphabet_index(ch, code, text_context=raw)
            if idx is not None:
                sequence.append(int(idx))
            continue

        # Non-letter, non-digit: leave for uid_sequence_with_code / symbol pass.
        # Do not pretend they are letters.

    return sequence


def uid_sequence_with_code(
    token: str,
    lang: str = "en",
) -> list[int]:
    """
    Main tokenizer path for code-mixed tokens and paths.

    Interleaves:
      - letter/digit identity from uid_sequence on spans
      - code symbol markers as negative registry columns (-(col+1))
    Never drops registered symbols or digit markers.
    """
    raw = str(token or "")
    if not raw:
        return []

    sequence: list[int] = []
    try:
        from code_tokenizer import tokenize_code
        from code_symbol_registry import CODE_SYMBOL_TO_COLUMN
    except Exception:
        try:
            from backend.code_tokenizer import tokenize_code
            from backend.code_symbol_registry import CODE_SYMBOL_TO_COLUMN
        except Exception:
            return uid_sequence(raw, lang)

    for rec in tokenize_code(raw, lang):
        typ = (rec.get("type") or "").lower()
        tok = rec.get("token") or rec.get("source") or ""
        if typ in ("code_symbol", "operator") or rec.get("grid") == "code":
            col = rec.get("col")
            if col is None and tok in CODE_SYMBOL_TO_COLUMN:
                col = CODE_SYMBOL_TO_COLUMN[tok]
            if col is not None:
                sequence.append(-(int(col) + 1))  # marker id; never strip
            continue
        if typ in ("number",) or (tok and tok.isdigit()):
            sequence.extend(uid_sequence(tok, lang))
            continue
        if typ in ("ident", "keyword", "builtin", "string") or tok:
            # letters + digits inside the span
            sequence.extend(uid_sequence(tok, lang))
            continue
    return sequence



def identity_stream(token: str, lang: str = "en") -> list:
    """
    Main identity stream (train/place). Not the full code highlighter.

    letter  -> 0-based alphabet index
    digit   -> atomic marker "000".."009" (never split to 3 ints)
    symbol  -> code registry uid "-{col}" via match_code_symbol
               (# is a symbol here, NOT a line-comment eater)

    KEYWORDS/BUILTINS statics: applied on letter-runs after scan.
    """
    raw = str(token or "")
    if not raw:
        return []
    code = normalize_lang(lang)
    out = []

    try:
        try:
            from code_symbol_registry import (
                match_code_symbol,
                code_symbol_identity,
            )
        except ImportError:
            from backend.code_symbol_registry import (
                match_code_symbol,
                code_symbol_identity,
            )
    except Exception:
        match_code_symbol = None
        code_symbol_identity = None

    # Optional static role tags for identifier spans
    try:
        try:
            from code_tokenizer import KEYWORDS, BUILTINS, classify_code_token
        except ImportError:
            from backend.code_tokenizer import KEYWORDS, BUILTINS, classify_code_token
    except Exception:
        KEYWORDS, BUILTINS = set(), set()
        def classify_code_token(tok: str) -> str:
            return "IDENT"

    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch.isspace():
            i += 1
            continue

        # 1) Longest registered code symbol (includes # ( ) . / _ etc.)
        if match_code_symbol is not None:
            sym = match_code_symbol(raw, i)
            if sym:
                try:
                    ident = code_symbol_identity(sym)
                except Exception:
                    ident = {"uid": None, "col": None}
                out.append({
                    "kind": "symbol",
                    "token": sym,
                    "uid": ident.get("uid"),
                    "col": ident.get("col"),
                    "grid": "code",
                    "class": "OPERATOR",
                })
                i += len(sym)
                continue

        # 2) Digit -> atomic marker 000..009
        if ch.isdigit() and ch in DIGIT_MARKERS:
            out.append({
                "kind": "digit",
                "token": ch,
                "marker": DIGIT_MARKERS[ch],
                "grid": "digit",
            })
            i += 1
            continue

        # 3) Identifier / keyword / builtin letter-run
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (raw[j].isalnum() or raw[j] == "_"):
                j += 1
            span = raw[i:j]
            low = span.lower()
            if low in KEYWORDS:
                role, cls = "keyword", "KEYWORD"
            elif span in BUILTINS or low in {b.lower() for b in BUILTINS}:
                role, cls = "builtin", "BUILTIN"
            else:
                role, cls = "identifier", classify_code_token(span)
            for c in span:
                if c == "_":
                    # underscore often in registry; if not matched above, keep visible
                    if match_code_symbol is not None and match_code_symbol("_", 0) == "_":
                        try:
                            ident = code_symbol_identity("_")
                        except Exception:
                            ident = {"uid": None, "col": None}
                        out.append({
                            "kind": "symbol",
                            "token": "_",
                            "uid": ident.get("uid"),
                            "col": ident.get("col"),
                            "grid": "code",
                            "class": "OPERATOR",
                        })
                    else:
                        out.append({"kind": "unregistered", "token": "_", "uid": None})
                elif c.isdigit() and c in DIGIT_MARKERS:
                    out.append({
                        "kind": "digit",
                        "token": c,
                        "marker": DIGIT_MARKERS[c],
                        "grid": "digit",
                        "role": role,
                    })
                elif c.isalpha():
                    idx = alphabet_index(c, code, text_context=span)
                    if idx is not None:
                        out.append({
                            "kind": "letter",
                            "token": c,
                            "index": int(idx),
                            "role": role,
                            "class": cls,
                        })
            i = j
            continue

        # 4) Unknown punct
        out.append({"kind": "unregistered", "token": ch, "uid": None})
        i += 1

    return out




def uid_chain(token: str, lang: str = "en") -> list:
    """Full place/train chain. Whitespace skipped. Letters + digit markers + symbol uids + unregistered as uORD."""
    """
    Full identity chain for serialize + S + start_row.

    Units (in order, nothing omitted for calculation):
      letter  -> int index (0-based alphabet)
      digit   -> str marker "000".."009"
      symbol  -> str registry uid "-{col}"
      unregistered kept as ("unreg", token) only if needed for audit —
                 M5.4: unregistered -> u{ord} on chain; S includes unit_S_value

    Code symbols and digit markers identify on the same chain as letters.
    """
    stream = identity_stream(token, lang)
    out: list = []
    for x in stream:
        k = x.get("kind")
        if k == "letter" and x.get("index") is not None:
            out.append(int(x["index"]))
        elif k == "digit" and x.get("marker"):
            out.append(str(x["marker"]))
        elif k == "symbol" and x.get("uid") is not None:
            out.append(str(x["uid"]))  # "-147"
        elif k == "unregistered":
            ch = str(x.get("token") or "")
            if not ch or ch.isspace():
                continue
            # M5.4: stable unit, never drop from chain/S
            out.append("u" + str(ord(ch[0])))
    return out


def unit_S_value(unit) -> int:
    """Numeric contribution of one chain unit to S."""
    if isinstance(unit, int):
        return int(unit)
    if not isinstance(unit, str):
        return 0
    s = unit.strip()
    if not s:
        return 0
    # digit marker "001" -> 1
    if s in DIGIT_MARKERS.values() or (len(s) == 3 and s.isdigit()):
        return int(s)  # 001 -> 1, 000 -> 0
    # code symbol uid "-147" -> 147 (column id magnitude)
    if s.startswith("-") and s[1:].isdigit():
        return int(s[1:])
    if s.lstrip("-").isdigit():
        return abs(int(s))
    # M5.4 unregistered: "u64" -> 64
    if s.startswith("u") and s[1:].isdigit():
        return int(s[1:])
    return 0


def chain_S(chain) -> int:
    """
    S = sum of every unit on the full chain (letters + markers + symbol ids).
    Always non-negative: abs before return so start_row never sees S < 0.
    """
    total = int(sum(unit_S_value(x) for x in (chain or [])))
    return abs(total)


def serialize_uid_chain(chain) -> str:
    """Underscore-separated full chain: 9_0_12_-147_001_002"""
    return "_".join(str(x) for x in (chain or []))


def deserialize_uid_chain(uid: str) -> list:
    """Inverse: markers stay str, symbol uids stay '-N', letter indexes -> int."""
    s = str(uid or "").strip()
    if not s:
        return []
    markers = set(DIGIT_MARKERS.values())
    out: list = []
    for part in s.split("_"):
        part = part.strip()
        if not part:
            continue
        if part in markers or (len(part) == 3 and part.isdigit() and part.startswith("00")):
            out.append(part)
        elif part.startswith("-") and part[1:].isdigit():
            out.append(part)
        elif part.lstrip("-").isdigit() and not part.startswith("-"):
            if part.startswith("u") and part[1:].isdigit():
            out.append(part)
        else:
            out.append(int(part))
        else:
            out.append(part)
    return out


def letter_indexes_from_stream(stream) -> list:
    return [int(x["index"]) for x in stream if x.get("kind") == "letter" and x.get("index") is not None]


def digit_markers_from_stream(stream) -> list:
    return [str(x["marker"]) for x in stream if x.get("kind") == "digit" and x.get("marker")]


def symbol_uids_from_stream(stream) -> list:
    return [str(x["uid"]) for x in stream if x.get("kind") == "symbol" and x.get("uid")]



def serialize_uid(
    sequence: Iterable[int],
) -> str:
    """
    Serialize the ordered UID sequence.

    Underscore separates each index so multi-digit indexes stay distinct:
      [0, 2, 2, 14, 3, 8, 19, 4] -> "0_2_2_14_3_8_19_4"
    Leading 0 (A/a) is kept as the token "0".

    IMPORTANT:
    S is NOT calculated by digit-summing this string — use sum(sequence).
    """
    return "_".join(str(int(value)) for value in sequence)


def deserialize_uid(uid: str) -> list:
    """Inverse of serialize_uid: split on '_' → list[int]."""
    s = str(uid or "").strip()
    if not s:
        return []
    parts = s.split("_")
    out = []
    for p in parts:
        p = p.strip()
        if p == "" or not p.lstrip("-").isdigit():
            continue
        out.append(int(p))
    return out


def uid_for_token(
    token: str,
    lang: str = "en",
) -> str:
    return serialize_uid(uid_sequence(token, lang))


def uid_digit_sum(
    uid: str | Iterable[int],
) -> int:
    """
    Compatibility helper.

    Historically this represented digit summation.

    It is deliberately NOT used for lexical S.

    Use lexical_S() for the authoritative UID-sequence sum.
    """

    if isinstance(uid, str):
        return sum(
            int(ch)
            for ch in uid
            if ch.isdigit()
        )

    return sum(int(value) for value in uid)


def lexical_L(
    token: str,
    lang: str = "en",
) -> int:
    """
    L = normalized lexical token length.
    """

    normalized = normalize_lexical_token(token, lang)

    return len(normalized)


def lexical_S(
    token: str,
    lang: str = "en",
) -> int:
    """
    Authoritative lexical S.

    S = sum(ordered UID sequence)

    NOT:
        digit sum of serialized UID.
    """

    return sum(uid_sequence(token, lang))


# =====================================================================
# LEXICAL IDENTITY
# =====================================================================

def lexical_identity(
    token: str,
    lang: str = "en",
) -> dict[str, Any]:
    """
    Principal tokenizer identity for train / place / retrieval.

    Letters  -> uid_sequence (0-based indexes); S = sum(sequence)
    Digits   -> atomic markers 000..009 on identity_stream
    Symbols  -> code registry -{col} on identity_stream
    """

    code = normalize_lang(lang)
    raw = str(token or "")

    normalized = normalize_lexical_token(raw, code)

    stream = identity_stream(raw, code)
    letter_seq = letter_indexes_from_stream(stream)
    # Prefer stream letters when present; else normalized letter path
    sequence = letter_seq if letter_seq else uid_sequence(normalized, code)
    uid = serialize_uid(sequence)

    digit_markers = digit_markers_from_stream(stream)
    symbol_uids = symbol_uids_from_stream(stream)

    L = len(normalized) if normalized else max(len(letter_seq), 0)
    S = sum(sequence)
    SC = sequence[0] if sequence else 0

    row = (
        ((L + S - 1) % WORD_GRID_ROWS) + 1
        if (normalized or letter_seq)
        else 1
    )

    return {
        "text": token,
        "normalized": normalized,
        "lang": code,
        "L": L,
        "uid_sequence": sequence,
        "uID_sequence": sequence,
        "uid": uid,
        "uID": uid,
        "S": S,
        "SC": SC,
        "identity_stream": stream,
        "digit_markers": digit_markers,
        "symbol_uids": symbol_uids,
        "word_grid": {
            "columns": WORD_GRID_COLUMNS,
            "rows": WORD_GRID_ROWS,
            "col": SC,
            "row": row,
            "L": L,
            "S": S,
            "formula": f"((L+S-1)%{WORD_GRID_ROWS})+1",
        },
    }


# =====================================================================
# WORD GRID
# =====================================================================

def word_index(
    token: str,
    lang: str = "en",
) -> int:
    """
    Compatibility helper.

    Returns the one-based word-grid row.

    Authoritative formula:

        ((L + S - 1) % 26) + 1
    """

    identity = lexical_identity(token, lang)

    return int(identity["word_grid"]["row"])


def word_cell(
    token: str,
    lang: str = "en",
) -> dict[str, Any]:
    """
    Return deterministic 46 × 26 word-grid placement metadata.

    IMPORTANT:

        L = lexical token length
        uID = ordered UID sequence
        S = sum(uID sequence)
        c/SC = first-letter alphabet index

    Row:

        ((L + S - 1) % 26) + 1

    The UID sequence remains intact.
    """

    identity = lexical_identity(token, lang)

    return {
        "L": identity["L"],

        "uID": identity["uid"],
        "uid": identity["uid"],

        "uid_sequence": list(identity["uid_sequence"]),
        "uID_sequence": list(identity["uID_sequence"]),

        "S": identity["S"],
        "word_S": identity["S"],

        "SC": identity["SC"],
        "c": identity["SC"],
        "col": identity["SC"],

        "row": identity["word_grid"]["row"],

        "columns": WORD_GRID_COLUMNS,
        "rows": WORD_GRID_ROWS,

        "R": WORD_GRID_ROWS,
        "lang": identity["lang"],

        "grid": f"{WORD_GRID_COLUMNS}x{WORD_GRID_ROWS}",

        "row_rule": f"((L+S-1)%{WORD_GRID_ROWS})+1",
    }


# =====================================================================
# CHARACTER RECORDS
# =====================================================================

def character_records(
    token: str,
    lang: str = "en",
) -> list[dict[str, Any]]:
    """
    Decompose a lexical token into deterministic character records.

    The character sequence is retained in order.
    """

    normalized = normalize_lexical_token(token, lang)

    records: list[dict[str, Any]] = []

    for position, ch in enumerate(normalized):
        index = alphabet_index(
            ch,
            lang,
            text_context=normalized,
        )

        records.append(
            {
                "char": ch,
                "position": position,
                "alphabet_index": index,
                "uid_component": index,
                "lang": normalize_lang(lang),
            }
        )

    return records


# =====================================================================
# TOKENIZATION
# =====================================================================

_TOKEN_PATTERN = re.compile(
    r"\S+",
    flags=re.UNICODE,
)


def tokenize(
    text: str,
    lang: str = "en",
) -> list[dict[str, Any]]:
    """
    Tokenize text into deterministic lexical records.

    Every occurrence is preserved.

    This means:

        "hello hello"

    produces two token records, not one.

    The occurrence index is supplied by the token list position.
    """

    raw_text = normalize_text(text)

    if not raw_text:
        return []

    code = normalize_lang(lang)

    # Specialist scanner identifies code-path tokens and registered symbols.
    # The main tokenizer remains authoritative for identity and grid placement.
    try:
        try:
            from code_tokenizer import tokenize_code
        except ImportError:
            from backend.code_tokenizer import tokenize_code
        code_records = tokenize_code(raw_text, code)
    except ImportError:
        code_records = []

    out: list[dict[str, Any]] = []

    for token_index, match in enumerate(
        _TOKEN_PATTERN.finditer(raw_text)
    ):
        original = match.group(0)
        source_start, source_end = match.span()

        # Attach every specialist token found inside this main-token span.
        helper_records = [
            dict(item)
            for item in code_records
            if item.get("start", -1) >= source_start
            and item.get("end", 0) <= source_end
        ]

        normalized = normalize_lexical_token(
            original,
            code,
        )

        # Symbol-only tokens are preserved as token records too.
        if not normalized:
            out.append(
                {
                    "token_index": token_index,
                    "start": source_start,
                    "end": source_end,
                    "source": original,
                    "type": "symbol",
                    "identity_type": "symbol",
                    "code_tokens": helper_records,
                    "code_symbols": [
                        item for item in helper_records
                        if item.get("type") in ("code_symbol", "unregistered_symbol")
                    ],
                    "original": original,
                    "normalized": "",
                    "stem": "",
                    "lang": code,
                    "letter": [],
                    "uid_sequence": [],
                    "uID_sequence": [],
                    "uid": "",
                    "uID": "",
                    "L": 0,
                    "S": 0,
                    "SC": 0,
                    "word": {
                        "columns": WORD_GRID_COLUMNS,
                        "rows": WORD_GRID_ROWS,
                        "col": 0,
                        "row": 1,
                        "L": 0,
                        "S": 0,
                        "uid_sequence": [],
                    },
                    "symbols": recognize_global_symbols(original),
                }
            )
            continue

        identity = lexical_identity(
            normalized,
            code,
        )

        digit_records = [
            {
                "digit": ch,
                "uid": DIGIT_MARKERS[ch],
                "position": match.start() + offset,
            }
            for offset, ch in enumerate(original)
            if ch.isdigit() and ch in DIGIT_MARKERS
        ]

        out.append(
            {
                "token_index": token_index,
                "start": source_start,
                "end": source_end,
                "source": original,
                "type": "word",
                "identity_type": "letter",
                "code_tokens": helper_records,
                "code_symbols": [
                    item for item in helper_records
                    if item.get("type") in ("code_symbol", "unregistered_symbol")
                ],
                "original": original,
                "normalized": normalized,
                "stem": stem_token(normalized, code),
                "lang": code,

                "letter": letter_cells(
                    normalized,
                    code,
                ),

                "characters": character_records(
                    normalized,
                    code,
                ),

                "uid_sequence": list(
                    identity["uid_sequence"]
                ),

                "uID_sequence": list(
                    identity["uID_sequence"]
                ),

                "uid": identity["uid"],
                "uID": identity["uID"],

                "L": identity["L"],
                "S": identity["S"],
                "SC": identity["SC"],

                "word": word_cell(
                    normalized,
                    code,
                ),

                "symbols": recognize_global_symbols(
                    original
                ),

                "digits": digit_records,
                "digit_uid_sequence": [
                    item["uid"] for item in digit_records
                ],
            }
        )

    return out


def tokenize_words(
    text: str,
    lang: str = "en",
) -> list[dict[str, Any]]:
    """
    Alias for word-level deterministic tokenization.
    """

    return tokenize(text, lang)


def unique_lexical_tokens(
    text: str,
    lang: str = "en",
) -> list[str]:
    """
    Return unique normalized lexical tokens while preserving order.
    """

    seen: set[str] = set()
    result: list[str] = []

    for record in tokenize(text, lang):
        token = record.get("normalized", "")

        if not token:
            continue

        if token not in seen:
            seen.add(token)
            result.append(token)

    return result


# =====================================================================
# FULL-TEXT UID SUPPORT
# =====================================================================

def text_uid_sequences(
    text: str,
    lang: str = "en",
) -> list[list[int]]:
    """
    Return the ordered UID sequence for every lexical word occurrence.

    Full-text placement uses these sequences downstream.

    This function does NOT perform full-text placement.
    """

    return [
        list(record["uid_sequence"])
        for record in tokenize(text, lang)
        if record.get("uid_sequence")
    ]


def text_uid_sequence(
    text: str,
    lang: str = "en",
) -> list[int]:
    """
    Flatten word UID sequences while preserving word and character order.

    This is the sequence handed to the full-text placement layer for
    column-index UID chaining.
    """

    sequence: list[int] = []

    for word_sequence in text_uid_sequences(text, lang):
        sequence.extend(word_sequence)

    return sequence


def text_uid(
    text: str,
    lang: str = "en",
) -> str:
    """
    Serialize the flattened full-text UID sequence.

    The full-text placement layer decides how this is used for
    full-text S/placement.
    """

    return serialize_uid(
        text_uid_sequence(text, lang)
    )


def text_S(
    text: str,
    lang: str = "en",
) -> int:
    """
    Total UID S for full-text placement.

    S is calculated from UID components, not decimal digits.
    """

    return sum(
        text_uid_sequence(text, lang)
    )


def full_text_uid_data(
    text: str,
    lang: str = "en",
) -> dict[str, Any]:
    """
    Return the tokenizer-side full-text identity.

    The actual full-text grid placement remains outside tokenizer.py.
    """

    sequences = text_uid_sequences(text, lang)
    flattened = text_uid_sequence(text, lang)

    return {
        "lang": normalize_lang(lang),
        "uid_sequences": sequences,
        "uid_sequence": flattened,
        "uid": serialize_uid(flattened),
        "S": sum(flattened),
        "token_count": len(sequences),
    }


# =====================================================================
# GSP INPUTS
# =====================================================================

def _local_lsum(stem: str) -> int:
    return max(len(stem), 1)


def _local_ssum(stem: str) -> int:
    """
    Compatibility fallback only.

    The authoritative lexical S is lexical_S(), which is based on
    UID sequence.

    This fallback exists for older GSP callers that expect keyboard.py
    Lsum/Ssum behavior.
    """

    total = 0

    for ch in stem:
        if ch.isdigit():
            total += int(ch)
        else:
            total += ord(ch) % 10

    return total or 1


def gsp_inputs(
    token: str,
    lang: str = "en",
) -> dict[str, int]:
    """
    GSP-facing lexical inputs.

    The lexical UID values are exposed explicitly.

    If keyboard.py provides its established GSP calculations,
    those calculations remain authoritative for GSP compatibility.

    Tokenizer does not perform GSP traversal.
    """

    code = normalize_lang(lang)
    normalized = normalize_lexical_token(token, code)

    identity = lexical_identity(
        normalized,
        code,
    )

    result: dict[str, int] = {
        "L": int(identity["L"]),
        "S": int(identity["S"]),
        "SC": int(identity["SC"]),
    }

    # Preserve the established keyboard/GSP API when available.
    if keyboard is not None:
        if hasattr(keyboard, "calculate_lsum"):
            try:
                result["Lsum"] = int(
                    keyboard.calculate_lsum(
                        normalized,
                        code,
                    )
                )
            except Exception:
                result["Lsum"] = _local_lsum(normalized)
        else:
            result["Lsum"] = _local_lsum(normalized)

        if hasattr(keyboard, "calculate_ssum"):
            try:
                result["Ssum"] = int(
                    keyboard.calculate_ssum(
                        normalized,
                        code,
                    )
                )
            except Exception:
                result["Ssum"] = _local_ssum(normalized)
        else:
            result["Ssum"] = _local_ssum(normalized)
    else:
        result["Lsum"] = _local_lsum(normalized)
        result["Ssum"] = _local_ssum(normalized)

    # Compatibility c.
    result["c"] = int(identity["SC"])

    return result


def gsp_start_row(
    token: str,
    lang: str = "en",
    R: int = 64,
) -> int:
    """
    Return the canonical GSP start row.

    This remains a GSP-facing helper.

    Preferred authority is keyboard.py.

    Fallback:

        ((Lsum + Ssum - 1) % R) + 1
    """

    values = gsp_inputs(token, lang)

    if keyboard is not None:
        if hasattr(keyboard, "start_row"):
            try:
                return int(
                    keyboard.start_row(
                        values["Lsum"],
                        values["Ssum"],
                        R,
                    )
                )
            except Exception:
                pass

        if hasattr(keyboard, "gsp_start_row"):
            try:
                return int(
                    keyboard.gsp_start_row(
                        values["Lsum"],
                        values["Ssum"],
                        R,
                    )
                )
            except Exception:
                pass

    return (
        (values["Lsum"] + values["Ssum"] - 1) % R
    ) + 1


def full_text_placement_config() -> dict[str, Any]:
    """
    Configuration metadata only.

    GSP/MemoryGrid owns actual traversal and placement.
    """

    return {
        "forward_d": FORWARD_D,
        "backward_d": BACKWARD_D,
        "owner": "gsp_memory_grid",
        "tokenizer_applies": False,
        "word_grid_columns": WORD_GRID_COLUMNS,
        "word_grid_rows": WORD_GRID_ROWS,
        "full_text_uid_chaining": True,
        "full_text_uid_source": "ordered_word_uid_sequences",
        "full_text_S_source": "sum(total_uid_sequence)",
    }


# =====================================================================
# LEXICAL SCORING
# =====================================================================

def letter_score(
    query_tokens: list[dict],
    doc_text: str,
    lang: str = "en",
) -> float:
    """
    Lightweight lexical letter-path similarity.

    This is a signal only.

    Ranking policy remains in ranking.py.
    """

    doc_tokens = tokenize(doc_text, lang)

    if not query_tokens or not doc_tokens:
        return 0.0

    score = 0.0

    for query in query_tokens:
        q_letters = query.get("letter") or []

        if not q_letters:
            continue

        for document in doc_tokens:
            d_letters = document.get("letter") or []

            i = 0
            j = 0
            matches = 0

            while (
                i < len(q_letters)
                and j < len(d_letters)
            ):
                if q_letters[i] == d_letters[j]:
                    matches += 1
                    i += 1

                j += 1

            score += (
                matches
                / max(len(q_letters), 1)
            ) * 10

    return score


def word_score(
    query_tokens: list[dict],
    doc_text: str,
    lang: str = "en",
) -> float:
    """
    Lightweight word-grid similarity.

    This is not ranking policy.
    """

    doc_tokens = tokenize(doc_text, lang)

    if not query_tokens or not doc_tokens:
        return 0.0

    score = 0.0

    doc_cells = {
        (
            token["word"]["col"],
            token["word"]["row"],
            token["normalized"],
        )
        for token in doc_tokens
        if token.get("normalized")
    }

    for query in query_tokens:
        normalized = query.get(
            "normalized",
            query.get("stem", ""),
        )

        word = query.get("word") or {}

        for col, row, doc_word in doc_cells:

            if normalized == doc_word:
                score += 25

            elif (
                word.get("col") == col
                and word.get("row") == row
            ):
                score += 15

            elif (
                word.get("col") == col
                or word.get("row") == row
            ):
                score += 5

    return score


# =====================================================================
# LANGUAGE REGISTRY
# =====================================================================

def supported_languages() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for code, alphabet in ALPHABETS.items():

        if code == "default":
            continue

        result.append(
            {
                "code": code,
                "A": len(alphabet),
                "letter_grid": f"{len(alphabet)}x1",
                "word_grid": (
                    f"{WORD_GRID_COLUMNS}x{WORD_GRID_ROWS}"
                ),
                "word_R": WORD_GRID_R,
                "word_columns": WORD_GRID_COLUMNS,
                "word_rows": WORD_GRID_ROWS,
                "key_line": KEY_LINES.get(
                    code,
                    KEY_LINES["default"],
                ),
            }
        )

    return result


def language_key_mapping(
    lang: str | None,
) -> dict[str, Any]:
    code = normalize_lang(lang)

    alphabet = alphabet_for(code)
    key_line = key_line_for(code)

    return {
        "code": code,
        "alphabet": alphabet,
        "key_line": key_line,
        "A": len(alphabet),

        "letter_grid": f"{len(alphabet)}x1",

        "word_grid": (
            f"{WORD_GRID_COLUMNS}x{WORD_GRID_ROWS}"
        ),

        "letter_R": LETTER_GRID_R,
        "word_R": WORD_GRID_R,

        "word_columns": WORD_GRID_COLUMNS,
        "word_rows": WORD_GRID_ROWS,
    }


# =====================================================================
# VALIDATION
# =====================================================================

def _validate_identity_examples() -> None:
    """
    Locked identity checks.

    These are development assertions and do not run on import.
    """

    zed = lexical_identity("ZED", "en")
    zee = lexical_identity("ZEE", "en")

    assert zed["uid_sequence"] == [25, 4, 3]
    assert zee["uid_sequence"] == [25, 4, 4]

    assert zed["uid"] == "2543"
    assert zee["uid"] == "2544"

    # S is the sum of UID COMPONENTS.
    assert zed["S"] == 32
    assert zee["S"] == 33

    assert zed["L"] == 3
    assert zee["L"] == 3

    assert zed["SC"] == 25
    assert zee["SC"] == 25

    # Word grid:
    #
    # ZED:
    # ((3 + 32 - 1) % 26) + 1 = 10
    #
    # ZEE:
    # ((3 + 33 - 1) % 26) + 1 = 11

    assert zed["word_grid"]["row"] == 10
    assert zee["word_grid"]["row"] == 11


# =====================================================================
# DEVELOPMENT ENTRY POINT
# =====================================================================

if __name__ == "__main__":

    _validate_identity_examples()

    print("CoMpaNeoN tokenizer validation passed.")
    print()

    print("ZED:")
    print(lexical_identity("ZED", "en"))
    print()

    print("ZEE:")
    print(lexical_identity("ZEE", "en"))
    print()

    print("Arabic:")
    print(
        tokenize(
            "مرحبا بالعالم",
            "ar",
        )
    )
    print()

    print("Yoruba:")
    print(
        tokenize(
            "Ẹ káàrọ̀",
            "yo",
        )
    )
    print()

    print("Japanese:")
    print(
        tokenize(
            "こんにちは 世界",
            "ja",
        )
    )
    print()

    print("Chinese:")
    print(
        tokenize(
            "你好世界",
            "zh",
        )
    )
    print()

    print("Full text UID:")
    print(
        full_text_uid_data(
            "ZEE ZED",
            "en",
        )
    )
    print()

    print("Symbols:")
    print(
        recognize_global_symbols(
            "Can GSP calculate x >= 10%?"
        )
    )