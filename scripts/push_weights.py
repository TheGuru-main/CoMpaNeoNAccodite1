#!/usr/bin/env python3
"""
Push trained weights from the local trainer (phone/VM) to the live backend.

Usage:
    export ACCD_BACKEND=https://your-backend.onrender.com
    export WEIGHTS_RELAY_TOKEN=the-same-token-as-on-the-server
    python3 scripts/push_weights.py
"""
import os, sys, hashlib, mimetypes, urllib.request, urllib.error, json
from pathlib import Path

BACKEND = os.environ.get("ACCD_BACKEND", "").rstrip("/")
TOKEN = os.environ.get("WEIGHTS_RELAY_TOKEN", "")
WEIGHTS = Path(os.environ.get("ACCD_WEIGHTS_PATH", "companion_model.pth"))
VOCAB = Path(os.environ.get("ACCD_VOCAB_PATH", "tokenizer_vocab.json"))

def push(path: Path, endpoint: str) -> dict:
    if not path.exists():
        return {"skipped": True, "reason": f"{path} not found"}
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:16]
    boundary = "----accd" + digest
    ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BACKEND}{endpoint}",
        data=body,
        method="POST",
        headers={
            "X-API-Key": TOKEN,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

def main():
    if not BACKEND or not TOKEN:
        print("set ACCD_BACKEND and WEIGHTS_RELAY_TOKEN"); sys.exit(1)
    print(f"pushing {WEIGHTS} → {BACKEND}/weights/upload")
    print(push(WEIGHTS, "/weights/upload"))
    print(f"pushing {VOCAB} → {BACKEND}/weights/upload_vocab")
    print(push(VOCAB, "/weights/upload_vocab"))

if __name__ == "__main__":
    main()
