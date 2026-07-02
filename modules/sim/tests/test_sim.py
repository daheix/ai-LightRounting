"""polaris-sim 子模块测试（R13 强制自测）。

测试覆盖:
- test_waveguide_s: 有损耗波导 |S| < 1
- test_mmi_models: MMI 1x2/2x2/GC 功率守恒与相位
- test_mzi_sparam: 谐振波长 1540-1560nm, ER > 20dB
- test_clements_unitary: 4x4, unitarity_error < 1e-10, is_unitary=True
- test_pam4: BER > 0, SNR > 0
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Saleh & Teich 2019 §4.4 https://www.wiley.com/
- Clements et al., Optica 2016
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Shafik et al., IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7410082
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_sim  # noqa: E402
from polaris_sim import (  # noqa: E402
    compute_clements_unitary,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    port_key,
    simulate_mzi_sparam,
    simulate_pam4,
    waveguide_s,
)


def test_waveguide_s():
    """有损耗波导 |S| < 1（传输项振幅衰减）。"""
    wl = [1.50, 1.55, 1.60]
    # 100μm 波导，3 dB/cm 损耗 → 0.03 dB 总损耗，|S| 略小于 1
    result = waveguide_s(wl, length_um=100.0, neff=2.4, loss_db_cm=3.0)
    s = result[port_key("out", "in")]
    assert len(s) == 3, f"波长数 3，得到 {len(s)}"
    for v in s:
        mag = abs(v)
        assert mag < 1.0, f"有损耗波导 |S| 应 < 1，得到 {mag}"
        assert mag > 0.99, f"100μm/3dB·cm 损耗应很小，|S|={mag} 异常过小"
    # 无反射：对角项为 0
    assert all(v == 0 for v in result[port_key("in", "in")])
    # 互易
    assert result[port_key("out", "in")] == result[port_key("in", "out")]


def test_mmi_models():
    """MMI 1x2/2x2 功率守恒，GC 高斯响应。"""
    wl = [1.55]
    # MMI 1x2: 两输出功率和 = 10^(-il/10)
    mmi1 = mmi_1x2_s(wl, insertion_loss_db=0.4)
    s1 = abs(mmi1[port_key("out1", "in")][0]) ** 2
    s2 = abs(mmi1[port_key("out2", "in")][0]) ** 2
    assert math.isclose(s1 + s2, 10.0 ** (-0.4 / 10.0), rel_tol=1e-9), (
        f"MMI 1x2 功率守恒失败: {s1 + s2}"
    )
    # MMI 1x2 π/2 相位
    assert math.isclose(mmi1[port_key("out1", "in")][0].imag, abs(mmi1[port_key("out1", "in")][0]), rel_tol=1e-9)

    # MMI 2x2: bar 实数, cross 虚数（π/2 相位）
    mmi2 = mmi_2x2_s(wl, insertion_loss_db=0.5)
    bar = mmi2[port_key("out1", "in1")][0]
    cross = mmi2[port_key("out2", "in1")][0]
    assert abs(bar.imag) < 1e-12, f"bar 应为实数，得到 {bar}"
    assert abs(cross.real) < 1e-12, f"cross 应为纯虚数（π/2 相位），得到 {cross}"

    # GC: peak 处响应最大，偏离 peak 衰减
    gc = grating_coupler_s([1.55, 1.59], peak_wl=1.55, bandwidth_3db=0.04, insertion_loss_db=1.9)
    s_peak = abs(gc[port_key("waveguide", "fiber")][0])
    s_off = abs(gc[port_key("waveguide", "fiber")][1])
    assert s_peak > s_off, f"GC peak 处应更大: {s_peak} vs {s_off}"


def test_mzi_sparam():
    """MZI S 参数扫描: 谐振波长 1540-1560nm, ER > 20dB。"""
    result = simulate_mzi_sparam()
    # 默认 1500-1600nm 101 点
    assert result["n_points"] == 101, f"n_points 应 101，得到 {result['n_points']}"
    # 谐振波长在 1540-1560nm
    assert 1540.0 <= result["resonant_wavelength_nm"] <= 1560.0, (
        f"谐振波长应在 1540-1560nm，得到 {result['resonant_wavelength_nm']}"
    )
    # 理论消光比 > 20dB（R=0.48 → ≈28dB）
    assert result["extinction_ratio_db"] > 20.0, (
        f"理论 ER 应 > 20dB，得到 {result['extinction_ratio_db']}"
    )
    # 实际消光比 > 20dB
    assert result["extinction_ratio_physical_db"] > 20.0, (
        f"实际 ER 应 > 20dB，得到 {result['extinction_ratio_physical_db']}"
    )
    # 传输率极值范围合理
    assert 0.0 < result["T_min"] < result["T_max"] <= 1.0, (
        f"T_min/T_max 异常: {result['T_min']}, {result['T_max']}"
    )


def test_clements_unitary():
    """4x4 Clements 酉矩阵: unitarity_error < 1e-10, is_unitary=True。"""
    result = compute_clements_unitary(n_modes=4)
    U = np.array(result["unitary"], dtype=complex)
    assert U.shape == (4, 4), f"酉矩阵应 4x4，得到 {U.shape}"
    assert result["unitarity_error"] < 1e-10, (
        f"酉性误差应 < 1e-10，得到 {result['unitarity_error']}"
    )
    assert result["is_unitary"] is True, "is_unitary 应为 True"
    # 独立验证 U·U† = I
    identity_err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
    assert identity_err < 1e-10, f"独立验证 U·U†=I 失败: {identity_err}"


def test_pam4():
    """PAM4 仿真: BER > 0, SNR > 0。"""
    result = simulate_pam4(n_symbols=1000, bit_rate_gbps=100, samples_per_symbol=16, noise_std=0.05)
    assert result["ber"] > 0, f"BER 应 > 0，得到 {result['ber']}"
    assert result["snr_db"] > 0, f"SNR 应 > 0，得到 {result['snr_db']}"
    assert result["n_symbols"] == 1000
    assert result["bit_rate_gbps"] == 100.0
    # BER 应在合理范围（< 0.5，远低于 0.5 误码上限）
    assert result["ber"] < 0.5, f"BER 应 < 0.5，得到 {result['ber']}"


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    # 波导负长度
    with pytest.raises(ValueError):
        waveguide_s([1.55], length_um=-1.0)
    # 波长非正
    with pytest.raises(ValueError):
        waveguide_s([0.0], length_um=100.0)
    # MZI 扫描点数 < 2
    with pytest.raises(ValueError):
        simulate_mzi_sparam(wavelength_nm=[1550.0])
    # Clements n_modes < 1
    with pytest.raises(ValueError):
        compute_clements_unitary(n_modes=0)
    # PAM4 符号数 <= 0
    with pytest.raises(ValueError):
        simulate_pam4(n_symbols=0)
    # PAM4 负噪声
    with pytest.raises(ValueError):
        simulate_pam4(noise_std=-0.1)


def test_sim_version():
    """验证子模块版本号为 5.0.0（8 子模块统一版本）。"""
    assert polaris_sim.__version__ == "5.0.0"
