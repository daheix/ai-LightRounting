"""电路级频率域仿真器。

对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

集成方式:
- 优先使用 SAX（规则 2 直接集成）
- 回退到纯 numpy 子网络增长（规则 3 复刻）

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
class WavelengthSweepConfig:
    """波长扫描配置（规则 4.1：参数打包降低函数参数个数）。

    将 sweep_wavelength 的起始/结束波长与采样点数打包为单一对象，
    支持位置参数与 config 关键字两种向后兼容调用方式。

    来源:
    - Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
    - SAX 仿真器: https://flaport.github.io/sax/
    """

    wl_start: float = 1.5
    wl_end: float = 1.6
    n_points: int = 1000


def _resolve_sweep_config(args: tuple, model_kwargs: dict) -> WavelengthSweepConfig:
    """从位置参数或关键字参数解析波长扫描配置。

    向后兼容：
    - 位置参数 (wl_start, wl_end, n_points)
    - 关键字 config=WavelengthSweepConfig(...)
    - 默认配置
    """
    if len(args) == 3:
        return WavelengthSweepConfig(args[0], args[1], args[2])
    if len(args) == 1 and isinstance(args[0], WavelengthSweepConfig):
        return args[0]
    config = model_kwargs.pop("config", None)
    if config is not None:
        return config
    return WavelengthSweepConfig()


@dataclass
class CircuitSimulator:
    """电路级频率域仿真器。

    对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

    集成方式:
    - 优先使用 SAX（规则 2 直接集成）
    - 回退到纯 numpy 子网络增长（规则 3 复刻）

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
        *args,
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """波长扫描仿真。

        向后兼容调用方式：
        - sweep_wavelength(netlist, wl_start, wl_end, n_points)  # 位置参数
        - sweep_wavelength(netlist, config=WavelengthSweepConfig(...))  # 配置对象
        - sweep_wavelength(netlist)  # 默认 1.5-1.6μm 1000点

        Args:
            netlist: 网表。
            *args: 位置参数 (wl_start, wl_end, n_points) 或单个 WavelengthSweepConfig。
            **model_kwargs: 器件模型参数（含可选 config 关键字）。

        Returns:
            (波长数组, S 参数字典)
        """
        config = _resolve_sweep_config(args, model_kwargs)
        wavelengths = np.linspace(config.wl_start, config.wl_end, config.n_points)
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
    """返回 Simphony SiEPIC 模型库（规则 2 直接集成）。

    来源: https://simphonyphotonics.readthedocs.io/
    """
    try:
        import sax  # noqa: F401
    except ImportError:
        return {}

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
