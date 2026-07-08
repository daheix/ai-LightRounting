"""扩展测试（从 test_route.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_route.py。
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
from polaris_route import (  # noqa: E402
    BEND_LOSS_DB,
    CROSSING_LOSS_DB,
    PROPAGATION_LOSS_DB_CM,
    CurveType,
    CurvyRouteConfig,
    CurvyRouter,
    compute_path_loss,
    count_bends,
    count_crossings,
    generate_arc_bend,
    generate_euler_bend,
    path_length,
    route_circuit,
    s_bend_bezier,
)


# ---------------------------------------------------------------------------
# 辅助：构造测试电路
# ---------------------------------------------------------------------------


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


# ============================================================
# 1. TestRouteConstants — 常量溯源（R02 学术诚信）
# ============================================================


class TestRouteCircuitEndToEnd:
    """route_circuit 端到端布线与校验（含原 smoke test 回归）。"""

    def test_route_mzi(self):
        """5 器件 MZI 布线: n_paths=5, total_loss_db>0, router_type="curvy"。

        回归测试: 保留原 v5.0 smoke test 行为。
        """
        circuit = _make_mzi_circuit()
        placement_result = place_circuit(circuit, mode="analytical")
        placements = placement_result["placements"]

        result = route_circuit(circuit, placements)

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
            assert path["loss_db"] >= 0.0
            assert path["n_bends"] >= 0
            assert path["n_crossings"] >= 0

        assert result["total_loss_db"] > 0.0
        assert result["n_bends"] >= 0
        assert result["n_crossings"] >= 0

    def test_route_path_count_matches_connections(self):
        """路径数 = 连接数（端到端一致性）。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        result = route_circuit(circuit, placements)
        assert len(result["paths"]) == len(circuit["connections"])

    def test_route_empty(self):
        """无连接的电路返回空 paths，total_loss_db=0。"""
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

    def test_route_invalid_mode(self):
        """非法 mode 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        with pytest.raises(RuntimeError, match="不支持的布线模式"):
            route_circuit(circuit, placements, mode="unknown_mode")

    def test_route_missing_port(self):
        """端口缺失应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")],
        )
        circuit = make_circuit(
            "BadLink", [gc, mmi],
            [("gc1", "out", "mmi1", "out2")],  # mmi1 无 out2 端口
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="未找到端口"):
            route_circuit(circuit, placements)

    def test_route_missing_placement(self):
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
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="不在 placements 中"):
            route_circuit(circuit, placements)

    def test_route_negative_insertion_loss(self):
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

    def test_route_path_topology_aligned(self):
        """同 y 端口: 直线 2 点 0 弯曲。"""
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
        path = result["paths"][0]
        assert len(path["points"]) == 2, \
            f"同 y 应为直线（2 点），实际 {len(path['points'])} 点"
        assert path["n_bends"] == 0

    def test_route_path_topology_step(self):
        """不同 y 端口: step S-bend 4 点 2 弯曲。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 20,
            ports=[("in", 0, 10, "west")],
        )
        circuit = make_circuit(
            "Step", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 30.0, "w": 20.0, "h": 20.0},
        }
        result = route_circuit(circuit, placements)
        path = result["paths"][0]
        assert len(path["points"]) == 4, \
            f"不同 y 应为 step（4 点），实际 {len(path['points'])} 点"
        assert path["n_bends"] == 2

    def test_route_device_insertion_loss(self):
        """回归测试: 路径损耗含 dev2 插入损耗, total 含所有器件去重(R05)。

        构造 gc1(insertion_loss=1.9) → mmi1(insertion_loss=0.4) 单连接电路:
        - 路径 (20,10)→(100,2.5), step 拓扑 2 弯曲, 长度 87.5μm
        - 波导损耗 = 传播(3.0*87.5/1e4=0.02625) + 弯曲(2*0.05=0.1) = 0.12625
        - 路径级 loss_db = 波导损耗 + dev2(mmi1)插入损耗(0.4) = 0.52625
        - total = 波导损耗 + 所有器件去重(gc1=1.9 + mmi1=0.4) = 2.42625

        来源: SiEPIC EBeam PDK GC 1.9dB / MMI1x2 0.4dB
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
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

        path = result["paths"][0]
        expected_waveguide = 3.0 * 87.5 / 1e4 + 2 * 0.05  # 0.12625
        expected_path = expected_waveguide + 0.4  # 0.52625
        assert abs(path["loss_db"] - expected_path) < 1e-9

        expected_total = expected_waveguide + 1.9 + 0.4  # 2.42625
        assert abs(result["total_loss_db"] - expected_total) < 1e-9
        # total 必须包含起始器件 gc1(1.9), 故 > 2.3
        assert result["total_loss_db"] > 2.3

    def test_route_invalid_circuit_dict(self):
        """circuit 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
            route_circuit("not a dict", placements)
        with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
            route_circuit(None, placements)

    def test_route_invalid_placements(self):
        """placements 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = _make_mzi_circuit()
        with pytest.raises(RuntimeError, match="placements 必须是 dict"):
            route_circuit(circuit, "not a dict")
        with pytest.raises(RuntimeError, match="placements 必须是 dict"):
            route_circuit(circuit, None)

    def test_route_zero_canvas_raises(self):
        """画布尺寸为 0 应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        circuit = make_circuit("Zero", [gc], [], canvas_w=0, canvas_h=300)
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="画布尺寸必须为正"):
            route_circuit(circuit, placements)

    def test_route_duplicate_device_name(self):
        """器件名重复应 raise RuntimeError（R03 禁止 fall-back）。"""
        # 直接构造 circuit dict 绕过 make_circuit 校验
        circuit = {
            "name": "Dup",
            "devices": [
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("out", 20, 10, "east")], "params": {}},
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("in", 0, 10, "west")], "params": {}},
            ],
            "connections": [],
            "canvas_w": 500,
            "canvas_h": 300,
        }
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="器件名重复"):
            route_circuit(circuit, placements)

    def test_route_invalid_connection_format(self):
        """connection 非长度 4 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = {
            "name": "BadConn",
            "devices": [
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("out", 20, 10, "east")], "params": {}},
            ],
            "connections": [["gc1", "out"]],  # 长度 2，非法
            "canvas_w": 500,
            "canvas_h": 300,
        }
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="connection 必须是长度 4"):
            route_circuit(circuit, placements)

    def test_route_unknown_device_in_connection(self):
        """连接引用不存在的器件应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        circuit = make_circuit(
            "Unknown", [gc],
            [("gc1", "out", "ghost", "in")],  # ghost 不在 devices
            canvas_w=500, canvas_h=300,
        )
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="引用了不存在的器件"):
            route_circuit(circuit, placements)

    def test_route_placement_missing_xy(self):
        """placements 器件缺 x/y 字段应 raise RuntimeError（R03）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west")],
        )
        circuit = make_circuit(
            "Link", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        # mmi1 缺 y 字段
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="缺少字段"):
            route_circuit(circuit, placements)

    def test_route_invalid_params_type(self):
        """器件 params 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = {
            "name": "BadParams",
            "devices": [
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("out", 20, 10, "east")],
                 "params": "not a dict"},
                {"name": "mmi1", "device_type": "mmi", "width_um": 20,
                 "height_um": 5, "ports": [("in", 0, 2.5, "west")], "params": {}},
            ],
            "connections": [["gc1", "out", "mmi1", "in"]],
            "canvas_w": 500,
            "canvas_h": 300,
        }
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="params 必须是 dict"):
            route_circuit(circuit, placements)
