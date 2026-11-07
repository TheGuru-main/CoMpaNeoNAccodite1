#!/usr/bin/env python3
import base64, json
from pathlib import Path
cands = [
    Path.home()/"accd_stream_persist_v2.json",
    Path(__file__).resolve().parent/"accd_stream_persist_v2.json",
    Path.home()/"storage"/"downloads"/"accd_stream_persist_v2.json",
    Path("/storage/emulated/0/Download/accd_stream_persist_v2.json"),
]
payload = next((p for p in cands if p.is_file()), None)
if not payload:
    raise SystemExit("NOT FOUND accd_stream_persist_v2.json")
for rel, b64 in json.loads(payload.read_text()).items():
    Path(rel).parent.mkdir(parents=True, exist_ok=True)
    Path(rel).write_bytes(base64.b64decode(b64))
    print("wrote", rel)
print("DONE: stream AI → DB + B2; client always persists if no message_id")
