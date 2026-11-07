#!/usr/bin/env python3
import base64, json
from pathlib import Path
cands = [
    Path.home()/"accd_ui_org_place_fix.json",
    Path(__file__).resolve().parent/"accd_ui_org_place_fix.json",
    Path.home()/"storage"/"downloads"/"accd_ui_org_place_fix.json",
    Path("/storage/emulated/0/Download/accd_ui_org_place_fix.json"),
]
payload = next((p for p in cands if p.is_file()), None)
if not payload:
    raise SystemExit("NOT FOUND accd_ui_org_place_fix.json")
for rel, b64 in json.loads(payload.read_text()).items():
    Path(rel).parent.mkdir(parents=True, exist_ok=True)
    Path(rel).write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE: DBase grid+config, GSP place, AI dedup, live roles, strip header")
