"""Accodite Head Router — 96 base + 44 special = 140 heads."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

TOTAL_HEADS=140; BASE_HEADS=96; SPECIAL_HEADS=44; PAIRS=BASE_HEADS//2
POOL_A_RANGE=(1,16); POOL_B_RANGE=(17,32); POOL_C_RANGE=(33,48); POOL_D_RANGE=(49,96)
SPECIAL_RANGES = {
    "crisis": (97,104), "metadata": (105,112), "memory_health": (113,119),
    "orchestration": (120,126), "directives": (127,133), "stream": (134,140),
}

class PoolKind(str, Enum):
    ORG="A"; ROOM="B"; PERSONAL="C"; SHARED="D"

@dataclass
class Segment:
    segment_id: str
    kind: str
    priority: int = 100
    ttl_s: Optional[int] = None

@dataclass
class BindingPlan:
    assignments: Dict[int, Optional[Segment]] = field(default_factory=dict)
    unmapped: List[Segment] = field(default_factory=list)

class HeadAllocator:
    def __init__(self):
        self._binding: Dict[int, Optional[Segment]] = {i: None for i in range(PAIRS)}
        self._by_segment: Dict[str, int] = {}

    def plan(self, segments):
        p = BindingPlan()
        for s in segments:
            p.assignments[self.bind(s)] = s
        return p

    def bind(self, seg):
        if seg.segment_id in self._by_segment:
            return self._by_segment[seg.segment_id]
        for i in self._slots(self._pool_for(seg)):
            if self._binding[i] is None:
                self._binding[i] = seg
                self._by_segment[seg.segment_id] = i
                return i
        for i in self._slots(PoolKind.SHARED):
            if self._binding[i] is None:
                self._binding[i] = seg
                self._by_segment[seg.segment_id] = i
                return i
        victim = min(
            (i for i in self._slots(PoolKind.SHARED) if self._binding[i]),
            key=lambda i: self._binding[i].priority,
        )
        old = self._binding[victim]
        if old:
            self._by_segment.pop(old.segment_id, None)
        self._binding[victim] = seg
        self._by_segment[seg.segment_id] = victim
        return victim

    def release(self, segment_id):
        i = self._by_segment.pop(segment_id, None)
        if i is not None:
            self._binding[i] = None

    def snapshot(self):
        return {i: (s.segment_id if s else None) for i, s in self._binding.items()}

    def _pool_for(self, seg):
        return {"org": PoolKind.ORG, "room": PoolKind.ROOM,
                "personal": PoolKind.PERSONAL,
                "shared": PoolKind.SHARED}.get(seg.kind, PoolKind.SHARED)

    def _slots(self, pool):
        lo, hi = {PoolKind.ORG: POOL_A_RANGE, PoolKind.ROOM: POOL_B_RANGE,
                  PoolKind.PERSONAL: POOL_C_RANGE,
                  PoolKind.SHARED: POOL_D_RANGE}[pool]
        return range((lo - 1) // 2, (hi - 1) // 2 + 1)
