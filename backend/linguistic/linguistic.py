"""
CoMpaNeoN Linguistic Layer
==========================

Multilingual linguistic analysis and enrichment layer.

ARCHITECTURE
------------

                    User / AI / External Text
                                │
                                ▼
                            langdetect
                                │
                                ▼
                           tokenizer.py
                                │
                ┌───────────────┴────────────────┐
                │                                │
                ▼                                ▼
relation_and_alphabet_matrix.py              Token data
                │                                │
                ▼                                │
                         matrix_maths.py          │
                                │                │
                                └────────┬───────┘
                                         ▼
                                   linguistic.py
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         │                               │                               │
         ▼                               ▼                               ▼
    Structural Analysis              Grammar                         Lexical
         │                               │                               │
         ├── vowels                     ├── parts of speech             ├── synonyms
         ├── consonants                 ├── conjunctions                ├── antonyms
         ├── syllables                  └── interjections               ├── semantic relationships
         ├── phonetic patterns                                              ├── hierarchical relationships
         ├── assonance                                                       └── close-proxy relationships
         └── resonance
                                         │
                                         ▼
                              Expression / Meaning
                                         │
                              ├── idioms
                              ├── figures of speech
                              ├── linguistic patterns
                              └── semantic analysis
                                         │
                                         ▼
                                  external.py
                                         │
                                         ▼
                               Dictionary enrichment
                                         │
                               definitions / meanings
                               synonyms / antonyms
                               examples / word forms
                               phonetics / etymology
                                         │
                                         ▼
                               Linguistic enrichment
                                         │
                                         ▼
                           Question Type Interpretation
                                         │
                                         ▼
                                WordUnderstanding
                                         │
                                         ▼
                                   WordChain


AUTHORITIES
-----------

tokenizer.py
    Owns canonical tokenization, language normalization,
    language alphabets and token coordinates.

relation_and_alphabet_matrix.py
    Owns alphabet/relationship substrate.

matrix_maths.py
    Owns mathematical signal construction.

external.py
    Owns communication with external dictionary providers.

question_type_detector.py
    Owns deterministic question-type interpretation.

word_understanding.py
    Owns structured understanding.

word_chain.py
    Owns word relationship, continuation and construction.

THIS MODULE
-----------

linguistic.py owns:

    - orchestration of linguistic members
    - structural linguistic analysis
    - internal lexical heuristics
    - grammar-oriented signal assembly
    - semantic relationship assembly
    - phonetic/orthographic signal analysis
    - external dictionary enrichment orchestration
    - unified linguistic output

IMPORTANT
---------

External dictionaries enrich CoMpaNeoN.

They do NOT replace CoMpaNeoN's internal linguistic intelligence.

This module does NOT:

    - place MemoryGrid documents
    - calculate GSP traversal
    - perform crawler traversal
    - rank candidates
    - generate prompts
    - generate AI responses
"""

from __future__ import annotations

import asyncio
import inspect
import re

from collections import Counter

from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================

try:

    from langdetect import (
        detect,
        LangDetectException,
    )

except ImportError:

    detect = None
    LangDetectException = Exception


# ============================================================================
# TOKENIZER AUTHORITY
# ============================================================================

from tokenizer import (
    tokenize,
    normalize_lang,
    alphabet_for,
)


# ============================================================================
# RELATION / ALPHABET MATRIX
# ============================================================================

try:

    from relation_and_alphabet_matrix import (
        analyze_relation_and_alphabet,
    )

except ImportError:

    analyze_relation_and_alphabet = None


# ============================================================================
# MATRIX MATHS
# ============================================================================

try:

    from matrix_maths import (
        intent_domain_signal,
        directive_signal,
        symbol_signal,
        code_language_signal,
        data_mixer_signal,
    )

except Exception:

    intent_domain_signal = None
    directive_signal = None
    symbol_signal = None
    code_language_signal = None
    data_mixer_signal = None


# ============================================================================
# QUESTION TYPE DETECTOR
# ============================================================================

try:

    from question_type_detector import (
        detect_question_type,
    )

except Exception:

    detect_question_type = None


# ============================================================================
# EXTERNAL DICTIONARY
# ============================================================================

try:

    from external import (
        fetch_dictionary,
    )

except Exception:

    fetch_dictionary = None


# ============================================================================
# BASIC LANGUAGE SETS
# ============================================================================

LATIN_VOWELS = set(
    "aeiou"
)

EXTENDED_LATIN_VOWELS = set(
    "aeiou"
    "àáâäãå"
    "æ"
    "èéêë"
    "ìíîï"
    "òóôöõ"
    "œ"
    "ùúûü"
    "ÿ"
    "ẹ"
    "ị"
    "ọ"
    "ụ"
    "ă"
    "ơ"
    "ư"
)

ARABIC_VOWEL_MARKS = set(
    "ًٌٍَُِّْ"
)

HEBREW_VOWEL_MARKS = set(
    "ְֱֲֳִֵֶַָֹֻּ"
)

DEVANAGARI_VOWELS = set(
    "अआइईउऊऋएऐओऔ"
)

BENGALI_VOWELS = set(
    "অআইঈউঊঋএঐওঔ"
)

JAPANESE_VOWELS = set(
    "あいうえお"
)

KOREAN_VOWEL_SIGNS = set(
    "ㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ"
    "ㅐㅔㅚㅟㅢㅘㅙㅝㅞ"
)

THAI_VOWELS = set(
    "ะาิีึืุูเแโใไ"
)


# ============================================================================
# ENGLISH GRAMMAR HEURISTICS
# ============================================================================

ENGLISH_CONJUNCTIONS = {
    "and",
    "but",
    "or",
    "nor",
    "for",
    "yet",
    "so",
    "although",
    "because",
    "since",
    "unless",
    "while",
    "whereas",
    "if",
    "though",
    "when",
    "before",
    "after",
}

ENGLISH_INTERJECTIONS = {
    "ah",
    "aha",
    "alas",
    "amen",
    "aw",
    "bravo",
    "eh",
    "hey",
    "hmm",
    "oh",
    "oops",
    "ouch",
    "ugh",
    "wow",
    "yay",
    "yes",
    "no",
}

ENGLISH_PRONOUNS = {
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
}

ENGLISH_ARTICLES = {
    "a",
    "an",
    "the",
}

ENGLISH_PREPOSITIONS = {
    "in",
    "on",
    "at",
    "by",
    "with",
    "from",
    "to",
    "for",
    "of",
    "about",
    "under",
    "over",
    "between",
    "through",
    "into",
    "during",
    "before",
    "after",
}

ENGLISH_AUXILIARIES = {
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
}


# ============================================================================
# SEMANTIC RELATION LEXICON
# ============================================================================

RELATION_HINTS = {

    "cause": {
        "because",
        "therefore",
        "thus",
        "hence",
        "causes",
        "cause",
        "result",
        "results",
    },

    "comparison": {
        "than",
        "versus",
        "vs",
        "compare",
        "comparison",
        "difference",
        "similar",
    },

    "definition": {
        "means",
        "meaning",
        "defined",
        "definition",
        "called",
        "refers",
    },

    "hierarchy": {
        "type",
        "kind",
        "category",
        "class",
        "parent",
        "child",
        "subclass",
        "superclass",
    },

    "sequence": {
        "first",
        "then",
        "next",
        "after",
        "before",
        "finally",
        "last",
    },

    "condition": {
        "if",
        "unless",
        "when",
        "provided",
        "assuming",
    },

    "contrast": {
        "but",
        "however",
        "although",
        "whereas",
        "instead",
        "unlike",
    },
}


# ============================================================================
# IDIOM / FIGURATIVE MARKERS
# ============================================================================

COMMON_IDIOMS = {

    "break the ice",
    "piece of cake",
    "once in a blue moon",
    "under the weather",
    "spill the beans",
    "hit the nail on the head",
    "cost an arm and a leg",
    "beat around the bush",
    "burn the midnight oil",
    "the ball is in your court",
}

FIGURATIVE_MARKERS = {
    "like",
    "as",
    "as if",
    "as though",
    "literally",
    "metaphor",
    "symbolizes",
    "represents",
}


# ============================================================================
# TEXT HELPERS
# ============================================================================

WORD_RE = re.compile(
    r"[^\W\d_]+(?:[-'][^\W\d_]+)*",
    re.UNICODE,
)

SENTENCE_RE = re.compile(
    r"(?<=[.!?])\s+"
)


def _clean_text(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def _words(
    text: str,
) -> List[str]:

    return [
        word
        for word in WORD_RE.findall(
            str(text or "").lower()
        )
        if word
    ]


def _safe_dict(
    value: Any,
) -> Dict[str, Any]:

    return (
        value
        if isinstance(value, dict)
        else {}
    )


# ============================================================================
# LANGUAGE RESOLUTION
# ============================================================================

def detect_language(
    text: str,
    fallback: str = "en",
) -> str:
    """
    Detect language, then pass the result through tokenizer.py.

    tokenizer.py remains the canonical language normalization authority.
    """

    clean = _clean_text(
        text
    )

    if not clean:
        return normalize_lang(
            fallback
        )

    if detect is None:
        return normalize_lang(
            fallback
        )

    try:

        detected = detect(
            clean
        )

        return normalize_lang(
            detected
        )

    except (
        LangDetectException,
        Exception,
    ):

        return normalize_lang(
            fallback
        )


# ============================================================================
# STRUCTURAL ANALYSIS
# ============================================================================

def structural_analysis(
    text: str,
) -> Dict[str, Any]:

    clean = _clean_text(
        text
    )

    sentences = [
        sentence.strip()
        for sentence in SENTENCE_RE.split(
            clean
        )
        if sentence.strip()
    ]

    words = _words(
        clean
    )

    punctuation = [
        char
        for char in clean
        if not char.isalnum()
        and not char.isspace()
    ]

    return {

        "character_count":
            len(clean),

        "word_count":
            len(words),

        "sentence_count":
            len(sentences),

        "sentences":
            sentences,

        "words":
            words,

        "punctuation":
            punctuation,

        "punctuation_count":
            len(punctuation),

        "has_question":
            "?" in clean,

        "has_exclamation":
            "!" in clean,

        "has_statement":
            bool(clean)
            and not clean.endswith("?"),

        "token_density":
            (
                len(words)
                / max(
                    len(sentences),
                    1,
                )
            ),
    }


# ============================================================================
# VOWELS
# ============================================================================

def vowel_inventory(
    lang: str,
) -> Set[str]:

    language = normalize_lang(
        lang
    )

    if language in {
        "en",
        "fr",
        "de",
        "es",
        "pt",
        "tr",
        "it",
        "nl",
        "pl",
        "cs",
        "sv",
        "no",
        "da",
        "fi",
        "vi",
        "yo",
        "ha",
        "ig",
        "sw",
    }:

        return EXTENDED_LATIN_VOWELS

    if language == "ar":
        return ARABIC_VOWEL_MARKS

    if language == "he":
        return HEBREW_VOWEL_MARKS

    if language == "hi":
        return DEVANAGARI_VOWELS

    if language == "bn":
        return BENGALI_VOWELS

    if language == "ja":
        return JAPANESE_VOWELS

    if language == "ko":
        return KOREAN_VOWEL_SIGNS

    if language == "th":
        return THAI_VOWELS

    return EXTENDED_LATIN_VOWELS


def analyze_vowels(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    clean = _clean_text(
        text
    )

    inventory = vowel_inventory(
        lang
    )

    found = [
        char
        for char in clean.lower()
        if char in inventory
    ]

    counts = Counter(
        found
    )

    return {

        "language":
            normalize_lang(lang),

        "inventory":
            sorted(inventory),

        "count":
            len(found),

        "unique":
            sorted(counts.keys()),

        "frequency":
            dict(counts),

        "positions":
            [
                index
                for index, char
                in enumerate(
                    clean.lower()
                )
                if char in inventory
            ],
    }


# ============================================================================
# CONSONANTS
# ============================================================================

def analyze_consonants(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    clean = _clean_text(
        text
    )

    language = normalize_lang(
        lang
    )

    alphabet = set(
        alphabet_for(
            language
        )
    )

    vowels = vowel_inventory(
        language
    )

    found = [
        char
        for char in clean.lower()
        if char in alphabet
        and char not in vowels
    ]

    counts = Counter(
        found
    )

    return {

        "language":
            language,

        "count":
            len(found),

        "unique":
            sorted(counts.keys()),

        "frequency":
            dict(counts),

        "positions":
            [
                index
                for index, char
                in enumerate(
                    clean.lower()
                )
                if char in alphabet
                and char not in vowels
            ],
    }


# ============================================================================
# SYLLABIC STRUCTURE
# ============================================================================

def _estimate_latin_syllables(
    word: str,
) -> List[str]:

    clean = (
        word
        .lower()
        .strip()
    )

    if not clean:
        return []

    groups = re.findall(
        r"[aeiouy]+",
        clean,
    )

    if not groups:
        return [
            clean
        ]

    return groups


def analyze_syllabic_structure(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    language = normalize_lang(
        lang
    )

    words = _words(
        text
    )

    per_word = []

    for word in words:

        if language in {
            "en",
            "fr",
            "de",
            "es",
            "pt",
            "tr",
            "it",
            "nl",
            "pl",
            "cs",
            "sv",
            "no",
            "da",
            "fi",
            "vi",
            "yo",
            "ha",
            "ig",
            "sw",
        }:

            units = _estimate_latin_syllables(
                word
            )

        else:

            units = [
                char
                for char in word
                if not char.isspace()
            ]

        per_word.append({

            "word":
                word,

            "units":
                units,

            "count":
                len(units),
        })

    return {

        "language":
            language,

        "words":
            per_word,

        "estimated_total":
            sum(
                item["count"]
                for item in per_word
            ),
    }


# ============================================================================
# PHONETIC STRUCTURE
# ============================================================================

def phonetic_structure(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    language = normalize_lang(
        lang
    )

    vowels = vowel_inventory(
        language
    )

    words = _words(
        text
    )

    structures = []

    for word in words:

        pattern = []

        for char in word.lower():

            if char in vowels:
                pattern.append(
                    "V"
                )

            elif char.isalpha():
                pattern.append(
                    "C"
                )

            else:
                pattern.append(
                    "X"
                )

        structures.append({

            "word":
                word,

            "pattern":
                "".join(pattern),
        })

    return {

        "language":
            language,

        "structures":
            structures,
    }


# ============================================================================
# ASSONANCE
# ============================================================================

def analyze_assonance(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    words = _words(
        text
    )

    vowel_data = analyze_vowels(
        text,
        lang,
    )

    vowels = vowel_data[
        "frequency"
    ]

    repeated = {
        vowel: count
        for vowel, count
        in vowels.items()
        if count > 1
    }

    word_patterns = []

    inventory = vowel_inventory(
        lang
    )

    for word in words:

        pattern = "".join(
            char
            for char in word.lower()
            if char in inventory
        )

        if pattern:
            word_patterns.append({

                "word":
                    word,

                "vowel_pattern":
                    pattern,
            })

    return {

        "repeated_vowels":
            repeated,

        "patterns":
            word_patterns,

        "assonance_strength":
            (
                sum(
                    repeated.values()
                )
                / max(
                    len(words),
                    1,
                )
            ),
    }


# ============================================================================
# RESONANCE
# ============================================================================

def analyze_resonance(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    words = _words(
        text
    )

    phonetics = phonetic_structure(
        text,
        lang,
    )

    endings = Counter()

    for word in words:

        if len(word) >= 2:

            endings[
                word[-2:]
            ] += 1

        elif word:

            endings[
                word
            ] += 1

    repeated_endings = {
        ending: count
        for ending, count
        in endings.items()
        if count > 1
    }

    patterns = Counter(
        item["pattern"]
        for item in phonetics[
            "structures"
        ]
        if item.get(
            "pattern"
        )
    )

    repeated_patterns = {
        pattern: count
        for pattern, count
        in patterns.items()
        if count > 1
    }

    return {

        "repeated_endings":
            repeated_endings,

        "repeated_phonetic_patterns":
            repeated_patterns,

        "resonance_strength":
            (
                (
                    sum(
                        repeated_endings.values()
                    )
                    +
                    sum(
                        repeated_patterns.values()
                    )
                )
                /
                max(
                    len(words),
                    1,
                )
            ),
    }


# ============================================================================
# PARTS OF SPEECH
# ============================================================================

def _english_pos(
    word: str,
) -> str:

    lower = (
        word
        .lower()
    )

    if lower in ENGLISH_INTERJECTIONS:
        return "interjection"

    if lower in ENGLISH_CONJUNCTIONS:
        return "conjunction"

    if lower in ENGLISH_PRONOUNS:
        return "pronoun"

    if lower in ENGLISH_ARTICLES:
        return "article"

    if lower in ENGLISH_PREPOSITIONS:
        return "preposition"

    if lower in ENGLISH_AUXILIARIES:
        return "auxiliary"

    if lower.endswith(
        "ly"
    ):
        return "adverb"

    if lower.endswith(
        (
            "ing",
            "ed",
        )
    ):
        return "verb"

    if lower.endswith(
        (
            "ous",
            "ful",
            "ive",
            "able",
            "ible",
            "al",
            "ic",
        )
    ):
        return "adjective"

    if lower.endswith(
        (
            "tion",
            "ment",
            "ness",
            "ity",
            "ship",
            "ism",
        )
    ):
        return "noun"

    return "unknown"


def analyze_parts_of_speech(
    tokens: Sequence[
        Dict[str, Any]
    ],
    lang: str,
) -> Dict[str, Any]:

    language = normalize_lang(
        lang
    )

    entries = []

    counts = Counter()

    for token in tokens:

        word = (
            token.get(
                "stem"
            )
            or token.get(
                "original"
            )
            or ""
        )

        if not word:
            continue

        if language == "en":

            pos = _english_pos(
                word
            )

        else:

            # Multilingual-safe baseline.

            if word in ENGLISH_CONJUNCTIONS:
                pos = "conjunction"

            elif word in ENGLISH_INTERJECTIONS:
                pos = "interjection"

            else:
                pos = "unknown"

        counts[
            pos
        ] += 1

        entries.append({

            "word":
                word,

            "pos":
                pos,
        })

    return {

        "language":
            language,

        "tokens":
            entries,

        "counts":
            dict(counts),
    }


# ============================================================================
# CONJUNCTIONS
# ============================================================================

def analyze_conjunctions(
    words: Iterable[str],
    lang: str,
) -> Dict[str, Any]:

    language = normalize_lang(
        lang
    )

    found = []

    if language == "en":

        for word in words:

            if word.lower() in ENGLISH_CONJUNCTIONS:

                found.append(
                    word
                )

    return {

        "language":
            language,

        "items":
            found,

        "count":
            len(found),
    }


# ============================================================================
# INTERJECTIONS
# ============================================================================

def analyze_interjections(
    words: Iterable[str],
    lang: str,
) -> Dict[str, Any]:

    language = normalize_lang(
        lang
    )

    found = []

    if language == "en":

        for word in words:

            if word.lower() in ENGLISH_INTERJECTIONS:

                found.append(
                    word
                )

    return {

        "language":
            language,

        "items":
            found,

        "count":
            len(found),
    }


# ============================================================================
# INTERNAL SEMANTIC RELATIONSHIPS
# ============================================================================

def semantic_relationships(
    words: Sequence[str],
) -> Dict[str, Any]:

    normalized = {
        word.lower()
        for word in words
    }

    relations: Dict[
        str,
        List[str]
    ] = {}

    for relation, hints in (
        RELATION_HINTS.items()
    ):

        matched = sorted(
            normalized
            & hints
        )

        if matched:

            relations[
                relation
            ] = matched

    return relations


# ============================================================================
# HIERARCHICAL RELATIONSHIPS
# ============================================================================

def hierarchical_relationships(
    words: Sequence[str],
) -> Dict[str, Any]:

    normalized = [
        word.lower()
        for word in words
    ]

    hierarchy_markers = {

        "type",
        "kind",
        "class",
        "category",
        "parent",
        "child",
        "subclass",
        "superclass",
    }

    found = [
        word
        for word in normalized
        if word in hierarchy_markers
    ]

    return {

        "markers":
            found,

        "hierarchy_detected":
            bool(found),
    }


# ============================================================================
# CLOSE-PROXY RELATIONSHIPS
# ============================================================================

def close_proxy_relationships(
    words: Sequence[str],
) -> Dict[str, Any]:

    unique = []

    seen = set()

    for word in words:

        lower = word.lower()

        if lower in seen:
            continue

        seen.add(
            lower
        )

        unique.append(
            lower
        )

    pairs = []

    for index, left in enumerate(
        unique
    ):

        for right in unique[
            index + 1:
        ]:

            if not left or not right:
                continue

            shared = (
                len(
                    set(left)
                    &
                    set(right)
                )
                /
                max(
                    len(
                        set(left)
                        |
                        set(right)
                    ),
                    1,
                )
            )

            prefix = 0

            for a, b in zip(
                left,
                right,
            ):

                if a != b:
                    break

                prefix += 1

            score = (
                shared * 0.6
                +
                (
                    prefix
                    /
                    max(
                        max(
                            len(left),
                            len(right),
                        ),
                        1,
                    )
                )
                * 0.4
            )

            if score >= 0.45:

                pairs.append({

                    "left":
                        left,

                    "right":
                        right,

                    "score":
                        score,
                })

    return {

        "pairs":
            sorted(
                pairs,
                key=lambda item: item[
                    "score"
                ],
                reverse=True,
            ),
    }


# ============================================================================
# IDIOMS
# ============================================================================

def detect_idioms(
    text: str,
) -> Dict[str, Any]:

    clean = (
        _clean_text(
            text
        )
        .lower()
    )

    found = [

        idiom

        for idiom in COMMON_IDIOMS

        if idiom in clean
    ]

    return {

        "items":
            found,

        "count":
            len(found),
    }


# ============================================================================
# FIGURES OF SPEECH
# ============================================================================

def detect_figures_of_speech(
    text: str,
) -> Dict[str, Any]:

    clean = (
        _clean_text(
            text
        )
        .lower()
    )

    detected = []

    if re.search(
        r"\blike\b",
        clean,
    ):

        detected.append(
            "possible_simile"
        )

    if re.search(
        r"\bas\s+\w+\s+as\b",
        clean,
    ):

        detected.append(
            "possible_simile"
        )

    if (
        "represents" in clean
        or "symbolizes" in clean
    ):

        detected.append(
            "possible_symbolism"
        )

    return {

        "items":
            sorted(
                set(detected)
            ),
    }


# ============================================================================
# LINGUISTIC PATTERNS
# ============================================================================

def linguistic_patterns(
    text: str,
) -> Dict[str, Any]:

    words = _words(
        text
    )

    bigrams = Counter(
        " ".join(pair)
        for pair in zip(
            words,
            words[1:],
        )
    )

    repeated_bigrams = {

        pair: count

        for pair, count in (
            bigrams.items()
        )

        if count > 1
    }

    repeated_words = {

        word: count

        for word, count in (
            Counter(words).items()
        )

        if count > 1
    }

    return {

        "repeated_words":
            repeated_words,

        "repeated_bigrams":
            repeated_bigrams,

        "word_sequence":
            words,
    }


# ============================================================================
# SEMANTIC ANALYSIS
# ============================================================================

def semantic_analysis(
    text: str,
    words: Sequence[str],
) -> Dict[str, Any]:

    relations = semantic_relationships(
        words
    )

    hierarchy = hierarchical_relationships(
        words
    )

    idioms = detect_idioms(
        text
    )

    figures = detect_figures_of_speech(
        text
    )

    return {

        "relations":
            relations,

        "hierarchy":
            hierarchy,

        "idioms":
            idioms,

        "figures_of_speech":
            figures,

        "semantic_relation_count":
            len(relations),

        "figurative_language_detected":
            bool(
                idioms["items"]
                or figures["items"]
            ),
    }


# ============================================================================
# DICTIONARY RESULT NORMALIZATION
# ============================================================================

def normalize_dictionary_result(
    result: Any,
) -> Dict[str, Any]:
    """
    Normalize external.py dictionary output without forcing a provider
    shape onto the linguistic layer.
    """

    if not isinstance(
        result,
        dict,
    ):

        return {

            "available":
                False,

            "raw":
                result,
        }

    meanings = (
        result.get(
            "meanings"
        )
        or []
    )

    definitions = []

    synonyms = set()

    antonyms = set()

    examples = []

    phonetics = []

    etymology = (
        result.get(
            "etymology"
        )
        or result.get(
            "origin"
        )
    )

    if result.get(
        "phonetic"
    ):

        phonetics.append(
            result[
                "phonetic"
            ]
        )

    if result.get(
        "phonetics"
    ):

        for item in result[
            "phonetics"
        ]:

            if isinstance(
                item,
                dict,
            ):

                value = (
                    item.get(
                        "text"
                    )
                    or item.get(
                        "phonetic"
                    )
                )

                if value:

                    phonetics.append(
                        value
                    )

    for meaning in meanings:

        if not isinstance(
            meaning,
            dict,
        ):
            continue

        for synonym in (
            meaning.get(
                "synonyms"
            )
            or []
        ):

            synonyms.add(
                str(synonym)
            )

        for antonym in (
            meaning.get(
                "antonyms"
            )
            or []
        ):

            antonyms.add(
                str(antonym)
            )

        for definition in (
            meaning.get(
                "definitions"
            )
            or []
        ):

            if not isinstance(
                definition,
                dict,
            ):
                continue

            value = definition.get(
                "definition"
            )

            if value:

                definitions.append(
                    str(value)
                )

            example = definition.get(
                "example"
            )

            if example:

                examples.append(
                    str(example)
                )

            for synonym in (
                definition.get(
                    "synonyms"
                )
                or []
            ):

                synonyms.add(
                    str(synonym)
                )

            for antonym in (
                definition.get(
                    "antonyms"
                )
                or []
            ):

                antonyms.add(
                    str(antonym)
                )

    return {

        "available":
            True,

        "definitions":
            definitions,

        "meanings":
            meanings,

        "synonyms":
            sorted(synonyms),

        "antonyms":
            sorted(antonyms),

        "examples":
            examples,

        "phonetics":
            phonetics,

        "word_forms":
            result.get(
                "word_forms",
                []
            ),

        "etymology":
            etymology,

        "raw":
            result,
    }


# ============================================================================
# EXTERNAL DICTIONARY ENRICHMENT
# ============================================================================

async def enrich_dictionary(
    word: str,
) -> Dict[str, Any]:
    """
    Ask external.py for dictionary enrichment.

    external.py owns provider communication.

    linguistic.py owns integration of the returned enrichment.
    """

    clean = (
        str(word or "")
        .strip()
    )

    if not clean:

        return {

            "available":
                False,

            "reason":
                "empty_word",
        }

    if not callable(
        fetch_dictionary
    ):

        return {

            "available":
                False,

            "reason":
                "dictionary_adapter_unavailable",
        }

    try:

        result = fetch_dictionary(
            clean
        )

        if inspect.isawaitable(
            result
        ):

            result = await result

        return normalize_dictionary_result(
            result
        )

    except Exception as exc:

        return {

            "available":
                False,

            "error":
                str(exc),
        }


async def enrich_tokens(
    words: Sequence[str],
    limit: int = 8,
) -> Dict[str, Any]:
    """
    Enrich selected lexical units through external.py.

    The limit prevents dictionary acquisition from turning ordinary
    linguistic analysis into uncontrolled external crawling.
    """

    selected = []

    seen = set()

    for word in words:

        clean = (
            str(word or "")
            .strip()
            .lower()
        )

        if not clean:
            continue

        if clean in seen:
            continue

        seen.add(
            clean
        )

        selected.append(
            clean
        )

        if len(selected) >= limit:
            break

    if not selected:

        return {}

    results = await asyncio.gather(
        *[
            enrich_dictionary(
                word
            )
            for word in selected
        ],
        return_exceptions=True,
    )

    output = {}

    for word, result in zip(
        selected,
        results,
    ):

        if isinstance(
            result,
            Exception,
        ):

            output[word] = {

                "available":
                    False,

                "error":
                    str(result),
            }

        else:

            output[word] = result

    return output


# ============================================================================
# INTERNAL + EXTERNAL LEXICAL ENRICHMENT
# ============================================================================

def internal_lexical_enrichment(
    words: Sequence[str],
) -> Dict[str, Any]:
    """
    Internal lexical baseline.

    This deliberately exists independently of external dictionaries.
    """

    normalized = []

    seen = set()

    for word in words:

        lower = word.lower()

        if lower in seen:
            continue

        seen.add(
            lower
        )

        normalized.append(
            lower
        )

    proxies = close_proxy_relationships(
        normalized
    )

    return {

        "words":
            normalized,

        "close_proxy":
            proxies,

        "semantic_relationships":
            semantic_relationships(
                normalized
            ),

        "hierarchical_relationships":
            hierarchical_relationships(
                normalized
            ),
    }


# ============================================================================
# MATRIX SIGNAL CONSUMPTION
# ============================================================================

def consume_matrix_signals(
    text: str,
    lang: str,
) -> Dict[str, Any]:

    output = {}

    if callable(
        intent_domain_signal
    ):

        try:

            output[
                "intent_domain"
            ] = intent_domain_signal(
                text
            )

        except Exception as exc:

            output[
                "intent_domain"
            ] = {

                "error":
                    str(exc),
            }

    if callable(
        directive_signal
    ):

        try:

            output[
                "directive"
            ] = directive_signal(
                text
            )

        except Exception as exc:

            output[
                "directive"
            ] = {

                "error":
                    str(exc),
            }

    if callable(
        symbol_signal
    ):

        try:

            domain = (
                _safe_dict(
                    output.get(
                        "intent_domain"
                    )
                )
                .get(
                    "domain",
                    "general",
                )
            )

            output[
                "symbol"
            ] = symbol_signal(
                text,
                domain=domain,
            )

        except Exception as exc:

            output[
                "symbol"
            ] = {

                "error":
                    str(exc),
            }

    if callable(
        code_language_signal
    ):

        try:

            output[
                "code_language"
            ] = code_language_signal(
                text
            )

        except Exception as exc:

            output[
                "code_language"
            ] = {

                "error":
                    str(exc),
            }

    if callable(
        data_mixer_signal
    ):

        try:

            output[
                "data_mixer"
            ] = data_mixer_signal(
                text,
                lang=lang,
            )

        except Exception as exc:

            output[
                "data_mixer"
            ] = {

                "error":
                    str(exc),
            }

    return output


# ============================================================================
# QUESTION INTERPRETATION BRIDGE
# ============================================================================

def question_interpretation(
    text: str,
) -> Dict[str, Any]:

    if not callable(
        detect_question_type
    ):

        return {

            "available":
                False,
        }

    try:

        result = detect_question_type(
            text
        )

        return {

            "available":
                True,

            "result":
                result,
        }

    except Exception as exc:

        return {

            "available":
                False,

            "error":
                str(exc),
        }


# ============================================================================
# LINGUISTIC ANALYZER
# ============================================================================

class LinguisticAnalyzer:
    """
    Canonical orchestration object for CoMpaNeoN's linguistic phase.

    It consumes existing project authorities and assembles their output.

    It does not replace those authorities.
    """

    def __init__(
        self,
        dictionary_limit: int = 8,
    ) -> None:

        self.dictionary_limit = max(
            int(
                dictionary_limit
            ),
            0,
        )

    # ========================================================================
    # LANGUAGE
    # ========================================================================

    def resolve_language(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> str:

        if lang:

            return normalize_lang(
                lang
            )

        return detect_language(
            text
        )

    # ========================================================================
    # TOKENIZER
    # ========================================================================

    def tokenize(
        self,
        text: str,
        lang: str,
    ) -> List[
        Dict[str, Any]
    ]:

        try:

            return tokenize(
                text,
                lang,
            )

        except Exception:

            return []

    # ========================================================================
    # INTERNAL ANALYSIS
    # ========================================================================

    def analyze_internal(
        self,
        text: str,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:

        clean = _clean_text(
            text
        )

        language = self.resolve_language(
            clean,
            lang,
        )

        tokens = self.tokenize(
            clean,
            language,
        )

        words = [

            token.get(
                "stem"
            )
            or token.get(
                "original"
            )

            for token in tokens

            if (
                token.get(
                    "stem"
                )
                or token.get(
                    "original"
                )
            )
        ]

        structure = structural_analysis(
            clean
        )

        return {

            "text":
                clean,

            "language":
                language,

            "alphabet":
                alphabet_for(
                    language
                ),

            "tokens":
                tokens,

            "words":
                words,

            "structure":
                structure,

            "vowels":
                analyze_vowels(
                    clean,
                    language,
                ),

            "consonants":
                analyze_consonants(
                    clean,
                    language,
                ),

            "syllables":
                analyze_syllabic_structure(
                    clean,
                    language,
                ),

            "phonetic":
                phonetic_structure(
                    clean,
                    language,
                ),

            "assonance":
                analyze_assonance(
                    clean,
                    language,
                ),

            "resonance":
                analyze_resonance(
                    clean,
                    language,
                ),

            "parts_of_speech":
                analyze_parts_of_speech(
                    tokens,
                    language,
                ),

            "conjunctions":
                analyze_conjunctions(
                    words,
                    language,
                ),

            "interjections":
                analyze_interjections(
                    words,
                    language,
                ),

            "lexical":
                internal_lexical_enrichment(
                    words
                ),

            "semantic":
                semantic_analysis(
                    clean,
                    words,
                ),

            "patterns":
                linguistic_patterns(
                    clean
                ),
        }

    # ========================================================================
    # RELATION / ALPHABET MATRIX
    # ========================================================================

    def analyze_matrix(
        self,
        text: str,
        lang: str,
        partition: Optional[Any] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not callable(
            analyze_relation_and_alphabet
        ):

            return {

                "available":
                    False,
            }

        try:

            result = (
                analyze_relation_and_alphabet(
                    text,
                    lang=lang,
                    partition=partition,
                    source=source,
                )
            )

            return {

                "available":
                    True,

                "result":
                    result,
            }

        except Exception as exc:

            return {

                "available":
                    False,

                "error":
                    str(exc),
            }

    # ========================================================================
    # MATRIX MATHS
    # ========================================================================

    def analyze_matrix_maths(
        self,
        text: str,
        lang: str,
    ) -> Dict[str, Any]:

        return consume_matrix_signals(
            text,
            lang,
        )

    # ========================================================================
    # COMPLETE INTERNAL ANALYSIS
    # ========================================================================

    def analyze(
        self,
        text: str,
        lang: Optional[str] = None,
        partition: Optional[Any] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:

        internal = self.analyze_internal(
            text,
            lang,
        )

        language = internal[
            "language"
        ]

        matrix = self.analyze_matrix(
            internal[
                "text"
            ],
            language,
            partition=partition,
            source=source,
        )

        matrix_maths = (
            self.analyze_matrix_maths(
                internal[
                    "text"
                ],
                language,
            )
        )

        question = (
            question_interpretation(
                internal[
                    "text"
                ]
            )
        )

        return {

            "text":
                internal[
                    "text"
                ],

            "language":
                language,

            "internal":
                internal,

            "relation_and_alphabet":
                matrix,

            "matrix_maths":
                matrix_maths,

            "question":
                question,
        }

    # ========================================================================
    # EXTERNAL ENRICHMENT
    # ========================================================================

    async def enrich(
        self,
        analysis: Dict[
            str,
            Any,
        ],
    ) -> Dict[str, Any]:

        words = (
            analysis
            .get(
                "internal",
                {},
            )
            .get(
                "words",
                []
            )
        )

        if (
            self.dictionary_limit
            <= 0
        ):

            return {

                "enabled":
                    False,

                "dictionary":
                    {},
            }

        dictionary = await enrich_tokens(
            words,
            limit=self.dictionary_limit,
        )

        return {

            "enabled":
                True,

            "dictionary":
                dictionary,
        }

    # ========================================================================
    # FULL ANALYSIS
    # ========================================================================

    async def analyze_full(
        self,
        text: str,
        lang: Optional[str] = None,
        partition: Optional[Any] = None,
        source: Optional[str] = None,
        dictionary: bool = True,
    ) -> Dict[str, Any]:
        """
        Full linguistic pipeline.

        Internal intelligence always runs first.

        Dictionary enrichment is optional and additive.
        """

        analysis = self.analyze(
            text,
            lang=lang,
            partition=partition,
            source=source,
        )

        enrichment = {

            "enabled":
                False,

            "dictionary":
                {},
        }

        if dictionary:

            enrichment = await self.enrich(
                analysis
            )

        analysis[
            "enrichment"
        ] = enrichment

        return analysis


# ============================================================================
# FUNCTIONAL API
# ============================================================================

def analyze_linguistics(
    text: str,
    lang: Optional[str] = None,
    partition: Optional[Any] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:

    analyzer = LinguisticAnalyzer()

    return analyzer.analyze(
        text,
        lang=lang,
        partition=partition,
        source=source,
    )


async def analyze_linguistics_full(
    text: str,
    lang: Optional[str] = None,
    partition: Optional[Any] = None,
    source: Optional[str] = None,
    dictionary: bool = True,
    dictionary_limit: int = 8,
) -> Dict[str, Any]:

    analyzer = LinguisticAnalyzer(
        dictionary_limit=dictionary_limit
    )

    return await analyzer.analyze_full(
        text,
        lang=lang,
        partition=partition,
        source=source,
        dictionary=dictionary,
    )


# ============================================================================
# DEVELOPMENT TEST
# ============================================================================

if __name__ == "__main__":

    sample = (
        "Wow, explain why language and relationships "
        "resonate like music, because patterns connect "
        "words and meaning."
    )

    analyzer = LinguisticAnalyzer()

    result = analyzer.analyze(
        sample
    )

    print(
        result
    )
 