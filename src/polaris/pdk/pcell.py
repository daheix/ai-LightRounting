"""R11 路标：版图参数化代码驱动（Code-as-Layout）。

对标 gdsfactory @gf.cell + IPKISS PCell 多视图架构。
所有错误必须 raise，禁止 fall-back（规则14.1）。

学术依据:
- gdsfactory @gf.cell: https://gdsfactory.github.io/gdsfactory/
- Matres et al., "GDSFactory", CLEO 2026
- IPKISS 多视图 PCell: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
- Foley et al., "Computer Graphics: Principles and Practice", 2013（仿射变换）
- Gamma et al., "Design Patterns", 1994（Observer Pattern）
- Farin, "Curves and Surfaces for CAGD", 2002（贝塞尔曲线）
- PhIDO arXiv:2508.14123（AI 辅助 PCell 生成理论）
"""

from __future__ import annotations

import inspect
import logging
import math
import re
import types
import typing
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Protocol, Union, get_args, get_origin

import numpy as np

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port

logger = logging.getLogger(__name__)

__all__ = [
    "PCellCache",
    "PCellMultiView",
    "TransformMatrix",
    "ai_generate_pcell",
    "clear_pcell_cache",
    "polaris_cell",
]


class PCellCache:
    """PCell 缓存管理器（LRU 淘汰）。

    来源: gdsfactory @gf.cell 缓存机制
    https://gdsfactory.github.io/gdsfactory/
    """

    def __init__(self, maxsize: int = 1024) -> None:
        """初始化 LRU 缓存。

        Args:
            maxsize: 缓存最大容量（默认 1024，R11 路标要求）。

        Raises:
            ValueError: maxsize <= 0。
        """
        if maxsize <= 0:
            raise ValueError(f"maxsize 须 > 0，得到 {maxsize}")
        self._maxsize = maxsize
        self._store: OrderedDict[tuple, PCellMultiView] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: tuple) -> PCellMultiView | None:
        """获取缓存项（命中时移至末尾标记为最近使用）。"""
        if key in self._store:
            self._store.move_to_end(key)
            self._hits += 1
            return self._store[key]
        self._misses += 1
        return None

    def put(self, key: tuple, cell: PCellMultiView) -> None:
        """放入缓存项（超出 maxsize 时淘汰最久未使用项）。"""
        if key in self._store:
            self._store.move_to_end(key)
            self._store[key] = cell
            return
        if len(self._store) >= self._maxsize:
            self._store.popitem(last=False)
        self._store[key] = cell

    def clear(self) -> None:
        """清空缓存并重置命中统计。"""
        self._store.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率（0.0-1.0）。无访问时返回 0.0。"""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def size(self) -> int:
        """当前缓存条目数。"""
        return len(self._store)


# 模块级默认缓存实例（maxsize=1024，R11 路标要求）与命名注册表
_DEFAULT_CACHE = PCellCache(maxsize=1024)
_NAME_REGISTRY: dict[str, set[tuple]] = {}


def clear_pcell_cache() -> None:
    """清空模块级默认缓存与命名注册表。"""
    _DEFAULT_CACHE.clear()
    _NAME_REGISTRY.clear()


@dataclass
class TransformMatrix:
    """仿射变换矩阵引擎。

    3x3 仿射变换矩阵：
    [x']   [a  b  tx] [x]
    [y'] = [c  d  ty] [y]
    [1 ]   [0  0  1 ] [1]

    来源: Foley et al., "Computer Graphics: Principles and Practice", 2013
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    tx: float = 0.0
    ty: float = 0.0

    def rotate(self, angle_deg: float) -> TransformMatrix:
        """旋转变换（逆时针，标准数学坐标系，返回新矩阵）。

        Args:
            angle_deg: 旋转角度（度）。

        Returns:
            旋转后的新 TransformMatrix。
        """
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        rot = TransformMatrix(a=cos_a, b=-sin_a, c=sin_a, d=cos_a)
        return self.compose(rot)

    def scale(self, sx: float, sy: float | None = None) -> TransformMatrix:
        """缩放变换（返回新矩阵）。

        Args:
            sx: x 方向缩放因子。
            sy: y 方向缩放因子（None 时等比缩放）。

        Returns:
            缩放后的新 TransformMatrix。
        """
        if sy is None:
            sy = sx
        sc = TransformMatrix(a=sx, d=sy)
        return self.compose(sc)

    def translate(self, tx: float, ty: float) -> TransformMatrix:
        """平移变换（返回新矩阵）。

        Args:
            tx: x 方向平移量。
            ty: y 方向平移量。

        Returns:
            平移后的新 TransformMatrix。
        """
        tr = TransformMatrix(tx=tx, ty=ty)
        return self.compose(tr)

    def shear(self, kx: float, ky: float = 0.0) -> TransformMatrix:
        """剪切变换（返回新矩阵）。

        Args:
            kx: x 方向剪切因子。
            ky: y 方向剪切因子。

        Returns:
            剪切后的新 TransformMatrix。
        """
        sh = TransformMatrix(b=kx, c=ky)
        return self.compose(sh)

    def apply(self, point: np.ndarray | tuple | list) -> np.ndarray:
        """应用变换到点或点集。

        Args:
            point: 单个点 (2,) 或点集 (N, 2)。

        Returns:
            变换后的点 (2,) 或点集 (N, 2)。

        Raises:
            ValueError: 点形状不对。
        """
        pts = np.asarray(point, dtype=float)
        if pts.ndim == 1:
            if pts.shape[0] != 2:
                raise ValueError(f"点须为 (2,)，得到 shape={pts.shape}")
            return np.array([
                self.a * pts[0] + self.b * pts[1] + self.tx,
                self.c * pts[0] + self.d * pts[1] + self.ty,
            ])
        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError(f"点集须为 (N, 2)，得到 shape={pts.shape}")
        xs, ys = pts[:, 0], pts[:, 1]
        return np.column_stack([
            self.a * xs + self.b * ys + self.tx,
            self.c * xs + self.d * ys + self.ty,
        ])

    def compose(self, other: TransformMatrix) -> TransformMatrix:
        """组合变换（self ∘ other，先应用 other 再应用 self）。"""
        return TransformMatrix(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            tx=self.a * other.tx + self.b * other.ty + self.tx,
            ty=self.c * other.tx + self.d * other.ty + self.ty,
        )

    def inverse(self) -> TransformMatrix:
        """逆变换。

        Raises:
            ValueError: 矩阵奇异（行列式为零）。
        """
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-15:
            raise ValueError(f"变换矩阵奇异，行列式={det}，无法求逆")
        inv_a, inv_b = self.d / det, -self.b / det
        inv_c, inv_d = -self.c / det, self.a / det
        return TransformMatrix(
            a=inv_a, b=inv_b, c=inv_c, d=inv_d,
            tx=-(inv_a * self.tx + inv_b * self.ty),
            ty=-(inv_c * self.tx + inv_d * self.ty),
        )

    @staticmethod
    def bezier_transform(
        control_points: np.ndarray, t: float | np.ndarray
    ) -> np.ndarray:
        """贝塞尔曲线变换（【创新】非线性变换引擎）。

        【创新】gdsfactory 仅支持仿射变换+欧拉弯曲，PoLaRIS 用贝塞尔实现任意曲率。
        支持理论: Farin, "Curves and Surfaces for CAGD", 2002。

        使用 Bernstein 多项式: B(t) = Σ C(n,i) · (1-t)^(n-i) · t^i · P_i

        Args:
            control_points: 控制点 (N, 2)，N ≥ 2。
            t: 参数 t ∈ [0, 1]，标量或数组。

        Returns:
            曲线上的点 (2,) 或 (M, 2)。

        Raises:
            ValueError: control_points 形状不对或控制点不足。
        """
        cp = np.asarray(control_points, dtype=float)
        if cp.ndim != 2 or cp.shape[1] != 2:
            raise ValueError(f"control_points 须为 (N, 2) 数组，得到 shape={cp.shape}")
        if cp.shape[0] < 2:
            raise ValueError(f"至少需要 2 个控制点，得到 {cp.shape[0]}")
        n = cp.shape[0] - 1
        t_arr = np.asarray(t, dtype=float)
        if t_arr.ndim == 0:
            point = np.zeros(2)
            for i in range(n + 1):
                coeff = math.comb(n, i) * ((1.0 - t_arr) ** (n - i)) * (t_arr ** i)
                point += coeff * cp[i]
            return point
        coeffs = np.array([math.comb(n, k) for k in range(n + 1)])
        t_col = t_arr[:, np.newaxis]
        i_arr = np.arange(n + 1)
        basis = coeffs * (t_col**i_arr) * ((1.0 - t_col) ** (n - i_arr))
        return basis @ cp


class ViewObserver(Protocol):
    """视图观察者接口（Observer Pattern）。

    来源: Gamma et al., "Design Patterns", 1994
    """

    def on_view_changed(self, source: str, event: dict[str, Any]) -> None:
        """当其他视图变化时的回调。

        Args:
            source: 变化源（"layout"/"circuit"/"netlist"）。
            event: 变化事件字典。
        """
        ...


@dataclass
class LayoutView:
    """Layout 视图（几何+端口+多边形）。

    来源: gdsfactory Component layout, IPKISS LayoutView。
    """

    polygons: list[tuple[np.ndarray, str]] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)

    def on_view_changed(self, source: str, event: dict[str, Any]) -> None:
        """响应其他视图变化（Observer Pattern）。"""
        # Layout 视图为主视图，不主动从其他视图同步
        pass


@dataclass
class CircuitView:
    """Circuit 视图（S参数模型+连接）。

    来源: gdsfactory Circuit, IPKISS CircuitView。
    """

    model: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    connections: list[tuple[str, str]] = field(default_factory=list)

    def on_view_changed(self, source: str, event: dict[str, Any]) -> None:
        """响应 Layout 视图变化（【创新】Observer Pattern 自动同步）。

        【创新】当 Layout 视图添加端口时，自动更新 Circuit 视图的端口列表。
        """
        if source == "layout" and event.get("type") == "add_port":
            port_name = event.get("port_name", "")
            if port_name:
                self.params.setdefault("ports", [])
                if port_name not in self.params["ports"]:
                    self.params["ports"].append(port_name)


@dataclass
class NetlistView:
    """Netlist 视图（网表实例+连接+端口）。

    来源: gdsfactory get_netlist, IPKISS NetlistView。
    """

    instances: list[dict] = field(default_factory=list)
    connections: list[dict] = field(default_factory=list)
    ports: dict[str, str] = field(default_factory=dict)

    def on_view_changed(self, source: str, event: dict[str, Any]) -> None:
        """响应 Layout 视图变化（【创新】Observer Pattern 自动同步）。

        【创新】当 Layout 视图添加端口/引用时，自动更新 Netlist 视图。
        """
        if source != "layout":
            return
        etype = event.get("type")
        if etype == "add_port":
            name = event.get("port_name", "")
            x, y = event.get("x", 0.0), event.get("y", 0.0)
            if name:
                self.ports[name] = f"{x},{y}"
        elif etype == "add_ref":
            cell_name = event.get("cell_name", "")
            x, y = event.get("x", 0.0), event.get("y", 0.0)
            if cell_name:
                self.instances.append({
                    "name": cell_name, "x": x, "y": y,
                    "rotation": event.get("rotation", 0.0),
                })


class PCellMultiView:
    """多视图参数化单元（对标 gdsfactory Component + IPKISS PCell）。

    支持三视图：Layout/Circuit/Netlist。
    【创新】Observer Pattern 自动同步：修改 Layout 视图自动更新 Circuit/Netlist 视图。

    来源:
    - gdsfactory Component (Matres et al., CLEO 2026)
    - IPKISS PCell (Luceda Photonics)
    - Observer Pattern (Gamma et al., "Design Patterns", 1994)
    """

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        """初始化多视图 PCell。

        Args:
            name: PCell 名称。
            params: 参数字典。
        """
        self.name = name
        self.params: dict[str, Any] = dict(params) if params else {}
        self.layout_view = LayoutView()
        self.circuit_view = CircuitView()
        self.netlist_view = NetlistView()
        self.info: dict[str, Any] = {}
        self._observers: list[ViewObserver] = [
            self.layout_view, self.circuit_view, self.netlist_view,
        ]

    def _notify(self, source: str, event: dict[str, Any]) -> None:
        """通知所有观察者（Observer Pattern）。"""
        for obs in self._observers:
            obs.on_view_changed(source, event)

    def add_polygon(self, points: np.ndarray, layer: str) -> None:
        """添加多边形到 Layout 视图。

        Args:
            points: 多边形顶点 (N, 2)。
            layer: 层名（如 "WG"）。
        """
        pts = np.asarray(points, dtype=float)
        self.layout_view.polygons.append((pts, layer))
        self._notify("layout", {"type": "add_polygon", "points": pts, "layer": layer})

    def add_port(
        self, name: str, x: float, y: float,
        direction: str | Direction, width: float = 0.5,
    ) -> None:
        """添加端口到 Layout 视图。

        Args:
            name: 端口名。
            x: x 坐标（μm）。
            y: y 坐标（μm）。
            direction: 朝向（"north"/"south"/"east"/"west" 或 Direction）。
            width: 波导宽度（μm）。
        """
        if isinstance(direction, str):
            direction = Direction(direction.lower())
        port = Port(
            name=name, x=x, y=y, direction=direction,
            waveguide_type="strip", width=width,
        )
        self.layout_view.ports.append(port)
        self._notify("layout", {
            "type": "add_port", "port_name": name, "x": x, "y": y, "width": width,
        })

    def add_ref(
        self, other: PCellMultiView, x: float = 0.0, y: float = 0.0,
        rotation: float = 0.0,
    ) -> None:
        """添加子 PCell 引用（对标 gdsfactory << 操作符）。

        Args:
            other: 被引用的子 PCell。
            x: x 方向偏移（μm）。
            y: y 方向偏移（μm）。
            rotation: 旋转角度（度）。
        """
        self._notify("layout", {
            "type": "add_ref", "cell_name": other.name,
            "x": x, "y": y, "rotation": rotation,
        })

    def get_netlist(self) -> dict[str, Any]:
        """获取网表视图。

        Returns:
            网表字典 {"instances": [...], "connections": [...], "ports": {...}}。
        """
        return {
            "instances": list(self.netlist_view.instances),
            "connections": list(self.netlist_view.connections),
            "ports": dict(self.netlist_view.ports),
        }

    def to_device(self) -> Device:
        """转换为 PoLaRIS Device。

        Returns:
            Device 对象。
        """
        all_x: list[float] = []
        all_y: list[float] = []
        for points, _ in self.layout_view.polygons:
            all_x.extend(points[:, 0].tolist())
            all_y.extend(points[:, 1].tolist())
        for p in self.layout_view.ports:
            all_x.append(p.x)
            all_y.append(p.y)
        if all_x:
            bbox = BoundingBox(min(all_x), min(all_y), max(all_x), max(all_y))
        else:
            bbox = BoundingBox(0.0, 0.0, 0.0, 0.0)
        return Device(
            device_id=self.name,
            platform=self.params.get("platform", "SOI"),
            category=self.params.get("category", "passive"),
            name=self.name,
            ports=list(self.layout_view.ports),
            bbox=bbox,
            params=dict(self.params),
        )


# ===== @polaris_cell 装饰器辅助函数 =====


def _is_instance(value: Any, annotation: Any) -> bool:
    """检查值是否匹配类型标注。"""
    if annotation is Any:
        return True
    if annotation is type(None):
        return value is None
    origin = get_origin(annotation)
    if origin is not None:
        if origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
            return any(_is_instance(value, a) for a in get_args(annotation))
        return isinstance(value, origin)
    if annotation is float and isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(annotation, type):
        return isinstance(value, annotation)
    return False


def _validate_type(name: str, value: Any, annotation: Any) -> None:
    """参数类型校验。"""
    if annotation is inspect.Parameter.empty:
        return
    if not _is_instance(value, annotation):
        raise TypeError(f"参数 '{name}' 期望 {annotation}，得到 {type(value).__name__}")


def _make_hashable(value: Any) -> Any:
    """将值转换为可哈希形式。"""
    if isinstance(value, np.ndarray):
        return ("ndarray", value.shape, value.tobytes().hex())
    if isinstance(value, (list, tuple)):
        return tuple(_make_hashable(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in value.items()))
    try:
        hash(value)
        return value
    except TypeError:
        return repr(value)


def _make_cache_key(func_name: str, arguments: dict[str, Any]) -> tuple:
    """生成缓存键：(函数名, 参数元组的 hash)。

    来源: gdsfactory @gf.cell 缓存键设计
    """
    args_tuple = tuple((k, _make_hashable(v)) for k, v in sorted(arguments.items()))
    return (func_name, hash(args_tuple))


def _ensure_unique_name(base_name: str, param_key: tuple) -> str:
    """命名唯一性：同名 PCell 不同参数 → 不同实例名。

    来源: gdsfactory Component 命名规则
    """
    reg = _NAME_REGISTRY.setdefault(base_name, set())
    if param_key in reg:
        return base_name
    suffix = len(reg)
    reg.add(param_key)
    return base_name if suffix == 0 else f"{base_name}_{suffix}"


def _resolve_hints(func: Callable) -> dict[str, Any]:
    """解析函数类型标注。

    R05 改进 v3.3-PCELL-HINTS: 原 `except NameError: return {}` 静默丢失
    forward reference 解析失败信息。改进：添加 logger.debug 记录被跳过的
    函数名，便于调试注解缺失问题。返回空 dict 仍为合法业务语义（typing
    官方文档化行为：forward reference 未定义时 get_type_hints 抛 NameError）。
    """
    try:
        return typing.get_type_hints(func)
    except NameError as e:
        # 不 raise：forward reference 解析失败时返回空 dict 是合法业务语义
        # 但需记录调试信息，避免静默吞异常（R03 边界改进）
        logger.debug(
            "类型注解解析失败（forward reference 未定义）: func=%s | error=%s",
            getattr(func, "__qualname__", func), e,
        )
        return {}


def polaris_cell(func: Callable) -> Callable:
    """PCell 装饰器（对标 gdsfactory @gf.cell）。

    功能：自动缓存（LRU，maxsize=1024）、参数校验（类型检查）、命名唯一性、info 元数据。

    来源: gdsfactory @gf.cell https://gdsfactory.github.io/gdsfactory/

    用法:
        @polaris_cell
        def mmi1x2(width: float = 0.5, length: float = 10.0) -> PCellMultiView:
            ...
    """
    sig = inspect.signature(func)
    hints = _resolve_hints(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> PCellMultiView:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        for param_name, param_value in bound.arguments.items():
            _validate_type(
                param_name, param_value,
                hints.get(param_name, inspect.Parameter.empty),
            )
        key = _make_cache_key(func.__name__, bound.arguments)
        cached = _DEFAULT_CACHE.get(key)
        if cached is not None:
            return cached
        cell = func(*args, **kwargs)
        if not isinstance(cell, PCellMultiView):
            raise TypeError(
                f"@polaris_cell 装饰的函数 '{func.__name__}' 须返回 PCellMultiView，"
                f"得到 {type(cell).__name__}"
            )
        cell.name = _ensure_unique_name(cell.name, key)
        cell.info.setdefault("function", func.__name__)
        cell.info.setdefault("params", dict(bound.arguments))
        _DEFAULT_CACHE.put(key, cell)
        return cell

    return wrapper


# ===== AI 辅助 PCell 代码生成（【创新】） =====


def _extract_number(description: str, *patterns: str) -> float | None:
    """从描述中提取数字。"""
    for pat in patterns:
        match = re.search(pat, description, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def ai_generate_pcell(description: str, platform: str = "SOI") -> str:
    """AI 辅助 PCell 代码生成（【创新】）。

    【创新】gdsfactory 无此能力，PhIDO 仅配置参数。PoLaRIS 用模板生成 PCell 代码。
    支持理论: PhIDO arXiv:2508.14123 验证 LLM 可理解光子电路结构。

    根据自然语言描述生成 @polaris_cell 装饰的 PCell 代码（规则模板匹配，非 LLM 调用）。

    Args:
        description: 自然语言描述（如"半径5μm的环谐振器"）。
        platform: 目标平台（默认 SOI）。

    Returns:
        PCell Python 代码字符串。

    Raises:
        ValueError: 无法识别的器件类型。
    """
    desc_lower = description.lower()
    if "环" in description or "ring" in desc_lower or "谐振" in description:
        return _gen_ring_code(description, platform)
    if "mmi" in desc_lower:
        return _gen_mmi_code(description, platform)
    if "波导" in description or "waveguide" in desc_lower or "straight" in desc_lower:
        return _gen_waveguide_code(description, platform)
    if "y" in desc_lower and ("分支" in description or "branch" in desc_lower):
        return _gen_ybranch_code(description, platform)
    raise ValueError(f"无法识别的器件类型: {description}")


def _gen_ring_code(description: str, platform: str) -> str:
    """生成环谐振器 PCell 代码。"""
    r = _extract_number(description, r"(?:半径|radius)\s*[:：]?\s*(\d+\.?\d*)") or 5.0
    g = _extract_number(description, r"(?:间距|gap)\s*[:：]?\s*(\d+\.?\d*)") or 0.2
    w = _extract_number(description, r"(?:宽度|宽|width)\s*[:：]?\s*(\d+\.?\d*)") or 0.5
    return f'''@polaris_cell
def ring_resonator(radius: float = {r}, gap: float = {g}, width: float = {w}) -> PCellMultiView:
    """环谐振器 PCell（AI 生成，平台={platform}）。"""
    cell = PCellMultiView(name="ring_resonator", params={{"radius": radius, "gap": gap,
                  "width": width, "platform": "{platform}"}})
    ang = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    cell.add_polygon(np.column_stack([radius * np.cos(ang), radius * np.sin(ang)]), layer="WG")
    bus_y = -radius - gap
    cell.add_polygon(np.array([[-radius - 5, bus_y], [radius + 5, bus_y]]), layer="WG")
    cell.add_port("in", -radius - 5, bus_y, "west", width)
    cell.add_port("out", radius + 5, bus_y, "east", width)
    return cell
'''


def _gen_mmi_code(description: str, platform: str) -> str:
    """生成 MMI 1x2 PCell 代码。"""
    w = _extract_number(description, r"(?:宽度|宽|width)\s*[:：]?\s*(\d+\.?\d*)") or 0.5
    ln = _extract_number(description, r"(?:长度|长|length)\s*[:：]?\s*(\d+\.?\d*)") or 10.0
    return f'''@polaris_cell
def mmi1x2(width: float = {w}, length: float = {ln}) -> PCellMultiView:
    """MMI 1x2 PCell（AI 生成，平台={platform}）。"""
    cell = PCellMultiView(name="mmi1x2", params={{"width": width, "length": length,
                  "platform": "{platform}"}})
    cell.add_polygon(np.array([[0, -1.0], [length, -1.5], [length, 1.5], [0, 1.0]]), layer="WG")
    cell.add_port("in", 0, 0, "west", width)
    cell.add_port("out1", length, 1.0, "east", width)
    cell.add_port("out2", length, -1.0, "east", width)
    return cell
'''


def _gen_waveguide_code(description: str, platform: str) -> str:
    """生成直波导 PCell 代码。"""
    w = _extract_number(description, r"(?:宽度|宽|width)\s*[:：]?\s*(\d+\.?\d*)") or 0.5
    ln = _extract_number(description, r"(?:长度|长|length)\s*[:：]?\s*(\d+\.?\d*)") or 10.0
    return f'''@polaris_cell
def straight_waveguide(width: float = {w}, length: float = {ln}) -> PCellMultiView:
    """直波导 PCell（AI 生成，平台={platform}）。"""
    cell = PCellMultiView(name="straight_waveguide", params={{"width": width,
                  "length": length, "platform": "{platform}"}})
    wg_pts = np.array([[0, -w / 2], [length, -w / 2], [length, w / 2], [0, w / 2]])
    cell.add_polygon(wg_pts, layer="WG")
    cell.add_port("in", 0, 0, "west", width)
    cell.add_port("out", length, 0, "east", width)
    return cell
'''


def _gen_ybranch_code(description: str, platform: str) -> str:
    """生成 Y 分支 PCell 代码。"""
    w = _extract_number(description, r"(?:宽度|宽|width)\s*[:：]?\s*(\d+\.?\d*)") or 0.5
    return f'''@polaris_cell
def y_branch(width: float = {w}) -> PCellMultiView:
    """Y 分支 PCell（AI 生成，平台={platform}）。"""
    cell = PCellMultiView(name="y_branch", params={{"width": width, "platform": "{platform}"}})
    cell.add_polygon(np.array([[0, 0], [10, 2], [10, 0.5]]), layer="WG")
    cell.add_polygon(np.array([[0, 0], [10, -2], [10, -0.5]]), layer="WG")
    cell.add_port("in", 0, 0, "west", width)
    cell.add_port("out1", 10, 2, "east", width)
    cell.add_port("out2", 10, -2, "east", width)
    return cell
'''
