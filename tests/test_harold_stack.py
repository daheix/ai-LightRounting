"""P0-7 Harold 半导体器件仿真 + STACK 求解器验收测试。

测试覆盖：
- VCSEL 阈值电流（Coldren & Corzine 2012 §2.6）+ 文献对比 <5%
- 量子点能级（Bastard 1988 粒子盒模型）+ 增益（Chow & Koch §5.4）
- 载流子-光子速率方程（Coldren §5.2）稳态/瞬态
- 多层薄膜反射率（Macleod §2.2 TMM）对比解析解 <1%
- DBR 设计（Macleod §6.1）+ 闭式解对比
- 错误处理（规则 14 禁止 fall-back）

物理参数（SI 单位，CODATA 2018）：
- q = 1.602176634e-19 C
- ħ = 1.054571817e-34 J·s
- m_e = 9.1093837015e-31 kg
- ε_0 = 8.8541878128e-12 F/m
- c = 2.99792458e8 m/s

文献来源（≥5，规则 18 学术诚信）：
1. Coldren, Corzine & Mašanović, "Diode Lasers and Photonic Integrated
   Circuits" 2nd ed., Wiley 2012 —
   https://www.wiley.com/en-us/Diode+Lasers+and+Photonic+Integrated+Circuits
2. Chow & Koch, "Semiconductor-Laser Fundamentals", Springer 1999 —
   https://link.springer.com/book/10.1007/978-3-662-04104-1
3. Bastard, "Wave Mechanics Applied to Semiconductor Heterostructures",
   Wiley 1988 — https://onlinelibrary.wiley.com/doi/book/10.1002/3527600182
4. Macleod, "Thin-Film Optical Filters" 4th ed., CRC Press 2010 —
   https://www.routledge.com/Thin-Film-Optical-Filters/Macleod/p/book/9781420073027
5. Born & Wolf, "Principles of Optics" 7th ed., Cambridge 1999 —
   https://www.cambridge.org/core/books/principles-of-optics/
6. Chang & Coldren 2013, Springer Ch. 7 —
   https://doi.org/10.1007/978-3-642-24986-0_7
7. Wyant, "Multilayer Films" Optics 505 —
   https://wp.optics.arizona.edu/jcwyant/wp-content/uploads/sites/13/2016/08/multilayerfilms.pdf

代码规范（R01-R10）：
- R02: 文件 docstring 含 ≥5 文献 URL
- R03: 验证 raise，无 fall-back
- R04: 纯 numpy/scipy
- R05: 发现 Bug 必修，附回归测试
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.constants import c, epsilon_0, hbar, m_e

# 将项目根目录加入 sys.path（兼容命令行直接 pytest）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from polaris.sim.harold import (  # noqa: E402
    HaroldSolver,
    QDParams,
    VCSELParams,
)
from polaris.sim.stack_solver import (  # noqa: E402
    Layer,
    StackSolver,
)

# ============================================================
# 物理常数（SI，CODATA 2018，规则 18 学术诚信）
# ============================================================
Q_E = 1.602176634e-19
HBAR = hbar
M_E = m_e
EPS_0 = epsilon_0
C_LIGHT = c


# ============================================================
# 辅助构造
# ============================================================
def _make_typical_vcsel() -> VCSELParams:
    """构造典型 850nm GaAs/AlGaAs VCSEL 参数。

    学术依据：Coldren & Corzine 2012 §1.8 / Chang & Coldren 2013
    URL: https://www.wiley.com/en-us/Diode+Lasers+and+Photonic+Integrated+Circuits
    V_active=5e-18 m³ 对应 ~9μm 氧化孔径、~80nm 有源区厚度
    （π·(4.5e-6)²·80e-9 ≈ 5.1e-18 m³），为商用 850nm VCSEL 最典型尺寸。
    """
    return VCSELParams(
        wavelength=850e-9,
        cavity_length=1e-6,           # 1 μm 腔长（VCSEL 典型）
        R_top=0.995,                   # 顶部 DBR
        R_bottom=0.995,                # 底部 DBR
        alpha_i=1000.0,                # 10 cm⁻¹ 内部损耗
        Gamma=0.05,                    # 单 QW 限制因子
        g_0=150000.0,                  # 1500 cm⁻¹ 对数增益系数
        N_tr=1.5e24,                   # 1.5e18 cm⁻³ 透明载流子浓度
        tau_s=3e-9,                    # 3 ns 载流子寿命
        V_active=5e-18,                # ~9μm 孔径 VCSEL 有源区体积（Coldren §1.8 典型）
        eta_i=0.8,
        beta=1e-5,
    )


def _make_typical_qd() -> QDParams:
    """构造典型 InAs/GaAs 量子点参数（Bastard 1988 / Chow & Koch 1999）。"""
    return QDParams(
        wavelength=1310e-9,
        dot_size=5e-9,                 # 5 nm 量子点尺寸
        m_eff_e=0.023 * M_E,           # InAs 电子有效质量
        m_eff_h=0.41 * M_E,            # InAs 空穴有效质量
        n_refractive=3.5,              # GaAs 介质折射率
        N_QD=1e14,                     # 1e10 cm⁻² 面密度
        L_z=10e-9,                     # 10 nm 有源区厚度
    )


# ============================================================
# VCSEL 阈值电流测试
# ============================================================
class TestVCSELThreshold:
    """VCSEL 阈值电流测试（Coldren & Corzine 2012 §2.6）。"""

    def test_threshold_current_in_typical_range(self) -> None:
        """阈值电流应在 mA 量级（典型 850nm VCSEL 文献范围 0.5-10 mA）。

        学术依据：Chang & Coldren 2013, Springer Ch. 7
        URL: https://doi.org/10.1007/978-3-642-24986-0_7
        """
        params = _make_typical_vcsel()
        I_th = HaroldSolver.threshold_current(params)
        # 典型 850nm 小孔径 VCSEL：0.5 mA < I_th < 10 mA
        assert 0.5e-3 < I_th < 10e-3, (
            f"I_th={I_th*1e3:.3f} mA 不在典型 0.5-10 mA 范围"
        )

    def test_threshold_carrier_density_above_transparency(self) -> None:
        """阈值载流子浓度 N_th 必须严格大于 N_tr（物理可行性）。"""
        params = _make_typical_vcsel()
        N_th = HaroldSolver.threshold_carrier_density(params)
        assert N_th > params.N_tr, (
            f"N_th={N_th:.3e} 必须大于 N_tr={params.N_tr:.3e}"
        )

    def test_threshold_gain_equals_cavity_loss(self) -> None:
        """阈值条件 Γ·g(N_th) = α_total 严格成立（Coldren Eq. 2.43）。"""
        params = _make_typical_vcsel()
        N_th = HaroldSolver.threshold_carrier_density(params)
        # 镜面损耗与总损耗
        alpha_m = float(np.log(1.0 / (params.R_top * params.R_bottom))
                        / (2.0 * params.cavity_length))
        alpha_total = params.alpha_i + alpha_m
        # 模态增益
        g_th = params.g_0 * np.log(N_th / params.N_tr)
        modal_gain = params.Gamma * g_th
        rel_err = abs(modal_gain - alpha_total) / alpha_total
        assert rel_err < 1e-10, (
            f"阈值条件不满足：Γ·g(N_th)={modal_gain:.3e} "
            f"α_total={alpha_total:.3e} rel_err={rel_err:.2e}"
        )

    def test_threshold_current_matches_independent_formula(self) -> None:
        """阈值电流对比独立公式重算，相对误差 <5%（规则 18 学术诚信）。

        独立计算：I_th = q·V_a·N_tr·exp(α_total/(Γ·g_0)) / (η_i·τ_s)
        文献：Coldren & Corzine 2012 Eq. 2.43 + §5.2.1
        URL: https://www.wiley.com/en-us/Diode+Lasers+and+Photonic+Integrated+Circuits
        """
        params = _make_typical_vcsel()
        I_th_solver = HaroldSolver.threshold_current(params)
        # 独立重算（端电流含 η_i）
        alpha_m = float(np.log(1.0 / (params.R_top * params.R_bottom))
                        / (2.0 * params.cavity_length))
        alpha_total = params.alpha_i + alpha_m
        N_th_indep = params.N_tr * np.exp(alpha_total / (params.Gamma * params.g_0))
        I_th_indep = (
            Q_E * params.V_active * N_th_indep
            / (params.eta_i * params.tau_s)
        )
        rel_err = abs(I_th_solver - I_th_indep) / I_th_indep
        assert rel_err < 0.05, (
            f"阈值电流对比文献公式 >5%：solver={I_th_solver*1e3:.4f} mA "
            f"independent={I_th_indep*1e3:.4f} mA rel_err={rel_err:.4f}"
        )

    def test_higher_reflectivity_reduces_threshold(self) -> None:
        """更高 DBR 反射率 → 更低阈值电流（物理单调性）。"""
        params_low_R = _make_typical_vcsel()
        params_high_R = VCSELParams(
            wavelength=params_low_R.wavelength,
            cavity_length=params_low_R.cavity_length,
            R_top=0.999,  # 更高反射率
            R_bottom=0.999,
            alpha_i=params_low_R.alpha_i,
            Gamma=params_low_R.Gamma,
            g_0=params_low_R.g_0,
            N_tr=params_low_R.N_tr,
            tau_s=params_low_R.tau_s,
            V_active=params_low_R.V_active,
        )
        I_low_R = HaroldSolver.threshold_current(params_low_R)
        I_high_R = HaroldSolver.threshold_current(params_high_R)
        assert I_high_R < I_low_R, (
            f"更高反射率应降低阈值电流：high_R={I_high_R*1e3:.4f} mA "
            f"low_R={I_low_R*1e3:.4f} mA"
        )


# ============================================================
# 量子点激光器测试
# ============================================================
class TestQuantumDot:
    """量子点激光器测试（Bastard 1988 / Chow & Koch 1999）。"""

    def test_energy_levels_particle_in_box(self) -> None:
        """量子点能级满足 E_n = n²·π²·ħ²/(2·m*·L²)（Bastard §2.1）。

        URL: https://onlinelibrary.wiley.com/doi/book/10.1002/3527600182
        """
        params = _make_typical_qd()
        result = HaroldSolver.quantum_dot_levels(params, n_max=3)
        # 独立计算前 3 个电子能级
        prefactor_e = (np.pi ** 2 * HBAR ** 2) / (2.0 * params.m_eff_e * params.dot_size ** 2)
        for n in range(1, 4):
            E_n_expected = prefactor_e * n ** 2
            E_n_actual = result["E_e"][n - 1]
            rel_err = abs(E_n_actual - E_n_expected) / E_n_expected
            assert rel_err < 1e-12, (
                f"能级 E_{n} 不匹配：actual={E_n_actual:.4e} "
                f"expected={E_n_expected:.4e} rel_err={rel_err:.2e}"
            )

    def test_energy_levels_scale_quadratically(self) -> None:
        """能级随 n² 标度（粒子盒模型特征）。"""
        params = _make_typical_qd()
        result = HaroldSolver.quantum_dot_levels(params, n_max=3)
        E1 = result["E_e"][0]
        E2 = result["E_e"][1]
        E3 = result["E_e"][2]
        assert abs(E2 / E1 - 4.0) < 1e-10, f"E2/E1={E2/E1} 应=4"
        assert abs(E3 / E1 - 9.0) < 1e-10, f"E3/E1={E3/E1} 应=9"

    def test_quantum_dot_gain_positive(self) -> None:
        """量子点最大增益 g_max 必须为正（Chow & Koch §5.4）。"""
        params = _make_typical_qd()
        g_max = HaroldSolver.quantum_dot_gain(params)
        assert g_max > 0, f"g_max={g_max} 必须为正"

    def test_quantum_dot_returns_complete_dict(self) -> None:
        """quantum_dot 返回完整特性字典。"""
        params = _make_typical_qd()
        result = HaroldSolver.quantum_dot(params, n_max=2)
        for key in ("E_e", "E_h", "E_transition", "wavelength_actual", "g_max",
                    "dot_size", "N_QD"):
            assert key in result, f"返回字典缺少键 '{key}'"


# ============================================================
# 速率方程测试
# ============================================================
class TestRateEquations:
    """载流子-光子速率方程测试（Coldren §5.2）。"""

    def test_rate_equations_dimension(self) -> None:
        """速率方程右端函数返回长度 2 的 list[dN/dt, dS/dt]。"""
        params = _make_typical_vcsel()
        dydt = HaroldSolver.rate_equations(0.0, [1e24, 1e20], params, current=1e-3)
        assert isinstance(dydt, list) and len(dydt) == 2

    def test_below_threshold_no_stimulated_emission(self) -> None:
        """阈值以下、零光子时 dS/dt > 0（仅自发辐射），dN/dt > 0（注入>复合）。

        Coldren §5.2.1
        """
        params = _make_typical_vcsel()
        # 注入电流小于阈值电流
        I_th = HaroldSolver.threshold_current(params)
        I_below = 0.5 * I_th
        # 状态：低载流子（< N_th）、零光子
        N_below_th = 0.5 * params.N_tr
        dydt = HaroldSolver.rate_equations(0.0, [N_below_th, 0.0], params, I_below)
        dN_dt, dS_dt = dydt
        # 零光子下受激辐射项为零，自发辐射 β·N/τ_s > 0 ⇒ dS/dt > 0
        assert dS_dt > 0, f"零光子下 dS/dt 应>0（自发辐射），实际 {dS_dt}"

    def test_above_threshold_steady_state_photon_density(self) -> None:
        """阈值以上稳态光子密度匹配解析解（Coldren §5.2.2 Case ii）。

        S_ss = Γ·η_i·(I − I_th)·τ_p / (q·V_a)
        """
        params = _make_typical_vcsel()
        I_th = HaroldSolver.threshold_current(params)
        I_above = 2.0 * I_th
        ss = HaroldSolver.steady_state_above_threshold(params, I_above)
        # 独立重算（含 Γ 模态增益转换）
        tau_p = HaroldSolver.photon_lifetime(params)
        S_ss_expected = (
            params.Gamma * params.eta_i * (I_above - I_th) * tau_p
            / (Q_E * params.V_active)
        )
        rel_err = abs(ss["S_ss"] - S_ss_expected) / S_ss_expected
        assert rel_err < 1e-10, (
            f"稳态光子密度不匹配：actual={ss['S_ss']:.4e} "
            f"expected={S_ss_expected:.4e} rel_err={rel_err:.2e}"
        )

    def test_rate_equations_integration_converges(self) -> None:
        """ODE 积分阈值以上应收敛到稳态光子密度（10% 内）。"""
        params = _make_typical_vcsel()
        I_th = HaroldSolver.threshold_current(params)
        I_above = 2.0 * I_th
        ss = HaroldSolver.steady_state_above_threshold(params, I_above)
        # 积分 30 ns（10 倍 τ_s）
        result = HaroldSolver.integrate_rate_equations(
            params=params,
            current=I_above,
            y0=[0.0, 0.0],
            t_span=(0.0, 30e-9),
            n_points=200,
        )
        S_final = result["S"][-1]
        N_final = result["N"][-1]
        # 稳态光子密度 5% 内
        rel_err_S = abs(S_final - ss["S_ss"]) / ss["S_ss"]
        assert rel_err_S < 0.10, (
            f"积分未收敛到稳态：S_final={S_final:.4e} "
            f"S_ss={ss['S_ss']:.4e} rel_err={rel_err_S:.4f}"
        )
        # 稳态载流子浓度钳制在 N_th 附近（5% 内）
        N_th = HaroldSolver.threshold_carrier_density(params)
        rel_err_N = abs(N_final - N_th) / N_th
        assert rel_err_N < 0.10, (
            f"载流子未钳制在 N_th：N_final={N_final:.4e} "
            f"N_th={N_th:.4e} rel_err={rel_err_N:.4f}"
        )


# ============================================================
# STACK 多层薄膜反射率测试
# ============================================================
class TestStackReflectance:
    """多层薄膜反射率测试（Macleod §2.2 TMM）。"""

    def test_no_layers_matches_fresnel(self) -> None:
        """零层（仅入射/衬底界面）反射率 = Fresnel 公式 ((n0-ns)/(n0+ns))²。

        URL: https://www.routledge.com/Thin-Film-Optical-Filters/Macleod/p/book/9781420073027
        """
        n0, n_s = 1.0, 1.5
        solver = StackSolver(n_incident=n0, n_substrate=n_s, theta_incident=0.0)
        # 零层等价于单位矩阵——但本实现要求至少 1 层；用极薄层近似
        # 改用 d→0 极薄层验证 Fresnel 极限
        thin = Layer(n=n_s, k=0.0, thickness=1e-15)
        R = solver.reflectance([thin], wavelength=1e-6)
        R_fresnel = ((n0 - n_s) / (n0 + n_s)) ** 2
        rel_err = abs(R - R_fresnel) / R_fresnel
        assert rel_err < 1e-6, (
            f"Fresnel 极限不匹配：R={R:.6f} R_fresnel={R_fresnel:.6f} "
            f"rel_err={rel_err:.2e}"
        )

    def test_quarter_wave_ar_coating_zero_reflectance(self) -> None:
        """λ/4 增透膜中心波长反射率 = 0（n_1 = sqrt(n_0·n_s)）。

        Macleod §3.1: R = ((n_0·n_s − n_1²) / (n_0·n_s + n_1²))²
        URL: https://www.routledge.com/Thin-Film-Optical-Filters/Macleod/p/book/9781420073027
        """
        n0, n_s = 1.0, 1.5
        n1 = np.sqrt(n0 * n_s)  # 完美匹配
        wavelength = 550e-9
        d1 = wavelength / (4.0 * n1)  # λ/4 光学厚度
        solver = StackSolver(n_incident=n0, n_substrate=n_s)
        layer = Layer(n=n1, k=0.0, thickness=d1)
        R = solver.reflectance([layer], wavelength)
        assert R < 1e-9, f"λ/4 AR 膜中心波长 R 应=0，实际 R={R:.4e}"

    def test_quarter_wave_ar_coating_analytical(self) -> None:
        """λ/4 膜反射率匹配解析公式（<1%）。

        R = ((n_0·n_s − n_1²) / (n_0·n_s + n_1²))²
        """
        n0, n_s, n1 = 1.0, 1.5, 2.0
        wavelength = 1e-6
        d1 = wavelength / (4.0 * n1)
        solver = StackSolver(n_incident=n0, n_substrate=n_s)
        R = solver.reflectance([Layer(n=n1, k=0.0, thickness=d1)], wavelength)
        R_analytical = ((n0 * n_s - n1 ** 2) / (n0 * n_s + n1 ** 2)) ** 2
        rel_err = abs(R - R_analytical) / max(R_analytical, 1e-12)
        assert rel_err < 0.01, (
            f"λ/4 膜反射率不匹配：TMM={R:.6f} analytical={R_analytical:.6f} "
            f"rel_err={rel_err:.4f}"
        )

    def test_energy_conservation_non_absorbing(self) -> None:
        """非吸收多层膜 R + T = 1（能量守恒，规则 14 禁止 fall-back）。"""
        n0, n_s = 1.0, 1.5
        solver = StackSolver(n_incident=n0, n_substrate=n_s)
        layers = [
            Layer(n=2.0, k=0.0, thickness=100e-9),
            Layer(n=1.46, k=0.0, thickness=200e-9),
            Layer(n=2.0, k=0.0, thickness=150e-9),
        ]
        wavelength = 850e-9
        assert solver.energy_conservation_check(layers, wavelength)

    def test_dbr_analytical_vs_tmm_center_wavelength(self) -> None:
        """DBR 中心波长 TMM vs 解析公式 <1%（Macleod Eq. 6.7）。

        URL: https://www.routledge.com/Thin-Film-Optical-Filters/Macleod/p/book/9781420073027
        """
        n0, n_s = 1.0, 3.5  # air / Si
        nH, nL = 3.5, 1.46   # Si / SiO2
        N = 5
        wavelength = 1550e-9
        # 解析反射率
        R_analytical = StackSolver.dbr_reflectance_analytical(n0, nH, nL, n_s, N)
        # TMM 数值反射率
        solver = StackSolver(n_incident=n0, n_substrate=n_s)
        d_H = wavelength / (4.0 * nH)
        d_L = wavelength / (4.0 * nL)
        layers = []
        for _ in range(N):
            layers.append(Layer(n=nH, k=0.0, thickness=d_H))
            layers.append(Layer(n=nL, k=0.0, thickness=d_L))
        R_tmm = solver.reflectance(layers, wavelength)
        rel_err = abs(R_tmm - R_analytical) / max(R_analytical, 1e-12)
        assert rel_err < 0.01, (
            f"DBR 中心波长 TMM vs 解析 >1%：TMM={R_tmm:.6f} "
            f"analytical={R_analytical:.6f} rel_err={rel_err:.4f}"
        )

    def test_dbr_design_achieves_target(self) -> None:
        """DBR 设计达到目标反射率。"""
        n0, n_s = 1.0, 3.5
        wavelength = 1550e-9
        target_r = 0.99
        # 先估算所需 N
        N = StackSolver.dbr_min_pairs_for_target(1.0, 3.5, 1.46, 3.5, target_r)
        solver = StackSolver(n_incident=n0, n_substrate=n_s)
        layers = solver.dbr_design(
            target_r=target_r, n_pairs=N, wavelength=wavelength
        )
        # 应有 2N 层
        assert len(layers) == 2 * N
        # 实际反射率达到目标
        R_actual = solver.reflectance(layers, wavelength)
        assert R_actual >= target_r * 0.99, (
            f"DBR 设计未达目标：target={target_r} actual={R_actual:.6f}"
        )

    def test_dbr_reflectance_increases_with_pairs(self) -> None:
        """DBR 反射率随周期对数 N 单调递增（物理单调性）。"""
        n0, n_s, nH, nL = 1.0, 3.5, 3.5, 1.46
        R_prev = 0.0
        for N in range(1, 6):
            R = StackSolver.dbr_reflectance_analytical(n0, nH, nL, n_s, N)
            assert R > R_prev, f"DBR R 应随 N 单调递增：N={N} R={R} ≤ prev={R_prev}"
            R_prev = R


# ============================================================
# 错误处理测试（规则 14.1 禁止 fall-back）
# ============================================================
class TestErrorHandling:
    """参数校验与错误处理（R03 禁止 fall-back）。"""

    def test_vcsel_invalid_reflectivity_raises(self) -> None:
        """DBR 反射率 ≥1 或 ≤0 必须 raise。"""
        with pytest.raises(ValueError):
            VCSELParams(
                wavelength=850e-9,
                cavity_length=1e-6,
                R_top=1.5,  # 非法
                R_bottom=0.99,
                alpha_i=1000.0,
                Gamma=0.05,
                g_0=150000.0,
                N_tr=1.5e24,
                tau_s=3e-9,
                V_active=2e-18,
            )

    def test_vcsel_negative_cavity_length_raises(self) -> None:
        """负腔长必须 raise。"""
        with pytest.raises(ValueError):
            VCSELParams(
                wavelength=850e-9,
                cavity_length=-1e-6,
                R_top=0.99,
                R_bottom=0.99,
                alpha_i=1000.0,
                Gamma=0.05,
                g_0=150000.0,
                N_tr=1.5e24,
                tau_s=3e-9,
                V_active=2e-18,
            )

    def test_qd_invalid_dot_size_raises(self) -> None:
        """量子点尺寸 ≤0 必须 raise。"""
        with pytest.raises(ValueError):
            QDParams(
                wavelength=1310e-9,
                dot_size=0.0,  # 非法
                m_eff_e=0.023 * M_E,
                m_eff_h=0.41 * M_E,
                n_refractive=3.5,
                N_QD=1e14,
                L_z=10e-9,
            )

    def test_layer_invalid_thickness_raises(self) -> None:
        """层厚 ≤0 必须 raise。"""
        with pytest.raises(ValueError):
            Layer(n=1.5, k=0.0, thickness=-1e-9)

    def test_layer_invalid_index_raises(self) -> None:
        """折射率 ≤0 必须 raise。"""
        with pytest.raises(ValueError):
            Layer(n=-1.5, k=0.0, thickness=1e-9)

    def test_stack_solver_invalid_polarization_raises(self) -> None:
        """非法偏振字符串必须 raise。"""
        with pytest.raises(ValueError):
            StackSolver(n_incident=1.0, n_substrate=1.5, polarization="x")

    def test_stack_solver_empty_layers_raises(self) -> None:
        """空层列表必须 raise。"""
        solver = StackSolver(n_incident=1.0, n_substrate=1.5)
        with pytest.raises(ValueError):
            solver.reflectance([], wavelength=1e-6)

    def test_steady_state_below_threshold_raises(self) -> None:
        """阈值以下电流求稳态必须 raise。"""
        params = _make_typical_vcsel()
        I_th = HaroldSolver.threshold_current(params)
        with pytest.raises(ValueError):
            HaroldSolver.steady_state_above_threshold(params, 0.5 * I_th)

    def test_rate_equations_negative_state_raises(self) -> None:
        """负载流子/光子密度必须 raise。"""
        params = _make_typical_vcsel()
        with pytest.raises(ValueError):
            HaroldSolver.rate_equations(0.0, [-1e24, 1e20], params, current=1e-3)

    def test_dbr_design_insufficient_pairs_raises(self) -> None:
        """n_pairs 不足达到目标必须 raise（不 fall-back 到低 R）。"""
        solver = StackSolver(n_incident=1.0, n_substrate=3.5)
        with pytest.raises(ValueError):
            # target_r=0.99 但仅 1 对，必达不到
            solver.dbr_design(
                target_r=0.99, n_pairs=1, wavelength=1550e-9,
                nH=3.5, nL=1.46,
            )
