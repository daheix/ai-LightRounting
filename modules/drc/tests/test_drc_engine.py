"""polaris-drc 引擎回归测试 + P0 波导级规则测试。

从原 test_drc.py 拆分（R11 质量门禁：单文件 ≤800 行），覆盖:
- 回归测试: expert_demos 中心点坐标 Bug（R05 Bug 必修）
- 12. P0 波导级规则（6 条 × 3 测试 = 18 个测试）:
  BEND_RADIUS_MIN / WAVEGUIDE_WIDTH_MATCH / MIN_NOTCH /
  WAVEGUIDE_MANHATTAN / ENCLOSED_AREA_MIN / CROSSING_ANGULAR

学术依据（R02 学术诚信，≥5 个文献 URL）:
- SiEPIC EBeam PDK DRC runset URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC-Tools Verification URL: https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  URL: https://www.cambridge.org/core/books/silicon-photonics-design/
- KLayout DRC 文档 URL: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- LiDAR 2.0: Zhou et al. arXiv:2505.17239v1, ISPD 2025（Bend/Crossing）
  URL: https://arxiv.org/html/2505.17239v1
- FluxCore DRC 文档（MIN_NOTCH=100nm, MIN_BEND_RADIUS=5-10μm）
  URL: https://www.fluxcoredynamics.com/docs/design-rules
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  URL: https://doi.org/10.1007/978-3-540-77974-2
- SiEPIC Tools GDS 提取约定 https://github.com/SiEPIC/SiEPIC-Tools
- KLayout Instance API https://www.klayout.org/doc-qt5/code/class_Instance.html
- IMEC iSiPP50G 5μm（Ring Modulator）

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_drc import run_drc  # noqa: E402


# =============================================================================
# 测试辅助构造函数（真实几何数据，R03 禁止 fall-back）
# =============================================================================


def _make_simple_circuit() -> dict:
    """构造最简波导电路（与任务验证脚本一致）。"""
    return {
        "name": "test",
        "devices": [
            {
                "name": "wg",
                "device_type": "strip_waveguide",
                "ports": [
                    ("in", 0, 0, "west"),
                    ("out", 10, 0, "east"),
                ],
            },
        ],
        "connections": [],
        "canvas_w": 100,
        "canvas_h": 100,
    }


def _make_simple_placements() -> dict:
    """构造最简布局（单个波导）。"""
    return {"wg": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}


def _make_clean_circuit() -> dict:
    """构造 DRC clean 电路（2 器件 + 1 连接，所有规则通过）。

    d1.out (east) ↔ d2.in (west)，端口方向相对；
    端口 y 坐标对齐（共享 y 轴），dx=10μm 但 dy=0 ≤ 容差 10μm，PORT_ALIGNMENT 通过。
    """
    return {
        "name": "clean",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100,
        "canvas_h": 100,
    }


def _make_clean_placements() -> dict:
    """构造 DRC clean 布局（间距 10μm ≥ 1.0μm，无重叠，密度 0.1%）。"""
    return {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }


def _violation_rule_names(result: dict) -> set[str]:
    """从 run_drc 结果提取触发的规则名集合。"""
    return {v["rule_name"] for v in result["violations"]}


# =============================================================================
# 回归测试：expert_demos 中心点坐标 Bug（R05 Bug 必修）
# =============================================================================
# Bug 描述: scripts/run_real_board_drc.py 的 convert_expert_demo 函数
#   误把 SiEPIC GDS 提取的 placements.json 中 x/y（器件中心点坐标）当作
#   左下角，导致 AABB 向右上方偏移 (w/2, h/2)，相邻器件误报 NO_OVERLAP。
# 修复: 优先用 bbox[0:2]（真实物理 AABB 左下角），无 bbox 时 x-w/2, y-h/2。
# 来源: SiEPIC Tools GDS 提取约定 + KLayout Instance API bbox 语义
#   https://github.com/SiEPIC/SiEPIC-Tools
#   https://www.klayout.org/doc-qt5/code/class_Instance.html


def test_expert_demos_center_point_to_corner_bbox():
    """验证 convert_expert_demo 用 bbox 作为左下角（R05 回归）。

    构造中心点坐标 (147, 27) + bbox=[132, 17, 162, 37] + w=30, h=20 的器件，
    验证转换后 placements.x = 132（bbox[0]），而非 147（中心点 x）。
    """
    # 延迟导入：测试 scripts/run_real_board_drc.py 的转换函数
    sys.path.insert(0, "/workspace/scripts")
    # 重命名避免与测试模块名冲突
    import importlib
    rbd = importlib.import_module("run_real_board_drc")

    meta = {"canvas_w_um": 200.0, "canvas_h_um": 100.0}
    netlist = {
        "name": "test_center",
        "devices": [{
            "name": "d1",
            "device_type": "mmi",
            "width_um": 30.0,
            "height_um": 20.0,
            "ports": [["o1", 0, 10, "west"], ["o2", 30, 10, "east"]],
            "params": {},
        }],
        "connections": [],
        "canvas_w": 200.0,
        "canvas_h": 100.0,
    }
    # x/y=中心点 (147, 27)，bbox=[xmin=132, ymin=17, xmax=162, ymax=37]
    placements_raw = {
        "d1": {
            "x": 147.0, "y": 27.0,
            "width": 30.0, "height": 20.0,
            "bbox": [132.0, 17.0, 162.0, 37.0],
            "rotation": 0.0, "mirror": False,
        }
    }
    circuit, placements = rbd.convert_expert_demo(meta, netlist, placements_raw)
    # 修复后: x 应为 bbox[0]=132.0（左下角），而非中心点 147.0
    assert placements["d1"]["x"] == 132.0, (
        f"bbox 优先: x 应为 132.0（bbox[0]），实际 {placements['d1']['x']}"
    )
    assert placements["d1"]["y"] == 17.0, (
        f"bbox 优先: y 应为 17.0（bbox[1]），实际 {placements['d1']['y']}"
    )
    assert placements["d1"]["w"] == 30.0
    assert placements["d1"]["h"] == 20.0


def test_expert_demos_center_point_to_corner_no_bbox():
    """验证无 bbox 时中心点坐标转左下角（R05 回归）。

    构造中心点 (50, 30) + w=20, h=10（无 bbox）的器件，
    验证转换后 x = 50 - 20/2 = 40, y = 30 - 10/2 = 25。
    """
    sys.path.insert(0, "/workspace/scripts")
    import importlib
    rbd = importlib.import_module("run_real_board_drc")

    meta = {"canvas_w_um": 100.0, "canvas_h_um": 100.0}
    netlist = {
        "name": "test_no_bbox",
        "devices": [{
            "name": "d1",
            "device_type": "wg",
            "width_um": 20.0,
            "height_um": 10.0,
            "ports": [["o1", 0, 5, "west"], ["o2", 20, 5, "east"]],
            "params": {},
        }],
        "connections": [],
        "canvas_w": 100.0,
        "canvas_h": 100.0,
    }
    placements_raw = {
        "d1": {"x": 50.0, "y": 30.0, "width": 20.0, "height": 10.0}
    }
    circuit, placements = rbd.convert_expert_demo(meta, netlist, placements_raw)
    # 修复后: x = 50 - 20/2 = 40, y = 30 - 10/2 = 25
    assert placements["d1"]["x"] == 40.0, (
        f"中心点→左下角: x 应为 40.0 (50-20/2)，实际 {placements['d1']['x']}"
    )
    assert placements["d1"]["y"] == 25.0, (
        f"中心点→左下角: y 应为 25.0 (30-10/2)，实际 {placements['d1']['y']}"
    )


def test_expert_demos_mzi_2x2_switch_no_overlap():
    """验证 mzi_2x2_switch 不再误报 NO_OVERLAP（R05 回归）。

    Bug 修复前: mmi_rgt_1 (中心 147,27) 与 phase_shifter4 (中心 81,44)
    因中心点当左下角导致 AABB 偏移，误报重叠。
    修复后: 用 bbox 正确计算 AABB，无重叠。
    """
    sys.path.insert(0, "/workspace/scripts")
    import importlib
    rbd = importlib.import_module("run_real_board_drc")
    import json
    from pathlib import Path

    demo_dir = Path("/workspace/data/expert_demos/mzi_2x2_switch")
    meta = json.loads((demo_dir / "meta.json").read_text())
    netlist = json.loads((demo_dir / "netlist.json").read_text())
    placements_raw = json.loads((demo_dir / "placements.json").read_text())

    circuit, placements = rbd.convert_expert_demo(meta, netlist, placements_raw)
    result = run_drc(circuit, placements)
    # 修复后应无 NO_OVERLAP / MIN_SPACING 违规
    violated = {v["rule_name"] for v in result["violations"]}
    assert "NO_OVERLAP" not in violated, (
        f"mzi_2x2_switch 不应误报 NO_OVERLAP，违规: {violated}"
    )
    assert "MIN_SPACING" not in violated, (
        f"mzi_2x2_switch 不应误报 MIN_SPACING，违规: {violated}"
    )


# =============================================================================
# 12. P0 波导级规则（6 条 × 3 测试 = 18 个测试，2026-07-05 新增）
# =============================================================================


# ----- BEND_RADIUS_MIN（最小弯曲半径 5.0μm）-----


def test_bend_radius_min_pass():
    """BEND_RADIUS_MIN 通过: device.params.bend_radius_um=10.0 ≥ 阈值 5.0μm。

    来源: SiEPIC EBeam PDK bend_radius=5μm / IMEC iSiPP50G 5μm / AMF 10μm
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    circuit = {
        "name": "bend_ok",
        "devices": [{
            "name": "bend1", "device_type": "bend_waveguide",
            "params": {"bend_radius_um": 10.0},
            "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")],
        }],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"bend1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "BEND_RADIUS_MIN" not in _violation_rule_names(result), (
        f"bend_radius=10μm ≥ 5μm 应通过，违规: {_violation_rule_names(result)}"
    )


def test_bend_radius_min_fail():
    """BEND_RADIUS_MIN 违规: device.params.bend_radius_um=3.0 < 阈值 5.0μm。

    来源: SiEPIC EBeam PDK bend_radius=5μm（最小值）
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    circuit = {
        "name": "bend_fail",
        "devices": [{
            "name": "bend1", "device_type": "bend_waveguide",
            "params": {"bend_radius_um": 3.0},
            "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")],
        }],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"bend1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "BEND_RADIUS_MIN" in _violation_rule_names(result), (
        f"bend_radius=3μm < 5μm 应违规"
    )


def test_bend_radius_min_edge_no_params():
    """BEND_RADIUS_MIN 边界: 无 bend_radius_um 声明 → 跳过（直段无弯曲）。

    非 fall-back: 仅检查显式声明的弯曲半径，不伪造默认值。
    """
    circuit = {
        "name": "no_bend",
        "devices": [{
            "name": "wg1", "device_type": "strip_waveguide",
            "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")],
        }],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"wg1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "BEND_RADIUS_MIN" not in _violation_rule_names(result), (
        "无 bend_radius_um 声明应跳过（直段无弯曲半径）"
    )


# ----- WAVEGUIDE_WIDTH_MATCH（连接两端波导宽度匹配）-----


def test_waveguide_width_match_pass():
    """WAVEGUIDE_WIDTH_MATCH 通过: 两器件 h=0.5（宽度匹配）。

    来源: SiEPIC Verification "Mismatched pin widths"
    https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
    """
    circuit = _make_clean_circuit()  # d1/d2 h=0.5
    placements = _make_clean_placements()
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_WIDTH_MATCH" not in _violation_rule_names(result), (
        f"h=0.5/0.5 宽度匹配应通过，违规: {_violation_rule_names(result)}"
    )


def test_waveguide_width_match_fail():
    """WAVEGUIDE_WIDTH_MATCH 违规: d1.h=0.5 vs d2.h=0.8 宽度不匹配。

    来源: SiEPIC Verification "Mismatched pin widths"
    """
    circuit = _make_clean_circuit()  # d1.out → d2.in
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.8},  # h 不同
    }
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_WIDTH_MATCH" in _violation_rule_names(result), (
        "d1.h=0.5 vs d2.h=0.8 宽度不匹配应违规"
    )


def test_waveguide_width_match_edge_explicit_param():
    """WAVEGUIDE_WIDTH_MATCH 边界: device.params.width_um 优先于 h。

    d1.params.width_um=0.5, d2.params.width_um=0.5（即使 h 不同也匹配）。
    """
    circuit = {
        "name": "explicit_width",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "params": {"width_um": 0.5},
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "strip_waveguide",
             "params": {"width_um": 0.5},
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    # h 不同但 params.width_um 相同 → 应通过
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.8},
    }
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_WIDTH_MATCH" not in _violation_rule_names(result), (
        f"params.width_um=0.5/0.5 应匹配（优先于 h），"
        f"违规: {_violation_rule_names(result)}"
    )


def test_waveguide_width_match_bbox_false_positive_regression():
    """WAVEGUIDE_WIDTH_MATCH 回归: 非波导器件 BBOX 宽度不得用作波导宽度。

    R05 Bug: 真实板子测试 (real_board/siepic/MZI1.gds) 发现两个 ebeam_y_1550
    (y_branch) 的 device.width_um (BBOX 宽度) 分别为 15.0 和
    14.999999999999998 (GDS 浮点噪声)，被误判为波导宽度不匹配，导致
    7/7 真实电路 DRC 全失败 (0% 通过率)。

    修复后 device_waveguide_width 应取 params.wg_width=0.5 (真实波导宽度)，
    而非 device.width_um=15.0 (BBOX 宽度)。

    来源 (R02):
        - SiEPIC EBeam PDK ebeam_y_1550 y_branch 器件
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - gdsfactory wg_width 参数约定 (波导端口宽度)
          https://gdsfactory.github.io/gdsfactory/
        - SiEPIC-Tools Verification "Mismatched pin widths"
          https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
        - IEEE 754 浮点比较 (math.isclose, PEP 485)
          https://peps.python.org/pep-0485/
        - Chrostowski & Hochberg 2015 §4.3 (模式失配)
          https://www.cambridge.org/core/books/silicon-photonics-design/
    """
    # 模拟真实 GDS 提取的 y_branch 器件: BBOX width_um 不同 (浮点噪声),
    # 但 params.wg_width 相同 (0.5μm 真实波导宽度)
    circuit = {
        "name": "y_branch_bbox_regression",
        "devices": [
            {
                "name": "ebeam_y_1550",
                "device_type": "y_branch",
                "width_um": 15.0,  # BBOX 宽度 (非波导宽度)
                "height_um": 7.0,
                "params": {"radius": 5.0, "wg_width": 0.5, "wg_length": 9.5},
                "ports": [("pin1", 0, 0, "west"), ("pin2", 10, 0, "east")],
            },
            {
                "name": "ebeam_y_1550_1",
                "device_type": "y_branch",
                "width_um": 14.999999999999998,  # BBOX 浮点噪声
                "height_um": 7.0,
                "params": {"radius": 5.0, "wg_width": 0.5, "wg_length": 12.3},
                "ports": [("pin1", 0, 0, "west"), ("pin2", 10, 0, "east")],
            },
        ],
        "connections": [("ebeam_y_1550", "pin2", "ebeam_y_1550_1", "pin2")],
        "canvas_w": 200, "canvas_h": 200,
    }
    placements = {
        "ebeam_y_1550": {"x": 1.0, "y": 31.89, "w": 15.0, "h": 7.0},
        "ebeam_y_1550_1": {"x": 1.0, "y": 38.89, "w": 14.999999999999998, "h": 7.0},
    }
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_WIDTH_MATCH" not in _violation_rule_names(result), (
        f"y_branch wg_width=0.5/0.5 应匹配 (BBOX 15.0 vs 14.999... 不得用作"
        f"波导宽度)，违规: {_violation_rule_names(result)}"
    )


def test_waveguide_width_match_float_noise_tolerance():
    """WAVEGUIDE_WIDTH_MATCH 回归: 同宽度浮点噪声不得触发假阳性。

    两个 strip_waveguide 的 params.width_um 因浮点运算产生 1e-15 级差异，
    math.isclose 应吸收此噪声，不报告违规。
    """
    circuit = {
        "name": "float_noise",
        "devices": [
            {"name": "wg1", "device_type": "strip_waveguide",
             "params": {"width_um": 0.5},
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "wg2", "device_type": "strip_waveguide",
             "params": {"width_um": 0.49999999999999994},  # 浮点噪声
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [("wg1", "out", "wg2", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "wg1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "wg2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_WIDTH_MATCH" not in _violation_rule_names(result), (
        f"浮点噪声 (0.5 vs 0.49999999999999994) 应由 math.isclose 吸收，"
        f"违规: {_violation_rule_names(result)}"
    )


# ----- MIN_NOTCH（最小凹槽宽度 0.1μm = 100nm）-----


def test_min_notch_pass():
    """MIN_NOTCH 通过: 两无连接器件间距 0.5μm ≥ 阈值 0.1μm。

    来源: KLayout notch() / FluxCore MIN_NOTCH=100nm
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """
    circuit = {
        "name": "notch_ok",
        "devices": [
            {"name": "d1", "device_type": "mmi",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "mmi",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 5.0},
        "d2": {"x": 20.5, "y": 10.0, "w": 10.0, "h": 5.0},  # gap=0.5μm
    }
    result = run_drc(circuit, placements)
    assert "MIN_NOTCH" not in _violation_rule_names(result), (
        f"gap=0.5μm ≥ 0.1μm 应通过，违规: {_violation_rule_names(result)}"
    )


def test_min_notch_fail():
    """MIN_NOTCH 违规: 两无连接器件间距 0.05μm < 阈值 0.1μm。

    d1 AABB=(10,10,20,15), d2 AABB=(20.05,10,30.05,15),
    dx=max(20.05-20, 10-30.05, 0)=0.05, dy=0, dist=0.05 < 0.1。
    """
    circuit = {
        "name": "notch_fail",
        "devices": [
            {"name": "d1", "device_type": "mmi",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "mmi",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 5.0},
        "d2": {"x": 20.05, "y": 10.0, "w": 10.0, "h": 5.0},  # gap=0.05μm
    }
    result = run_drc(circuit, placements)
    assert "MIN_NOTCH" in _violation_rule_names(result), (
        "gap=0.05μm < 0.1μm 应违规（窄颈）"
    )


def test_min_notch_edge_touching():
    """MIN_NOTCH 边界: 两无连接器件 touching（gap=0）→ 不报 MIN_NOTCH。

    touching 由 NO_OVERLAP 处理（gap=0 不算窄颈）。
    aabb_distance 返回 0 表示 touching/overlapping。
    """
    circuit = {
        "name": "notch_touching",
        "devices": [
            {"name": "d1", "device_type": "mmi",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "mmi",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 5.0},
        "d2": {"x": 20.0, "y": 10.0, "w": 10.0, "h": 5.0},  # touching gap=0
    }
    result = run_drc(circuit, placements)
    assert "MIN_NOTCH" not in _violation_rule_names(result), (
        "touching (gap=0) 不应报 MIN_NOTCH（由 NO_OVERLAP 处理）"
    )


# ----- WAVEGUIDE_MANHATTAN（波导首末段 Manhattan）-----


def test_waveguide_manhattan_pass():
    """WAVEGUIDE_MANHATTAN 通过: 波导端口方向 east/west（Manhattan）。

    来源: SiEPIC Verification "首末段必须 Manhattan"
    https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
    """
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "WAVEGUIDE_MANHATTAN" not in _violation_rule_names(result), (
        f"east/west Manhattan 应通过，违规: {_violation_rule_names(result)}"
    )


def test_waveguide_manhattan_fail():
    """WAVEGUIDE_MANHATTAN 违规: 波导端口方向 'northeast' 非 Manhattan。

    来源: SiEPIC Verification "首末段必须 Manhattan"
    """
    circuit = {
        "name": "manhattan_fail",
        "devices": [{
            "name": "wg1", "device_type": "strip_waveguide",
            "ports": [("in", 0, 0, "west"), ("out", 10, 0, "northeast")],
        }],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"wg1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_MANHATTAN" in _violation_rule_names(result), (
        "波导端口方向 'northeast' 非 Manhattan 应违规"
    )


def test_waveguide_manhattan_edge_non_waveguide():
    """WAVEGUIDE_MANHATTAN 边界: 非波导器件（如 mmi）不检查 Manhattan。

    本规则仅约束波导器件首末段，MMI/ GC 等非波导器件跳过。
    """
    circuit = {
        "name": "non_wg",
        "devices": [{
            "name": "mmi1", "device_type": "mmi",
            "ports": [("in", 0, 0, "west"), ("out", 10, 0, "northeast")],
        }],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"mmi1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 5.0}}
    result = run_drc(circuit, placements)
    assert "WAVEGUIDE_MANHATTAN" not in _violation_rule_names(result), (
        "MMI 非波导器件不应触发 WAVEGUIDE_MANHATTAN"
    )


# ----- ENCLOSED_AREA_MIN（最小封闭面积 0.01μm²）-----


def test_enclosed_area_min_pass():
    """ENCLOSED_AREA_MIN 通过: 无环（树形连接）→ 无封闭区域。

    来源: KLayout area_check（内孔检测）
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "ENCLOSED_AREA_MIN" not in _violation_rule_names(result), (
        f"无环连接应通过，违规: {_violation_rule_names(result)}"
    )


def test_enclosed_area_min_fail():
    """ENCLOSED_AREA_MIN 违规: 3 器件环包围面积 < 0.01μm²。

    3 器件环: d1↔d2↔d3↔d1，bbox=(0,0)-(0.03,0.03), area=0.0009 < 0.01。
    来源: KLayout area_check（避免孤立小洞）
    """
    circuit = {
        "name": "small_loop",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("p1", 0, 0, "west"), ("p2", 0.01, 0, "east")]},
            {"name": "d2", "device_type": "wg",
             "ports": [("p1", 0, 0, "west"), ("p2", 0.01, 0, "east")]},
            {"name": "d3", "device_type": "wg",
             "ports": [("p1", 0, 0, "west"), ("p2", 0.01, 0, "east")]},
        ],
        "connections": [
            ("d1", "p2", "d2", "p1"),
            ("d2", "p2", "d3", "p1"),
            ("d3", "p2", "d1", "p1"),
        ],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 0.0, "y": 0.0, "w": 0.01, "h": 0.01},
        "d2": {"x": 0.02, "y": 0.0, "w": 0.01, "h": 0.01},
        "d3": {"x": 0.01, "y": 0.02, "w": 0.01, "h": 0.01},
    }
    result = run_drc(circuit, placements)
    assert "ENCLOSED_AREA_MIN" in _violation_rule_names(result), (
        f"3 器件小环 area=0.0009μm² < 0.01μm² 应违规，"
        f"违规: {_violation_rule_names(result)}"
    )


def test_enclosed_area_min_edge_large_loop():
    """ENCLOSED_AREA_MIN 边界: 3 器件环包围面积 > 0.01μm² → 通过。

    3 器件环: d1↔d2↔d3↔d1，bbox=(0,0)-(30,30), area=900 > 0.01。
    """
    circuit = {
        "name": "large_loop",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("p1", 0, 0, "west"), ("p2", 10, 0, "east")]},
            {"name": "d2", "device_type": "wg",
             "ports": [("p1", 0, 0, "west"), ("p2", 10, 0, "east")]},
            {"name": "d3", "device_type": "wg",
             "ports": [("p1", 0, 0, "west"), ("p2", 10, 0, "east")]},
        ],
        "connections": [
            ("d1", "p2", "d2", "p1"),
            ("d2", "p2", "d3", "p1"),
            ("d3", "p2", "d1", "p1"),
        ],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 20.0, "y": 0.0, "w": 10.0, "h": 0.5},
        "d3": {"x": 10.0, "y": 20.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "ENCLOSED_AREA_MIN" not in _violation_rule_names(result), (
        f"3 器件大环 area=900μm² > 0.01μm² 应通过，"
        f"违规: {_violation_rule_names(result)}"
    )


# ----- CROSSING_ANGULAR（交叉角度 90° 优选）-----


def test_crossing_angular_pass():
    """CROSSING_ANGULAR 通过: 水平×垂直波导交叉 = 90°。

    来源: LiDAR 2.0 II-B3 arXiv:2505.17239v1（90° 交叉最优）
    https://arxiv.org/html/2505.17239v1
    """
    circuit = {
        "name": "crossing_90",
        "devices": [
            {"name": "h_wg", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "v_wg", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "south"), ("out", 0, 10, "north")]},
        ],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "h_wg": {"x": 0.0, "y": 4.75, "w": 10.0, "h": 0.5},   # 水平
        "v_wg": {"x": 4.75, "y": 0.0, "w": 0.5, "h": 10.0},    # 垂直
    }
    result = run_drc(circuit, placements)
    assert "CROSSING_ANGULAR" not in _violation_rule_names(result), (
        f"水平×垂直 = 90° 应通过，违规: {_violation_rule_names(result)}"
    )


def test_crossing_angular_fail():
    """CROSSING_ANGULAR 违规: 两水平波导交叉（同向，0°）。

    两无连接水平波导 AABB 重叠，同为水平方向 → 非 90° 交叉。
    """
    circuit = {
        "name": "crossing_0",
        "devices": [
            {"name": "h1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "h2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "h1": {"x": 0.0, "y": 4.75, "w": 10.0, "h": 0.5},
        "h2": {"x": 5.0, "y": 4.75, "w": 10.0, "h": 0.5},  # 同水平，重叠
    }
    result = run_drc(circuit, placements)
    assert "CROSSING_ANGULAR" in _violation_rule_names(result), (
        "两水平波导交叉（0°）应违规"
    )


def test_crossing_angular_edge_connected():
    """CROSSING_ANGULAR 边界: 连接器件重叠不报 CROSSING_ANGULAR（由 NO_OVERLAP 处理）。

    d1↔d2 连接，即使方向相同也不报 CROSSING_ANGULAR。
    """
    circuit = {
        "name": "crossing_connected",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 0.0, "y": 4.75, "w": 10.0, "h": 0.5},
        "d2": {"x": 5.0, "y": 4.75, "w": 10.0, "h": 0.5},  # 重叠但已连接
    }
    result = run_drc(circuit, placements)
    assert "CROSSING_ANGULAR" not in _violation_rule_names(result), (
        "连接器件重叠不应报 CROSSING_ANGULAR（由 NO_OVERLAP 处理）"
    )
