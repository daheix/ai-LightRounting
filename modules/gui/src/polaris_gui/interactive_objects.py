"""GUI 交互 - 数据模型与曲线模块（polaris-gui 子模块）。

从 ``interactive.py`` 拆分而来，包含版图对象数据模型与曲线求值:
- ObjectType 枚举（point/polyline/polygon/bezier/spline/arc/ellipse/port）
- LayoutObject dataclass（统一抽象）
- 曲线求值（De Casteljau / Catmull-Rom / 参数化折线）

无 GUI 框架依赖（PyQt/Tkinter），便于 CI/CD 与 Web 后端复用。

文献来源（R02 学术诚信）:
1. Farin, G., "Curves and Surfaces for CAGD", 5th ed., MK 2002
   https://www.sciencedirect.com/book/9781558607378/curves-and-surfaces-for-cagd
2. De Casteljau 算法 https://en.wikipedia.org/wiki/De_Casteljau%27s_algorithm
3. Catmull & Rom 1974
   https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
4. KLayout Scripting https://www.klayout.org/doc-qt5/manual/scripting.html
5. Siemens L-Edit Photonics
   https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import math
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


__all__ = [
    "_DEFAULT_SAMPLES",
    "_DEFAULT_SNAP_THRESHOLD",
    "ObjectType",
    "LayoutObject",
    "evaluate_object",
    "_require_object",
]
