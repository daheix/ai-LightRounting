"""R231-R235 寄生提取一站式聚合门面（AdvancedParasiticExtractor）。

从 v4 ``polaris.sim.parasitic_advanced`` 迁移至 polaris-parasitic 子模块
（R13: 不保留 v4 兼容路径）。综合 R231-R235 五大能力：电阻/电容/电感/S 参数/
SPICE 网表，对齐 Synopsys StarRC / Cadence Quantus QRC。

## 架构说明（facade 模式）

本文件为聚合门面，实现已拆分到子模块，对外提供一站式 ``extract_all`` /
``compute_s_params`` / ``write_spice_netlist`` 接口：
- ``resistance`` — ParasiticResistor (R231)
- ``capacitance`` — ParasiticCapacitor (R232)
- ``inductance`` — ParasiticInductor (R233)
- ``sparam`` — ParasiticSParam (R234)
- ``spice`` — SpiceNetlistWriter (R235)

学术依据（≥5 文献 URL，R02 学术诚信）:
- Synopsys StarRC Datasheet（Gold Standard 寄生提取，RLCK 模型，TC1/TC2）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Synopsys StarRC Resistance Extraction Blog（RPSQ × L/W 片电阻公式）:
  https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
- Synopsys StarRC Custom Datasheet（Rapid3D 场求解，3D 耦合电容）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-custom-ds.pdf
- Cadence Quantus QRC 3D 场求解器精度研究:
  https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
- UCLA ECE902 电容提取教程（电容矩阵，2.5D 基础，耦合电容屏蔽效应）:
  http://eda.ee.ucla.edu/ECE902_pd/cap1.pdf
- Banerjee ECE 225 UCSB Lecture 6（边缘电容 arcosh 模型，VLSI 互连）:
  http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
- Arora et al., IEEE TCAD 15(1), 1996（互连电容建模，doi:10.1109/43.534256）:
  https://www.stanford.edu/class/archive/ee/ee371/ee371.1066/handouts/arora96.pdf
- Wheeler, "Inductance Formulas for Single-Layer Coils", Proc. IRE 1928:
  https://ieeexplore.ieee.org/document/1654891
- Rosa, "The Self and Mutual Inductances of Linear Conductors", NIST BS 1908:
  https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
- Pozar, "Microwave Engineering", 4th ed., §4 (ABCD → S 参数变换)

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简 / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from polaris_parasitic.capacitance import ParasiticCapacitor
from polaris_parasitic.inductance import ParasiticInductor
from polaris_parasitic.resistance import ParasiticResistor
from polaris_parasitic.spice import SpiceNetlistWriter
from polaris_parasitic.sparam import ParasiticSParam

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
