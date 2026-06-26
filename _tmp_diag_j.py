"""诊断 Drude ADE 实际 J 值与理论稳态对比。"""
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DrudeParams, FdtdConfig, FdtdSolver,
    GaussianPulse, TfsfBox, YeeGridFdtd, courant_dt,
)
from polaris.sim.fdtd.dispersive import drude_ade_coefficients

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
OMEGA0 = 2 * np.pi * F0
_EPS0 = 8.8541878128e-12


def diagnose():
    dx = dy = 8e-9
    nx, ny = 400, 80
    dt = courant_dt(dx, dy, cfl=0.49)

    tau = 2.0e-15
    t0 = 5 * tau
    wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=t0, tau=tau)
    pml = CpmlConfig(layers=12, alpha=0.08)
    tfsf = TfsfBox(i0=20, i1=380, j0=12, j1=ny - 13)
    n_steps = 3000
    i_au = 120
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    alpha, beta = drude_ade_coefficients(drude, dt)
    cb_gold = dt / (_EPS0 * drude.eps_inf)
    omega = OMEGA0

    # 正确的解析稳态 J/E：
    # J^{n+1/2} = alpha*J^{n-1/2} + beta*E^n
    # 稳态: J*exp(-i*omega*(n+1/2)*dt) = alpha*J*exp(-i*omega*(n-1/2)*dt) + beta*E*exp(-i*omega*n*dt)
    # J*(exp(-i*omega*dt/2) - alpha*exp(i*omega*dt/2)) = beta*E
    z_correct = np.exp(-1j * omega * dt / 2) - alpha * np.exp(1j * omega * dt / 2)
    J_over_E_correct = beta / z_correct
    cbJ_over_E_correct = cb_gold * J_over_E_correct
    print(f"alpha={alpha:.6f} beta={beta:.4e}")
    print(f"正确解析 cb*J/E = {cbJ_over_E_correct:.4f}")

    # 连续极限检验（用正确公式）
    eps_eff = drude.permittivity(omega)
    lhs = -1j * omega * dt
    rhs = -1j * omega * dt / drude.eps_inf * eps_eff - cbJ_over_E_correct
    print(f"eps_eff={eps_eff:.4f}")
    print(f"连续极限检验（正确公式）: lhs={lhs:.6f} rhs={rhs:.6f}")
    print(f"  差异={abs(lhs-rhs):.2e} (应≈0)")

    # Drude 弛豫时间
    tau_drude = 1.0 / drude.gamma
    print(f"\nDrude 弛豫时间 1/gamma={tau_drude:.3e}s = {tau_drude/dt:.0f} steps")
    print(f"脉冲 tau={tau:.3e}s = {tau/dt:.0f} steps")
    print(f"脉冲/弛豫 = {tau/tau_drude:.3f} (应>>1 才能达稳态)")

    # 运行仿真
    eps = np.full((nx, ny), drude.eps_inf)
    eps[:i_au, :] = 1.0
    mask = np.zeros((nx, ny), dtype=bool)
    mask[i_au:, :] = True
    grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
    cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=1.0,
                    tfsf=tfsf, tfsf_waveform=wf,
                    drude=drude, drude_mask=mask)
    solver = FdtdSolver(cfg)
    # 手动设置 _drude_mask（run() 中才设置）
    solver._drude_mask = mask

    e_z, h_x, h_y = grid.allocate_fields()
    from polaris.sim.fdtd.tfsf import Incident1D, apply_tfsf_h_correction, apply_tfsf_e_correction
    incident = Incident1D(grid.shape[0], grid.dx, grid.dt)
    j_polar = np.zeros(grid.shape, dtype=np.float64)
    for n in range(n_steps):
        t = n * grid.dt
        solver._update_h(e_z, h_x, h_y)
        apply_tfsf_h_correction(h_y, cfg.tfsf, incident, solver._db, solver._dx)
        incident.step(float(wf(t)))
        solver._update_e(e_z, h_x, h_y, j_polar)
        apply_tfsf_e_correction(e_z, cfg.tfsf, incident, solver._cb, solver._dx)

    jmid = ny // 2
    print(f"\n金界面附近场剖面 (j={jmid}):")
    print(f"{'i':>4} {'E_z':>12} {'J_polar':>12} {'cb*J':>12} {'cb*J/E':>12}")
    for i in range(i_au - 3, i_au + 12):
        ez = e_z[i, jmid]
        jp = j_polar[i, jmid]
        cbj = solver._cb[i, jmid] * jp
        ratio = cbj / ez if abs(ez) > 1e-30 else 0.0
        print(f"{i:4d} {ez:12.4e} {jp:12.4e} {cbj:12.4e} {ratio:12.4f}")


if __name__ == "__main__":
    diagnose()
