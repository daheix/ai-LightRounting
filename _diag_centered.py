"""验证 cell-centered eps 构造（核心居中）能否修复 PML 污染。

对比两种 eps 构造方式：
1. 整数像素（当前 _make_strip_eps）：核心可能偏离中心半网格
2. cell-centered（test_a04_fde.py 风格）：核心始终居中

测试所有 taper 段宽度，看 cell-centered 是否能可靠找到真实导模。
"""
from __future__ import annotations

import numpy as np
import scipy.sparse.linalg as spla

from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml


def make_eps_pixel(width, height, n_core, n_clad, nx, ny, dx, dy):
    """整数像素 eps 构造（当前 _make_strip_eps 方式）。"""
    eps = np.full((nx, ny), n_clad**2, dtype=np.float64)
    w_n = max(1, int(round(width / dx)))
    h_n = max(1, int(round(height / dy)))
    x0 = (nx - w_n) // 2
    y0 = (ny - h_n) // 2
    eps[x0:x0+w_n, y0:y0+h_n] = n_core**2
    return eps, w_n, h_n


def make_eps_centered(width, height, n_core, n_clad, nx, ny, dx, dy, lx, ly):
    """cell-centered eps 构造（核心居中）。"""
    x = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y = (np.arange(ny) + 0.5) * dy - ly / 2.0
    eps = np.full((nx, ny), n_clad**2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= width / 2.0) & (np.abs(y)[None, :] <= height / 2.0)
    eps[mask] = n_core**2
    w_n = int(mask.sum(axis=0).max())  # 实际核心宽度（cells）
    h_n = int(mask.sum(axis=1).max())
    return eps, w_n, h_n


def field_localization(ey, w_n, h_n):
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
    return float(np.sum(np.abs(ey[ix0:ix1, iy0:iy1]) ** 2)) / total


def solve(eps, w_n, h_n, window, label):
    nx, ny = eps.shape
    dx = window[0] / nx
    dy = window[1] / ny
    cfg = FdeSolverConfig(wavelength=1.55e-6, num_modes=1, polarization="te",
                          pml=ScPml(layers=8))
    solver = FdeSolver(cfg)
    grid = solver._build_grid(eps.astype(np.complex128), window)
    a_mat = solver._assemble_te_matrix(grid)
    n_clad = float(np.sqrt(eps.min()))
    n_core = float(np.sqrt(eps.max()))
    sigma = (solver.k0 * (n_clad + 0.5 * (n_core - n_clad))) ** 2
    k_req = min(9, nx * ny - 2)
    eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma, which="LM")
    real_modes = []
    for i in range(len(eigvals)):
        beta = np.sqrt(eigvals[i])
        n_eff = beta / solver.k0
        re, im = float(np.real(n_eff)), float(np.imag(n_eff))
        if not (n_clad < re < n_core):
            continue
        ey = eigvecs[:, i].reshape(grid.spec.shape)
        loc = field_localization(ey, w_n, h_n)
        if loc > 0.5:
            real_modes.append((re, im, loc))
    real_modes.sort(key=lambda m: m[0], reverse=True)
    if real_modes:
        re, im, loc = real_modes[0]
        print(f"  {label}: n_eff={re:.6f}{im:+.6e}j, central_E={loc:.4f} ✓ 真实导模")
    else:
        print(f"  {label}: 未找到真实导模 ✗ (PML 污染)")


if __name__ == "__main__":
    N_SI, N_SIO2 = 3.476, 1.444
    H = 0.22e-6
    lx, ly = 3.0e-6, 2.5e-6
    dx, dy = 5e-8, 5e-8
    nx, ny = 60, 50

    print("=== 整数像素 eps（当前 _make_strip_eps）===")
    for w_nm in [500, 530, 590, 650, 710, 770, 800]:
        w = w_nm * 1e-9
        eps, w_n, h_n = make_eps_pixel(w, H, N_SI, N_SIO2, nx, ny, dx, dy)
        solve(eps, w_n, h_n, (lx, ly), f"w={w_nm}nm(w_n={w_n})")

    print("\n=== cell-centered eps（核心居中）===")
    for w_nm in [500, 530, 590, 650, 710, 770, 800]:
        w = w_nm * 1e-9
        eps, w_n, h_n = make_eps_centered(w, H, N_SI, N_SIO2, nx, ny, dx, dy, lx, ly)
        solve(eps, w_n, h_n, (lx, ly), f"w={w_nm}nm(w_n={w_n})")
