"""
CoMpaNeoNAccodite — AI Model
============================
140 heads total:
    96 base heads   -> 48 pairs -> segment-bound at inference
    44 special heads-> global    -> control / shaping

Segment routing:
    head_segment:        LongTensor[n_heads]  (-1 for special heads)
    segment_token_mask:  BoolTensor[B, n_segments, Lk]
    -> per-head attention mask limits base heads to their segment.
"""
from __future__ import annotations
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from model.head_router import (
    TOTAL_HEADS, BASE_HEADS, SPECIAL_HEADS,
    POOL_A_RANGE, POOL_B_RANGE, POOL_C_RANGE, POOL_D_RANGE,
    SPECIAL_RANGES,
)


def build_default_head_segment_map() -> torch.Tensor:
    """
    Return a [TOTAL_HEADS] LongTensor where:
        base heads     = 0..47  (pair index 0-47)
        special heads  = -1     (global)
    Pairs are indexed by pair-id, matching model.head_router.
    """
    m = torch.full((TOTAL_HEADS,), -1, dtype=torch.long)
    for pair_idx in range(BASE_HEADS // 2):
        m[pair_idx * 2] = pair_idx
        m[pair_idx * 2 + 1] = pair_idx
    return m


class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.q_linear = nn.Linear(d_model, d_model)
        self.k_linear = nn.Linear(d_model, d_model)
        self.v_linear = nn.Linear(d_model, d_model)
        self.out_linear = nn.Linear(d_model, d_model)
        self.scale = math.sqrt(self.head_dim)

    def forward(self, q, k, v, mask=None, head_mask=None):
        """
        mask:       [B, 1, Lq, Lk] or broadcastable, True = keep, False = mask
        head_mask:  [B, H, Lq, Lk]  True = keep, False = mask
        """
        B, Lq, _ = q.size()
        Lk = k.size(1)
        H = self.n_heads
        Hd = self.head_dim

        q = self.q_linear(q).view(B, Lq, H, Hd).transpose(1, 2)
        k = self.k_linear(k).view(B, Lk, H, Hd).transpose(1, 2)
        v = self.v_linear(v).view(B, Lk, H, Hd).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) / self.scale

        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        if head_mask is not None:
            scores = scores.masked_fill(head_mask == 0, -1e9)

        attn = F.softmax(scores, dim=-1)
        ctx = torch.matmul(attn, v)
        ctx = ctx.transpose(1, 2).contiguous().view(B, Lq, self.d_model)
        return self.out_linear(ctx)


class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(d_model, n_heads)
        self.norm1 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
        self.norm2 = nn.LayerNorm(d_model)

    def forward(self, x, mask=None, head_mask=None):
        x = self.norm1(x + self.attn(x, x, x, mask, head_mask))
        x = self.norm2(x + self.ff(x))
        return x


class MiniCompanionAI(nn.Module):
    """
    Backward-compatible MiniCompanionAI with segment-aware attention.

    New optional args:
        n_heads=140, head_dim=8  -> d_model = 1120 by default
        head_segment_map: LongTensor[TOTAL_HEADS], -1 for special heads
        segment_token_mask: [B, n_segments, Lk] bool, forwarded at runtime
    """
    def __init__(
        self,
        vocab_size,
        d_model=1120,
        n_heads=TOTAL_HEADS,
        n_layers=2,
        max_len=512,
        d_ff=2048,
        head_segment_map: torch.Tensor | None = None,
    ):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.position_embedding = nn.Embedding(max_len, d_model)
        self.blocks = nn.ModuleList([
            TransformerBlock(d_model, n_heads, d_ff) for _ in range(n_layers)
        ])
        self.ln_final = nn.LayerNorm(d_model)
        self.fc_out = nn.Linear(d_model, vocab_size)

        if head_segment_map is None:
            head_segment_map = build_default_head_segment_map()
        self.register_buffer("head_segment_map", head_segment_map, persistent=False)

    # -----------------------------------------------------------------

    def _expand_head_mask(
        self,
        segment_token_mask: torch.Tensor,
        Lq: int,
        Lk: int,
        device,
    ) -> torch.Tensor:
        """
        segment_token_mask: [B, S, Lk] bool   (tokens belonging to each segment)
        returns:            [B, H, Lq, Lk] bool
        """
        B = segment_token_mask.size(0)
        H = self.n_heads
        seg_ids = self.head_segment_map.to(device)              # [H]
        is_special = (seg_ids == -1)                            # [H]

        # base heads -> gather their segment's token mask
        safe = seg_ids.clamp(min=0)                             # [H]
        per_head = segment_token_mask[:, safe, :]               # [B, H, Lk]
        per_head = per_head.unsqueeze(2).expand(B, H, Lq, Lk)   # broadcast over Lq

        # special heads attend everywhere
        all_true = torch.ones((B, H, Lq, Lk), dtype=torch.bool, device=device)
        per_head = torch.where(is_special.view(1, H, 1, 1), all_true, per_head)
        return per_head

    # -----------------------------------------------------------------

    def forward(
        self,
        x,
        mask=None,
        segment_token_mask: torch.Tensor | None = None,
    ):
        """
        x: [B, L]
        mask: [B, 1, L, L] or None
        segment_token_mask: [B, S, L] bool  (optional)
        """
        B, L = x.size()
        positions = torch.arange(0, L, device=x.device).unsqueeze(0)
        h = self.token_embedding(x) + self.position_embedding(positions)

        head_mask = None
        if segment_token_mask is not None:
            head_mask = self._expand_head_mask(
                segment_token_mask, L, L, x.device
            ).to(dtype=torch.bool)

        for block in self.blocks:
            h = block(h, mask=mask, head_mask=head_mask)
        h = self.ln_final(h)
        return self.fc_out(h)
