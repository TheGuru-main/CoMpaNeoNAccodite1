"""
Follow-up Questions Module
==========================

CoMpaNeoN post-response continuity layer.

Responsibilities:
    - Understand the user's query and AI answer.
    - Feed conversational language into WordChain.
    - Preserve word and phrase continuity.
    - Generate deterministic contextual follow-up questions.
    - Return a structured interaction event for the memory layer.
    - Support ProjectTraceMemoryLayer without owning STM/LTM routing.

Architecture:

    User Query
        ↓
    WordUnderstanding
        ↓
    WordChain
        ↓
    AI Response
        ↓
    FollowUp
        ↓
    ProjectTraceMemoryLayer
        ↓
    MemoryGrid / PSTM / LTM

Important:

FollowUp does NOT:
    - generate the primary AI response
    - perform model inference
    - replace ranking.py
    - replace word_chain.py
    - replace word_understanding.py
    - own MemoryGrid placement
    - own GSP-XOR relevancy sharding
    - decide final STM/LTM storage
"""

from __future__ import annotations

import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from intent_analyzer import detect_domain
from symbols import recognize_symbols

from word_chain import (
    WordChain,
    clean_words,
)

from word_understanding import (
    WordUnderstanding,
)

from memory_grid import MemoryGrid


# ---------------------------------------------------------------------------
# STOP WORDS
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "of", "in", "on", "at", "by", "for", "with",
    "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "out", "off", "over",
    "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than",
    "too", "very", "s", "t", "just", "don", "now",
    "i", "me", "my", "we", "our", "ours", "you",
    "your", "yours", "he", "him", "his", "she",
    "her", "hers", "it", "its", "they", "them",
    "their", "theirs", "what", "which", "who",
    "whom", "this", "that", "these", "those",
}


# ---------------------------------------------------------------------------
# KEYWORD EXTRACTION
# ---------------------------------------------------------------------------

def extract_keywords(
    text: str,
    top_n: int = 5,
) -> List[str]:
    """
    Extract deterministic keywords.

    WordChain remains responsible for word relationships.
    This helper only identifies useful lexical subjects for
    follow-up question construction.
    """

    words = re.findall(
        r"[a-zA-Z0-9_]+",
        str(text).lower(),
    )

    filtered = [
        word
        for word in words
        if (
            word not in STOP_WORDS
            and len(word) > 2
        )
    ]

    frequency: Dict[str, int] = {}

    for word in filtered:
        frequency[word] = (
            frequency.get(word, 0) + 1
        )

    ranked = sorted(
        frequency.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    return [
        word
        for word, _ in ranked[:top_n]
    ]


# ---------------------------------------------------------------------------
# WORD PAIRS
# ---------------------------------------------------------------------------

def extract_word_pairs(
    text: str,
) -> List[str]:
    """
    Compatibility helper.

    WordChain is the authoritative relationship engine,
    but this helper remains available for existing callers.
    """

    words = clean_words(text)

    return [
        f"{words[index]}_{words[index + 1]}"
        for index in range(
            len(words) - 1
        )
    ]


# ---------------------------------------------------------------------------
# NEXT-WORD CANDIDATES
# ---------------------------------------------------------------------------

def extract_next_word_candidates(
    text: str,
    limit: int = 5,
    word_chain: Optional[WordChain] = None,
) -> List[Dict[str, Any]]:
    """
    Return continuation candidates using WordChain.

    If no persistent WordChain is supplied, a temporary chain is
    created for compatibility with the previous implementation.
    """

    chain = (
        word_chain
        if word_chain is not None
        else WordChain()
    )

    if word_chain is None:
        chain.add_text(
            text,
            source="conversation",
        )

    return chain.predict_from_text(
        text,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# FOLLOW-UP ENGINE
# ---------------------------------------------------------------------------

class FollowUp:
    """
    CoMpaNeoN follow-up and post-response continuity engine.

    The engine can operate with:

        WordChain
        WordUnderstanding
        MemoryGrid

    independently or together.
    """

    def __init__(
        self,
        word_chain: Optional[WordChain] = None,
        word_understanding: Optional[
            WordUnderstanding
        ] = None,
        memory_grid: Optional[MemoryGrid] = None,
    ):
        self.word_chain = (
            word_chain
            if word_chain is not None
            else WordChain()
        )

        self.word_understanding = (
            word_understanding
        )

        self.memory = memory_grid

    # ==================================================================
    # UNDERSTAND INTERACTION
    # ==================================================================

    def understand_interaction(
        self,
        query: str,
        answer: str,
        lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Understand the interaction before it is sent to
        the project-trace memory layer.
        """

        domain = detect_domain(
            query
        )

        understanding = None

        if self.word_understanding is not None:

            understanding = (
                self.word_understanding.understand(
                    query,
                    lang=lang,
                )
            )

        return {
            "query": query,
            "answer": answer,
            "language": lang,
            "domain": domain,
            "understanding": understanding,
        }

    # ==================================================================
    # ADD INTERACTION TO WORDCHAIN
    # ==================================================================

    def learn_interaction(
        self,
        query: str,
        answer: str,
        source: str = "conversation",
    ) -> Dict[str, Any]:
        """
        Feed both sides of the interaction into WordChain.

        Query and answer are deliberately ingested separately so their
        linguistic provenance remains distinguishable.
        """

        query_result = self.word_chain.add_text(
            query,
            source=source,
        )

        answer_result = self.word_chain.add_text(
            answer,
            source=source,
        )

        return {
            "query": query_result,
            "answer": answer_result,
        }

    # ==================================================================
    # CONTINUITY
    # ==================================================================

    def continuity(
        self,
        query: str,
        answer: str,
    ) -> Dict[str, float]:
        """
        Calculate continuity between the user's query and AI answer.
        """

        return {
            "phrase_continuity": (
                self.word_chain.phrase_continuity(
                    query,
                    answer,
                )
            ),
            "pair_overlap": (
                self.word_chain.pair_overlap(
                    query,
                    answer,
                )
            ),
        }

    # ==================================================================
    # WORDCHAIN CANDIDATES
    # ==================================================================

    def continuation_candidates(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve learned continuation candidates.
        """

        return self.word_chain.predict_from_text(
            query,
            limit=limit,
        )

    # ==================================================================
    # MEMORY EVENT
    # ==================================================================

    def build_memory_event(
        self,
        query: str,
        answer: str,
        lang: str = "en",
        source: str = "conversation",
        user_id: Optional[int] = None,
        org_id: Optional[int] = None,
        room_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build the interaction event consumed by the
        ProjectTraceMemoryLayer.

        This method does NOT decide relevancy.

        GSP-XOR relevancy sharding belongs to the memory layer.
        """

        analysis = self.understand_interaction(
            query=query,
            answer=answer,
            lang=lang,
        )

        continuity = self.continuity(
            query,
            answer,
        )

        query_keywords = extract_keywords(
            query
        )

        answer_keywords = extract_keywords(
            answer
        )

        return {
            "event_type": "conversation_interaction",

            "query": query,

            "answer": answer,

            "language": lang,

            "source": source,

            "user_id": user_id,

            "org_id": org_id,

            "room_id": room_id,

            "domain": analysis[
                "domain"
            ],

            "query_keywords": query_keywords,

            "answer_keywords": answer_keywords,

            "continuity": continuity,

            "wordchain": {
                "query_candidates": (
                    self.continuation_candidates(
                        query
                    )
                ),
                "query_pairs": (
                    extract_word_pairs(
                        query
                    )
                ),
                "answer_pairs": (
                    extract_word_pairs(
                        answer
                    )
                ),
            },

            "understanding": analysis[
                "understanding"
            ],
        }

    # ==================================================================
    # POST RESPONSE
    # ==================================================================

    def process_response(
        self,
        query: str,
        answer: str,
        lang: str = "en",
        source: str = "conversation",
        user_id: Optional[int] = None,
        org_id: Optional[int] = None,
        room_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process an interaction after the AI response.

        Flow:

            query + answer
                ↓
            WordChain learning
                ↓
            understanding
                ↓
            continuity
                ↓
            memory event
                ↓
            ProjectTraceMemoryLayer

        The actual memory routing is intentionally left to the
        ProjectTraceMemoryLayer.
        """

        learning = self.learn_interaction(
            query=query,
            answer=answer,
            source=source,
        )

        event = self.build_memory_event(
            query=query,
            answer=answer,
            lang=lang,
            source=source,
            user_id=user_id,
            org_id=org_id,
            room_id=room_id,
        )

        return {
            "learning": learning,
            "event": event,
        }


# ---------------------------------------------------------------------------
# MODULE-LEVEL API
# ---------------------------------------------------------------------------

def generate_follow_ups(
    query: str,
    answer: str,
    domain: Optional[str] = None,
    max_questions: int = 3,
    word_chain: Optional[WordChain] = None,
    word_understanding: Optional[
        WordUnderstanding
    ] = None,
    memory_grid: Optional[MemoryGrid] = None,
) -> List[str]:
    """
    Generate contextual follow-up questions.

    WordChain and WordUnderstanding are now available to the
    follow-up layer.

    The actual AI response remains outside this module.
    """

    engine = FollowUp(
        word_chain=word_chain,
        word_understanding=word_understanding,
        memory_grid=memory_grid,
    )

    # ---------------------------------------------------------------
    # DOMAIN
    # ---------------------------------------------------------------

    if domain is None:
        domain = detect_domain(
            query
        )

    # ---------------------------------------------------------------
    # KEYWORDS
    # ---------------------------------------------------------------

    query_keywords = extract_keywords(
        query
    )

    answer_keywords = extract_keywords(
        answer
    )

    keywords = (
        query_keywords
        or answer_keywords
    )

    if not keywords:
        return []

    primary = keywords[0]

    secondary = (
        keywords[1]
        if len(keywords) > 1
        else None
    )

    questions: List[str] = []

    # ---------------------------------------------------------------
    # DOMAIN QUESTIONS
    # ---------------------------------------------------------------

    if domain == "code":

        questions.extend([
            f"Can you show me an example of using {primary}?",
            f"What are the common errors when using {primary}?",
        ])

        if secondary:

            questions.append(
                f"How does {primary} relate to {secondary}?"
            )

    elif domain == "medical":

        questions.extend([
            f"What are the symptoms associated with {primary}?",
            f"What treatments are commonly used for {primary}?",
            (
                f"What should someone know before considering "
                f"treatment for {primary}?"
            ),
        ])

    elif domain == "business":

        questions.extend([
            f"How does {primary} affect a business?",
            (
                f"What are the main considerations when dealing "
                f"with {primary}?"
            ),
            (
                f"Can you give me a practical example involving "
                f"{primary}?"
            ),
        ])

    else:

        questions.extend([
            f"Can you explain {primary} in more detail?",
            f"How does {primary} work?",
            (
                f"What is the relationship between "
                f"{primary} and {secondary}?"
                if secondary
                else f"What are the key aspects of {primary}?"
            ),
        ])

    # ---------------------------------------------------------------
    # WORDCHAIN CONTINUITY
    # ---------------------------------------------------------------

    candidates = (
        engine.continuation_candidates(
            query,
            limit=3,
        )
    )

    if candidates:

        candidate = candidates[0].get(
            "word"
        )

        after = candidates[0].get(
            "after"
        )

        if candidate and after:

            questions.append(
                f"How does {after} relate to {candidate}?"
            )

    # ---------------------------------------------------------------
    # LAST WORD-PAIR
    # ---------------------------------------------------------------

    pairs = extract_word_pairs(
        query
    )

    if pairs:

        first, second = pairs[-1].split(
            "_",
            1,
        )

        questions.append(
            f"How does {first} relate to {second}?"
        )

    # ---------------------------------------------------------------
    # DEDUPLICATION
    # ---------------------------------------------------------------

    unique_questions = []

    for question in questions:

        question = question.strip()

        if (
            question
            and question not in unique_questions
        ):
            unique_questions.append(
                question
            )

    return unique_questions[
        :max_questions
    ]


# ---------------------------------------------------------------------------
# CONVENIENCE POST-RESPONSE FUNCTION
# ---------------------------------------------------------------------------

def process_ai_interaction(
    query: str,
    answer: str,
    lang: str = "en",
    source: str = "conversation",
    word_chain: Optional[WordChain] = None,
    word_understanding: Optional[
        WordUnderstanding
    ] = None,
    memory_grid: Optional[MemoryGrid] = None,
    user_id: Optional[int] = None,
    org_id: Optional[int] = None,
    room_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convenience entry point for the model/runtime layer.

    This is the intended post-response integration point.
    """

    engine = FollowUp(
        word_chain=word_chain,
        word_understanding=word_understanding,
        memory_grid=memory_grid,
    )

    return engine.process_response(
        query=query,
        answer=answer,
        lang=lang,
        source=source,
        user_id=user_id,
        org_id=org_id,
        room_id=room_id,
    )


# ---------------------------------------------------------------------------
# DEVELOPMENT
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    chain = WordChain()

    engine = FollowUp(
        word_chain=chain,
    )

    query = (
        "How does deterministic storage work "
        "in the GSP project?"
    )

    answer = (
        "Deterministic storage maps the same input "
        "to the same storage location."
    )

    result = engine.process_response(
        query=query,
        answer=answer,
        lang="en",
        source="project",
    )

    print(
        "Interaction:"
    )

    print(
        result
    )

    print(
        "\nFollow-ups:"
    )

    print(
        generate_follow_ups(
            query=query,
            answer=answer,
            word_chain=chain,
        )
    )