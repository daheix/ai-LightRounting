"""polaris-core 深度测试（DeviceSpec/CircuitSpec/Tensor/工厂/校验全覆盖）。

测试分层:
1. DeviceSpec dataclass: 默认值/完整构造/ports
2. CircuitSpec dataclass: 默认值/完整构造/benchmark_source/target_metric
3. BenchmarkSource/TargetMetric 枚举
4. make_device 工厂: 默认值/完整参数/ports 转 list/JSON 可序列化
5. make_circuit 工厂: 默认值/完整参数/接受 DeviceSpec 与 dict/JSON 可序列化
6. validate_circuit: 合法/非 dict/缺字段/类型不符/连接引用非法
7. circuit_to_dict: CircuitSpec→dict/dict 透传/非法类型 raise
8. Tensor: 构造/shape/T/加减乘/matmul/sum/mean/relu/tanh/log/exp/softmax/
   reshape/flatten/detach/numpy/backward 自动微分/requires_grad/pow/neg

R02 学术诚信: 所有断言基于 specs.py/tensor.py 源码公开契约。
R03 禁止 fall-back: validate 失败场景验证 raise RuntimeError。

来源（R02 学术诚信，均经 WebSearch 验证可访问）:
- pytest 文档: https://docs.pytest.org/
- NumPy 测试实践: https://numpy.org/doc/stable/reference/testing.html
- PyTorch autograd 梯度校验: https://pytorch.org/docs/stable/autograd.html
- PyTorch torch.Tensor: https://github.com/pytorch/pytorch
- Autograd 反向模式: https://en.wikipedia.org/wiki/Automatic_differentiation
- NumPy 广播规则: https://numpy.org/doc/stable/user/basics.broadcasting.html
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
- TILOS MacroPlacement benchmark:
  https://github.com/TILOS-AI-Institute/MacroPlacement
- Apollo PTC/oNoC benchmark: https://github.com/ASU-LOPE-Group/Apollo
- SiEPIC PDK 设计规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_core import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
    Tensor,
    circuit_to_dict,
    make_circuit,
    make_device,
    validate_circuit,
)


# ===========================================================================
# 1. DeviceSpec dataclass
# ===========================================================================
def test_device_spec_defaults():
    """DeviceSpec 默认值（width/height=10, ports=[], params={}, process_node=None）。"""
    d = DeviceSpec(name="d1", device_type="wg")
    assert d.name == "d1"
    assert d.device_type == "wg"
    assert d.width_um == 10.0
    assert d.height_um == 10.0
    assert d.ports == []
    assert d.params == {}
    assert d.process_node is None


def test_device_spec_full():
    """DeviceSpec 完整构造（含 ports/params/process_node）。"""
    d = DeviceSpec(
        name="gc1", device_type="grating_coupler",
        width_um=20.0, height_um=20.0,
        ports=[("in", 0.0, 10.0, "west")],
        params={"insertion_loss_db": 1.9},
        process_node="220nm SOI",
    )
    assert d.width_um == 20.0
    assert len(d.ports) == 1
    assert d.ports[0] == ("in", 0.0, 10.0, "west")
    assert d.params["insertion_loss_db"] == 1.9
    assert d.process_node == "220nm SOI"


# ===========================================================================
# 2. CircuitSpec dataclass
# ===========================================================================
def test_circuit_spec_defaults():
    """CircuitSpec 默认值（canvas 1000x1000, wavelength 1550, CUSTOM）。"""
    c = CircuitSpec(name="c1")
    assert c.name == "c1"
    assert c.devices == []
    assert c.connections == []
    assert c.canvas_w == 1000.0
    assert c.canvas_h == 1000.0
    assert c.benchmark_source == BenchmarkSource.CUSTOM
    assert c.optical_wavelength_nm == 1550.0
    assert c.target_metric == TargetMetric.ROUTING_SUCCESS_RATE
    assert c.target_value == 1.0


def test_circuit_spec_full():
    """CircuitSpec 完整构造（含 devices/benchmark_source/target_metric）。"""
    d = DeviceSpec(name="d1", device_type="wg")
    c = CircuitSpec(
        name="mzi", devices=[d], connections=[("d1", "in", "d1", "out")],
        canvas_w=500, canvas_h=300,
        benchmark_source=BenchmarkSource.APOLLO,
        process_node="220nm SOI",
        optical_wavelength_nm=1310.0,
        target_metric=TargetMetric.INSERTION_LOSS_DB,
        target_value=0.5,
    )
    assert len(c.devices) == 1
    assert c.benchmark_source == BenchmarkSource.APOLLO
    assert c.optical_wavelength_nm == 1310.0
    assert c.target_metric == TargetMetric.INSERTION_LOSS_DB
    assert c.target_value == 0.5


# ===========================================================================
# 3. BenchmarkSource / TargetMetric 枚举
# ===========================================================================
def test_benchmark_source_values():
    """BenchmarkSource 4 个枚举值。"""
    assert BenchmarkSource.TILOS.value == "tilos"
    assert BenchmarkSource.APOLLO.value == "apollo"
    assert BenchmarkSource.LIDAR.value == "lidar"
    assert BenchmarkSource.CUSTOM.value == "custom"
    assert len(list(BenchmarkSource)) == 4


def test_target_metric_values():
    """TargetMetric 4 个枚举值。"""
    assert TargetMetric.HPWL.value == "hpwl"
    assert TargetMetric.DRV.value == "drv"
    assert TargetMetric.ROUTING_SUCCESS_RATE.value == "routing_success_rate"
    assert TargetMetric.INSERTION_LOSS_DB.value == "insertion_loss_db"
    assert len(list(TargetMetric)) == 4


# ===========================================================================
# 4. make_device 工厂
# ===========================================================================
def test_make_device_defaults():
    """make_device 默认 width/height=10，ports/params 空。"""
    d = make_device("d1", "wg")
    assert d["name"] == "d1"
    assert d["device_type"] == "wg"
    assert d["width_um"] == 10.0
    assert d["height_um"] == 10.0
    assert d["ports"] == []
    assert d["params"] == {}
    assert d["process_node"] is None


def test_make_device_full():
    """make_device 完整参数（ports tuple → list）。"""
    d = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        params={"insertion_loss_db": 1.9},
        process_node="220nm SOI",
    )
    assert d["width_um"] == 20.0
    assert len(d["ports"]) == 2
    assert d["ports"][0] == ["in", 0, 10, "west"]
    assert d["ports"][1] == ["out", 20, 10, "east"]
    assert d["params"]["insertion_loss_db"] == 1.9
    assert d["process_node"] == "220nm SOI"


def test_make_device_ports_converted_to_list():
    """make_device ports 内部 tuple 转为 list（JSON 可序列化）。"""
    d = make_device("d", "wg", ports=[("in", 0.0, 0.0, "west")])
    assert isinstance(d["ports"][0], list)
    assert d["ports"][0] == ["in", 0.0, 0.0, "west"]


def test_make_device_json_serializable():
    """make_device 返回 dict 可 JSON 序列化。"""
    d = make_device("gc1", "gc", 20, 20,
                    ports=[("in", 0, 10, "west")],
                    params={"loss": 1.5})
    s = json.dumps(d)
    assert "gc1" in s


def test_make_device_params_copied():
    """make_device params 是副本（不共享可变引用）。"""
    src = {"k": 1}
    d = make_device("d", "wg", params=src)
    d["params"]["k"] = 999
    assert src["k"] == 1, "params 应为副本"


# ===========================================================================
# 5. make_circuit 工厂
# ===========================================================================
def test_make_circuit_defaults():
    """make_circuit 默认 canvas 1000x1000, wavelength 1550。"""
    d = make_device("d1", "wg")
    c = make_circuit("c1", [d], [])
    assert c["name"] == "c1"
    assert c["canvas_w"] == 1000.0
    assert c["canvas_h"] == 1000.0
    assert c["optical_wavelength_nm"] == 1550.0
    assert c["process_node"] is None


def test_make_circuit_full():
    """make_circuit 完整参数（含 process_node/wavelength）。"""
    d = make_device("d1", "wg")
    c = make_circuit("MZI", [d], [("d1", "in", "d1", "out")],
                     canvas_w=500, canvas_h=300,
                     process_node="220nm SOI",
                     optical_wavelength_nm=1310.0)
    assert c["canvas_w"] == 500.0
    assert c["canvas_h"] == 300.0
    assert c["process_node"] == "220nm SOI"
    assert c["optical_wavelength_nm"] == 1310.0


def test_make_circuit_accepts_device_spec():
    """make_circuit 接受 DeviceSpec 实例（_device_to_dict 处理）。"""
    d = DeviceSpec(name="d1", device_type="wg", width_um=5.0, height_um=1.0)
    c = make_circuit("c", [d], [])
    assert c["devices"][0]["name"] == "d1"
    assert c["devices"][0]["width_um"] == 5.0


def test_make_circuit_accepts_dict_device():
    """make_circuit 接受 dict 器件（_device_to_dict 重建）。"""
    d = {"name": "d1", "device_type": "wg", "width_um": 5.0, "height_um": 1.0}
    c = make_circuit("c", [d], [])
    assert c["devices"][0]["name"] == "d1"
    assert c["devices"][0]["width_um"] == 5.0


def test_make_circuit_connections_to_list():
    """make_circuit connections tuple → list（JSON 可序列化）。"""
    d = make_device("d1", "wg", ports=[("in", 0, 0, "w"), ("out", 1, 0, "e")])
    c = make_circuit("c", [d], [("d1", "in", "d1", "out")])
    assert isinstance(c["connections"][0], list)
    assert c["connections"][0] == ["d1", "in", "d1", "out"]


def test_make_circuit_json_serializable():
    """make_circuit 返回 dict 可 JSON 序列化。"""
    d = make_device("d1", "wg", ports=[("in", 0, 0, "w")])
    c = make_circuit("c", [d], [])
    s = json.dumps(c)
    assert "d1" in s


def test_make_circuit_mzi_topology():
    """make_circuit 构建 MZI（5器件5连接）拓扑。"""
    devices = [
        make_device(f"d{i}", "wg", 10, 2) for i in range(5)
    ]
    connections = [
        ("d0", "out", "d1", "in"),
        ("d1", "out1", "d2", "in"),
        ("d2", "out", "d3", "in1"),
        ("d1", "out2", "d3", "in2"),
        ("d3", "out", "d4", "in"),
    ]
    c = make_circuit("MZI", devices, connections)
    assert len(c["devices"]) == 5
    assert len(c["connections"]) == 5
    assert validate_circuit(c) is True


# ===========================================================================
# 6. validate_circuit
# ===========================================================================
def test_validate_circuit_valid():
    """合法电路返回 True。"""
    d = make_device("gc1", "gc", 20, 20,
                    ports=[("in", 0, 10, "west")])
    c = make_circuit("MZI", [d], [], canvas_w=500, canvas_h=300)
    assert validate_circuit(c) is True


def test_validate_circuit_not_dict():
    """非 dict 输入 raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="dict"):
        validate_circuit("not a circuit")  # type: ignore[arg-type]


def test_validate_circuit_missing_name():
    """缺 name 字段 raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    broken = {k: v for k, v in c.items() if k != "name"}
    with pytest.raises(RuntimeError):
        validate_circuit(broken)


def test_validate_circuit_missing_devices():
    """缺 devices 字段 raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    broken = {k: v for k, v in c.items() if k != "devices"}
    with pytest.raises(RuntimeError):
        validate_circuit(broken)


def test_validate_circuit_missing_canvas_w():
    """缺 canvas_w 字段 raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    broken = {k: v for k, v in c.items() if k != "canvas_w"}
    with pytest.raises(RuntimeError, match="canvas_w"):
        validate_circuit(broken)


def test_validate_circuit_name_not_str():
    """name 非 str raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["name"] = 123
    with pytest.raises(RuntimeError, match="name"):
        validate_circuit(c)


def test_validate_circuit_devices_not_list():
    """devices 非 list raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["devices"] = "not_list"
    with pytest.raises(RuntimeError, match="devices"):
        validate_circuit(c)


def test_validate_circuit_connections_not_list():
    """connections 非 list raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["connections"] = "not_list"
    with pytest.raises(RuntimeError, match="connections"):
        validate_circuit(c)


def test_validate_circuit_canvas_w_not_number():
    """canvas_w 非 number raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["canvas_w"] = "str"
    with pytest.raises(RuntimeError, match="canvas_w"):
        validate_circuit(c)


def test_validate_circuit_wavelength_not_number():
    """optical_wavelength_nm 非 number raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["optical_wavelength_nm"] = "str"
    with pytest.raises(RuntimeError, match="optical_wavelength_nm"):
        validate_circuit(c)


def test_validate_circuit_device_not_dict():
    """device 非 dict raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["devices"][0] = "not_dict"
    with pytest.raises(RuntimeError, match="devices"):
        validate_circuit(c)


def test_validate_circuit_device_missing_field():
    """device 缺 width_um raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    del c["devices"][0]["width_um"]
    with pytest.raises(RuntimeError, match="width_um"):
        validate_circuit(c)


def test_validate_circuit_device_name_not_str():
    """device.name 非 str raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["devices"][0]["name"] = 123
    with pytest.raises(RuntimeError, match="name"):
        validate_circuit(c)


def test_validate_circuit_device_ports_not_list():
    """device.ports 非 list raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["devices"][0]["ports"] = "not_list"
    with pytest.raises(RuntimeError, match="ports"):
        validate_circuit(c)


def test_validate_circuit_device_params_not_dict():
    """device.params 非 dict raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["devices"][0]["params"] = "not_dict"
    with pytest.raises(RuntimeError, match="params"):
        validate_circuit(c)


def test_validate_circuit_connection_wrong_length():
    """connection 长度≠4 raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["connections"] = [["d", "in", "d"]]  # 长度 3
    with pytest.raises(RuntimeError, match="connections"):
        validate_circuit(c)


def test_validate_circuit_connection_unknown_device():
    """connection 引用不存在的器件 raise RuntimeError。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    c["connections"] = [["d", "in", "ghost", "in"]]
    with pytest.raises(RuntimeError, match="ghost"):
        validate_circuit(c)


def test_validate_circuit_empty_devices_valid():
    """空 devices 列表 + 空 connections 合法（返回 True）。"""
    c = make_circuit("empty", [], [])
    assert validate_circuit(c) is True


# ===========================================================================
# 7. circuit_to_dict
# ===========================================================================
def test_circuit_to_dict_from_dict():
    """circuit_to_dict 对已是 dict 的输入原样重建返回。"""
    d = make_device("d1", "wg")
    c = make_circuit("c", [d], [])
    c2 = circuit_to_dict(c)
    assert c2["name"] == "c"
    assert len(c2["devices"]) == 1
    assert c2["devices"][0]["name"] == "d1"


def test_circuit_to_dict_from_circuit_spec():
    """circuit_to_dict 接受 CircuitSpec 实例。"""
    d = DeviceSpec(name="d1", device_type="wg", width_um=5.0, height_um=1.0)
    c = CircuitSpec(name="c1", devices=[d],
                    connections=[("d1", "in", "d1", "out")])
    result = circuit_to_dict(c)
    assert result["name"] == "c1"
    assert len(result["devices"]) == 1
    assert result["devices"][0]["name"] == "d1"
    assert result["canvas_w"] == 1000.0


def test_circuit_to_dict_invalid_type():
    """circuit_to_dict 非 dict/非 CircuitSpec raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="circuit"):
        circuit_to_dict("not a circuit")  # type: ignore[arg-type]


def test_circuit_to_dict_dict_missing_field():
    """circuit_to_dict dict 缺字段 raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        circuit_to_dict({"name": "c"})  # 缺 devices/connections/canvas_w/canvas_h


def test_circuit_to_dict_preserves_wavelength():
    """circuit_to_dict 保留 optical_wavelength_nm。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [], optical_wavelength_nm=1310.0)
    c2 = circuit_to_dict(c)
    assert c2["optical_wavelength_nm"] == 1310.0


def test_circuit_to_dict_default_wavelength():
    """circuit_to_dict 无 wavelength 字段时默认 1550。"""
    d = make_device("d", "wg")
    c = make_circuit("c", [d], [])
    del c["optical_wavelength_nm"]
    c2 = circuit_to_dict(c)
    assert c2["optical_wavelength_nm"] == 1550.0


# ===========================================================================
# 8. Tensor 构造与基本属性
# ===========================================================================
def test_tensor_from_list():
    """Tensor 从 list 构造，统一 float64。"""
    t = Tensor([1.0, 2.0, 3.0])
    assert t.data.dtype == np.float64
    assert t.shape == (3,)


def test_tensor_from_scalar():
    """Tensor 从标量构造（0-d 数组）。"""
    t = Tensor(5.0)
    assert t.shape == ()
    assert t.data == 5.0


def test_tensor_from_numpy():
    """Tensor 从 numpy 数组构造。"""
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    t = Tensor(arr)
    assert t.shape == (2, 2)


def test_tensor_dtype_converted_to_float64():
    """Tensor int 数据转为 float64。"""
    t = Tensor([1, 2, 3])
    assert t.data.dtype == np.float64


def test_tensor_shape_property():
    """Tensor.shape 属性。"""
    t = Tensor([[1, 2], [3, 4], [5, 6]])
    assert t.shape == (3, 2)


def test_tensor_T_property():
    """Tensor.T 转置。"""
    t = Tensor([[1.0, 2.0, 3.0]])
    assert t.T.shape == (3, 1)


def test_tensor_numpy_method():
    """Tensor.numpy() 返回内部 ndarray。"""
    t = Tensor([1.0, 2.0])
    arr = t.numpy()
    assert isinstance(arr, np.ndarray)
    assert np.allclose(arr, [1.0, 2.0])


# ===========================================================================
# 9. Tensor 算术运算
# ===========================================================================
def test_tensor_add():
    """Tensor 加法。"""
    a = Tensor([1.0, 2.0, 3.0])
    b = Tensor([4.0, 5.0, 6.0])
    c = a + b
    assert np.allclose(c.numpy(), [5.0, 7.0, 9.0])


def test_tensor_sub():
    """Tensor 减法。"""
    a = Tensor([4.0, 5.0, 6.0])
    b = Tensor([1.0, 2.0, 3.0])
    c = a - b
    assert np.allclose(c.numpy(), [3.0, 3.0, 3.0])


def test_tensor_mul():
    """Tensor 逐元素乘法。"""
    a = Tensor([1.0, 2.0, 3.0])
    b = Tensor([4.0, 5.0, 6.0])
    c = a * b
    assert np.allclose(c.numpy(), [4.0, 10.0, 18.0])


def test_tensor_scalar_mul():
    """Tensor 与标量乘法（自动包装）。"""
    a = Tensor([1.0, 2.0, 3.0])
    c = a * 2.0
    assert np.allclose(c.numpy(), [2.0, 4.0, 6.0])


def test_tensor_neg():
    """Tensor 取负。"""
    a = Tensor([1.0, -2.0, 3.0])
    assert np.allclose((-a).numpy(), [-1.0, 2.0, -3.0])


def test_tensor_pow():
    """Tensor 幂运算。"""
    a = Tensor([2.0, 3.0])
    c = a ** 2
    assert np.allclose(c.numpy(), [4.0, 9.0])


def test_tensor_matmul_1d_2d():
    """Tensor 矩阵乘法（1D @ 2D）。"""
    W = Tensor([[1.0, 2.0], [3.0, 4.0]])
    x = Tensor([1.0, 1.0])
    y = x @ W
    assert np.allclose(y.numpy(), [4.0, 6.0])


def test_tensor_matmul_2d_2d():
    """Tensor 矩阵乘法（2D @ 2D）。"""
    A = Tensor([[1.0, 2.0], [3.0, 4.0]])
    B = Tensor([[1.0, 0.0], [0.0, 1.0]])
    C = A @ B
    assert np.allclose(C.numpy(), A.numpy())


def test_tensor_matmul_method():
    """Tensor.matmul 方法等价于 @。"""
    A = Tensor([[1.0, 2.0], [3.0, 4.0]])
    x = Tensor([1.0, 1.0])
    y1 = x @ A
    y2 = x.matmul(A)
    assert np.allclose(y1.numpy(), y2.numpy())


# ===========================================================================
# 10. Tensor 数学函数
# ===========================================================================
def test_tensor_sum():
    """Tensor.sum()。"""
    t = Tensor([1.0, 2.0, 3.0])
    s = t.sum()
    assert np.allclose(s.numpy(), 6.0)


def test_tensor_mean():
    """Tensor.mean()。"""
    t = Tensor([2.0, 4.0, 6.0])
    m = t.mean()
    assert np.allclose(m.numpy(), 4.0)


def test_tensor_relu():
    """Tensor.relu()（负数置零）。"""
    t = Tensor([-1.0, 2.0, -3.0, 4.0])
    r = t.relu()
    assert np.allclose(r.numpy(), [0.0, 2.0, 0.0, 4.0])


def test_tensor_tanh():
    """Tensor.tanh()。"""
    t = Tensor([0.0])
    assert np.allclose(t.tanh().numpy(), [0.0])


def test_tensor_exp():
    """Tensor.exp()。"""
    t = Tensor([0.0])
    assert np.allclose(t.exp().numpy(), [1.0])


def test_tensor_log():
    """Tensor.log()（含 1e-12 偏移防 log(0)）。"""
    t = Tensor([1.0])
    assert np.allclose(t.log().numpy(), [0.0], atol=1e-6)


def test_tensor_softmax_sums_to_one():
    """Tensor.softmax() 输出和为 1。"""
    t = Tensor([1.0, 2.0, 3.0])
    sm = t.softmax()
    assert np.allclose(sm.numpy().sum(), 1.0)
    assert np.all(sm.numpy() > 0)


def test_tensor_reshape():
    """Tensor.reshape()。"""
    t = Tensor([1.0, 2.0, 3.0, 4.0])
    r = t.reshape(2, 2)
    assert r.shape == (2, 2)


def test_tensor_flatten():
    """Tensor.flatten()。"""
    t = Tensor([[1.0, 2.0], [3.0, 4.0]])
    f = t.flatten()
    assert f.shape == (4,)


def test_tensor_detach():
    """Tensor.detach() 返回 requires_grad=False 的副本。"""
    t = Tensor([1.0, 2.0], requires_grad=True)
    d = t.detach()
    assert d.requires_grad is False
    assert np.allclose(d.numpy(), t.numpy())
    # 修改副本不影响原数据
    d.data[0] = 999.0
    assert t.data[0] == 1.0


# ===========================================================================
# 11. Tensor 自动微分
# ===========================================================================
def test_tensor_autograd_simple():
    """自动微分: f=(a*b+a).sum(), df/da=b+1, df/db=a。"""
    a = Tensor([1.0, 2.0, 3.0], requires_grad=True)
    b = Tensor([4.0, 5.0, 6.0], requires_grad=True)
    f = (a * b + a).sum()
    f.backward()
    assert np.allclose(a.grad, [5.0, 6.0, 7.0])
    assert np.allclose(b.grad, [1.0, 2.0, 3.0])


def test_tensor_autograd_matmul():
    """矩阵乘法自动微分: y=sum(x@W), dy/dW=x_i, dy/dx=W 行和。"""
    W = Tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
    x = Tensor([1.0, 1.0], requires_grad=True)
    y = (x @ W).sum()
    y.backward()
    assert np.allclose(W.grad, [[1.0, 1.0], [1.0, 1.0]])
    assert np.allclose(x.grad, [3.0, 7.0])


def test_tensor_autograd_relu():
    """ReLU 自动微分: 负数梯度为 0。"""
    x = Tensor([-1.0, 2.0, -3.0], requires_grad=True)
    y = x.relu().sum()
    y.backward()
    assert np.allclose(x.grad, [0.0, 1.0, 0.0])


def test_tensor_autograd_pow():
    """幂运算自动微分: d(x^2)/dx=2x。"""
    x = Tensor([1.0, 2.0, 3.0], requires_grad=True)
    y = (x ** 2).sum()
    y.backward()
    assert np.allclose(x.grad, [2.0, 4.0, 6.0])


def test_tensor_no_grad_no_backward():
    """requires_grad=False 的 Tensor 不参与反向传播。"""
    a = Tensor([1.0, 2.0], requires_grad=False)
    b = Tensor([3.0, 4.0], requires_grad=True)
    f = (a * b).sum()
    f.backward()
    assert a.grad is None
    assert np.allclose(b.grad, [1.0, 2.0])


def test_tensor_zero_grad():
    """zero_grad 清空梯度。"""
    x = Tensor([1.0, 2.0], requires_grad=True)
    y = (x * 2).sum()
    y.backward()
    assert x.grad is not None
    x.zero_grad()
    assert x.grad is None


def test_tensor_backward_default_grad():
    """backward() 无参数时默认 ones_like（标量输出）。"""
    x = Tensor([1.0, 2.0, 3.0], requires_grad=True)
    y = (x * 2).sum()
    y.backward()
    assert np.allclose(x.grad, [2.0, 2.0, 2.0])
