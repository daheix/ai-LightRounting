"""Attention 与 Transformer 层（复刻 ``torch.nn``，规则 3）。

实现 Scaled Dot-Product Attention、Multi-Head Attention、TransformerBlock，
支持 ChipletFormer 风格的全局上下文建模。

来源:
- Vaswani et al., 2017, "Attention Is All You Need", NeurIPS
  https://arxiv.org/abs/1706.03762
- ChipletFormer (NeurIPS 2024): Transformer + GNN 融合布局布线
  https://mlforsystems.org/assets/papers/neurips2024/paper22.pdf
- PyTorch MultiheadAttention:
  https://pytorch.org/docs/stable/generated/torch.nn.MultiheadAttention
"""

from __future__ import annotations

import math

import numpy as np

from polaris.nn import Linear, Module, Tensor


class ScaledDotProductAttention(Module):
    """缩放点积注意力（Vaswani et al., 2017）。

    ``Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V``

    来源: Vaswani et al., 2017, https://arxiv.org/abs/1706.03762
    """

    def __init__(self, dropout: float = 0.0) -> None:
        self.dropout_p = dropout

    def forward(
        self,
        query: np.ndarray,
        key: np.ndarray,
        value: np.ndarray,
    ) -> np.ndarray:
        """前向：QK^T / sqrt(d_k) → softmax → V。"""
        d_k = query.shape[-1]
        scores = query @ key.swapaxes(-2, -1) / math.sqrt(d_k)
        # 数值稳定 softmax
        scores_max = scores.max(axis=-1, keepdims=True)
        exp_scores = np.exp(scores - scores_max)
        attn_weights = exp_scores / exp_scores.sum(axis=-1, keepdims=True)
        return attn_weights @ value


class MultiHeadAttention(Module):
    """多头注意力（Vaswani et al., 2017）。

    将 Q/K/V 投影到 h 个头，并行计算注意力后拼接。

    来源: Vaswani et al., 2017, https://arxiv.org/abs/1706.03762
    """

    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        dropout: float = 0.0,
    ) -> None:
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        if self.head_dim * num_heads != embed_dim:
            raise ValueError("embed_dim 必须能被 num_heads 整除")
        self.w_q = Linear(embed_dim, embed_dim)
        self.w_k = Linear(embed_dim, embed_dim)
        self.w_v = Linear(embed_dim, embed_dim)
        self.w_o = Linear(embed_dim, embed_dim)
        self.attn = ScaledDotProductAttention(dropout)

    def forward(self, x: Tensor) -> Tensor:
        """前向：投影 → 分头 → 注意力 → 拼接 → 输出投影。"""
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        seq_len = data.shape[0]
        # 投影
        q = self.w_q(x).data.reshape(seq_len, self.num_heads, self.head_dim)
        k = self.w_k(x).data.reshape(seq_len, self.num_heads, self.head_dim)
        v = self.w_v(x).data.reshape(seq_len, self.num_heads, self.head_dim)
        # 转置为 (heads, seq, head_dim)
        q = q.transpose(1, 0, 2)
        k = k.transpose(1, 0, 2)
        v = v.transpose(1, 0, 2)
        # 注意力
        out = self.attn.forward(q, k, v)  # (heads, seq, head_dim)
        # 拼接头
        out = out.transpose(1, 0, 2).reshape(seq_len, self.embed_dim)
        return self.w_o(Tensor(out))

    def parameters(self) -> list[Tensor]:
        return (
            self.w_q.parameters()
            + self.w_k.parameters()
            + self.w_v.parameters()
            + self.w_o.parameters()
        )


class TransformerBlock(Module):
    """Transformer 编码器块（Vaswani et al., 2017）。

    Multi-Head Attention + FFN + 残差 + LayerNorm。

    来源:
    - Vaswani et al., 2017, https://arxiv.org/abs/1706.03762
    - ChipletFormer (NeurIPS 2024): Transformer + GNN 融合
      https://mlforsystems.org/assets/papers/neurips2024/paper22.pdf
    """

    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        ff_dim: int | None = None,
        dropout: float = 0.1,
    ) -> None:
        ff_dim = ff_dim or 4 * embed_dim
        self.attn = MultiHeadAttention(embed_dim, num_heads, dropout)
        from polaris.nn import LayerNorm, ReLU

        self.norm1 = LayerNorm(embed_dim)
        self.norm2 = LayerNorm(embed_dim)
        self.ff1 = Linear(embed_dim, ff_dim)
        self.ff2 = Linear(ff_dim, embed_dim)
        self.relu = ReLU()
        self.dropout_p = dropout

    def forward(self, x: Tensor) -> Tensor:
        """前向：Attention + 残差 + FFN + 残差。"""
        # 自注意力 + 残差 + LayerNorm
        attn_out = self.attn(x)
        x = self.norm1(Tensor(x.data + attn_out.data))
        # FFN + 残差 + LayerNorm
        ff_out = self.ff2(self.relu(self.ff1(x)))
        x = self.norm2(Tensor(x.data + ff_out.data))
        return x

    def parameters(self) -> list[Tensor]:
        params = self.attn.parameters()
        params += self.norm1.parameters() + self.norm2.parameters()
        params += self.ff1.parameters() + self.ff2.parameters()
        return params


__all__ = ["ScaledDotProductAttention", "MultiHeadAttention", "TransformerBlock"]
