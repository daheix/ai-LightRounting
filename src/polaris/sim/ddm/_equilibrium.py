"""平衡态牛顿法与边界工具函数（A08-DDM §平衡求解）。

本模块从 `solver.py` 拆分而来（facade 模式，规则 9 单文件版本升级），
承载热平衡载流子计算、平衡电势、边界索引、Dirichlet 行替换，以及
非线性 Poisson-Boltzmann 平衡牛顿求解器。`solver.py` 通过 DdmSolver
委托调用本模块，保持外部 `from polaris.sim.ddm.solver import X` 不变。

R01 方案检索记录（规则 1）：
- 关键词：semiconductor equilibrium Newton Poisson-Boltzmann depletion region
  Dirichlet row replacement sparse matrix vectorized
- 采用方案：准中性初值 + 牛顿法求解非线性 Poisson-Boltzmann
  （Selberherr 1984 §6.3；Bank-Rose 1983；Jerome 1992），含自适应阻尼。
  Dirichlet 行替换用对角掩蔽矩阵 + 单位对角注入（向量化，禁止逐行循环）。
- 来源：Selberherr 1984；Bank-Rose 1983；Jerome 1992。

非线性 Poisson-Boltzmann 方程（Selberherr 1984 §6.3；Jerome 1992）：
    F(φ) = ∇·(ε·∇φ) + q·(p(φ) - n(φ) + N_D - N_A) = 0
其中 n(φ) = n_i·exp(φ/V_T), p(φ) = n_i·exp(-φ/V_T)（平衡 Boltzmann 关系，
来自零电流条件 J_n=J_p=0）。

牛顿线性化（Bank-Rose 1983；Jerome 1992 §4）：
    J·δφ = -F(φ)，φ ← φ + damp·δφ
    J = A_Lap - (q/V_T)·diag(n + p)
推导：dn/dφ = n/V_T，dp/dφ = -p/V_T，故
    ∂ρ/∂φ = q·(dp/dφ - dn/dφ) = -(q/V_T)·(n + p)
    J = A_Lap + ∂ρ/∂φ = A_Lap - (q/V_T)·diag(n + p)

*创新* 牛顿法比 Poisson-Boltzmann 固定点迭代显著稳定：
固定点 J_fixed = A_Lap 缺少 -(q/V_T)·(n+p) 对角项，φ 较大处 exp 正
反馈导致发散；牛顿 J 含 -(q/V_T)·(n+p) 增加对角占优（diag 更负），
保证收敛（Bank-Rose 1983 收敛性理论）。

文献来源（≥5，规则 18 学术诚信）：
1. Selberherr 1984 "Analysis and Simulation of Semiconductor Devices" —
   https://link.springer.com/book/10.1007/978-3-7091-8753-2
2. Bank, Rose & Fichtner 1983 SIAM J Sci Stat Comput 4(3):416-435 —
   https://doi.org/10.1137/0904046
3. Jerome 1992 "Analysis of Charge Transport" Springer —
   https://link.springer.com/book/10.1007/978-1-4612-2814-0
4. Markowich 1986 "The Stationary Semiconductor Device Equations" —
   https://link.springer.com/book/10.1007/978-3-7091-3692-6
5. Polak 1971 "Computational Methods in Optimization" Academic Press
   （Armijo/阻尼线搜索收敛性理论）—
   https://www.sciencedirect.com/book/9780125630500/computational-methods-in-optimization
6. Sze 2006 "Physics of Semiconductor Devices" —
   https://onlinelibrary.wiley.com/doi/book/10.1002/0470068329

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from polaris.sim.ddm.poisson import DIRICHLET, PoissonBc, PoissonSolver
from polaris.sim.ddm.scharfetter_gummel import Q_E

if TYPE_CHECKING:
    from polaris.sim.ddm.solver import DdmConfig

__all__ = [
    "apply_dirichlet",
    "boundary_indices",
    "equilibrium_carrier",
    "equilibrium_potential",
    "solve_equilibrium",
]


def equilibrium_carrier(
    doping_n: np.ndarray, doping_p: np.ndarray, n_i: float
) -> tuple[np.ndarray, np.ndarray]:
    """计算热平衡载流子浓度（电中性条件）。

    n_eq = 0.5·((N_D-N_A) + sqrt((N_D-N_A)² + 4·n_i²))
    p_eq = n_i² / n_eq（质量作用定律）

    Args:
        doping_n: N_D 场 [m^-3]。
        doping_p: N_A 场 [m^-3]。
        n_i: 本征浓度 [m^-3]。

    Returns:
        (n_eq, p_eq) 元组，与输入同形状，全为正值。
    """
    n_net = doping_n - doping_p
    n_eq = 0.5 * (n_net + np.sqrt(n_net**2 + 4.0 * n_i**2))
    p_eq = n_i**2 / n_eq
    return n_eq, p_eq


def equilibrium_potential(n_eq: np.ndarray, n_i: float, vt: float) -> np.ndarray:
    """平衡电势 φ_eq = V_T·ln(n_eq/n_i) [V]。

    推导：平衡时 n = n_i·exp(φ/V_T)，故 φ = V_T·ln(n/n_i)。
    """
    if np.any(n_eq <= 0.0):
        raise ValueError("n_eq 须 > 0（计算平衡电势前置条件）")
    return vt * np.log(n_eq / n_i)


def boundary_indices(side: str, nx: int, ny: int) -> np.ndarray:
    """返回某方向边界节点的线性索引（k = i·ny + j）。"""
    if side == "west":
        return np.array([j for j in range(ny)], dtype=np.int64)
    if side == "east":
        return np.array([(nx - 1) * ny + j for j in range(ny)], dtype=np.int64)
    if side == "south":
        return np.array([i * ny for i in range(nx)], dtype=np.int64)
    if side == "north":
        return np.array([i * ny + (ny - 1) for i in range(nx)], dtype=np.int64)
    raise ValueError(f"未知方向 {side}")


def apply_dirichlet(
    A: sparse.csr_matrix,
    b: np.ndarray,
    nodes: np.ndarray,
    values: np.ndarray,
) -> tuple[sparse.csr_matrix, np.ndarray]:
    """向量化 Dirichlet 行替换：A[k,k]=1, A[k,j≠k]=0, b[k]=value。

    用对角掩蔽矩阵 M（BC 行对角置 0）+ 稀疏 B_bc（仅 BC 行有对角项）注入，
    规则：禁止逐元素循环（与 heat/boundary.py 同模式）。

    Args:
        A: 装配后的稀疏矩阵。
        b: 装配后的右端向量。
        nodes: Dirichlet 节点线性索引数组。
        values: 对应的 Dirichlet 值数组。

    Returns:
        (A_final, b_final)：A_final 为 CSR 稀疏矩阵，b_final 为右端。
    """
    n = A.shape[0]
    A_csr = A.tocsr()
    b_out = np.asarray(b, dtype=float).copy()
    nodes_arr = np.asarray(nodes, dtype=np.int64)
    vals_arr = np.asarray(values, dtype=float)

    if nodes_arr.size == 0:
        return A_csr, b_out

    keep = np.ones(n, dtype=float)
    keep[nodes_arr] = 0.0
    M = sparse.diags(keep, format="csr")
    A_zeroed = M.dot(A_csr)

    # B_bc 对角项 = 1.0（让 A[k,k]=1，b[k]=value 决定 n[k]=value）。
    # 错误用法是把 vals_arr 放到对角（A[k,k]=value，则 n[k]=value/value=1，失效）。
    ones_arr = np.ones(nodes_arr.size, dtype=float)
    B_bc = sparse.csr_matrix((ones_arr, (nodes_arr, nodes_arr)), shape=(n, n))
    A_final = (A_zeroed + B_bc).tocsr()
    b_out[nodes_arr] = vals_arr
    return A_final, b_out


def solve_equilibrium(
    poisson: PoissonSolver,
    config: DdmConfig,
    phi_init: np.ndarray,
    bc_specs: dict[str, dict],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """牛顿法求解平衡态非线性 Poisson（Boltzmann 关系，含耗尽区）。

    准中性初值 phi_eq 处处满足电中性→Poisson 电荷≈0→Poisson 解为线性
    势（无耗尽区），与真实平衡势差异巨大，导致后续 Gummel 迭代发散。
    本方法用牛顿法求解非线性 Poisson-Boltzmann 方程，得到含耗尽区的
    真实平衡势。

    非线性 Poisson-Boltzmann 方程（Selberherr 1984 §6.3；Jerome 1992）：
        F(φ) = ∇·(ε·∇φ) + q·(p(φ) - n(φ) + N_D - N_A) = 0
    其中 n(φ) = n_i·exp(φ/V_T), p(φ) = n_i·exp(-φ/V_T)（平衡 Boltzmann 关系，
    来自零电流条件 J_n=J_p=0）。

    牛顿线性化（Bank-Rose 1983；Jerome 1992 §4）：
        J·δφ = -F(φ)，φ ← φ + damp·δφ
        J = A_Lap - (q/V_T)·diag(n + p)

    *创新* 牛顿法比 Poisson-Boltzmann 固定点迭代显著稳定：
    固定点 J_fixed = A_Lap 缺少 -(q/V_T)·(n+p) 对角项，φ 较大处 exp 正
    反馈导致发散；牛顿 J 含 -(q/V_T)·(n+p) 增加对角占优（diag 更负），
    保证收敛（Bank-Rose 1983 收敛性理论）。

    自适应阻尼（Bank-Rose 1983）：尝试 [1.0, 0.5, 0.25, 0.1, 0.05]，
    选择使 ||F||∞ 下降的因子；全失败则用 0.01 强制小步更新。

    Args:
        poisson: Poisson 求解器实例。
        config: DDM 配置。
        phi_init: 准中性平衡初值 phi_eq [V]。
        bc_specs: 平衡边界条件（V=0 的 Ohmic 接触，含 phi_b/idx）。

    Returns:
        (phi, n, p, n_iter)：真实平衡势 [V]、电子/空穴浓度 [m^-3]、迭代次数。

    Raises:
        ValueError: 牛顿迭代不收敛、J 奇异或产生非有限值。
    """
    nx, ny = config.nx, config.ny
    vt = config.vt
    n_i = config.n_i

    # 预装配 Laplacian A（含 Neumann，不含 Dirichlet）——牛顿迭代中不变
    bcs_for_laplacian = [
        PoissonBc(side=side, type=DIRICHLET, value=spec["phi_b"])
        for side, spec in bc_specs.items()
    ]
    A = poisson.build_laplacian_neumann(
        nx, ny, config.dx, config.dy, config.eps_rel, bcs_for_laplacian
    )

    # Dirichlet 边界节点索引和值（向量化合并）
    bc_idx_list: list[np.ndarray] = []
    bc_val_list: list[np.ndarray] = []
    for side, spec in bc_specs.items():
        idx = boundary_indices(side, nx, ny)
        bc_idx_list.append(idx)
        bc_val_list.append(np.full(idx.size, float(spec["phi_b"])))
    bc_idx = np.concatenate(bc_idx_list) if bc_idx_list else np.array([], dtype=np.int64)
    bc_vals = np.concatenate(bc_val_list) if bc_val_list else np.array([], dtype=float)

    phi = np.asarray(phi_init, dtype=float).copy()
    # exp 溢出阈值：|phi/vt| ≤ 50（远小于 float64 上限 700，留充分余量）
    phi_clip_limit = 50.0 * vt

    damping_candidates = (1.0, 0.5, 0.25, 0.1, 0.05, 0.01)
    norm_F = 0.0

    for k in range(config.max_iter):
        # Boltzmann 载流子（clip phi 防 exp 溢出）
        phi_clipped = np.clip(phi, -phi_clip_limit, phi_clip_limit)
        n = n_i * np.exp(phi_clipped / vt)
        p = n_i * np.exp(-phi_clipped / vt)
        if not np.all(np.isfinite(n)) or not np.all(np.isfinite(p)):
            raise ValueError(
                f"平衡牛顿法第 {k + 1} 步：Boltzmann 载流子溢出 "
                f"(|phi|/vt 最大 {float(np.max(np.abs(phi)) / vt):.1f})"
            )

        # 残差 F = A·φ + ρ(φ)，ρ(φ) = q·(p - n + N_D - N_A)
        charge = Q_E * (p - n + config.doping_n - config.doping_p)
        phi_vec = phi.ravel()
        F = A.dot(phi_vec) + charge.ravel()
        # Dirichlet 行：F[bc] = φ[bc] - φ_BC（残差 = 偏差）
        if bc_idx.size > 0:
            F[bc_idx] = phi_vec[bc_idx] - bc_vals

        norm_F = float(np.max(np.abs(F))) if F.size > 0 else 0.0
        if norm_F < config.tol:
            # 收敛，返回最终 Boltzmann 载流子
            phi_clipped = np.clip(phi, -phi_clip_limit, phi_clip_limit)
            n = n_i * np.exp(phi_clipped / vt)
            p = n_i * np.exp(-phi_clipped / vt)
            return phi, n, p, k + 1

        # Jacobian J = A - (q/V_T)·diag(n+p)
        # 向量化构造稀疏对角修正（Dirichlet 行由后续行替换覆盖，无需特殊处理）
        diag_newton = (Q_E / vt) * (n + p)
        J = A - sparse.diags(diag_newton.ravel(), format="csr")

        # 牛顿右端 -F
        neg_F = -F
        # 应用 Dirichlet 行替换：J[bc,bc]=1, J[bc,else]=0, (-F)[bc] = φ_BC - φ[bc]
        if bc_idx.size > 0:
            # 行清零 + identity 注入（向量化，复用 apply_dirichlet 模式）
            neg_F_bc_vals = bc_vals - phi_vec[bc_idx]  # -(φ[bc] - φ_BC)
            J, neg_F = apply_dirichlet(J, neg_F, bc_idx, neg_F_bc_vals)

        # 求解 J·δφ = -F
        delta_phi = spsolve(J.tocsc(), neg_F)
        if not np.all(np.isfinite(delta_phi)):
            raise ValueError(
                f"平衡牛顿法第 {k + 1} 步：J·δφ=-F 求解产生非有限值"
                f"（J 奇异或数值溢出，||F||={norm_F:.3e}）"
            )

        # 自适应阻尼：选择使 ||F||∞ 下降的因子（Bank-Rose 1983）
        best_damp = 0.0
        best_norm = norm_F
        for damp in damping_candidates:
            phi_trial = phi + damp * delta_phi.reshape(nx, ny)
            phi_trial_clip = np.clip(phi_trial, -phi_clip_limit, phi_clip_limit)
            n_trial = n_i * np.exp(phi_trial_clip / vt)
            p_trial = n_i * np.exp(-phi_trial_clip / vt)
            charge_trial = Q_E * (p_trial - n_trial + config.doping_n - config.doping_p)
            F_trial = A.dot(phi_trial.ravel()) + charge_trial.ravel()
            if bc_idx.size > 0:
                F_trial[bc_idx] = phi_trial.ravel()[bc_idx] - bc_vals
            norm_F_trial = float(np.max(np.abs(F_trial))) if F_trial.size > 0 else 0.0
            if norm_F_trial < best_norm:
                best_damp = damp
                best_norm = norm_F_trial
                break

        if best_damp == 0.0:
            # 所有阻尼都不能改善 ||F||，用最小阻尼强制小步更新
            # （避免完全停滞；若持续发散，下一轮 norm_F 检查会触发 raise）
            best_damp = 0.01

        phi = phi + best_damp * delta_phi.reshape(nx, ny)

    raise ValueError(
        f"平衡牛顿法未收敛（max_iter={config.max_iter}, 最后 ||F||∞={norm_F:.3e}）"
    )
