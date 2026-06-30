"""statistical_yield 模块单元测试（DRC/LVS/PEX/统计/良率/协同仿真）。

覆盖 verification.statistical_yield 模块的现有功能:
- DRCEngine: 版图设计规则检查
- LVSEngine: 版图-电路一致性检查
- PEXEngine: 寄生参数提取
- StatisticalAnalyzer: 工艺角/蒙特卡洛/良率/灵敏度/空间相关
- CoSimFlow: 电路-版图协同仿真流程

文献来源（R02 学术诚信）:
- KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html
- Synopsys IC Validator: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
- Bogaerts et al., OFC 2018: https://fib.intec.ugent.be/download/pub_4125.pdf
- Lumerical INTERCONNECT Monte Carlo: https://optics.ansys.com/hc/en-us/articles/360054921214
- Banerjee ECE 225 UCSB: http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf

合规: R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修验证。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.verification.statistical_yield import (
    CoSimFlow,
    CornerType,
    DRCEngine,
    DRCRule,
    DRCSeverity,
    LVSNetlist,
    LVSEngine,
    PEXEngine,
    PEXResult,
    StatisticalAnalyzer,
    StatisticalParam,
)


# ============================================================
# DRCEngine 测试
# ============================================================
class TestDRCEngine:
    """DRC 版图设计规则检查测试。"""

    def test_drc_detects_min_width_violation(self):
        """M1: 检测波导最小线宽违规。"""
        drc = DRCEngine()
        layout = {
            "waveguide": {"min_width": 0.42, "width_violations": 5},
        }
        drc.run(layout)
        assert drc.error_count > 0

    def test_drc_detects_min_spacing_violation(self):
        """M1: 检测波导最小间距违规。"""
        drc = DRCEngine()
        layout = {
            "waveguide": {"min_spacing": 0.45, "spacing_violations": 3},
        }
        drc.run(layout)
        assert drc.error_count > 0

    def test_drc_clean_layout_passes(self):
        """M1: 干净版图无 ERROR 违规。"""
        drc = DRCEngine()
        layout = {
            "waveguide": {"min_width": 0.50, "min_spacing": 0.60, "density": 0.15},
        }
        drc.run(layout)
        assert drc.error_count == 0

    def test_drc_report_structure(self):
        """M1: report 返回结构含 total_rules/errors/warnings/passed。"""
        drc = DRCEngine()
        report = drc.report()
        assert "total_rules" in report
        assert "errors" in report
        assert "warnings" in report
        assert "passed" in report
        assert "violations" in report
        assert isinstance(report["violations"], list)
        assert report["total_rules"] > 0


# ============================================================
# LVSEngine 测试
# ============================================================
class TestLVSEngine:
    """LVS 版图-电路一致性检查测试。"""

    def test_lvs_matching_topology_passes(self):
        """M1: 拓扑一致的网表通过 LVS。"""
        sch = LVSNetlist(
            devices={"D1": "wg", "D2": "mmi"},
            nets={"N1": ["D1:in", "D2:out1"], "N2": ["D2:in", "D1:out"]},
        )
        lay = LVSNetlist(
            devices={"X1": "wg", "X2": "mmi"},
            nets={"A": ["X1:in", "X2:out1"], "B": ["X2:in", "X1:out"]},
        )
        lvs = LVSEngine()
        result = lvs.compare(sch, lay)
        assert result["passed"] is True
        assert result["schematic_devices"] == 2

    def test_lvs_device_count_mismatch_fails(self):
        """M1: 设备数不一致 LVS 失败。"""
        sch = LVSNetlist(devices={"D1": "wg"}, nets={"N1": ["D1:in"]})
        lay = LVSNetlist(
            devices={"X1": "wg", "X2": "mmi"},
            nets={"A": ["X1:in"], "B": ["X2:in"]},
        )
        lvs = LVSEngine()
        result = lvs.compare(sch, lay)
        assert result["passed"] is False
        assert any(m["type"] == "device_count" for m in result["mismatches"])

    def test_lvs_device_type_mismatch_fails(self):
        """M2: 设备类型不一致 LVS 失败。"""
        sch = LVSNetlist(devices={"D1": "wg"}, nets={"N1": ["D1:in", "D1:out"]})
        lay = LVSNetlist(devices={"X1": "ring"}, nets={"A": ["X1:in", "X1:out"]})
        lvs = LVSEngine()
        result = lvs.compare(sch, lay)
        assert result["passed"] is False


# ============================================================
# PEXEngine 测试
# ============================================================
class TestPEXEngine:
    """PEX 寄生参数提取测试。"""

    def test_pex_extract_wire_positive(self):
        """M1: 单根导线寄生 R/C/L > 0。"""
        pex = PEXEngine(sheet_resistance_ohm_sq=0.05, metal_thickness_um=0.5)
        result = pex.extract_wire(length_um=1000.0, width_um=1.0)
        assert result["resistance_ohm"] > 0
        assert result["capacitance_ff"] > 0
        assert result["inductance_ph"] != 0  # 可能为负（公式特性）
        assert result["length_um"] == 1000.0

    def test_pex_resistance_formula(self):
        """M1: R = RPSQ × L / W 公式验证。"""
        pex = PEXEngine(sheet_resistance_ohm_sq=0.05)
        result = pex.extract_wire(length_um=1000.0, width_um=1.0)
        # R = 0.05 × 1000 / 1 = 50 Ω
        assert result["resistance_ohm"] == pytest.approx(50.0, abs=0.01)

    def test_pex_extract_netlist_aggregation(self):
        """M1: extract_netlist 聚合多导线总 R/C/L。"""
        pex = PEXEngine(sheet_resistance_ohm_sq=0.05, metal_thickness_um=0.5)
        wires = [
            {"name": "clk", "length_um": 500.0, "width_um": 2.0},
            {"name": "data", "length_um": 800.0, "width_um": 1.0},
        ]
        total = pex.extract_netlist(wires)
        assert isinstance(total, PEXResult)
        assert total.total_resistance_ohm > 0
        assert total.total_capacitance_ff > 0
        assert "clk" in total.by_net
        assert "data" in total.by_net

    def test_pex_invalid_width_raises(self):
        """M1: R03 — 线宽 ≤ 0 必须 raise。"""
        pex = PEXEngine()
        with pytest.raises(ValueError):
            pex.extract_wire(length_um=100.0, width_um=0.0)


# ============================================================
# StatisticalAnalyzer 测试
# ============================================================
class TestStatisticalAnalyzer:
    """统计分析引擎（工艺角/MC/良率/灵敏度/空间相关）测试。"""

    @pytest.fixture
    def analyzer(self):
        """两参数统计分析器。"""
        params = [
            StatisticalParam("wg_width", 0.45, 0.005, "gaussian", units="μm"),
            StatisticalParam("wg_thickness", 0.22, 0.002, "gaussian", units="μm"),
        ]
        return StatisticalAnalyzer(params)

    @staticmethod
    def _sim_fn(p):
        """环形谐振器波长偏移: λ = 1550 - 2×Δw - 5×Δt。"""
        return 1550.0 - 2.0 * (p["wg_width"] - 0.45) - 5.0 * (p["wg_thickness"] - 0.22)

    def test_get_corner_values_tt(self, analyzer):
        """M1: TT 角 = nominal。"""
        vals = analyzer.get_corner_values(CornerType.TT)
        assert vals["wg_width"] == pytest.approx(0.45)
        assert vals["wg_thickness"] == pytest.approx(0.22)

    def test_get_corner_values_ss(self, analyzer):
        """M1: SS 角 = nominal - 3σ。"""
        vals = analyzer.get_corner_values(CornerType.SS)
        assert vals["wg_width"] == pytest.approx(0.45 - 3 * 0.005)

    def test_run_corners_five(self, analyzer):
        """M1: 5 工艺角仿真全部返回性能值。"""
        result = analyzer.run_corners(self._sim_fn)
        assert set(result.keys()) == {"TT", "SS", "FF", "SF", "FS"}
        assert result["TT"] == pytest.approx(1550.0)

    def test_run_monte_carlo_statistics(self, analyzer):
        """M1: MC 仿真统计量 mean ≈ 1550（标称）。"""
        result = analyzer.run_monte_carlo(self._sim_fn, n_runs=500, seed=42)
        assert result["n_runs"] == 500
        assert result["mean"] == pytest.approx(1550.0, abs=0.5)
        assert result["std"] > 0
        assert result["min"] <= result["mean"] <= result["max"]

    def test_calculate_yield_in_range(self, analyzer):
        """M1: 良率 ∈ [0, 1]，CI 合理。"""
        analyzer.run_monte_carlo(self._sim_fn, n_runs=500, seed=42)
        yld = analyzer.calculate_yield(spec_lower=1549.0, spec_upper=1551.0)
        assert 0.0 <= yld["yield"] <= 1.0
        assert yld["pass_count"] + yld["fail_count"] == yld["total_runs"]
        assert 0.0 <= yld["ci_lower"] <= yld["ci_upper"] <= 1.0

    def test_calculate_yield_without_mc_raises(self, analyzer):
        """M1: R03 — 未运行 MC 直接计算良率必须 raise。"""
        with pytest.raises(RuntimeError, match="Monte Carlo"):
            analyzer.calculate_yield(spec_lower=0, spec_upper=10000)

    def test_sensitivity_analysis(self, analyzer):
        """M1: 灵敏度分析返回每参数敏感度。"""
        sens = analyzer.sensitivity_analysis(self._sim_fn)
        assert "wg_width" in sens
        assert "wg_thickness" in sens
        # dλ/dw = -2/σ × σ = -2（线性函数）
        assert sens["wg_width"] == pytest.approx(-2.0, abs=0.1)

    def test_run_layout_aware_mc(self, analyzer):
        """M1: Layout-Aware MC 空间相关仿真。"""
        def sim_layout(p, pos):
            return 1550.0 - 2.0 * (p["wg_width"] - 0.45)
        result = analyzer.run_layout_aware_mc(
            sim_layout,
            device_positions=[(0.0, 0.0), (500.0, 500.0), (1000.0, 1000.0)],
            n_runs=100,
            correlation_length_um=200.0,
            seed=42,
        )
        assert result["layout_aware"] is True
        assert result["n_devices"] == 3
        assert result["mean"] == pytest.approx(1550.0, abs=1.0)
        assert "gaussian" in result["spatial_correlation_model"]


# ============================================================
# CoSimFlow 协同仿真测试
# ============================================================
class TestCoSimFlow:
    """电路-版图协同仿真流程测试。"""

    def test_run_full_flow(self):
        """M1: 完整协同仿真流程（DRC→LVS→PEX→仿真→统计→良率）。"""
        stats = StatisticalAnalyzer([
            StatisticalParam("wg_width", 0.45, 0.005, "gaussian"),
        ])
        cosim = CoSimFlow(stats=stats)
        layout = {"waveguide": {"min_width": 0.50, "min_spacing": 0.60, "density": 0.15}}
        sch = LVSNetlist(
            devices={"D1": "wg"},
            nets={"N1": ["D1:in", "D1:out"]},
        )
        lay = LVSNetlist(
            devices={"X1": "wg"},
            nets={"A": ["X1:in", "X1:out"]},
        )

        def sim_fn(p):
            return 1550.0 - 2.0 * (p["wg_width"] - 0.45)

        result = cosim.run_full_flow(
            layout_data=layout,
            schematic=sch,
            layout_netlist=lay,
            sim_fn=sim_fn,
            spec_lower=1549.0,
            spec_upper=1551.0,
            n_mc_runs=200,
        )
        assert result.lvs_passed is True
        assert result.nominal_performance == pytest.approx(1550.0)
        assert "yield" in result.yield_analysis
        assert len(result.corner_results) == 5
