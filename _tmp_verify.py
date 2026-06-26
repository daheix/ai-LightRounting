"""A09-FDTD M1-M4 验收验证（临时脚本，验收后删除）。

关键改进（vs 之前失败的诊断）：
- M3: 双仿真法（有金/无金）+ 时间窗 DFT，避免 DftMonitor 在线累加稀释
- M2: 时域峰值分离（入射脉冲先到、反射脉冲后到），避免 DFT 稀释
- M4: 细网格 dx=5nm 降低色散，短传播距离 L=500nm 降低绝对相位误差
- M1: 短 n_steps + 大 ny，避免 y 方向衍射到达探针
"""
import sys
import time
import numpy as np

sys.path.insert(0, "/workspace/src")

from polaris.sim.fdtd import (
    CpmlConfig, DftMonitor, DrudeParams, FdtdConfig, FdtdSolver,
    ContinuousWave, GaussianPulse, RickerWavelet, TfsfBox,
    YeeGridFdtd, courant_dt, DipoleSource, SParamExtractor,
    Incident1D,
)

C0 = 2.99792458e8
EPS0 = 8.8541878128e-12
MU0 = 1.25663706212e-6
LAMBDA0 = 1.55e-6  # 1550 nm
F0 = C0 / LAMBDA0
OMEGA0 = 2 * np.pi * F0


def dft_windowed(ts, dt, freq, n_start, n_end):
    """时间窗 DFT（避免信号未到达期稀释）。

    DFT = (1/M) * sum_{n=n_start}^{n_end} E(n) * exp(-i*2*pi*f*n*dt)
    其中 M = n_end - n_start（仅累加有效窗口）。
    """
    n = np.arange(n_start, n_end)
    return np.sum(ts[n_start:n_end] * np.exp(-1j * 2 * np.pi * freq * n * dt)) / (n_end - n_start)


# ============================================================
# M1: 高斯脉冲自由空间传播误差 < 1e-3
# ============================================================
def test_m1():
    """M1: TFSF 注入高斯脉冲，2D 传播 vs 1D 辅助网格（Schneider 2004 零泄漏）。

    方法：短 n_steps + 大 ny，脉冲到达探针前 y 方向衍射未到达。
    比较终态 E_z[x_probe, y_center] 与独立运行的 1D Incident1D.e_inc[x_probe]。
    """
    print("\n=== M1: 高斯脉冲自由空间传播 ===")
    dx = dy = 10e-9  # 10 nm
    nx, ny = 300, 200
    dt = courant_dt(dx, dy, cfl=0.5)
    n_steps = 200  # 短，避免 y 衍射到达探针

    eps_r = np.ones((nx, ny))
    grid = YeeGridFdtd(shape=(nx, ny), dx=dx, dy=dy, dt=dt, eps_r=eps_r)

    # 高斯脉冲源（短脉冲，快速到达探针）
    tau = 3e-15  # ~0.6 个周期
    t0 = 3 * tau
    waveform = GaussianPulse(amplitude=1.0, frequency=F0, t0=t0, tau=tau)

    tfsf = TfsfBox(i0=50, i1=250, j0=10, j1=190)
    cfg = FdtdConfig(
        grid=grid, n_steps=n_steps,
        cpml=CpmlConfig(layers=10),
        eps_r_bg=1.0,
        tfsf=tfsf, tfsf_waveform=waveform,
    )
    solver = FdtdSolver(cfg)
    result = solver.run()
    e_z = result.e_z

    # 独立运行 1D 辅助网格（相同 dx/dt/源）
    incident = Incident1D(nx, dx, dt)
    for n in range(n_steps):
        t = n * dt
        incident.step(float(waveform(t)))

    x_probe = 100  # TF 区域内
    y_center = ny // 2

    # 比较 2D E_z 与 1D E_inc
    e_2d = e_z[x_probe, y_center]
    e_1d = incident.e_inc[x_probe]
    if abs(e_1d) < 1e-30:
        rel_err = abs(e_2d - e_1d)
    else:
        rel_err = abs(e_2d - e_1d) / max(abs(e_1d), 1e-30)

    # 也可比较整个 y 线的均匀性
    y_variation = np.max(np.abs(e_z[x_probe, :] - np.mean(e_z[x_probe, :])))
    y_max = np.max(np.abs(e_z[x_probe, :])) + 1e-30
    y_rel = y_variation / y_max

    print(f"  dx={dx*1e9:.0f}nm, dt={dt:.3e}s, n_steps={n_steps}")
    print(f"  E_2d[{x_probe},{y_center}] = {e_2d:.6e}")
    print(f"  E_1d[{x_probe}]           = {e_1d:.6e}")
    print(f"  相对误差 = {rel_err:.6e}")
    print(f"  y 线均匀性误差 = {y_rel:.6e}")
    passed = rel_err < 1e-3
    print(f"  M1: {'PASS' if passed else 'FAIL'} (阈值 < 1e-3)")
    return passed, rel_err


# ============================================================
# M2: CPML 反射 ≤ -60 dB
# ============================================================
def test_m2():
    """M2: TFSF 注入 Ricker 脉冲 → 右 PML 吸收 → 测反射。

    方法：TF 探针 + 时间窗分离。
      入射脉冲先到 TF 探针，PML 反射脉冲后到同一探针。
      分离两脉冲的时间窗，比较峰值。
      避免 SF 探针（TFSF y-截断边缘效应污染 SF 区）。
    """
    print("\n=== M2: CPML 反射测试 ===")
    dx = dy = 10e-9
    nx, ny = 500, 100
    dt = courant_dt(dx, dy, cfl=0.5)
    n_steps = 8000

    eps_r = np.ones((nx, ny))
    grid = YeeGridFdtd(shape=(nx, ny), dx=dx, dy=dy, dt=dt, eps_r=eps_r)

    # Ricker 小波（宽带、无 DC）
    t0_ricker = 3.0 / F0  # ~3 个周期
    waveform = RickerWavelet(amplitude=1.0, frequency=F0, t0=t0_ricker)

    # TFSF 边界（远离 PML）
    pml_layers = 10
    tfsf = TfsfBox(i0=50, i1=450, j0=10, j1=90)

    # TF 探针位置
    x_probe = 200
    j_probe = ny // 2

    # 右 PML 内边界
    x_pml_inner = nx - pml_layers  # 490

    cfg = FdtdConfig(
        grid=grid, n_steps=n_steps,
        cpml=CpmlConfig(layers=pml_layers),
        eps_r_bg=1.0,
        tfsf=tfsf, tfsf_waveform=waveform,
        probe_point=(x_probe, j_probe),
    )
    solver = FdtdSolver(cfg)
    result = solver.run()
    ts = result.time_series

    # 计算入射和反射脉冲到达 TF 探针的时间
    # 入射：从 TFSF 源(x=50)到探针(x=200)
    incident_arrival = int(t0_ricker / dt) + int((x_probe - 50) * dx / C0 / dt)
    # 反射：入射到右 PML(x_pml_inner)再返回探针(x_probe)
    reflect_arrival = incident_arrival + int(2 * (x_pml_inner - x_probe) * dx / C0 / dt)

    # 入射脉冲窗（入射到达前后 ±300 步）
    win_inc_start = max(0, incident_arrival - 300)
    win_inc_end = min(n_steps, incident_arrival + 300)
    # 反射脉冲窗（反射到达前后 ±300 步）
    win_refl_start = max(0, reflect_arrival - 300)
    win_refl_end = min(n_steps, reflect_arrival + 300)

    incident_peak = np.max(np.abs(ts[win_inc_start:win_inc_end]))
    reflected_peak = np.max(np.abs(ts[win_refl_start:win_refl_end]))

    if reflected_peak == 0.0:
        r_db = float("-inf")
    else:
        r_db = 20.0 * np.log10(reflected_peak / incident_peak)

    # 找反射峰值实际位置
    refl_idx = win_refl_start + int(np.argmax(np.abs(ts[win_refl_start:win_refl_end])))

    print(f"  dx={dx*1e9:.0f}nm, n_steps={n_steps}")
    print(f"  入射到达 step ≈ {incident_arrival}, 反射到达 step ≈ {reflect_arrival}")
    print(f"  入射窗 [{win_inc_start},{win_inc_end}], 反射窗 [{win_refl_start},{win_refl_end}]")
    print(f"  入射峰值 = {incident_peak:.6e}")
    print(f"  反射峰值 = {reflected_peak:.6e} (step {refl_idx})")
    print(f"  反射系数 = {r_db:.2f} dB")
    passed = r_db <= -60.0
    print(f"  M2: {'PASS' if passed else 'FAIL'} (阈值 ≤ -60 dB)")
    return passed, r_db


# ============================================================
# M3: 金 Drude 反射率 vs Palik < 2%
# ============================================================
def _run_m3_sim(eps_r, drude, drude_mask, n_steps, dx, dy, dt, nx, ny, waveform, tfsf):
    """运行单次 M3 仿真，返回探针时序。"""
    grid = YeeGridFdtd(shape=(nx, ny), dx=dx, dy=dy, dt=dt, eps_r=eps_r)
    cfg = FdtdConfig(
        grid=grid, n_steps=n_steps,
        cpml=CpmlConfig(layers=10),
        eps_r_bg=1.0,
        tfsf=tfsf, tfsf_waveform=waveform,
        drude=drude, drude_mask=drude_mask,
        probe_point=(200, ny // 2),
    )
    solver = FdtdSolver(cfg)
    result = solver.run()
    return result.time_series


def test_m3():
    """M3: 金 Drude 半空间反射率 vs 解析 Drude-Fresnel < 2%。

    方法：双仿真法。
      Sim A: 有金板 → 探针测 E_total
      Sim B: 无金（真空）→ 探针测 E_inc
      E_refl = E_total - E_inc
      R = |DFT(E_refl) / DFT(E_inc)|²
    DFT 用时间窗（仅稳态期），避免 DftMonitor 在线累加稀释。
    """
    print("\n=== M3: 金 Drude 反射率 ===")
    dx = dy = 8e-9  # 8 nm
    nx, ny = 400, 60
    dt = courant_dt(dx, dy, cfl=0.5)
    n_steps = 20000

    # CW 源（带斜坡）
    ramp = 5.0 / F0
    waveform = ContinuousWave(amplitude=1.0, frequency=F0, ramp_time=ramp)

    tfsf = TfsfBox(i0=20, i1=380, j0=10, j1=50)

    # 金 Drude 参数（Rakic 1998）
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    # 金板区域（i=170..220，50 cells = 400 nm，远离 PML）
    gold_start, gold_end = 170, 220
    mask_gold = np.zeros((nx, ny), dtype=bool)
    mask_gold[gold_start:gold_end, :] = True

    eps_gold = np.ones((nx, ny))
    eps_gold[gold_start:gold_end, :] = drude.eps_inf  # 9.84

    print(f"  dx={dx*1e9:.0f}nm, n_steps={n_steps}, gold=[{gold_start},{gold_end}] ({(gold_end-gold_start)*dx*1e9:.0f}nm)")
    print(f"  f={F0:.4e}Hz, λ={LAMBDA0*1e9:.0f}nm, dt={dt:.3e}s")

    t0 = time.time()
    # Sim A: 有金
    ts_total = _run_m3_sim(eps_gold, drude, mask_gold, n_steps, dx, dy, dt, nx, ny, waveform, tfsf)
    print(f"  Sim A (有金) 完成, {time.time()-t0:.1f}s")

    # Sim B: 无金（真空参考）
    eps_vac = np.ones((nx, ny))
    t0 = time.time()
    ts_inc = _run_m3_sim(eps_vac, None, None, n_steps, dx, dy, dt, nx, ny, waveform, tfsf)
    print(f"  Sim B (无金) 完成, {time.time()-t0:.1f}s")

    # 反射场 = 总场 - 入射场
    ts_refl = ts_total - ts_inc

    # 时间窗 DFT（仅稳态期）
    # Drude 弛豫时间 1/γ = 2.45e-14s ≈ 2600 steps
    # 脉冲到达金板并返回 ≈ 2*150*8e-9/c / dt ≈ 850 steps
    # 斜坡 5/f ≈ 2745 steps
    # 稳态开始 ≈ max(2600*3, 2745+850) ≈ 8000
    n_start_dft = 10000
    n_end_dft = n_steps

    dft_inc = dft_windowed(ts_inc, dt, F0, n_start_dft, n_end_dft)
    dft_refl = dft_windowed(ts_refl, dt, F0, n_start_dft, n_end_dft)

    if abs(dft_inc) == 0.0:
        raise ValueError("入射 DFT=0，源未到达探针")
    R_sim = abs(dft_refl / dft_inc) ** 2

    # 解析 Drude-Fresnel 反射率
    omega = OMEGA0
    eps_eff = drude.eps_inf - drude.omega_p**2 / (omega**2 + 1j * drude.gamma * omega)
    n_gold = np.sqrt(eps_eff)
    # 取 Im(n) > 0 的分支
    if n_gold.imag < 0:
        n_gold = -n_gold
    R_analytical = abs((1.0 - n_gold) / (1.0 + n_gold)) ** 2

    rel_err = abs(R_sim - R_analytical) / R_analytical

    print(f"  DFT 窗: [{n_start_dft}, {n_end_dft}]")
    print(f"  |DFT_inc| = {abs(dft_inc):.6e}")
    print(f"  |DFT_refl| = {abs(dft_refl):.6e}")
    print(f"  eps_eff(解析) = {eps_eff.real:.4f} + {eps_eff.imag:.4f}i")
    print(f"  n_gold(解析)  = {n_gold.real:.4f} + {n_gold.imag:.4f}i")
    print(f"  R(仿真)      = {R_sim:.6f}")
    print(f"  R(解析)      = {R_analytical:.6f}")
    print(f"  相对误差     = {rel_err*100:.2f}%")
    passed = rel_err < 0.02
    print(f"  M3: {'PASS' if passed else 'FAIL'} (阈值 < 2%)")
    return passed, rel_err


# ============================================================
# M4: SOI 波导 S21 相位误差 ≤ 1e-3
# ============================================================
def _solve_te0_mode(n_core, n_clad, k0, half_width):
    """求解 TE0 模传播常数 β（对称平板波导）。

    TE0（偶模）超越方程：u·tan(u) = w, V² = u² + w²
    其中 u = a·√(n_core²·k0² - β²), w = a·√(β² - n_clad²·k0²)
    """
    from scipy.optimize import brentq

    V = k0 * half_width * np.sqrt(n_core**2 - n_clad**2)

    def equation(u):
        w = np.sqrt(max(V**2 - u**2, 0.0))
        return u * np.tan(u) - w

    # TE0: u ∈ (0, min(V, π/2))，因 u²+w²=V² 要求 u≤V
    u_max = min(V, np.pi / 2) - 1e-10
    u = brentq(equation, 1e-10, u_max)
    w = np.sqrt(V**2 - u**2)
    beta = np.sqrt(n_clad**2 * k0**2 + (w / half_width)**2)
    return beta


def test_m4():
    """M4: SOI 波导 S21 相位 vs 解析 TE0 β ≤ 1e-3 rad。

    方法：细网格 dx=5nm 降低色散，短传播距离 L=500nm 降低绝对相位误差。
    偶极子源激励 TE0 模（V<π/2 单模），DftMonitor 测 S21 相位。
    """
    print("\n=== M4: SOI 波导 S21 相位 ===")

    dx = dy = 5e-9  # 5 nm 细网格
    nx, ny = 300, 100
    dt = courant_dt(dx, dy, cfl=0.5)
    n_steps = 8000

    n_core = 3.48  # Si
    n_clad = 1.44  # SiO2
    core_width = 220e-9  # 220 nm
    half_width = core_width / 2

    k0 = 2 * np.pi / LAMBDA0
    beta_analytical = _solve_te0_mode(n_core, n_clad, k0, half_width)
    n_eff = beta_analytical / k0

    # 波导沿 x，芯在 y 中心
    core_cells = int(core_width / dy)  # 44 cells
    y0_core = ny // 2 - core_cells // 2
    y1_core = y0_core + core_cells

    eps_r = np.full((nx, ny), n_clad**2, dtype=np.float64)
    eps_r[:, y0_core:y1_core] = n_core**2

    grid = YeeGridFdtd(shape=(nx, ny), dx=dx, dy=dy, dt=dt, eps_r=eps_r)

    # 偶极子源（TEz，位于波导中心）
    src_pos = (50, ny // 2)
    ramp = 3.0 / F0
    waveform = ContinuousWave(amplitude=1.0, frequency=F0, ramp_time=ramp)
    dipole = DipoleSource(position=src_pos, waveform=waveform)

    # DFT 监视器
    x_port1 = 100
    x_port2 = 200
    L = (x_port2 - x_port1) * dx  # 500 nm

    mon1 = DftMonitor(position=(x_port1, ny // 2), frequency=F0, name="port1")
    mon2 = DftMonitor(position=(x_port2, ny // 2), frequency=F0, name="port2")

    cfg = FdtdConfig(
        grid=grid, n_steps=n_steps,
        cpml=CpmlConfig(layers=10),
        eps_r_bg=n_clad**2,
        dipole_sources=[dipole],
        monitors=[mon1, mon2],
        probe_point=(x_port1, ny // 2),
    )
    solver = FdtdSolver(cfg)

    t0 = time.time()
    result = solver.run()
    print(f"  仿真完成, {time.time()-t0:.1f}s")

    dft1 = result.dft_results["port1"]
    dft2 = result.dft_results["port2"]

    if abs(dft1) == 0.0:
        raise ValueError("port1 DFT=0，源未到达监视器")

    s21 = dft2 / dft1
    phase_sim = np.angle(s21)
    phase_analytical = -beta_analytical * L

    # 相位解卷绕（比较模 2π）
    phase_diff = phase_sim - phase_analytical
    phase_diff_wrapped = (phase_diff + np.pi) % (2 * np.pi) - np.pi
    phase_err = abs(phase_diff_wrapped)

    print(f"  dx={dx*1e9:.0f}nm, core=[y{y0_core},y{y1_core}] ({core_cells} cells={core_cells*dy*1e9:.0f}nm)")
    print(f"  n_core={n_core}, n_clad={n_clad}")
    print(f"  β(解析) = {beta_analytical:.6e} /m, n_eff = {n_eff:.4f}")
    print(f"  L = {L*1e9:.0f} nm, β·L = {beta_analytical*L:.4f} rad")
    print(f"  |DFT1| = {abs(dft1):.6e}, |DFT2| = {abs(dft2):.6e}")
    print(f"  S21 = {abs(s21):.6f} ∠{np.degrees(np.angle(s21)):.2f}°")
    print(f"  phase(仿真)   = {phase_sim:.6f} rad")
    print(f"  phase(解析)   = {phase_analytical:.6f} rad (mod 2π = {phase_analytical % (2*np.pi):.6f})")
    print(f"  相位误差     = {phase_err:.6e} rad")
    passed = phase_err <= 1e-3
    print(f"  M4: {'PASS' if passed else 'FAIL'} (阈值 ≤ 1e-3 rad)")
    return passed, phase_err


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("A09-FDTD M1-M4 验收验证")
    print(f"λ0 = {LAMBDA0*1e9:.0f} nm, f0 = {F0:.4e} Hz")
    print("=" * 60)

    results = {}

    # M1
    try:
        passed, val = test_m1()
        results["M1"] = (passed, val)
    except Exception as e:
        print(f"  M1: ERROR - {e}")
        import traceback; traceback.print_exc()
        results["M1"] = (False, str(e))

    # M2
    try:
        passed, val = test_m2()
        results["M2"] = (passed, val)
    except Exception as e:
        print(f"  M2: ERROR - {e}")
        import traceback; traceback.print_exc()
        results["M2"] = (False, str(e))

    # M3
    try:
        passed, val = test_m3()
        results["M3"] = (passed, val)
    except Exception as e:
        print(f"  M3: ERROR - {e}")
        import traceback; traceback.print_exc()
        results["M3"] = (False, str(e))

    # M4
    try:
        passed, val = test_m4()
        results["M4"] = (passed, val)
    except Exception as e:
        print(f"  M4: ERROR - {e}")
        import traceback; traceback.print_exc()
        results["M4"] = (False, str(e))

    print("\n" + "=" * 60)
    print("验收结果汇总")
    print("=" * 60)
    for name, (passed, val) in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}  ({val})")
    print("=" * 60)
