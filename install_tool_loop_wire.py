#!/usr/bin/env python3
"""Install tool-loop wire pack: full registry on stream, flight API removed."""
import base64
import json
from pathlib import Path

def main():
    candidates = [
        Path.home() / "accd_tool_loop_wire.json",
        Path(__file__).resolve().parent / "accd_tool_loop_wire.json",
        Path.home() / "storage" / "downloads" / "accd_tool_loop_wire.json",
        Path("/storage/emulated/0/Download/accd_tool_loop_wire.json"),
    ]
    payload = next((p for p in candidates if p.is_file()), None)
    if payload is None:
        raise SystemExit(
            "NOT FOUND accd_tool_loop_wire.json — place it in ~/ or Download/"
        )
    data = json.loads(payload.read_text(encoding="utf-8"))
    expected = {
        "backend/agent/default_tools.py",
        "backend/agent/tool_dispatch_prompt.py",
        "backend/integration.py",
        "backend/main.py",
    }
    missing = expected - set(data.keys())
    if missing:
        raise SystemExit(f"pack incomplete, missing: {sorted(missing)}")
    for rel, b64 in data.items():
        path = Path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(b64)
        path.write_bytes(raw)
        print(f"wrote {rel} ({len(raw)} bytes)")
    # quick sanity
    dt = Path("backend/agent/default_tools.py").read_text(encoding="utf-8")
    if "flight.lookup" in dt:
        print("WARN: flight.lookup still present in default_tools.py")
    else:
        print("OK: flight.lookup removed")
    main_py = Path("backend/main.py").read_text(encoding="utf-8")
    if "run_registry_tool_loop" in main_py or "ACCD-TOOL-LOOP" in main_py:
        print("OK: stream tool_loop wiring present in main.py")
    else:
        print("WARN: tool_loop marker not found in main.py")
    integ = Path("backend/integration.py").read_text(encoding="utf-8")
    if "def run_registry_tool_loop" in integ:
        print("OK: run_registry_tool_loop helper present")
    else:
        print("WARN: run_registry_tool_loop missing")
    print("DONE: tool_loop on stream + full registry; flight API removed")

if __name__ == "__main__":
    main()
