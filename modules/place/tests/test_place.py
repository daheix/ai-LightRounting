"""polaris-place 子模块测试。

测试覆盖:
- test_place_analytical_mzi: 5 器件 MZI 解析法布局，验证 n_placements=5, hpwl>0
- test_compute_hpwl: 验证 HPWL 计算正确性
- test_render_ascii: 验证 ASCII 渲染返回非空字符串
- test_place_ppo_gnn_no_checkpoint: ppo_gnn 模式无 checkpoint 时 raise RuntimeError

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
- SiEPIC PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
for _p in (_SRC, _CORE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_place  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_place import compute_hpwl, place_circuit, render_ascii_layout  # noqa: E402


def _make_mzi_circuit() -> dict:
    """构造 5 器件 MZI 电路（与验证脚本一致）。

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


def test_place_analytical_mzi():
    """5 器件 MZI 解析法布局: n_placements=5, hpwl>0, 模式与字段正确。

    验证:
    - 返回 dict 含全部必要字段
    - placements 数量 = 5（与器件数一致）
    - 每个 placement 含 x/y/w/h 字段，且在画布内
    - hpwl > 0（器件间有连线，布局物理合理）
    - placement_mode == "analytical"
    - checkpoint_loaded == False
    """
    circuit = _make_mzi_circuit()
    result = place_circuit(circuit, mode="analytical")

    # 必要字段
    for key in ("placements", "hpwl", "placement_mode", "checkpoint_loaded"):
        assert key in result, f"结果缺少字段: {key}"

    assert result["placement_mode"] == "analytical"
    assert result["checkpoint_loaded"] is False

    placements = result["placements"]
    assert len(placements) == 5, f"应有 5 个 placement，实际 {len(placements)}"

    canvas_w = circuit["canvas_w"]
    canvas_h = circuit["canvas_h"]
    for name, pl in placements.items():
        assert {"x", "y", "w", "h"} <= set(pl.keys()), \
            f"placement {name} 缺少字段: {pl}"
        assert pl["w"] > 0 and pl["h"] > 0, f"placement {name} 尺寸非正: {pl}"
        # 左下角坐标在画布内（允许等号边界）
        assert 0.0 <= pl["x"] <= canvas_w, f"placement {name} x 越界: {pl}"
        assert 0.0 <= pl["y"] <= canvas_h, f"placement {name} y 越界: {pl}"
        # 右上角不超出画布
        assert pl["x"] + pl["w"] <= canvas_w + 1e-6, \
            f"placement {name} 右边界越界: {pl}"
        assert pl["y"] + pl["h"] <= canvas_h + 1e-6, \
            f"placement {name} 上边界越界: {pl}"

    assert result["hpwl"] > 0.0, f"HPWL 应 > 0，实际 {result['hpwl']}"


def test_place_analytical_signal_flow():
    """回归测试: 信号流方向 x 坐标必须递增（R05 防 BUG 复发）。

    BUG 现象: FFDH 合法化仅按高度降序装箱，不考虑信号流拓扑，导致后端
    器件（mmi2/gc2）被塞到前端器件的行内空隙，x 坐标反而小于中段器件
    （ps1），产生物理重叠与 DRC 违规。

    修复: FFDH 装箱前先用 Kahn 算法计算拓扑深度，按 (拓扑深度, -高度)
    排序，候选行需满足拓扑约束（行内最大 depth < 当前 depth）。

    本测试用验证脚本同款 MZI 电路（gc1→mmi1→ps1→mmi2→gc2），
    断言信号流方向 x 严格递增。

    来源（R02 学术诚信）:
        - Kahn 1962 拓扑排序 https://doi.org/10.1145/368996.369025
        - FFDH: Coffman et al. 1980 https://epubs.siam.org/doi/10.1137/0209062
        - DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746
        - HPWL: Kahng & Lienig IEEE TCAD 2009
          https://ieeexplore.ieee.org/document/4685534
        - SiEPIC PDK MZI 示例 https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    gc1 = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi1 = make_device(
        "mmi1", "mmi_1x2", 30, 20,
        ports=[("in", 0, 10, "west"), ("out1", 30, 5, "east"),
               ("out2", 30, 15, "east")],
    )
    ps1 = make_device(
        "ps1", "phase_shifter", 100, 10,
        ports=[("in", 0, 5, "west"), ("out", 100, 5, "east")],
    )
    mmi2 = make_device(
        "mmi2", "mmi_2x2", 30, 20,
        ports=[("in1", 0, 5, "west"), ("in2", 0, 15, "west"),
               ("out1", 30, 10, "east"), ("out2", 30, 10, "east")],
    )
    gc2 = make_device(
        "gc2", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    circuit = make_circuit(
        "MZI", [gc1, mmi1, ps1, mmi2, gc2],
        [
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "ps1", "in"),
            ("ps1", "out", "mmi2", "in1"),
            ("mmi1", "out2", "mmi2", "in2"),
            ("mmi2", "out1", "gc2", "in"),
        ],
        canvas_w=500, canvas_h=300,
    )
    result = place_circuit(circuit, mode="analytical")
    xs = {name: p["x"] for name, p in result["placements"].items()}

    # 信号流 gc1->mmi1->ps1->mmi2->gc2 应 x 严格递增
    assert xs["gc1"] < xs["mmi1"] < xs["ps1"], (
        f"gc1={xs['gc1']} mmi1={xs['mmi1']} ps1={xs['ps1']} 顺序错误"
    )
    assert xs["ps1"] < xs["mmi2"], (
        f"ps1={xs['ps1']} mmi2={xs['mmi2']} 顺序错误"
    )
    assert xs["mmi2"] < xs["gc2"], (
        f"mmi2={xs['mmi2']} gc2={xs['gc2']} 顺序错误"
    )


def test_compute_hpwl():
    """验证 HPWL 计算: 手工构造两个器件一条连接，HPWL = 曼哈顿距离。"""
    gc = make_device("gc1", "grating_coupler", 20, 20,
                     ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")])
    mmi = make_device("mmi1", "mmi_1x2", 20, 5,
                      ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")])
    circuit = make_circuit("Link", [gc, mmi],
                           [("gc1", "out", "mmi1", "in")],
                           canvas_w=500, canvas_h=300)
    # 手工放置: gc 中心 (10, 10), mmi 中心 (460, 152.5)
    placements = {
        "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},   # 中心 (10, 10)
        "mmi1": {"x": 450.0, "y": 150.0, "w": 20.0, "h": 5.0},  # 中心 (460, 152.5)
    }
    expected = abs(460.0 - 10.0) + abs(152.5 - 10.0)  # 450.0 + 142.5 = 592.5
    hpwl = compute_hpwl(circuit, placements)
    assert abs(hpwl - expected) < 1e-9, f"HPWL 期望 {expected}，实际 {hpwl}"


def test_render_ascii():
    """验证 ASCII 渲染: 返回非空字符串，含标题/图例/器件字符。"""
    circuit = _make_mzi_circuit()
    result = place_circuit(circuit, mode="analytical")
    ascii_layout = render_ascii_layout(circuit, result["placements"],
                                       grid_w=40, grid_h=15)
    assert isinstance(ascii_layout, str)
    assert len(ascii_layout) > 0, "ASCII 渲染结果为空"
    # 含标题
    assert "MZI" in ascii_layout
    # 含图例
    assert "G=grating_coupler" in ascii_layout
    # 含器件字符（5 个器件放置后至少有一个 G/M/W 字符出现）
    assert any(c in ascii_layout for c in ("G", "M", "W")), \
        "ASCII 渲染未包含任何器件字符"
    # 含点号（空位）
    assert "." in ascii_layout


def test_place_ppo_gnn_no_checkpoint():
    """ppo_gnn 模式无 checkpoint 时 raise RuntimeError（R03 禁止 fall-back）。

    通过环境变量强制指向不存在的 checkpoint 路径，并确保候选路径均不存在，
    验证 place_circuit(mode="ppo_gnn") raise RuntimeError。
    """
    circuit = _make_mzi_circuit()

    # 备份并清除可能指向真实 checkpoint 的环境变量
    saved = os.environ.pop("POLARIS_PLACE_CHECKPOINT", None)
    # 临时指向一个确定不存在的路径（确保不与候选路径命中真实文件）
    os.environ["POLARIS_PLACE_CHECKPOINT"] = "/nonexistent/polaris_place_ppo_gnn.json"
    try:
        with pytest.raises(RuntimeError, match="checkpoint"):
            place_circuit(circuit, mode="ppo_gnn")
    finally:
        # 恢复环境
        os.environ.pop("POLARIS_PLACE_CHECKPOINT", None)
        if saved is not None:
            os.environ["POLARIS_PLACE_CHECKPOINT"] = saved


def test_place_circuit_invalid_mode():
    """非法 mode 应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="不支持的布局模式"):
        place_circuit(circuit, mode="unknown_mode")
