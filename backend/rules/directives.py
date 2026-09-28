"""
Directive vocabulary: question words and what they retrieve.
Used in query analysis to focus the grid crawler.
"""

DIRECTIVES = {
    "who": "entity_identity",
    "what": "definition_object",
    "where": "location",
    "when": "time",
    "why": "cause_purpose",
    "how": "method_process",
    "which": "selection_comparison",
    "whose": "ownership",
    "whom": "relationship_recipient",
    "how many": "quantity_count",
    "how much": "value_price",
    "how long": "duration",
    "how far": "distance",
    "how often": "frequency",
    "what kind of": "classification",
    "is": "verification",
    "are": "verification",
    "can": "capability",
    "does": "behaviour",
    "do": "behaviour",
    "did": "historical_action",
    "will": "scheduled_action",
    "and": "composition_multi_query",
    "or": "alternative",
    "not": "exclusion",
}

def detect_directive(query: str) -> str:
    q = query.lower().strip()
    # Check multi-word directives first
    for phrase, intent in sorted(DIRECTIVES.items(), key=lambda x: len(x[0]), reverse=True):
        if q.startswith(phrase + " ") or q.startswith(phrase):
            return intent
    return "general"