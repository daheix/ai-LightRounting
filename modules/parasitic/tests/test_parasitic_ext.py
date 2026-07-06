"""扩展测试（从 test_parasitic.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_parasitic.py。
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
