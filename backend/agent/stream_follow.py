"""
Accodite Stream + Follow-Up Bridge
==================================
Glues StreamGate, FollowUp, MemoryGrid, and MemoryPartition.

Does NOT modify any of those modules.

Flow:
    StreamGate.stream()  ->  frames yielded to caller
                         ->  #token# payloads reassembled
                         ->  memory_grid.add_document(rebuilt)
                         ->  FollowUp.process_response(query, answer)
                         ->  generate_follow_ups(query, answer)
                         ->  partition.trace_project(project_id, {...})
                         ->  partition.partition_document({...})
                         ->  #meta#<json> frame with post-stream data

Frontend sees: #begin#, #kind#, #color#, #token#* , #end#, #meta#<json>
(or a single #error#<hint> if the gate rejects).
"""
from __future__ import annotations
import json
from typing import Any, Dict, Generator, List, Optional


# ============================================================================
# OPTIONAL IMPORTS
# ============================================================================

try:
    from agent.stream_gate import StreamGate
except ImportError:
    StreamGate = None

try:
    from agent.follow_up import FollowUp, generate_follow_ups
except ImportError:
    FollowUp = None
    generate_follow_ups = None

try:
    from memory_grid import MemoryGrid
except ImportError:
    MemoryGrid = None

try:
    import memory_partition as _mp
    MEMORY_PARTITION_AVAILABLE = True
except ImportError:
    _mp = None
    MEMORY_PARTITION_AVAILABLE = False


# ============================================================================
# HELPERS
# ============================================================================

def _reconstruct(frames: List[str]) -> str:
    """Concatenate every #token# payload to rebuild the source."""
    parts: List[str] = []
    prefix = "#token#"
    for f in frames:
        if f.startswith(prefix):
            parts.append(f[len(prefix):])
    return "".join(parts)


# ============================================================================
# BRIDGE
# ============================================================================

class StreamFollowBridge:
    def __init__(
        self,
        *,
        gate=None,
        follow=None,
        grid=None,
        partition=None,
        tracer=None,
        root: str = ".",
    ):
        if gate is None and StreamGate is not None:
            try:
                gate = StreamGate(root=root)
            except Exception:
                gate = None
        self.gate = gate

        if follow is None and FollowUp is not None:
            try:
                follow = FollowUp()
            except Exception:
                follow = None
        self.follow = follow

        if grid is None and MemoryGrid is not None:
            try:
                grid = MemoryGrid()
            except Exception:
                grid = None
        self.grid = grid

        self.partition = partition
        self.tracer = tracer
        self.root = root

    # -----------------------------------------------------------------

    def stream(
        self,
        *,
        path: str,
        source: str,
        query: str = "",
        lang: Optional[str] = None,
        project_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        room_id: Optional[str] = None,
        run_tests: bool = True,
        run_security: bool = True,
    ) -> Generator[str, None, None]:
        """
        Generator. Yields StreamGate frames verbatim, then a #meta#<json>
        frame with post-stream data.

        If the gate rejects, yields the #error#<hint> frame and stops.
        """
        if self.gate is None:
            yield "#error#no StreamGate configured"
            return

        frames: List[str] = []
        rejected = False

        for frame in self.gate.stream(
            path=path, source=source, lang=lang,
            run_tests=run_tests, run_security=run_security,
            tracer=self.tracer, partition=self.partition,
            project_id=project_id,
        ):
            frames.append(frame)
            yield frame
            if frame.startswith("#error#"):
                rejected = True
                break

        if rejected:
            return

        rebuilt = _reconstruct(frames)

        # ---- write to grid ----
        doc_id = None
        if self.grid is not None:
            try:
                doc_id = self.grid.add_document(
                    rebuilt,
                    source="accodite-stream",
                    metadata={
                        "path": path,
                        "project_id": project_id,
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "org_id": org_id,
                    },
                )
            except Exception:
                doc_id = None

        # ---- follow-up event ----
        event: Optional[Dict[str, Any]] = None
        if self.follow is not None:
            try:
                result = self.follow.process_response(
                    query=query or "",
                    answer=rebuilt,
                    lang=lang or "en",
                    source="accodite-stream",
                    user_id=user_id,
                    org_id=org_id,
                    room_id=room_id,
                )
                if isinstance(result, dict):
                    event = result.get("event")
            except Exception:
                event = None

        followups: List[str] = []
        if event is not None and generate_follow_ups is not None:
            try:
                followups = list(generate_follow_ups(
                    query=query or "",
                    answer=rebuilt,
                    memory_grid=self.grid,
                ) or [])
            except Exception:
                followups = []

        # ---- partition trace ----
        if self.partition is not None and project_id is not None:
            try:
                self.partition.trace_project(project_id, {
                    "event": "stream_follow.complete",
                    "path": path,
                    "doc_id": doc_id,
                    "followups": followups,
                    "has_event": event is not None,
                })
            except Exception:
                pass

        if self.partition is not None:
            try:
                self.partition.partition_document({
                    "path": path,
                    "project_id": project_id,
                    "workspace_id": workspace_id,
                    "doc_id": doc_id,
                })
            except Exception:
                pass

        meta: Dict[str, Any] = {
            "path": path,
            "doc_id": doc_id,
            "followups": followups,
            "has_event": event is not None,
            "reconstructed_len": len(rebuilt),
        }
        yield f"#meta#{json.dumps(meta)}"

    # -----------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Consume the generator and return a structured dict.

        Returns:
            {
              ok: bool,
              error: str | None,
              frames: List[str],
              rebuilt: str,
              meta: dict | None,
            }
        """
        frames: List[str] = []
        meta: Optional[Dict[str, Any]] = None
        error: Optional[str] = None

        for frame in self.stream(**kwargs):
            frames.append(frame)
            if frame.startswith("#error#"):
                error = frame[len("#error#"):]
            elif frame.startswith("#meta#"):
                try:
                    meta = json.loads(frame[len("#meta#"):])
                except Exception:
                    meta = None

        return {
            "ok": error is None,
            "error": error,
            "frames": frames,
            "rebuilt": _reconstruct(frames),
            "meta": meta,
        }
