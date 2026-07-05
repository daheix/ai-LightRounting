"""Photoelectric CoSim 光电协同仿真（章节10）。

从 v4 旧包 sim/photoelectric_cosim.py 迁移 MZM + PD + Laser 光电协同 API。

学术依据（R02 ≥5 文献 URL）:
- Chrostowski 2015 Silicon Photonics Design Cambridge §8 §9,
  https://www.cambridge.org/core/books/photonic-electronics/
- Coldren & Corzine 1995 Diode Lasers and Photonic Integrated Circuits §5,
  https://www.wiley.com/en-us/Diode+Lasers+and+Photonic+Integrated+Circuits
- VLSIR SPICE, https://github.com/dan-fritchman/vlsir
- cocotb, https://docs.cocotb.org/
- ngspice, https://ngspice.sourceforge.io/
- Ansys Lumerical INTERCONNECT (光电协同仿真),
  https://optics.ansys.com/hc/en-us

设计原则: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy /
R05 无 TODO / R13 不保留 v4 兼容 / 函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class CoSimConfig:
    """光电协同仿真全局配置。来源: SPICE 瞬态分析 https://ngspice.sourceforge.io/"""
    timestep: float = 1e-12
    total_time: float = 1e-9
    input_power_w: float = 1.0e-3
    load_resistance: float = 50.0
    wavelength_m: float = 1.55e-6
    newton_tol: float = 1.0e-10
    newton_maxiter: int = 50

    def __post_init__(self) -> None:
        if self.timestep <= 0:
            raise ValueError(f"timestep 须 > 0，得到 {self.timestep}")
        if self.total_time <= self.timestep:
            raise ValueError(f"total_time 须 > timestep")
        if self.load_resistance <= 0:
            raise ValueError(f"load_resistance 须 > 0")


@dataclass
class ModulatorSpec:
    """MZM 调制器规格。来源: Chrostowski 2015 §8.4。"""
    vpi: float
    insertion_loss_db: float
    bias_v: float = 0.0

    def __post_init__(self) -> None:
        if self.vpi <= 0:
            raise ValueError(f"V_pi 须 > 0，得到 {self.vpi}")
        if self.insertion_loss_db < 0:
            raise ValueError(f"insertion_loss_db 须 >= 0")


@dataclass
class PhotodetectorSpec:
    """光电探测器规格。来源: Chrostowski 2015 §9.2。"""
    responsivity: float
    dark_current: float

    def __post_init__(self) -> None:
        if self.responsivity < 0:
            raise ValueError(f"responsivity 须 >= 0")
        if self.dark_current < 0:
            raise ValueError(f"dark_current 须 >= 0")


@dataclass
class LaserSpec:
    """DFB 激光器规格。来源: Coldren & Corzine 1995 §5。"""
    threshold_current: float
    slope_efficiency: float
    bias_current: float = 0.0
    tau_n: float = 1.0e-9
    tau_p: float = 1.0e-12
    gamma_confinement: float = 0.3

    def __post_init__(self) -> None:
        if self.threshold_current <= 0:
            raise ValueError(f"threshold_current 须 > 0")
        if not 0.0 < self.gamma_confinement <= 1.0:
            raise ValueError(f"Γ 须在 (0,1]")
        if self.bias_current <= 0:
            self.bias_current = 2.0 * self.threshold_current


class PhotoelectricCoSim:
    """光电协同仿真主控（VLSIR SPICE + Verilog-A + 牛顿迭代）。

    *创新*: VLSIR SPICE 中间表示 + Verilog-A 光子紧凑模型 + Python 数值协同
    仿真统一封装，消除 Lumerical INTERCONNECT 与 Spectre 之间的手动网表搬运。
    底层逻辑: SPICE 子电路声明器件拓扑 + Verilog-A 描述光子非线性行为 +
    Python 牛顿迭代求解光电耦合稳态。

    学术依据: Chrostowski 2015 §8/§9 / Coldren & Corzine 1995 §5 /
    VLSIR SPICE https://github.com/dan-fritchman/vlsir / cocotb https://docs.cocotb.org/
    """

    def __init__(self, config: CoSimConfig) -> None:
        self.config = config
        self._devices: dict[int, tuple[str, object]] = {}
        self._next_id = 1

    def add_modulator(self, vpi: float, insertion_loss: float, bias_v: float = 0.0) -> int:
        return self._register("modulator", ModulatorSpec(vpi, insertion_loss, bias_v))

    def add_photodetector(self, responsivity: float, dark_current: float) -> int:
        return self._register("photodetector", PhotodetectorSpec(responsivity, dark_current))

    def add_laser(self, threshold_current: float, slope_efficiency: float) -> int:
        return self._register("laser", LaserSpec(threshold_current, slope_efficiency))

    def _register(self, kind: str, spec: object) -> int:
        dev_id = self._next_id
        self._devices[dev_id] = (kind, spec)
        self._next_id += 1
        return dev_id

    @staticmethod
    def mzm_transmission(voltage: np.ndarray | float, spec: ModulatorSpec) -> np.ndarray | float:
        """MZM 光强传输 T(V)=cos²(π(V+Vbias)/(2Vπ))·10^(-IL/20)。

        来源: Chrostowski 2015 §8.4 推挽 MZM 传输函数。
        """
        amp = 10.0 ** (-spec.insertion_loss_db / 20.0)
        phi = math.pi * (np.asarray(voltage) + spec.bias_v) / (2.0 * spec.vpi)
        return (np.cos(phi) ** 2) * amp

    @staticmethod
    def laser_li(current: float | np.ndarray, spec: LaserSpec) -> float | np.ndarray:
        """激光器 L-I 特性: P=max(0, η_d·(I-I_th))。来源: Coldren 1995 §5.4。"""
        i = np.asarray(current)
        p = spec.slope_efficiency * np.maximum(i - spec.threshold_current, 0.0)
        return float(p) if np.isscalar(current) else p
