import os
from pathlib import Path

def ensure_weights():
    dest = Path(os.environ.get("ACCD_MODEL_DIR", "/var/data/models"))
    dest.mkdir(parents=True, exist_ok=True)
    # Prefer smallest demo pack first
    preferred = [
        os.environ.get("ACCD_HF_WEIGHTS", "companion_model_int8pack.pth"),
        "companion_model_fp16.pth",
        "companion_model.pth",
    ]
    vocab = os.environ.get("ACCD_HF_VOCAB", "tokenizer_vocab.json")
    have_w = any((dest / n).is_file() for n in preferred)
    need = []
    if not have_w:
        need.append(preferred[0])
    if not (dest / vocab).is_file():
        need.append(vocab)
    if not need:
        print("[weights] present", dest, list(dest.iterdir()))
        return str(dest)
    repo = os.environ.get("ACCD_HF_REPO") or ""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not repo or not token:
        print("[weights] skip: ACCD_HF_REPO / HF_TOKEN")
        return str(dest)
    from huggingface_hub import hf_hub_download
    for name in need:
        print("[weights] download", name)
        try:
            hf_hub_download(repo_id=repo, filename=name, local_dir=str(dest), token=token)
        except Exception as e:
            print("[weights] fail", name, type(e).__name__, e)
            # try next weight name
            if name == preferred[0]:
                for alt in preferred[1:]:
                    try:
                        print("[weights] try", alt)
                        hf_hub_download(repo_id=repo, filename=alt, local_dir=str(dest), token=token)
                        break
                    except Exception as e2:
                        print("[weights] fail", alt, e2)
    print("[weights] ready", list(dest.iterdir()))
    return str(dest)
