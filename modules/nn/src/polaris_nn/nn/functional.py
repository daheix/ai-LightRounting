"""可微张量运算函数（复刻 ``torch.nn.functional`` 子集）。

从 v4 旧包 ``src/polaris/nn/functional.py`` 迁移，``Tensor`` 改为从
``polaris_core`` 导入。

含: ``cat`` / ``scatter_add`` / ``index_select`` / ``matmul_backward`` /
``leaky_relu`` / ``segment_softmax``，全部支持自动微分。

来源（R02 学术诚信）:
- PyTorch torch.cat: https://pytorch.org/docs/stable/generated/torch.cat.html
- PyTorch torch.scatter_add_: https://pytorch.org/docs/stable/generated/torch.Tensor.scatter_add_.html
- PyTorch torch.index_select: https://pytorch.org/docs/stable/generated/torch.index_select.html
- PyTorch torch.nn.functional.leaky_relu: https://pytorch.org/docs/stable/generated/torch.nn.functional.leaky_relu
- PyTorch torch.scatter_softmax: https://pytorch.org/docs/stable/generated/torch.scatter_softmax.html
- Maas et al., 2013, Rectifier Nonlinearities
  https://ai.stanford.edu/~amaas/papers/relu_hybrid_icml2013_final.pdf
- Veličković et al., ICLR 2018, GAT（LeakyReLU 负斜率 0.2）
  https://arxiv.org/abs/1710.10903
- NumPy dtype promotion: https://numpy.org/doc/stable/reference/arrays.promotion.html
"""

from __future__ import annotations

import numpy as np

from polaris_core import Tensor


def matmul_backward(left: Tensor, right: Tensor, g: np.ndarray) -> None:
    """``__matmul__`` 的反向传播（通过 reshape 统一处理 1D/2D 输入）。

    将 1D 输入 reshape 为 2D 后用标准矩阵梯度公式，避免多分支判断：
    - 1D @ 2D: ``x[k] @ W[k,m]`` → reshape x 为 ``[1,k]``
    - 2D @ 1D: ``X[n,k] @ v[k]`` → reshape v 为 ``[k,1]``

    Args:
        left: ``__matmul__`` 左操作数。
        right: ``__matmul__`` 右操作数。
        g: 上游梯度。
    """
    l2d = left.data.ndim == 1
    r2d = right.data.ndim == 1
    left_data = left.data.reshape(1, -1) if l2d else left.data
    right_data = right.data.reshape(-1, 1) if r2d else right.data
    g2d = g.reshape(1, -1) if g.ndim == 1 else g

    if left.requires_grad:
        left._ensure_grad()
        gl = g2d @ right_data.T
        left.grad = left.grad + (gl.flatten() if l2d else gl)
    if right.requires_grad:
        right._ensure_grad()
        gr = left_data.T @ g2d
        right.grad = right.grad + (gr.flatten() if r2d else gr)


def cat(tensors: list[Tensor], axis: int = 0) -> Tensor:
    """沿指定轴拼接张量（复刻 ``torch.cat``，支持自动微分）。

    前向：``out = np.concatenate([t.data for t in tensors], axis)``
    反向：将上游梯度按各 tensor 在拼接轴上的大小切分回去。

    Args:
        tensors: 待拼接的 Tensor 列表（须同 shape 除拼接轴外）。
        axis: 拼接轴。

    Returns:
        拼接后的 Tensor（含计算图）。

    Raises:
        ValueError: tensors 列表为空。

    来源: PyTorch torch.cat
    https://pytorch.org/docs/stable/generated/torch.cat.html
    """
    if not tensors:
        raise ValueError("cat: tensors 列表不能为空")
    data = np.concatenate([t.data for t in tensors], axis=axis)
    rg = any(t.requires_grad for t in tensors)
    out = Tensor(data, rg, tuple(tensors))

    def _back(g):
        sizes = [t.data.shape[axis] for t in tensors]
        splits = np.split(g, np.cumsum(sizes)[:-1], axis=axis)
        for t, s in zip(tensors, splits, strict=True):
            if t.requires_grad:
                t._ensure_grad()
                t.grad = t.grad + s

    out._backward = _back
    return out


def scatter_add(src: Tensor, dsts: np.ndarray, n: int) -> Tensor:
    """散射累加（复刻 ``torch.scatter_add_``，支持自动微分）。

    前向：``out[dsts[i]] += src[i]``（沿第 0 轴散射累加）
    反向：``src.grad[i] += out.grad[dsts[i]]``（按 dsts 收集梯度）

    用于 GNN 消息传递中邻居特征聚合，使梯度能从聚合结果流回
    邻居线性变换的参数。

    统一使用 float64 dtype，确保数值精度一致性。

    Args:
        src: 源张量 ``[E, D]``（E 条边，D 维特征）。
        dsts: 目标节点索引 ``[E]``（取值范围 ``[0, n)``）。
        n: 输出第 0 维大小（节点数）。

    Returns:
        聚合后的张量 ``[n, D]``。

    来源: PyTorch torch.scatter_add_
    https://pytorch.org/docs/stable/generated/torch.Tensor.scatter_add_.html
    """
    d = src.data.shape[-1] if src.data.ndim > 1 else 1
    out_data = np.zeros((n, d), dtype=np.float64)
    np.add.at(out_data, dsts, src.data)
    out = Tensor(out_data, src.requires_grad, (src,))

    def _back(g):
        if src.requires_grad:
            src._ensure_grad()
            src.grad = src.grad + g[dsts]

    out._backward = _back
    return out


def index_select(src: Tensor, idx: np.ndarray) -> Tensor:
    """按索引选取行（复刻 ``torch.index_select``，支持自动微分）。

    前向：``out[i] = src[idx[i]]``（沿第 0 轴选取行）
    反向：``src.grad[idx[i]] += out.grad[i]``（散射梯度回原行）

    用于 GNN 消息传递中按边源节点选取特征，使梯度能流回源节点变换参数。

    统一使用 float64 dtype，确保数值精度一致性。

    Args:
        src: 源张量 ``[N, D]``。
        idx: 行索引 ``[E]``（取值范围 ``[0, N)``）。

    Returns:
        选取后的张量 ``[E, D]``。

    来源: PyTorch torch.index_select
    https://pytorch.org/docs/stable/generated/torch.index_select.html
    """
    out = Tensor(src.data[idx], src.requires_grad, (src,))

    def _back(g):
        if src.requires_grad:
            src._ensure_grad()
            grad = np.zeros_like(src.data, dtype=np.float64)
            np.add.at(grad, idx, g)
            src.grad = src.grad + grad

    out._backward = _back
    return out


def leaky_relu(x: Tensor, slope: float = 0.2) -> Tensor:
    """LeakyReLU 激活（复刻 ``torch.nn.functional.leaky_relu``，支持自动微分）。

    前向：``out = where(x > 0, x, slope * x)``
    反向：``g * where(x > 0, 1, slope)``

    用于 GAT 注意力分数的 LeakyReLU 激活（Veličković 2018 原文 §2.1）。

    Args:
        x: 输入 Tensor。
        slope: 负斜率（默认 0.2，GAT 原文值）。

    Returns:
        激活后的 Tensor（含计算图）。

    来源:
    - Maas et al., 2013, Rectifier Nonlinearities Improve Neural Network Acoustic Models
      https://ai.stanford.edu/~amaas/papers/relu_hybrid_icml2013_final.pdf
    - Veličković et al., ICLR 2018, GAT（LeakyReLU 负斜率 0.2）
      https://arxiv.org/abs/1710.10903
    """
    data = np.where(x.data > 0, x.data, slope * x.data)
    out = Tensor(data, x.requires_grad, (x,))

    def _back(g):
        if x.requires_grad:
            x._ensure_grad()
            x.grad = x.grad + g * np.where(x.data > 0, 1.0, slope)

    out._backward = _back
    return out


def segment_softmax(scores: Tensor, dsts: np.ndarray, n: int) -> Tensor:
    """按目标节点分组的 softmax（支持自动微分，用于 GAT 注意力归一化）。

    对每个目标节点 ``i``，对其所有入边 ``j``（``dsts[j] == i``）的分数做
    softmax 归一化。数学等价于 ``torch.scatter_softmax``。

    前向（数值稳定）::

        max_i = max_{j: dsts[j]==i} scores[j]               # 组内最大值
        exp_j = exp(scores[j] - max_{dsts[j]})               # 减最大值防溢出
        sum_i = sum_{j: dsts[j]==i} exp_j                    # 组内求和
        alpha_j = exp_j / sum_{dsts[j]}                      # 归一化

    反向（softmax 链式法则，按 dst 分组）::

        dL/dscores[j] = alpha_j * (dL/dalpha[j]
                                   - sum_{k: dsts[k]==dsts[j]} alpha[k] * dL/dalpha[k])

    Args:
        scores: 边注意力分数 ``[E]``（E 条边）。
        dsts: 目标节点索引 ``[E]``（取值范围 ``[0, n)``）。
        n: 节点数（输出第 0 维大小）。

    Returns:
        注意力权重 ``[E]``（每条边的归一化权重，按 dst 分组和为 1）。

    来源:
    - Veličković et al., ICLR 2018, GAT（按邻居 softmax 归一化）
      https://arxiv.org/abs/1710.10903
    - PyTorch torch.scatter_softmax（segment softmax 语义）
      https://pytorch.org/docs/stable/generated/torch.scatter_softmax.html
    """
    scores_data = scores.data.astype(np.float64, copy=False)
    max_per_dst = np.full(n, -np.inf, dtype=np.float64)
    np.maximum.at(max_per_dst, dsts, scores_data)
    shifted = scores_data - max_per_dst[dsts]
    exp_scores = np.exp(shifted)
    sum_per_dst = np.zeros(n, dtype=np.float64)
    np.add.at(sum_per_dst, dsts, exp_scores)
    sum_per_dst[sum_per_dst == 0.0] = 1.0  # 避免除零（孤立节点）
    alpha_data = exp_scores / sum_per_dst[dsts]

    out = Tensor(alpha_data, scores.requires_grad, (scores,))

    def _back(g):
        if scores.requires_grad:
            scores._ensure_grad()
            # softmax 反向：dL/ds_k = a_k * (g_k - sum_{j in group} a_j * g_j)
            weighted_g = alpha_data * g  # [E]
            sum_weighted_g = np.zeros(n, dtype=np.float64)
            np.add.at(sum_weighted_g, dsts, weighted_g)
            grad = alpha_data * (g - sum_weighted_g[dsts])
            scores.grad = scores.grad + grad

    out._backward = _back
    return out


__all__ = [
    "cat",
    "index_select",
    "leaky_relu",
    "matmul_backward",
    "scatter_add",
    "segment_softmax",
]
