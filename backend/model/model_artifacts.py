"""
Base model artifacts for serving (numpy only, no torch needed to read them).

Why: the trainer writes full fp32 state dicts (two copies per run plus a
resume checkpoint). This module turns one state dict into fp16 shards that
each stay under a size cap, with a manifest of sha256 checksums.

Layout on Hugging Face (fixed):
    base/model_manifest.json
    base/shard_00000.npz  ...          each <= max_shard_bytes

Only the one-off conversion needs torch (tools/pack_model.py). Serving
(Render) only needs numpy plus the shards.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

DEFAULT_MAX_SHARD_BYTES = 400 * 1024 * 1024   # stays under Render's 500 MB cap
FP16_MAX = float(np.finfo(np.float16).max)     # 65504
MANIFEST_NAME = "model_manifest.json"


class ArtifactError(RuntimeError):
    pass


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_fp16_checked(state: Dict[str, np.ndarray], *, max_rel_error: float = 1e-2) -> Dict[str, np.ndarray]:
    """
    Convert float tensors to fp16. Refuse any tensor that would overflow,
    or whose relative error after conversion exceeds max_rel_error.
    Non-float tensors are kept as they are.
    """
    out: Dict[str, np.ndarray] = {}
    for name, arr in state.items():
        a = np.asarray(arr)
        if not np.issubdtype(a.dtype, np.floating):
            out[name] = a
            continue
        if a.size and np.max(np.abs(a)) > FP16_MAX:
            raise ArtifactError(f"{name}: values exceed fp16 range; cannot convert safely")
        h = a.astype(np.float16)
        if not np.all(np.isfinite(h)):
            raise ArtifactError(f"{name}: non-finite values after fp16 conversion")
        # error scaled by the tensor's largest magnitude (per-element relative error is
        # meaningless for values near zero)
        scale = float(np.max(np.abs(a))) if a.size else 0.0
        err = float(np.max(np.abs(a.astype(np.float32) - h.astype(np.float32)))) if a.size else 0.0
        scaled = err / max(scale, 1e-8)
        if scaled > max_rel_error:
            raise ArtifactError(f"{name}: conversion error {scaled:.4f} exceeds {max_rel_error}")
        out[name] = h
    return out


def shard_state(state: Dict[str, np.ndarray], max_shard_bytes: int = DEFAULT_MAX_SHARD_BYTES) -> List[Dict[str, np.ndarray]]:
    """Greedy split in key order. A single tensor larger than the cap is an error."""
    shards: List[Dict[str, np.ndarray]] = []
    cur: Dict[str, np.ndarray] = {}
    cur_bytes = 0
    for name in sorted(state):
        arr = state[name]
        n = int(np.asarray(arr).nbytes)
        if n > max_shard_bytes:
            raise ArtifactError(f"{name} is {n} bytes, larger than the shard cap {max_shard_bytes}")
        if cur and cur_bytes + n > max_shard_bytes:
            shards.append(cur)
            cur, cur_bytes = {}, 0
        cur[name] = arr
        cur_bytes += n
    if cur:
        shards.append(cur)
    return shards


def write_artifacts(
    state: Dict[str, np.ndarray],
    out_dir: str | Path,
    *,
    source_sha256: str,
    max_shard_bytes: int = DEFAULT_MAX_SHARD_BYTES,
    version: int = 1,
) -> dict:
    """Write fp16 shards + manifest into out_dir. Returns the manifest dict."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fp16_state = to_fp16_checked(state)
    shards = shard_state(fp16_state, max_shard_bytes)
    entries = []
    for i, shard in enumerate(shards):
        fname = f"shard_{i:05d}.npz"
        tmp = out / (fname + ".tmp")
        with open(tmp, "wb") as f:
            np.savez_compressed(f, **{k.replace(".", "__"): v for k, v in shard.items()})
        os.replace(tmp, out / fname)
        entries.append({
            "file": fname,
            "sha256": sha256_file(out / fname),
            "bytes": (out / fname).stat().st_size,
            "keys": sorted(shard.keys()),
        })
    manifest = {
        "version": int(version),
        "dtype": "float16",
        "source_sha256": source_sha256,
        "max_shard_bytes": int(max_shard_bytes),
        "total_bytes": sum(e["bytes"] for e in entries),
        "shards": entries,
    }
    tmp = out / (MANIFEST_NAME + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(tmp, out / MANIFEST_NAME)
    return manifest


def fetch_base_model(
    manifest: dict,
    *,
    download: Callable[[str, str], None],
    cache_dir: str | Path,
    remote_prefix: str = "base/",
) -> Dict[str, np.ndarray]:
    """
    Download (if not cached), verify and load every shard. Returns fp16 arrays
    keyed by the original state-dict names.
    """
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    state: Dict[str, np.ndarray] = {}
    for e in manifest["shards"]:
        local = cache / e["file"]
        if not (local.is_file() and sha256_file(local) == e["sha256"]):
            tmp = cache / (e["file"] + ".dl")
            download(remote_prefix + e["file"], str(tmp))
            if sha256_file(tmp) != e["sha256"]:
                tmp.unlink(missing_ok=True)
                raise ArtifactError(f"{e['file']} failed sha256 check")
            os.replace(tmp, local)
        with np.load(local) as z:
            for k in z.files:
                state[k.replace("__", ".")] = z[k]
    expected = {k for e in manifest["shards"] for k in e["keys"]}
    if set(state) != expected:
        raise ArtifactError("loaded keys do not match the manifest")
    return state
