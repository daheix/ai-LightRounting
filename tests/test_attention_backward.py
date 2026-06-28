"""P0-C 回归测试：验证 MultiHeadAttention / TransformerBlock 可微性。

背景: 原实现 ``MultiHeadAttention.forward`` / ``TransformerBlock.forward``
使用 ``.data`` 截断自动微分计算图，导致 ``w_q`` / ``w_k`` / ``w_v`` 等参数
无法接收梯度（R03 禁止 fall-back：假实现）。commit f14009e 已用自定义可微
``_multi_head_attention_op`` 修复，本测试为回归保护。

测试覆盖:
- forward + backward 不抛异常
- 损失对各权重 (w_q/w_k/w_v/w_o) 梯度非 None 且非零
- 残差连接梯度可流向输入 x
- 反向梯度与数值有限差分一致（R02 学术诚信）

文献溯源:
- Vaswani et al., 2017, "Attention Is All You Need", NeurIPS
  https://arxiv.org/abs/1706.03762
- Bahdanau et al., 2015, "Neural Machine Translation by Jointly Learning to
  Align and Translate", ICLR, https://arxiv.org/abs/1409.0473
- Goodfellow et al., 2016, "Deep Learning" §6.2.2 softmax 反向
  https://www.deeplearningbook.org/
- Kingma & Ba, 2015, "Adam", ICLR, https://arxiv.org/abs/1412.6980
- Ba et al., 2016, "Layer Normalization", https://arxiv.org/abs/1607.06450
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.nn import Tensor
from polaris.nn.attention import (
    MultiHeadAttention,
    TransformerBlock,
    _multi_head_attention_op,
)


def _seed() -> None:
    np.random.seed(42)


# ---------------------------------------------------------------------------
# 1. forward + backward 不抛异常
# ---------------------------------------------------------------------------
def test_mha_forward_backward_no_exception() -> None:
    """MHA 前向 + 反向必须完整运行无异常（R03: 不再是假实现）。"""
    _seed()
    mha = MultiHeadAttention(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = mha(x)
    assert out.shape == (4, 8)
    loss = (out * out).sum()
    # 不应抛出任何异常
    loss.backward()
    assert loss.data.ndim == 0 or loss.data.size == 1


def test_transformer_block_forward_backward_no_exception() -> None:
    """TransformerBlock 前向 + 反向必须完整运行无异常。"""
    _seed()
    tb = TransformerBlock(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = tb(x)
    assert out.shape == (4, 8)
    loss = (out * out).mean()
    loss.backward()


# ---------------------------------------------------------------------------
# 2. 各权重梯度非 None 且非零
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("weight_attr", ["w_q", "w_k", "w_v", "w_o"])
def test_mha_weight_grad_nonzero(weight_attr: str) -> None:
    """MHA 各投影权重梯度必须非 None 且存在非零元素。"""
    _seed()
    mha = MultiHeadAttention(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = mha(x)
    loss = (out * out).sum()
    loss.backward()
    layer = getattr(mha, weight_attr)
    assert layer.weight.grad is not None, f"{weight_attr}.weight.grad is None"
    assert np.any(
        layer.weight.grad != 0.0
    ), f"{weight_attr}.weight.grad 全为零，计算图被截断"
    if layer.bias is not None:
        assert layer.bias.grad is not None, f"{weight_attr}.bias.grad is None"
        assert np.any(layer.bias.grad != 0.0)


def test_transformer_block_all_params_grad_nonzero() -> None:
    """TransformerBlock 所有可训练参数梯度必须非 None 且非零。"""
    _seed()
    tb = TransformerBlock(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = tb(x)
    loss = (out * out).sum()
    loss.backward()
    params = tb.parameters()
    assert len(params) > 0, "TransformerBlock 无可训练参数"
    for i, p in enumerate(params):
        assert p.grad is not None, f"参数 #{i} 梯度为 None"
        assert np.any(p.grad != 0.0), f"参数 #{i} 梯度全为零"


# ---------------------------------------------------------------------------
# 3. 残差连接梯度可流向输入
# ---------------------------------------------------------------------------
def test_mha_input_grad_flows() -> None:
    """MHA 输入 x 梯度必须可反向流回（注意力路径）。"""
    _seed()
    mha = MultiHeadAttention(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = mha(x)
    loss = (out * out).sum()
    loss.backward()
    assert x.grad is not None, "输入 x.grad 为 None（计算图未连通）"
    assert np.any(x.grad != 0.0), "输入 x.grad 全为零"


def test_transformer_block_residual_grad_flows_to_input() -> None:
    """TransformerBlock 残差路径梯度必须流回输入 x。

    残差结构 ``x + sublayer(x)`` 保证梯度至少通过加法支路流回 x。
    """
    _seed()
    tb = TransformerBlock(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = tb(x)
    loss = (out * out).sum()
    loss.backward()
    assert x.grad is not None, "残差路径未连通，x.grad 为 None"
    assert np.any(x.grad != 0.0), "残差路径梯度全为零"


# ---------------------------------------------------------------------------
# 4. 数值梯度验证（R02 学术诚信：反向梯度必须与有限差分一致）
# ---------------------------------------------------------------------------
def _mha_loss_at(mha: MultiHeadAttention, x_np: np.ndarray) -> float:
    """在当前参数下计算 loss = sum(out^2)，不污染计算图。"""
    x = Tensor(x_np, requires_grad=False)
    out = mha(x)
    return float((out.data * out.data).sum())


def test_mha_wq_grad_matches_numerical() -> None:
    """w_q.weight 解析梯度与数值有限差分一致（eps=1e-6, atol=1e-4）。

    数学（Vaswani et al. 2017 + Goodfellow 2016 §6.2.2 softmax 反向）:
        scores = Q·K^T / sqrt(d_k)
        attn = softmax(scores)
        out = attn · V
    """
    _seed()
    embed_dim, num_heads, seq_len = 6, 2, 3
    mha = MultiHeadAttention(embed_dim=embed_dim, num_heads=num_heads)
    x_np = np.random.randn(seq_len, embed_dim)

    # 解析梯度
    x = Tensor(x_np, requires_grad=True)
    out = mha(x)
    loss = (out * out).sum()
    loss.backward()
    assert mha.w_q.weight.grad is not None

    # 数值梯度（中心差分）
    eps = 1e-6
    w = mha.w_q.weight.data
    grad_num = np.zeros_like(w)
    for i in range(w.shape[0]):
        for j in range(w.shape[1]):
            orig = w[i, j]
            w[i, j] = orig + eps
            l_plus = _mha_loss_at(mha, x_np)
            w[i, j] = orig - eps
            l_minus = _mha_loss_at(mha, x_np)
            w[i, j] = orig  # 还原
            grad_num[i, j] = (l_plus - l_minus) / (2 * eps)

    # 相对误差容忍（数值差分本身有 1e-6 级误差）
    assert np.allclose(
        mha.w_q.weight.grad, grad_num, atol=1e-4, rtol=1e-3
    ), f"w_q 解析梯度与数值梯度不一致: max|Δ|={np.max(np.abs(mha.w_q.weight.grad - grad_num)):.2e}"


def test_multi_head_op_grad_matches_numerical() -> None:
    """``_multi_head_attention_op`` 反向梯度与数值有限差分一致。

    直接验证自定义可微 op（不经过 Linear 投影），确保 softmax/QK^T/V
    反向公式正确（R02: 公式可溯源）。
    """
    _seed()
    seq_len, embed_dim, num_heads = 4, 6, 2
    head_dim = embed_dim // num_heads
    q_np = np.random.randn(seq_len, embed_dim)
    k_np = np.random.randn(seq_len, embed_dim)
    v_np = np.random.randn(seq_len, embed_dim)

    # 解析梯度
    q = Tensor(q_np, requires_grad=True)
    k = Tensor(k_np, requires_grad=True)
    v = Tensor(v_np, requires_grad=True)
    out = _multi_head_attention_op(q, k, v, num_heads, head_dim, embed_dim)
    loss = (out * out).sum()
    loss.backward()
    assert q.grad is not None and k.grad is not None and v.grad is not None

    # 数值梯度（仅验证 q；k/v 同理）
    eps = 1e-6

    def loss_at(qq_np, kk_np, vv_np) -> float:
        o = _multi_head_attention_op(
            Tensor(qq_np), Tensor(kk_np), Tensor(vv_np),
            num_heads, head_dim, embed_dim,
        )
        return float((o.data * o.data).sum())

    grad_q_num = np.zeros_like(q_np)
    for i in range(seq_len):
        for j in range(embed_dim):
            orig = q_np[i, j]
            q_np[i, j] = orig + eps
            l_p = loss_at(q_np, k_np, v_np)
            q_np[i, j] = orig - eps
            l_m = loss_at(q_np, k_np, v_np)
            q_np[i, j] = orig
            grad_q_num[i, j] = (l_p - l_m) / (2 * eps)

    assert np.allclose(
        q.grad, grad_q_num, atol=1e-4, rtol=1e-3
    ), f"q 解析梯度与数值梯度不一致: max|Δ|={np.max(np.abs(q.grad - grad_q_num)):.2e}"


# ---------------------------------------------------------------------------
# 5. 形状/可配置性
# ---------------------------------------------------------------------------
def test_mha_embed_dim_not_divisible_raises() -> None:
    """embed_dim 不能被 num_heads 整除时必须 raise（R03: 禁止静默兜底）。"""
    with pytest.raises(ValueError):
        MultiHeadAttention(embed_dim=7, num_heads=2)


def test_mha_preserves_seq_len() -> None:
    """MHA 输出 seq_len 必须与输入一致。"""
    _seed()
    mha = MultiHeadAttention(embed_dim=8, num_heads=4)
    for seq_len in [1, 5, 16]:
        x = Tensor(np.random.randn(seq_len, 8), requires_grad=True)
        out = mha(x)
        assert out.shape == (seq_len, 8)
