#!/usr/bin/env python3
"""Install B2 + docs_store + subtitle seed + grid B2 from repo root."""
import base64, json, sys
from pathlib import Path
ROOT = Path(".").resolve()
assert (ROOT/"backend").is_dir(), "run from repo root"
# payload path next to script or embedded
payload_path = Path(__file__).resolve().parent / "accd_b2_files.json"
if not payload_path.is_file():
    payload_path = Path.home() / "accd_b2_files.json"
if not payload_path.is_file():
    raise SystemExit("Missing accd_b2_files.json next to installer or in $HOME")
blob = json.loads(payload_path.read_text(encoding="utf-8"))
for rel, b64 in blob.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(base64.b64decode(b64))
    print("wrote", rel, p.stat().st_size)
print("DONE. Set on Render:")
print("  B2_KEY_ID B2_APPLICATION_KEY B2_BUCKET B2_ENDPOINT")
print("  optional: B2_REGION ACCD_B2_PREFIX")
print("pip install boto3 && git add -A && commit && push")
