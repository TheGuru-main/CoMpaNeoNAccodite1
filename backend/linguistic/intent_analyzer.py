"""
CoMpaNeoN Intent Analyzer
=========================

Unified query-analysis authority.

This module combines:

    1. Domain detection
    2. Domain knowledge
    3. Entity recognition
    4. Country recognition
    5. State / region recognition
    6. People recognition
    7. Animal recognition
    8. Thing recognition
    9. Intent analysis

All downstream phases should import from this module.

Example:

    from intent_analyzer import analyze_intent

    result = analyze_intent(
        "Explain Python programming in Nigeria"
    )

The returned object becomes shared metadata for:

    WordUnderstanding
    WordChain
    CrawlerRetrieval
    WebCrawler
    DataMixer
    PromptManager
    Memory
    Response generation
"""


from __future__ import annotations

import re

from typing import Any, Dict, List


# ============================================================================
# DOMAIN KEYWORDS
# ============================================================================

DOMAIN_KEYWORDS: Dict[str, List[str]] = {

    "code": [
        "def",
        "class",
        "import",
        "function",
        "return",
        "if",
        "else",
        "loop",
        "variable",
        "algorithm",
        "debug",
        "compiler",
        "library",
        "api",
        "database",
        "framework",
        "python",
        "javascript",
        "java",
        "c++",
        "c#",
        "ruby",
        "php",
        "sql",
        "html",
        "css",
        "python_rules",
        "fix_my_code",
        "debug",
    ],

    "medical": [
        "diagnosis",
        "treatment",
        "symptom",
        "surgery",
        "disease",
        "patient",
        "clinical",
        "pharmacy",
        "drug",
    ],

    "legal": [
        "law",
        "court",
        "attorney",
        "legal",
        "statute",
        "regulation",
        "compliance",
        "lawsuit",
        "judge",
    ],

    "education": [
        "homework",
        "explain",
        "definition",
        "learn",
        "teach",
        "curriculum",
        "classroom",
        "student",
        "school",
    ],

    "sports": [
        "football",
        "basketball",
        "tennis",
        "goal",
        "match",
        "tournament",
        "player",
        "league",
        "championship",
    ],

    "business": [
        "stock",
        "revenue",
        "profit",
        "market",
        "economy",
        "investment",
        "trade",
        "finance",
        "entrepreneur",
    ],

    "agriculture": [
        "crop",
        "farm",
        "harvest",
        "soil",
        "livestock",
        "fertilizer",
        "agriculture",
        "irrigation",
        "poultry",
    ],

    "technology": [
        "code",
        "software",
        "ai",
        "blockchain",
        "server",
        "api",
        "programming",
        "app",
        "cloud",
    ],

    "religious": [
        "prayer",
        "quran",
        "bible",
        "allah",
        "god",
        "surah",
        "zakat",
        "church",
        "mosque",
    ],

    "news": [
        "breaking",
        "headlines",
        "latest",
        "report",
        "update",
        "today",
        "journal",
        "news",
    ],
}


# ============================================================================
# DOMAIN KNOWLEDGE — COUNTRIES
# ============================================================================

COUNTRIES: Dict[str, str] = {

    "NG": "Nigeria",
    "GH": "Ghana",
    "US": "United States",
    "IN": "India",
    "GB": "United Kingdom",
    "FR": "France",
    "DE": "Germany",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "ZA": "South Africa",
    "KE": "Kenya",
    "TZ": "Tanzania",
    "UG": "Uganda",
    "EG": "Egypt",
    "MA": "Morocco",
    "DZ": "Algeria",
    "SN": "Senegal",
    "CI": "Ivory Coast",
    "CM": "Cameroon",
    "ET": "Ethiopia",
    "RW": "Rwanda",
    "SD": "Sudan",
    "SS": "South Sudan",
    "AO": "Angola",
    "MZ": "Mozambique",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
    "BW": "Botswana",
    "MW": "Malawi",
    "NA": "Namibia",
    "LS": "Lesotho",
    "SZ": "Eswatini",
    "CD": "Democratic Republic of the Congo",
    "CG": "Republic of the Congo",
    "GA": "Gabon",
    "BJ": "Benin",
    "TG": "Togo",
    "BF": "Burkina Faso",
    "ML": "Mali",
    "NE": "Niger",
    "TD": "Chad",
    "MR": "Mauritania",
    "LY": "Libya",
    "TN": "Tunisia",
    "ER": "Eritrea",
    "DJ": "Djibouti",
    "SO": "Somalia",
    "KM": "Comoros",
    "MG": "Madagascar",
    "SC": "Seychelles",
    "MU": "Mauritius",
    "CV": "Cape Verde",
    "ST": "São Tomé and Príncipe",
    "GQ": "Equatorial Guinea",
    "GW": "Guinea-Bissau",
    "GN": "Guinea",
    "LR": "Liberia",
    "SL": "Sierra Leone",
    "GM": "Gambia",
}


# ============================================================================
# STATES / REGIONS
# ============================================================================

STATES_BY_COUNTRY: Dict[str, List[str]] = {

    "NG": [
        "Lagos",
        "Abuja",
        "Rivers",
        "Kano",
        "Oyo",
        "Ogun",
        "Enugu",
        "Anambra",
        "Kaduna",
        "Delta",
        "Edo",
        "Benue",
        "Kwara",
        "Ondo",
        "Ekiti",
        "Osun",
        "Bauchi",
        "Gombe",
        "Jigawa",
        "Katsina",
        "Kebbi",
        "Niger",
        "Plateau",
        "Sokoto",
        "Taraba",
        "Yobe",
        "Zamfara",
    ],

    "GH": [
        "Greater Accra",
        "Ashanti",
        "Western",
        "Eastern",
        "Central",
        "Volta",
        "Northern",
        "Upper East",
        "Upper West",
        "Bono",
        "Bono East",
        "Ahafo",
        "Savannah",
        "North East",
        "Oti",
    ],

    "KE": [
        "Nairobi",
        "Mombasa",
        "Kisumu",
        "Nakuru",
        "Uasin Gishu",
        "Kiambu",
        "Kajiado",
        "Machakos",
        "Meru",
        "Nyeri",
    ],

    "TZ": [
        "Dar es Salaam",
        "Dodoma",
        "Arusha",
        "Mwanza",
        "Mbeya",
        "Morogoro",
        "Tanga",
        "Kigoma",
        "Tabora",
        "Zanzibar Urban/West",
    ],

    "UG": [
        "Kampala",
        "Wakiso",
        "Mbarara",
        "Gulu",
        "Jinja",
        "Mbale",
        "Masaka",
        "Fort Portal",
        "Arua",
        "Lira",
    ],

    "ZA": [
        "Gauteng",
        "Western Cape",
        "KwaZulu-Natal",
        "Eastern Cape",
        "Free State",
        "Limpopo",
        "Mpumalanga",
        "North West",
        "Northern Cape",
    ],

    "EG": [
        "Cairo",
        "Alexandria",
        "Giza",
        "Luxor",
        "Aswan",
        "Asyut",
        "Beheira",
        "Dakahlia",
        "Gharbia",
        "Minya",
    ],

    "MA": [
        "Casablanca-Settat",
        "Rabat-Salé-Kénitra",
        "Marrakech-Safi",
        "Fès-Meknès",
        "Tangier-Tétouan-Al Hoceïma",
        "Oriental",
        "Béni Mellal-Khénifra",
        "Drâa-Tafilalet",
        "Souss-Massa",
        "Guelmim-Oued Noun",
    ],

    "DZ": [
        "Algiers",
        "Oran",
        "Constantine",
        "Annaba",
        "Blida",
        "Batna",
        "Sétif",
        "Tlemcen",
        "Béjaïa",
        "Tizi Ouzou",
    ],

    "SN": [
        "Dakar",
        "Thiès",
        "Saint-Louis",
        "Ziguinchor",
        "Kaolack",
        "Louga",
        "Tambacounda",
        "Kolda",
        "Matam",
        "Fatick",
    ],

    "CI": [
        "Abidjan",
        "Yamoussoukro",
        "Bouaké",
        "San-Pédro",
        "Daloa",
        "Korhogo",
        "Man",
        "Gagnoa",
        "Divo",
        "Abengourou",
    ],

    "CM": [
        "Centre",
        "Littoral",
        "West",
        "North",
        "Far North",
        "East",
        "South",
        "Adamawa",
        "Northwest",
        "Southwest",
    ],

    "ET": [
        "Addis Ababa",
        "Oromia",
        "Amhara",
        "Tigray",
        "Somali",
        "Afar",
        "Benishangul-Gumuz",
        "Gambela",
        "Harari",
        "SNNPR",
    ],

    "RW": [
        "Kigali",
        "Eastern",
        "Western",
        "Northern",
        "Southern",
    ],

    "SD": [
        "Khartoum",
        "Omdurman",
        "North Kordofan",
        "South Kordofan",
        "Darfur",
        "Red Sea",
        "River Nile",
        "Gezira",
        "Kassala",
    ],

    "SS": [
        "Central Equatoria",
        "Eastern Equatoria",
        "Western Equatoria",
        "Jonglei",
        "Upper Nile",
        "Unity",
        "Lakes",
        "Warrap",
        "Northern Bahr el Ghazal",
        "Western Bahr el Ghazal",
    ],

    "AO": [
        "Luanda",
        "Benguela",
        "Huambo",
        "Lubango",
        "Malanje",
        "Cabinda",
        "Uíge",
        "Namibe",
        "Cunene",
        "Moxico",
    ],

    "MZ": [
        "Maputo",
        "Sofala",
        "Zambezia",
        "Nampula",
        "Tete",
        "Manica",
        "Gaza",
        "Inhambane",
        "Cabo Delgado",
        "Niassa",
    ],

    "ZM": [
        "Lusaka",
        "Copperbelt",
        "Central",
        "Eastern",
        "Luapula",
        "Muchinga",
        "Northern",
        "North-Western",
        "Southern",
        "Western",
    ],

    "ZW": [
        "Harare",
        "Bulawayo",
        "Manicaland",
        "Mashonaland Central",
        "Mashonaland East",
        "Mashonaland West",
        "Masvingo",
        "Matabeleland North",
        "Matabeleland South",
        "Midlands",
    ],
}


# ============================================================================
# GENERAL ENTITY KNOWLEDGE
# ============================================================================

PEOPLE_NAMES = [
    "Idris Akeem",
    "Chinedu Okafor",
    "Amina Bello",
    "John Smith",
    "Fatima Yusuf",
    "Emeka Obi",
    "Grace Adeyemi",
    "Musa Ibrahim",
    "Ngozi Eze",
    "David Johnson",
    "Maryam Abubakar",
    "Tunde Bakare",
    "Kwame Mensah",
    "Ama Serwaa",
    "Jean-Pierre Dubois",
    "Sophie Martin",
    "Ahmed Hassan",
    "Layla Ali",
    "Raj Patel",
    "Priya Sharma",
    "Li Wei",
    "Zhang Min",
    "Carlos Mendoza",
    "Isabella García",
    "Omar Farouk",
    "Nadia Khaled",
    "Thabo Mbeki",
    "Lindiwe Zulu",
    "Samuel Okonkwo",
    "Esther Adeleke",
]


ANIMALS = [
    "dog",
    "cat",
    "lion",
    "tiger",
    "elephant",
    "goat",
    "sheep",
    "cow",
    "horse",
    "chicken",
    "fish",
    "snake",
    "monkey",
    "eagle",
    "parrot",
    "camel",
    "rabbit",
    "crocodile",
    "hippopotamus",
    "giraffe",
    "zebra",
    "antelope",
    "leopard",
    "cheetah",
    "hyena",
    "jackal",
    "warthog",
    "buffalo",
    "rhinoceros",
    "gorilla",
    "chimpanzee",
    "baboon",
    "ostrich",
    "flamingo",
    "pelican",
    "duck",
    "goose",
    "turkey",
    "pig",
    "donkey",
    "mule",
]


THINGS = [
    "phone",
    "computer",
    "car",
    "bicycle",
    "television",
    "radio",
    "chair",
    "table",
    "book",
    "pen",
    "shoe",
    "shirt",
    "laptop",
    "camera",
    "refrigerator",
    "air conditioner",
    "fan",
    "watch",
    "microwave",
    "blender",
    "kettle",
    "iron",
    "washing machine",
    "stove",
    "oven",
    "toaster",
    "vacuum cleaner",
    "hair dryer",
    "electric fan",
    "generator",
    "solar panel",
    "battery",
    "light bulb",
    "door",
    "window",
    "mirror",
    "clock",
    "calendar",
]


# ============================================================================
# DOMAIN DETECTION
# ============================================================================

def detect_domain(query: str) -> str:
    """
    Detect the primary domain of a query.

    This remains available for backwards compatibility.

    New code should preferably use analyze_intent().
    """

    q = query.lower()

    scores: Dict[str, int] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            # Exact-ish word matching prevents words such as
            # "classical" from accidentally matching "class".

            if re.search(
                rf"(?<!\w){re.escape(keyword.lower())}(?!\w)",
                q,
            ):
                score += 1

        if score:
            scores[domain] = score

    if not scores:
        return "general"

    return max(
        scores,
        key=scores.get,
    )


# ============================================================================
# DOMAIN KEYWORD MATCHES
# ============================================================================

def detect_domain_matches(
    query: str,
) -> Dict[str, List[str]]:
    """
    Return the actual domain keywords found in the query.
    """

    q = query.lower()

    matches: Dict[str, List[str]] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():

        found = []

        for keyword in keywords:

            if re.search(
                rf"(?<!\w){re.escape(keyword.lower())}(?!\w)",
                q,
            ):
                found.append(keyword)

        if found:
            matches[domain] = found

    return matches


# ============================================================================
# ENTITY HELPERS
# ============================================================================

def get_domain_entities(
    domain: str,
) -> List[str]:
    """
    Return domain-specific entities.
    """

    domain_lower = domain.lower()

    if domain_lower == "country":
        return list(COUNTRIES.values())

    if domain_lower == "state":
        states: List[str] = []

        for country_states in STATES_BY_COUNTRY.values():
            states.extend(country_states)

        return states

    if domain_lower == "people":
        return PEOPLE_NAMES

    if domain_lower == "animal":
        return ANIMALS

    if domain_lower == "thing":
        return THINGS

    return []


def _find_entities(
    query: str,
    entities: List[str],
) -> List[str]:
    """
    Find known entities appearing in a query.

    Longest entities are checked first so that:

        United States

    wins over:

        States
    """

    query_lower = query.lower()

    found = []

    for entity in sorted(
        entities,
        key=len,
        reverse=True,
    ):

        if re.search(
            rf"(?<!\w){re.escape(entity.lower())}(?!\w)",
            query_lower,
        ):
            found.append(entity)

    return found


# ============================================================================
# ENTITY ANALYSIS
# ============================================================================

def detect_entities(
    query: str,
) -> Dict[str, List[str]]:
    """
    Detect known entities across the domain knowledge registry.
    """

    states: List[str] = []

    for country_states in STATES_BY_COUNTRY.values():
        states.extend(country_states)

    return {
        "countries": _find_entities(
            query,
            list(COUNTRIES.values()),
        ),

        "states": _find_entities(
            query,
            states,
        ),

        "people": _find_entities(
            query,
            PEOPLE_NAMES,
        ),

        "animals": _find_entities(
            query,
            ANIMALS,
        ),

        "things": _find_entities(
            query,
            THINGS,
        ),
    }


# ============================================================================
# INTENT TYPE
# ============================================================================

INTENT_PATTERNS: Dict[str, List[str]] = {

    "question": [
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "which",
        "can you",
        "could you",
        "is there",
        "are there",
    ],

    "explanation": [
        "explain",
        "describe",
        "meaning",
        "definition",
        "what does",
        "what is",
    ],

    "instruction": [
        "how do i",
        "how can i",
        "show me",
        "teach me",
        "guide me",
        "steps",
    ],

    "code_generation": [
        "write code",
        "generate code",
        "create code",
        "build this",
        "implement this",
        "code this",
    ],

    "debugging": [
        "debug",
        "fix this",
        "error",
        "exception",
        "not working",
        "bug",
    ],

    "comparison": [
        "compare",
        "difference",
        "versus",
        "vs",
        "better than",
    ],

    "planning": [
        "plan",
        "roadmap",
        "strategy",
        "schedule",
        "design",
        "architecture",
    ],

    "summarization": [
        "summarize",
        "summary",
        "summarise",
        "shorten",
        "key points",
    ],
}


def detect_intent_type(
    query: str,
) -> str:
    """
    Determine the primary request intent.
    """

    q = query.lower()

    scores: Dict[str, int] = {}

    for intent, patterns in INTENT_PATTERNS.items():

        score = 0

        for pattern in patterns:

            if pattern in q:
                score += 1

        if score:
            scores[intent] = score

    if not scores:
        return "general"

    return max(
        scores,
        key=scores.get,
    )


# ============================================================================
# ANALYZE INTENT
# ============================================================================

def analyze_intent(
    query: str,
    language: str = "en",
) -> Dict[str, Any]:
    """
    Produce the unified query-analysis object.

    This is the main entry point for downstream architecture.

    The function does not retrieve memory, crawl the web, rank
    documents, or generate a response.

    It only establishes what the query is about and what entities
    it contains.
    """

    query = query.strip()

    domain = detect_domain(
        query
    )

    domain_matches = detect_domain_matches(
        query
    )

    entities = detect_entities(
        query
    )

    intent_type = detect_intent_type(
        query
    )

    return {
        "query": query,

        "language": language,

        "domain": domain,

        "domain_matches": domain_matches,

        "intent": intent_type,

        "entities": entities,

        "entity_counts": {
            key: len(value)
            for key, value in entities.items()
        },

        "has_entities": any(
            bool(value)
            for value in entities.values()
        ),

        "domain_entities": get_domain_entities(
            domain
        ),
    }


# ============================================================================
# COMPATIBILITY ALIAS
# ============================================================================

analyze = analyze_intent