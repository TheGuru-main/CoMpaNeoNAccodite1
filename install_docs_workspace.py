#!/usr/bin/env python3
import base64, json
from pathlib import Path
cands = [
    Path.home()/"accd_docs_workspace.json",
    Path(__file__).resolve().parent/"accd_docs_workspace.json",
    Path.home()/"storage"/"downloads"/"accd_docs_workspace.json",
    Path("/storage/emulated/0/Download/accd_docs_workspace.json"),
]
payload = next((x for x in cands if x.is_file()), None)
if not payload:
    raise SystemExit("NOT FOUND accd_docs_workspace.json")
for rel, b64 in json.loads(payload.read_text()).items():
    Path(rel).parent.mkdir(parents=True, exist_ok=True)
    Path(rel).write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE: workspace DBase/Sheet buttons + name/desc place")
