"""polaris-route 子模块测试。

测试覆盖:
- test_route_mzi: 5 器件 5 连接 MZI + analytical 布局 + route_circuit，
  验证 n_paths=5, total_loss_db>0, router_type="curvy"
- test_compute_path_loss: 验证路径损耗计算（传播 + 弯曲）
- test_route_empty: 无连接的电路返回空 paths
- test_route_invalid_mode: 非法 mode 应 raise RuntimeError（R03 禁止 fall-back）
- test_route_missing_port: 端口缺失应 raise RuntimeError（R03 禁止 fall-back）
- test_route_device_insertion_loss: 回归测试-路径损耗含 dev2 插入损耗,
  total 含所有器件去重(含起始器件 gc1)（R05 Bug 修复）
- test_route_negative_insertion_loss: 负 insertion_loss_db 应 raise（R03）

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
_PLACE_SRC = str(Path(__file__).resolve().parents[2] / "place" / "src")
for _p in (_SRC, _CORE_SRC, _PLACE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_route  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_place import place_circuit  # noqa: E402
from polaris_route import compute_path_loss, route_circuit  # noqa: E402


def _make_mzi_circuit() -> dict:
    """构造 5 器件 5 连接 MZI 电路（与验证脚本一致）。

    1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east"),
               ("out2", 20, 3.5, "east")],
    )
    wg1 = make_device(
        "wg1", "strip_waveguide", 100, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 100, 0.25, "east")],
    )
    wg2 = make_device(
        "wg2", "strip_waveguide", 120, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 120, 0.25, "east")],
    )
    mmi2 = make_device(
        "mmi2", "mmi_2x2", 20, 5,
        ports=[("in1", 0, 1.5, "west"), ("in2", 0, 3.5, "west"),
               ("out1", 20, 1.5, "east"), ("out2", 20, 3.5, "east")],
    )
    return make_circuit(
        "MZI",
        [gc, mmi, wg1, wg2, mmi2],
        [
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
        canvas_w=500,
        canvas_h=300,
    )


def test_route_mzi():
    """5 器件 MZI 布线: n_paths=5, total_loss_db>0, router_type="curvy"。

    验证:
    - 返回 dict 含全部必要字段
    - paths 数量 = 5（与连接数一致）
    - 每条 path 含 dev1/port1/dev2/port2/points/loss_db/n_bends/n_crossings
    - 每条 path 的 points 至少 2 个点（起止端口坐标）
    - 每条 path 的 loss_db >= 0
    - total_loss_db > 0（有路径就有传播损耗）
    - n_bends >= 0
    - n_crossings >= 0
    - router_type == "curvy"
    """
    circuit = _make_mzi_circuit()
    placement_result = place_circuit(circuit, mode="analytical")
    placements = placement_result["placements"]

    result = route_circuit(circuit, placements)

    # 必要字段
    for key in ("paths", "total_loss_db", "n_crossings", "n_bends", "router_type"):
        assert key in result, f"结果缺少字段: {key}"

    assert result["router_type"] == "curvy"

    paths = result["paths"]
    assert len(paths) == 5, f"应有 5 条路径，实际 {len(paths)}"

    for i, path in enumerate(paths):
        for field in ("dev1", "port1", "dev2", "port2",
                      "points", "loss_db", "n_bends", "n_crossings"):
            assert field in path, f"path[{i}] 缺少字段: {field}"
        points = path["points"]
        assert len(points) >= 2, \
            f"path[{i}] points 至少 2 个点，实际 {len(points)}"
        # 坐标在画布范围内（含容差，因为端口偏移可能略超画布）
        canvas_w = circuit["canvas_w"]
        canvas_h = circuit["canvas_h"]
        for pt in points:
            assert -50.0 <= pt[0] <= canvas_w + 50.0, \
                f"path[{i}] 点 x 越界: {pt}"
            assert -50.0 <= pt[1] <= canvas_h + 50.0, \
                f"path[{i}] 点 y 越界: {pt}"
        assert path["loss_db"] >= 0.0, \
            f"path[{i}] loss_db 应 >= 0，实际 {path['loss_db']}"
        assert path["n_bends"] >= 0, \
            f"path[{i}] n_bends 应 >= 0，实际 {path['n_bends']}"
        assert path["n_crossings"] >= 0, \
            f"path[{i}] n_crossings 应 >= 0，实际 {path['n_crossings']}"

    assert result["total_loss_db"] > 0.0, \
        f"total_loss_db 应 > 0，实际 {result['total_loss_db']}"
    assert result["n_bends"] >= 0
    assert result["n_crossings"] >= 0


def test_compute_path_loss():
    """验证路径损耗计算: 传播损耗 + 弯曲损耗。

    构造已知路径 [(0,0), (100,0), (100,50)]:
    - 路径长度 = 100 + 50 = 150 μm
    - 弯曲数 = 1（在 (100,0) 处方向从水平变垂直）
    - 传播损耗 = 3.0 * 150 / 1e4 = 0.045 dB
    - 弯曲损耗 = 1 * 0.05 = 0.05 dB
    - 总损耗 = 0.045 + 0.05 = 0.095 dB
    """
    points = [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0)]
    loss = compute_path_loss(points, loss_db_cm=3.0)
    expected = 3.0 * 150.0 / 1e4 + 1 * 0.05  # 0.045 + 0.05 = 0.095
    assert abs(loss - expected) < 1e-9, \
        f"loss 期望 {expected}，实际 {loss}"

    # 验证直线（0 弯曲）: 路径 [(0,0), (100,0)]
    straight = [(0.0, 0.0), (100.0, 0.0)]
    loss_straight = compute_path_loss(straight, loss_db_cm=3.0)
    expected_straight = 3.0 * 100.0 / 1e4  # 0.03 dB，无弯曲
    assert abs(loss_straight - expected_straight) < 1e-9, \
        f"直线 loss 期望 {expected_straight}，实际 {loss_straight}"

    # 验证自定义 loss_db_cm
    loss_custom = compute_path_loss(straight, loss_db_cm=2.0)
    expected_custom = 2.0 * 100.0 / 1e4  # 0.02 dB
    assert abs(loss_custom - expected_custom) < 1e-9, \
        f"自定义 loss_db_cm 期望 {expected_custom}，实际 {loss_custom}"


def test_compute_path_loss_empty():
    """空路径或单点路径损耗应为 0。"""
    assert compute_path_loss([]) == 0.0
    assert compute_path_loss([(5.0, 5.0)]) == 0.0


def test_compute_path_loss_negative_coeff():
    """负 loss_db_cm 应 raise RuntimeError（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError, match="loss_db_cm 不能为负"):
        compute_path_loss([(0.0, 0.0), (10.0, 0.0)], loss_db_cm=-1.0)


def test_route_empty():
    """无连接的电路返回空 paths，total_loss_db=0。

    验证:
    - paths == []
    - total_loss_db == 0.0
    - n_crossings == 0
    - n_bends == 0
    - router_type == "curvy"
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    circuit = make_circuit("Empty", [gc], [], canvas_w=500, canvas_h=300)
    placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}

    result = route_circuit(circuit, placements)

    assert result["paths"] == []
    assert result["total_loss_db"] == 0.0
    assert result["n_crossings"] == 0
    assert result["n_bends"] == 0
    assert result["router_type"] == "curvy"


def test_route_invalid_mode():
    """非法 mode 应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_mzi_circuit()
    placement_result = place_circuit(circuit, mode="analytical")
    placements = placement_result["placements"]

    with pytest.raises(RuntimeError, match="不支持的布线模式"):
        route_circuit(circuit, placements, mode="unknown_mode")


def test_route_missing_port():
    """端口缺失应 raise RuntimeError（R03 禁止 fall-back）。"""
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")],
    )
    # 引用 mmi1 的不存在的端口 "out2"
    circuit = make_circuit(
        "BadLink", [gc, mmi],
        [("gc1", "out", "mmi1", "out2")],
        canvas_w=500, canvas_h=300,
    )
    placements = {
        "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
    }
    with pytest.raises(RuntimeError, match="未找到端口"):
        route_circuit(circuit, placements)


def test_route_missing_placement():
    """连接引用的器件不在 placements 中应 raise RuntimeError（R03）。"""
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")],
    )
    circuit = make_circuit(
        "Link", [gc, mmi],
        [("gc1", "out", "mmi1", "in")],
        canvas_w=500, canvas_h=300,
    )
    # mmi1 不在 placements 中
    placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
    with pytest.raises(RuntimeError, match="不在 placements 中"):
        route_circuit(circuit, placements)


def test_route_path_topology():
    """验证路径拓扑: 同 y 直线，不同 y 为 step（4 点 2 弯）。

    构造两个器件端口在同一 y 坐标 → 直线（2 点 0 弯曲）；
    不同 y 坐标 → step S-bend（4 点 2 弯曲）。
    """
    # 同 y: 直线
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 20,
        ports=[("in", 0, 10, "west")],
    )
    circuit = make_circuit(
        "Straight", [gc, mmi],
        [("gc1", "out", "mmi1", "in")],
        canvas_w=500, canvas_h=300,
    )
    placements = {
        "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 20.0},
    }
    result = route_circuit(circuit, placements)
    assert len(result["paths"]) == 1
    path = result["paths"][0]
    # 同 y: 直线，2 点，0 弯曲
    assert len(path["points"]) == 2, \
        f"同 y 应为直线（2 点），实际 {len(path['points'])} 点"
    assert path["n_bends"] == 0, \
        f"同 y 直线应 0 弯曲，实际 {path['n_bends']}"

    # 不同 y: step S-bend
    placements2 = {
        "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 30.0, "w": 20.0, "h": 20.0},
    }
    # 重新构造电路用 mmi1 端口在 y=10 处（相对器件）
    circuit2 = make_circuit(
        "Step", [gc, mmi],
        [("gc1", "out", "mmi1", "in")],
        canvas_w=500, canvas_h=300,
    )
    result2 = route_circuit(circuit2, placements2)
    path2 = result2["paths"][0]
    # 不同 y: step S-bend，4 点，2 弯曲
    assert len(path2["points"]) == 4, \
        f"不同 y 应为 step（4 点），实际 {len(path2['points'])} 点"
    assert path2["n_bends"] == 2, \
        f"不同 y step 应 2 弯曲，实际 {path2['n_bends']}"


def test_route_device_insertion_loss():
    """回归测试: 路径损耗含 dev2 插入损耗, total 含所有器件去重(R05)。

    构造 gc1(insertion_loss=1.9) → mmi1(insertion_loss=0.4) 单连接电路:
    - gc1 布局 (0,0), 端口 out 绝对坐标 (20, 10)
    - mmi1 布局 (100,0), 端口 in 绝对坐标 (100, 2.5)
    - 路径 (20,10)→(100,2.5), step 拓扑 2 弯曲, 长度 87.5μm
    - 波导损耗 = 传播(3.0*87.5/1e4=0.02625) + 弯曲(2*0.05=0.1) = 0.12625
    - 路径级 loss_db = 波导损耗 + dev2(mmi1)插入损耗(0.4) = 0.52625
    - total = 波导损耗 + 所有器件去重(gc1=1.9 + mmi1=0.4) = 2.42625

    验证 total > 2.3 (仅器件插入损耗), 且 total 含起始器件 gc1(1.9)。

    来源（R02 学术诚信）:
    - SiEPIC EBeam PDK GC 1.9dB / MMI1x2 0.4dB
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg 2015 §3.3 光子链路功率预算
      https://www.cambridge.org/core/books/silicon-photonics-design/
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("out", 20, 10, "east")],
        params={"insertion_loss_db": 1.9},
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west")],
        params={"insertion_loss_db": 0.4},
    )
    circuit = make_circuit(
        "InsertionLoss", [gc, mmi],
        [("gc1", "out", "mmi1", "in")],
        canvas_w=500, canvas_h=300,
    )
    placements = {
        "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
    }
    result = route_circuit(circuit, placements)

    assert len(result["paths"]) == 1
    path = result["paths"][0]
    # 波导损耗: 传播(3.0*87.5/1e4=0.02625) + 弯曲(2*0.05=0.1) = 0.12625
    expected_waveguide = 3.0 * 87.5 / 1e4 + 2 * 0.05
    # 路径级 loss_db = 波导损耗 + dev2(mmi1)插入损耗(0.4)
    expected_path = expected_waveguide + 0.4
    assert abs(path["loss_db"] - expected_path) < 1e-9, \
        f"路径 loss_db 期望 {expected_path}，实际 {path['loss_db']}"

    # total = 波导损耗 + 所有器件去重(gc1=1.9 + mmi1=0.4)
    expected_total = expected_waveguide + 1.9 + 0.4
    assert abs(result["total_loss_db"] - expected_total) < 1e-9, \
        f"total_loss_db 期望 {expected_total}，实际 {result['total_loss_db']}"

    # total 必须包含起始器件 gc1(1.9), 故 > 2.3(仅器件插入损耗)
    assert result["total_loss_db"] > 2.3, \
        f"total_loss_db 应含所有器件插入损耗(>2.3)，实际 {result['total_loss_db']}"


def test_route_negative_insertion_loss():
    """负 insertion_loss_db 应 raise RuntimeError（R03 禁止 fall-back）。"""
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("out", 20, 10, "east")],
        params={"insertion_loss_db": -0.5},
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west")],
    )
    circuit = make_circuit(
        "NegLoss", [gc, mmi],
        [("gc1", "out", "mmi1", "in")],
        canvas_w=500, canvas_h=300,
    )
    placements = {
        "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
    }
    with pytest.raises(RuntimeError, match="insertion_loss_db 不能为负"):
        route_circuit(circuit, placements)
