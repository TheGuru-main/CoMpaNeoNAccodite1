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

if DBase record create/list (incl. image/voice/doc meta):
  → dbase.place / dbase.list (object_name, description, media_type, filename, payload_ref)

if SheetS create/list:
  → sheets.place / sheets.list

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

if research / "look up" / latest / compare vendors / docs online:
  → web.http.get (or permitted research tools); never invent URLs or results
if plan / roadmap / milestones (no code asked):
  → no mutating fs/grid tools; answer with PLANNER structure only
if API contract / OpenAPI / endpoint design:
  → describe contract from known routes/tools only; flag unknowns

if train/seed requested:
  → do not fake; only real endpoints

if talk / chat / "just talking" / casual conversation (no artifact):
  → no mutating tools; answer in temperament; optional followup.remember if they ask to recall later

if connect team / open team doc / share with dept / "team file":
  → docs.team_open or grid.ns.list under org room scope; never cross owner phone

if table / spreadsheet grid / SheetS rows:
  → sheets.place / sheets.list or grid.ns.place ns=sheets; object_name required for GSP place

if image attach / describe image / OCR already in context:
  → use supplied OCR/transcript only; dbase.place or grid.ns.place with media_type=image when placing

if research / "look up" / latest / compare vendors / docs online:
  → web.http.get (or permitted research tools); never invent URLs or results

if plan / roadmap / milestones (no code asked):
  → no mutating fs/grid tools; answer with PLANNER structure only

if API contract / OpenAPI / endpoint design:
  → describe contract from known routes/tools only; flag unknowns

if acd terminal / repo create / path place under codespace:
  → sandbox repo tools + fs.*; placement via content_place (L,S,c) — do not invent start_row

if none apply:
  → answer from context; honor temperament; stay short

No flight APIs. For travel, ask for itinerary text or known times.
"""


def append_tool_branches(system_prompt: str) -> str:
    base = (system_prompt or "").rstrip()
    if "TOOL ROUTING" in base:
        return base
    return base + "\n\n" + TOOL_IF_BRANCHES.strip() + "\n"
