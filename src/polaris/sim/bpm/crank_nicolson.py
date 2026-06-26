"""1D Crank-Nicolson 隐式步进（A03 §4.2 公式 F2，θ=0.5，Thomas solve_banded）。

Crank-Nicolson θ 加权隐式格式（A03 §4.2，二阶时间精度、无条件稳定）::

    (ψ^{n+1} - ψ^n)/Δz = (1/a)·[θ·A·ψ^{n+1} + (1-θ)·A·ψ^n]

整理为线性系统（A03 §4.2 公式 F2）::

    [I - θ·Δz/a·A]·ψ^{n+1} = [I + (1-θ)·Δz/a·A]·ψ^n

    即 M_lhs·ψ^{n+1} = rhs，其中
        M_lhs = I - α_lhs·A，α_lhs = θ·Δz/a
        rhs   = (I + α_rhs·A)·ψ^n，α_rhs = (1-θ)·Δz/a

每次 z 步进求解一个三对角线性系统，Thomas 算法 O(N) 复杂度
（scipy.linalg.solve_banded，BLAS 后端）。

无条件稳定性（A03 §4.2，Press Numerical Recipes §20）：
    对自由空间（A 实对称负定，α 纯虚），Crank-Nicolson 推进算子
    U = (I - α·A)^{-1}·(I + α·A) 为酉算子（U^H·U = I），
    故 ||ψ^{n+1}|| = ||ψ^n||，功率严格守恒（M2 验收点）。
    θ=0.5 时为二阶时间精度；θ=1（全隐式 Euler）为一阶但数值耗散更强；
    商业工具默认 θ=0.5（OptiBPM/FIMMPROP）。

主循环结构（A03 §7.1 伪代码，唯一允许的 Python 循环：
z 步进主循环，python代码开发规则.md §4）::

    psi[0] = psi_init
    for n in 0..Nz-1:
        rhs = apply_rhs_operator(A_sparse, psi[n], α_rhs)
        if boundary == TBC:
            kx_L = estimate_kx_left(psi[n], dx)
            kx_R = estimate_kx_right(psi[n], dx)
            lhs = lhs_base.copy()
            apply_tbc_lhs_banded_inplace(lhs, kx_L, kx_R, ...)
            apply_tbc_rhs_inplace(rhs, psi[n], kx_L, kx_R, ...)  # Bug 5 修复
        else:
            lhs = lhs_base
        psi[n+1] = solve_banded((1,1), lhs, rhs)

文献来源（≥5，规则 18 学术诚信）：
1. Hadley 1992 IEEE J Quantum Electron 28(1) 363-370 — TBC + CN-BPM —
   https://doi.org/10.1109/3.119546
2. Hadley 1991 Opt Lett 16 624-626 — TBC 短文版本 —
   https://doi.org/10.1364/OL.16.000624
3. Chung & Dagli 1991 IEEE PTL 3 150-152 — FD-BPM CN 三对角实现 —
   https://doi.org/10.1109/68.84566
4. Hadley 1994 Opt Lett 17 1426-1428 (Padé wide-angle) —
   https://doi.org/10.1364/OL.17.001426
5. Optiwave OptiBPM Boundary Conditions —
   https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
6. RP Photonics Encyclopedia: Numerical Beam Propagation —
   https://www.rp-photonics.com/numerical_beam_propagation.html
7. beampy Python BPM — CN + TBC 开源参考实现 —
   https://beampy.readthedocs.io/en/latest/code_bpm.html

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy+scipy.linalg.solve_banded）
/python代码开发规则.md §4（z 步进主循环为唯一允许循环）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.linalg
import scipy.sparse as sp

from polaris.sim.bpm.boundary import (
    BoundaryType,
    apply_tbc_lhs_banded_inplace,
    apply_tbc_rhs_inplace,
    estimate_kx_left,
    estimate_kx_right,
)
from polaris.sim.bpm.operators import (
    apply_rhs_operator,
    build_lhs_banded,
    sparse_to_banded,
)

__all__ = [
    "CrankNicolsonStepper",
    "crank_nicolson_propagate_1d",
]

# 默认 Crank-Nicolson 权重 θ=0.5（二阶时间精度，A03 §4.2 商业默认）
DEFAULT_THETA = 0.5


@dataclass
class CrankNicolsonStepper:
    """1D Crank-Nicolson 步进器（A03 §4.2 公式 F2，可复用算子缓存）。

    预构造 M_lhs 基底（Dirichlet）与 A_sparse，z 步进中复用：
    - 折射率不变段：M_lhs_base 与 A_sparse 仅构造一次（A03 §8.3 性能策略）
    - TBC 模式：每步 copy 基底 + 修改边界行（避免基底污染）
    - Dirichlet 模式：直接复用基底（零拷贝）

    Attributes:
        a_sparse: 三对角算子 A 的 CSR 稀疏矩阵 (N, N)。
        a_banded: A 的 banded 表示 (3, N)，供 build_lhs_banded 使用。
        lhs_base: M_lhs = I - α_lhs·A 的 Dirichlet 基底 (3, N)。
        alpha_lhs: 复系数 θ·Δz/a。
        alpha_rhs: 复系数 (1-θ)·Δz/a。
        dx: x 方向网格间距。
        boundary: 边界类型（'tbc'/'dirichlet'/'neumann'）。
    """

    a_sparse: sp.csr_matrix
    a_banded: np.ndarray
    lhs_base: np.ndarray
    alpha_lhs: complex
    alpha_rhs: complex
    dx: float
    boundary: str = BoundaryType.TBC

    def __post_init__(self) -> None:
        if self.a_sparse.shape[0] != self.a_sparse.shape[1]:
            raise ValueError(f"a_sparse 须为方阵，实际 shape={self.a_sparse.shape}")
        if self.dx <= 0.0:
            raise ValueError(f"dx 必须为正，实际 {self.dx}")
        if self.boundary not in (
            BoundaryType.TBC,
            BoundaryType.DIRICHLET,
            BoundaryType.NEUMANN,
        ):
            raise ValueError(f"boundary 须为 'tbc'/'dirichlet'/'neumann'，实际 {self.boundary!r}")

    @classmethod
    def from_operator(
        cls,
        a_sparse: sp.csr_matrix,
        dz: float,
        a_coef: complex,
        dx: float,
        theta: float = DEFAULT_THETA,
        boundary: str = BoundaryType.TBC,
    ) -> CrankNicolsonStepper:
        """由稀疏算子构造步进器（预计算 M_lhs 基底与 α 系数）。

        Args:
            a_sparse: 三对角算子 A 的 CSR 矩阵 (N, N)。
            dz: z 方向步长（米）。
            a_coef: SVEA 抛物方程系数 a = 2i·k₀·n_ref（复数）。
            dx: x 方向网格间距（米）。
            theta: CN 权重 θ（默认 0.5，二阶时间精度）。
            boundary: 边界类型。

        Returns:
            CrankNicolsonStepper 实例（含预计算的 lhs_base）。

        Raises:
            ValueError: dz/a_coef/dx 非法（规则 14）。
        """
        if dz <= 0.0:
            raise ValueError(f"dz 必须为正，实际 {dz}")
        if abs(a_coef) < 1e-300:
            raise ValueError(f"a_coef 过小 |a|={abs(a_coef):.2e}（k₀·n_ref 异常？）")
        if not 0.0 <= theta <= 1.0:
            raise ValueError(f"theta 须 ∈ [0, 1]，实际 {theta}")
        a_banded = sparse_to_banded(a_sparse, ku=1, kl=1)
        alpha_lhs = theta * dz / a_coef
        alpha_rhs = (1.0 - theta) * dz / a_coef
        lhs_base = build_lhs_banded(a_banded, alpha_lhs)
        return cls(
            a_sparse=a_sparse,
            a_banded=a_banded,
            lhs_base=lhs_base,
            alpha_lhs=alpha_lhs,
            alpha_rhs=alpha_rhs,
            dx=dx,
            boundary=boundary,
        )

    def step(self, psi: np.ndarray) -> np.ndarray:
        """单步 Crank-Nicolson 推进 ψ^n → ψ^{n+1}（A03 §4.2 公式 F2）。

        Args:
            psi: 当前场 ψ^n (N,)，复数。

        Returns:
            下一步场 ψ^{n+1} (N,)，复数。

        Raises:
            RuntimeError: solve_banded 求解失败（奇异矩阵，规则 14）。
            ValueError: TBC 估计退化（边界场过小）。
        """
        psi_c = np.asarray(psi, dtype=np.complex128)
        if psi_c.shape != (self.a_sparse.shape[0],):
            raise ValueError(
                f"psi 形状 {psi_c.shape} 与算子维度 ({self.a_sparse.shape[0]},) 不匹配"
            )
        # 右端：rhs = (I + α_rhs·A)·ψ^n（稀疏 matvec，向量化）
        rhs = apply_rhs_operator(self.a_sparse, psi_c, self.alpha_rhs)
        # 左侧矩阵准备
        if self.boundary == BoundaryType.TBC:
            # TBC 模式：每步重估 kx + copy 基底 + 修改边界行
            kx_left = estimate_kx_left(psi_c, self.dx)
            kx_right = estimate_kx_right(psi_c, self.dx)
            lhs = self.lhs_base.copy()
            inv_dx2 = 1.0 / (self.dx * self.dx)
            apply_tbc_lhs_banded_inplace(lhs, kx_left, kx_right, self.dx, self.alpha_lhs, inv_dx2)
            # RHS TBC 修改（Bug 5 修复）：右端也须用 TBC 修改的算子，
            # 否则基底（Dirichlet）与 LHS 不一致，平面波也产生 ~0.96 反射
            apply_tbc_rhs_inplace(rhs, psi_c, kx_left, kx_right, self.dx, self.alpha_rhs, inv_dx2)
        else:
            # Dirichlet/Neumann：直接复用基底（零拷贝）
            lhs = self.lhs_base
        # Thomas 算法求解三对角系统（scipy.linalg.solve_banded，O(N)，BLAS 后端）
        try:
            psi_next = scipy.linalg.solve_banded((1, 1), lhs, rhs)
        except np.linalg.LinAlgError as exc:
            raise RuntimeError(
                f"Crank-Nicolson 三对角求解失败：{exc}（检查 M_lhs 是否奇异）"
            ) from exc
        return psi_next


def crank_nicolson_propagate_1d(
    psi_init: np.ndarray,
    a_sparse: sp.csr_matrix,
    dz: float,
    nz: int,
    a_coef: complex,
    dx: float,
    theta: float = DEFAULT_THETA,
    boundary: str = BoundaryType.TBC,
    store_interval: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """1D Crank-Nicolson 主循环（A03 §7.1 伪代码）。

    Args:
        psi_init: 初始场 ψ(z=0) (N,)，复数。
        a_sparse: 三对角算子 A 的 CSR 矩阵 (N, N)。
        dz: z 方向步长（米）。
        nz: z 方向步数，必须 ≥1。
        a_coef: SVEA 抛物方程系数 a = 2i·k₀·n_ref。
        dx: x 方向网格间距（米）。
        theta: CN 权重（默认 0.5）。
        boundary: 边界类型（默认 'tbc'）。
        store_interval: 快照存储间隔（每 store_interval 步存一次，
            store_interval=1 表示每步存，store_interval≥nz 表示仅存首末）。

    Returns:
        (snapshots, z_coords):
            snapshots: (N_snapshots, N) 复数场快照，
                N_snapshots = nz // store_interval + 1（含初始场）。
            z_coords: (N_snapshots,) 对应的 z 坐标（米）。

    Raises:
        ValueError: 输入非法（规则 14）。
        RuntimeError: 求解发散或 TBC 退化。

    算法复杂度：O(nz · N)（每步 Thomas O(N) + TBC O(1)）。
    """
    psi_init_c = np.asarray(psi_init, dtype=np.complex128)
    if psi_init_c.ndim != 1:
        raise ValueError(f"psi_init 须为 1D，实际 {psi_init_c.ndim}D")
    if psi_init_c.shape != (a_sparse.shape[0],):
        raise ValueError(f"psi_init 长度 {psi_init_c.size} 与算子维度 {a_sparse.shape[0]} 不匹配")
    if nz < 1:
        raise ValueError(f"nz 须 ≥1，实际 {nz}")
    if store_interval < 1:
        raise ValueError(f"store_interval 须 ≥1，实际 {store_interval}")

    stepper = CrankNicolsonStepper.from_operator(
        a_sparse=a_sparse, dz=dz, a_coef=a_coef, dx=dx, theta=theta, boundary=boundary
    )
    # 快照索引：0, store_interval, 2*store_interval, ..., nz（含末步）
    n_snapshots = nz // store_interval + 1
    snapshots = np.empty((n_snapshots, psi_init_c.size), dtype=np.complex128)
    z_coords = np.empty(n_snapshots, dtype=np.float64)
    snapshots[0] = psi_init_c
    z_coords[0] = 0.0

    psi = psi_init_c.copy()
    snap_idx = 1
    # z 步进主循环（python代码开发规则.md §4 唯一允许循环）
    for n in range(nz):
        psi = stepper.step(psi)
        z_now = (n + 1) * dz
        if (n + 1) % store_interval == 0:
            if snap_idx >= n_snapshots:
                break
            snapshots[snap_idx] = psi
            z_coords[snap_idx] = z_now
            snap_idx += 1
    # 末步兜底（store_interval 不整除 nz 时也存末步）
    if snap_idx < n_snapshots:
        snapshots[snap_idx] = psi
        z_coords[snap_idx] = nz * dz
        snap_idx += 1
    return snapshots[:snap_idx], z_coords[:snap_idx]
