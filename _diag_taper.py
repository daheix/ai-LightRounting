"""临时诊断脚本：锥形各段 n_eff + SOI 基模网格收敛。运行后删除。"""
import numpy as np
from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml

# 诊断 1: 锥形各段 n_eff（新窗口 3.0x2.5um, pml=8）
cfg = EMEConfig(n_modes=1, wavelength=1.55e-6, dx=5e-8, dy=5e-8,
                window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te")
backend = FIMMPROPBackend(cfg)
backend.build_taper(length=20e-6, w_in=0.5e-6, w_out=0.8e-6,
                    height=0.22e-6, n_core=3.476, n_clad=1.444, n_steps=5)
print("=== 锥形各段 n_eff (窗口 3.0x2.5um, pml=8) ===")
for sec in backend._sections:
    r = backend.solve_modes(sec.section_id)
    neff = r["n_eff"][0]
    im = float(np.imag(neff))
    te = r["te_fraction"][0]
    print(f"{sec.label}: n_eff={neff:.8f}, Im={im:.6e}, te_frac={te:.4f}")

# 诊断 2: SOI 基模 n_eff 网格收敛性
print("\n=== SOI 500x220nm 基模 n_eff 网格收敛 (窗口 3.0x3.0um, pml=10) ===")

def build_soi(nx, window=(3.0e-6, 3.0e-6)):
    lx, ly = window
    dx, dy = lx / nx, ly / nx
    x = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y = (np.arange(nx) + 0.5) * dy - ly / 2.0
    eps = np.full((nx, nx), 1.444 ** 2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= 0.25e-6) & (np.abs(y)[None, :] <= 0.11e-6)
    eps[mask] = 3.476 ** 2
    return eps, window

for nx in [80, 120, 160]:
    eps, win = build_soi(nx)
    cfg2 = FdeSolverConfig(wavelength=1.55e-6, num_modes=2, pml=ScPml(layers=10))
    modes = FdeSolver(cfg2).solve(eps, win)
    neff0 = modes[0].n_eff
    print(f"nx={nx} (dx={3e-6/nx*1e9:.1f}nm): n_eff={neff0:.8f}, te_frac={modes[0].te_fraction:.4f}")
