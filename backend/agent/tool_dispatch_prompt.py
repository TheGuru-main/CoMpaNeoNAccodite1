"""
Explicit if-style tool routing text for Accodite agent prompts.
"""
from __future__ import annotations

TOOL_IF_BRANCHES = """
TOOL ROUTING (emit ```tool fences with these names when needed):

if calendar / schedule / meeting agenda:
  → schedule.list or schedule.add (title, when, note)

if alarm / reminder / wake-up:
  → alarm.set (time_spec, label) — records on grid; does not set phone OS alarm

if flight / itinerary / airport:
  → flight.lookup (flight_number, date) — never invent gates

if DBase record create/list:
  → dbase.place / dbase.list  (or grid.ns.place ns=dbase)

if sheets / collab / presentations / codespace objects on memory grid:
  → grid.ns.place / grid.ns.list with ns=sheets|collabsheet|presentations|codespace

if codespace files on disk:
  → fs.read_file / fs.list_dir / fs.write_file inside workspace root only

if image / voice:
  → use provided OCR/transcript context only

if slide reply (ref_message_id present):
  → answer that target only; short quote of preview

if train/seed requested:
  → do not fake; only real endpoints

if none apply:
  → answer from context; honor temperament; stay short
"""


def append_tool_branches(system_prompt: str) -> str:
    base = (system_prompt or "").rstrip()
    if "TOOL ROUTING" in base:
        return base
    return base + "\n\n" + TOOL_IF_BRANCHES.strip() + "\n"
