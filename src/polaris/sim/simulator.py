"""电路级频率域仿真器。

对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

集成方式:
- 纯 numpy 子网络增长实现（规则 3 复刻，独立实现）
- SAX 作为可选依赖（规则 2 直接集成），但本模块不依赖 SAX

来源:
- Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
- SAX 仿真器: https://flaport.github.io/sax/
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from polaris.sim.cascade import cascade_circuit
from polaris.sim.models import (
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
from polaris.sim.types import ModelFunc, SDict


@dataclass
class WavelengthRange:
    """波长扫描范围参数集合（降低 sweep_wavelength 参数个数，规则 4）。

    将 wl_start/wl_end/n_points 聚合为单一 dataclass，
    使 sweep_wavelength 的参数个数从 6 降至 4。

    来源:
    - Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
    """

    wl_start: float = 1.5
    wl_end: float = 1.6
    n_points: int = 1000


@dataclass
class CircuitSimulator:
    """电路级频率域仿真器。

    对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

    集成方式:
    - 纯 numpy 子网络增长实现（规则 3 复刻，独立实现）
    - SAX 作为可选依赖（规则 2 直接集成），但本模块不依赖 SAX

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
        """
        if wavelengths is None:
            wavelengths = np.linspace(1.5, 1.6, 1000)

        # 计算每个实例的 S 参数
        instance_s: dict[str, SDict] = {}
        for inst_name, model_name in netlist.get("instances", {}).items():
            if model_name in self.models:
                instance_s[inst_name] = self.models[model_name](wl=wavelengths, **model_kwargs)

        # 级联
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
            wl_range: 波长扫描范围（起始、结束、点数），
                为 None 时使用默认 WavelengthRange()（1.5-1.6μm 1000点）。
            **model_kwargs: 器件模型参数。

        Returns:
            (波长数组, S 参数字典)
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


def simphony_models() -> dict[str, ModelFunc]:
    """返回 Simphony SiEPIC 模型库（规则 2 直接集成，必装依赖）。

    来源: https://simphonyphotonics.readthedocs.io/
    """
    from simphony.libraries import siepic

    return {
        "siepic_waveguide": siepic.waveguide,
        "siepic_y_branch": siepic.y_branch,
        "siepic_directional_coupler": siepic.directional_coupler,
        "siepic_grating_coupler": siepic.grating_coupler,
        "siepic_half_ring": siepic.half_ring,
        "siepic_terminator": siepic.terminator,
        "siepic_taper": siepic.taper,
    }
