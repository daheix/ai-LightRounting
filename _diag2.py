"""临时诊断脚本2：测试不同 shift_frac/k_request 对 taper_0 真实导模求解的影响。"""
import numpy as np
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml


def make_strip_eps(width, height, n_core, n_clad, window=(3.0e-6, 2.5e-6), dx=5e-8, dy=5e-8):
    lx, ly = window
    nx = max(5, int(round(lx / dx)))
    ny = max(5, int(round(ly / dy)))
    eps = np.full((nx, ny), n_clad ** 2, dtype=np.float64)
    w_n = max(1, int(round(width / dx)))
    h_n = max(1, int(round(height / dy)))
    x0 = (nx - w_n) // 2
    y0 = (ny - h_n) // 2
    eps[x0:x0 + w_n, y0:y0 + h_n] = n_core ** 2
    return eps, (lx / nx, ly / ny)


# taper_0: w=530nm
eps, (dx, dy) = make_strip_eps(530e-9, 220e-9, 3.476, 1.444)
window = (3.0e-6, 2.5e-6)

print("=== taper_0 (w=530nm) 不同 shift_frac / k_request ===")
for shift_frac in [0.5, 0.44, 0.4]:
    for k_extra in [8, 16, 24]:
        # 临时覆盖 k_request 逻辑：用 num_modes 控制 k = num_modes + k_extra
        # 实际 k_request = num_modes + 8（固定），这里通过 num_modes 间接增大
        num_modes_req = max(1, k_extra - 8)  # 让 k_request = num_modes_req + 8 = k_extra
        cfg = FdeSolverConfig(
            wavelength=1.55e-6, num_modes=num_modes_req,
            pml=ScPml(layers=8), shift_frac=shift_frac,
        )
        solver = FdeSolver(cfg)
        modes = solver.solve(eps, window)
        neffs = [(float(np.real(m.n_eff)), float(np.imag(m.n_eff))) for m in modes]
        neffs_str = ", ".join(f"{r:.4f}{i:+.4f}j" for r, i in neffs)
        print(f"shift_frac={shift_frac} k≈{k_extra}: n_eff=[{neffs_str}]")

# 也测试 pml 层数影响
print("\n=== taper_0 (w=530nm) 不同 pml_layers (shift_frac=0.44) ===")
for pml_l in [4, 6, 8, 12]:
    cfg = FdeSolverConfig(
        wavelength=1.55e-6, num_modes=1,
        pml=ScPml(layers=pml_l), shift_frac=0.44,
    )
    solver = FdeSolver(cfg)
    try:
        modes = solver.solve(eps, window)
        neff = modes[0].n_eff
        print(f"pml={pml_l}: n_eff={neff:.8f}, Im={float(np.imag(neff)):.6e}")
    except Exception as e:
        print(f"pml={pml_l}: ERROR {e}")
