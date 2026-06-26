"""M3 长脉冲 + 修复金-PML 重叠。

关键修复：
1. tau=5e-14 >> 1/gamma=2.45e-14（Drude 达稳态）
2. 金区域不与 PML 重叠（mask 与 eps_r 限制在内部）
3. PML 区域保持真空 eps_r=1.0
"""
import time
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DftMonitor, DrudeParams, FdtdConfig, FdtdSolver,
    GaussianPulse, TfsfBox, YeeGridFdtd, courant_dt,
)

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
OMEGA0 = 2 * np.pi * F0


def m3_fixed():
    dx = dy = 8e-9
    nx, ny = 400, 80
    dt = courant_dt(dx, dy, cfl=0.49)
    v_step = C0 * dt / dx

    tau = 5.0e-14
    t0 = 3 * tau
    wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=t0, tau=tau)
    pml_layers = 12
    pml = CpmlConfig(layers=pml_layers, alpha=0.08)
    tfsf = TfsfBox(i0=20, i1=380, j0=pml_layers, j1=ny - pml_layers - 1)
    n_steps = 40000
    mi, mj = 60, ny // 2
    i_au = 120
    # 金区域不与 PML 重叠
    i_au_end = nx - pml_layers  # 388
    j_au_start = pml_layers  # 12
    j_au_end = ny - pml_layers  # 68
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    t0_step = t0 / dt
    gold_arrive = t0_step + (i_au - tfsf.i0) / v_step
    refl_at_probe = gold_arrive + (i_au - mi) / v_step
    print(f"tau/tau_drude={tau/(1.0/drude.gamma):.2f}")
    print(f"t0_step={t0_step:.0f} gold_arrive={gold_arrive:.0f} "
          f"refl_at_probe={refl_at_probe:.0f} n_steps={n_steps}")
    print(f"金区域: i=[{i_au},{i_au_end-1}] j=[{j_au_start},{j_au_end-1}]")

    def run(gold):
        eps = np.ones((nx, ny))  # 全真空（含 PML）
        mask = None
        if gold:
            # 金仅在内部区域（不与 PML 重叠）
            eps[i_au:i_au_end, j_au_start:j_au_end] = drude.eps_inf
            mask = np.zeros((nx, ny), dtype=bool)
            mask[i_au:i_au_end, j_au_start:j_au_end] = True
        grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
        mon = DftMonitor(position=(mi, mj), frequency=F0, name="m")
        cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=1.0,
                        tfsf=tfsf, tfsf_waveform=wf,
                        drude=drude if gold else None,
                        drude_mask=mask if gold else None, monitors=[mon])
        return FdtdSolver(cfg).run()

    print("运行真空参考...")
    t0 = time.time()
    res_ref = run(False)
    print(f"  用时 {time.time()-t0:.1f}s")
    print("运行金 Drude...")
    t0 = time.time()
    res_au = run(True)
    print(f"  用时 {time.time()-t0:.1f}s")

    inc = res_ref.dft_results["m"]
    tot = res_au.dft_results["m"]
    refl = tot - inc
    R = (abs(refl) / abs(inc)) ** 2
    eps_au = drude.permittivity(OMEGA0)
    n_au = np.sqrt(eps_au)
    R_ana = abs((1.0 - n_au) / (1.0 + n_au)) ** 2
    err = abs(R - R_ana) / R_ana
    print(f"[M3] |inc|={abs(inc):.4e} |tot|={abs(tot):.4e} |refl|={abs(refl):.4e}")
    print(f"[M3] |refl/inc|={abs(refl)/abs(inc):.4f} (应≈{np.sqrt(R_ana):.4f})")
    print(f"[M3] ε_Au={eps_au:.2f} n_Au={n_au:.4f}")
    print(f"[M3] FDTD R={R:.5f} 解析 R={R_ana:.5f} 相对误差={err*100:.3f}% "
          f"{'PASS' if err < 0.02 else 'FAIL'} (阈值 2%)")
    return err < 0.02


if __name__ == "__main__":
    t0 = time.time()
    m3_fixed()
    print(f"总用时 {time.time()-t0:.1f}s")
