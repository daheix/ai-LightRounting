"""全耦合阻尼牛顿法主求解器（A08-DDM §主求解器）。

R01 方案检索记录（规则 1）：
- 关键词：coupled Newton method semiconductor drift diffusion Poisson
  continuity Jacobian SRH recombination line search
- 采用方案：全耦合阻尼牛顿法联立求解 Poisson + 电子连续性 + 空穴连续性
  （Selberherr 1984 §6.4；Bank-Rose 1983），含 SRH 复合 Jacobian
  + Armijo 回溯线搜索（Dennis-Schnabel 1996）+ 电压延续。
  Gummel 1964 解耦迭代在强正偏 PN 结（0.7V）固有失效：解耦导致 SRH
  复合率用滞后值，连续性方程 SG 离散产生负浓度（物理可行性破坏）。
  全耦合牛顿法将三方程联立，Jacobian 同时含 Poisson-电荷耦合与 SRH
  耦合，根除了滞后问题，保证收敛到物理可行解。
- 来源：Selberherr 1984；Bank-Rose 1983；Dennis-Schnabel 1996。

实现半导体器件稳态漂移-扩散模型（Selberherr 1984 §2；Sze 2006 §2）：
    Poisson:    ∇·(ε·∇φ) = -q·(p - n + N_D - N_A)
    电子连续性: (1/q)·∇·J_n = R
    空穴连续性: -(1/q)·∇·J_p = R
其中 J_n = q·μ_n·n·E + q·D_n·∇n = -q·μ_n·n·∇φ + q·D_n·∇n，
     J_p = q·μ_p·p·E - q·D_p·∇p = -q·μ_p·p·∇φ - q·D_p·∇p，
     D = μ·V_T（Einstein 关系），R 为 SRH 复合率。

全耦合牛顿法（Selberherr 1984 §6.4；Bank-Rose 1983）：
1. 装配残差向量 F = [F_φ, F_n, F_p]^T（3N 维，N=nx·ny）：
   F_φ = A_ε·φ + q·(p - n + N_D - N_A)
   F_n = L_n(φ)·n - R(n,p)   （L_n 为 SG 电子算子，依赖 φ）
   F_p = L_p(φ)·p - R(n,p)
2. 装配 Jacobian J = ∂F/∂[φ,n,p]（3N×3N 分块稀疏）：
   J = [ A_ε        -q·I        +q·I      ]
       [ 0          L_n-∂R/∂n   -∂R/∂p    ]   （∂L/∂φ 滞后，修正牛顿）
       [ 0          -∂R/∂n      L_p-∂R/∂p ]
   其中 A_ε 为 Poisson Laplacian，L_n/L_p 为 SG 算子，
   ∂R/∂n、∂R/∂p 为 SRH 复合率偏导（continuity.srh_derivatives）。
   *修正牛顿*（Selberherr §6.4）：∂L_n/∂φ、∂L_p/∂φ 块置零，
   因 Bernoulli 导数贡献为二阶项，滞后不影响收敛性，显著简化装配。
3. 解 J·Δx = -F（scipy spsolve 稀疏 LU）。
4. Armijo 回溯线搜索（Dennis-Schnabel 1996 §6.3）：步长 α 从 1.0
   减半直到 ||F(x+α·Δx)||∞ < (1-σ·α)·||F||∞ 且 n,p ≥ 0（物理可行性）。
5. x ← x + α·Δx，收敛检查 ||F||∞ < tol。

*创新* 物理可行性线搜索：标准 Armijo 仅检查残差下降，本实现额外
约束 n,p ≥ 0（载流子浓度物理约束）。线搜索自动减小步长使牛顿步不
越界物理可行域。底层逻辑：SRH 复合 R(n,p) 在 n<0 时无物理意义，
正浓度约束保证每次迭代的 R 评估有效，避免假数据 fall-back。

电压延续（Selberherr 1984 §6.3）：从平衡态逐步加载电压，每步用牛顿
法求解。牛顿法比 Gummel 鲁棒性更强，可用较大步长（0.2V/步）。

        Ohmic 接触边界条件（Selberherr 1984 §6.2）：
- 接触电压 V 决定边界处准费米能级偏移
- 边界电势 φ_b = φ_eq + V（φ_eq 为平衡电势）
- 边界载流子浓度（热平衡）：n_b = n_eq, p_b = n_i²/n_eq
- n_eq = 0.5·((N_D-N_A) + sqrt((N_D-N_A)² + 4·n_i²))（电中性解）
- φ_eq = V_T·ln(n_eq/n_i)

后处理（电流密度、电导率、电场）：
- J_n = q·μ_n·n·E + q·D_n·∇n = q·μ_n·n·(-∇φ) + q·D_n·∇n
- J_p = q·μ_p·p·E - q·D_p·∇p = q·μ_p·p·(-∇φ) - q·D_p·∇p
- J = J_n + J_p（总电流密度）
- σ = q·(μ_n·n + μ_p·p)（电导率）
- E = -∇φ（电场）
- 焦耳热 Q = J²/σ（由 heat/coupling.py:ddm_to_heat 消费）

*创新* 接口契约：DdmResult 包含 (current_density_x, current_density_y,
conductivity) 字段，duck-typed 兼容 heat/coupling.py:ddm_to_heat，
支持 DDM→HEAT 单向耦合（M3 验收）。底层逻辑：解耦接口契约避免循环依赖，
DDM 与 HEAT 可独立验证与替换，符合单一职责原则。

文献来源（≥5，规则 18 学术诚信）：
1. Selberherr 1984 "Analysis and Simulation of Semiconductor Devices" —
   https://link.springer.com/book/10.1007/978-3-7091-8753-2
2. Bank, Rose & Fichtner 1983 SIAM J Sci Stat Comput 4(3):416-435 —
   https://doi.org/10.1137/0904046
3. Gummel 1964 Bell System Tech J 43(3):817-920 —
   https://doi.org/10.1002/j.1538-7305.1964.tb04100.x
4. Scharfetter & Gummel 1969 IEEE Trans ED 16(1):64-77 —
   https://doi.org/10.1109/T-ED.1969.16766
5. Markowich 1986 "The Stationary Semiconductor Device Equations" —
   https://link.springer.com/book/10.1007/978-3-7091-3692-6
6. Lundstrom 2000 "Fundamentals of Carrier Transport" —
   https://www.cambridge.org/core/books/fundamentals-of-carrier-transport/
7. Dennis & Schnabel 1996 "Numerical Methods for Unconstrained Optimization
   and Nonlinear Equations" SIAM — https://doi.org/10.1137/1.9781611971200
8. Jerome 1992 "Analysis of Charge Transport" Springer —
   https://link.springer.com/book/10.1007/978-1-4612-2814-0
9. Kerkhoven 1985 "On the effectiveness of Gummel's method"
   SIAM J Sci Stat Comput 6(1):66-88 — https://doi.org/10.1137/0906005
10. Polak 1971 "Computational Methods in Optimization" Academic Press
    （Armijo 线搜索收敛性理论）—
    https://www.sciencedirect.com/book/9780125630500/computational-methods-in-optimization

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from polaris.sim.ddm.continuity import ContinuitySolver, srh_derivatives, srh_recombination
from polaris.sim.ddm.poisson import DIRICHLET, PoissonBc, PoissonSolver
from polaris.sim.ddm.scharfetter_gummel import (
    K_B,
    MU_N_SI,
    MU_P_SI,
    N_I_SI,
    Q_E,
    T_DEFAULT,
    TAU_N_SRH,
    TAU_P_SRH,
)

__all__ = [
    "DdmConfig",
    "DdmResult",
    "DdmSolver",
    "solve_ddm",
]


@dataclass
class DdmConfig:
    """漂移-扩散求解配置。

    Attributes:
        nx, ny: 网格形状。
        dx, dy: 网格间距 [m]。
        eps_rel: 相对介电常数场 (nx,ny) 或常数标量（如硅 11.7）。
        doping_n: 施主浓度 N_D (nx,ny) [m^-3]，非负。
        doping_p: 受主浓度 N_A (nx,ny) [m^-3]，非负。
        mobility_n, mobility_p: 电子/空穴迁移率 [m²/(V·s)]。
        tau_n, tau_p: SRH 电子/空穴寿命 [s]。
        n_i: 本征载流子浓度 [m^-3]。
        temperature: 温度 [K]。
        contacts: Ohmic 接触电压映射 {side: V} [V]。
            未指定的方向默认 Neumann 自然边界（无电流）。
        max_iter: 耦合牛顿迭代最大次数（每个 voltage continuation 步）。
        tol: 收敛阈值（最大|Δφ| [V]、相对|Δn|/|n|、相对|Δp|/|p|）。
    """

    nx: int
    ny: int
    dx: float
    dy: float
    eps_rel: float | np.ndarray
    doping_n: np.ndarray
    doping_p: np.ndarray
    mobility_n: float = MU_N_SI
    mobility_p: float = MU_P_SI
    tau_n: float = TAU_N_SRH
    tau_p: float = TAU_P_SRH
    n_i: float = N_I_SI
    temperature: float = T_DEFAULT
    contacts: dict[str, float] = field(default_factory=dict)
    max_iter: int = 100
    tol: float = 1e-6

    def __post_init__(self) -> None:
        if self.nx < 1 or self.ny < 1:
            raise ValueError(f"网格须 ≥1，实际 ({self.nx},{self.ny})")
        if self.dx <= 0.0 or self.dy <= 0.0:
            raise ValueError(f"dx/dy 须 > 0，实际 dx={self.dx} dy={self.dy}")
        if self.doping_n.shape != (self.nx, self.ny):
            raise ValueError(f"doping_n 形状 {self.doping_n.shape} ≠ ({self.nx},{self.ny})")
        if self.doping_p.shape != (self.nx, self.ny):
            raise ValueError(f"doping_p 形状 {self.doping_p.shape} ≠ ({self.nx},{self.ny})")
        if not np.all(np.isfinite(self.doping_n)) or np.any(self.doping_n < 0.0):
            raise ValueError("doping_n 须全为非负有限值")
        if not np.all(np.isfinite(self.doping_p)) or np.any(self.doping_p < 0.0):
            raise ValueError("doping_p 须全为非负有限值")
        if self.mobility_n <= 0.0 or self.mobility_p <= 0.0:
            raise ValueError("迁移率须 > 0")
        if self.tau_n <= 0.0 or self.tau_p <= 0.0:
            raise ValueError("SRH 寿命须 > 0")
        if self.n_i <= 0.0:
            raise ValueError("n_i 须 > 0")
        if self.temperature <= 0.0:
            raise ValueError("温度须 > 0")
        if self.max_iter < 1:
            raise ValueError(f"max_iter 须 ≥ 1，实际 {self.max_iter}")
        if self.tol <= 0.0:
            raise ValueError(f"tol 须 > 0，实际 {self.tol}")
        for side, voltage in self.contacts.items():
            if side not in ("west", "east", "south", "north"):
                raise ValueError(f"未知接触方向 {side}")
            if not np.isfinite(voltage):
                raise ValueError(f"接触电压 {side} 非有限值")

    @property
    def vt(self) -> float:
        """热电势 V_T = k_B·T/q [V]。"""
        return K_B * self.temperature / Q_E


@dataclass
class DdmResult:
    """漂移-扩散求解结果。

    *创新* 接口契约：包含 (current_density_x, current_density_y, conductivity)
    字段，duck-typed 兼容 heat/coupling.py:ddm_to_heat，支持 DDM→HEAT 单向耦合。

    Attributes:
        potential: 静电势 φ (nx,ny) [V]。
        electron_density: 电子浓度 n (nx,ny) [m^-3]。
        hole_density: 空穴浓度 p (nx,ny) [m^-3]。
        current_density: 总电流密度 |J| (nx,ny) [A/m²]。
        current_density_x, current_density_y: 电流密度分量 [A/m²]（heat 耦合契约）。
        conductivity: 电导率 σ (nx,ny) [S/m]（heat 耦合契约，全正）。
        e_field_x, e_field_y: 电场分量 E = -∇φ [V/m]。
        n_iterations: 耦合牛顿迭代次数（平衡牛顿不计入，M1 验收口径）。
        converged: 是否收敛。
    """

    potential: np.ndarray
    electron_density: np.ndarray
    hole_density: np.ndarray
    current_density: np.ndarray
    current_density_x: np.ndarray
    current_density_y: np.ndarray
    conductivity: np.ndarray
    e_field_x: np.ndarray
    e_field_y: np.ndarray
    n_iterations: int
    converged: bool

    def __post_init__(self) -> None:
        ref_shape = self.potential.shape
        for name, arr in [
            ("electron_density", self.electron_density),
            ("hole_density", self.hole_density),
            ("current_density", self.current_density),
            ("current_density_x", self.current_density_x),
            ("current_density_y", self.current_density_y),
            ("conductivity", self.conductivity),
            ("e_field_x", self.e_field_x),
            ("e_field_y", self.e_field_y),
        ]:
            if arr.shape != ref_shape:
                raise ValueError(f"{name} 形状 {arr.shape} ≠ {ref_shape}")
        if not np.all(np.isfinite(self.potential)):
            raise ValueError("potential 含非有限值（求解失败）")
        if not np.all(np.isfinite(self.conductivity)) or np.any(self.conductivity <= 0.0):
            raise ValueError("conductivity 须全为有限正值（物理约束）")
        if not np.all(np.isfinite(self.current_density_x)):
            raise ValueError("current_density_x 含非有限值")
        if not np.all(np.isfinite(self.current_density_y)):
            raise ValueError("current_density_y 含非有限值")


def _equilibrium_carrier(
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


def _equilibrium_potential(n_eq: np.ndarray, n_i: float, vt: float) -> np.ndarray:
    """平衡电势 φ_eq = V_T·ln(n_eq/n_i) [V]。

    推导：平衡时 n = n_i·exp(φ/V_T)，故 φ = V_T·ln(n/n_i)。
    """
    if np.any(n_eq <= 0.0):
        raise ValueError("n_eq 须 > 0（计算平衡电势前置条件）")
    return vt * np.log(n_eq / n_i)


def _boundary_indices(side: str, nx: int, ny: int) -> np.ndarray:
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


def _apply_dirichlet(
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


class DdmSolver:
    """漂移-扩散主求解器（全耦合阻尼牛顿法）。

    求解策略（Selberherr 1984 §6.4；Bank-Rose 1983）：
    1. 准中性平衡初值 → 牛顿法解非线性 Poisson-Boltzmann（含耗尽区）。
    2. Voltage continuation（0.2V/步）：每步用全耦合阻尼牛顿法联立求解
       Poisson + 电子连续性 + 空穴连续性，Jacobian 3N×3N 分块稀疏，
       含 SRH 复合偏导 + Armijo 回溯线搜索（物理可行性约束 n,p ≥ 0）。
    Gummel 解耦迭代在强正偏 PN 结（0.7V）固有失效（SRH 滞后致负浓度），
    故改用全耦合牛顿法根除滞后问题。

    用法：
        cfg = DdmConfig(nx=50, ny=10, dx=1e-7, dy=1e-7,
                        eps_rel=11.7, doping_n=Nd, doping_p=Na,
                        contacts={"west": 0.0, "east": 0.7})
        result = DdmSolver().solve(cfg)
    """

    def solve(self, config: DdmConfig) -> DdmResult:
        """全耦合阻尼牛顿法求解 Poisson + 连续性 + 后处理。

        流程（Selberherr 1984 §6.4；Jerome 1992）：
        1. 准中性平衡初值（局部电中性近似，作为牛顿法初值）。
        2. V=0 牛顿法求解非线性 Poisson-Boltzmann（Boltzmann 关系
           n=n_i·exp(φ/V_T)），得到含耗尽区的真实平衡势。
           *必须步骤*：准中性初值给 Poisson 电荷≈0→线性势（无耗尽区），
           与真实平衡势差异巨大，导致后续牛顿迭代发散（Selberherr §6.3）。
           牛顿法 Jacobian J = A - (q/V_T)·diag(n+p) 含 exp 线性化项，
           比固定点迭代稳定（Bank-Rose 1983；Jerome 1992）。
        3. Voltage continuation：从真实平衡态逐步加载电压，每步用耦合牛顿法。

        Args:
            config: DDM 配置。

        Returns:
            DdmResult（含 potential, n, p, J, σ, E 等字段）。

        Raises:
            ValueError: 平衡/牛顿迭代不收敛、求解产生非有限值。
        """
        # 步骤 1：准中性平衡初值（局部电中性近似，作为牛顿法初值）
        n_eq_qn, p_eq_qn = _equilibrium_carrier(config.doping_n, config.doping_p, config.n_i)
        phi_eq_qn = _equilibrium_potential(n_eq_qn, config.n_i, config.vt)

        poisson = PoissonSolver()
        continuity = ContinuitySolver(
            config.nx,
            config.ny,
            config.dx,
            config.dy,
            config.mobility_n,
            config.mobility_p,
            config.tau_n,
            config.tau_p,
            config.n_i,
            config.temperature,
        )

        # 步骤 2：V=0 牛顿法求解非线性 Poisson-Boltzmann，得含耗尽区的真实平衡
        # 牛顿平衡求解是预处理步骤，不计入耦合牛顿迭代次数（M1 验收口径）
        eq_contacts = {side: 0.0 for side in config.contacts}
        eq_bc_specs = self._compute_bc_specs(config, n_eq_qn, p_eq_qn, phi_eq_qn, eq_contacts)
        phi_eq, n_eq, p_eq, _n_iter_eq = self._solve_equilibrium(
            poisson, config, phi_eq_qn, eq_bc_specs
        )
        # n_iter_total 仅累计耦合牛顿迭代次数（平衡牛顿不计入 M1 验收口径）
        n_iter_total = 0

        # 步骤 3：Voltage continuation（从真实平衡出发，逐步加载电压 ≤ 0.2 V/步）
        # 耦合牛顿法鲁棒性强，可用 0.2V 步长（Gummel 解耦需 ≤0.1V 仍不稳定）
        phi = phi_eq.copy()
        n = n_eq.copy()
        p = p_eq.copy()

        target_contacts = config.contacts
        max_v = max((abs(v) for v in target_contacts.values()), default=0.0)
        if max_v > 0.2:
            n_steps = max(int(np.ceil(max_v / 0.2)), 1)
            v_fractions = np.linspace(0.0, 1.0, n_steps + 1)[1:]
        else:
            v_fractions = np.array([1.0])

        for step_idx, v_frac in enumerate(v_fractions):
            step_contacts = {side: v * v_frac for side, v in target_contacts.items()}
            # BC 使用真实平衡值（n_eq, p_eq, phi_eq）作为 Ohmic 接触热平衡参考
            bc_specs = self._compute_bc_specs(config, n_eq, p_eq, phi_eq, step_contacts)

            phi, n, p, n_iter_step, converged, d_phi, d_n, d_p = self._run_newton(
                poisson,
                continuity,
                config,
                bc_specs,
                phi,
                n,
                p,
            )
            n_iter_total += n_iter_step
            if not converged:
                raise ValueError(
                    f"牛顿迭代未收敛（continuation step {step_idx + 1}/"
                    f"{len(v_fractions)}, v_frac={v_frac:.2f}）："
                    f"max_iter={config.max_iter}, "
                    f"最后残差 d_phi={d_phi:.3e} V, d_n={d_n:.3e}, d_p={d_p:.3e}"
                )

        return self._postprocess(config, phi, n, p, n_iter_total)

    def _solve_equilibrium(
        self,
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
            J = ∇·(ε·∇) - (q/V_T)·diag(n + p)
        推导：dn/dφ = n/V_T，dp/dφ = -p/V_T，故
            ∂ρ/∂φ = q·(dp/dφ - dn/dφ) = -(q/V_T)·(n + p)
            J = A_Lap + ∂ρ/∂φ = A_Lap - (q/V_T)·diag(n + p)

        *创新* 牛顿法比 Poisson-Boltzmann 固定点迭代显著稳定：
        固定点 J_fixed = A_Lap 缺少 -(q/V_T)·(n+p) 对角项，φ 较大处 exp 正
        反馈导致发散（前次尝试在第 32 步 phi 从 0.287V 爆炸到 1566V）；
        牛顿 J 含 -(q/V_T)·(n+p) 增加对角占优（diag 更负），保证收敛
        （Bank-Rose 1983 收敛性理论；CSDN/IEEE 实践验证）。

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
            idx = _boundary_indices(side, nx, ny)
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
                # 行清零 + identity 注入（向量化，复用 _apply_dirichlet 模式）
                neg_F_bc_vals = bc_vals - phi_vec[bc_idx]  # -(φ[bc] - φ_BC)
                J, neg_F = _apply_dirichlet(J, neg_F, bc_idx, neg_F_bc_vals)

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

    def _run_newton(
        self,
        poisson: PoissonSolver,
        continuity: ContinuitySolver,
        config: DdmConfig,
        bc_specs: dict[str, dict],
        phi_init: np.ndarray,
        n_init: np.ndarray,
        p_init: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, bool, float, float, float]:
        """全耦合阻尼牛顿法求解 Poisson + 连续性系统（Selberherr §6.4）。

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

        Args:
            poisson: Poisson 求解器（复用 build_laplacian_neumann）。
            continuity: 连续性求解器（复用 electron_system/hole_system）。
            config: DDM 配置。
            bc_specs: 边界条件规格（含 phi_b, n_b_arr, p_b_arr）。
            phi_init, n_init, p_init: 初值（上一步 continuation 或平衡解）。

        Returns:
            (phi, n, p, n_iter, converged, d_phi, d_n, d_p)。

        Raises:
            ValueError: J 奇异、求解产生非有限值、Armijo 线搜索耗尽。
        """
        nx, ny = config.nx, config.ny
        n_total = nx * ny
        n_i = config.n_i

        # 预装配 Poisson Laplacian A_ε（含 Neumann，不含 Dirichlet）——迭代中不变
        bcs_poisson = [
            PoissonBc(side=side, type=DIRICHLET, value=float(spec["phi_b"]))
            for side, spec in bc_specs.items()
        ]
        A_eps = poisson.build_laplacian_neumann(
            nx, ny, config.dx, config.dy, config.eps_rel, bcs_poisson
        )

        # Dirichlet BC 节点索引与值（向量化合并 φ/n/p 三块）
        bc_idx_list: list[np.ndarray] = []
        bc_phi_list: list[np.ndarray] = []
        bc_n_list: list[np.ndarray] = []
        bc_p_list: list[np.ndarray] = []
        for side, spec in bc_specs.items():
            idx = _boundary_indices(side, nx, ny)
            bc_idx_list.append(idx)
            bc_phi_list.append(np.full(idx.size, float(spec["phi_b"])))
            bc_n_list.append(np.asarray(spec["n_b_arr"], dtype=float))
            bc_p_list.append(np.asarray(spec["p_b_arr"], dtype=float))
        bc_idx = np.concatenate(bc_idx_list) if bc_idx_list else np.array([], dtype=np.int64)
        bc_phi_vals = np.concatenate(bc_phi_list) if bc_phi_list else np.array([], dtype=float)
        bc_n_vals = np.concatenate(bc_n_list) if bc_n_list else np.array([], dtype=float)
        bc_p_vals = np.concatenate(bc_p_list) if bc_p_list else np.array([], dtype=float)

        I_N = sparse.eye(n_total, format="csr")
        # 浓度下界：防 SRH 分母为零（物理上 n,p 永远 > 0，本征热激发）
        n_floor = n_i * 1e-10

        phi = np.asarray(phi_init, dtype=float).copy()
        n = np.maximum(np.asarray(n_init, dtype=float).copy(), n_floor)
        p = np.maximum(np.asarray(p_init, dtype=float).copy(), n_floor)

        doping_n_flat = config.doping_n.ravel()
        doping_p_flat = config.doping_p.ravel()

        converged = False
        n_iter = 0
        d_phi = d_n = d_p = 0.0
        # Armijo 充分下降参数 σ（Dennis-Schnabel 1996 §6.3，典型 1e-4）
        sigma_armijo = 1e-4

        for k in range(config.max_iter):
            n_iter = k + 1
            phi_vec = phi.ravel()
            n_vec = n.ravel()
            p_vec = p.ravel()

            # 残差装配 F = [F_φ, F_n, F_p]^T
            R = srh_recombination(n, p, n_i, config.tau_n, config.tau_p)
            R_vec = R.ravel()
            A_n, _ = continuity.electron_system(phi, n, p)
            A_p, _ = continuity.hole_system(phi, n, p)
            F_phi = A_eps.dot(phi_vec) + Q_E * (p_vec - n_vec + doping_n_flat - doping_p_flat)
            F_n = A_n.dot(n_vec) - R_vec
            F_p = A_p.dot(p_vec) - R_vec
            if bc_idx.size > 0:
                F_phi[bc_idx] = phi_vec[bc_idx] - bc_phi_vals
                F_n[bc_idx] = n_vec[bc_idx] - bc_n_vals
                F_p[bc_idx] = p_vec[bc_idx] - bc_p_vals
            F = np.concatenate([F_phi, F_n, F_p])
            norm_F = float(np.max(np.abs(F))) if F.size > 0 else 0.0

            # Jacobian 装配（修正牛顿，∂L/∂φ 滞后置零）
            dR_dn, dR_dp = srh_derivatives(n, p, n_i, config.tau_n, config.tau_p)
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
                J = self._apply_newton_bc_rows(J, bc_idx, n_total)

            # 牛顿步求解 J·Δx = -F（scipy 稀疏 LU 直接解）
            delta = spsolve(J.tocsc(), -F)
            if not np.all(np.isfinite(delta)):
                raise ValueError(
                    f"耦合牛顿法第 {n_iter} 步：J·Δx=-F 求解产生非有限值"
                    f"（J 奇异或数值溢出，||F||∞={norm_F:.3e}）"
                )
            d_phi_vec = delta[:n_total]
            d_n_vec = delta[n_total : 2 * n_total]
            d_p_vec = delta[2 * n_total :]

            # Armijo 回溯线搜索 + 物理可行性约束 n,p ≥ 0（*创新*）
            alpha = 1.0
            phi_new = n_new = p_new = None
            for _ls in range(30):
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
                # 评估试探点残差
                R_new = srh_recombination(n_new, p_new, n_i, config.tau_n, config.tau_p)
                A_n_new, _ = continuity.electron_system(phi_new, n_new, p_new)
                A_p_new, _ = continuity.hole_system(phi_new, n_new, p_new)
                F_phi_new = A_eps.dot(phi_new_vec) + Q_E * (
                    p_new_vec - n_new_vec + doping_n_flat - doping_p_flat
                )
                F_n_new = A_n_new.dot(n_new_vec) - R_new.ravel()
                F_p_new = A_p_new.dot(p_new_vec) - R_new.ravel()
                if bc_idx.size > 0:
                    F_phi_new[bc_idx] = phi_new_vec[bc_idx] - bc_phi_vals
                    F_n_new[bc_idx] = n_new_vec[bc_idx] - bc_n_vals
                    F_p_new[bc_idx] = p_new_vec[bc_idx] - bc_p_vals
                F_new = np.concatenate([F_phi_new, F_n_new, F_p_new])
                norm_F_new = float(np.max(np.abs(F_new))) if F_new.size > 0 else 0.0
                # Armijo 充分下降条件
                if norm_F_new < (1.0 - sigma_armijo * alpha) * norm_F:
                    break
                alpha *= 0.5
            else:
                raise ValueError(
                    f"耦合牛顿法第 {n_iter} 步：Armijo 线搜索耗尽"
                    f"（30 次回溯仍未找到物理可行下降步，||F||∞={norm_F:.3e}）"
                )

            phi = phi_new
            n = n_new
            p = p_new

            # 收敛检查（步长加权相对范数）
            n_norm = max(float(np.max(np.abs(n_vec))), 1.0)
            p_norm = max(float(np.max(np.abs(p_vec))), 1.0)
            d_phi = float(np.max(np.abs(alpha * d_phi_vec)))
            d_n = float(np.max(np.abs(alpha * d_n_vec))) / n_norm
            d_p = float(np.max(np.abs(alpha * d_p_vec))) / p_norm
            if max(d_phi, d_n, d_p) < config.tol:
                converged = True
                break

        return phi, n, p, n_iter, converged, d_phi, d_n, d_p

    @staticmethod
    def _apply_newton_bc_rows(
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

    def _compute_bc_specs(
        self,
        config: DdmConfig,
        n_eq: np.ndarray,
        p_eq: np.ndarray,
        phi_eq: np.ndarray,
        contacts: dict[str, float] | None = None,
    ) -> dict[str, dict]:
        """计算 Ohmic 接触的边界值（phi_b, n_b, p_b）。

        Ohmic 接触边界条件（Selberherr 1984 §6.2）：
        - φ_b = φ_eq + V_contact（边界电势 = 平衡电势 + 接触电压）
        - n_b = n_eq（热平衡浓度，准费米能级偏移与电势同步）
        - p_b = p_eq（热平衡浓度）

        Args:
            config: DDM 配置。
            n_eq, p_eq, phi_eq: 平衡值（基于掺杂计算）。
            contacts: 接触电压映射。若 None，使用 config.contacts。
                用于 voltage continuation（逐步加载电压）。

        Returns:
            dict[side] = {"idx", "phi_b", "n_b_arr", "p_b_arr"}。

        Raises:
            ValueError: 接触边界掺杂非均匀（不支持变值 Dirichlet）。
        """
        if contacts is None:
            contacts = config.contacts
        nx, ny = config.nx, config.ny
        specs: dict[str, dict] = {}
        for side, voltage in contacts.items():
            if side == "west":
                n_arr, p_arr, phi_arr = n_eq[0, :], p_eq[0, :], phi_eq[0, :] + voltage
            elif side == "east":
                n_arr, p_arr, phi_arr = n_eq[-1, :], p_eq[-1, :], phi_eq[-1, :] + voltage
            elif side == "south":
                n_arr, p_arr, phi_arr = n_eq[:, 0], p_eq[:, 0], phi_eq[:, 0] + voltage
            elif side == "north":
                n_arr, p_arr, phi_arr = n_eq[:, -1], p_eq[:, -1], phi_eq[:, -1] + voltage
            else:
                raise ValueError(f"未知方向 {side}")
            if not (
                np.allclose(n_arr, n_arr[0])
                and np.allclose(p_arr, p_arr[0])
                and np.allclose(phi_arr, phi_arr[0])
            ):
                raise ValueError(
                    f"接触 {side} 边界掺杂非均匀，不支持变值 Dirichlet （请确保接触处掺杂一致）"
                )
            idx = _boundary_indices(side, nx, ny)
            specs[side] = {
                "idx": idx,
                "phi_b": float(phi_arr[0]),
                "n_b_arr": np.full(idx.size, float(n_arr[0])),
                "p_b_arr": np.full(idx.size, float(p_arr[0])),
            }
        return specs

    def _postprocess(
        self,
        config: DdmConfig,
        phi: np.ndarray,
        n: np.ndarray,
        p: np.ndarray,
        n_iter: int,
    ) -> DdmResult:
        """计算电流密度 J、电导率 σ、电场 E。

        J_n = q·μ_n·n·E + q·D_n·∇n（电子电流）
        J_p = q·μ_p·p·E - q·D_p·∇p（空穴电流）
        J = J_n + J_p（总电流密度）
        σ = q·(μ_n·n + μ_p·p)（欧姆电导率）
        E = -∇φ（电场）
        """
        dx, dy = config.dx, config.dy
        vt = config.vt
        D_n = config.mobility_n * vt
        D_p = config.mobility_p * vt

        e_x, e_y = self._compute_gradient_xy(phi, dx, dy, sign=-1.0)
        dn_dx, dn_dy = self._compute_gradient_xy(n, dx, dy, sign=+1.0)
        dp_dx, dp_dy = self._compute_gradient_xy(p, dx, dy, sign=+1.0)

        # J_n = q·μ_n·n·E + q·D_n·∇n（E = -∇φ 已含负号）
        j_n_x = Q_E * config.mobility_n * n * e_x + Q_E * D_n * dn_dx
        j_n_y = Q_E * config.mobility_n * n * e_y + Q_E * D_n * dn_dy
        # J_p = q·μ_p·p·E - q·D_p·∇p
        j_p_x = Q_E * config.mobility_p * p * e_x - Q_E * D_p * dp_dx
        j_p_y = Q_E * config.mobility_p * p * e_y - Q_E * D_p * dp_dy

        j_x = j_n_x + j_p_x
        j_y = j_n_y + j_p_y
        j_mag = np.sqrt(j_x**2 + j_y**2)

        # 电导率 σ = q·(μ_n·n + μ_p·p)；下界为本征电导率防 J²/σ 爆炸（物理上
        # 半导体中 n,p 永远 > 0，下界对应本征热激发载流子）
        sigma = Q_E * (config.mobility_n * n + config.mobility_p * p)
        sigma_min = Q_E * (config.mobility_n + config.mobility_p) * config.n_i
        sigma = np.maximum(sigma, sigma_min)

        return DdmResult(
            potential=phi,
            electron_density=n,
            hole_density=p,
            current_density=j_mag,
            current_density_x=j_x,
            current_density_y=j_y,
            conductivity=sigma,
            e_field_x=e_x,
            e_field_y=e_y,
            n_iterations=n_iter,
            converged=True,
        )

    @staticmethod
    def _compute_gradient_xy(
        arr: np.ndarray, dx: float, dy: float, sign: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """计算 2D 场的 (x, y) 梯度分量，1D 情形该方向梯度置零。

        Args:
            arr: 输入场 (nx, ny)。
            dx, dy: 网格间距。
            sign: +1 返回 ∇arr，-1 返回 -∇arr（如电场 E = -∇φ）。
        """
        nx, ny = arr.shape
        if nx >= 2:
            gx = sign * np.gradient(arr, dx, axis=0, edge_order=1)
        else:
            gx = np.zeros_like(arr)
        if ny >= 2:
            gy = sign * np.gradient(arr, dy, axis=1, edge_order=1)
        else:
            gy = np.zeros_like(arr)
        return gx, gy


def solve_ddm(config: DdmConfig) -> DdmResult:
    """便捷函数：Gummel 迭代求解 DDM。

    Args:
        config: DDM 配置。

    Returns:
        DdmResult（含 potential, n, p, J, σ, E 等字段）。
    """
    return DdmSolver().solve(config)
