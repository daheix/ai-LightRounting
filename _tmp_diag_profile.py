"""诊断：检查金内波传播，验证 Drude 有效介电常数。

全空间金（无界面），CW 源从左注入，测量金内波长与衰减率，
反推有效 n、k，与解析 Drude 对比。
"""
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DrudeParams, FdtdConfig, FdtdSolver,
    ContinuousWave, TfsfBox, YeeGridFdtd, courant_dt,
)

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
OMEGA0 = 2 * np.pi * F0
_EPS0 = 8.8541878128e-12


def diagnose_gold_propagation():
    """全空间金，CW 注入，测金内波长+衰减率。"""
    dx = dy = 8e-9
    nx, ny = 600, 30
    dt = courant_dt(dx, dy, cfl=0.49)
    v_step = C0 * dt / dx

    ramp = 5.0e-14
    wf = ContinuousWave(amplitude=1.0, frequency=F0, ramp_time=ramp)
    pml_layers = 12
    pml = CpmlConfig(layers=pml_layers, alpha=0.08)
    # TF 区全内部，金填充全域
    tfsf = TfsfBox(i0=20, i1=560, j0=pml_layers, j1=ny - pml_layers - 1)
    n_steps = 50000  # 长仿真确保稳态
    drude = DrudeParams(omega_p=1.37e16, gamma=4.08e13, eps_inf=9.84)

    eps = np.full((nx, ny), drude.eps_inf)
    mask = np.ones((nx, ny), dtype=bool)
    mask[:pml_layers, :] = False
    mask[-pml_layers:, :, ] = False
    mask[:, :pml_layers] = False
    mask[:, -pml_layers:] = False
    grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
    cfg = FdtdConfig(grid=grid, n_steps=n_steps, cpml=pml, eps_r_bg=drude.eps_inf,
                    tfsf=tfsf, tfsf_waveform=wf,
                    drude=drude, drude_mask=mask,
                    probe_point=(100, ny // 2))
    print(f"运行全金仿真 (n_steps={n_steps})...")
    import time
    t0 = time.time()
    res = FdtdSolver(cfg).run()
    print(f"  用时 {time.time()-t0:.1f}s")

    # 取 j=ny//2 行的 E_z 终态场
    jmid = ny // 2
    ez = res.e_z[:, jmid]

    # 解析 Drude 有效 n, k
    eps_eff = drude.permittivity(OMEGA0)
    n_eff = np.sqrt(eps_eff)
    print(f"\n解析: eps_eff={eps_eff:.4f}")
    print(f"解析: n_eff={n_eff:.4f}")
    print(f"解析: 衰减长度 1/(omega*Im(n)/c) = {1.0/(OMEGA0*np.imag(n_eff)/C0)*1e9:.2f} nm")
    print(f"解析: 金内波长 = {2*np.pi/(OMEGA0*np.real(n_eff)/C0)*1e9:.2f} nm")

    # 从仿真场提取波长和衰减
    # 取 i=50..200 范围（远离源和 PML）
    x = np.arange(50, 250) * dx
    ez_seg = ez[50:250]
    # 用 Hilbert 变换提取包络
    from scipy.signal import hilbert
    analytic = hilbert(ez_seg)
    envelope = np.abs(analytic)
    phase = np.unwrap(np.angle(analytic))

    # 衰减率（包络指数衰减）
    log_env = np.log(envelope + 1e-30)
    # 线性拟合 log(env) = -alpha*x + const
    coeffs = np.polyfit(x, log_env, 1)
    alpha_fit = -coeffs[0]
    decay_length = 1.0 / alpha_fit if alpha_fit > 0 else np.inf

    # 波数（相位线性增长）
    phase_coeffs = np.polyfit(x, phase, 1)
    k_fit = phase_coeffs[0]

    print(f"\n仿真: 衰减率={alpha_fit:.4e} /m")
    print(f"仿真: 衰减长度={decay_length*1e9:.2f} nm")
    print(f"仿真: 波数 k={k_fit:.4e} /m")
    print(f"仿真: 波长={2*np.pi/k_fit*1e9:.2f} nm")

    # 反推 n, k
    # E(x) = E0 * exp(-alpha*x) * exp(i*k*x)
    # = E0 * exp(i*(k+i*alpha)*x)
    # n_eff = (k + i*alpha) * c / omega
    n_real = k_fit * C0 / OMEGA0
    n_imag = alpha_fit * C0 / OMEGA0
    print(f"仿真: n_real={n_real:.4f} n_imag={n_imag:.4f}")
    print(f"解析: n_real={np.real(n_eff):.4f} n_imag={np.imag(n_eff):.4f}")
    eps_sim = (n_real + 1j*n_imag)**2
    print(f"仿真: eps_eff={eps_sim:.4f}")
    print(f"解析: eps_eff={eps_eff:.4f}")
    print(f"eps 误差={abs(eps_sim-eps_eff)/abs(eps_eff)*100:.2f}%")


if __name__ == "__main__":
    diagnose_gold_propagation()
