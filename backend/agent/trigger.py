"""Accodite Trigger Engine — @AI parser."""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

DEFAULT_TRIGGERS = ("@AI", "@Accodite")

class Mode(str, Enum):
    OBSERVING = "observing"
    ENGAGED   = "engaged"

class TriggerKind(str, Enum):
    MENTION     = "mention"
    HIGHLIGHT   = "highlight"
    SWIPE_REPLY = "swipe_reply"
    DIRECT      = "direct"

@dataclass
class Trigger:
    kind: TriggerKind
    actor_id: str
    workspace_id: str
    message_id: Optional[str] = None
    ref_message_id: Optional[str] = None
    text: str = ""

class TriggerParser:
    def __init__(self, tokens=DEFAULT_TRIGGERS):
        escaped = "|".join(re.escape(t) for t in tokens)
        self._re = re.compile(rf"({escaped})", re.IGNORECASE)

    def mentioned(self, text):
        return bool(self._re.search(text or ""))

    def parse(self, *, actor_id, workspace_id, text,
              message_id=None, ref_message_id=None,
              ref_is_ai=False, is_one_to_one=False):
        if is_one_to_one:
            return Trigger(TriggerKind.DIRECT, actor_id, workspace_id,
                           message_id, None, text)
        if self.mentioned(text):
            return Trigger(TriggerKind.MENTION, actor_id, workspace_id,
                           message_id, None, text)
        if ref_message_id and ref_is_ai and text.strip():
            return Trigger(TriggerKind.HIGHLIGHT, actor_id, workspace_id,
                           message_id, ref_message_id, text)
        if ref_message_id and ref_is_ai:
            return Trigger(TriggerKind.SWIPE_REPLY, actor_id, workspace_id,
                           message_id, ref_message_id, text)
        return None
