"""
Accodite Room Hub
=================
WebSocket fan-out for room messages. Every member connected to a room
receives user messages AND AI frames in real time.
"""
from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, Set

from fastapi import WebSocket


class RoomHub:
    def __init__(self):
        self._rooms: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(str(room_id), set()).add(ws)

    async def disconnect(self, room_id: str, ws: WebSocket) -> None:
        async with self._lock:
            s = self._rooms.get(str(room_id))
            if s is not None:
                s.discard(ws)
                if not s:
                    self._rooms.pop(str(room_id), None)

    async def broadcast(self, room_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            subs = list(self._rooms.get(str(room_id), set()))
        if not subs:
            return
        text = json.dumps(payload, default=str)
        dead = []
        for ws in subs:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                s = self._rooms.get(str(room_id))
                if s is not None:
                    for ws in dead:
                        s.discard(ws)


HUB = RoomHub()
