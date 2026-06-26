"""BPM 求解器主体（A03 §6/§7/§8.1，统一 1D/2D 调度入口）。

本模块将 operators/boundary/crank_nicolson/adi 四个子模块组装为统一求解器 API：
- BpmConfig：求解配置（波长/网格/步长/参考折射率/极化/边界/θ）
- BpmResult：求解结果（场快照/z 坐标/末场/功率守恒校验）
- BpmSolver：求解器类，按输入场维度自动调度 1D CN 或 2D ADI
- solve_bpm()：便捷入口函数

SVEA 抛物方程核心系数（A03 §3.2 公式 F1，exp(-iωt) 时间约定）::

    a = -2i·k₀·n_ref，b = k₀²·(n² - n_ref²)，k₀ = 2π/λ

正向传播载波 exp(+i·k₀·n_ref·z)，a·∂ψ/∂z = ∇⊥²ψ + b·ψ（与 TBC 公式
Re(kₓ)>0 外向自洽，详见 BpmConfig.a_coef）。

调度逻辑（A03 §7.1 / §7.2 伪代码）：
- 输入场 ψ_init 为 1D (Nx,) → 1D Crank-Nicolson + TBC（crank_nicolson_propagate_1d）
- 输入场 ψ_init 为 2D (Ny, Nx) → 2D ADI 分裂 + TBC（adi_propagate_2d）

默认步长 Δz = λ/(4·n_ref)（A03 §8.3 性能策略初始步长）。

功率守恒校验（M2 验收点，A03 §7.3）::

    P(z) = ∫|ψ(x,y,z)|² dx dy（或 1D 时 P(z) = ∫|ψ(x,z)|² dx）
    相对误差 ε = |P(L) - P(0)| / P(0) < 1e-6（自由空间 + CN θ=0.5 严格守恒）

文献来源（≥5，规则 18 学术诚信）：
1. Hadley 1992 IEEE J Quantum Electron 28(1) 363-370 — TBC + CN-BPM —
   https://doi.org/10.1109/3.119546
2. Hadley 1991 Opt Lett 16 624-626 — TBC 短文版本 —
   https://doi.org/10.1364/OL.16.000624
3. Chung & Dagli 1991 IEEE PTL 3 150-152 — FD-BPM CN 三对角实现 —
   https://doi.org/10.1109/68.84566
4. Hadley 1994 Opt Lett 17 1426-1428 (Padé wide-angle) —
   https://doi.org/10.1364/OL.17.001426
5. Optiwave OptiBPM Boundary Conditions for BPM —
   https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
6. RP Photonics Encyclopedia: Numerical Beam Propagation —
   https://www.rp-photonics.com/numerical_beam_propagation.html
7. beampy Python BPM — CN + TBC + ADI 开源参考实现 —
   https://beampy.readthedocs.io/en/latest/code_bpm.html

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy+scipy）/python代码开发规则.md §4（向量化，禁循环）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.bpm.adi import adi_propagate_2d
from polaris.sim.bpm.boundary import BoundaryType
from polaris.sim.bpm.crank_nicolson import crank_nicolson_propagate_1d
from polaris.sim.bpm.operators import Polarization, build_tridiag_operator

__all__ = [
    "BpmConfig",
    "BpmResult",
    "BpmSolver",
    "solve_bpm",
]

# 默认波长（米）： telecom C-band 1550nm（A03 §2.1 弱导波导主场景）
DEFAULT_WAVELENGTH = 1.55e-6
# 默认 CN 权重 θ=0.5（二阶时间精度，A03 §4.2 商业默认）
DEFAULT_THETA = 0.5


def _compute_power(psi: np.ndarray, dx: float, dy: float | None = None) -> float:
    """计算场功率 P = ∫|ψ|² dA（A03 §7.3 功率沿 z 演化，向量化）。

    Args:
        psi: 场分布，1D (Nx,) 或 2D (Ny, Nx)。
        dx: x 方向网格间距（米）。
        dy: y 方向网格间距（米），1D 时传 None。

    Returns:
        功率（W，归一化前为 |ψ|²·面积积分值）。

    Raises:
        ValueError: 输入非法（规则 14）。
    """
    psi_c = np.asarray(psi, dtype=np.complex128)
    intensity = np.abs(psi_c) ** 2  # |ψ|²（向量化）
    if psi_c.ndim == 1:
        return float(np.sum(intensity) * dx)
    if psi_c.ndim == 2:
        if dy is None:
            raise ValueError("2D 场功率计算需要 dy（规则 14：禁止 fall-back）")
        return float(np.sum(intensity) * dx * dy)
    raise ValueError(f"psi 须为 1D 或 2D，实际 {psi_c.ndim}D（规则 14）")


@dataclass
class BpmConfig:
    """BPM 求解器配置（A03 §3/§4/§5，降低函数参数个数，规则 4）。

    封装波长、网格、步长、参考折射率、极化、边界、CN 权重等参数。
    默认 Δz = λ/(4·n_ref)（A03 §8.3 性能策略初始步长），可在构造后显式覆盖。

    Attributes:
        wavelength: 自由空间波长 λ（米），默认 1.55e-6（C-band）。
        dx: x 方向网格间距（米）。
        dy: y 方向网格间距（米），1D 仿真时可设为 dx（仅用于功率积分，未实际参与差分）。
        dz: z 方向步长（米）。None 表示用默认 λ/(4·n_ref)（A03 §8.3）。
        nz: z 方向步数，必须 ≥1。
        n_ref: 参考折射率（SVEA 载波 exp(i·k₀·n_ref·z) 的相速度），必须 >0。
        polarization: 偏振模式 'te'/'tm'/'scalar'（A03 §3.3）。
        boundary: 边界类型 'tbc'/'dirichlet'/'neumann'（A03 §5）。
        theta: CN 权重 θ∈[0,1]，默认 0.5（二阶时间精度，A03 §4.2）。
        store_interval: 快照存储间隔（每 store_interval 步存一次）。
    """

    wavelength: float = DEFAULT_WAVELENGTH
    dx: float = 0.0
    dy: float = 0.0
    dz: float | None = None
    nz: int = 1
    n_ref: float = 1.0
    polarization: str = Polarization.TE
    boundary: str = BoundaryType.TBC
    theta: float = DEFAULT_THETA
    store_interval: int = 1

    def __post_init__(self) -> None:
        if self.wavelength <= 0.0:
            raise ValueError(f"波长必须为正，实际 {self.wavelength}（规则 14）")
        if self.dx <= 0.0:
            raise ValueError(f"dx 必须为正，实际 {self.dx}（规则 14）")
        if self.dy <= 0.0:
            raise ValueError(f"dy 必须为正，实际 {self.dy}（规则 14）")
        if self.nz < 1:
            raise ValueError(f"nz 须 ≥1，实际 {self.nz}（规则 14）")
        if self.n_ref <= 0.0:
            raise ValueError(f"n_ref 必须为正，实际 {self.n_ref}（规则 14）")
        if self.polarization not in (
            Polarization.TE,
            Polarization.TM,
            Polarization.SCALAR,
        ):
            raise ValueError(
                f"polarization 须为 'te'/'tm'/'scalar'，实际 {self.polarization!r}（规则 14）"
            )
        if self.boundary not in (
            BoundaryType.TBC,
            BoundaryType.DIRICHLET,
            BoundaryType.NEUMANN,
        ):
            raise ValueError(
                f"boundary 须为 'tbc'/'dirichlet'/'neumann'，实际 {self.boundary!r}（规则 14）"
            )
        if not 0.0 <= self.theta <= 1.0:
            raise ValueError(f"theta 须 ∈ [0, 1]，实际 {self.theta}（规则 14）")
        if self.store_interval < 1:
            raise ValueError(f"store_interval 须 ≥1，实际 {self.store_interval}（规则 14）")

    @property
    def k0(self) -> float:
        """真空波数 k₀ = 2π/λ（1/m）。"""
        return 2.0 * np.pi / self.wavelength

    @property
    def a_coef(self) -> complex:
        """SVEA 抛物方程系数 a = -2i·k₀·n_ref（A03 §3.2 公式 F1，exp(-iωt) 约定）。

        采用 exp(-iωt) 时间约定（与 Hadley 1992 TBC 公式 Re(kₓ)>0 外向一致）：
        正向传播载波 exp(+i·k₀·n_ref·z)，SVEA 慢变包络 ψ 满足
            a·∂ψ/∂z = ∇⊥²ψ + b·ψ，a = -2i·k₀·n_ref
        TBC 公式 kₓ = (-i/Δx)·ln(ψ_m/ψ_{m-1}) 在此约定下 Re(kₓ)>0 为外向波，
        与 CN 步进 [I - α·A]ψ^{n+1} = [I + α·A]ψ^n 中 α = θ·Δz/a 自洽。
        （若误用 a = +2i·k₀·n_ref，CN 推进算子相位反号，光束反向传播且
        TBC 将外向波误判为内向波导致反射而非吸收，M3 验收失败。）
        """
        return -2.0j * self.k0 * self.n_ref

    @property
    def dz_resolved(self) -> float:
        """实际使用的 z 步长。None 时取默认 λ/(4·n_ref)（A03 §8.3）。"""
        if self.dz is not None:
            return self.dz
        return self.wavelength / (4.0 * self.n_ref)


@dataclass
class BpmResult:
    """BPM 求解结果（A03 §7.3 输出后处理）。

    Attributes:
        snapshots: 场快照数组。
            - 1D 仿真：(N_snapshots, Nx) 复数。
            - 2D 仿真：(N_snapshots, Ny, Nx) 复数。
        z_coords: 快照对应的 z 坐标 (N_snapshots,)，米。
        final_field: 末步场 ψ(z=L)，与 snapshots[-1] 一致。
        power_initial: 初始功率 P(0) = ∫|ψ(x,y,0)|² dA。
        power_final: 末步功率 P(L) = ∫|ψ(x,y,L)|² dA。
        power_conservation_error: 功率守恒相对误差
            ε = |P(L) - P(0)| / P(0)（M2 验收点：< 1e-6）。
        n_dim: 仿真维度（1 或 2）。
        n_steps: 实际执行步数 nz。
    """

    snapshots: np.ndarray
    z_coords: np.ndarray
    final_field: np.ndarray
    power_initial: float
    power_final: float
    power_conservation_error: float
    n_dim: int
    n_steps: int

    def __post_init__(self) -> None:
        if self.snapshots.ndim not in (2, 3):
            raise ValueError(
                f"snapshots 须为 2D (N,Nx) 或 3D (N,Ny,Nx)，实际 {self.snapshots.ndim}D（规则 14）"
            )
        if self.z_coords.ndim != 1:
            raise ValueError(f"z_coords 须为 1D，实际 {self.z_coords.ndim}D（规则 14）")
        if self.snapshots.shape[0] != self.z_coords.shape[0]:
            raise ValueError(
                f"snapshots 快照数 {self.snapshots.shape[0]} 与 z_coords "
                f"{self.z_coords.shape[0]} 不一致（规则 14）"
            )
        if self.n_dim not in (1, 2):
            raise ValueError(f"n_dim 须为 1 或 2，实际 {self.n_dim}（规则 14）")
        if self.n_steps < 1:
            raise ValueError(f"n_steps 须 ≥1，实际 {self.n_steps}（规则 14）")


@dataclass
class BpmSolver:
    """BPM 求解器（A03 §6/§8.1，统一 1D CN / 2D ADI 调度）。

    根据 BpmConfig 构造所需算子并按输入场维度自动调度：
    - ψ_init.ndim == 1 → crank_nicolson_propagate_1d（A03 §7.1）
    - ψ_init.ndim == 2 → adi_propagate_2d（A03 §7.2）

    用法::

        cfg = BpmConfig(wavelength=1.55e-6, dx=5e-8, dy=5e-8, nz=100, n_ref=1.5)
        solver = BpmSolver(cfg)
        result = solver.solve(psi_init, n_arr)

    Attributes:
        config: 求解配置（BpmConfig 实例）。
    """

    config: BpmConfig

    def __post_init__(self) -> None:
        # 配置校验已在 BpmConfig.__post_init__ 完成，此处仅复检关键派生量
        if abs(self.config.a_coef) < 1e-300:
            raise ValueError(
                f"a_coef 过小 |a|={abs(self.config.a_coef):.2e}（k₀·n_ref 异常？规则 14）"
            )

    def _solve_1d(self, psi_init: np.ndarray, n_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """1D Crank-Nicolson 传播（A03 §7.1 伪代码）。

        Args:
            psi_init: 初始场 ψ(z=0) (Nx,)。
            n_arr: 折射率分布 (Nx,)。

        Returns:
            (snapshots, z_coords): (N_snapshots, Nx) 与 (N_snapshots,)。
        """
        # 构造三对角算子 A（scipy.sparse.diags 一次性构造，A03 §8.3 性能策略）
        a_sparse = build_tridiag_operator(
            n_arr=n_arr,
            dx=self.config.dx,
            k0=self.config.k0,
            n_ref=self.config.n_ref,
            polarization=self.config.polarization,
        )
        # CN 主循环（z 步进主循环为唯一允许循环，python代码开发规则.md §4）
        snapshots, z_coords = crank_nicolson_propagate_1d(
            psi_init=psi_init,
            a_sparse=a_sparse,
            dz=self.config.dz_resolved,
            nz=self.config.nz,
            a_coef=self.config.a_coef,
            dx=self.config.dx,
            theta=self.config.theta,
            boundary=self.config.boundary,
            store_interval=self.config.store_interval,
        )
        return snapshots, z_coords

    def _solve_2d(self, psi_init: np.ndarray, n_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """2D ADI 传播（A03 §7.2 伪代码，Peaceman & Rachford 1955）。

        Args:
            psi_init: 初始场 ψ(z=0) (Ny, Nx)。
            n_arr: 折射率分布，1D (Nx,) 沿 y 均匀，或 2D (Ny, Nx)。

        Returns:
            (snapshots, z_coords): (N_snapshots, Ny, Nx) 与 (N_snapshots,)。
        """
        snapshots, z_coords = adi_propagate_2d(
            psi_init=psi_init,
            n_arr=n_arr,
            dx=self.config.dx,
            dy=self.config.dy,
            dz=self.config.dz_resolved,
            nz=self.config.nz,
            a_coef=self.config.a_coef,
            k0=self.config.k0,
            n_ref=self.config.n_ref,
            theta=self.config.theta,
            polarization=self.config.polarization,
            boundary=self.config.boundary,
            store_interval=self.config.store_interval,
        )
        return snapshots, z_coords

    def solve(self, psi_init: np.ndarray, n_arr: np.ndarray) -> BpmResult:
        """求解 BPM 传播（A03 §6，按输入场维度自动调度 1D/2D）。

        Args:
            psi_init: 初始场 ψ(z=0)，1D (Nx,) 或 2D (Ny, Nx)，复数。
            n_arr: 折射率分布。
                - 1D 仿真：1D (Nx,)。
                - 2D 仿真：1D (Nx,) 沿 y 均匀，或 2D (Ny, Nx)。

        Returns:
            BpmResult（含场快照、z 坐标、末场、功率守恒校验）。

        Raises:
            ValueError: 输入维度非法或与折射率分布不匹配（规则 14）。
            RuntimeError: 求解发散或 TBC 退化（由下层步进器抛出）。
        """
        psi_init_c = np.asarray(psi_init, dtype=np.complex128)
        n_arr_c = np.asarray(n_arr, dtype=np.complex128)

        if psi_init_c.ndim == 1:
            # 1D 仿真：折射率须为 1D (Nx,)
            if n_arr_c.ndim != 1:
                raise ValueError(f"1D 仿真 n_arr 须为 1D (Nx,)，实际 {n_arr_c.ndim}D（规则 14）")
            if psi_init_c.shape[0] != n_arr_c.shape[0]:
                raise ValueError(
                    f"psi_init 长度 {psi_init_c.shape[0]} 与 n_arr {n_arr_c.shape[0]} 不匹配（规则 14）"
                )
            snapshots, z_coords = self._solve_1d(psi_init_c, n_arr_c)
            n_dim = 1
            dy_for_power: float | None = None
        elif psi_init_c.ndim == 2:
            # 2D 仿真：折射率 1D (Nx,) 沿 y 均匀，或 2D (Ny, Nx)
            ny, nx = psi_init_c.shape
            if n_arr_c.ndim == 1:
                if n_arr_c.shape[0] != nx:
                    raise ValueError(
                        f"n_arr 长度 {n_arr_c.shape[0]} 与 psi_init x 维度 {nx} 不匹配（规则 14）"
                    )
            elif n_arr_c.ndim == 2:
                if n_arr_c.shape != psi_init_c.shape:
                    raise ValueError(
                        f"n_arr 形状 {n_arr_c.shape} 与 psi_init {psi_init_c.shape} 不匹配（规则 14）"
                    )
            else:
                raise ValueError(f"2D 仿真 n_arr 须为 1D 或 2D，实际 {n_arr_c.ndim}D（规则 14）")
            snapshots, z_coords = self._solve_2d(psi_init_c, n_arr_c)
            n_dim = 2
            dy_for_power = self.config.dy
        else:
            raise ValueError(f"psi_init 须为 1D 或 2D，实际 {psi_init_c.ndim}D（规则 14）")

        # 功率守恒校验（M2 验收点，A03 §7.3，向量化积分）
        final_field = snapshots[-1]
        power_initial = _compute_power(psi_init_c, self.config.dx, dy_for_power)
        power_final = _compute_power(final_field, self.config.dx, dy_for_power)
        if power_initial < 1e-300:
            raise ValueError("初始场功率 ≈ 0，无法计算功率守恒误差（场未归一化？规则 14）")
        power_conservation_error = abs(power_final - power_initial) / power_initial

        return BpmResult(
            snapshots=snapshots,
            z_coords=z_coords,
            final_field=final_field,
            power_initial=power_initial,
            power_final=power_final,
            power_conservation_error=power_conservation_error,
            n_dim=n_dim,
            n_steps=self.config.nz,
        )


def solve_bpm(
    psi_init: np.ndarray,
    n_arr: np.ndarray,
    config: BpmConfig,
) -> BpmResult:
    """便捷入口：一键求解 BPM 传播（A03 §6）。

    Args:
        psi_init: 初始场 ψ(z=0)，1D (Nx,) 或 2D (Ny, Nx)。
        n_arr: 折射率分布（与 psi_init 维度匹配规则见 BpmSolver.solve）。
        config: 求解配置（BpmConfig 实例）。

    Returns:
        BpmResult（含场快照、z 坐标、末场、功率守恒校验）。

    Raises:
        ValueError: 输入非法（规则 14）。
        RuntimeError: 求解发散或 TBC 退化。

    示例::

        from polaris.sim.bpm import BpmConfig, solve_bpm
        import numpy as np

        # 1D 自由空间高斯光束传播
        nx, dx = 256, 5e-8
        x = (np.arange(nx) - nx / 2) * dx
        psi0 = np.exp(-(x / (5e-6))**2)  # 高斯初始场
        n_arr = np.ones(nx) * 1.5         # 均匀折射率
        cfg = BpmConfig(wavelength=1.55e-6, dx=dx, dy=dx, nz=200, n_ref=1.5)
        result = solve_bpm(psi0, n_arr, cfg)
        print(f"功率守恒误差: {result.power_conservation_error:.2e}")  # < 1e-6
    """
    solver = BpmSolver(config=config)
    return solver.solve(psi_init=psi_init, n_arr=n_arr)
