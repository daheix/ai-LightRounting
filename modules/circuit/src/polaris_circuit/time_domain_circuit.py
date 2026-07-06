"""时域光子电路仿真模块。

对齐 Aspic/PICWave（时域）+ VPIphotonics（TLLM）。
包含: YeeGrid / FDTDSimulator / NonlinearModel / TimeDomainCircuitSimulator / PMLBoundary。

来源:
- Yee 1966 IEEE TAP: https://ieeexplore.ieee.org/document/1138693
- Berenger 1994 JCP: https://doi.org/10.1006/jcph.1994.1159
- Courant 1928: https://link.springer.com/article/10.1007/BF01448839
- Lowery 1987 IEE Proc. J: https://digital-library.theiet.org/doi/abs/10.1049/ip-j-1.1987.0062
- Lin et al., Opt. Express 2007: https://opg.optica.org/oe/fulltext.cfm?uri=oe-15-6-3454
- Boyd, Nonlinear Optics, 4th ed., §4

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO /
R13 不保留 v4 兼容 / 函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 物理常量（来源: NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/）
C0 = 2.99792458e8  # 真空光速 m/s
EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
MU0 = 1.25663706212e-6  # 真空磁导率 H/m


@dataclass
class YeeGrid:
    """Yee 交错网格（E/H 场空间交错）。

    场分量位置（2D TMz 模式）:
    - Ex: (i, j+1/2) → 数组形状 (nx, ny+1)
    - Ey: (i+1/2, j) → 数组形状 (nx+1, ny)
    - Hz: (i+1/2, j+1/2) → 数组形状 (nx, ny)

    来源: Yee, IEEE Trans. Antennas Propag. AP-14(3), 302-307 (1966)
    https://ieeexplore.ieee.org/document/1138693
    """

    nx: int
    ny: int
    dx: float
    dy: float
    Ex: np.ndarray | None = None
    Ey: np.ndarray | None = None
    Hz: np.ndarray | None = None

    def __post_init__(self) -> None:
        """初始化后校验并分配场数组。"""
        if self.nx <= 0:
            raise ValueError(f"nx 必须 > 0，实际 {self.nx}")
        if self.ny <= 0:
            raise ValueError(f"ny 必须 > 0，实际 {self.ny}")
        if self.dx <= 0:
            raise ValueError(f"dx 必须 > 0，实际 {self.dx}")
        if self.dy <= 0:
            raise ValueError(f"dy 必须 > 0，实际 {self.dy}")
        self.Ex = np.zeros((self.nx, self.ny + 1), dtype=np.float64)
        self.Ey = np.zeros((self.nx + 1, self.ny), dtype=np.float64)
        self.Hz = np.zeros((self.nx, self.ny), dtype=np.float64)


class PMLBoundary:
    """PML 吸收边界（Berenger 1994）。

    在边界层内对电磁场施加指数衰减，模拟完美匹配层吸收。
    简化实现：用导电率渐变实现场衰减。

    来源: Berenger, J. Comput. Phys. 114(2), 185-200 (1994)
    https://doi.org/10.1006/jcph.1994.1159
    """

    def __init__(self, thickness: int = 10, sigma: float = 1.0) -> None:
        """初始化 PML 吸收边界。

        Args:
            thickness: PML 层厚度（网格数）。
            sigma: 衰减系数（越大吸收越强）。
        """
        if thickness <= 0:
            raise ValueError(f"thickness 必须 > 0，实际 {thickness}")
        if sigma <= 0:
            raise ValueError(f"sigma 必须 > 0，实际 {sigma}")
        self.thickness = thickness
        self.sigma = sigma

    def apply(self, grid: YeeGrid) -> None:
        """应用 PML 吸收边界条件（对边界层场施加衰减）。"""
        t = min(self.thickness, grid.nx, grid.ny)
        for i in range(t):
            decay = float(np.exp(-self.sigma * (t - i) / t))
            grid.Ex[i, :] *= decay
            grid.Hz[i, :] *= decay
            grid.Ex[-(i + 1), :] *= decay
            grid.Hz[-(i + 1), :] *= decay
        for j in range(t):
            decay = float(np.exp(-self.sigma * (t - j) / t))
            grid.Ey[:, j] *= decay
            grid.Hz[:, j] *= decay
            grid.Ey[:, -(j + 1)] *= decay
            grid.Hz[:, -(j + 1)] *= decay


class FDTDSimulator:
    """2D FDTD 时域仿真器（Yee 1966 算法 + PML 吸收边界）。

    实现 2D TMz 模式（Ex, Ey, Hz）的 FDTD 时域更新：
    1. 法拉第定律: ∂H/∂t = -(1/μ) ∇×E → 更新 Hz
    2. 安培定律: ∂E/∂t = (1/ε) ∇×H → 更新 Ex, Ey
    3. PML 吸收边界处理开放边界

    来源:
    - Yee 1966 IEEE TAP: https://ieeexplore.ieee.org/document/1138693
    - Berenger 1994 PML: https://doi.org/10.1006/jcph.1994.1159
    - Taflove, Computational Electrodynamics, 3rd ed.
    """

    def __init__(
        self,
        grid: YeeGrid,
        epsilon_r: np.ndarray,
        mu_r: np.ndarray | None = None,
        pml: PMLBoundary | None = None,
    ) -> None:
        """初始化 FDTD 仿真器。

        Args:
            grid: Yee 网格。
            epsilon_r: 相对介电常数分布 (nx, ny)。
            mu_r: 相对磁导率分布（默认全 1）。
            pml: PML 吸收边界（默认厚度 10）。
        """
        if epsilon_r.shape != (grid.nx, grid.ny):
            raise ValueError(f"epsilon_r 形状 {epsilon_r.shape} != ({grid.nx}, {grid.ny})")
        if np.any(epsilon_r <= 0):
            raise ValueError("epsilon_r 所有元素必须 > 0")
        self.grid = grid
        self.epsilon_r = epsilon_r
        self.mu_r = np.ones_like(epsilon_r) if mu_r is None else mu_r
        if self.mu_r.shape != (grid.nx, grid.ny):
            raise ValueError(f"mu_r 形状 {self.mu_r.shape} != ({grid.nx}, {grid.ny})")
        if np.any(self.mu_r <= 0):
            raise ValueError("mu_r 所有元素必须 > 0")
        self.eps = EPS0 * self.epsilon_r
        self.mu = MU0 * self.mu_r
        self.pml = pml if pml is not None else PMLBoundary()

    @staticmethod
    def cfl_condition(dx: float, dy: float, c: float = C0) -> float:
        """计算 CFL 稳定性条件允许的最大时间步长。

        公式: dt <= 1 / (c * sqrt(1/dx^2 + 1/dy^2))

        来源: Courant, Friedrichs, Lewy 1928 Math. Ann. 100(1), 32-74
        https://link.springer.com/article/10.1007/BF01448839
        """
        if dx <= 0 or dy <= 0:
            raise ValueError("dx, dy 必须 > 0")
        return 1.0 / (c * np.sqrt(1.0 / dx**2 + 1.0 / dy**2))

    def step(self, dt: float) -> None:
        """单步 FDTD 更新（Yee 算法）: 更新 H 场 → E 场 → PML。

        Raises:
            ValueError: dt 违反 CFL 条件。
            RuntimeError: 数值不稳定（NaN/Inf）。
        """
        dt_max = self.cfl_condition(self.grid.dx, self.grid.dy)
        if dt > dt_max:
            raise ValueError(f"dt={dt:.3e} 违反 CFL 条件（最大 {dt_max:.3e}）")
        g = self.grid
        g.Hz += (dt / self.mu) * (
            (g.Ey[1:, :] - g.Ey[:-1, :]) / g.dx
            - (g.Ex[:, 1:] - g.Ex[:, :-1]) / g.dy
        )
        g.Ex[:, 1:-1] += (dt / self.eps[:, :-1]) * (
            g.Hz[:, 1:] - g.Hz[:, :-1]
        ) / g.dy
        g.Ey[1:-1, :] += -(dt / self.eps[:-1, :]) * (
            g.Hz[1:, :] - g.Hz[:-1, :]
        ) / g.dx
        self.pml.apply(g)
        if not np.all(np.isfinite(g.Ex)):
            raise RuntimeError("FDTD 仿真数值不稳定（Ex 含 NaN/Inf）")
        if not np.all(np.isfinite(g.Hz)):
            raise RuntimeError("FDTD 仿真数值不稳定（Hz 含 NaN/Inf）")

    def run(
        self, n_steps: int, source_pos: tuple[int, int], source_freq: float,
    ) -> dict:
        """运行 FDTD 仿真。

        Args:
            n_steps: 仿真步数。
            source_pos: 源位置 (i, j)。
            source_freq: 源频率 (Hz)。

        Returns:
            {"E": np.ndarray, "H": np.ndarray, "t": np.ndarray}

        Raises:
            ValueError: 参数无效。
        """
        if n_steps <= 0:
            raise ValueError(f"n_steps 必须 > 0，实际 {n_steps}")
        if source_freq <= 0:
            raise ValueError(f"source_freq 必须 > 0，实际 {source_freq}")
        si, sj = source_pos
        if not (0 <= si < self.grid.nx and 0 <= sj < self.grid.ny):
            raise ValueError(f"source_pos {source_pos} 超出网格范围 ({self.grid.nx}, {self.grid.ny})")
        dt_max = self.cfl_condition(self.grid.dx, self.grid.dy)
        dt = 0.95 * dt_max
        e_history = np.zeros((n_steps, self.grid.nx, self.grid.ny))
        h_history = np.zeros((n_steps, self.grid.nx, self.grid.ny))
        t_history = np.zeros(n_steps)
        for n in range(n_steps):
            t = n * dt
            self.grid.Ex[si, sj] += np.sin(2 * np.pi * source_freq * t)
            self.step(dt)
            e_history[n] = self.grid.Ex[:, :-1]
            h_history[n] = self.grid.Hz
            t_history[n] = t
        return {"E": e_history, "H": h_history, "t": t_history}


@dataclass
class NonlinearModel:
    """非线性效应模型（Kerr/TPA/自由载流子色散）。

    硅波导典型非线性参数（1.55μm 波段）。

    来源:
    - Lin et al., Opt. Express 15(6), 3454-3460 (2007)
      https://opg.optica.org/oe/fulltext.cfm?uri=oe-15-6-3454
    - Boyd, Nonlinear Optics, 4th ed., §4
    """

    n2: float = 6e-18  # Kerr 系数 (m^2/W), 硅典型值
    beta_tpa: float = 0.8e-11  # TPA 系数 (m/W), 硅典型值
    tau_c: float = 1e-9  # 自由载流子寿命 (s)

    def kerr_phase(self, I, L: float, wavelength: float) -> np.ndarray:  # noqa: E741
        """Kerr 自相位调制相位。

        公式: phi_NL = 2*pi*n2*I*L / wavelength
        来源: Boyd, Nonlinear Optics, 4th ed., Eq.(4.1-5)
        """
        I_arr = np.asarray(I, dtype=np.float64)
        if np.any(I_arr < 0):
            raise ValueError("光强 I 所有元素必须 >= 0")
        if L < 0:
            raise ValueError(f"长度 L 必须 >= 0，实际 {L}")
        if wavelength <= 0:
            raise ValueError(f"wavelength 必须 > 0，实际 {wavelength}")
        return 2 * np.pi * self.n2 * I_arr * L / wavelength

    def tpa_loss(self, I, L: float) -> np.ndarray:  # noqa: E741
        """TPA 损耗系数。

        公式: alpha_tpa = beta_tpa * I
        来源: Lin et al., Opt. Express 2007, Eq.(2)
        """
        I_arr = np.asarray(I, dtype=np.float64)
        if np.any(I_arr < 0):
            raise ValueError("光强 I 所有元素必须 >= 0")
        if L < 0:
            raise ValueError(f"长度 L 必须 >= 0，实际 {L}")
        return self.beta_tpa * I_arr

    def fcd_effect(self, N_c, wavelength: float) -> tuple[np.ndarray, np.ndarray]:
        """自由载流子色散效应。

        返回 (delta_n, delta_alpha)
        公式: delta_n = -sigma_r * N_c, delta_alpha = sigma_i * N_c

        硅典型值（1.55μm，来源: Lin et al. 2007）:
        - sigma_r ≈ 1.35e-27 m³
        - sigma_i ≈ 2.0e-20 m²
        """
        N_arr = np.asarray(N_c, dtype=np.float64)
        if np.any(N_arr < 0):
            raise ValueError("N_c 所有元素必须 >= 0")
        if wavelength <= 0:
            raise ValueError(f"wavelength 必须 > 0，实际 {wavelength}")
        sigma_r = 1.35e-27
        sigma_i = 2.0e-20
        delta_n = -sigma_r * N_arr
        delta_alpha = sigma_i * N_arr
        return (delta_n, delta_alpha)


class TimeDomainCircuitSimulator:
    """时域电路仿真器（TLLM 风格 + 非线性）。

    基于传输线激光器模型（TLLM）思想，将波导/器件分段，
    用时域脉冲传播仿真电路级响应。避免 FDTD 全波仿真的计算量爆炸。

    来源:
    - Lowery 1987 IEE Proc. J 134(5), 281-289
      https://digital-library.theiet.org/doi/abs/10.1049/ip-j-1.1987.0062
    - VPIphotonics 白皮书: https://www.vpiphotonics.com/
    """

    def __init__(self, dt: float = 1e-14, n_steps: int = 1000) -> None:
        """初始化时域电路仿真器。

        Args:
            dt: 时间步长 (s)。
            n_steps: 仿真步数。

        Raises:
            ValueError: 参数无效。
        """
        if dt <= 0:
            raise ValueError(f"dt 必须 > 0，实际 {dt}")
        if n_steps <= 0:
            raise ValueError(f"n_steps 必须 > 0，实际 {n_steps}")
        self.dt = dt
        self.n_steps = n_steps

    def simulate_waveguide(
        self,
        length: float,
        input_signal: np.ndarray,
        neff: float = 2.4,
        alpha: float = 0.0,
        nonlinear: NonlinearModel | None = None,
    ) -> np.ndarray:
        """仿真波导时域传输。

        1. 信号沿波导传播，时延 = neff * length / c
        2. 应用损耗衰减
        3. 应用非线性效应（Kerr/TPA）
        """
        if length < 0:
            raise ValueError(f"length 必须 >= 0，实际 {length}")
        if neff <= 0:
            raise ValueError(f"neff 必须 > 0，实际 {neff}")
        if alpha < 0:
            raise ValueError(f"alpha 必须 >= 0，实际 {alpha}")
        sig = np.asarray(input_signal, dtype=np.complex128)
        delay = neff * length / C0
        n_delay = int(delay / self.dt)
        output = np.zeros_like(sig)
        n = len(sig)
        if n_delay < n:
            output[n_delay:] = sig[: n - n_delay]
        elif n_delay == 0:
            output = sig.copy()
        if alpha > 0 and length > 0:
            attenuation = 10 ** (-alpha * length / 20)
            output *= attenuation
        if nonlinear is not None and length > 0:
            wavelength = 1.55e-6
            I = np.abs(output) ** 2  # noqa: E741
            phase = nonlinear.kerr_phase(I, length, wavelength)
            output *= np.exp(1j * phase)
            tpa_alpha = nonlinear.tpa_loss(I, length)
            output *= np.exp(-tpa_alpha * length / 2)
        return output

    def simulate_mzi(
        self,
        input_signal: np.ndarray,
        arm_length_diff: float,
        neff: float = 2.4,
    ) -> np.ndarray:
        """仿真 MZI 时域响应（双臂干涉）。

        MZI 结构: 输入 → 50:50 分束 → 两臂（臂长差）→ 50:50 合束 → 输出
        """
        if arm_length_diff < 0:
            raise ValueError(f"arm_length_diff 必须 >= 0，实际 {arm_length_diff}")
        if neff <= 0:
            raise ValueError(f"neff 必须 > 0，实际 {neff}")
        sig = np.asarray(input_signal, dtype=np.complex128)
        arm1 = sig / np.sqrt(2)
        arm2 = sig / np.sqrt(2)
        delay_diff = neff * arm_length_diff / C0
        n_delay = int(delay_diff / self.dt)
        delayed_arm2 = np.zeros_like(arm2)
        n = len(arm2)
        if n_delay < n:
            delayed_arm2[n_delay:] = arm2[: n - n_delay]
        return (arm1 + delayed_arm2) / np.sqrt(2)


def run_time_domain_circuit(
    input_signal: np.ndarray,
    length: float,
    dt: float = 1e-14,
    neff: float = 2.4,
    alpha: float = 0.0,
    nonlinear: NonlinearModel | None = None,
) -> np.ndarray:
    """时域电路仿真便利入口（统一 API）。

    对输入信号执行波导时域传输仿真，支持损耗和非线性效应。

    Args:
        input_signal: 输入信号（复数数组）。
        length: 波导长度 (m)。
        dt: 时间步长 (s)。
        neff: 有效折射率。
        alpha: 损耗系数 (dB/m)。
        nonlinear: 非线性模型，None 表示线性仿真。

    Returns:
        输出信号（与输入同形状）。
    """
    sim = TimeDomainCircuitSimulator(dt=dt, n_steps=len(input_signal))
    return sim.simulate_waveguide(
        length=length,
        input_signal=input_signal,
        neff=neff,
        alpha=alpha,
        nonlinear=nonlinear,
    )


__all__ = [
    "YeeGrid",
    "PMLBoundary",
    "FDTDSimulator",
    "NonlinearModel",
    "TimeDomainCircuitSimulator",
    "run_time_domain_circuit",
    "C0",
    "EPS0",
    "MU0",
]
