"""R231-R235 寄生提取进阶模块（对齐 Synopsys StarRC / Cadence Quantus QRC）。

在 layout_aware.ParasiticExtractor 基础上扩展：
- R231 寄生电阻提取（片电阻 + 一阶/二阶温度系数 TC1/TC2）
- R232 寄生电容提取（平行板 + 侧边/边缘电容修正 + 多导体耦合电容矩阵）
- R233 寄生电感提取（Grover/Wheeler 自感解析公式 + Neumann 互感）
- R234 S 参数生成（从 RLC 寄生构建 π 型网络 → ABCD → S，无源性/互易性验证）
- R235 SPICE 网表输出（生成兼容 SPICE 的 .subckt，含 TC1/TC2）

## 架构说明（facade 模式，批次 10-B 续 超长文件拆分）

本文件为 facade 入口，实现已按功能拆分到子模块，外部 import 路径
与公共 API 完全保持不变：
- ``parasitic_resistance`` — ParasiticResistor (R231)
- ``parasitic_capacitance`` — ParasiticCapacitor (R232)
- ``parasitic_inductance`` — ParasiticInductor (R233)
- ``parasitic_sparam`` — ParasiticSParam (R234)
- ``parasitic_spice`` — SpiceNetlistWriter (R235)
本文件保留 AdvancedParasiticExtractor 一站式聚合门面（综合 R231-R235）。

学术依据（≥5 文献 URL，R02 学术诚信）:
- Synopsys StarRC Datasheet（Gold Standard 寄生提取，RLCK 模型，TC1/TC2）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Synopsys StarRC Resistance Extraction Blog（RPSQ × L/W 片电阻公式）:
  https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
- Synopsys StarRC Custom Datasheet（Rapid3D 场求解，3D 耦合电容）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-custom-ds.pdf
- Cadence Quantus QRC 3D 场求解器精度研究:
  https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
- Cadence PCB 互容/互感解析（奇偶模阻抗法）:
  https://resources.pcb.cadence.com/blog/mutual-capacitance-and-mutual-inductance-calculation
- UCLA ECE902 电容提取教程（电容矩阵，2.5D 基础，耦合电容屏蔽效应）:
  http://eda.ee.ucla.edu/ECE902_pd/cap1.pdf
- Banerjee ECE 225 UCSB Lecture 6（边缘电容 arcosh 模型，VLSI 互连）:
  http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
- Arora et al., IEEE TCAD 15(1), 1996（互连电容建模，doi:10.1109/43.534256）:
  https://www.stanford.edu/class/archive/ee/ee371/ee371.1066/handouts/arora96.pdf
- Wheeler, "Inductance Formulas for Single-Layer Coils", Proc. IRE 1928:
  https://ieeexplore.ieee.org/document/1654891
- Grover, "Inductance Calculations: Working Formulas and Tables", 1946（互感 Neumann 公式）
- Rosa, "The Self and Mutual Inductances of Linear Conductors", NIST BS 1908:
  https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
- Pozar, "Microwave Engineering", 4th ed., §4 (ABCD → S 参数变换)
- Altair SimLab Parasitics Extraction（Touchstone .sNp 导出 + SPICE 导出）:
  https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from polaris.sim.parasitic_capacitance import ParasiticCapacitor
from polaris.sim.parasitic_inductance import ParasiticInductor
from polaris.sim.parasitic_resistance import ParasiticResistor
from polaris.sim.parasitic_spice import SpiceNetlistWriter
from polaris.sim.parasitic_sparam import ParasiticSParam

__all__ = [
    "ParasiticResistor",
    "ParasiticCapacitor",
    "ParasiticInductor",
    "ParasiticSParam",
    "SpiceNetlistWriter",
    "AdvancedParasiticExtractor",
]


# =============================================================================
# 一站式寄生提取器：综合 R231-R235
# =============================================================================
@dataclass
class AdvancedParasiticExtractor:
    """一站式寄生提取器：综合 R231-R235，输出 RLC + S 参数 + SPICE 网表。

    工作流：
        1. extract_resistance (R231) → R + 温度系数
        2. extract_capacitance (R232) → C_pp + C_fringe + C_coupling
        3. extract_inductance (R233) → L_self + M_mutual
        4. compute_s_params (R234) → 频域 S 参数
        5. write_spice_netlist (R235) → .subckt 文本

    来源（≥5 文献 URL）见各组件类 docstring。
    """

    resistor: ParasiticResistor = field(default_factory=lambda: ParasiticResistor(0.05))
    capacitor: ParasiticCapacitor = field(
        default_factory=lambda: ParasiticCapacitor(eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0)
    )
    inductor: ParasiticInductor = field(
        default_factory=lambda: ParasiticInductor(metal_thickness_um=0.5)
    )

    def extract_all(
        self,
        length_um: float,
        width_um: float,
        temperature_c: float | None = None,
    ) -> dict[str, object]:
        """一次性提取 R/L/C 寄生参数。

        Args:
            length_um: 导线长度 (μm)。
            width_um: 导线宽度 (μm)。
            temperature_c: 工作温度 (°C)，可选。

        Returns:
            {"resistance": dict, "capacitance": dict, "inductance": dict}

        Raises:
            ValueError: 几何参数非法时告警退出。
        """
        return {
            "resistance": self.resistor.extract(length_um, width_um, temperature_c),
            "capacitance": self.capacitor.extract_self(length_um, width_um),
            "inductance": self.inductor.extract_self(length_um, width_um),
        }

    def compute_s_params(
        self,
        frequencies_ghz: NDArray[np.float64] | list[float],
        resistance_ohm: float,
        inductance_ph: float,
        capacitance_ff: float,
        z0_ohm: float = 50.0,
    ) -> NDArray[np.complex128]:
        """计算 S 参数（委托 ParasiticSParam）。"""
        return ParasiticSParam.compute_s_params(
            frequencies_ghz, resistance_ohm, inductance_ph, capacitance_ff, z0_ohm
        )

    def write_spice_netlist(
        self,
        node1: str,
        node2: str,
        resistance_ohm: float,
        inductance_h: float,
        capacitance_f: float,
        tc1: float | None = None,
        tc2: float | None = None,
        subckt_name: str = "parasitic_net",
    ) -> str:
        """生成 SPICE 子电路网表。

        Args:
            node1: 端口 1 节点。
            node2: 端口 2 节点。
            resistance_ohm: 串联电阻 (Ω)。
            inductance_h: 串联电感 (H)。
            capacitance_f: 总电容 (F)。
            tc1: 电阻一阶温度系数 (1/°C)，可选。
            tc2: 电阻二阶温度系数 (1/°C²)，可选。
            subckt_name: 子电路名。

        Returns:
            SPICE 网表字符串。
        """
        writer = SpiceNetlistWriter(subckt_name=subckt_name)
        writer.add_pi_network(
            node1, node2, resistance_ohm, inductance_h, capacitance_f, tc1, tc2
        )
        return writer.to_string(ports=[node1, node2])
