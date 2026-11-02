import os
from pathlib import Path

def ensure_weights():
    dest = Path(os.environ.get("ACCD_MODEL_DIR", "/tmp/accd_models"))
    dest.mkdir(parents=True, exist_ok=True)
    weights = os.environ.get("ACCD_HF_WEIGHTS", "companion_model_fp16.pth")
    vocab = os.environ.get("ACCD_HF_VOCAB", "tokenizer_vocab.json")
    need = []
    if not any((dest / n).is_file() for n in (weights, "companion_model.pth")):
        need.append(weights)
    if not (dest / vocab).is_file():
        need.append(vocab)
    if not need:
        print("[weights] present", dest)
        return str(dest)
    repo = os.environ.get("ACCD_HF_REPO") or ""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not repo or not token:
        print("[weights] skip: set ACCD_HF_REPO and HF_TOKEN")
        return str(dest)
    from huggingface_hub import hf_hub_download
    for name in need:
        print("[weights] download", name)
        hf_hub_download(repo_id=repo, filename=name, local_dir=str(dest), token=token)
    fp16 = dest / weights
    classic = dest / "companion_model.pth"
    if fp16.is_file() and not classic.is_file():
        classic.write_bytes(fp16.read_bytes())
    print("[weights] ready", list(dest.iterdir()))
    return str(dest)
