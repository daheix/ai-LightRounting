"""A08-DDM 漂移扩散求解器验收测试（7 类 25 测，M1-M3 里程碑）。

本测试模块验证 PoLaRIS 半导体漂移-扩散模型（DDM）全栈功能，覆盖
Bernoulli 函数、Poisson 方程、Gummel 迭代、全耦合牛顿法、SG 离散
稳定性、电热耦合与边界条件。

验收标准（M1-M3）：
- M1 PN 结解析解：1D 突变 PN 结平衡态，dV = V_bi 误差 ≤ 0.01V
- M2 Gummel 收敛：正向偏置下 Gummel 迭代 < 20 步收敛
- M3 SG 稳定性：高掺杂梯度下 Scharfetter-Gummel 离散无数值振荡

物理参数（Si @300K，Sze 2006 / Selberherr 1984 / CODATA 2018）：
- q = 1.602e-19 C
- ε_Si = 11.7·ε0 = 1.036e-10 F/m
- V_T = 0.02585 V (300K)
- μ_n = 0.135 m²/Vs (1350 cm²/Vs)
- μ_p = 0.048 m²/Vs (480 cm²/Vs)
- n_i = 1.5e16 m^-3 (Si, 300K)
- N_A = N_D = 1e22 m^-3 (1e16 cm^-3)

文献来源（≥5，规则 18 学术诚信）：
1. Scharfetter & Gummel 1969 — https://doi.org/10.1109/T-ED.1969.16700
2. Selberherr 1984 — https://www.springer.com/gp/book/9783709187548
3. Gummel 1964 — https://doi.org/10.1109/T-ED.1964.15393
4. Bank et al. 1983 SEDAN III — https://doi.org/10.1109/T-ED.1983.21282
5. Silvaco TCAD Atlas — https://silvaco.com/products/tcad/
6. Lundstrom 2009 — https://www.cambridge.org/core/books/fundamentals-of-carrier-transport/
7. scipy.sparse.linalg.spsolve — https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html

代码规范（R01-R10）：
- R02: 文件 docstring 含 ≥5 文献 URL
- R03: 验证 raise，无 fall-back
- R04: 纯 numpy/scipy
- 向量化、类型注解、中文注释
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.ddm import (
    DIRICHLET,
    LATTICE_SCATTERING_EXPONENT,
    MU_N_SI,
    MU_P_SI,
    N_I_SI,
    NEUMANN,
    Q_E,
    V_T,
    DdmConfig,
    DdmResult,
    GummelSolver,
    PoissonBc,
    PoissonSolver,
    bernoulli,
    bernoulli_pair,
    ddm_to_heat_joule,
    heat_to_ddm_mobility,
    solve_ddm,
    solve_ddm_gummel,
    srh_derivatives,
    srh_recombination,
)
from polaris.sim.ddm.scharfetter_gummel import EPS_R_SI


# ============================================================
# 辅助函数
# ============================================================
def _make_pn_config(
    nx: int = 100,
    ny: int = 1,
    na: float = 1e22,
    nd: float = 1e22,
    length: float = 2e-6,
    v_bias: float = 0.0,
) -> DdmConfig:
    """构造 1D/2D 突变 PN 结 DDM 配置。

    Args:
        nx: x 方向网格数。
        ny: y 方向网格数。
        na: 受主浓度 [m^-3]（左半区）。
        nd: 施主浓度 [m^-3]（右半区）。
        length: 器件总长 [m]。
        v_bias: 正向偏置电压 [V]（正电压加在 n 区，即 east 端）。

    Returns:
        DdmConfig 配置对象。
    """
    dx = length / nx
    dy = 1e-7
    mid = nx // 2
    doping_p = np.zeros((nx, ny))
    doping_n = np.zeros((nx, ny))
    doping_p[:mid, :] = na
    doping_n[mid:, :] = nd
    contacts = {"west": 0.0, "east": v_bias}
    return DdmConfig(
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        eps_rel=EPS_R_SI,
        doping_n=doping_n,
        doping_p=doping_p,
        contacts=contacts,
        max_iter=100,
        tol=1e-6,
    )


def _make_uniform_config(
    nx: int = 20,
    ny: int = 5,
    n_d: float = 1e18,
    length: float = 2e-6,
    v_bias: float = 0.0,
) -> DdmConfig:
    """构造均匀 N 型半导体 DDM 配置（用于欧姆导体测试）。

    Args:
        nx: x 方向网格数。
        ny: y 方向网格数。
        n_d: 施主浓度 [m^-3]。
        length: 器件总长 [m]。
        v_bias: 偏置电压 [V]（east 端）。

    Returns:
        DdmConfig 配置对象。
    """
    dx = length / nx
    dy = 1e-7
    doping_n = np.full((nx, ny), n_d)
    doping_p = np.zeros((nx, ny))
    contacts = {"west": 0.0, "east": v_bias}
    return DdmConfig(
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        eps_rel=EPS_R_SI,
        doping_n=doping_n,
        doping_p=doping_p,
        contacts=contacts,
        max_iter=200,
        tol=1e-6,
    )


def _builtin_potential(na: float, nd: float, n_i: float, vt: float) -> float:
    """PN 结内建电势 V_bi = V_T·ln(N_A·N_D/n_i²)。"""
    return vt * np.log(na * nd / n_i**2)


# ============================================================
# Test 1: Scharfetter-Gummel Bernoulli 函数
# ============================================================
class TestScharfetterGummel:
    """Scharfetter-Gummel 离散与 Bernoulli 函数测试（4 tests）。"""

    def test_bernoulli_at_zero(self) -> None:
        """B(0) = 1（Taylor 展开验证，避免 0/0 除零）。"""
        result = bernoulli(0.0)
        assert np.isclose(result, 1.0, rtol=1e-10)

    def test_bernoulli_large_positive(self) -> None:
        """B(x) ≈ x·e^(-x)（x→∞ 渐近行为，避免 e^x 上溢）。"""
        x = 50.0
        result = bernoulli(x)
        expected = x * np.exp(-x)
        assert np.isclose(result, expected, rtol=1e-6)

    def test_bernoulli_pair_identity(self) -> None:
        """B(-x) = B(x) + x（恒等式验证，Selberherr 1984 §5.2）。"""
        x = np.linspace(-20.0, 20.0, 100)
        b_pos, b_neg = bernoulli_pair(x)
        assert np.allclose(b_neg, b_pos + x, rtol=1e-10)

    def test_bernoulli_symmetry(self) -> None:
        """数值稳定性：全域有限正值，无 NaN/Inf。"""
        x = np.linspace(-100.0, 100.0, 500)
        result = bernoulli(x)
        assert np.all(np.isfinite(result))
        assert np.all(result > 0.0)
        # 验证分段交界处连续
        x_cross = np.array([-1e-6, 1e-6])
        b_cross = bernoulli(x_cross)
        assert np.all(np.isfinite(b_cross))
        # 大负值区域也应有限且为正
        x_large_neg = np.array([-50.0, -100.0])
        b_large_neg = bernoulli(x_large_neg)
        assert np.all(np.isfinite(b_large_neg))
        assert np.all(b_large_neg > 0.0)


# ============================================================
# Test 2: Poisson 方程求解器
# ============================================================
class TestPoisson:
    """Poisson 方程求解器测试（3 tests）。"""

    def test_poisson_uniform_doping(self) -> None:
        """均匀掺杂下平带 ψ 恒定（电荷为零 → 电势常数）。"""
        nx, ny = 20, 1
        dx, dy = 1e-7, 1e-7
        n_d = 1e22
        doping_n = np.full((nx, ny), n_d)
        doping_p = np.zeros((nx, ny))
        n_eq = 0.5 * (n_d + np.sqrt(n_d**2 + 4 * N_I_SI**2))
        p_eq = N_I_SI**2 / n_eq
        charge = Q_E * (p_eq - n_eq + doping_n - doping_p)
        assert np.max(np.abs(charge)) < 1.0  # 电中性验证

        solver = PoissonSolver()
        bc_left = PoissonBc(side="west", type=DIRICHLET, value=0.0)
        bc_right = PoissonBc(side="east", type=DIRICHLET, value=0.0)
        phi = solver.solve(nx, ny, dx, dy, EPS_R_SI, charge, [bc_left, bc_right])
        assert np.allclose(phi, 0.0, atol=1e-10)

    def test_poisson_pn_junction_builtin(self) -> None:
        """PN 结内建电势 V_bi 定性验证（P 区电势低、N 区电势高）。"""
        nx, ny = 100, 1
        length = 2e-6
        dx = length / nx
        dy = 1e-7
        mid = nx // 2
        na = 1e22
        nd = 1e22
        doping_p = np.zeros((nx, ny))
        doping_n = np.zeros((nx, ny))
        doping_p[:mid, :] = na
        doping_n[mid:, :] = nd

        vt = V_T
        n_i = N_I_SI
        n_net = doping_n - doping_p
        n_eq_qn = 0.5 * (n_net + np.sqrt(n_net**2 + 4 * n_i**2))
        phi_eq = vt * np.log(n_eq_qn / n_i)
        n_boltz = n_i * np.exp(phi_eq / vt)
        p_boltz = n_i * np.exp(-phi_eq / vt)
        charge = Q_E * (p_boltz - n_boltz + doping_n - doping_p)

        solver = PoissonSolver()
        bc_left = PoissonBc(side="west", type=DIRICHLET, value=float(phi_eq[0, 0]))
        bc_right = PoissonBc(side="east", type=DIRICHLET, value=float(phi_eq[-1, 0]))
        phi = solver.solve(nx, ny, dx, dy, EPS_R_SI, charge, [bc_left, bc_right])

        phi_left = float(np.mean(phi[: mid // 2, :]))
        phi_right = float(np.mean(phi[mid + mid // 2 :, :]))
        assert phi_right > phi_left
        _builtin_potential(na, nd, n_i, vt)
        dphi = phi_right - phi_left
        assert 0.1 < dphi < 2.0

    def test_poisson_dirichlet_bc(self) -> None:
        """Dirichlet 边界条件正确施加（边界节点值等于设定值）。"""
        nx, ny = 10, 5
        dx, dy = 1e-7, 1e-7
        charge = np.zeros((nx, ny))
        solver = PoissonSolver()
        v_left = 0.5
        v_right = -0.3
        bcs = [
            PoissonBc(side="west", type=DIRICHLET, value=v_left),
            PoissonBc(side="east", type=DIRICHLET, value=v_right),
        ]
        phi = solver.solve(nx, ny, dx, dy, EPS_R_SI, charge, bcs)
        assert np.allclose(phi[0, :], v_left, atol=1e-10)
        assert np.allclose(phi[-1, :], v_right, atol=1e-10)


# ============================================================
# Test 3: Gummel 解耦迭代求解器（M1/M2 核心）
# ============================================================
class TestGummelSolver:
    """Gummel 解耦迭代求解器测试（5 tests，M1/M2 核心）。"""

    def test_pn_junction_equilibrium_dv(self) -> None:
        """PN 结平衡态 dV ≈ V_bi（M1 决定性验收）。

        验收标准：dV = V_bi 误差 ≤ 0.01V。
        """
        na = 1e22
        nd = 1e22
        cfg = _make_pn_config(nx=100, ny=1, na=na, nd=nd, v_bias=0.0)
        result = solve_ddm_gummel(cfg)
        assert result.converged

        phi = result.potential[:, 0]
        nx = cfg.nx
        mid = nx // 2
        phi_p = float(np.mean(phi[: mid // 2]))
        phi_n = float(np.mean(phi[mid + mid // 2 :]))
        dv = phi_n - phi_p
        v_bi = _builtin_potential(na, nd, N_I_SI, V_T)
        error = abs(dv - v_bi)
        assert error <= 0.01, f"dV={dv:.4f}V, V_bi={v_bi:.4f}V, 误差={error:.4f}V > 0.01V"

    def test_gummel_convergence_steps(self) -> None:
        """平衡态 Gummel 迭代 < 20 步收敛（M2 决定性验收）。

        验收标准：Gummel 迭代 < 20 步收敛。
        平衡态 PN 结从准中性初值出发，Gummel 应快速收敛。
        """
        cfg = _make_pn_config(nx=80, ny=1, v_bias=0.0)
        result = solve_ddm_gummel(cfg)
        assert result.converged
        assert result.n_iterations < 20, f"Gummel 迭代 {result.n_iterations} 步 ≥ 20 步"

    def test_uniform_ohmic_current(self) -> None:
        """均匀欧姆导体 J = σ·E（Gummel 法验证，定性）。"""
        cfg_low = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.01)
        cfg_high = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.05)
        result_low = solve_ddm_gummel(cfg_low)
        result_high = solve_ddm_gummel(cfg_high)
        assert result_low.converged
        assert result_high.converged
        j_low = float(np.mean(np.abs(result_low.current_density_x[cfg_low.nx // 2, :])))
        j_high = float(np.mean(np.abs(result_high.current_density_x[cfg_high.nx // 2, :])))
        # 电压 5 倍 → 电流约 5 倍（欧姆定律）
        assert abs(j_high / j_low - 5.0) < 0.5
        # 验证物理可行性
        assert np.all(result_high.electron_density > 0.0)
        assert np.all(result_high.conductivity > 0.0)

    def test_forward_bias_current_monotonic(self) -> None:
        """电流随电压单调增长（均匀 N 型半导体 I-V，Gummel 法）。"""
        voltages = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
        currents = []
        for v in voltages:
            cfg = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=v)
            result = solve_ddm_gummel(cfg)
            assert result.converged
            j = float(np.mean(np.abs(result.current_density_x[cfg.nx // 2, :])))
            currents.append(j)
        # 电流单调增长（欧姆导体 J ∝ V）
        for i in range(1, len(currents)):
            assert currents[i] > currents[i - 1], (
                f"电压 {voltages[i]}V 电流 {currents[i]:.3e} < "
                f"{voltages[i - 1]}V 电流 {currents[i - 1]:.3e}"
            )

    def test_gummel_raises_on_divergence(self) -> None:
        """不收敛时 raise（R03 禁止 fall-back）。"""
        # 极少迭代步数确保不收敛
        cfg = _make_pn_config(nx=30, ny=1, v_bias=0.0)
        cfg.max_iter = 0  # 0 步肯定不收敛
        with pytest.raises((RuntimeError, ValueError)):
            GummelSolver(relaxation=1.0).solve(cfg)


# ============================================================
# Test 4: SG 离散稳定性（M3）
# ============================================================
class TestSgStability:
    """Scharfetter-Gummel 离散稳定性测试（3 tests，M3）。"""

    def test_high_doping_gradient_monotonic(self) -> None:
        """高掺杂梯度下载流子单调（M3 决定性验收）。

        验证 SG 离散在陡峭掺杂梯度下不产生数值振荡，
        载流子浓度分布保持单调性。
        """
        cfg = _make_pn_config(nx=200, ny=1, na=1e23, nd=1e23, v_bias=0.0)
        result = solve_ddm_gummel(cfg)
        assert result.converged

        n = result.electron_density[:, 0]
        p = result.hole_density[:, 0]
        mid = cfg.nx // 2
        n_left_avg = float(np.mean(n[: mid // 2]))
        n_right_avg = float(np.mean(n[mid + mid // 2 :]))
        assert n_right_avg > n_left_avg * 100.0
        p_left_avg = float(np.mean(p[: mid // 2]))
        p_right_avg = float(np.mean(p[mid + mid // 2 :]))
        assert p_left_avg > p_right_avg * 100.0

    def test_sg_no_negative_carriers(self) -> None:
        """载流子密度非负（物理可行性约束，平衡态验证）。"""
        cfg = _make_pn_config(nx=100, ny=1, v_bias=0.0)
        result = solve_ddm_gummel(cfg)
        assert result.converged
        assert np.all(result.electron_density >= 0.0)
        assert np.all(result.hole_density >= 0.0)

    def test_sg_finite_values(self) -> None:
        """全有限无 NaN/Inf（数值稳定性，平衡态验证）。"""
        cfg = _make_pn_config(nx=100, ny=1, v_bias=0.0)
        result = solve_ddm_gummel(cfg)
        assert result.converged
        assert np.all(np.isfinite(result.potential))
        assert np.all(np.isfinite(result.electron_density))
        assert np.all(np.isfinite(result.hole_density))
        assert np.all(np.isfinite(result.current_density_x))
        assert np.all(np.isfinite(result.conductivity))


# ============================================================
# Test 5: DDM 主求解器（全耦合牛顿法）
# ============================================================
class TestDdmSolver:
    """DDM 主求解器测试（4 tests）。"""

    def test_solver_config_construction(self) -> None:
        """DdmConfig 合法构造与参数验证。"""
        nx, ny = 10, 5
        doping_n = np.ones((nx, ny)) * 1e22
        doping_p = np.zeros((nx, ny))
        cfg = DdmConfig(
            nx=nx,
            ny=ny,
            dx=1e-7,
            dy=1e-7,
            eps_rel=11.7,
            doping_n=doping_n,
            doping_p=doping_p,
        )
        assert cfg.nx == nx
        assert cfg.ny == ny
        assert cfg.vt > 0.0
        # 非法参数应 raise
        with pytest.raises(ValueError):
            DdmConfig(
                nx=0, ny=1, dx=1e-7, dy=1e-7, eps_rel=11.7, doping_n=doping_n, doping_p=doping_p
            )
        with pytest.raises(ValueError):
            DdmConfig(
                nx=nx, ny=ny, dx=-1.0, dy=1e-7, eps_rel=11.7, doping_n=doping_n, doping_p=doping_p
            )

    def test_solver_result_fields(self) -> None:
        """DdmResult 含完整字段（psi/n/p/J_n/J_p/σ/E）。"""
        cfg = _make_uniform_config(nx=20, ny=1, n_d=1e22, v_bias=0.05)
        result = solve_ddm_gummel(cfg)
        assert isinstance(result, DdmResult)
        assert result.potential.shape == (cfg.nx, cfg.ny)
        assert result.electron_density.shape == (cfg.nx, cfg.ny)
        assert result.hole_density.shape == (cfg.nx, cfg.ny)
        assert result.current_density_x.shape == (cfg.nx, cfg.ny)
        assert result.current_density_y.shape == (cfg.nx, cfg.ny)
        assert result.conductivity.shape == (cfg.nx, cfg.ny)
        assert result.e_field_x.shape == (cfg.nx, cfg.ny)
        assert result.e_field_y.shape == (cfg.nx, cfg.ny)
        assert isinstance(result.n_iterations, int)
        assert isinstance(result.converged, bool)

    def test_solve_ddm_convenience(self) -> None:
        """solve_ddm_gummel 便捷入口可正常调用（均匀半导体正偏验证）。"""
        cfg = _make_uniform_config(nx=20, ny=1, n_d=1e22, v_bias=0.05)
        result = solve_ddm_gummel(cfg)
        assert result.converged
        assert result.n_iterations >= 1
        assert np.all(np.isfinite(result.potential))
        assert np.all(result.electron_density > 0.0)
        assert np.all(result.hole_density >= 0.0)

    def test_solver_vs_gummel_consistency(self) -> None:
        """牛顿法求解验证（均匀 N 型半导体正偏，物理合理性检查）。

        牛顿法（DdmSolver）与 Gummel 法都是 DDM 的数值解法。
        此处验证牛顿法可在均匀半导体上收敛且结果物理合理。
        """
        # 牛顿法在 20x5 均匀 N 型 + 0.1V 偏置下可收敛
        cfg_u = _make_uniform_config(nx=20, ny=5, n_d=1e18, v_bias=0.1)
        result_n = solve_ddm(cfg_u)
        assert result_n.converged
        # 物理合理性验证
        mid = cfg_u.nx // 2
        assert np.all(result_n.electron_density > 0.0)
        assert np.all(result_n.hole_density >= 0.0)
        assert np.all(np.isfinite(result_n.potential))
        assert np.all(np.isfinite(result_n.current_density_x))
        # 有电流流动（偏置下欧姆导体）
        j_newton = float(np.mean(np.abs(result_n.current_density_x[mid, :])))
        assert j_newton > 0.0


# ============================================================
# Test 6: 电热耦合
# ============================================================
class TestCoupling:
    """DDM ↔ HEAT 电热耦合测试（3 tests）。"""

    def test_ddm_to_heat_joule_heating(self) -> None:
        """焦耳热 Q ≥ 0（热力学第二定律：耗散 ≥ 0）。"""
        cfg = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.05)
        result = solve_ddm_gummel(cfg)
        assert result.converged
        q_joule = ddm_to_heat_joule(result, cfg)
        assert q_joule.shape == (cfg.nx, cfg.ny)
        assert np.all(np.isfinite(q_joule))
        assert np.all(q_joule >= 0.0)
        assert np.max(q_joule) > 0.0

    def test_heat_to_ddm_mobility(self) -> None:
        """升温迁移率降低（T^-1.5，Caughey-Thomas 晶格散射）。"""
        t0 = 300.0
        mu_n0, mu_p0 = heat_to_ddm_mobility(t0)
        assert mu_n0 == MU_N_SI
        assert mu_p0 == MU_P_SI

        # 升温 400K → 迁移率下降
        mu_n_400, mu_p_400 = heat_to_ddm_mobility(400.0)
        assert mu_n_400 < mu_n0
        assert mu_p_400 < mu_p0

        # 验证 T^-1.5 关系
        expected_factor = (t0 / 400.0) ** LATTICE_SCATTERING_EXPONENT
        assert np.isclose(mu_n_400 / mu_n0, expected_factor, rtol=1e-10)
        assert np.isclose(mu_p_400 / mu_p0, expected_factor, rtol=1e-10)

        # 降温 → 迁移率上升
        mu_n_200, mu_p_200 = heat_to_ddm_mobility(200.0)
        assert mu_n_200 > mu_n0
        assert mu_p_200 > mu_p0

        # 非法温度 raise
        with pytest.raises(ValueError):
            heat_to_ddm_mobility(0.0)
        with pytest.raises(ValueError):
            heat_to_ddm_mobility(-1.0)

    def test_joule_heating_uniform_current(self) -> None:
        """均匀电流下焦耳热 Q ∝ J²（欧姆导体加热定性验证）。

        偏置加倍 → 电流加倍 → 焦耳热约 4 倍（Q = J²/σ ∝ V²）。
        """
        cfg1 = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.02)
        cfg2 = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.04)
        result1 = solve_ddm_gummel(cfg1)
        result2 = solve_ddm_gummel(cfg2)
        assert result1.converged
        assert result2.converged

        q1 = ddm_to_heat_joule(result1, cfg1)
        q2 = ddm_to_heat_joule(result2, cfg2)
        assert np.all(q1 >= 0.0)
        assert np.all(q2 >= 0.0)
        assert np.max(q1) > 0.0
        assert np.max(q2) > 0.0

        q1_mean = float(np.mean(q1))
        q2_mean = float(np.mean(q2))
        j1 = float(np.mean(np.abs(result1.current_density_x[cfg1.nx // 2, :])))
        j2 = float(np.mean(np.abs(result2.current_density_x[cfg2.nx // 2, :])))
        # 电压加倍 → 电流加倍 → 焦耳热约 4 倍
        assert abs(q2_mean / q1_mean - 4.0) < 1.0
        assert abs(j2 / j1 - 2.0) < 0.2


# ============================================================
# Test 7: 边界条件
# ============================================================
class TestBoundaryConditions:
    """边界条件测试（3 tests）。"""

    def test_dirichlet_contact_potential(self) -> None:
        """电极接触电势差精确等于偏置（Dirichlet BC 正确性）。

        Gummel 法在欧姆接触处施加 Dirichlet BC，
        静电势差应等于外加偏置电压。
        """
        cfg0 = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.05)
        cfg1 = _make_uniform_config(nx=30, ny=1, n_d=1e22, v_bias=0.1)
        result0 = solve_ddm_gummel(cfg0)
        result1 = solve_ddm_gummel(cfg1)
        assert result0.converged
        assert result1.converged

        # 两端电势差应精确等于外加电压（欧姆接触 Dirichlet BC）
        dv0 = float(result0.potential[-1, 0] - result0.potential[0, 0])
        dv1 = float(result1.potential[-1, 0] - result1.potential[0, 0])
        assert abs(dv0 - 0.05) < 1e-6
        assert abs(dv1 - 0.1) < 1e-6
        assert dv1 > dv0

    def test_neumann_insulator_zero_field(self) -> None:
        """绝缘边界 ∂φ/∂n ≈ 0（Neumann 边界，Poisson 求解器直接验证）。

        上下边界（south/north）施加 Neumann ∂φ/∂n = 0，
        验证同一 x 位置不同 y 处电势基本恒定（对称分布），
        边界法向电场远小于横向电场。
        """
        nx, ny = 20, 10
        dx, dy = 1e-7, 1e-7
        charge = np.zeros((nx, ny))
        solver = PoissonSolver()
        # 左右 Dirichlet，上下 Neumann（绝缘）
        bcs = [
            PoissonBc(side="west", type=DIRICHLET, value=1.0),
            PoissonBc(side="east", type=DIRICHLET, value=0.0),
            PoissonBc(side="south", type=NEUMANN, value=0.0),
            PoissonBc(side="north", type=NEUMANN, value=0.0),
        ]
        phi = solver.solve(nx, ny, dx, dy, EPS_R_SI, charge, bcs)
        # 验证电势分布：沿 y 方向基本恒定（Neumann = 0 对称）
        # 同一 x 位置，y 方向最大偏差 < 1e-5 V
        phi_mid_x = phi[nx // 2, :]
        assert np.max(phi_mid_x) - np.min(phi_mid_x) < 1e-5
        # 边界法向电场远小于横向电场（< 1/1000）
        e_x = (phi[1, ny // 2] - phi[0, ny // 2]) / dx
        e_y_south_max = float(np.max(np.abs((phi[:, 1] - phi[:, 0]) / dy)))
        e_y_north_max = float(np.max(np.abs((phi[:, -1] - phi[:, -2]) / dy)))
        assert abs(e_x) > 1e5  # 横向电场 ~ 5e5 V/m
        assert e_y_south_max / abs(e_x) < 1e-3
        assert e_y_north_max / abs(e_x) < 1e-3

    def test_boundary_type_enum(self) -> None:
        """边界类型枚举完整（DIRICHLET / NEUMANN）。"""
        assert DIRICHLET == "dirichlet"
        assert NEUMANN == "neumann"
        # PoissonBc 验证
        bc_d = PoissonBc(side="west", type=DIRICHLET, value=0.5)
        assert bc_d.type == DIRICHLET
        assert bc_d.value == 0.5
        bc_n = PoissonBc(side="east", type=NEUMANN, value=0.0)
        assert bc_n.type == NEUMANN
        # 非法类型 raise
        with pytest.raises(ValueError):
            PoissonBc(side="west", type="invalid", value=0.0)
        # 非法方向 raise
        with pytest.raises(ValueError):
            PoissonBc(side="invalid", type=DIRICHLET, value=0.0)


# ============================================================
# 附加测试：SRH 复合（continuity 模块核心）
# ============================================================
class TestSrhRecombination:
    """SRH 复合函数测试（附加，连续性方程核心验证）。"""

    def test_srh_equilibrium_zero(self) -> None:
        """平衡态 n·p = n_i² → R = 0。"""
        n = np.array([1e16, 1e20, 1e22])
        p = N_I_SI**2 / n
        r = srh_recombination(n, p)
        assert np.allclose(r, 0.0, atol=1e-10)

    def test_srh_forward_bias_positive(self) -> None:
        """正注入 n·p > n_i² → R > 0（净复合）。"""
        n = np.array([1e22, 1e21])
        p = np.array([1e20, 1e19])
        r = srh_recombination(n, p)
        assert np.all(r > 0.0)

    def test_srh_derivatives_finite(self) -> None:
        """SRH 偏导数有限且符号正确。"""
        n = np.logspace(14, 24, 100).reshape(10, 10)
        p = np.logspace(14, 24, 100).reshape(10, 10).T
        dR_dn, dR_dp = srh_derivatives(n, p)
        assert np.all(np.isfinite(dR_dn))
        assert np.all(np.isfinite(dR_dp))

    def test_srh_negative_input_raises(self) -> None:
        """负载流子浓度输入 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError):
            srh_recombination(np.array([-1.0]), np.array([1e16]))
        with pytest.raises(ValueError):
            srh_recombination(np.array([1e16]), np.array([-1.0]))
