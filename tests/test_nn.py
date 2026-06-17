"""纯 NumPy 神经网络库（torch 复刻）测试（Task 10/13）。

验证 ``polaris.nn`` 与 torch 行为一致：
- Linear 前向 ``y = x @ W^T + b``
- 自动微分梯度正确
- Adam 优化器收敛
"""

from __future__ import annotations

import numpy as np
import pytest

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
