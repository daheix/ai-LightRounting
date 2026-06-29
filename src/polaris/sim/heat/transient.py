"""瞬态热传导求解器（Crank-Nicolson 有限差分法，A07-HEAT §瞬态）。

求解瞬态热传导方程（含内热源）：
    ρ·Cp · ∂T/∂t = ∇·(k(x,y)·∇T) + Q(x,y,t)

采用 Crank-Nicolson（CN）隐式时间步进（2 阶时间精度，无条件稳定），
空间离散与稳态求解器一致：5 点有限差分 + 界面调和平均热导率。
每步求解稀疏线性方程组 (M + dt/2·L)·T^{n+1} = (M - dt/2·L)·T^n + dt·Q^{n+1/2}，
其中 M 为热容对角矩阵（集中质量矩阵），L 为稳态离散 Laplacian 矩阵（负定）。

Crank-Nicolson 格式（1947）：
    T^{n+1} - T^n   =  dt/(2ρCp) · [ L·T^{n+1} + L·T^n + 2·Q ]
→  (I - dt/(2ρCp)·L) · T^{n+1}  =  (I + dt/(2ρCp)·L) · T^n + dt/(ρCp)·Q
该格式为 2 阶时间精度且无条件稳定（A-稳定），优于显式 Euler（受 CFL 限制）
和全隐式 Euler（仅 1 阶精度）。参考文献见下方。

物理参数（Cocorullo 1999 / Incropera / CODATA 2018）：
- 硅热导率 k_Si = 148 W/(m·K)
- SiO2 热导率 k_SiO2 = 1.4 W/(m·K)
- 硅密度 ρ_Si = 2330 kg/m³
- SiO2 密度 ρ_SiO2 = 2200 kg/m³
- 硅定压热容 Cp_Si = 700 J/(kg·K)
- SiO2 定压热容 Cp_SiO2 = 740 J/(kg·K)
- 硅热扩散率 α_Si = k/(ρ·Cp) ≈ 9.07e-5 m²/s

文献来源（≥5，规则 18 学术诚信）：
1. Crank & Nicolson 1947 Proc Camb Phil Soc 43:50-67 —
   Crank-Nicolson 隐式方法原创论文 —
   https://doi.org/10.1017/S0305004100023197
2. Carslaw & Jaeger 1959 "Conduction of Heat in Solids" 2nd ed. Oxford —
   瞬态热传导 Green's 函数与解析解 §10.4 §14 —
   https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
3. Incropera & DeWitt "Fundamentals of Heat and Mass Transfer" —
   瞬态导热 §5 数值方法 §5.6 Crank-Nicolson —
   https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
4. Taflove & Hagness 2005 "Computational Electrodynamics" 3rd ed. —
   有限差分时域方法学（CN 格式稳定性分析同构适用）—
   https://us.artechhouse.com/Computational-Electrodynamics-The-FDTD-Method-Third-Edition-P1815.aspx
5. Cocorullo 1999 IEEE J Quantum Electron 35(5):791-799 —
   硅热光系数与器件热时间常数测量 —
   https://doi.org/10.1109/3.791939
6. Litz 2011 Optics Express 19(13):12997-13006 —
   光子集成器件瞬态自热仿真 —
   https://doi.org/10.1364/OE.19.012997
7. Coenen et al. 2024 Photonics 11(7):603 —
   Si 光子器件热光时间常数临界分析 —
   https://doi.org/10.3390/photonics11070603
8. scipy.sparse.linalg.spsolve —
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from polaris.sim.heat.boundary import BcSpec, BoundaryType, apply_boundary_conditions
from polaris.sim.heat.solver import (
    ADIABATIC,
    DN_DT_SI,
    K_SILICON,
    K_SIO2,
    HeatConfig,
    HeatResult,
    HeatSolver,
    _build_interior,
    _harmonic_mean,
    _side_applicable,
    solve_heat,
)

__all__ = [
    "TransientHeatConfig",
    "TransientHeatResult",
    "TransientHeatSolver",
    "solve_transient_heat",
    "thermal_time_constant_1d",
    # 材料热物性常量
    "RHO_SILICON",
    "RHO_SIO2",
    "CP_SILICON",
    "CP_SIO2",
    "ALPHA_SILICON",
]

# =============================================================================
# 材料热物性常量（Cocorullo 1999 / Incropera / CRC Handbook）
# =============================================================================
RHO_SILICON: float = 2330.0  # 硅密度 [kg/m³]
RHO_SIO2: float = 2200.0  # SiO2 密度 [kg/m³]
CP_SILICON: float = 700.0  # 硅定压热容 [J/(kg·K)]
CP_SIO2: float = 740.0  # SiO2 定压热容 [J/(kg·K)]
ALPHA_SILICON: float = K_SILICON / (RHO_SILICON * CP_SILICON)  # 硅热扩散率 [m²/s]


@dataclass
class TransientHeatConfig:
    """瞬态热传导求解配置。

    Attributes:
        heat_config: 稳态热配置（含 k_arr, q_arr, bc_dict, dx, dy）。
            q_arr 可视为 t=0 时的热源；时变热源通过 heater_func 提供。
        rho_arr: 密度场 (nx, ny) [kg/m³]，全正。
        cp_arr: 定压热容场 (nx, ny) [J/(kg·K)]，全正。
        t_initial: 初始温度场 (nx, ny) [K] 或标量（均匀初始温度）。
        t_final: 终止时间 [s]，> 0。
        dt: 时间步长 [s]，> 0。CN 格式无条件稳定，但精度受 dt 限制。
        heater_func: 时变体积热源函数 Q(t, x_idx, y_idx) -> float [W/m³]，
            或 None（使用 heat_config.q_arr 作为恒定热源）。
            签名：heater_func(t: float) -> np.ndarray（返回与 k_arr 同形状的热源场）。
        save_every: 每隔多少步保存一次温度场（默认 1，即每步都存）。
            为降低内存占用，大仿真可设为 >1 的整数。
    """

    heat_config: HeatConfig
    rho_arr: np.ndarray
    cp_arr: np.ndarray
    t_initial: float | np.ndarray = 300.0
    t_final: float = 1e-6
    dt: float = 1e-8
    heater_func: callable | None = None
    save_every: int = 1

    def __post_init__(self) -> None:
        if self.rho_arr.shape != self.heat_config.k_arr.shape:
            raise ValueError(
                f"rho_arr {self.rho_arr.shape} 与 k_arr "
                f"{self.heat_config.k_arr.shape} 形状不匹配"
            )
        if self.cp_arr.shape != self.heat_config.k_arr.shape:
            raise ValueError(
                f"cp_arr {self.cp_arr.shape} 与 k_arr "
                f"{self.heat_config.k_arr.shape} 形状不匹配"
            )
        if not np.all(np.isfinite(self.rho_arr)) or np.any(self.rho_arr <= 0.0):
            raise ValueError("rho_arr 须全为有限正值（密度物理约束）")
        if not np.all(np.isfinite(self.cp_arr)) or np.any(self.cp_arr <= 0.0):
            raise ValueError("cp_arr 须全为有限正值（热容物理约束）")
        if self.t_final <= 0.0:
            raise ValueError(f"t_final 须 > 0，实际 {self.t_final}")
        if self.dt <= 0.0:
            raise ValueError(f"dt 须 > 0，实际 {self.dt}")
        if self.dt > self.t_final:
            raise ValueError(
                f"dt ({self.dt}) 不应大于 t_final ({self.t_final})"
            )
        if self.save_every < 1:
            raise ValueError(f"save_every 须 ≥ 1，实际 {self.save_every}")
        # 初始温度场校验与广播
        if np.isscalar(self.t_initial):
            t0 = float(self.t_initial)
            if not np.isfinite(t0):
                raise ValueError("t_initial 非有限值")
            object.__setattr__(
                self,
                "t_initial",
                np.full(self.heat_config.k_arr.shape, t0, dtype=float),
            )
        else:
            t0_arr = np.asarray(self.t_initial, dtype=float)
            if t0_arr.shape != self.heat_config.k_arr.shape:
                raise ValueError(
                    f"t_initial {t0_arr.shape} 与 k_arr "
                    f"{self.heat_config.k_arr.shape} 形状不匹配"
                )
            if not np.all(np.isfinite(t0_arr)):
                raise ValueError("t_initial 含非有限值")
            object.__setattr__(self, "t_initial", t0_arr)


@dataclass
class TransientHeatResult:
    """瞬态热求解结果。

    Attributes:
        times: 时间点数组 [s]，shape (n_times,)。
        temperatures: 温度场序列 [K]，shape (n_times, nx, ny)。
        dx, dy: 空间网格间距 [m]。
        dt: 时间步长 [s]。
    """

    times: np.ndarray
    temperatures: np.ndarray
    dx: float
    dy: float
    dt: float

    def __post_init__(self) -> None:
        if self.temperatures.ndim != 3:
            raise ValueError(
                f"temperatures 须为 3D (n_times, nx, ny)，"
                f"实际 {self.temperatures.ndim}D"
            )
        if self.times.shape[0] != self.temperatures.shape[0]:
            raise ValueError(
                f"times 长度 {self.times.shape[0]} 与 temperatures "
                f"第 0 维 {self.temperatures.shape[0]} 不匹配"
            )
        if not np.all(np.isfinite(self.temperatures)):
            raise ValueError("温度场含非有限值（瞬态求解失败）")
        if not np.all(np.isfinite(self.times)):
            raise ValueError("时间数组含非有限值")

    def temperature_at(self, t: float) -> np.ndarray:
        """获取指定时刻的温度场（线性插值）。

        Args:
            t: 查询时间 [s]。

        Returns:
            温度场 (nx, ny) [K]。
        """
        if t < self.times[0] or t > self.times[-1]:
            raise ValueError(
                f"t={t} 超出仿真时间范围 [{self.times[0]}, {self.times[-1]}]"
            )
        idx = np.searchsorted(self.times, t) - 1
        idx = max(0, min(idx, len(self.times) - 2))
        t0, t1 = self.times[idx], self.times[idx + 1]
        if t1 == t0:
            return self.temperatures[idx]
        alpha = (t - t0) / (t1 - t0)
        return (1.0 - alpha) * self.temperatures[idx] + alpha * self.temperatures[idx + 1]

    def max_temperature_vs_time(self) -> tuple[np.ndarray, np.ndarray]:
        """返回 (times, T_max(t)) 最大温度随时间变化曲线。"""
        t_max = np.array([np.max(T) for T in self.temperatures])
        return self.times, t_max

    def steady_state_approx(self, rtol: float = 1e-4) -> np.ndarray | None:
        """判断是否达到稳态（最后两步最大温度相对变化 < rtol）。

        Returns:
            若达到稳态则返回最后一步温度场，否则返回 None。
        """
        if len(self.temperatures) < 2:
            return None
        T_last = self.temperatures[-1]
        T_prev = self.temperatures[-2]
        max_change = np.max(np.abs(T_last - T_prev))
        scale = np.max(np.abs(T_last)) + 1e-30
        if max_change / scale < rtol:
            return T_last
        return None


class TransientHeatSolver:
    """瞬态热传导求解器（Crank-Nicolson 隐式方法）。

    求解 ρ·Cp · ∂T/∂t = ∇·(k∇T) + Q(x,y,t)
    空间离散：5 点有限差分 + 界面调和平均热导率（与稳态求解器一致）
    时间离散：Crank-Nicolson 2 阶精度，无条件稳定
    求解器：scipy.sparse.linalg.spsolve 稀疏直接解

    用法：
        cfg = TransientHeatConfig(heat_config, rho_arr, cp_arr, ...)
        result = TransientHeatSolver().solve(cfg)
    """

    def solve(self, config: TransientHeatConfig) -> TransientHeatResult:
        """求解瞬态温度场时间序列。

        Args:
            config: 瞬态热配置。

        Returns:
            TransientHeatResult（含 times 与 temperatures）。

        Raises:
            ValueError: 参数非法、系统奇异或求解发散（含非有限值）。
        """
        hc = config.heat_config
        nx, ny = hc.k_arr.shape
        n = nx * ny
        dx, dy = hc.dx, hc.dy

        # 1. 构建离散热传导算子 A（与稳态内部矩阵相同）
        # A_interior · T = ∇·(k∇T) 的 5 点差分离散（W/m³）
        # 稳态方程：A_interior · T + q_v = 0
        A_interior, _ = _build_interior(hc)

        # 2. 构建单位体积热容对角矩阵 M = diag(ρ·Cp)（集中质量矩阵）
        # 瞬态方程：ρ·Cp · ∂T/∂t = ∇·(k∇T) + q_v
        # 所有项单位均为 W/m³（体积功率密度）
        rho_cp = config.rho_arr * config.cp_arr  # (nx, ny) J/(m³·K)
        diag_vals = rho_cp.ravel()
        M_mat = sparse.diags(diag_vals, 0, shape=(n, n), format="csr")

        # 3. 初始温度场
        T_vec = np.asarray(config.t_initial, dtype=float).ravel().copy()
        if not np.all(np.isfinite(T_vec)):
            raise ValueError("初始温度场含非有限值")

        # 4. 时间步数与保存数组分配
        dt = config.dt
        n_steps = int(np.ceil(config.t_final / dt))
        save_every = max(1, int(config.save_every))

        saved_times: list[float] = []
        saved_temps: list[np.ndarray] = []

        # 保存初始时刻
        saved_times.append(0.0)
        saved_temps.append(T_vec.reshape(nx, ny).copy())

        # 5. 构建 Crank-Nicolson 矩阵
        # 瞬态方程：M · dT/dt = A · T + q
        # CN 格式（2 阶时间精度，无条件稳定）：
        #   M·(T^{n+1} - T^n)/dt = 0.5·A·(T^{n+1} + T^n) + q_half
        # 整理：
        #   (M - 0.5·dt·A) · T^{n+1} = (M + 0.5·dt·A) · T^n + dt·q_half
        A_lhs = M_mat - (dt / 2.0) * A_interior
        A_rhs_mat = M_mat + (dt / 2.0) * A_interior

        # 6. 时间步进
        t = 0.0
        q_const = hc.q_arr.ravel().astype(float, copy=True)

        for step in range(1, n_steps + 1):
            dt_actual = min(dt, config.t_final - t)
            if dt_actual <= 0:
                break

            if abs(dt_actual - dt) > 1e-12 * dt:
                A_lhs_step = M_mat - (dt_actual / 2.0) * A_interior
                A_rhs_step = M_mat + (dt_actual / 2.0) * A_interior
            else:
                A_lhs_step = A_lhs
                A_rhs_step = A_rhs_mat

            # 计算半时间步的热源 Q(t + dt/2)
            t_half = t + dt_actual / 2.0
            if config.heater_func is not None:
                q_half = np.asarray(
                    config.heater_func(t_half), dtype=float
                ).ravel()
                if q_half.shape != (n,):
                    raise ValueError(
                        f"heater_func 返回形状 {q_half.shape}，"
                        f"期望 ({n},) 或 (nx, ny)"
                    )
            else:
                q_half = q_const

            # 右端向量：RHS = A_rhs · T^n + dt · Q_half
            b_vec = A_rhs_step.dot(T_vec) + dt_actual * q_half

            # 应用边界条件（Dirichlet 行替换到 A_lhs 与 b_vec）
            # 注意：边界条件也需在 CN 格式中处理，这里采用简单方法：
            # 对 Dirichlet 边界节点，强制 T^{n+1} = T_boundary（精确满足）
            # 通过行替换实现，与稳态求解器一致。
            # 先构造完整的 A_lhs（含边界），再对边界节点行替换。
            A_lhs_bc, b_bc = apply_boundary_conditions(
                A_lhs_step.copy(), b_vec.copy(), hc
            )

            # 求解 T^{n+1}
            T_new = spsolve(A_lhs_bc, b_bc)
            if not np.all(np.isfinite(T_new)):
                raise RuntimeError(
                    f"瞬态求解第 {step} 步失败：温度场含非有限值"
                    f"（系统奇异或时间步长问题）"
                )

            T_vec = T_new
            t += dt_actual

            # 保存
            if step % save_every == 0 or step == n_steps:
                saved_times.append(t)
                saved_temps.append(T_vec.reshape(nx, ny).copy())

        # 8. 组装结果
        times_arr = np.array(saved_times, dtype=float)
        temps_arr = np.stack(saved_temps, axis=0)  # (n_times, nx, ny)

        return TransientHeatResult(
            times=times_arr,
            temperatures=temps_arr,
            dx=dx,
            dy=dy,
            dt=dt,
        )


def solve_transient_heat(config: TransientHeatConfig) -> TransientHeatResult:
    """便捷函数：单步求解瞬态热传导。"""
    return TransientHeatSolver().solve(config)


def thermal_time_constant_1d(
    thickness: float,
    thermal_conductivity: float = K_SILICON,
    rho: float = RHO_SILICON,
    cp: float = CP_SILICON,
) -> float:
    """1D 平板热时间常数解析估计（τ ≈ L²/(π²·α)，基模衰减）。

    对于厚度为 L 的薄板，两侧固定温度或绝热时，瞬态热响应的
    主时间常数由导热方程分离变量的基模给出：
        τ = L² / (π² · α)
    其中 α = k/(ρ·Cp) 为热扩散率。

    参考：Carslaw & Jaeger 1959 §5.2 §10.4；Incropera §5.5。

    Args:
        thickness: 特征厚度 [m]。
        thermal_conductivity: 热导率 [W/(m·K)]，默认硅。
        rho: 密度 [kg/m³]，默认硅。
        cp: 定压热容 [J/(kg·K)]，默认硅。

    Returns:
        τ 热时间常数 [s]。
    """
    if thickness <= 0.0:
        raise ValueError(f"thickness 须 > 0，实际 {thickness}")
    alpha = thermal_conductivity / (rho * cp)
    return thickness**2 / (np.pi**2 * alpha)
