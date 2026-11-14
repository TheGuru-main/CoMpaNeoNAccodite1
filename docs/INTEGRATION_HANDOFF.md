# CoMpaNeoNAccodite1 — Integration Handoff

## Architecture decisions

1. The tokenizer is NOT a grid.
2. The main tokenizer is an identity calculator and placement identifier.
3. It constructs complete letter-index chains (uID) for letters, words,
   texts, numbers, ordinary symbols and code symbols.
4. Word identity is determined by its complete letter-index chain,
   regardless of letter sequence.
5. Code tokenizer and digit-marker helpers support the main tokenizer.
6. Training, inference and response must use consistent token identities.

## Grid ownership

### Platform MemoryGrid
- Accodite-owned foundational knowledge and seed corpus.
- Source for initial platform training.
- Persisted as a platform snapshot.

### Tenant parent instance MemoryGrid
- Owns tenant memory placement, storage, indexing and retrieval.
- Receives an independent snapshot of the platform MemoryGrid.
- Maintains tenant isolation.
- Workers use their organisation's parent instance grid.
- Tenant memory placement is independent of tokenizer identity.

### Platform model
- Initial model is trained from platform MemoryGrid.
- Model weights, vocabulary and tokenizer identity metadata must remain
  version-aligned.
- Tenant MemoryGrid snapshots and model checkpoints are separate artifacts.

## Required lifecycle

1. Seed platform MemoryGrid.
2. Validate seed population.
3. Persist platform MemoryGrid and manifest.
4. Tokenize seeded material and construct complete uID identities.
5. Build vocabulary and encode training sequences.
6. Train initial platform model.
7. Publish weights, vocabulary and identity metadata as one version.
8. Load the matching model artifacts for inference.
9. Provision tenant parent instance snapshots from platform MemoryGrid.
10. Support authorised tenant-specific learning.
11. Generate responses using the same tokenizer identity mapping and
    authorised tenant memory.

## Verified repository findings — 12 November 2026

### Seeding
- backend/external/seed_crawler.py
- seed_crawl() resolves the platform grid when no grid is supplied.
- It adds documents through grid.add_document().
- Seed documents are tokenized through MemoryGrid ingestion.
- The inspected output ended before the crawler's final persistence code.
  Confirm whether save_platform_grid() is called.

### Platform grid
- backend/memory/platform_grid.py
- bootstrap_platform_grid() creates an empty platform grid when necessary.
- save_platform_grid() persists the grid and manifest.
- Platform grid path is configurable through ACCD_PLATFORM_GRID_PATH,
  ACCD_GRID_PATH and ACCD_MEMORY_ROOT.

### Training
- backend/training/train.py
- load_texts_from_memorygrid() reads MemoryGrid documents.
- collect_training_data() combines MemoryGrid records with optional
  legacy data/*.txt records.
- build_vocab() and encode_records() construct training sequences.
- train() requires a non-empty platform grid when no tenant owner is supplied.
- EMBED_ROWS defaults to 8192.
- letter_chain_id() maps letter-chain fingerprints into embedding rows.
- Model construction uses embed_rows.

### Seed execution
- ensure_seed_crawl() is defined in train.py.
- Importing train.py can start a background seed thread.
- Standalone execution also invokes ensure_seed_crawl().
- Inspect possible duplicate invocation, concurrency and generic load_grid()
  fallback before changing this mechanism.
- Ensure seeding and training operate on the exact same platform grid object.

### Model publication and inference
- train.py saves model weights and vocabulary metadata.
- It currently calls main.load_model_if_exists() before writing the new
  save_vocab file. This ordering must be corrected.
- Training constructs MiniCompanionAI using embed_rows.
- backend/main.py currently constructs it using len(tokenizer_vocab).
- Reconcile model dimensions and token-to-ID mapping before integration.
- Publish weights, vocabulary and tokenizer identity metadata consistently.

### Tenant provisioning
- backend/memory/instance_grid.py
- create_instance_grid() restores existing tenant data first, otherwise
  copies the platform snapshot.
- Empty tenant grids are permitted only when explicitly requested.
- Inspect the JSON fallback versus grid.pkl persistence format.
- Preserve OwnerRef and tenant isolation.

### Additional unresolved work
- Inspect backend/training/background_training.py as a second training path.
- Establish whether it is intentional or duplicates train.py.
- Verify response_stream.py uses the same token mapping as training.
- Preserve attention/KV cache mechanics.
- Do not feed negative registered code-symbol IDs directly into embedding
  indices; maintain stable symbol identity and a consistent model mapping.

## Implementation discipline

- Preserve existing functionality and untracked files.
- No wholesale rewrites.
- No temporary patch files.
- Use exact Termux commands.
- Validate each change with syntax checks and targeted tests.
- Do not claim success without actual test output.

## Immediate next task

Complete the seed-to-training-to-response handoff investigation:
1. Inspect the remainder of seed_crawl() for persistence.
2. Verify the exact platform grid used by seeding and training.
3. Reconcile training and inference model dimensions and vocabulary.
4. Correct artifact publication ordering.
5. Validate platform snapshot provisioning.
6. Then integrate tenant learning and response.
