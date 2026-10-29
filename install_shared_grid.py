#!/usr/bin/env python3
import base64, json
from pathlib import Path
ROOT = Path(".").resolve()
assert (ROOT / "backend").is_dir()
payload = Path.home() / "accd_shared_grid_files.json"
if not payload.is_file():
    payload = Path(__file__).resolve().parent / "accd_shared_grid_files.json"
blob = json.loads(payload.read_text(encoding="utf-8"))
for rel, b64 in blob.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE — commit and push")
print("Shared grid is sole storage; train/generate refuse empty fabricated grids.")
