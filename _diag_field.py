"""诊断 2.6632 模式场分布 + FDE 单段计时。"""
import sys
sys.path.insert(0, "/workspace/src")
import time
import numpy as np
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml
from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend

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
print("诊断 E: 2.6632 模式场分布（判断 slab 模 vs 真实波导模）")
print("=" * 70)
eps_r, window = build_soi_eps(80, 80, (3.0e-6, 3.0e-6))
cfg = FdeSolverConfig(wavelength=_WL, num_modes=2, pml=ScPml(layers=10))
solver = FdeSolver(cfg)
modes = solver.solve(eps_r, window)
mode0 = modes[0]
print(f"mode 0: n_eff={float(np.real(mode0.n_eff)):.6f}")
ey = mode0.ey
nx, ny = ey.shape
# 场能量在 x 方向的分布（按列求和）
energy_x = np.sum(np.abs(ey)**2, axis=1)  # (nx,)
energy_y = np.sum(np.abs(ey)**2, axis=0)  # (ny,)
total = np.sum(energy_x)
energy_x_norm = energy_x / total
energy_y_norm = energy_y / total
# 核心区域（500nm 宽）能量占比
lx = 3.0e-6
dx = lx / nx
x_coords = (np.arange(nx) + 0.5) * dx - lx / 2.0
core_mask_x = np.abs(x_coords) <= _W / 2.0
core_energy_x = np.sum(energy_x[core_mask_x]) / total
print(f"  x 方向核心区（|x|<=250nm）能量占比: {core_energy_x:.4f}")
print(f"  x 方向能量分布（每 10 列）: {[f'{v:.3f}' for v in energy_x_norm[::10]]}")
# y 方向核心区域（220nm 高）能量占比
ly = 3.0e-6
dy = ly / ny
y_coords = (np.arange(ny) + 0.5) * dy - ly / 2.0
core_mask_y = np.abs(y_coords) <= _H / 2.0
core_energy_y = np.sum(energy_y[core_mask_y]) / total
print(f"  y 方向核心区（|y|<=110nm）能量占比: {core_energy_y:.4f}")
print(f"  y 方向能量分布（每 10 列）: {[f'{v:.3f}' for v in energy_y_norm[::10]]}")
# 判断：如果 x 方向核心区能量占比 > 0.5，是真实波导模；否则 slab 模
if core_energy_x > 0.5:
    print(f"  => 真实波导模（x 方向受限，核心占比 {core_energy_x:.2%}）")
else:
    print(f"  => slab 模（x 方向弥散，核心占比 {core_energy_x:.2%}）")

print("\n" + "=" * 70)
print("诊断 F: FDE 单段求解计时（n_modes=1,2,3）")
print("=" * 70)
for n_modes in [1, 2, 3]:
    backend = FIMMPROPBackend(EMEConfig(
        n_modes=n_modes, wavelength=_WL, dx=5e-8, dy=5e-8,
        window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
    ))
    # 构造 800nm 宽波导段（最难求第 2 模式）
    eps_r = backend._make_strip_eps(0.8e-6, _H, _N_SI, _N_SIO2)
    sid = backend.add_section(1.0e-6, eps_r, label="test")
    t0 = time.time()
    try:
        r = backend.solve_modes(sid)
        t1 = time.time()
        print(f"  n_modes={n_modes}: {t1-t0:.2f}s, n_eff={[float(np.real(n)) for n in r['n_eff']]}", flush=True)
    except Exception as e:
        t1 = time.time()
        print(f"  n_modes={n_modes}: {t1-t0:.2f}s 失败 {type(e).__name__}: {e}", flush=True)

print("\n" + "=" * 70)
print("诊断 G: 不同宽度 FDE n_modes=2 计时")
print("=" * 70)
for w_nm in [500, 650, 800, 1000, 1500, 2000]:
    backend = FIMMPROPBackend(EMEConfig(
        n_modes=2, wavelength=_WL, dx=5e-8, dy=5e-8,
        window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
    ))
    eps_r = backend._make_strip_eps(w_nm * 1e-9, _H, _N_SI, _N_SIO2)
    sid = backend.add_section(1.0e-6, eps_r, label=f"w{w_nm}")
    t0 = time.time()
    try:
        r = backend.solve_modes(sid)
        t1 = time.time()
        print(f"  w={w_nm}nm: {t1-t0:.2f}s, n_eff={[float(np.real(n)) for n in r['n_eff']]}", flush=True)
    except Exception as e:
        t1 = time.time()
        print(f"  w={w_nm}nm: {t1-t0:.2f}s 失败 {type(e).__name__}: {e}", flush=True)
print("\n完成", flush=True)
