"""R235 SPICE 网表输出（兼容 SPICE .subckt，含 TC1/TC2 温度系数）。

从 parasitic_advanced.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。对齐 Synopsys StarRC DSPF 输出与 SPICE 语法。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Synopsys StarRC Datasheet（DSPF 寄生网表输出）
   https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
2. StarRC TC1/TC2 SPICE 输出格式
   https://wenku.csdn.net/answer/3t8nxpm1me
3. Berkeley SPICE3f5 用户手册（R/L/C/互感语法）
   https://bwrcs.eecs.berkeley.edu/Classes/IcBook/SPICE/
4. ngspice 用户手册 §1.1（无源元件语法）
   https://ngspice.sourceforge.io/docs.html
5. Altair SimLab SPICE 导出
   https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm
6. Qucs-S Spice4qucs 子电路语法
   https://qucs-help.readthedocs.io/en/spice4qucs/SubLib.html

## 规则依据

R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简。
"""

from __future__ import annotations

__all__ = ["SpiceNetlistWriter"]


class SpiceNetlistWriter:
    """R235 SPICE 网表输出（生成兼容 SPICE 的 .subckt，含温度系数）。

    对齐 Synopsys StarRC DSPF 输出与 SPICE 语法：
    - 电阻：R<name> n1 n2 <value> [TC1=<tc1>] [TC2=<tc2>]
    - 电容：C<name> n1 n2 <value>
    - 电感：L<name> n1 n2 <value>
    - 互感：K<name> L<name1> L<name2> <coupling>

    来源（≥5 文献 URL）:
    - Synopsys StarRC Datasheet（DSPF 寄生网表输出）:
      https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
    - StarRC TC1/TC2 SPICE 输出格式:
      https://wenku.csdn.net/answer/3t8nxpm1me
    - Berkeley SPICE3f5 用户手册（R/L/C/互感语法）:
      https://bwrcs.eecs.berkeley.edu/Classes/IcBook/SPICE/
    - ngspice 用户手册 §1.1（无源元件语法）:
      https://ngspice.sourceforge.io/docs.html
    - Altair SimLab SPICE 导出:
      https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm
    - Qucs-S Spice4qucs 子电路语法:
      https://qucs-help.readthedocs.io/en/spice4qucs/SubLib.html
    """

    def __init__(self, subckt_name: str = "parasitic_net") -> None:
        """初始化网表写入器。

        Args:
            subckt_name: 子电路名称，默认 "parasitic_net"。

        Raises:
            ValueError: 子电路名非法时告警退出。
        """
        if not subckt_name or not subckt_name.replace("_", "").isalnum():
            msg = f"subckt_name 必须为字母数字下划线，得到 '{subckt_name}'"
            raise ValueError(msg)
        self.subckt_name = subckt_name
        self._lines: list[str] = []
        self._nodes: set[str] = set()

    def _check_node(self, node: str) -> None:
        """校验节点名合法性（R03）。"""
        if not node:
            msg = "节点名不能为空"
            raise ValueError(msg)
        if not node.replace("_", "").replace(".", "").isalnum():
            msg = f"节点名非法 '{node}'，须为字母数字下划线/点"
            raise ValueError(msg)

    def add_resistor(
        self,
        name: str,
        node1: str,
        node2: str,
        value_ohm: float,
        tc1: float | None = None,
        tc2: float | None = None,
    ) -> None:
        """添加电阻元件。

        Args:
            name: 元件名（不含前缀 R）。
            node1: 节点 1。
            node2: 节点 2。
            value_ohm: 电阻值 (Ω)。
            tc1: 一阶温度系数 (1/°C)，可选。
            tc2: 二阶温度系数 (1/°C²)，可选。

        Raises:
            ValueError: 名称/节点/值非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"电阻名非法 '{name}'"
            raise ValueError(msg)
        self._check_node(node1)
        self._check_node(node2)
        if value_ohm < 0:
            msg = f"电阻值必须 >= 0，得到 {value_ohm}"
            raise ValueError(msg)
        line = f"R{name} {node1} {node2} {value_ohm:.6g}"
        if tc1 is not None:
            line += f" tc1={tc1:.6g}"
        if tc2 is not None:
            line += f" tc2={tc2:.6g}"
        self._lines.append(line)
        self._nodes.add(node1)
        self._nodes.add(node2)

    def add_capacitor(
        self,
        name: str,
        node1: str,
        node2: str,
        value_f: float,
    ) -> None:
        """添加电容元件。

        Args:
            name: 元件名（不含前缀 C）。
            node1: 节点 1。
            node2: 节点 2。
            value_f: 电容值 (F)。

        Raises:
            ValueError: 名称/节点/值非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"电容名非法 '{name}'"
            raise ValueError(msg)
        self._check_node(node1)
        self._check_node(node2)
        if value_f < 0:
            msg = f"电容值必须 >= 0，得到 {value_f}"
            raise ValueError(msg)
        line = f"C{name} {node1} {node2} {value_f:.6g}"
        self._lines.append(line)
        self._nodes.add(node1)
        self._nodes.add(node2)

    def add_inductor(
        self,
        name: str,
        node1: str,
        node2: str,
        value_h: float,
    ) -> None:
        """添加电感元件。

        Args:
            name: 元件名（不含前缀 L）。
            node1: 节点 1。
            node2: 节点 2。
            value_h: 电感值 (H)。

        Raises:
            ValueError: 名称/节点/值非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"电感名非法 '{name}'"
            raise ValueError(msg)
        self._check_node(node1)
        self._check_node(node2)
        if value_h < 0:
            msg = f"电感值必须 >= 0，得到 {value_h}"
            raise ValueError(msg)
        line = f"L{name} {node1} {node2} {value_h:.6g}"
        self._lines.append(line)
        self._nodes.add(node1)
        self._nodes.add(node2)

    def add_mutual(
        self,
        name: str,
        inductor1: str,
        inductor2: str,
        coupling: float,
    ) -> None:
        """添加互感耦合（K 元件）。

        K = M / sqrt(L1·L2)，取值范围 [0, 1]。

        Args:
            name: 元件名（不含前缀 K）。
            inductor1: 第一个电感元件名（不含前缀 L）。
            inductor2: 第二个电感元件名（不含前缀 L）。
            coupling: 耦合系数 K，范围 [0, 1]。

        Raises:
            ValueError: 名称/耦合系数非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"互感名非法 '{name}'"
            raise ValueError(msg)
        if not inductor1 or not inductor2:
            msg = "电感元件名不能为空"
            raise ValueError(msg)
        if coupling < 0 or coupling > 1:
            msg = f"耦合系数必须在 [0, 1]，得到 {coupling}"
            raise ValueError(msg)
        line = f"K{name} L{inductor1} L{inductor2} {coupling:.6g}"
        self._lines.append(line)

    def add_pi_network(
        self,
        node1: str,
        node2: str,
        resistance_ohm: float,
        inductance_h: float,
        capacitance_f: float,
        tc1: float | None = None,
        tc2: float | None = None,
        suffix: str = "",
    ) -> None:
        """添加 π 型 RLC 寄生网络（串联 R+L，两端并联 C/2）。

        节点：node1 --[R+L]-- internal --[C/2]-- gnd
                                internal --[R+L]-- node2（这里简化为单段串联）
        实际布线：node1 --[R_series + L_series]-- node2，
                  node1 --[C/2]-- gnd，node2 --[C/2]-- gnd

        Args:
            node1: 端口 1 节点。
            node2: 端口 2 节点。
            resistance_ohm: 串联电阻 (Ω)。
            inductance_h: 串联电感 (H)。
            capacitance_f: 总电容 (F)，每端 C/2。
            tc1: 电阻一阶温度系数 (1/°C)，可选。
            tc2: 电阻二阶温度系数 (1/°C²)，可选。
            suffix: 元件名后缀，避免重名。

        Raises:
            ValueError: 参数非法时告警退出。
        """
        self._check_node(node1)
        self._check_node(node2)
        if resistance_ohm < 0 or inductance_h < 0 or capacitance_f < 0:
            msg = (
                f"R/L/C 必须 >= 0，得到 R={resistance_ohm}, "
                f"L={inductance_h}, C={capacitance_f}"
            )
            raise ValueError(msg)
        # 串联 R + L
        if resistance_ohm > 0:
            self.add_resistor(
                f"rs{suffix}", node1, node2, resistance_ohm, tc1, tc2
            )
        if inductance_h > 0:
            self.add_inductor(f"ls{suffix}", node1, node2, inductance_h)
        # 两端并联 C/2
        if capacitance_f > 0:
            half_c = capacitance_f / 2.0
            self.add_capacitor(f"cp1{suffix}", node1, "0", half_c)
            self.add_capacitor(f"cp2{suffix}", node2, "0", half_c)

    def to_string(self, ports: list[str] | None = None) -> str:
        """生成完整 SPICE 子电路网表字符串。

        Args:
            ports: 子电路端口节点列表，默认使用所有已添加节点的字母序首个+末个。

        Returns:
            SPICE 网表字符串。

        Raises:
            ValueError: 端口非法时告警退出。
        """
        if ports is None:
            if not self._nodes:
                msg = "网表为空，未添加任何元件"
                raise ValueError(msg)
            sorted_nodes = sorted(self._nodes)
            if "0" in sorted_nodes:
                # 去除地节点
                non_gnd = [n for n in sorted_nodes if n != "0"]
                if len(non_gnd) >= 2:
                    ports = [non_gnd[0], non_gnd[-1]]
                elif len(non_gnd) == 1:
                    ports = [non_gnd[0], "0"]
                else:
                    ports = ["0"]
            else:
                ports = [sorted_nodes[0], sorted_nodes[-1]] if len(sorted_nodes) >= 2 else sorted_nodes
        if not ports:
            msg = "端口列表不能为空"
            raise ValueError(msg)
        for p in ports:
            self._check_node(p)
        header = f".SUBCKT {self.subckt_name} {' '.join(ports)}"
        body = "\n".join(self._lines)
        footer = ".ENDS"
        return f"{header}\n{body}\n{footer}\n"

    def reset(self) -> None:
        """清空已添加的元件与节点。"""
        self._lines = []
        self._nodes = set()
