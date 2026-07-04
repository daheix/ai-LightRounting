"""验证基础类型内化模块（消除 polaris.sim.constraint_types / polaris.sim.lvs 依赖）。

包含 ViolationType/Violation（DRC 违规类型）、LVSMismatchType（LVS 不匹配类型）、
ExtractedNetlist（提取网表）、_find_layer_index（KLayout 层索引查找）。

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC runset: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Calibre nmLVS: https://eda.sw.siemens.com/en-US/calibre/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np  # noqa: F401  R04 纯 NumPy 依赖一致性


class VerifyError(RuntimeError):
    """verify_advanced 模块统一业务异常（R03 禁止 fall-back）。

    用于 DRC/LVS 检查中"假数据兜底"场景的替代：当检查无法正常执行
    （如规则配置缺失、GDS 数据非法、阈值非法等）时，必须 raise 本异常，
    而非返回空违规列表让调用方误以为检查通过。

    合法的"空输入产生空输出"不在本异常覆盖范围（应直接返回空列表 + 注释）。

    来源:
    - R03 禁止 fall-back: /workspace/.trae/rules/R03-禁止fall-back.md
    - Calibre nmDRC 错误处理: https://eda.sw.siemens.com/en-US/calibre/
    - KLayout DRC runset 错误模型:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """

    pass


class ViolationType(Enum):
    """违规类型枚举（覆盖 SiEPIC EBeam PDK 与商业 foundry runset 常见规则类别）。

    来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK；
    KLayout DRC 规则类别: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """

    BEND_RADIUS = "bend_radius"
    SPACING = "spacing"
    INSERTION_LOSS = "insertion_loss"
    CROSSTALK = "crosstalk"
    CROSSING = "crossing"
    OVERLAP = "overlap"
    THERMAL = "thermal"
    MIN_WIDTH = "min_width"
    COUPLING_GAP = "coupling_gap"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_AREA = "min_area"
    ENCLOSURE = "enclosure"
    NOTCH = "notch"
    PORT_CONNECTIVITY = "port_connectivity"
    PIN_MATCH = "pin_match"
    LAYER_DENSITY = "layer_density"


@dataclass
class Violation:
    """约束违规记录。"""

    vtype: ViolationType
    severity: float = 0.0
    message: str = ""
    device_name: str = ""
    net_id: str = ""
    location: tuple[float, float] | None = None


class LVSMismatchType(Enum):
    """LVS 不匹配类型（与 KLayout LVS 比对状态对应）。

    来源: KLayout LVS 比对状态
    https://www.klayout.org/doc-qt5/manual/lvs.html
    """

    MISSING_DEVICE = "missing_device"
    EXTRA_DEVICE = "extra_device"
    DEVICE_TYPE_MISMATCH = "device_type_mismatch"
    MISSING_CONNECTION = "missing_connection"
    EXTRA_CONNECTION = "extra_connection"


@dataclass
class ExtractedNetlist:
    """从 GDS 提取的网表。

    Attributes:
        devices: 器件名列表（从 DEVREC 层提取）。
        connections: 连接列表 [(dev1, dev2), ...]（从波导邻近关系提取）。
    """

    devices: list[str] = field(default_factory=list)
    connections: list[tuple[str, str]] = field(default_factory=list)


def _find_layer_index(layout, layer_num: int, datatype: int) -> int | None:
    """查找 GDS 中指定层的索引。

    Args:
        layout: KLayout Layout 对象。
        layer_num: GDS layer number。
        datatype: GDS datatype。

    Returns:
        层索引，层不存在返回 None。

    Note:
        合法：查找失败返回 None，调用方应检查（如 _get_layer_index 中
        layer_idx is None 时视为 GDS 无该层并跳过规则，而非业务错误）。
    """
    for idx in layout.layer_indexes():
        info = layout.get_info(idx)
        if info.layer == layer_num and info.datatype == datatype:
            return idx
    return None  # 合法：GDS 中无此 (layer, datatype) 组合，调用方应检查


__all__ = [
    "VerifyError",
    "ViolationType",
    "Violation",
    "LVSMismatchType",
    "ExtractedNetlist",
    "_find_layer_index",
]
