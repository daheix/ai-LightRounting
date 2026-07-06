"""polaris-fdfd 子模块深度测试（v5.0，R13 强制自测 / R05 回归防护）。

覆盖稳定 API: C0 / build_helmholtz_operator / build_line_source / solve_fdfd。
测试维度: 常量、矩阵结构（5 点拉普拉斯 + PML 复坐标拉伸）、高斯线源、
场分布、传输率（Poynting 流）、边界条件、网格收敛性、参数校验（R03）、
R05 网格尺寸 BUG 回归。

## Input / Process / Output
- I: 各 API 输入参数（合法/非法）
- P: 调用 API → 断言矩阵结构/数组形状/物理量/异常
- O: 全部断言通过（无 fall-back，失败即修复测试本身）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Taflove & Hagness 2005 "Computational Electrodynamics" §5.8 PML
- Shin & Fan 2014 Opt. Express
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-22-5-5230
- Shin & Fan 2012 J. Comput. Phys. (SC-PML)
  https://doi.org/10.1016/j.jcp.2012.01.015
- Berenger 1994 J. Comput. Phys. (PML 原创)
  https://doi.org/10.1006/jcph.1994.1159
- scipy.sparse.linalg.spsolve
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- pytest 文档 https://docs.pytest.org/
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_fdfd  # noqa: E402
from polaris_fdfd import (  # noqa: E402
    C0,
    build_helmholtz_operator,
    build_line_source,
    solve_fdfd,
)


# =============================================================================
# 常量与模块元信息
# =============================================================================


def test_c0_constant_value():
    """C0 真空光速 = NIST CODATA 2018 精确值 299792458.0 m/s。"""
    assert C0 == 299_792_458.0
    assert isinstance(C0, float)


def test_module_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_fdfd.__version__ == "5.0.0"


def test_module_exports():
    """__all__ 导出全部稳定 API。"""
    expected = {"solve_fdfd", "build_helmholtz_operator", "build_line_source", "C0"}
    assert expected.issubset(set(polaris_fdfd.__all__))


# =============================================================================
# build_helmholtz_operator — 5 点拉普拉斯稀疏算子
# =============================================================================


def test_helmholtz_operator_shape():
    """算子形状 = (nx*nz, nx*nz)，CSR 稀疏格式。"""
    n_profile = np.full((5, 7), 1.5, dtype=np.float64)
    A = build_helmholtz_operator(n_profile, dx=0.1, dz=0.2, k0=4.0)
    assert A.shape == (35, 35)
    assert sparse.issparse(A)
    assert A.format == "csr"


def test_helmholtz_operator_dtype_no_pml():
    """pml_n=0 退化为 Dirichlet 实数矩阵（float64）。"""
    n_profile = np.full((5, 7), 1.5, dtype=np.float64)
    A = build_helmholtz_operator(n_profile, dx=0.1, dz=0.2, k0=4.0, pml_n=0)
    assert A.dtype == np.float64


def test_helmholtz_operator_dtype_with_pml():
    """pml_n>0 启用 PML 复坐标拉伸 → complex128。"""
    n_profile = np.full((10, 12), 1.5, dtype=np.float64)
    A = build_helmholtz_operator(
        n_profile, dx=0.1, dz=0.1, k0=4.0, pml_n=3, sigma_max=2.0
    )
    assert A.dtype == np.complex128


def test_helmholtz_operator_main_diagonal_free_space():
    """自由空间内部点主对角 = -2(1/dx²+1/dz²)+k₀²n²。

    来源: Shin & Fan 2012 JCP 5 点拉普拉斯离散。
    """
    nx, nz = 5, 7
    dx, dz, k0, n = 0.1, 0.2, 4.0, 1.5
    n_profile = np.full((nx, nz), n, dtype=np.float64)
    A = build_helmholtz_operator(n_profile, dx=dx, dz=dz, k0=k0, pml_n=0).toarray()
    # 内部点 (i=2, j=3) → index = 2*7+3 = 17
    idx = 2 * nz + 3
    expected = -2.0 * (1.0 / dx**2 + 1.0 / dz**2) + k0**2 * n**2
    assert abs(A[idx, idx] - expected) < 1e-12, (
        f"主对角元 {A[idx, idx]} 期望 {expected}"
    )


def test_helmholtz_operator_off_diagonals_free_space():
    """自由空间内部点 x/z 邻居副对角 = 1/dx² / 1/dz²。"""
    nx, nz = 5, 7
    dx, dz, k0 = 0.1, 0.2, 4.0
    n_profile = np.full((nx, nz), 1.5, dtype=np.float64)
    A = build_helmholtz_operator(n_profile, dx=dx, dz=dz, k0=k0, pml_n=0).toarray()
    idx = 2 * nz + 3  # 内部点 (2,3)
    # x 方向邻居 ±nz
    assert abs(A[idx, idx + nz] - 1.0 / dx**2) < 1e-12
    assert abs(A[idx, idx - nz] - 1.0 / dx**2) < 1e-12
    # z 方向邻居 ±1
    assert abs(A[idx, idx + 1] - 1.0 / dz**2) < 1e-12
    assert abs(A[idx, idx - 1] - 1.0 / dz**2) < 1e-12


def test_helmholtz_operator_z_wrap_prevention():
    """z 方向偏移在行末清零，防止 x 方向 wrap（index = i*nz-1 处 ±1 为 0）。

    来源: 数组布局 index = i*nz + j，行末 j=nz-1 的 +1 邻居不应连到下一行 i+1,j=0。
    """
    nx, nz = 5, 7
    n_profile = np.full((nx, nz), 1.5, dtype=np.float64)
    A = build_helmholtz_operator(
        n_profile, dx=0.1, dz=0.2, k0=4.0, pml_n=0
    ).toarray()
    # 行 i=0 末尾 index = 0*nz + (nz-1) = 6，其 +1 邻居 index=7 应为 0
    assert A[6, 7] == 0.0, "行末 +1 邻居应清零（防 x-wrap）"
    # 行 i=1 起始 index = 1*nz = 7，其 -1 邻居 index=6 应为 0
    assert A[7, 6] == 0.0, "行首 -1 邻居应清零（防 x-wrap）"


def test_helmholtz_operator_pml_imaginary_nonzero():
    """PML 复坐标拉伸使算子含非零虚部（Berenger 1994）。"""
    n_profile = np.full((10, 12), 1.5, dtype=np.float64)
    A = build_helmholtz_operator(
        n_profile, dx=0.1, dz=0.1, k0=4.0, pml_n=3, sigma_max=2.0
    ).toarray()
    assert np.max(np.abs(A.imag)) > 0, "PML 启用后算子须含非零虚部"


def test_helmholtz_operator_invalid_shape():
    """网格过小（<3×3）raise（R03）。"""
    with pytest.raises(ValueError):
        build_helmholtz_operator(np.full((2, 7), 1.5), dx=0.1, dz=0.1, k0=4.0)
    with pytest.raises(ValueError):
        build_helmholtz_operator(np.full((5, 2), 1.5), dx=0.1, dz=0.1, k0=4.0)


def test_helmholtz_operator_invalid_steps():
    """dx/dz/k0 非正 raise（R03 禁止 fall-back）。"""
    n_profile = np.full((5, 7), 1.5)
    with pytest.raises(ValueError):
        build_helmholtz_operator(n_profile, dx=0.0, dz=0.1, k0=4.0)
    with pytest.raises(ValueError):
        build_helmholtz_operator(n_profile, dx=0.1, dz=-0.1, k0=4.0)
    with pytest.raises(ValueError):
        build_helmholtz_operator(n_profile, dx=0.1, dz=0.1, k0=0.0)


def test_helmholtz_operator_invalid_pml_n():
    """pml_n < 0 raise（R03）。"""
    n_profile = np.full((5, 7), 1.5)
    with pytest.raises(ValueError):
        build_helmholtz_operator(
            n_profile, dx=0.1, dz=0.1, k0=4.0, pml_n=-1
        )


# =============================================================================
# build_line_source — 高斯线源
# =============================================================================


def test_line_source_shape_dtype():
    """源向量形状 (nx*nz,) complex128。"""
    b = build_line_source(
        nx=11, nz=13, dx=0.1, source_z_idx=3,
        center_x_um=0.5, waist_um=0.3,
    )
    assert b.shape == (143,)
    assert b.dtype == np.complex128


def test_line_source_gaussian_peak_at_center():
    """高斯源峰值位于 center_x_um 对应的横向索引。"""
    nx, nz, dx = 21, 11, 0.05
    center_x_um = 0.5
    b = build_line_source(
        nx=nx, nz=nz, dx=dx, source_z_idx=2,
        center_x_um=center_x_um, waist_um=0.2,
    )
    # 重塑 (nx, nz)，取 source_z_idx 列
    b2d = b.reshape(nx, nz)
    col = np.abs(b2d[:, 2])
    peak_i = int(np.argmax(col))
    # 峰值索引对应的 x 坐标应最接近 center_x_um
    assert abs(peak_i * dx - center_x_um) < dx, (
        f"峰值索引 {peak_i} (x={peak_i*dx}) 偏离中心 {center_x_um}"
    )


def test_line_source_normalization():
    """归一化后 max|b| = 1。"""
    b = build_line_source(
        nx=21, nz=11, dx=0.05, source_z_idx=2,
        center_x_um=0.5, waist_um=0.2,
    )
    assert abs(float(np.max(np.abs(b))) - 1.0) < 1e-12


def test_line_source_only_source_column_nonzero():
    """仅 source_z_idx 列非零，其余位置为 0（线源）。"""
    nx, nz = 21, 11
    source_z_idx = 4
    b = build_line_source(
        nx=nx, nz=nz, dx=0.05, source_z_idx=source_z_idx,
        center_x_um=0.5, waist_um=0.2,
    )
    b2d = b.reshape(nx, nz)
    nonzero_cols = np.where(np.any(np.abs(b2d) > 0, axis=0))[0]
    assert list(nonzero_cols) == [source_z_idx], (
        f"非零列应为 [{source_z_idx}]，实际 {list(nonzero_cols)}"
    )


def test_line_source_invalid_waist():
    """waist_um <= 0 raise（R03）。"""
    with pytest.raises(ValueError):
        build_line_source(
            nx=11, nz=13, dx=0.1, source_z_idx=3,
            center_x_um=0.5, waist_um=0.0,
        )


def test_line_source_invalid_source_z():
    """source_z_idx 越界 raise（R03）。"""
    with pytest.raises(ValueError):
        build_line_source(
            nx=11, nz=13, dx=0.1, source_z_idx=13,
            center_x_um=0.5, waist_um=0.3,
        )
    with pytest.raises(ValueError):
        build_line_source(
            nx=11, nz=13, dx=0.1, source_z_idx=-1,
            center_x_um=0.5, waist_um=0.3,
        )


def test_line_source_invalid_grid():
    """网格过小 raise（R03）。"""
    with pytest.raises(ValueError):
        build_line_source(
            nx=2, nz=13, dx=0.1, source_z_idx=3,
            center_x_um=0.5, waist_um=0.3,
        )


# =============================================================================
# solve_fdfd — 端到端求解
# =============================================================================


def test_solve_fdfd_returns_dict_fields():
    """solve_fdfd 返回 dict 含全部必需字段。"""
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    for key in [
        "field_2d", "transmission", "transmission_db",
        "p_output", "p_source", "n_grid", "wavelength_um",
        "grid_info", "physics",
    ]:
        assert key in result, f"返回 dict 缺少字段: {key}"


def test_solve_fdfd_field_shape():
    """场分布形状匹配网格 (nx, nz)，无 NaN。"""
    result = solve_fdfd(
        width_um=0.5, length_um=6.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    field = np.array(result["field_2d"], dtype=complex)
    nx = result["grid_info"]["nx"]
    nz = result["grid_info"]["nz"]
    assert field.shape == (nx, nz)
    assert np.all(np.isfinite(field))
    assert np.max(np.abs(field)) > 0, "场分布全零"


def test_solve_fdfd_transmission_finite_positive():
    """传输率为有限正数，dB 与线性值一致。"""
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    t = result["transmission"]
    assert math.isfinite(t) and t > 0
    assert math.isfinite(result["transmission_db"])
    # dB 与线性值一致性
    assert abs(t - 10.0 ** (result["transmission_db"] / 10.0)) < 1e-9


def test_solve_fdfd_poynting_positive():
    """Poynting 流 p_source / p_output 为正（PML 复坐标拉伸生效）。"""
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    assert result["p_source"] > 0
    assert result["p_output"] > 0


def test_solve_fdfd_pml_imaginary_field():
    """场分布含非零虚部（PML 复坐标拉伸生效，BUG 时场纯实数）。"""
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    field = np.array(result["field_2d"], dtype=complex)
    assert np.max(np.abs(field.imag)) > 0, "场虚部全零，PML 未生效"


def test_solve_fdfd_grid_metadata():
    """grid_info 元数据完整且自洽。"""
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    gi = result["grid_info"]
    for key in [
        "nx", "nz", "dx_um", "dz_um", "window_x_um", "length_um",
        "core_x", "source_z_idx", "input_z_idx", "output_z_idx",
        "pml_n", "sigma_max",
    ]:
        assert key in gi, f"grid_info 缺少字段: {key}"
    # 监视器位置有序
    assert gi["source_z_idx"] == gi["pml_n"]
    assert gi["input_z_idx"] > gi["source_z_idx"]
    assert gi["output_z_idx"] > gi["input_z_idx"]
    assert gi["output_z_idx"] == gi["nz"] - 1 - gi["pml_n"]
    # PML 参数合理
    assert gi["pml_n"] >= 4
    assert gi["sigma_max"] > 0


def test_solve_fdfd_physics_metadata():
    """physics 元数据: k0 = 2π/λ，n_core > n_clad。"""
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    ph = result["physics"]
    assert abs(ph["k0"] - 2.0 * np.pi / 1.55) < 1e-12
    assert ph["n_core"] == 3.476
    assert ph["n_clad"] == 1.444
    assert ph["n_core"] > ph["n_clad"]


def test_solve_fdfd_grid_size_regression():
    """*R05 回归*: 网格尺寸 BUG 修复 — nx=51, nz=201, n_grid=10251。

    BUG 现象（修复前）: int(round(W/dx)) 致网格点数少 1、物理尺寸被压缩、
    Dirichlet 边界 + 实数系统 → Poynting 流=0、transmission_db=-49.7 dB。
    修复后: int(W/dx)+1，(N-1)*dx 精确等于窗口尺寸。
    """
    result = solve_fdfd(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.05, pad_um=1.0,
    )
    gi = result["grid_info"]
    assert gi["nx"] == 51, f"nx 应为 51，得到 {gi['nx']}"
    assert gi["nz"] == 201, f"nz 应为 201，得到 {gi['nz']}"
    assert result["n_grid"] == 51 * 201 == 10251
    # 传输率合理（BUG 时 -49.7 dB）
    assert -20 < result["transmission_db"] < 0
    assert 0 < result["transmission"] < 1


def test_solve_fdfd_grid_convergence():
    """网格收敛性: dx 减半传输率稳定（Cauchy 收敛）。

    直波导近无损，dx=0.1 与 dx=0.05 传输率 dB 差应 < 3 dB。
    """
    r_coarse = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    r_fine = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.05, pad_um=1.0,
    )
    # 细网格点数更多
    assert r_fine["n_grid"] > r_coarse["n_grid"]
    # 两者均有限正
    assert r_coarse["transmission"] > 0 and r_fine["transmission"] > 0
    # dB 差收敛
    db_diff = abs(r_fine["transmission_db"] - r_coarse["transmission_db"])
    assert db_diff < 3.0, (
        f"网格收敛性差: dx=0.1→{r_coarse['transmission_db']:.3f} dB, "
        f"dx=0.05→{r_fine['transmission_db']:.3f} dB, 差 {db_diff:.3f} dB"
    )


def test_solve_fdfd_invalid_width():
    """width_um <= 0 raise（R03）。"""
    with pytest.raises(ValueError):
        solve_fdfd(width_um=0.0)


def test_solve_fdfd_invalid_length():
    """length_um <= 0 raise（R03）。"""
    with pytest.raises(ValueError):
        solve_fdfd(length_um=0.0)


def test_solve_fdfd_invalid_wavelength():
    """wavelength_um <= 0 raise（R03）。"""
    with pytest.raises(ValueError):
        solve_fdfd(wavelength_um=0.0)


def test_solve_fdfd_invalid_refractive_index():
    """n_core <= n_clad raise（R03，全反射条件不满足）。"""
    with pytest.raises(ValueError):
        solve_fdfd(n_core=1.0, n_clad=2.0)
    with pytest.raises(ValueError):
        solve_fdfd(n_core=0.0)


def test_solve_fdfd_invalid_dx():
    """dx_um 非正或 >= width raise（R03）。"""
    with pytest.raises(ValueError):
        solve_fdfd(dx_um=0.0)
    with pytest.raises(ValueError):
        solve_fdfd(width_um=0.5, dx_um=1.0)


def test_solve_fdfd_invalid_pad():
    """pad_um <= 0 raise（R03）。"""
    with pytest.raises(ValueError):
        solve_fdfd(pad_um=0.0)


def test_solve_fdfd_wavelength_metadata():
    """返回 wavelength_um 与输入一致。"""
    result = solve_fdfd(
        width_um=0.5, length_um=6.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, dx_um=0.1, pad_um=1.0,
    )
    assert result["wavelength_um"] == 1.55
