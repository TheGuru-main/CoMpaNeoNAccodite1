"""
Accodite Repo Seed
==================
Local repositories that feed the grid on first run. Never sent
anywhere — read from disk, chunked, indexed.

Add your own paths here. The same file is used by new accounts:
they point it at their local repos and the same pipeline runs.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Iterator, List, Tuple

# --- your repos, from your device ---
DEFAULT_LOCAL_REPOS = [
    os.path.expanduser("~/CoMpaNeoNAccodite1"),
    os.path.expanduser("~/himate"),
    os.path.expanduser("~/shop-near-me"),
    os.path.expanduser("~/reccord-db"),
    os.path.expanduser("~/companeon-src"),
]

# --- what to skip ---
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv", "env",
    "dist", "build", ".next", ".nuxt", "target", ".cache",
    "storage", "downloads", "icons", ".pytest_cache",
}
SKIP_EXTS = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".mp3", ".mp4", ".webm", ".wav", ".ogg",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".lock", ".sum",
}
MAX_FILE_BYTES = 64 * 1024     # 64 KB per file for training
MAX_FILES_PER_REPO = 500


def iter_repo_files(root: str) -> Iterator[Tuple[str, str]]:
    """Yield (relative_path, text) for every training-safe file in root."""
    base = Path(root).expanduser().resolve()
    if not base.exists() or not base.is_dir():
        return
    count = 0
    for path in base.rglob("*"):
        if count >= MAX_FILES_PER_REPO:
            break
        if not path.is_file():
            continue
        # skip by dir
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # skip by ext
        if path.suffix.lower() in SKIP_EXTS:
            continue
        # skip by size
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not text.strip():
            continue
        rel = str(path.relative_to(base))
        yield rel, text
        count += 1


def collect_seed_texts(roots: List[str] | None = None) -> List[str]:
    """Return a flat list of training chunks from the given (or default) repos."""
    roots = roots or DEFAULT_LOCAL_REPOS
    out: List[str] = []
    for r in roots:
        for rel, text in iter_repo_files(r):
            header = f"# {rel}\n"
            out.append(header + text)
    return out
