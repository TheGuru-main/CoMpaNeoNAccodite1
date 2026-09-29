"""
User / Workspace Preference Store
==================================
Per (user_id, workspace_id) memory of the user's steering behavior.

Two kinds of entries:

    ALONG  — "the user keeps accepting this"
             (a suggested direction that was picked up, reinforced, or
              approved across turns). Feeds a positive bias.

    PIVOT  — "the user changed direction here"
             (a correction, redirection, rejection, or new constraint).
             Feeds a veto / adjust signal.

Both decay with TTL. Repeat sightings reinforce strength. Very strong
pivots can be promoted to project pins; every entry writes a project
trace line and (optionally) indexes into the memory grid.

Scope inside memory_partition: PARTITION_SCOPE = "preference"
Key: (user_id, workspace_id) — stored under the user's own scope, not
shared with other members of the same workspace.
"""
from __future__ import annotations
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================================
# CONSTANTS
# ============================================================================

PARTITION_SCOPE = "preference"

KIND_ALONG = "along"
KIND_PIVOT = "pivot"
KINDS = (KIND_ALONG, KIND_PIVOT)


# ============================================================================
# ENTRY
# ============================================================================

@dataclass
class PreferenceEntry:
    user_id: str
    workspace_id: str
    kind: str                 # KIND_ALONG | KIND_PIVOT
    text: str                 # canonical phrasing of the preference
    context: str = ""         # what was happening when it was expressed
    direction: str = ""       # for pivots: "from X -> to Y" hint
    strength: float = 1.0     # 0..1
    hits: int = 1
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    extra: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------

    def decayed_strength(self, *, now: float, tau_s: float) -> float:
        age = max(0.0, now - self.last_seen)
        return float(self.strength) * math.exp(-age / max(1.0, tau_s))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "kind": self.kind,
            "text": self.text,
            "context": self.context,
            "direction": self.direction,
            "strength": round(self.strength, 4),
            "hits": self.hits,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "extra": dict(self.extra),
        }


# ============================================================================
# SIMILARITY (cheap token overlap)
# ============================================================================

_WORD = re.compile(r"[A-Za-z0-9_]+")

def _tokens(text: str) -> set:
    return {w.lower() for w in _WORD.findall(text or "") if len(w) > 2}

def _similar(a: str, b: str, threshold: float = 0.5) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    union = len(ta | tb)
    return (inter / union) >= threshold


# ============================================================================
# STORE
# ============================================================================

class UserWorkspacePreferenceStore:
    def __init__(
        self,
        *,
        ttl_s: int = 7 * 24 * 3600,       # one week
        tau_s: int = 3 * 24 * 3600,       # decay constant
        min_strength: float = 0.05,       # below this, entry is dropped
        max_per_key: int = 500,
        pin_threshold: float = 0.85,      # pivots above this get pinned
    ):
        self.ttl_s = int(ttl_s)
        self.tau_s = int(tau_s)
        self.min_strength = float(min_strength)
        self.max_per_key = int(max_per_key)
        self.pin_threshold = float(pin_threshold)

        # (user_id, workspace_id) -> list[PreferenceEntry]
        self._store: Dict[Tuple[str, str], List[PreferenceEntry]] = {}

    # ------------------------------------------------------------------
    # keys
    # ------------------------------------------------------------------

    @staticmethod
    def _key(user_id: str, workspace_id: str) -> Tuple[str, str]:
        return (str(user_id or ""), str(workspace_id or ""))

    @staticmethod
    def partition_key(user_id: str, workspace_id: str) -> Dict[str, str]:
        return {
            "scope": PARTITION_SCOPE,
            "user_id": str(user_id or ""),
            "workspace_id": str(workspace_id or ""),
        }

    # ------------------------------------------------------------------
    # recording
    # ------------------------------------------------------------------

    def record_along(
        self,
        user_id: str,
        workspace_id: str,
        text: str,
        *,
        context: str = "",
        weight: float = 1.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> PreferenceEntry:
        return self._record(
            user_id, workspace_id, KIND_ALONG, text,
            context=context, direction="", weight=weight, extra=extra,
        )

    def record_pivot(
        self,
        user_id: str,
        workspace_id: str,
        text: str,
        *,
        context: str = "",
        direction: str = "",
        weight: float = 1.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> PreferenceEntry:
        return self._record(
            user_id, workspace_id, KIND_PIVOT, text,
            context=context, direction=direction, weight=weight, extra=extra,
        )

    def _record(
        self,
        user_id: str,
        workspace_id: str,
        kind: str,
        text: str,
        *,
        context: str = "",
        direction: str = "",
        weight: float = 1.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> PreferenceEntry:
        if kind not in KINDS:
            raise ValueError(f"unknown kind: {kind}")
        text = (text or "").strip()
        if not text:
            raise ValueError("preference text is required")

        key = self._key(user_id, workspace_id)
        bucket = self._store.setdefault(key, [])

        # merge with an existing similar entry of the same kind
        for e in bucket:
            if e.kind != kind:
                continue
            if _similar(e.text, text):
                e.hits += 1
                e.last_seen = time.time()
                e.strength = min(1.0, e.strength + 0.1 * weight)
                if context and context not in (e.context or ""):
                    e.context = (e.context + " | " + context)[-500:]
                if direction and not e.direction:
                    e.direction = direction
                if extra:
                    e.extra.update(extra)
                return e

        # new entry
        entry = PreferenceEntry(
            user_id=key[0],
            workspace_id=key[1],
            kind=kind,
            text=text[:500],
            context=(context or "")[:500],
            direction=(direction or "")[:200],
            strength=min(1.0, 0.5 + 0.5 * max(0.0, weight)),
            hits=1,
            extra=dict(extra or {}),
        )
        bucket.append(entry)
        self._evict_if_needed(key)
        return entry

    # ------------------------------------------------------------------
    # reading
    # ------------------------------------------------------------------

    def get_all(self, user_id: str, workspace_id: str) -> List[PreferenceEntry]:
        self.sweep()
        return list(self._store.get(self._key(user_id, workspace_id), []))

    def get_along(self, user_id: str, workspace_id: str) -> List[PreferenceEntry]:
        return [e for e in self.get_all(user_id, workspace_id) if e.kind == KIND_ALONG]

    def get_pivots(self, user_id: str, workspace_id: str) -> List[PreferenceEntry]:
        return [e for e in self.get_all(user_id, workspace_id) if e.kind == KIND_PIVOT]

    def top_k(
        self,
        user_id: str,
        workspace_id: str,
        k: int = 5,
        *,
        kind: Optional[str] = None,
    ) -> List[PreferenceEntry]:
        now = time.time()
        entries = self.get_all(user_id, workspace_id)
        if kind:
            entries = [e for e in entries if e.kind == kind]
        entries.sort(
            key=lambda e: (e.decayed_strength(now=now, tau_s=self.tau_s), e.hits),
            reverse=True,
        )
        return entries[:k]

    def summary(self, user_id: str, workspace_id: str, k: int = 5) -> Dict[str, Any]:
        along = self.top_k(user_id, workspace_id, k=k, kind=KIND_ALONG)
        pivots = self.top_k(user_id, workspace_id, k=k, kind=KIND_PIVOT)
        return {
            "user_id": str(user_id or ""),
            "workspace_id": str(workspace_id or ""),
            "along": [e.as_dict() for e in along],
            "pivot": [e.as_dict() for e in pivots],
            "total": len(self._store.get(self._key(user_id, workspace_id), [])),
        }

    # ------------------------------------------------------------------
    # TTL
    # ------------------------------------------------------------------

    def sweep(self) -> int:
        """Drop entries whose decayed strength falls below min_strength."""
        now = time.time()
        removed = 0
        for key in list(self._store.keys()):
            kept = []
            for e in self._store[key]:
                if e.decayed_strength(now=now, tau_s=self.tau_s) < self.min_strength:
                    removed += 1
                    continue
                if (now - e.last_seen) > self.ttl_s:
                    removed += 1
                    continue
                kept.append(e)
            if kept:
                self._store[key] = kept
            else:
                del self._store[key]
        return removed

    def _evict_if_needed(self, key: Tuple[str, str]) -> None:
        bucket = self._store.get(key)
        if not bucket or len(bucket) <= self.max_per_key:
            return
        now = time.time()
        bucket.sort(
            key=lambda e: e.decayed_strength(now=now, tau_s=self.tau_s),
            reverse=True,
        )
        del bucket[self.max_per_key:]

    def clear(self, user_id: str, workspace_id: str) -> None:
        self._store.pop(self._key(user_id, workspace_id), None)

    def size(self) -> int:
        return sum(len(v) for v in self._store.values())

    # ------------------------------------------------------------------
    # persistence hooks
    # ------------------------------------------------------------------

    def to_trace_payload(self, entry: PreferenceEntry) -> Dict[str, Any]:
        return {
            "event": f"pref.{entry.kind}.recorded",
            "scope": PARTITION_SCOPE,
            "user_id": entry.user_id,
            "workspace_id": entry.workspace_id,
            "text": entry.text,
            "context": entry.context,
            "direction": entry.direction,
            "strength": round(entry.strength, 4),
            "hits": entry.hits,
        }

    def persist_to_partition(
        self,
        partition: Any,
        project_id: str,
        entry: PreferenceEntry,
        *,
        pin: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Write the entry to project_trace. Optionally pin strong pivots.

        Both calls are defensive; missing methods are ignored.
        """
        result: Dict[str, Any] = {"traced": False, "pinned": False}

        if partition is None:
            return result

        payload = self.to_trace_payload(entry)

        try:
            if hasattr(partition, "trace_project"):
                partition.trace_project(project_id, payload)
                result["traced"] = True
            elif hasattr(partition, "ensure_project_trace"):
                partition.ensure_project_trace(project_id)
                if hasattr(partition, "trace_project"):
                    partition.trace_project(project_id, payload)
                    result["traced"] = True
        except Exception as e:
            result["trace_error"] = f"{type(e).__name__}: {e}"

        should_pin = pin
        if should_pin is None:
            should_pin = (entry.kind == KIND_PIVOT
                          and entry.strength >= self.pin_threshold)

        if should_pin and hasattr(partition, "pin_project"):
            try:
                partition.pin_project(
                    project_id,
                    scope=PARTITION_SCOPE.upper(),
                    target_ref=f"{entry.user_id}:{entry.text[:60]}",
                    reason=f"{entry.kind} preference, strength {entry.strength:.2f}",
                    priority=int(50 + entry.strength * 50),
                )
                result["pinned"] = True
            except TypeError:
                # tolerate alternative signatures
                try:
                    partition.pin_project(project_id, payload)
                    result["pinned"] = True
                except Exception as e:
                    result["pin_error"] = f"{type(e).__name__}: {e}"
            except Exception as e:
                result["pin_error"] = f"{type(e).__name__}: {e}"

        return result

    def index_to_grid(
        self,
        grid: Any,
        entry: PreferenceEntry,
        *,
        source_tag: str = "preference",
    ) -> Optional[int]:
        """
        Index the preference text into the memory grid. Returns doc_id.
        """
        if grid is None or not hasattr(grid, "add_document"):
            return None
        try:
            return grid.add_document(
                entry.text,
                source=source_tag,
                metadata={
                    "scope": PARTITION_SCOPE,
                    "kind": entry.kind,
                    "user_id": entry.user_id,
                    "workspace_id": entry.workspace_id,
                    "strength": entry.strength,
                    "hits": entry.hits,
                },
            )
        except Exception:
            return None


# ============================================================================
# MODULE-LEVEL SINGLETON (opt-in)
# ============================================================================

_DEFAULT: Optional[UserWorkspacePreferenceStore] = None


def default_store() -> UserWorkspacePreferenceStore:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = UserWorkspacePreferenceStore()
    return _DEFAULT
