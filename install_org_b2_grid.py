#!/usr/bin/env python3
import base64, json
from pathlib import Path
payload = Path.home() / "accd_org_b2_grid.json"
if not payload.is_file():
    payload = Path(__file__).resolve().parent / "accd_org_b2_grid.json"
for rel, b64 in json.loads(payload.read_text()).items():
    Path(rel).parent.mkdir(parents=True, exist_ok=True)
    Path(rel).write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE: membership + org instance grid on signup + B2 grid key layout")
print("B2: grids/platform/... and grids/instances/{org|user}/...")
