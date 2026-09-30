"""
Accodite AI Model (v2)
======================
Upgrades over v1:
    - RoPE (rotary positional encoding): language-agnostic, code-switch safe
    - GSP keyboard prior injected into QKV attention
    - Multilingual token embedding (token + lang embedding)
    - d_model raised: head_dim configurable, larger default
    - head_segment_map is rebindable at runtime (not a buffer)
    - Dynamic segment binding via segment_token_mask
    - KV cache reuse across forward passes
    - Optional memory_partition hook for building attention masks

Head layout (unchanged):
    96 base heads   -> 48 pairs -> segment-bound
    44 special heads-> global   -> control / enforcement
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple

# ACCD-TORCH-GUARD: model classes need torch; module imports without it.
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    F = None

    class _StubModule:
        """Placeholder for nn.Module so class bodies still execute."""
        def __init__(self, *a, **k):
            pass
        def __call__(self, *a, **k):
            raise RuntimeError(
                "torch is required to instantiate model classes"
            )

    class _StubNN:
        Module = _StubModule
        Linear = _StubModule
        Embedding = _StubModule
        LayerNorm = _StubModule
        Dropout = _StubModule
        Sequential = _StubModule
        ModuleList = _StubModule

    nn = _StubNN()
    TORCH_AVAILABLE = False

from model.head_router import TOTAL_HEADS, BASE_HEADS, SPECIAL_HEADS, PAIRS


# ============================================================================
# DEFAULTS
# ============================================================================

DEFAULT_D_MODEL  = 2240      # 140 heads x 16 head_dim
DEFAULT_HEAD_DIM = 16
DEFAULT_D_FF     = 4096
DEFAULT_MAX_LEN  = 4096
DEFAULT_N_LANGS  = 64


# ============================================================================
# HEAD MAP
# ============================================================================

def build_default_head_segment_map():
    """Return a length-TOTAL_HEADS map: pair idx for base heads, -1 for specials.

    Returns a torch.LongTensor when torch is available, else a plain list.
    """
    if not TORCH_AVAILABLE:
        m = [-1] * TOTAL_HEADS
        for pair_idx in range(PAIRS):
            m[pair_idx * 2] = pair_idx
            m[pair_idx * 2 + 1] = pair_idx
        return m
    m = torch.full((TOTAL_HEADS,), -1, dtype=torch.long)
    for pair_idx in range(PAIRS):
        m[pair_idx * 2] = pair_idx
        m[pair_idx * 2 + 1] = pair_idx
    return m


# ============================================================================
# ROTARY POSITIONAL ENCODING
# ============================================================================

class RotaryPositionalEncoding(nn.Module):
    """
    RoPE applied to Q and K.

    Language-agnostic: the positional signal is relative and carries no
    language-specific parameters, so code-switching and mixed-language
    sequences use the same geometry.
    """
    def __init__(self, head_dim: int, base: float = 10000.0):
        super().__init__()
        if head_dim % 2 != 0:
            raise ValueError("head_dim must be even for RoPE")
        self.head_dim = head_dim
        inv_freq = 1.0 / (base ** (torch.arange(0, head_dim, 2).float() / head_dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    def _freqs(self, seq_len: int, device, dtype):
        pos = torch.arange(seq_len, device=device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(pos, self.inv_freq)
        return freqs.cos().to(dtype), freqs.sin().to(dtype)

    @staticmethod
    def _rotate_half(x):
        x1 = x[..., : x.shape[-1] // 2]
        x2 = x[..., x.shape[-1] // 2 :]
        return torch.cat((-x2, x1), dim=-1)

    def apply(self, q, k, *, offset: int = 0):
        L = q.shape[-2]
        cos, sin = self._freqs(offset + L, q.device, q.dtype)
        cos = cos[offset: offset + L].unsqueeze(0).unsqueeze(0)
        sin = sin[offset: offset + L].unsqueeze(0).unsqueeze(0)
        cos = torch.cat([cos, cos], dim=-1)
        sin = torch.cat([sin, sin], dim=-1)
        q_ = q * cos + self._rotate_half(q) * sin
        k_ = k * cos + self._rotate_half(k) * sin
        return q_, k_


# ============================================================================
# ATTENTION
# ============================================================================

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads, dropout=0.0):
        super().__init__()
        if d_model % n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.q_linear = nn.Linear(d_model, d_model, bias=False)
        self.k_linear = nn.Linear(d_model, d_model, bias=False)
        self.v_linear = nn.Linear(d_model, d_model, bias=False)
        self.out_linear = nn.Linear(d_model, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        self.rope = RotaryPositionalEncoding(self.head_dim)

    def forward(
        self,
        q, k, v,
        *,
        mask: Optional[torch.Tensor] = None,          # [B,1,Lq,Lk_all]
        head_mask: Optional[torch.Tensor] = None,     # [B,H,Lq,Lk_all]
        gsp_prior: Optional[torch.Tensor] = None,     # [B,1|H,Lq,Lk_all]
        kv_cache: Optional[Dict[str, Any]] = None,
    ):
        B, Lq, _ = q.size()
        Lk = k.size(1)
        H = self.n_heads
        Hd = self.head_dim

        q_ = self.q_linear(q).view(B, Lq, H, Hd).transpose(1, 2)
        k_ = self.k_linear(k).view(B, Lk, H, Hd).transpose(1, 2)
        v_ = self.v_linear(v).view(B, Lk, H, Hd).transpose(1, 2)

        offset = 0
        if kv_cache is not None:
            past_k = kv_cache.get("k")
            past_v = kv_cache.get("v")
            offset = kv_cache.get("offset", 0)
            if past_k is not None and past_v is not None:
                k_ = torch.cat([past_k, k_], dim=2)
                v_ = torch.cat([past_v, v_], dim=2)

        # RoPE on the new tokens only
        q_new, k_new = self.rope.apply(q_, k_[:, :, offset: offset + Lq, :], offset=offset)
        if offset > 0:
            k_ = torch.cat([k_[:, :, :offset, :], k_new], dim=2)
        else:
            k_ = k_new
        q_ = q_new

        if kv_cache is not None:
            kv_cache["k"] = k_.detach()
            kv_cache["v"] = v_.detach()
            kv_cache["offset"] = offset + Lq

        scale = math.sqrt(Hd)
        scores = torch.matmul(q_, k_.transpose(-2, -1)) / scale

        if gsp_prior is not None:
            scores = scores + gsp_prior.to(scores.dtype)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        if head_mask is not None:
            scores = scores.masked_fill(head_mask == 0, -1e9)

        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)
        ctx = torch.matmul(attn, v_)
        ctx = ctx.transpose(1, 2).contiguous().view(B, Lq, self.d_model)
        return self.out_linear(ctx)


# ============================================================================
# TRANSFORMER BLOCK
# ============================================================================

class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(d_model, n_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
        self.norm2 = nn.LayerNorm(d_model)

    def forward(self, x, *, mask=None, head_mask=None, gsp_prior=None, kv_cache=None):
        h = self.norm1(x)
        x = x + self.attn(h, h, h, mask=mask, head_mask=head_mask,
                          gsp_prior=gsp_prior, kv_cache=kv_cache)
        x = x + self.ff(self.norm2(x))
        return x


# ============================================================================
# MODEL
# ============================================================================

class MiniCompanionAI(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        d_model: int = DEFAULT_D_MODEL,
        n_heads: int = TOTAL_HEADS,
        n_layers: int = 4,
        max_len: int = DEFAULT_MAX_LEN,
        d_ff: int = DEFAULT_D_FF,
        dropout: float = 0.1,
        n_langs: int = DEFAULT_N_LANGS,
        head_segment_map: Optional[torch.Tensor] = None,
    ):
        super().__init__()
        if d_model % n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")

        self.d_model = d_model
        self.n_heads = n_heads
        self.max_len = max_len
        self.n_langs = n_langs

        # multilingual embeddings: token + language id
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.lang_embedding  = nn.Embedding(n_langs, d_model)
        self.dropout_in = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([
            TransformerBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])
        self.ln_final = nn.LayerNorm(d_model)
        self.fc_out = nn.Linear(d_model, vocab_size, bias=False)

        # runtime-rebindable head-segment map (plain attribute, not buffer)
        if head_segment_map is None:
            head_segment_map = build_default_head_segment_map()
        self.head_segment_map: torch.Tensor = head_segment_map

    # -----------------------------------------------------------------
    # dynamic binding
    # -----------------------------------------------------------------

    def set_head_segment_map(self, mapping) -> None:
        """
        Rebind which head pairs attend to which segments at runtime.

        mapping: LongTensor[n_heads] or list of ints.
                 base heads carry their pair index (0..47);
                 special heads carry -1 (attend everywhere).
        """
        if not isinstance(mapping, torch.Tensor):
            mapping = torch.tensor(mapping, dtype=torch.long)
        if mapping.numel() != self.n_heads:
            raise ValueError(
                f"head_segment_map must have {self.n_heads} entries, "
                f"got {mapping.numel()}"
            )
        self.head_segment_map = mapping

    def _expand_head_mask(self, segment_token_mask, Lq, Lk, device):
        """
        segment_token_mask: [B, S, Lk]  (bool)
        -> [B, H, Lq, Lk]  (bool)
        Special heads (map == -1) attend everywhere.
        """
        B = segment_token_mask.size(0)
        H = self.n_heads
        seg_ids = self.head_segment_map.to(device)
        is_special = (seg_ids == -1)
        safe = seg_ids.clamp(min=0)
        per_head = segment_token_mask[:, safe, :]              # [B,H,Lk]
        per_head = per_head.unsqueeze(2).expand(B, H, Lq, Lk)  # broadcast Lq
        all_true = torch.ones((B, H, Lq, Lk), dtype=torch.bool, device=device)
        return torch.where(is_special.view(1, H, 1, 1), all_true, per_head)

    # -----------------------------------------------------------------
    # memory_partition hook
    # -----------------------------------------------------------------

    @staticmethod
    def build_segment_token_mask(
        *,
        partition: Any,
        batch_segments: List[List[str]],
        seq_len: int,
        device,
    ) -> Optional[torch.Tensor]:
        """
        Ask memory_partition which token positions belong to which segment.

        partition must expose:
            .tokens_for_segment(segment_id) -> Iterable[int]

        Returns [B, S, L] bool, or None if partition is None.
        """
        if partition is None:
            return None
        B = len(batch_segments)
        S = max((len(segs) for segs in batch_segments), default=0)
        if S == 0:
            return None
        mask = torch.zeros((B, S, seq_len), dtype=torch.bool, device=device)
        for b, segs in enumerate(batch_segments):
            for s, seg_id in enumerate(segs):
                try:
                    idxs = list(partition.tokens_for_segment(seg_id) or [])
                except Exception:
                    idxs = []
                for i in idxs:
                    if 0 <= i < seq_len:
                        mask[b, s, i] = True
        return mask

    # -----------------------------------------------------------------
    # forward
    # -----------------------------------------------------------------

    def forward(
        self,
        x,
        *,
        lang_ids: Optional[torch.Tensor] = None,
        mask: Optional[torch.Tensor] = None,
        segment_token_mask: Optional[torch.Tensor] = None,
        gsp_prior: Optional[torch.Tensor] = None,
        kv_cache: Optional[Dict[int, Dict[str, Any]]] = None,
        partition: Any = None,
        batch_segments: Optional[List[List[str]]] = None,
    ):
        """
        x:                  [B, L] token ids
        lang_ids:           [B, L] language ids (optional)
        mask:               [B, 1, L, L] causal/attention mask (optional)
        segment_token_mask: [B, S, L] bool (optional, or auto-built via partition)
        gsp_prior:          [B, 1, L, L] or [B, H, L, L] additive bias (optional)
        kv_cache:           dict of per-layer dicts (optional, for streaming)
        partition:          MemoryPartition-like object (optional)
        batch_segments:     list of segment id lists per batch item (optional)
        """
        B, L = x.size()
        h = self.token_embedding(x)
        if lang_ids is not None:
            h = h + self.lang_embedding(lang_ids)
        h = self.dropout_in(h)

        head_mask = None
        if segment_token_mask is None and partition is not None and batch_segments is not None:
            segment_token_mask = self.build_segment_token_mask(
                partition=partition,
                batch_segments=batch_segments,
                seq_len=L,
                device=x.device,
            )
        if segment_token_mask is not None:
            head_mask = self._expand_head_mask(segment_token_mask, L, L, x.device)

        for i, block in enumerate(self.blocks):
            layer_cache = None
            if kv_cache is not None:
                layer_cache = kv_cache.setdefault(i, {})
            h = block(
                h,
                mask=mask,
                head_mask=head_mask,
                gsp_prior=gsp_prior,
                kv_cache=layer_cache,
            )

        h = self.ln_final(h)
        return self.fc_out(h)


# ============================================================================
# HELPERS
# ============================================================================

def build_causal_mask(seq_len: int, device) -> torch.Tensor:
    """[1, 1, L, L] lower-triangular bool."""
    m = torch.tril(torch.ones((seq_len, seq_len), dtype=torch.bool, device=device))
    return m.view(1, 1, seq_len, seq_len)


def build_gsp_prior(
    *,
    query_gsp: torch.Tensor,       # [B, Lq, D]
    key_gsp: torch.Tensor,         # [B, Lk, D]
    scale: float = 1.0,
) -> torch.Tensor:
    """
    Build an additive attention bias from GSP keyboard vectors.

    query_gsp, key_gsp are [B, L, D] float tensors (from keyboard.py).
    Returns [B, 1, Lq, Lk] additive bias.
    """
    sim = torch.matmul(query_gsp, key_gsp.transpose(-2, -1))   # [B, Lq, Lk]
    return (sim * scale).unsqueeze(1)
