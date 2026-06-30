"""DRC 规则定义模块（从 drc_curvilinear_18rules.py 拆分，R181-R200）。

定义 18 类曲线感知 DRC 规则的枚举、规则 dataclass、违规记录 dataclass。
对齐 Synopsys OptoDesigner DRC 模块 + Siemens Calibre nmDRC + KLayout DRC。

学术依据:
- Synopsys OptoDesigner DRC Module（18 类曲线感知规则）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- KLayout DRC Reference (曲线感知规则)
  URL: https://www.klayout.de/doc-qt5/manual/drc.html
- Siemens Calibre nmDRC
  URL: https://www.siemens.com/en-us/products/ic/ic-custom/verification/calibre-nmdrc/
- OpenROAD DRC Engine
  URL: https://openroad.readthedocs.io/en/latest/main/src/drt/README.html
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
- PDRC, Jiang et al., DAC 2024,
  http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DRCRuleCategory(str, Enum):
    """18 类 DRC 规则分类（对齐 OptoDesigner DRC 模块）。"""
    # 宽度类 (3)
    MIN_WIDTH = "min_width"
    MAX_WIDTH = "max_width"
    MIN_WIDTH_CURVE = "min_width_curve"  # 曲线最小宽度
    # 间距类 (4)
    MIN_SPACING = "min_spacing"
    MIN_SPACING_SAME_NET = "min_spacing_same_net"
    MIN_SPACING_DENSITY = "min_spacing_density"
    MIN_END_TO_END = "min_end_to_end"
    # 包围类 (2)
    MIN_ENCLOSURE = "min_enclosure"
    MIN_EXTENSION = "min_extension"
    # 面积类 (3)
    MIN_AREA = "min_area"
    MAX_AREA = "max_area"
    MIN_DENSITY = "min_density"
    # 角度类 (3)
    MAX_ANGLE = "max_angle"  # 最大拐角
    MIN_ANGLE = "min_angle"  # 最小拐角（锐角禁止）
    ACUTE_ANGLE = "acute_angle_check"  # 锐角检测
    # 曲线类 (3)
    MIN_BEND_RADIUS = "min_bend_radius"  # 最小弯曲半径
    MAX_CURVATURE = "max_curvature"  # 最大曲率
    TAPER_ANGLE = "taper_angle"  # 锥形角度


@dataclass
class CurvilinearDRCRule:
    """曲线感知 DRC 规则。"""
    name: str
    category: DRCRuleCategory
    layer: str
    limit_value: float
    units: str = "μm"
    is_curvilinear: bool = False
    description: str = ""
    severity: str = "error"


@dataclass
class DRCViolation18:
    """DRC 违规记录。"""
    rule_name: str
    category: str
    layer: str
    severity: str
    message: str
    location_um: tuple[float, float] = (0.0, 0.0)
    measured_value: float = 0.0
    limit_value: float = 0.0
