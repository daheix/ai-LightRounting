"""polaris-parasitic 子模块测试（R13 强制自测）。

测试覆盖（≥3 个 pytest，任务要求）:
- test_parasitic_resistance_extract: R231 片电阻 + TC1/TC2 温度模型
- test_parasitic_capacitance_extract: R232 平行板 + 边缘电容
- test_parasitic_inductance_extract: R233 Rosa 自感
- test_parasitic_sparam_passivity_reciprocity: R234 S 参数无源/互易验证
- test_spice_netlist_writer: R235 SPICE .subckt 生成
- test_advanced_extractor_all: 一站式 R/L/C 提取
- test_generate_waveguide_verilog_a: 波导 Verilog-A 模型生成
- test_generate_all_devices_verilog_a: 5 器件统一入口
- test_verilog_a_save: .va 文件写入
- test_generate_spice_netlist: Ngspice 网表生成
- test_differentiable_model_forward: 光电协同前向（*创新*）
- test_optimize_opto_electrical_link: 联合优化收敛
- test_invalid_params_raise: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Synopsys StarRC Datasheet
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Cadence Quantus QRC
  https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Verilog-AMS LRM
  https://www.accellera.org/downloads/standards/v-ams
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §2.3/§8/§9
- Pozar, "Microwave Engineering", 4th ed., §4
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
    DEFAULT_WAVELENGTH_UM,
    DEVICE_TYPE_WAVEGUIDE,
    DifferentiableOptoElectricalModel,
    ParasiticCapacitor,
    ParasiticInductor,
    ParasiticResistor,
    ParasiticSParam,
    SDict,
    SPICESimulationConfig,
    SpiceNetlistWriter,
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
# Smoke test 1: 寄生电阻提取（R231）
# =============================================================================
def test_parasitic_resistance_extract() -> None:
    """R231 片电阻 + TC1/TC2 温度模型 smoke test。

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


# =============================================================================
# Smoke test 2: 寄生电容提取（R232）
# =============================================================================
def test_parasitic_capacitance_extract() -> None:
    """R232 平行板 + 边缘电容 smoke test。

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


# =============================================================================
# Smoke test 3: 寄生电感提取（R233）
# =============================================================================
def test_parasitic_inductance_extract() -> None:
    """R233 Rosa 1908 矩形截面自感 smoke test。

    L_self = μ0·L/(2π)·[ln(2L/(W+H)) + 0.5 + (W+H)/(6L)] > 0。
    """
    L = ParasiticInductor(metal_thickness_um=0.5)
    result = L.extract_self(length_um=100.0, width_um=1.0)
    assert result["inductance_ph"] > 0.0
    # 互感应为正且小于自感（物理事实）
    m = L.extract_mutual(length_um=100.0, spacing_um=2.0)
    assert m["mutual_inductance_ph"] > 0.0
    assert m["mutual_inductance_ph"] < result["inductance_ph"]


# =============================================================================
# Smoke test 4: S 参数无源/互易验证（R234）
# =============================================================================
def test_parasitic_sparam_passivity_reciprocity() -> None:
    """R234 π 型网络 S 参数无源 + 互易 smoke test。

    无源 RLC 网络：max 奇异值 ≤ 1（无源），S = Sᵀ（互易）。
    """
    s = ParasiticSParam.compute_s_params(
        frequencies_ghz=[1.0, 10.0],
        resistance_ohm=1.0,
        inductance_ph=10.0,
        capacitance_ff=1.0,
        z0_ohm=50.0,
    )
    assert s.shape == (2, 2, 2)
    passivity = ParasiticSParam.verify_passivity(s)
    assert passivity["passive"] is True
    assert passivity["max_singular_value"] <= 1.0 + 1e-6
    reciprocity = ParasiticSParam.verify_reciprocity(s)
    assert reciprocity["reciprocal"] is True


# =============================================================================
# Smoke test 5: SPICE 网表生成（R235）
# =============================================================================
def test_spice_netlist_writer() -> None:
    """R235 SPICE .subckt 生成 smoke test。

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
    assert "Rrs" in netlist  # 串联电阻
    assert "Ccp1" in netlist  # 端口1 并联电容


# =============================================================================
# Smoke test 6: 一站式寄生提取（facade）
# =============================================================================
def test_advanced_extractor_all() -> None:
    """AdvancedParasiticExtractor.extract_all 一站式 R/L/C 提取 smoke test。"""
    extractor = AdvancedParasiticExtractor()
    result = extractor.extract_all(length_um=100.0, width_um=1.0)
    assert "resistance" in result
    assert "capacitance" in result
    assert "inductance" in result
    assert result["resistance"]["resistance_ohm"] > 0
    assert result["capacitance"]["capacitance_ff"] > 0
    assert result["inductance"]["inductance_ph"] > 0


# =============================================================================
# Smoke test 7: 波导 Verilog-A 模型生成
# =============================================================================
def test_generate_waveguide_verilog_a() -> None:
    """波导 Verilog-A 模型生成 smoke test。

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
    assert "module wg_test" in model.verilog_a_code
    # S21 幅度 = 损耗衰减（100μm 波导，0.5 dB/cm → ~0.9943）
    s21 = complex(model.s_params[("out", "in")])
    assert 0.99 < abs(s21) < 1.0


# =============================================================================
# Smoke test 8: 5 器件统一入口
# =============================================================================
def test_generate_all_devices_verilog_a() -> None:
    """generate_verilog_a 统一入口分发 5 器件 smoke test。"""
    devices = [
        ("waveguide", {}),
        ("mmi_1x2", {}),
        ("ring_resonator", {}),
        ("modulator", {}),
        ("detector", {}),
    ]
    for device_type, kwargs in devices:
        model = generate_verilog_a(device_type, **kwargs)
        assert isinstance(model, VerilogAModel)
        assert model.device_type == device_type
        assert model.verilog_a_code  # 非空
        assert "module" in model.verilog_a_code


# =============================================================================
# Smoke test 9: Verilog-A 文件保存
# =============================================================================
def test_verilog_a_save(tmp_path: Path) -> None:
    """save_verilog_a 写入 .va 文件 smoke test。"""
    model = generate_mmi_1x2_verilog_a(module_name="mmi_test")
    out = tmp_path / "mmi_test.va"
    path = save_verilog_a(model, out)
    assert path.exists()
    assert path.read_text() == model.verilog_a_code


# =============================================================================
# Smoke test 10: SPICE 联合仿真网表生成
# =============================================================================
def test_generate_spice_netlist() -> None:
    """generate_spice_netlist Ngspice 网表生成 smoke test。"""
    model = generate_waveguide_verilog_a()
    config = SPICESimulationConfig()
    netlist = generate_spice_netlist(
        models=[model], config=config, input_signal="pulse"
    )
    assert ".tran" in netlist
    assert ".end" in netlist
    assert "V_in in 0 PULSE" in netlist
    assert "X1" in netlist  # 器件实例


# =============================================================================
# Smoke test 11: 光电协同可微分前向（*创新*）
# =============================================================================
def test_differentiable_model_forward() -> None:
    """DifferentiableOptoElectricalModel.forward 光电协同前向 smoke test。"""
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


# =============================================================================
# Smoke test 12: 光电协同联合优化（*创新*）
# =============================================================================
def test_optimize_opto_electrical_link() -> None:
    """optimize_opto_electrical_link 梯度下降联合优化 smoke test。"""
    result = optimize_opto_electrical_link(
        target_output_voltage=0.5,
        initial_voltage=1.0,
        initial_length=100.0,
        n_iterations=5,
        learning_rate=0.1,
    )
    assert "final_v_in" in result
    assert "final_l_mod" in result
    assert "history" in result
    assert len(result["history"]) == 5
    # 损失应下降（梯度下降有效）
    first_loss = result["history"][0]["loss"]
    last_loss = result["history"][-1]["loss"]
    assert last_loss <= first_loss


# =============================================================================
# Smoke test 13: 非法参数 raise（R03 禁止 fall-back）
# =============================================================================
def test_invalid_params_raise() -> None:
    """非法参数 raise smoke test（R03 禁止 fall-back）。"""
    # 电阻：片电阻非正
    with pytest.raises(ValueError):
        ParasiticResistor(sheet_resistance_ohm_sq=-1.0)
    # 电阻：长度非正
    r = ParasiticResistor(sheet_resistance_ohm_sq=0.05)
    with pytest.raises(ValueError):
        r.extract(length_um=-1.0, width_um=1.0)
    # 电容：介电常数非正
    with pytest.raises(ValueError):
        ParasiticCapacitor(eps_r=-1.0, metal_thickness_um=0.5, dielectric_thickness_um=1.0)
    # Verilog-A：不支持器件类型
    with pytest.raises(ValueError):
        generate_verilog_a("unknown_device")
    # Verilog-A：环半径非正
    with pytest.raises(ValueError):
        generate_ring_verilog_a(radius_um=-1.0)
    # SPICE 配置：时间步非正
    with pytest.raises(ValueError):
        SPICESimulationConfig(spice_timestep=-1.0)
    # 可微分模型：负载电阻非正
    with pytest.raises(ValueError):
        DifferentiableOptoElectricalModel(load_resistance=-1.0)


# =============================================================================
# Smoke test 14: 包级 API 完整性
# =============================================================================
def test_package_api_completeness() -> None:
    """polaris_parasitic 包级 API 导出完整性 smoke test。"""
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
