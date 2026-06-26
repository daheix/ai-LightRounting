"""M3 用 CW 源 + 稳态窗口 DFT（跳过瞬态）。

关键改进：只在 Drude 达稳态后（step > drude_settle）做 DFT，
避免瞬态污染。用探针时序手动 DFT。
"""
import time
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DrudeParams, FdtdConfig, FdtdSolver,
    ContinuousWave, TfsfBox, YeeGridFdtd, courant_dt,
)

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
OMEGA0 = 2 * np.pi * F0


def dft_windowed(ts, dt, freq, n_start, n_end):
    """对时序 ts[n_start:n_end] 做 DFT at freq。"""
    n = np.arange(n_start, n_end)
    sig = ts[n_start:n_end]
    return np.sum(sig * np.exp(-1j * 2 * np.pi * freq * n * dt)) / (n_end - n_start)


def m3_cw_steady():
    dx = dy = 8e-9
    nx, ny = 400, 80
    dt = courant_dt(dx, dy, cfl=0.49)
    v_step = C0 * dt / dx

    ramp = 5.0e-14
    wf = ContinuousWave(amplitude=1.0, frequency=F0, ramp_time=ramp)
    pml_layers = 12
    pml = CpmlConfig(layers=pml_layers, alpha=0.08)
    tfsf = TfsfBox(i0=20, i1=380, j0=pml_layers, j1=ny - pml_layers - 1)
    n_steps = 30000
    mi, mj = 60, ny // 2
    i_au = 120
    i_au_end = nx - pml_layers
    j_au_start = pml_layers
    j_au_end = ny - pml_layers
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    # 稳态开始：ramp + 传播到金 + 3/gamma 弛豫 + 反射传回探针
    ramp_step = ramp / dt
    gold_arrive = ramp_step + (i_au - tfsf.i0) / v_step
    drude_settle = gold_arrive + 5.0 / (drude.gamma * dt)  # 5/gamma = 99.3% 稳态
    refl_at_probe = gold_arrive + (i_au - mi) / v_step
    steady_start = int(drude_settle + (i_au - mi) / v_step) + 100
    print(f"ramp={ramp_step:.0f} gold_arrive={gold_arrive:.0f} "
          f"drude_settle={drude_settle:.0f} refl_at_probe={refl_at_probe:.0f}")
    print(f"steady_start={steady_start} n_steps={n_steps}")

    def run(gold):
        eps = np.ones((nx, ny))
        mask = None
        if gold:
            eps[i_au:i_au_end, j_au_start:j_au_end] = drude.eps_inf
            mask = np.zeros((nx, ny), dtype=bool)
            mask[i_au:i_au_end, j_au_start:j_au_end] = True
        grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
        cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=1.0,
                        tfsf=tfsf, tfsf_waveform=wf,
                        drude=drude if gold else None,
                        drude_mask=mask if gold else None,
                        probe_point=(mi, mj))
        return FdtdSolver(cfg).run()

    print("运行真空参考...")
    t0 = time.time()
    res_ref = run(False)
    print(f"  用时 {time.time()-t0:.1f}s")
    print("运行金 Drude...")
    t0 = time.time()
    res_au = run(True)
    print(f"  用时 {time.time()-t0:.1f}s")

    # 稳态窗口 DFT
    ts_ref = res_ref.time_series
    ts_au = res_au.time_series
    n_end = n_steps
    inc = dft_windowed(ts_ref, dt, F0, steady_start, n_end)
    tot = dft_windowed(ts_au, dt, F0, steady_start, n_end)
    refl = tot - inc
    R = (abs(refl) / abs(inc)) ** 2
    eps_au = drude.permittivity(OMEGA0)
    n_au = np.sqrt(eps_au)
    R_ana = abs((1.0 - n_au) / (1.0 + n_au)) ** 2
    err = abs(R - R_ana) / R_ana
    print(f"\n[M3-CW-SS] 窗口 [{steady_start},{n_end}]")
    print(f"[M3-CW-SS] |inc|={abs(inc):.4e} |tot|={abs(tot):.4e} |refl|={abs(refl):.4e}")
    print(f"[M3-CW-SS] |refl/inc|={abs(refl)/abs(inc):.4f} (应≈{np.sqrt(R_ana):.4f})")
    print(f"[M3-CW-SS] FDTD R={R:.5f} 解析 R={R_ana:.5f} 相对误差={err*100:.3f}% "
          f"{'PASS' if err < 0.02 else 'FAIL'} (阈值 2%)")
    return err < 0.02


if __name__ == "__main__":
    t0 = time.time()
    m3_cw_steady()
    print(f"总用时 {time.time()-t0:.1f}s")
