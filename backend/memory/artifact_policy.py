"""
Storage policy for artifacts.

  Model weights (.pth/.pt/.safetensors/...)  -> Hugging Face only, never B2.
  B2 holds workflows, grid snapshots, docs snapshots, continuity records.

Enforced in code: any B2 write goes through check_b2_key() first.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import shutil
from pathlib import Path

WEIGHT_SUFFIXES = (
    ".pth", ".pt", ".bin", ".safetensors", ".ckpt", ".onnx", ".gguf", ".h5",
)
_WRAPPER_SUFFIXES = (".gz", ".gzip", ".zst", ".zstd", ".xz", ".bz2")

# Only these top-level prefixes may be written to B2.
B2_ALLOWED_PREFIXES = (
    "workflows/",
    "snapshots/",
    "continuity/",
    "docs/",
    "training/",  # existing vocab / manifest JSON, not weights
)


class ArtifactPolicyError(ValueError):
    pass


def _strip_wrappers(name: str) -> str:
    n = name.lower()
    changed = True
    while changed:
        changed = False
        for s in _WRAPPER_SUFFIXES:
            if n.endswith(s):
                n = n[: -len(s)]
                changed = True
    return n


def is_weight_name(name: str) -> bool:
    base = _strip_wrappers(name)
    return any(base.endswith(s) for s in WEIGHT_SUFFIXES)


def check_b2_key(key: str) -> str:
    k = (key or "").strip().lstrip("/")
    if not k or ".." in k.split("/") or k.startswith("/"):
        raise ArtifactPolicyError(f"invalid B2 key: {key!r}")
    if is_weight_name(k):
        raise ArtifactPolicyError(f"model weights are not stored on B2: {key!r} (use Hugging Face)")
    if not k.startswith(B2_ALLOWED_PREFIXES):
        raise ArtifactPolicyError(f"B2 key outside allowed prefixes: {key!r}")
    return k


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gzip_file(src: str | Path, dst: str | Path) -> str:
    """Compress src into dst (gzip, level 6). Returns sha256 of dst."""
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(dst) + ".tmp")
    with open(src, "rb") as fin, gzip.open(tmp, "wb", compresslevel=6) as fout:
        shutil.copyfileobj(fin, fout, 1 << 20)
    os.replace(tmp, dst)
    return sha256_file(dst)


def gunzip_file(src: str | Path, dst: str | Path) -> str:
    """Decompress src into dst atomically. Returns sha256 of dst."""
    tmp = Path(str(dst) + ".tmp")
    with gzip.open(src, "rb") as fin, open(tmp, "wb") as fout:
        shutil.copyfileobj(fin, fout, 1 << 20)
    os.replace(tmp, dst)
    return sha256_file(dst)
