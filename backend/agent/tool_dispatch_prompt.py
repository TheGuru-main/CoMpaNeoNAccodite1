"""
Explicit if-style tool routing text for Accodite agent prompts.
Mirrors code dispatch — keep in sync with tools registry.
"""
from __future__ import annotations

TOOL_IF_BRANCHES = """
TOOL ROUTING (follow these if-branches; do not invent tools):

if message includes an image attachment or asks to read a screenshot:
  → use vision/OCR understanding text if provided in context; do not claim you saw pixels you were not given.

if message includes a voice note:
  → use the transcript field if present; if no transcript, say voice is pending STT.

if user asks to list/open/edit files in codespace or a repo:
  → tools: sandbox fs list/read/write, run — only inside the active repo path.

if user asks about a sheet, excel cell, workspace placement, or GSP doc:
  → tools: docs list/get/cell with parent_type repo|room and sane doc names (must start with a letter).

if user asks to search memory / training knowledge / Accodite brain:
  → use retrieved MemoryGrid context only; if shared grid is empty, say knowledge store is empty — do not fabricate docs.

if user message is in an org room and requests admin or private data:
  → require membership; if access denied, refuse.

if user asks to train or seed:
  → only via explicit train/seed endpoints; do not pretend training completed without tool result.

if none of the above:
  → answer from context + general knowledge; keep answers concrete and short.
"""


def append_tool_branches(system_prompt: str) -> str:
    base = (system_prompt or "").rstrip()
    if "TOOL ROUTING" in base:
        return base
    return base + "\n\n" + TOOL_IF_BRANCHES.strip() + "\n"
