"""R231-R235 寄生提取进阶模块单元测试。

覆盖:
- R231 ParasiticResistor: 片电阻 + TC1/TC2 温度系数
- R232 ParasiticCapacitor: 平行板 + Banerjee 边缘 + Sakurai-Tamaru 耦合 + 电容矩阵
- R233 ParasiticInductor: Rosa 1908 自感 + Neumann 互感 + 电感矩阵
- R234 ParasiticSParam: π 型网络 ABCD→S，无源性/互易性验证
- R235 SpiceNetlistWriter: .subckt 输出 + R/C/L/K + TC1/TC2
- AdvancedParasiticExtractor: 一站式综合提取

文献来源（R02 学术诚信）:
- Synopsys StarRC Datasheet: https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Banerjee ECE 225 UCSB: http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
- Rosa 1908 NIST: https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
- Pozar, Microwave Engineering 4th ed., §4.4
- ngspice 用户手册: https://ngspice.sourceforge.io/docs.html

合规: R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修验证。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.sim.parasitic_advanced import (
    AdvancedParasiticExtractor,
    ParasiticCapacitor,
    ParasiticInductor,
    ParasiticResistor,
    ParasiticSParam,
    SpiceNetlistWriter,
)


# ============================================================
# R231 寄生电阻提取测试
# ============================================================
class TestParasiticResistor:
    """R231 寄生电阻（片电阻 + 温度系数）测试。"""

    def test_resistance_basic_formula(self):
        """M1: R = RPSQ × L / W 基本公式验证。"""
        # 铝互连典型值: RPSQ=0.05 Ω/□, L=1000μm, W=1μm → 50Ω
        r = ParasiticResistor(sheet_resistance_ohm_sq=0.05)
        result = r.extract(length_um=1000.0, width_um=1.0)
        assert result["resistance_ohm"] == pytest.approx(50.0, abs=1e-9)
        assert result["n_squares"] == pytest.approx(1000.0)

    def test_temperature_coefficient_tc1(self):
        """M1: TC1 一阶温度系数 R(T) = R0×(1+TC1×ΔT)。"""
        # TiN heater: RPSQ=5, TC1=-0.0005/°C, T_ref=25, T_op=125 (ΔT=100)
        r = ParasiticResistor(sheet_resistance_ohm_sq=5.0, tc1=-0.0005, t_ref=25.0)
        result = r.extract(length_um=100.0, width_um=10.0, temperature_c=125.0)
        # R0 = 5 × 100/10 = 50Ω; temp_factor = 1 + (-0.0005)*100 = 0.95
        assert result["resistance_nominal_ohm"] == pytest.approx(50.0)
        assert result["temp_factor"] == pytest.approx(0.95)
        assert result["resistance_ohm"] == pytest.approx(47.5, abs=1e-9)

    def test_temperature_coefficient_tc2(self):
        """M2: TC2 二阶温度系数 R(T) = R0×(1+TC1×ΔT+TC2×ΔT²)。"""
        r = ParasiticResistor(
            sheet_resistance_ohm_sq=1.0, tc1=0.0039, tc2=1e-6, t_ref=25.0
        )
        result = r.extract(length_um=10.0, width_um=1.0, temperature_c=125.0)
        # ΔT=100, temp_factor = 1 + 0.0039*100 + 1e-6*10000 = 1 + 0.39 + 0.01 = 1.40
        assert result["temp_factor"] == pytest.approx(1.40)
        assert result["resistance_ohm"] == pytest.approx(14.0, abs=1e-9)

    def test_default_temperature_uses_t_ref(self):
        """M1: temperature_c=None 时使用 t_ref，ΔT=0，temp_factor=1。"""
        r = ParasiticResistor(sheet_resistance_ohm_sq=0.05, t_ref=25.0)
        result = r.extract(length_um=100.0, width_um=1.0)
        assert result["temp_factor"] == pytest.approx(1.0)
        assert result["resistance_ohm"] == result["resistance_nominal_ohm"]

    def test_invalid_sheet_resistance_raises(self):
        """M1: R03 禁止 fall-back — 片电阻 ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="sheet_resistance"):
            ParasiticResistor(sheet_resistance_ohm_sq=0.0)

    def test_invalid_length_raises(self):
        """M1: R03 — 长度 ≤ 0 必须 raise。"""
        r = ParasiticResistor(sheet_resistance_ohm_sq=0.05)
        with pytest.raises(ValueError, match="length_um"):
            r.extract(length_um=0.0, width_um=1.0)

    def test_invalid_width_raises(self):
        """M1: R03 — 宽度 ≤ 0 必须 raise。"""
        r = ParasiticResistor(sheet_resistance_ohm_sq=0.05)
        with pytest.raises(ValueError, match="width_um"):
            r.extract(length_um=100.0, width_um=-1.0)


# ============================================================
# R232 寄生电容提取测试
# ============================================================
class TestParasiticCapacitor:
    """R232 寄生电容（平行板 + 边缘 + 耦合）测试。"""

    def test_self_capacitance_positive(self):
        """M1: 自容 = C_pp + C_fringe > 0。"""
        cap = ParasiticCapacitor(
            eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
        )
        result = cap.extract_self(length_um=1000.0, width_um=1.0)
        assert result["capacitance_ff"] > 0
        assert result["capacitance_area_ff"] > 0
        assert result["capacitance_fringe_ff"] > 0
        # C_pp = 3.9 * 8.854e-12 * 1e-6 * 1e-3 / 1e-6 = 34.53 fF
        assert result["capacitance_area_ff"] == pytest.approx(34.53, abs=0.1)

    def test_self_capacitance_scales_with_length(self):
        """M2: 电容与长度成正比。"""
        cap = ParasiticCapacitor(
            eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
        )
        c1 = cap.extract_self(length_um=500.0, width_um=1.0)["capacitance_ff"]
        c2 = cap.extract_self(length_um=1000.0, width_um=1.0)["capacitance_ff"]
        ratio = c2 / c1
        assert ratio == pytest.approx(2.0, abs=0.01)

    def test_coupling_capacitance_positive(self):
        """M1: 耦合电容 > 0（Sakurai-Tamaru 公式）。"""
        cap = ParasiticCapacitor(
            eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
        )
        result = cap.extract_coupling(
            length_um=500.0, width_um=1.0, spacing_um=0.5
        )
        assert result["coupling_capacitance_ff"] > 0

    def test_coupling_decreases_with_spacing(self):
        """M2: 耦合电容随间距增大而减小。"""
        cap = ParasiticCapacitor(
            eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
        )
        c_near = cap.extract_coupling(500.0, 1.0, 0.5)["coupling_capacitance_ff"]
        c_far = cap.extract_coupling(500.0, 1.0, 5.0)["coupling_capacitance_ff"]
        assert c_near > c_far

    def test_capacitance_matrix_symmetric(self):
        """M1: 电容矩阵对称，对角线为自容，非对角线为负耦合。"""
        cap = ParasiticCapacitor(
            eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
        )
        wires = [
            {"length_um": 500.0, "width_um": 1.0, "spacing_um": 0.5},
            {"length_um": 500.0, "width_um": 1.0, "spacing_um": 0.5},
            {"length_um": 500.0, "width_um": 1.0},
        ]
        cmat = cap.extract_capacitance_matrix(wires)
        assert cmat.shape == (3, 3)
        # 对称
        assert np.allclose(cmat, cmat.T)
        # 对角线为正（自容）
        assert cmat[0, 0] > 0 and cmat[1, 1] > 0 and cmat[2, 2] > 0
        # 相邻非对角线为负（SPICE 约定）
        assert cmat[0, 1] < 0 and cmat[1, 2] < 0
        # 非相邻为 0（仅最近邻耦合）
        assert cmat[0, 2] == 0.0

    def test_invalid_eps_raises(self):
        """M1: R03 — eps_r ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="eps_r"):
            ParasiticCapacitor(eps_r=0.0, metal_thickness_um=0.5, dielectric_thickness_um=1.0)

    def test_invalid_spacing_raises(self):
        """M1: R03 — spacing < 0.01μm 必须 raise（避免耦合发散）。"""
        cap = ParasiticCapacitor(eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0)
        with pytest.raises(ValueError, match="spacing_um"):
            cap.extract_coupling(100.0, 1.0, 0.005)


# ============================================================
# R233 寄生电感提取测试
# ============================================================
class TestParasiticInductor:
    """R233 寄生电感（Rosa 自感 + Neumann 互感）测试。"""

    def test_self_inductance_positive(self):
        """M1: 自感 > 0（Rosa 1908 公式）。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        result = ind.extract_self(length_um=1000.0, width_um=1.0)
        assert result["inductance_ph"] > 0
        # 典型值 ~1500 pH（1mm 长导线）
        assert 1000 < result["inductance_ph"] < 2000

    def test_mutual_inductance_positive_and_less_than_self(self):
        """M1: 互感 0 < M < L_self（Neumann 公式）。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        l_self = ind.extract_self(1000.0, 1.0)["inductance_ph"]
        m = ind.extract_mutual(1000.0, spacing_um=2.0)["mutual_inductance_ph"]
        assert m > 0
        assert m < l_self

    def test_mutual_decreases_with_spacing(self):
        """M2: 互感随间距增大而减小。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        m_near = ind.extract_mutual(1000.0, spacing_um=2.0)["mutual_inductance_ph"]
        m_far = ind.extract_mutual(1000.0, spacing_um=20.0)["mutual_inductance_ph"]
        assert m_near > m_far

    def test_inductance_matrix_shapes(self):
        """M1: 电感矩阵自感对角 (n,) + 互感矩阵 (n,n)。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        wires = [
            {"length_um": 500.0, "width_um": 1.0, "spacing_um": 2.0},
            {"length_um": 500.0, "width_um": 1.0, "spacing_um": 2.0},
            {"length_um": 500.0, "width_um": 1.0},
        ]
        l_self, m_mutual = ind.extract_inductance_matrix(wires)
        assert l_self.shape == (3,)
        assert m_mutual.shape == (3, 3)
        assert np.allclose(m_mutual, m_mutual.T)
        # 对角线为 0
        assert m_mutual[0, 0] == 0.0
        # 相邻互感 > 0
        assert m_mutual[0, 1] > 0
        # 非相邻为 0
        assert m_mutual[0, 2] == 0.0

    def test_invalid_length_raises(self):
        """M1: R03 — 长度 ≤ 0 必须 raise。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        with pytest.raises(ValueError, match="length_um"):
            ind.extract_self(0.0, 1.0)


# ============================================================
# R234 S 参数生成测试
# ============================================================
class TestParasiticSParam:
    """R234 S 参数（π 型网络 ABCD→S，无源/互易验证）测试。"""

    def test_dc_known_case_series_resistor(self):
        """M1: DC 下纯串联电阻 R=50Ω, z0=50 → S11=S22=1/3, S21=S12=2/3。

        理论: Z_s=50, Y_s=0 → A=1, B=50, C=0, D=1
        denom = 1 + 50/50 + 0 + 1 = 3
        S11 = (1+1-0-1)/3 = 1/3, S21 = 2/3 (Pozar §4.4)
        """
        s = ParasiticSParam.compute_s_params(
            frequencies_ghz=[0.0],
            resistance_ohm=50.0,
            inductance_ph=0.0,
            capacitance_ff=0.0,
            z0_ohm=50.0,
        )
        assert s.shape == (1, 2, 2)
        s0 = s[0]
        assert s0[0, 0] == pytest.approx(1.0 / 3.0, abs=1e-9)
        assert s0[1, 1] == pytest.approx(1.0 / 3.0, abs=1e-9)
        assert s0[1, 0] == pytest.approx(2.0 / 3.0, abs=1e-9)
        assert s0[0, 1] == pytest.approx(2.0 / 3.0, abs=1e-9)

    def test_passivity_passive_network(self):
        """M1: 无源 RLC 网络最大奇异值 ≤ 1。"""
        s = ParasiticSParam.compute_s_params(
            frequencies_ghz=np.linspace(0, 50, 51),
            resistance_ohm=10.0,
            inductance_ph=100.0,
            capacitance_ff=50.0,
            z0_ohm=50.0,
        )
        result = ParasiticSParam.verify_passivity(s)
        assert result["passive"] is True
        assert result["max_singular_value"] <= 1.0 + 1e-6
        assert result["n_freqs"] == 51

    def test_reciprocity_symmetric_network(self):
        """M1: 对称 π 型网络互易 S = Sᵀ。"""
        s = ParasiticSParam.compute_s_params(
            frequencies_ghz=np.linspace(0, 50, 51),
            resistance_ohm=10.0,
            inductance_ph=100.0,
            capacitance_ff=50.0,
            z0_ohm=50.0,
        )
        result = ParasiticSParam.verify_reciprocity(s)
        assert result["reciprocal"] is True
        assert result["max_transpose_error"] < 1e-9

    def test_s11_equals_s22_symmetric(self):
        """M2: 对称 π 网络应有 S11 == S22（R05 Bug 修复验证）。"""
        s = ParasiticSParam.compute_s_params(
            frequencies_ghz=[1.0, 10.0, 50.0],
            resistance_ohm=25.0,
            inductance_ph=200.0,
            capacitance_ff=30.0,
            z0_ohm=50.0,
        )
        for i in range(s.shape[0]):
            assert s[i, 0, 0] == pytest.approx(s[i, 1, 1], abs=1e-12)

    def test_invalid_frequency_raises(self):
        """M1: R03 — 负频率必须 raise。"""
        with pytest.raises(ValueError, match="频率"):
            ParasiticSParam.compute_s_params(
                frequencies_ghz=[-1.0],
                resistance_ohm=10.0,
                inductance_ph=0.0,
                capacitance_ff=0.0,
            )

    def test_verify_passivity_2d_input(self):
        """M2: verify_passivity 接受 (2,2) 单矩阵输入。"""
        s = ParasiticSParam.compute_s_params(
            frequencies_ghz=[1.0],
            resistance_ohm=10.0,
            inductance_ph=0.0,
            capacitance_ff=0.0,
        )
        result = ParasiticSParam.verify_passivity(s[0])
        assert result["n_freqs"] == 1


# ============================================================
# R235 SPICE 网表输出测试
# ============================================================
class TestSpiceNetlistWriter:
    """R235 SPICE 网表输出测试。"""

    def test_resistor_with_tc(self):
        """M1: 电阻输出含 TC1/TC2。"""
        w = SpiceNetlistWriter(subckt_name="r_test")
        w.add_resistor("r1", "n1", "n2", 100.0, tc1=0.0039, tc2=1e-6)
        netlist = w.to_string(ports=["n1", "n2"])
        assert ".SUBCKT r_test n1 n2" in netlist
        assert "Rr1 n1 n2 100" in netlist
        assert "tc1=0.0039" in netlist
        assert "tc2=1e-06" in netlist
        assert ".ENDS" in netlist

    def test_capacitor_and_inductor(self):
        """M1: 电容/电感元件输出。"""
        w = SpiceNetlistWriter(subckt_name="lc_test")
        w.add_capacitor("c1", "n1", "0", 1e-15)
        w.add_inductor("l1", "n2", "n3", 1e-12)
        netlist = w.to_string(ports=["n1", "n2", "n3"])
        assert "Cc1 n1 0 1e-15" in netlist
        assert "Ll1 n2 n3 1e-12" in netlist

    def test_mutual_coupling(self):
        """M1: 互感 K 元件输出。"""
        w = SpiceNetlistWriter(subckt_name="k_test")
        w.add_inductor("l1", "n1", "n2", 1e-12)
        w.add_inductor("l2", "n3", "n4", 1e-12)
        w.add_mutual("k1", "l1", "l2", 0.5)
        netlist = w.to_string(ports=["n1", "n2", "n3", "n4"])
        assert "Kk1 Ll1 Ll2 0.5" in netlist

    def test_pi_network(self):
        """M1: π 型 RLC 网络输出（串联 R+L，两端并联 C/2）。"""
        w = SpiceNetlistWriter(subckt_name="pi_test")
        w.add_pi_network("p1", "p2", 50.0, 1e-12, 2e-15, tc1=0.0039)
        netlist = w.to_string(ports=["p1", "p2"])
        assert "Rrs p1 p2 50" in netlist
        assert "Lls p1 p2 1e-12" in netlist
        # 两端各 C/2 = 1e-15
        assert "Ccp1 p1 0 1e-15" in netlist
        assert "Ccp2 p2 0 1e-15" in netlist

    def test_invalid_subckt_name_raises(self):
        """M1: R03 — 非法子电路名必须 raise。"""
        with pytest.raises(ValueError, match="subckt_name"):
            SpiceNetlistWriter(subckt_name="bad name!")

    def test_invalid_coupling_raises(self):
        """M1: R03 — 耦合系数 > 1 必须 raise。"""
        w = SpiceNetlistWriter()
        with pytest.raises(ValueError, match="耦合系数"):
            w.add_mutual("k1", "l1", "l2", 1.5)

    def test_reset_clears(self):
        """M2: reset 清空元件。"""
        w = SpiceNetlistWriter()
        w.add_resistor("r1", "n1", "n2", 100.0)
        w.reset()
        with pytest.raises(ValueError, match="网表为空"):
            w.to_string()


# ============================================================
# AdvancedParasiticExtractor 一站式测试
# ============================================================
class TestAdvancedParasiticExtractor:
    """AdvancedParasiticExtractor 综合提取测试。"""

    def test_extract_all_returns_rlc(self):
        """M1: extract_all 返回 R/L/C 三项寄生参数。"""
        ext = AdvancedParasiticExtractor()
        result = ext.extract_all(length_um=1000.0, width_um=1.0)
        assert "resistance" in result
        assert "capacitance" in result
        assert "inductance" in result
        assert result["resistance"]["resistance_ohm"] > 0
        assert result["capacitance"]["capacitance_ff"] > 0
        assert result["inductance"]["inductance_ph"] > 0

    def test_compute_s_params_via_extractor(self):
        """M1: 综合提取器 S 参数计算委托正常。"""
        ext = AdvancedParasiticExtractor()
        s = ext.compute_s_params(
            frequencies_ghz=[0.0],
            resistance_ohm=50.0,
            inductance_ph=0.0,
            capacitance_ff=0.0,
            z0_ohm=50.0,
        )
        assert s[0, 0, 0] == pytest.approx(1.0 / 3.0, abs=1e-9)

    def test_write_spice_netlist_via_extractor(self):
        """M1: 综合提取器 SPICE 网表生成。"""
        ext = AdvancedParasiticExtractor()
        netlist = ext.write_spice_netlist(
            "p1", "p2", 50.0, 1e-12, 2e-15, tc1=0.0039
        )
        assert ".SUBCKT" in netlist
        assert ".ENDS" in netlist
        assert "Rrs" in netlist
