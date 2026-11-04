"""
Explicit if-style tool routing for Accodite agent prompts.
"""
from __future__ import annotations

TOOL_IF_BRANCHES = """
TOOL ROUTING (emit one ```tool fence per call; names must match the registry):

if calendar / schedule / meeting agenda / "remind me" / task due:
  → schedule.add or schedule.list; for pure reminders also alarm.set or followup.remember

if alarm / wake-up / reminder time:
  → alarm.set (time_spec, label) — grid record only, not phone OS alarm

if "remember this" / follow-up / later / don't forget:
  → followup.remember (task, due, note); list with followup.list

if DBase record create/list:
  → dbase.place / dbase.list

if sheets / collab / presentations / codespace objects on memory grid:
  → grid.ns.place / grid.ns.list (ns=sheets|collabsheet|presentations|codespace|schedule|workflow)

if codespace files on disk:
  → fs.read_file / fs.list_dir / fs.write_file / fs.eof_append (workspace root only)

if docs by name:
  → docs.team_open (doc_name, parent_type, parent_id)

if image / voice:
  → use provided OCR/transcript context only

if slide reply (ref_message_id present):
  → answer that target only; short quote of preview

if train/seed requested:
  → do not fake; only real endpoints

if none apply:
  → answer from context; honor temperament; stay short

No flight APIs. For travel, ask for itinerary text or known times.
"""


def append_tool_branches(system_prompt: str) -> str:
    base = (system_prompt or "").rstrip()
    if "TOOL ROUTING" in base:
        return base
    return base + "\n\n" + TOOL_IF_BRANCHES.strip() + "\n"
