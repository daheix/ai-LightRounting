"""simphony 兼容电路构建 API（R02 步骤 1）。

复刻 simphony 的 Subcircuit/Term/Connector 类层次结构，提供 SPICE 风格的
光子电路构建接口。用户可通过 add_component/connect/add_terminal 方法
声明式构建电路，再转换为 PoLaRIS 内部网表格式进行仿真。

来源:
- simphony API: https://simphonyphotonics.readthedocs.io/en/stable/api/simphony.core.html
- simphony Subcircuit: https://github.com/BYUCamachoLab/simphony
- Ploeg et al., "Simphony", IEEE CiSE 2021, §2

API 示例（对齐 simphony 风格）:
    sub = Subcircuit("mzi")
    sub.add_component(waveguide_s, "wg1")
    sub.add_component(waveguide_s, "wg2")
    sub.connect("wg1", "out", "wg2", "in")
    sub.add_terminal("in", "wg1", "in")
    sub.add_terminal("out", "wg2", "out")
    netlist = sub.to_netlist()
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polaris.sim.types import ModelFunc


@dataclass
class Term:
    """端口定义（对齐 simphony.Term）。

    表示一个器件实例上的端口引用，由实例名和端口名组成。

    来源:
    - simphony.Term: https://github.com/BYUCamachoLab/simphony

    Attributes:
        name: 端口名（如 "in", "out", "pin1"）。
        instance: 所属实例名（如 "wg1"）。
    """

    name: str
    instance: str

    def to_ref(self) -> str:
        """转换为 'instance.port' 引用字符串。

        Returns:
            'instance.port' 格式的引用字符串，用于网表连接。
        """
        return f"{self.instance}.{self.name}"


@dataclass
class Connector:
    """连接器（对齐 simphony.Connector）。

    表示两个 Term 之间的连接关系。

    来源:
    - simphony.Connector: https://github.com/BYUCamachoLab/simphony

    Attributes:
        term1: 第一个端口。
        term2: 第二个端口。
    """

    term1: Term
    term2: Term

    def to_connection(self) -> tuple[str, str]:
        """转换为网表连接元组。

        Returns:
            ('inst1.port1', 'inst2.port2') 格式的连接元组。
        """
        return (self.term1.to_ref(), self.term2.to_ref())


@dataclass
class Subcircuit:
    """子电路（对齐 simphony.Subcircuit）。

    SPICE 风格的光子电路构建器，支持声明式添加器件、连接端口、
    定义外部端子，最终转换为 PoLaRIS 内部网表格式。

    来源:
    - simphony.Subcircuit: https://github.com/BYUCamachoLab/simphony
    - Ploeg et al., "Simphony", IEEE CiSE 2021, §2

    Attributes:
        name: 子电路名。
        components: 组件字典 {instance_name: ModelFunc}。
        connections: 连接列表 [Connector, ...]。
        terminals: 外部端子字典 {terminal_name: Term}。
    """

    name: str
    components: dict[str, ModelFunc] = field(default_factory=dict)
    connections: list[Connector] = field(default_factory=list)
    terminals: dict[str, Term] = field(default_factory=dict)

    def add_component(self, model: ModelFunc, name: str) -> None:
        """添加器件实例。

        Args:
            model: S 参数模型函数。
            name: 实例名（唯一标识）。

        Raises:
            ValueError: 实例名重复时告警退出（禁止 fall-back）。
        """
        if name in self.components:
            msg = f"实例名 '{name}' 已存在，禁止重复添加（禁止 fall-back）"
            raise ValueError(msg)
        self.components[name] = model

    def connect(
        self,
        inst1: str,
        port1: str,
        inst2: str,
        port2: str,
    ) -> None:
        """连接两个器件实例的端口。

        Args:
            inst1: 第一个实例名。
            port1: 第一个实例的端口名。
            inst2: 第二个实例名。
            port2: 第二个实例的端口名。

        Raises:
            ValueError: 实例不存在时告警退出（禁止 fall-back）。
        """
        self._validate_instance(inst1)
        self._validate_instance(inst2)
        term1 = Term(name=port1, instance=inst1)
        term2 = Term(name=port2, instance=inst2)
        self.connections.append(Connector(term1, term2))

    def add_terminal(self, term_name: str, inst: str, port: str) -> None:
        """添加外部端子。

        外部端子是子电路对外暴露的端口，对应某个器件实例的内部端口。

        Args:
            term_name: 外部端子名。
            inst: 器件实例名。
            port: 器件实例的端口名。

        Raises:
            ValueError: 实例不存在或端子名重复时告警退出（禁止 fall-back）。
        """
        self._validate_instance(inst)
        if term_name in self.terminals:
            msg = f"端子名 '{term_name}' 已存在，禁止重复添加（禁止 fall-back）"
            raise ValueError(msg)
        self.terminals[term_name] = Term(name=port, instance=inst)

    def to_netlist(self) -> dict:
        """转换为 PoLaRIS 内部网表格式。

        生成 SAX 兼容的网表字典，可直接传给 CircuitSimulator.simulate()。

        Returns:
            网表字典 {instances, connections, ports}。
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
        """转换为 SAX 直接可用的网表（含模型函数）。

        与 to_netlist() 不同，此格式直接包含模型函数对象，
        可用于 CircuitSimulator 直接仿真。

        Returns:
            SAX 网表 {instances: {name: ModelFunc}, connections, ports}。
        """
        connections = [c.to_connection() for c in self.connections]
        ports = {ext: term.to_ref() for ext, term in self.terminals.items()}
        return {
            "instances": dict(self.components),
            "connections": connections,
            "ports": ports,
        }

    def _validate_instance(self, inst: str) -> None:
        """验证实例是否存在。

        Args:
            inst: 实例名。

        Raises:
            ValueError: 实例不存在时告警退出（禁止 fall-back）。
        """
        if inst not in self.components:
            msg = (
                f"实例 '{inst}' 不存在，请先调用 add_component 添加。"
                "禁止 fall-back（规则 14.1）。"
            )
            raise ValueError(msg)
