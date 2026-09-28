from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from langdetect import detect, LangDetectException

from ai_model import MiniCompanionAI
from memory_grid import MemoryGrid
from tokenizer import tokenize, normalize_lang


# ============================================================================
# MEMORY GRID
# ============================================================================

memory = MemoryGrid()


# ============================================================================
# GLOBAL TOKENIZER STATE
# ============================================================================

tokenizer_vocab: Optional[Dict[str, int]] = None
reverse_vocab: Optional[Dict[int, str]] = None


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================

def detect_lang(text: str) -> str:
    """
    Dynamically detect language for multilingual training data.

    Short, empty, code-like, emoji-heavy, or ambiguous content safely
    falls back to English.
    """

    try:
        if not text or not text.strip():
            return "en"

        detected = detect(text)

        return normalize_lang(detected)

    except LangDetectException:
        return "en"

    except Exception:
        return "en"


# ============================================================================
# MEMORY GRID DATA EXTRACTION
# ============================================================================

def collect_memorygrid_texts() -> List[str]:
    """
    Collect training material directly from MemoryGrid.

    MemoryGrid is the primary knowledge source for background training.

    The grid may contain knowledge originating from:

        - user entries
        - web crawlers
        - grid crawlers
        - research
        - dictionaries/domain knowledge
        - AI-generated knowledge
        - other indexed material

    The complete document text is retained as the training document.
    """

    texts: List[str] = []

    for document in memory.doc_store:

        if not isinstance(document, dict):
            continue

        text = document.get("text", "")

        if not isinstance(text, str):
            continue

        text = text.strip()

        if text:
            texts.append(text)

    return texts


# ============================================================================
# MEMORY GRID TOKEN EXTRACTION
# ============================================================================

def collect_memorygrid_tokens() -> List[Dict[str, Any]]:
    """
    Collect tokenized knowledge already stored in MemoryGrid.

    This allows training to use the tokenizer output already associated
    with indexed documents instead of rebuilding the lexical representation
    unnecessarily.

    If a document does not contain stored tokenizer output, its text is
    tokenized dynamically.
    """

    token_records: List[Dict[str, Any]] = []

    for document in memory.doc_store:

        if not isinstance(document, dict):
            continue

        stored_tokens = document.get("tokens", [])

        if stored_tokens:
            for token in stored_tokens:

                if not isinstance(token, dict):
                    continue

                token_records.append(token)

            continue

        text = document.get("text", "")

        if not isinstance(text, str) or not text.strip():
            continue

        lang = normalize_lang(
            document.get(
                "lang",
                detect_lang(text),
            )
        )

        tokens = tokenize(
            text,
            lang,
        )

        token_records.extend(tokens)

    return token_records


# ============================================================================
# UNIQUE WORD COUNT
# ============================================================================

def get_unique_words_count() -> int:
    """
    Count unique lexical units currently present in MemoryGrid.

    Both original and stem forms are considered.
    """

    unique = set()

    for document in memory.doc_store:

        if not isinstance(document, dict):
            continue

        tokens = document.get("tokens", [])

        if tokens:

            for token in tokens:

                if not isinstance(token, dict):
                    continue

                stem = token.get("stem")

                original = token.get("original")

                if stem:
                    unique.add(stem)

                if original:
                    unique.add(original)

        else:

            text = document.get("text", "")

            if not isinstance(text, str):
                continue

            if not text.strip():
                continue

            lang = normalize_lang(
                document.get(
                    "lang",
                    detect_lang(text),
                )
            )

            for token in tokenize(text, lang):

                stem = token.get("stem")
                original = token.get("original")

                if stem:
                    unique.add(stem)

                if original:
                    unique.add(original)

    return len(unique)


# ============================================================================
# VOCABULARY
# ============================================================================

def build_vocab(
    texts: List[str],
) -> Tuple[
    Dict[str, int],
    Dict[int, str],
]:
    """
    Build the model vocabulary from MemoryGrid content.

    Both stem and original token forms are retained.
    """

    vocab: Dict[str, int] = {
        "<pad>": 0,
        "<unk>": 1,
        "<start>": 2,
        "<end>": 3,
    }

    reverse: Dict[int, str] = {
        0: "<pad>",
        1: "<unk>",
        2: "<start>",
        3: "<end>",
    }

    for text in texts:

        lang = detect_lang(text)

        tokens = tokenize(
            text,
            lang,
        )

        for token in tokens:

            stem = token.get(
                "stem",
                "",
            )

            original = token.get(
                "original",
                "",
            )

            for word in (
                stem,
                original,
            ):

                if not word:
                    continue

                if word not in vocab:

                    token_id = len(vocab)

                    vocab[word] = token_id
                    reverse[token_id] = word

    return vocab, reverse


# ============================================================================
# ENCODE MEMORY GRID
# ============================================================================

def encode_texts(
    texts: List[str],
    vocab: Dict[str, int],
) -> List[List[int]]:
    """
    Encode MemoryGrid documents into model training sequences.

    Tokenization remains multilingual and synchronized with tokenizer.py.
    """

    encoded: List[List[int]] = []

    for text in texts:

        lang = detect_lang(text)

        tokens = tokenize(
            text,
            lang,
        )

        ids: List[int] = [
            vocab["<start>"]
        ]

        for token in tokens:

            stem = token.get(
                "stem",
                "",
            )

            original = token.get(
                "original",
                "",
            )

            if stem in vocab:

                ids.append(
                    vocab[stem]
                )

            elif original in vocab:

                ids.append(
                    vocab[original]
                )

            else:

                ids.append(
                    vocab["<unk>"]
                )

        ids.append(
            vocab["<end>"]
        )

        if len(ids) > 2:
            encoded.append(ids)

    return encoded


# ============================================================================
# BATCH GENERATOR
# ============================================================================

def get_batch(
    encoded_docs: List[List[int]],
    batch_size: int,
    seq_len: int,
    vocab: Dict[str, int],
):

    while True:

        inputs = []
        targets = []

        for _ in range(batch_size):

            doc = encoded_docs[
                torch.randint(
                    0,
                    len(encoded_docs),
                    (1,),
                ).item()
            ]

            if len(doc) < seq_len + 1:

                doc = doc + (
                    [vocab["<pad>"]]
                    * (
                        seq_len
                        + 1
                        - len(doc)
                    )
                )

            max_start = (
                len(doc)
                - seq_len
                - 1
            )

            if max_start > 0:

                start = torch.randint(
                    0,
                    max_start + 1,
                    (1,),
                ).item()

            else:

                start = 0

            chunk = doc[
                start:
                start + seq_len + 1
            ]

            if len(chunk) < seq_len + 1:

                chunk = chunk + (
                    [vocab["<pad>"]]
                    * (
                        seq_len
                        + 1
                        - len(chunk)
                    )
                )

            inputs.append(
                chunk[:-1]
            )

            targets.append(
                chunk[1:]
            )

        yield (
            torch.tensor(
                inputs,
                dtype=torch.long,
            ),
            torch.tensor(
                targets,
                dtype=torch.long,
            ),
        )


# ============================================================================
# TRAIN MODEL
# ============================================================================

def train_model(
    grid_cv_params: Optional[Dict[str, Any]] = None,
):
    """
    Train MiniCompanionAI directly from MemoryGrid knowledge.

    MemoryGrid is the training-data source.

    No crawler K/D logic is introduced here.
    K and D remain crawler concepts.

    Training consumes tokenized knowledge already indexed into MemoryGrid.
    """

    global tokenizer_vocab
    global reverse_vocab

    # ----------------------------------------------------------------------
    # COLLECT MEMORY GRID KNOWLEDGE
    # ----------------------------------------------------------------------

    texts = collect_memorygrid_texts()

    if not texts:

        print(
            "No training data found in MemoryGrid."
        )

        return

    print(
        f"Collected {len(texts)} MemoryGrid documents."
    )

    # ----------------------------------------------------------------------
    # VERSION
    # ----------------------------------------------------------------------

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    batch_version = (
        f"v_{timestamp}"
    )

    # ----------------------------------------------------------------------
    # HYPERPARAMETERS
    # ----------------------------------------------------------------------

    hyperparams = (
        grid_cv_params
        if grid_cv_params is not None
        else {
            "lr": 1e-4,
            "epochs": 30,
            "batch_size": 4,
            "seq_len": 32,
        }
    )

    lr = float(
        hyperparams.get(
            "lr",
            1e-4,
        )
    )

    epochs = int(
        hyperparams.get(
            "epochs",
            30,
        )
    )

    batch_size = int(
        hyperparams.get(
            "batch_size",
            4,
        )
    )

    seq_len = int(
        hyperparams.get(
            "seq_len",
            32,
        )
    )

    # ----------------------------------------------------------------------
    # BUILD VOCABULARY
    # ----------------------------------------------------------------------

    tokenizer_vocab, reverse_vocab = build_vocab(
        texts
    )

    print(
        f"Vocabulary size: "
        f"{len(tokenizer_vocab)}"
    )

    # ----------------------------------------------------------------------
    # ENCODE
    # ----------------------------------------------------------------------

    encoded_docs = encode_texts(
        texts,
        tokenizer_vocab,
    )

    if not encoded_docs:

        print(
            "No encoded MemoryGrid documents."
        )

        return

    print(
        f"Encoded "
        f"{len(encoded_docs)} "
        f"MemoryGrid documents."
    )

    # ----------------------------------------------------------------------
    # DEVICE
    # ----------------------------------------------------------------------

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    # ----------------------------------------------------------------------
    # MODEL
    # ----------------------------------------------------------------------

    model = MiniCompanionAI(
        vocab_size=len(
            tokenizer_vocab
        )
    )

    model.to(device)

    optimizer = optim.Adam(
        model.parameters(),
        lr=lr,
    )

    criterion = nn.CrossEntropyLoss(
        ignore_index=tokenizer_vocab[
            "<pad>"
        ]
    )

    # ----------------------------------------------------------------------
    # TRAIN
    # ----------------------------------------------------------------------

    print(
        f"Starting background training "
        f"Run [{batch_version}]"
    )

    print(
        f"Device: {device}"
    )

    print(
        f"Hyperparameters: {hyperparams}"
    )

    avg_loss = 0.0

    for epoch in range(
        epochs
    ):

        model.train()

        total_loss = 0.0

        steps = max(
            1,
            min(
                50,
                len(encoded_docs)
                // max(batch_size, 1),
            ),
        )

        batch_iterator = get_batch(
            encoded_docs,
            batch_size,
            seq_len,
            tokenizer_vocab,
        )

        for _ in range(
            steps
        ):

            x, y = next(
                batch_iterator
            )

            x = x.to(device)
            y = y.to(device)

            optimizer.zero_grad()

            logits = model(x)

            loss = criterion(
                logits.reshape(
                    -1,
                    len(tokenizer_vocab),
                ),
                y.reshape(-1),
            )

            loss.backward()

            optimizer.step()

            total_loss += (
                loss.item()
            )

        avg_loss = (
            total_loss
            / max(steps, 1)
        )

        if (
            (epoch + 1) % 5 == 0
            or epoch == 0
            or epoch == epochs - 1
        ):

            print(
                f"Batch {batch_version} | "
                f"Epoch {epoch + 1}/{epochs} | "
                f"Loss: {avg_loss:.4f}"
            )

    # ----------------------------------------------------------------------
    # VERSIONED MODEL
    # ----------------------------------------------------------------------

    model_filename = (
        f"companion_model_"
        f"{batch_version}.pth"
    )

    vocab_filename = (
        f"tokenizer_vocab_"
        f"{batch_version}.json"
    )

    torch.save(
        model.state_dict(),
        model_filename,
    )

    # ----------------------------------------------------------------------
    # METADATA
    # ----------------------------------------------------------------------

    metadata = {

        "batch_version":
            batch_version,

        "trained_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "training_source":
            "memorygrid",

        "documents_trained":
            len(encoded_docs),

        "memorygrid_documents":
            len(texts),

        "unique_words":
            get_unique_words_count(),

        "final_loss":
            avg_loss,

        "device":
            str(device),

        "hyperparameters":
            hyperparams,

        "vocab":
            tokenizer_vocab,

        "reverse":
            reverse_vocab,
    }

    with open(
        vocab_filename,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False,
        )

    # ----------------------------------------------------------------------
    # PRODUCTION POINTER
    # ----------------------------------------------------------------------

    torch.save(
        model.state_dict(),
        "companion_model.pth",
    )

    with open(
        "tokenizer_vocab.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False,
        )

    print(
        "Deployment artifacts saved."
    )

    print(
        f"Active production model: "
        f"{batch_version}"
    )


# ============================================================================
# BACKGROUND MONITOR
# ============================================================================

async def auto_train_monitor():
    """
    Continuously monitor MemoryGrid for newly indexed lexical knowledge.

    When MemoryGrid grows, the model is retrained from the current
    MemoryGrid knowledge set.
    """

    last_count = (
        get_unique_words_count()
    )

    print(
        "Auto-train monitor started."
    )

    print(
        f"Initial MemoryGrid unique words: "
        f"{last_count}"
    )

    while True:

        await asyncio.sleep(
            60
        )

        current_count = (
            get_unique_words_count()
        )

        if current_count > last_count:

            print(
                "New MemoryGrid knowledge "
                "detected."
            )

            print(
                f"Unique words: "
                f"{last_count} -> "
                f"{current_count}"
            )

            await asyncio.to_thread(
                train_model
            )

            last_count = current_count

        else:

            last_count = current_count


# ============================================================================
# START BACKGROUND TRAINING
# ============================================================================

def start_background_training():
    """
    Start the asynchronous MemoryGrid training monitor
    in the current event loop.
    """

    loop = asyncio.get_event_loop()

    loop.create_task(
        auto_train_monitor()
    )


# ============================================================================
# OPTIONAL DIRECT EXECUTION
# ============================================================================

if __name__ == "__main__":

    train_model()