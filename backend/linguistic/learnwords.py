"""
CoMpaNeoN LearnWords
====================

Lexical learning-unit construction layer.

Pipeline:

    DataFilter
        ↓
    LearnWords
        ↓
    WordChain
        ↓
    WordUnderstanding

LearnWords is responsible for:

- language detection
- tokenizer integration
- canonical lexical extraction
- irrelevant abbreviation filtering
- preservation of original lexical forms
- multilingual structural representation
- words
- phrases
- sentences
- paragraphs
- linguistic sequence construction
- WordChain ingestion

LearnWords does NOT:

- replace tokenizer.py
- change tokenizer mathematics
- perform GSP traversal
- perform MemoryGrid placement
- perform MemoryPartition routing
- perform final model training
- replace WordUnderstanding
- replace FineTunerAndWeightScalar
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional

from langdetect import detect, LangDetectException

try:
    from .tokenizer import (
        tokenize,
        normalize_lang,
    )
    from .word_chain import WordChain
except ImportError:
    from tokenizer import (
        tokenize,
        normalize_lang,
    )
    from word_chain import WordChain


# ============================================================================
# CANONICAL ABBREVIATIONS
# ============================================================================

# These are retained because they are meaningful lexical/technical units.
# This list is deliberately conservative.

CANONICAL_ABBREVIATIONS = {
    # computing
    "cpu",
    "gpu",
    "ram",
    "rom",
    "arm",
    "x86",
    "x64",
    "nvme",
    "ssd",
    "hdd",
    "ecc",
    "ddr",
    "ddr4",
    "ddr5",
    "hbm",
    "hbm2",
    "hbm3",
    "hbm3e",
    "usb",
    "pci",
    "pcie",
    "nvlink",

    # software
    "api",
    "sdk",
    "orm",
    "sql",
    "http",
    "https",
    "html",
    "css",
    "json",
    "xml",
    "yaml",
    "rest",
    "jwt",
    "otp",
    "url",
    "uri",
    "uid",
    "uuid",
    "ip",
    "dns",
    "tcp",
    "udp",
    "ssh",
    "ssl",
    "tls",

    # operating systems / infrastructure
    "os",
    "vm",
    "kvm",
    "vps",
    "cdn",
    "ram",
    "lan",
    "wan",

    # AI
    "ai",
    "ml",
    "llm",
    "nlp",
    "cuda",
    "cudnn",
    "opencl",

    # common academic/technical
    "phd",
    "msc",
    "bsc",
    "lga",
    "ltd",
    "inc",
}


# ============================================================================
# IRRELEVANT ABBREVIATIONS
# ============================================================================

# These should not become canonical learning words unless explicitly
# overridden by metadata.

IRRELEVANT_ABBREVIATIONS = {
    "etc",
    "e.g",
    "eg",
    "i.e",
    "ie",
    "aka",
    "approx",
    "misc",
    "dept",
    "est",
    "fig",
    "no",
    "nos",
    "vol",
    "vs",
    "viz",
    "msg",
    "info",
    "ref",
    "temp",
    "misc",
}


# ============================================================================
# CLASSIC SAMPLE CORPUS
# ============================================================================

CLASSIC_LEARNING_BLOCKS = {

    "daily_conversation": {

        "words": [
            "hello",
            "goodbye",
            "please",
            "thanks",
            "sorry",
            "yes",
            "no",
            "maybe",
            "friend",
            "family",
            "home",
            "work",
            "school",
            "today",
            "tomorrow",
            "help",
            "understand",
            "explain",
            "remember",
            "forget",
        ],

        "phrases": [
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "I am fine",
            "thank you",
            "you are welcome",
            "please help me",
            "I understand",
            "I do not understand",
            "can you explain",
            "what do you mean",
            "let me check",
            "give me a moment",
            "that is correct",
            "that is not correct",
        ],

        "sentences": [
            "Hello, how are you today?",
            "I am fine, thank you.",
            "Please help me understand this.",
            "Can you explain what you mean?",
            "I understand the idea.",
            "I do not understand the last part.",
            "Let me check the information.",
            "That is correct.",
            "That is not correct.",
            "Please give me a moment.",
            "We can continue the discussion tomorrow.",
            "I will explain the problem clearly.",
        ],

        "paragraphs": [
            (
                "A conversation begins with a clear exchange between "
                "people. One person may ask a question, another person "
                "may answer, and either person may ask for clarification. "
                "Good communication depends on understanding what was "
                "said before responding."
            ),
            (
                "When a person does not understand something, the person "
                "can ask for an explanation. The explanation may be short "
                "or detailed depending on the subject. A useful response "
                "should address the actual question instead of assuming "
                "what the person meant."
            ),
        ],
    },

    "questions_and_explanations": {

        "words": [
            "what",
            "why",
            "when",
            "where",
            "who",
            "which",
            "how",
            "difference",
            "reason",
            "example",
            "meaning",
            "definition",
            "explanation",
        ],

        "phrases": [
            "what is",
            "what does it mean",
            "why does this happen",
            "how does it work",
            "what is the difference",
            "give an example",
            "explain the reason",
            "define the term",
        ],

        "sentences": [
            "What is this system?",
            "What does this word mean?",
            "Why does this happen?",
            "How does the system work?",
            "What is the difference between the two systems?",
            "Can you give an example?",
            "Please explain the reason.",
            "What does this result mean?",
            "How can the problem be solved?",
        ],

        "paragraphs": [
            (
                "A question identifies something that the speaker wants "
                "to understand. The answer should identify the subject, "
                "explain the relevant relationship, and provide an example "
                "when an example makes the idea easier to understand."
            ),
        ],
    },

    "mathematics": {

        "words": [
            "number",
            "value",
            "sum",
            "difference",
            "product",
            "ratio",
            "equation",
            "variable",
            "matrix",
            "vector",
            "coordinate",
            "function",
            "set",
            "factor",
            "constant",
        ],

        "phrases": [
            "add two numbers",
            "calculate the sum",
            "find the difference",
            "multiply the values",
            "solve the equation",
            "calculate the ratio",
            "find the coordinate",
            "compare two values",
            "calculate the vector",
            "evaluate the function",
        ],

        "sentences": [
            "The sum of two numbers is calculated by adding their values.",
            "The difference between two numbers is found by subtraction.",
            "A variable represents a value that may change.",
            "A coordinate identifies a position in a grid.",
            "A vector can represent direction and magnitude.",
            "A matrix contains values arranged in rows and columns.",
            "The same input should produce the same deterministic result.",
        ],

        "paragraphs": [
            (
                "A mathematical system uses defined operations to transform "
                "values. An equation may contain constants and variables, "
                "while a matrix may contain values arranged into rows and "
                "columns. A deterministic calculation produces the same "
                "result whenever the same valid inputs are supplied."
            ),
        ],
    },

    "engineering": {

        "words": [
            "system",
            "server",
            "processor",
            "memory",
            "storage",
            "network",
            "database",
            "kernel",
            "container",
            "device",
            "sensor",
            "controller",
            "architecture",
            "component",
            "interface",
        ],

        "phrases": [
            "computer system",
            "server processor",
            "memory controller",
            "storage device",
            "database server",
            "network interface",
            "system architecture",
            "software component",
            "hardware component",
            "distributed system",
        ],

        "sentences": [
            "A computer system contains hardware and software components.",
            "A server provides resources or services to other systems.",
            "A database stores structured information for later retrieval.",
            "A network interface connects a device to a network.",
            "A software component performs a defined responsibility.",
            "System architecture describes how components work together.",
        ],

        "paragraphs": [
            (
                "A computing system may contain processors, memory, storage, "
                "network interfaces, operating-system services, and application "
                "software. Each component has a defined responsibility. A good "
                "architecture keeps those responsibilities separated while "
                "allowing the components to communicate through clear interfaces."
            ),
        ],
    },

    "coding": {

        "words": [
            "code",
            "function",
            "class",
            "object",
            "variable",
            "method",
            "module",
            "package",
            "route",
            "request",
            "response",
            "database",
            "query",
            "error",
            "debug",
        ],

        "phrases": [
            "write a function",
            "call a function",
            "create an object",
            "define a class",
            "import a module",
            "send a request",
            "return a response",
            "query the database",
            "handle an error",
            "debug the program",
        ],

        "sentences": [
            "A function performs a defined operation.",
            "A class defines the structure and behavior of objects.",
            "A module groups related functionality.",
            "A request can be sent to a server endpoint.",
            "A response contains the result returned by the server.",
            "An error should be identified before the system is changed.",
            "A database query retrieves information from stored data.",
        ],

        "paragraphs": [
            (
                "A software application is usually divided into components "
                "with specific responsibilities. A function may perform a "
                "calculation, a class may represent an object, and a module "
                "may group related functionality. Clear separation makes "
                "the system easier to understand, test, and extend."
            ),
        ],
    },

    "education": {

        "words": [
            "student",
            "teacher",
            "lesson",
            "class",
            "subject",
            "question",
            "answer",
            "knowledge",
            "practice",
            "example",
            "exercise",
            "understanding",
        ],

        "phrases": [
            "learn a concept",
            "study a subject",
            "answer a question",
            "solve an exercise",
            "give an example",
            "practice a skill",
            "understand the lesson",
        ],

        "sentences": [
            "A student learns by studying information and practicing skills.",
            "A teacher can explain a difficult concept with an example.",
            "An exercise allows a student to practice a concept.",
            "A question can reveal what a student understands.",
            "Practice helps reinforce previously learned information.",
        ],

        "paragraphs": [
            (
                "Learning develops through repeated exposure, understanding, "
                "practice, comparison, and correction. A learner may first "
                "encounter a word, then see the word in a phrase, sentence, "
                "and paragraph. The surrounding context helps the learner "
                "understand how the word behaves in real communication."
            ),
        ],
    },

    "business": {

        "words": [
            "business",
            "customer",
            "merchant",
            "product",
            "service",
            "price",
            "payment",
            "order",
            "receipt",
            "invoice",
            "account",
            "transaction",
        ],

        "phrases": [
            "buy a product",
            "sell a product",
            "make a payment",
            "place an order",
            "receive a receipt",
            "create an invoice",
            "complete a transaction",
            "customer account",
            "merchant account",
        ],

        "sentences": [
            "A customer can place an order for a product.",
            "A merchant provides products or services to customers.",
            "A payment records the transfer of value for a transaction.",
            "A receipt records a completed purchase.",
            "An invoice describes an amount that is due.",
        ],

        "paragraphs": [
            (
                "A transaction connects a customer, a merchant, a product "
                "or service, and a payment process. An order describes what "
                "the customer wants to obtain. A receipt can confirm a "
                "completed purchase, while an invoice can describe an amount "
                "that remains due."
            ),
        ],
    },

    "organization_ai": {

        "words": [
            "organization",
            "worker",
            "member",
            "manager",
            "team",
            "department",
            "project",
            "role",
            "permission",
            "privacy",
            "memory",
            "context",
        ],

        "phrases": [
            "organization memory",
            "personal memory",
            "project context",
            "worker identity",
            "team member",
            "department role",
            "access permission",
            "private information",
            "shared knowledge",
        ],

        "sentences": [
            "An organization contains people with different roles.",
            "A worker may belong to a team or department.",
            "Project context describes the work currently being performed.",
            "Private information should not automatically become shared knowledge.",
            "Permissions determine which information a member can access.",
            "Personal memory and organization memory can have different boundaries.",
        ],

        "paragraphs": [
            (
                "An organization-aware AI must distinguish between personal "
                "context and shared organizational knowledge. A worker may "
                "have private information that should remain private, while "
                "the organization may maintain knowledge that is available "
                "to authorized members. Access should therefore follow the "
                "defined role, permission, and context boundaries."
            ),
        ],
    },

    "technical_infrastructure": {

        "words": [
            "CPU",
            "ARM",
            "x86",
            "ECC",
            "DDR5",
            "NVMe",
            "Linux",
            "kernel",
            "KVM",
            "container",
            "GPU",
            "Tensor",
            "Core",
            "VRAM",
            "HBM",
            "CUDA",
            "cuDNN",
            "OpenCL",
            "Nginx",
            "Apache",
            "OpenSSL",
            "cache",
        ],

        "phrases": [
            "server CPU",
            "ECC memory",
            "DDR5 memory",
            "NVMe storage",
            "Linux kernel",
            "KVM virtual machine",
            "GPU memory",
            "HBM memory",
            "CUDA application",
            "OpenCL application",
            "web server",
            "application server",
            "AI training server",
        ],

        "sentences": [
            "A server CPU executes instructions for the operating system and applications.",
            "ECC memory can detect and correct certain memory errors.",
            "NVMe storage provides a high-speed interface for storage devices.",
            "The Linux kernel manages hardware and system resources.",
            "A container isolates an application environment from other processes.",
            "A GPU can accelerate parallel workloads.",
            "HBM provides high-bandwidth memory access for supported processors.",
            "A web server receives requests and returns responses.",
            "An AI training server can contain multiple GPUs connected by a high-speed interconnect.",
        ],

        "paragraphs": [
            (
                "A modern computing infrastructure can contain server CPUs, "
                "ECC DDR5 memory, NVMe storage, Linux, virtualization, "
                "containers, GPUs, high-bandwidth memory, and networking. "
                "Each layer provides a different responsibility. The "
                "application depends on the operating system and hardware "
                "while the infrastructure provides the resources required "
                "to execute the workload."
            ),
        ],
    },
}


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================

def detect_language(text: str) -> str:
    """
    Detect language with langdetect, then normalize through tokenizer.py.
    """

    if not text or not str(text).strip():
        return "en"

    try:
        detected = detect(
            str(text)
        )

        return normalize_lang(
            detected
        )

    except LangDetectException:
        return "en"

    except Exception:
        return "en"

# ============================================================================
# TEXT / ABBREVIATION HELPERS
# ============================================================================

_WORDLIKE_RE = re.compile(
    r"^[^\W\d_]+(?:[-'][^\W\d_]+)*$",
    flags=re.UNICODE,
)

_LATIN_ABBREVIATION_RE = re.compile(
    r"^[A-Z]{1,8}$"
)

_DOTTED_ABBREVIATION_RE = re.compile(
    r"^(?:[A-Za-z]\.){2,}$"
)


def _surface_word(
    token: Mapping[str, Any],
) -> str:

    return str(
        token.get(
            "original",
            token.get(
                "word",
                "",
            ),
        )
        or ""
    ).strip()


def _canonical_word(
    token: Mapping[str, Any],
) -> str:

    """
    tokenizer.py is authoritative.

    normalized = canonical lexical form.

    stem is preserved separately and is NOT used as the canonical
    spelling because the original normalized lexical identity must
    remain available.
    """

    return str(
        token.get(
            "normalized",
            "",
        )
        or ""
    ).strip().lower()


def _is_abbreviation(
    surface: str,
    canonical: str,
) -> bool:

    if not surface:
        return False

    if _DOTTED_ABBREVIATION_RE.match(
        surface
    ):
        return True

    if _LATIN_ABBREVIATION_RE.match(
        surface
    ):
        return canonical.isascii()

    return False


def _keep_abbreviation(
    surface: str,
    canonical: str,
    metadata: Mapping[str, Any],
) -> bool:

    # Explicit caller override.
    if metadata.get(
        "keep_abbreviations"
    ) is True:
        return True

    if canonical in CANONICAL_ABBREVIATIONS:
        return True

    if canonical in IRRELEVANT_ABBREVIATIONS:
        return False

    # DataFilter may have already recognized a code or technical term.
    if canonical in {
        str(x).lower()
        for x in (
            metadata.get(
                "code_terms",
                []
            )
            if isinstance(
                metadata.get(
                    "code_terms",
                    []
                ),
                list,
            )
            else []
        )
    }:
        return True

    # An explicitly recognized symbol/code/domain term survives.
    if metadata.get(
        "technical_term"
    ):
        return True

    if metadata.get(
        "code_term"
    ):
        return True

    # Unknown abbreviation: do not make it a canonical learning word.
    return False


def _is_valid_canonical_word(
    token: Mapping[str, Any],
    language: str,
    metadata: Mapping[str, Any],
) -> bool:

    canonical = _canonical_word(
        token
    )

    surface = _surface_word(
        token
    )

    if not canonical:
        return False

    # ------------------------------------------------------------
    # Pure symbol/numeric material does not become a canonical word.
    # ------------------------------------------------------------

    if not any(
        ch.isalpha()
        for ch in canonical
    ):
        return False

    # ------------------------------------------------------------
    # Abbreviations are explicitly controlled.
    # ------------------------------------------------------------

    if _is_abbreviation(
        surface,
        canonical,
    ):

        return _keep_abbreviation(
            surface,
            canonical,
            metadata,
        )

    # ------------------------------------------------------------
    # Non-word tokens should not become canonical words.
    # ------------------------------------------------------------

    if not _WORDLIKE_RE.match(
        canonical
    ):

        # Some writing systems do not behave like Latin words.
        # tokenizer.py has already established the lexical identity,
        # so allow such tokens when they contain alphabetic characters.
        if not any(
            ch.isalpha()
            for ch in canonical
        ):
            return False

    # ------------------------------------------------------------
    # Language-aware single-character handling.
    # ------------------------------------------------------------

    if len(canonical) == 1:

        # Never globally reject single-character lexical units.
        # Chinese/Japanese/Arabic/etc. may legitimately use them.
        if language in {
            "zh",
            "ja",
            "ko",
            "ar",
            "fa",
            "ur",
            "he",
            "th",
        }:
            return True

        # Latin single-letter tokens are generally not canonical words
        # unless explicitly marked by the source.
        if canonical not in {
            "a",
            "i",
        } and not metadata.get(
            "allow_single_letter"
        ):
            return False

    return True


# ============================================================================
# LANGUAGE STRUCTURE
# ============================================================================

def build_language_structure(
    text: str,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a language-neutral structural representation.

    This does NOT pretend to implement full grammatical parsing.

    It preserves the information needed for later linguistic learning:

        original order
        canonical lexical order
        surface forms
        stems
        punctuation
        token positions
        token count
        lexical count
        language
        script/character profile

    WordUnderstanding can later add deeper semantic/grammatical analysis.
    """

    lang = normalize_lang(
        language
        or detect_language(text)
    )

    tokens = tokenize(
        text,
        lang,
    )

    structures = []

    canonical_sequence = []
    surface_sequence = []

    punctuation = []

    for index, token in enumerate(
        tokens
    ):

        canonical = _canonical_word(
            token
        )

        surface = _surface_word(
            token
        )

        stem = str(
            token.get(
                "stem",
                "",
            )
            or ""
        ).strip().lower()

        canonical_sequence.append(
            canonical
        )

        surface_sequence.append(
            surface
        )

        symbols = token.get(
            "symbols",
            [],
        )

        if symbols:
            punctuation.extend(
                symbols
                if isinstance(
                    symbols,
                    list,
                )
                else [symbols]
            )

        structures.append({

            "position": index,

            "surface": surface,

            "canonical": canonical,

            "stem": stem,

            "uid": token.get(
                "uid"
            ),

            "uid_sequence": token.get(
                "uid_sequence",
                [],
            ),

            "L": token.get(
                "L",
                0,
            ),

            "S": token.get(
                "S",
                0,
            ),

            "SC": token.get(
                "SC",
                0,
            ),

            "word_grid": token.get(
                "word",
                {},
            ),

            "symbols": symbols,

        })

    return {

        "language": lang,

        "detected_language": lang,

        "text": text,

        "tokens": structures,

        "canonical_sequence": [
            x
            for x in canonical_sequence
            if x
        ],

        "surface_sequence": [
            x
            for x in surface_sequence
            if x
        ],

        "token_count": len(
            tokens
        ),

        "lexical_count": sum(
            1
            for token in structures
            if token["canonical"]
        ),

        "punctuation": punctuation,

        "structure": [
            token["canonical"]
            for token in structures
            if token["canonical"]
        ],

    }


# ============================================================================
# LEARNWORDS
# ============================================================================

class LearnWords:

    UNIT_TYPES = (
        "word",
        "phrase",
        "sentence",
        "paragraph",
    )

    def __init__(
        self,
        word_chain: Optional[WordChain] = None,
    ):

        self.word_chain = (
            word_chain
            if word_chain is not None
            else WordChain()
        )

        self.units = []

        self.word_index = defaultdict(
            list
        )

        self.phrase_index = defaultdict(
            list
        )

        self.sentence_index = defaultdict(
            list
        )

        self.paragraph_index = defaultdict(
            list
        )

        self.language_structures = defaultdict(
            list
        )

        self.statistics = Counter()

    # ========================================================================
    # TOKENIZER
    # ========================================================================

    def tokenize_unit(
        self,
        text: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:

        lang = normalize_lang(
            language
            or detect_language(text)
        )

        tokens = tokenize(
            text,
            lang,
        )

        return {

            "language": lang,

            "tokens": tokens,

            "structure": build_language_structure(
                text,
                lang,
            ),

        }

    # ========================================================================
    # CANONICAL WORD EXTRACTION
    # ========================================================================

    def canonical_words(
        self,
        text: str,
        language: Optional[str] = None,
        metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> List[Dict[str, Any]]:

        metadata = dict(
            metadata or {}
        )

        lang = normalize_lang(
            language
            or detect_language(text)
        )

        tokens = tokenize(
            text,
            lang,
        )

        result = []

        for position, token in enumerate(
            tokens
        ):

            canonical = _canonical_word(
                token
            )

            surface = _surface_word(
                token
            )

            if not _is_valid_canonical_word(
                token,
                lang,
                metadata,
            ):
                continue

            result.append({

                "position": position,

                "surface": surface,

                "canonical": canonical,

                "stem": str(
                    token.get(
                        "stem",
                        "",
                    )
                    or ""
                ).strip().lower(),

                "language": lang,

                "uid": token.get(
                    "uid"
                ),

                "uid_sequence": list(
                    token.get(
                        "uid_sequence",
                        [],
                    )
                    or []
                ),

                "L": token.get(
                    "L",
                    0,
                ),

                "S": token.get(
                    "S",
                    0,
                ),

                "SC": token.get(
                    "SC",
                    0,
                ),

                "word": token.get(
                    "word",
                    {},
                ),

                "symbols": token.get(
                    "symbols",
                    [],
                ),

            })

        return result

    # ========================================================================
    # BUILD UNIT
    # ========================================================================

    def build_unit(
        self,
        text: str,
        unit_type: str,
        record: Optional[
            Mapping[str, Any]
        ] = None,
        category: str = "general",
        language: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        if not text or not str(
            text
        ).strip():

            return None

        if unit_type not in self.UNIT_TYPES:
            raise ValueError(
                f"Unsupported learning unit: {unit_type}"
            )

        record = dict(
            record or {}
        )

        # ------------------------------------------------------------
        # Resolve language.
        # ------------------------------------------------------------

        lang = normalize_lang(
            language
            or record.get(
                "language"
            )
            or record.get(
                "lang"
            )
            or detect_language(
                text
            )
        )

        # ------------------------------------------------------------
        # TOKENIZER IS CALLED HERE.
        # ------------------------------------------------------------

        token_result = self.tokenize_unit(
            text,
            lang,
        )

        tokens = token_result[
            "tokens"
        ]

        # ------------------------------------------------------------
        # Canonical lexical layer.
        # ------------------------------------------------------------

        words = self.canonical_words(
            text,
            lang,
            record,
        )

        # ------------------------------------------------------------
        # A unit containing no usable lexical material is not learned.
        # ------------------------------------------------------------

        if not words:

            # For some scripts the tokenizer may legitimately provide
            # structural/symbolic material. Keep sentence/paragraph
            # structure only when there are actual tokenizer tokens.
            if not tokens:
                return None

        unit = {

            "text": str(
                text
            ).strip(),

            "unit_type": unit_type,

            "language": lang,

            "detected_language": lang,

            "category": category,

            "source": record.get(
                "source",
                "classic_learning",
            ),

            "source_factor": record.get(
                "source_factor",
                1.0,
            ),

            # --------------------------------------------------------
            # Canonical words.
            # --------------------------------------------------------

            "words": words,

            "canonical_words": [
                word[
                    "canonical"
                ]
                for word in words
            ],

            # --------------------------------------------------------
            # Full tokenizer output.
            # --------------------------------------------------------

            "tokens": tokens,

            # --------------------------------------------------------
            # Multilingual structure.
            # --------------------------------------------------------

            "language_structure": token_result[
                "structure"
            ],

            "structure": token_result[
                "structure"
            ][
                "structure"
            ],

            # --------------------------------------------------------
            # Context.
            # --------------------------------------------------------

            "domain": record.get(
                "domain",
                category,
            ),

            "intent": record.get(
                "intent"
            ),

            "question_type": record.get(
                "question_type"
            ),

            "directive": record.get(
                "directive"
            ),

            "project_id": record.get(
                "project_id"
            ),

            "project": record.get(
                "project"
            ),

            "project_trace": record.get(
                "project_trace"
            ),

            "project_pin": record.get(
                "project_pin"
            ),

            "project_iteration": record.get(
                "project_iteration"
            ),

            "project_context_aware": record.get(
                "project_context_aware"
            ),

            "metadata": record.get(
                "metadata",
                {},
            ),

        }

        # ------------------------------------------------------------
        # Index.
        # ------------------------------------------------------------

        self.units.append(
            unit
        )

        self.statistics[
            unit_type
        ] += 1

        self.statistics[
            f"language:{lang}"
        ] += 1

        self.statistics[
            f"category:{category}"
        ] += 1

        # ------------------------------------------------------------
        # Index canonical words.
        # ------------------------------------------------------------

        if unit_type == "word":

            for word in words:

                self.word_index[
                    word[
                        "canonical"
                    ]
                ].append(
                    unit
                )

        elif unit_type == "phrase":

            self.phrase_index[
                str(text).lower()
            ].append(
                unit
            )

        elif unit_type == "sentence":

            self.sentence_index[
                str(text).lower()
            ].append(
                unit
            )

        elif unit_type == "paragraph":

            self.paragraph_index[
                str(text).lower()
            ].append(
                unit
            )

        self.language_structures[
            lang
        ].append(
            unit[
                "language_structure"
            ]
        )

        return unit

    # ========================================================================
    # WORDCHAIN
    # ========================================================================

    def feed_word_chain(
        self,
        unit: Mapping[str, Any],
    ) -> Dict[str, Any]:

        text = unit.get(
            "text",
            "",
        )

        if not text:
            return {}

        source = unit.get(
            "source",
            "conversation",
        )

        # WordChain itself calls tokenizer.py again and performs its
        # language detection when language is supplied/omitted.
        #
        # We explicitly pass language so the language already resolved
        # by LearnWords is preserved.

        return self.word_chain.add_text(
            text=text,
            source=source,
            metadata={
                "unit_type": unit.get(
                    "unit_type"
                ),
                "category": unit.get(
                    "category"
                ),
                "domain": unit.get(
                    "domain"
                ),
                "language": unit.get(
                    "language"
                ),
                "project_id": unit.get(
                    "project_id"
                ),
                "project": unit.get(
                    "project"
                ),
                "project_trace": unit.get(
                    "project_trace"
                ),
            },
            language=unit.get(
                "language"
            ),
        )

    # ========================================================================
    # LEARN
    # ========================================================================

    def learn(
        self,
        text: str,
        unit_type: str = "sentence",
        record: Optional[
            Mapping[str, Any]
        ] = None,
        category: str = "general",
        language: Optional[str] = None,
        feed_chain: bool = True,
    ) -> Optional[Dict[str, Any]]:

        unit = self.build_unit(
            text=text,
            unit_type=unit_type,
            record=record,
            category=category,
            language=language,
        )

        if unit is None:
            return None

        if feed_chain:

            unit[
                "word_chain"
            ] = self.feed_word_chain(
                unit
            )

        return unit

    # ========================================================================
    # LEARN DATAFILTER RECORD
    # ========================================================================

    def learn_record(
        self,
        record: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:

        if not isinstance(
            record,
            Mapping,
        ):
            return []

        if record.get(
            "accepted",
            True,
        ) is False:

            return []

        text = str(
            record.get(
                "text",
                record.get(
                    "content",
                    record.get(
                        "data",
                        "",
                    ),
                ),
            )
            or ""
        ).strip()

        if not text:
            return []

        language = (
            record.get(
                "language"
            )
            or record.get(
                "lang"
            )
            or detect_language(
                text
            )
        )

        category = str(
            record.get(
                "domain",
                "general",
            )
            or "general"
        )

        unit_type = record.get(
            "unit_type"
        )

        if unit_type not in self.UNIT_TYPES:

            # DataFilter normally supplies text that represents a
            # sentence or paragraph. Preserve it as sentence material
            # unless explicitly identified otherwise.
            unit_type = (
                "paragraph"
                if len(
                    text.split()
                ) >= 30
                else "sentence"
            )

        unit = self.learn(
            text=text,
            unit_type=unit_type,
            record=record,
            category=category,
            language=language,
        )

        return (
            [unit]
            if unit
            else []
        )

    # ========================================================================
    # BATCH
    # ========================================================================

    def learn_records(
        self,
        records: Iterable[
            Mapping[str, Any]
        ],
    ) -> List[Dict[str, Any]]:

        results = []

        for record in records:

            results.extend(
                self.learn_record(
                    record
                )
            )

        return results

    # ========================================================================
    # CLASSIC CORPUS
    # ========================================================================

    def load_classic_samples(
        self,
        categories: Optional[
            Iterable[str]
        ] = None,
        language: str = "en",
    ) -> List[Dict[str, Any]]:

        if categories is None:

            selected = list(
                CLASSIC_LEARNING_BLOCKS.keys()
            )

        else:

            selected = [
                category
                for category in categories
                if category
                in CLASSIC_LEARNING_BLOCKS
            ]

        results = []

        for category in selected:

            block = CLASSIC_LEARNING_BLOCKS[
                category
            ]

            record = {

                "source": "classic_learning",

                "source_factor": 1.0,

                "language": language,

                "domain": category,

                "metadata": {
                    "learning_style": "classic",
                    "corpus": "foundational",
                    "category": category,
                },

            }

            for word in block.get(
                "words",
                [],
            ):

                unit = self.learn(
                    word,
                    "word",
                    record,
                    category,
                    language,
                )

                if unit:
                    results.append(unit)

            for phrase in block.get(
                "phrases",
                [],
            ):

                unit = self.learn(
                    phrase,
                    "phrase",
                    record,
                    category,
                    language,
                )

                if unit:
                    results.append(unit)

            for sentence in block.get(
                "sentences",
                [],
            ):

                unit = self.learn(
                    sentence,
                    "sentence",
                    record,
                    category,
                    language,
                )

                if unit:
                    results.append(unit)

            for paragraph in block.get(
                "paragraphs",
                [],
            ):

                unit = self.learn(
                    paragraph,
                    "paragraph",
                    record,
                    category,
                    language,
                )

                if unit:
                    results.append(unit)

        return results

    # ========================================================================
    # LOOKUPS
    # ========================================================================

    def find_word(
        self,
        word: str,
    ) -> List[Dict[str, Any]]:

        return list(
            self.word_index.get(
                str(word).strip().lower(),
                [],
            )
        )

    def find_phrase(
        self,
        phrase: str,
    ) -> List[Dict[str, Any]]:

        return list(
            self.phrase_index.get(
                str(phrase).strip().lower(),
                [],
            )
        )

    def find_sentence(
        self,
        sentence: str,
    ) -> List[Dict[str, Any]]:

        return list(
            self.sentence_index.get(
                str(sentence).strip().lower(),
                [],
            )
        )

    # ========================================================================
    # LANGUAGE PROFILE
    # ========================================================================

    def language_profile(
        self,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:

        if language:

            lang = normalize_lang(
                language
            )

            structures = (
                self.language_structures.get(
                    lang,
                    [],
                )
            )

            return {

                "language": lang,

                "units": len(
                    structures
                ),

                "tokens": sum(
                    item.get(
                        "token_count",
                        0,
                    )
                    for item in structures
                ),

                "lexical_tokens": sum(
                    item.get(
                        "lexical_count",
                        0,
                    )
                    for item in structures
                ),

            }

        return {

            lang: {
                "units": len(
                    structures
                ),
                "tokens": sum(
                    item.get(
                        "token_count",
                        0,
                    )
                    for item in structures
                ),
                "lexical_tokens": sum(
                    item.get(
                        "lexical_count",
                        0,
                    )
                    for item in structures
                ),
            }

            for lang, structures
            in self.language_structures.items()
        }

    # ========================================================================
    # SYSTEM PROFILE
    # ========================================================================

    def profile(self) -> Dict[str, Any]:

        return {

            "total_units": len(
                self.units
            ),

            "words": len(
                self.word_index
            ),

            "phrases": len(
                self.phrase_index
            ),

            "sentences": len(
                self.sentence_index
            ),

            "paragraphs": len(
                self.paragraph_index
            ),

            "languages": self.language_profile(),

            "statistics": dict(
                self.statistics
            ),

            "word_chain": {
                "words": sum(
                    self.word_chain.word_frequency.values()
                ),

                "pairs": sum(
                    self.word_chain.pairs.values()
                ),

                "languages": dict(
                    self.word_chain.language_statistics
                ),
            },

        }


# ============================================================================
# SIMPLE FACTORY
# ============================================================================

def create_learn_words(
    word_chain: Optional[
        WordChain
    ] = None,
    load_classic: bool = False,
) -> LearnWords:

    learner = LearnWords(
        word_chain=word_chain
    )

    if load_classic:

        learner.load_classic_samples()

    return learner


# ============================================================================
# SIMPLE BATCH HELPER
# ============================================================================

def learn_words(
    records: Iterable[
        Mapping[str, Any]
    ],
    word_chain: Optional[
        WordChain
    ] = None,
) -> List[Dict[str, Any]]:

    learner = LearnWords(
        word_chain=word_chain
    )

    return learner.learn_records(
        records
    )


__all__ = [
    "LearnWords",
    "CLASSIC_LEARNING_BLOCKS",
    "CANONICAL_ABBREVIATIONS",
    "IRRELEVANT_ABBREVIATIONS",
    "detect_language",
    "build_language_structure",
    "create_learn_words",
    "learn_words",
]