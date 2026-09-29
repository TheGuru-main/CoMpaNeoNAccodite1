"""
CoMpaNeoN Fine Tuner and Weight Scalar
=======================================

Domain-aware learning calibration layer for CoMpaNeoN.

ARCHITECTURE
------------

                         Raw Learning Material
                                  │
                                  ▼
                           tokenizer.py
                                  │
                                  ▼
                              langdetect
                                  │
                                  ▼
                         FineTunerAndWeightScalar
                                  │
          ┌───────────────┬───────┼────────┬───────────────┐
          │               │       │        │               │
          ▼               ▼       ▼        ▼               ▼
       GridCV        MatrixMaths Symbols CodeMixer MemoryPartition
          │               │       │        │               │
          └───────────────┴───────┴────────┴───────────────┘
                                  │
                                  ▼
                          Learning Calibration
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
              User Material                  AI Response
                   │                             │
                   ▼                             ▼
            MemoryPartition               AI Response Bank
                   │                             │
                   └──────────────┬──────────────┘
                                  ▼
                              MemoryGrid
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
                  train.py            background_training.py


RESPONSIBILITIES
----------------

FineTunerAndWeightScalar:

    - detect languages
    - preserve mono-language and multi-language structures
    - inspect sentence and paragraph structures
    - classify learning domains
    - call GridCV
    - call MatrixMaths
    - inspect symbol signals
    - call CodeMixer when available
    - preserve coding knowledge as distinct knowledge
    - calculate independent learning weights
    - calculate final learning scalar
    - generate training parameters
    - route user-originated learning separately from AI-originated learning
    - call MemoryPartition for storage routing
    - store AI responses through the existing AI response partition
    - preserve validation and training state
    - support the basic mirror-learning scale of up to 5,000 units

FineTunerAndWeightScalar DOES NOT own:

    - tokenization mathematics
    - MemoryGrid placement mathematics
    - GSP mathematics
    - crawler traversal
    - memory partition implementation
    - WordUnderstanding
    - WordChain
    - final model training
    - AI response generation

AUTHORITIES
-----------

tokenizer.py
    Canonical tokenization and linguistic normalization.

langdetect
    External language detection support.

GridCV
    Grid/context validation signals.

matrix_maths.py
    Mathematical signal construction.

symbols.py
    Symbol analysis.

CodeMixer
    Code-specific analysis when available.

MemoryPartition
    Memory routing and partition authority.

MemoryGrid
    Canonical storage/indexing authority.

"""

from __future__ import annotations

import math
import re

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set


# ============================================================================
# OPTIONAL LANGUAGE DETECTION
# ============================================================================

try:

    from langdetect import detect
    from langdetect import detect_langs

    LANGDETECT_AVAILABLE = True

except ImportError:

    detect = None
    detect_langs = None

    LANGDETECT_AVAILABLE = False


# ============================================================================
# TOKENIZER
# ============================================================================

try:

    from tokenizer import (
        normalize_lang,
        tokenize,
    )

except ImportError:

    def normalize_lang(
        lang: Optional[str],
    ) -> str:

        return (
            str(lang or "en")
            .strip()
            .lower()
        )

    def tokenize(
        text: str,
        lang: str = "en",
    ) -> List[str]:

        return re.findall(
            r"\w+|[^\w\s]",
            str(text),
            flags=re.UNICODE,
        )


# ============================================================================
# OPTIONAL MATRIX MATHS
# ============================================================================

try:

    from matrix_maths import MatrixMaths

except ImportError:

    MatrixMaths = None


# ============================================================================
# OPTIONAL GRID CV
# ============================================================================

try:

    from grid_cv import GridCV

except ImportError:

    GridCV = None


# ============================================================================
# OPTIONAL SYMBOL ANALYSIS
# ============================================================================

try:

    import symbols as symbols_module

except ImportError:

    symbols_module = None


# ============================================================================
# OPTIONAL CODE MIXER
# ============================================================================

try:

    from code_mixer import CodeMixer

except ImportError:

    CodeMixer = None


# ============================================================================
# EXISTING DATA MIXER COMPATIBILITY
# ============================================================================

try:

    from data_mixer import DataMixer

except ImportError:

    DataMixer = None


# ============================================================================
# OPTIONAL MEMORY PARTITION
# ============================================================================

try:

    from memory_partition import MemoryPartition

except ImportError:

    MemoryPartition = None


# ============================================================================
# CONFIGURATION
# ============================================================================

MIRROR_LEARNING_LIMIT = 5000

DEFAULT_LANGUAGE = "en"

DEFAULT_BASE_WEIGHT = 1.0

MIN_WEIGHT = 0.10

MAX_WEIGHT = 10.0

DEFAULT_VALIDATION_SCORE = 0.50

AI_RESPONSE_SOURCE = "ai_response"

USER_INPUT_SOURCE = "user_input"


# ============================================================================
# DOMAIN CONSTANTS
# ============================================================================

DOMAIN_GENERAL_LANGUAGE = "general_language"

DOMAIN_CASUAL_CONVERSATION = (
    "casual_conversation"
)

DOMAIN_LOCAL_LANGUAGE = (
    "local_language"
)

DOMAIN_IDIOMS = "idioms"

DOMAIN_MATHEMATICS = "mathematics"

DOMAIN_PHYSICS = "physics"

DOMAIN_GEOGRAPHY = "geography"

DOMAIN_ENGINEERING = "engineering"

DOMAIN_MEDICINE = "medicine"

DOMAIN_EDUCATION = "education"

DOMAIN_BUSINESS = "business"

DOMAIN_COMMERCE = "commerce"

DOMAIN_TRANSACTION = "transaction"

DOMAIN_SECURITY = "security"

DOMAIN_ISLAMIC_RELIGION = (
    "islamic_religion"
)

DOMAIN_CYBER_ATTACK = "cyber_attack"

DOMAIN_CYBER_SECURITY = "cyber_security"

DOMAIN_CODING = "coding"

DOMAIN_SOFTWARE_ENGINEERING = (
    "software_engineering"
)

DOMAIN_PROGRAMMING_LANGUAGES = (
    "programming_languages"
)


# ============================================================================
# DOMAIN PARENTS
# ============================================================================

DOMAIN_PARENTS: Dict[
    str,
    str,
] = {

    DOMAIN_GENERAL_LANGUAGE:
        "language",

    DOMAIN_CASUAL_CONVERSATION:
        "language",

    DOMAIN_LOCAL_LANGUAGE:
        "language",

    DOMAIN_IDIOMS:
        "language",

    DOMAIN_MATHEMATICS:
        "science",

    DOMAIN_PHYSICS:
        "science",

    DOMAIN_GEOGRAPHY:
        "science",

    DOMAIN_ENGINEERING:
        "engineering",

    DOMAIN_MEDICINE:
        "science",

    DOMAIN_EDUCATION:
        "education",

    DOMAIN_BUSINESS:
        "commerce",

    DOMAIN_COMMERCE:
        "commerce",

    DOMAIN_TRANSACTION:
        "commerce",

    DOMAIN_SECURITY:
        "security",

    DOMAIN_ISLAMIC_RELIGION:
        "religion",

    DOMAIN_CYBER_ATTACK:
        "security",

    DOMAIN_CYBER_SECURITY:
        "security",

    DOMAIN_CODING:
        "computing",

    DOMAIN_SOFTWARE_ENGINEERING:
        "computing",

    DOMAIN_PROGRAMMING_LANGUAGES:
        "computing",
}


# ============================================================================
# DOMAIN WEIGHTS
# ============================================================================

DOMAIN_WEIGHTS: Dict[
    str,
    float,
] = {

    DOMAIN_GENERAL_LANGUAGE:
        1.00,

    DOMAIN_CASUAL_CONVERSATION:
        0.95,

    DOMAIN_LOCAL_LANGUAGE:
        1.15,

    DOMAIN_IDIOMS:
        1.20,

    DOMAIN_MATHEMATICS:
        1.30,

    DOMAIN_PHYSICS:
        1.30,

    DOMAIN_GEOGRAPHY:
        1.15,

    DOMAIN_ENGINEERING:
        1.35,

    DOMAIN_MEDICINE:
        1.35,

    DOMAIN_EDUCATION:
        1.20,

    DOMAIN_BUSINESS:
        1.20,

    DOMAIN_COMMERCE:
        1.20,

    DOMAIN_TRANSACTION:
        1.30,

    DOMAIN_SECURITY:
        1.30,

    DOMAIN_ISLAMIC_RELIGION:
        1.25,

    DOMAIN_CYBER_ATTACK:
        1.35,

    DOMAIN_CYBER_SECURITY:
        1.40,

    DOMAIN_CODING:
        1.35,

    DOMAIN_SOFTWARE_ENGINEERING:
        1.40,

    DOMAIN_PROGRAMMING_LANGUAGES:
        1.35,
}


# ============================================================================
# DOMAIN SIGNALS
# ============================================================================

DOMAIN_SIGNALS: Dict[
    str,
    Set[str],
] = {

    DOMAIN_MATHEMATICS: {

        "equation",
        "formula",
        "theorem",
        "calculate",
        "integral",
        "derivative",
        "algebra",
        "geometry",
        "matrix",
        "vector",
        "probability",
        "fraction",
    },

    DOMAIN_PHYSICS: {

        "force",
        "energy",
        "mass",
        "velocity",
        "acceleration",
        "quantum",
        "particle",
        "gravity",
        "momentum",
        "wave",
        "electron",
    },

    DOMAIN_GEOGRAPHY: {

        "country",
        "continent",
        "city",
        "state",
        "region",
        "latitude",
        "longitude",
        "coordinate",
        "climate",
        "population",
        "distance",
    },

    DOMAIN_ENGINEERING: {

        "engineering",
        "system",
        "mechanism",
        "component",
        "structure",
        "design",
        "specification",
        "constraint",
        "circuit",
        "mechanical",
    },

    DOMAIN_MEDICINE: {

        "patient",
        "symptom",
        "diagnosis",
        "treatment",
        "anatomy",
        "physiology",
        "medicine",
        "disease",
        "clinical",
        "medical",
    },

    DOMAIN_EDUCATION: {

        "lesson",
        "student",
        "teacher",
        "curriculum",
        "exam",
        "assessment",
        "learn",
        "education",
        "classroom",
        "school",
    },

    DOMAIN_BUSINESS: {

        "business",
        "management",
        "strategy",
        "marketing",
        "revenue",
        "profit",
        "customer",
        "operations",
        "company",
        "market",
    },

    DOMAIN_COMMERCE: {

        "merchant",
        "buyer",
        "seller",
        "product",
        "purchase",
        "sale",
        "shop",
        "marketplace",
        "price",
        "goods",
    },

    DOMAIN_TRANSACTION: {

        "payment",
        "transaction",
        "invoice",
        "receipt",
        "transfer",
        "refund",
        "balance",
        "settlement",
        "purchase",
        "payment",
    },

    DOMAIN_SECURITY: {

        "authentication",
        "authorization",
        "access",
        "security",
        "protection",
        "identity",
        "permission",
        "fraud",
        "verification",
    },

    DOMAIN_CYBER_ATTACK: {

        "exploit",
        "payload",
        "malware",
        "phishing",
        "vulnerability",
        "attack",
        "breach",
        "injection",
        "ransomware",
    },

    DOMAIN_CYBER_SECURITY: {

        "hardening",
        "mitigation",
        "detection",
        "monitoring",
        "patching",
        "incident",
        "firewall",
        "defense",
        "security",
    },

    DOMAIN_ISLAMIC_RELIGION: {

        "allah",
        "quran",
        "qur'an",
        "hadith",
        "sunnah",
        "islam",
        "muslim",
        "fiqh",
        "tafsir",
        "salah",
        "zakat",
        "ramadan",
    },

    DOMAIN_CODING: {

        "function",
        "class",
        "variable",
        "import",
        "return",
        "loop",
        "syntax",
        "compile",
        "program",
        "code",
    },

    DOMAIN_SOFTWARE_ENGINEERING: {

        "architecture",
        "repository",
        "api",
        "database",
        "backend",
        "frontend",
        "deployment",
        "testing",
        "software",
    },

    DOMAIN_PROGRAMMING_LANGUAGES: {

        "python",
        "javascript",
        "typescript",
        "java",
        "rust",
        "golang",
        "c++",
        "sql",
        "html",
        "css",
    },

    DOMAIN_IDIOMS: {

        "idiom",
        "expression",
        "figurative",
        "phrase",
    },
}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class LanguageProfile:

    primary_language: str

    detected_languages: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    language_count: int = 1

    multilingual: bool = False


@dataclass
class DomainProfile:

    primary_domain: str

    parent_domain: str

    secondary_domains: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    confidence: float = 0.0


@dataclass
class WeightProfile:

    base: float = (
        DEFAULT_BASE_WEIGHT
    )

    language: float = 1.0

    structure: float = 1.0

    domain: float = 1.0

    validation: float = 1.0

    complexity: float = 1.0

    final: float = (
        DEFAULT_BASE_WEIGHT
    )


# ============================================================================
# FINE TUNER
# ============================================================================

class FineTunerAndWeightScalar:
    """
    Domain-aware learning calibration layer.

    This class prepares learning units for:

        - WordUnderstanding
        - train.py
        - background_training.py

    AI responses are routed through MemoryPartition so that they
    remain structurally distinct from user-originated input.
    """

    # ======================================================================
    # INITIALIZATION
    # ======================================================================

    def __init__(
        self,
        memory_grid: Any,
        memory_partition: Optional[
            Any
        ] = None,
        grid_cv: Optional[
            Any
        ] = None,
        matrix_maths: Optional[
            Any
        ] = None,
        code_mixer: Optional[
            Any
        ] = None,
        data_mixer: Optional[
            Any
        ] = None,
        mirror_learning_limit: int = (
            MIRROR_LEARNING_LIMIT
        ),
    ) -> None:

        self.memory = memory_grid

        # --------------------------------------------------------------
        # MemoryPartition
        # --------------------------------------------------------------

        self.partition = (
            memory_partition
        )

        if (
            self.partition is None
            and hasattr(
                memory_grid,
                "memory_partition",
            )
        ):

            self.partition = (
                memory_grid.memory_partition
            )

        if (
            self.partition is None
            and hasattr(
                memory_grid,
                "partition",
            )
        ):

            self.partition = (
                memory_grid.partition
            )

        # --------------------------------------------------------------
        # GridCV
        # --------------------------------------------------------------

        self.grid_cv = grid_cv

        if (
            self.grid_cv is None
            and GridCV is not None
        ):

            try:

                self.grid_cv = (
                    GridCV(
                        memory_grid
                    )
                )

            except Exception:

                self.grid_cv = None

        # --------------------------------------------------------------
        # MatrixMaths
        # --------------------------------------------------------------

        self.matrix_maths = (
            matrix_maths
        )

        if (
            self.matrix_maths is None
            and MatrixMaths is not None
        ):

            try:

                self.matrix_maths = (
                    MatrixMaths()
                )

            except Exception:

                self.matrix_maths = None

        # --------------------------------------------------------------
        # CodeMixer
        # --------------------------------------------------------------

        self.code_mixer = (
            code_mixer
        )

        if (
            self.code_mixer is None
            and CodeMixer is not None
        ):

            try:

                self.code_mixer = (
                    CodeMixer()
                )

            except Exception:

                self.code_mixer = None

        # --------------------------------------------------------------
        # DataMixer compatibility
        # --------------------------------------------------------------

        self.data_mixer = (
            data_mixer
        )

        if (
            self.data_mixer is None
            and DataMixer is not None
        ):

            try:

                self.data_mixer = (
                    DataMixer()
                )

            except Exception:

                self.data_mixer = None

        self.mirror_learning_limit = (
            max(
                1,
                int(
                    mirror_learning_limit
                ),
            )
        )

        # --------------------------------------------------------------
        # Mirror learning state
        # --------------------------------------------------------------

        self.learning_units: List[
            Dict[str, Any]
        ] = []

        self.ai_response_units: List[
            Dict[str, Any]
        ] = []

        self.user_input_units: List[
            Dict[str, Any]
        ] = []

    # ======================================================================
    # TEXT NORMALIZATION
    # ======================================================================

    @staticmethod
    def normalize_text(
        text: Any,
    ) -> str:

        value = str(
            text or ""
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

# ======================================================================
    # LANGUAGE DETECTION
    # ======================================================================

    def detect_language_profile(
        self,
        text: str,
        fallback: str = (
            DEFAULT_LANGUAGE
        ),
    ) -> LanguageProfile:

        text = self.normalize_text(
            text
        )

        fallback = normalize_lang(
            fallback
        )

        if not text:

            return LanguageProfile(
                primary_language=fallback
            )

        if (
            not LANGDETECT_AVAILABLE
            or detect is None
        ):

            return LanguageProfile(
                primary_language=fallback,
                detected_languages=[
                    {
                        "language": fallback,
                        "probability": 1.0,
                    }
                ],
            )

        try:

            detected = detect_langs(
                text
            )

            languages: List[
                Dict[str, Any]
            ] = []

            for item in detected:

                language = normalize_lang(
                    getattr(
                        item,
                        "lang",
                        fallback,
                    )
                )

                probability = float(
                    getattr(
                        item,
                        "prob",
                        0.0,
                    )
                )

                languages.append(
                    {
                        "language":
                            language,

                        "probability":
                            probability,
                    }
                )

            if not languages:

                primary = normalize_lang(
                    detect(
                        text
                    )
                )

                languages = [
                    {
                        "language":
                            primary,

                        "probability":
                            1.0,
                    }
                ]

            primary_language = (
                languages[0][
                    "language"
                ]
            )

            meaningful = [

                item

                for item in languages

                if item[
                    "probability"
                ] >= 0.05

            ]

            unique_languages = {

                item[
                    "language"
                ]

                for item in meaningful
            }

            return LanguageProfile(

                primary_language=
                    primary_language,

                detected_languages=
                    languages,

                language_count=
                    max(
                        1,
                        len(
                            unique_languages
                        ),
                    ),

                multilingual=
                    len(
                        unique_languages
                    ) > 1,
            )

        except Exception:

            return LanguageProfile(
                primary_language=fallback,
                detected_languages=[
                    {
                        "language":
                            fallback,

                        "probability":
                            1.0,
                    }
                ],
            )

    # ======================================================================
    # TOKENIZATION
    # ======================================================================

    def tokenize_text(
        self,
        text: str,
        lang: str,
    ) -> List[Any]:

        try:

            return list(
                tokenize(
                    text,
                    lang,
                )
            )

        except Exception:

            return re.findall(
                r"\w+|[^\w\s]",
                text,
                flags=re.UNICODE,
            )

    # ======================================================================
    # STRUCTURE ANALYSIS
    # ======================================================================

    def analyse_structure(
        self,
        text: str,
        tokens: List[Any],
    ) -> Dict[
        str,
        Any,
    ]:

        text = self.normalize_text(
            text
        )

        token_count = len(
            tokens
        )

        sentence_count = len(
            [
                value

                for value in re.split(
                    r"[.!?]+",
                    text,
                )

                if value.strip()
            ]
        )

        paragraph_count = len(
            [
                value

                for value in re.split(
                    r"\n\s*\n",
                    text,
                )

                if value.strip()
            ]
        )

        code_like = bool(

            re.search(
                r"("
                r"\bdef\s+"
                r"|"
                r"\bclass\s+"
                r"|"
                r"\bfunction\s+"
                r"|"
                r"\bimport\s+"
                r"|"
                r"\breturn\b"
                r"|"
                r"[{};]"
                r")",
                text,
            )
        )

        mathematical = bool(

            re.search(
                r"("
                r"\d+\s*[+\-*/=^]\s*\d+"
                r"|"
                r"[∑∫√∞≈≠≤≥]"
                r")",
                text,
            )
        )

        symbolic = bool(

            re.search(
                r"[^\w\s.,!?;:'\"()-]",
                text,
            )
        )

        conversation = (
            text.count(
                "?"
            )
            > 0
            or bool(
                re.search(
                    r"\b("
                    r"hello"
                    r"|hi"
                    r"|hey"
                    r"|you"
                    r"|i"
                    r"|we"
                    r")\b",
                    text,
                    flags=re.I,
                )
            )
        )

        return {

            "sentence_count":
                sentence_count,

            "paragraph_count":
                max(
                    1,
                    paragraph_count,
                ),

            "token_count":
                token_count,

            "character_count":
                len(
                    text
                ),

            "is_sentence":
                sentence_count == 1,

            "is_paragraph":
                (
                    paragraph_count > 1
                    or sentence_count > 1
                ),

            "is_code":
                code_like,

            "is_mathematical":
                mathematical,

            "is_symbolic":
                symbolic,

            "is_conversation":
                conversation,
        }

    # ======================================================================
    # DOMAIN DETECTION
    # ======================================================================

    def classify_domain(
        self,
        text: str,
        tokens: Optional[
            List[Any]
        ] = None,
    ) -> DomainProfile:

        text = self.normalize_text(
            text
        )

        lowered = text.lower()

        token_set = set()

        if tokens:

            token_set = {

                str(
                    token
                ).lower()

                for token in tokens
            }

        scores: Dict[
            str,
            float,
        ] = {}

        for domain, signals in (
            DOMAIN_SIGNALS.items()
        ):

            score = 0.0

            for signal in signals:

                if (
                    signal
                    in token_set
                ):

                    score += 1.0

                    continue

                if (
                    re.search(
                        r"\b"
                        + re.escape(
                            signal
                        )
                        + r"\b",
                        lowered,
                    )
                ):

                    score += 1.0

            scores[
                domain
            ] = score

        # --------------------------------------------------------------
        # Code structural signals
        # --------------------------------------------------------------

        if re.search(
            r"\b("
            r"def"
            r"|class"
            r"|function"
            r"|import"
            r"|return"
            r"|async"
            r"|await"
            r")\b",
            lowered,
        ):

            scores[
                DOMAIN_CODING
            ] = (
                scores.get(
                    DOMAIN_CODING,
                    0.0,
                )
                + 3.0
            )

        # --------------------------------------------------------------
        # Default domain
        # --------------------------------------------------------------

        ranked = sorted(

            scores.items(),

            key=lambda item:
                item[1],

            reverse=True,
        )

        if (
            not ranked
            or ranked[0][1] <= 0
        ):

            primary = (
                DOMAIN_GENERAL_LANGUAGE
            )

            return DomainProfile(

                primary_domain=
                    primary,

                parent_domain=
                    DOMAIN_PARENTS[
                        primary
                    ],

                confidence=
                    0.0,
            )

        primary, primary_score = (
            ranked[0]
        )

        total_score = sum(
            value

            for _, value in ranked

            if value > 0
        )

        confidence = (

            primary_score
            / total_score

            if total_score > 0

            else 0.0
        )

        secondary = []

        for domain, score in ranked[
            1:
        ]:

            if score <= 0:
                continue

            secondary.append(
                {
                    "domain":
                        domain,

                    "parent_domain":
                        DOMAIN_PARENTS.get(
                            domain,
                            "knowledge",
                        ),

                    "score":
                        score,

                    "relative_confidence":
                        (
                            score
                            / total_score
                        ),
                }
            )

        return DomainProfile(

            primary_domain=
                primary,

            parent_domain=
                DOMAIN_PARENTS.get(
                    primary,
                    "knowledge",
                ),

            secondary_domains=
                secondary,

            confidence=
                confidence,
        )

    # ======================================================================
    # LANGUAGE WEIGHT
    # ======================================================================

    def language_weight(
        self,
        profile: LanguageProfile,
    ) -> float:

        if (
            profile.multilingual
        ):

            return min(
                1.0
                + (
                    0.10
                    * (
                        profile.language_count
                        - 1
                    )
                ),
                1.50,
            )

        return 1.0

    # ======================================================================
    # STRUCTURE WEIGHT
    # ======================================================================

    def structure_weight(
        self,
        structure: Dict[
            str,
            Any,
        ],
    ) -> float:

        weight = 1.0

        if structure.get(
            "is_paragraph"
        ):

            weight += 0.10

        if structure.get(
            "is_mathematical"
        ):

            weight += 0.15

        if structure.get(
            "is_symbolic"
        ):

            weight += 0.10

        if structure.get(
            "is_code"
        ):

            weight += 0.20

        return min(
            weight,
            2.0,
        )

    # ======================================================================
    # DOMAIN WEIGHT
    # ======================================================================

    def domain_weight(
        self,
        profile: DomainProfile,
    ) -> float:

        return DOMAIN_WEIGHTS.get(

            profile.primary_domain,

            1.0,
        )

    # ======================================================================
    # COMPLEXITY WEIGHT
    # ======================================================================

    def complexity_weight(
        self,
        structure: Dict[
            str,
            Any,
        ],
    ) -> float:

        token_count = int(
            structure.get(
                "token_count",
                0,
            )
        )

        if token_count <= 5:

            return 0.95

        if token_count <= 20:

            return 1.0

        if token_count <= 80:

            return 1.10

        if token_count <= 250:

            return 1.20

        return 1.30

    # ======================================================================
    # SYMBOL SIGNALS
    # ======================================================================

    def symbol_signals(
        self,
        text: str,
    ) -> Dict[
        str,
        Any,
    ]:

        if (
            symbols_module is None
        ):

            return {

                "available":
                    False,

                "signals":
                    {},
            }

        # --------------------------------------------------------------
        # Flexible module API.
        # --------------------------------------------------------------

        for name in (
            "analyse",
            "analyze",
            "extract",
            "process",
        ):

            function = getattr(
                symbols_module,
                name,
                None,
            )

            if callable(
                function
            ):

                try:

                    result = function(
                        text
                    )

                    return {

                        "available":
                            True,

                        "signals":
                            result,
                    }

                except Exception:
                    pass

        return {

            "available":
                True,

            "signals":
                {},
        }

    # ======================================================================
    # MATRIX SIGNALS
    # ======================================================================

    def matrix_signals(
        self,
        text: str,
        lang: str,
        domain: DomainProfile,
    ) -> Dict[
        str,
        Any,
    ]:

        if (
            self.matrix_maths
            is None
        ):

            return {}

        for name in (
            "analyse",
            "analyze",
            "process",
            "calculate",
            "signals",
        ):

            method = getattr(
                self.matrix_maths,
                name,
                None,
            )

            if not callable(
                method
            ):
                continue

            try:

                return method(
                    text=text,
                    lang=lang,
                    domain=(
                        domain.primary_domain
                    ),
                )

            except TypeError:

                try:

                    return method(
                        text
                    )

                except Exception:
                    continue

            except Exception:
                continue

        return {}

    # ======================================================================
    # CODE MIXER SIGNALS
    # ======================================================================

    def code_signals(
        self,
        text: str,
        structure: Dict[
            str,
            Any,
        ],
    ) -> Dict[
        str,
        Any,
    ]:

        if not structure.get(
            "is_code"
        ):

            return {

                "is_code":
                    False,

                "signals":
                    {},
            }

        mixer = (
            self.code_mixer
            or self.data_mixer
        )

        if mixer is None:

            return {

                "is_code":
                    True,

                "signals":
                    {},
            }

        for name in (
            "analyse",
            "analyze",
            "mix",
            "process",
        ):

            method = getattr(
                mixer,
                name,
                None,
            )

            if callable(
                method
            ):

                try:

                    return {

                        "is_code":
                            True,

                        "signals":
                            method(
                                text
                            ),
                    }

                except Exception:
                    continue

        return {

            "is_code":
                True,

            "signals":
                {},
        }

# ======================================================================
    # GRID CV VALIDATION
    # ======================================================================

    def validate_with_grid_cv(
        self,
        text: str,
        lang: str,
        domain: DomainProfile,
        structure: Dict[
            str,
            Any,
        ],
    ) -> Dict[
        str,
        Any,
    ]:

        if (
            self.grid_cv is None
        ):

            return {

                "available":
                    False,

                "validation_score":
                    DEFAULT_VALIDATION_SCORE,

                "signals":
                    {},
            }

        for name in (
            "validate",
            "analyse",
            "analyze",
            "evaluate",
            "compare",
        ):

            method = getattr(
                self.grid_cv,
                name,
                None,
            )

            if not callable(
                method
            ):
                continue

            try:

                result = method(

                    text=text,

                    lang=lang,

                    domain=(
                        domain.primary_domain
                    ),

                    structure=structure,
                )

                return self._normalise_validation(
                    result
                )

            except TypeError:

                try:

                    result = method(
                        text
                    )

                    return self._normalise_validation(
                        result
                    )

                except Exception:
                    continue

            except Exception:
                continue

        return {

            "available":
                True,

            "validation_score":
                DEFAULT_VALIDATION_SCORE,

            "signals":
                {},
        }

    # ======================================================================
    # VALIDATION NORMALIZATION
    # ======================================================================

    @staticmethod
    def _normalise_validation(
        result: Any,
    ) -> Dict[
        str,
        Any,
    ]:

        if isinstance(
            result,
            dict,
        ):

            score = (

                result.get(
                    "validation_score"
                )

                or result.get(
                    "score"
                )

                or result.get(
                    "confidence"
                )

                or DEFAULT_VALIDATION_SCORE
            )

            try:

                score = float(
                    score
                )

            except Exception:

                score = (
                    DEFAULT_VALIDATION_SCORE
                )

            return {

                "available":
                    True,

                "validation_score":
                    max(
                        0.0,
                        min(
                            1.0,
                            score,
                        ),
                    ),

                "signals":
                    result,
            }

        if isinstance(
            result,
            bool,
        ):

            return {

                "available":
                    True,

                "validation_score":
                    1.0
                    if result
                    else 0.0,

                "signals":
                    {
                        "valid":
                            result
                    },
            }

        return {

            "available":
                True,

            "validation_score":
                DEFAULT_VALIDATION_SCORE,

            "signals":
                {
                    "result":
                        result
                },
        }

    # ======================================================================
    # VALIDATION WEIGHT
    # ======================================================================

    @staticmethod
    def validation_weight(
        validation_score: float,
    ) -> float:

        validation_score = max(
            0.0,
            min(
                1.0,
                float(
                    validation_score
                ),
            ),
        )

        return (
            0.50
            + validation_score
        )

    # ======================================================================
    # CALCULATE WEIGHTS
    # ======================================================================

    def calculate_weights(
        self,
        language: LanguageProfile,
        structure: Dict[
            str,
            Any,
        ],
        domain: DomainProfile,
        validation: Dict[
            str,
            Any,
        ],
    ) -> WeightProfile:

        profile = WeightProfile()

        profile.language = (
            self.language_weight(
                language
            )
        )

        profile.structure = (
            self.structure_weight(
                structure
            )
        )

        profile.domain = (
            self.domain_weight(
                domain
            )
        )

        profile.validation = (
            self.validation_weight(

                validation.get(
                    "validation_score",
                    DEFAULT_VALIDATION_SCORE,
                )
            )
        )

        profile.complexity = (
            self.complexity_weight(
                structure
            )
        )

        profile.final = (

            profile.base

            * profile.language

            * profile.structure

            * profile.domain

            * profile.validation

            * profile.complexity
        )

        profile.final = max(

            MIN_WEIGHT,

            min(
                MAX_WEIGHT,
                profile.final,
            ),
        )

        return profile

    # ======================================================================
    # TRAINING PARAMETERS
    # ======================================================================

    def build_training_parameters(
        self,
        language: LanguageProfile,
        domain: DomainProfile,
        structure: Dict[
            str,
            Any,
        ],
        validation: Dict[
            str,
            Any,
        ],
        weights: WeightProfile,
    ) -> Dict[
        str,
        Any,
    ]:

        validation_score = float(

            validation.get(
                "validation_score",
                DEFAULT_VALIDATION_SCORE,
            )
        )

        return {

            "sample_weight":
                weights.final,

            "base_weight":
                weights.base,

            "language_weight":
                weights.language,

            "structure_weight":
                weights.structure,

            "domain_weight":
                weights.domain,

            "validation_weight":
                weights.validation,

            "complexity_weight":
                weights.complexity,

            "validation_score":
                validation_score,

            "primary_language":
                language.primary_language,

            "multilingual":
                language.multilingual,

            "primary_domain":
                domain.primary_domain,

            "parent_domain":
                domain.parent_domain,

            "training_eligible":

                validation_score
                >= 0.50,

            "structure_type":

                "code"

                if structure.get(
                    "is_code"
                )

                else (

                    "mathematical"

                    if structure.get(
                        "is_mathematical"
                    )

                    else (

                        "paragraph"

                        if structure.get(
                            "is_paragraph"
                        )

                        else "sentence"
                    )
                ),
        }

    # ======================================================================
    # BUILD LEARNING UNIT
    # ======================================================================

    def build_learning_unit(
        self,
        text: str,
        lang: Optional[
            str
        ] = None,
        source_type: str = (
            USER_INPUT_SOURCE
        ),
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[
        str,
        Any,
    ]:

        text = self.normalize_text(
            text
        )

        fallback_language = (
            normalize_lang(
                lang
                or DEFAULT_LANGUAGE
            )
        )

        language = (
            self.detect_language_profile(
                text,
                fallback=
                    fallback_language,
            )
        )

        tokens = (
            self.tokenize_text(

                text,

                language.primary_language,
            )
        )

        structure = (
            self.analyse_structure(
                text,
                tokens,
            )
        )

        domain = (
            self.classify_domain(
                text,
                tokens,
            )
        )

        validation = (
            self.validate_with_grid_cv(

                text,

                language.primary_language,

                domain,

                structure,
            )
        )

        weights = (
            self.calculate_weights(

                language,

                structure,

                domain,

                validation,
            )
        )

        training_parameters = (
            self.build_training_parameters(

                language,

                domain,

                structure,

                validation,

                weights,
            )
        )

        return {

            "text":
                text,

            "source_type":
                source_type,

            "language": {

                "primary":
                    language.primary_language,

                "detected":
                    language.detected_languages,

                "count":
                    language.language_count,

                "multilingual":
                    language.multilingual,
            },

            "tokens":
                tokens,

            "token_count":
                len(
                    tokens
                ),

            "structure":
                structure,

            "domain": {

                "primary":
                    domain.primary_domain,

                "parent":
                    domain.parent_domain,

                "secondary":
                    domain.secondary_domains,

                "confidence":
                    domain.confidence,
            },

            "matrix":
                self.matrix_signals(

                    text,

                    language.primary_language,

                    domain,
                ),

            "symbols":
                self.symbol_signals(
                    text
                ),

            "code":
                self.code_signals(

                    text,

                    structure,
                ),

            "grid_cv":
                validation,

            "weights": {

                "base":
                    weights.base,

                "language":
                    weights.language,

                "structure":
                    weights.structure,

                "domain":
                    weights.domain,

                "validation":
                    weights.validation,

                "complexity":
                    weights.complexity,

                "final":
                    weights.final,
            },

            "training_parameters":
                training_parameters,

            "metadata":
                metadata
                or {},
        }

    # ======================================================================
    # MEMORY PARTITION ROUTING
    # ======================================================================

    def _store_via_partition(
        self,
        learning_unit: Dict[
            str,
            Any,
        ],
        source_type: str,
    ) -> Dict[
        str,
        Any,
    ]:

        if (
            self.partition is None
        ):

            return {

                "stored":
                    False,

                "reason":
                    "memory_partition_unavailable",
            }

        # --------------------------------------------------------------
        # Flexible routing API.
        # --------------------------------------------------------------

        routing_methods = (

            "store_learning_unit",

            "store",

            "partition_and_store",

            "route",

            "add",
        )

        for name in routing_methods:

            method = getattr(
                self.partition,
                name,
                None,
            )

            if not callable(
                method
            ):
                continue

            # ----------------------------------------------------------
            # AI response route
            # ----------------------------------------------------------

            try:

                result = method(

                    data=
                        learning_unit,

                    source_type=
                        source_type,

                    partition_type=

                        "ai_response"

                        if source_type
                        == AI_RESPONSE_SOURCE

                        else "user_input",
                )

                return {

                    "stored":
                        True,

                    "result":
                        result,
                }

            except TypeError:

                try:

                    result = method(
                        learning_unit
                    )

                    return {

                        "stored":
                            True,

                        "result":
                            result,
                    }

                except Exception:
                    continue

            except Exception:
                continue

        return {

            "stored":
                False,

            "reason":
                "no_compatible_partition_method",
        }

    # ======================================================================
    # MEMORYGRID FALLBACK
    # ======================================================================

    def _store_in_memory_grid(
        self,
        learning_unit: Dict[
            str,
            Any,
        ],
        source_type: str,
    ) -> Dict[
        str,
        Any,
    ]:

        if not hasattr(
            self.memory,
            "add_document",
        ):

            return {

                "stored":
                    False,

                "reason":
                    "memory_grid_add_document_unavailable",
            }

        text = (
            learning_unit[
                "text"
            ]
        )

        lang = (
            learning_unit[
                "language"
            ][
                "primary"
            ]
        )

        try:

            document_id = (
                self.memory.add_document(

                    text=text,

                    lang=lang,

                    source=
                        source_type,
                )
            )

            return {

                "stored":
                    True,

                "doc_id":
                    document_id,
            }

        except Exception as exc:

            return {

                "stored":
                    False,

                "reason":
                    str(
                        exc
                    ),
            }

    # ======================================================================
    # STORE LEARNING UNIT
    # ======================================================================

    def store_learning_unit(
        self,
        learning_unit: Dict[
            str,
            Any,
        ],
    ) -> Dict[
        str,
        Any,
    ]:

        source_type = (
            learning_unit.get(
                "source_type"
            )
            or USER_INPUT_SOURCE
        )

        # --------------------------------------------------------------
        # MemoryPartition remains first authority.
        # --------------------------------------------------------------

        result = (
            self._store_via_partition(

                learning_unit,

                source_type,
            )
        )

        if result.get(
            "stored"
        ):

            return result

        # --------------------------------------------------------------
        # MemoryGrid fallback.
        #
        # This is not a replacement partition architecture.
        # It preserves ingestion while MemoryPartition APIs evolve.
        # --------------------------------------------------------------

        return (
            self._store_in_memory_grid(

                learning_unit,

                source_type,
            )
        )

    # ======================================================================
    # PROCESS LEARNING MATERIAL
    # ======================================================================

    def process(
        self,
        text: str,
        lang: Optional[
            str
        ] = None,
        source_type: str = (
            USER_INPUT_SOURCE
        ),
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        store: bool = True,
    ) -> Dict[
        str,
        Any,
    ]:

        if (
            len(
                self.learning_units
            )
            >= self.mirror_learning_limit
        ):

            return {

                "processed":
                    False,

                "reason":
                    "mirror_learning_limit_reached",

                "limit":
                    self.mirror_learning_limit,
            }

        learning_unit = (
            self.build_learning_unit(

                text=text,

                lang=lang,

                source_type=
                    source_type,

                metadata=
                    metadata,
            )
        )

        self.learning_units.append(
            learning_unit
        )

        if (
            source_type
            == AI_RESPONSE_SOURCE
        ):

            self.ai_response_units.append(
                learning_unit
            )

        else:

            self.user_input_units.append(
                learning_unit
            )

        storage = {

            "stored":
                False
        }

        if store:

            storage = (
                self.store_learning_unit(
                    learning_unit
                )
            )

        return {

            "processed":
                True,

            "learning_unit":
                learning_unit,

            "storage":
                storage,
        }

    # ======================================================================
    # USER INPUT
    # ======================================================================

    def process_user_input(
        self,
        text: str,
        lang: Optional[
            str
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        store: bool = True,
    ) -> Dict[
        str,
        Any,
    ]:

        return self.process(

            text=text,

            lang=lang,

            source_type=
                USER_INPUT_SOURCE,

            metadata=
                metadata,

            store=store,
        )

    # ======================================================================
    # AI RESPONSE
    # ======================================================================

    def process_ai_response(
        self,
        response_text: str,
        lang: Optional[
            str
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        store: bool = True,
    ) -> Dict[
        str,
        Any,
    ]:
        """
        Process an AI-generated response.

        FLOW
        ----

            AI Response
                ↓
            GridCV
                ↓
            FineTuner weights
                ↓
            Training parameters
                ↓
            MemoryPartition
                ↓
            AI Response Partition
                ↓
            MemoryGrid

        AI-generated responses remain distinct from user input.
        """

        metadata = dict(
            metadata
            or {}
        )

        metadata.setdefault(

            "memory_origin",

            "ai_generated",
        )

        metadata.setdefault(

            "training_state",

            "generated",
        )

        return self.process(

            text=response_text,

            lang=lang,

            source_type=
                AI_RESPONSE_SOURCE,

            metadata=
                metadata,

            store=store,
        )

    # ======================================================================
    # BATCH PROCESS
    # ======================================================================

    def process_many(
        self,
        texts: Iterable[
            str
        ],
        lang: Optional[
            str
        ] = None,
        source_type: str = (
            USER_INPUT_SOURCE
        ),
        store: bool = True,
    ) -> List[
        Dict[str, Any]
    ]:

        results = []

        for text in texts:

            if (
                len(
                    self.learning_units
                )
                >= self.mirror_learning_limit
            ):

                break

            results.append(

                self.process(

                    text=text,

                    lang=lang,

                    source_type=
                        source_type,

                    store=store,
                )
            )

        return results

    # ======================================================================
    # AI RESPONSE TRAINING DATA
    # ======================================================================

    def training_eligible_ai_responses(
        self,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Return AI responses that passed the basic FineTuner
        training eligibility threshold.

        train.py and background_training.py can consume this through
        their own training pipelines.
        """

        results = []

        for unit in (
            self.ai_response_units
        ):

            parameters = (
                unit.get(
                    "training_parameters",
                    {},
                )
            )

            if not parameters.get(
                "training_eligible",
                False,
            ):

                continue

            results.append(
                unit
            )

        return results

    # ======================================================================
    # STATISTICS
    # ======================================================================

    def stats(
        self,
    ) -> Dict[
        str,
        Any,
    ]:

        domain_counts: Dict[
            str,
            int,
        ] = {}

        language_counts: Dict[
            str,
            int,
        ] = {}

        for unit in (
            self.learning_units
        ):

            domain = (
                unit.get(
                    "domain",
                    {}
                ).get(
                    "primary"
                )
            )

            if domain:

                domain_counts[
                    domain
                ] = (

                    domain_counts.get(
                        domain,
                        0,
                    )
                    + 1
                )

            language = (
                unit.get(
                    "language",
                    {}
                ).get(
                    "primary"
                )
            )

            if language:

                language_counts[
                    language
                ] = (

                    language_counts.get(
                        language,
                        0,
                    )
                    + 1
                )

        return {

            "mirror_learning_limit":
                self.mirror_learning_limit,

            "learning_units":
                len(
                    self.learning_units
                ),

            "user_input_units":
                len(
                    self.user_input_units
                ),

            "ai_response_units":
                len(
                    self.ai_response_units
                ),

            "training_eligible_ai_responses":
                len(
                    self.training_eligible_ai_responses()
                ),

            "domains":
                domain_counts,

            "languages":
                language_counts,

            "langdetect_available":
                LANGDETECT_AVAILABLE,

            "grid_cv_available":
                self.grid_cv
                is not None,

            "matrix_maths_available":
                self.matrix_maths
                is not None,

            "code_mixer_available":
                self.code_mixer
                is not None,

            "data_mixer_available":
                self.data_mixer
                is not None,

            "memory_partition_available":
                self.partition
                is not None,
        }


# ============================================================================
# FUNCTIONAL API
# ============================================================================

def fine_tune(
    memory_grid: Any,
    text: str,
    lang: Optional[
        str
    ] = None,
    memory_partition: Optional[
        Any
    ] = None,
    source_type: str = (
        USER_INPUT_SOURCE
    ),
    store: bool = True,
) -> Dict[
    str,
    Any,
]:

    fine_tuner = (
        FineTunerAndWeightScalar(

            memory_grid=
                memory_grid,

            memory_partition=
                memory_partition,
        )
    )

    return fine_tuner.process(

        text=text,

        lang=lang,

        source_type=
            source_type,

        store=store,
    )


def fine_tune_ai_response(
    memory_grid: Any,
    response_text: str,
    lang: Optional[
        str
    ] = None,
    memory_partition: Optional[
        Any
    ] = None,
    store: bool = True,
) -> Dict[
    str,
    Any,
]:

    fine_tuner = (
        FineTunerAndWeightScalar(

            memory_grid=
                memory_grid,

            memory_partition=
                memory_partition,
        )
    )

    return (
        fine_tuner.process_ai_response(

            response_text=
                response_text,

            lang=lang,

            store=store,
        )
    )


# ============================================================================
# DEVELOPMENT TEST
# ============================================================================

if __name__ == "__main__":

    print(
        "CoMpaNeoN FineTunerAndWeightScalar"
    )

    print(
        {
            "mirror_learning_limit":
                MIRROR_LEARNING_LIMIT,

            "langdetect_available":
                LANGDETECT_AVAILABLE,

            "domains":
                sorted(
                    DOMAIN_WEIGHTS.keys()
                ),
        }
    )
