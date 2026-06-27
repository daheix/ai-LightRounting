"""诊断 80×80 网格全本征值谱 + 2.6932 vs 2.3401 场分布对比。"""
import sys
sys.path.insert(0, "/workspace/src")
import time
import numpy as np
import scipy.sparse.linalg as spla
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml

_N_SI = 3.476
_N_SIO2 = 1.444
_WL = 1.55e-6
_W = 0.5e-6
_H = 0.22e-6


def build_soi_eps(nx, ny, window, width=_W, height=_H):
    lx, ly = window
    dx, dy = lx / nx, ly / ny
    x = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y = (np.arange(ny) + 0.5) * dy - ly / 2.0
    eps = np.full((nx, ny), _N_SIO2**2, dtype=np.float64)
    core = (np.abs(x)[:, None] <= width / 2.0) & (np.abs(y)[None, :] <= height / 2.0)
    eps[core] = _N_SI**2
    return eps, window


print("=" * 70)
print("诊断 H: 80×80 网格全本征值谱（找 2.344）")
print("=" * 70)
eps_r, window = build_soi_eps(80, 80, (3.0e-6, 3.0e-6))
cfg = FdeSolverConfig(wavelength=_WL, num_modes=4, pml=ScPml(layers=10))
solver = FdeSolver(cfg)
eps_c = eps_r.astype(np.complex128, copy=True)
grid = solver._build_grid(eps_c, window)
a_mat = solver._assemble_te_matrix(grid)
n_clad = float(np.sqrt(np.real(eps_c).min()))
n_core = float(np.sqrt(np.real(eps_c).max()))
k0 = solver.k0
print(f"n_clad={n_clad:.4f}, n_core={n_core:.4f}, k0={k0:.4e}")

# 用不同 sigma 扫描，找 2.344
for target_neff in [2.0, 2.2, 2.344, 2.4, 2.6, 2.8]:
    sigma = (k0 * target_neff) ** 2
    t0 = time.time()
    try:
        eigvals, eigvecs = spla.eigs(a_mat, k=20, sigma=sigma, which="LM")
        t1 = time.time()
        neffs = sorted([float(np.real(np.sqrt(v))) for v in eigvals if np.real(v) > 0], reverse=True)
        # 过滤导模范围
        guided = [n for n in neffs if n_clad < n < n_core]
        print(f"  sigma(neff={target_neff}): {t1-t0:.1f}s, 导模n_eff={[f'{n:.4f}' for n in guided[:8]]}", flush=True)
    except Exception as e:
        t1 = time.time()
        print(f"  sigma(neff={target_neff}): {t1-t0:.1f}s 失败 {type(e).__name__}", flush=True)

print("\n" + "=" * 70)
print("诊断 I: 60×50 网格 2.6932 vs 2.3401 场分布对比")
print("=" * 70)
from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend
backend = FIMMPROPBackend(EMEConfig(
    n_modes=2, wavelength=_WL, dx=5e-8, dy=5e-8,
    window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
))
eps_r2 = backend._make_strip_eps(_W, _H, _N_SI, _N_SIO2)
sid = backend.add_section(1.0e-6, eps_r2, label="test")
r = backend.solve_modes(sid)
print(f"60×50 网格 n_modes=2: n_eff={[float(np.real(n)) for n in r['n_eff']]}")
for i, mode in enumerate(r["modes"]):
    ey = mode.ey
    nx, ny = ey.shape
    energy_x = np.sum(np.abs(ey)**2, axis=1)
    energy_y = np.sum(np.abs(ey)**2, axis=0)
    total = np.sum(energy_x)
    lx, ly = 3.0e-6, 2.5e-6
    dx, dy = lx / nx, ly / ny
    x_c = (np.arange(nx) + 0.5) * dx - lx / 2.0
    y_c = (np.arange(ny) + 0.5) * dy - ly / 2.0
    core_x = np.sum(energy_x[np.abs(x_c) <= _W / 2.0]) / total
    core_y = np.sum(energy_y[np.abs(y_c) <= _H / 2.0]) / total
    # y 方向节点数（零点数）
    ey_mid = ey[:, ny // 2]  # 取 x=0 的 y 方向剖面
    # 找符号变化次数（节点数）
    signs = np.sign(ey_mid.real)
    sign_changes = np.sum(np.diff(signs) != 0)
    print(f"  mode {i} (n_eff={float(np.real(mode.n_eff)):.4f}): "
          f"core_x={core_x:.4f}, core_y={core_y:.4f}, "
          f"y节点数={sign_changes}, te_frac={mode.te_fraction:.4f}")
print("\n完成", flush=True)
