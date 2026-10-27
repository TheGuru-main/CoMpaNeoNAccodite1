# Accodite (CoMpaNeoN Accodite1)

End-to-end coding agent and org-aware workspace platform: rooms, Monaco codespace, GSP-addressed memory grid, seed crawl, and on-instance training.

## Product

- **Workspaces / org rooms** — chat, departments, meetings, `@AI` agent
- **Codespace** — Monaco editor, repo tree, terminal/sandbox (network-capable)
- **Memory grid + GSP** — document placement and letter-chain identity for retrieval
- **Train path** — external seed crawl → grid → MiniCompanionAI (causal decoder, KV-cache stream)

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, Uvicorn |
| DB | Neon Postgres (`DATABASE_URL`) |
| Auth | JWT (`SECRET_KEY`), org membership + `credential_active` |
| Model | `MiniCompanionAI` + `tokenizer_vocab.json` + `companion_model.pth` |
| Frontend | `frontend/ui` (app.js, codespace, stream client) |

## Required environment

| Variable | Required | Notes |
|----------|----------|--------|
| `SECRET_KEY` | Yes (prod) | Strong random; no default in production |
| `DATABASE_URL` | Yes | Neon Postgres connection string |
| `ACCD_CORS_ORIGINS` | Prod | Comma-separated frontend origins |
| `ACCD_ENV` | Recommended | `production` on Render |
| `ACCD_MODEL_DIR` | After train | Directory with weights + vocab |
| `PORT` | Optional | Default `7860` (HF); Render injects `PORT` |

Optional train/seed: `ACCD_SEED_ENABLED`, `ACCD_SEED_THRESHOLD`, `ACCD_GRID_PATH`.

## Run locally

```bash
export DATABASE_URL=postgresql://...
export SECRET_KEY=$(openssl rand -hex 32)
export PYTHONPATH=backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health: `GET /health` · Inference ready: `GET /ready`

## Train (Colab)

1. Clone repo, `cd backend`, `export PYTHONPATH=.`
2. Seed + train in one process (`epochs=3`, grid snapshot via `ACCD_GRID_PATH`)
3. Copy `companion_model.pth` and `tokenizer_vocab.json` into `ACCD_MODEL_DIR` on the host

## Docker

```bash
docker build -t accodite .
docker run -e DATABASE_URL=... -e SECRET_KEY=... -e PORT=7860 -p 7860:7860 accodite
```

## Security notes

- Expensive routes (`/generate`, `/generate/stream`, `/train`, `/crawl`) require Bearer JWT
- Public API under `/api/v1/public/*` uses `PUBLIC_API_KEY`
- Tool dispatch enforces role / mutation / argument filters
- Admin actions require active org membership

## License / IP

Product and code under GuruInnovations control; do not reassign IP without founder approval.
