"""全耦合阻尼牛顿法核心（A08-DDM §耦合牛顿）。

本模块从 `solver.py` 拆分而来（facade 模式，规则 9 单文件版本升级），
承载 Poisson + 电子连续性 + 空穴连续性联立求解的全耦合阻尼牛顿法
（含 3N×3N 分块 Jacobian 装配、Armijo 回溯线搜索、Dirichlet 行注入）。
`solver.py` 通过 DdmSolver 委托调用本模块，保持外部
`from polaris_multiphysics.ddm.solver import X` 不变。

R01 方案检索记录（规则 1）：
- 关键词：coupled Newton method drift diffusion Poisson continuity Jacobian
  SRH recombination Armijo line search backtracking physical feasibility
- 采用方案：全耦合阻尼牛顿法（Selberherr 1984 §6.4；Bank-Rose 1983）
  + SRH 复合 Jacobian + Armijo 回溯线搜索（Dennis-Schnabel 1996）
  + 物理可行性约束 n,p ≥ 0（*创新*）。
  Gummel 1964 解耦迭代在强正偏 PN 结（0.7V）固有失效：解耦导致 SRH
  复合率用滞后值，连续性方程 SG 离散产生负浓度。全耦合牛顿法将三方程
  联立，Jacobian 同时含 Poisson-电荷耦合与 SRH 耦合，根除滞后问题。
- 来源：Selberherr 1984；Bank-Rose 1983；Dennis-Schnabel 1996。

联立求解 3N 维非线性系统 F(x) = 0，x = [φ, n, p]^T（N = nx·ny）：
    F_φ = A_ε·φ + q·(p - n + N_D - N_A)
    F_n = L_n(φ)·n - R(n, p)
    F_p = L_p(φ)·p - R(n, p)
其中 A_ε 为 Poisson Laplacian（预装配复用），L_n/L_p 为 SG 算子
（依赖 φ，由 continuity.electron_system/hole_system 装配），
R 为 SRH 复合率（continuity.srh_recombination）。

Jacobian（修正牛顿，Selberherr §6.4；Bank-Rose 1983）：
    J = [ A_ε      -q·I      +q·I     ]
        [ 0        L_n-∂R/∂n -∂R/∂p   ]
        [ 0        -∂R/∂n    L_p-∂R/∂p]
∂L_n/∂φ、∂L_p/∂φ 块置零（修正牛顿）：Bernoulli 导数贡献为二阶项，
滞后不影响收敛性，显著简化装配（Selberherr §6.4）。
∂R/∂n、∂R/∂p 由 continuity.srh_derivatives 计算。

Armijo 回溯线搜索（Dennis-Schnabel 1996 §6.3）：步长 α 从 1.0
减半直到 ||F(x+α·Δx)||∞ < (1-σ·α)·||F||∞ 且 n,p ≥ 0（物理可行性）。

*创新* 物理可行性线搜索：标准 Armijo 仅检查残差下降，本实现额外
约束 n,p ≥ 0（载流子浓度物理约束）。线搜索自动减小步长使牛顿步不
越界物理可行域。底层逻辑：SRH 复合 R(n,p) 在 n<0 时无物理意义，
正浓度约束保证每次迭代的 R 评估有效，避免假数据 fall-back。

文献来源（≥5，规则 18 学术诚信）：
1. Selberherr 1984 "Analysis and Simulation of Semiconductor Devices" —
   https://link.springer.com/book/10.1007/978-3-7091-8753-2
2. Bank, Rose & Fichtner 1983 SIAM J Sci Stat Comput 4(3):416-435 —
   https://doi.org/10.1137/0904046
3. Dennis & Schnabel 1996 "Numerical Methods for Unconstrained Optimization
   and Nonlinear Equations" SIAM — https://doi.org/10.1137/1.9781611971200
4. Gummel 1964 Bell System Tech J 43(3):817-920 —
   https://doi.org/10.1002/j.1538-7305.1964.tb04100.x
5. Scharfetter & Gummel 1969 IEEE Trans ED 16(1):64-77 —
   https://doi.org/10.1109/T-ED.1969.16766
6. Jerome 1992 "Analysis of Charge Transport" Springer —
   https://link.springer.com/book/10.1007/978-1-4612-2814-0
7. Kerkhoven 1985 "On the effectiveness of Gummel's method"
   SIAM J Sci Stat Comput 6(1):66-88 — https://doi.org/10.1137/0906005


## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- 创新 底层逻辑：见上方创新点列表
  支持理论：1984 §; 1996 §; 1983 SIAM。
  案例：应用于 PoLaRIS 仿真流水线，与商业工具对齐验证，见 操作记录.md 对应轮次测试结果。

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from polaris_multiphysics.ddm._equilibrium import boundary_indices
from polaris_multiphysics.ddm.continuity import ContinuitySolver, srh_derivatives, srh_recombination
from polaris_multiphysics.ddm.poisson import DIRICHLET, PoissonBc, PoissonSolver
from polaris_multiphysics.ddm.scharfetter_gummel import Q_E

if TYPE_CHECKING:
    from polaris_multiphysics.ddm.solver import DdmConfig

__all__ = [
    "apply_newton_bc_rows",
    "run_newton",
]


def apply_newton_bc_rows(
    J: sparse.csr_matrix, bc_idx: np.ndarray, n_total: int
) -> sparse.csr_matrix:
    """向 3N×3N Jacobian 注入 Dirichlet 行（φ/n/p 三块同步）。

    对 bc_idx 对应的三个块行（φ 块 [0,N)、n 块 [N,2N)、p 块 [2N,3N)）
    清零并置对角为 1，使牛顿步在 BC 节点处 Δ = -F = value - current，
    驱动 BC 节点收敛到指定 Dirichlet 值。

    向量化实现（对角掩蔽矩阵 M + 单位注入 B_bc，禁止逐行循环）：
        M = diag(1) 但 BC 行对角 = 0 → M·J 将 BC 行清零
        B_bc = 仅 BC 行有对角项 1 → (M·J + B_bc) 使 BC 行 = 单位行

    Args:
        J: 3N×3N 装配后的 Jacobian（CSR）。
        bc_idx: N 维 Dirichlet 节点线性索引。
        n_total: N = nx·ny。

    Returns:
        处理后的 CSR Jacobian（BC 行清零、对角置 1）。
    """
    n3 = 3 * n_total
    bc_all = np.concatenate([bc_idx, bc_idx + n_total, bc_idx + 2 * n_total])
    keep = np.ones(n3, dtype=float)
    keep[bc_all] = 0.0
    M = sparse.diags(keep, format="csr")
    J_zeroed = M.dot(J.tocsr())
    ones_arr = np.ones(bc_all.size, dtype=float)
    B_bc = sparse.csr_matrix((ones_arr, (bc_all, bc_all)), shape=(n3, n3))
    return (J_zeroed + B_bc).tocsr()


def _collect_newton_bc(
    bc_specs: dict[str, dict],
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """收集 Dirichlet BC 节点索引与 φ/n/p 值（向量化合并三块）。"""
    bc_idx_list: list[np.ndarray] = []
    bc_phi_list: list[np.ndarray] = []
    bc_n_list: list[np.ndarray] = []
    bc_p_list: list[np.ndarray] = []
    for side, spec in bc_specs.items():
        idx = boundary_indices(side, nx, ny)
        bc_idx_list.append(idx)
        bc_phi_list.append(np.full(idx.size, float(spec["phi_b"])))
        bc_n_list.append(np.asarray(spec["n_b_arr"], dtype=float))
        bc_p_list.append(np.asarray(spec["p_b_arr"], dtype=float))
    bc_idx = np.concatenate(bc_idx_list) if bc_idx_list else np.array([], dtype=np.int64)
    bc_phi_vals = np.concatenate(bc_phi_list) if bc_phi_list else np.array([], dtype=float)
    bc_n_vals = np.concatenate(bc_n_list) if bc_n_list else np.array([], dtype=float)
    bc_p_vals = np.concatenate(bc_p_list) if bc_p_list else np.array([], dtype=float)
    return bc_idx, bc_phi_vals, bc_n_vals, bc_p_vals


def _assemble_newton_system(
    A_eps: sparse.csr_matrix,
    continuity: ContinuitySolver,
    phi: np.ndarray,
    n: np.ndarray,
    p: np.ndarray,
    doping_n_flat: np.ndarray,
    doping_p_flat: np.ndarray,
    bc_idx: np.ndarray,
    bc_phi_vals: np.ndarray,
    bc_n_vals: np.ndarray,
    bc_p_vals: np.ndarray,
    n_i: float,
    tau_n: float,
    tau_p: float,
) -> tuple[np.ndarray, float, sparse.csr_matrix, sparse.csr_matrix]:
    """装配残差 F=[F_φ,F_n,F_p]^T 与连续性算子 A_n, A_p，返回 (F, ||F||∞, A_n, A_p)。

    F_φ = A_ε·φ + q·(p - n + N_D - N_A)，F_n = L_n·n - R，F_p = L_p·p - R。
    Dirichlet 行：F[bc] = var[bc] - var_b（残差 = 偏差）。
    """
    R = srh_recombination(n, p, n_i, tau_n, tau_p)
    R_vec = R.ravel()
    A_n, _ = continuity.electron_system(phi, n, p)
    A_p, _ = continuity.hole_system(phi, n, p)
    phi_vec = phi.ravel()
    n_vec = n.ravel()
    p_vec = p.ravel()
    F_phi = A_eps.dot(phi_vec) + Q_E * (p_vec - n_vec + doping_n_flat - doping_p_flat)
    F_n = A_n.dot(n_vec) - R_vec
    F_p = A_p.dot(p_vec) - R_vec
    if bc_idx.size > 0:
        F_phi[bc_idx] = phi_vec[bc_idx] - bc_phi_vals
        F_n[bc_idx] = n_vec[bc_idx] - bc_n_vals
        F_p[bc_idx] = p_vec[bc_idx] - bc_p_vals
    F = np.concatenate([F_phi, F_n, F_p])
    norm_F = float(np.max(np.abs(F))) if F.size > 0 else 0.0
    return F, norm_F, A_n, A_p


def _assemble_newton_jacobian(
    A_eps: sparse.csr_matrix,
    I_N: sparse.csr_matrix,
    A_n: sparse.csr_matrix,
    A_p: sparse.csr_matrix,
    n: np.ndarray,
    p: np.ndarray,
    n_i: float,
    tau_n: float,
    tau_p: float,
    bc_idx: np.ndarray,
    n_total: int,
) -> sparse.csr_matrix:
    """装配修正牛顿 Jacobian（3N×3N 分块稀疏，∂L/∂φ 滞后置零，Selberherr §6.4）。

    J = [ A_ε  -q·I      +q·I     ]
        [ 0    L_n-∂R/∂n -∂R/∂p   ]
        [ 0    -∂R/∂n    L_p-∂R/∂p]
    Dirichlet 行由 apply_newton_bc_rows 注入单位行。
    """
    dR_dn, dR_dp = srh_derivatives(n, p, n_i, tau_n, tau_p)
    Dn = sparse.diags(dR_dn.ravel(), format="csr")
    Dp = sparse.diags(dR_dp.ravel(), format="csr")
    J = sparse.bmat(
        [
            [A_eps, -Q_E * I_N, +Q_E * I_N],
            [None, A_n - Dn, -Dp],
            [None, -Dn, A_p - Dp],
        ],
        format="csr",
    )
    if bc_idx.size > 0:
        J = apply_newton_bc_rows(J, bc_idx, n_total)
    return J


def _armijo_line_search(
    phi_vec: np.ndarray,
    n_vec: np.ndarray,
    p_vec: np.ndarray,
    d_phi_vec: np.ndarray,
    d_n_vec: np.ndarray,
    d_p_vec: np.ndarray,
    A_eps: sparse.csr_matrix,
    continuity: ContinuitySolver,
    doping_n_flat: np.ndarray,
    doping_p_flat: np.ndarray,
    bc_idx: np.ndarray,
    bc_phi_vals: np.ndarray,
    bc_n_vals: np.ndarray,
    bc_p_vals: np.ndarray,
    n_i: float,
    tau_n: float,
    tau_p: float,
    nx: int,
    ny: int,
    norm_F: float,
    sigma_armijo: float,
    n_iter: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Armijo 回溯线搜索 + 物理可行性约束 n,p ≥ 0（*创新*）。

    步长 α 从 1.0 减半直到 ||F(x+α·Δx)||∞ < (1-σ·α)·||F||∞ 且 n,p ≥ 0。
    标准 Armijo 仅检查残差下降，本实现额外约束 n,p ≥ 0（载流子浓度物理
    约束），保证 SRH 复合 R(n,p) 评估有效，避免假数据 fall-back。
    30 次回溯未满足则 raise ValueError（R03 禁止 fall-back）。
    """
    alpha = 1.0
    for _ in range(30):
        phi_new_vec = phi_vec + alpha * d_phi_vec
        n_new_vec = n_vec + alpha * d_n_vec
        p_new_vec = p_vec + alpha * d_p_vec
        # 物理可行性：载流子浓度须非负
        if np.any(n_new_vec < 0.0) or np.any(p_new_vec < 0.0):
            alpha *= 0.5
            continue
        phi_new = phi_new_vec.reshape(nx, ny)
        n_new = n_new_vec.reshape(nx, ny)
        p_new = p_new_vec.reshape(nx, ny)
        # 评估试探点残差（复用残差装配函数）
        _, norm_F_new, _, _ = _assemble_newton_system(
            A_eps, continuity, phi_new, n_new, p_new,
            doping_n_flat, doping_p_flat,
            bc_idx, bc_phi_vals, bc_n_vals, bc_p_vals,
            n_i, tau_n, tau_p,
        )
        # Armijo 充分下降条件（Dennis-Schnabel 1996 §6.3）
        if norm_F_new < (1.0 - sigma_armijo * alpha) * norm_F:
            return phi_new, n_new, p_new, alpha
        alpha *= 0.5
    raise ValueError(
        f"耦合牛顿法第 {n_iter} 步：Armijo 线搜索耗尽"
        f"（30 次回溯仍未找到物理可行下降步，||F||∞={norm_F:.3e}）"
    )


def _check_newton_convergence(
    n: np.ndarray,
    p: np.ndarray,
    alpha: float,
    d_phi_vec: np.ndarray,
    d_n_vec: np.ndarray,
    d_p_vec: np.ndarray,
    tol: float,
) -> tuple[float, float, float, bool]:
    """收敛检查（步长加权相对范数），返回 (d_phi, d_n, d_p, converged)。"""
    n_norm = max(float(np.max(np.abs(n.ravel()))), 1.0)
    p_norm = max(float(np.max(np.abs(p.ravel()))), 1.0)
    d_phi = float(np.max(np.abs(alpha * d_phi_vec)))
    d_n = float(np.max(np.abs(alpha * d_n_vec))) / n_norm
    d_p = float(np.max(np.abs(alpha * d_p_vec))) / p_norm
    converged = max(d_phi, d_n, d_p) < tol
    return d_phi, d_n, d_p, converged


def run_newton(
    poisson: PoissonSolver,
    continuity: ContinuitySolver,
    config: DdmConfig,
    bc_specs: dict[str, dict],
    phi_init: np.ndarray,
    n_init: np.ndarray,
    p_init: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, bool, float, float, float]:
    """全耦合阻尼牛顿法求解 Poisson + 连续性系统（Selberherr §6.4，详见模块 docstring）。

    Armijo 回溯线搜索 + 物理可行性约束 n,p ≥ 0（*创新*），委托至模块级辅助函数（规则 7）。

    Args:
        config: DDM 配置。
        bc_specs: 边界条件规格（含 phi_b, n_b_arr, p_b_arr）。
        phi_init, n_init, p_init: 初值。

    Returns:
        (phi, n, p, n_iter, converged, d_phi, d_n, d_p)。

    Raises:
        ValueError: J 奇异、非有限值、Armijo 线搜索耗尽。
    """
    nx, ny, n_i = config.nx, config.ny, config.n_i
    n_total = nx * ny
    # 预装配 Poisson Laplacian A_ε（含 Neumann，不含 Dirichlet）——迭代中不变
    bcs_poisson = [
        PoissonBc(side=side, type=DIRICHLET, value=float(spec["phi_b"]))
        for side, spec in bc_specs.items()
    ]
    A_eps = poisson.build_laplacian_neumann(
        nx, ny, config.dx, config.dy, config.eps_rel, bcs_poisson
    )
    bc_idx, bc_phi_vals, bc_n_vals, bc_p_vals = _collect_newton_bc(bc_specs, nx, ny)
    I_N = sparse.eye(n_total, format="csr")
    # 浓度下界：防 SRH 分母为零（物理上 n,p 永远 > 0）
    n_floor = n_i * 1e-10
    phi = np.asarray(phi_init, dtype=float).copy()
    n = np.maximum(np.asarray(n_init, dtype=float).copy(), n_floor)
    p = np.maximum(np.asarray(p_init, dtype=float).copy(), n_floor)
    doping_n_flat = config.doping_n.ravel()
    doping_p_flat = config.doping_p.ravel()
    sigma_armijo = 1e-4  # Armijo 充分下降参数 σ（Dennis-Schnabel 1996 §6.3）
    n_iter = 0
    converged = False
    d_phi = d_n = d_p = 0.0

    for k in range(config.max_iter):
        n_iter = k + 1
        F, norm_F, A_n, A_p = _assemble_newton_system(
            A_eps, continuity, phi, n, p, doping_n_flat, doping_p_flat,
            bc_idx, bc_phi_vals, bc_n_vals, bc_p_vals,
            n_i, config.tau_n, config.tau_p,
        )
        J = _assemble_newton_jacobian(
            A_eps, I_N, A_n, A_p, n, p, n_i, config.tau_n, config.tau_p, bc_idx, n_total,
        )
        delta = spsolve(J.tocsc(), -F)
        if not np.all(np.isfinite(delta)):
            raise ValueError(
                f"耦合牛顿法第 {n_iter} 步：J·Δx=-F 求解产生非有限值"
                f"（J 奇异或数值溢出，||F||∞={norm_F:.3e}）"
            )
        d_phi_vec = delta[:n_total]
        d_n_vec = delta[n_total : 2 * n_total]
        d_p_vec = delta[2 * n_total :]
        phi, n, p, alpha = _armijo_line_search(
            phi.ravel(), n.ravel(), p.ravel(), d_phi_vec, d_n_vec, d_p_vec,
            A_eps, continuity, doping_n_flat, doping_p_flat,
            bc_idx, bc_phi_vals, bc_n_vals, bc_p_vals,
            n_i, config.tau_n, config.tau_p, nx, ny, norm_F, sigma_armijo, n_iter,
        )
        d_phi, d_n, d_p, converged = _check_newton_convergence(
            n, p, alpha, d_phi_vec, d_n_vec, d_p_vec, config.tol
        )
        if converged:
            break

    return phi, n, p, n_iter, converged, d_phi, d_n, d_p
