"""
Per-User Short-Term Memory (PSTM)
=================================
Private per (room_id, user_id). Never visible to other members.

Holds:
    - draft (what the user is typing before sending)
    - suggestions (agent hints, private to that user)
    - tool_calls (pending/running, scoped to that user)
    - scratchpad (working notes)
    - extras (free-form)

Backed by an in-process dict with TTL + LRU eviction.
Persistence to disk is intentionally opt-in via save()/load().
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class UserState:
    room_id: str
    user_id: str
    draft: str = ""
    suggestions: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    scratchpad: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "user_id": self.user_id,
            "draft": self.draft,
            "suggestions": list(self.suggestions),
            "tool_calls": list(self.tool_calls),
            "scratchpad": self.scratchpad,
            "extras": dict(self.extras),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PSTM:
    def __init__(self, *, ttl_s: int = 1800, max_entries: int = 10000):
        self.ttl_s = int(ttl_s)
        self.max_entries = int(max_entries)
        self._store: Dict[Tuple[str, str], UserState] = {}

    def _key(self, room_id: str, user_id: str) -> Tuple[str, str]:
        return (str(room_id), str(user_id))

    # ------------------------------------------------------------------

    def get(self, room_id: str, user_id: str) -> UserState:
        k = self._key(room_id, user_id)
        s = self._store.get(k)
        if s is None:
            s = UserState(room_id=k[0], user_id=k[1])
            self._store[k] = s
            self._evict_if_needed()
        s.updated_at = time.time()
        return s

    def as_dict(self, room_id: str, user_id: str) -> Dict[str, Any]:
        return self.get(room_id, user_id).as_dict()

    # ------------------------------------------------------------------

    def set_draft(self, room_id, user_id, draft: str) -> None:
        s = self.get(room_id, user_id)
        s.draft = draft or ""

    def add_suggestion(self, room_id, user_id, text: str) -> None:
        s = self.get(room_id, user_id)
        s.suggestions.append({"text": text, "at": time.time()})

    def add_tool_call(self, room_id, user_id, *, name: str, status: str, detail: str = "") -> None:
        s = self.get(room_id, user_id)
        s.tool_calls.append({
            "name": name, "status": status, "detail": detail, "at": time.time(),
        })

    def append_scratchpad(self, room_id, user_id, text: str) -> None:
        s = self.get(room_id, user_id)
        s.scratchpad = (s.scratchpad or "") + text

    def set_extra(self, room_id, user_id, key: str, value: Any) -> None:
        s = self.get(room_id, user_id)
        s.extras[key] = value

    def clear(self, room_id, user_id) -> None:
        self._store.pop(self._key(room_id, user_id), None)

    # ------------------------------------------------------------------

    def sweep(self) -> int:
        now = time.time()
        dead = [k for k, s in self._store.items() if (now - s.updated_at) > self.ttl_s]
        for k in dead:
            del self._store[k]
        return len(dead)

    def _evict_if_needed(self) -> None:
        if len(self._store) <= self.max_entries:
            return
        # evict oldest updated
        items = sorted(self._store.items(), key=lambda kv: kv[1].updated_at)
        drop = len(self._store) - self.max_entries
        for k, _ in items[:drop]:
            del self._store[k]

    def size(self) -> int:
        return len(self._store)

    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        blob = {f"{r}::{u}": s.as_dict() for (r, u), s in self._store.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blob, f, indent=2)

    def load(self, path: str) -> int:
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except FileNotFoundError:
            return 0
        count = 0
        for key, data in blob.items():
            r, _, u = key.partition("::")
            s = UserState(room_id=r, user_id=u)
            for fld in ("draft", "scratchpad"):
                if fld in data:
                    setattr(s, fld, data[fld])
            s.suggestions = list(data.get("suggestions", []))
            s.tool_calls = list(data.get("tool_calls", []))
            s.extras = dict(data.get("extras", {}))
            self._store[self._key(r, u)] = s
            count += 1
        return count
