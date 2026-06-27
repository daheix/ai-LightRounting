"""诊断 FDE 基模选择 Bug：打印所有候选模式的 n_eff + 场局域化度。"""
import sys
sys.path.insert(0, "/workspace/src")
import numpy as np
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml

_N_SI = 3.476
_N_SIO2 = 1.444
_WL = 1.55e-6
_W = 0.5e-6
_H = 0.22e-6

def build_eps(nx=80, ny=80, window=(3.0e-6, 3.0e-6)):
    lx, ly = window
    dx, dy = lx/nx, ly/ny
    x = (np.arange(nx)+0.5)*dx - lx/2.0
    y = (np.arange(ny)+0.5)*dy - ly/2.0
    eps = np.full((nx, ny), _N_SIO2**2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= _W/2.0) & (np.abs(y)[None, :] <= _H/2.0)
    eps[mask] = _N_SI**2
    return eps, window

eps, win = build_eps()
cfg = FdeSolverConfig(wavelength=_WL, num_modes=6, pml=ScPml(layers=10))
solver = FdeSolver(cfg)

grid = solver._build_grid(eps.astype(np.complex128), win)
a_mat = solver._assemble_te_matrix(grid)
n_clad = float(np.sqrt(eps.min()))
n_core = float(np.sqrt(eps.max()))
n_eff_shift = n_clad + cfg.shift_frac * (n_core - n_clad)
pml_layers = 10
n_eff_max_guided = n_core - 0.5
n_total = grid.spec.num_cells
k_request = min(cfg.num_modes + 12, n_total - 2)
sigma_main = (solver.k0 * n_eff_shift) ** 2

print(f"n_clad={n_clad:.4f} n_core={n_core:.4f}")
print(f"shift_frac={cfg.shift_frac} target_neff={n_eff_shift:.4f}")
print(f"k_request={k_request} n_eff_max_guided={n_eff_max_guided:.4f}")
print(f"窗口={win} 网格={eps.shape} dx={grid.spec.dx*1e9:.2f}nm")

import scipy.sparse.linalg as spla
strategies = [
    ("C", sigma_main, "LR"),
    ("A", sigma_main, "LM"),
    ("D", (solver.k0 * 2.8) ** 2, "LM"),
]
for name, sigma, which in strategies:
    print(f"\n=== 策略 {name} sigma={sigma:.4e} which={which} ===")
    try:
        eigvals, eigvecs = spla.eigs(a_mat, k=k_request, sigma=sigma, which=which)
    except Exception as e:
        print(f"  失败: {e}")
        continue
    cands = solver._extract_guided_candidates(eigvals, eigvecs, grid, n_clad, n_eff_max_guided, pml_layers)
    print(f"  候选数={len(cands)}")
    cands.sort(key=lambda c: float(np.real(c[0])) - 10.0*abs(float(np.imag(c[0]))), reverse=True)
    for i, (n_eff, beta, ey, loc) in enumerate(cands[:8]):
        print(f"  [{i}] n_eff={float(np.real(n_eff)):.4f}{float(np.imag(n_eff)):+.2e}  loc={loc:.4f}")

modes = solver.solve(eps, win)
print(f"\n=== 最终 modes (前 {len(modes)}) ===")
for i, m in enumerate(modes):
    print(f"  [{i}] n_eff={float(np.real(m.n_eff)):.4f}{float(np.imag(m.n_eff)):+.2e}  te={m.te_fraction:.4f}")
