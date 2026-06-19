"""版图渲染与导出（Task 16）。

提供：
- matplotlib 版图渲染（器件矩形 + 波导折线 + 端口标记 + 拥塞热力图）
- GDSII/OASIS 导出（通过 klayout.db，开源工具直接集成）
- DRC 报告（间距/重叠检查）

工具来源：
- klayout Python: https://www.klayout.de/ （GDSII/OASIS 读写 + DRC）
- matplotlib: https://matplotlib.org/ （版图渲染）
- gdsfactory GDS 导出参考: https://gdsfactory.github.io/gdsfactory/

可选依赖处理（规则 5.3.1）：
- klayout 为可选依赖（pyproject.toml [project.optional-dependencies].layout）
- 缺失时 GDS/OASIS 导出函数抛出 ImportError 并提示安装命令
- 核心功能（PDK/布局/布线/训练）不依赖 klayout
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.engine.floorplan_env import Placement
from polaris.router.waveguide_router import WaveguidePath

# 可选依赖：klayout（缺失时 GDS/OASIS 导出抛出明确错误）
try:
    import klayout.db as _db

    _HAS_KLAYOUT = True
except ImportError:
    _db = None
    _HAS_KLAYOUT = False


def _require_klayout(feature_name: str) -> None:
    """检查 klayout 是否可用，不可用时抛出 ImportError。

    Args:
        feature_name: 功能名称（用于错误提示）。

    Raises:
        ImportError: klayout 未安装时。
    """
    if not _HAS_KLAYOUT:
        raise ImportError(
            f"{feature_name} 需要 klayout 库。请安装：pip install klayout"
            "（或 pip install polaris-pnr[layout]）"
        )


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
        fig.savefig(opts.save_path, dpi=150, bbox_inches="tight")
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
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return LayoutRender(fig=fig, ax=ax)


# ---------------------------------------------------------------------------
# GDSII/OASIS 导出（klayout.db 集成）
# ---------------------------------------------------------------------------
def _um_to_dbu(um: float, dbu: float = 0.001) -> int:
    """微米转 database unit（klayout 默认 1nm = 0.001μm dbu）。"""
    return int(round(um / dbu))


def _create_klayout_layout(dbu: float = 0.001):
    """创建 klayout Layout 并定义工艺层，返回 (layout, top, layer_map)。"""
    _require_klayout("GDS/OASIS 导出")
    db = _db

    ly = db.Layout()
    ly.dbu = dbu
    top = ly.create_cell("TOP")
    layer_map = {
        "passive": ly.layer(1, 0),
        "active": ly.layer(2, 0),
        "source": ly.layer(3, 0),
        "detector": ly.layer(4, 0),
        "waveguide": ly.layer(5, 0),
        "port": ly.layer(10, 0),
    }
    return ly, top, layer_map


def _place_device_boxes(top, placements, layer_map, dbu, add_ports: bool) -> None:
    """将器件矩形画到对应工艺层，可选添加端口标记。"""
    db = _db

    for pl in placements.values():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        layer = layer_map.get(pl.device.category, layer_map["passive"])
        box = db.Box(
            _um_to_dbu(xmin, dbu),
            _um_to_dbu(ymin, dbu),
            _um_to_dbu(xmax, dbu),
            _um_to_dbu(ymax, dbu),
        )
        top.shapes(layer).insert(box)
        if add_ports:
            _place_port_markers(top, pl, layer_map["port"], dbu)


def _place_port_markers(top, pl, layer_port, dbu) -> None:
    """在端口位置画小矩形标记。"""
    db = _db

    ps = _um_to_dbu(0.5, dbu)
    for _, (px, py) in pl.port_positions().items():
        pbox = db.Box(
            _um_to_dbu(px, dbu) - ps,
            _um_to_dbu(py, dbu) - ps,
            _um_to_dbu(px, dbu) + ps,
            _um_to_dbu(py, dbu) + ps,
        )
        top.shapes(layer_port).insert(pbox)


def _place_waveguide_paths(top, paths, layer_waveguide) -> None:
    """将波导路径画到布线层。"""
    db = _db

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

    将器件矩形画到对应工艺层，波导画到布线层，端口画到端口层。

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
    _place_waveguide_paths(top, paths, layers["waveguide"])
    ly.write(output_path)
    return output_path


def export_oasis(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    output_path: str = "layout.oas",
    dbu: float = 0.001,
) -> str:
    """导出 OASIS 文件（通过 klayout.db）。

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
    _place_waveguide_paths(top, paths, layers["waveguide"])
    ly.write(output_path)
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
    """检查波导路径弯曲半径违规，返回 (违规数, 详情列表)。"""
    violations = 0
    details: list[str] = []
    for conn_idx, wp in paths.items():
        for i in range(1, len(wp.points) - 1):
            dx1 = wp.points[i][0] - wp.points[i - 1][0]
            dy1 = wp.points[i][1] - wp.points[i - 1][1]
            dx2 = wp.points[i + 1][0] - wp.points[i][0]
            dy2 = wp.points[i + 1][1] - wp.points[i][1]
            if abs(dx1 - dx2) > 1e-9 or abs(dy1 - dy2) > 1e-9:
                seg1_len = (dx1**2 + dy1**2) ** 0.5
                if seg1_len < min_bend_radius_um:
                    violations += 1
                    details.append(
                        f"弯曲半径不足: 连接 {conn_idx} 在 {wp.points[i]} "
                        f"段长 {seg1_len:.3f}μm < {min_bend_radius_um}μm"
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
