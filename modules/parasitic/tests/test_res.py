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
