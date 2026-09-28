"""
Response Stream
---------------

Controls the streaming lifecycle of CoMpaNeoN responses.

Responsibilities:
- Stream high-level AI activity/status events.
- Stream generated response text.
- Keep frontend rendering synchronized with backend generation.
- Support response cancellation.
- Preserve user/session/workspace/message identity.
- Preserve model version.
- Never expose private chain-of-thought.

This module does NOT:
- rank candidates
- retrieve memory
- generate follow-up questions
- alter prompts
- modify the tokenizer
- modify the model architecture

Those systems continue doing their own jobs.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Dict, Any

import torch
import torch.nn.functional as F

from ai_model import MiniCompanionAI
from tokenizer import tokenize, normalize_lang


# ---------------------------------------------------------------------------
# RESPONSE STATE
# ---------------------------------------------------------------------------

@dataclass
class ResponseContext:
    """
    Identity and deployment information attached to one AI response.
    """

    response_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    workspace_id: Optional[str] = None
    message_id: Optional[str] = None
    model_version: str = "1.0.0.1idr"
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# RESPONSE EVENTS
# ---------------------------------------------------------------------------

def make_event(
    event_type: str,
    context: ResponseContext,
    **payload,
) -> Dict[str, Any]:
    """
    Build a frontend-safe stream event.

    event_type examples:

        status
        token
        complete
        error
        cancelled
    """

    return {
        "event": event_type,
        "response_id": context.response_id,
        "user_id": context.user_id,
        "session_id": context.session_id,
        "workspace_id": context.workspace_id,
        "message_id": context.message_id,
        "model_version": context.model_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }


# ---------------------------------------------------------------------------
# HIGH-LEVEL ACTIVITY STATES
# ---------------------------------------------------------------------------

ACTIVITY_STAGES = {
    "understanding": {
        "label": "Understanding",
        "description": "Understanding your request.",
    },

    "recalling": {
        "label": "Recalling",
        "description": "Checking relevant memory and conversation context.",
    },

    "retrieving": {
        "label": "Retrieving",
        "description": "Retrieving relevant knowledge.",
    },

    "analyzing": {
        "label": "Analyzing",
        "description": "Analyzing relationships and context.",
    },

    "planning": {
        "label": "Planning",
        "description": "Planning the response.",
    },

    "generating": {
        "label": "Generating",
        "description": "Generating the response.",
    },

    "complete": {
        "label": "Complete",
        "description": "Response complete.",
    },
}


def activity_event(
    context: ResponseContext,
    stage: str,
) -> Dict[str, Any]:

    info = ACTIVITY_STAGES.get(
        stage,
        {
            "label": stage.title(),
            "description": "",
        },
    )

    return make_event(
        "status",
        context,
        stage=stage,
        label=info["label"],
        description=info["description"],
    )


# ---------------------------------------------------------------------------
# CANCELLATION
# ---------------------------------------------------------------------------

class ResponseCancellation:
    """
    Lightweight cancellation registry.

    A response can be cancelled by its response_id.

    This remains local to the running AI process.
    """

    def __init__(self):
        self._cancelled = set()

    def cancel(self, response_id: str):
        self._cancelled.add(response_id)

    def is_cancelled(self, response_id: str) -> bool:
        return response_id in self._cancelled

    def clear(self, response_id: str):
        self._cancelled.discard(response_id)


# Global cancellation controller.
cancellation = ResponseCancellation()


# ---------------------------------------------------------------------------
# TOKENIZER HELPERS
# ---------------------------------------------------------------------------

def encode_prompt(
    text: str,
    vocab: Dict[str, int],
    lang: str = "en",
):
    """
    Encode text using the existing tokenizer.

    This deliberately follows the same vocabulary rules
    used by summary.py and train.py.
    """

    lang = normalize_lang(lang)

    tokens = tokenize(
        text,
        lang,
    )

    ids = [
        vocab.get("<start>", 2)
    ]

    for token in tokens:

        stem = token["stem"]
        original = token["original"]

        if stem in vocab:
            word = stem

        elif original in vocab:
            word = original

        else:
            word = "<unk>"

        ids.append(
            vocab.get(word, 1)
        )

    ids.append(
        vocab.get("<end>", 3)
    )

    return ids


def decode_token(
    token_id: int,
    reverse: Dict[int, str],
    vocab: Dict[str, int],
) -> Optional[str]:

    if token_id in {
        vocab.get("<pad>", 0),
        vocab.get("<start>", 2),
        vocab.get("<end>", 3),
    }:
        return None

    return reverse.get(
        token_id,
        "<unk>",
    )


# ---------------------------------------------------------------------------
# RESPONSE STREAM
# ---------------------------------------------------------------------------

class ResponseStream:
    """
    Main response streaming controller.

    It sits between the AI backend and the frontend transport layer.

    Retrieval, ranking, memory, word-chain and prompt systems are
    external to this class and should be executed before generation.
    """

    def __init__(
        self,
        model: MiniCompanionAI,
        vocab: Dict[str, int],
        reverse: Dict[int, str],
        model_version: str = "1.0.0.1idr",
        device: Optional[torch.device] = None,
    ):

        self.model = model
        self.vocab = vocab
        self.reverse = reverse
        self.model_version = model_version

        self.device = device or torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        self.model.to(self.device)
        self.model.eval()

    # -----------------------------------------------------------------------
    # CREATE CONTEXT
    # -----------------------------------------------------------------------

    def create_context(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        message_id: Optional[str] = None,
        language: str = "en",
    ) -> ResponseContext:

        return ResponseContext(
            response_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            workspace_id=workspace_id,
            message_id=message_id,
            model_version=self.model_version,
            language=normalize_lang(language),
        )

    # -----------------------------------------------------------------------
    # GENERATE
    # -----------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        context: ResponseContext,
        max_len: int = 256,
        temperature: float = 0.7,
        stream_delay: float = 0.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate and stream one response.

        The frontend receives:

            status
            token
            complete

        or:

            cancelled

        or:

            error
        """

        try:

            # ---------------------------------------------------------------
            # UNDERSTANDING
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "understanding",
            )

            await asyncio.sleep(0)

            if cancellation.is_cancelled(
                context.response_id
            ):
                yield make_event(
                    "cancelled",
                    context,
                )
                return

            # ---------------------------------------------------------------
            # RECALLING
            #
            # This is a status event only.
            #
            # Actual memory retrieval is performed outside this class.
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "recalling",
            )

            await asyncio.sleep(0)

            if cancellation.is_cancelled(
                context.response_id
            ):
                yield make_event(
                    "cancelled",
                    context,
                )
                return

            # ---------------------------------------------------------------
            # RETRIEVING
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "retrieving",
            )

            await asyncio.sleep(0)

            if cancellation.is_cancelled(
                context.response_id
            ):
                yield make_event(
                    "cancelled",
                    context,
                )
                return

            # ---------------------------------------------------------------
            # ANALYZING
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "analyzing",
            )

            await asyncio.sleep(0)

            if cancellation.is_cancelled(
                context.response_id
            ):
                yield make_event(
                    "cancelled",
                    context,
                )
                return

            # ---------------------------------------------------------------
            # PLANNING
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "planning",
            )

            await asyncio.sleep(0)

            if cancellation.is_cancelled(
                context.response_id
            ):
                yield make_event(
                    "cancelled",
                    context,
                )
                return

            # ---------------------------------------------------------------
            # GENERATION
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "generating",
            )

            input_ids = encode_prompt(
                prompt,
                self.vocab,
                context.language,
            )

            input_tensor = torch.tensor(
                [input_ids],
                dtype=torch.long,
                device=self.device,
            )

            generated_ids = []

            # ---------------------------------------------------------------
            # MODEL GENERATION
            # ---------------------------------------------------------------

            with torch.no_grad():

                for _ in range(max_len):

                    if cancellation.is_cancelled(
                        context.response_id
                    ):
                        yield make_event(
                            "cancelled",
                            context,
                            generated_tokens=len(
                                generated_ids
                            ),
                        )
                        return

                    logits = self.model(
                        input_tensor
                    )[0, -1, :]

                    # Prevent invalid temperatures.
                    safe_temperature = max(
                        float(temperature),
                        0.05,
                    )

                    logits = (
                        logits
                        / safe_temperature
                    )

                    probs = F.softmax(
                        logits,
                        dim=-1,
                    )

                    next_id = torch.multinomial(
                        probs,
                        1,
                    ).item()

                    generated_ids.append(
                        next_id
                    )

                    input_tensor = torch.cat(
                        [
                            input_tensor,
                            torch.tensor(
                                [[next_id]],
                                dtype=torch.long,
                                device=self.device,
                            ),
                        ],
                        dim=1,
                    )

                    if next_id == self.vocab.get(
                        "<end>",
                        3,
                    ):
                        break

                    text = decode_token(
                        next_id,
                        self.reverse,
                        self.vocab,
                    )

                    if text is None:
                        continue

                    yield make_event(
                        "token",
                        context,
                        text=text,
                        token_id=next_id,
                    )

                    if stream_delay > 0:
                        await asyncio.sleep(
                            stream_delay
                        )
                    else:
                        await asyncio.sleep(0)

            # ---------------------------------------------------------------
            # COMPLETE
            # ---------------------------------------------------------------

            yield activity_event(
                context,
                "complete",
            )

            yield make_event(
                "complete",
                context,
                generated_tokens=len(
                    generated_ids
                ),
            )

        except asyncio.CancelledError:

            yield make_event(
                "cancelled",
                context,
            )

        except Exception as exc:

            yield make_event(
                "error",
                context,
                error=str(exc),
            )

        finally:

            cancellation.clear(
                context.response_id
            )


# ---------------------------------------------------------------------------
# RESPONSE CANCELLATION API
# ---------------------------------------------------------------------------

def cancel_response(
    response_id: str,
) -> bool:
    """
    Cancel an active response.
    """

    cancellation.cancel(
        response_id
    )

    return True


# ---------------------------------------------------------------------------
# SIMPLE STREAM HELPER
# ---------------------------------------------------------------------------

async def stream_response(
    model: MiniCompanionAI,
    vocab: Dict[str, int],
    reverse: Dict[int, str],
    prompt: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    message_id: Optional[str] = None,
    language: str = "en",
    model_version: str = "1.0.0.1idr",
    max_len: int = 256,
    temperature: float = 0.7,
    stream_delay: float = 0.0,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function for API routes.

    The API does not need to know the internal implementation
    of ResponseStream.
    """

    streamer = ResponseStream(
        model=model,
        vocab=vocab,
        reverse=reverse,
        model_version=model_version,
    )

    context = streamer.create_context(
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
        message_id=message_id,
        language=language,
    )

    async for event in streamer.generate(
        prompt=prompt,
        context=context,
        max_len=max_len,
        temperature=temperature,
        stream_delay=stream_delay,
    ):
        yield event