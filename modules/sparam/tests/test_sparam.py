"""polaris-sparam 子模块测试（R13 强制自测）。

测试覆盖（≥5 个 pytest，任务要求）:
- test_waveguide_s_length_zero: 波导长度0传输1（无相位无衰减）
- test_mmi_unitarity: MMI 1x2 功率守恒、MMI 2x2 bar/cross 相位
- test_mzi_resonance: MZI 谐振波长落在 1540-1560nm（约 1549nm）
- test_clements_unitarity: Clements 酉性误差 < 1e-10
- test_port_key_format: port_key 格式正确
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Saleh & Teich 2019 §4.4（MZI 传输率）
- Clements et al., Optica 2016
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Soldano & Pennings, J. Lightwave Technol. 1995
  https://ieeexplore.ieee.org/document/374358
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Simphony MZI 教程
  https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
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

import polaris_sparam  # noqa: E402
from polaris_sparam import (  # noqa: E402
    compute_clements_unitary,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    port_key,
    simulate_mzi_sparam,
    waveguide_s,
)


def test_waveguide_s_length_zero():
    """波导长度0：传输系数幅度=1（无衰减无相位）。"""
    result = waveguide_s([1.55], length_um=0.0, neff=2.4, loss_db_cm=3.0)
    s = result[port_key("out", "in")][0]
    # 长度0 → S = exp(0) = 1
    assert math.isclose(abs(s), 1.0, rel_tol=1e-12), (
        f"长度0 波导 |S| 应为 1，得到 {abs(s)}"
    )
    assert math.isclose(s.imag, 0.0, abs_tol=1e-12)
    assert math.isclose(s.real, 1.0, rel_tol=1e-12)
    # 互易
    assert result[port_key("out", "in")] == result[port_key("in", "out")]


def test_mmi_unitarity():
    """MMI 1x2 功率守恒 + MMI 2x2 bar/cross 相位。"""
    wl = [1.55]
    # MMI 1x2: 两输出功率和 = 10^(-il/10)
    mmi1 = mmi_1x2_s(wl, insertion_loss_db=0.4)
    s1 = abs(mmi1[port_key("out1", "in")][0]) ** 2
    s2 = abs(mmi1[port_key("out2", "in")][0]) ** 2
    assert math.isclose(s1 + s2, 10.0 ** (-0.4 / 10.0), rel_tol=1e-9)
    # π/2 相位: 实部=0，虚部=|S|
    val = mmi1[port_key("out1", "in")][0]
    assert abs(val.real) < 1e-12
    assert math.isclose(val.imag, abs(val), rel_tol=1e-9)

    # MMI 2x2: bar 实数 + cross 纯虚数
    mmi2 = mmi_2x2_s(wl, insertion_loss_db=0.5)
    bar = mmi2[port_key("out1", "in1")][0]
    cross = mmi2[port_key("out2", "in1")][0]
    assert abs(bar.imag) < 1e-12, f"bar 应为实数，得到 {bar}"
    assert abs(cross.real) < 1e-12, f"cross 应为纯虚数（π/2 相位），得到 {cross}"
    # 等功分束
    assert math.isclose(abs(bar), abs(cross), rel_tol=1e-12)


def test_mzi_resonance():
    """MZI S 参数扫描: 谐振波长落在 1540-1560nm（≈1549nm）。"""
    result = simulate_mzi_sparam()
    assert result["n_points"] == 101
    # 关键: 谐振波长应落在 1540-1560nm（设计目标 1549nm）
    assert 1540.0 <= result["resonant_wavelength_nm"] <= 1560.0, (
        f"谐振波长应在 1540-1560nm，得到 {result['resonant_wavelength_nm']}"
    )
    # 实际谐振点应接近设计目标 1549nm（采样间隔 1nm）
    assert abs(result["resonant_wavelength_nm"] - 1549.0) <= 1.5, (
        f"谐振波长应接近 1549nm，得到 {result['resonant_wavelength_nm']}"
    )
    # 消光比 > 20dB（R=0.48 → ≈28dB）
    assert result["extinction_ratio_db"] > 20.0
    assert result["extinction_ratio_physical_db"] > 20.0


def test_clements_unitarity():
    """Clements 酉性: 4x4 unitarity_error < 1e-10。"""
    result = compute_clements_unitary(n_modes=4)
    U = np.array(result["unitary"], dtype=complex)
    assert U.shape == (4, 4)
    assert result["unitarity_error"] < 1e-10, (
        f"酉性误差应 < 1e-10，得到 {result['unitarity_error']}"
    )
    assert result["is_unitary"] is True
    # 独立验证 U·U† = I
    identity_err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
    assert identity_err < 1e-10


def test_port_key_format():
    """port_key 格式: str((out, in))。"""
    key = port_key("out1", "in2")
    assert key == "('out1', 'in2')"
    assert isinstance(key, str)
    # 应可被 eval 还原为 tuple
    parsed = eval(key)
    assert parsed == ("out1", "in2")


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        waveguide_s([1.55], length_um=-1.0)
    with pytest.raises(ValueError):
        waveguide_s([0.0], length_um=100.0)
    with pytest.raises(ValueError):
        simulate_mzi_sparam(wavelength_nm=[1550.0])  # < 2 点
    with pytest.raises(ValueError):
        compute_clements_unitary(n_modes=0)
    with pytest.raises(ValueError):
        grating_coupler_s([1.55], bandwidth_3db=0.0)


def test_sparam_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_sparam.__version__ == "5.0.0"
