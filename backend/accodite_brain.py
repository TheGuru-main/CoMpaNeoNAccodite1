"""
CoMpaNeoNAccodite Brain
=======================
Working-cortex layer for Accodite.

Reads from the canonical MemoryGrid (main memory) and keeps its own
46x64 activation grid as a per-query heatmap for reply relevancy.

Own grid zones (rows):
    repo       0-7     repository / project identifiers
    ast        8-23    symbols from code drafts
    lsp        24-39   diagnostics, refs, hover
    runway     40-51   task prompt intent
    actuator   52-63   tool calls, side effects

Responsibility split:
    MemoryGrid        canonical storage (owned by CoMpaNeoN)
    MemoryPartition   routing/sharding
    MemoryCache       STM/LTM cache
    AccoditeBrain     per-query working set + relevancy ranking
                      + head segment binding + prompt context
"""
from __future__ import annotations
import json, hashlib
from typing import Any, Dict, List, Optional, Tuple

from code_tokenizer import word_cell, split_code_identifiers

COLS = 46
ROWS = 64

ZONES = {
    "repo":     (0, 7),
    "ast":      (8, 23),
    "lsp":      (24, 39),
    "runway":   (40, 51),
    "actuator": (52, 63),
}


class AccoditeBrain:
    """
    Per-query working cortex.

    Depends on canonical modules via injection:
        memory_grid     — MemoryGrid instance
        memory_cache    — MemoryCache instance (STM/LTM/retrieval)
        head_allocator  — model.head_router.HeadAllocator
        ltm_gate        — memory.ltm_gate.LTMGate (role-gated LTM reads)
        tracer          — project_trace tracker (optional)
    """

    def __init__(
        self,
        workspace_root: str,
        *,
        memory_grid=None,
        memory_cache=None,
        head_allocator=None,
        ltm_gate=None,
        tracer=None,
        workspace_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "member",
    ):
        self.workspace_root = workspace_root
        self.COLS = COLS
        self.ROWS = ROWS

        # canonical dependencies
        self._grid = memory_grid
        self._cache = memory_cache
        self._heads = head_allocator
        self._ltm = ltm_gate
        self._tracer = tracer

        # scope
        self.workspace_id = workspace_id
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role

        # own working heatmap (activation), reset per task
        self._own_grid: List[List[float]] = [
            [0.0 for _ in range(self.COLS)] for _ in range(self.ROWS)
        ]

        # per-task cache of the last composed context
        self._last_context: Dict[str, Any] = {}

        # current binding plan (segment_id -> pair index)
        self._binding_plan: Dict[int, Optional[str]] = {}

    # -----------------------------------------------------------------
    # GSP SLOT MATH (unchanged signature, zones preserved)
    # -----------------------------------------------------------------

    def calculate_gsp_slot(self, token: str, zone_name: str) -> Tuple[int, int]:
        meta = word_cell(token, lang="en")
        lsum = meta["Lsum"]; ssum = meta["Ssum"]
        col = (meta["c"] + lsum) % self.COLS
        r_min, r_max = ZONES.get(zone_name, (8, 23))
        row = r_min + ((lsum + ssum) % ((r_max - r_min) + 1))
        return col, row

    def _touch(self, token: str, zone: str, weight: float = 1.0):
        c, r = self.calculate_gsp_slot(token, zone)
        self._own_grid[r][c] = min(1.0, self._own_grid[r][c] + weight)
        return c, r

    # -----------------------------------------------------------------
    # OWN GRID (working heatmap)
    # -----------------------------------------------------------------

    def reset_working_grid(self):
        for r in range(self.ROWS):
            for c in range(self.COLS):
                self._own_grid[r][c] = 0.0

    def map_incoming_task(self, prompt: str, code_draft: str) -> List[Tuple[int, int]]:
        """
        Populate own grid from prompt + draft. Zones:
            prompt tokens -> runway
            code identifiers -> ast
        """
        activated: List[Tuple[int, int]] = []
        for tok in split_code_identifiers(prompt):
            activated.append(self._touch(tok, "runway"))
        for tok in split_code_identifiers(code_draft):
            activated.append(self._touch(tok, "ast"))
        return activated

    # -----------------------------------------------------------------
    # READ FROM CANONICAL MEMORYGRID
    # -----------------------------------------------------------------

    def read_main_grid(
        self,
        query: str,
        *,
        top_k: int = 20,
        scope: Optional[dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Pull evidence from the canonical MemoryGrid.

        Falls back to memory_cache (retrieval) if MemoryGrid is not injected.
        Scope dict may carry workspace_id / organization_id / user_id.
        """
        hits: List[Dict[str, Any]] = []
        if self._grid is not None:
            try:
                hits = self._grid.retrieve(query, top_k=top_k) or []
            except Exception as e:
                self._trace("read_main_grid", {"error": str(e)})
                hits = []
        if not hits and self._cache is not None:
            try:
                cached = self._cache.get_retrieval(query)
                if cached:
                    hits = cached if isinstance(cached, list) else [cached]
            except Exception:
                pass
        return hits[:top_k]

    # -----------------------------------------------------------------
    # LTM VAULT READ (role-gated)
    # -----------------------------------------------------------------

    def read_ltm(self, query: str) -> Any:
        if self._ltm is None:
            return None
        try:
            return self._ltm.read(
                user_id=self.user_id,
                organization_id=self.organization_id,
                query=query,
            )
        except PermissionError:
            return None

    # -----------------------------------------------------------------
    # HEAD SEGMENT BINDING
    # -----------------------------------------------------------------

    def bind_segments(self) -> Dict[int, Optional[str]]:
        """
        Bind head pairs for this query:
            Pool C  personal  (user's working segment)
            Pool B  room      (workspace segment)
            Pool A  org       (only if role can read LTM)
        """
        if self._heads is None:
            return {}
        from model.head_router import Segment

        segs: List[Segment] = []

        if self.user_id:
            segs.append(Segment(
                segment_id=f"personal:{self.user_id}",
                kind="personal", priority=200,
            ))

        if self.workspace_id:
            segs.append(Segment(
                segment_id=f"room:{self.workspace_id}",
                kind="room", priority=150,
            ))

        if self.organization_id and self._can_read_org():
            segs.append(Segment(
                segment_id=f"org:{self.organization_id}",
                kind="org", priority=100,
            ))

        plan = self._heads.plan(segs)
        self._binding_plan = self._heads.snapshot()
        self._trace("bind_segments", {"plan": self._binding_plan})
        return self._binding_plan

    def _can_read_org(self) -> bool:
        try:
            from org.roles import can_read_ltm
            return can_read_ltm(self.role)
        except Exception:
            return False

    # -----------------------------------------------------------------
    # RELEVANCY RANKING (main grid hits x own heatmap)
    # -----------------------------------------------------------------

    def rank_for_reply(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Combine:
            1. canonical MemoryGrid hits
            2. own activation heatmap
            3. LTM vault (role-gated)
        Return an ordered evidence list.
        """
        candidates = self.read_main_grid(query, top_k=top_k * 3)

        scored: List[Dict[str, Any]] = []
        for h in candidates:
            text = (
                h.get("text") or h.get("content") or
                h.get("token") or ""
            )
            score = float(h.get("score", 0.0))

            # activation overlap: does this hit touch hot cells?
            hot = 0.0
            for tok in split_code_identifiers(text):
                for zone in ("ast", "repo", "lsp"):
                    c, r = self.calculate_gsp_slot(tok, zone)
                    hot += self._own_grid[r][c]
            score += 0.5 * hot

            scored.append({**h, "relevancy": score})

        # LTM overlay
        ltm_hit = self.read_ltm(query)
        if ltm_hit:
            scored.append({"source": "LTM", "content": ltm_hit, "relevancy": 1.0})

        scored.sort(key=lambda x: x["relevancy"], reverse=True)
        return scored[:top_k]

    # -----------------------------------------------------------------
    # COMPOSE REPLY CONTEXT (for prompt_manager)
    # -----------------------------------------------------------------

    def compose_reply_context(
        self,
        *,
        prompt: str,
        code_draft: str = "",
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Full per-query pass. Returns a bundle the prompt manager
        can consume without further work.
        """
        self.reset_working_grid()
        activated = self.map_incoming_task(prompt, code_draft)
        binding = self.bind_segments()
        evidence = self.rank_for_reply(prompt, top_k=top_k)

        self._last_context = {
            "workspace_id": self.workspace_id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "role": self.role,
            "activated_cells": len(activated),
            "binding_plan": binding,
            "evidence": evidence,
            "query_hash": hashlib.sha256(
                (prompt or "").encode("utf-8")
            ).hexdigest()[:12],
        }
        self._trace("compose_reply_context", {
            "hits": len(evidence),
            "activated": len(activated),
        })
        return self._last_context

    # -----------------------------------------------------------------

    def _trace(self, action: str, payload: dict):
        if self._tracer is None:
            return
        try:
            self._tracer.log_execution_step("AccoditeBrain", action, payload)
        except Exception:
            pass

    def get_working_grid(self) -> List[List[float]]:
        return [row[:] for row in self._own_grid]

    def get_last_context(self) -> Dict[str, Any]:
        return dict(self._last_context)
