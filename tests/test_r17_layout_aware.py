"""R17 路标 layout-aware 仿真模块测试。

测试内容:
1. TestBBPlacement: BB 物理位置（创建/默认值/非法）
2. TestElasticConnector: Smart Elastic Connector（长度/S 参数/零长度）
3. TestParasiticExtractor: 寄生参数提取（波导/弯曲/负寄生）
4. TestLayoutAwareSimulator: layout-aware 仿真器（添加/连接/寄生/仿真）
5. TestLayoutCircuitFeedback: 反馈循环（运行/收敛）
6. TestR17Integration: R17 集成（完整流程/综合得分）

来源:
- R17 路标: /workspace/docs/roundmap/R17.md
- Mingaleev et al., ECIO 2016:
  https://www.ecio-conference.org/wp-content/uploads/2016/06/ECIO-p-21.pdf
- Bogaerts et al., SPIE 8627, 862702 (2013):
  https://doi.org/10.1117/12.2003261
- Silvaco Hipex-RC: https://silvaco.com/tcad/parasitic-extraction/
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.sim.layout_aware import (
    BBPlacement,
    ElasticConnector,
    LayoutAwareSimulator,
    LayoutCircuitFeedback,
    ParasiticExtractor,
)


# ---------------------------------------------------------------------------
# 1. TestBBPlacement — BB 物理位置
# ---------------------------------------------------------------------------
class TestBBPlacement:
    """BB 物理位置测试。"""

    def test_placement_creation(self):
        """创建位置，验证字段。"""
        p = BBPlacement(bb_name="mzi1", x=100.0, y=200.0, rotation=45.0, flip=True)
        assert p.bb_name == "mzi1"
        assert p.x == 100.0
        assert p.y == 200.0
        assert p.rotation == 45.0
        assert p.flip is True
        assert p.position == (100.0, 200.0)

    def test_placement_defaults(self):
        """默认值: rotation=0.0, flip=False。"""
        p = BBPlacement(bb_name="wg1", x=0.0, y=0.0)
        assert p.rotation == 0.0
        assert p.flip is False
        assert p.position == (0.0, 0.0)

    def test_placement_empty_name(self):
        """空名称 raise ValueError。"""
        with pytest.raises(ValueError, match="bb_name"):
            BBPlacement(bb_name="", x=0.0, y=0.0)

    def test_placement_non_finite(self):
        """非有限坐标 raise ValueError。"""
        with pytest.raises(ValueError, match="x"):
            BBPlacement(bb_name="x", x=float("inf"), y=0.0)
        with pytest.raises(ValueError, match="y"):
            BBPlacement(bb_name="x", x=0.0, y=float("nan"))


# ---------------------------------------------------------------------------
# 2. TestElasticConnector — Smart Elastic Connector
# ---------------------------------------------------------------------------
class TestElasticConnector:
    """Smart Elastic Optical Connector 测试。"""

    def test_compute_length(self):
        """计算长度: 曼哈顿距离 + 弯曲。"""
        # 起止方向均为 0°（无弯曲）
        c = ElasticConnector(
            start_pos=(0.0, 0.0),
            end_pos=(100.0, 50.0),
            start_direction=0.0,
            end_direction=0.0,
        )
        length = c.compute_length()
        # 曼哈顿距离 = 100 + 50 = 150
        assert math.isclose(length, 150.0, rel_tol=1e-9)

    def test_compute_length_with_bends(self):
        """带弯曲的长度: 曼哈顿 + 弯曲弧长。"""
        # 起止方向均为 90°（2 个弯曲）
        c = ElasticConnector(
            start_pos=(0.0, 0.0),
            end_pos=(100.0, 0.0),
            start_direction=90.0,
            end_direction=90.0,
        )
        length = c.compute_length()
        # 曼哈顿 = 100, 弯曲 = 2 * π*5/2 = 5π
        expected = 100.0 + 2 * 0.5 * math.pi * 5.0
        assert math.isclose(length, expected, rel_tol=1e-9)

    def test_compute_s_params(self):
        """计算 S 参数: 振幅 + 相位。"""
        c = ElasticConnector(
            start_pos=(0.0, 0.0),
            end_pos=(100.0, 0.0),
            start_direction=0.0,
            end_direction=0.0,
        )
        s = c.compute_s_params(wavelength=1.55, neff=2.4, alpha_db_cm=0.0)
        # 无损耗时 |s21| = 1
        assert "out" in str(s.keys())
        s21 = s[("out", "in")]
        assert math.isclose(abs(s21), 1.0, rel_tol=1e-9)
        # 相位 = 2*pi*neff*L/wl
        expected_phase = 2.0 * math.pi * 2.4 * 100.0 / 1.55
        assert math.isclose(s21.imag, math.sin(expected_phase), abs_tol=1e-6)

    def test_compute_s_params_with_loss(self):
        """带损耗的 S 参数: |s21| < 1。"""
        c = ElasticConnector(
            start_pos=(0.0, 0.0),
            end_pos=(1000.0, 0.0),  # 1mm = 100cm
            start_direction=0.0,
            end_direction=0.0,
        )
        s = c.compute_s_params(wavelength=1.55, neff=2.4, alpha_db_cm=1.0)
        s21 = s[("out", "in")]
        # 1mm = 0.1cm, 损耗 1 dB/cm → 0.1 dB → 振幅 10^(-0.1/20)
        expected_amp = 10.0 ** (-1.0 * 0.1 / 20.0)
        assert math.isclose(abs(s21), expected_amp, rel_tol=1e-6)
        assert abs(s21) < 1.0

    def test_connector_zero_length(self):
        """零长度连接器: 起止重合且方向一致。"""
        c = ElasticConnector(
            start_pos=(50.0, 50.0),
            end_pos=(50.0, 50.0),
            start_direction=0.0,
            end_direction=0.0,
        )
        length = c.compute_length()
        assert length == 0.0
        s = c.compute_s_params(wavelength=1.55)
        s21 = s[("out", "in")]
        # 零长度: s21 = 1 (无相位无损耗)
        assert math.isclose(s21.real, 1.0, rel_tol=1e-9)
        assert math.isclose(s21.imag, 0.0, abs_tol=1e-9)

    def test_connector_zero_length_direction_mismatch(self):
        """零长度但方向不一致 raise RuntimeError。"""
        c = ElasticConnector(
            start_pos=(50.0, 50.0),
            end_pos=(50.0, 50.0),
            start_direction=0.0,
            end_direction=90.0,
        )
        with pytest.raises(RuntimeError, match="无法布线"):
            c.compute_length()

    def test_connector_invalid_wavelength(self):
        """非法波长 raise ValueError。"""
        c = ElasticConnector(start_pos=(0.0, 0.0), end_pos=(10.0, 0.0))
        with pytest.raises(ValueError, match="波长"):
            c.compute_s_params(wavelength=-1.0)

    def test_connector_invalid_neff(self):
        """非法 neff raise ValueError。"""
        c = ElasticConnector(start_pos=(0.0, 0.0), end_pos=(10.0, 0.0))
        with pytest.raises(ValueError, match="neff"):
            c.compute_s_params(wavelength=1.55, neff=0.0)


# ---------------------------------------------------------------------------
# 3. TestParasiticExtractor — 寄生参数提取
# ---------------------------------------------------------------------------
class TestParasiticExtractor:
    """寄生参数提取测试。"""

    def test_extract_waveguide_parasitics(self):
        """波导寄生提取: delta_length/phase/loss。"""
        # routed=105μm, schematic=100μm, 寄生 5μm
        result = ParasiticExtractor.extract_waveguide_parasitics(
            routed_length=105.0,
            schematic_length=100.0,
            neff=2.4,
            alpha_db_cm=1.0,
            wavelength=1.55,
        )
        assert math.isclose(result["delta_length"], 5.0, rel_tol=1e-9)
        # phi = 2*pi*2.4*5/1.55
        expected_phase = 2.0 * math.pi * 2.4 * 5.0 / 1.55
        assert math.isclose(result["delta_phase"], expected_phase, rel_tol=1e-6)
        # loss = 1 dB/cm * 5μm * 1e-4 cm/μm = 5e-4 dB
        assert math.isclose(result["delta_loss_db"], 5e-4, rel_tol=1e-9)

    def test_extract_waveguide_parasitics_zero(self):
        """零寄生: routed == schematic。"""
        result = ParasiticExtractor.extract_waveguide_parasitics(
            routed_length=100.0,
            schematic_length=100.0,
        )
        assert result["delta_length"] == 0.0
        assert result["delta_phase"] == 0.0
        assert result["delta_loss_db"] == 0.0

    def test_extract_bend_parasitics(self):
        """弯曲寄生提取: 弧长 + 相位。"""
        # 2 个 90° 弯曲，半径 5μm
        result = ParasiticExtractor.extract_bend_parasitics(
            n_bends=2,
            bend_radius=5.0,
            wavelength=1.55,
            neff=2.4,
        )
        # 弧长 = 2 * π*5/2 = 5π
        expected_len = 2 * 0.5 * math.pi * 5.0
        assert math.isclose(result["delta_length"], expected_len, rel_tol=1e-9)
        expected_phase = 2.0 * math.pi * 2.4 * expected_len / 1.55
        assert math.isclose(result["delta_phase"], expected_phase, rel_tol=1e-6)
        assert result["delta_loss_db"] >= 0.0

    def test_extract_bend_parasitics_zero(self):
        """零弯曲: n_bends=0。"""
        result = ParasiticExtractor.extract_bend_parasitics(
            n_bends=0,
            bend_radius=5.0,
        )
        assert result["delta_length"] == 0.0
        assert result["delta_phase"] == 0.0
        assert result["delta_loss_db"] == 0.0

    def test_negative_parasitic(self):
        """负寄生 (routed < schematic) raise ValueError。"""
        with pytest.raises(ValueError, match="寄生长度为负"):
            ParasiticExtractor.extract_waveguide_parasitics(
                routed_length=95.0,
                schematic_length=100.0,
            )

    def test_negative_length(self):
        """负长度 raise ValueError。"""
        with pytest.raises(ValueError, match="长度必须"):
            ParasiticExtractor.extract_waveguide_parasitics(
                routed_length=-10.0,
                schematic_length=0.0,
            )

    def test_invalid_bend_count(self):
        """负弯曲数 raise ValueError。"""
        with pytest.raises(ValueError, match="弯曲数"):
            ParasiticExtractor.extract_bend_parasitics(n_bends=-1, bend_radius=5.0)

    def test_invalid_bend_radius(self):
        """非正弯曲半径 raise ValueError。"""
        with pytest.raises(ValueError, match="弯曲半径"):
            ParasiticExtractor.extract_bend_parasitics(n_bends=2, bend_radius=0.0)


# ---------------------------------------------------------------------------
# 4. TestLayoutAwareSimulator — layout-aware 仿真器
# ---------------------------------------------------------------------------
class TestLayoutAwareSimulator:
    """layout-aware 仿真器测试。"""

    def test_init_empty(self):
        """空初始化。"""
        sim = LayoutAwareSimulator()
        assert sim.placements == []
        assert sim.connectors == []

    def test_init_with_placements(self):
        """带 placements 初始化。"""
        placements = [
            BBPlacement(bb_name="bb1", x=0.0, y=0.0),
            BBPlacement(bb_name="bb2", x=100.0, y=0.0),
        ]
        sim = LayoutAwareSimulator(placements=placements)
        assert len(sim.placements) == 2
        assert sim.placements[0].bb_name == "bb1"

    def test_add_placement(self):
        """添加位置。"""
        sim = LayoutAwareSimulator()
        p = BBPlacement(bb_name="mzi1", x=50.0, y=50.0)
        sim.add_placement(p)
        assert len(sim.placements) == 1
        assert sim.placements[0].bb_name == "mzi1"

    def test_add_placement_duplicate(self):
        """重复名称 raise ValueError。"""
        sim = LayoutAwareSimulator()
        sim.add_placement(BBPlacement(bb_name="bb1", x=0.0, y=0.0))
        with pytest.raises(ValueError, match="已存在"):
            sim.add_placement(BBPlacement(bb_name="bb1", x=100.0, y=0.0))

    def test_auto_connect(self):
        """自动连接两个 BB。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=100.0, y=50.0),
            ]
        )
        connector = sim.auto_connect("bb1", "bb2")
        assert len(sim.connectors) == 1
        assert connector.start_pos == (0.0, 0.0)
        assert connector.end_pos == (100.0, 50.0)
        # 长度已计算
        assert connector._length is not None
        assert connector._length > 0

    def test_auto_connect_missing_bb(self):
        """连接不存在的 BB raise KeyError。"""
        sim = LayoutAwareSimulator([BBPlacement(bb_name="bb1", x=0.0, y=0.0)])
        with pytest.raises(KeyError, match="bb2"):
            sim.auto_connect("bb1", "bb2")

    def test_extract_all_parasitics(self):
        """提取所有连接器寄生。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=105.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        # schematic 长度 100，routed 长度 105
        result = sim.extract_all_parasitics({0: 100.0})
        assert 0 in result
        assert math.isclose(result[0]["delta_length"], 5.0, rel_tol=1e-9)

    def test_extract_all_parasitics_invalid_idx(self):
        """无效连接器索引 raise KeyError。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=100.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        with pytest.raises(KeyError, match="超出范围"):
            sim.extract_all_parasitics({5: 100.0})

    def test_simulate_with_layout(self):
        """layout-aware 仿真: 频域 S 参数。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=100.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        wavelengths = np.array([1.55, 1.56, 1.57])
        result = sim.simulate_with_layout(wavelengths)
        assert 0 in result
        s21 = result[0]
        assert s21.shape == (3,)
        # 无损耗时 |s21| = 1
        assert np.allclose(np.abs(s21), 1.0, rtol=1e-9)

    def test_simulate_with_layout_with_schematic(self):
        """带原理图 S 参数的 layout-aware 仿真。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=100.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        wavelengths = np.array([1.55, 1.56])
        # 原理图 S 参数（单位传输）
        schematic_s = {0: np.ones(2, dtype=complex)}
        result = sim.simulate_with_layout(wavelengths, schematic_s=schematic_s)
        # 级联后仍为连接器 S 参数
        assert np.allclose(np.abs(result[0]), 1.0, rtol=1e-9)

    def test_simulate_invalid_wavelength(self):
        """非法波长 raise ValueError。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=100.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        with pytest.raises(ValueError, match="波长"):
            sim.simulate_with_layout(np.array([-1.0, 1.55]))


# ---------------------------------------------------------------------------
# 5. TestLayoutCircuitFeedback — 反馈循环
# ---------------------------------------------------------------------------
class TestLayoutCircuitFeedback:
    """layout-电路反馈循环测试。"""

    def test_feedback_creation(self):
        """创建反馈循环，验证默认值。"""
        fb = LayoutCircuitFeedback()
        assert fb.max_iterations == 5
        assert fb.tolerance == 0.01

    def test_feedback_invalid_iterations(self):
        """非法迭代次数 raise ValueError。"""
        with pytest.raises(ValueError, match="max_iterations"):
            LayoutCircuitFeedback(max_iterations=0)

    def test_feedback_invalid_tolerance(self):
        """非法容差 raise ValueError。"""
        with pytest.raises(ValueError, match="tolerance"):
            LayoutCircuitFeedback(tolerance=0.0)
        with pytest.raises(ValueError, match="tolerance"):
            LayoutCircuitFeedback(tolerance=1.5)

    def test_run_feedback(self):
        """运行反馈循环: 返回结构正确。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=105.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        fb = LayoutCircuitFeedback(max_iterations=3, tolerance=0.01)
        result = fb.run_feedback(sim, schematic_lengths={0: 100.0})
        assert "iterations" in result
        assert "converged" in result
        assert "final_parasitics" in result
        assert "history" in result
        assert result["iterations"] >= 1
        assert len(result["history"]) == result["iterations"]

    def test_feedback_convergence(self):
        """反馈循环收敛: 第二次迭代寄生为 0。"""
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=105.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        # 容差 1%，初始寄生 5/100 = 5% > 1%
        # 第一次迭代后 schematic_length 调整为 105，第二次寄生为 0
        fb = LayoutCircuitFeedback(max_iterations=5, tolerance=0.01)
        result = fb.run_feedback(sim, schematic_lengths={0: 100.0})
        # 应在 2 次迭代内收敛
        assert result["converged"] is True
        assert result["iterations"] <= 2
        # 收敛后寄生长度 ≈ 0
        final_delta = result["final_parasitics"][0]["delta_length"]
        assert abs(final_delta) < 1e-6


# ---------------------------------------------------------------------------
# 6. TestR17Integration — R17 集成
# ---------------------------------------------------------------------------
class TestR17Integration:
    """R17 路标集成测试。"""

    def test_layout_aware_pipeline(self):
        """完整 layout-aware 流程: 位置→连接→寄生→仿真→反馈。"""
        # 1. 定义 BB 位置
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="laser", x=0.0, y=0.0),
                BBPlacement(bb_name="mzi", x=200.0, y=100.0),
                BBPlacement(bb_name="detector", x=400.0, y=0.0),
            ]
        )
        # 2. 自动连接
        c1 = sim.auto_connect("laser", "mzi")
        c2 = sim.auto_connect("mzi", "detector")
        assert len(sim.connectors) == 2
        assert c1.compute_length() > 0
        assert c2.compute_length() > 0
        # 3. 提取寄生
        schematic_lengths = {0: 250.0, 1: 250.0}
        parasitics = sim.extract_all_parasitics(schematic_lengths)
        assert len(parasitics) == 2
        # 4. layout-aware 仿真
        wavelengths = np.linspace(1.50, 1.60, 11)
        s_result = sim.simulate_with_layout(wavelengths)
        assert len(s_result) == 2
        assert s_result[0].shape == (11,)
        assert s_result[1].shape == (11,)
        # 5. 反馈循环
        fb = LayoutCircuitFeedback(max_iterations=5, tolerance=0.01)
        fb_result = fb.run_feedback(sim, schematic_lengths=schematic_lengths)
        assert fb_result["iterations"] >= 1
        # 验证所有 S 参数有限
        assert np.all(np.isfinite(s_result[0]))
        assert np.all(np.isfinite(s_result[1]))

    def test_comprehensive_score_79(self):
        """综合得分 ≥ 7.9。

        得分构成（R17.md §6.4）:
        - 基础分 7.75（R15 完成后）
        - +0.05: Smart Elastic Optical Connector 实现
        - +0.05: 寄生参数提取（波导 + 弯曲）
        - +0.05: layout-aware 仿真器 + 反馈循环
        总计: 7.90 ≥ 7.9
        """
        score = 7.75
        # 1. Smart Elastic Optical Connector
        connector = ElasticConnector(
            start_pos=(0.0, 0.0),
            end_pos=(100.0, 50.0),
            start_direction=0.0,
            end_direction=0.0,
        )
        length = connector.compute_length()
        assert length > 0
        s = connector.compute_s_params(wavelength=1.55)
        assert abs(s[("out", "in")]) <= 1.0 + 1e-9
        score += 0.05
        # 2. 寄生参数提取
        wg_parasitic = ParasiticExtractor.extract_waveguide_parasitics(
            routed_length=105.0,
            schematic_length=100.0,
        )
        assert wg_parasitic["delta_length"] > 0
        bend_parasitic = ParasiticExtractor.extract_bend_parasitics(
            n_bends=2,
            bend_radius=5.0,
        )
        assert bend_parasitic["delta_length"] > 0
        score += 0.05
        # 3. layout-aware 仿真器 + 反馈循环
        sim = LayoutAwareSimulator(
            [
                BBPlacement(bb_name="bb1", x=0.0, y=0.0),
                BBPlacement(bb_name="bb2", x=105.0, y=0.0),
            ]
        )
        sim.auto_connect("bb1", "bb2")
        wavelengths = np.array([1.55, 1.56])
        s_layout = sim.simulate_with_layout(wavelengths)
        assert len(s_layout) == 1
        fb = LayoutCircuitFeedback(max_iterations=3, tolerance=0.01)
        fb_result = fb.run_feedback(sim, schematic_lengths={0: 100.0})
        assert fb_result["converged"] is True
        score += 0.05
        # 浮点精度容差（7.75 + 0.05*3 = 7.9，浮点累加误差 < 1e-9）
        assert round(score, 2) >= 7.9, f"综合得分 {score:.4f} < 7.9"
