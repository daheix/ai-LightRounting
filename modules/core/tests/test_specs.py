"""polaris-core 核心数据结构测试。

测试覆盖:
- make_device: 创建 grating_coupler，验证 dict 字段
- make_circuit: 创建 MZI（5器件5连接），验证 n_devices=5 n_connections=5
- validate_circuit: 合法电路返回 True，缺字段 raise RuntimeError
- circuit_to_dict: dict 透传重建
- Tensor: 基本运算 + 自动微分

来源:
- pytest 文档: https://docs.pytest.org/
- NumPy 测试实践: https://numpy.org/doc/stable/reference/testing.html
- PyTorch autograd 梯度校验: https://pytorch.org/docs/stable/autograd.html
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from polaris_core import (
    Tensor,
    circuit_to_dict,
    make_circuit,
    make_device,
    validate_circuit,
)


def test_make_device():
    """创建 grating_coupler，验证 dict 字段完整且 JSON 可序列化。"""
    d = make_device(
        "gc1",
        "grating_coupler",
        20,
        20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        params={"insertion_loss_db": 1.9},
        process_node="220nm SOI",
    )
    assert d["name"] == "gc1"
    assert d["device_type"] == "grating_coupler"
    assert d["width_um"] == 20.0
    assert d["height_um"] == 20.0
    assert len(d["ports"]) == 2
    assert d["ports"][0] == ["in", 0, 10, "west"]
    assert d["ports"][1] == ["out", 20, 10, "east"]
    assert d["params"]["insertion_loss_db"] == 1.9
    assert d["process_node"] == "220nm SOI"
    # JSON 可序列化（稳定 API 原则）
    s = json.dumps(d)
    assert "gc1" in s


def test_make_circuit():
    """创建 MZI（5器件5连接），验证 n_devices=5 n_connections=5。"""
    # 5 个器件：2 grating_coupler + 2 y_branch + 1 waveguide
    gc1 = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    gc2 = make_device(
        "gc2", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    yb1 = make_device(
        "yb1", "y_branch", 10, 10,
        ports=[("in", 0, 5, "west"), ("out1", 10, 2, "east"), ("out2", 10, 8, "east")],
    )
    yb2 = make_device(
        "yb2", "y_branch", 10, 10,
        ports=[("in1", 0, 2, "west"), ("in2", 0, 8, "west"), ("out", 10, 5, "east")],
    )
    wg = make_device(
        "wg1", "waveguide", 50, 2,
        ports=[("in", 0, 1, "west"), ("out", 50, 1, "east")],
    )
    devices = [gc1, gc2, yb1, yb2, wg]
    # 5 条连接（MZI 拓扑：gc1→yb1 分束→wg1→yb2 合束→gc2，直臂 yb1→yb2）
    connections = [
        ("gc1", "out", "yb1", "in"),
        ("yb1", "out1", "wg1", "in"),
        ("wg1", "out", "yb2", "in1"),
        ("yb1", "out2", "yb2", "in2"),
        ("yb2", "out", "gc2", "in"),
    ]
    c = make_circuit(
        "MZI", devices, connections, canvas_w=500, canvas_h=300,
        process_node="220nm SOI", optical_wavelength_nm=1550.0,
    )
    assert c["name"] == "MZI"
    assert len(c["devices"]) == 5
    assert len(c["connections"]) == 5
    assert c["canvas_w"] == 500.0
    assert c["canvas_h"] == 300.0
    assert c["process_node"] == "220nm SOI"
    assert c["optical_wavelength_nm"] == 1550.0
    # JSON 可序列化
    json.dumps(c)
    # 该合法电路应通过 validate
    assert validate_circuit(c) is True


def test_validate_circuit_valid():
    """合法电路返回 True。"""
    d = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    c = make_circuit("MZI", [d], [], canvas_w=500, canvas_h=300)
    assert validate_circuit(c) is True


def test_validate_circuit_missing_field():
    """缺字段 raise RuntimeError（R03: 禁止 fall-back）。"""
    d = make_device("gc1", "grating_coupler", 20, 20)
    c = make_circuit("MZI", [d], [])
    # 删除必要字段 canvas_w
    broken = {k: v for k, v in c.items() if k != "canvas_w"}
    with pytest.raises(RuntimeError, match="canvas_w"):
        validate_circuit(broken)


def test_validate_circuit_bad_connection():
    """连接引用不存在的器件 raise RuntimeError。"""
    d = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("out", 20, 10, "east")],
    )
    c = make_circuit("MZI", [d], [("gc1", "out", "ghost", "in")])
    with pytest.raises(RuntimeError, match="ghost"):
        validate_circuit(c)


def test_validate_circuit_not_dict():
    """非 dict 输入 raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="dict"):
        validate_circuit("not a circuit")  # type: ignore[arg-type]


def test_circuit_to_dict_passthrough():
    """circuit_to_dict 对已是 dict 的输入原样重建返回。"""
    d = make_device("gc1", "grating_coupler", 20, 20)
    c = make_circuit("MZI", [d], [])
    c2 = circuit_to_dict(c)
    assert c2["name"] == "MZI"
    assert len(c2["devices"]) == 1
    assert c2["devices"][0]["name"] == "gc1"


def test_tensor_basic_ops():
    """Tensor 基本运算：加减乘与矩阵乘。"""
    a = Tensor([1.0, 2.0, 3.0])
    b = Tensor([4.0, 5.0, 6.0])
    c = a + b
    assert np.allclose(c.numpy(), [5.0, 7.0, 9.0])
    d = a * b
    assert np.allclose(d.numpy(), [4.0, 10.0, 18.0])

    # 矩阵乘法（1D @ 2D）
    W = Tensor([[1.0, 2.0], [3.0, 4.0]])
    x = Tensor([1.0, 1.0])
    y = x @ W
    assert np.allclose(y.numpy(), [4.0, 6.0])


def test_tensor_autograd():
    """自动微分：验证梯度计算正确。

    例: f = ((a * b) + a).sum()，df/da = b + 1，df/db = a
    """
    a = Tensor([1.0, 2.0, 3.0], requires_grad=True)
    b = Tensor([4.0, 5.0, 6.0], requires_grad=True)
    f = (a * b + a).sum()
    f.backward()
    # df/da = b + 1
    assert np.allclose(a.grad, [5.0, 6.0, 7.0])
    # df/db = a
    assert np.allclose(b.grad, [1.0, 2.0, 3.0])


def test_tensor_matmul_grad():
    """矩阵乘法自动微分。

    y = sum(x @ W)，dy/dx = W 行和，dy/dW = x 广播外积。
    """
    W = Tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
    x = Tensor([1.0, 1.0], requires_grad=True)
    y = (x @ W).sum()
    y.backward()
    # dy/dW = x_i（每行 = x）
    assert np.allclose(W.grad, [[1.0, 1.0], [1.0, 1.0]])
    # dy/dx = W 行和
    assert np.allclose(x.grad, [3.0, 7.0])
