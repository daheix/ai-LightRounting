"""P0-3 GUI 版图编辑器交互功能（interactive.py）。

实现 L-Edit / KLayout / OptoDesigner 风格交互式版图编辑器：
- 曲线多边形（贝塞尔 / Catmull-Rom 样条 / 圆弧 / 椭圆 / 顶点编辑）
- 对象交互（snap-to-grid 抓取移动 / 拖放 / 飞线 airline / 查看器只读模式）
- 宏 IDE（断点 / 单步 / Python 交互控制台 / 监视表达式）

实现策略：**数据模型层 + 命令模式**，无 GUI 框架依赖（PyQt/Tkinter），
便于 CI/CD 与 Web 后端复用。

文献来源（R02 学术诚信，≥5 条）：
1. KLayout Scripting Manual https://www.klayout.org/doc-qt5/manual/scripting.html
2. Siemens L-Edit Photonics
   https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
3. Farin, G., "Curves and Surfaces for CAGD", 5th ed., Morgan Kaufmann 2002
   https://www.sciencedirect.com/book/9781558607378/curves-and-surfaces-for-cagd
4. De Casteljau 算法 https://en.wikipedia.org/wiki/De_Casteljau%27s_algorithm
5. Catmull & Rom 1974 https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
6. Gamma et al., "Design Patterns", Addison-Wesley 1994（Command Pattern）
   https://en.wikipedia.org/wiki/Command_pattern
7. Python bdb — Debugger framework https://docs.python.org/3/library/bdb.html
8. KLayout Rubber-band / airline https://www.klayout.de/doc-qt5/manual/rubberband.html

*创新*：纯 Python 数据模型 + 命令模式 GUI 引擎。底层逻辑：
``LayoutObject`` 统一抽象（点/折线/多边形/贝塞尔/样条/圆弧/椭圆/端口），
编辑操作封装为 ``EditCommand`` 入栈，``CommandStack`` 实现 undo/redo
（Gamma 1994 命令模式）。``SnapEngine`` 多模态吸附（网格/顶点/中点/端点），
对标 L-Edit "Snap to Objects" 与 KLayout snap-to-grid/vertex。
``AirlineRouter`` 为未连接端口生成直线飞线，对标 KLayout "show airlines"。
``MacroIDE`` 基于 ``sys.settrace``（bdb 底层机制）+
``code.InteractiveConsole``，提供 KLayout Macro IDE 等价的脚本调试/
控制台/监视能力，零 GUI 依赖。
支持理论：MVC 分离（Gamma 1994）+ Python bdb 跟踪框架（PSF 文档）。
"""

from __future__ import annotations

import copy
import math
import sys
from code import InteractiveConsole
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# 默认曲线采样段数（μm 量级版图足够分辨率，对标 KLayout 默认 64 段）
_DEFAULT_SAMPLES = 64
# 默认吸附阈值（μm），L-Edit 默认 0.5μm 拾取半径
_DEFAULT_SNAP_THRESHOLD = 0.5


class ObjectType(str, Enum):
    """场景对象类型（对齐 KLayout Shapes + L-Edit Drawing Tools）。"""

    POINT = "point"
    POLYLINE = "polyline"
    POLYGON = "polygon"
    BEZIER = "bezier"      # 三次贝塞尔曲线（控制点存于 points）
    SPLINE = "spline"      # Catmull-Rom 样条（穿过所有控制点）
    ARC = "arc"            # 圆弧（attrs: center/radius/start_angle/end_angle）
    ELLIPSE = "ellipse"    # 椭圆（attrs: center/a/b/start_angle/end_angle）
    PORT = "port"          # 器件端口（飞线连接点，attrs: net_id/direction）


@dataclass
class LayoutObject:
    """场景对象（统一数据模型，所有形状/端口共享）。

    Attributes:
        obj_id: 唯一对象 ID（>0）。
        obj_type: 对象类型（见 :class:`ObjectType`）。
        points: 控制点/顶点序列 ``[(x, y), ...]``（μm）。贝塞尔/样条 ≥2
            控制点；多边形/折线为顶点序列；圆弧/椭圆可空（用 attrs）。
        attrs: 类型相关属性（圆弧 center/radius/角度等）。
        layer: 图层名（SiEPIC 标准 layer/datatype 字符串）。
    """

    obj_id: int
    obj_type: str
    points: list[tuple[float, float]] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)
    layer: str = "WG"

    def __post_init__(self) -> None:
        if self.obj_id <= 0:
            raise ValueError(f"obj_id 必须为正整数，收到 {self.obj_id}")
        if self.obj_type not in ObjectType._value2member_map_:
            raise ValueError(f"未知对象类型: {self.obj_type!r}")


# === 1. 曲线几何求值 ===

def _de_casteljau(
    control_points: list[tuple[float, float]], t: float
) -> tuple[float, float]:
    """De Casteljau 算法求贝塞尔曲线点（数值稳定）。

    来源：Farin 2002 §2.1；De Casteljau 算法。
    """
    if len(control_points) < 2:
        raise ValueError(f"贝塞尔控制点至少 2 个，收到 {len(control_points)}")
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"参数 t 必须在 [0,1]，收到 {t}")
    pts = [(float(p[0]), float(p[1])) for p in control_points]
    for _ in range(1, len(pts)):
        pts = [
            ((1.0 - t) * pts[i][0] + t * pts[i + 1][0],
             (1.0 - t) * pts[i][1] + t * pts[i + 1][1])
            for i in range(len(pts) - 1)
        ]
    return pts[0]


def _catmull_rom_segment(
    p0: tuple[float, float], p1: tuple[float, float],
    p2: tuple[float, float], p3: tuple[float, float], t: float,
) -> tuple[float, float]:
    """Catmull-Rom 样条段求值（uniform 参数化）。

    来源：Catmull & Rom 1974。
    """
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"参数 t 必须在 [0,1]，收到 {t}")
    t2, t3 = t * t, t * t * t
    x = 0.5 * (2.0 * p1[0] + (-p0[0] + p2[0]) * t
               + (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * t2
               + (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * t3)
    y = 0.5 * (2.0 * p1[1] + (-p0[1] + p2[1]) * t
               + (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * t2
               + (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * t3)
    return (x, y)


def _catmull_rom_polyline(
    points: list[tuple[float, float]], n_samples: int
) -> list[tuple[float, float]]:
    """对整条 Catmull-Rom 样条采样（端点镜像重复）。"""
    if len(points) < 2:
        raise ValueError(f"样条穿过点至少 2 个，收到 {len(points)}")
    if n_samples < 1:
        raise ValueError(f"每段采样数必须 ≥1，收到 {n_samples}")
    extended = [points[0]] + list(points) + [points[-1]]
    out: list[tuple[float, float]] = []
    for i in range(len(extended) - 3):
        p0, p1, p2, p3 = extended[i], extended[i + 1], extended[i + 2], extended[i + 3]
        for k in range(n_samples):
            out.append(_catmull_rom_segment(p0, p1, p2, p3, k / n_samples))
    out.append(points[-1])
    return out


def _parametric_polyline(
    center: tuple[float, float], a: float, b: float,
    start_angle: float, end_angle: float, n_samples: int,
) -> list[tuple[float, float]]:
    """参数曲线采样（圆弧 a=b=r；椭圆 a≠b）。``x=cx+a·cosθ, y=cy+b·sinθ``。"""
    if a <= 0.0 or b <= 0.0:
        raise ValueError(f"半轴必须 >0，收到 a={a} b={b}")
    if n_samples < 1:
        raise ValueError(f"采样数必须 ≥1，收到 {n_samples}")
    cx, cy = float(center[0]), float(center[1])
    a1 = math.radians(float(start_angle))
    a2 = math.radians(float(end_angle))
    return [
        (cx + a * math.cos(a1 + (a2 - a1) * k / n_samples),
         cy + b * math.sin(a1 + (a2 - a1) * k / n_samples))
        for k in range(n_samples + 1)
    ]


def evaluate_object(
    obj: LayoutObject, n_samples: int = _DEFAULT_SAMPLES
) -> list[tuple[float, float]]:
    """求值场景对象为采样点序列（渲染/碰撞检测用）。"""
    if n_samples < 1:
        raise ValueError(f"采样数必须 ≥1，收到 {n_samples}")
    t = obj.obj_type
    if t == ObjectType.POINT.value:
        if not obj.points:
            raise ValueError("POINT 对象缺少 points")
        return [obj.points[0]]
    if t in (ObjectType.POLYLINE.value, ObjectType.POLYGON.value):
        if len(obj.points) < 2:
            raise ValueError(f"{t} 至少 2 个顶点，收到 {len(obj.points)}")
        pts = list(obj.points)
        if t == ObjectType.POLYGON.value:
            pts.append(pts[0])  # 闭合
        return pts
    if t == ObjectType.BEZIER.value:
        if len(obj.points) < 2:
            raise ValueError(f"BEZIER 至少 2 个控制点，收到 {len(obj.points)}")
        return [_de_casteljau(obj.points, k / n_samples)
                for k in range(n_samples + 1)]
    if t == ObjectType.SPLINE.value:
        return _catmull_rom_polyline(obj.points, n_samples)
    if t == ObjectType.ARC.value:
        r = float(obj.attrs["radius"])
        return _parametric_polyline(
            obj.attrs["center"], r, r,
            float(obj.attrs.get("start_angle", 0.0)),
            float(obj.attrs.get("end_angle", 360.0)), n_samples)
    if t == ObjectType.ELLIPSE.value:
        return _parametric_polyline(
            obj.attrs["center"], float(obj.attrs["a"]), float(obj.attrs["b"]),
            float(obj.attrs.get("start_angle", 0.0)),
            float(obj.attrs.get("end_angle", 360.0)), n_samples)
    if t == ObjectType.PORT.value:
        if not obj.points:
            raise ValueError("PORT 对象缺少 position")
        return [obj.points[0]]
    raise ValueError(f"不支持求值的对象类型: {t!r}")


# === 2. 命令模式（Gamma et al. 1994） ===

def _require_object(scene: dict[int, LayoutObject], obj_id: int) -> LayoutObject:
    """按 ID 取对象，不存在则 raise（R03 禁止 fall-back）。"""
    if obj_id not in scene:
        raise KeyError(f"对象 ID {obj_id} 不存在")
    return scene[obj_id]


@dataclass
class AddObjectCommand:
    """添加对象命令。

    使用深拷贝保存对象快照，避免外部修改导致撤销/重做副作用。
    来源: Gamma et al., "Design Patterns", Addison-Wesley 1994 (Command Pattern)
    URL: https://en.wikipedia.org/wiki/Command_pattern
    """

    obj: LayoutObject

    def do(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 已存在")
        scene[self.obj.obj_id] = copy.deepcopy(self.obj)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id not in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 不存在，无法撤销")
        del scene[self.obj.obj_id]


@dataclass
class RemoveObjectCommand:
    """删除对象命令（do 时深拷贝快照当前对象以备撤销）。

    使用深拷贝保存对象快照，避免外部修改导致撤销/重做副作用。
    来源: Gamma et al., "Design Patterns", Addison-Wesley 1994 (Command Pattern)
    URL: https://en.wikipedia.org/wiki/Command_pattern
    深度拷贝参考: https://docs.python.org/3/library/copy.html
    """

    obj: LayoutObject

    def do(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id not in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 不存在")
        self.obj = copy.deepcopy(scene[self.obj.obj_id])
        del scene[self.obj.obj_id]

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 已存在，无法撤销")
        scene[self.obj.obj_id] = copy.deepcopy(self.obj)


@dataclass
class MoveObjectCommand:
    """平移对象命令（整体偏移 dx,dy；含 center 属性同步）。"""

    obj_id: int
    dx: float
    dy: float

    def _apply(self, scene: dict[int, LayoutObject], sign: float) -> None:
        obj = _require_object(scene, self.obj_id)
        sdx, sdy = sign * self.dx, sign * self.dy
        obj.points = [(p[0] + sdx, p[1] + sdy) for p in obj.points]
        if "center" in obj.attrs:
            cx, cy = obj.attrs["center"]
            obj.attrs["center"] = (cx + sdx, cy + sdy)

    def do(self, scene: dict[int, LayoutObject]) -> None:
        self._apply(scene, 1.0)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        self._apply(scene, -1.0)


@dataclass
class InsertVertexCommand:
    """在折线/多边形的指定索引处插入顶点。"""

    obj_id: int
    index: int
    vertex: tuple[float, float]

    def do(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if obj.obj_type not in (ObjectType.POLYLINE.value,
                                ObjectType.POLYGON.value):
            raise ValueError(f"仅折线/多边形支持顶点编辑，收到 {obj.obj_type!r}")
        if not 0 <= self.index <= len(obj.points):
            raise IndexError(f"插入索引越界: {self.index} (len={len(obj.points)})")
        obj.points.insert(self.index, self.vertex)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if len(obj.points) <= self.index or obj.points[self.index] != self.vertex:
            raise RuntimeError("撤销插入顶点失败：状态不一致")
        obj.points.pop(self.index)


@dataclass
class RemoveVertexCommand:
    """删除折线/多边形指定索引顶点。"""

    obj_id: int
    index: int
    vertex: tuple[float, float]

    def do(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if obj.obj_type not in (ObjectType.POLYLINE.value,
                                ObjectType.POLYGON.value):
            raise ValueError(f"仅折线/多边形支持顶点编辑，收到 {obj.obj_type!r}")
        if not 0 <= self.index < len(obj.points):
            raise IndexError(f"删除索引越界: {self.index} (len={len(obj.points)})")
        if len(obj.points) <= 2:
            raise ValueError(f"对象至少保留 2 个顶点，当前 {len(obj.points)}")
        self.vertex = obj.points[self.index]
        obj.points.pop(self.index)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if not 0 <= self.index <= len(obj.points):
            raise IndexError(f"恢复索引越界: {self.index}")
        obj.points.insert(self.index, self.vertex)


@dataclass
class MoveVertexCommand:
    """移动折线/多边形指定顶点到新坐标。"""

    obj_id: int
    index: int
    old_vertex: tuple[float, float]
    new_vertex: tuple[float, float]

    def do(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if not 0 <= self.index < len(obj.points):
            raise IndexError(f"顶点索引越界: {self.index}")
        self.old_vertex = obj.points[self.index]
        obj.points[self.index] = self.new_vertex

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if not 0 <= self.index < len(obj.points):
            raise IndexError(f"顶点索引越界: {self.index}")
        obj.points[self.index] = self.old_vertex


class CommandStack:
    """命令栈（undo/redo，Gamma 1994 命令模式）。

    ``execute`` 执行命令并压入 undo 栈；``undo`` 弹出执行反向；
    ``redo`` 弹出重做。新命令清空 redo 栈。
    """

    def __init__(self, max_steps: int = 100) -> None:
        if max_steps <= 0:
            raise ValueError(f"max_steps 必须 >0，收到 {max_steps}")
        self._undo: list[Any] = []
        self._redo: list[Any] = []
        self._max_steps = max_steps

    def execute(self, cmd: Any, target: dict[int, LayoutObject]) -> None:
        cmd.do(target)
        self._undo.append(cmd)
        self._redo.clear()
        overflow = len(self._undo) - self._max_steps
        if overflow > 0:
            del self._undo[:overflow]

    def undo(self, target: dict[int, LayoutObject]) -> bool:
        if not self._undo:
            return False
        cmd = self._undo.pop()
        cmd.undo(target)
        self._redo.append(cmd)
        return True

    def redo(self, target: dict[int, LayoutObject]) -> bool:
        if not self._redo:
            return False
        cmd = self._redo.pop()
        cmd.do(target)
        self._undo.append(cmd)
        return True

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    @property
    def redo_depth(self) -> int:
        return len(self._redo)


# === 3. SnapEngine 吸附引擎 ===

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

class _PauseSignal(Exception):
    """调试器暂停信号（控制流信号，非业务异常）。

    在 sys.settrace 回调中抛出以中断脚本执行，实现断点/单步暂停。
    捕获方应记录已暂停状态后正常返回。
    """


class MacroDebugger:
    """宏调试器：基于 ``sys.settrace`` 行级跟踪（bdb 底层机制）。

    文献：https://docs.python.org/3/library/bdb.html
    支持：断点（含条件断点）、单步（step/next/continue）、监视表达式、执行轨迹。
    """

    def __init__(self) -> None:
        self._breakpoints: dict[tuple[str, int], str | None] = {}
        self._watches: list[str] = []
        self._watch_values: dict[str, Any] = {}
        self._executed_lines: list[tuple[str, int]] = []
        self._paused_at: tuple[str, int] | None = None
        self._step_mode: str = "continue"

    def set_breakpoint(
        self, filename: str, line: int, cond: str | None = None
    ) -> None:
        """设置断点（``cond`` 为 None 表示无条件）。"""
        if line <= 0:
            raise ValueError(f"断点行号必须 >0，收到 {line}")
        if cond is not None and (not isinstance(cond, str) or not cond.strip()):
            raise ValueError(f"断点条件必须为非空字符串或 None，收到 {cond!r}")
        self._breakpoints[(filename, line)] = cond

    def clear_breakpoint(self, filename: str, line: int) -> None:
        if (filename, line) not in self._breakpoints:
            raise KeyError(f"断点 ({filename!r}, {line}) 不存在")
        del self._breakpoints[(filename, line)]

    def add_watch(self, expr: str) -> None:
        if not isinstance(expr, str) or not expr.strip():
            raise ValueError(f"监视表达式必须为非空字符串，收到 {expr!r}")
        self._watches.append(expr)

    def clear_watches(self) -> None:
        self._watches.clear()
        self._watch_values.clear()

    @property
    def paused_at(self) -> tuple[str, int] | None:
        return self._paused_at

    @property
    def watch_values(self) -> dict[str, Any]:
        return dict(self._watch_values)

    @property
    def executed_lines(self) -> list[tuple[str, int]]:
        return list(self._executed_lines)

    @property
    def breakpoints(self) -> dict[tuple[str, int], str | None]:
        return dict(self._breakpoints)

    def run(
        self, code_obj: Any, namespace: dict,
        step_mode: str = "continue",
    ) -> bool:
        """执行代码对象，命中断点或单步时暂停。True=暂停，False=运行到结束。"""
        if step_mode not in ("step", "next", "continue"):
            raise ValueError(f"未知 step_mode: {step_mode!r}")
        self._step_mode = step_mode
        self._executed_lines = []
        self._paused_at = None
        self._watch_values = {}
        old_trace = sys.gettrace()
        sys.settrace(self._make_trace())
        paused = False
        try:
            exec(code_obj, namespace)
        except _PauseSignal:
            # 设计的暂停信号：状态已记录到 _paused_at/watch_values
            paused = True
        finally:
            sys.settrace(old_trace)
        return paused

    def _make_trace(self):
        def trace(frame, event, _arg):
            if event == "call":
                # next 模式且已开始跟踪则不进入子帧
                if self._step_mode == "next" and self._executed_lines:
                    return None
                return trace
            if event != "line":
                return trace
            fn = frame.f_code.co_filename
            ln = frame.f_lineno
            self._executed_lines.append((fn, ln))
            if self._should_pause(fn, ln, frame):
                self._paused_at = (fn, ln)
                self._eval_watches(frame)
                raise _PauseSignal()
            return trace
        return trace

    def _should_pause(self, fn: str, ln: int, frame) -> bool:
        if (fn, ln) in self._breakpoints:
            bp_cond = self._breakpoints[(fn, ln)]
            if bp_cond:
                return bool(self._eval_condition(bp_cond, frame))
            return True
        return self._step_mode in ("step", "next")

    def _eval_condition(self, cond: str, frame) -> bool:
        try:
            return bool(eval(cond, frame.f_globals, frame.f_locals))
        except Exception as e:
            raise RuntimeError(
                f"断点条件 {cond!r} 求值失败: {type(e).__name__}: {e}") from e

    def _eval_watches(self, frame) -> None:
        self._watch_values = {}
        for expr in self._watches:
            try:
                self._watch_values[expr] = eval(
                    expr, frame.f_globals, frame.f_locals)
            except Exception as e:
                self._watch_values[expr] = (
                    f"<error: {type(e).__name__}: {e}>")


class MacroIDE:
    """宏 IDE（KLayout Macro IDE 风格，纯 Python）。

    集成控制台（``code.InteractiveConsole``）、调试器（:class:`MacroDebugger`）、
    脚本加载（编译后可重复调试运行）。文献：
    https://www.klayout.org/doc-qt5/manual/scripting.html
    """

    def __init__(self, namespace: dict | None = None) -> None:
        self._namespace: dict = namespace if namespace is not None else {
            "__name__": "__macro__", "__builtins__": __builtins__}
        self._console = InteractiveConsole(self._namespace)
        self._debugger = MacroDebugger()
        self._filename: str = "<macro>"
        self._code_obj: Any = None

    @property
    def namespace(self) -> dict:
        return self._namespace

    @property
    def debugger(self) -> MacroDebugger:
        return self._debugger

    def load_script(self, filename: str, source: str) -> None:
        """加载并编译宏脚本。"""
        if not isinstance(source, str) or not source.strip():
            raise ValueError("宏脚本源码必须为非空字符串")
        self._filename = filename
        self._code_obj = compile(source, filename, "exec")

    def console_eval(self, source: str) -> Any:
        """在交互控制台中求值表达式/语句。表达式返回结果，语句返回 None。"""
        if not isinstance(source, str) or not source.strip():
            raise ValueError("控制台输入必须为非空字符串")
        try:
            return eval(source, self._namespace)
        except SyntaxError:
            # 语句而非表达式：交由 InteractiveConsole 执行
            more = self._console.push(source)
            if more:
                raise SyntaxError(f"控制台输入不完整: {source!r}")
            return None

    def set_breakpoint(self, line: int, cond: str | None = None) -> None:
        if self._code_obj is None:
            raise RuntimeError("尚未加载宏脚本，无法设置断点")
        self._debugger.set_breakpoint(self._filename, line, cond)

    def clear_breakpoint(self, line: int) -> None:
        self._debugger.clear_breakpoint(self._filename, line)

    def add_watch(self, expr: str) -> None:
        self._debugger.add_watch(expr)

    def run(self, step_mode: str = "continue") -> bool:
        """执行宏脚本（按 step_mode 暂停策略）。True 表示暂停命中。"""
        if self._code_obj is None:
            raise RuntimeError("尚未加载宏脚本，无法运行")
        return self._debugger.run(
            self._code_obj, self._namespace, step_mode=step_mode)

    @property
    def watch_values(self) -> dict[str, Any]:
        return self._debugger.watch_values

    @property
    def paused_at(self) -> tuple[str, int] | None:
        return self._debugger.paused_at

    @property
    def executed_lines(self) -> list[tuple[str, int]]:
        return self._debugger.executed_lines


# === 6. ViewerGuard 查看器只读模式守卫（对标 L-Edit Viewer Mode） ===

class ViewerGuard:
    """查看器只读模式守卫（对标 L-Edit Viewer Mode）。

    viewer_mode=True 时所有编辑操作 raise PermissionError（R03 禁止 fall-back）。
    调用方组合各组件时通过 :meth:`require_editable` 守卫编辑入口。
    """

    def __init__(self, viewer_mode: bool = False) -> None:
        self._viewer_mode = bool(viewer_mode)

    @property
    def viewer_mode(self) -> bool:
        return self._viewer_mode

    def set_viewer_mode(self, enabled: bool) -> None:
        self._viewer_mode = bool(enabled)

    def require_editable(self) -> None:
        """检查可编辑性，viewer_mode=True 时 raise PermissionError。"""
        if self._viewer_mode:
            raise PermissionError("查看器模式下禁止编辑（只读）")
