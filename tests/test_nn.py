"""纯 NumPy 神经网络库（torch 复刻）测试（Task 10/13）。

验证 ``polaris.nn`` 与 torch 行为一致：
- Linear 前向 ``y = x @ W^T + b``
- 自动微分梯度正确
- Adam 优化器收敛
"""

from __future__ import annotations

import numpy as np

from polaris.nn import Adam, Linear, ReLU, Sequential, Tensor


def test_tensor_basic_ops():
    a = Tensor([1.0, 2.0, 3.0])
    b = Tensor([4.0, 5.0, 6.0])
    c = a + b
    assert np.allclose(c.data, [5.0, 7.0, 9.0])
    d = a * b
    assert np.allclose(d.data, [4.0, 10.0, 18.0])


def test_linear_forward_shape():
    layer = Linear(3, 4)
    x = Tensor(np.random.randn(5, 3))
    out = layer(x)
    assert out.shape == (5, 4)


def test_linear_forward_matches_torch_formula():
    """验证 y = x @ W^T + b（与 torch.nn.Linear 一致）。"""
    layer = Linear(2, 3)
    x = np.random.randn(4, 2)
    expected = x @ layer.weight.data.T + layer.bias.data
    out = layer(Tensor(x))
    assert np.allclose(out.data, expected)


def test_autograd_linear_gradient():
    """验证 Linear 权重梯度与数值梯度一致。"""
    layer = Linear(2, 1)
    x = np.random.randn(3, 2)
    y_target = np.array([[1.0], [2.0], [3.0]])
    out = layer(Tensor(x))
    loss = ((out - Tensor(y_target)) ** 2).mean()
    loss.backward()
    # 数值梯度
    eps = 1e-6
    w0 = layer.weight.data.copy()
    grad_num = np.zeros_like(w0)
    for i in range(w0.shape[0]):
        for j in range(w0.shape[1]):
            layer.weight.data = w0.copy()
            layer.weight.data[i, j] += eps
            l1 = ((layer(Tensor(x)).data - y_target) ** 2).mean()
            layer.weight.data[i, j] -= 2 * eps
            l2 = ((layer(Tensor(x)).data - y_target) ** 2).mean()
            grad_num[i, j] = (l1 - l2) / (2 * eps)
    layer.weight.data = w0
    assert np.allclose(layer.weight.grad, grad_num, atol=1e-4)


def test_relu_gradient():
    x = Tensor([-1.0, 0.0, 2.0], requires_grad=True)
    out = x.relu()
    out.backward(np.array([1.0, 1.0, 1.0]))
    assert np.allclose(x.grad, [0.0, 0.0, 1.0])


def test_tanh_gradient():
    x = Tensor([0.5], requires_grad=True)
    out = x.tanh()
    out.backward(np.array([1.0]))
    expected = 1 - np.tanh(0.5) ** 2
    assert np.allclose(x.grad, expected, atol=1e-6)


def test_adam_converges():
    """Adam 应能拟合简单线性回归。"""
    np.random.seed(42)
    W_true = np.array([[2.0, -1.0]])
    model = Sequential(Linear(2, 8), ReLU(), Linear(8, 1))
    opt = Adam(model.parameters(), lr=0.05)
    X = np.random.randn(64, 2)
    y = X @ W_true.T + 0.1
    for _ in range(300):
        opt.zero_grad()
        pred = model(Tensor(X))
        loss = ((pred - Tensor(y)) ** 2).mean()
        loss.backward()
        opt.step()
    assert loss.data < 0.5


def test_tensor_transpose():
    a = Tensor([[1.0, 2.0], [3.0, 4.0]])
    at = a.T
    assert at.shape == (2, 2)
    assert np.allclose(at.data, [[1.0, 3.0], [2.0, 4.0]])


def test_tensor_matmul():
    a = Tensor([[1.0, 2.0], [3.0, 4.0]])
    b = Tensor([[5.0, 6.0], [7.0, 8.0]])
    c = a @ b
    assert np.allclose(c.data, [[19.0, 22.0], [43.0, 50.0]])


def test_tensor_flatten():
    a = Tensor([[1.0, 2.0], [3.0, 4.0]])
    f = a.flatten()
    assert f.shape == (4,)


def test_module_parameters():
    model = Sequential(Linear(2, 3), ReLU(), Linear(3, 1))
    params = model.parameters()
    assert len(params) >= 4  # 2 weights + 2 biases


# ---------------------------------------------------------------------------
# P0-C 回归测试：attention.py 移除 .data 截断，实现可微多头注意力
# 修复前 bug: MultiHeadAttention.forward / TransformerBlock.forward
#   大量使用 .data 截断计算图，w_q/w_k/w_v 参数无法接收梯度
# 修复后: 自定义可微 _multi_head_attention_op，保留完整计算图
# 学术依据: Vaswani 2017 NeurIPS / Goodfellow 2016 §6.2.2 softmax 反向
# ---------------------------------------------------------------------------

import ast
import inspect
import textwrap

from polaris.nn.attention import MultiHeadAttention, TransformerBlock


class TestP0CAttentionDifferentiable:
    """P0-C 回归测试：多头注意力可微性验证。"""

    def test_mha_forward_shape(self) -> None:
        """MultiHeadAttention 前向应输出正确 shape。"""
        mha = MultiHeadAttention(embed_dim=8, num_heads=2)
        x = Tensor(np.random.randn(4, 8))
        out = mha(x)
        assert out.shape == (4, 8)

    def test_mha_backward_populates_w_qkv_grads(self) -> None:
        """backward 应填充 w_q/w_k/w_v 权重梯度（非 None）。

        修复前: .data 截断计算图，w_q.grad 永远为 None。
        """
        mha = MultiHeadAttention(embed_dim=8, num_heads=2)
        x = Tensor(np.random.randn(4, 8))
        out = mha(x)
        loss = out.sum()
        loss.backward()
        # w_q/w_k/w_v 权重梯度必须非 None（P0-C 核心：梯度能流回参数）
        assert mha.w_q.weight.grad is not None, "w_q.weight.grad 为 None（P0-C bug 复现）"
        assert mha.w_k.weight.grad is not None, "w_k.weight.grad 为 None（P0-C bug 复现）"
        assert mha.w_v.weight.grad is not None, "w_v.weight.grad 为 None（P0-C bug 复现）"
        assert mha.w_o.weight.grad is not None, "w_o.weight.grad 为 None"

    def test_mha_gradient_nonzero(self) -> None:
        """w_q 权重梯度应有非零值（不是全 0 的假梯度）。"""
        mha = MultiHeadAttention(embed_dim=8, num_heads=2)
        x = Tensor(np.random.randn(4, 8))
        out = mha(x)
        loss = out.sum()
        loss.backward()
        assert np.any(mha.w_q.weight.grad != 0.0), "w_q 梯度全 0，未真正传播"

    def test_mha_gradient_numerical_check(self) -> None:
        """解析梯度应与数值有限差分一致（atol=1e-4）。

        修复前: .data 截断，解析梯度全 0，与数值梯度严重不符。
        """
        np.random.seed(42)
        mha = MultiHeadAttention(embed_dim=4, num_heads=2)
        x_np = np.random.randn(3, 4)
        x = Tensor(x_np)

        # 前向 + 反向
        out = mha(x)
        loss = out.sum()
        loss.backward()
        analytic_grad = mha.w_q.weight.grad.copy()

        # 数值梯度（中心差分）
        eps = 1e-6
        w0 = mha.w_q.weight.data.copy()
        num_grad = np.zeros_like(w0)
        for i in range(w0.shape[0]):
            for j in range(w0.shape[1]):
                mha.w_q.weight.data = w0.copy()
                mha.w_q.weight.data[i, j] += eps
                l1 = mha(x).sum().data
                mha.w_q.weight.data[i, j] -= 2 * eps
                l2 = mha(x).sum().data
                num_grad[i, j] = (l1 - l2) / (2 * eps)
        mha.w_q.weight.data = w0
        assert np.allclose(analytic_grad, num_grad, atol=1e-4), (
            f"解析梯度与数值梯度不一致:\n analytic={analytic_grad}\n numeric={num_grad}"
        )

    def test_transformer_block_backward_all_params(self) -> None:
        """TransformerBlock backward 应填充所有子层参数梯度。

        修复前: 残差 Tensor(x.data + sublayer(x).data) 截断计算图。
        """
        block = TransformerBlock(embed_dim=8, num_heads=2)
        x = Tensor(np.random.randn(4, 8))
        out = block(x)
        loss = out.sum()
        loss.backward()
        # 所有子层参数梯度应非 None
        for name in ("w_q", "w_k", "w_v", "w_o"):
            w = getattr(block.attn, name)
            assert w.weight.grad is not None, f"attn.{name}.weight.grad 为 None"
        assert block.ff1.weight.grad is not None, "ff1.weight.grad 为 None"
        assert block.ff2.weight.grad is not None, "ff2.weight.grad 为 None"

    def test_no_data_in_forward_methods(self) -> None:
        """AST 检查: MultiHeadAttention.forward / TransformerBlock.forward
        不应包含 .data 属性访问（P0-C 根因）。

        修复前: forward 中大量使用 x.data / sublayer(x).data 截断计算图。
        """
        # 检查 MultiHeadAttention.forward
        src_mha = textwrap.dedent(inspect.getsource(MultiHeadAttention.forward))
        tree_mha = ast.parse(src_mha)
        data_accesses_mha = [
            n
            for n in ast.walk(tree_mha)
            if isinstance(n, ast.Attribute) and n.attr == "data"
        ]
        assert len(data_accesses_mha) == 0, (
            f"MultiHeadAttention.forward 仍含 .data 访问（P0-C bug）: "
            f"{len(data_accesses_mha)} 处"
        )
        # 检查 TransformerBlock.forward
        src_tb = textwrap.dedent(inspect.getsource(TransformerBlock.forward))
        tree_tb = ast.parse(src_tb)
        data_accesses_tb = [
            n
            for n in ast.walk(tree_tb)
            if isinstance(n, ast.Attribute) and n.attr == "data"
        ]
        assert len(data_accesses_tb) == 0, (
            f"TransformerBlock.forward 仍含 .data 访问（P0-C bug）: "
            f"{len(data_accesses_tb)} 处"
        )
