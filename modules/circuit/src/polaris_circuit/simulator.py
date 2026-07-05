"""电路级频率域仿真器（纯 numpy 实现）。

对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

来源（R02 学术诚信，≥5 个文献 URL）:
- Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
- SAX 仿真器: https://flaport.github.io/sax/
- Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85,
  https://arxiv.org/abs/2009.05146
- Filipsson 1978, "A New General Computer Algorithm for S-Parameter
  Cascade of Multiport Networks", Eur. Microw. Conf.,
  https://doi.org/10.1109/EUMA.1978.332681
- Pozar, "Microwave Engineering", 4th ed., §4.3 (S 参数级联/群延迟),
  https://www.wiley.com/en-us/Microwave+Engineering
- Agrawal, "Fiber-Optic Communication Systems", §2.4 (群延迟),
  https://www.wiley.com/en-us/Fiber-Optic+Communication+Systems

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO /
R13 不保留 v4 兼容（去掉 jax backend 简化为单 numpy 后端）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from polaris_circuit.cascade import cascade_circuit
from polaris_circuit.models import (
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris_circuit.types import ModelFunc, SDict

# 光速（m/s），CODATA 2018 推荐值
SPEED_OF_LIGHT = 2.99792458e8


@dataclass
class WavelengthRange:
    """波长扫描范围参数集合。

    将 wl_start/wl_end/n_points 聚合为单一 dataclass，降低参数个数。
    来源: Simphony 仿真器 https://simphonyphotonics.readthedocs.io/
    """

    wl_start: float = 1.5
    wl_end: float = 1.6
    n_points: int = 1000


@dataclass
class CircuitSimulator:
    """电路级频率域仿真器。

    对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。
    纯 numpy 子网络增长实现。

    来源:
    - Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
    - SAX 仿真器: https://flaport.github.io/sax/
    """

    models: dict[str, ModelFunc] = field(default_factory=dict)

    def register_model(self, name: str, model: ModelFunc) -> None:
        """注册器件 S 参数模型。"""
        self.models[name] = model

    def simulate(
        self,
        netlist: dict,
        wavelengths: np.ndarray | None = None,
        **model_kwargs,
    ) -> SDict:
        """执行频率域仿真。

        Args:
            netlist: SAX 格式网表 {instances, connections, ports}。
            wavelengths: 波长数组（μm），默认 1.5-1.6μm 1000点。
            **model_kwargs: 传递给器件模型的参数。

        Returns:
            电路级 S 参数字典。

        Raises:
            KeyError: 网表中引用的模型未注册时（禁止 fall-back）。
        """
        if wavelengths is None:
            wavelengths = np.linspace(1.5, 1.6, 1000)
        instance_s: dict[str, SDict] = {}
        for inst_name, model_name in netlist.get("instances", {}).items():
            if model_name not in self.models:
                raise KeyError(
                    f"实例 '{inst_name}' 引用的模型 '{model_name}' 未注册。"
                    f"已注册模型: {sorted(self.models.keys())}。"
                    f"请先调用 register_model('{model_name}', ...) 注册该模型。"
                )
            instance_s[inst_name] = self.models[model_name](wl=wavelengths, **model_kwargs)
        connections = list(netlist.get("connections", {}).items())
        connections = [(k, v) for k, v in connections]
        ports = netlist.get("ports", {})
        return cascade_circuit(instance_s, connections, ports)

    def sweep_wavelength(
        self,
        netlist: dict,
        wl_range: WavelengthRange | None = None,
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """波长扫描仿真。

        Args:
            netlist: 网表。
            wl_range: 波长扫描范围，None 时使用默认 WavelengthRange()。
            **model_kwargs: 器件模型参数。

        Returns:
            (波长数组, S 参数字典)。
        """
        if wl_range is None:
            wl_range = WavelengthRange()
        wavelengths = np.linspace(wl_range.wl_start, wl_range.wl_end, wl_range.n_points)
        s = self.simulate(netlist, wavelengths, **model_kwargs)
        return wavelengths, s


def default_models() -> dict[str, ModelFunc]:
    """返回默认 S 参数模型库。

    包含波导、Y分支、定向耦合器、环谐振器、MMI、光栅耦合器、交叉、
    终端吸收器、移相器等基础器件模型。

    来源:
    - Simphony SiEPIC 模型库: https://simphonyphotonics.readthedocs.io/
    - SiPANN 模型库: https://sipann.readthedocs.io/
    """
    return {
        "waveguide": waveguide_s,
        "y_branch": y_branch_s,
        "directional_coupler": directional_coupler_s,
        "ring_resonator": ring_resonator_s,
        "mmi_1x2": mmi_1x2_s,
        "mmi_2x2": mmi_2x2_s,
        "grating_coupler": grating_coupler_s,
        "crossing": crossing_s,
        "terminator": terminator_s,
        "phase_shifter": phase_shifter_s,
    }


def group_delay(
    sdict: SDict,
    wavelengths: np.ndarray,
    port_out: str | None = None,
    port_in: str | None = None,
) -> np.ndarray:
    """计算群延迟 τ_g = dφ/dω（R02 步骤 4）。

    与波导模型 exp(+i·β·L) 相位约定匹配，故 τ_g = +dφ/dω（正值）。
    使用中心差分计算。验证: 波导 τ_g = n_g·L/c（解析解）。

    来源:
    - Agrawal, "Fiber-Optic Communication Systems", §2.4

    Args:
        sdict: S 参数字典。
        wavelengths: 波长数组（μm），单调。
        port_out: 输出端口名，None 时自动选取。
        port_in: 输入端口名，None 时自动选取。

    Returns:
        群延迟数组（秒），长度比 wavelengths 少 2（中心差分）。

    Raises:
        ValueError: 波长数组长度不足或端口不存在时告警退出。
    """
    wl = np.asarray(wavelengths, dtype=float)
    if len(wl) < 3:
        raise ValueError(f"波长数组长度必须 >= 3（中心差分需要），得到 {len(wl)}")
    if port_out is None or port_in is None:
        for (p_out, p_in), val in sdict.items():
            if p_out != p_in and np.any(np.asarray(val) != 0):
                port_out = p_out if port_out is None else port_out
                port_in = p_in if port_in is None else port_in
                break
    if port_out is None or port_in is None:
        raise ValueError("无法自动选取端口，请显式指定 port_out 和 port_in")
    key = (port_out, port_in)
    if key not in sdict:
        raise ValueError(f"端口对 ({port_out}, {port_in}) 不存在于 S 参数字典")
    h = np.asarray(sdict[key], dtype=complex)
    if len(h) != len(wl):
        raise ValueError(f"S 参数长度 {len(h)} 与波长数组长度 {len(wl)} 不匹配")
    omega = 2.0 * np.pi * SPEED_OF_LIGHT / (wl * 1e-6)
    phase = np.unwrap(np.angle(h))
    d_phase = phase[1:-1] - phase[:-2]
    d_phase_alt = phase[2:] - phase[1:-1]
    d_phase_center = (d_phase + d_phase_alt) / 2.0
    d_omega = (omega[2:] - omega[:-2]) / 2.0
    return d_phase_center / d_omega


__all__ = [
    "WavelengthRange",
    "CircuitSimulator",
    "default_models",
    "group_delay",
    "SPEED_OF_LIGHT",
]
