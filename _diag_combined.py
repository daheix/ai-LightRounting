"""测试组合策略：策略C优先 + 体模过滤 + 策略A/D回退。

最终求解器策略：
1. 策略 C (shift-invert sigma, which="LR") 找 k 个候选
2. 过滤：n_clad < Re(n_eff) < n_core - 0.5（排除体模）+ central_E > 0.5（排除 PML）
3. 如果策略 C 无真实导模，回退策略 A (which="LM")
4. 如果仍无，回退策略 D (sigma=2.8, which="LM")
5. 全失败则 raise（无 fall-back）
"""
from __future__ import annotations

import numpy as np
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


def solve_robust(eps, window, w_n, h_n, num_modes=1):
    """鲁棒求解策略：策略C + 体模过滤 + 策略A/D回退。"""
    nx, ny = eps.shape
    cfg = FdeSolverConfig(wavelength=1.55e-6, num_modes=num_modes, polarization="te",
                          pml=ScPml(layers=8))
    solver = FdeSolver(cfg)
    grid = solver._build_grid(eps.astype(np.complex128), window)
    a_mat = solver._assemble_te_matrix(grid)
    n_clad = float(np.sqrt(eps.min()))
    n_core = float(np.sqrt(eps.max()))
    # 体模上界：n_core - 0.5（排除接近 n_core 的体模）
    n_eff_max_guided = n_core - 0.5
    k_req = min(num_modes + 12, nx * ny - 2)
    sigma_main = (solver.k0 * (n_clad + 0.5 * (n_core - n_clad))) ** 2

    def extract_real_modes(eigvals, eigvecs):
        real_modes = []
        for i in range(len(eigvals)):
            beta = np.sqrt(eigvals[i])
            n_eff = beta / solver.k0
            re, im = float(np.real(n_eff)), float(np.imag(n_eff))
            # 过滤：导模范围 + 排除体模（n_eff < n_core - 0.5）
            if not (n_clad < re < n_eff_max_guided):
                continue
            ey = eigvecs[:, i].reshape(grid.spec.shape)
            loc = field_localization(ey, w_n, h_n)
            if loc > 0.5:  # 排除 PML 模式
                real_modes.append((re, im, loc, i))
        real_modes.sort(key=lambda m: m[0], reverse=True)  # 基模（高 n_eff）在前
        return real_modes

    # 策略 C: shift-invert sigma, which="LR"
    try:
        eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma_main, which="LR")
        modes_c = extract_real_modes(eigvals, eigvecs)
        if modes_c:
            return modes_c[:num_modes], "C"
    except Exception:
        pass

    # 策略 A: shift-invert sigma, which="LM"（当前默认）
    try:
        eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma_main, which="LM")
        modes_a = extract_real_modes(eigvals, eigvecs)
        if modes_a:
            return modes_a[:num_modes], "A"
    except Exception:
        pass

    # 策略 D: shift-invert sigma=2.8, which="LM"
    try:
        sigma_high = (solver.k0 * 2.8) ** 2
        eigvals, eigvecs = spla.eigs(a_mat, k=k_req, sigma=sigma_high, which="LM")
        modes_d = extract_real_modes(eigvals, eigvecs)
        if modes_d:
            return modes_d[:num_modes], "D"
    except Exception:
        pass

    return [], "FAIL"


if __name__ == "__main__":
    N_SI, N_SIO2 = 3.476, 1.444
    H = 0.22e-6
    lx, ly = 3.0e-6, 2.5e-6
    dx, dy = 5e-8, 5e-8
    nx, ny = 60, 50

    print("=== 组合策略（C→A→D 回退 + 体模过滤 n_eff<n_core-0.5 + 场局域化>0.5）===")
    for w_nm in [500, 530, 590, 650, 710, 770, 800]:
        w = w_nm * 1e-9
        x = (np.arange(nx) + 0.5) * dx - lx / 2.0
        y = (np.arange(ny) + 0.5) * dy - ly / 2.0
        eps = np.full((nx, ny), N_SIO2**2, dtype=np.float64)
        mask = (np.abs(x)[:, None] <= w / 2.0) & (np.abs(y)[None, :] <= H / 2.0)
        eps[mask] = N_SI**2
        w_n = int(mask.sum(axis=0).max())
        h_n = int(mask.sum(axis=1).max())
        modes, strat = solve_robust(eps, (lx, ly), w_n, h_n, num_modes=1)
        if modes:
            re, im, loc, idx = modes[0]
            print(f"  w={w_nm}nm: n_eff={re:.6f}{im:+.6e}j, E={loc:.4f}, 策略={strat} ✓")
        else:
            print(f"  w={w_nm}nm: ✗ 全策略失败")

    # 也测试 MMI 宽截面（2.0um 宽）
    print("\n=== MMI 宽截面 w=2.0um ===")
    w = 2.0e-6
    x = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y = (np.arange(ny) + 0.5) * dy - ly / 2.0
    eps = np.full((nx, ny), N_SIO2**2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= w / 2.0) & (np.abs(y)[None, :] <= H / 2.0)
    eps[mask] = N_SI**2
    w_n = int(mask.sum(axis=0).max())
    h_n = int(mask.sum(axis=1).max())
    modes, strat = solve_robust(eps, (lx, ly), w_n, h_n, num_modes=1)
    if modes:
        re, im, loc, idx = modes[0]
        print(f"  w=2000nm: n_eff={re:.6f}{im:+.6e}j, E={loc:.4f}, 策略={strat} ✓")
    else:
        print(f"  w=2000nm: ✗ 全策略失败")

    # 测试 w=1.5um（crossing 宽截面）
    print("\n=== Crossing 宽截面 w=1.5um ===")
    w = 1.5e-6
    eps = np.full((nx, ny), N_SIO2**2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= w / 2.0) & (np.abs(y)[None, :] <= H / 2.0)
    eps[mask] = N_SI**2
    w_n = int(mask.sum(axis=0).max())
    h_n = int(mask.sum(axis=1).max())
    modes, strat = solve_robust(eps, (lx, ly), w_n, h_n, num_modes=1)
    if modes:
        re, im, loc, idx = modes[0]
        print(f"  w=1500nm: n_eff={re:.6f}{im:+.6e}j, E={loc:.4f}, 策略={strat} ✓")
    else:
        print(f"  w=1500nm: ✗ 全策略失败")
