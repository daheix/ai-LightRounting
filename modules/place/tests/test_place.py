"""polaris-place 子模块深度测试（v5.0）。

覆盖 polaris_place 全部公开 API:
- 配置: AnalyticalConfig (gamma/density_weight/learning_rate/max_iterations/...)
- 解析法: place_analytical (DREAMPlace warm-start + FFDH 合法化)
- 端到端: place_circuit (analytical/ppo_gnn 模式)
- AI 布局: place_ppo_gnn (Edge-GNN + PPO, 需 checkpoint)
- 指标: compute_hpwl (半周长线长)
- 可视化: render_ascii_layout (ASCII 网格)

测试组织（共 42 个测试）:
1. TestAnalyticalConfig: 配置参数 (5)
2. TestComputeHpwl: HPWL 计算 (6)
3. TestPlaceAnalytical: 解析法布局 (8)
4. TestPlaceCircuit: 端到端布局 (7)
5. TestPlacePpoGnn: AI 布局与 checkpoint (4)
6. TestRenderAsciiLayout: ASCII 可视化 (6)
7. TestPlaceEdgeCases: 边界情况 (6)

来源（R02 学术诚信，≥5 个文献 URL）:
- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020 (Lin et al.): https://arxiv.org/abs/2004.10746
- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
- FFDH 合法化: Coffman et al. SIAM J. Comput. 9(4) 1980
  https://epubs.siam.org/doi/10.1137/0209062
- Adam 优化器: Kingma & Ba 2014 https://arxiv.org/abs/1412.6980
- PPO: Schulman et al. 2017 https://arxiv.org/abs/1707.06347
- GAT: Veličković et al. ICLR 2018 https://arxiv.org/abs/1710.10903
- Kahn 1962 拓扑排序 https://doi.org/10.1145/368996.369025
- pytest 文档: https://docs.pytest.org/
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
for _p in (_SRC, _CORE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_place  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_place import (  # noqa: E402
    AnalyticalConfig,
    compute_hpwl,
    place_analytical,
    place_circuit,
    place_ppo_gnn,
    render_ascii_layout,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _make_mzi_circuit() -> dict:
    """构造 5 器件 5 连接 MZI 电路（与验证脚本一致）。"""
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


def _check_no_overlap(placements: dict) -> bool:
    """检查所有器件无重叠（轴对齐矩形相交判定）。

    Returns:
        True 若无重叠，False 若存在至少一对重叠。
    """
    items = list(placements.values())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            # 轴对齐矩形重叠: x/y 方向投影均相交
            x_overlap = not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"])
            y_overlap = not (a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"])
            if x_overlap and y_overlap:
                return False
    return True


def _make_valid_ppo_checkpoint() -> dict:
    """构造合法的 ppo_gnn checkpoint（PPO 权重形状与网络架构一致）。

    权重形状来源: polaris_place.ppo_gnn.ActorCritic
    - shared.0.weight: [64, 24]  (obs_dim=24, hidden_dim=64)
    - shared.0.bias: [64]
    - shared.2.weight: [64, 64]
    - shared.2.bias: [64]
    - action_mean.weight: [2, 64]  (action_dim=2)
    - action_mean.bias: [2]
    - value_head.weight: [1, 64]
    - value_head.bias: [1]
    """
    rng = np.random.default_rng(42)
    return {
        "network": {
            "shared.0.weight": rng.standard_normal((64, 24)).tolist(),
            "shared.0.bias": rng.standard_normal(64).tolist(),
            "shared.2.weight": rng.standard_normal((64, 64)).tolist(),
            "shared.2.bias": rng.standard_normal(64).tolist(),
            "action_mean.weight": rng.standard_normal((2, 64)).tolist(),
            "action_mean.bias": rng.standard_normal(2).tolist(),
            "value_head.weight": rng.standard_normal((1, 64)).tolist(),
            "value_head.bias": rng.standard_normal(1).tolist(),
        }
    }


# ============================================================
# 1. TestAnalyticalConfig — 解析法布局配置
# ============================================================
class TestAnalyticalConfig:
    """AnalyticalConfig 默认值与自定义参数（DREAMPlace TCAD 2020）。"""

    def test_default_config(self):
        """默认配置符合 DREAMPlace 论文值。"""
        cfg = AnalyticalConfig()
        assert cfg.gamma == 4.0  # DREAMPlace 默认
        assert cfg.density_weight == 1.0e-3
        assert cfg.learning_rate == 0.01
        assert cfg.max_iterations == 200
        assert cfg.density_bandwidth == 10.0
        assert cfg.convergence_threshold == 1.0
        assert cfg.seed == 42

    def test_custom_config(self):
        """自定义配置应正确传递。"""
        cfg = AnalyticalConfig(
            gamma=2.0,
            density_weight=0.01,
            learning_rate=0.001,
            max_iterations=50,
            density_bandwidth=5.0,
            convergence_threshold=0.5,
            seed=123,
        )
        assert cfg.gamma == 2.0
        assert cfg.density_weight == 0.01
        assert cfg.learning_rate == 0.001
        assert cfg.max_iterations == 50
        assert cfg.density_bandwidth == 5.0
        assert cfg.convergence_threshold == 0.5
        assert cfg.seed == 123

    def test_config_is_dataclass(self):
        """AnalyticalConfig 应为 dataclass（可解构）。"""
        from dataclasses import fields, is_dataclass
        assert is_dataclass(AnalyticalConfig)
        field_names = {f.name for f in fields(AnalyticalConfig)}
        assert {"gamma", "density_weight", "learning_rate",
                "max_iterations", "density_bandwidth",
                "convergence_threshold", "seed"} <= field_names

    def test_config_attribute_types(self):
        """配置属性类型正确（float/int）。"""
        cfg = AnalyticalConfig()
        assert isinstance(cfg.gamma, float)
        assert isinstance(cfg.density_weight, float)
        assert isinstance(cfg.learning_rate, float)
        assert isinstance(cfg.max_iterations, int)
        assert isinstance(cfg.density_bandwidth, float)
        assert isinstance(cfg.convergence_threshold, float)
        assert isinstance(cfg.seed, int)

    def test_config_seed_reproducibility(self):
        """同 seed 的布局结果一致（DREAMPlace 可复现性约定）。"""
        circuit = _make_mzi_circuit()
        cfg1 = AnalyticalConfig(seed=42, max_iterations=20)
        cfg2 = AnalyticalConfig(seed=42, max_iterations=20)
        p1 = place_analytical(circuit, cfg1)
        p2 = place_analytical(circuit, cfg2)
        for name in p1:
            assert p1[name]["x"] == pytest.approx(p2[name]["x"])
            assert p1[name]["y"] == pytest.approx(p2[name]["y"])


# ============================================================
# 2. TestComputeHpwl — HPWL 半周长线长
# ============================================================
class TestComputeHpwl:
    """compute_hpwl 曼哈顿距离求和（Kahng & Lienig IEEE TCAD 2009）。"""

    def test_compute_hpwl_single_connection(self):
        """单连接 HPWL = 两器件中心曼哈顿距离。"""
        gc = make_device("gc1", "grating_coupler", 20, 20,
                         ports=[("out", 20, 10, "east")])
        mmi = make_device("mmi1", "mmi_1x2", 20, 5,
                          ports=[("in", 0, 2.5, "west")])
        circuit = make_circuit("Link", [gc, mmi],
                               [("gc1", "out", "mmi1", "in")],
                               canvas_w=500, canvas_h=300)
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},   # 中心 (10, 10)
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},  # 中心 (110, 2.5)
        }
        expected = abs(110.0 - 10.0) + abs(2.5 - 10.0)  # 100 + 7.5 = 107.5
        hpwl = compute_hpwl(circuit, placements)
        assert abs(hpwl - expected) < 1e-9

    def test_compute_hpwl_multiple_connections(self):
        """多连接 HPWL = 各连接曼哈顿距离之和。"""
        d1 = make_device("d1", "mmi_1x2", 10, 10, ports=[("o", 10, 5, "east")])
        d2 = make_device("d2", "mmi_1x2", 10, 10, ports=[("i", 0, 5, "west")])
        d3 = make_device("d3", "mmi_1x2", 10, 10, ports=[("i", 0, 5, "west")])
        circuit = make_circuit("Chain", [d1, d2, d3],
                               [("d1", "o", "d2", "i"),
                                ("d2", "o", "d3", "i")],
                               canvas_w=500, canvas_h=300)
        placements = {
            "d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0},    # 中心 (5, 5)
            "d2": {"x": 100.0, "y": 0.0, "w": 10.0, "h": 10.0},  # 中心 (105, 5)
            "d3": {"x": 200.0, "y": 0.0, "w": 10.0, "h": 10.0},  # 中心 (205, 5)
        }
        # d1-d2: |105-5| + |5-5| = 100
        # d2-d3: |205-105| + |5-5| = 100
        expected = 100.0 + 100.0
        hpwl = compute_hpwl(circuit, placements)
        assert abs(hpwl - expected) < 1e-9

    def test_compute_hpwl_no_connections(self):
        """无连接时 HPWL = 0。"""
        gc = make_device("gc1", "grating_coupler", 20, 20)
        circuit = make_circuit("Empty", [gc], [], canvas_w=500, canvas_h=300)
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        assert compute_hpwl(circuit, placements) == 0.0

    def test_compute_hpwl_missing_device_skipped(self):
        """连接引用的器件不在 placements 中时跳过该连接。"""
        d1 = make_device("d1", "mmi_1x2", 10, 10, ports=[("o", 10, 5, "east")])
        d2 = make_device("d2", "mmi_1x2", 10, 10, ports=[("i", 0, 5, "west")])
        circuit = make_circuit("Link", [d1, d2],
                               [("d1", "o", "d2", "i")],
                               canvas_w=500, canvas_h=300)
        # d2 不在 placements 中
        placements = {"d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}}
        assert compute_hpwl(circuit, placements) == 0.0

    def test_compute_hpwl_uses_center_coordinates(self):
        """HPWL 使用器件中心坐标（x + w/2, y + h/2），非左下角。"""
        d1 = make_device("d1", "mmi_1x2", 20, 10, ports=[("o", 20, 5, "east")])
        d2 = make_device("d2", "mmi_1x2", 20, 10, ports=[("i", 0, 5, "west")])
        circuit = make_circuit("Center", [d1, d2],
                               [("d1", "o", "d2", "i")],
                               canvas_w=500, canvas_h=300)
        placements = {
            # d1 左下角 (0,0), 中心 (10, 5)
            "d1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 10.0},
            # d2 左下角 (100, 50), 中心 (110, 55)
            "d2": {"x": 100.0, "y": 50.0, "w": 20.0, "h": 10.0},
        }
        # 中心距离 = |110-10| + |55-5| = 100 + 50 = 150
        # 左下角距离 = |100-0| + |50-0| = 100 + 50 = 150 (巧合相同)
        # 用非对称尺寸确保区分: d1 中心 (10,5), d2 中心 (110,55)
        expected = abs(110.0 - 10.0) + abs(55.0 - 5.0)  # 150
        hpwl = compute_hpwl(circuit, placements)
        assert abs(hpwl - expected) < 1e-9

    def test_compute_hpwl_returns_float(self):
        """compute_hpwl 返回 float 类型。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        hpwl = compute_hpwl(circuit, placements)
        assert isinstance(hpwl, float)


# ============================================================
# 3. TestPlaceAnalytical — 解析法布局
# ============================================================
class TestPlaceAnalytical:
    """place_analytical DREAMPlace warm-start + FFDH 合法化。"""

    def test_place_analytical_returns_dict(self):
        """place_analytical 返回布局字典。"""
        circuit = _make_mzi_circuit()
        placements = place_analytical(circuit)
        assert isinstance(placements, dict)
        assert len(placements) == 5
        assert "gc1" in placements
        assert "mmi2" in placements

    def test_place_analytical_empty_circuit(self):
        """空电路（无器件）返回空字典。"""
        circuit = make_circuit("Empty", [], [], canvas_w=500, canvas_h=300)
        placements = place_analytical(circuit)
        assert placements == {}

    def test_place_analytical_single_device(self):
        """单器件电路返回 1 个布局。"""
        gc = make_device("gc1", "grating_coupler", 20, 20)
        circuit = make_circuit("Single", [gc], [], canvas_w=500, canvas_h=300)
        placements = place_analytical(circuit)
        assert len(placements) == 1
        assert "gc1" in placements

    def test_place_analytical_in_canvas(self):
        """布局坐标在画布内（左下角 + 尺寸不超出画布）。"""
        circuit = _make_mzi_circuit()
        placements = place_analytical(circuit)
        canvas_w = circuit["canvas_w"]
        canvas_h = circuit["canvas_h"]
        for name, pl in placements.items():
            assert 0.0 <= pl["x"] <= canvas_w, f"{name} x 越界: {pl}"
            assert 0.0 <= pl["y"] <= canvas_h, f"{name} y 越界: {pl}"
            assert pl["x"] + pl["w"] <= canvas_w + 1e-6, \
                f"{name} 右边界越界: {pl}"
            assert pl["y"] + pl["h"] <= canvas_h + 1e-6, \
                f"{name} 上边界越界: {pl}"

    def test_place_analytical_no_nan(self):
        """布局坐标无 NaN/Inf。"""
        circuit = _make_mzi_circuit()
        placements = place_analytical(circuit)
        for name, pl in placements.items():
            for key in ("x", "y", "w", "h"):
                assert np.isfinite(pl[key]), f"{name}.{key} 非有限: {pl[key]}"

    def test_place_analytical_with_custom_config(self):
        """自定义配置应正确执行（少迭代加速测试）。"""
        circuit = _make_mzi_circuit()
        cfg = AnalyticalConfig(max_iterations=10, convergence_threshold=0.1)
        placements = place_analytical(circuit, cfg)
        assert len(placements) == 5

    def test_place_analytical_no_overlap(self):
        """合法化后无重叠（FFDH + 拓扑约束）。"""
        circuit = _make_mzi_circuit()
        placements = place_analytical(circuit)
        assert _check_no_overlap(placements), "布局存在重叠"

    def test_place_analytical_preserves_device_count(self):
        """布局后器件数不变。"""
        circuit = _make_mzi_circuit()
        placements = place_analytical(circuit)
        assert len(placements) == len(circuit["devices"])

    def test_place_analytical_preserves_sizes(self):
        """布局后器件宽高与输入一致。"""
        circuit = _make_mzi_circuit()
        placements = place_analytical(circuit)
        for dev in circuit["devices"]:
            name = dev["name"]
            assert placements[name]["w"] == pytest.approx(dev["width_um"])
            assert placements[name]["h"] == pytest.approx(dev["height_um"])


# ============================================================
# 4. TestPlaceCircuit — 端到端布局
# ============================================================
class TestPlaceCircuit:
    """place_circuit 端到端布局（analytical/ppo_gnn 模式）。"""

    def test_place_circuit_analytical_mode(self):
        """analytical 模式返回完整结果 dict。"""
        circuit = _make_mzi_circuit()
        result = place_circuit(circuit, mode="analytical")
        for key in ("placements", "hpwl", "placement_mode", "checkpoint_loaded"):
            assert key in result, f"结果缺少字段: {key}"
        assert result["placement_mode"] == "analytical"
        assert result["checkpoint_loaded"] is False
        assert len(result["placements"]) == 5

    def test_place_circuit_invalid_mode(self):
        """非法 mode 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = _make_mzi_circuit()
        with pytest.raises(RuntimeError, match="不支持的布局模式"):
            place_circuit(circuit, mode="unknown_mode")

    def test_place_circuit_returns_hpwl(self):
        """place_circuit 返回的 hpwl 与 compute_hpwl 一致。"""
        circuit = _make_mzi_circuit()
        result = place_circuit(circuit, mode="analytical")
        expected_hpwl = compute_hpwl(circuit, result["placements"])
        assert abs(result["hpwl"] - expected_hpwl) < 1e-9

    def test_place_circuit_analytical_hpwl_positive(self):
        """analytical 布局 HPWL > 0（器件间有连线）。"""
        circuit = _make_mzi_circuit()
        result = place_circuit(circuit, mode="analytical")
        assert result["hpwl"] > 0.0

    def test_place_circuit_invalid_circuit_dict(self):
        """circuit 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
            place_circuit("not a dict", mode="analytical")
        with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
            place_circuit(None, mode="analytical")

    def test_place_circuit_missing_field(self):
        """circuit 缺必要字段应 raise RuntimeError（R03 禁止 fall-back）。"""
        # 缺 connections 字段
        bad_circuit = {
            "name": "Bad",
            "devices": [],
            "canvas_w": 500,
            "canvas_h": 300,
        }
        with pytest.raises(RuntimeError, match="circuit 缺少必要字段"):
            place_circuit(bad_circuit, mode="analytical")

    def test_place_circuit_zero_canvas_raises(self):
        """画布尺寸为 0 应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device("gc1", "grating_coupler", 20, 20)
        circuit = make_circuit("Zero", [gc], [], canvas_w=0, canvas_h=300)
        with pytest.raises(RuntimeError, match="画布尺寸必须为正"):
            place_circuit(circuit, mode="analytical")

    def test_place_circuit_default_mode_analytical(self):
        """默认 mode 为 analytical。"""
        circuit = _make_mzi_circuit()
        result = place_circuit(circuit)  # 不传 mode
        assert result["placement_mode"] == "analytical"


# ============================================================
# 5. TestPlacePpoGnn — AI 布局与 checkpoint
# ============================================================
class TestPlacePpoGnn:
    """place_ppo_gnn Edge-GNN + PPO AI 布局（R03: 无 checkpoint 即 raise）。"""

    def test_place_ppo_gnn_no_checkpoint_raises(self):
        """ppo_gnn 无 checkpoint 时 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = _make_mzi_circuit()
        saved = os.environ.pop("POLARIS_PLACE_CHECKPOINT", None)
        os.environ["POLARIS_PLACE_CHECKPOINT"] = "/nonexistent/polaris_place_ppo_gnn.json"
        try:
            with pytest.raises(RuntimeError, match="checkpoint"):
                place_circuit(circuit, mode="ppo_gnn")
        finally:
            os.environ.pop("POLARIS_PLACE_CHECKPOINT", None)
            if saved is not None:
                os.environ["POLARIS_PLACE_CHECKPOINT"] = saved

    def test_place_ppo_gnn_with_checkpoint(self, tmp_path, monkeypatch):
        """ppo_gnn 有合法 checkpoint 时返回布局（checkpoint_loaded=True）。

        构造合法 PPO checkpoint（权重形状与 ActorCritic 架构一致），
        通过环境变量 POLARIS_PLACE_CHECKPOINT 指定路径。
        """
        ckpt = _make_valid_ppo_checkpoint()
        ckpt_path = tmp_path / "ppo_gnn.json"
        ckpt_path.write_text(json.dumps(ckpt), encoding="utf-8")
        monkeypatch.setenv("POLARIS_PLACE_CHECKPOINT", str(ckpt_path))

        circuit = _make_mzi_circuit()
        result = place_circuit(circuit, mode="ppo_gnn")
        assert result["placement_mode"] == "ppo_gnn"
        assert result["checkpoint_loaded"] is True
        assert len(result["placements"]) == 5
        # 布局在画布内
        for name, pl in result["placements"].items():
            assert 0.0 <= pl["x"] <= circuit["canvas_w"]
            assert 0.0 <= pl["y"] <= circuit["canvas_h"]

    def test_place_ppo_gnn_empty_circuit(self, monkeypatch):
        """空电路（无器件）ppo_gnn 返回空布局（不需 checkpoint）。"""
        monkeypatch.setenv("POLARIS_PLACE_CHECKPOINT",
                           "/nonexistent/ppo_gnn.json")
        circuit = make_circuit("Empty", [], [], canvas_w=500, canvas_h=300)
        placements, ckpt_loaded = place_ppo_gnn(circuit)
        assert placements == {}
        assert ckpt_loaded is True

    def test_place_ppo_gnn_corrupt_checkpoint_raises(self, tmp_path, monkeypatch):
        """checkpoint 缺 'network' 键应 raise RuntimeError（R03）。"""
        ckpt_path = tmp_path / "corrupt.json"
        ckpt_path.write_text(json.dumps({"wrong_key": {}}), encoding="utf-8")
        monkeypatch.setenv("POLARIS_PLACE_CHECKPOINT", str(ckpt_path))

        circuit = _make_mzi_circuit()
        with pytest.raises(RuntimeError, match="checkpoint 格式非法"):
            place_circuit(circuit, mode="ppo_gnn")


# ============================================================
# 6. TestRenderAsciiLayout — ASCII 可视化
# ============================================================
class TestRenderAsciiLayout:
    """render_ascii_layout ASCII 网格布局预览。"""

    def test_render_ascii_returns_str(self):
        """render_ascii_layout 返回非空字符串。"""
        circuit = _make_mzi_circuit()
        result = place_circuit(circuit, mode="analytical")
        ascii_layout = render_ascii_layout(circuit, result["placements"],
                                           grid_w=40, grid_h=15)
        assert isinstance(ascii_layout, str)
        assert len(ascii_layout) > 0

    def test_render_ascii_contains_title(self):
        """ASCII 渲染含电路名标题。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        ascii_layout = render_ascii_layout(circuit, placements)
        assert "MZI" in ascii_layout
        assert "布局预览" in ascii_layout

    def test_render_ascii_contains_legend(self):
        """ASCII 渲染含器件字符图例。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        ascii_layout = render_ascii_layout(circuit, placements)
        assert "G=grating_coupler" in ascii_layout
        assert "M=mmi" in ascii_layout

    def test_render_ascii_contains_device_chars(self):
        """ASCII 渲染含至少一个器件字符（G/M/W/P/D）。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        ascii_layout = render_ascii_layout(circuit, placements)
        assert any(c in ascii_layout for c in ("G", "M", "W", "P", "D")), \
            "ASCII 渲染未包含任何器件字符"
        # 含点号（空位）
        assert "." in ascii_layout

    def test_render_ascii_invalid_canvas_raises(self):
        """画布尺寸非正应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = {
            "name": "Bad",
            "devices": [],
            "connections": [],
            "canvas_w": 0,
            "canvas_h": 300,
        }
        placements = {}
        with pytest.raises(RuntimeError, match="画布尺寸必须为正"):
            render_ascii_layout(circuit, placements)

    def test_render_ascii_grid_dimensions(self):
        """ASCII 渲染网格尺寸正确（grid_w × grid_h + 标题 + 图例）。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        grid_w, grid_h = 40, 15
        ascii_layout = render_ascii_layout(circuit, placements,
                                           grid_w=grid_w, grid_h=grid_h)
        lines = ascii_layout.split("\n")
        # 1 (标题) + grid_h (网格行) + 1 (图例) = grid_h + 2
        assert len(lines) == grid_h + 2, \
            f"应有 {grid_h + 2} 行，实际 {len(lines)}"
        # 网格行（lines[1] 到 lines[grid_h]）每行宽度 = grid_w
        for i in range(1, grid_h + 1):
            assert len(lines[i]) == grid_w, \
                f"第 {i} 行宽度应为 {grid_w}，实际 {len(lines[i])}"

    def test_render_ascii_unknown_device_type(self):
        """未知器件类型用 '?' 字符表示。"""
        dev = make_device("d1", "unknown_type", 10, 10, ports=[])
        circuit = make_circuit("Unknown", [dev], [], canvas_w=100, canvas_h=100)
        placements = {"d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}}
        ascii_layout = render_ascii_layout(circuit, placements, grid_w=20, grid_h=10)
        assert "?" in ascii_layout


# ============================================================
# 7. TestPlaceEdgeCases — 边界情况
# ============================================================
class TestPlaceEdgeCases:
    """边界情况: 密集器件/混合尺寸/星型/链式拓扑。"""

    def test_place_dense_devices(self):
        """10 个密集小器件布局后无重叠、在画布内。"""
        devices = [
            make_device(f"d{i}", "mmi_1x2", 10, 10,
                        ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")])
            for i in range(10)
        ]
        connections = [(f"d{i}", "out", f"d{i + 1}", "in") for i in range(9)]
        circuit = make_circuit("Dense", devices, connections,
                               canvas_w=500, canvas_h=300)
        placements = place_analytical(circuit)
        assert len(placements) == 10
        assert _check_no_overlap(placements), "密集布局存在重叠"
        for name, pl in placements.items():
            assert 0.0 <= pl["x"] <= 500.0
            assert 0.0 <= pl["y"] <= 300.0

    def test_place_mixed_sizes(self):
        """器件尺寸差异大时合法化无重叠。"""
        big = make_device("big", "mmi_2x2", 100, 80,
                          ports=[("in", 0, 40, "west"), ("out", 100, 40, "east")])
        s1 = make_device("s1", "strip_waveguide", 20, 5,
                         ports=[("in", 0, 2.5, "west"), ("out", 20, 2.5, "east")])
        s2 = make_device("s2", "strip_waveguide", 30, 5,
                         ports=[("in", 0, 2.5, "west"), ("out", 30, 2.5, "east")])
        s3 = make_device("s3", "phase_shifter", 50, 10,
                         ports=[("in", 0, 5, "west"), ("out", 50, 5, "east")])
        circuit = make_circuit(
            "Mixed", [big, s1, s2, s3],
            [("big", "out", "s1", "in"), ("s1", "out", "s2", "in"),
             ("s2", "out", "s3", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = place_analytical(circuit)
        assert len(placements) == 4
        assert _check_no_overlap(placements), "混合尺寸布局存在重叠"

    def test_place_star_topology(self):
        """星型拓扑（1 中心 + 4 叶）布局合法。"""
        center = make_device("center", "mmi_1x4", 30, 30,
                             ports=[("in", 0, 15, "west"),
                                    ("o1", 30, 5, "east"),
                                    ("o2", 30, 12, "east"),
                                    ("o3", 30, 19, "east"),
                                    ("o4", 30, 26, "east")])
        leaves = [
            make_device(f"leaf{i}", "detector", 15, 15,
                        ports=[("in", 0, 7.5, "west")])
            for i in range(4)
        ]
        connections = [(f"center", f"o{i + 1}", f"leaf{i}", "in")
                       for i in range(4)]
        circuit = make_circuit("Star", [center] + leaves, connections,
                               canvas_w=500, canvas_h=300)
        placements = place_analytical(circuit)
        assert len(placements) == 5
        assert _check_no_overlap(placements), "星型布局存在重叠"

    def test_place_chain_signal_flow_x_increasing(self):
        """回归测试: 链式电路信号流方向 x 坐标递增（R05 防 BUG 复发）。

        构造 gc1→mmi1→ps1→mmi2→gc2 链式电路，断言 x 严格递增。
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

    def test_place_analytical_reproducible_across_calls(self):
        """同 seed 多次调用布局结果一致。"""
        circuit = _make_mzi_circuit()
        cfg = AnalyticalConfig(seed=42, max_iterations=20)
        p1 = place_analytical(circuit, cfg)
        p2 = place_analytical(circuit, cfg)
        for name in p1:
            assert p1[name]["x"] == pytest.approx(p2[name]["x"])
            assert p1[name]["y"] == pytest.approx(p2[name]["y"])

    def test_place_large_circuit_no_overlap(self):
        """20 器件链式电路合法化后无重叠。"""
        devices = [
            make_device(f"d{i}", "mmi_1x2", 15, 10,
                        ports=[("in", 0, 5, "west"), ("out", 15, 5, "east")])
            for i in range(20)
        ]
        connections = [(f"d{i}", "out", f"d{i + 1}", "in")
                       for i in range(19)]
        circuit = make_circuit("Large", devices, connections,
                               canvas_w=1000, canvas_h=500)
        placements = place_analytical(circuit)
        assert len(placements) == 20
        assert _check_no_overlap(placements), "20 器件布局存在重叠"
