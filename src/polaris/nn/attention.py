"""Attention 与 Transformer 层（复刻 ``torch.nn``，规则 3）。

实现 Scaled Dot-Product Attention、Multi-Head Attention、TransformerBlock，
支持 ChipletFormer 风格的全局上下文建模。

修复 P0-C: 原实现 MultiHeadAttention.forward / TransformerBlock.forward
大量使用 ``.data`` 截断自动微分计算图，导致 w_q/w_k/w_v 参数无法接收梯度，
是 R03 禁止的假实现/fall-back。现实现自定义可微 attention op
（手动前向+反向，softmax/QK^T/V 反向公式），保留完整计算图，
w_q/w_k/w_v/w_o 全部可接收非零梯度，残差连接梯度可流回输入。

文献溯源（R02 学术诚信，公式/算法均可溯源）:
- Vaswani et al., 2017, "Attention Is All You Need", NeurIPS
  https://arxiv.org/abs/1706.03762
  （Scaled Dot-Product Attention、Multi-Head Attention、TransformerBlock
   编码器结构、1/sqrt(d_k) 缩放因子来源）
- Bahdanau et al., 2015, "Neural Machine Translation by Jointly Learning to
  Align and Translate", ICLR, https://arxiv.org/abs/1409.0473
  （注意力机制起源，additive attention → dot-product attention 演进）
- Kingma & Ba, 2015, "Adam: A Method for Stochastic Optimization", ICLR
  https://arxiv.org/abs/1412.6980
  （Adam 优化器，与本层配合训练时的默认 eps=1e-8/betas=(0.9,0.999) 一致）
- Glorot & Bengio, 2010, "Understanding the difficulty of training deep
  feedforward neural networks", AISTATS
  http://proceedings.mlr.press/v9/glorot10a/glorot10a.pdf
  （Xavier 初始化，w_q/w_k/w_v/w_o 投影矩阵方差稳定理论基础）
- Ba et al., 2016, "Layer Normalization", https://arxiv.org/abs/1607.06450
  （LayerNorm，TransformerBlock 残差后归一化的来源）
- Goodfellow et al., 2016, "Deep Learning" §6.2.2 softmax 反向
  https://www.deeplearningbook.org/
  （softmax 反向梯度公式 d_scores = attn ⊙ (d_attn - Σ(d_attn⊙attn))）
- PyTorch MultiheadAttention 实现参考:
  https://pytorch.org/docs/stable/generated/torch.nn.MultiheadAttention
- ChipletFormer (NeurIPS 2024): Transformer + GNN 融合布局布线
  https://mlforsystems.org/assets/papers/neurips2024/paper22.pdf
"""

from __future__ import annotations

import math

import numpy as np

from polaris.nn import Linear, Module, Tensor


class ScaledDotProductAttention(Module):
    """缩放点积注意力（Vaswani et al., 2017）。

    ``Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V``

    注意: 本类为 numpy 工具实现（非可微），用于测试/参考。
    可微版本见 ``_multi_head_attention_op``。

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


def _multi_head_attention_op(
    q: Tensor,
    k: Tensor,
    v: Tensor,
    num_heads: int,
    head_dim: int,
    embed_dim: int,
) -> Tensor:
    """可微多头注意力前向+反向（修复 P0-C）。

    将 q/k/v 投影、分头、attention、拼头、输出投影表达为自定义可微 op，
    手动实现反向传播，梯度可流回 w_q/w_k/w_v 参数。

    数学（来源: Vaswani et al. 2017 NeurIPS）:
    - scores = Q·K^T / sqrt(d_k)
    - attn = softmax(scores)
    - out = attn · V

    反向（来源: Goodfellow 2016 §6.2.2 softmax 反向）:
    - d_attn = d_out · V^T
    - d_v = attn^T · d_out
    - d_scores = attn ⊙ (d_attn - Σ(d_attn ⊙ attn, axis=-1))
    - d_q = d_scores · K / sqrt(d_k)
    - d_k = d_scores^T · Q / sqrt(d_k)

    Args:
        q: 查询 Tensor [seq, embed]（来自 w_q 投影，requires_grad=True）。
        k: 键 Tensor [seq, embed]。
        v: 值 Tensor [seq, embed]。
        num_heads: 头数。
        head_dim: 每头维度。
        embed_dim: 嵌入维度。

    Returns:
        注意力输出 Tensor [seq, embed]，保留计算图。
    """
    seq_len = q.data.shape[0]
    # 前向（用 .data 计算，但记录 parents 供反向）
    q3d = q.data.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)  # [h,s,d]
    k3d = k.data.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
    v3d = v.data.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
    d_k = head_dim
    scores = q3d @ k3d.swapaxes(-2, -1) / math.sqrt(d_k)  # [h,s,s]
    scores_max = scores.max(axis=-1, keepdims=True)
    exp_scores = np.exp(scores - scores_max)
    attn = exp_scores / exp_scores.sum(axis=-1, keepdims=True)
    out_3d = attn @ v3d  # [h,s,d]
    out_data = out_3d.transpose(1, 0, 2).reshape(seq_len, embed_dim)  # [s,embed]
    rg = q.requires_grad or k.requires_grad or v.requires_grad
    out = Tensor(out_data, rg, (q, k, v))

    def _back(g: np.ndarray) -> None:
        # g: [seq, embed] → [h, s, d]
        g3d = g.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
        # d_out = attn @ v → d_attn, d_v
        grad_attn = g3d @ v3d.swapaxes(-2, -1)  # [h,s,s]
        grad_v_3d = attn.swapaxes(-2, -1) @ g3d  # [h,s,d]
        # softmax 反向: d_scores = attn ⊙ (d_attn - Σ(d_attn⊙attn))
        grad_scores = attn * (
            grad_attn - (grad_attn * attn).sum(axis=-1, keepdims=True)
        )
        grad_scores = grad_scores / math.sqrt(d_k)
        # d_scores = Q·K^T / sqrt(d_k) → d_q, d_k
        grad_q_3d = grad_scores @ k3d  # [h,s,d]
        grad_k_3d = grad_scores.swapaxes(-2, -1) @ q3d  # [h,s,d]
        # 还原为 [seq, embed]
        if q.requires_grad:
            q._ensure_grad()
            q.grad = q.grad + grad_q_3d.transpose(1, 0, 2).reshape(seq_len, embed_dim)
        if k.requires_grad:
            k._ensure_grad()
            k.grad = k.grad + grad_k_3d.transpose(1, 0, 2).reshape(seq_len, embed_dim)
        if v.requires_grad:
            v._ensure_grad()
            v.grad = v.grad + grad_v_3d.transpose(1, 0, 2).reshape(seq_len, embed_dim)

    out._backward = _back
    return out


class MultiHeadAttention(Module):
    """多头注意力（Vaswani et al., 2017）。

    将 Q/K/V 投影到 h 个头，并行计算注意力后拼接。

    修复 P0-C: 原实现用 ``.data`` 截断计算图，w_q/w_k/w_v 无法接收梯度。
    现使用 ``_multi_head_attention_op`` 自定义可微 op，保留完整计算图。

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
        """前向：投影 → 分头 → 注意力 → 拼接 → 输出投影（全可微）。"""
        # 投影（Linear 返回 Tensor，保留计算图）
        q = self.w_q(x)  # Tensor [seq, embed]
        k = self.w_k(x)
        v = self.w_v(x)
        # 可微多头注意力（不再用 .data 截断）
        out = _multi_head_attention_op(
            q, k, v, self.num_heads, self.head_dim, self.embed_dim
        )
        # 输出投影（Tensor → Linear，梯度可流回 w_o 和 attention）
        return self.w_o(out)

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

    修复 P0-C: 原实现残差用 ``Tensor(x.data + sublayer(x).data)`` 截断计算图。
    现用 ``x + sublayer(x)``（Tensor.__add__ 可微），保留残差梯度。

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
        """前向：Attention + 残差 + FFN + 残差（全可微，无 .data 截断）。"""
        # 自注意力 + 残差（Tensor.__add__ 可微）+ LayerNorm
        attn_out = self.attn(x)
        x = self.norm1(x + attn_out)
        # FFN + 残差 + LayerNorm
        ff_out = self.ff2(self.relu(self.ff1(x)))
        x = self.norm2(x + ff_out)
        return x

    def parameters(self) -> list[Tensor]:
        params = self.attn.parameters()
        params += self.norm1.parameters() + self.norm2.parameters()
        params += self.ff1.parameters() + self.ff2.parameters()
        return params


__all__ = ["ScaledDotProductAttention", "MultiHeadAttention", "TransformerBlock"]
