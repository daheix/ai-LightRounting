"""3D 多层布线支持（2025 增强）。

支持多层光子芯片的布线，通过层间耦合器（光学通孔 OTV）实现
垂直层间连接，提升集成密度。

方法参考（方案检索，见项目规则 1.1）：
- Xu et al., Laser & Photonics Reviews 2024: 多层可重构 3D PIC
  来源: https://onlinelibrary.wiley.com/doi/10.1002/lpor.202400827
- Sarad JSTQE 2025: CMOS 兼容低损耗光学通孔（OTV）
  来源: https://www.techrxiv.org/users/961414/articles/1330406
- LiDAR 2.0 分层曲线波导布线
  来源: https://arxiv.org/html/2505.17239v2

架构: 每层独立 A* 布线 + 层间 OTV 连接
- Layer 0: SOI 器件层（有源/无源）
- Layer 1: SiN 无源层（低损传输）
- Layer 2: LNOI 调制层（高速调制）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from polaris.router.waveguide_router import GridRouter, RouterConstraints

logger = logging.getLogger(__name__)


@dataclass
class LayerSpec:
    """单层布线规格。

    Attributes:
        name: 层名称。
        grid_w: 网格宽度。
        grid_h: 网格高度。
        grid_size: 网格尺寸（μm）。
        platform: 工艺平台（SOI/SiN/LNOI）。
    """

    name: str
    grid_w: int
    grid_h: int
    grid_size: float = 1.0
    platform: str = "SOI"


@dataclass
class OTVSpec:
    """光学通孔（OTV）规格。

    层间垂直耦合器，实现 3D PIC 的垂直连接。

    来源:
    - Sarad JSTQE 2025: CMOS 兼容低损耗 OTV
      https://www.techrxiv.org/users/961414/articles/1330406

    Attributes:
        name: OTV 名称。
        layer_from: 起始层索引。
        layer_to: 目标层索引。
        x: OTV 位置 x（μm）。
        y: OTV 位置 y（μm）。
        loss_db: 耦合损耗（dB）。
    """

    name: str
    layer_from: int
    layer_to: int
    x: float
    y: float
    loss_db: float = 0.5


@dataclass
class MultiLayerRouteResult:
    """3D 多层布线结果。

    Attributes:
        layer_paths: 每层路径 {layer_idx: [(x, y), ...]}。
        otv_used: 使用的 OTV 列表。
        total_length_um: 总路径长度（μm）。
        total_loss_db: 总损耗（dB）。
    """

    layer_paths: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    otv_used: list[OTVSpec] = field(default_factory=list)
    total_length_um: float = 0.0
    total_loss_db: float = 0.0


class MultiLayerRouter:
    """3D 多层布线器（每层独立 A* + OTV 层间连接）。

    来源:
    - Xu et al., LPR 2024: 多层 3D PIC
      https://onlinelibrary.wiley.com/doi/10.1002/lpor.202400827
    - Sarad JSTQE 2025: OTV 垂直耦合
      https://www.techrxiv.org/users/961414/articles/1330406
    """

    def __init__(
        self,
        layers: list[LayerSpec],
        otvs: list[OTVSpec] | None = None,
        constraints: RouterConstraints | None = None,
    ) -> None:
        self.layers = layers
        self.otvs = otvs or []
        self.constraints = constraints or RouterConstraints()
        self.routers: dict[int, GridRouter] = {}
        for i, layer in enumerate(layers):
            self.routers[i] = GridRouter(
                layer.grid_w, layer.grid_h, layer.grid_size, self.constraints
            )
        self._otv_grid_map = self._build_otv_map()

    def _build_otv_map(self) -> dict[tuple[int, int], list[OTVSpec]]:
        """构建层对 → OTV 映射。"""
        otv_map: dict[tuple[int, int], list[OTVSpec]] = {}
        for otv in self.otvs:
            key = (otv.layer_from, otv.layer_to)
            otv_map.setdefault(key, []).append(otv)
            key_rev = (otv.layer_to, otv.layer_from)
            otv_map.setdefault(key_rev, []).append(otv)
        return otv_map

    def add_obstacle(self, layer_idx: int, rect: tuple[int, int, int, int]) -> None:
        """在指定层添加矩形障碍物。

        Args:
            layer_idx: 层索引。
            rect: (x, y, w, h) 矩形参数。
        """
        if layer_idx in self.routers:
            self.routers[layer_idx].add_obstacle(rect[0], rect[1], rect[2], rect[3])

    def route(
        self,
        start_layer: int,
        start_pos: tuple[float, float],
        end_layer: int,
        end_pos: tuple[float, float],
    ) -> MultiLayerRouteResult | None:
        """3D 多层布线（支持层间 OTV 连接）。"""
        if start_layer == end_layer:
            return self._route_single_layer(start_layer, start_pos, end_pos)
        return self._route_multi_layer(start_layer, start_pos, end_layer, end_pos)

    def _route_single_layer(
        self,
        layer_idx: int,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> MultiLayerRouteResult | None:
        """单层布线。"""
        router = self.routers[layer_idx]
        gs = self.layers[layer_idx].grid_size
        sg = (int(start[0] / gs), int(start[1] / gs))
        eg = (int(end[0] / gs), int(end[1] / gs))
        grid_path = router.route(sg, eg)
        if grid_path is None:
            logger.error("层 %s 布线失败: %s -> %s", self.layers[layer_idx].name, start, end)
            return None
        pts = [(g[0] * gs, g[1] * gs) for g in grid_path]
        length = sum(
            np.sqrt((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2)
            for i in range(len(pts) - 1)
        )
        return MultiLayerRouteResult(
            layer_paths={layer_idx: pts},
            total_length_um=length,
            total_loss_db=length * 2.0 / 1e4,
        )

    def _route_multi_layer(
        self,
        start_layer: int,
        start: tuple[float, float],
        end_layer: int,
        end: tuple[float, float],
    ) -> MultiLayerRouteResult | None:
        """多层布线：找最近 OTV → 层1到OTV → OTV到层2 → OTV到终点。"""
        otv_key = (start_layer, end_layer)
        available_otvs = self._otv_grid_map.get(otv_key, [])
        if not available_otvs:
            logger.error("层 %d→%d 无可用 OTV", start_layer, end_layer)
            return None
        # 选择距离起点+终点最近的 OTV
        best_otv = min(
            available_otvs,
            key=lambda o: (
                abs(o.x - start[0]) + abs(o.y - start[1]) + abs(o.x - end[0]) + abs(o.y - end[1])
            ),
        )
        # 层1: 起点 → OTV
        r1 = self._route_single_layer(start_layer, start, (best_otv.x, best_otv.y))
        if r1 is None:
            return None
        # 层2: OTV → 终点
        r2 = self._route_single_layer(end_layer, (best_otv.x, best_otv.y), end)
        if r2 is None:
            return None
        # 合并结果
        merged = MultiLayerRouteResult()
        merged.layer_paths = {**r1.layer_paths, **r2.layer_paths}
        merged.otv_used = [best_otv]
        merged.total_length_um = r1.total_length_um + r2.total_length_um
        merged.total_loss_db = r1.total_loss_db + r2.total_loss_db + best_otv.loss_db
        return merged


__all__ = ["LayerSpec", "OTVSpec", "MultiLayerRouteResult", "MultiLayerRouter"]
