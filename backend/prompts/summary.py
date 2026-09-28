"""
Summary Module

Generates a concise, AI-aware summary of a workspace conversation.

Memory behavior:
- Conversation input is tokenized and entered into MemoryGrid.
- AI response is also tokenized and entered into MemoryGrid.
- Both use the same three independent memory routes:
    1. Letter Grid
    2. Word Grid
    3. Full-Text / Storage Grid
- The summary itself is generated separately.
- Summary generation does not replace conversation/AI-response memory.
- Existing model loading and generation behavior is preserved.
"""

from __future__ import annotations

import os
import json

import torch
import torch.nn.functional as F

from ai_model import MiniCompanionAI
from tokenizer import tokenize, normalize_lang
from memory_grid import MemoryGrid
from word_understanding import WordUnderstanding
from prompts_manager import build_prompt


# ---------------------------------------------------------------------------
# SHARED MEMORY
# ---------------------------------------------------------------------------

# Summary remains a consumer of the existing MemoryGrid architecture.
#
# If another application layer already owns a MemoryGrid instance, it can
# continue using that instance independently. This module keeps a local
# instance so summary generation can also register conversation/AI material.
memory = MemoryGrid()

word_understanding = WordUnderstanding(
    memory
)


# ---------------------------------------------------------------------------
# MODEL / VOCABULARY
# ---------------------------------------------------------------------------

def load_model_and_vocab():
    """
    Load the active tokenizer vocabulary and companion model.

    Existing behavior is preserved:
        tokenizer_vocab.json
        companion_model.pth

    Returns:
        model, vocab, reverse
    """

    vocab = None
    reverse = None
    model = None

    # ---------------------------------------------------------------
    # VOCABULARY
    # ---------------------------------------------------------------

    if os.path.exists(
        "tokenizer_vocab.json"
    ):

        with open(
            "tokenizer_vocab.json",
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

            vocab = data.get(
                "vocab",
                {},
            )

            reverse_data = data.get(
                "reverse",
                {},
            )

            reverse = {
                int(k): v
                for k, v in reverse_data.items()
            }

    # ---------------------------------------------------------------
    # MODEL
    # ---------------------------------------------------------------

    if os.path.exists(
        "companion_model.pth"
    ):

        model = MiniCompanionAI(
            len(vocab)
            if vocab
            else 1000
        )

        model.load_state_dict(
            torch.load(
                "companion_model.pth",
                map_location="cpu",
            )
        )

        model.eval()

    return (
        model,
        vocab,
        reverse,
    )


# ---------------------------------------------------------------------------
# ENCODING
# ---------------------------------------------------------------------------

def encode_text(
    text,
    vocab,
    lang: str = "en",
):
    """
    Encode text using the active tokenizer vocabulary.

    Tokenization remains language-aware.
    """

    lang = normalize_lang(
        lang
    )

    tokens = tokenize(
        text,
        lang,
    )

    ids = [
        vocab.get(
            "<start>",
            2,
        )
    ]

    for token in tokens:

        word = (
            token.get("stem")
            if token.get("stem") in vocab
            else token.get(
                "original",
                "",
            )
        )

        if word not in vocab:
            word = "<unk>"

        ids.append(
            vocab.get(
                word,
                1,
            )
        )

    ids.append(
        vocab.get(
            "<end>",
            3,
        )
    )

    return ids


# ---------------------------------------------------------------------------
# DECODING
# ---------------------------------------------------------------------------

def decode_ids(
    ids,
    reverse,
):
    """
    Decode generated token IDs.

    Special tokens are removed from the returned text.
    """

    return " ".join(
        reverse.get(
            i,
            "<unk>",
        )
        for i in ids
        if i not in {
            0,
            2,
            3,
        }
    )


# ---------------------------------------------------------------------------
# MEMORY INGESTION
# ---------------------------------------------------------------------------

def index_memory_text(
    text: str,
    lang: str = "en",
    source: str = "",
) -> int | None:
    """
    Enter text into the three independent MemoryGrid routes.

    The MemoryGrid owns placement.

    This function deliberately does NOT calculate:
        - letter-grid positions
        - Word Grid coordinates
        - storage positions
        - GSP cells

    Those responsibilities remain inside the established architecture.

    Routes entered by MemoryGrid:

        Text
          │
          ├── Letter Grid
          ├── Word Grid
          └── 64-row storage / Full-Text route

    Returns:
        doc_id, or None when text is empty.
    """

    if not text:
        return None

    clean = str(
        text
    ).strip()

    if not clean:
        return None

    lang = normalize_lang(
        lang
    )

    return memory.add_document(
        text=clean,
        lang=lang,
        source=source,
    )


# ---------------------------------------------------------------------------
# CONVERSATION + AI MEMORY
# ---------------------------------------------------------------------------

def index_conversation_memory(
    conversation_text: str,
    ai_response: str = "",
    lang: str = "en",
) -> dict:
    """
    Register both sides of the interaction in MemoryGrid.

    The user's conversation and the AI response are independent documents.

    This is intentional.

    User:
        source = conversation

    AI:
        source = ai_response

    Both are tokenized and entered through the same three memory routes.
    """

    conversation_doc_id = None
    response_doc_id = None

    if conversation_text:

        conversation_doc_id = index_memory_text(
            conversation_text,
            lang=lang,
            source="conversation",
        )

    if ai_response:

        response_doc_id = index_memory_text(
            ai_response,
            lang=lang,
            source="ai_response",
        )

    return {
        "conversation_doc_id": conversation_doc_id,
        "response_doc_id": response_doc_id,
    }


# ---------------------------------------------------------------------------
# SUMMARY GENERATION
# ---------------------------------------------------------------------------

def generate_summary(
    conversation_text,
    max_len=100,
    temperature=0.7,
    lang: str = "en",
    index_memory: bool = True,
):
    """
    Generate a summary using the trained model.

    Memory behavior:
        1. The conversation is optionally entered into MemoryGrid.
        2. The summary is generated.
        3. The generated AI summary is also entered into MemoryGrid.

    If the model is unavailable:
        - The existing truncated-text fallback is preserved.
        - The fallback summary is still indexed as AI-generated material.

    Parameters:
        conversation_text:
            Conversation to summarize.

        max_len:
            Maximum number of generated tokens.

        temperature:
            Sampling temperature.

        lang:
            Language of the conversation.

        index_memory:
            When True, register conversation and generated summary
            in MemoryGrid.

    Returns:
        Summary string.
    """

    if not conversation_text:
        return ""

    lang = normalize_lang(
        lang
    )

    # ---------------------------------------------------------------
    # REGISTER USER / CONVERSATION MATERIAL
    # ---------------------------------------------------------------

    conversation_doc_id = None

    if index_memory:

        conversation_doc_id = index_memory_text(
            conversation_text,
            lang=lang,
            source="conversation",
        )

    # ---------------------------------------------------------------
    # LOAD MODEL
    # ---------------------------------------------------------------

    model, vocab, reverse = (
        load_model_and_vocab()
    )

    summary = ""

    # ---------------------------------------------------------------
    # MODEL SUMMARY
    # ---------------------------------------------------------------

    if (
        model is not None
        and vocab is not None
    ):

        prompt = (
            "Summarize the following conversation briefly:\n"
            f"{conversation_text}\n"
            "Summary:"
        )

        input_ids = torch.tensor(
            [
                encode_text(
                    prompt,
                    vocab,
                    lang=lang,
                )
            ],
            dtype=torch.long,
        )

        output_ids = []

        # -----------------------------------------------------------
        # GENERATION
        # -----------------------------------------------------------

        with torch.no_grad():

            for _ in range(
                max_len
            ):

                logits = (
                    model(input_ids)[
                        0,
                        -1,
                        :
                    ]
                    / temperature
                )

                probs = F.softmax(
                    logits,
                    dim=-1,
                )

                next_id = (
                    torch.multinomial(
                        probs,
                        1,
                    ).item()
                )

                output_ids.append(
                    next_id
                )

                input_ids = torch.cat(
                    [
                        input_ids,
                        torch.tensor(
                            [[next_id]],
                            dtype=torch.long,
                        ),
                    ],
                    dim=1,
                )

                if next_id == vocab.get(
                    "<end>",
                    3,
                ):
                    break

        summary = decode_ids(
            output_ids,
            reverse,
        )

    # ---------------------------------------------------------------
    # FALLBACK
    # ---------------------------------------------------------------

    else:

        summary = (
            conversation_text[:500]
            + (
                "..."
                if len(
                    conversation_text
                ) > 500
                else ""
            )
        )

    # ---------------------------------------------------------------
    # REGISTER AI SUMMARY
    # ---------------------------------------------------------------

    summary_doc_id = None

    if (
        index_memory
        and summary
    ):

        summary_doc_id = index_memory_text(
            summary,
            lang=lang,
            source="ai_summary",
        )

    return summary


# ---------------------------------------------------------------------------
# COMPLETE SUMMARY + MEMORY OPERATION
# ---------------------------------------------------------------------------

def summarize_and_remember(
    conversation_text: str,
    max_len: int = 100,
    temperature: float = 0.7,
    lang: str = "en",
) -> dict:
    """
    Generate a summary while explicitly exposing the memory operation.

    This is useful to higher-level CoMpaNeoN orchestration.

    The flow is:

        Conversation
             │
             ▼
        MemoryGrid
             │
        ┌────┼────┐
        ▼    ▼    ▼
      Letter Word Storage
             │
             ▼
        Summary Generation
             │
             ▼
          AI Summary
             │
             ▼
        MemoryGrid again
             │
        ┌────┼────┐
        ▼    ▼    ▼
      Letter Word Storage

    Returns:
        {
            "summary": ...,
            "conversation_doc_id": ...,
            "summary_doc_id": ...
        }
    """

    lang = normalize_lang(
        lang
    )

    # ---------------------------------------------------------------
    # USER / CONVERSATION
    # ---------------------------------------------------------------

    conversation_doc_id = index_memory_text(
        conversation_text,
        lang=lang,
        source="conversation",
    )

    # ---------------------------------------------------------------
    # GENERATE WITHOUT DUPLICATING CONVERSATION INSERTION
    # ---------------------------------------------------------------

    summary = generate_summary(
        conversation_text=conversation_text,
        max_len=max_len,
        temperature=temperature,
        lang=lang,
        index_memory=False,
    )

    # ---------------------------------------------------------------
    # AI SUMMARY
    # ---------------------------------------------------------------

    summary_doc_id = None

    if summary:

        summary_doc_id = index_memory_text(
            summary,
            lang=lang,
            source="ai_summary",
        )

    return {
        "summary": summary,
        "conversation_doc_id": conversation_doc_id,
        "summary_doc_id": summary_doc_id,
    }


# ---------------------------------------------------------------------------
# AI RESPONSE MEMORY
# ---------------------------------------------------------------------------

def remember_ai_response(
    response: str,
    lang: str = "en",
) -> int | None:
    """
    Enter an AI response into all applicable MemoryGrid routes.

    This exists separately from summary generation because an AI response
    does not necessarily produce a summary.

    Therefore the normal CoMpaNeoN interaction can do:

        user input
             ↓
        understanding
             ↓
        AI response
             ↓
        remember_ai_response()
             ↓
        three grids
    """

    return index_memory_text(
        response,
        lang=lang,
        source="ai_response",
    )


# ---------------------------------------------------------------------------
# MEMORY ACCESS
# ---------------------------------------------------------------------------

def get_memory_grid() -> MemoryGrid:
    """
    Return the MemoryGrid used by this summary module.

    Higher-level orchestration can use this to connect summary memory
    with WordUnderstanding or other context services.
    """

    return memory


def get_word_understanding() -> WordUnderstanding:
    """
    Return the WordUnderstanding instance associated with this memory.
    """

    return word_understanding