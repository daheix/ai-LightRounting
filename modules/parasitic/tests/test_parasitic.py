"""polaris-parasitic 子模块深度测试。

测试覆盖（38 个 pytest，覆盖全部 44 个公开 API）:
- 常量与器件类型: 10 个 DEVICE_TYPE_* 常量/SUPPORTED_DEVICE_TYPES frozenset
                  /6 个 DEFAULT_* 物理常量
- R231 寄生电阻: ParasiticResistor.extract（片电阻 + TC1/TC2 温度模型）
                 /非法参数 raise（R03）
- R232 寄生电容: extract_self（平行板 + arcosh 边缘）/extract_coupling
                 （Sakurai-Tamaru 耦合）/extract_capacitance_matrix
- R233 寄生电感: extract_self（Rosa 1908）/extract_mutual（Neumann）
                 /extract_inductance_matrix
- R234 S 参数: compute_s_params（π 型 ABCD→S）/verify_passivity
              /verify_reciprocity（Pozar §4）
- R235 SPICE 网表: SpiceNetlistWriter.add_resistor/add_capacitor
                   /add_inductor/add_mutual/add_pi_network/to_string
                   /reset（含非法名称/节点/值 raise 分支）
- AdvancedParasiticExtractor: extract_all/compute_s_params/write_spice_netlist
- Verilog-A 模型生成: 5 器件 generate_*（waveguide/mmi/ring/modulator/detector）
                     /generate_verilog_a 统一入口/save_verilog_a
                     /VerilogAModel 数据类验证
- SPICE 联合仿真: SPICESimulationConfig（时间步同步）/generate_spice_netlist
                  （pulse/sine/pam4 三种信号 + raise 分支）/CoSimulationResult
- 光电协同可微分（*创新*）: DifferentiableOptoElectricalModel.forward/gradient
                            /optimize_opto_electrical_link（梯度下降联合优化）

来源（R02 学术诚信，≥5 文献 URL）:
- pytest 文档: https://docs.pytest.org/
- Synopsys StarRC Datasheet（RLCK 寄生提取，TC1/TC2）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Cadence Quantus QRC 3D 场求解:
  https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
- Ansys Lumerical CML Compiler（Verilog-A 紧凑模型）:
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Verilog-AMS LRM: https://www.accellera.org/downloads/standards/v-ams
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §2.3/§8/§9
- Pozar, "Microwave Engineering", 4th ed., §4（ABCD↔S 变换）
- Rosa, "Self and Mutual Inductances", NIST BS 1908:
  https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
- Banerjee ECE 225 UCSB Lecture 6（arcosh 边缘电容模型）:
  http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
- Sakurai & Tamaru, IEEE JSSC 18(4), 1983（同层耦合经验公式）
- Ngspice 用户手册: https://ngspice.sourceforge.io/docs.html
- SiPANN ring_resonator: https://sipann.readthedocs.io/en/latest/models.html
- Simphony waveguide: https://simphonyphotonics.readthedocs.io/

规则: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_parasitic  # noqa: E402
from polaris_parasitic import (  # noqa: E402
    AdvancedParasiticExtractor,
    CoSimulationResult,
    DEFAULT_DETECTOR_RESPONSIVITY,
    DEFAULT_LOAD_RESISTANCE_OHM,
    DEFAULT_MODULATOR_EFFICIENCY,
    DEFAULT_OPTICAL_TIMESTEP_S,
    DEFAULT_SPICE_TIMESTEP_S,
    DEFAULT_WAVELENGTH_UM,
    DEVICE_TYPE_DETECTOR,
    DEVICE_TYPE_DIRECTIONAL_COUPLER,
    DEVICE_TYPE_GRATING_COUPLER,
    DEVICE_TYPE_MMI_1X2,
    DEVICE_TYPE_MMI_2X2,
    DEVICE_TYPE_MODULATOR,
    DEVICE_TYPE_PHASE_SHIFTER,
    DEVICE_TYPE_RING,
    DEVICE_TYPE_WAVEGUIDE,
    DEVICE_TYPE_Y_BRANCH,
    DifferentiableOptoElectricalModel,
    ParasiticCapacitor,
    ParasiticInductor,
    ParasiticResistor,
    ParasiticSParam,
    SDict,
    SPICESimulationConfig,
    SpiceNetlistWriter,
    SUPPORTED_DEVICE_TYPES,
    VerilogAModel,
    generate_detector_verilog_a,
    generate_mmi_1x2_verilog_a,
    generate_modulator_verilog_a,
    generate_ring_verilog_a,
    generate_spice_netlist,
    generate_verilog_a,
    generate_waveguide_verilog_a,
    optimize_opto_electrical_link,
    save_verilog_a,
)


# =============================================================================
# 常量与器件类型枚举
# =============================================================================


def test_device_type_constants():
    """10 个 DEVICE_TYPE_* 常量值符合 Lumerical CML 命名规范。"""
    assert DEVICE_TYPE_WAVEGUIDE == "waveguide"
    assert DEVICE_TYPE_MMI_1X2 == "mmi_1x2"
    assert DEVICE_TYPE_MMI_2X2 == "mmi_2x2"
    assert DEVICE_TYPE_RING == "ring_resonator"
    assert DEVICE_TYPE_MODULATOR == "modulator"
    assert DEVICE_TYPE_DETECTOR == "detector"
    assert DEVICE_TYPE_GRATING_COUPLER == "grating_coupler"
    assert DEVICE_TYPE_Y_BRANCH == "y_branch"
    assert DEVICE_TYPE_DIRECTIONAL_COUPLER == "directional_coupler"
    assert DEVICE_TYPE_PHASE_SHIFTER == "phase_shifter"


def test_supported_device_types_frozenset():
    """SUPPORTED_DEVICE_TYPES 为 frozenset 且包含全部 10 种器件。"""
    assert isinstance(SUPPORTED_DEVICE_TYPES, frozenset)
    assert len(SUPPORTED_DEVICE_TYPES) == 10
    assert DEVICE_TYPE_WAVEGUIDE in SUPPORTED_DEVICE_TYPES
    assert DEVICE_TYPE_DETECTOR in SUPPORTED_DEVICE_TYPES


def test_default_physical_constants():
    """6 个 DEFAULT_* 物理常量值符合 SiEPIC EBeam PDK / Chrostowski 2015。"""
    assert DEFAULT_WAVELENGTH_UM == 1.55  # SiEPIC 1550nm
    assert DEFAULT_DETECTOR_RESPONSIVITY == 1.0  # Chrostowski §9.2
    assert DEFAULT_MODULATOR_EFFICIENCY == 0.1  # Chrostowski §8.4
    assert DEFAULT_LOAD_RESISTANCE_OHM == 50.0  # 50Ω 射频标准
    assert DEFAULT_SPICE_TIMESTEP_S == 1e-12
    assert DEFAULT_OPTICAL_TIMESTEP_S == 1e-13


# =============================================================================
# R231 寄生电阻提取
# =============================================================================


def test_parasitic_resistance_extract():
    """R231 片电阻 + TC1/TC2 温度模型。

    R = RPSQ × L / W；25°C 时 temp_factor=1.0。
    """
    r = ParasiticResistor(sheet_resistance_ohm_sq=0.05, tc1=0.0039, tc2=0.0)
    result = r.extract(length_um=100.0, width_um=1.0, temperature_c=25.0)
    assert result["resistance_ohm"] == pytest.approx(5.0, rel=1e-9)
    assert result["n_squares"] == pytest.approx(100.0)
    assert result["temp_factor"] == pytest.approx(1.0)
    # 高温时电阻升高（金属 tc1>0）
    r_hot = r.extract(length_um=100.0, width_um=1.0, temperature_c=125.0)
    assert r_hot["resistance_ohm"] > result["resistance_ohm"]
    assert r_hot["temp_factor"] > 1.0


def test_resistor_default_temperature_uses_t_ref():
    """temperature_c=None 时使用参考温度 t_ref。"""
    r = ParasiticResistor(sheet_resistance_ohm_sq=1.0, t_ref=25.0)
    result = r.extract(length_um=10.0, width_um=1.0)
    # 默认温度 = t_ref → temp_factor = 1.0
    assert result["temperature_c"] == 25.0
    assert result["temp_factor"] == pytest.approx(1.0)


def test_resistor_invalid_params_raise():
    """R231 非法参数 raise（R03 禁止 fall-back）。"""
    # 片电阻非正
    with pytest.raises(ValueError, match="sheet_resistance_ohm_sq"):
        ParasiticResistor(sheet_resistance_ohm_sq=-1.0)
    # 长度非正
    r = ParasiticResistor(sheet_resistance_ohm_sq=0.05)
    with pytest.raises(ValueError, match="length_um"):
        r.extract(length_um=-1.0, width_um=1.0)
    # 宽度非正
    with pytest.raises(ValueError, match="width_um"):
        r.extract(length_um=1.0, width_um=0.0)


# =============================================================================
# R232 寄生电容提取
# =============================================================================


def test_parasitic_capacitance_extract():
    """R232 平行板 + 边缘电容。

    C_pp = ε·W·L/d > 0；C_fringe > 0；C_total = C_pp + C_fringe。
    """
    c = ParasiticCapacitor(
        eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
    )
    result = c.extract_self(length_um=100.0, width_um=1.0)
    assert result["capacitance_ff"] > 0.0
    assert result["capacitance_area_ff"] > 0.0
    assert result["capacitance_fringe_ff"] > 0.0
    assert result["capacitance_ff"] == pytest.approx(
        result["capacitance_area_ff"] + result["capacitance_fringe_ff"]
    )


def test_capacitor_extract_coupling():
    """R232 Sakurai-Tamaru 同层耦合电容。"""
    c = ParasiticCapacitor(
        eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
    )
    result = c.extract_coupling(length_um=100.0, width_um=1.0, spacing_um=2.0)
    assert result["coupling_capacitance_ff"] > 0.0
    assert result["spacing_um"] == 2.0
    # 间距越小耦合越大
    close = c.extract_coupling(length_um=100.0, width_um=1.0, spacing_um=0.5)
    assert close["coupling_capacitance_ff"] > result["coupling_capacitance_ff"]


def test_capacitor_extract_matrix():
    """R232 多导体电容矩阵（n×n，对角自容 + 非对角耦合取负）。"""
    c = ParasiticCapacitor(
        eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0
    )
    wires = [
        {"length_um": 100.0, "width_um": 1.0, "spacing_um": 2.0},
        {"length_um": 100.0, "width_um": 1.0, "spacing_um": 2.0},
        {"length_um": 100.0, "width_um": 1.0},
    ]
    cmat = c.extract_capacitance_matrix(wires)
    assert cmat.shape == (3, 3)
    # 对角线为正（自容）
    assert cmat[0, 0] > 0.0
    assert cmat[1, 1] > 0.0
    # 非对角线为负（SPICE 约定）
    assert cmat[0, 1] < 0.0
    assert cmat[1, 0] < 0.0
    # 对称
    assert cmat[0, 1] == cmat[1, 0]


def test_capacitor_invalid_params_raise():
    """R232 非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="eps_r"):
        ParasiticCapacitor(eps_r=-1.0, metal_thickness_um=0.5, dielectric_thickness_um=1.0)
    with pytest.raises(ValueError, match="metal_thickness_um"):
        ParasiticCapacitor(eps_r=3.9, metal_thickness_um=0.0, dielectric_thickness_um=1.0)
    c = ParasiticCapacitor(eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0)
    with pytest.raises(ValueError, match="spacing_um"):
        c.extract_coupling(length_um=100.0, width_um=1.0, spacing_um=0.001)
    with pytest.raises(ValueError, match="wires"):
        c.extract_capacitance_matrix([])


# =============================================================================
# R233 寄生电感提取
# =============================================================================


def test_parasitic_inductance_extract():
    """R233 Rosa 1908 矩形截面自感。

    L_self = μ0·L/(2π)·[ln(2L/(W+H)) + 0.5 + (W+H)/(6L)] > 0。
    """
    L = ParasiticInductor(metal_thickness_um=0.5)
    result = L.extract_self(length_um=100.0, width_um=1.0)
    assert result["inductance_ph"] > 0.0
    # 互感应为正且小于自感（物理事实）
    m = L.extract_mutual(length_um=100.0, spacing_um=2.0)
    assert m["mutual_inductance_ph"] > 0.0
    assert m["mutual_inductance_ph"] < result["inductance_ph"]


def test_inductor_extract_matrix():
    """R233 多导体电感矩阵（自感对角 + 互感非对角）。"""
    L = ParasiticInductor(metal_thickness_um=0.5)
    wires = [
        {"length_um": 100.0, "width_um": 1.0, "spacing_um": 2.0},
        {"length_um": 100.0, "width_um": 1.0, "spacing_um": 2.0},
        {"length_um": 100.0, "width_um": 1.0},
    ]
    l_self, m_mutual = L.extract_inductance_matrix(wires)
    assert l_self.shape == (3,)
    assert m_mutual.shape == (3, 3)
    # 自感为正
    assert np.all(l_self > 0.0)
    # 互感矩阵对角线为 0
    assert m_mutual[0, 0] == 0.0
    # 非对角线为正（相邻耦合）
    assert m_mutual[0, 1] > 0.0
    # 对称
    assert m_mutual[0, 1] == m_mutual[1, 0]


def test_inductor_invalid_params_raise():
    """R233 非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="metal_thickness_um"):
        ParasiticInductor(metal_thickness_um=0.0)
    L = ParasiticInductor(metal_thickness_um=0.5)
    with pytest.raises(ValueError, match="length_um"):
        L.extract_self(length_um=0.0, width_um=1.0)
    with pytest.raises(ValueError, match="spacing_um"):
        L.extract_mutual(length_um=100.0, spacing_um=-1.0)
    with pytest.raises(ValueError, match="wires"):
        L.extract_inductance_matrix([])


# =============================================================================
# R234 S 参数生成
# =============================================================================


def test_sparam_compute_shape():
    """R234 compute_s_params 返回 (N,2,2) 复数数组。"""
    s = ParasiticSParam.compute_s_params(
        frequencies_ghz=[1.0, 10.0, 50.0],
        resistance_ohm=1.0,
        inductance_ph=10.0,
        capacitance_ff=1.0,
        z0_ohm=50.0,
    )
    assert s.shape == (3, 2, 2)
    assert s.dtype == np.complex128


def test_sparam_passivity_reciprocity():
    """R234 π 型网络 S 参数无源 + 互易。

    无源 RLC 网络：max 奇异值 ≤ 1（无源），S = Sᵀ（互易）。
    """
    s = ParasiticSParam.compute_s_params(
        frequencies_ghz=[1.0, 10.0],
        resistance_ohm=1.0,
        inductance_ph=10.0,
        capacitance_ff=1.0,
        z0_ohm=50.0,
    )
    passivity = ParasiticSParam.verify_passivity(s)
    assert passivity["passive"] is True
    assert passivity["max_singular_value"] <= 1.0 + 1e-6
    assert passivity["n_freqs"] == 2
    reciprocity = ParasiticSParam.verify_reciprocity(s)
    assert reciprocity["reciprocal"] is True
    assert reciprocity["n_freqs"] == 2


def test_sparam_verify_2d_input():
    """R234 verify_passivity/reciprocity 接受 2D 单频输入。"""
    s = ParasiticSParam.compute_s_params(
        frequencies_ghz=[1.0],
        resistance_ohm=1.0, inductance_ph=10.0, capacitance_ff=1.0,
    )
    s_2d = s[0]  # (2, 2)
    passivity = ParasiticSParam.verify_passivity(s_2d)
    assert passivity["n_freqs"] == 1
    reciprocity = ParasiticSParam.verify_reciprocity(s_2d)
    assert reciprocity["n_freqs"] == 1


def test_sparam_invalid_params_raise():
    """R234 非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="frequencies_ghz"):
        ParasiticSParam.compute_s_params([], 1.0, 10.0, 1.0)
    with pytest.raises(ValueError, match="频率"):
        ParasiticSParam.compute_s_params([-1.0], 1.0, 10.0, 1.0)
    with pytest.raises(ValueError, match="resistance_ohm"):
        ParasiticSParam.compute_s_params([1.0], -1.0, 10.0, 1.0)
    with pytest.raises(ValueError, match="z0_ohm"):
        ParasiticSParam.compute_s_params([1.0], 1.0, 10.0, 1.0, z0_ohm=0.0)
    # shape[1] != shape[2]（3 != 4）触发维度校验
    with pytest.raises(ValueError, match="维度"):
        ParasiticSParam.verify_passivity(np.zeros((2, 3, 4)))


# =============================================================================
# R235 SPICE 网表生成
# =============================================================================


def test_spice_netlist_writer_pi_network():
    """R235 SPICE .subckt π 网络生成。

    网表含 .SUBCKT 头、R/C 元件、.ENDS 尾。
    """
    writer = SpiceNetlistWriter(subckt_name="test_net")
    writer.add_pi_network(
        node1="in", node2="out",
        resistance_ohm=1.0, inductance_h=1e-12, capacitance_f=1e-15,
    )
    netlist = writer.to_string(ports=["in", "out"])
    assert ".SUBCKT test_net in out" in netlist
    assert ".ENDS" in netlist
    assert "Rrs" in netlist
    assert "Ccp1" in netlist


def test_spice_add_resistor_with_tc():
    """R235 add_resistor 含 TC1/TC2 温度系数。"""
    writer = SpiceNetlistWriter()
    writer.add_resistor("r1", "n1", "n2", 100.0, tc1=0.0039, tc2=1e-6)
    netlist = writer.to_string(ports=["n1", "n2"])
    assert "Rr1 n1 n2 100" in netlist
    assert "tc1=0.0039" in netlist
    assert "tc2=1e-06" in netlist


def test_spice_add_capacitor_and_inductor():
    """R235 add_capacitor / add_inductor 元件。"""
    writer = SpiceNetlistWriter()
    writer.add_capacitor("c1", "a", "b", 1e-15)
    writer.add_inductor("l1", "a", "b", 1e-12)
    netlist = writer.to_string(ports=["a", "b"])
    assert "Cc1 a b" in netlist
    assert "Ll1 a b" in netlist


def test_spice_add_mutual():
    """R235 add_mutual 互感耦合 K 元件。"""
    writer = SpiceNetlistWriter()
    writer.add_inductor("l1", "a", "b", 1e-12)
    writer.add_inductor("l2", "c", "d", 1e-12)
    writer.add_mutual("k1", "l1", "l2", 0.5)
    netlist = writer.to_string(ports=["a", "d"])
    assert "Kk1 Ll1 Ll2 0.5" in netlist


def test_spice_reset():
    """R235 reset 清空已添加元件。"""
    writer = SpiceNetlistWriter()
    writer.add_resistor("r1", "a", "b", 100.0)
    assert len(writer._lines) == 1
    writer.reset()
    assert len(writer._lines) == 0
    assert len(writer._nodes) == 0


def test_spice_invalid_params_raise():
    """R235 非法参数 raise（R03）。"""
    # 子电路名非法
    with pytest.raises(ValueError, match="subckt_name"):
        SpiceNetlistWriter(subckt_name="invalid name!")
    writer = SpiceNetlistWriter()
    # 电阻名非法
    with pytest.raises(ValueError, match="电阻名"):
        writer.add_resistor("invalid name", "a", "b", 1.0)
    # 节点名空
    with pytest.raises(ValueError, match="节点名不能为空"):
        writer.add_resistor("r1", "", "b", 1.0)
    # 电阻值负
    with pytest.raises(ValueError, match="电阻值"):
        writer.add_resistor("r1", "a", "b", -1.0)
    # 耦合系数越界
    with pytest.raises(ValueError, match="耦合系数"):
        writer.add_mutual("k1", "l1", "l2", 1.5)
    # 空网表 to_string（未添加任何元件 + ports=None）
    empty_writer = SpiceNetlistWriter()
    with pytest.raises(ValueError, match="网表为空"):
        empty_writer.to_string()
    # ports 显式传空列表
    with pytest.raises(ValueError, match="端口列表"):
        empty_writer.to_string(ports=[])


# =============================================================================
# AdvancedParasiticExtractor 一站式门面
# =============================================================================


def test_advanced_extractor_all():
    """AdvancedParasiticExtractor.extract_all 一站式 R/L/C 提取。"""
    extractor = AdvancedParasiticExtractor()
    result = extractor.extract_all(length_um=100.0, width_um=1.0)
    assert "resistance" in result
    assert "capacitance" in result
    assert "inductance" in result
    assert result["resistance"]["resistance_ohm"] > 0
    assert result["capacitance"]["capacitance_ff"] > 0
    assert result["inductance"]["inductance_ph"] > 0


def test_advanced_extractor_compute_s_params():
    """AdvancedParasiticExtractor.compute_s_params 委托 ParasiticSParam。"""
    extractor = AdvancedParasiticExtractor()
    s = extractor.compute_s_params(
        frequencies_ghz=[1.0, 10.0],
        resistance_ohm=1.0,
        inductance_ph=10.0,
        capacitance_ff=1.0,
    )
    assert s.shape == (2, 2, 2)


def test_advanced_extractor_write_spice_netlist():
    """AdvancedParasiticExtractor.write_spice_netlist 生成 SPICE 网表。"""
    extractor = AdvancedParasiticExtractor()
    netlist = extractor.write_spice_netlist(
        node1="in", node2="out",
        resistance_ohm=1.0, inductance_h=1e-12, capacitance_f=1e-15,
    )
    assert ".SUBCKT parasitic_net in out" in netlist
    assert ".ENDS" in netlist


# =============================================================================
# Verilog-A 紧凑模型生成（5+ 器件）
# =============================================================================


def test_generate_waveguide_verilog_a():
    """波导 Verilog-A 模型生成。

    S21 = exp(-α·L/2)·exp(j·2π·neff·L/λ)；.va 代码含 module 声明。
    """
    model = generate_waveguide_verilog_a(
        module_name="wg_test",
        length_um=100.0,
        neff=2.4,
        ng=4.0,
        loss_db_cm=0.5,
        wavelength_um=DEFAULT_WAVELENGTH_UM,
    )
    assert isinstance(model, VerilogAModel)
    assert model.module_name == "wg_test"
    assert model.ports == ["in", "out"]
    assert model.device_type == DEVICE_TYPE_WAVEGUIDE
    assert "module wg_test" in model.verilog_a_code
    # S21 幅度 = 损耗衰减
    s21 = complex(model.s_params[("out", "in")])
    assert 0.99 < abs(s21) < 1.0


def test_generate_mmi_1x2_verilog_a():
    """MMI 1x2 3dB 分束器 Verilog-A 模型。"""
    model = generate_mmi_1x2_verilog_a(
        module_name="mmi_test", insertion_loss_db=0.4,
    )
    assert model.device_type == DEVICE_TYPE_MMI_1X2
    assert model.ports == ["in", "out1", "out2"]
    # 3dB 分束 + 0.4dB 插损 → amp = 10^(-(0.4+3)/20)
    amp = complex(model.s_params[("out1", "in")])
    expected = 10.0 ** (-(0.4 + 3.0) / 20.0)
    assert abs(abs(amp) - expected) < 1e-6


def test_generate_ring_verilog_a():
    """环谐振器全通传输 Verilog-A 模型。"""
    model = generate_ring_verilog_a(
        module_name="ring_test", radius_um=10.0, coupling=0.05,
    )
    assert model.device_type == DEVICE_TYPE_RING
    assert model.ports == ["in", "through"]
    # 传输函数 T = (t - a·e^{jφ}) / (1 - t·a·e^{jφ})
    T = complex(model.s_params[("through", "in")])
    assert abs(T) <= 1.0 + 1e-6  # 无源


def test_generate_modulator_verilog_a():
    """MZM 调制器 Verilog-A 模型。"""
    model = generate_modulator_verilog_a(
        module_name="mzm_test", v_pi=2.0, efficiency=0.1,
    )
    assert model.device_type == DEVICE_TYPE_MODULATOR
    assert model.ports == ["in", "out", "rf_in"]
    assert model.parameters["v_pi"] == 2.0


def test_generate_detector_verilog_a():
    """光电探测器 Verilog-A 模型。"""
    model = generate_detector_verilog_a(
        module_name="pd_test", responsivity=1.0, load_resistance=50.0,
    )
    assert model.device_type == DEVICE_TYPE_DETECTOR
    assert model.ports == ["in", "rf_out"]
    assert model.parameters["responsivity"] == 1.0


def test_generate_verilog_a_unified_entry():
    """generate_verilog_a 统一入口分发 5 器件。"""
    devices = [
        (DEVICE_TYPE_WAVEGUIDE, {}),
        (DEVICE_TYPE_MMI_1X2, {}),
        (DEVICE_TYPE_RING, {}),
        (DEVICE_TYPE_MODULATOR, {}),
        (DEVICE_TYPE_DETECTOR, {}),
    ]
    for device_type, kwargs in devices:
        model = generate_verilog_a(device_type, **kwargs)
        assert isinstance(model, VerilogAModel)
        assert model.device_type == device_type
        assert model.verilog_a_code
        assert "module" in model.verilog_a_code


def test_generate_verilog_a_auto_module_name():
    """generate_verilog_a module_name=None 自动生成。"""
    model = generate_verilog_a(DEVICE_TYPE_WAVEGUIDE)
    assert model.module_name == "waveguide_polaris"


def test_generate_verilog_a_invalid_device_raises():
    """generate_verilog_a 不支持的器件类型 raise（R03）。"""
    with pytest.raises(ValueError, match="不支持的器件类型"):
        generate_verilog_a("unknown_device")


def test_verilog_a_model_post_init_validation():
    """VerilogAModel 数据类验证 device_type/module_name/ports。"""
    # 不支持的器件类型
    with pytest.raises(ValueError, match="不支持的器件类型"):
        VerilogAModel(
            module_name="test", device_type="unknown",
            ports=["in"], parameters={}, s_params={},
        )
    # 模块名空
    with pytest.raises(ValueError, match="module_name"):
        VerilogAModel(
            module_name="", device_type=DEVICE_TYPE_WAVEGUIDE,
            ports=["in"], parameters={}, s_params={},
        )
    # 端口空
    with pytest.raises(ValueError, match="ports"):
        VerilogAModel(
            module_name="test", device_type=DEVICE_TYPE_WAVEGUIDE,
            ports=[], parameters={}, s_params={},
        )


def test_verilog_a_invalid_params_raise():
    """Verilog-A 各生成器非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="波导长度"):
        generate_waveguide_verilog_a(length_um=-1.0)
    with pytest.raises(ValueError, match="neff"):
        generate_waveguide_verilog_a(neff=0.0)
    with pytest.raises(ValueError, match="插损"):
        generate_mmi_1x2_verilog_a(insertion_loss_db=-1.0)
    with pytest.raises(ValueError, match="环半径"):
        generate_ring_verilog_a(radius_um=-1.0)
    with pytest.raises(ValueError, match="coupling"):
        generate_ring_verilog_a(coupling=1.5)
    with pytest.raises(ValueError, match="V_pi"):
        generate_modulator_verilog_a(v_pi=0.0)
    with pytest.raises(ValueError, match="响应度"):
        generate_detector_verilog_a(responsivity=-1.0)
    with pytest.raises(ValueError, match="负载电阻"):
        generate_detector_verilog_a(load_resistance=0.0)


def test_save_verilog_a(tmp_path: Path):
    """save_verilog_a 写入 .va 文件。"""
    model = generate_mmi_1x2_verilog_a(module_name="mmi_test")
    out = tmp_path / "mmi_test.va"
    path = save_verilog_a(model, out)
    assert path.exists()
    assert path.read_text() == model.verilog_a_code


# =============================================================================
# SPICE 联合仿真
# =============================================================================


def test_spice_simulation_config_defaults():
    """SPICESimulationConfig 默认值与时间步同步。"""
    cfg = SPICESimulationConfig()
    assert cfg.spice_timestep == DEFAULT_SPICE_TIMESTEP_S
    assert cfg.optical_timestep == DEFAULT_OPTICAL_TIMESTEP_S
    assert cfg.total_time == 1e-9
    assert cfg.temperature == 25.0
    assert cfg.ngspice_path == "ngspice"
    # sync_timestep = max(spice, optical) = 1e-12
    assert cfg.sync_timestep == max(cfg.spice_timestep, cfg.optical_timestep)


def test_spice_simulation_config_invalid_raise():
    """SPICESimulationConfig 非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="spice_timestep"):
        SPICESimulationConfig(spice_timestep=-1.0)
    with pytest.raises(ValueError, match="optical_timestep"):
        SPICESimulationConfig(optical_timestep=0.0)
    with pytest.raises(ValueError, match="total_time"):
        SPICESimulationConfig(total_time=-1.0)


def test_generate_spice_netlist_pulse():
    """generate_spice_netlist pulse 信号 Ngspice 网表生成。"""
    model = generate_waveguide_verilog_a()
    config = SPICESimulationConfig()
    netlist = generate_spice_netlist(
        models=[model], config=config, input_signal="pulse"
    )
    assert ".tran" in netlist
    assert ".end" in netlist
    assert "V_in in 0 PULSE" in netlist
    assert "X1" in netlist


def test_generate_spice_netlist_sine_and_pam4():
    """generate_spice_netlist sine/pam4 信号网表生成。"""
    model = generate_waveguide_verilog_a()
    config = SPICESimulationConfig()
    sine_netlist = generate_spice_netlist(
        models=[model], config=config, input_signal="sine"
    )
    assert "SINE" in sine_netlist
    pam4_netlist = generate_spice_netlist(
        models=[model], config=config, input_signal="pam4"
    )
    assert "PULSE" in pam4_netlist


def test_generate_spice_netlist_invalid_raise():
    """generate_spice_netlist 非法参数 raise（R03）。"""
    config = SPICESimulationConfig()
    # 空模型列表
    with pytest.raises(ValueError, match="模型列表"):
        generate_spice_netlist(models=[], config=config)
    # 不支持的信号
    model = generate_waveguide_verilog_a()
    with pytest.raises(ValueError, match="不支持的输入信号"):
        generate_spice_netlist(models=[model], config=config, input_signal="unknown")


def test_co_simulation_result_dataclass():
    """CoSimulationResult 数据类字段。"""
    result = CoSimulationResult(
        time_points=np.array([0.0, 1e-12]),
        voltage=np.array([0.0, 1.0]),
        optical_power=np.array([0.0, 0.1]),
    )
    assert result.ber == 0.0
    assert result.snr_db == 0.0
    assert result.eye_diagram is None


# =============================================================================
# 光电协同可微分仿真（*创新*）
# =============================================================================


def test_differentiable_model_forward():
    """DifferentiableOptoElectricalModel.forward 光电协同前向（*创新*）。"""
    model = DifferentiableOptoElectricalModel()
    v_in = np.array([0.0, 0.5, 1.0, 2.0])
    result = model.forward(v_in, modulator_length=100.0)
    assert result["optical_power"].shape == v_in.shape
    assert result["detector_current"].shape == v_in.shape
    assert result["output_voltage"].shape == v_in.shape
    # V_out 随 V_in 单调递增（V² 关系）
    assert result["output_voltage"][3] > result["output_voltage"][2]
    assert result["output_voltage"][2] > result["output_voltage"][1]
    # V=0 时输出为 0
    assert result["output_voltage"][0] == pytest.approx(0.0, abs=1e-15)


def test_differentiable_model_gradient():
    """DifferentiableOptoElectricalModel.gradient 有限差分梯度（*创新*）。"""
    model = DifferentiableOptoElectricalModel()
    v_in = np.array([1.0, 2.0])
    grad = model.gradient(v_in, modulator_length=100.0, eps=1e-6)
    assert "dV_out_dV_in" in grad
    assert "dV_out_dL_mod" in grad
    assert grad["dV_out_dV_in"].shape == v_in.shape
    # dV_out/dV_in 应为正（V² 关系，输出随输入增大）
    assert np.all(grad["dV_out_dV_in"] > 0.0)


def test_differentiable_model_invalid_params_raise():
    """DifferentiableOptoElectricalModel 非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="modulator_efficiency"):
        DifferentiableOptoElectricalModel(modulator_efficiency=-1.0)
    with pytest.raises(ValueError, match="detector_responsivity"):
        DifferentiableOptoElectricalModel(detector_responsivity=-1.0)
    with pytest.raises(ValueError, match="load_resistance"):
        DifferentiableOptoElectricalModel(load_resistance=0.0)


def test_optimize_opto_electrical_link():
    """optimize_opto_electrical_link 梯度下降联合优化（*创新*）。"""
    result = optimize_opto_electrical_link(
        target_output_voltage=0.5,
        initial_voltage=1.0,
        initial_length=100.0,
        n_iterations=5,
        learning_rate=0.1,
    )
    assert "final_v_in" in result
    assert "final_l_mod" in result
    assert "final_v_out" in result
    assert "history" in result
    assert "converged" in result
    assert len(result["history"]) == 5
    # 损失应下降（梯度下降有效）
    first_loss = result["history"][0]["loss"]
    last_loss = result["history"][-1]["loss"]
    assert last_loss <= first_loss


def test_optimize_invalid_params_raise():
    """optimize_opto_electrical_link 非法参数 raise（R03）。"""
    with pytest.raises(ValueError, match="迭代次数"):
        optimize_opto_electrical_link(n_iterations=0)
    with pytest.raises(ValueError, match="学习率"):
        optimize_opto_electrical_link(learning_rate=0.0)


# =============================================================================
# 包级 API 完整性
# =============================================================================


def test_package_api_completeness():
    """polaris_parasitic 包级 API 导出完整性。"""
    assert polaris_parasitic.__version__ == "5.0.0"
    # 寄生提取 6 个核心类
    assert hasattr(polaris_parasitic, "ParasiticResistor")
    assert hasattr(polaris_parasitic, "ParasiticCapacitor")
    assert hasattr(polaris_parasitic, "ParasiticInductor")
    assert hasattr(polaris_parasitic, "ParasiticSParam")
    assert hasattr(polaris_parasitic, "SpiceNetlistWriter")
    assert hasattr(polaris_parasitic, "AdvancedParasiticExtractor")
    # Verilog-A 5 个 generate 函数
    assert hasattr(polaris_parasitic, "generate_waveguide_verilog_a")
    assert hasattr(polaris_parasitic, "generate_mmi_1x2_verilog_a")
    assert hasattr(polaris_parasitic, "generate_ring_verilog_a")
    assert hasattr(polaris_parasitic, "generate_modulator_verilog_a")
    assert hasattr(polaris_parasitic, "generate_detector_verilog_a")
    # SPICE 联合仿真
    assert hasattr(polaris_parasitic, "SPICESimulationConfig")
    assert hasattr(polaris_parasitic, "generate_spice_netlist")
    # 可微分（*创新*）
    assert hasattr(polaris_parasitic, "DifferentiableOptoElectricalModel")
    assert hasattr(polaris_parasitic, "optimize_opto_electrical_link")
    # SDict 本地定义（切断 v4 依赖）
    assert SDict is not None
