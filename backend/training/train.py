from __future__ import annotations
import re

import os
import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ACCD-TORCH-GUARD: training requires torch; module imports without it.
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    optim = None
    TORCH_AVAILABLE = False

try:
    from langdetect import detect, LangDetectException
except ImportError:
    def detect(_): return "en"
    class LangDetectException(Exception): pass

from model.ai_model import MiniCompanionAI
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

    # MG-DOCS-FIX-TRAIN: MemoryGrid stores documents in .documents (a dict),
    # older branches used .doc_store. Try both, iterating dict values when
    # we have a mapping.
    _store = None
    for _attr in ("documents", "doc_store", "_documents"):
        _val = getattr(memory_grid, _attr, None)
        if _val is not None:
            _store = _val
            break

    if _store is None:
        return

    # ACCD-MG-ITER-SNAPSHOT
    # Freeze document list so concurrent grid writes cannot mutate during iteration.
    # Does not change MemoryGrid storage, GSP, crawl, or training math.
    _iterable = list(_store.values()) if hasattr(_store, "values") else list(_store)

    for document in _iterable:

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

        # ACCD-KEEP-CRAWLED-TEXT
        # Usable record == crawled text on the grid. Do not drop docs when
        # tokenizer returns empty; fall back to whitespace words so the full
        # document text still enters training (architecture unchanged).
        if isinstance(stored_tokens, list) and stored_tokens:
            tokens = stored_tokens
        else:
            try:
                tokens = tokenize(text, language)
            except Exception:
                tokens = []
            if not tokens:
                tokens = []
                for w in re.findall(r"\S+", text):
                    tokens.append({
                        "original": w,
                        "normalized": w,
                        "stem": w,
                    })

        if not tokens:
            # truly empty after fallback — only then skip
            continue

        training_records.append({
            "text": text,
            "lang": language,
            "source": document.get("source", ""),
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
# VOCABULARY  (letter-chain v1 — tokenizer uid_sequence identity)
# ============================================================================

# Fixed embedding table size. Model rows are NOT sequential discovery ids.
# Content identity = int(serialize_uid(uid_sequence(...))) e.g. home -> 714124
EMBED_ROWS = int(__import__("os").environ.get("ACCD_EMBED_ROWS", "8192"))


def letter_chain_id(token_str: str, lang: str = "en") -> int:
    """
    Training path only (not phone/placement uID).

    1) uid_sequence = ordered letter/digit-marker indexes (0 = letter a; zeros kept).
    2) embed fingerprint = stable hash(tuple(seq)) — NOT int(serialize_uid).
    3) chain_to_row maps fingerprint into rows [4, embed_rows) so specials 0..3 stay free.

    Placement / phone formatting must not be used here.
    """
    if not token_str or not str(token_str).strip():
        return -1
    try:
        from tokenizer import (
            uid_sequence,
            normalize_lexical_token,
            normalize_lang,
        )
    except ImportError:
        try:
            from tokenizer.tokenizer import (
                uid_sequence,
                normalize_lexical_token,
                normalize_lang,
            )
        except ImportError:
            return -1
    code = normalize_lang(lang)
    norm = normalize_lexical_token(str(token_str), code)
    if not norm:
        return -1
    seq = uid_sequence(norm, code)
    if not seq:
        # symbol-only fallback: hash codepoints, still training-only
        seq = tuple(ord(ch) & 0xFFFF for ch in norm)
    else:
        seq = tuple(int(x) for x in seq)
    # stable hash independent of PYTHONHASHSEED
    h = 0
    for x in seq:
        h = (h * 131 + (int(x) + 1)) & 0x7FFFFFFFFFFFFFFF
    return h if h > 0 else 4


def chain_to_row(chain_id: int, embed_rows: int = EMBED_ROWS) -> int:
    """
    Training embed seat only.
    Rows 0..3 = named specials (<pad>, <unk>, <start>, <end>).
    Content spans 4 .. embed_rows-1  (addition of +4 at the front of the usable grid).
    """
    er = max(8, int(embed_rows))
    usable = er - 4  # cross content span
    if chain_id is None or int(chain_id) < 0:
        return 1  # unk seat when caller passed failure signal
    cid = int(chain_id)
    return 4 + (cid % usable)




def build_vocab(
    records: List[Dict[str, Any]],
    embed_rows: int = EMBED_ROWS,
) -> Tuple[
    Dict[str, int],
    Dict[int, str],
]:
    """
    Letter-chain vocabulary metadata.

    vocab maps:
      specials by name -> 0..3
      normalized word  -> embed row (from chain id)
      str(chain_id)    -> same row (debug / export)

    reverse maps embed row -> representative normalized word.
    Identity is always letter-chain, not corpus order.
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
    chain_to_word: Dict[str, str] = {}

    for record in records:
        lang = record.get("lang") or "en"
        tokens = record.get("tokens") or []
        for token in tokens:
            if not isinstance(token, dict):
                continue
            word = (
                token.get("normalized")
                or token.get("stem")
                or token.get("original")
                or ""
            )
            word = str(word).strip()
            if not word:
                continue
            cid = letter_chain_id(word, lang)
            if cid == 1 and len(word) > 0:
                # still record surface for debugging
                pass
            row = chain_to_row(cid, embed_rows)
            vocab[word] = row
            vocab[str(cid)] = row
            if row not in reverse or reverse[row] in (
                "<pad>", "<unk>", "<start>", "<end>",
            ):
                reverse[row] = word
            chain_to_word[str(cid)] = word

    # stash for metadata writers (optional attribute on function)
    build_vocab._last_chain_to_word = chain_to_word  # type: ignore
    build_vocab._embed_rows = embed_rows  # type: ignore
    return vocab, reverse


# ============================================================================
# TOKEN ENCODING
# ============================================================================

def encode_records(
    records: List[Dict[str, Any]],
    vocab: Dict[str, int],
    embed_rows: int = EMBED_ROWS,
) -> List[List[int]]:
    """
    Encode via letter-chain ids -> embed rows (not sequential discovery).
    """
    encoded: List[List[int]] = []
    start_id = 2
    end_id = 3
    unk_id = 1

    for record in records:
        lang = record.get("lang") or "en"
        tokens = record.get("tokens") or []
        ids = [start_id]
        for token in tokens:
            if not isinstance(token, dict):
                continue
            word = (
                token.get("normalized")
                or token.get("stem")
                or token.get("original")
                or ""
            )
            word = str(word).strip()
            if not word:
                ids.append(unk_id)
                continue
            cid = letter_chain_id(word, lang)
            row = chain_to_row(cid, embed_rows)
            ids.append(row)
        ids.append(end_id)
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
    resume_checkpoint: Optional[str] = "companion_training_resume.pth",
):
    if not TORCH_AVAILABLE:
        raise RuntimeError(
            "torch is required for training. Install it on the runtime "
            "(pip install torch) before calling train()."
        )

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
        try:
            from integration import get_shared_grid
            memory_grid = get_shared_grid()
        except Exception:
            memory_grid = None
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
        embed_rows=int(__import__("os").environ.get("ACCD_EMBED_ROWS", str(EMBED_ROWS))),
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

    embed_rows = int(__import__("os").environ.get("ACCD_EMBED_ROWS", str(EMBED_ROWS)))
    print(f"Letter-chain scheme: embed_rows={embed_rows} (home chain id example 714124)")
    model = MiniCompanionAI(
        vocab_size=embed_rows,
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
    # RESUME CHECKPOINT
    # ----------------------------------------------------------------

    avg_loss = 0.0
    start_epoch = 0

    if resume_checkpoint and os.path.isfile(resume_checkpoint):
        print(f"[resume] Loading checkpoint: {resume_checkpoint}")

        try:
            try:
                checkpoint = torch.load(
                    resume_checkpoint,
                    map_location=device,
                    weights_only=False,
                )
            except TypeError:
                checkpoint = torch.load(
                    resume_checkpoint,
                    map_location=device,
                )

            if checkpoint.get("vocab") != vocab:
                raise RuntimeError(
                    "Resume checkpoint vocabulary differs from the "
                    "current MemoryGrid vocabulary. Refusing to resume "
                    "with misaligned token IDs."
                )

            saved_hparams = checkpoint.get("hyperparameters", {})
            for key, current in (
                ("batch_size", batch_size),
                ("seq_len", seq_len),
            ):
                previous = saved_hparams.get(key)
                if previous is not None and previous != current:
                    raise RuntimeError(
                        f"Cannot resume: {key} changed from "
                        f"{previous} to {current}."
                    )

            model.load_state_dict(checkpoint["model_state_dict"])
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

            start_epoch = int(checkpoint.get("completed_epochs", 0))
            avg_loss = float(checkpoint.get("avg_loss", 0.0))
            batch_version = checkpoint.get("batch_version", batch_version)

            if start_epoch < 0 or start_epoch > epochs:
                raise RuntimeError(
                    f"Checkpoint completed_epochs={start_epoch} is "
                    f"outside the requested training range 0..{epochs}."
                )

            print(
                f"[resume] Restored completed epochs: {start_epoch}/{epochs}; "
                f"next epoch: {start_epoch + 1}"
            )

        except Exception as e:
            raise RuntimeError(
                f"Could not safely resume training from "
                f"{resume_checkpoint}: {type(e).__name__}: {e}"
            ) from e

    else:
        print("[resume] No recovery checkpoint found; starting a new run.")

    for epoch in range(
        start_epoch,
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

            # letter-chain: class dim = embedding table (8192), NOT len(vocab)
            V = logits.size(-1)
            loss = criterion(
                logits.reshape(-1, V),
                y.reshape(-1),
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

        # Save a recoverable snapshot after every completed epoch.
        if resume_checkpoint:
            checkpoint_data = {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "completed_epochs": epoch + 1,
                "avg_loss": avg_loss,
                "batch_version": batch_version,
                "vocab": vocab,
                "hyperparameters": {
                    "lr": lr,
                    "batch_size": batch_size,
                    "seq_len": seq_len,
                    "epochs": epochs,
                },
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }

            checkpoint_tmp = resume_checkpoint + ".tmp"
            torch.save(checkpoint_data, checkpoint_tmp)
            os.replace(checkpoint_tmp, resume_checkpoint)

            print(
                f"[checkpoint] Saved after epoch {epoch + 1}/{epochs}: "
                f"{resume_checkpoint}"
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

    try:
        from main import load_model_if_exists
        load_model_if_exists()
        print("[train] load_model_if_exists() called")
    except Exception as _e:
        print("[train] load_model_if_exists skipped:", type(_e).__name__, _e)


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

# Standalone training entry point is defined at the end of this file.
         

# ============================================================================
# SEED-CRAWLER-AUTOSTART — fill the grid with external content before training
# ============================================================================
#
# On import: waits a few seconds so the module finishes loading, then checks
# whether the grid has enough content. If it's below a threshold, it fires
# the seed crawler in a background thread.
#
# Nothing in train() or train_model() changes. This is a pre-flight that runs
# once per process. Disable with ACCD_SEED_ENABLED=0.
# ============================================================================

import threading as _seed_threading
import time as _seed_time

SEED_ENABLED = os.environ.get("ACCD_SEED_ENABLED", "1") == "1"
SEED_THRESHOLD = int(os.environ.get("ACCD_SEED_THRESHOLD", "20"))
SEED_PER_LICENSE = int(os.environ.get("ACCD_SEED_PER_LICENSE", "3"))

_seed_done = False
_seed_lock = _seed_threading.Lock()


def ensure_seed_crawl(*, force: bool = False, grid=None):
    """Run the seed crawl once if the grid is thin. Idempotent."""
    global _seed_done
    with _seed_lock:
        if _seed_done and not force:
            return {"skipped": True, "reason": "already ran"}
        _seed_done = True

    # Use the caller's grid when supplied, so seeding and training
    # operate on the exact same MemoryGrid instance.
    if grid is None:
        try:
            from integration import get_state
            grid = get_state().get("grid")
        except Exception:
            pass

    if grid is None:
        try:
            from integration import get_shared_grid
            grid = get_shared_grid()
        except Exception:
            grid = None
        if grid is None:
            try:
                grid = MemoryGrid()
            except Exception:
                return {"ok": False, "reason": "no grid"}

    
    # ACCD-ENSURE-SEED-LOAD — restore persisted seed before counting
    try:
        _docs0 = getattr(grid, "documents", None) or {}
        if len(_docs0) == 0:
            try:
                from memory.memory_grid import load_grid
            except Exception:
                from memory_grid import load_grid
            g2 = load_grid()
            if g2 is not None and len(getattr(g2, "documents", {}) or {}) > 0:
                grid = g2
                print("[seed] loaded grid snapshot docs=", len(grid.documents))
    except Exception as e:
        print("[seed] load_grid skip:", e)

    docs = getattr(grid, "documents", None)
    current = len(docs) if docs else 0
    if current >= SEED_THRESHOLD and not force:
        print(f"[seed] skip (grid already has {current} docs)")
        return {"ok": True, "skipped": True, "grid_count": current}

    # import and run seed crawler
    seed_crawl = None
    for path in ("external.seed_crawler", "seed_crawler"):
        try:
            mod = __import__(path, fromlist=["seed_crawl"])
            seed_crawl = getattr(mod, "seed_crawl", None)
            if seed_crawl:
                break
        except ImportError:
            continue
    if seed_crawl is None:
        print("[seed] seed_crawler module not importable")
        return {"ok": False, "reason": "module missing"}

    print(f"[seed] running (grid has {current} docs, threshold {SEED_THRESHOLD})")
    try:
        stats = seed_crawl(grid=grid)
        # ACCD-ENSURE-SEED-SAVE (seed_crawl also saves; re-save if path missing)
        try:
            if not (stats or {}).get("grid_path"):
                import os
                try:
                    from memory.memory_grid import save_grid
                except Exception:
                    from memory_grid import save_grid
                path = save_grid(grid, os.environ.get("ACCD_GRID_PATH") or None)
                if isinstance(stats, dict):
                    stats["grid_path"] = path
                print("[seed] ensure save_grid", path)
        except Exception as e:
            print("[seed] ensure save_grid skip:", e)
        return {"ok": True, "stats": stats}
    except Exception as e:
        print(f"[seed] failed: {type(e).__name__}: {e}")
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}


def _seed_thread_main():
    try:
        _seed_time.sleep(3.0)   # let the module finish loading
        ensure_seed_crawl()
    except Exception as e:
        print(f"[seed] daemon failed: {type(e).__name__}: {e}")


def _seed_autostart():
    if not SEED_ENABLED:
        return
    t = _seed_threading.Thread(
        target=_seed_thread_main,
        daemon=True,
        name="seed-crawler",
    )
    t.start()

# Preserve background seeding for importers, but do not race the
# standalone training entry point against its own synchronous seed pass.
if __name__ != "__main__":
    try:
        _seed_autostart()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from integration import get_shared_grid
        grid = get_shared_grid()
    except Exception:
        grid = None
    if grid is None:
        try:
            from memory.memory_grid import get_process_grid, load_grid
            grid = get_process_grid()
            if grid is not None and not getattr(grid, "documents", None):
                load_grid()
                grid = get_process_grid()
        except Exception:
            grid = None
    if grid is None:
        grid = MemoryGrid()
    # Seed into THIS grid, then train
    try:
        ensure_seed_crawl(force=False, grid=grid)
    except Exception as e:
        print("[train __main__] seed:", type(e).__name__, e)
    print("[train __main__] grid docs:", len(getattr(grid, "documents", {}) or {}))


    docs_before = getattr(grid, "documents", None)
    count_before = len(docs_before) if docs_before is not None else 0
    print(f"[seed] Initial MemoryGrid documents: {count_before}")

    if SEED_ENABLED:
        seed_result = ensure_seed_crawl(grid=grid)
        print(f"[seed] result: {seed_result}")

        if seed_result.get("ok") is False:
            raise SystemExit(
                "[train] STOP: seed crawler failed; training was not started."
            )

        stats = seed_result.get("stats", {})
        if stats and stats.get("written", 0) <= 0 and count_before == 0:
            raise SystemExit(
                "[train] STOP: crawler wrote no documents; "
                "training was not started."
            )

    docs = getattr(grid, "documents", None)
    doc_count = len(docs) if docs is not None else 0
    print(f"[train] MemoryGrid documents after seeding: {doc_count}")

    if doc_count <= 0:
        raise SystemExit(
            "[train] STOP: MemoryGrid is empty; training was not started."
        )

    records = collect_training_data(memory_grid=grid)
    print(f"[train] Usable training records: {len(records)}")

    if not records:
        raise SystemExit(
            "[train] STOP: MemoryGrid has no usable training records; "
            "training was not started."
        )

    train(memory_grid=grid)
