#!/usr/bin/env python3
"""One-shot clean gap close: phone grids, signup instance, rooms PSTM, seed lang, no flight."""
import base64, json
from pathlib import Path

def main():
    candidates = [
        Path.home() / "accd_cleanslate.json",
        Path(__file__).resolve().parent / "accd_cleanslate.json",
        Path.home() / "storage" / "downloads" / "accd_cleanslate.json",
        Path("/storage/emulated/0/Download/accd_cleanslate.json"),
    ]
    payload = next((p for p in candidates if p.is_file()), None)
    if not payload:
        raise SystemExit("NOT FOUND accd_cleanslate.json")
    data = json.loads(payload.read_text(encoding="utf-8"))
    for rel, b64 in data.items():
        path = Path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(b64))
        print("wrote", rel)
    # sanity
    ig = Path("backend/memory/instance_grid.py").read_text(encoding="utf-8")
    assert "OwnerRef" in ig and "phone" in ig.lower()
    dt = Path("backend/agent/default_tools.py").read_text(encoding="utf-8")
    if "flight.lookup" in dt:
        print("WARN flight still present")
    else:
        print("OK no flight.lookup")
    print("DONE cleanslate:", len(data), "files")

if __name__ == "__main__":
    main()
