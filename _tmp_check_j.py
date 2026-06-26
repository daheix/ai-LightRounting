"""检查 Drude J 在稳态下的实际值（全金，长仿真）。"""
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DrudeParams, FdtdConfig, FdtdSolver,
    ContinuousWave, TfsfBox, YeeGridFdtd, courant_dt,
)
from polaris.sim.fdtd.dispersive import drude_ade_coefficients

C0 = 2.99792458e8
F0 = C0 / 1.55e-6
OMEGA0 = 2 * np.pi * F0
_EPS0 = 8.8541878128e-12


def check_j():
    dx = dy = 8e-9
    nx, ny = 600, 30
    dt = courant_dt(dx, dy, cfl=0.49)

    ramp = 5.0e-14
    wf = ContinuousWave(amplitude=1.0, frequency=F0, ramp_time=ramp)
    pml_layers = 12
    pml = CpmlConfig(layers=pml_layers, alpha=0.08)
    tfsf = TfsfBox(i0=20, i1=560, j0=pml_layers, j1=ny - pml_layers - 1)
    n_steps = 30000
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    eps = np.full((nx, ny), drude.eps_inf)
    mask = np.ones((nx, ny), dtype=bool)
    mask[:pml_layers, :] = False
    mask[nx - pml_layers:, :] = False
    mask[:, :pml_layers] = False
    mask[:, ny - pml_layers:] = False
    grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
    cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=drude.eps_inf,
                    tfsf=tfsf, tfsf_waveform=wf,
                    drude=drude, drude_mask=mask)
    solver = FdtdSolver(cfg)
    solver._drude_mask = mask

    e_z, h_x, h_y = grid.allocate_fields()
    from polaris.sim.fdtd.tfsf import Incident1D, apply_tfsf_h_correction, apply_tfsf_e_correction
    incident = Incident1D(grid.shape[0], grid.dx, grid.dt)
    j_polar = np.zeros(grid.shape, dtype=np.float64)

    # 运行到稳态
    for n in range(n_steps):
        t = n * grid.dt
        solver._update_h(e_z, h_x, h_y)
        apply_tfsf_h_correction(h_y, cfg.tfsf, incident, solver._db, solver._dx)
        incident.step(float(wf(t)))
        solver._update_e(e_z, h_x, h_y, j_polar)
        apply_tfsf_e_correction(e_z, cfg.tfsf, incident, solver._cb, solver._dx)

    # 检查 J 在不同位置的值
    jmid = ny // 2
    alpha, beta = drude_ade_coefficients(drude, dt)
    cb_gold = dt / (_EPS0 * drude.eps_inf)

    # 解析稳态 cb*J/E
    z = np.exp(-1j * OMEGA0 * dt / 2) - alpha * np.exp(1j * OMEGA0 * dt / 2)
    cbJ_over_E_ana = cb_gold * beta / z
    print(f"解析稳态 cb*J/E = {cbJ_over_E_ana:.6f}")
    print(f"  (实部={np.real(cbJ_over_E_ana):.6f} 虚部={np.imag(cbJ_over_E_ana):.6f})")

    # 仿真 J 值
    print(f"\n仿真 J/E 比值（稳态后）:")
    print(f"{'i':>4} {'E_z':>12} {'J':>12} {'cb*J':>12} {'cb*J/E':>12}")
    for i in [25, 30, 35, 40, 50]:
        ez = e_z[i, jmid]
        jp = j_polar[i, jmid]
        cbj = solver._cb[i, jmid] * jp
        ratio = cbj / ez if abs(ez) > 1e-30 else 0.0
        print(f"{i:4d} {ez:12.4e} {jp:12.4e} {cbj:12.4e} {ratio:12.6f}")

    # 检查：J 是否在 mask 外被强制为 0
    print(f"\nmask 外 J 值 (i=10, PML 内): {j_polar[10, jmid]:.4e}")
    print(f"mask 内 J 值 (i=30): {j_polar[30, jmid]:.4e}")

    # 对比：用 DFT 提取 E 和 J 在 f0 的复振幅
    # 重新运行，记录时序
    print("\n重新运行记录时序...")
    e_z2, h_x2, h_y2 = grid.allocate_fields()
    incident2 = Incident1D(grid.shape[0], grid.dx, grid.dt)
    j_polar2 = np.zeros(grid.shape, dtype=np.float64)
    n_rec = 5000
    n_start = 20000  # 稳态后
    e_ts = np.zeros(n_rec)
    j_ts = np.zeros(n_rec)
    for n in range(n_start + n_rec):
        t = n * grid.dt
        solver._update_h(e_z2, h_x2, h_y2)
        apply_tfsf_h_correction(h_y2, cfg.tfsf, incident2, solver._db, solver._dx)
        incident2.step(float(wf(t)))
        solver._update_e(e_z2, h_x2, h_y2, j_polar2)
        apply_tfsf_e_correction(e_z2, cfg.tfsf, incident2, solver._cb, solver._dx)
        if n >= n_start:
            k = n - n_start
            e_ts[k] = e_z2[30, jmid]
            j_ts[k] = j_polar2[30, jmid]

    # DFT at f0
    n_arr = np.arange(n_rec)
    e_dft = np.sum(e_ts * np.exp(-1j * 2 * np.pi * F0 * (n_arr + n_start) * dt)) / n_rec
    j_dft = np.sum(j_ts * np.exp(-1j * 2 * np.pi * F0 * (n_arr + n_start) * dt)) / n_rec
    cb_j_over_e = solver._cb[30, jmid] * j_dft / e_dft if abs(e_dft) > 0 else 0
    print(f"DFT E={e_dft:.4e} J={j_dft:.4e}")
    print(f"DFT cb*J/E = {cb_j_over_e:.6f}")
    print(f"  (实部={np.real(cb_j_over_e):.6f} 虚部={np.imag(cb_j_over_e):.6f})")
    print(f"解析 cb*J/E = {cbJ_over_E_ana:.6f}")
    print(f"  (实部={np.real(cbJ_over_E_ana):.6f} 虚部={np.imag(cbJ_over_E_ana):.6f})")
    print(f"虚部比 = {np.imag(cb_j_over_e)/np.imag(cbJ_over_E_ana):.4f} (应≈1)")


if __name__ == "__main__":
    check_j()
