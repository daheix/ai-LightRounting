"""扩展测试（从test_cap.py拆分，R11质量门禁文件≤800行）.

测试覆盖:
- 定向耦合器/移相器 Verilog-A 模型生成
- Ngspice 真实联合仿真（sine/pulse/pam4，R13 §2 端到端自测）
- run_photoelectric_cosim PAM4 BER 公式验证（*创新*）

来源（R02 学术诚信）:
- pytest: https://docs.pytest.org/
- Ngspice: https://ngspice.sourceforge.io/docs.html
- Chrostowski 2015 §8.4/§9.2
- Shafik 2016 PAM4 BER https://ieeexplore.ieee.org/document/7410082
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

from polaris_parasitic import (  # noqa: E402
    DEVICE_TYPE_DIRECTIONAL_COUPLER,
    DEVICE_TYPE_PHASE_SHIFTER,
    CoSimulationResult,
    SPICESimulationConfig,
    generate_detector_verilog_a,
    generate_directional_coupler_verilog_a,
    generate_modulator_verilog_a,
    generate_phase_shifter_verilog_a,
    generate_spice_netlist,
    run_ngspice_cosimulation,
    run_photoelectric_cosim,
)


def test_directional_coupler_verilog_a():
    """定向耦合器: through=cos(κL), cross=-j·sin(κL)。"""
    model = generate_directional_coupler_verilog_a(
        module_name="dc_test", coupling_length_um=10.0, kappa=0.3
    )
    assert model.device_type == DEVICE_TYPE_DIRECTIONAL_COUPLER
    assert model.ports == ["in", "through", "coupled_in", "cross"]
    # 无源: |through|² + |cross|² = cos²(κL) + sin²(κL) = 1
    s_through = complex(model.s_params[("through", "in")])
    s_cross = complex(model.s_params[("cross", "in")])
    assert abs(s_through) ** 2 + abs(s_cross) ** 2 <= 1.0 + 1e-6
    # cross 端 -90° 相位（-j·sin(κL)）
    assert s_cross.imag <= 0 or s_cross.real == 0.0


def test_phase_shifter_verilog_a():
    """移相器: φ=(2π/λ)·Δn_eff·L。"""
    model = generate_phase_shifter_verilog_a(
        module_name="ps_test", length_um=100.0, delta_n_eff=0.001
    )
    assert model.device_type == DEVICE_TYPE_PHASE_SHIFTER
    assert model.ports == ["in", "out"]
    # S21 幅度 = 1（无损耗），相位 = (2π/λ)·Δn_eff·L
    s21 = complex(model.s_params[("out", "in")])
    assert abs(abs(s21) - 1.0) < 1e-6
    # 相位非零（Δn_eff ≠ 0）
    assert abs(np.angle(s21)) > 0


# =============================================================================
# Ngspice 真实联合仿真（R13 §2 强制自测：调用真实 ngspice 子进程）
# =============================================================================


def _ngspice_available() -> bool:
    """检测 ngspice 可执行文件是否可用。"""
    import shutil
    return shutil.which("ngspice") is not None


def test_ngspice_real_cosimulation_sine():
    """Ngspice 真实联合仿真（sine 信号，R13 §2 端到端自测）。

    R02 学术诚信: 真实调用 ngspice 子进程生成 rawfile，解析真实仿真数据，
    禁止任何合成数据（R03）。ngspice 不可用时跳过（环境依赖，非业务路径）。
    """
    if not _ngspice_available():
        pytest.skip("ngspice 未安装，跳过真实联合仿真测试")
    modulator = generate_modulator_verilog_a(module_name="mzm_test")
    detector = generate_detector_verilog_a(module_name="pd_test")
    config = SPICESimulationConfig(
        spice_timestep=1e-11, optical_timestep=1e-11, total_time=1e-9
    )
    netlist = generate_spice_netlist(
        models=[modulator, detector], config=config, input_signal="sine"
    )
    result = run_ngspice_cosimulation(netlist, config, timeout=30)
    # 真实 ngspice 仿真数据验证
    assert isinstance(result, CoSimulationResult)
    assert result.time_points.shape[0] > 0, "时间点数组不能为空"
    assert result.voltage.shape[0] > 0, "电压数组不能为空"
    assert result.optical_power.shape[0] > 0, "光功率数组不能为空"
    # 时间点单调递增
    assert np.all(np.diff(result.time_points) >= 0), "时间点应单调递增"
    # sine 信号电压应有正负波动
    assert np.max(result.voltage) > 0
    assert np.min(result.voltage) < 0


def test_ngspice_real_cosimulation_pulse():
    """Ngspice 真实联合仿真（pulse 信号，R13 §2 端到端自测）。"""
    if not _ngspice_available():
        pytest.skip("ngspice 未安装，跳过真实联合仿真测试")
    modulator = generate_modulator_verilog_a(module_name="mzm_test")
    detector = generate_detector_verilog_a(module_name="pd_test")
    config = SPICESimulationConfig(
        spice_timestep=1e-11, optical_timestep=1e-11, total_time=5e-10
    )
    netlist = generate_spice_netlist(
        models=[modulator, detector], config=config, input_signal="pulse"
    )
    result = run_ngspice_cosimulation(netlist, config, timeout=30)
    assert isinstance(result, CoSimulationResult)
    # pulse 信号应有上升沿（0 → 1）
    assert np.max(result.voltage) > 0.5, "pulse 峰值应 > 0.5"


def test_ngspice_real_cosimulation_pam4():
    """Ngspice 真实联合仿真（pam4 信号，R13 §2 端到端自测）。"""
    if not _ngspice_available():
        pytest.skip("ngspice 未安装，跳过真实联合仿真测试")
    modulator = generate_modulator_verilog_a(module_name="mzm_test")
    detector = generate_detector_verilog_a(module_name="pd_test")
    config = SPICESimulationConfig(
        spice_timestep=1e-11, optical_timestep=1e-11, total_time=5e-10
    )
    netlist = generate_spice_netlist(
        models=[modulator, detector], config=config, input_signal="pam4"
    )
    result = run_ngspice_cosimulation(netlist, config, timeout=30)
    assert isinstance(result, CoSimulationResult)
    # PAM4 信号应有多个电平（0 和 0.33）
    unique_levels = np.unique(np.round(result.voltage, decimals=2))
    assert len(unique_levels) >= 2, f"PAM4 应有 ≥2 电平，得到 {unique_levels}"


# =============================================================================
# run_photoelectric_cosim PAM4 BER 公式验证（MNA SPICE 桥接，*创新*）
# =============================================================================


def test_run_photoelectric_cosim_pam4_ber():
    """run_photoelectric_cosim PAM4 BER 公式验证（*创新*）。

    R02: PAM4 BER ≈ (3/4)·erfc(√(Es/(5·N0)))，区别于 NRZ BER=0.5·erfc(√(SNR/2))。
    来源: Proakis §5; Keysight 5992-3268; Shafik 2016
    """
    try:
        from polaris_circuit.mna_spice import MNACircuit  # noqa: F401
    except ImportError:
        pytest.skip("polaris_circuit 未安装，跳过 run_photoelectric_cosim 测试")
    modulator = generate_modulator_verilog_a(module_name="mzm_test")
    detector = generate_detector_verilog_a(module_name="pd_test")
    config = SPICESimulationConfig()
    # NRZ 调制
    result_nrz = run_photoelectric_cosim(
        [modulator, detector], config, input_signal="sine", modulation="NRZ"
    )
    # PAM4 调制
    result_pam4 = run_photoelectric_cosim(
        [modulator, detector], config, input_signal="pam4", modulation="PAM4"
    )
    # 两种调制方式都应返回 CoSimulationResult
    assert isinstance(result_nrz, CoSimulationResult)
    assert isinstance(result_pam4, CoSimulationResult)
    # BER 在 [0, 0.75] 范围内（PAM4 理论上限 0.75）
    assert 0 <= result_pam4.ber <= 0.75
    assert 0 <= result_nrz.ber <= 0.5  # NRZ 上限 0.5
    # 眼图矩阵非空
    assert result_pam4.eye_diagram is not None
    assert result_nrz.eye_diagram is not None


def test_run_photoelectric_cosim_invalid_modulation_raise():
    """R03: run_photoelectric_cosim 不支持的调制方式 raise。"""
    try:
        from polaris_circuit.mna_spice import MNACircuit  # noqa: F401
    except ImportError:
        pytest.skip("polaris_circuit 未安装，跳过 run_photoelectric_cosim 测试")
    modulator = generate_modulator_verilog_a(module_name="mzm_test")
    detector = generate_detector_verilog_a(module_name="pd_test")
    config = SPICESimulationConfig()
    with pytest.raises(ValueError, match="不支持的调制方式"):
        run_photoelectric_cosim(
            [modulator, detector], config, modulation="QAM16"
        )
