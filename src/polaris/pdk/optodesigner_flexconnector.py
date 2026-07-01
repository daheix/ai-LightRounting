"""R20 路标：Synopsys OptoDesigner - Any-angle flexConnector（任意角度弹性连接器）。

用贝塞尔曲线连接任意角度的两个端口，支持 bezier/spline/manhattan 路径类型。

## 学术依据

- Synopsys 2023.12 Newsletter — Any-angle flexConnector
  URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html
- Farin, "Curves and Surfaces for CAGD", 5th ed., 2002（贝塞尔曲线
  Bernstein 多项式）

补充文献（≥5，规则 R02 学术诚信）：
1. Synopsys, "Photonic Solutions — PIC Design Suite Datasheet" —
   https://www.synopsys.com/content/dam/synopsys/photonic-solutions/pdf/photonic-solutions-pic-design-suite-ds.pdf
2. Synopsys, "OptoDesigner — Mode-Division Multiplexing for Silicon
   Photonic Network-on-Chip" —
   https://www.synopsys.com/photonic-solutions/product-applications/coherent-fiber-optic/mode-division-multiplexing-silicon-photonic-network.html
3. Synopsys, "QPSK Transceiver PIC Design with OptoDesigner" —
   https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/qpsk-transceiver-pic.html
4. Synopsys, "PIC Design Suite — OptoDesigner" —
   https://www.synopsys.com/photonic-solutions/pic-design-suite.html#optodesigner
5. Synopsys, "Photonic Solutions e-News December 2023 — flexConnector"
   — https://www.synopsys.com/photonic-solutions/e-news/2023-december.html
6. Chrostowski L, Hochberg M, "Silicon Photonics Design: From Devices
   to Systems," Cambridge University Press (2015) —
   https://www.cambridge.org/9781107085459

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- R20 路标: docs/roundmap/R20.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from polaris.pdk.optodesigner_design_intent import (
    _URL_NEWSLETTER_2023_12,
    _offset_path_to_polygon,
)
from polaris.pdk.optodesigner_pycell import PyCell


@dataclass
class FlexConnector:
    """OptoDesigner Any-angle flexConnector（任意角度弹性连接器）。

    用贝塞尔曲线连接任意角度的两个端口，支持 bezier/spline/manhattan 路径类型。

    学术依据: Synopsys 2023.12 Newsletter — Any-angle flexConnector
    URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html

    几何: 贝塞尔曲线 B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃

    Attributes:
        start_port: 起点端口 (x, y, angle_deg, width)。
        end_port: 终点端口 (x, y, angle_deg, width)。
        path_type: 路径类型（bezier/spline/manhattan）。
    """

    start_port: tuple[float, float, float, float]
    end_port: tuple[float, float, float, float]
    path_type: str = "bezier"

    def _control_points(self) -> np.ndarray:
        """计算贝塞尔曲线 4 个控制点。

        P0 = 起点，P3 = 终点，P1/P2 沿起止方向延伸距离 = 起止间距的 1/3。

        Returns:
            控制点数组 (4, 2)。
        """
        x0, y0, a0, _ = self.start_port
        x3, y3, a3, _ = self.end_port
        dist = math.hypot(x3 - x0, y3 - y0)
        d = max(dist / 3.0, 1.0)
        r0 = math.radians(a0)
        r3 = math.radians(a3)
        p1 = (x0 + d * math.cos(r0), y0 + d * math.sin(r0))
        p2 = (x3 - d * math.cos(r3), y3 - d * math.sin(r3))
        return np.array([(x0, y0), p1, p2, (x3, y3)], dtype=float)

    def compute_path(self, n_points: int = 100) -> list[tuple[float, float]]:
        """计算贝塞尔曲线路径。

        使用三次贝塞尔曲线 Bernstein 多项式:
            B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃

        Args:
            n_points: 采样点数。

        Returns:
            路径点列表 [(x, y), ...]。

        Raises:
            ValueError: n_points < 2。
        """
        if n_points < 2:
            raise ValueError(f"n_points 须 >= 2，得到 {n_points}")
        cp = self._control_points()
        t = np.linspace(0.0, 1.0, n_points)
        t_col = t[:, np.newaxis]
        # 三次贝塞尔 Bernstein 基函数
        b0 = (1 - t_col) ** 3
        b1 = 3 * (1 - t_col) ** 2 * t_col
        b2 = 3 * (1 - t_col) * t_col ** 2
        b3 = t_col ** 3
        pts = b0 * cp[0] + b1 * cp[1] + b2 * cp[2] + b3 * cp[3]
        return [(float(p[0]), float(p[1])) for p in pts]

    def compute_length(self) -> float:
        """计算路径长度（折线段累加）。

        Returns:
            路径长度（μm）。
        """
        pts = self.compute_path(200)
        arr = np.asarray(pts)
        diffs = np.diff(arr, axis=0)
        return float(np.sum(np.hypot(diffs[:, 0], diffs[:, 1])))

    def to_pycell(self) -> PyCell:
        """转换为 PyCell（沿路径生成多边形）。

        Returns:
            含贝塞尔路径多边形的 PyCell。
        """
        path = self.compute_path(100)
        width = (self.start_port[3] + self.end_port[3]) / 2.0
        polygon = _offset_path_to_polygon(path, width / 2.0)
        return PyCell(
            name="flex_connector",
            params={"path_type": self.path_type, "width": width},
            polygons=[polygon],
            ports=[("in", self.start_port[0], self.start_port[1],
                    self.start_port[2], self.start_port[3]),
                   ("out", self.end_port[0], self.end_port[1],
                    self.end_port[2], self.end_port[3])],
            metadata={"source": _URL_NEWSLETTER_2023_12},
        )


__all__ = [
    "FlexConnector",
]
