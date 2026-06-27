"""连续性方程 SG 离散求解器（A08-DDM §连续性）。

R01 方案检索记录（规则 1）：
- 关键词：semiconductor continuity equation Scharfetter-Gummel SRH recombination
- 采用方案：经典 Gummel 解耦迭代 + SG 边系数 + SRH 复合视作常数源
  （Selberherr 1984 §5.2；Vasileska lecture notes；Gummel 1964）。
- 来源：Selberherr 1984；Scharfetter-Gummel 1969；Shockley-Read-Hall 1952。

实现稳态电子/空穴连续性方程（Selberherr 1984 §2；Sze 2006 §2）：
    (1/q)·∇·J_n = R       (电子，R 为净复合率)
    -(1/q)·∇·J_p = R      (空穴)
其中 R 为 SRH 复合率 [1/(m³·s)]。

漂移扩散电流密度（SG 离散形式，Selberherr 1984 §5.2 eq 5.2.6/5.2.7）：
    J_{n,i+1/2} = (q·D_n/dx)·[B(δ)·n_{i+1} - B(-δ)·n_i]
    J_{p,i+1/2} = (q·D_p/dx)·[B(-δ)·p_{i+1} - B(δ)·p_i]
其中 δ = (φ_{i+1} - φ_i)/V_T，B(x) = x/(e^x-1) 为 Bernoulli 函数，
D_n = μ_n·V_T，D_p = μ_p·V_T（Einstein 关系，300K 硅 V_T ≈ 0.0259 V）。
平衡态检验：n_{i+1}=n_i·exp(δ)，利用恒等式 B(-δ)=exp(δ)·B(δ) 得
J_n = (q·D_n/dx)·n_i·[B(δ)·exp(δ) - exp(δ)·B(δ)] = 0 ✓（零电流）。

矩阵装配推导（电子，节点 i 离散 ∇·J_n/q = R）：
    (D_n/dx²)·[B(δ_+)·n_{i+1} - (B(-δ_+) + B(δ_-))·n_i + B(-δ_-)·n_{i-1}] = R_i
矩阵 A_n @ n = R（A 负定，对角负、邻接正，行和为零）：
    A[i, i+1] = +(D_n/dx²)·B(δ)
    A[i+1, i] = +(D_n/dx²)·B(-δ)
    A[i, i]   = -(D_n/dx²)·(B(-δ_+) + B(δ_-))

空穴连续性 -(1/q)·∇·J_p = R → A_p @ p = R（A_p 正定，对角正、邻接负）：
    A[i, i+1] = -(D_p/dx²)·B(-δ)
    A[i+1, i] = -(D_p/dx²)·B(δ)
    A[i, i]   = +(D_p/dx²)·(B(δ_+) + B(-δ_-))
注意：空穴邻接系数取负号（因 -(1/q)·∇·J_p = R 中负号翻转），对角取正号。

Gummel 迭代策略（Selberherr 1984 §6；Gummel 1964）：
- 求电子时把 R 视为常数源（用上一步 n_old, p_old 计算 R）
- 求空穴时把 R 视为常数源（用最新 n_new, 上一步 p_old 计算 R）
- 多次 Gummel 迭代收敛到自洽解（线性收敛，Bank-Rose 1983 收敛理论）

SRH 复合率（Shockley-Read-Hall 1952；Hall 1952）：
    R = (n·p - n_i²) / (τ_p·(n + n_1) + τ_n·(p + p_1))
其中 n_1 = n_i·exp((E_t - E_i)/kT)，p_1 = n_i·exp(-(E_t - E_i)/kT)。
深能级陷阱（E_t = E_i）下 n_1 = p_1 = n_i，简化为：
    R = (n·p - n_i²) / (τ_p·(n + n_i) + τ_n·(p + n_i))

向量化装配：每条内部边 (i, i+1) 同时贡献 A[i,i+1]、A[i+1,i] 和两端对角
（np.add.at 处理重复索引）。禁止逐元素循环（规则：向量化）。
边界节点 Dirichlet 由 solver.py 行替换注入，本模块只装配内部矩阵。

文献来源（≥5，规则 18 学术诚信）：
1. Scharfetter & Gummel 1969 IEEE Trans ED 16(1):64-77 —
   https://doi.org/10.1109/T-ED.1969.16766
2. Selberherr 1984 "Analysis and Simulation of Semiconductor Devices" —
   https://link.springer.com/book/10.1007/978-3-7091-8753-2
3. Shockley & Read 1952 Phys Rev 87:835-842 —
   https://doi.org/10.1103/PhysRev.87.835
4. Hall 1952 Phys Rev 87:387 —
   https://doi.org/10.1103/PhysRev.87.387
5. Gummel 1964 Bell System Tech J 43(3):817-920 —
   https://doi.org/10.1002/j.1538-7305.1964.tb04100.x
6. Vasileska 2008 Lecture Notes "DDM and Gummel Iteration" —
   https://nanohub.org/resources/19636
7. Lundstrom 2000 "Fundamentals of Carrier Transport" —
   https://www.cambridge.org/core/books/fundamentals-of-carrier-transport/

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from polaris.sim.ddm.scharfetter_gummel import (
    K_B,
    MU_N_SI,
    MU_P_SI,
    N_I_SI,
    Q_E,
    T_DEFAULT,
    TAU_N_SRH,
    TAU_P_SRH,
    bernoulli_pair,
)

__all__ = [
    "ContinuitySolver",
    "ContinuityBc",
    "DIRICHLET",
    "NEUMANN",
    "srh_recombination",
    "srh_derivatives",
]

DIRICHLET = "dirichlet"
NEUMANN = "neumann"


@dataclass
class ContinuityBc:
    """连续性方程边界条件规格。

    Attributes:
        side: 方向 'west'|'east'|'south'|'north'。
        type: DIRICHLET 或 NEUMANN。
        value: Dirichlet 时为载流子浓度 [m^-3]；Neumann 时为 ∂n/∂n [m^-4]。
    """

    side: str
    type: str
    value: float = 0.0

    def __post_init__(self) -> None:
        if self.side not in ("west", "east", "south", "north"):
            raise ValueError(f"未知边界方向 {self.side}")
        if self.type not in (DIRICHLET, NEUMANN):
            raise ValueError(f"未知边界类型 {self.type}（须 dirichlet/neumann）")


def srh_recombination(
    n: np.ndarray,
    p: np.ndarray,
    n_i: float = N_I_SI,
    tau_n: float = TAU_N_SRH,
    tau_p: float = TAU_P_SRH,
) -> np.ndarray:
    """SRH 复合率 R = (n·p - n_i²)/(τ_p·(n+n_i) + τ_n·(p+n_i))。

    深能级陷阱假设（E_t = E_i），n_1 = p_1 = n_i（Shockley-Read 1952）。
    R > 0 表示净复合（n·p > n_i²），R < 0 表示净产生（n·p < n_i²）。

    Args:
        n: 电子浓度场 [m^-3]，非负有限值。
        p: 空穴浓度场 [m^-3]，非负有限值。
        n_i: 本征载流子浓度 [m^-3]。
        tau_n, tau_p: SRH 电子/空穴寿命 [s]。

    Returns:
        与输入同形状的 SRH 复合率 [1/(m³·s)]，全为有限值。

    Raises:
        ValueError: 输入非有限、负值或参数非法。
    """
    n_arr = np.asarray(n, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    if not np.all(np.isfinite(n_arr)) or np.any(n_arr < 0.0):
        raise ValueError("n 须全为非负有限值（载流子浓度物理约束）")
    if not np.all(np.isfinite(p_arr)) or np.any(p_arr < 0.0):
        raise ValueError("p 须全为非负有限值（载流子浓度物理约束）")
    if n_i <= 0.0 or tau_n <= 0.0 or tau_p <= 0.0:
        raise ValueError("n_i/tau_n/tau_p 须 > 0")
    denom = tau_p * (n_arr + n_i) + tau_n * (p_arr + n_i)
    if np.any(denom <= 0.0):
        raise ValueError("SRH 分母须 > 0（参数非法）")
    return (n_arr * p_arr - n_i**2) / denom


def srh_derivatives(
    n: np.ndarray,
    p: np.ndarray,
    n_i: float = N_I_SI,
    tau_n: float = TAU_N_SRH,
    tau_p: float = TAU_P_SRH,
) -> tuple[np.ndarray, np.ndarray]:
    """SRH 复合率对 n、p 的偏导数（牛顿法 Jacobian 用）。

    R = (n·p - n_i²) / D，D = τ_p·(n + n_i) + τ_n·(p + n_i)
    令 N = n·p - n_i²：
        ∂R/∂n = (p·D - N·τ_p) / D²
        ∂R/∂p = (n·D - N·τ_n) / D²

    Args:
        n: 电子浓度场 [m^-3]，非负有限值。
        p: 空穴浓度场 [m^-3]，非负有限值。
        n_i: 本征载流子浓度 [m^-3]。
        tau_n, tau_p: SRH 电子/空穴寿命 [s]。

    Returns:
        (dR_dn, dR_dp)：与输入同形状，全为有限值。

    Raises:
        ValueError: 输入非法。
    """
    n_arr = np.asarray(n, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    if not np.all(np.isfinite(n_arr)) or np.any(n_arr < 0.0):
        raise ValueError("n 须全为非负有限值（载流子浓度物理约束）")
    if not np.all(np.isfinite(p_arr)) or np.any(p_arr < 0.0):
        raise ValueError("p 须全为非负有限值（载流子浓度物理约束）")
    if n_i <= 0.0 or tau_n <= 0.0 or tau_p <= 0.0:
        raise ValueError("n_i/tau_n/tau_p 须 > 0")
    prod_np = n_arr * p_arr - n_i**2
    denom = tau_p * (n_arr + n_i) + tau_n * (p_arr + n_i)
    if np.any(denom <= 0.0):
        raise ValueError("SRH 分母须 > 0（参数非法）")
    dR_dn = (p_arr * denom - prod_np * tau_p) / denom**2
    dR_dp = (n_arr * denom - prod_np * tau_n) / denom**2
    return dR_dn, dR_dp


def _add_sg_face(
    phi: np.ndarray,
    ny: int,
    coef: float,
    is_x: bool,
    is_electron: bool,
    rows_l: list[np.ndarray],
    cols_l: list[np.ndarray],
    vals_l: list[np.ndarray],
    center: np.ndarray,
    vt: float,
) -> None:
    """添加一个方向（x 或 y）的所有 SG 内部边贡献（向量化）。

    每条内部边 (i, i+1) 同时贡献：
    - A[i, i+1]（节点 i 的右/上邻）
    - A[i+1, i]（节点 i+1 的左/下邻）
    - center[i] += c0（节点 i 对角贡献）
    - center[i+1] += c1（节点 i+1 对角贡献）
    最终对角 = ±center（电子 -, 空穴 +）由调用方设定符号。

    Args:
        phi: 静电势场 (nx, ny) [V]。
        ny: y 方向节点数（用于线性索引 k = i·ny + j）。
        coef: D/d²，扩散系数除以间距平方。
        is_x: True 处理 x 方向边，False 处理 y 方向边。
        is_electron: True 电子（A 负定），False 空穴（A 正定）。
        rows_l, cols_l, vals_l: COO 三元组累加列表。
        center: 对角累加数组（in-place 修改）。
        vt: 热电势 V_T = k_B·T/q [V]。
    """
    if is_x:
        nx = phi.shape[0]
        delta = (phi[1:, :] - phi[:-1, :]) / vt  # (nx-1, ny)
        n_edge = nx - 1
        I, J = np.meshgrid(np.arange(n_edge), np.arange(ny), indexing="ij")  # noqa: E741  矩阵行索引
        r0 = (I * ny + J).ravel()
        r1 = ((I + 1) * ny + J).ravel()
    else:
        ny_arr = phi.shape[1]
        delta = (phi[:, 1:] - phi[:, :-1]) / vt  # (nx, ny-1)
        n_edge = ny_arr - 1
        I, J = np.meshgrid(np.arange(phi.shape[0]), np.arange(n_edge), indexing="ij")  # noqa: E741  矩阵行索引
        r0 = (I * ny + J).ravel()
        r1 = (I * ny + (J + 1)).ravel()

    B_pos, B_neg = bernoulli_pair(delta)
    B_pos = B_pos.ravel()
    B_neg = B_neg.ravel()

    if is_electron:
        # 电子（Selberherr 1984 §5.2 eq 5.2.6）：
        # A[i,i+1]=+coef·B(δ), A[i+1,i]=+coef·B(-δ)
        v01 = coef * B_pos
        v10 = coef * B_neg
        # center[i]+=coef·B(-δ)（右邻边贡献），center[i+1]+=coef·B(δ)，对角=-center
        c0 = coef * B_neg
        c1 = coef * B_pos
    else:  # hole
        # 空穴（Selberherr 1984 §5.2 eq 5.2.7，-(1/q)·∇·J_p = R 翻转符号）：
        # A[i,i+1]=-coef·B(-δ), A[i+1,i]=-coef·B(δ)
        v01 = -coef * B_neg
        v10 = -coef * B_pos
        # center[i]+=coef·B(δ)（右邻边贡献），center[i+1]+=coef·B(-δ)，对角=+center
        c0 = coef * B_pos
        c1 = coef * B_neg

    rows_l.append(np.asarray(r0, dtype=np.int64))
    cols_l.append(np.asarray(r1, dtype=np.int64))
    vals_l.append(np.asarray(v01, dtype=float))
    rows_l.append(np.asarray(r1, dtype=np.int64))
    cols_l.append(np.asarray(r0, dtype=np.int64))
    vals_l.append(np.asarray(v10, dtype=float))
    np.add.at(center, r0, c0)
    np.add.at(center, r1, c1)


class ContinuitySolver:
    """连续性方程 SG 离散求解器（Gummel 解耦迭代中的一步）。

    装配 SG 离散的内部矩阵（不含边界节点处理）。
    边界节点 Dirichlet 由 solver.py 行替换注入。

    用法：
        cs = ContinuitySolver(nx, ny, dx, dy)
        A_n, b_n = cs.electron_system(phi, n_old, p_old)
        # solver.py 应用 Dirichlet 行替换后 spsolve
    """

    def __init__(
        self,
        nx: int,
        ny: int,
        dx: float,
        dy: float,
        mu_n: float = MU_N_SI,
        mu_p: float = MU_P_SI,
        tau_n: float = TAU_N_SRH,
        tau_p: float = TAU_P_SRH,
        n_i: float = N_I_SI,
        temperature: float = T_DEFAULT,
    ) -> None:
        if nx < 1 or ny < 1:
            raise ValueError(f"网格须 ≥1，实际 ({nx},{ny})")
        if dx <= 0.0 or dy <= 0.0:
            raise ValueError(f"dx/dy 须 > 0，实际 dx={dx} dy={dy}")
        if mu_n <= 0.0 or mu_p <= 0.0:
            raise ValueError("迁移率须 > 0")
        if tau_n <= 0.0 or tau_p <= 0.0:
            raise ValueError("SRH 寿命须 > 0")
        if n_i <= 0.0:
            raise ValueError("本征浓度须 > 0")
        if temperature <= 0.0:
            raise ValueError("温度须 > 0")

        self.nx = nx
        self.ny = ny
        self.dx = dx
        self.dy = dy
        self.mu_n = mu_n
        self.mu_p = mu_p
        self.tau_n = tau_n
        self.tau_p = tau_p
        self.n_i = n_i
        self.temperature = temperature
        # Einstein 关系 D = μ·V_T，V_T = k_B·T/q（CODATA 2018）
        self.vt = K_B * temperature / Q_E
        self.D_n = mu_n * self.vt
        self.D_p = mu_p * self.vt

    def electron_system(
        self,
        phi: np.ndarray,
        n_old: np.ndarray,
        p_old: np.ndarray,
    ) -> tuple[sparse.csr_matrix, np.ndarray]:
        """返回电子连续性方程 SG 离散线性系统 (A, b)。

        方程：(1/q)·∇·J_n = R(n_old, p_old)，R 视为常数源。
        A 负定（对角负、邻接正），右端 b = +R。

        Args:
            phi: 当前静电势 (nx,ny) [V]。
            n_old: 上一步电子浓度 (nx,ny) [m^-3]。
            p_old: 上一步空穴浓度 (nx,ny) [m^-3]。

        Returns:
            (A, b)：A 为 CSR 稀疏矩阵 (nx*ny, nx*ny)，b 为右端 (nx*ny,)。
        """
        return self._build_system(phi, n_old, p_old, "electron")

    def hole_system(
        self,
        phi: np.ndarray,
        n_new: np.ndarray,
        p_old: np.ndarray,
    ) -> tuple[sparse.csr_matrix, np.ndarray]:
        """返回空穴连续性方程 SG 离散线性系统 (A, b)。

        方程：-(1/q)·∇·J_p = R(n_new, p_old)，R 视为常数源。
        A 负定（对角负、邻接正），右端 b = +R（同电子，因空穴方程已含负号翻转）。

        Args:
            phi: 当前静电势 (nx,ny) [V]。
            n_new: 最新电子浓度 (nx,ny) [m^-3]（Gummel 顺序耦合）。
            p_old: 上一步空穴浓度 (nx,ny) [m^-3]。

        Returns:
            (A, b)：A 为 CSR 稀疏矩阵 (nx*ny, nx*ny)，b 为右端 (nx*ny,)。
        """
        return self._build_system(phi, n_new, p_old, "hole")

    def _build_system(
        self,
        phi: np.ndarray,
        n: np.ndarray,
        p: np.ndarray,
        carrier: str,
    ) -> tuple[sparse.csr_matrix, np.ndarray]:
        """SG 离散核心装配。

        装配内部 5 点差分 SG 矩阵（不含边界处理）。边界节点由 solver.py
        行替换注入 Dirichlet（Ohmic 接触），未指定方向视为自然 Neumann。
        """
        nx, ny = self.nx, self.ny
        n_total = nx * ny
        phi_arr = np.asarray(phi, dtype=float)
        if phi_arr.shape != (nx, ny):
            raise ValueError(f"phi 形状 {phi_arr.shape} ≠ ({nx},{ny})")
        if not np.all(np.isfinite(phi_arr)):
            raise ValueError("phi 含非有限值（NaN/Inf）")

        R = srh_recombination(n, p, self.n_i, self.tau_n, self.tau_p)
        if R.shape != (nx, ny):
            raise ValueError(f"R 形状 {R.shape} ≠ ({nx},{ny})")

        if carrier == "electron":
            D = self.D_n
            sgn_diag = -1.0
            sgn_R = +1.0
        elif carrier == "hole":
            D = self.D_p
            sgn_diag = +1.0
            sgn_R = +1.0
        else:
            raise ValueError(f"未知载流子类型 {carrier}（须 electron/hole）")

        rows_l: list[np.ndarray] = []
        cols_l: list[np.ndarray] = []
        vals_l: list[np.ndarray] = []
        center = np.zeros(n_total, dtype=float)

        if nx >= 2:
            _add_sg_face(
                phi_arr,
                ny,
                D / self.dx**2,
                is_x=True,
                is_electron=(carrier == "electron"),
                rows_l=rows_l,
                cols_l=cols_l,
                vals_l=vals_l,
                center=center,
                vt=self.vt,
            )
        if ny >= 2:
            _add_sg_face(
                phi_arr,
                ny,
                D / self.dy**2,
                is_x=False,
                is_electron=(carrier == "electron"),
                rows_l=rows_l,
                cols_l=cols_l,
                vals_l=vals_l,
                center=center,
                vt=self.vt,
            )

        all_idx = np.arange(n_total, dtype=np.int64)
        rows_l.append(all_idx)
        cols_l.append(all_idx)
        vals_l.append(sgn_diag * center)

        b = sgn_R * R.ravel().astype(float, copy=True)

        rows = np.concatenate(rows_l)
        cols = np.concatenate(cols_l)
        vals = np.concatenate(vals_l)
        A = sparse.csr_matrix((vals, (rows, cols)), shape=(n_total, n_total))
        return A, b
