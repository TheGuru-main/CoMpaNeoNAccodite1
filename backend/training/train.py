from __future__ import annotations

import os
import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from langdetect import detect, LangDetectException

from ai_model import MiniCompanionAI
from tokenizer import tokenize, normalize_lang
from memory_grid import MemoryGrid


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================

def detect_lang(text: str) -> str:
    """
    Dynamically detect language for training data.

    The detected language is normalized through tokenizer.py.
    """

    try:
        if not text or not text.strip():
            return "en"

        return normalize_lang(
            detect(text)
        )

    except LangDetectException:
        return "en"

    except Exception:
        return "en"


# ============================================================================
# MEMORYGRID TRAINING DATA
# ============================================================================

def iter_memorygrid_documents(
    memory_grid: MemoryGrid,
) -> Iterable[Dict[str, Any]]:
    """
    Iterate over documents already stored inside MemoryGrid.

    MemoryGrid is the authoritative knowledge source.

    Documents may have originated from:

        - user entries
        - WebCrawler
        - GridCrawler/indexed material
        - research material
        - dictionary/domain knowledge
        - AI-generated output
        - other indexed sources

    No crawler logic is performed here.

    train.py consumes what MemoryGrid already contains.
    """

    if memory_grid is None:
        return

    doc_store = getattr(
        memory_grid,
        "doc_store",
        None,
    )

    if not doc_store:
        return

    for document in doc_store:

        if not isinstance(
            document,
            dict,
        ):
            continue

        text = document.get(
            "text",
            "",
        )

        if not isinstance(
            text,
            str,
        ):
            continue

        text = text.strip()

        if not text:
            continue

        yield document


def load_texts_from_memorygrid(
    memory_grid: MemoryGrid,
) -> List[Dict[str, Any]]:
    """
    Collect training material from MemoryGrid.

    Each returned record preserves:

        text
        language
        source
        tokens

    The tokenizer output already stored in MemoryGrid is preferred.

    If an older MemoryGrid document does not contain tokenized output,
    tokenizer.py is called to reconstruct it.
    """

    training_records: List[
        Dict[str, Any]
    ] = []

    for document in iter_memorygrid_documents(
        memory_grid
    ):

        text = document.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        language = normalize_lang(
            document.get(
                "lang",
                detect_lang(text),
            )
        )

        stored_tokens = document.get(
            "tokens",
            [],
        )

        # --------------------------------------------------------------
        # MemoryGrid normally already contains tokenizer output.
        # --------------------------------------------------------------

        if isinstance(
            stored_tokens,
            list,
        ) and stored_tokens:

            tokens = stored_tokens

        else:

            tokens = tokenize(
                text,
                language,
            )

        if not tokens:
            continue

        training_records.append({
            "text": text,
            "lang": language,
            "source": document.get(
                "source",
                "",
            ),
            "tokens": tokens,
        })

    return training_records


# ============================================================================
# OPTIONAL LEGACY TEXT LOADER
# ============================================================================

def load_texts(
    data_dir: str = "data",
) -> List[Dict[str, Any]]:
    """
    Load legacy .txt material.

    MemoryGrid is the primary training source.

    This loader is retained so existing manual-training workflows do
    not break when standalone text files are intentionally supplied.
    """

    records: List[
        Dict[str, Any]
    ] = []

    if not os.path.isdir(
        data_dir
    ):
        return records

    for filename in os.listdir(
        data_dir
    ):

        if not filename.endswith(
            ".txt"
        ):
            continue

        path = os.path.join(
            data_dir,
            filename,
        )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            for line in f:

                text = line.strip()

                if not text:
                    continue

                lang = detect_lang(
                    text
                )

                tokens = tokenize(
                    text,
                    lang,
                )

                if not tokens:
                    continue

                records.append({
                    "text": text,
                    "lang": lang,
                    "source": f"file:{filename}",
                    "tokens": tokens,
                })

    return records


# ============================================================================
# TRAINING DATA MIXER
# ============================================================================

def collect_training_data(
    memory_grid: MemoryGrid,
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Collect the complete manual-training corpus.

    Primary source:

        MemoryGrid

    Optional legacy source:

        data/*.txt

    MemoryGrid remains authoritative for the CoMpaNeoN architecture.

    The optional file source exists only for compatibility with older
    manual training workflows.
    """

    records = load_texts_from_memorygrid(
        memory_grid
    )

    # --------------------------------------------------------------
    # Optional legacy files.
    #
    # They are appended, not substituted for MemoryGrid.
    # --------------------------------------------------------------

    if data_dir is not None:

        records.extend(
            load_texts(
                data_dir
            )
        )

    return records


# ============================================================================
# VOCABULARY
# ============================================================================

def build_vocab(
    records: List[Dict[str, Any]],
) -> Tuple[
    Dict[str, int],
    Dict[int, str],
]:
    """
    Build vocabulary from the same tokenized representation used by
    MemoryGrid and tokenizer.py.

    Both stem and original forms are retained where available.
    """

    vocab = {
        "<pad>": 0,
        "<unk>": 1,
        "<start>": 2,
        "<end>": 3,
    }

    reverse = {
        0: "<pad>",
        1: "<unk>",
        2: "<start>",
        3: "<end>",
    }

    for record in records:

        tokens = record.get(
            "tokens",
            [],
        )

        for token in tokens:

            if not isinstance(
                token,
                dict,
            ):
                continue

            stem = token.get(
                "stem",
                "",
            )

            original = token.get(
                "original",
                "",
            )

            if stem:

                if stem not in vocab:

                    token_id = len(
                        vocab
                    )

                    vocab[stem] = token_id
                    reverse[token_id] = stem

            if (
                original
                and original != stem
            ):

                if original not in vocab:

                    token_id = len(
                        vocab
                    )

                    vocab[original] = token_id
                    reverse[token_id] = original

    return vocab, reverse


# ============================================================================
# TOKEN ENCODING
# ============================================================================

def encode_records(
    records: List[Dict[str, Any]],
    vocab: Dict[str, int],
) -> List[List[int]]:
    """
    Encode MemoryGrid tokenized records into model token IDs.
    """

    encoded: List[
        List[int]
    ] = []

    start_id = vocab[
        "<start>"
    ]

    end_id = vocab[
        "<end>"
    ]

    unk_id = vocab[
        "<unk>"
    ]

    for record in records:

        tokens = record.get(
            "tokens",
            [],
        )

        ids = [
            start_id
        ]

        for token in tokens:

            if not isinstance(
                token,
                dict,
            ):
                continue

            stem = token.get(
                "stem",
                "",
            )

            original = token.get(
                "original",
                "",
            )

            if stem in vocab:

                word = stem

            elif original in vocab:

                word = original

            else:

                ids.append(
                    unk_id
                )
                continue

            ids.append(
                vocab[word]
            )

        ids.append(
            end_id
        )

        if len(ids) > 2:

            encoded.append(
                ids
            )

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
    """
    Generate random sequential training windows.

    This operates on tokenized MemoryGrid knowledge after the
    tokenization/grid stage has already completed.
    """

    if not encoded_docs:
        raise RuntimeError(
            "No encoded training documents available."
        )

    pad_id = vocab[
        "<pad>"
    ]

    while True:

        inputs = []
        targets = []

        for _ in range(
            batch_size
        ):

            doc = random.choice(
                encoded_docs
            )

            if len(doc) < seq_len + 1:

                doc = (
                    doc
                    + [
                        pad_id
                    ]
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

            if max_start <= 0:

                start = 0

            else:

                start = random.randint(
                    0,
                    max_start,
                )

            chunk = doc[
                start:
                start
                + seq_len
                + 1
            ]

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
# TRAINING
# ============================================================================

def train(
    memory_grid: Optional[MemoryGrid] = None,
    data_dir: Optional[str] = None,
    epochs: int = 100,
    batch_size: int = 8,
    seq_len: int = 32,
    lr: float = 1e-4,
    save_model: str = "companion_model.pth",
    save_vocab: str = "tokenizer_vocab.json",
    device=None,
):
    """
    Train MiniCompanionAI from MemoryGrid knowledge.

    MemoryGrid is the primary training source.

    Architecture:

        MemoryGrid
             ↓
        stored tokenized words
             ↓
        vocabulary
             ↓
        encoded sequences
             ↓
        MiniCompanionAI
             ↓
        model checkpoint
    """

    # ----------------------------------------------------------------
    # DEVICE
    # ----------------------------------------------------------------

    if device is None:

        device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

    # ----------------------------------------------------------------
    # MEMORY GRID
    # ----------------------------------------------------------------

    if memory_grid is None:

        memory_grid = MemoryGrid()

    # ----------------------------------------------------------------
    # COLLECT TRAINING DATA
    # ----------------------------------------------------------------

    records = collect_training_data(
        memory_grid=memory_grid,
        data_dir=data_dir,
    )

    if not records:

        raise RuntimeError(
            "No training data found in MemoryGrid."
        )

    print(
        f"Collected {len(records)} "
        "training records from MemoryGrid."
    )

    # ----------------------------------------------------------------
    # LANGUAGE DISTRIBUTION
    # ----------------------------------------------------------------

    language_counts: Dict[
        str,
        int
    ] = {}

    for record in records:

        lang = normalize_lang(
            record.get(
                "lang",
                "en",
            )
        )

        language_counts[lang] = (
            language_counts.get(
                lang,
                0,
            )
            + 1
        )

    print(
        f"Languages represented: "
        f"{language_counts}"
    )

    # ----------------------------------------------------------------
    # VOCABULARY
    # ----------------------------------------------------------------

    vocab, reverse = build_vocab(
        records
    )

    print(
        f"Vocabulary size: "
        f"{len(vocab)}"
    )

    # ----------------------------------------------------------------
    # ENCODE
    # ----------------------------------------------------------------

    encoded_docs = encode_records(
        records,
        vocab,
    )

    if not encoded_docs:

        raise RuntimeError(
            "MemoryGrid contained no encodable token sequences."
        )

    print(
        f"Encoded "
        f"{len(encoded_docs)} "
        "documents."
    )

    # ----------------------------------------------------------------
    # MODEL
    # ----------------------------------------------------------------

    model = MiniCompanionAI(
        vocab_size=len(vocab)
    )

    model.to(
        device
    )

    optimizer = optim.Adam(
        model.parameters(),
        lr=lr,
    )

    criterion = nn.CrossEntropyLoss(
        ignore_index=vocab[
            "<pad>"
        ]
    )

    # ----------------------------------------------------------------
    # TRAINING VERSION
    # ----------------------------------------------------------------

    timestamp = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    batch_version = (
        f"manual_{timestamp}"
    )

    print(
        f"Starting manual training "
        f"Run [{batch_version}]..."
    )

    # ----------------------------------------------------------------
    # TRAINING LOOP
    # ----------------------------------------------------------------

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
                // max(
                    batch_size,
                    1,
                ),
            ),
        )

        batch_iterator = get_batch(
            encoded_docs,
            batch_size,
            seq_len,
            vocab,
        )

        for step in range(
            steps
        ):

            x, y = next(
                batch_iterator
            )

            x = x.to(
                device
            )

            y = y.to(
                device
            )

            optimizer.zero_grad()

            logits = model(
                x
            )

            loss = criterion(
                logits.view(
                    -1,
                    len(vocab),
                ),
                y.view(
                    -1
                ),
            )

            loss.backward()

            optimizer.step()

            total_loss += (
                loss.item()
            )

        avg_loss = (
            total_loss
            / steps
        )

        if (
            (epoch + 1) % 10 == 0
            or epoch == 0
            or epoch == epochs - 1
        ):

            print(
                f"Epoch "
                f"{epoch + 1}/"
                f"{epochs}, "
                f"Loss: "
                f"{avg_loss:.4f}"
            )

    # ----------------------------------------------------------------
    # SOURCE STATISTICS
    # ----------------------------------------------------------------

    source_counts: Dict[
        str,
        int
    ] = {}

    for record in records:

        source = record.get(
            "source",
            "",
        )

        if not source:

            source = "memorygrid"

        source_counts[source] = (
            source_counts.get(
                source,
                0,
            )
            + 1
        )

    # ----------------------------------------------------------------
    # METADATA
    # ----------------------------------------------------------------

    metadata = {

        "batch_version":
            batch_version,

        "trained_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "training_source":
            "memorygrid",

        "total_training_records":
            len(records),

        "total_encoded_documents":
            len(encoded_docs),

        "final_loss":
            avg_loss,

        "languages":
            language_counts,

        "sources":
            source_counts,

        "hyperparameters": {
            "lr": lr,
            "epochs": epochs,
            "batch_size": batch_size,
            "seq_len": seq_len,
        },

        "vocab":
            vocab,

        "reverse":
            reverse,
    }

    # ----------------------------------------------------------------
    # HISTORICAL CHECKPOINT
    # ----------------------------------------------------------------

    torch.save(
        model.state_dict(),
        f"companion_model_"
        f"{batch_version}.pth",
    )

    with open(
        f"tokenizer_vocab_"
        f"{batch_version}.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False,
        )

    # ----------------------------------------------------------------
    # PRODUCTION CHECKPOINT
    # ----------------------------------------------------------------

    torch.save(
        model.state_dict(),
        save_model,
    )

    with open(
        save_vocab,
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
        "Model and aligned vocab metadata "
        f"saved under deployment pointer: "
        f"{batch_version}"
    )

    return {
        "batch_version":
            batch_version,

        "training_source":
            "memorygrid",

        "training_records":
            len(records),

        "encoded_documents":
            len(encoded_docs),

        "vocabulary_size":
            len(vocab),

        "languages":
            language_counts,

        "sources":
            source_counts,

        "final_loss":
            avg_loss,

        "model_path":
            save_model,

        "vocab_path":
            save_vocab,
    }


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    train(
        memory_grid=MemoryGrid()
    )
         