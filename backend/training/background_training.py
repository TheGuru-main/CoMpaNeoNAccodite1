from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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

try:
    from model.ai_model import MiniCompanionAI
except ImportError:
    MiniCompanionAI = None

try:
    from memory_grid import MemoryGrid
except ImportError:
    MemoryGrid = None

try:
    from tokenizer.tokenizer import tokenize, normalize_lang, uid_sequence, lexical_S
except ImportError:
    try:
        from tokenizer import tokenize, normalize_lang, uid_sequence, lexical_S
    except ImportError:
        def tokenize(t, lang="en"):
            return (t or "").split()
        def normalize_lang(l):
            return l or "en"
        def uid_sequence(token, lang="en"):
            return []
        def lexical_S(token, lang="en"):
            # token S = sum(uid_sequence) — never GSP placement S
            return sum(uid_sequence(token, lang))


# ============================================================================
# MEMORY GRID
# ============================================================================

# ============================================================================
# GRID RESOLVE — platform vs instance (GSP placement S is NOT used here)
# Token S = sum(uid_sequence) via tokenizer; placement S stays in GSP/keyboard.
# ============================================================================

def resolve_training_grid(
    grid=None,
    *,
    owner=None,
    owner_kind: str | None = None,
    owner_id: str | None = None,
    prefer_platform: bool = False,
):
    """
    Background / consolidation grid selection.

    - prefer_platform=True  → platform grid only (product seed continuity)
    - owner / owner_kind+id → instance grid for that org|user (no worker grid)
    - workers               → no instance; pass org owner (brainstorm = ns inside org)\n    - else                  → platform if prefer_platform; never invent empty tenant grid
    """
    if grid is not None:
        return grid

    # Explicit instance owner
    kind = owner_kind
    oid = owner_id
    if owner is not None:
        kind = getattr(owner, "kind", None) or (owner.get("kind") if isinstance(owner, dict) else None)
        oid = getattr(owner, "id", None) or (owner.get("id") if isinstance(owner, dict) else None)

    if kind in ("org", "user") and oid:
        try:
            from memory.instance_grid import OwnerRef, grid_path
            from memory.memory_grid import load_grid
            o = owner if hasattr(owner, "kind") else OwnerRef(str(kind), str(oid))
            path = grid_path(o)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file():
                try:
                    from memory.b2_grid_layout import fetch_instance_grid_to_path
                    tmp = path.with_name(path.name + ".b2.tmp")
                    if fetch_instance_grid_to_path(o.kind, o.id, str(tmp)):
                        import os as _os
                        _os.replace(tmp, path)
                        print(f"[bg-train] restored B2 instance {o.kind}:{o.id}")
                    else:
                        try:
                            tmp.unlink(missing_ok=True)
                        except Exception:
                            pass
                except Exception as _be:
                    print(f"[bg-train] B2 instance restore: {type(_be).__name__}: {_be}")
            if path.is_file():
                g = load_grid(str(path), bind_process=False)
                print(f"[bg-train] instance grid {o.kind}:{o.id} docs={len(getattr(g,'documents',{}) or {})}")
                return g
            print(f"[bg-train] no instance grid for {kind}:{oid} — fail closed (no platform substitute)")
            return None
        except Exception as e:
            print(f"[bg-train] instance resolve: {type(e).__name__}: {e}")
            return None

    if prefer_platform:
        try:
            from memory.platform_grid import load_platform_grid, PlatformGridError
            try:
                g = load_platform_grid(require_docs=False, allow_empty=True)
                print(f"[bg-train] platform grid docs={len(getattr(g,'documents',{}) or {})}")
                return g
            except PlatformGridError as e:
                print(f"[bg-train] platform missing: {e}")
        except Exception as e:
            print(f"[bg-train] platform_grid: {type(e).__name__}: {e}")

        try:
            from memory.shared_grid import get_shared_grid
            g = get_shared_grid(require_docs=False, allow_empty=True)
            return g
        except Exception as e:
            print(f"[bg-train] shared fallback: {type(e).__name__}: {e}")
            return None

    return None



def _persist_if_instance(grid, owner=None) -> None:
    """Write background-train results to durable user/org instance only."""
    if grid is None or owner is None:
        return
    kind = getattr(owner, "kind", None) or (owner.get("kind") if isinstance(owner, dict) else None)
    oid = getattr(owner, "id", None) or (owner.get("id") if isinstance(owner, dict) else None)
    if kind not in ("org", "user") or not oid:
        return
    try:
        from memory.instance_grid import OwnerRef, persist_owner_grid
        persist_owner_grid(OwnerRef(str(kind), str(oid)), grid)
        print(f"[bg-train] persisted instance {kind}:{oid}")
    except Exception as e:
        print(f"[bg-train] persist instance: {type(e).__name__}: {e}")


def resolve_partition_for_grid(grid, *, owner=None):
    """Bind MemoryPartition to the active grid (instance or platform). Soft fail."""
    if grid is None:
        return None
    try:
        from memory.memory_partition import MemoryPartition
    except Exception:
        try:
            from memory_partition import MemoryPartition
        except Exception:
            return None
    try:
        part = MemoryPartition(grid) if callable(MemoryPartition) else None
        # constructors vary — try common shapes
    except TypeError:
        try:
            part = MemoryPartition()
            if hasattr(part, "bind_grid"):
                part.bind_grid(grid)
            elif hasattr(part, "grid"):
                part.grid = grid
        except Exception as e:
            print(f"[bg-train] partition: {type(e).__name__}: {e}")
            return None
    except Exception as e:
        print(f"[bg-train] partition: {type(e).__name__}: {e}")
        return None
    try:
        from integration import get_state
        st = get_state()
        st["grid"] = grid
        st["partition"] = part
        if owner is not None:
            st["grid_owner"] = getattr(owner, "key", None) or str(owner)
        st["grid_kind"] = "instance" if owner else st.get("grid_kind") or "platform"
    except Exception:
        pass
    return part



memory = None  # resolved per-call via resolve_training_grid


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

def collect_memorygrid_texts(grid=None) -> List[str]:
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
    global memory
    if grid is not None:
        memory = grid
    elif memory is None:
        memory = resolve_training_grid(prefer_platform=True)
    if memory is None:
        return []


    texts: List[str] = []

    # MG-DOCS-FIX: MemoryGrid stores documents in .documents (dict),
    # older branches used .doc_store. Handle both.
    _docs = None
    for attr in ("documents", "doc_store", "_documents"):
        val = getattr(memory, attr, None)
        if val is None:
            continue
        _docs = val
        break
    if _docs is None:
        return 0
    _iter = _docs.values() if hasattr(_docs, "values") else _docs
    for document in _iter:

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

def collect_memorygrid_tokens(grid=None) -> List[Dict[str, Any]]:
    """
    Collect tokenized knowledge already stored in MemoryGrid.

    This allows training to use the tokenizer output already associated
    with indexed documents instead of rebuilding the lexical representation
    unnecessarily.

    If a document does not contain stored tokenizer output, its text is
    tokenized dynamically.
    """
    global memory
    if grid is not None:
        memory = grid
    elif memory is None:
        memory = resolve_training_grid(prefer_platform=True)
    if memory is None:
        return []


    token_records: List[Dict[str, Any]] = []

    for document in (
        list(memory.documents.values()) if hasattr(memory, "documents") and hasattr(memory.documents, "values")
        else getattr(memory, "doc_store", None) or getattr(memory, "_documents", None) or []
    ):

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

    for document in (
        list(memory.documents.values()) if hasattr(memory, "documents") and hasattr(memory.documents, "values")
        else getattr(memory, "doc_store", None) or getattr(memory, "_documents", None) or []
    ):

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

    _g = resolve_training_grid(prefer_platform=False)
    texts = collect_memorygrid_texts(_g)

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
    try:
        from main import load_model_if_exists
        load_model_if_exists()
        print("[background_training] load_model_if_exists() called")
    except Exception as _e:
        print("[background_training] load_model_if_exists skipped:", type(_e).__name__, _e)

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

def run_consolidation_cycle(grid=None) -> dict:
    """
    One consolidation pass:
      1. Collect MemoryGrid texts (shared grid if available).
      2. Filter via data.filter.DataFilter.is_training_worthy.
      3. Feed survivors to FineTunerAndWeightScalar.process.
      4. Return counters.
    """
    report = {"collected": 0, "kept": 0, "rejected": 0, "processed": 0, "errors": 0}

    # instance owner grid if provided on report context; else platform — NEVER empty MemoryGrid()
    if grid is None:
        owner = report.get("_owner")  # optional inject
        grid = resolve_training_grid(
            None,
            owner=owner,
            prefer_platform=(owner is None),
        )
    if grid is None:
        print("[consolidation] no platform/instance grid — skip (refusing empty MemoryGrid)")
        return report
    try:
        resolve_partition_for_grid(grid, owner=report.get("_owner"))
    except Exception as e:
        print("[consolidation] partition bind:", type(e).__name__, e)

    try:
        texts = collect_memorygrid_texts(grid)
    except Exception as e:
        print(f"[consolidation] collect failed: {type(e).__name__}: {e}")
        return report

    report["collected"] = len(texts)
    if not texts:
        return report

    # filter
    dfilter = None
    try:
        try:
            from data.filter import DataFilter
        except Exception:
            from data_filter import DataFilter
        dfilter = DataFilter()
    except Exception:
        dfilter = None

    kept = []
    for t in texts[:200]:
        if dfilter is None:
            kept.append(t); continue
        try:
            ok = True
            # preferred: filter_text returns recognized dict, then is_training_worthy
            if hasattr(dfilter, "filter_text") and hasattr(dfilter, "is_training_worthy"):
                rec = dfilter.filter_text(t)
                ok = dfilter.is_training_worthy(rec)
            elif hasattr(dfilter, "is_training_worthy"):
                ok = dfilter.is_training_worthy({"text": t})
        except Exception:
            ok = True
        if ok:
            kept.append(t)
        else:
            report["rejected"] += 1

    report["kept"] = len(kept)
    if not kept:
        return report

    # finetuner
    try:
        try:
            from training.fine_tuner_and_weight_scalar import FineTunerAndWeightScalar
        except Exception:
            from fine_tuner_and_weight_scalar import FineTunerAndWeightScalar
    except Exception:
        return report

    ft = None
    try:
        ft = FineTunerAndWeightScalar()
    except Exception:
        try:
            ft = FineTunerAndWeightScalar.__new__(FineTunerAndWeightScalar)
        except Exception:
            return report

    for t in kept:
        try:
            if hasattr(ft, "process"):
                ft.process(t)
            elif hasattr(ft, "process_user_input"):
                ft.process_user_input(t)
            report["processed"] += 1
        except Exception:
            report["errors"] += 1

    print(f"[consolidation] {report}")
    return report


def _shared_grid():
    """Return the app's live grid if bootstrapped; else a fresh one."""
    try:
        from integration import get_state
        g = get_state().get("grid")
        if g is not None:
            return g
    except Exception:
        pass
    try:
        return MemoryGrid()
    except Exception:
        return None


# MONITOR-V3
async def auto_train_monitor():
    """
    Three-cadence background monitor:

        60s  — grid growth check -> retrain (existing behaviour)
        5min — crawler queue tick -> run_scheduled
        10min— finetuner consolidation -> run_consolidation_cycle
    """
    last_count = get_unique_words_count()
    print(f"[monitor] started. Initial unique words: {last_count}")

    # lazy singletons so we don't rebuild them each tick
    _crawler = None
    ticks = 0

    while True:
        await asyncio.sleep(60)
        ticks += 1

        # --- 1) crawl queue tick (every 5 minutes) ---
        if ticks % 5 == 0:
            try:
                if _crawler is None:
                    from web_crawler import WebCrawler
                    _grid = _shared_grid()
                    try:
                        _crawler = WebCrawler(_grid) if _grid is not None else WebCrawler(MemoryGrid())
                    except TypeError:
                        _crawler = WebCrawler()
                result = _crawler.run_scheduled(limit=10)
                if result:
                    print(f"[monitor] crawler processed {len(result)} item(s)")
            except Exception as e:
                print(f"[monitor] crawl tick failed: {type(e).__name__}: {e}")

        # --- 2) finetuner consolidation (every 10 minutes) ---
        if ticks % 10 == 0:
            try:
                report = run_consolidation_cycle(grid=_shared_grid())
                print(f"[monitor] consolidation: {report}")
            except Exception as e:
                print(f"[monitor] consolidation failed: {type(e).__name__}: {e}")

        # --- 3) full retrain on grid growth (every 60s) ---
        try:
            current_count = get_unique_words_count()
        except Exception as e:
            print(f"[monitor] count failed: {type(e).__name__}: {e}")
            continue

        if current_count > last_count:
            print(f"[monitor] grid grew: {last_count} -> {current_count}")
            try:
                await asyncio.to_thread(train_model)
                last_count = current_count
            except Exception as e:
                print(f"[monitor] retrain failed: {type(e).__name__}: {e}")


def start_background_training(loop=None):
    """
    Start the asynchronous MemoryGrid training monitor.

    Safe to call from an async context (uses running loop) or from a
    thread with an explicit `loop` argument.

    # LOOP-FIX
    """
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                print("[monitor] no event loop available — skipping")
                return None

    return loop.create_task(auto_train_monitor())


# ============================================================================
# OPTIONAL DIRECT EXECUTION
# ============================================================================

if __name__ == "__main__":

    train_model()