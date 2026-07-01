"""测试芯片设计（P0-24，批次 10-B 拆分子模块）。

本子模块定义测试芯片设计器：
- :class:`TestType`: 测试类型枚举（DC/RF/Optical/Thermal/Reliability）
- :class:`TestStructure`: 测试结构
- :class:`TestChipDesigner`: 测试芯片设计器（11 种标准测试结构 + 布图 + 测试计划）

包含: DC/RF/光学/热/可靠性 测试结构阵列。
对齐: JEDEC JESD22 / IEEE P1687 IJTAG。

## 学术依据

- IEEE P1687 IJTAG test infrastructure
  URL: https://standards.ieee.org/standard/1687-2014.html
- JEDEC JESD22 可靠性测试标准
  URL: https://www.jedec.org/standards-documents/results/term/213
- Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., Wiley 2006
  URL: https://www.wiley.com/en-us/Physics+of+Semiconductor+Devices-9780471143239

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。

来源（拆分依据）:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html


## 补充文献（R02 学术诚信补齐）
- gdsfactory 主站: https://gdsfactory.com/
- Python 文档: https://docs.python.org/3/
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TestType(str, Enum):
    DC = "dc"
    RF = "rf"
    OPTICAL = "optical"
    THERMAL = "thermal"
    RELIABILITY = "reliability"


@dataclass
class TestStructure:
    """测试结构。"""
    name: str
    test_type: TestType
    description: str
    area_um2: float = 0.0
    pads: int = 0


class TestChipDesigner:
    """测试芯片 (Test Chip) 设计器。

    包含: DC/RF/光学/热/可靠性 测试结构阵列。
    对齐: JEDEC JESD22 / IEEE P1687 IJTAG。
    """

    def __init__(self) -> None:
        self._structures: list[TestStructure] = []
        self._register_standard()

    def add_structure(self, ts: TestStructure) -> None:
        self._structures.append(ts)

    def _register_standard(self) -> None:
        # DC 测试
        self.add_structure(TestStructure(
            "van_der_pauw_sheet_resistance", TestType.DC,
            "范德堡法测方块电阻", area_um2=40000, pads=4,
        ))
        self.add_structure(TestStructure(
            "contact_chain", TestType.DC,
            "接触孔链测试", area_um2=20000, pads=2,
        ))
        self.add_structure(TestStructure(
            "diode_iv", TestType.DC,
            "PN 结 IV 特性", area_um2=10000, pads=2,
        ))
        # RF 测试
        self.add_structure(TestStructure(
            "cpw_line_thru", TestType.RF,
            "共面波导直通线", area_um2=15000, pads=4,
        ))
        self.add_structure(TestStructure(
            "rf_pad_open_short", TestType.RF,
            "RF Pad 开路/短路去嵌", area_um2=5000, pads=2,
        ))
        # 光学测试
        self.add_structure(TestStructure(
            "wg_propagation_loss", TestType.OPTICAL,
            "波导传输损耗测试 (cut-back)", area_um2=100000, pads=0,
        ))
        self.add_structure(TestStructure(
            "grating_coupler_efficiency", TestType.OPTICAL,
            "光栅耦合效率测试", area_um2=30000, pads=0,
        ))
        self.add_structure(TestStructure(
            "ring_resonator_q", TestType.OPTICAL,
            "环形谐振器 Q 值测试", area_um2=20000, pads=0,
        ))
        # 热测试
        self.add_structure(TestStructure(
            "heater_thermal_resistance", TestType.THERMAL,
            "加热器热阻测试", area_um2=15000, pads=2,
        ))
        # 可靠性
        self.add_structure(TestStructure(
            "electromigration_stripe", TestType.RELIABILITY,
            "电迁移测试条", area_um2=10000, pads=2,
        ))
        self.add_structure(TestStructure(
            "tddb_capacitor", TestType.RELIABILITY,
            "经时击穿测试电容", area_um2=8000, pads=2,
        ))

    @property
    def total_structures(self) -> int:
        return len(self._structures)

    def total_area_um2(self) -> float:
        return sum(s.area_um2 for s in self._structures)

    def by_type(self, test_type: TestType) -> list[TestStructure]:
        return [s for s in self._structures if s.test_type == test_type]

    def floorplan(
        self,
        die_size_um: tuple[float, float] = (3000.0, 3000.0),
    ) -> dict[str, Any]:
        """生成初步布图规划。"""
        total = self.total_area_um2()
        die_area = die_size_um[0] * die_size_um[1]
        utilization = total / die_area
        return {
            "die_size_um": list(die_size_um),
            "total_structures": self.total_structures,
            "total_structure_area_um2": total,
            "die_area_um2": die_area,
            "utilization": utilization,
            "by_type_counts": {
                t.value: len(self.by_type(t)) for t in TestType
            },
        }

    def test_plan(self) -> dict[str, list[str]]:
        """生成测试计划大纲。"""
        return {
            "DC": [s.name for s in self.by_type(TestType.DC)],
            "RF": [s.name for s in self.by_type(TestType.RF)],
            "Optical": [s.name for s in self.by_type(TestType.OPTICAL)],
            "Thermal": [s.name for s in self.by_type(TestType.THERMAL)],
            "Reliability": [s.name for s in self.by_type(TestType.RELIABILITY)],
        }


__all__ = [
    "TestType",
    "TestStructure",
    "TestChipDesigner",
]
