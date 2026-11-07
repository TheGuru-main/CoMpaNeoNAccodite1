#!/usr/bin/env python3
import base64, json
from pathlib import Path
cands = [
    Path.home()/"accd_repo_roots_term.json",
    Path(__file__).resolve().parent/"accd_repo_roots_term.json",
    Path.home()/"storage"/"downloads"/"accd_repo_roots_term.json",
    Path("/storage/emulated/0/Download/accd_repo_roots_term.json"),
]
payload = next((p for p in cands if p.is_file()), None)
if not payload:
    raise SystemExit("NOT FOUND accd_repo_roots_term.json")
for rel, b64 in json.loads(payload.read_text()).items():
    Path(rel).parent.mkdir(parents=True, exist_ok=True)
    Path(rel).write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE: GSP repo roots scaffold, unique paths, clone depth, ls")
