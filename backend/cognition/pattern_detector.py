"""Accodite Pattern Detector — room health monitor."""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class PatternKind(str, Enum):
    ESCALATION="ESCALATION"; DRIFT="DRIFT"; CONTRADICTION="CONTRADICTION"
    ANOMALY="ANOMALY"; RISK="RISK"; OPPORTUNITY="OPPORTUNITY"
    CONSENSUS="CONSENSUS"; CONFLICT="CONFLICT"; STALENESS="STALENESS"
    REPETITION="REPETITION"; ORPHAN="ORPHAN"

class Severity(str, Enum):
    INFO="info"; NOTICE="notice"; WARN="warn"; CRITICAL="critical"

@dataclass
class Pattern:
    kind: PatternKind
    severity: Severity
    workspace_id: str
    organization_id: Optional[str]
    actor_id: Optional[str]
    evidence: dict

class PatternDetector:
    def __init__(self, write_event, route_to_boards):
        self._write = write_event
        self._route = route_to_boards

    def scan(self, *, messages, workspace_id, organization_id):
        found = []
        fails = 0
        for m in messages:
            fails = fails + 1 if m.get("kind") == "tool_fail" else 0
            if fails >= 3:
                found.append(Pattern(
                    PatternKind.ESCALATION, Severity.WARN,
                    workspace_id, organization_id, m.get("user_id"),
                    {"consecutive_fails": fails},
                ))
                break
        texts = [m.get("content", "") for m in messages]
        for t in set(texts):
            if t and texts.count(t) >= 3:
                found.append(Pattern(
                    PatternKind.REPETITION, Severity.NOTICE,
                    workspace_id, organization_id, None,
                    {"text": t[:120], "count": texts.count(t)},
                ))
        for p in found:
            try:
                self._write(p); self._route(p)
            except Exception as e:
                print("pattern dispatch failed:", e)
        return found
