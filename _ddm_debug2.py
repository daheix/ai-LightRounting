"""DDM 调试：Anderson 加速逐步日志。"""

import numpy as np
from polaris.sim.ddm import DdmConfig
from polaris.sim.ddm.solver import DdmSolver, _equilibrium_carrier, _equilibrium_potential
from polaris.sim.ddm.poisson import PoissonSolver
from polaris.sim.ddm.continuity import ContinuitySolver
from polaris.sim.ddm.scharfetter_gummel import EPS_R_SI


def main() -> None:
    nx, ny = 200, 1
    L = 2e-6
    dx = L / nx
    dy = 1e-6
    N = 1.0e21
    x = np.linspace(0.0, L, nx)
    doping_p = np.where(x < L / 2, N, 0.0).reshape(nx, ny)
    doping_n = np.where(x >= L / 2, N, 0.0).reshape(nx, ny)

    config = DdmConfig(
        nx=nx, ny=ny, dx=dx, dy=dy, eps_rel=EPS_R_SI,
        doping_n=doping_n, doping_p=doping_p,
        contacts={"west": 0.0, "east": 0.175}, max_iter=100, tol=1e-6,
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
    eq_contacts = {s: 0.0 for s in config.contacts}
    eq_bc = solver._compute_bc_specs(config, n_eq_qn, p_eq_qn, phi_eq_qn, eq_contacts)
    phi_eq, n_eq, p_eq, _ = solver._solve_equilibrium(poisson, config, phi_eq_qn, eq_bc)
    bc_specs = solver._compute_bc_specs(config, n_eq, p_eq, phi_eq, config.contacts)

    phi, n, p = phi_eq.copy(), n_eq.copy(), p_eq.copy()
    n_total = nx * ny
    m_depth = 5
    x_hist, f_hist = [], []
    damping_candidates = (0.5, 0.25, 0.1, 0.05)

    for k in range(15):
        phi_old, n_old, p_old = phi.copy(), n.copy(), p.copy()
        phi_full = solver._solve_poisson(poisson, config, n, p, bc_specs)
        phi_g = n_g = p_g = None
        for damping in damping_candidates:
            phi_d = phi_old + damping * (phi_full - phi_old)
            n_full = solver._solve_electron(continuity, config, phi_d, n_old, p_old, bc_specs)
            n_d = n_old + damping * (n_full - n_old)
            if not (np.all(np.isfinite(n_d)) and np.all(n_d >= 0.0)):
                continue
            p_full = solver._solve_hole(continuity, config, phi_d, n_d, p_old, bc_specs)
            p_d = p_old + damping * (p_full - p_old)
            if np.all(np.isfinite(p_d)) and np.all(p_d >= 0.0):
                phi_g, n_g, p_g = phi_d, n_d, p_d
                break
        if phi_g is None:
            print(f"Iter {k+1}: ALL damping failed, phi_full [{phi_full.min():.3e},{phi_full.max():.3e}]")
            break

        n_norm = max(float(np.max(np.abs(n_old))), 1.0)
        p_norm = max(float(np.max(np.abs(p_old))), 1.0)
        d_phi = float(np.max(np.abs(phi_g - phi_old)))
        d_n = float(np.max(np.abs(n_g - n_old))) / n_norm
        d_p = float(np.max(np.abs(p_g - p_old))) / p_norm
        print(f"Iter {k+1}: damp={damping} d_phi={d_phi:.3e} d_n={d_n:.3e} phi_g[{phi_g.min():.3f},{phi_g.max():.3f}]")

        x_k = np.concatenate([phi_old.ravel(), n_old.ravel(), p_old.ravel()])
        g_k = np.concatenate([phi_g.ravel(), n_g.ravel(), p_g.ravel()])
        f_k = g_k - x_k
        x_hist.append(x_k.copy())
        f_hist.append(f_k.copy())

        m_k = min(m_depth, k)
        if m_k >= 1:
            cols_F = [f_k - f_hist[k - j] for j in range(1, m_k + 1)]
            cols_X = [x_k - x_hist[k - j] for j in range(1, m_k + 1)]
            F_diff = np.column_stack(cols_F)
            X_diff = np.column_stack(cols_X)
            gamma, _, _, _ = np.linalg.lstsq(F_diff, f_k, rcond=None)
            x_next = g_k - (X_diff + F_diff) @ gamma
            step_a = np.linalg.norm(x_next - x_k)
            step_g = np.linalg.norm(f_k)
            print(f"  AA: ||gamma||={np.linalg.norm(gamma):.3e} ||step_a||={step_a:.3e} ||step_g||={step_g:.3e} ratio={step_a/max(step_g,1e-30):.2f}")
        else:
            x_next = g_k
            print(f"  AA: first step (no history)")

        phi = x_next[:n_total].reshape(nx, ny)
        n = x_next[n_total:2*n_total].reshape(nx, ny)
        p = x_next[2*n_total:].reshape(nx, ny)
        if not (np.all(np.isfinite(phi)) and np.all(np.isfinite(n)) and np.all(np.isfinite(p))) or np.any(n < 0) or np.any(p < 0):
            print(f"  AA infeasible! phi[{phi.min():.3f},{phi.max():.3f}] n[{n.min():.2e},{n.max():.2e}] -> fallback to g_k")
            phi, n, p = phi_g, n_g, p_g
        else:
            print(f"  AA ok: phi[{phi.min():.3f},{phi.max():.3f}] n[{n.min():.2e},{n.max():.2e}]")


if __name__ == "__main__":
    main()
