"""稳态傅里叶导热有限差分求解器（A07-HEAT §求解器）。

求解稳态热传导方程（无内热源时为 Laplace，有源时为 Poisson）：
    ∇·(k(x,y)·∇T) + Q(x,y) = 0

采用 5 点有限差分离散 + 界面调和平均热导率（保证材料跳变处热流连续），
稀疏矩阵 scipy.sparse.linalg.spsolve 直接求解。线性索引 k = i·ny + j，
T.shape = (nx, ny)，axis 0 = x，axis 1 = y。

离散格式（变系数 k，有限体积/调和平均，Incropera §4.4；COMSOL HT）：
    节点 (i,j) 邻接系数（east 面为例）：
        k_e = 2·k[i,j]·k[i+1,j] / (k[i,j] + k[i+1,j])   # 调和平均
        A[(i,j),(i+1,j)] = k_e / dx²
    对角 A[(i,j),(i,j)] = -(Σ 邻接系数)
    右端 b[(i,j)] = -Q[i,j]
常数 k 时退化为标准 5 点拉普拉斯算子 k·(T_{i+1}+T_{i-1}-2T_i)/dx² + ...。

周期边界在装配阶段对法向索引环绕（west 邻接 → east 列），使系统矩阵
在周期方向为循环矩阵；其余 4 类边界（Dirichlet/Neumann/Convective/Radiative）
由 heat.boundary.apply_boundary_conditions 行替换注入。

物理可解性检查（M2 功率守恒）：
    纯 Neumann（无接地）+ 净体积热源 ≠ 0 → 无稳态解（功率不守恒），raise。
    纯 Neumann + 净源 = 0 → 解差一常数（奇异），spsolve 产生非有限值 → raise。
这符合热力学第一定律：稳态要求产热=散热，绝热闭域内持续产热无稳态。

文献来源（≥5，规则 18 学术诚信）：
1. Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer" —
   https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
2. COMSOL Heat Transfer Module — https://www.comsol.com/heat-transfer-module
3. Cocorullo 1999 IEEE J Quantum Electron — 硅热光系数（耦合模块复用）—
   https://doi.org/10.1109/3.791939
4. Litz 2011 Optics Express — 光子器件自热仿真 —
   https://doi.org/10.1364/OE.19.012997
5. Schneider 1973 IEEE Trans MTT — 数值热传导稳定格式 —
   https://doi.org/10.1109/TMTT.1973.1127965
6. scipy.sparse.linalg.spsolve —
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
7. Taflove 2005 Computational Electrodynamics — 有限差分方法论 —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from polaris_multiphysics.heat.boundary import (
    BcSpec,
    BoundaryType,
    apply_boundary_conditions,
    is_grounding_bc,
)

__all__ = [
    "HeatConfig",
    "HeatResult",
    "HeatSolver",
    "solve_heat",
    "ADIABATIC",
]

# 物理参数（光电子典型材料，Cocorullo 1999 / Incropera）。
K_SILICON: float = 148.0  # 硅热导率 [W/(m·K)]
K_SIO2: float = 1.4  # SiO2 热导率 [W/(m·K)]
DN_DT_SI: float = 1.86e-4  # 硅热光系数 [1/K]（Cocorullo 1999）

# 默认绝热 Neumann 规格（边界未指定时使用）。
ADIABATIC = BcSpec(type=BoundaryType.NEUMANN, value=0.0)

# 纯 Neumann 净源判零相对容差（M2 功率守恒）。
_NET_SOURCE_TOL = 1e-12


@dataclass
class HeatConfig:
    """热传导求解配置。

    Attributes:
        dx, dy: 网格间距 [m]。
        k_arr: 热导率场 (nx, ny) [W/(m·K)]，全正。
        q_arr: 体积热源密度 (nx, ny) [W/m³]（≥0 产热）。
        bc_dict: 边界条件映射 {west/east/south/north: BcSpec}。
            未指定的有效方向默认绝热 Neumann（q=0）。
    """

    dx: float
    dy: float
    k_arr: np.ndarray
    q_arr: np.ndarray
    bc_dict: dict[str, BcSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.dx <= 0.0:
            raise ValueError(f"dx 须 > 0，实际 {self.dx}")
        if self.dy <= 0.0:
            raise ValueError(f"dy 须 > 0，实际 {self.dy}")
        if self.k_arr.ndim != 2:
            raise ValueError(f"k_arr 须 2D，实际 {self.k_arr.ndim}D")
        if self.k_arr.shape != self.q_arr.shape:
            raise ValueError(f"k_arr {self.k_arr.shape} 与 q_arr {self.q_arr.shape} 形状不匹配")
        if not np.all(np.isfinite(self.k_arr)) or np.any(self.k_arr <= 0.0):
            raise ValueError("k_arr 须全为有限正值（热导率物理约束）")
        if not np.all(np.isfinite(self.q_arr)):
            raise ValueError("q_arr 须全为有限值")
        for side, spec in self.bc_dict.items():
            if side not in ("west", "east", "south", "north"):
                raise ValueError(f"未知边界方向 {side}")
            if not isinstance(spec, BcSpec):
                raise TypeError(f"bc_dict[{side}] 须为 BcSpec，实际 {type(spec)}")
        self._validate_periodic_pairs()

    @property
    def shape(self) -> tuple[int, int]:
        """网格形状 (nx, ny)。"""
        return self.k_arr.shape  # type: ignore[return-value]

    def _validate_periodic_pairs(self) -> None:
        """周期边界须成对（west&east 或 south&north），否则 raise。"""
        w = self.bc_dict.get("west")
        e = self.bc_dict.get("east")
        s = self.bc_dict.get("south")
        no = self.bc_dict.get("north")
        wp = w is not None and w.type is BoundaryType.PERIODIC
        ep = e is not None and e.type is BoundaryType.PERIODIC
        if wp != ep:
            raise ValueError("周期边界须 west/east 同时为 PERIODIC")
        sp = s is not None and s.type is BoundaryType.PERIODIC
        np_ = no is not None and no.type is BoundaryType.PERIODIC
        if sp != np_:
            raise ValueError("周期边界须 south/north 同时为 PERIODIC")

    def effective_bc(self, side: str) -> BcSpec:
        """返回有效边界条件（缺失且方向有效时默认绝热 Neumann）。"""
        spec = self.bc_dict.get(side)
        if spec is not None:
            return spec
        return ADIABATIC


@dataclass
class HeatResult:
    """热求解结果。

    Attributes:
        temperature: 温度场 (nx, ny) [K]。
        heat_flux_x: x 向热流密度 -k·∂T/∂x (nx, ny) [W/m²]（Fourier 律）。
        heat_flux_y: y 向热流密度 -k·∂T/∂y (nx, ny) [W/m²]。
        dx, dy: 网格间距 [m]。
    """

    temperature: np.ndarray
    heat_flux_x: np.ndarray
    heat_flux_y: np.ndarray
    dx: float
    dy: float

    def __post_init__(self) -> None:
        if self.temperature.shape != self.heat_flux_x.shape:
            raise ValueError("temperature 与 heat_flux_x 形状须一致")
        if self.temperature.shape != self.heat_flux_y.shape:
            raise ValueError("temperature 与 heat_flux_y 形状须一致")
        if not np.all(np.isfinite(self.temperature)):
            raise ValueError("温度场含非有限值（求解失败）")


def _harmonic_mean(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """调和平均 2ab/(a+b)，保证材料界面热流连续（Incropera §4.4）。"""
    return 2.0 * a * b / (a + b)


def _side_applicable(side: str, nx: int, ny: int) -> bool:
    """该方向是否有可施加边界的节点（维度 ≥ 2 才有真正的边界）。"""
    if side in ("west", "east"):
        return nx >= 2
    return ny >= 2


def _build_interior(config: HeatConfig) -> tuple[sparse.csr_matrix, np.ndarray]:
    """装配变系数 5 点差分内部矩阵 A 与右端 b（含周期环绕）。

    每条内部面同时贡献两个对称非对角项 A[i,j] 与 A[j,i]，并对两端节点
    对角各累加面热导（保证矩阵对称、行和为零）。向量化构造，禁止逐元素循环。
    """
    nx, ny = config.k_arr.shape
    n = nx * ny
    k = config.k_arr
    dx, dy = config.dx, config.dy

    w = config.effective_bc("west")
    e = config.effective_bc("east")
    s = config.effective_bc("south")
    no = config.effective_bc("north")
    x_per = w.type is BoundaryType.PERIODIC and e.type is BoundaryType.PERIODIC
    y_per = s.type is BoundaryType.PERIODIC and no.type is BoundaryType.PERIODIC

    rows_l: list[np.ndarray] = []
    cols_l: list[np.ndarray] = []
    vals_l: list[np.ndarray] = []
    center = np.zeros(n, dtype=float)

    def _add_face(r0: np.ndarray, r1: np.ndarray, v: np.ndarray) -> None:
        """添加对称面：A[r0,r1]=A[r1,r0]=v，两端 center 各 += v。"""
        rows_l.append(np.asarray(r0, dtype=np.int64).ravel())
        cols_l.append(np.asarray(r1, dtype=np.int64).ravel())
        vals_l.append(np.asarray(v, dtype=float).ravel())
        rows_l.append(np.asarray(r1, dtype=np.int64).ravel())
        cols_l.append(np.asarray(r0, dtype=np.int64).ravel())
        vals_l.append(np.asarray(v, dtype=float).ravel())
        nonlocal center
        center = _accum_center(center, r0, v)
        center = _accum_center(center, r1, v)

    def _add_diag(r: np.ndarray, v: np.ndarray) -> None:
        rows_l.append(np.asarray(r, dtype=np.int64).ravel())
        cols_l.append(np.asarray(r, dtype=np.int64).ravel())
        vals_l.append(np.asarray(v, dtype=float).ravel())

    if nx >= 2:
        kxe = _harmonic_mean(k[:-1, :], k[1:, :])  # x 面 (nx-1, ny)
        Ie, Je = np.meshgrid(np.arange(nx - 1), np.arange(ny), indexing="ij")
        r0 = (Ie * ny + Je).ravel()
        r1 = ((Ie + 1) * ny + Je).ravel()
        _add_face(r0, r1, (kxe / dx**2).ravel())

    if x_per:  # 周期环绕：最东列 ↔ 最西列
        kxe_w = _harmonic_mean(k[-1, :], k[0, :])
        jw = np.arange(ny)
        r0 = ((nx - 1) * ny + jw).ravel()
        r1 = (0 * ny + jw).ravel()
        _add_face(r0, r1, (kxe_w / dx**2).ravel())

    if ny >= 2:
        kyn = _harmonic_mean(k[:, :-1], k[:, 1:])  # y 面 (nx, ny-1)
        In, Jn = np.meshgrid(np.arange(nx), np.arange(ny - 1), indexing="ij")
        r0 = (In * ny + Jn).ravel()
        r1 = (In * ny + (Jn + 1)).ravel()
        _add_face(r0, r1, (kyn / dy**2).ravel())

    if y_per:
        kyn_w = _harmonic_mean(k[:, -1], k[:, 0])
        iw = np.arange(nx)
        r0 = (iw * ny + (ny - 1)).ravel()
        r1 = (iw * ny + 0).ravel()
        _add_face(r0, r1, (kyn_w / dy**2).ravel())

    # 对角 = -邻接系数之和（行和为零，Laplacian 性质）
    all_idx = np.arange(n)
    _add_diag(all_idx, -center)

    rows = np.concatenate(rows_l)
    cols = np.concatenate(cols_l)
    vals = np.concatenate(vals_l)
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    b = -config.q_arr.ravel().astype(float, copy=True)
    return A, b


def _accum_center(center: np.ndarray, idx: np.ndarray, val: np.ndarray) -> np.ndarray:
    """向量化累加对角贡献（np.add.at 处理重复索引）。"""
    out = center.copy()
    np.add.at(out, idx, val)
    return out


class HeatSolver:
    """稳态热传导求解器。

    用法：
        cfg = HeatConfig(dx, dy, k_arr, q_arr, bc_dict)
        result = HeatSolver().solve(cfg)
    """

    def solve(self, config: HeatConfig) -> HeatResult:
        """求解稳态温度场与热流密度。

        Args:
            config: 热配置。

        Returns:
            HeatResult。

        Raises:
            ValueError: 纯 Neumann+净热源≠0（M2 功率不守恒）或系统奇异。
        """
        nx, ny = config.k_arr.shape
        A, b = _build_interior(config)
        A, b = apply_boundary_conditions(A, b, config)
        self._check_solvability(config, A, b)

        T_vec = spsolve(A, b)
        if not np.all(np.isfinite(T_vec)):
            raise ValueError(
                "热系统求解产生非有限值（系统奇异："
                "可能为纯 Neumann 边界且净热源≈0，解差一常数，无法唯一确定）"
            )
        T = T_vec.reshape(nx, ny)

        # 热流密度 Fourier 律 q = -k∇T。逐向梯度，1D 情形（nx=1 或 ny=1）
        # 该方向热流置零；edge_order=1 兼容最小 2 节点维度。
        if nx >= 2:
            dTdx = np.gradient(T, config.dx, axis=0, edge_order=1)
        else:
            dTdx = np.zeros_like(T)
        if ny >= 2:
            dTdy = np.gradient(T, config.dy, axis=1, edge_order=1)
        else:
            dTdy = np.zeros_like(T)
        qx = -config.k_arr * dTdx
        qy = -config.k_arr * dTdy
        return HeatResult(temperature=T, heat_flux_x=qx, heat_flux_y=qy, dx=config.dx, dy=config.dy)

    @staticmethod
    def _check_solvability(config: HeatConfig, A: sparse.csr_matrix, b: np.ndarray) -> None:
        """M2 功率守恒：无接地且净体积热源≠0 → raise。

        纯 Neumann/Periodic（无温度锚定）下，稳态要求产热=边界散热；
        绝热闭域持续产热无稳态解（热力学第一定律）。
        """
        nx, ny = config.shape
        grounding = any(
            is_grounding_bc(config.effective_bc(side))
            for side in ("west", "east", "south", "north")
            if _side_applicable(side, nx, ny)
        )
        if grounding:
            return
        net = float(np.abs(config.q_arr.sum()) * config.dx * config.dy)
        scale = float(np.abs(config.q_arr).sum() * config.dx * config.dy) + 1e-30
        if net > _NET_SOURCE_TOL * scale and net > 0.0:
            raise ValueError(
                "功率不守恒：所有边界均为 Neumann/Periodic（无温度锚定）"
                f"而净体积热源 {net:.3e} W ≠ 0，绝热闭域持续产热无稳态解（M2）"
            )


def solve_heat(config: HeatConfig) -> HeatResult:
    """便捷函数：单步求解稳态热传导。"""
    return HeatSolver().solve(config)
