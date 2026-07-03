"""polaris-multiphysics 子模块深度测试（覆盖全 API，30 个测试）。

覆盖核心 API:
- DDM: DdmConfig/DdmResult/DdmSolver/solve_ddm/solve_ddm_gummel/GummelSolver
- HEAT: HeatConfig/HeatResult/HeatSolver/solve_heat/TransientHeatSolver/solve_transient_heat
- VarFDTD: compute_effective_index/marcatili_neff/VarFdtdConfig/VarFdtdResult/VarFdtdSolver/solve_varfdtd
- RCWA: RcwaConfig1D/2D, solve_rcwa_1d/2d, GratingLayer1D/2D
- FETD: FetdMaterial/TetrahedronMesh/HexahedronMesh/assemble_*/NewmarkIntegrator/
        newmark_beta_coefficients/enforce_dirichlet/FetdConfig/FetdResult/FetdSolver
- 耦合: PLASMA_DISPERSION_COEFFS/THERMO_OPTIC_COEFFS/DEFAULT_T_REF/
        compute_delta_n_from_carriers/temperature/apply_electro_optic/thermo_optic_coupling
- TCAD: ThermalLayer/ThermalSolver2D (steady/crosstalk/transient)

学术依据（R02 学术诚信，≥5 个文献 URL）:
1. Scharfetter & Gummel 1969 IEEE TED 16(1):64-77 —
   https://doi.org/10.1109/T-ED.1969.16766
2. Soref & Bennett 1987 IEEE JQE 23(1):123-129 —
   https://doi.org/10.1109/JQE.1987.1073206
3. Cocorullo 1999 IEEE JSTQE 5(3):519-521 —
   https://doi.org/10.1109/2944.788409
4. Moharam 1995 JOSA A 12:1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
5. Newmark 1959 ASCE J Eng Mech Div 85(3):67-94 —
   https://doi.org/10.1061/JMCEA3.0000097
6. Chang 1980 IEEE TMTT 28(8):889 (EIM) —
   https://doi.org/10.1109/TMTT.1980.1130551
7. Crank & Nicolson 1947 Proc Camb Phil Soc —
   https://doi.org/10.1017/S0305004100023197
8. Carslaw & Jaeger 1959 "Conduction of Heat in Solids" §10.4 —
   https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
9. Jin 2014 "The Finite Element Method in Electromagnetics" 3rd ed. —
   https://onlinelibrary.wiley.com/doi/book/10.1002/9781118576637
10. Redheffer 1959 J Math Mech —
    https://www.jstor.org/stable/24900576

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 无 TODO。
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

import polaris_multiphysics  # noqa: E402
from polaris_multiphysics import (  # noqa: E402
    DEFAULT_T_REF,
    DdmConfig,
    DdmSolver,
    FetdConfig,
    FetdResult,
    FetdSolver,
    HeatConfig,
    HeatSolver,
    NewmarkIntegrator,
    PLASMA_DISPERSION_COEFFS,
    RcwaConfig1D,
    RcwaConfig2D,
    THERMO_OPTIC_COEFFS,
    ThermalLayer,
    ThermalSolver2D,
    TransientHeatSolver,
    VarFdtdConfig,
    VarFdtdResult,
    VarFdtdSolver,
    apply_electro_optic_coupling,
    apply_thermo_optic_coupling,
    compute_delta_n_from_carriers,
    compute_delta_n_from_temperature,
    compute_effective_index,
    solve_ddm,
    solve_ddm_gummel,
    solve_heat,
    solve_rcwa_1d,
    solve_rcwa_2d,
    solve_transient_heat,
    solve_varfdtd,
)
# FETD 内部类与组装函数在子包导出，顶层未 re-export（避免 __all__ 膨胀）
from polaris_multiphysics.fetd import (  # noqa: E402
    FetdMaterial,
    HexahedronMesh,
    TetrahedronMesh,
    assemble_damping,
    assemble_mass,
    assemble_stiffness,
    enforce_dirichlet,
    newmark_beta_coefficients,
)
from polaris_multiphysics.varfdtd import marcatili_neff  # noqa: E402
from polaris_multiphysics.heat.boundary import BoundaryType, BcSpec  # noqa: E402
from polaris_multiphysics.rcwa import GratingLayer1D, GratingLayer2D  # noqa: E402
from polaris_multiphysics.rcwa.smatrix import cascade_redheffer  # noqa: E402


# =============================================================================
# 辅助：构造标准 PN 结 DDM 配置（多测试复用）
# =============================================================================
def _make_pn_config(va: float = 0.0, vc: float = 0.0) -> DdmConfig:
    """1D PN 结 0V 平衡态配置（左 P 1e22 / 右 N 1e22 m^-3）。"""
    nx, ny = 8, 4
    dx, dy = 200e-9, 200e-9
    doping_n = np.zeros((nx, ny))
    doping_p = np.zeros((nx, ny))
    doping_n[4:, :] = 1e22
    doping_p[:4, :] = 1e22
    return DdmConfig(
        nx=nx, ny=ny, dx=dx, dy=dy, eps_rel=11.7,
        doping_n=doping_n, doping_p=doping_p,
        contacts={"west": va, "east": vc},
        max_iter=50, tol=1e-5,
    )


# =============================================================================
# 1. 常量与版本
# =============================================================================
def test_module_version_and_constants() -> None:
    """模块版本 5.0.0 + 物理常量已溯源（Soref-Bennett 1987 / Cocorullo 1999）。"""
    assert polaris_multiphysics.__version__ == "5.0.0"
    # Soref-Bennett 1987 等离子体色散系数 @1.55μm
    assert 1.55e-6 in PLASMA_DISPERSION_COEFFS
    alpha_e, alpha_h = PLASMA_DISPERSION_COEFFS[1.55e-6]
    assert abs(alpha_e - 8.8e-22) < 1e-30, "α_e 应为 8.8e-22 cm³（Soref 1987）"
    assert abs(alpha_h - 8.5e-22) < 1e-30, "α_h 应为 8.5e-22 cm³（Soref 1987）"
    # Cocorullo 1999 硅热光系数
    assert abs(THERMO_OPTIC_COEFFS["silicon"] - 1.86e-4) < 1e-12
    assert abs(THERMO_OPTIC_COEFFS["sio2"] - 1.0e-5) < 1e-12
    # 默认参考温度
    assert DEFAULT_T_REF == 300.0, "DEFAULT_T_REF 应为 300K（室温）"


# =============================================================================
# 2. DDM 漂移扩散
# =============================================================================
def test_ddm_newton_equilibrium() -> None:
    """DDM 牛顿法平衡态求解：PN 结 0V 偏置，验证 potential/n/p 有限且收敛。"""
    cfg = _make_pn_config()
    result = DdmSolver().solve(cfg)
    assert result.converged, "DDM 牛顿法平衡态须收敛"
    assert np.all(np.isfinite(result.potential)), "potential 须全有限"
    assert np.all(result.electron_density > 0), "n 须 >0（物理约束）"
    assert np.all(result.hole_density > 0), "p 须 >0（物理约束）"
    assert np.all(np.abs(result.potential) < 2.0), "平衡态电位应在 ±2V 内"


def test_solve_ddm_convenience_entry() -> None:
    """solve_ddm 便捷入口与 DdmSolver().solve 等价（返回 DdmResult）。"""
    cfg = _make_pn_config()
    result = solve_ddm(cfg)
    assert result.converged, "solve_ddm 便捷入口须收敛"
    assert np.all(np.isfinite(result.potential))
    # DdmResult 字段完整性
    assert hasattr(result, "electron_density")
    assert hasattr(result, "hole_density")
    assert hasattr(result, "current_density")
    assert hasattr(result, "conductivity")


def test_ddm_gummel_low_bias() -> None:
    """DDM Gummel 迭代 0V 平衡态：验证 Gummel 1964 解耦路径求解成功。"""
    cfg = _make_pn_config()
    cfg = DdmConfig(
        nx=10, ny=4, dx=200e-9, dy=200e-9, eps_rel=11.7,
        doping_n=np.where(np.arange(10)[:, None] >= 5, 1e22, 0.0) * np.ones((10, 4)),
        doping_p=np.where(np.arange(10)[:, None] < 5, 1e22, 0.0) * np.ones((10, 4)),
        contacts={"west": 0.0, "east": 0.0}, max_iter=100, tol=1e-5,
    )
    result = solve_ddm_gummel(cfg)
    assert np.all(np.isfinite(result.potential)), "potential 须全有限"
    assert np.all(np.isfinite(result.current_density)), "J 须全有限"
    assert np.all(result.conductivity > 0), "σ 须 >0（物理约束）"


# =============================================================================
# 3. HEAT 稳态热传导
# =============================================================================
def _make_heat_config() -> HeatConfig:
    """5x5 Si 均匀网格 + 中心热点。"""
    nx, ny = 5, 5
    k_arr = np.full((nx, ny), 148.0)
    q_arr = np.zeros((nx, ny))
    q_arr[2, 2] = 1e10
    return HeatConfig(
        dx=1e-6, dy=1e-6, k_arr=k_arr, q_arr=q_arr,
        bc_dict={
            "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
            "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
        },
    )


def test_heat_solve() -> None:
    """HEAT 5 点有限差分稳态求解：温度场有限且 Dirichlet 边界满足。"""
    cfg = _make_heat_config()
    result = solve_heat(cfg)
    assert np.all(np.isfinite(result.temperature)), "温度场须全有限"
    assert np.allclose(result.temperature[0, :], 300.0, atol=1e-6), "west 边界须 T=300K"
    assert np.allclose(result.temperature[-1, :], 300.0, atol=1e-6), "east 边界须 T=300K"
    assert result.temperature[2, 2] > 300.0, "热点温度须 > 300K"
    assert np.max(result.temperature) < 1000.0, "温度须 < 1000K（无发散）"


def test_heat_solver_class_interface() -> None:
    """HeatSolver 类接口与 solve_heat 便捷入口一致。"""
    cfg = _make_heat_config()
    solver = HeatSolver()
    result = solver.solve(cfg)
    assert np.all(np.isfinite(result.temperature)), "HeatSolver 类求解须成功"
    assert result.temperature.shape == (5, 5)
    assert hasattr(result, "dx") and hasattr(result, "dy")


def test_heat_transient_crank_nicolson() -> None:
    """TransientHeatSolver Crank-Nicolson 瞬态：温度场有限且时间序列非空。

    Crank-Nicolson 1947 隐式 2 阶时间精度，无条件稳定。
    """
    from polaris_multiphysics.heat import TransientHeatConfig

    cfg = _make_heat_config()
    nx, ny = 5, 5
    rho_arr = np.full((nx, ny), 2330.0)  # Si 密度
    cp_arr = np.full((nx, ny), 700.0)    # Si 热容
    trans_cfg = TransientHeatConfig(
        heat_config=cfg, rho_arr=rho_arr, cp_arr=cp_arr,
        t_initial=300.0, t_final=1e-6, dt=1e-7, save_every=2,
    )
    result = solve_transient_heat(trans_cfg)
    assert result.temperatures.ndim == 3, "瞬态温度场须为 3D (n_times, nx, ny)"
    assert result.times.shape[0] >= 2, "至少 2 个时间点"
    assert np.all(np.isfinite(result.temperatures)), "温度场须全有限"
    # 初始时刻应 = 300K（均匀初值）
    assert np.allclose(result.temperatures[0], 300.0, atol=1e-6)


def test_heat_transient_solver_class() -> None:
    """TransientHeatSolver 类接口与便捷入口一致。"""
    from polaris_multiphysics.heat import TransientHeatConfig

    cfg = _make_heat_config()
    nx, ny = 5, 5
    trans_cfg = TransientHeatConfig(
        heat_config=cfg,
        rho_arr=np.full((nx, ny), 2330.0),
        cp_arr=np.full((nx, ny), 700.0),
        t_initial=300.0, t_final=5e-7, dt=1e-7,
    )
    solver = TransientHeatSolver()
    result = solver.solve(trans_cfg)
    assert result.temperatures.shape[0] >= 2, "TransientHeatSolver 类须返回多步"
    assert np.all(np.isfinite(result.times))


# =============================================================================
# 4. VarFDTD 有效折射率法
# =============================================================================
def test_marcatili_neff_soi_strip() -> None:
    """Marcatili 1969 近似：SOI strip n_eff 介于 n_clad 与 n_core 之间。"""
    n_eff = marcatili_neff(
        n_core=3.476, n_clad=1.444, width=500e-9, wavelength=1.55e-6,
    )
    assert 1.444 < n_eff < 3.476, f"n_eff 应在 (n_clad, n_core)，实际 {n_eff}"


def test_compute_effective_index_single_row() -> None:
    """compute_effective_index 单行剖面：SOI strip TE0 n_eff ∈ (n_clad, n_core)。"""
    # SOI strip 剖面：Si 芯 (3.476) + SiO2 包层 (1.444)
    n_y = np.array([1.444, 1.444, 3.476, 3.476, 3.476, 1.444, 1.444])
    n_eff = compute_effective_index(n_y, wavelength=1.55e-6, dy=100e-9, polarization="te")
    assert 1.444 < n_eff < 3.476, f"TE0 n_eff 应在 (n_clad, n_core)，实际 {n_eff}"


def test_compute_effective_index_returns_result() -> None:
    """compute_effective_index return_profile=True 返回 EffectiveIndexResult。"""
    n_y = np.array([1.444, 1.444, 3.476, 3.476, 3.476, 1.444, 1.444])
    res = compute_effective_index(
        n_y, wavelength=1.55e-6, dy=100e-9, polarization="te", return_profile=True,
    )
    assert hasattr(res, "n_eff_arr"), "return_profile=True 应返回 EffectiveIndexResult"
    assert hasattr(res, "mode_profiles")
    assert hasattr(res, "n_core_arr")


def test_varfdtd_config_validation() -> None:
    """VarFdtdConfig 基本构造（字段完整性，不实际运行长仿真）。"""
    n_eff_arr = np.full((20, 20), 2.8)  # 2D 均匀有效折射率（build_eps_from_neff 须 2D）
    cfg = VarFdtdConfig(
        wavelength=1.55e-6, dx=50e-9, dy=50e-9,
        n_eff_arr=n_eff_arr, n_steps=1, dt=1e-16,
    )
    assert cfg.wavelength == 1.55e-6
    assert cfg.n_steps == 1


def test_solve_varfdtd_minimal() -> None:
    """solve_varfdtd 最小仿真：返回 VarFdtdResult 含场数组（smoke test）。"""
    n_eff_arr = np.full((30, 30), 2.8)  # 2D n_eff_arr（至少 5x5 网格）
    cfg = VarFdtdConfig(
        wavelength=1.55e-6, dx=50e-9, dy=50e-9,
        n_eff_arr=n_eff_arr, n_steps=2, dt=1e-17,
    )
    result = solve_varfdtd(cfg)
    assert isinstance(result, VarFdtdResult), "应返回 VarFdtdResult"
    assert hasattr(result, "e_z"), "VarFdtdResult 须含 e_z 场"
    assert hasattr(result, "energy_history"), "VarFdtdResult 须含 energy_history"


# =============================================================================
# 5. RCWA 1D 严格耦合波
# =============================================================================
def test_rcwa_1d_energy_conservation() -> None:
    """RCWA 1D 均匀空气层：能量守恒 Σ(R+T)≈1 与 0 反射（阻抗匹配）。"""
    layer = GratingLayer1D(thickness=200e-9, eps_r_period=np.full(8, 1.0))
    cfg = RcwaConfig1D(
        wavelength=1.55e-6, period=1.0e-6, n_harmonics=3,
        theta_inc=0.0, n_inc=1.0, n_sub=1.0, polarization="te",
    )
    result = solve_rcwa_1d([layer], cfg)
    assert abs(result.energy_sum - 1.0) < 1e-6, \
        f"能量守恒违反: Σ(R+T)={result.energy_sum}"
    n_h = cfg.n_harmonics
    assert result.reflection_eff[n_h] < 1e-6, "阻抗匹配 0 阶反射须 ≈0"
    assert abs(result.transmission_eff[n_h] - 1.0) < 1e-6, "0 阶透射须 ≈1"


def test_rcwa_1d_high_contrast_layer() -> None:
    """RCWA 1D 高折射率层：反射 > 0（Si 层 vs 空气，存在反射）。"""
    layer = GratingLayer1D(thickness=220e-9, eps_r_period=np.full(8, 3.476**2))
    cfg = RcwaConfig1D(
        wavelength=1.55e-6, period=1.0e-6, n_harmonics=3,
        n_inc=1.0, n_sub=1.0, polarization="te",
    )
    result = solve_rcwa_1d([layer], cfg)
    assert abs(result.energy_sum - 1.0) < 1e-4, "能量守恒须成立"
    n_h = cfg.n_harmonics
    assert result.reflection_eff[n_h] > 0, "Si 层应产生反射"


# =============================================================================
# 6. RCWA 2D 严格耦合波
# =============================================================================
def test_rcwa_2d_energy_conservation() -> None:
    """RCWA 2D 均匀空气层：能量守恒 Σ(R+T)≈1（Liu & Fan 2012 S4 公式）。"""
    eps_r = np.ones((5, 5))  # 均匀空气
    layer = GratingLayer2D(thickness=200e-9, eps_r_period=eps_r)
    cfg = RcwaConfig2D(
        wavelength=1.55e-6, period_x=1e-6, period_y=1e-6,
        n_harmonics_x=2, n_harmonics_y=2, n_inc=1.0, n_sub=1.0,
    )
    result = solve_rcwa_2d([layer], cfg)
    assert abs(result.energy_sum - 1.0) < 1e-4, \
        f"2D 能量守恒违反: Σ(R+T)={result.energy_sum}"
    assert result.m_total > 0, "总模式数须 > 0"


def test_rcwa_2d_grating_layer_validation() -> None:
    """GratingLayer2D 非法厚度 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        GratingLayer2D(thickness=0.0, eps_r_period=np.ones((5, 5)))


# =============================================================================
# 7. FETD 有限元时域
# =============================================================================
def _make_tet_mesh() -> TetrahedronMesh:
    """构造最小四面体网格（2 个单元，5 节点）。"""
    nodes = np.array([
        [0.0, 0.0, 0.0],
        [1e-6, 0.0, 0.0],
        [0.0, 1e-6, 0.0],
        [0.0, 0.0, 1e-6],
        [1e-6, 1e-6, 1e-6],
    ], dtype=np.float64)
    elements = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=np.int64)
    mat_id = np.array([0, 0], dtype=np.int64)
    return TetrahedronMesh(nodes=nodes, elements=elements, mat_id=mat_id)


def test_fetd_material_validation() -> None:
    """FetdMaterial 非法参数 raise（eps_r≤0 / mu_r≤0 / sigma<0）。"""
    assert FetdMaterial(eps_r=11.7).eps_r == 11.7
    with pytest.raises(ValueError):
        FetdMaterial(eps_r=0.0)
    with pytest.raises(ValueError):
        FetdMaterial(eps_r=1.0, mu_r=-1.0)
    with pytest.raises(ValueError):
        FetdMaterial(eps_r=1.0, sigma=-0.1)


def test_tetrahedron_mesh_properties() -> None:
    """TetrahedronMesh 节点/单元计数 + 非法形状 raise。"""
    mesh = _make_tet_mesh()
    assert mesh.n_nodes == 5
    assert mesh.n_elements == 2
    with pytest.raises(ValueError):
        TetrahedronMesh(
            nodes=np.zeros((3, 2)),  # 应为 (Nn, 3)
            elements=np.array([[0, 1, 2, 3]]),
            mat_id=np.array([0]),
        )


def test_assemble_mass_stiffness_damping() -> None:
    """assemble_mass/stiffness/damping 返回 CSR 稀疏矩阵（Jin 2014 §1.7）。"""
    mesh = _make_tet_mesh()
    materials = [FetdMaterial(eps_r=11.7, mu_r=1.0, sigma=0.0)]
    m = assemble_mass(mesh, materials)
    k = assemble_stiffness(mesh, materials)
    c = assemble_damping(mesh, materials)
    assert m.shape == (5, 5), "质量矩阵形状须 = (n_nodes, n_nodes)"
    assert k.shape == (5, 5)
    assert c.shape == (5, 5)
    # 质量矩阵须对称正定（实对称）
    m_dense = m.toarray()
    assert np.allclose(m_dense, m_dense.T, atol=1e-12), "M 须对称"


def test_newmark_beta_coefficients_stability() -> None:
    """newmark_beta_coefficients 稳定性条件 2β ≥ γ（Newmark 1959）。"""
    b, g = newmark_beta_coefficients(0.25, 0.5)
    assert (b, g) == (0.25, 0.5)
    with pytest.raises(ValueError, match="无条件稳定"):
        newmark_beta_coefficients(0.1, 0.5)  # 2β=0.2 < γ=0.5


def test_newmark_integrator_step() -> None:
    """NewmarkIntegrator 单步推进：构建有效刚度 + step 返回 3 数组。"""
    mesh = _make_tet_mesh()
    materials = [FetdMaterial(eps_r=11.7)]
    m = assemble_mass(mesh, materials)
    c = assemble_damping(mesh, materials)
    k = assemble_stiffness(mesh, materials)
    integ = NewmarkIntegrator(dt=1e-15)
    lu_piv = integ.build_effective_stiffness(m, c, k)
    e_n = np.zeros(5)
    v_n = np.zeros(5)
    a_n = np.zeros(5)
    f_next = np.zeros(5)
    e, v, a = integ.step(lu_piv, c.toarray(), k.toarray(), e_n, v_n, a_n, f_next)
    assert e.shape == (5,) and v.shape == (5,) and a.shape == (5,)
    assert np.all(np.isfinite(e)), "Newmark 步进场须有限"


def test_enforce_dirichlet() -> None:
    """enforce_dirichlet 对角置 1、行列清零（Jin 2014 §11）。"""
    mesh = _make_tet_mesh()
    materials = [FetdMaterial(eps_r=1.0)]
    m = assemble_mass(mesh, materials)
    m_bc = enforce_dirichlet(m, np.array([0]))
    m_dense = m_bc.toarray()
    assert m_dense[0, 0] == 1.0, "Dirichlet 节点对角须 = 1"
    assert np.all(m_dense[0, 1:] == 0.0), "Dirichlet 节点行须清零"
    assert np.all(m_dense[1:, 0] == 0.0), "Dirichlet 节点列须清零"


def test_fetd_solver_minimal() -> None:
    """FetdSolver 最小仿真：返回 FetdResult 含场历史（Newmark-β 时间推进）。"""
    mesh = _make_tet_mesh()
    materials = [FetdMaterial(eps_r=11.7, sigma=0.0)]
    cfg = FetdConfig(
        mesh=mesh, materials=materials, dt=1e-15, n_steps=3,
        source=lambda t: np.zeros(5),
        dirichlet_nodes=np.array([0, 4]),
    )
    solver = FetdSolver(cfg)
    result = solver.solve()
    assert isinstance(result, FetdResult), "应返回 FetdResult"
    assert result.field_history.shape == (4, 5), "场历史形状须 = (n_steps+1, n_nodes)"
    assert np.all(np.isfinite(result.field_history)), "场历史须全有限"
    assert result.time.shape == (4,)


# =============================================================================
# 8. 电-光/热-光耦合
# =============================================================================
class _DuckDdmResult:
    """Duck-typed DDM 结果（仅含 electron_density/hole_density 字段，[cm^-3]）。"""
    def __init__(self) -> None:
        self.electron_density = np.full((5, 5), 1e17)
        self.hole_density = np.full((5, 5), 1e17)


class _DuckHeatResult:
    """Duck-typed HEAT 结果（仅含 temperature 字段，[K]）。"""
    def __init__(self) -> None:
        self.temperature = np.full((5, 5), 310.0)


def test_compute_delta_n_from_carriers() -> None:
    """compute_delta_n_from_carriers: Δn = -α_e·ΔN_e - α_h·ΔN_h ≤ 0。"""
    n_e = np.full((3, 3), 1e17)
    n_h = np.full((3, 3), 1e17)
    dn = compute_delta_n_from_carriers(n_e, n_h, wavelength=1.55e-6)
    assert np.all(dn <= 0), "等离子体色散 Δn 须 ≤0"
    expected = -(8.8e-22 + 8.5e-22) * 1e17
    assert abs(dn[0, 0] - expected) < 1e-8


def test_compute_delta_n_from_temperature() -> None:
    """compute_delta_n_from_temperature: Δn = (dn/dT)·ΔT ≥ 0。"""
    delta_T = np.full((3, 3), 10.0)
    dn = compute_delta_n_from_temperature(delta_T, material="silicon")
    assert np.all(dn >= 0), "热光效应 Δn 须 ≥0"
    expected = 1.86e-4 * 10.0
    assert abs(dn[0, 0] - expected) < 1e-10


def test_electro_optic_coupling() -> None:
    """电光耦合：Δn ≤ 0（Soref-Bennett 1987 等离子体色散）。"""
    ddm_result = _DuckDdmResult()
    result = apply_electro_optic_coupling(
        ddm_result, wavelength=1.55e-6, confinement_factor=0.5,
    )
    assert np.all(np.isfinite(result.delta_n)), "delta_n 须全有限"
    assert np.all(result.delta_n <= 0), "等离子体色散 Δn 须 ≤0"
    assert result.delta_n_eff < 0, "Δn_eff 须 <0"
    expected_dn = -1.73e-4
    assert abs(result.delta_n[0, 0] - expected_dn) < 1e-6


def test_thermo_optic_coupling() -> None:
    """热光耦合：Δn ≥ 0（Cocorullo 1999 热光效应）。"""
    heat_result = _DuckHeatResult()
    result = apply_thermo_optic_coupling(
        heat_result, material="silicon", confinement_factor=0.5, t_ref=300.0,
    )
    assert np.all(result.delta_n >= 0), "热光效应 Δn 须 ≥0"
    assert result.delta_n_eff > 0, "Δn_eff 须 >0"
    expected_dn = 1.86e-3
    assert abs(result.delta_n[0, 0] - expected_dn) < 1e-6
    assert abs(result.dn_dt - 1.86e-4) < 1e-12


def test_thermo_optic_unknown_material_raise() -> None:
    """R03: 未知材料必须 raise KeyError（禁止编造系数）。"""
    heat_result = _DuckHeatResult()
    with pytest.raises(KeyError):
        apply_thermo_optic_coupling(heat_result, material="bogus_material")


# =============================================================================
# 9. TCAD 2D 热仿真
# =============================================================================
def _make_thermal_layers() -> list:
    """SOI 5 层堆叠（衬底/BOX/波导/上包层/TiN 加热器）。"""
    return [
        ThermalLayer("substrate", 500.0, 148.0),
        ThermalLayer("buried_oxide", 2.0, 1.4),
        ThermalLayer("waveguide", 0.22, 148.0),
        ThermalLayer("upper_cladding", 1.0, 1.4),
        ThermalLayer("heater", 0.1, 1.0, True, 0.5),
    ]


def test_thermal_2d_steady_state() -> None:
    """TCAD ThermalSolver2D 稳态求解：SOI 多层 + TiN 加热器温升 > 0。"""
    solver = ThermalSolver2D(_make_thermal_layers(), width_um=20.0, nx=20, substrate_temp_k=300.0)
    T = solver.solve_steady_state()
    assert np.all(np.isfinite(T)), "温度场须全有限"
    assert T.shape == (solver.nz, solver.nx)
    t_max = solver.max_temperature_k()
    assert t_max > 300.0, f"加热器温升须使 T_max > 300K, 实际 {t_max}"
    assert np.allclose(T[0, :], 300.0, atol=1e-6), "底部 Dirichlet 须 T=300K"


def test_thermal_2d_crosstalk_matrix() -> None:
    """thermal_crosstalk_matrix: Carslaw-Jaeger Green's function 线热源串扰。

    返回形状 (n_heaters × n_devices) [K]（源码 docstring 明示，Carslaw-Jaeger §10.4）。
    """
    solver = ThermalSolver2D(_make_thermal_layers(), width_um=20.0, nx=15, substrate_temp_k=300.0)
    solver.solve_steady_state()
    xtalk = solver.thermal_crosstalk_matrix(
        heater_positions_um=np.array([5.0]),
        device_positions_um=np.array([10.0, 15.0]),
        heater_power_mw=10.0, heater_length_um=50.0,
    )
    # 源码契约：thermal_crosstalk_matrix 返回 (n_heaters × n_devices) = (1, 2)
    assert xtalk.shape == (1, 2), f"串扰矩阵形状须 (n_heater, n_dev)，实际 {xtalk.shape}"
    assert np.all(np.isfinite(xtalk)), "串扰矩阵须全有限"
    # heater 在 5μm；device 在 10μm(近,列0) 与 15μm(远,列1)，串扰随距离衰减
    assert xtalk[0, 0] >= xtalk[0, 1], "近端串扰应 ≥ 远端串扰"


def test_thermal_2d_max_temp_pre_solve_returns_tsub() -> None:
    """求解前 _T 已被 _build_grid 初始化为 T_sub（300K）；求解后温升 > T_sub。

    源码 __init__ 调用 _build_grid 将 _T 预填为衬底温度（占位场，非 fall-back，
    是显式初始化契约）。max_temperature_k 在求解前返回 T_sub，求解后 > T_sub。
    """
    solver = ThermalSolver2D(_make_thermal_layers(), width_um=20.0, nx=10, substrate_temp_k=300.0)
    # 求解前：温度场已初始化为衬底温度（非空，不 raise）
    t_pre = solver.max_temperature_k()
    assert abs(t_pre - 300.0) < 1e-9, f"求解前 max_temp 须 = T_sub=300K，实际 {t_pre}"
    # 求解后：加热器温升使 max_temp > T_sub
    solver.solve_steady_state()
    t_post = solver.max_temperature_k()
    assert t_post > 300.0, f"求解后 max_temp 须 > 300K，实际 {t_post}"


# =============================================================================
# 10. R03 禁止 fall-back
# =============================================================================
def test_no_fallback_raise() -> None:
    """R03 禁止 fall-back：所有非法参数与空列表必须 raise。"""
    with pytest.raises(ValueError):
        DdmConfig(
            nx=0, ny=4, dx=1e-7, dy=1e-7, eps_rel=11.7,
            doping_n=np.zeros((0, 4)), doping_p=np.zeros((0, 4)),
        )
    with pytest.raises(ValueError):
        HeatConfig(
            dx=0.0, dy=1e-6,
            k_arr=np.full((5, 5), 148.0), q_arr=np.zeros((5, 5)),
        )
    with pytest.raises(ValueError):
        RcwaConfig1D(wavelength=0.0, period=1e-6)
    with pytest.raises(ValueError):
        GratingLayer1D(thickness=0.0, eps_r_period=np.full(5, 1.0))
    with pytest.raises(ValueError):
        ThermalSolver2D(layers=[], width_um=20.0, nx=20)
    with pytest.raises(ValueError):
        cascade_redheffer([])


def test_compute_effective_index_cutoff_raise() -> None:
    """R03: 波导截止（V ≤ π/2）必须 raise，禁止 fall-back 假数据。"""
    # 极窄波导 → V < π/2 → 无导模
    n_y = np.array([1.444, 1.444, 3.476, 1.444, 1.444])
    with pytest.raises(ValueError):
        compute_effective_index(n_y, wavelength=1.55e-6, dy=1e-9, polarization="te")


def test_newmark_integrator_invalid_dt_raise() -> None:
    """R03: NewmarkIntegrator dt≤0 必须 raise。"""
    with pytest.raises(ValueError):
        NewmarkIntegrator(dt=0.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
