RULES = {
    "professionalism": True,
    "no_contradiction": True,
    "respect_punctuation": True,
    "temperament_aware": True,
    "max_output_words": 5000,
    "max_paragraphs": 30,
    "no_hallucination": True,
    "no_secret_leaking": True,
    "direct_answers": True,
    "respect_idioms_disjunctions": True,
    "always_remember": True,
    "be_collaborative": True,
    "expose_root_code": False,
    "structured_vocabulary": True,
    "supportive": True,
    "track_workflow": True,
    "be_iterative": True,
    "honor_the_user_request": True,
    "procastination": False,
    "understand_intent_before_answering": True,
    "bias": False,
    "criminal_and_cyber_theft_support": False,
    "religious_view": "Islam",
    "political_view": None,
    "Name": "CoMpaNeoNAI",
}

# Patterns that indicate hallucination or placeholder text
HALLUCINATION_PATTERNS = [
    "i don't know",
    "i am not sure",
    "to be honest",
    "as an ai",
    "i cannot provide",
    "i am unable",
    "i apologize",
    "i'm sorry, but",
    "i cannot answer",
    "i have no information",
    "i do not have",
]

# Patterns that may indicate secret leaking
SECRET_PATTERNS = [
    "A###@@@55019655199##@@@",
    "K#3$550198110189&26012002#",
    "E#2$560198110199&27012001#",
    "D#2$550198111199&26012001#",
    "J#2$550298111129&26912001#",
    "C#2$950128111199&26012001#",
    "B#2$550108111199&26012201#",
    "api key",
    "secret key",
    "password",
    "token",
    "access key",
]

def enforce_rules(text: str, temperament: str = "sanguine") -> bool:
    """
    Enforce AI guidelines.
    Returns True if text passes all rules, False otherwise.
    """
    # Check word count
    words = len(text.split())
    if words > RULES["max_output_words"]:
        return False

    # Check hallucination patterns
    lower_text = text.lower()
    if RULES["no_hallucination"]:
        for pattern in HALLUCINATION_PATTERNS:
            if pattern in lower_text and words < 5:
                return False

    # Check secret leaking
    if RULES["no_secret_leaking"]:
        for pattern in SECRET_PATTERNS:
            if pattern in lower_text:
                return False

    # Check directness: reject if text starts with hedging phrases
    if RULES["direct_answers"]:
        if lower_text.startswith(("i think", "maybe", "perhaps", "i'm not sure, but..." , "this might get blocked!!!" , "this has been restricted")):
            return False

    # Ensure respect for idiomatic expressions and disjunctions
    # (This is more about training data; but we can do a basic check:
    # no rule applied here for simplicity, but the flag is set)
    return True