"""LVS 进阶几何辅助函数（纯 NumPy/KLayout，R04 不参与 GPU）。

批次 10-B 拆分说明（2026-07-01）:
    从 lvs_advanced.py 抽出 GDS 加载、Region 获取、形状顶点提取、
    面积/包围盒/包围盒相交判定等公共几何辅助函数，供各 R181-R187
    子模块共享调用。

来源（R02 学术诚信）:
- KLayout Database API: https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- KLayout Region: https://www.klayout.org/downloads/master/doc-qt5/about/rba_region.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Shoelace 面积公式: https://en.wikipedia.org/wiki/Shoelace_formula
- NumPy 文档: https://numpy.org/doc/stable/
"""

from __future__ import annotations

from pathlib import Path

import klayout.db as db
import numpy as np

from polaris.pdk.layer_map import get_layer_tuple
from polaris.sim.lvs import _find_layer_index


def _load_layout(gds_path: str | Path) -> tuple[db.Layout, db.Cell, float]:
    """加载 GDS 文件，返回 (layout, top_cell, dbu)。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        (layout, top_cell, dbu_um)。

    Raises:
        FileNotFoundError: GDS 文件不存在。
        RuntimeError: GDS 加载失败或无 top cell。
    """
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDS 文件不存在: {path}")
    layout = db.Layout()
    layout.read(str(path))
    cell = layout.top_cell()
    if cell is None:
        raise RuntimeError(f"GDS 无 top cell: {path}")
    return layout, cell, layout.dbu


def _get_region(layout: db.Layout, cell: db.Cell, layer_name: str) -> db.Region:
    """获取指定层的 Region。

    Args:
        layout: KLayout Layout。
        cell: Top cell。
        layer_name: 层名（如 ``"WG"`` / ``"DEVREC"``）。

    Returns:
        该层的 Region。

    Raises:
        RuntimeError: 层不存在。
    """
    layer_info = get_layer_tuple(layer_name)
    idx = _find_layer_index(layout, layer_info[0], layer_info[1])
    if idx is None:
        raise RuntimeError(
            f"层 {layer_name} (layer {layer_info[0]}, datatype {layer_info[1]}) 不存在于 GDS"
        )
    return db.Region(layout.begin_shapes(cell, idx))


def _shape_vertices_um(shape, dbu: float) -> np.ndarray:
    """提取形状顶点（μm）。

    KLayout ``region.each()`` 返回 ``PolygonWithProperties``（直接含 ``each_edge``）
    或 ``db.Shape``（对多边形也含 ``each_edge``）。优先取多边形顶点；
    若形状无顶点（如纯文本/点），退化到包围盒四角（数学正确行为，非 fall-back）。

    Args:
        shape: KLayout Shape 或 PolygonWithProperties。
        dbu: 数据库单位（μm）。

    Returns:
        (N, 2) 顶点数组（μm）。
    """
    pts: list[list[float]] = []
    if hasattr(shape, "each_edge"):
        for edge in shape.each_edge():
            pts.append([edge.p1.x * dbu, edge.p1.y * dbu])
    if len(pts) >= 3:
        return np.array(pts, dtype=float)
    box = shape.bbox()
    return np.array(
        [
            [box.left * dbu, box.bottom * dbu],
            [box.right * dbu, box.bottom * dbu],
            [box.right * dbu, box.top * dbu],
            [box.left * dbu, box.top * dbu],
        ],
        dtype=float,
    )


def _polygon_area_um2(pts: np.ndarray) -> float:
    """计算多边形面积（shoelace 公式，μm²）。

    Args:
        pts: (N, 2) 顶点数组。

    Returns:
        面积（μm²），退化多边形返回 0.0（数学正确行为）。
    """
    if len(pts) < 3:
        return 0.0
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _bbox_um(shape: db.Shape, dbu: float) -> tuple[float, float, float, float]:
    """取形状包围盒（μm）。"""
    box = shape.bbox()
    return (box.left * dbu, box.bottom * dbu, box.right * dbu, box.top * dbu)


def _bbox_aspect(bbox: tuple[float, float, float, float]) -> float:
    """包围盒长宽比（≥1，长边/短边）。"""
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if w <= 0 or h <= 0:
        return 1.0
    return max(w, h) / min(w, h)


def _bboxes_overlap(
    b1: tuple[float, float, float, float],
    b2: tuple[float, float, float, float],
) -> bool:
    """判断两包围盒是否相交（严格相交，非仅邻接）。"""
    return (
        b1[0] < b2[2]
        and b1[2] > b2[0]
        and b1[1] < b2[3]
        and b1[3] > b2[1]
    )


__all__ = [
    "_load_layout",
    "_get_region",
    "_shape_vertices_um",
    "_polygon_area_um2",
    "_bbox_um",
    "_bbox_aspect",
    "_bboxes_overlap",
]
