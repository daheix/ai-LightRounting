"""R20 路标：Synopsys OptoDesigner - PyCell API（Python 脚本驱动参数化版图）。

PyCell 工厂：Python 脚本驱动的参数化版图生成 API，对齐 OptoDesigner PyCells，
支持参数化器件生成（straight/bend/DC/MMI/ring/taper/y_branch/crossing/
grating_coupler/terminator）。

## 学术依据

- Synopsys Photonic Solutions Newsletter 2023.12（PyCell 参数化版图）
  URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html
- Synopsys OptoDesigner 官方文档
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- R20 路标: docs/roundmap/R20.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from polaris.pdk.optodesigner_design_intent import _URL_NEWSLETTER_2023_12


@dataclass
class PyCell:
    """OptoDesigner PyCell 兼容的参数化版图单元。

    学术依据: Synopsys Photonic Solutions Newsletter 2023.12
    URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html

    公式: Cell(p) = PyCell_function(p) → Component

    Attributes:
        name: 单元名称。
        params: 参数字典。
        polygons: GDSII 多边形列表（每个多边形为顶点列表）。
        ports: 光学端口列表（每个端口为 (name, x, y, angle, width)）。
        metadata: 元数据字典。
    """

    name: str
    params: dict = field(default_factory=dict)
    polygons: list = field(default_factory=list)
    ports: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class PyCellFactory:
    """PyCell 工厂：Python 脚本驱动的参数化版图生成 API。

    对齐 OptoDesigner PyCells，支持参数化器件生成（straight/bend/DC/MMI/
    ring/taper/y_branch/crossing/grating_coupler/terminator）。

    学术依据: Synopsys Photonic Solutions Newsletter 2023.12
    URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html
    """

    def straight(self, length: float = 10.0, width: float = 0.5) -> PyCell:
        """直波导 PyCell。

        Args:
            length: 长度（μm）。
            width: 宽度（μm）。

        Returns:
            直波导 PyCell，含 1 个矩形多边形 + 2 个端口。
        """
        poly = [(0.0, -width / 2), (length, -width / 2),
                (length, width / 2), (0.0, width / 2)]
        return PyCell(
            name="straight",
            params={"length": length, "width": width},
            polygons=[poly],
            ports=[("in", 0.0, 0.0, 180.0, width), ("out", length, 0.0, 0.0, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def bend(self, radius: float = 5.0, angle: float = 90.0, width: float = 0.5) -> PyCell:
        """弯曲波导 PyCell（圆弧）。

        Args:
            radius: 弯曲半径（μm）。
            angle: 弯曲角度（度）。
            width: 宽度（μm）。

        Returns:
            弯曲波导 PyCell。
        """
        n_pts = max(16, int(abs(angle) / 5) + 1)
        thetas = np.linspace(0, math.radians(angle), n_pts)
        center_x, center_y = radius, 0.0
        outer = [(center_x + (radius + width / 2) * math.cos(t),
                  center_y + (radius + width / 2) * math.sin(t)) for t in thetas]
        inner = [(center_x + (radius - width / 2) * math.cos(t),
                  center_y + (radius - width / 2) * math.sin(t)) for t in thetas]
        poly = outer + inner[::-1]
        start_angle = 180.0
        end_angle = 180.0 + angle
        return PyCell(
            name="bend",
            params={"radius": radius, "angle": angle, "width": width},
            polygons=[poly],
            ports=[("in", center_x + radius, center_y, start_angle, width),
                   ("out", center_x + radius * math.cos(math.radians(angle)),
                    center_y + radius * math.sin(math.radians(angle)), end_angle, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def directional_coupler(
        self, length: float = 10.0, gap: float = 0.2, width: float = 0.5
    ) -> PyCell:
        """定向耦合器 PyCell（双平行波导）。

        Args:
            length: 耦合区长度（μm）。
            gap: 耦合间隙（μm）。
            width: 波导宽度（μm）。

        Returns:
            定向耦合器 PyCell，含 2 个多边形 + 4 个端口。
        """
        top_y = (gap + width) / 2
        bot_y = -(gap + width) / 2
        poly_top = [(0, top_y - width / 2), (length, top_y - width / 2),
                    (length, top_y + width / 2), (0, top_y + width / 2)]
        poly_bot = [(0, bot_y - width / 2), (length, bot_y - width / 2),
                    (length, bot_y + width / 2), (0, bot_y + width / 2)]
        return PyCell(
            name="directional_coupler",
            params={"length": length, "gap": gap, "width": width},
            polygons=[poly_top, poly_bot],
            ports=[("in1", 0, top_y, 180, width), ("in2", 0, bot_y, 180, width),
                   ("out1", length, top_y, 0, width),
                   ("out2", length, bot_y, 0, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def mmi_1x2(self, length: float = 10.0, width: float = 2.0) -> PyCell:
        """MMI 1x2 PyCell（梯形多模干涉器）。

        Args:
            length: MMI 长度（μm）。
            width: MMI 宽度（μm）。

        Returns:
            MMI 1x2 PyCell，含 1 个多边形 + 3 个端口。
        """
        port_w = 0.5
        poly = [(0, -port_w / 2), (2, -width / 2), (length - 2, -width / 2),
                (length, -port_w / 2), (length, port_w / 2),
                (length - 2, width / 2), (2, width / 2), (0, port_w / 2)]
        return PyCell(
            name="mmi_1x2",
            params={"length": length, "width": width},
            polygons=[poly],
            ports=[("in", 0, 0, 180, port_w),
                   ("out1", length, width / 4, 0, port_w),
                   ("out2", length, -width / 4, 0, port_w)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def ring_resonator(
        self, radius: float = 10.0, gap: float = 0.2, width: float = 0.5
    ) -> PyCell:
        """环谐振器 PyCell（环 + 总线波导）。

        Args:
            radius: 环半径（μm）。
            gap: 耦合间隙（μm）。
            width: 波导宽度（μm）。

        Returns:
            环谐振器 PyCell，含环多边形 + 总线多边形 + 2 个端口。
        """
        n_pts = 64
        thetas = np.linspace(0, 2 * math.pi, n_pts, endpoint=False)
        outer = [(radius * math.cos(t), radius * math.sin(t))
                 for t in thetas]
        inner = [((radius - width) * math.cos(t), (radius - width) * math.sin(t))
                 for t in thetas]
        ring_poly = outer + inner[::-1]
        bus_y = radius + gap + width / 2
        bus_poly = [(-radius - 5, bus_y - width / 2),
                    (radius + 5, bus_y - width / 2),
                    (radius + 5, bus_y + width / 2),
                    (-radius - 5, bus_y + width / 2)]
        return PyCell(
            name="ring_resonator",
            params={"radius": radius, "gap": gap, "width": width},
            polygons=[ring_poly, bus_poly],
            ports=[("in", -radius - 5, bus_y, 180, width),
                   ("through", radius + 5, bus_y, 0, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def taper(
        self, length: float = 5.0, width1: float = 0.5, width2: float = 1.0
    ) -> PyCell:
        """锥形器 PyCell（线性变宽）。

        Args:
            length: 长度（μm）。
            width1: 起始宽度（μm）。
            width2: 终止宽度（μm）。

        Returns:
            锥形器 PyCell。
        """
        poly = [(0, -width1 / 2), (length, -width2 / 2),
                (length, width2 / 2), (0, width1 / 2)]
        return PyCell(
            name="taper",
            params={"length": length, "width1": width1, "width2": width2},
            polygons=[poly],
            ports=[("in", 0, 0, 180, width1), ("out", length, 0, 0, width2)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def y_branch(self, length: float = 10.0, width: float = 0.5) -> PyCell:
        """Y 分支 PyCell（1→2 分束）。

        Args:
            length: 分支长度（μm）。
            width: 波导宽度（μm）。

        Returns:
            Y 分支 PyCell，含 2 个分支多边形 + 3 个端口。
        """
        sep = 2.0
        poly_top = [(0, 0), (length, sep), (length, sep - width), (0, width)]
        poly_bot = [(0, 0), (0, -width), (length, -sep + width), (length, -sep)]
        return PyCell(
            name="y_branch",
            params={"length": length, "width": width},
            polygons=[poly_top, poly_bot],
            ports=[("in", 0, 0, 180, width),
                   ("out1", length, sep - width / 2, 0, width),
                   ("out2", length, -sep + width / 2, 0, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def crossing(self, length: float = 10.0, width: float = 0.5) -> PyCell:
        """波导交叉 PyCell（十字形）。

        Args:
            length: 交叉臂长度（μm）。
            width: 波导宽度（μm）。

        Returns:
            交叉 PyCell，含水平+垂直 2 个多边形 + 4 个端口。
        """
        h = length / 2
        poly_h = [(-h, -width / 2), (h, -width / 2), (h, width / 2), (-h, width / 2)]
        poly_v = [(-width / 2, -h), (width / 2, -h), (width / 2, h), (-width / 2, h)]
        return PyCell(
            name="crossing",
            params={"length": length, "width": width},
            polygons=[poly_h, poly_v],
            ports=[("in1", -h, 0, 180, width), ("out1", h, 0, 0, width),
                   ("in2", 0, -h, 270, width), ("out2", 0, h, 90, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def grating_coupler(
        self, period: float = 0.66, duty_cycle: float = 0.5, n_periods: int = 20
    ) -> PyCell:
        """光栅耦合器 PyCell（周期性齿形）。

        Args:
            period: 光栅周期（μm）。
            duty_cycle: 占空比（0-1）。
            n_periods: 周期数。

        Returns:
            光栅耦合器 PyCell，含 n_periods 个齿多边形 + 2 个端口。

        Raises:
            ValueError: duty_cycle 不在 (0,1) 或 n_periods <= 0。
        """
        if not 0 < duty_cycle < 1:
            raise ValueError(f"duty_cycle 须在 (0,1)，得到 {duty_cycle}")
        if n_periods <= 0:
            raise ValueError(f"n_periods 须 > 0，得到 {n_periods}")
        width = 10.0
        tooth_w = period * duty_cycle
        polys: list[list[tuple[float, float]]] = []
        for i in range(n_periods):
            x0 = i * period
            polys.append([(x0, -width / 2), (x0 + tooth_w, -width / 2),
                          (x0 + tooth_w, width / 2), (x0, width / 2)])
        total_len = n_periods * period
        return PyCell(
            name="grating_coupler",
            params={"period": period, "duty_cycle": duty_cycle, "n_periods": n_periods},
            polygons=polys,
            ports=[("fiber", 0, 0, 90, width),
                   ("waveguide", total_len, 0, 0, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )

    def terminator(self, length: float = 5.0, width: float = 0.5) -> PyCell:
        """终端器 PyCell（三角形渐变终止）。

        Args:
            length: 终止长度（μm）。
            width: 起始宽度（μm）。

        Returns:
            终端器 PyCell，含 1 个三角形多边形 + 1 个端口。
        """
        poly = [(0, -width / 2), (0, width / 2), (length, 0)]
        return PyCell(
            name="terminator",
            params={"length": length, "width": width},
            polygons=[poly],
            ports=[("in", 0, 0, 180, width)],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )


__all__ = [
    "PyCell",
    "PyCellFactory",
]
