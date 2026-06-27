"""测试增大 k_request 是否能让 Arnoldi 找到 taper_0 (w=530nm) 的真实导模。

当前 k_request = num_modes + 8 = 9，对 w=530nm 找不到真实导模。
测试 k_request = 20, 30, 40 看真实导模是否出现。
同时测试更细网格（dx=dy=25nm）是否能可靠找到真实导模。
"""
from __future__ import annotations

import numpy as np
import scipy.sparse.linalg as spla

from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml


def field_localization(ey: np.ndarray, w_n: int, h_n: int):
    nx, ny = ey.shape
    cx_w = max(1, 2 * w_n)
    cy_h = max(1, 2 * h_n)
    ix0 = (nx - cx_w) // 2
    ix1 = ix0 + cx_w
    iy0 = (ny - cy_h) // 2
    iy1 = iy0 + cy_h
    total = float(np.sum(np.abs(ey) ** 2))
    if total <= 0:
        return 0.0
    central = float(np.sum(np.abs(ey[ix0:ix1, iy0:iy1]) ** 2))
    return central / total


def diagnose(label: str, width: float, height: float, dx: float, dy: float,
             window: tuple[float, float], pml_layers: int, k_extra: int):
    print(f"\n=== {label} (w={width*1e9:.0f}nm, dx={dx*1e9:.1f}nm, k_extra={k_extra}) ===")
    cfg = EMEConfig(
        n_modes=1, wavelength=1.55e-6, dx=dx, dy=dy,
        window_size=window, pml_layers=pml_layers, polarization="te",
    )
    backend = FIMMPROPBackend(cfg)
    eps_r = backend._make_strip_eps(width, height, 3.476, 1.444)
    nx, ny = eps_r.shape
    w_n = max(1, int(round(width / cfg.dx)))
    h_n = max(1, int(round(height / cfg.dy)))
    print(f"  eps shape={eps_r.shape}, w_n={w_n}, h_n={h_n}")

    fde_cfg = FdeSolverConfig(
        wavelength=cfg.wavelength, num_modes=cfg.n_modes,
        polarization=cfg.polarization, pml=ScPml(layers=cfg.pml_layers),
    )
    solver = FdeSolver(fde_cfg)
    eps_real = eps_r.real.copy()
    grid = solver._build_grid(eps_real, cfg.window_size)
    a_mat = solver._assemble_te_matrix(grid)
    n_clad = float(np.sqrt(eps_real.min()))
    n_core = float(np.sqrt(eps_real.max()))
    n_eff_shift = n_clad + fde_cfg.shift_frac * (n_core - n_clad)
    sigma = (solver.k0 * n_eff_shift) ** 2
    n_total = grid.spec.num_cells
    k_request = min(fde_cfg.num_modes + k_extra, n_total - 2)
    print(f"  k_request={k_request}")

    eigvals, eigvecs = spla.eigs(a_mat, k=k_request, sigma=sigma, which="LM")

    # 找真实导模（central_E > 0.5）
    real_modes = []
    pml_modes = 0
    for i in range(len(eigvals)):
        beta = np.sqrt(eigvals[i])
        n_eff = beta / solver.k0
        re = float(np.real(n_eff))
        im = float(np.imag(n_eff))
        if not (n_clad < re < n_core):
            continue
        ey = eigvecs[:, i].reshape(grid.spec.shape)
        loc = field_localization(ey, w_n, h_n)
        if loc > 0.5:
            real_modes.append((re, im, loc, i))
        else:
            pml_modes += 1
    real_modes.sort(key=lambda m: m[0], reverse=True)
    print(f"  真实导模（central_E>0.5）：{len(real_modes)} 个，PML 模式：{pml_modes} 个")
    for re, im, loc, i in real_modes[:5]:
        print(f"    n_eff={re:.6f}{im:+.6e}j, central_E={loc:.4f}, idx={i}")


if __name__ == "__main__":
    # 测试不同 k_extra 对 taper_0 (w=530nm) 的影响
    for k_extra in [8, 16, 24, 32, 48]:
        diagnose(f"taper_0 k_extra={k_extra}", 0.53e-6, 0.22e-6,
                 dx=5e-8, dy=5e-8, window=(3.0e-6, 2.5e-6), pml_layers=8, k_extra=k_extra)

    # 测试更细网格（dx=dy=25nm）
    print("\n\n>>> 测试更细网格 dx=dy=25nm <<<")
    for w in [0.50e-6, 0.53e-6, 0.59e-6, 0.65e-6, 0.71e-6, 0.77e-6, 0.80e-6]:
        diagnose(f"w={w*1e9:.0f}nm @ 25nm", w, 0.22e-6,
                 dx=2.5e-8, dy=2.5e-8, window=(3.0e-6, 2.5e-6), pml_layers=10, k_extra=8)

    # 测试中等网格（dx=dy=33nm）
    print("\n\n>>> 测试中等网格 dx=dy=33nm <<<")
    for w in [0.50e-6, 0.53e-6, 0.65e-6, 0.77e-6]:
        diagnose(f"w={w*1e9:.0f}nm @ 33nm", w, 0.22e-6,
                 dx=3.3e-8, dy=3.3e-8, window=(3.0e-6, 2.5e-6), pml_layers=10, k_extra=8)
