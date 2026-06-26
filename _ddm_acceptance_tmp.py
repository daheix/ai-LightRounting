"""A08-DDM 验收脚本（M1/M2/M3，运行后删除）。"""

import numpy as np

from polaris.sim.ddm import DdmConfig, solve_ddm
from polaris.sim.ddm.scharfetter_gummel import (
    EPS_0,
    EPS_R_SI,
    N_I_SI,
    Q_E,
    V_T,
)


def main() -> None:
    # 网格设置：1D PN 结（ny=1），2 μm 长
    nx, ny = 200, 1
    L = 2e-6  # 2 μm
    dx = L / nx
    dy = 1e-6  # 任意，1D 不影响结果

    # 对称突变结掺杂（P 区 N_A = N 区 N_D = N = 1e21 m^-3 = 1e15 cm^-3）
    N = 1.0e21
    x = np.linspace(0.0, L, nx)
    doping_p = np.where(x < L / 2, N, 0.0).reshape(nx, ny)
    doping_n = np.where(x >= L / 2, N, 0.0).reshape(nx, ny)

    # === M1: PN 结正偏 0.7V，Gummel 迭代 <= 50 次收敛 ===
    print("=" * 60)
    print("M1: PN 结正偏 0.7V Gummel 收敛测试")
    print("=" * 60)
    config_fwd = DdmConfig(
        nx=nx, ny=ny, dx=dx, dy=dy,
        eps_rel=EPS_R_SI,
        doping_n=doping_n,
        doping_p=doping_p,
        contacts={"west": 0.0, "east": 0.7},
        max_iter=100,
        tol=1e-6,
    )
    result_fwd = solve_ddm(config_fwd)
    print(f"  收敛状态: {result_fwd.converged}")
    print(f"  Gummel 迭代次数: {result_fwd.n_iterations}")
    assert result_fwd.converged, "M1 失败：未收敛"
    assert result_fwd.n_iterations <= 50, f"M1 失败：迭代次数 {result_fwd.n_iterations} > 50"
    print(f"  OK M1 通过：迭代 {result_fwd.n_iterations} <= 50 次")

    # === M2: 平衡 PN 结耗尽区宽度 vs 解析公式 ===
    print("\n" + "=" * 60)
    print("M2: 1D 平衡 PN 结耗尽区宽度 vs Debye 长度公式")
    print("=" * 60)
    config_eq = DdmConfig(
        nx=nx, ny=ny, dx=dx, dy=dy,
        eps_rel=EPS_R_SI,
        doping_n=doping_n,
        doping_p=doping_p,
        contacts={"west": 0.0, "east": 0.0},
        max_iter=100,
        tol=1e-6,
    )
    result_eq = solve_ddm(config_eq)
    print(f"  平衡 Gummel 收敛: {result_eq.converged}, 迭代 {result_eq.n_iterations} 次")

    # 解析公式（McKelvey 1966 §8.3，对称突变结）
    V_bi = 2.0 * V_T * np.log(N / N_I_SI)
    eps = EPS_0 * EPS_R_SI
    W_analytic = np.sqrt(4.0 * eps * V_bi / (Q_E * N))
    L_D = np.sqrt(eps * V_T / (Q_E * N))
    print(f"  内建电势 V_bi = {V_bi:.4f} V")
    print(f"  Debye 长度 L_D = {L_D*1e9:.2f} nm")
    print(f"  解析耗尽区宽度 W = {W_analytic*1e6:.4f} um = {W_analytic*1e9:.2f} nm")

    # 数值耗尽区宽度：空间电荷 rho 在耗尽区近似 = +/-q*N
    rho = Q_E * (
        result_eq.hole_density - result_eq.electron_density + doping_n - doping_p
    )
    threshold = 0.5 * Q_E * N
    rho_1d = rho[:, 0]
    depletion_indices = np.where(np.abs(rho_1d) > threshold)[0]
    if depletion_indices.size == 0:
        print("  FAIL M2：未检测到耗尽区")
        raise AssertionError("M2 失败")
    W_numeric = (depletion_indices[-1] - depletion_indices[0] + 1) * dx
    rel_error = abs(W_numeric - W_analytic) / W_analytic
    print(f"  数值耗尽区宽度 W = {W_numeric*1e6:.4f} um = {W_numeric*1e9:.2f} nm")
    print(f"  相对误差 = {rel_error*100:.2f}%")
    assert rel_error <= 0.05, f"M2 失败：误差 {rel_error*100:.2f}% > 5%"
    print(f"  OK M2 通过：误差 {rel_error*100:.2f}% <= 5%")

    # === M3: DDM 焦耳热 -> HEAT 耦合 ===
    print("\n" + "=" * 60)
    print("M3: DDM 焦耳热 -> HEAT 耦合（heat/coupling.py:ddm_to_heat）")
    print("=" * 60)
    from polaris.sim.heat.coupling import ddm_to_heat

    Q_joule = ddm_to_heat(result_fwd)
    print(f"  DDM current_density_x shape: {result_fwd.current_density_x.shape}")
    print(f"  DDM current_density_y shape: {result_fwd.current_density_y.shape}")
    print(f"  DDM conductivity shape: {result_fwd.conductivity.shape}")
    print(f"  焦耳热 Q = J^2/sigma (W/m^3):")
    print(f"    max = {np.max(Q_joule):.3e}")
    print(f"    mean = {np.mean(Q_joule):.3e}")
    print(f"    min = {np.min(Q_joule):.3e}")
    assert np.all(np.isfinite(Q_joule)), "M3 失败：焦耳热含非有限值"
    assert np.all(Q_joule >= 0.0), "M3 失败：焦耳热出现负值"
    print(f"  OK M3 通过：DDM 焦耳热已成功注入 heat 耦合接口")

    print("\n" + "=" * 60)
    print("ALL PASS: 全部 M1/M2/M3 验收通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
