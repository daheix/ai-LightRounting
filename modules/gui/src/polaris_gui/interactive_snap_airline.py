"""GUI 交互 - 吸附引擎与飞线路由模块（polaris-gui 子模块）。

从 ``interactive.py`` 拆分而来:
- SnapEngine 多模态吸附（网格/顶点/中点/端点），对标 L-Edit "Snap to Objects"
  与 KLayout snap-to-grid/vertex
- AirlineRouter 为未连接端口生成直线飞线，对标 KLayout "show airlines"

无 GUI 框架依赖。

文献来源（R02 学术诚信）:
1. KLayout Rubber-band / airline
   https://www.klayout.de/doc-qt5/manual/rubberband.html
2. KLayout snap-to-grid https://www.klayout.org/doc-qt5/manual/snapping.html
3. Siemens L-Edit Photonics
   https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
4. Gamma et al., "Design Patterns", Addison-Wesley 1994
5. Farin, G., "Curves and Surfaces for CAGD", MK 2002

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .interactive_objects import LayoutObject, ObjectType, _DEFAULT_SNAP_THRESHOLD


@dataclass
class SnapResult:
    """吸附结果。"""

    point: tuple[float, float]
    mode: str  # "grid" / "vertex" / "midpoint" / "endpoint" / "none"


class SnapEngine:
    """多模态吸附引擎（对标 L-Edit "Snap to Objects" 与 KLayout snap）。

    模式：``grid``/``vertex``/``midpoint``/``endpoint``。
    优先级：vertex > midpoint > endpoint > grid。
    """

    def __init__(
        self, grid_size: float = 0.1,
        threshold: float = _DEFAULT_SNAP_THRESHOLD,
        modes: list[str] | None = None,
    ) -> None:
        if grid_size <= 0.0:
            raise ValueError(f"grid_size 必须 >0，收到 {grid_size}")
        if threshold < 0.0:
            raise ValueError(f"threshold 必须 ≥0，收到 {threshold}")
        self.grid_size = float(grid_size)
        self.threshold = float(threshold)
        self.modes = modes if modes is not None else [
            "vertex", "midpoint", "endpoint", "grid"]

    def snap(
        self, point: tuple[float, float],
        objects: list[LayoutObject] | None = None,
    ) -> SnapResult:
        """对点吸附。按 modes 顺序遍历非 grid 模式，距离 ≤ threshold
        的候选立即返回（vertex > midpoint > endpoint）；grid 作为 fallback。"""
        px, py = float(point[0]), float(point[1])
        threshold_d2 = self.threshold * self.threshold
        for mode in self.modes:
            if mode == "grid":
                continue
            cand = self._snap_mode(mode, px, py, objects or [])
            if cand is None:
                continue
            d2 = (cand[0] - px) ** 2 + (cand[1] - py) ** 2
            if d2 <= threshold_d2:
                return SnapResult(point=cand, mode=mode)
        if "grid" in self.modes:
            gx = round(px / self.grid_size) * self.grid_size
            gy = round(py / self.grid_size) * self.grid_size
            return SnapResult(point=(gx, gy), mode="grid")
        return SnapResult(point=(px, py), mode="none")

    def _snap_mode(
        self, mode: str, px: float, py: float,
        objects: list[LayoutObject],
    ) -> tuple[float, float] | None:
        if mode == "grid":
            return (round(px / self.grid_size) * self.grid_size,
                    round(py / self.grid_size) * self.grid_size)
        if mode == "vertex":
            return self._nearest_in_set(px, py, self._vertex_iter(objects))
        if mode == "midpoint":
            return self._nearest_in_set(px, py, self._midpoint_iter(objects))
        if mode == "endpoint":
            return self._nearest_in_set(px, py, self._endpoint_iter(objects))
        raise ValueError(f"未知吸附模式: {mode!r}")

    @staticmethod
    def _vertex_iter(objects: list[LayoutObject]):
        for obj in objects:
            yield from obj.points

    @staticmethod
    def _midpoint_iter(objects: list[LayoutObject]):
        for obj in objects:
            pts = obj.points
            for i in range(len(pts) - 1):
                yield ((pts[i][0] + pts[i + 1][0]) / 2.0,
                       (pts[i][1] + pts[i + 1][1]) / 2.0)

    @staticmethod
    def _endpoint_iter(objects: list[LayoutObject]):
        for obj in objects:
            pts = obj.points
            if pts:
                yield pts[0]
                yield pts[-1]

    def _nearest_in_set(
        self, px: float, py: float, candidates
    ) -> tuple[float, float] | None:
        best: tuple[float, float] | None = None
        best_d2 = self.threshold * self.threshold
        for v in candidates:
            d2 = (v[0] - px) ** 2 + (v[1] - py) ** 2
            if d2 <= best_d2:
                best_d2 = d2
                best = (float(v[0]), float(v[1]))
        return best


# === 4. AirlineRouter 飞线路由器 ===

@dataclass
class AirlineSegment:
    """飞线段（直线连接两端口的虚拟 net 段）。"""

    start: tuple[float, float]
    end: tuple[float, float]
    net_id: str


class AirlineRouter:
    """飞线（airline）路由器。

    为未连接端口对生成直线段（rubber-band），可视化 net 连接关系。
    对标 KLayout "show airlines" 与 L-Edit "flight lines"。
    来源：https://www.klayout.de/doc-qt5/manual/rubberband.html

    *创新*：基于端口 net_id 自动配对（同 net_id 端口顺序直线连接），
    无需手工指定 airline 列表。底层逻辑：扫描 PORT 对象，按 net_id 分组，
    组内按端口 ID 排序后顺序配对（P0-P1, P1-P2, ...）形成飞线链，
    与 KLayout net-to-rubberband 视觉一致。
    """

    def route(
        self, ports: list[LayoutObject],
        netlist: dict[str, list[int]] | None = None,
    ) -> list[AirlineSegment]:
        """为端口列表生成飞线段（同 net 的端口顺序配对）。"""
        for p in ports:
            if p.obj_type != ObjectType.PORT.value:
                raise ValueError(f"非 PORT 对象不能参与飞线: {p.obj_type!r}")
            if not p.points:
                raise ValueError(f"PORT {p.obj_id} 缺少位置点")
        if netlist is None:
            netlist = self._infer_netlist(ports)
        segments: list[AirlineSegment] = []
        pos_by_id = {p.obj_id: p.points[0] for p in ports}
        for net_id, port_ids in netlist.items():
            if len(port_ids) < 2:
                continue
            ordered = sorted(port_ids)
            for i in range(len(ordered) - 1):
                a, b = ordered[i], ordered[i + 1]
                if a not in pos_by_id or b not in pos_by_id:
                    raise KeyError(
                        f"net {net_id!r} 引用了不存在的端口 ID: {a}/{b}")
                segments.append(AirlineSegment(
                    start=pos_by_id[a], end=pos_by_id[b], net_id=net_id))
        return segments

    def _infer_netlist(
        self, ports: list[LayoutObject]
    ) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for p in ports:
            net = p.attrs.get("net_id")
            if not isinstance(net, str) or not net:
                raise ValueError(
                    f"PORT {p.obj_id} 缺少 net_id 属性，无法推断 netlist")
            out.setdefault(net, []).append(p.obj_id)
        return out


# === 5. MacroIDE 宏 IDE（断点/单步/控制台/监视） ===


__all__ = ["SnapResult", "SnapEngine", "AirlineSegment", "AirlineRouter"]
