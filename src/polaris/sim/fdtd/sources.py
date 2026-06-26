"""FDTD 时域源（A09 §6 光源注入）。

实现 3 类时域波形源 + 1 类点源（覆盖 T01 Lumerical / T04 Tidy3D / T16 SimWorks
光源集的基础子集）：
- GaussianPulse  : 高斯调制脉冲（A09 §6 标准波形 E0·sin(2πf0 t)·exp(-(t-t0)²/τ²)）
- ContinuousWave : 连续波（带可选线性斜坡避免突变激励引入 DC 分量）
- RickerWavelet  : Ricker 小波（高斯导数，无 DC 分量，宽带单脉冲）
- DipoleSource   : 软点源（Hertzian dipole，J_z δ 函数注入）

所有波形实现为可调用对象（__call__），供 TFSF / 模式源 / 偶极子统一调用。
波形为纯函数（无状态），满足§5.1 纯函数优先原则，便于并行与测试。

软源注入（Taflove 2005 §5.5）：
    E_z[i_src] += g(t)  （叠加，避免硬源反射干扰）
偶极子：J_amp = I·dl / (dx·dy)，E += J_amp·g(t)·Δt/ε

DC 分量考量：纯高斯包络 sin 载波在 t→∞ 残留 DC（Ricker 小波无此问题）；
连续波用线性斜坡（前 N_sstep 步线性增长振幅）降低起始瞬态。

文献来源（≥5，规则 18 学术诚信）：
1. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
2. Taflove & Hagness 2005 Computational Electrodynamics §5（软源与 TFSF）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
3. Shin & Fan 2012 J Comput Phys 231 3406-3431 —
   https://doi.org/10.1016/j.jcp.2011.12.037
4. Gedney 1996 IEEE Trans AP 44(12) 1630-1639 —
   https://doi.org/10.1109/8.546242
5. Lumerical FDTD Sources —
   https://optics.ansys.com/hc/en-us/categories/360001366534
6. MEEP FDTD Sources —
   https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. Roden & Gedney 2000 CPML —
   https://doi.org/10.1002/1099-1207(20000612)12:3<284::AID-MMPS5>3.0.CO;2-K

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

__all__ = [
    "Waveform",
    "GaussianPulse",
    "ContinuousWave",
    "RickerWavelet",
    "DipoleSource",
    "inject_dipole",
]


class Waveform(Protocol):
    """时域波形协议（可调用，t→振幅，纯函数）。"""

    def __call__(self, t: float | np.ndarray) -> float | np.ndarray:
        """计算时刻 t（秒）的波形振幅。"""
        ...

    @property
    def center_frequency(self) -> float:
        """波形中心频率（Hz）。"""
        ...

    @property
    def center_time(self) -> float:
        """波形中心时刻（秒，脉冲峰值近似位置）。"""
        ...

    @property
    def bandwidth(self) -> float:
        """波形 -3dB 带宽估计（Hz）。"""
        ...


@dataclass(frozen=True)
class GaussianPulse:
    """高斯调制脉冲（A09 §6 标准源波形）。

    g(t) = E0 · sin(2π·f0·t) · exp(-(t - t0)² / τ²)

    高斯包络保证有限时宽，宽频谱（单次仿真覆盖整个频带）。
    τ 与带宽关系：Δf ≈ 1/(2πτ)（-3dB 带宽，傅里叶变换性质）。

    Attributes:
        amplitude: 峰值振幅 E0（V/m）。
        frequency: 中心频率 f0（Hz），>0。
        t0: 脉冲中心时刻（秒），建议 ≥ 5τ 以保证起始平滑。
        tau: 高斯包络时间常数 τ（秒），>0，决定脉冲宽度与带宽。
    """

    amplitude: float
    frequency: float
    t0: float
    tau: float

    def __post_init__(self) -> None:
        if self.amplitude < 0.0:
            raise ValueError(f"振幅须 ≥0，实际 {self.amplitude}")
        if self.frequency <= 0.0:
            raise ValueError(f"中心频率须 >0，实际 {self.frequency}")
        if self.tau <= 0.0:
            raise ValueError(f"tau 须 >0，实际 {self.tau}")
        if self.t0 < 0.0:
            raise ValueError(f"t0 须 ≥0，实际 {self.t0}")

    @property
    def center_frequency(self) -> float:
        """中心频率 f0（Hz）。"""
        return self.frequency

    @property
    def center_time(self) -> float:
        """脉冲中心时刻 t0（秒）。"""
        return self.t0

    @property
    def bandwidth(self) -> float:
        """-3dB 带宽 Δf ≈ 1/(2πτ)（Hz，傅里叶变换性质）。"""
        return 1.0 / (2.0 * np.pi * self.tau)

    def __call__(self, t: float | np.ndarray) -> float | np.ndarray:
        """计算高斯调制脉冲 g(t)。"""
        return (
            self.amplitude
            * np.sin(2.0 * np.pi * self.frequency * t)
            * np.exp(-((t - self.t0) ** 2) / (self.tau**2))
        )


@dataclass(frozen=True)
class ContinuousWave:
    """连续波（CW）源，带线性斜坡避免起始突变。

    g(t) = E0 · min(t/t_ramp, 1.0) · sin(2π·f0·t)

    斜坡前 t_ramp 秒内振幅线性增长，避免硬启动引入宽频带瞬态。
    适用于稳态响应提取（需仿真时长 ≥ t_ramp + 数个周期）。

    Attributes:
        amplitude: 稳态振幅 E0（V/m）。
        frequency: 频率 f0（Hz），>0。
        ramp_time: 线性斜坡时长 t_ramp（秒），≥0（0 表示硬启动）。
        phase: 初始相位（rad），默认 0。
    """

    amplitude: float
    frequency: float
    ramp_time: float = 0.0
    phase: float = 0.0

    def __post_init__(self) -> None:
        if self.amplitude < 0.0:
            raise ValueError(f"振幅须 ≥0，实际 {self.amplitude}")
        if self.frequency <= 0.0:
            raise ValueError(f"频率须 >0，实际 {self.frequency}")
        if self.ramp_time < 0.0:
            raise ValueError(f"斜坡时长须 ≥0，实际 {self.ramp_time}")

    @property
    def center_frequency(self) -> float:
        """频率 f0（Hz）。"""
        return self.frequency

    @property
    def center_time(self) -> float:
        """中心时刻取斜坡结束时刻（秒）。"""
        return self.ramp_time

    @property
    def bandwidth(self) -> float:
        """连续波为单频，理论带宽 0（Hz）。"""
        return 0.0

    def __call__(self, t: float | np.ndarray) -> float | np.ndarray:
        """计算连续波 g(t)（含斜坡）。"""
        t_arr = np.asarray(t, dtype=np.float64)
        if self.ramp_time > 0.0:
            ramp = np.clip(t_arr / self.ramp_time, 0.0, 1.0)
        else:
            ramp = np.where(t_arr >= 0.0, 1.0, 0.0)
        return (
            self.amplitude
            * ramp
            * np.sin(2.0 * np.pi * self.frequency * t_arr + self.phase)
        )


@dataclass(frozen=True)
class RickerWavelet:
    """Ricker 小波（高斯导数，无 DC 分量，宽带单脉冲）。

    g(t) = E0 · (1 - 2π²·f0²·(t-t0)²) · exp(-π²·f0²·(t-t0)²)

    等价于高斯包络二阶导数，频谱中心 f0，无 DC（零均值），
    适合反射/散射测量（无低频泄漏）。峰值位于 t=t0，过零点 t=t0 ± 1/(√2·π·f0)。

    Attributes:
        amplitude: 峰值振幅 E0（V/m）。
        frequency: 中心频率 f0（Hz），>0。
        t0: 脉冲中心时刻（秒），≥0。
    """

    amplitude: float
    frequency: float
    t0: float

    def __post_init__(self) -> None:
        if self.amplitude < 0.0:
            raise ValueError(f"振幅须 ≥0，实际 {self.amplitude}")
        if self.frequency <= 0.0:
            raise ValueError(f"中心频率须 >0，实际 {self.frequency}")
        if self.t0 < 0.0:
            raise ValueError(f"t0 须 ≥0，实际 {self.t0}")

    @property
    def center_frequency(self) -> float:
        """中心频率 f0（Hz）。"""
        return self.frequency

    @property
    def center_time(self) -> float:
        """脉冲中心时刻 t0（秒）。"""
        return self.t0

    @property
    def bandwidth(self) -> float:
        """-3dB 带宽 Δf ≈ √(2/ln2)·f0/2 ≈ 0.85·f0（Hz，Ricker 频谱性质）。"""
        return float(np.sqrt(2.0 / np.log(2.0)) * self.frequency / 2.0)

    def __call__(self, t: float | np.ndarray) -> float | np.ndarray:
        """计算 Ricker 小波 g(t)。"""
        arg = np.pi * self.frequency * (t - self.t0)
        return self.amplitude * (1.0 - 2.0 * arg**2) * np.exp(-(arg**2))


@dataclass(frozen=True)
class DipoleSource:
    """电偶极子点源（Hertzian dipole，J_z δ 函数软注入）。

    注入方式（Taflove 2005 §5.5 软源）：
        E_z[i, j] += J_amp · g(t) · Δt / ε
    其中 J_amp = I·dl / (dx·dy)（电流矩除以单元面积）。

    Attributes:
        position: 网格索引 (i, j)，必须位于内部区域。
        waveform: 时域波形对象（GaussianPulse/ContinuousWave/RickerWavelet）。
        current_moment: 电流矩 I·dl（A·m），默认 1.0。
        polarization: 'ez'（2D TEz 仅支持 z 向）。
    """

    position: tuple[int, int]
    waveform: Waveform
    current_moment: float = 1.0
    polarization: str = "ez"

    def __post_init__(self) -> None:
        ix, iy = self.position
        if ix < 0 or iy < 0:
            raise ValueError(f"偶极子位置必须为非负整数，实际 {self.position}")
        if self.polarization != "ez":
            raise ValueError(f"2D TEz 仅支持 'ez' 偏振，实际 {self.polarization}")
        if self.current_moment == 0.0:
            raise ValueError("电流矩不能为零")


def inject_dipole(
    e_z: np.ndarray,
    source: DipoleSource,
    t: float,
    dt: float,
    eps_r: np.ndarray,
    dx: float,
    dy: float,
) -> None:
    """软注入偶极子源到 E_z 场（原地修改，Taflove 2005 §5.5）。

    E_z[i, j] += (I·dl / (dx·dy)) · g(t) · Δt / (ε_0·ε_r)

    Args:
        e_z: 电场数组 (Nx, Ny)，原地修改。
        source: 偶极子源对象。
        t: 当前时刻（秒）。
        dt: 时间步（秒）。
        eps_r: 相对介电常数 (Nx, Ny)。
        dx, dy: 网格间距（米）。

    Raises:
        IndexError: 偶极子位置越界（规则 14）。
    """
    nx, ny = e_z.shape
    ix, iy = source.position
    if not (0 <= ix < nx and 0 <= iy < ny):
        raise IndexError(
            f"偶极子位置 ({ix},{iy}) 越界，网格形状 {(nx, ny)}"
        )
    j_amp = source.current_moment / (dx * dy)
    eps0 = 8.8541878128e-12
    eps = eps0 * eps_r[ix, iy]
    e_z[ix, iy] += j_amp * float(source.waveform(t)) * dt / eps
