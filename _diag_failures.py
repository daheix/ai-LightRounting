"""诊断 3 个失败测试的根因（临时诊断脚本，完成后删除）。"""
import sys
sys.path.insert(0, "/workspace/src")
import numpy as np
import scipy.sparse.linalg as spla
from polaris.sim.fde import FdeSolver, FdeSolverConfig
from polaris.sim.grid.pml import ScPml
from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend
from polaris.sim.eme import build_interface_smatrix
from polaris.sim.eme.overlap import overlap_matrix

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
print("诊断 1: test_soi_fundamental_mode 候选模式频谱")
print("=" * 70)
eps_r, window = build_soi_eps(80, 80, (3.0e-6, 3.0e-6))
cfg = FdeSolverConfig(wavelength=_WL, num_modes=4, pml=ScPml(layers=10))
solver = FdeSolver(cfg)
eps_c = eps_r.astype(np.complex128, copy=True)
grid = solver._build_grid(eps_c, window)
a_mat = solver._assemble_te_matrix(grid)
n_clad = float(np.sqrt(np.real(eps_c).min()))
n_core = float(np.sqrt(np.real(eps_c).max()))
n_eff_shift = n_clad + cfg.shift_frac * (n_core - n_clad)
pml_layers = cfg.pml.layers
n_eff_max_guided = n_core - 0.5
n_total = grid.spec.num_cells
k_request = min(cfg.num_modes + 12, n_total - 2)
sigma_main = (solver.k0 * n_eff_shift) ** 2
strategies = [
    ("C", sigma_main, "LR"),
    ("A", sigma_main, "LM"),
    ("D", (solver.k0 * 2.8) ** 2, "LM"),
]
print(f"n_clad={n_clad:.4f}, n_core={n_core:.4f}, n_eff_shift={n_eff_shift:.4f}")
print(f"n_eff_max_guided={n_eff_max_guided:.4f}, k_request={k_request}")
print(f"导模范围: ({n_clad:.4f}, {n_eff_max_guided:.4f})")
all_neffs = set()
for name, sigma, which in strategies:
    try:
        eigvals, eigvecs = spla.eigs(a_mat, k=k_request, sigma=sigma, which=which)
    except spla.ArpackNoConvergence:
        print(f"  策略 {name}: 不收敛")
        continue
    cands = solver._extract_guided_candidates(
        eigvals, eigvecs, grid, n_clad, n_eff_max_guided, pml_layers
    )
    print(f"  策略 {name} (sigma={sigma:.4e}, which={which}): {len(cands)} 导模候选")
    for n_eff, beta, ey, loc in cands:
        re_n = float(np.real(n_eff))
        im_n = float(np.imag(n_eff))
        key = round(re_n, 4)
        if key in all_neffs:
            continue
        all_neffs.add(key)
        print(f"    n_eff={re_n:.6f}{im_n:+.2e}j  loc={loc:.4f}  beta={beta:.4e}")

modes = solver.solve(eps_r, window)
print(f"\n最终返回 {len(modes)} 个模式:")
for i, m in enumerate(modes):
    print(f"  mode {i}: n_eff={float(np.real(m.n_eff)):.6f}  te_frac={m.te_fraction:.4f}")

print("\n" + "=" * 70)
print("诊断 2: test_run_taper 各段 n_eff")
print("=" * 70)
backend = FIMMPROPBackend(EMEConfig(
    n_modes=1, wavelength=_WL, dx=5e-8, dy=5e-8,
    window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
))
backend.build_taper(length=20.0e-6, w_in=_W, w_out=0.8e-6,
                    height=_H, n_core=_N_SI, n_clad=_N_SIO2, n_steps=5)
for sec in backend._sections:
    r = backend.solve_modes(sec.section_id)
    n_eff = r["n_eff"][0]
    te = r["te_fraction"][0]
    print(f"  段 {sec.section_id} ({sec.label}): n_eff={float(np.real(n_eff)):.6f}, te={te:.4f}")
result = backend.run()
print(f"  energy_sum={result['energy_sum']:.6f}")
print(f"  reflection={np.abs(result['reflection'])}")
print(f"  transmission={np.abs(result['transmission'])}")

print("\n  界面 S 矩阵酉性检验 (|S11|²+|S21|² 应=1):")
dx, dy = backend.config.dx, backend.config.dy
for i in range(len(backend._sections) - 1):
    ma = backend._sections[i].modes
    mb = backend._sections[i + 1].modes
    s = build_interface_smatrix(ma, mb, dx, dy)
    unitary = float(np.abs(s.s11[0, 0])**2 + np.abs(s.s21[0, 0])**2)
    s11 = s.s11[0, 0]
    s21 = s.s21[0, 0]
    me, mh = overlap_matrix(ma, mb, dx, dy)
    print(f"  界面 {i}->{i+1}: |S11|²+|S21|²={unitary:.6f}  "
          f"S11={s11:.4f} S21={s21:.4f}  "
          f"m_e={me[0,0]:.4f} m_h={mh[0,0]:.4f}  "
          f"Re(m_e·conj(m_h))={np.real(me[0,0]*np.conj(mh[0,0])):.4f}")

print("\n" + "=" * 70)
print("诊断 3: test_build_mmi_and_crossing 各段 n_eff")
print("=" * 70)
backend2 = FIMMPROPBackend(EMEConfig(
    n_modes=1, wavelength=_WL, dx=5e-8, dy=5e-8,
    window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
))
ids = backend2.build_crossing(
    length=10.0e-6, width_port=_W, width_wide=1.5e-6,
    height=_H, n_core=_N_SI, n_clad=_N_SIO2, n_steps=2,
)
print(f"  crossing 段数: {len(ids)}")
for sec in backend2._sections:
    r = backend2.solve_modes(sec.section_id)
    n_eff = r["n_eff"][0]
    te = r["te_fraction"][0]
    print(f"  段 {sec.section_id} ({sec.label}): L={sec.length*1e6:.2f}um, "
          f"n_eff={float(np.real(n_eff)):.6f}, te={te:.4f}")
result2 = backend2.run()
print(f"  energy_sum={result2['energy_sum']:.6f}")
print(f"  reflection={np.abs(result2['reflection'])}")
print(f"  transmission={np.abs(result2['transmission'])}")

print("\n  界面 S 矩阵酉性检验:")
for i in range(len(backend2._sections) - 1):
    ma = backend2._sections[i].modes
    mb = backend2._sections[i + 1].modes
    s = build_interface_smatrix(ma, mb, dx, dy)
    unitary = float(np.abs(s.s11[0, 0])**2 + np.abs(s.s21[0, 0])**2)
    me, mh = overlap_matrix(ma, mb, dx, dy)
    print(f"  界面 {i}->{i+1} ({backend2._sections[i].label}->{backend2._sections[i+1].label}): "
          f"|S11|²+|S21|²={unitary:.6f}  "
          f"m_e={me[0,0]:.4f} m_h={mh[0,0]:.4f}  "
          f"Re(m_e·conj(m_h))={np.real(me[0,0]*np.conj(mh[0,0])):.4f}")
