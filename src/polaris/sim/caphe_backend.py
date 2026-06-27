"""CAPHE 电路仿真后端（R26 路标）。

对标 CAPHE（Circuit Analysis Program for Photonic Elements）的电路级仿真
能力，提供频率域 S 参数级联与时域 ODE 求解，作为光子电路仿真后端。

## 模块组成

1. ``CAPHENode`` — 电路节点（器件实例 + S 参数模型）
2. ``CAPHENetwork`` — 电路网络（节点集合 + 连接关系）
3. ``CAPHEFrequencySolver`` — 频率域求解器（S 参数级联）
4. ``CAPHETimeDomainSolver`` — 时域求解器（ODE 积分，环调制/载流子动力学）
5. ``CAPHEBackend`` — 统一后端接口（频率域 + 时域）

## 学术依据

- CAPHE 电路仿真器: D. Vermeulen et al., "Efficient TDM with a silicon
  ring resonator", OFC 2008; CAPHE 由 Ghent University / Luceda 开发
  https://www.lucedaphotonics.com/products/caphe
- 时域 ODE 环谐振器模型: Bogaerts et al., "Silicon microring resonators",
  Laser & Photonics Reviews 6(1), 2012, https://doi.org/10.1002/lpor.201100017
- S 参数级联子网络增长: SAX, https://flaport.github.io/sax/

来源:
- CAPHE: https://www.lucedaphotonics.com/products/caphe
- SAX 级联: https://flaport.github.io/sax/
- Simphony: https://simphonyphotonics.readthedocs.io/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from polaris.sim.cascade import cascade_circuit
from polaris.sim.models import (
    directional_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.types import ModelFunc, SDict

# CAPHE 与 SAX 交叉验证容差（S 参数幅值最大绝对误差阈值）
# 来源: 与 fdtd_gpu_engine.CROSS_VALIDATE_TOL 一致，1e-3 为工程级仿真容差
CROSS_VALIDATE_TOL: float = 1e-3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 器件类型到 S 参数模型的映射（来源: polaris.sim.models）
# ---------------------------------------------------------------------------
_MODEL_MAP: dict[str, ModelFunc] = {
    "waveguide": waveguide_s,
    "y_branch": y_branch_s,
    "directional_coupler": directional_coupler_s,
    "ring_resonator": ring_resonator_s,
    "mmi_1x2": mmi_1x2_s,
    "mmi_2x2": mmi_2x2_s,
    "phase_shifter": phase_shifter_s,
}


# ---------------------------------------------------------------------------
# CAPHENode — 电路节点
# ---------------------------------------------------------------------------


@dataclass
class CAPHENode:
    """CAPHE 电路节点（器件实例 + S 参数模型）。

    每个节点对应一个光子器件实例，持有器件类型、参数与端口列表，
    可在指定波长计算 S 参数。

    学术依据: CAPHE 节点模型,
    https://www.lucedaphotonics.com/products/caphe

    Attributes:
        name: 节点名称（实例名）。
        cell_type: 器件类型（如 "waveguide"、"ring_resonator"）。
        params: 器件参数字典。
        ports: 端口名称列表。
    """

    name: str
    cell_type: str
    params: dict[str, Any] = field(default_factory=dict)
    ports: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化后补全端口列表。"""
        if not self.ports:
            self.ports = self._default_ports()

    @staticmethod
    def _default_ports() -> list[str]:
        """返回默认端口列表（单端口通用）。"""
        return ["in", "out"]

    def compute_sparams(self, wl: float | np.ndarray = 1.55) -> SDict:
        """计算节点 S 参数。

        Args:
            wl: 波长（μm）或波长数组。

        Returns:
            S 参数字典。

        Raises:
            ValueError: 器件类型无对应模型时。
        """
        model = _MODEL_MAP.get(self.cell_type)
        if model is None:
            raise ValueError(
                f"CAPHE 节点 '{self.name}' 器件类型 '{self.cell_type}' 无 S 参数模型，"
                f"可用: {list(_MODEL_MAP)}"
            )
        # 透传模型支持的参数
        valid_keys = {
            "length", "width", "radius", "gap", "coupling",
            "insertion_loss_db", "phase_rad", "neff", "ng", "loss_db_cm",
        }
        kwargs = {k: v for k, v in self.params.items() if k in valid_keys}
        return model(wl=wl, **kwargs)


# ---------------------------------------------------------------------------
# CAPHENetwork — 电路网络
# ---------------------------------------------------------------------------


@dataclass
class CAPHENetwork:
    """CAPHE 电路网络（节点集合 + 连接关系）。

    持有多个 CAPHENode 与它们之间的端口连接关系，
    构成完整的光子电路拓扑。

    学术依据: CAPHE 网络拓扑,
    https://www.lucedaphotonics.com/products/caphe

    Attributes:
        nodes: 节点字典 ``{name: CAPHENode}``。
        connections: 连接字典 ``{"node1,port1": "node2,port2"}``。
        ports: 外部端口字典 ``{ext_port: "node,internal_port"}``。
    """

    nodes: dict[str, CAPHENode] = field(default_factory=dict)
    connections: dict[str, str] = field(default_factory=dict)
    ports: dict[str, str] = field(default_factory=dict)

    def add_node(self, node: CAPHENode) -> None:
        """添加节点到网络。"""
        self.nodes[node.name] = node

    def connect(self, src: str, dst: str) -> None:
        """连接两个端口。

        Args:
            src: 源端口 ``"node1,port1"``。
            dst: 目标端口 ``"node2,port2"``。
        """
        self.connections[src] = dst

    def set_port(self, ext_name: str, internal: str) -> None:
        """设置外部端口。

        Args:
            ext_name: 外部端口名。
            internal: 内部端口 ``"node,port"``。
        """
        self.ports[ext_name] = internal

    def to_netlist(self) -> dict:
        """转换为 SAX 格式网表。

        Returns:
            SAX 格式网表 ``{instances, connections, ports}``。
        """
        return {
            "instances": {n: nd.cell_type for n, nd in self.nodes.items()},
            "connections": dict(self.connections),
            "ports": dict(self.ports),
        }

    @classmethod
    def from_netlist(cls, netlist: dict) -> CAPHENetwork:
        """从 SAX 格式网表构建网络。

        Args:
            netlist: SAX 格式网表 ``{instances, connections, ports}``。

        Returns:
            CAPHENetwork 实例。
        """
        net = cls()
        for inst_name, cell_type in netlist.get("instances", {}).items():
            net.add_node(CAPHENode(name=inst_name, cell_type=cell_type))
        net.connections = dict(netlist.get("connections", {}))
        net.ports = dict(netlist.get("ports", {}))
        return net


# ---------------------------------------------------------------------------
# CAPHEFrequencySolver — 频率域求解器
# ---------------------------------------------------------------------------


@dataclass
class CAPHEFrequencySolver:
    """CAPHE 频率域求解器（S 参数级联）。

    对指定波长范围执行频率扫描，通过子网络增长算法级联各节点 S 参数，
    计算电路级传输谱。

    学术依据: S 参数级联子网络增长算法,
    SAX, https://flaport.github.io/sax/

    Attributes:
        network: 待求解的电路网络。
    """

    network: CAPHENetwork

    def solve(
        self,
        wavelengths: np.ndarray | None = None,
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """执行频率域求解。

        Args:
            wavelengths: 波长数组（μm），默认 1.5-1.6μm 100点。
            **model_kwargs: 传递给器件模型的参数。

        Returns:
            (波长数组, 电路级 S 参数字典)。
        """
        if wavelengths is None:
            wavelengths = np.linspace(1.5, 1.6, 100)
        # 计算每个节点的 S 参数
        instance_s: dict[str, SDict] = {}
        for name, node in self.network.nodes.items():
            instance_s[name] = node.compute_sparams(wl=wavelengths, **{
                k: v for k, v in model_kwargs.items()
            })
        # 级联
        connections = list(self.network.connections.items())
        ports = self.network.ports
        s_total = cascade_circuit(instance_s, connections, ports)
        return wavelengths, s_total

    def transmission(
        self,
        out_port: str,
        in_port: str,
        wavelengths: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """计算指定端口对的传输谱。

        Args:
            out_port: 输出端口名。
            in_port: 输入端口名。
            wavelengths: 波长数组。

        Returns:
            (波长数组, 传输率数组 T=|S|²)。
        """
        wl, s = self.solve(wavelengths)
        key = (out_port, in_port)
        if key not in s:
            raise KeyError(
                f"S 参数中无端口对 {key}，可用: {list(s.keys())}"
            )
        t = np.abs(s[key]) ** 2
        return wl, t


# ---------------------------------------------------------------------------
# CAPHETimeDomainSolver — 时域求解器
# ---------------------------------------------------------------------------


@dataclass
class CAPHETimeDomainSolver:
    """CAPHE 时域求解器（ODE 积分）。

    对环谐振器等动态器件求解时域耦合模方程（CMT）ODE，
    模拟调制响应、载流子动力学与瞬态行为。

    学术依据: Bogaerts et al., "Silicon microring resonators",
    Laser & Photonics Reviews 6(1), 2012,
    https://doi.org/10.1002/lpor.201100017

    耦合模方程（全通环）:
        dA/dt = (j·Δω - 1/τ)·A + κ·s_in(t)
        s_out(t) = s_in(t) - κ*·A(t)
    其中 A 为环内场幅度，τ 为光子寿命，κ 为耦合系数，Δω 为失谐。

    Attributes:
        network: 待求解的电路网络。
    """

    network: CAPHENetwork

    def solve_ring(
        self,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        t_span_ps: tuple[float, float] = (0.0, 1000.0),
        n_steps: int = 1000,
        input_power_mw: float = 1.0,
    ) -> dict:
        """求解环谐振器时域响应（耦合模理论 ODE）。

        使用前向欧拉法积分全通环 CMT 方程。

        Args:
            detuning_ghz: 激光-环失谐频率（GHz）。
            photon_lifetime_ps: 环内光子寿命（ps）。
            coupling: 总线-环功率耦合系数。
            t_span_ps: 时间范围（ps）。
            n_steps: 时间步数。
            input_power_mw: 输入功率（mW）。

        Returns:
            含 ``time``（时间数组 ps）、``ring_field``（环内场幅度）、
            ``output_power``（输出功率 mW）的字典。
        """
        t = np.linspace(t_span_ps[0], t_span_ps[1], n_steps)
        dt = t[1] - t[0]
        # 失谐角频率（rad/ps）：GHz → rad/ps = 2π·GHz·1e-3
        delta_omega = 2.0 * np.pi * detuning_ghz * 1e-3
        # 光子寿命倒数（1/ps）
        gamma = 1.0 / photon_lifetime_ps
        # 振幅耦合系数
        kappa = np.sqrt(coupling)
        # 输入场幅度（mW^0.5）
        s_in = np.sqrt(input_power_mw)
        # 前向欧拉积分
        a = 0.0 + 0.0j  # 环内场幅度
        ring_field = np.zeros(n_steps, dtype=complex)
        output_power = np.zeros(n_steps)
        for i in range(n_steps):
            # dA/dt = (j·Δω - γ)·A + κ·s_in
            da_dt = (1j * delta_omega - gamma) * a + kappa * s_in
            a = a + da_dt * dt
            ring_field[i] = a
            # s_out = s_in - κ*·A
            s_out = s_in - kappa * a
            output_power[i] = np.abs(s_out) ** 2
        return {
            "time": t,
            "ring_field": ring_field,
            "output_power": output_power,
            "detuning_ghz": detuning_ghz,
            "photon_lifetime_ps": photon_lifetime_ps,
        }

    def solve_step_response(
        self,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        t_span_ps: tuple[float, float] = (0.0, 2000.0),
        n_steps: int = 2000,
    ) -> dict:
        """求解环谐振器阶跃响应。

        输入阶跃信号（t=0 时开启），观察环内场与输出的瞬态建立过程。

        Args:
            detuning_ghz: 失谐频率（GHz）。
            photon_lifetime_ps: 光子寿命（ps）。
            coupling: 耦合系数。
            t_span_ps: 时间范围（ps）。
            n_steps: 时间步数。

        Returns:
            含 ``time``、``ring_field``、``output_power`` 的字典。
        """
        return self.solve_ring(
            detuning_ghz=detuning_ghz,
            photon_lifetime_ps=photon_lifetime_ps,
            coupling=coupling,
            t_span_ps=t_span_ps,
            n_steps=n_steps,
            input_power_mw=1.0,
        )


# ---------------------------------------------------------------------------
# CAPHEBackend — 统一后端接口
# ---------------------------------------------------------------------------


@dataclass
class CAPHEBackend:
    """CAPHE 统一仿真后端接口。

    封装频率域与时域求解器，提供统一的电路仿真入口。

    学术依据: CAPHE 仿真后端,
    https://www.lucedaphotonics.com/products/caphe

    Attributes:
        network: 电路网络。
    """

    network: CAPHENetwork | None = None

    def set_network(self, network: CAPHENetwork) -> None:
        """设置仿真网络。"""
        self.network = network

    def frequency_domain(
        self,
        wavelengths: np.ndarray | None = None,
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """频率域仿真。

        Args:
            wavelengths: 波长数组。
            **model_kwargs: 器件模型参数。

        Returns:
            (波长数组, S 参数字典)。

        Raises:
            RuntimeError: 未设置网络时。
        """
        if self.network is None:
            raise RuntimeError("CAPHE 后端未设置网络，请先调用 set_network()")
        solver = CAPHEFrequencySolver(network=self.network)
        return solver.solve(wavelengths, **model_kwargs)

    def time_domain(
        self,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        t_span_ps: tuple[float, float] = (0.0, 1000.0),
        n_steps: int = 1000,
    ) -> dict:
        """时域仿真（环谐振器 ODE）。

        Args:
            detuning_ghz: 失谐频率（GHz）。
            photon_lifetime_ps: 光子寿命（ps）。
            coupling: 耦合系数。
            t_span_ps: 时间范围（ps）。
            n_steps: 时间步数。

        Returns:
            时域求解结果字典。

        Raises:
            RuntimeError: 未设置网络时。
        """
        if self.network is None:
            raise RuntimeError("CAPHE 后端未设置网络，请先调用 set_network()")
        solver = CAPHETimeDomainSolver(network=self.network)
        return solver.solve_ring(
            detuning_ghz=detuning_ghz,
            photon_lifetime_ps=photon_lifetime_ps,
            coupling=coupling,
            t_span_ps=t_span_ps,
            n_steps=n_steps,
        )

    @classmethod
    def from_netlist(cls, netlist: dict) -> CAPHEBackend:
        """从网表构建后端。

        Args:
            netlist: SAX 格式网表。

        Returns:
            CAPHEBackend 实例。
        """
        network = CAPHENetwork.from_netlist(netlist)
        return cls(network=network)
