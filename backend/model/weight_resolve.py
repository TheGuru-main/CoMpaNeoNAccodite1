"""
Platform weights: HF (base) → local ACCD_MODEL_DIR cache.
Instance weights: B2 grids/instances/{kind}/{phone}/models/ then optional HF.

Inference must not require tenant grid.pkl to load platform weights.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple


def _model_dir() -> Path:
    d = Path(os.environ.get("ACCD_MODEL_DIR") or "/var/data/models")
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_platform_weights_from_hf() -> Path:
    """Download platform companion weights + vocab from HF into ACCD_MODEL_DIR."""
    dest = _model_dir()
    weights_names = [
        os.environ.get("ACCD_HF_WEIGHTS") or "companion_model_fp16.pth",
        "companion_model.pth",
    ]
    vocab = os.environ.get("ACCD_HF_VOCAB") or "tokenizer_vocab.json"
    have_w = any((dest / n).is_file() for n in weights_names)
    have_v = (dest / vocab).is_file()
    if have_w and have_v:
        return dest

    repo = (os.environ.get("ACCD_HF_REPO") or os.environ.get("HF_REPO") or "").strip()
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not repo:
        return dest
    try:
        from huggingface_hub import hf_hub_download
    except Exception as e:
        print("[weights] huggingface_hub missing:", e)
        return dest

    need = []
    if not have_w:
        need.append(weights_names[0])
    if not have_v:
        need.append(vocab)
    for name in need:
        try:
            print("[weights] HF download", name)
            hf_hub_download(repo_id=repo, filename=name, local_dir=str(dest), token=token)
        except Exception as e:
            print("[weights] HF fail", name, type(e).__name__, e)

    # normalize fp16 → companion_model.pth alias if needed
    fp16 = dest / weights_names[0]
    classic = dest / "companion_model.pth"
    if fp16.is_file() and not classic.is_file():
        try:
            classic.write_bytes(fp16.read_bytes())
        except Exception:
            pass
    return dest


def pull_instance_weights_from_b2(kind: str, phone_uid: str) -> Optional[Path]:
    """
    Load tenant model into local cache dir for this owner.
    Returns local dir if at least vocab or weights present after pull.
    """
    phone_uid = str(phone_uid or "").strip()
    if kind not in ("user", "org") or not phone_uid:
        return None
    if os.environ.get("ACCD_B2_ENABLED", "1").strip() in ("0", "false", "False"):
        return None
    try:
        from memory.b2_grid_layout import instance_model_key
        from storage.b2 import b2_get_bytes, b2_enabled
    except Exception as e:
        print("[weights] b2 import:", e)
        return None
    if not b2_enabled():
        return None

    dest = _model_dir() / "instances" / kind / phone_uid
    dest.mkdir(parents=True, exist_ok=True)
    for fname in (
        "companion_model.pth",
        "companion_model_fp16.pth",
        "tokenizer_vocab.json",
    ):
        key = instance_model_key(kind, phone_uid, fname)
        local = dest / fname
        if local.is_file():
            continue
        try:
            data = b2_get_bytes(key)
            if data:
                local.write_bytes(data)
                print("[weights] B2 instance", key, "->", local)
        except Exception as e:
            print("[weights] B2 miss", key, type(e).__name__, e)
    if any(dest.glob("*")):
        return dest
    return None


def publish_instance_weights_to_b2(kind: str, phone_uid: str, src_dir: Optional[str] = None) -> dict:
    """Copy platform/local weights into tenant B2 model prefix (snapshot at signup or train)."""
    phone_uid = str(phone_uid or "").strip()
    if kind not in ("user", "org") or not phone_uid:
        return {"ok": False, "reason": "bad owner"}
    try:
        from memory.b2_grid_layout import instance_model_key
        from storage.b2 import b2_put_bytes, b2_enabled
    except Exception as e:
        return {"ok": False, "reason": str(e)}
    if not b2_enabled():
        return {"ok": False, "reason": "b2_disabled"}

    src = Path(src_dir) if src_dir else _model_dir()
    published = []
    for fname in ("companion_model.pth", "companion_model_fp16.pth", "tokenizer_vocab.json"):
        f = src / fname
        if not f.is_file():
            continue
        key = instance_model_key(kind, phone_uid, fname)
        try:
            b2_put_bytes(key, f.read_bytes(), content_type="application/octet-stream")
            published.append(key)
        except Exception as e:
            print("[weights] publish fail", key, e)
    return {"ok": bool(published), "keys": published}


def resolve_weight_dir(
    *,
    kind: Optional[str] = None,
    phone_uid: Optional[str] = None,
) -> Tuple[Path, str]:
    """
    Returns (local_dir, source) source in {instance_b2, platform_hf, platform_local}.
    """
    if kind in ("user", "org") and phone_uid:
        inst = pull_instance_weights_from_b2(kind, phone_uid)
        if inst is not None and (
            (inst / "companion_model.pth").is_file()
            or (inst / "companion_model_fp16.pth").is_file()
        ):
            return inst, "instance_b2"

    ensure_platform_weights_from_hf()
    d = _model_dir()
    if (d / "companion_model.pth").is_file() or (d / "companion_model_fp16.pth").is_file():
        return d, "platform_hf_or_local"
    return d, "empty"
