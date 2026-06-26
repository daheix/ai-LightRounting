"""调试牛顿法残差分量。"""
import numpy as np
from polaris.sim.ddm import DdmConfig
from polaris.sim.ddm.scharfetter_gummel import EPS_R_SI, N_I_SI, Q_E
from polaris.sim.ddm.poisson import DIRICHLET, PoissonBc, PoissonSolver
from polaris.sim.ddm.continuity import ContinuitySolver, srh_recombination
from polaris.sim.ddm.solver import (
    DdmSolver,
    _boundary_indices,
    _equilibrium_carrier,
    _equilibrium_potential,
)

nx, ny = 200, 1
L = 2e-6
dx = L / nx
dy = 1e-6
N = 1.0e21
x = np.linspace(0.0, L, nx)
doping_p = np.where(x < L / 2, N, 0.0).reshape(nx, ny)
doping_n = np.where(x >= L / 2, N, 0.0).reshape(nx, ny)

config = DdmConfig(
    nx=nx, ny=ny, dx=dx, dy=dy,
    eps_rel=EPS_R_SI, doping_n=doping_n, doping_p=doping_p,
    contacts={"west": 0.0, "east": 0.7}, max_iter=100, tol=1e-6,
)

solver = DdmSolver()
n_eq_qn, p_eq_qn = _equilibrium_carrier(config.doping_n, config.doping_p, config.n_i)
phi_eq_qn = _equilibrium_potential(n_eq_qn, config.n_i, config.vt)
poisson = PoissonSolver()
continuity = ContinuitySolver(
    config.nx, config.ny, config.dx, config.dy,
    config.mobility_n, config.mobility_p,
    config.tau_n, config.tau_p, config.n_i, config.temperature,
)

eq_contacts = {side: 0.0 for side in config.contacts}
eq_bc_specs = solver._compute_bc_specs(config, n_eq_qn, p_eq_qn, phi_eq_qn, eq_contacts)
phi_eq, n_eq, p_eq, n_iter_eq = solver._solve_equilibrium(poisson, config, phi_eq_qn, eq_bc_specs)
print(f"平衡牛顿迭代 {n_iter_eq} 次")
print(f"phi_eq range: [{phi_eq.min():.4e}, {phi_eq.max():.4e}]")
print(f"n_eq range:   [{n_eq.min():.4e}, {n_eq.max():.4e}]")
print(f"p_eq range:   [{p_eq.min():.4e}, {p_eq.max():.4e}]")
print(f"n*p vs n_i^2: n*p range [{(n_eq*p_eq).min():.4e}, {(n_eq*p_eq).max():.4e}], n_i^2={config.n_i**2:.4e}")

# 第一个 voltage continuation step
step_contacts = {side: v * 0.25 for side, v in config.contacts.items()}
bc_specs = solver._compute_bc_specs(config, n_eq, p_eq, phi_eq, step_contacts)
print(f"\nV_frac=0.25, contacts={step_contacts}")
print(f"west phi_b={bc_specs['west']['phi_b']:.4f}, east phi_b={bc_specs['east']['phi_b']:.4f}")

# 残差分析（用平衡解作为初值）
phi = phi_eq.copy()
n = n_eq.copy()
p = p_eq.copy()
n_total = nx * ny
n_i = config.n_i

bcs_poisson = [PoissonBc(side=side, type=DIRICHLET, value=float(spec["phi_b"])) for side, spec in bc_specs.items()]
A_eps = poisson.build_laplacian_neumann(nx, ny, config.dx, config.dy, config.eps_rel, bcs_poisson)

bc_idx_list = []
bc_phi_list = []
bc_n_list = []
bc_p_list = []
for side, spec in bc_specs.items():
    idx = _boundary_indices(side, nx, ny)
    bc_idx_list.append(idx)
    bc_phi_list.append(np.full(idx.size, float(spec["phi_b"])))
    bc_n_list.append(np.asarray(spec["n_b_arr"], dtype=float))
    bc_p_list.append(np.asarray(spec["p_b_arr"], dtype=float))
bc_idx = np.concatenate(bc_idx_list)
bc_phi_vals = np.concatenate(bc_phi_list)
bc_n_vals = np.concatenate(bc_n_list)
bc_p_vals = np.concatenate(bc_p_list)

phi_vec = phi.ravel()
n_vec = n.ravel()
p_vec = p.ravel()
R = srh_recombination(n, p, n_i, config.tau_n, config.tau_p)
R_vec = R.ravel()
A_n, b_n = continuity.electron_system(phi, n, p)
A_p, b_p = continuity.hole_system(phi, n, p)

doping_n_flat = config.doping_n.ravel()
doping_p_flat = config.doping_p.ravel()
F_phi = A_eps.dot(phi_vec) + Q_E * (p_vec - n_vec + doping_n_flat - doping_p_flat)
F_n = A_n.dot(n_vec) - R_vec
F_p = A_p.dot(p_vec) - R_vec
print(f"\n残差分量（BC 注入前）:")
print(f"  ||F_phi||inf = {np.max(np.abs(F_phi)):.4e}")
print(f"  ||F_n||inf   = {np.max(np.abs(F_n)):.4e}")
print(f"  ||F_p||inf   = {np.max(np.abs(F_p)):.4e}")
print(f"  ||R||inf     = {np.max(np.abs(R_vec)):.4e}")
print(f"  ||A_n*n||inf = {np.max(np.abs(A_n.dot(n_vec))):.4e}")
print(f"  ||b_n(=R)||inf = {np.max(np.abs(b_n)):.4e}")
print(f"  ||A_p*p||inf = {np.max(np.abs(A_p.dot(p_vec))):.4e}")
print(f"  ||b_p(=R)||inf = {np.max(np.abs(b_p)):.4e}")

F_phi[bc_idx] = phi_vec[bc_idx] - bc_phi_vals
F_n[bc_idx] = n_vec[bc_idx] - bc_n_vals
F_p[bc_idx] = p_vec[bc_idx] - bc_p_vals
print(f"\n残差分量（BC 注入后）:")
print(f"  ||F_phi||inf = {np.max(np.abs(F_phi)):.4e}")
print(f"  ||F_n||inf   = {np.max(np.abs(F_n)):.4e}")
print(f"  ||F_p||inf   = {np.max(np.abs(F_p)):.4e}")
