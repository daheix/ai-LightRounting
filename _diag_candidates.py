"""诊断 FDE 求解器返回的所有候选本征值，分析 PML/盒模污染情况。

打印所有 Arnoldi 候选本征值 + 场局域化分数（中心区域能量占比），
用于设计场局域化过滤器排除 PML/盒模污染。
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml


def make_strip_eps(width: float, height: float, n_core: float, n_clad: float,
                    nx: int = 80, ny: int = 80, window: tuple[float, float] = (3.0e-6, 3.0e-6)):
    lx, ly = window
    dx, dy = lx / nx, ly / ny
    x = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y = (np.arange(ny) + 0.5) * dy - ly / 2.0
    eps = np.full((nx, ny), n_clad**2, dtype=np.float64)
    mask = (np.abs(x)[:, None] <= width / 2.0) & (np.abs(y)[None, :] <= height / 2.0)
    eps[mask] = n_core**2
    return eps, window, (dx, dy)


def field_localization(ey: np.ndarray, width: float, height: float, dx: float, dy: float):
    """计算场在波导中心矩形区域的能量占比。

    真实导模：场集中于波导中心，>50% 能量在中心 2×(width,height) 矩形内。
    PML/盒模污染：场弥散到 PML 边界，<30% 能量在中心矩形内。
    """
    nx, ny = ey.shape
    # 中心矩形：2× 波导尺寸（容许模式场外溢）
    cx_w = max(1, int(2 * width / dx))
    cy_h = max(1, int(2 * height / dy))
    ix0 = (nx - cx_w) // 2
    ix1 = ix0 + cx_w
    iy0 = (ny - cy_h) // 2
    iy1 = iy0 + cy_h
    total = float(np.sum(np.abs(ey) ** 2))
    if total <= 0:
        return 0.0
    central = float(np.sum(np.abs(ey[ix0:ix1, iy0:iy1]) ** 2))
    return central / total


def diagnose(label: str, width: float, height: float, n_core: float, n_clad: float,
             wavelength: float = 1.55e-6, nx: int = 80, ny: int = 80,
             window: tuple[float, float] = (3.0e-6, 3.0e-6),
             pml_layers: int = 10, shift_frac: float = 0.5, k_extra: int = 8):
    print(f"\n=== {label} (w={width*1e9:.0f}nm, h={height*1e9:.0f}nm, nx={nx}, pml={pml_layers}, shift_frac={shift_frac}) ===")
    eps, win, (dx, dy) = make_strip_eps(width, height, n_core, n_clad, nx, ny, window)
    cfg = FdeSolverConfig(
        wavelength=wavelength, num_modes=1, polarization="te",
        pml=ScPml(layers=pml_layers), shift_frac=shift_frac,
    )
    solver = FdeSolver(cfg)
    grid = solver._build_grid(eps.astype(np.complex128), win)
    a_mat = solver._assemble_te_matrix(grid)
    n_clad_v = float(np.sqrt(np.real(eps).min()))
    n_core_v = float(np.sqrt(np.real(eps).max()))
    n_eff_shift = n_clad_v + cfg.shift_frac * (n_core_v - n_clad_v)
    sigma = (solver.k0 * n_eff_shift) ** 2
    n_total = grid.spec.num_cells
    k_request = min(cfg.num_modes + k_extra, n_total - 2)
    print(f"  n_clad={n_clad_v:.4f}, n_core={n_core_v:.4f}, target_n_eff={n_eff_shift:.4f}, k_request={k_request}")
    try:
        eigvals, eigvecs = spla.eigs(a_mat, k=k_request, sigma=sigma, which="LM")
    except spla.ArpackNoConvergence as e:
        print(f"  ARNOLDI 未收敛: {e}")
        return
    # 排序：按 penalty_score 降序
    cands = []
    for i in range(len(eigvals)):
        beta = np.sqrt(eigvals[i])
        n_eff = beta / solver.k0
        re = float(np.real(n_eff))
        im = float(np.imag(n_eff))
        if not (n_clad_v < re < n_core_v):
            continue
        # 场局域化分数
        ey = eigvecs[:, i].reshape(grid.spec.shape)
        loc = field_localization(ey, width, height, dx, dy)
        penalty = re - 10.0 * abs(im)
        cands.append((penalty, i, complex(n_eff), loc))
    cands.sort(key=lambda c: c[0], reverse=True)
    print(f"  候选导模（n_clad<Re<{n_core_v:.3f}）：{len(cands)} 个")
    print(f"  {'rank':>4} {'idx':>4} {'Re(n_eff)':>14} {'Im(n_eff)':>14} {'penalty':>10} {'central_E':>10}")
    for rank, (pen, i, neff, loc) in enumerate(cands[:12]):
        print(f"  {rank:>4} {i:>4} {float(np.real(neff)):>14.6f} {float(np.imag(neff)):>14.6e} {pen:>10.4f} {loc:>10.4f}")


if __name__ == "__main__":
    # SOI 参数
    N_SI = 3.476
    N_SIO2 = 1.444
    WL = 1.55e-6
    H = 0.22e-6  # 220nm

    # 1) SOI 500x220nm 基模测试（test_soi_fundamental_mode 配置）
    diagnose("SOI 500x220nm @ nx=80,3.0um,pml=10", 0.5e-6, H, N_SI, N_SIO2,
             nx=80, ny=80, window=(3.0e-6, 3.0e-6), pml_layers=10, shift_frac=0.5)
    diagnose("SOI 500x220nm @ nx=120,3.0um,pml=10", 0.5e-6, H, N_SI, N_SIO2,
             nx=120, ny=120, window=(3.0e-6, 3.0e-6), pml_layers=10, shift_frac=0.5)
    diagnose("SOI 500x220nm @ nx=160,3.0um,pml=10", 0.5e-6, H, N_SI, N_SIO2,
             nx=160, ny=160, window=(3.0e-6, 3.0e-6), pml_layers=10, shift_frac=0.5)

    # 2) taper_0 (w=530nm) 在 EME 测试窗口配置下
    diagnose("taper_0 w=530nm @ 3.0x2.5um,pml=8", 0.53e-6, H, N_SI, N_SIO2,
             nx=60, ny=50, window=(3.0e-6, 2.5e-6), pml_layers=8, shift_frac=0.5)
    # 更细网格
    diagnose("taper_0 w=530nm @ 3.0x2.5um,pml=8, finer", 0.53e-6, H, N_SI, N_SIO2,
             nx=120, ny=100, window=(3.0e-6, 2.5e-6), pml_layers=8, shift_frac=0.5)

    # 3) 测试 shift_frac 较小是否更好定位基模
    diagnose("SOI 500x220nm @ nx=80,3.0um,pml=10, shift=0.3", 0.5e-6, H, N_SI, N_SIO2,
             nx=80, ny=80, window=(3.0e-6, 3.0e-6), pml_layers=10, shift_frac=0.3)
    diagnose("SOI 500x220nm @ nx=80,3.0um,pml=10, shift=0.4", 0.5e-6, H, N_SI, N_SIO2,
             nx=80, ny=80, window=(3.0e-6, 3.0e-6), pml_layers=10, shift_frac=0.4)
