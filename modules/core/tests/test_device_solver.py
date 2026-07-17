"""polaris-core 统一器件级求解器调度测试（DeviceLevelSolver）。

覆盖:
1. DeviceSolverConfig 构造与非法方法 raise
2. _select_method 自动选择策略（7 种几何 → 7 种求解器）
3. 各 _solve_* 委托实际求解（EME 1D/2D / FDE / RCWA / BPM / varFDTD / FDTD）
4. solve_device 便捷入口
5. 显式 method 覆盖 auto

================================================================
学术诚信文献溯源（R02，≥5 篇）
================================================================
1. Bienstman 2001 PhD §2.3（EME 模式匹配）
   https://www.photonics.intec.ugent.be/download/phd_bienstman.pdf
2. Smit & van Dam 1996 JLT（模式展开）
   https://doi.org/10.1109/50.511954
3. Yee 1966 IEEE TAP（FDTD）
   https://doi.org/10.1109/TAP.1966.1138693
4. Chang 1980 IEEE TMTT（varFDTD EIM）
   https://doi.org/10.1109/TMTT.1980.1130198
5. Moharam 1995 JOSA A（RCWA ETM）
   https://doi.org/10.1364/JOSAA.12.001077
6. Feit & Fleck 1978 Appl. Opt.（BPM）
   https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
7. Soref 1993 IEEE JQE（Si/SiO2 折射率）
   https://ieeexplore.ieee.org/document/1148303

================================================================
合规声明
================================================================
- R02 学术诚信: 文献 URL 可溯源
- R03 禁止 fall-back: 测试用真实求解器，无 mock
- R04 不参与 GPU: 纯 CPU
- R05 无 TODO/FIXME/HACK
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

from polaris_core import (  # noqa: E402
    DeviceLevelSolver,
    DeviceSolverConfig,
    DeviceSolverResult,
    solve_device,
)


# =============================================================================
# 1. DeviceSolverConfig 构造与校验
# =============================================================================


def test_config_defaults():
    """DeviceSolverConfig 默认 method=auto, wavelength=1.55。"""
    cfg = DeviceSolverConfig()
    assert cfg.method == "auto"
    assert cfg.wavelength_um == 1.55
    assert cfg.n_modes == 4


def test_config_invalid_method_raises():
    """非法 method raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="method"):
        DeviceSolverConfig(method="invalid_solver")


def test_config_invalid_wavelength_raises():
    """非法 wavelength ≤ 0 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="wavelength_um"):
        DeviceSolverConfig(wavelength_um=0.0)


# =============================================================================
# 2. _select_method 自动选择策略
# =============================================================================


def test_select_method_eme_1d():
    """1D slab 波导（sections 无 height_um）→ eme。"""
    solver = DeviceLevelSolver()
    geom = {"type": "waveguide", "sections": [
        {"width_um": 0.5, "length_um": 5.0, "n_core": 3.476, "n_clad": 1.444}]}
    assert solver._select_method(geom) == "eme"


def test_select_method_grating_rcwa():
    """周期性光栅（is_periodic）→ rcwa。"""
    solver = DeviceLevelSolver()
    geom = {"is_periodic": True, "layers": [], "period_um": 1.0}
    assert solver._select_method(geom) == "rcwa"
    geom2 = {"type": "grating", "layers": []}
    assert solver._select_method(geom2) == "rcwa"


def test_select_method_mode_analysis_fde():
    """模式分析 → fde。"""
    solver = DeviceLevelSolver()
    geom = {"type": "mode_analysis", "width_um": 0.5, "height_um": 0.22}
    assert solver._select_method(geom) == "fde"


def test_select_method_propagation_varfdtd():
    """2.5D 传播 → varfdtd。"""
    solver = DeviceLevelSolver()
    geom = {"type": "propagation_2_5d", "width_um": 2.0, "height_um": 2.0}
    assert solver._select_method(geom) == "varfdtd"


def test_select_method_beam_propagation_bpm():
    """光束传播 → bpm。"""
    solver = DeviceLevelSolver()
    geom = {"type": "beam_propagation", "width_um": 0.5, "length_um": 20.0}
    assert solver._select_method(geom) == "bpm"


def test_select_method_full_3d_fdtd():
    """全 3D → fdtd。"""
    solver = DeviceLevelSolver()
    geom = {"type": "full_3d"}
    assert solver._select_method(geom) == "fdtd"


# =============================================================================
# 3. EME 1D 委托
# =============================================================================


def test_solve_eme_1d_delegation():
    """EME 1D 委托: 单段直波导 |T| ≈ 1，solver_used=eme, eme_dim=1d。"""
    cfg = DeviceSolverConfig(method="auto", wavelength_um=1.55,
                             dx_um=0.01, pad_um=1.0, n_modes=2)
    solver = DeviceLevelSolver(cfg)
    geom = {"type": "waveguide", "sections": [
        {"width_um": 0.5, "length_um": 10.0, "n_core": 3.476, "n_clad": 1.444}]}
    result = solver.solve(geom)
    assert isinstance(result, DeviceSolverResult)
    assert result.solver_used == "eme"
    assert result.metadata["eme_dim"] == "1d"
    assert result.s_matrix is not None
    assert result.s_matrix.shape == (2, 2)
    t_abs = abs(result.s_matrix[1, 0])
    assert math.isclose(t_abs, 1.0, rel_tol=1e-9), (
        f"单段直波导 |T| 应 = 1，得到 {t_abs}"
    )


# =============================================================================
# 4. EME 2D 委托
# =============================================================================


def test_solve_eme_2d_delegation():
    """EME 2D 委托: sections 含 height_um → eme_dim=2d，|T| ≈ 1。"""
    cfg = DeviceSolverConfig(method="auto", wavelength_um=1.55,
                             dx_um=0.02, dy_um=0.02, pad_um=1.0, n_modes=2)
    solver = DeviceLevelSolver(cfg)
    geom = {"type": "waveguide", "sections": [
        {"width_um": 0.5, "height_um": 0.22, "length_um": 5.0,
         "n_core": 3.476, "n_clad": 1.444}]}
    result = solver.solve(geom)
    assert result.solver_used == "eme"
    assert result.metadata["eme_dim"] == "2d"
    t_abs = abs(result.s_matrix[1, 0])
    assert math.isclose(t_abs, 1.0, rel_tol=1e-9), (
        f"单段 2D 直波导 |T| 应 = 1，得到 {t_abs}"
    )
    # 模式信息含 neff，且在导模范围
    assert len(result.modes) == 1
    assert 1.444 < result.modes[0]["neff"] < 3.476


# =============================================================================
# 5. FDE 委托
# =============================================================================


def test_solve_fde_delegation():
    """FDE 委托: 模式分析 → modes 非空，neff ∈ (n_clad, n_core)，field_profile 2D。"""
    cfg = DeviceSolverConfig(method="fde", wavelength_um=1.55,
                             dx_um=0.02, pad_um=1.0, n_modes=4)
    solver = DeviceLevelSolver(cfg)
    geom = {"type": "mode_analysis", "width_um": 0.5, "height_um": 0.22,
            "n_core": 3.476, "n_clad": 1.444}
    result = solver.solve(geom)
    assert result.solver_used == "fde"
    assert result.s_matrix is None  # FDE 不产生 S 矩阵
    assert len(result.modes) >= 1
    assert 1.444 < result.modes[0]["neff"] < 3.476
    assert result.field_profile is not None
    assert result.field_profile.ndim == 2


# =============================================================================
# 6. RCWA 委托
# =============================================================================


def test_solve_rcwa_delegation():
    """RCWA 委托: 均匀空气层能量守恒 Σ(R+T)≈1，solver_used=rcwa。"""
    cfg = DeviceSolverConfig(method="rcwa", wavelength_um=1.55,
                             n_harmonics_rcwa=3)
    solver = DeviceLevelSolver(cfg)
    geom = {
        "is_periodic": True,
        "period_um": 1.0,
        "layers": [{"thickness": 200e-9, "eps_r_period": np.full(8, 1.0)}],
    }
    result = solver.solve(geom)
    assert result.solver_used == "rcwa"
    assert result.s_matrix is not None
    assert result.s_matrix.shape == (2, 2)
    # 均匀空气层无反射、全透射，能量守恒
    assert abs(result.metadata["energy_sum"] - 1.0) < 1e-6, (
        f"能量守恒违反: Σ(R+T)={result.metadata['energy_sum']}"
    )
    assert result.metadata["reflection_eff_0th"] < 1e-6
    assert result.metadata["transmission_eff_0th"] > 0.99


# =============================================================================
# 7. BPM 委托
# =============================================================================


def test_solve_bpm_delegation():
    """BPM 委托: transmission_db 有限，solver_used=bpm，S21 = 10^(dB/20)。"""
    cfg = DeviceSolverConfig(method="bpm", wavelength_um=1.55,
                             dx_um=0.01, dz_um=0.1, pad_um=2.0)
    solver = DeviceLevelSolver(cfg)
    geom = {"type": "beam_propagation", "width_um": 0.5, "length_um": 20.0,
            "n_core": 3.476, "n_clad": 1.444}
    result = solver.solve(geom)
    assert result.solver_used == "bpm"
    assert result.s_matrix is not None
    t_db = result.metadata["transmission_db"]
    assert math.isfinite(t_db), f"transmission_db 须有限，得到 {t_db}"
    # S21 振幅 = 10^(dB/20)
    t_lin = float(10.0 ** (t_db / 20.0))
    assert abs(abs(result.s_matrix[1, 0]) - t_lin) < 1e-9


# =============================================================================
# 8. varFDTD 委托
# =============================================================================


def test_solve_varfdtd_delegation():
    """varFDTD 委托: field_profile 有限，solver_used=varfdtd。"""
    n_eff_arr = np.full((20, 20), 2.8)  # 均匀有效折射率（Lumerical varFDTD 典型）
    cfg = DeviceSolverConfig(method="varfdtd", wavelength_um=1.55,
                             dx_um=0.05, dy_um=0.05, n_steps_varfdtd=10)
    solver = DeviceLevelSolver(cfg)
    geom = {"type": "propagation_2_5d", "n_eff_arr": n_eff_arr}
    result = solver.solve(geom)
    assert result.solver_used == "varfdtd"
    assert result.field_profile is not None
    assert np.all(np.isfinite(result.field_profile)), "varFDTD 场含 NaN/Inf"
    assert result.metadata["n_steps"] == 10


# =============================================================================
# 9. FDTD 委托
# =============================================================================


def test_solve_fdtd_delegation():
    """FDTD 委托: T_fdtd ∈ (0,1]，solver_used=fdtd。"""
    cfg = DeviceSolverConfig(method="fdtd", wavelength_um=1.55,
                             dx_um=0.1, n_steps_fdtd=200)
    solver = DeviceLevelSolver(cfg)
    geom = {"type": "full_3d", "nx": 32, "ny": 24, "nz": 20, "pml_layers": 4}
    result = solver.solve(geom)
    assert result.solver_used == "fdtd"
    assert result.s_matrix is not None
    t_fdtd = result.metadata["T_fdtd"]
    assert math.isfinite(t_fdtd), f"T_fdtd 须有限，得到 {t_fdtd}"
    assert 0.0 < t_fdtd <= 1.0, f"T_fdtd 应 ∈ (0,1]，得到 {t_fdtd}"
    assert result.metadata["pml_enabled"] is True


# =============================================================================
# 10. solve_device 便捷入口 + 显式 method 覆盖
# =============================================================================


def test_solve_device_convenience_eme():
    """solve_device 便捷入口: 自动选择 EME。"""
    geom = {"sections": [
        {"width_um": 0.5, "length_um": 5.0, "n_core": 3.476, "n_clad": 1.444}]}
    result = solve_device(geom, wavelength_um=1.55, method="auto")
    assert isinstance(result, DeviceSolverResult)
    assert result.solver_used == "eme"


def test_solve_device_explicit_fde():
    """solve_device 显式 method=fde 覆盖 auto。"""
    geom = {"type": "waveguide", "width_um": 0.5, "height_um": 0.22,
            "n_core": 3.476, "n_clad": 1.444}
    result = solve_device(geom, wavelength_um=1.55, method="fde")
    assert result.solver_used == "fde"


def test_solve_device_invalid_method_raises():
    """solve_device 非法 method raise（R03 禁止 fall-back）。"""
    geom = {"type": "waveguide"}
    with pytest.raises(ValueError, match="method"):
        solve_device(geom, method="nonexistent")


def test_solve_invalid_geometry_raises():
    """geometry 非 dict raise（R03 禁止 fall-back）。"""
    solver = DeviceLevelSolver()
    with pytest.raises(ValueError, match="geometry"):
        solver.solve("not_a_dict")  # type: ignore[arg-type]


def test_solve_eme_missing_sections_raises():
    """EME 缺 sections raise（R03 禁止 fall-back）。"""
    solver = DeviceLevelSolver(DeviceSolverConfig(method="eme"))
    with pytest.raises(ValueError, match="sections"):
        solver.solve({"type": "waveguide"})
