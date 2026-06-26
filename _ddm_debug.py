"""DDM 调试：测试 V=0 平衡情况。"""

import numpy as np
from polaris.sim.ddm import DdmConfig, solve_ddm
from polaris.sim.ddm.scharfetter_gummel import EPS_0, EPS_R_SI, N_I_SI, Q_E, V_T

nx, ny = 100, 1
L = 2e-6
dx = L / nx
dy = 1e-6

N = 1.0e21
x = np.linspace(0.0, L, nx)
doping_p = np.where(x < L / 2, N, 0.0).reshape(nx, ny)
doping_n = np.where(x >= L / 2, N, 0.0).reshape(nx, ny)

print("=== V=0 平衡测试 ===")
config = DdmConfig(
    nx=nx, ny=ny, dx=dx, dy=dy,
    eps_rel=EPS_R_SI,
    doping_n=doping_n,
    doping_p=doping_p,
    contacts={"west": 0.0, "east": 0.0},
    max_iter=5,  # 只跑 5 次看
    tol=1e-6,
)
try:
    result = solve_ddm(config)
    print(f"  收敛: {result.converged}, 迭代: {result.n_iterations}")
    print(f"  phi range: [{result.potential.min():.4f}, {result.potential.max():.4f}] V")
    print(f"  n range: [{result.electron_density.min():.3e}, {result.electron_density.max():.3e}]")
    print(f"  p range: [{result.hole_density.min():.3e}, {result.hole_density.max():.3e}]")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    # 手动调试：单步执行
    from polaris.sim.ddm.solver import (
        DdmSolver, _equilibrium_carrier, _equilibrium_potential
    )
    from polaris.sim.ddm.poisson import PoissonSolver, PoissonBc, DIRICHLET
    from polaris.sim.ddm.continuity import ContinuitySolver
    from scipy.sparse.linalg import spsolve
    
    n_eq, p_eq = _equilibrium_carrier(doping_n, doping_p, N_I_SI)
    phi = _equilibrium_potential(n_eq, N_I_SI, V_T)
    print(f"\n  初值:")
    print(f"    phi range: [{phi.min():.4f}, {phi.max():.4f}] V")
    print(f"    n_eq range: [{n_eq.min():.3e}, {n_eq.max():.3e}]")
    print(f"    p_eq range: [{p_eq.min():.3e}, {p_eq.max():.3e}]")
    
    solver = DdmSolver()
    bc_specs = solver._compute_bc_specs(config, n_eq, p_eq, phi)
    print(f"  BC specs:")
    for side, spec in bc_specs.items():
        print(f"    {side}: phi_b={spec['phi_b']:.4f}, n_b={spec['n_b_arr'][0]:.3e}, p_b={spec['p_b_arr'][0]:.3e}")
    
    poisson = PoissonSolver()
    continuity = ContinuitySolver(
        nx, ny, dx, dy, config.mobility_n, config.mobility_p,
        config.tau_n, config.tau_p, N_I_SI, config.temperature,
    )
    
    n = n_eq.copy()
    p = p_eq.copy()
    
    # Step 1: Poisson
    charge = Q_E * (p - n + doping_n - doping_p)
    print(f"\n  Poisson charge range: [{charge.min():.3e}, {charge.max():.3e}]")
    bcs = [PoissonBc(side=s, type=DIRICHLET, value=sp["phi_b"]) for s, sp in bc_specs.items()]
    phi_new = poisson.solve(nx, ny, dx, dy, EPS_R_SI, charge, bcs)
    print(f"  phi_new range: [{phi_new.min():.4f}, {phi_new.max():.4f}] V")
    print(f"  phi_new - phi range: [{(phi_new-phi).min():.3e}, {(phi_new-phi).max():.3e}]")
    
    # Step 2: Electron
    A_n, b_n = continuity.electron_system(phi_new, n, p)
    print(f"\n  Electron matrix:")
    print(f"    A_n.shape: {A_n.shape}")
    print(f"    A_n.nnz: {A_n.nnz}")
    print(f"    A_n diag range: [{A_n.diagonal().min():.3e}, {A_n.diagonal().max():.3e}]")
    print(f"    b_n range: [{b_n.min():.3e}, {b_n.max():.3e}]")
    
    # 应用 Dirichlet
    from polaris.sim.ddm.solver import _apply_dirichlet
    for side, spec in bc_specs.items():
        A_n, b_n = _apply_dirichlet(A_n, b_n, spec["idx"], spec["n_b_arr"])
    print(f"    After BC: A_n diag range: [{A_n.diagonal().min():.3e}, {A_n.diagonal().max():.3e}]")
    print(f"    After BC: b_n range: [{b_n.min():.3e}, {b_n.max():.3e}]")
    
    n_new_vec = spsolve(A_n.tocsc(), b_n)
    print(f"  n_new range: [{n_new_vec.min():.3e}, {n_new_vec.max():.3e}]")
    if n_new_vec.min() < 0:
        print(f"  WARNING: n_new 出现负值！")
    
    # Step 3: Hole
    n_new = n_new_vec.reshape(nx, ny)
    A_p, b_p = continuity.hole_system(phi_new, n_new, p)
    print(f"\n  Hole matrix:")
    print(f"    A_p diag range: [{A_p.diagonal().min():.3e}, {A_p.diagonal().max():.3e}]")
    print(f"    b_p range: [{b_p.min():.3e}, {b_p.max():.3e}]")
    
    for side, spec in bc_specs.items():
        A_p, b_p = _apply_dirichlet(A_p, b_p, spec["idx"], spec["p_b_arr"])
    print(f"    After BC: A_p diag range: [{A_p.diagonal().min():.3e}, {A_p.diagonal().max():.3e}]")
    
    p_new_vec = spsolve(A_p.tocsc(), b_p)
    print(f"  p_new range: [{p_new_vec.min():.3e}, {p_new_vec.max():.3e}]")
    if p_new_vec.min() < 0:
        print(f"  WARNING: p_new 出现负值！")
        # 检查哪里出现负值
        neg_idx = np.where(p_new_vec < 0)[0]
        print(f"  负值位置（前 10）: {neg_idx[:10]}")
        print(f"  负值（前 10）: {p_new_vec[neg_idx[:10]]}")
        # 检查这些位置的 phi, n
        for k in neg_idx[:5]:
            i, j = k // ny, k % ny
            print(f"    k={k} (i={i},j={j}): phi={phi_new[i,j]:.4f}, n={n_new[i,j]:.3e}, p_old={p[i,j]:.3e}")
