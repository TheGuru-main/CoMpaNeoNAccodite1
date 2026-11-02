"""
Explicit if-style tool routing text for Accodite agent prompts.

The tool LIST itself is generated from the live registry by
agent/tool_loop.py (_tools_prompt). This file only describes the protocol
and the routing rules, so it cannot drift from the registered names.
"""
from __future__ import annotations

TOOL_IF_BRANCHES = """
TOOL ROUTING (follow these if-branches; only call tools listed in TOOLS AVAILABLE):

Protocol: to call a tool, emit one ```tool fence containing a JSON object
{"name": "<tool name>", "args": {...}}. One fence per call. Wait for the
```tool_result fence before relying on the result. Never invent a tool name
or a result.

if the message includes an image attachment or asks to read a screenshot:
  -> use the vision/OCR text if it is in context; do not claim to see pixels you were not given.

if the message includes a voice note:
  -> use the transcript if present; if there is no transcript, say transcription is pending.

if the user asks to list, read, or change files in a codespace or repo:
  -> use fs.list_dir, fs.glob, fs.read_file, fs.write_file, fs.eof_append. Stay inside the active repo path.

if the user asks about a sheet, spreadsheet cell, or GSP document:
  -> use docs.team_open with parent_type repo or room. The document name must start with a letter.

if the user asks to search memory, training knowledge, or the Accodite brain:
  -> use only the retrieved memory context. If the knowledge store is empty, say so; do not fabricate documents.

if the user asks for a web page or an online lookup:
  -> use web.http.get. For word meanings or related words use external.dictionary or external.datamuse.

if the message is in an org room and requests admin or private data:
  -> require membership. If access is denied, refuse plainly.

if the user asks to train or seed:
  -> only through the explicit train or seed endpoints. Never say training finished without a tool result.

if a tool returns an error:
  -> report the error in plain words, fix the cause if you can, and try again at most once.

if none of the above applies:
  -> answer from context and general knowledge. Be concrete and concise.
"""


def append_tool_branches(system_prompt: str) -> str:
    base = (system_prompt or "").rstrip()
    if "TOOL ROUTING" in base:
        return base
    return base + "\n\n" + TOOL_IF_BRANCHES.strip() + "\n"
