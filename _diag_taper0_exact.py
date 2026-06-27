"""使用 EME 后端 EXACT 一致的 eps 构造诊断 taper_0 候选本征值。

复用 FIMMPROPBackend._make_strip_eps 构造 eps，确保与实际 EME run 相同。
打印所有 Arnoldi 候选 + 场局域化分数，定位为何 taper_0 返回 PML 模式而非真实导模。
"""
from __future__ import annotations

import numpy as np
import scipy.sparse.linalg as spla

from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml


def field_localization(ey: np.ndarray, w_n: int, h_n: int):
    """计算场在波导中心矩形（2×波导尺寸）的能量占比。"""
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


def diagnose(label: str, width: float, height: float):
    print(f"\n=== {label} (w={width*1e9:.0f}nm, h={height*1e9:.0f}nm) ===")
    cfg = EMEConfig(
        n_modes=1, wavelength=1.55e-6, dx=5e-8, dy=5e-8,
        window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
    )
    backend = FIMMPROPBackend(cfg)
    # 用 EME 后端的 eps 构造
    eps_r = backend._make_strip_eps(width, height, 3.476, 1.444)
    nx, ny = eps_r.shape
    w_n = max(1, int(round(width / cfg.dx)))
    h_n = max(1, int(round(height / cfg.dy)))
    print(f"  eps shape={eps_r.shape}, w_n={w_n}, h_n={h_n}, dx={cfg.dx*1e9:.2f}nm, dy={cfg.dy*1e9:.2f}nm")

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
    k_request = min(fde_cfg.num_modes + 8, n_total - 2)
    print(f"  n_clad={n_clad:.4f}, n_core={n_core:.4f}, target={n_eff_shift:.4f}, k_req={k_request}")

    eigvals, eigvecs = spla.eigs(a_mat, k=k_request, sigma=sigma, which="LM")

    cands = []
    for i in range(len(eigvals)):
        beta = np.sqrt(eigvals[i])
        n_eff = beta / solver.k0
        re = float(np.real(n_eff))
        im = float(np.imag(n_eff))
        if not (n_clad < re < n_core):
            continue
        ey = eigvecs[:, i].reshape(grid.spec.shape)
        loc = field_localization(ey, w_n, h_n)
        penalty = re - 10.0 * abs(im)
        cands.append((penalty, i, complex(n_eff), loc))
    cands.sort(key=lambda c: c[0], reverse=True)
    print(f"  候选导模：{len(cands)} 个")
    print(f"  {'rank':>4} {'idx':>4} {'Re(n_eff)':>14} {'Im(n_eff)':>14} {'penalty':>10} {'central_E':>10}")
    for rank, (pen, i, neff, loc) in enumerate(cands[:12]):
        print(f"  {rank:>4} {i:>4} {float(np.real(neff)):>14.6f} {float(np.imag(neff)):>14.6e} {pen:>10.4f} {loc:>10.4f}")

    # 现在调用实际 backend.solve_modes 看返回什么
    sid = backend.add_section(4.0e-6, eps_r, label=label)
    result = backend.solve_modes(sid)
    actual_neff = result["n_eff"][0]
    print(f"  >>> backend.solve_modes 实际返回: n_eff={float(np.real(actual_neff)):.6f}{float(np.imag(actual_neff)):+.6e}j")


if __name__ == "__main__":
    # taper 各段宽度（build_taper 中点宽度法，n_steps=5）
    # frac = (i + 0.5) / 5, w_i = 500nm + (800-500)*frac
    widths = [500e-9 + 300e-9 * (i + 0.5) / 5 for i in range(5)]
    for i, w in enumerate(widths):
        diagnose(f"taper_{i}", w, 0.22e-6)
