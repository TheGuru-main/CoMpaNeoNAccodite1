#!/usr/bin/env python3
import base64, json
from pathlib import Path
payload = Path.home() / "accd_grid_namespaces.json"
if not payload.is_file():
    payload = Path(__file__).resolve().parent / "accd_grid_namespaces.json"
for rel, b64 in json.loads(payload.read_text()).items():
    Path(rel).parent.mkdir(parents=True, exist_ok=True)
    Path(rel).write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE: DBase/sheets/codespace as marked namespaces on owner instance grid")
