"""pyCopyTorch 与真实 torch 对比测试（规则 4.6）。

对比 src/polaris/nn/（pyCopyTorch 复刻）与 PyTorch 的数值一致性，
覆盖 Tensor 基本运算、Linear 前向、Adam 一步更新。

来源:
- PyTorch: https://pytorch.org/ (BSD-3-Clause)
- 复刻位置: src/polaris/nn/__init__.py
- 复刻入口: 3dtool/pycopy/pyCopyTorch/__init__.py
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from pycopy.pyCopyTorch import Adam, AdamConfig, Linear, Tensor  # noqa: E402


# ---------------------------------------------------------------------------
# Tensor 基本运算一致性
# ---------------------------------------------------------------------------
class TestTensorOps:
    """对比 pyCopyTorch Tensor 与 torch.Tensor 的基本运算。"""

    def test_add(self):
        # Arrange
        a_np = np.array([[1.0, 2.0], [3.0, 4.0]])
        b_np = np.array([[5.0, 6.0], [7.0, 8.0]])
        a_replica = Tensor(a_np)
        a_torch = torch.tensor(a_np, dtype=torch.float64)
        b_torch = torch.tensor(b_np, dtype=torch.float64)

        # Act
        out_replica = a_replica + b_np  # Tensor + ndarray
        out_torch = a_torch + b_torch

        # Assert
        np.testing.assert_allclose(out_replica.data, out_torch.numpy(), atol=1e-9)

    def test_mul(self):
        # Arrange
        a_np = np.array([[1.0, 2.0], [3.0, 4.0]])
        b_np = np.array([[2.0, 3.0], [4.0, 5.0]])
        a_replica = Tensor(a_np)
        a_torch = torch.tensor(a_np, dtype=torch.float64)
        b_torch = torch.tensor(b_np, dtype=torch.float64)

        # Act
        out_replica = a_replica * Tensor(b_np)
        out_torch = a_torch * b_torch

        # Assert
        np.testing.assert_allclose(out_replica.data, out_torch.numpy(), atol=1e-9)

    def test_matmul(self):
        # Arrange
        a_np = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])  # (2,3)
        b_np = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])  # (3,2)
        a_replica = Tensor(a_np)
        a_torch = torch.tensor(a_np, dtype=torch.float64)
        b_torch = torch.tensor(b_np, dtype=torch.float64)

        # Act
        out_replica = a_replica @ Tensor(b_np)
        out_torch = a_torch @ b_torch

        # Assert
        np.testing.assert_allclose(out_replica.data, out_torch.numpy(), atol=1e-9)


# ---------------------------------------------------------------------------
# Linear 层前向一致性
# ---------------------------------------------------------------------------
class TestLinearForward:
    """对比 pyCopyTorch Linear 与 torch.nn.Linear 的前向输出。"""

    def test_linear_forward_same_weights(self):
        # Arrange — 用相同权重确保前向输出一致
        in_features, out_features = 4, 3
        weight_np = np.random.randn(out_features, in_features)
        bias_np = np.random.randn(out_features)
        x_np = np.random.randn(2, in_features)

        # pyCopyTorch Linear
        layer_replica = Linear(in_features, out_features, bias=True, init="orthogonal")
        layer_replica.weight = Tensor(weight_np.copy(), requires_grad=True)
        layer_replica.bias = Tensor(bias_np.copy(), requires_grad=True)

        # torch.nn.Linear
        layer_torch = torch.nn.Linear(in_features, out_features, bias=True)
        layer_torch.weight.data = torch.tensor(weight_np, dtype=torch.float64)
        layer_torch.bias.data = torch.tensor(bias_np, dtype=torch.float64)
        layer_torch = layer_torch.double()

        x_torch = torch.tensor(x_np, dtype=torch.float64)

        # Act
        out_replica = layer_replica.forward(Tensor(x_np))
        out_torch = layer_torch(x_torch)

        # Assert
        np.testing.assert_allclose(out_replica.data, out_torch.detach().numpy(), atol=1e-9)


# ---------------------------------------------------------------------------
# Adam 优化器一步更新一致性
# ---------------------------------------------------------------------------
class TestAdamStep:
    """对比 pyCopyTorch Adam 与 torch.optim.Adam 的一步参数更新。"""

    def test_adam_one_step(self):
        # Arrange — 相同初始参数与梯度，对比一步更新后参数
        param_np = np.array([0.5, -0.3, 0.8])
        grad_np = np.array([0.1, -0.2, 0.05])

        # pyCopyTorch Adam
        p_replica = Tensor(param_np.copy(), requires_grad=True)
        p_replica.grad = grad_np.copy()
        opt_replica = Adam([p_replica], lr=1e-3, config=AdamConfig())

        # torch.optim.Adam
        p_torch = torch.tensor(param_np.copy(), dtype=torch.float64, requires_grad=True)
        p_torch.grad = torch.tensor(grad_np, dtype=torch.float64)
        opt_torch = torch.optim.Adam([p_torch], lr=1e-3)

        # Act
        opt_replica.step()
        opt_torch.step()

        # Assert
        np.testing.assert_allclose(p_replica.data, p_torch.detach().numpy(), atol=1e-9)
