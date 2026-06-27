"""测试不同 Arnoldi 求解策略，找到能可靠定位真实导模的方法。

策略对比：
A. shift-invert sigma=2.46, which="LM"（当前）：找最接近 sigma 的 k 个本征值
B. which="LR" 无 sigma：找最大实部本征值（体模→导模→PML 复数）
C. shift-invert sigma=2.46, which="LR"：找接近 sigma 且实部大的
D. shift-invert sigma=2.8（高于 PML 簇）, which="LM"：从上方接近真实导模
E. shift-invert sigma=2.0（低于 PML 簇）, which="LM"：从下方接近
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml


def make_eps_centered(width, height, n_core, n_clad, nx, ny, dx, dy, lx, ly):
    x = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y = (np.arange(ny) + 0.5) * dy - ly / 2.0
    eps = np.full((nx, ny), n_clad**2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= width / 2.0) & (np.abs(y)[None, :] <= height / 2.0)
    eps[mask] = n_core**2
    return eps


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


def try_strategy(eps, window, w_n, h_n, label, strategy):
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
    k_req = min(20, nx * ny - 2)

    try:
        if strategy == "A":  # shift-invert LM
            sigma = (solver.k0 * 2.46) ** 2
            eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma, which="LM")
        elif strategy == "B":  # LR no sigma
            eigvals, eigvecs = spla.eigs(a_mat, k=k_req, which="LR")
        elif strategy == "C":  # shift-invert LR
            sigma = (solver.k0 * 2.46) ** 2
            eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma, which="LR")
        elif strategy == "D":  # sigma=2.8 LM
            sigma = (solver.k0 * 2.8) ** 2
            eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma, which="LM")
        elif strategy == "E":  # sigma=2.0 LM
            sigma = (solver.k0 * 2.0) ** 2
            eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma, which="LM")
    except Exception as e:
        print(f"  {label} 策略{strategy}: 失败 {type(e).__name__}")
        return

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
        print(f"  {label} 策略{strategy}: n_eff={re:.6f}{im:+.6e}j, E={loc:.4f} ✓")
    else:
        print(f"  {label} 策略{strategy}: ✗ 未找到真实导模")


if __name__ == "__main__":
    N_SI, N_SIO2 = 3.476, 1.444
    H = 0.22e-6
    lx, ly = 3.0e-6, 2.5e-6
    dx, dy = 5e-8, 5e-8
    nx, ny = 60, 50

    widths = [500, 530, 590, 650, 710, 770, 800]
    for w_nm in widths:
        w = w_nm * 1e-9
        x = (np.arange(nx) + 0.5) * dx - lx / 2.0
        y = (np.arange(ny) + 0.5) * dy - ly / 2.0
        eps = np.full((nx, ny), N_SIO2**2, dtype=np.float64)
        mask = (np.abs(x)[:, None] <= w / 2.0) & (np.abs(y)[None, :] <= H / 2.0)
        eps[mask] = N_SI**2
        w_n = int(mask.sum(axis=0).max())
        h_n = int(mask.sum(axis=1).max())
        print(f"\n--- w={w_nm}nm (w_n={w_n}, h_n={h_n}) ---")
        for strat in ["A", "B", "C", "D", "E"]:
            try_strategy(eps, (lx, ly), w_n, h_n, f"w={w_nm}", strat)
