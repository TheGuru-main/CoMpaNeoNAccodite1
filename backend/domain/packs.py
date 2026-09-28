"""
CoMpaNeoN Domain Rules
======================

Domain-specific knowledge and rule metadata.

This module extends the existing rules.py rather than replacing it.

rules.py
    ↓
global AI rules / response safety
    ↓
domain_rules.py
    ↓
domain-specific rules
    ↓
WordUnderstanding / Brain
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from .rules import RULES, enforce_rules
except ImportError:
    from rules import RULES, enforce_rules


# ---------------------------------------------------------------------------
# DOMAIN REGISTRY
# ---------------------------------------------------------------------------

DOMAIN_RULES: Dict[str, Dict[str, Any]] = {

    # -----------------------------------------------------------------------
    # IDIOMS
    # -----------------------------------------------------------------------

    "idioms": {
        "name": "Idioms",
        "type": "language",
        "requires_context": True,
        "literal_interpretation": False,
        "preserve_expression": True,
        "rules": [
            "Do not automatically interpret an idiom literally.",
            "Preserve the original expression.",
            "Use surrounding context to determine intended meaning.",
            "Distinguish idiomatic meaning from literal meaning.",
        ],
    },

    # -----------------------------------------------------------------------
    # PARABLES
    # -----------------------------------------------------------------------

    "parables": {
        "name": "Parables",
        "type": "narrative",
        "requires_context": True,
        "rules": [
            "Preserve the narrative structure.",
            "Distinguish story events from the lesson or principle.",
            "Do not invent a moral that is absent from the source.",
            "Keep source attribution when a source is available.",
        ],
    },

    # -----------------------------------------------------------------------
    # ISLAMIC BASIC UNDERSTANDING
    # -----------------------------------------------------------------------

    "islamic_basic": {
        "name": "Islamic Basic Understanding",
        "type": "religious",
        "tradition": "Islam",
        "requires_source_context": True,
        "rules": [
            "Distinguish established teachings from interpretation.",
            "Preserve Qur'an and Hadith source references when available.",
            "Do not present an uncertain interpretation as an established ruling.",
            "Distinguish religious teaching from cultural practice.",
        ],
    },

    # -----------------------------------------------------------------------
    # SHARIAH / ISLAMIC LAW
    # -----------------------------------------------------------------------

    "shariah": {
        "name": "Shariah",
        "type": "religious_law",
        "requires_source": True,
        "requires_context": True,
        "requires_authority": True,
        "rules": [
            "Identify the relevant legal question.",
            "Identify the source or authority.",
            "Distinguish Qur'an, Sunnah, scholarly interpretation and local law.",
            "Preserve differences between recognized scholarly positions.",
            "Do not present an unsupported conclusion as a definitive fatwa.",
            "Record uncertainty when the evidence does not establish one conclusion.",
        ],
    },

    # -----------------------------------------------------------------------
    # BUSINESS
    # -----------------------------------------------------------------------

    "business": {
        "name": "Business",
        "type": "business",
        "rules": [
            "Identify the business concept before applying a rule.",
            "Distinguish business practice from legal obligation.",
            "Preserve contractual conditions.",
            "Consider jurisdiction when a rule has legal consequences.",
            "Distinguish strategy, convention and enforceable requirement.",
        ],
    },

    # -----------------------------------------------------------------------
    # CODING
    # -----------------------------------------------------------------------

    "coding": {
        "name": "Coding",
        "type": "technical",
        "rules": [
            "Identify the programming language or framework.",
            "Identify the relevant version when known.",
            "Preserve syntax rules.",
            "Distinguish language rules from framework conventions.",
            "Distinguish compile-time errors from runtime errors.",
            "Do not invent APIs or library behavior.",
        ],
    },

    # -----------------------------------------------------------------------
    # LAW
    # -----------------------------------------------------------------------

    "law": {
        "name": "Legal Research",
        "type": "law",
        "requires_jurisdiction": True,
        "requires_source": True,
        "requires_date_context": True,
        "rules": [
            "Identify jurisdiction.",
            "Identify the relevant legal authority.",
            "Identify the applicable date/version.",
            "Prefer primary legal sources where available.",
            "Distinguish statute, regulation, case law and commentary.",
            "Distinguish researched law from general explanation.",
            "Do not manufacture citations.",
        ],
    },

    # -----------------------------------------------------------------------
    # MEDICINE
    # -----------------------------------------------------------------------

    "medical": {
        "name": "Medical",
        "type": "medicine",
        "requires_context": True,
        "requires_source": True,
        "rules": [
            "Distinguish medical information from diagnosis.",
            "Preserve uncertainty where evidence is incomplete.",
            "Identify relevant clinical context.",
            "Prefer authoritative medical sources.",
            "Do not invent clinical guidelines.",
            "Distinguish general medical information from patient-specific advice.",
        ],
    },
}


# ---------------------------------------------------------------------------
# DOMAIN ALIASES
# ---------------------------------------------------------------------------

DOMAIN_ALIASES = {
    "islam": "islamic_basic",
    "islamic": "islamic_basic",
    "religion": "islamic_basic",
    "sharia": "shariah",
    "shariah_law": "shariah",
    "legal": "law",
    "law_research": "law",
    "programming": "coding",
    "software": "coding",
    "medicine": "medical",
    "health": "medical",
    "healthcare": "medical",
}


# ---------------------------------------------------------------------------
# DOMAIN RESOLUTION
# ---------------------------------------------------------------------------

def normalize_domain(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None

    value = str(domain).strip().lower()

    if value in DOMAIN_RULES:
        return value

    return DOMAIN_ALIASES.get(value, value)


def get_domain_rules(
    domain: Optional[str],
) -> Dict[str, Any]:
    domain = normalize_domain(domain)

    if not domain:
        return {}

    return DOMAIN_RULES.get(
        domain,
        {},
    )


# ---------------------------------------------------------------------------
# REQUIRED CONTEXT
# ---------------------------------------------------------------------------

def required_context(
    domain: Optional[str],
) -> Dict[str, Any]:

    rules = get_domain_rules(domain)

    return {
        "domain": normalize_domain(domain),
        "requires_source": bool(
            rules.get("requires_source", False)
        ),
        "requires_authority": bool(
            rules.get("requires_authority", False)
        ),
        "requires_jurisdiction": bool(
            rules.get("requires_jurisdiction", False)
        ),
        "requires_date_context": bool(
            rules.get("requires_date_context", False)
        ),
        "requires_context": bool(
            rules.get("requires_context", False)
        ),
    }


# ---------------------------------------------------------------------------
# RULE EXTRACTION
# ---------------------------------------------------------------------------

def applicable_rules(
    domain: Optional[str],
) -> List[str]:

    rules = get_domain_rules(domain)

    return list(
        rules.get("rules", [])
    )


# ---------------------------------------------------------------------------
# BUILD DOMAIN CONTEXT
# ---------------------------------------------------------------------------

def build_domain_context(
    domain: Optional[str],
    source: Optional[str] = None,
    authority: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    date_context: Optional[str] = None,
) -> Dict[str, Any]:

    normalized = normalize_domain(domain)

    return {
        "domain": normalized,
        "rules": applicable_rules(
            normalized
        ),
        "requirements": required_context(
            normalized
        ),
        "source": source,
        "authority": authority,
        "jurisdiction": jurisdiction,
        "date_context": date_context,
        "global_rules": RULES,
    }


# ---------------------------------------------------------------------------
# OUTPUT VALIDATION
# ---------------------------------------------------------------------------

def validate_domain_output(
    text: str,
    domain: Optional[str],
    temperament: str = "sanguine",
) -> Dict[str, Any]:

    global_pass = enforce_rules(
        text,
        temperament,
    )

    normalized = normalize_domain(
        domain
    )

    domain_info = get_domain_rules(
        normalized
    )

    return {
        "valid": global_pass,
        "domain": normalized,
        "domain_name": domain_info.get(
            "name"
        ),
        "requirements": required_context(
            normalized
        ),
    }


__all__ = [
    "DOMAIN_RULES",
    "DOMAIN_ALIASES",
    "normalize_domain",
    "get_domain_rules",
    "required_context",
    "applicable_rules",
    "build_domain_context",
    "validate_domain_output",
]