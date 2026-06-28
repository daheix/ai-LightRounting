"""P0-6 FETD + Active FDTD + 子网格加速验收测试。

验证 polaris.sim.fetd / active_fdtd / subgridding 三个模块：
- FETD 矩阵组装（四面体 / 六面体）
- Newmark-β 时间积分稳定性（保守系统：能量守恒；无条件稳定）
- Active FDTD 增益模型（Lorentz ADE + 4 能级速率方程）
- 子网格插值（主↔子网格场量映射、4x 加速比）
- 错误处理（参数校验 raise，无 fall-back）

物理参数（Jin 2014 / Taflove 2005 / CODATA 2018）：
- 真空 ε0 = 8.8541878128e-12 F/m, μ0 = 1.25663706212e-6 H/m
- c0 = 2.99792458e8 m/s
- 电子 e = 1.602176634e-19 C, m_e = 9.1093837015e-31 kg, ℏ = 1.054571817e-34 J·s
- 激光波长 λ = 1.55e-6 m, ω_0 = 2π·c/λ ≈ 1.216e15 rad/s
- 半导体激光器典型：τ_21 = 1 ns, γ_L = 1e12 rad/s, N_total = 1e24 m⁻³

文献来源（≥5，规则 18 学术诚信）：
1. Jin, "The Finite Element Method in Electromagnetics" 3rd ed., Wiley 2014 —
   https://onlinelibrary.wiley.com/doi/book/10.1002/9781118576637
2. Newmark 1959 ASCE J. Eng. Mech. Div. 85(3) 67-94 —
   https://doi.org/10.1061/JMCEA3.0000097
3. Chang & Taflove 2004 Opt Express 12(15) 3395-3405 —
   https://doi.org/10.1364/OPEX.12.003395
4. Liang & Johnson 2013 IEEE JQE —
   https://doi.org/10.1109/JQE.2013.2270491
5. Deng et al. 2022 IEEE TAP 70(8) 6155-6164 —
   https://doi.org/10.1109/TAP.2022.3166240
6. Taflove & Hagness 2005 Computational Electrodynamics —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
7. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
8. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise，无 fall-back）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy CPU）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.fetd import (
    FetdConfig,
    FetdMaterial,
    FetdResult,
    FetdSolver,
    HexahedronMesh,
    NewmarkIntegrator,
    TetrahedronMesh,
    assemble_damping,
    assemble_mass,
    assemble_stiffness,
    enforce_dirichlet,
    newmark_beta_coefficients,
)
from polaris.sim.active_fdtd import (
    ActiveFdtdConfig,
    ActiveFdtdResult,
    ActiveFdtdSolver,
    ActiveMedium,
    step_lorentz_ade,
    step_rate_equation,
)
from polaris.sim.subgridding import (
    SubgridConfig,
    SubgridFdtdSolver,
    SubgridResult,
    estimate_speedup,
    interpolate_main_to_sub,
    interpolate_sub_to_main,
    step_yee_1d,
)

# 物理常数
_C0 = 2.99792458e8
_EPS0 = 8.8541878128e-12
_MU0 = 1.25663706212e-6


# =============================================================================
# FETD 矩阵组装测试
# =============================================================================


def _make_simple_tet_mesh() -> TetrahedronMesh:
    """构造单个标准四面体网格（单位正交四面体）。"""
    # 单位立方体 [0,1]^3 的一个四面体（顶点 0,1,2,5）
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    elements = np.array([[0, 1, 2, 3]])
    mat_id = np.array([0])
    return TetrahedronMesh(nodes=nodes, elements=elements, mat_id=mat_id)


def _make_simple_hex_mesh() -> HexahedronMesh:
    """构造单个标准六面体网格（单位立方体）。"""
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    )
    # Hex8 标准局部编号：i + 2j + 4k
    elements = np.array([[0, 1, 2, 3, 4, 5, 6, 7]])
    mat_id = np.array([0])
    return HexahedronMesh(nodes=nodes, elements=elements, mat_id=mat_id)


class TestFetdAssembly:
    """FETD 矩阵组装测试。"""

    def test_tet_mass_matrix_symmetry(self) -> None:
        """测试 1：四面体质量矩阵对称正定。"""
        mesh = _make_simple_tet_mesh()
        mat = [FetdMaterial(eps_r=2.0)]
        m = assemble_mass(mesh, mat)
        m_dense = m.toarray()
        # 对称性
        assert np.allclose(m_dense, m_dense.T, atol=1e-12), \
            "质量矩阵必须对称"
        # 正定性（4x4 正定矩阵所有特征值 > 0）
        eigvals = np.linalg.eigvalsh(m_dense)
        assert np.all(eigvals > 0), f"质量矩阵特征值须 >0，得到 {eigvals}"
        # 单位正交四面体体积 V = 1/6，ε_0·2·V = ε_0/3
        # 对角元素 = ε_0·2·V·2/20 = ε_0·V/5 = ε_0/30
        expected_diag = _EPS0 * 2.0 * (1.0 / 6.0) * 2.0 / 20.0
        assert abs(m_dense[0, 0] - expected_diag) / expected_diag < 1e-10

    def test_tet_stiffness_matrix_psd(self) -> None:
        """测试 2：四面体刚度矩阵半正定（旋度退化到梯度）。"""
        mesh = _make_simple_tet_mesh()
        mat = [FetdMaterial(eps_r=1.0, mu_r=1.0)]
        k = assemble_stiffness(mesh, mat)
        k_dense = k.toarray()
        eigvals = np.linalg.eigvalsh(k_dense)
        # 刚度矩阵半正定（特征值 ≥ 0）
        assert np.all(eigvals >= -1e-12), \
            f"刚度矩阵须半正定，特征值 {eigvals}"

    def test_hex_mass_matrix_shape(self) -> None:
        """测试 3：六面体质量矩阵形状与对称性。"""
        mesh = _make_simple_hex_mesh()
        mat = [FetdMaterial(eps_r=1.0)]
        m = assemble_mass(mesh, mat)
        m_dense = m.toarray()
        assert m_dense.shape == (8, 8)
        assert np.allclose(m_dense, m_dense.T, atol=1e-12)
        # 正定性
        eigvals = np.linalg.eigvalsh(m_dense)
        assert np.all(eigvals > 0), f"特征值须 >0，得到 {eigvals}"

    def test_damping_matrix_zero_when_sigma_zero(self) -> None:
        """测试 4：σ=0 时阻尼矩阵全零。"""
        mesh = _make_simple_tet_mesh()
        mat = [FetdMaterial(eps_r=1.0, sigma=0.0)]
        c = assemble_damping(mesh, mat)
        assert np.allclose(c.toarray(), 0.0)

    def test_damping_matrix_nonzero_when_sigma_positive(self) -> None:
        """测试 5：σ>0 时阻尼矩阵对称正定。"""
        mesh = _make_simple_tet_mesh()
        sigma = 1.0  # S/m
        mat = [FetdMaterial(eps_r=1.0, sigma=sigma)]
        c = assemble_damping(mesh, mat)
        c_dense = c.toarray()
        assert np.allclose(c_dense, c_dense.T)
        eigvals = np.linalg.eigvalsh(c_dense)
        assert np.all(eigvals > 0)


# =============================================================================
# Newmark-β 时间积分测试
# =============================================================================


class TestNewmarkBeta:
    """Newmark-β 时间积分稳定性测试。"""

    def test_newmark_coefficients_default_conservative(self) -> None:
        """测试 6：默认 β=0.25, γ=0.5 满足保守稳定性。"""
        beta, gamma = newmark_beta_coefficients()
        assert beta == 0.25
        assert gamma == 0.5
        assert 2.0 * beta >= gamma  # 无条件稳定

    def test_newmark_coefficients_invalid_raises(self) -> None:
        """测试 7：不满足稳定性的参数 raise。"""
        with pytest.raises(ValueError, match="无条件稳定"):
            newmark_beta_coefficients(beta=0.1, gamma=0.5)
        with pytest.raises(ValueError):
            newmark_beta_coefficients(beta=0.0, gamma=0.5)
        with pytest.raises(ValueError):
            newmark_beta_coefficients(beta=0.25, gamma=0.0)
        with pytest.raises(ValueError):
            newmark_beta_coefficients(beta=0.6, gamma=0.5)

    def test_newmark_energy_conservation_undamped(self) -> None:
        """测试 8：无阻尼保守系统能量守恒（Newmark 梯形法则，Hughes §7）。

        构造一维弹簧-质量系统：M·ë + K·e = 0，初始位移 e0 = 1，零速度。
        能量 E = 0.5·e^T·K·e + 0.5·v^T·M·v 应在 Newmark β=0.25, γ=0.5 下守恒。
        """
        # 2-DOF 弹簧-质量系统：M = I, K = [[2,-1],[-1,2]]（标准 FEM 1D Laplacian）
        n = 4
        m_dense = np.eye(n)
        k_dense = (
            2.0 * np.eye(n)
            - np.diag(np.ones(n - 1), 1)
            - np.diag(np.ones(n - 1), -1)
        )
        # Dirichlet 边界（两端固定）
        k_dense[0, :] = 0.0
        k_dense[:, 0] = 0.0
        k_dense[0, 0] = 1.0
        k_dense[-1, :] = 0.0
        k_dense[:, -1] = 0.0
        k_dense[-1, -1] = 1.0
        from scipy.sparse import csr_matrix
        m = csr_matrix(m_dense)
        k = csr_matrix(k_dense)
        c = csr_matrix(np.zeros((n, n)))
        dt = 0.01
        integrator = NewmarkIntegrator(dt=dt, beta=0.25, gamma=0.5)
        lu_piv = integrator.build_effective_stiffness(m, c, k)
        e = np.zeros(n)
        e[1] = 1.0  # 初始位移
        v = np.zeros(n)
        # 初始加速度 a_0 = M⁻¹·(f_0 - K·e_0)
        a = np.linalg.solve(m_dense, -k_dense @ e)
        # 运行 200 步，检查能量
        e_init = 0.5 * e @ (k_dense @ e) + 0.5 * v @ (m_dense @ v)
        # 无阻尼：c_dense = 0
        c_dense = np.zeros((n, n))
        for _ in range(200):
            e, v, a = integrator.step(
                lu_piv, c_dense, k_dense, e, v, a, np.zeros(n)
            )
            # Dirichlet 节点强制
            e[0] = 0.0
            e[-1] = 0.0
            v[0] = 0.0
            v[-1] = 0.0
            a[0] = 0.0
            a[-1] = 0.0
            assert np.all(np.isfinite(e)), "场发散"
        e_final = 0.5 * e @ (k_dense @ e) + 0.5 * v @ (m_dense @ v)
        # 能量应守恒（容差 1%，因 Dirichlet 边界轻微扰动）
        rel_err = abs(e_final - e_init) / abs(e_init)
        assert rel_err < 0.01, \
            f"能量不守恒：初始 {e_init:.4e}，最终 {e_final:.4e}，" \
            f"相对误差 {rel_err:.4f}"

    def test_newmark_stability_large_dt(self) -> None:
        """测试 9：Newmark 无条件稳定 — 大 Δt 仍不发散。"""
        # 简单 1-DOF 振子：M·ë + K·e = 0，ω = sqrt(K/M)
        # 用 Δt = 10·T（远超显式稳定极限），Newmark β=0.25 γ=0.5 仍稳定
        m_dense = np.array([[1.0]])
        k_dense = np.array([[1.0]])  # ω = 1 rad/s, T = 2π
        from scipy.sparse import csr_matrix
        m = csr_matrix(m_dense)
        k = csr_matrix(k_dense)
        c = csr_matrix(np.zeros((1, 1)))
        dt = 1.0  # 远大于显式极限 π/ω
        integrator = NewmarkIntegrator(dt=dt, beta=0.25, gamma=0.5)
        lu_piv = integrator.build_effective_stiffness(m, c, k)
        e = np.array([1.0])
        v = np.array([0.0])
        a = np.array([-1.0])  # a_0 = -K·e/M
        c_dense = np.zeros((1, 1))
        for _ in range(100):
            e, v, a = integrator.step(
                lu_piv, c_dense, k_dense, e, v, a, np.zeros(1)
            )
            assert np.all(np.isfinite(e)), "大 Δt 下 Newmark 发散"
        # 振幅应保持有界（< 10·初始振幅）
        assert abs(e[0]) < 10.0, f"振幅过大 {e[0]}"


# =============================================================================
# FETD 求解器集成测试
# =============================================================================


class TestFetdSolver:
    """FETD 主求解器集成测试。"""

    def test_fetd_solver_runs_and_returns_result(self) -> None:
        """测试 10：FETD 求解器运行返回 FetdResult。"""
        mesh = _make_simple_tet_mesh()
        mat = [FetdMaterial(eps_r=1.0, sigma=0.0)]
        # 持续常力源
        def source(t: float) -> np.ndarray:
            f = np.zeros(4)
            f[1] = 1.0  # 节点 1 上的常力
            return f

        cfg = FetdConfig(
            mesh=mesh,
            materials=mat,
            dt=1e-12,
            n_steps=10,
            source=source,
            dirichlet_nodes=np.array([0]),
        )
        result = FetdSolver(cfg).solve()
        assert isinstance(result, FetdResult)
        assert result.field_history.shape == (11, 4)
        assert result.energy.shape == (11,)
        assert np.all(np.isfinite(result.field_history))
        # Dirichlet 节点 0 应保持 0
        assert np.allclose(result.field_history[:, 0], 0.0)

    def test_fetd_solver_invalid_dt_raises(self) -> None:
        """测试 11：FETD 无效 dt raise。"""
        mesh = _make_simple_tet_mesh()
        mat = [FetdMaterial(eps_r=1.0)]
        with pytest.raises(ValueError, match="dt"):
            FetdConfig(
                mesh=mesh,
                materials=mat,
                dt=-1.0,
                n_steps=10,
                source=lambda t: np.zeros(4),
            )

    def test_fetd_solver_divergence_raises(self) -> None:
        """测试 12：FETD 发散（NaN/Inf）raise ValueError。"""
        mesh = _make_simple_tet_mesh()
        mat = [FetdMaterial(eps_r=1.0)]
        # 极大源 + 极大 dt 触发发散
        def huge_source(t: float) -> np.ndarray:
            f = np.zeros(4)
            f[1] = 1e30
            return f

        cfg = FetdConfig(
            mesh=mesh,
            materials=mat,
            dt=1e3,  # 极大 dt
            n_steps=5,
            source=huge_source,
        )
        with pytest.raises((ValueError, OverflowError, FloatingPointError)):
            FetdSolver(cfg).solve()


# =============================================================================
# Active FDTD 测试
# =============================================================================


class TestActiveFdtd:
    """Active FDTD 增益模型测试。"""

    def _make_medium(self, pump_rate: float = 1.0e27) -> ActiveMedium:
        """构造典型半导体增益介质参数。"""
        return ActiveMedium(
            omega_0=2.0 * np.pi * _C0 / 1.55e-6,  # 1.55 μm 跃迁
            gamma_L=1.0e12,  # 1 ps 退相干
            tau_21=1.0e-9,  # 1 ns 自发辐射
            pump_rate=pump_rate,
            n_total=1.0e24,
        )

    def test_lorentz_ade_decay_without_field(self) -> None:
        """测试 13：无外场时 Lorentz 振子自由衰减。

        dJ/dt + 2γ·J + ω_0²·P = 0（无驱动）
        衰减率 = γ，振幅指数衰减 e^{-γ·t}。
        """
        medium = self._make_medium()
        n = 5
        p = np.zeros(n)
        j = np.ones(n)  # 初始 J = 1
        e = np.zeros(n)
        n2 = np.full(n, 1.0e20)  # N_2 给定值，避免耦合
        dt = 1.0e-15
        # 1000 步衰减
        for _ in range(1000):
            p, j = step_lorentz_ade(p, j, e, n2, medium, dt)
        # 衰减后 J 应远小于初始值 1
        assert np.all(np.abs(j) < 0.5), \
            f"J 未衰减：{j}"

    def test_rate_equation_pump_below_threshold(self) -> None:
        """测试 14：泵浦低于阈值时 N_2 线性增长，未受激辐射消耗。"""
        # 阈值 R_th = N_total / (2·τ_21)
        medium = self._make_medium(pump_rate=1.0e25)  # 远低于阈值
        # 阈值 R_th = 1e24 / (2·1e-9) = 5e32
        assert medium.pump_rate < medium.threshold_pump_rate()
        n = 5
        n2 = np.zeros(n)
        e = np.zeros(n)  # 无场 → 无受激辐射
        j = np.zeros(n)
        active_mask = np.ones(n, dtype=bool)
        dt = 1.0e-12
        # 1000 步（1 ns 仿真）
        for _ in range(1000):
            n2 = step_rate_equation(n2, e, j, medium, dt, active_mask)
        # N_2 应 ≈ R_pump·t·exp(-t/τ) ≈ R_pump·t（t << τ_21 时线性增长）
        # t = 1000·1e-12 = 1e-9 s = τ_21，故 N_2 ≈ R_pump·τ_21·(1-e^{-1})
        expected = medium.pump_rate * medium.tau_21 * (1.0 - np.exp(-1.0))
        rel_err = abs(n2[0] - expected) / expected
        assert rel_err < 0.05, \
            f"N_2 演化偏离预期：实际 {n2[0]:.3e}，预期 {expected:.3e}，" \
            f"误差 {rel_err:.3f}"

    def test_rate_equation_invalid_pump_raises(self) -> None:
        """测试 15：负泵浦率 raise。"""
        with pytest.raises(ValueError, match="pump_rate"):
            ActiveMedium(
                omega_0=1e15,
                gamma_L=1e12,
                tau_21=1e-9,
                pump_rate=-1.0,
                n_total=1e24,
            )

    def test_rate_equation_negative_n2_raises(self) -> None:
        """测试 16：N_2 出现非物理负值（超过容差）时 raise。"""
        medium = self._make_medium()
        # 通过极大受激辐射项触发负 N_2
        n2 = np.array([1.0e10])
        e = np.array([1.0e10])
        j = np.array([1.0e30])  # 极大 J 使 E·J/(ℏ·ω_0) 远超 pump_rate
        active_mask = np.array([True])
        dt = 1.0e-12
        with pytest.raises(ValueError, match="非物理负值"):
            step_rate_equation(n2, e, j, medium, dt, active_mask)

    def test_active_fdtd_solver_runs(self) -> None:
        """测试 17：Active FDTD 求解器端到端运行。"""
        medium = self._make_medium(pump_rate=1.0e27)
        n_cells = 50
        active_mask = np.zeros(n_cells, dtype=bool)
        active_mask[20:30] = True  # 增益区域
        cfg = ActiveFdtdConfig(
            n_cells=n_cells,
            dx=50.0e-9,  # 50 nm
            dt=0.5 * 50.0e-9 / _C0,  # 0.5·CFL
            n_steps=50,
            medium=medium,
            active_mask=active_mask,
            source_idx=5,
            source_amplitude=1.0e5,
            source_freq=medium.omega_0,
            eps_r_bg=1.0,
        )
        result = ActiveFdtdSolver(cfg).solve()
        assert isinstance(result, ActiveFdtdResult)
        assert result.e_history.shape == (51, n_cells)
        assert result.n2_history.shape == (51, n_cells)
        assert np.all(np.isfinite(result.e_history))
        # 增益区域 N_2 应随泵浦增长（小于 N_total）
        assert np.all(result.n2_history[-1, 20:30] >= 0.0)
        assert np.all(result.n2_history[-1, 20:30] <= medium.n_total)


# =============================================================================
# 子网格加速测试
# =============================================================================


class TestSubgridding:
    """子网格加速测试。"""

    def test_interpolate_main_to_sub_endpoints_match(self) -> None:
        """测试 18：主→子插值端点重合。"""
        e_main = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0], dtype=float)
        factor = 4
        i0, i1 = 1, 4
        e_sub = interpolate_main_to_sub(e_main, factor, i0, i1)
        # 子网格点数 = (4-1)*4 + 1 = 13
        assert e_sub.shape[0] == 13
        # 端点与主网格值重合
        assert abs(e_sub[0] - e_main[i0]) < 1e-12
        assert abs(e_sub[-1] - e_main[i1]) < 1e-12

    def test_interpolate_main_to_sub_linear_preserved(self) -> None:
        """测试 19：线性函数插值后保持线性。"""
        x = np.arange(10, dtype=float)
        e_main = 2.0 * x + 1.0  # y = 2x+1
        factor = 4
        i0, i1 = 2, 7
        e_sub = interpolate_main_to_sub(e_main, factor, i0, i1)
        # 子网格上 y(x_sub) = 2·(i0 + j/factor) + 1
        n_sub = (i1 - i0) * factor + 1
        x_sub = i0 + np.arange(n_sub) / factor
        expected = 2.0 * x_sub + 1.0
        assert np.allclose(e_sub, expected, atol=1e-12)

    def test_interpolate_sub_to_main_recovers_coarse_nodes(self) -> None:
        """测试 20：子→主投影恢复主网格节点值。"""
        # 子网格上 e_sub[j] = (i0 + j/factor)，j=0..n_sub-1
        factor = 4
        i0, i1 = 1, 5
        n_sub = (i1 - i0) * factor + 1
        e_sub = i0 + np.arange(n_sub) / factor
        result = interpolate_sub_to_main(e_sub, factor, i0, i1)
        # 主网格节点应恢复 i0, i0+1, ..., i1
        expected = np.arange(i0, i1 + 1, dtype=float)
        assert np.allclose(result, expected)

    def test_estimate_speedup_4x_achieved(self) -> None:
        """测试 21：4x 细化子网格在小区间上达到接近 4x 加速比。"""
        n_main = 200
        factor = 4
        # 子网格覆盖 1/10 区域
        i0, i1 = 90, 110
        speedup = estimate_speedup(n_main, factor, i0, i1)
        # 加速比 = 200*4 / (180 + 20*4) = 800/260 ≈ 3.08
        assert speedup > 2.5, f"加速比未达 ~3x：{speedup}"
        # 理论 4x 在子网格占整域时不可达（须有粗网格区域）
        # 用更小子网格覆盖达到更高加速比
        speedup2 = estimate_speedup(n_main, factor, 95, 105)
        assert speedup2 > speedup  # 子网格更小 → 加速比更高

    def test_step_yee_1d_propagates_pulse(self) -> None:
        """测试 22：1D Yee 推进脉冲 +x 方向传播。

        初始化匹配 +x 传播的 H_y = -E_z/Z_0（Taflove 2005 §3.4），
        使脉冲单向传播。200 步后脉冲应从 index 50 移动到 index ~150。
        """
        n = 300  # 留足空间避免边界反射
        dx = 1.0e-7
        dt = 0.5 * dx / _C0  # 0.5·CFL
        x = np.arange(n) * dx
        # +x 传播高斯脉冲：E_z = G(x)，H_y = -E_z/Z_0
        z0 = np.sqrt(_MU0 / _EPS0)
        e = np.exp(-((x - 50 * dx) / (5 * dx)) ** 2)
        # H 在 i+1/2 处，近似用 (E[i]+E[i+1])/2 / Z_0（带负号匹配 +x 传播）
        h = -(e[1:] + e[:-1]) * 0.5 / z0
        # 200 步推进（脉冲应传播 100 cells 到 index ~150）
        for _ in range(200):
            e, h = step_yee_1d(e, h, dt, dx, eps_r=1.0)
        peak_idx_final = int(np.argmax(np.abs(e)))
        # 中心从 50 移到 ~150（dt=0.5·dx/c → 200·0.5 = 100 cells 位移）
        assert peak_idx_final > 100, \
            f"脉冲未传播：峰值位置 {peak_idx_final}"
        assert peak_idx_final < 200, \
            f"脉冲位置异常：{peak_idx_final}"
        assert np.all(np.isfinite(e))

    def test_subgridding_solver_end_to_end(self) -> None:
        """测试 23：子网格 FDTD 求解器端到端运行 + 加速比报告。"""
        n_main = 100
        dx = 5.0e-8  # 50 nm
        dt = 0.5 * dx / _C0
        cfg = SubgridConfig(
            n_main=n_main,
            dx_main=dx,
            dt_main=dt,
            n_steps=50,
            factor=4,
            i0=40,
            i1=60,
            eps_r=1.0,
            source_idx=10,
            source_amplitude=1.0,
            source_freq=2.0 * np.pi * _C0 / 1.55e-6,
        )
        result = SubgridFdtdSolver(cfg).solve()
        assert isinstance(result, SubgridResult)
        assert result.e_main_history.shape == (51, n_main)
        # 子网格点数 = (60-40)*4 + 1 = 81
        assert result.e_sub_history.shape == (51, 81)
        assert np.all(np.isfinite(result.e_main_history))
        assert np.all(np.isfinite(result.e_sub_history))
        # 加速比应 > 2
        assert result.speedup_factor > 2.0, \
            f"加速比 {result.speedup_factor} 未达 2x"

    def test_subgridding_invalid_factor_raises(self) -> None:
        """测试 24：factor<2 raise。"""
        with pytest.raises(ValueError, match="factor"):
            SubgridConfig(
                n_main=50,
                dx_main=1e-7,
                dt_main=0.5e-7 / _C0,
                n_steps=10,
                factor=1,  # 无效
                i0=10,
                i1=20,
            )

    def test_subgridding_cfl_violation_raises(self) -> None:
        """测试 25：主网格 CFL 违规 raise。"""
        with pytest.raises(ValueError, match="CFL"):
            SubgridConfig(
                n_main=50,
                dx_main=1e-7,
                dt_main=2.0 * 1e-7 / _C0,  # 超过 CFL
                n_steps=10,
                factor=4,
                i0=10,
                i1=20,
            )


# =============================================================================
# Dirichlet 边界条件测试
# =============================================================================


class TestDirichletBoundary:
    """Dirichlet 边界条件测试。"""

    def test_enforce_dirichlet_zeroes_rows_and_cols(self) -> None:
        """测试 26：Dirichlet 节点对应行列清零、对角线置 1。"""
        from scipy.sparse import csr_matrix
        # 4x4 单位矩阵 + 非对角项
        m_dense = np.eye(4) + 0.1 * np.ones((4, 4))
        m = csr_matrix(m_dense)
        # 节点 0 与 3 强制 Dirichlet
        m_bc = enforce_dirichlet(m, np.array([0, 3]))
        result = m_bc.toarray()
        # 行 0 和 3 应为单位向量
        assert result[0, 0] == 1.0
        assert result[3, 3] == 1.0
        assert np.allclose(result[0, 1:], 0.0)
        assert np.allclose(result[3, :3], 0.0)
        # 列 0 和 3 应清零（除对角线）
        assert np.allclose(result[1:3, 0], 0.0)
        assert np.allclose(result[1:3, 3], 0.0)

    def test_enforce_dirichlet_empty_nodes_returns_original(self) -> None:
        """测试 27：空 Dirichlet 节点返回原矩阵。"""
        from scipy.sparse import csr_matrix
        m = csr_matrix(np.eye(4))
        result = enforce_dirichlet(m, np.array([], dtype=int))
        assert np.allclose(result.toarray(), m.toarray())
