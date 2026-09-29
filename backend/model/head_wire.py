"""
Accodite Head Wiring
====================
Bridges HeadAllocator -> MiniCompanionAI.

Two conversions:

    1. BindingPlan -> head_segment_map [TOTAL_HEADS]
         base heads  : segment index (0..S-1)
         special heads: -1

    2. token labels -> segment_token_mask [B, S, L]
         token at position i is True for segment s iff its label == s
         label None matches every segment (attend everywhere)

Runtime usage:
    from model.head_wire import run_with_binding
    out = run_with_binding(model, tokens, plan, token_segment_ids=labels)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from model.head_router import TOTAL_HEADS, PAIRS, BindingPlan, Segment


# ============================================================================
# PLAN -> HEAD MAP
# ============================================================================

def plan_to_head_map(
    plan: BindingPlan,
) -> Tuple[List[int], Dict[str, int]]:
    """
    Convert a BindingPlan into (head_map, segment_to_idx).

    head_map:        length TOTAL_HEADS, values are segment indices
                     (0..S-1) for base heads, -1 for special heads.
    segment_to_idx:  segment_id -> index into the mask dimension.
    """
    ordered: List[str] = []
    for pair_idx in sorted(plan.assignments.keys()):
        seg = plan.assignments[pair_idx]
        if seg is not None and seg.segment_id not in ordered:
            ordered.append(seg.segment_id)
    seg_to_idx: Dict[str, int] = {sid: i for i, sid in enumerate(ordered)}

    head_map: List[int] = [-1] * TOTAL_HEADS
    for pair_idx, seg in plan.assignments.items():
        if seg is None:
            continue
        if pair_idx < 0 or pair_idx >= PAIRS:
            continue
        idx = seg_to_idx.get(seg.segment_id)
        if idx is None:
            continue
        h1 = pair_idx * 2
        h2 = h1 + 1
        if 0 <= h1 < TOTAL_HEADS:
            head_map[h1] = idx
        if 0 <= h2 < TOTAL_HEADS:
            head_map[h2] = idx
    return head_map, seg_to_idx


def plan_segment_order(plan: BindingPlan) -> List[str]:
    """Stable ordering of segment ids present in a plan."""
    seen: List[str] = []
    for pair_idx in sorted(plan.assignments.keys()):
        seg = plan.assignments[pair_idx]
        if seg is None:
            continue
        if seg.segment_id not in seen:
            seen.append(seg.segment_id)
    return seen


# ============================================================================
# MODEL HOOK
# ============================================================================

def apply_binding_to_model(model, plan: BindingPlan) -> Dict[str, int]:
    """
    Push the plan into the model's runtime head map.
    Returns segment_to_idx for later mask construction.
    """
    head_map, seg_to_idx = plan_to_head_map(plan)
    if hasattr(model, "set_head_segment_map"):
        model.set_head_segment_map(head_map)
    else:
        # tolerate models without the setter
        try:
            model.head_segment_map = head_map
        except Exception:
            pass
    return seg_to_idx


# ============================================================================
# TOKEN LABELS -> SEGMENT MASK
# ============================================================================

def token_labels_to_mask(
    token_segment_ids: List[Optional[str]],
    seg_to_idx: Dict[str, int],
) -> List[List[bool]]:
    """
    Build [S, L] bool. S = len(seg_to_idx), L = len(token_segment_ids).

    A token at position i is True for segment s when:
        - its label == segment_id at index s, OR
        - its label is None (attend everywhere)
    """
    S = len(seg_to_idx)
    L = len(token_segment_ids)
    idx_to_seg = {i: sid for sid, i in seg_to_idx.items()}
    mask: List[List[bool]] = [[False] * L for _ in range(S)]
    for s in range(S):
        sid = idx_to_seg.get(s)
        for i, label in enumerate(token_segment_ids):
            if label is None or label == sid:
                mask[s][i] = True
    return mask


# ============================================================================
# ONE-SHOT: BIND + FORWARD
# ============================================================================

def run_with_binding(
    model,
    tokens,
    plan: BindingPlan,
    *,
    token_segment_ids: Optional[List[Optional[str]]] = None,
    partition: Any = None,
    batch_segments: Optional[List[List[str]]] = None,
    **forward_kwargs,
):
    """
    Bind the model's head map from a plan, build the segment mask if
    labels are provided, then run a forward pass.

    - token_segment_ids: length L, one label per token position.
    - partition + batch_segments: alternative path; passed straight
      through to model.forward, which builds the mask itself.
    """
    seg_to_idx = apply_binding_to_model(model, plan)

    stm = None
    if token_segment_ids is not None:
        try:
            import torch
            per_item = token_labels_to_mask(token_segment_ids, seg_to_idx)
            device = getattr(tokens, "device", "cpu")
            stm = torch.tensor([per_item], dtype=torch.bool, device=device)
        except ImportError:
            stm = None

    return model(
        tokens,
        segment_token_mask=stm,
        partition=partition,
        batch_segments=batch_segments,
        **forward_kwargs,
    )
