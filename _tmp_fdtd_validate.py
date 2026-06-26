"""A09-FDTD 验收脚本 M1-M4（临时，验证后删除）。

M1: 自由空间 TFSF 平面波注入保真度（峰值误差 <1e-3）
M2: CPML 边界反射 ≤ -60 dB
M3: 金 Drude 半空间反射率 vs 解析 Drude-Fresnel < 2%
M4: SOI 对称平板波导 S21 相位 vs 解析 β·L
"""
import time
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DftMonitor, DrudeParams, FdtdConfig, FdtdSolver, GaussianPulse,
    Incident1D, SParamExtractor, TfsfBox, YeeGridFdtd, courant_dt,
)
from polaris.sim.fdtd.sources import DipoleSource

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
OMEGA0 = 2 * np.pi * F0


def m1():
    """M1: TF 区 E_z 应精确等于 1D 辅助网格 e_inc（完美 TFSF 零泄漏）。

    2D 网格 y 方向边界（PML/PEC）会截断 +x 平面波产生 y 方向衍射
    （ky≠0 分量相速度慢于 ky=0），扭曲 TF 区中部场。为使 TF 区中部
    在仿真时长内保持纯 +x 平面波（ky=0），须 ny 足够大且 n_steps 足够短，
    使 y 衍射（从 TF 边界 j0 向中部传播，速度 c·CFL_2D）传不到中部：
        jmid - j0 > n_steps · CFL_2D   （CFL_2D = c·Δt·√(1/Δx²+1/Δy²)）
    取 ny=300, n_steps=150：jmid-j0=138 > 150·0.49=73.5，衍射传不到中部。
    """
    dx = dy = 20e-9
    nx, ny = 200, 300
    dt = courant_dt(dx, dy, cfl=0.49)
    grid = YeeGridFdtd((nx, ny), dx, dy, dt, np.ones((nx, ny)))
    tau = 0.3e-14
    wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=3 * tau, tau=tau)
    pml = CpmlConfig(layers=12, alpha=0.08, r_target=1e-8)
    tfsf = TfsfBox(i0=20, i1=80, j0=12, j1=ny - 13)
    n_steps = 150
    cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=1.0,
                    tfsf=tfsf, tfsf_waveform=wf)
    res = FdtdSolver(cfg).run()
    inc = Incident1D(nx, dx, dt)
    for n in range(n_steps):
        inc.step(float(wf(n * dt)))
    jmid = ny // 2
    i0, i1 = tfsf.i0, tfsf.i1
    ez_tf = res.e_z[i0:i1 + 1, jmid]
    ref = inc.e_inc[i0:i1 + 1]
    m = np.abs(ref) > 1e-4 * (np.max(np.abs(ref)) + 1e-30)
    err = np.max(np.abs(ez_tf[m] - ref[m]))
    peak = np.max(np.abs(ref))
    rel = err / peak
    print(f"[M1] 绝对误差={err:.3e} 峰值={peak:.3e} 相对={rel:.3e} "
          f"{'PASS' if rel < 1e-3 else 'FAIL'} (阈值 1e-3)")
    return rel < 1e-3


def m2():
    """M2: CPML 反射 dB。incident 首过 vs reflected 返回。"""
    dx = dy = 20e-9
    nx, ny = 500, 60
    dt = courant_dt(dx, dy, cfl=0.49)
    grid = YeeGridFdtd((nx, ny), dx, dy, dt, np.ones((nx, ny)))
    tau = 0.4e-14
    wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=3 * tau, tau=tau)
    pml = CpmlConfig(layers=16, alpha=0.08, r_target=1e-8)
    tfsf = TfsfBox(i0=6, i1=470, j0=2, j1=ny - 3)
    n_steps = 3200
    mi, mj = 40, ny // 2
    cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=1.0,
                    tfsf=tfsf, tfsf_waveform=wf, probe_point=(mi, mj))
    res = FdtdSolver(cfg).run()
    ts = res.time_series
    inc_peak = np.max(np.abs(ts[50:260]))
    refl_peak = np.max(np.abs(ts[2450:3000]))
    r_db = 20 * np.log10(refl_peak / inc_peak) if refl_peak > 0 else -np.inf
    print(f"[M2] inc={inc_peak:.3e} refl={refl_peak:.3e} 反射={r_db:.1f} dB "
          f"{'PASS' if r_db <= -60 else 'FAIL'} (阈值 -60 dB)")
    return r_db <= -60


def m3():
    """M3: 金 Drude 半空间反射率。双运行 refl=tot-inc。"""
    dx = dy = 8e-9
    nx, ny = 600, 70
    dt = courant_dt(dx, dy, cfl=0.49)
    tau = 1.0e-14
    wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=4 * tau, tau=tau)
    pml = CpmlConfig(layers=16, alpha=0.08)
    tfsf = TfsfBox(i0=6, i1=560, j0=2, j1=ny - 3)
    n_steps = 4500
    mi, mj = 60, ny // 2
    i_au = 340
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    def run(gold):
        eps = np.ones((nx, ny))
        mask = None
        if gold:
            eps = np.full((nx, ny), drude.eps_inf)
            eps[:i_au, :] = 1.0
            mask = np.zeros((nx, ny), dtype=bool)
            mask[i_au:, :] = True
        grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
        mon = DftMonitor(position=(mi, mj), frequency=F0, name="m")
        cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=1.0,
                        tfsf=tfsf, tfsf_waveform=wf,
                        drude=drude if gold else None,
                        drude_mask=mask if gold else None, monitors=[mon])
        return FdtdSolver(cfg).run()

    res_ref = run(False)
    res_au = run(True)
    inc = res_ref.dft_results["m"]
    tot = res_au.dft_results["m"]
    refl = tot - inc
    R = (abs(refl) / abs(inc)) ** 2
    eps_au = drude.permittivity(OMEGA0)
    n_au = np.sqrt(eps_au)
    R_ana = abs((1.0 - n_au) / (1.0 + n_au)) ** 2
    err = abs(R - R_ana) / R_ana
    print(f"[M3] ε_Au={eps_au:.2f} n_Au={n_au:.4f}")
    print(f"[M3] FDTD R={R:.5f} 解析 R={R_ana:.5f} 相对误差={err*100:.3f}% "
          f"{'PASS' if err < 0.02 else 'FAIL'} (阈值 2%)")
    return err < 0.02


def m4():
    """M4: SOI 对称平板 TE0 模 S21 相位 vs 解析 β·L。"""
    n_core, n_clad = 3.476, 1.444
    eps_core = n_core ** 2
    eps_clad = n_clad ** 2
    a = 0.10e-6
    k0 = 2 * np.pi / LAM
    V = k0 * a * np.sqrt(n_core ** 2 - n_clad ** 2)
    u = np.linspace(1e-4, np.pi / 2 - 1e-4, 400001)
    w = np.sqrt(np.clip(V ** 2 - u ** 2, 0, None))
    f = u * np.tan(u) - w
    cross = np.where(np.diff(np.sign(f)) != 0)[0]
    if len(cross) == 0:
        raise RuntimeError("未找到 TE0 模根")
    i0 = cross[0]
    u_root = u[i0] - f[i0] * (u[i0 + 1] - u[i0]) / (f[i0 + 1] - f[i0])
    kc = u_root / a
    gamma = np.sqrt(max(V ** 2 - u_root ** 2, 0)) / a
    beta = np.sqrt((n_core * k0) ** 2 - kc ** 2)
    print(f"[M4] V={V:.3f} neff={beta/k0:.5f} γ={gamma:.3e}")

    dx = dy = 6e-9
    nx, ny = 900, 160
    dt = courant_dt(dx, dy, cfl=0.49)
    yc = ny // 2
    yy = (np.arange(ny) - yc) * dy
    eps = np.full((nx, ny), eps_clad)
    eps[:, np.abs(yy) < a] = eps_core
    grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
    # 模式剖面
    prof = np.where(np.abs(yy) < a, np.cos(kc * yy),
                    np.cos(kc * a) * np.exp(-gamma * (np.abs(yy) - a)))
    prof /= np.max(np.abs(prof))
    eps_src = eps[8, :]  # 源行 eps_r（补偿 1/ε 使注入 ∝ prof）
    tau = 6e-14
    sources = []
    for j in range(ny):
        if abs(prof[j]) > 0.02:
            sources.append(DipoleSource(
                position=(8, j),
                waveform=GaussianPulse(amplitude=float(prof[j] * eps_src[j] * 1e-9),
                                       frequency=F0, t0=4 * tau, tau=tau),
                current_moment=1.0,
            ))
    i1, i2 = 200, 700
    L = (i2 - i1) * dx
    mon_in = DftMonitor(position=(i1, yc), frequency=F0, name="in")
    mon_out = DftMonitor(position=(i2, yc), frequency=F0, name="out")
    ext = SParamExtractor(name="S21", input_monitor=mon_in, output_monitor=mon_out)
    pml = CpmlConfig(layers=20, alpha=0.04)
    cfg = FdtdConfig(grid=grid, n_steps=8500, cpml=pml, eps_r_bg=eps_clad,
                    dipole_sources=sources, monitors=[mon_in, mon_out],
                    s_param_extractors=[ext])
    res = FdtdSolver(cfg).run()
    S21 = res.s_params["S21"]
    phase_m = np.angle(S21)
    phase_a = -beta * L
    dphase = (phase_m - phase_a + np.pi) % (2 * np.pi) - np.pi
    rel = abs(dphase) / abs(phase_a)
    print(f"[M4] S21={S21:.4f} |S21|={abs(S21):.4f} "
          f"φ_meas={phase_m:.4f} φ_ana={phase_a:.4f} Δ={dphase:.3e}rad 相对={rel:.3e}")
    print(f"[M4] {'PASS' if rel < 1e-3 else 'FAIL'} (阈值相对 1e-3)")
    return rel < 1e-3


if __name__ == "__main__":
    print("=" * 60)
    res = {}
    for name, fn in (("M1", m1), ("M2", m2), ("M3", m3), ("M4", m4)):
        t0 = time.time()
        try:
            res[name] = fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            res[name] = False
        print(f"({name} 用时 {time.time()-t0:.1f}s)")
        print("-" * 60)
    print("汇总:", {k: "PASS" if v else "FAIL" for k, v in res.items()})
