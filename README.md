---
title: Accodite
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# Accodite

Fork of CoMpaNeoN-AI → end-to-end coding agent with org-aware rooms,
dialect narration, verified code streaming, and per-instance training.

## Environment variables (Space → Settings → Repository secrets)

Required:
- `DATABASE_URL` — Neon Postgres connection string (sslmode=require)

Optional:
- `DATABASE_URL_ASYNC` — asyncpg variant
- `ACCD_SECRET_KEY` — override the default signing key
- `ACCD_ENV` — `production` in the Space
