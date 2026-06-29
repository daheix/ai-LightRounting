"""版图渲染与导出（Task 16）。

提供：
- matplotlib 版图渲染（器件矩形 + 波导折线 + 端口标记 + 拥塞热力图）
- GDSII/OASIS 导出（通过 klayout.db，开源工具直接集成）
- DRC 报告（间距/重叠检查）

工具来源：
- klayout Python: https://www.klayout.de/ （GDSII/OASIS 读写 + DRC）
- matplotlib: https://matplotlib.org/ （版图渲染）
- gdsfactory GDS 导出参考: https://gdsfactory.github.io/gdsfactory/

三方工具 import 处理（规则 5.3 + R05 Bug 修复 v3.3-EVAL-1）：
- klayout 为运行依赖（pyproject.toml [project.dependencies]），install.sh 统一安装
- **延迟导入**：klayout.db 不在顶层 import，仅在 GDS/OASIS 导出函数内按需导入，
  使 matplotlib 渲染等核心功能不受 klayout 安装状态影响
- import 失败时 GDS/OASIS 导出函数抛出 ImportError 并提示安装命令
- 核心功能（PDK/布局/布线/训练/渲染）独立于 klayout
- 规则: R02 学术诚信 / R03 禁止静默兜底 / R05 Bug 必修
- 文献: PEP 8 模块导入 https://peps.python.org/pep-0008/
- 文献: Python 延迟导入模式 https://docs.python.org/3/tutorial/modules.html
- 文献: TYPE_CHECKING 模式 https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING
- 文献: klayout Python API https://www.klayout.de/doc-qt5/code/
- 文献: gdsfactory KLayout 集成 https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from polaris.engine.floorplan_env import Placement
from polaris.pdk.layer_map import (
    POLARIS_CATEGORY_LAYER_MAP,
    POLARIS_GDS_LAYER_MAP,
)
from polaris.pdk.port import Direction
from polaris.router.waveguide_router import WaveguidePath

# 类型检查时导入 klayout.db 以提供精确类型注解（运行时不导入）
if TYPE_CHECKING:
    import klayout.db as _db  # noqa: F401


def _get_klayout_db() -> Any:
    """延迟导入 klayout.db 模块（R05 Bug 修复 v3.3-EVAL-1）。

    原 `import klayout.db as _db` 在顶层，导致 klayout 未安装时整个模块
    无法加载，matplotlib 渲染等核心功能也不可用。改为延迟导入后，仅
    GDS/OASIS 导出函数实际需要 klayout 时才导入。

    Returns:
        klayout.db 模块对象。

    Raises:
        ImportError: klayout 未安装时抛出，含安装命令提示（R03 禁止静默兜底）。
    """
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，GDS/OASIS 导出功能不可用。"
            "安装命令: pip install klayout"
            "（或参考 install.sh 统一安装）"
        ) from e
    return db


def _atomic_write_klayout(ly: Any, output_path: str) -> str:
    """原子写入 GDS/OASIS 文件（R05 Bug 修复 v4.0-ATOMIC-02，第1轮迭代发现）。

    原 ly.write(output_path) 非原子，大版图（>100MB）写入耗时长，中断会导致
    文件截断/半写入，损坏的 GDS 提交到代工厂会直接导致流片失败，客户索赔
    金额可达百万级。改为临时文件 + os.replace 原子替换。

    Args:
        ly: klayout.Layout 对象。
        output_path: 目标输出路径。

    Returns:
        output_path（写入成功后返回）。

    Raises:
        OSError: 临时文件创建或替换失败时抛出（R03 禁止 fall-back）。
    """
    target = Path(output_path)
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=target.name + ".", suffix=".tmp"
    )
    # 关闭 fd，由 klayout ly.write 重新打开（避免双 open 冲突）
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        ly.write(str(tmp_path))
        # 确保 klayout 写入的数据持久化到磁盘
        with open(tmp_path, "rb") as f:
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return output_path

# 器件类别 → 渲染颜色
_CATEGORY_COLORS = {
    "passive": "#4C72B0",
    "active": "#DD8452",
    "source": "#55A868",
    "detector": "#C44E52",
}


@dataclass
class LayoutRender:
    """版图渲染结果。"""

    fig: object
    ax: object


@dataclass
class RenderOptions:
    """渲染选项（将 render_layout 的可选参数打包，降低函数参数个数）。

    Attributes:
        title: 图标题。
        show_ports: 是否标记端口位置。
        save_path: 保存路径（None 则不保存）。
    """

    title: str = "PoLaRIS Layout"
    show_ports: bool = True
    save_path: str | None = None


def _draw_congestion(ax, congestion: np.ndarray) -> None:
    """在 ax 上绘制拥塞热力图背景。"""
    import matplotlib.pyplot as plt

    im = ax.imshow(
        congestion,
        origin="lower",
        extent=[0, congestion.shape[1], 0, congestion.shape[0]],
        alpha=0.3,
        cmap="YlOrRd",
    )
    plt.colorbar(im, ax=ax, label="Congestion")


def _draw_devices(ax, placements: dict[str, Placement], show_ports: bool) -> None:
    """在 ax 上绘制器件矩形与端口标记。"""
    from matplotlib.patches import Rectangle

    for inst_id, pl in placements.items():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        w = xmax - xmin
        h = ymax - ymin
        color = _CATEGORY_COLORS.get(pl.device.category, "#888888")
        rect = Rectangle(
            (xmin, ymin),
            w,
            h,
            linewidth=1,
            edgecolor="black",
            facecolor=color,
            alpha=0.7,
        )
        ax.add_patch(rect)
        ax.text(
            xmin + w / 2,
            ymin + h / 2,
            inst_id,
            ha="center",
            va="center",
            fontsize=7,
            rotation=45,
        )
        if show_ports:
            for _, (px, py) in pl.port_positions().items():
                ax.plot(px, py, "r.", markersize=4)


def _draw_paths(ax, paths: dict[int, WaveguidePath]) -> None:
    """在 ax 上绘制波导路径折线。"""
    for wp in paths.values():
        if len(wp.points) >= 2:
            xs = [p[0] for p in wp.points]
            ys = [p[1] for p in wp.points]
            ax.plot(xs, ys, "g-", linewidth=1.5, alpha=0.8)


def render_layout(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    congestion: np.ndarray | None = None,
    options: RenderOptions | None = None,
) -> LayoutRender:
    """渲染版图（matplotlib）。

    Args:
        placements: 器件放置结果。
        paths: 波导路径（conn_idx -> WaveguidePath）。
        congestion: 拥塞热力图（可选叠加）。
        options: 渲染选项（标题/端口标记/保存路径），默认使用 ``RenderOptions()``。

    Returns:
        ``LayoutRender``（含 fig/ax）。
    """
    import matplotlib.pyplot as plt

    opts = options or RenderOptions()
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    if congestion is not None:
        _draw_congestion(ax, congestion)
    _draw_devices(ax, placements, opts.show_ports)
    if paths:
        _draw_paths(ax, paths)
    ax.set_aspect("equal")
    ax.set_xlabel("X (μm)")
    ax.set_ylabel("Y (μm)")
    ax.set_title(opts.title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if opts.save_path:
        # R05 Bug 修复 v4.0-PLT-CLOSE（第1轮迭代发现）:
        # 原 savefig 后未 close fig，RL 训练批量渲染（rollout 1000+ 次）
        # 时 matplotlib 累积打开 figures 触发 RuntimeWarning:
        # "More than 20 figures have been opened" 内存泄漏。
        # 修复: savefig 后立即 plt.close(fig) 释放资源。
        # 规则: R05 Bug 必修 / R03 禁止 fall-back
        # 文献: matplotlib close 推荐
        #   https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.close.html
        # 文献: matplotlib 内存管理
        #   https://matplotlib.org/stable/users/explain/figure/event_handling.html
        # 文献: SO 高票答案 "matplotlib memory leak fig"
        #   https://stackoverflow.com/questions/8213522/
        fig.savefig(opts.save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    return LayoutRender(fig=fig, ax=ax)


def render_congestion_heatmap(
    congestion: np.ndarray,
    title: str = "Congestion Heatmap",
    save_path: str | None = None,
) -> LayoutRender:
    """渲染拥塞热力图。"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(congestion, origin="lower", cmap="YlOrRd")
    plt.colorbar(im, ax=ax, label="Congestion count")
    ax.set_xlabel("X grid")
    ax.set_ylabel("Y grid")
    ax.set_title(title)
    fig.tight_layout()
    if save_path:
        # R05 Bug 修复 v4.0-PLT-CLOSE: 同 render_layout，savefig 后 close 释放内存
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    return LayoutRender(fig=fig, ax=ax)


# ---------------------------------------------------------------------------
# GDSII/OASIS 导出（klayout.db 集成）
# ---------------------------------------------------------------------------
def _um_to_dbu(um: float, dbu: float = 0.001) -> int:
    """微米转 database unit（klayout 默认 1nm = 0.001μm dbu）。"""
    return int(round(um / dbu))


# Direction → 单位向量 (dx, dy)，用于 PinRec Path 方向计算
_DIR_VEC: dict[Direction, tuple[float, float]] = {
    Direction.EAST: (1.0, 0.0),
    Direction.WEST: (-1.0, 0.0),
    Direction.NORTH: (0.0, 1.0),
    Direction.SOUTH: (0.0, -1.0),
}


def _create_klayout_layout(dbu: float = 0.001) -> tuple[Any, Any, dict[str, Any]]:
    """创建 klayout Layout 并定义工艺层，返回 (layout, top, layer_map)。

    使用真实 foundry layer 编号（止血7），借鉴 SiEPIC EBeam PDK + ubcpdk +
    gdsfactory generic_pdk（均 MIT 许可证）。详见 ``polaris.pdk.layer_map``。

    Args:
        dbu: database unit（μm，默认 1nm）。

    Returns:
        ``(layout, top_cell, layer_map)`` 元组。``layer_map`` 为名称到
        klayout layer info 的字典，包含 WG/PORT/DEVREC/TEXT/FLOORPLAN 等层。
    """
    db = _get_klayout_db()

    ly = db.Layout()
    ly.dbu = dbu
    top = ly.create_cell("TOP")
    # 使用真实 foundry layer 编号（SiEPIC/gdsfactory 标准，止血7）
    layer_map: dict[str, object] = {}
    for name, gds_layer in POLARIS_GDS_LAYER_MAP.items():
        layer_map[name] = ly.layer(gds_layer.layer, gds_layer.datatype)
    return ly, top, layer_map


def _place_devrec_text(
    top: Any,
    pl: Placement,
    layer_devrec: Any,
    cx: float,
    cy: float,
) -> None:
    """在 DEVREC 层添加 SiEPIC 标准 Text 标签（真实版图验证）。

    真实 SiEPIC 格式（RingResonator.gds 验证）：
    - Lumerical_INTERCONNECT_library=Design kits/ebeam_v1.2
    - Lumerical_INTERCONNECT_component=<器件名>
    - Spice_param:<参数列表>（冒号，参数值带 'u' 后缀表示 μm）

    来源: SiEPIC EBeam PDK Examples
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    db = _get_klayout_db()
    lib_text = db.DText(
        "Lumerical_INTERCONNECT_library=Design kits/ebeam_v1.2",
        db.DTrans(cx, cy - 1.0),
    )
    top.shapes(layer_devrec).insert(lib_text)
    comp_text = db.DText(
        f"Lumerical_INTERCONNECT_component={pl.device.name}",
        db.DTrans(cx, cy),
    )
    top.shapes(layer_devrec).insert(comp_text)
    if pl.device.params:
        params_str = " ".join(f"{k}={v}u" for k, v in pl.device.params.items())
        spice_text = db.DText(f"Spice_param:{params_str}", db.DTrans(cx, cy + 1.0))
        top.shapes(layer_devrec).insert(spice_text)


def _place_device_boxes(
    top: Any,
    placements: dict[str, Placement],
    layer_map: dict[str, Any],
    dbu: float,
    add_ports: bool,
) -> None:
    """将器件矩形画到对应工艺层，可选添加端口标记。

    器件按其 ``category`` 映射到真实 foundry 层（止血7）：
    - passive/active → WG (1,0)
    - source → SOURCE (110,0)
    - detector → GE (5,0)
    同时在 DEVREC (68,0) 层画器件包围盒 + SiEPIC 标准 Text 标签
    （Lumerical_INTERCONNECT_component + Spice_param，netlist 提取与连接性验证）。

    来源: SiEPIC EBeam PDK Examples
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    db = _get_klayout_db()

    for _inst_id, pl in placements.items():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        # 按器件类别查真实 foundry 层名（默认 WG）
        layer_name = POLARIS_CATEGORY_LAYER_MAP.get(pl.device.category, "WG")
        layer = layer_map[layer_name]
        box = db.Box(
            _um_to_dbu(xmin, dbu),
            _um_to_dbu(ymin, dbu),
            _um_to_dbu(xmax, dbu),
            _um_to_dbu(ymax, dbu),
        )
        top.shapes(layer).insert(box)
        # DEVREC 层：器件识别层（SiEPIC 标准，netlist 提取/连接性验证）
        top.shapes(layer_map["DEVREC"]).insert(box)
        # DEVREC Text 标签（SiEPIC 真实格式）
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        _place_devrec_text(top, pl, layer_map["DEVREC"], cx, cy)
        if add_ports:
            # 端口 Path + pin名 Text 都在 PIN layer (69,0)（真实 SiEPIC 格式）
            _place_port_markers(top, pl, layer_map["PIN"], layer_map["PIN"], dbu)


def _place_port_markers(
    top: Any,
    pl: Placement,
    layer_port: Any,
    layer_text: Any,
    dbu: float,
) -> None:
    """在端口位置画 PinRec Path + pin 名称 Text（SiEPIC Tools 格式）。

    SiEPIC Tools 要求 PinRec 层用 Path 形状（非 Box）表示端口，
    Path 从器件内部指向外部，提供信号离开方向；并在 Path 中点
    添加 pin 名称 Text 标签（netlist 提取依赖此格式）。

    来源: SiEPIC-Tools Wiki - Layout - Devices
    https://github.com/SiEPIC/SiEPIC-Tools/wiki
    """
    db = _get_klayout_db()
    pin_len = 1.0  # PinRec Path 长度（μm，SiEPIC 推荐值）

    for port in pl.ports_abs():
        px, py = port.x, port.y
        dx, dy = _DIR_VEC.get(port.direction, (0.0, 0.0))
        # Path 跨越器件边界：起点在器件内部，终点在器件外部，中点为端口位置
        x1 = px - dx * pin_len / 2
        y1 = py - dy * pin_len / 2
        x2 = px + dx * pin_len / 2
        y2 = py + dy * pin_len / 2
        pts = [db.DPoint(x1, y1), db.DPoint(x2, y2)]
        path = db.DPath(pts, 0.5)  # 0.5μm 宽
        top.shapes(layer_port).insert(path)
        # pin 名称 Text 在 Path 中点（即端口位置）
        text = db.DText(port.name, db.DTrans(px, py))
        top.shapes(layer_text).insert(text)


def _place_waveguide_paths(
    top: Any,
    paths: dict[int, WaveguidePath] | None,
    layer_waveguide: Any,
) -> None:
    """将波导路径画到布线层（WG 层，与器件同层）。"""
    db = _get_klayout_db()

    if not paths:
        return
    for wp in paths.values():
        if len(wp.points) < 2:
            continue
        pts = [db.DPoint(p[0], p[1]) for p in wp.points]
        path = db.DPath(pts, 0.5)  # 0.5μm 宽
        top.shapes(layer_waveguide).insert(path)


def export_gds(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    output_path: str = "layout.gds",
    dbu: float = 0.001,
) -> str:
    """导出 GDSII 文件（通过 klayout.db）。

    使用真实 foundry layer 编号（止血7）：
    - 器件按类别画到 WG/SOURCE/GE 层
    - 器件包围盒同时画到 DEVREC 层（netlist 提取）
    - 端口画到 PORT (PinRec) 层
    - 波导画到 WG 层（与器件同层）

    Args:
        placements: 器件放置结果。
        paths: 波导路径。
        output_path: 输出 GDS 路径。
        dbu: database unit（μm，默认 1nm）。

    Returns:
        输出文件路径。
    """
    ly, top, layers = _create_klayout_layout(dbu)
    _place_device_boxes(top, placements, layers, dbu, add_ports=True)
    _place_waveguide_paths(top, paths, layers["WG"])
    # R05 Bug 修复 v4.0-ATOMIC-02: 原子写入（临时文件 + os.replace）
    _atomic_write_klayout(ly, output_path)
    return output_path


def export_oasis(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    output_path: str = "layout.oas",
    dbu: float = 0.001,
) -> str:
    """导出 OASIS 文件（通过 klayout.db）。

    使用真实 foundry layer 编号（止血7，详见 ``export_gds``）。

    Args:
        placements: 器件放置结果。
        paths: 波导路径。
        output_path: 输出 OASIS 路径。
        dbu: database unit（μm）。

    Returns:
        输出文件路径。
    """
    ly, top, layers = _create_klayout_layout(dbu)
    _place_device_boxes(top, placements, layers, dbu, add_ports=False)
    _place_waveguide_paths(top, paths, layers["WG"])
    # R05 Bug 修复 v4.0-ATOMIC-02: 原子写入（临时文件 + os.replace）
    _atomic_write_klayout(ly, output_path)
    return output_path


# ---------------------------------------------------------------------------
# DRC 报告
# ---------------------------------------------------------------------------
@dataclass
class DRCReport:
    """DRC 检查报告。"""

    overlap_violations: int = 0
    spacing_violations: int = 0
    min_bend_radius_violations: int = 0
    details: list[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []

    @property
    def total_violations(self) -> int:
        return self.overlap_violations + self.spacing_violations + self.min_bend_radius_violations

    @property
    def passed(self) -> bool:
        return self.total_violations == 0


def _boxes_intersect(a: tuple, b: tuple) -> bool:
    """纯 Python 判断两个轴对齐矩形是否相交（含边界接触）。

    替代 shapely.geometry.box.intersects，避免 shapely 依赖（规则 3.2/5.3）。

    Args:
        a: (xmin, ymin, xmax, ymax)。
        b: (xmin, ymin, xmax, ymax)。

    Returns:
        是否相交。
    """
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _boxes_distance(a: tuple, b: tuple) -> float:
    """纯 Python 计算两个轴对齐矩形之间的最短距离（0 表示相交）。

    替代 shapely.geometry.box.distance，避免 shapely 依赖。

    Args:
        a: (xmin, ymin, xmax, ymax)。
        b: (xmin, ymin, xmax, ymax)。

    Returns:
        最短距离（μm）。
    """
    if _boxes_intersect(a, b):
        return 0.0
    dx = max(0.0, max(b[0] - a[2], a[0] - b[2]))
    dy = max(0.0, max(b[1] - a[3], a[1] - b[3]))
    return (dx * dx + dy * dy) ** 0.5


def _check_device_overlaps(pls: list, min_spacing_um: float) -> tuple[int, int, list[str]]:
    """检查器件间重叠与间距违规，返回 (重叠数, 间距违规数, 详情列表)。

    使用纯 Python 几何运算（_boxes_intersect/_boxes_distance），
    不依赖 shapely（规则 3.2：shapely 不装，用纯 Python 实现）。
    """
    overlaps = 0
    spacings = 0
    details: list[str] = []
    for i in range(len(pls)):
        a = pls[i].bbox_abs()
        for j in range(i + 1, len(pls)):
            b = pls[j].bbox_abs()
            if _boxes_intersect(a, b):
                overlaps += 1
                details.append(f"重叠: {pls[i].instance_id} & {pls[j].instance_id}")
            else:
                dist = _boxes_distance(a, b)
                if dist < min_spacing_um:
                    spacings += 1
                    details.append(
                        f"间距不足: {pls[i].instance_id} & {pls[j].instance_id} "
                        f"距离 {dist:.3f}μm < {min_spacing_um}μm"
                    )
    return overlaps, spacings, details


def _check_bend_radius(paths: dict, min_bend_radius_um: float) -> tuple[int, list[str]]:
    """检查波导路径弯曲半径违规，返回 (违规数, 详情列表)。

    修复 P0-D: 原算法错误地用"段长 < min_bend_radius"判断违规，物理错误。
    现采用三点圆弧外接圆半径公式（正确物理定义）：

        R = |P1P2| · |P2P3| · |P1P3| / (4 · S)

    其中 S 为三点构成三角形的面积（叉积一半）。三点共线时 R = ∞（无弯曲）。

    等价形式（夹角法，验证用）：
        R = L / (2 · sin(θ))，θ 为 P1P2 与 P2P3 夹角，L 为相邻段长

    学术依据:
    - Fujisawa et al., "Design and fabrication of silicon photonic wires",
      Photonics 2017, https://www.mdpi.com/2304-6732/4/4/46
    - Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 波导损耗参数）
      https://ieeexplore.ieee.org/document/1148303
    - 三点外接圆半径公式: 任意解析几何教材（Coxeter "Introduction to Geometry"）
    """
    violations = 0
    details: list[str] = []
    for conn_idx, wp in paths.items():
        if len(wp.points) < 3:
            continue
        for i in range(1, len(wp.points) - 1):
            p1 = wp.points[i - 1]
            p2 = wp.points[i]
            p3 = wp.points[i + 1]
            # 三段长
            a = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5  # |P1P2|
            b = ((p3[0] - p2[0]) ** 2 + (p3[1] - p2[1]) ** 2) ** 0.5  # |P2P3|
            c = ((p3[0] - p1[0]) ** 2 + (p3[1] - p1[1]) ** 2) ** 0.5  # |P1P3|
            # 三角形面积（叉积一半，绝对值）
            cross = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p3[0] - p1[0]) * (
                p2[1] - p1[1]
            )
            area = abs(cross) / 2.0
            # 共线（area ≈ 0）→ 直线，无弯曲，R = ∞，跳过
            if area < 1e-12:
                continue
            # 三点外接圆半径 R = abc / (4·S)
            radius = (a * b * c) / (4.0 * area)
            if radius < min_bend_radius_um:
                violations += 1
                details.append(
                    f"弯曲半径不足: 连接 {conn_idx} 在 {p2} "
                    f"R={radius:.3f}μm < {min_bend_radius_um}μm"
                )
    return violations, details


def run_drc(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    min_spacing_um: float = 1.0,
    min_bend_radius_um: float = 5.0,
) -> DRCReport:
    """运行 DRC 检查（间距/重叠/弯曲半径）。

    使用纯 Python 几何运算（_boxes_intersect/_boxes_distance）检测器件
    重叠与间距违规，检查波导路径弯曲半径违规。
    不依赖 shapely（规则 3.2：shapely 不装，用纯 Python 实现）。
    """
    report = DRCReport()
    pls = list(placements.values())
    overlaps, spacings, overlap_details = _check_device_overlaps(pls, min_spacing_um)
    report.overlap_violations = overlaps
    report.spacing_violations = spacings
    report.details.extend(overlap_details)
    if paths:
        bend_violations, bend_details = _check_bend_radius(paths, min_bend_radius_um)
        report.min_bend_radius_violations = bend_violations
        report.details.extend(bend_details)
    return report
