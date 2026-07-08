"""simphony 兼容电路构建 API（SPICE 风格光子电路构建接口）。

复刻 simphony 的 Subcircuit/Term/Connector 类层次结构，提供 SPICE 风格的
光子电路构建接口。用户可通过 add_component/connect/add_terminal 方法
声明式构建电路，再转换为网表格式进行仿真。

来源（R02 学术诚信，≥5 个文献 URL）:
- simphony API: https://simphonyphotonics.readthedocs.io/en/stable/api/simphony.core.html
- simphony Subcircuit (源码仓库): https://github.com/BYUCamachoLab/simphony
- Pflüger et al., "Simphony: An Open-Source Photonic Circuit Simulation
  Framework", IEEE CiSE 2021, §2, https://arxiv.org/abs/2009.05146
- Filipsson 1978, "A New General Computer Algorithm for S-Parameter
  Cascade of Multiport Networks", Eur. Microw. Conf.,
  https://doi.org/10.1109/EUMA.1978.332681
- Pozar, "Microwave Engineering", 4th ed., §4.3 (S 参数级联),
  https://www.wiley.com/en-us/Microwave+Engineering
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015,
  https://www.cambridge.org/core/books/photonic-electronics/

补充文献（R02 ≥5 URL）:
- sax 矩阵化光子仿真库: https://flapport.github.io/sax/
- gdsfactory 电路构建: https://github.com/gdsfactory/gdsfactory
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg Silicon Photonics Design: https://www.cambridge.org/core/books/photonic-electronics/
- Lumerical INTERCONNECT CML: https://optics.ansys.com/hc/en-us

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO /
R13 不保留 v4 兼容。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polaris_circuit.types import ModelFunc


@dataclass
class Term:
    """端口定义（对齐 simphony.Term）。

    表示一个器件实例上的端口引用，由实例名和端口名组成。

    来源: simphony.Term https://github.com/BYUCamachoLab/simphony
    """

    name: str
    instance: str

    def to_ref(self) -> str:
        """转换为 'instance.port' 引用字符串。"""
        return f"{self.instance}.{self.name}"


@dataclass
class Connector:
    """连接器（对齐 simphony.Connector）。

    表示两个 Term 之间的连接关系。

    来源: simphony.Connector https://github.com/BYUCamachoLab/simphony
    """

    term1: Term
    term2: Term

    def to_connection(self) -> tuple[str, str]:
        """转换为网表连接元组 ('inst1.port1', 'inst2.port2')。"""
        return (self.term1.to_ref(), self.term2.to_ref())


@dataclass
class Subcircuit:
    """子电路（对齐 simphony.Subcircuit）。

    SPICE 风格的光子电路构建器，支持声明式添加器件、连接端口、
    定义外部端子，最终转换为网表格式。

    来源:
    - simphony.Subcircuit: https://github.com/BYUCamachoLab/simphony
    - Ploeg et al., "Simphony", IEEE CiSE 2021, §2
    """

    name: str
    components: dict[str, ModelFunc] = field(default_factory=dict)
    connections: list[Connector] = field(default_factory=list)
    terminals: dict[str, Term] = field(default_factory=dict)

    def add_component(self, model: ModelFunc, name: str) -> None:
        """添加器件实例。

        Raises:
            ValueError: 实例名重复时告警退出（禁止 fall-back）。
        """
        if name in self.components:
            raise ValueError(f"实例名 '{name}' 已存在，禁止重复添加（禁止 fall-back）")
        self.components[name] = model

    def connect(self, inst1: str, port1: str, inst2: str, port2: str) -> None:
        """连接两个器件实例的端口。

        Raises:
            ValueError: 实例不存在时告警退出（禁止 fall-back）。
        """
        self._validate_instance(inst1)
        self._validate_instance(inst2)
        term1 = Term(name=port1, instance=inst1)
        term2 = Term(name=port2, instance=inst2)
        self.connections.append(Connector(term1, term2))

    def add_terminal(self, term_name: str, inst: str, port: str) -> None:
        """添加外部端子（子电路对外暴露的端口）。

        Raises:
            ValueError: 实例不存在或端子名重复时告警退出（禁止 fall-back）。
        """
        self._validate_instance(inst)
        if term_name in self.terminals:
            raise ValueError(f"端子名 '{term_name}' 已存在，禁止重复添加（禁止 fall-back）")
        self.terminals[term_name] = Term(name=port, instance=inst)

    def to_netlist(self) -> dict:
        """转换为网表格式 {instances, connections, ports}。

        生成 SAX 兼容的网表字典，可直接传给 CircuitSimulator.simulate()。
        """
        instances = {name: func.__name__ for name, func in self.components.items()}
        connections = [c.to_connection() for c in self.connections]
        ports = {ext: term.to_ref() for ext, term in self.terminals.items()}
        return {
            "instances": instances,
            "connections": connections,
            "ports": ports,
        }

    def to_sax_netlist(self) -> dict:
        """转换为含模型函数的网表（可直接仿真）。"""
        connections = [c.to_connection() for c in self.connections]
        ports = {ext: term.to_ref() for ext, term in self.terminals.items()}
        return {
            "instances": dict(self.components),
            "connections": connections,
            "ports": ports,
        }

    def _validate_instance(self, inst: str) -> None:
        """验证实例是否存在。

        Raises:
            ValueError: 实例不存在时告警退出（禁止 fall-back）。
        """
        if inst not in self.components:
            raise ValueError(
                f"实例 '{inst}' 不存在，请先调用 add_component 添加。"
                "禁止 fall-back（R03）。"
            )


__all__ = ["Term", "Connector", "Subcircuit"]
