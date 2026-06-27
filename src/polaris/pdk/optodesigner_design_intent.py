"""R20 路标：Synopsys OptoDesigner - Design Intent 机制（单层设计 → 多层掩膜自动生成）。

设计师只需绘制单层中心路径与宽度，引擎根据工艺规则自动生成多层掩膜
（WG/SLAB/METAL 等），消除手动多层对齐错误。

本模块为 OptoDesigner 拆分子模块，集中承载学术来源 URL 常量与路径偏移几何工具，
供 pycell/flexconnector/hierarchy/pdaflow 子模块共享。

## 学术依据

- Synopsys OptoDesigner 官方文档
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- Synopsys Photonic Solutions Newsletter 2023.12
  URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- R20 路标: docs/roundmap/R20.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# 学术来源 URL 常量（规则 18 学术诚信）
# ---------------------------------------------------------------------------
_URL_OPTODESIGNER = (
    "https://www.synopsys.com/photonic-solutions/"
    "optocompiler/optodesigner.html"
)
_URL_NEWSLETTER_2023_12 = (
    "https://www.synopsys.com/photonic-solutions/e-news/2023-december.html"
)
_URL_PDAFLOW = "http://pdaflow.org/"
_URL_CMOS_VLSI = "https://www.pearson.com/us/higher-education/program/" \
    "Weste-CMOS-VLSI-Design-A-Circuits-and-Systems-Perspective-4th-Edition/" \
    "PGM320852.html"


@dataclass
class DesignIntent:
    """OptoDesigner Design Intent 机制（单层设计 → 多层掩膜自动生成）。

    设计师只需绘制单层中心路径与宽度，引擎根据工艺规则自动生成多层掩膜
    （WG/SLAB/METAL 等），消除手动多层对齐错误。

    学术依据: Synopsys OptoDesigner 官方文档
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

    转换公式: Mask Layers = T(DesignIntent, Technology)
    其中 T 为转换函数，Technology 含层映射、偏移、加宽规则。

    Attributes:
        path: 中心路径点列表 [(x, y), ...]（μm）。
        width: 波导宽度（μm）。
        wg_type: 波导类型（strip/rib/slot）。
    """

    path: list[tuple[float, float]]
    width: float
    wg_type: str = "strip"


@dataclass
class TechnologyRule:
    """工艺规则（层映射、偏移、加宽）。

    描述 Design Intent 到掩膜层的转换规则：目标 GDSII 层、宽度偏移、用途。

    学术依据: OptoDesigner Design Intent 白皮书
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

    Attributes:
        layer: GDSII 层 (layer_num, datatype)。
        offset: 宽度偏移（μm），如 +0.1 表示 Slab 层比 WG 层宽 0.1μm。
        purpose: 用途（WG/SLAB/METAL）。
    """

    layer: tuple[int, int]
    offset: float = 0.0
    purpose: str = "WG"


class DesignIntentEngine:
    """Design Intent 引擎：单层设计意图 → 多层掩膜自动生成。

    将 DesignIntent（中心路径+宽度）按工艺规则集转换为多层掩膜多边形。
    每条 TechnologyRule 生成一个掩膜层，宽度 = intent.width + rule.offset。

    学术依据: OptoDesigner Design Intent 白皮书
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

    转换公式:
        MaskPolygon_i = OffsetPath(intent.path, intent.width + rule_i.offset)
    """

    def __init__(self, tech_rules: list[TechnologyRule]) -> None:
        """初始化 Design Intent 引擎。

        Args:
            tech_rules: 工艺规则列表。

        Raises:
            ValueError: tech_rules 为空。
        """
        if not tech_rules:
            raise ValueError("tech_rules 不能为空（禁止 fall-back 默认规则）")
        self._rules: list[TechnologyRule] = list(tech_rules)

    def add_rule(self, rule: TechnologyRule) -> None:
        """添加工艺规则。

        Args:
            rule: 待添加的 TechnologyRule 实例。
        """
        self._rules.append(rule)

    @property
    def rules(self) -> list[TechnologyRule]:
        """当前工艺规则列表（只读视图）。"""
        return list(self._rules)

    def generate_masks(
        self, intent: DesignIntent
    ) -> dict[tuple[int, int], list[list[tuple[float, float]]]]:
        """将设计意图转换为多层掩膜多边形。

        对每条工艺规则，沿中心路径两侧偏移 (width+offset)/2 生成多边形。

        Args:
            intent: 设计意图（中心路径+宽度+类型）。

        Returns:
            层 → 多边形列表的映射。每个多边形为顶点列表 [(x, y), ...]。

        Raises:
            ValueError: 路径点不足 2 个。
        """
        if len(intent.path) < 2:
            raise ValueError(
                f"DesignIntent 路径至少需要 2 个点，得到 {len(intent.path)}"
            )
        masks: dict[tuple[int, int], list[list[tuple[float, float]]]] = {}
        for rule in self._rules:
            half_w = (intent.width + rule.offset) / 2.0
            polygon = _offset_path_to_polygon(intent.path, half_w)
            masks.setdefault(rule.layer, []).append(polygon)
        return masks


def _offset_path_to_polygon(
    path: list[tuple[float, float]], half_width: float
) -> list[tuple[float, float]]:
    """沿路径两侧偏移 half_width 生成闭合多边形。

    算法: 对每段路径计算法向量，左侧偏移 +half_width，右侧偏移 -half_width，
    左侧点正向排列 + 右侧点反向排列构成闭合多边形。

    Args:
        path: 中心路径点列表。
        half_width: 半宽（μm）。

        Returns:
            闭合多边形顶点列表 [(x, y), ...]。

    Raises:
        ValueError: half_width 非正。
    """
    if half_width <= 0:
        raise ValueError(f"half_width 必须 > 0，得到 {half_width}")
    pts = np.asarray(path, dtype=float)
    n = len(pts)
    left_pts: list[tuple[float, float]] = []
    right_pts: list[tuple[float, float]] = []
    for i in range(n):
        if i == 0:
            tangent = pts[1] - pts[0]
        elif i == n - 1:
            tangent = pts[-1] - pts[-2]
        else:
            tangent = pts[i + 1] - pts[i - 1]
        norm = float(np.hypot(tangent[0], tangent[1]))
        if norm < 1e-12:
            continue
        # 法向量（左侧）：旋转 90° 逆时针
        nx = -tangent[1] / norm
        ny = tangent[0] / norm
        left_pts.append((pts[i, 0] + nx * half_width, pts[i, 1] + ny * half_width))
        right_pts.append((pts[i, 0] - nx * half_width, pts[i, 1] - ny * half_width))
    return left_pts + right_pts[::-1]


__all__ = [
    "DesignIntent",
    "DesignIntentEngine",
    "TechnologyRule",
    "_URL_CMOS_VLSI",
    "_URL_NEWSLETTER_2023_12",
    "_URL_OPTODESIGNER",
    "_URL_PDAFLOW",
    "_offset_path_to_polygon",
]
