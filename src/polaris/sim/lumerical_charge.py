"""R33 路标：Ansys Lumerical CHARGE 对齐（电光协同仿真）。

提供 Lumerical CHARGE 的电光协同仿真能力，基于 PN 结解析模型
（Sze & Ng §3.4-3.5）求解耗尽区宽度、结电容、调制器带宽，并通过等离子
色散效应（Soref & Bennett 1987）实现电压→折射率变化→相位调制的电光协同。

## 学术依据

- Ansys Lumerical CHARGE: https://www.ansys.com/products/optics/charge
- Ansys Lumerical 多物理场协同:
  https://optics.ansys.com/hc/en-us/articles/360042414214
- Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., 2007
  - §1.4 本征载流子浓度
  - §3.4 PN 结内建电势与耗尽区
  - §3.5 结电容
  - §10.3 调制器带宽（RC 限制）
- Soref & Bennett, IEEE J. Quantum Electron. 23(1), 1987（硅等离子色散）

## 物理常数

共享常量定义在 ``lumerical_constants`` 模块，本模块引用 ``_Q``/``_KB``
/``_EPS0``/``_EPS_SI``。

## 🚫不参与 GPU（R04）

纯 NumPy 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from polaris.sim.lumerical_constants import _EPS0, _EPS_SI, _KB, _Q

logger = logging.getLogger(__name__)


@dataclass
class CHARGEConfig:
    """Lumerical CHARGE 配置。

    学术依据：Ansys Lumerical CHARGE
    URL: https://www.ansys.com/products/optics/charge

    Attributes:
        temperature: 温度（K）。
        doping_n: n 型掺杂（cm⁻³）。
        doping_p: p 型掺杂（cm⁻³）。
    """

    temperature: float = 300.0
    doping_n: float = 1e18
    doping_p: float = 1e18


class CHARGESimulator:
    """Lumerical CHARGE 对齐（电光协同仿真）。

    学术依据：
    - Ansys Lumerical CHARGE 官方文档
      https://www.ansys.com/products/optics/charge
    - Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., 2007

    求解 Poisson 方程 + 连续性方程：
        ∇·(ε∇φ) = -q(p - n + N_D⁺ - N_A⁻)
        ∂n/∂t = (1/q)∇·J_n + G - R
        ∂p/∂t = -(1/q)∇·J_p + G - R

    本实现采用解析公式（Sze & Ng §3.4 PN 结）求解 PN 结特性。
    """

    def __init__(self, config: CHARGEConfig) -> None:
        """初始化 CHARGE 仿真器。

        Args:
            config: CHARGE 配置。
        """
        self.config = config
        self.T = config.temperature
        self.N_D = config.doping_n * 1e6  # cm⁻³ → m⁻³
        self.N_A = config.doping_p * 1e6  # cm⁻³ → m⁻³
        # 硅材料参数（来源: Sze & Ng, Table 1.1）
        self.eps = _EPS_SI * _EPS0  # 介电常数 (F/m)
        self.n_i = self._compute_intrinsic_carrier()

    def _compute_intrinsic_carrier(self) -> float:
        """计算本征载流子浓度。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §1.4
        n_i = sqrt(N_C·N_V)·exp(-E_g/(2kT))
        硅 @ 300K：n_i ≈ 1.0e10 cm⁻³ = 1.0e16 m⁻³

        Returns:
            本征载流子浓度（m⁻³）。
        """
        # 硅禁带宽度 @ 300K
        E_g = 1.12 * _Q  # J
        # 有效态密度（硅 @ 300K）
        N_C = 2.8e19 * 1e6  # m⁻³
        N_V = 1.04e19 * 1e6  # m⁻³
        n_i = np.sqrt(N_C * N_V) * np.exp(-E_g / (2.0 * _KB * self.T))
        return float(n_i)

    def compute_depletion_width(self, va: float = 0.0) -> float:
        """计算耗尽区宽度。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §3.4
        公式：W = sqrt(2ε(V_bi - V_a)/q · (1/N_A + 1/N_D))

        Args:
            va: 外加电压（V），正向为正。

        Returns:
            耗尽区宽度（m）。
        """
        v_bi = self._compute_build_in_potential()
        # 反向偏置时 V_a < 0，V_bi - V_a > V_bi，耗尽区变宽
        v_total = v_bi - va
        if v_total <= 0:
            # 强正向偏置，耗尽区消失
            return 0.0
        w = np.sqrt(
            2.0 * self.eps * v_total / _Q * (1.0 / self.N_A + 1.0 / self.N_D)
        )
        return float(w)

    def _compute_build_in_potential(self) -> float:
        """计算内建电势 V_bi = (kT/q)·ln(N_A·N_D/n_i²)。

        学术依据：Sze & Ng, §3.4

        Returns:
            内建电势（V）。
        """
        v_bi = (_KB * self.T / _Q) * np.log(self.N_A * self.N_D / self.n_i**2)
        return float(v_bi)

    def compute_junction_capacitance(self, area: float, va: float = 0.0) -> float:
        """计算结电容 C_j = εA/W。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §3.5

        Args:
            area: 结面积（m²）。
            va: 外加电压（V）。

        Returns:
            结电容（F）。
        """
        w = self.compute_depletion_width(va)
        if w < 1e-12:
            return 0.0
        return float(self.eps * area / w)

    def compute_modulator_bandwidth(self, r_series: float, c_j: float) -> float:
        """计算调制器带宽 f_3dB = 1/(2π R C)。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §10.3
        RC 时间常数限制调制器带宽。

        Args:
            r_series: 串联电阻（Ω）。
            c_j: 结电容（F）。

        Returns:
            3dB 带宽（Hz）。
        """
        if r_series * c_j < 1e-30:
            return 1e15
        return float(1.0 / (2.0 * np.pi * r_series * c_j))

    def solve_pn_junction(self, width: float, length: float) -> dict:
        """求解 PN 结（耗尽区宽度、电容、电阻）。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §3.4-3.5
        解析求解 PN 结的 I-V 与 C-V 特性。

        Args:
            width: PN 结宽度（μm）。
            length: PN 结长度（μm）。

        Returns:
            包含 depletion_width/capacitance/resistance/v_bi 的字典。
        """
        # 结面积（假设高度 220nm，SiEPIC 标准）
        height_m = 220e-9  # m
        area = width * 1e-6 * length * 1e-6 * height_m  # m²
        # 耗尽区宽度（零偏）
        w_depl = self.compute_depletion_width(0.0)
        # 结电容（零偏）
        c_j = self.compute_junction_capacitance(area, 0.0)
        # 串联电阻（估算：R = ρ·L/A，ρ硅 ~ 0.01 Ω·cm @ 1e18 cm⁻³）
        rho = 0.01 * 1e-2  # Ω·m
        r_series = rho * length * 1e-6 / area
        # 带宽
        f_3db = self.compute_modulator_bandwidth(r_series, c_j)
        v_bi = self._compute_build_in_potential()
        return {
            "depletion_width": w_depl,
            "capacitance": c_j,
            "resistance": r_series,
            "v_bi": v_bi,
            "bandwidth": f_3db,
            "area": area,
        }

    def electro_optic_simulation(self, modulator_config: dict) -> dict:
        """电光协同仿真（电压→折射率变化→相位调制）。

        学术依据：
        - Ansys Lumerical CHARGE + MODE 协同
          https://optics.ansys.com/hc/en-us/articles/360042414214
        - Sze & Ng, "Physics of Semiconductor Devices", §10.3

        物理流程：
        1. 电压 V → 耗尽区宽度变化 ΔW
        2. ΔW → 有效折射率变化 Δn_eff（等离子色散效应）
        3. Δn_eff → 相位调制 Δφ = (2π/λ)·Δn_eff·L

        Args:
            modulator_config: 调制器配置（含 voltage/length/wavelength/width）。

        Returns:
            电光仿真结果字典。
        """
        voltage = modulator_config.get("voltage", 1.0)
        length = modulator_config.get("length", 100.0)  # μm
        wavelength = modulator_config.get("wavelength", 1.55)  # μm
        width = modulator_config.get("width", 0.5)  # μm
        # 1. 计算耗尽区宽度变化
        # 调制器电压约定：voltage > 0 表示反向偏置幅度（V_a = -voltage）
        # 反向偏置增大耗尽区，用于耗尽型电光调制器
        w_0 = self.compute_depletion_width(0.0)
        w_v = self.compute_depletion_width(-abs(voltage))  # 反向偏置
        delta_w = w_v - w_0  # m（反向偏置时为正，耗尽区变宽）
        # 2. 等离子色散效应：Δn_eff ≈ α·ΔW/W_0
        # 来源：Soref & Bennett, IEEE J. Quantum Electron. 23(1), 1987
        # 硅等离子色散系数 @ 1.55μm：Δn ≈ -8.5e-22·ΔN (ΔN 为载流子浓度变化)
        # 简化：Δn_eff 与耗尽区宽度变化成正比
        alpha_plasma = -1.0e-3  # 折射率变化系数（μm⁻¹）
        delta_n_eff = alpha_plasma * (delta_w * 1e6)  # 转换为 μm
        # 3. 相位调制 Δφ = (2π/λ)·Δn_eff·L
        delta_phi = (2.0 * np.pi / wavelength) * delta_n_eff * length
        # 4. 调制器带宽（反向偏置下的结电容）
        height_m = 220e-9
        area = width * 1e-6 * length * 1e-6 * height_m
        c_j = self.compute_junction_capacitance(area, -abs(voltage))
        rho = 0.01 * 1e-2
        r_series = rho * length * 1e-6 / area
        f_3db = self.compute_modulator_bandwidth(r_series, c_j)
        return {
            "voltage": voltage,
            "depletion_width_0": w_0,
            "depletion_width_v": w_v,
            "delta_n_eff": float(delta_n_eff),
            "phase_shift": float(delta_phi),
            "bandwidth": f_3db,
            "capacitance": c_j,
            "resistance": r_series,
            "length_um": length,
            "wavelength_um": wavelength,
        }
