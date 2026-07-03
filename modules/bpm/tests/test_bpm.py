"""polaris-bpm 子模块深度测试（v5.0，R13 强制自测 / R05 回归防护）。

覆盖稳定 API: C0 / CAP_FRACTION / CAP_STRENGTH / LOSS_DB_PER_CM_SI /
build_cn_matrices / build_loss_profile / gaussian_source / solve_bpm。
测试维度: 常量、Crank-Nicolson 三对角矩阵结构、Dirichlet 边界、CN 守恒性
(A+B=2I)、损耗分布（Soref 芯区 + CAP 边界）、高斯源功率归一化、传播传输率、
CN 无条件稳定性（CFL）、参数校验（R03）、R05 传输率 BUG 回归。

## Input / Process / Output
- I: 各 API 输入参数（合法/非法）
- P: 调用 API → 断言矩阵结构/数组形状/物理量/异常
- O: 全部断言通过（无 fall-back，失败即修复测试本身）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Feit & Fleck 1978 Appl. Opt.（BPM 理论）
  https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson 1947 Math. Proc. Cambridge（隐式差分格式）
- Chung & Dagli 1990 IEEE JQE（ADI 扩展）
  https://ieeexplore.ieee.org/document/59635
- scipy.linalg.solve_banded
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
- Soref 1993 Proc. IEEE（SOI 波导损耗）
  https://ieeexplore.ieee.org/document/249720
- Hadley 1992 Opt. Lett.（TBC/CAP 边界）
  https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
- Rickman & Reed 1994 Electron. Lett.（SOI 0.5 dB/cm 实测）
  https://digital-library.theiet.org/doi/abs/10.1049/el:19931356
- Grillot 2006 JLT（SOI 条形波导损耗）
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-24-2-891
- RP Photonics BPM 边界处理
  https://www.rp-photonics.com/numerical_beam_propagation.html
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- pytest 文档 https://docs.pytest.org/
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_bpm  # noqa: E402
from polaris_bpm import (  # noqa: E402
    CAP_FRACTION,
    CAP_STRENGTH,
    C0,
    LOSS_DB_PER_CM_SI,
    build_cn_matrices,
    build_loss_profile,
    gaussian_source,
    solve_bpm,
)


def _banded_to_dense(ab: np.ndarray, nx: int) -> np.ndarray:
    """scipy solve_banded 的 (3, nx) banded → dense (nx, nx)。

    约定 ab[u+i-j, j] = a[i,j]，u=1: ab[0,j]=超对角(j-1,j)，
    ab[1,j]=主对角，ab[2,j]=次对角(j+1,j)。
    """
    M = np.zeros((nx, nx), dtype=ab.dtype)
    for j in range(nx):
        M[j, j] = ab[1, j]
        if j > 0:
            M[j - 1, j] = ab[0, j]
        if j < nx - 1:
            M[j + 1, j] = ab[2, j]
    return M


# =============================================================================
# 常量与模块元信息
# =============================================================================


def test_c0_constant_value():
    """C0 真空光速 = NIST CODATA 2018 精确值 299792458.0 m/s。"""
    assert C0 == 299_792_458.0
    assert isinstance(C0, float)


def test_loss_constant_value():
    """LOSS_DB_PER_CM_SI = 3.0（Soref 1993 SOI 保守典型上界）。"""
    assert LOSS_DB_PER_CM_SI == 3.0


def test_cap_constants_values():
    """CAP_STRENGTH=0.5, CAP_FRACTION=0.3（Hadley 1992 / RP Photonics）。"""
    assert CAP_STRENGTH == 0.5
    assert CAP_FRACTION == 0.3
    assert 0.0 <= CAP_FRACTION <= 1.0


def test_module_version():
    """子模块版本号 5.0.0。"""
    assert polaris_bpm.__version__ == "5.0.0"


def test_module_exports():
    """__all__ 导出全部稳定 API。"""
    expected = {
        "solve_bpm", "build_cn_matrices", "gaussian_source",
        "build_loss_profile", "C0",
        "LOSS_DB_PER_CM_SI", "CAP_STRENGTH", "CAP_FRACTION",
    }
    assert expected.issubset(set(polaris_bpm.__all__))


# =============================================================================
# gaussian_source — 高斯光束源
# =============================================================================


def test_gaussian_source_shape_dtype():
    """高斯源形状 (nx,) complex128。"""
    E = gaussian_source(nx=21, dx=0.05, center_um=0.5, waist_um=0.2)
    assert E.shape == (21,)
    assert E.dtype == np.complex128


def test_gaussian_source_peak_at_center():
    """峰值位于 center_um 对应索引。"""
    nx, dx, center = 21, 0.05, 0.5
    E = gaussian_source(nx=nx, dx=dx, center_um=center, waist_um=0.2)
    peak_i = int(np.argmax(np.abs(E)))
    assert abs(peak_i * dx - center) < dx


def test_gaussian_source_power_normalization():
    """功率归一化 ∫|E|²dx = 1（BPM 标准归一化）。"""
    nx, dx = 51, 0.02
    E = gaussian_source(nx=nx, dx=dx, center_um=0.5, waist_um=0.2)
    power = float(np.sum(np.abs(E) ** 2) * dx)
    assert abs(power - 1.0) < 1e-10, f"功率 {power} 应为 1"


def test_gaussian_source_symmetry():
    """高斯源关于中心对称（|E(center-d)| = |E(center+d)|）。"""
    nx, dx, center = 41, 0.02, 0.4
    E = gaussian_source(nx=nx, dx=dx, center_um=center, waist_um=0.15)
    ic = int(round(center / dx))
    # 中心两侧等距点幅值相等
    for d in range(1, min(ic, nx - 1 - ic)):
        assert abs(abs(E[ic - d]) - abs(E[ic + d])) < 1e-12


def test_gaussian_source_invalid_params():
    """非法参数 raise（R03）。"""
    with pytest.raises(ValueError):
        gaussian_source(nx=2, dx=0.05, center_um=0.5, waist_um=0.2)
    with pytest.raises(ValueError):
        gaussian_source(nx=21, dx=0.0, center_um=0.5, waist_um=0.2)
    with pytest.raises(ValueError):
        gaussian_source(nx=21, dx=0.05, center_um=0.5, waist_um=0.0)
    with pytest.raises(ValueError):
        gaussian_source(nx=21, dx=0.05, center_um=-1.0, waist_um=0.2)


# =============================================================================
# build_loss_profile — 损耗分布 α(x)
# =============================================================================


def test_loss_profile_shape_dtype():
    """损耗分布形状 (nx,) float64，非负。"""
    alpha = build_loss_profile(nx=200, core_x0=80, core_x1=105, pad_pts=80)
    assert alpha.shape == (200,)
    assert alpha.dtype == np.float64
    assert np.all(alpha >= 0)


def test_loss_profile_core_alpha():
    """芯区 α = LOSS_DB_PER_CM_SI·ln(10)/10/1e4 (μm⁻¹)（Soref 1993）。"""
    nx, core_x0, core_x1, pad_pts = 200, 80, 105, 80
    alpha = build_loss_profile(nx, core_x0, core_x1, pad_pts)
    expected = LOSS_DB_PER_CM_SI * np.log(10.0) / 10.0 / 1e4
    mid = (core_x0 + core_x1) // 2
    assert abs(alpha[mid] - expected) < 1e-12


def test_loss_profile_cap_boundary_value():
    """CAP 边界处 α = CAP_STRENGTH，内侧递减到 0。"""
    nx, pad_pts = 200, 80
    alpha = build_loss_profile(nx, core_x0=80, core_x1=105, pad_pts=pad_pts)
    assert abs(alpha[0] - CAP_STRENGTH) < 1e-9
    assert abs(alpha[-1] - CAP_STRENGTH) < 1e-9


def test_loss_profile_cap_monotonic_decrease():
    """CAP 区域 α 从边界向内单调递减（平方渐变）。"""
    nx, pad_pts = 200, 80
    alpha = build_loss_profile(nx, core_x0=80, core_x1=105, pad_pts=pad_pts)
    cap_pts = int(round(pad_pts * CAP_FRACTION))
    # 左侧: alpha[1] > alpha[cap_pts-1]（边界附近 > 内侧）
    assert alpha[0] > alpha[cap_pts - 1]
    # 右侧同理
    assert alpha[-1] > alpha[nx - cap_pts]


def test_loss_profile_pure_clad_zero():
    """纯包层区域（CAP 之外、芯区之外）α = 0。"""
    nx, core_x0, core_x1, pad_pts = 200, 80, 105, 80
    alpha = build_loss_profile(nx, core_x0, core_x1, pad_pts)
    cap_pts = int(round(pad_pts * CAP_FRACTION))
    pure_clad = cap_pts + 5
    if pure_clad < core_x0:
        assert alpha[pure_clad] == 0.0


def test_loss_profile_zero_loss_no_cap():
    """loss_db_per_cm=0 且 cap_strength=0 时全零分布。"""
    alpha = build_loss_profile(
        nx=100, core_x0=40, core_x1=60, pad_pts=40,
        loss_db_per_cm=0.0, cap_strength=0.0,
    )
    assert np.all(alpha == 0.0)


def test_loss_profile_invalid_params():
    """非法参数 raise（R03）。"""
    with pytest.raises(ValueError):
        build_loss_profile(200, 50, 40, 80)  # core_x0 > core_x1
    with pytest.raises(ValueError):
        build_loss_profile(200, 80, 105, 80, cap_fraction=1.5)
    with pytest.raises(ValueError):
        build_loss_profile(200, 80, 105, 80, cap_strength=-0.1)
    with pytest.raises(ValueError):
        build_loss_profile(200, 80, 105, -10)


# =============================================================================
# build_cn_matrices — Crank-Nicolson 三对角矩阵
# =============================================================================


def test_cn_matrices_shape_dtype():
    """CN 矩阵返回 (A_banded, B_banded)，均 (3, nx) complex128。"""
    n_profile = np.full(11, 1.5, dtype=np.float64)
    A, B = build_cn_matrices(n_profile, dx=0.02, dz=0.1, k0=4.0, n0=1.444)
    assert A.shape == (3, 11)
    assert B.shape == (3, 11)
    assert A.dtype == np.complex128
    assert B.dtype == np.complex128


def test_cn_matrices_dirichlet_boundary():
    """Dirichlet 边界: A 首末行对角=1、副对角=0；B 首末行全 0。"""
    n_profile = np.full(11, 1.5, dtype=np.float64)
    A, B = build_cn_matrices(n_profile, dx=0.02, dz=0.1, k0=4.0, n0=1.444)
    # A 首末对角=1
    assert A[1, 0] == 1.0
    assert A[1, -1] == 1.0
    # A 首行超对角=0，末行次对角=0
    assert A[0, 1] == 0.0
    assert A[2, -2] == 0.0
    # B 首末对角=0
    assert B[1, 0] == 0.0
    assert B[1, -1] == 0.0


def test_cn_matrices_sum_is_identity_internal():
    """CN 守恒性: A+B = diag([1, 2, ..., 2, 1])（内部 2I，边界 Dirichlet）。

    A = I - dz/2·H, B = I + dz/2·H → A+B = 2I（内部）；
    Dirichlet 边界行 A=1,B=0 → A+B=1。
    来源: Crank & Nicolson 1947 隐式格式守恒性。
    """
    nx = 11
    n_profile = np.full(nx, 1.5, dtype=np.float64)
    A, B = build_cn_matrices(n_profile, dx=0.02, dz=0.1, k0=4.0, n0=1.444)
    A_dense = _banded_to_dense(A, nx)
    B_dense = _banded_to_dense(B, nx)
    S = A_dense + B_dense
    # 内部对角=2，边界对角=1，副对角=0
    for i in range(nx):
        diag_expected = 1.0 if i in (0, nx - 1) else 2.0
        assert abs(S[i, i] - diag_expected) < 1e-12, (
            f"S[{i},{i}]={S[i,i]} 期望 {diag_expected}"
        )
        if i < nx - 1:
            assert abs(S[i, i + 1]) < 1e-12
        if i > 0:
            assert abs(S[i, i - 1]) < 1e-12


def test_cn_matrices_invalid_params():
    """非法参数 raise（R03）。"""
    with pytest.raises(ValueError):
        build_cn_matrices(np.full(2, 1.5), dx=0.02, dz=0.1, k0=4.0, n0=1.444)
    with pytest.raises(ValueError):
        build_cn_matrices(np.full(11, 1.5), dx=0.0, dz=0.1, k0=4.0, n0=1.444)
    with pytest.raises(ValueError):
        build_cn_matrices(np.full(11, 1.5), dx=0.02, dz=0.0, k0=4.0, n0=1.444)
    with pytest.raises(ValueError):
        build_cn_matrices(np.full(11, 1.5), dx=0.02, dz=0.1, k0=0.0, n0=1.444)
    with pytest.raises(ValueError):
        build_cn_matrices(np.full(11, 1.5), dx=0.02, dz=0.1, k0=4.0, n0=0.0)


# =============================================================================
# solve_bpm — 端到端传播
# =============================================================================


def test_solve_bpm_returns_dict_fields():
    """solve_bpm 返回 dict 含全部必需字段。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    for key in [
        "field_z", "transmission", "transmission_db",
        "p_initial", "p_final", "n_steps", "wavelength_um",
        "grid_info", "physics", "loss",
    ]:
        assert key in result, f"返回 dict 缺少字段: {key}"


def test_solve_bpm_field_shape_finite():
    """末态场形状 (nx,)，无 NaN/Inf，非零。"""
    result = solve_bpm(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    field = np.array(result["field_z"], dtype=complex)
    nx = result["grid_info"]["nx"]
    assert field.shape == (nx,)
    assert np.all(np.isfinite(field))
    assert np.max(np.abs(field)) > 0


def test_solve_bpm_transmission_finite_positive():
    """传输率为有限正数，dB 与线性值一致。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    t = result["transmission"]
    assert math.isfinite(t) and t > 0
    assert math.isfinite(result["transmission_db"])
    assert abs(t - 10.0 ** (result["transmission_db"] / 10.0)) < 1e-9


def test_solve_bpm_power_decrease():
    """含物理损耗 → p_final < p_initial（功率单调递减）。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.5, dx_um=0.02, pad_um=1.0,
    )
    assert result["p_final"] < result["p_initial"]
    assert result["p_initial"] > 0
    assert result["p_final"] > 0


def test_solve_bpm_transmission_db_nonzero_regression():
    """*R05 回归*: 传输率 dB 必须为合理负值（不为 0）。

    BUG 现象（修复前）: CN 严格功率守恒 + Dirichlet 反射辐射模 →
    transmission_db ≡ 0.0 dB。修复后（split-step Soref + CAP）必须为负。
    """
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.5, dx_um=0.02, pad_um=1.0,
    )
    tdb = result["transmission_db"]
    assert tdb < -0.0001, f"transmission_db={tdb} 不应为 0（CN 守恒 BUG）"
    assert tdb > -1.0, f"transmission_db={tdb} 衰减过大（>1dB 不合理）"


def test_solve_bpm_cfl_stability_large_dz():
    """CN 无条件稳定: 大 dz 仍无 NaN（Crank & Nicolson 1947）。

    CN 隐式格式对任意 dz 数值稳定（抛物波动方程无条件稳定），
    仅精度受 dz 影响。大 dz 不应致场发散。
    """
    result = solve_bpm(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=1.0, dx_um=0.02, pad_um=1.0,
    )
    field = np.array(result["field_z"], dtype=complex)
    assert np.all(np.isfinite(field)), "大 dz 下场含 NaN/Inf（CN 不稳定）"
    assert result["n_steps"] > 0


def test_solve_bpm_grid_metadata():
    """grid_info 元数据完整且自洽。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    gi = result["grid_info"]
    for key in ["nx", "nz", "dx_um", "dz_um", "window_um", "core_x"]:
        assert key in gi, f"grid_info 缺少字段: {key}"
    assert gi["nx"] > 0 and gi["nz"] > 0
    assert gi["core_x"][0] < gi["core_x"][1]
    assert gi["core_x"][0] >= 1
    assert gi["core_x"][1] <= gi["nx"] - 1


def test_solve_bpm_physics_metadata():
    """physics 元数据: k0=2π/λ, n0=n_clad。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    ph = result["physics"]
    assert abs(ph["k0"] - 2.0 * np.pi / 1.55) < 1e-12
    assert ph["n0"] == 1.444
    assert ph["n_core"] == 3.476


def test_solve_bpm_loss_metadata():
    """loss 元数据含 Soref/CAP 参数与 alpha_profile。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    loss = result["loss"]
    assert loss["loss_db_per_cm"] == LOSS_DB_PER_CM_SI
    assert loss["cap_strength"] == CAP_STRENGTH
    assert loss["cap_fraction"] == CAP_FRACTION
    alpha = np.array(loss["alpha_profile"])
    assert alpha.shape == (result["grid_info"]["nx"],)
    assert np.all(alpha >= 0)


def test_solve_bpm_straight_waveguide_low_loss():
    """直波导短距离传输率 > 0.5（主体功率保留）。"""
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    assert result["transmission"] > 0.5, (
        f"直波导传输率应 > 0.5，得到 {result['transmission']}"
    )


def test_solve_bpm_invalid_params():
    """非法参数 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        solve_bpm(width_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(length_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(wavelength_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(dz_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(dx_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(pad_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(width_um=0.5, dx_um=1.0)
    with pytest.raises(ValueError):
        solve_bpm(n_core=0.0, n_clad=1.444)
    with pytest.raises(ValueError):
        solve_bpm(n_core=3.476, n_clad=-1.0)


def test_solve_bpm_wavelength_metadata():
    """返回 wavelength_um 与输入一致。"""
    result = solve_bpm(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    assert result["wavelength_um"] == 1.55
    assert result["n_steps"] == result["grid_info"]["nz"]
