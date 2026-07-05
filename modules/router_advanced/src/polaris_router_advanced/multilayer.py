"""3D 多层布线支持（2025 增强）。

支持多层光子芯片的布线，通过层间耦合器（光学通孔 OTV）实现
垂直层间连接，提升集成密度。

方法参考（方案检索，见项目规则 1.1）:
- Xu et al., Laser & Photonics Reviews 2024: 多层可重构 3D PIC
  来源: https://onlinelibrary.wiley.com/doi/10.1002/lpor.202400827
- Sarad JSTQE 2025: CMOS 兼容低损耗光学通孔（OTV）
  来源: https://www.techrxiv.org/users/961414/articles/1330406
- LiDAR 2.0 分层曲线波导布线
  来源: https://arxiv.org/html/2505.17239v2
- DREAMPlace (层间布线参考), https://arxiv.org/abs/2004.10746
- SiEPIC EBeam PDK (多层波导规则),
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

架构: 每层独立 A* 布线 + 层间 OTV 连接
- Layer 0: SOI 器件层（有源/无源）
- Layer 1: SiN 无源层（低损传输）
- Layer 2: LNOI 调制层（高速调制）

R4-P1 修复（2026-06-29）:
- _route_single_layer / _route_multi_layer / route: 删除 `return None`
  静默 fall-back（R03 违规），改为 raise RuntimeError 显式告警。
- total_loss_db: 删除硬编码 2.0 dB/cm 魔数，改为按 layer.platform
  查询 _PLATFORM_LOSS_DB_CM（与 waveguide_router.py 一致）。
  来源: SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from .waveguide_router import GridRouter, RouterConstraints, _PLATFORM_LOSS_DB_CM

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
    ) -> MultiLayerRouteResult:
        """3D 多层布线（支持层间 OTV 连接）。

        R4-P1: 删除 `-> MultiLayerRouteResult | None` 中的 None 静默 fall-back，
        布线失败时 raise RuntimeError（R03 禁止 fall-back）。

        Raises:
            RuntimeError: 布线失败（路径不可达 / 无可用 OTV）。
        """
        if start_layer == end_layer:
            return self._route_single_layer(start_layer, start_pos, end_pos)
        return self._route_multi_layer(start_layer, start_pos, end_layer, end_pos)

    def _route_single_layer(
        self,
        layer_idx: int,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> MultiLayerRouteResult:
        """单层布线。

        R4-P1: 删除 `return None` 静默 fall-back，改为 raise RuntimeError。
        R4-P1: 删除硬编码 2.0 dB/cm 魔数，改为按 layer.platform 查询
        _PLATFORM_LOSS_DB_CM（与 waveguide_router.py 一致）。

        Raises:
            RuntimeError: A* 路径不可达。
            KeyError: layer.platform 不在 _PLATFORM_LOSS_DB_CM 中。
        """
        router = self.routers[layer_idx]
        gs = self.layers[layer_idx].grid_size
        sg = (int(start[0] / gs), int(start[1] / gs))
        eg = (int(end[0] / gs), int(end[1] / gs))
        grid_path = router.route(sg, eg)
        if grid_path is None:
            # R4-P1: R03 禁止 fall-back —— 布线失败必须 raise
            raise RuntimeError(
                f"层 {self.layers[layer_idx].name} (idx={layer_idx}) 布线失败: "
                f"start={start} -> end={end}。"
                f"R03 禁止 fall-back: 禁止返回 None 让调用方误判成功。"
            )
        pts = [(g[0] * gs, g[1] * gs) for g in grid_path]
        length = sum(
            np.sqrt((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2)
            for i in range(len(pts) - 1)
        )
        # R4-P1: 按 layer.platform 查询传播损耗，禁止硬编码 2.0 dB/cm
        platform = self.layers[layer_idx].platform
        if platform not in _PLATFORM_LOSS_DB_CM:
            raise KeyError(
                f"层 {self.layers[layer_idx].name} (idx={layer_idx}) 平台 '{platform}' "
                f"未定义传播损耗系数 (dB/cm)。已知平台: {sorted(_PLATFORM_LOSS_DB_CM.keys())}。"
                f"R03 禁止 fall-back: 禁止返回魔数 2.0 dB/cm。"
            )
        loss_db_cm = _PLATFORM_LOSS_DB_CM[platform]
        return MultiLayerRouteResult(
            layer_paths={layer_idx: pts},
            total_length_um=length,
            total_loss_db=length * loss_db_cm / 1e4,  # μm → cm
        )

    def _route_multi_layer(
        self,
        start_layer: int,
        start: tuple[float, float],
        end_layer: int,
        end: tuple[float, float],
    ) -> MultiLayerRouteResult:
        """多层布线：找最近 OTV → 层1到OTV → OTV到层2 → OTV到终点。

        R4-P1: 删除 `return None` 静默 fall-back，改为 raise RuntimeError。
        R4-P1: _otv_grid_map.get(otv_key, []) 静默空列表 fall-back 改为显式 raise。

        Raises:
            RuntimeError: 无可用 OTV / 子层布线失败。
        """
        otv_key = (start_layer, end_layer)
        # R4-P1: R03 禁止 fall-back —— 无 OTV 必须 raise，禁止返回空列表
        if otv_key not in self._otv_grid_map:
            raise RuntimeError(
                f"层 {start_layer}→{end_layer} 无可用 OTV（键不存在）。"
                f"已注册 OTV 层对: {sorted(self._otv_grid_map.keys())}。"
                f"R03 禁止 fall-back: 禁止返回 None 让调用方误判成功。"
            )
        available_otvs = self._otv_grid_map[otv_key]
        if not available_otvs:
            raise RuntimeError(
                f"层 {start_layer}→{end_layer} OTV 列表为空。"
                f"R03 禁止 fall-back: 禁止返回 None 让调用方误判成功。"
            )
        # 选择距离起点+终点最近的 OTV
        best_otv = min(
            available_otvs,
            key=lambda o: (
                abs(o.x - start[0]) + abs(o.y - start[1]) + abs(o.x - end[0]) + abs(o.y - end[1])
            ),
        )
        # 层1: 起点 → OTV（R4-P1: _route_single_layer 已改为 raise，无需 None 检查）
        r1 = self._route_single_layer(start_layer, start, (best_otv.x, best_otv.y))
        # 层2: OTV → 终点（R4-P1: _route_single_layer 已改为 raise，无需 None 检查）
        r2 = self._route_single_layer(end_layer, (best_otv.x, best_otv.y), end)
        # 合并结果
        merged = MultiLayerRouteResult()
        merged.layer_paths = {**r1.layer_paths, **r2.layer_paths}
        merged.otv_used = [best_otv]
        merged.total_length_um = r1.total_length_um + r2.total_length_um
        merged.total_loss_db = r1.total_loss_db + r2.total_loss_db + best_otv.loss_db
        return merged


__all__ = ["LayerSpec", "OTVSpec", "MultiLayerRouteResult", "MultiLayerRouter"]
