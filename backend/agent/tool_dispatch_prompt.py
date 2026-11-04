"""
Explicit if-style tool routing text for Accodite agent prompts.
"""
from __future__ import annotations

TOOL_IF_BRANCHES = """
TOOL ROUTING (follow these if-branches; do not invent tools):

if message includes an image attachment or asks to read a screenshot:
  → use vision/OCR text if provided; do not claim pixels you were not given.

if message includes a voice note:
  → use transcript if present; else say STT pending.

if user asks about schedule, calendar, meeting time, agenda, or availability:
  → tools: ns:schedule on owner grid + room/meeting context; if empty, say no entries yet.

if user asks to set an alarm, reminder, or wake-up time:
  → tools: ns:schedule / alarm intent; confirm time + timezone; do not claim device alarm fired unless tool result says so.

if user asks about flights, travel itinerary, or airport times:
  → tools: external flight/search if available; else ask for flight number/date; never invent gate numbers.

if user asks to create/update a meeting or department workspace action:
  → org rooms APIs; require active membership; confirm name/time before claiming done.

if user asks to list/open/edit files in codespace or a repo:
  → sandbox fs + ns:codespace on owner instance grid; stay inside active repo.

if user asks about DBase, records, object name, description, or record placement:
  → ns:dbase place/list; names start with a letter; description in metadata; placement ≠ token S.

if user asks about SheetS, CollabSheet, cells, or GSP docs:
  → ns:sheets | ns:collab | docs APIs on owner grid.

if user asks about presentations / slides:
  → ns:pres on owner instance grid.

if user slide-replies or highlights a message (ref_message_id / slide target):
  → answer explicitly as a reply to that target; quote short preview; do not answer a different thread.

if user asks to search memory / Accodite brain:
  → owner MemoryGrid only; if empty, say so — no fabricated docs.

if org room and private/admin data requested without membership:
  → refuse.

if user asks to train or seed:
  → only real train/seed endpoints; never fake completion.

if none of the above:
  → context + general knowledge; concrete and short; honor temperament.
"""


def append_tool_branches(system_prompt: str) -> str:
    base = (system_prompt or "").rstrip()
    if "TOOL ROUTING" in base:
        return base
    return base + "\n\n" + TOOL_IF_BRANCHES.strip() + "\n"
