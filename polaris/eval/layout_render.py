"""版图渲染与导出（Task 16）。

提供：
- matplotlib 版图渲染（器件矩形 + 波导折线 + 端口标记 + 拥塞热力图）
- GDSII/OASIS 导出（通过 klayout.db，开源工具直接集成）
- DRC 报告（间距/重叠检查）

工具来源：
- klayout Python: https://www.klayout.de/ （GDSII/OASIS 读写 + DRC）
- matplotlib: https://matplotlib.org/ （版图渲染）
- gdsfactory GDS 导出参考: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.engine.floorplan_env import Placement
from polaris.router.waveguide_router import WaveguidePath


@dataclass
class LayoutRender:
    """版图渲染结果。"""

    fig: object
    ax: object


@dataclass
class RenderConfig:
    """渲染显示选项（标题/端口显示）。

    将 render_layout 的显示类参数打包为 dataclass，降低函数参数个数。
    """

    title: str = "PoLaRIS Layout"
    show_ports: bool = True


# ---------------------------------------------------------------------------
# matplotlib 版图渲染
# ---------------------------------------------------------------------------
def _draw_congestion(ax: object, congestion: np.ndarray) -> None:
    """绘制拥塞热力图背景。"""
    import matplotlib.pyplot as plt

    im = ax.imshow(
        congestion,
        origin="lower",
        extent=[0, congestion.shape[1], 0, congestion.shape[0]],
        alpha=0.3,
        cmap="YlOrRd",
    )
    plt.colorbar(im, ax=ax, label="Congestion")


def _draw_ports(ax: object, pl: Placement) -> None:
    """绘制器件端口标记。"""
    ports = pl.port_positions()
    for _, (px, py) in ports.items():
        ax.plot(px, py, "r.", markersize=4)


def _draw_devices(ax: object, placements: dict[str, Placement], show_ports: bool) -> None:
    """绘制器件矩形、标签与端口标记。"""
    from matplotlib.patches import Rectangle

    cat_colors = {
        "passive": "#4C72B0",
        "active": "#DD8452",
        "source": "#55A868",
        "detector": "#C44E52",
    }
    for inst_id, pl in placements.items():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        w = xmax - xmin
        h = ymax - ymin
        color = cat_colors.get(pl.device.category, "#888888")
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
            _draw_ports(ax, pl)


def _draw_waveguides(ax: object, paths: dict[int, WaveguidePath]) -> None:
    """绘制波导路径折线。"""
    for wp in paths.values():
        if len(wp.points) >= 2:
            xs = [p[0] for p in wp.points]
            ys = [p[1] for p in wp.points]
            ax.plot(xs, ys, "g-", linewidth=1.5, alpha=0.8)


def _setup_axes(ax: object, title: str) -> None:
    """配置坐标轴样式与标题。"""
    ax.set_aspect("equal")
    ax.set_xlabel("X (μm)")
    ax.set_ylabel("Y (μm)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)


def render_layout(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    congestion: np.ndarray | None = None,
    save_path: str | None = None,
    **options: object,
) -> LayoutRender:
    """渲染版图（matplotlib）。

    显示类参数（title/show_ports）通过关键字参数传入，向后兼容
    ``title=``/``show_ports=`` 调用方式。

    Args:
        placements: 器件放置结果。
        paths: 波导路径（conn_idx -> WaveguidePath）。
        congestion: 拥塞热力图（可选叠加）。
        save_path: 保存路径（None 则不保存）。
        **options: 显示选项，支持 ``title`` 与 ``show_ports``。

    Returns:
        ``LayoutRender``（含 fig/ax）。
    """
    import matplotlib.pyplot as plt

    cfg = RenderConfig(
        title=str(options.get("title", RenderConfig.title)),
        show_ports=bool(options.get("show_ports", RenderConfig.show_ports)),
    )
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    if congestion is not None:
        _draw_congestion(ax, congestion)
    _draw_devices(ax, placements, cfg.show_ports)
    if paths:
        _draw_waveguides(ax, paths)
    _setup_axes(ax, cfg.title)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
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


def _define_layers(ly: object) -> tuple[dict[str, object], object, object]:
    """定义 GDS/OASIS 工艺层。

    Returns:
        (类别->层 映射, 波导层, 端口层)。
    """
    cat_layers = {
        "passive": ly.layer(1, 0),
        "active": ly.layer(2, 0),
        "source": ly.layer(3, 0),
        "detector": ly.layer(4, 0),
    }
    layer_waveguide = ly.layer(5, 0)
    layer_port = ly.layer(10, 0)
    return cat_layers, layer_waveguide, layer_port


def _insert_port_markers(top: object, pl: Placement, layer_port: object, dbu: float) -> None:
    """插入端口标记小矩形。"""
    import klayout.db as db

    ps = _um_to_dbu(0.5, dbu)
    for _, (px, py) in pl.port_positions().items():
        pbox = db.Box(
            _um_to_dbu(px, dbu) - ps,
            _um_to_dbu(py, dbu) - ps,
            _um_to_dbu(px, dbu) + ps,
            _um_to_dbu(py, dbu) + ps,
        )
        top.shapes(layer_port).insert(pbox)


def _insert_device_boxes(
    top: object,
    placements: dict[str, Placement],
    cat_layers: dict[str, object],
    dbu: float,
    layer_port: object | None = None,
) -> None:
    """插入器件矩形，可选附加端口标记。"""
    import klayout.db as db

    default_layer = cat_layers["passive"]
    for pl in placements.values():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        box = db.Box(
            _um_to_dbu(xmin, dbu),
            _um_to_dbu(ymin, dbu),
            _um_to_dbu(xmax, dbu),
            _um_to_dbu(ymax, dbu),
        )
        layer = cat_layers.get(pl.device.category, default_layer)
        top.shapes(layer).insert(box)
        if layer_port is not None:
            _insert_port_markers(top, pl, layer_port, dbu)


def _insert_waveguide_paths(
    top: object, paths: dict[int, WaveguidePath] | None, layer_waveguide: object
) -> None:
    """插入波导路径（多边形带宽度）。"""
    import klayout.db as db

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

    将器件矩形画到对应工艺层，波导画到布线层。

    Args:
        placements: 器件放置结果。
        paths: 波导路径。
        output_path: 输出 GDS 路径。
        dbu: database unit（μm，默认 1nm）。

    Returns:
        输出文件路径。
    """
    import klayout.db as db

    ly = db.Layout()
    ly.dbu = dbu
    top = ly.create_cell("TOP")
    cat_layers, layer_waveguide, layer_port = _define_layers(ly)
    _insert_device_boxes(top, placements, cat_layers, dbu, layer_port)
    _insert_waveguide_paths(top, paths, layer_waveguide)
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
    import klayout.db as db

    ly = db.Layout()
    ly.dbu = dbu
    top = ly.create_cell("TOP")
    cat_layers, layer_waveguide, _ = _define_layers(ly)
    _insert_device_boxes(top, placements, cat_layers, dbu)
    _insert_waveguide_paths(top, paths, layer_waveguide)
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


def _check_device_overlaps(
    pls: list[Placement], min_spacing_um: float
) -> tuple[int, int, list[str]]:
    """检查器件重叠与间距违规。

    Returns:
        (重叠违规数, 间距违规数, 详情列表)。
    """
    from shapely.geometry import box as shapely_box

    overlap = 0
    spacing = 0
    details: list[str] = []
    for i in range(len(pls)):
        a = pls[i].bbox_abs()
        sa = shapely_box(a[0], a[1], a[2], a[3])
        for j in range(i + 1, len(pls)):
            b = pls[j].bbox_abs()
            sb = shapely_box(b[0], b[1], b[2], b[3])
            if sa.intersects(sb):
                overlap += 1
                details.append(f"重叠: {pls[i].instance_id} & {pls[j].instance_id}")
            elif sa.distance(sb) < min_spacing_um:
                spacing += 1
                details.append(
                    f"间距不足: {pls[i].instance_id} & {pls[j].instance_id} "
                    f"距离 {sa.distance(sb):.3f}μm < {min_spacing_um}μm"
                )
    return overlap, spacing, details


def _check_bend_radius(
    paths: dict[int, WaveguidePath] | None, min_bend_radius_um: float
) -> tuple[int, list[str]]:
    """检查波导弯曲半径违规（简化：检测直角转弯段长）。

    Returns:
        (违规数, 详情列表)。
    """
    violations = 0
    details: list[str] = []
    if not paths:
        return violations, details
    for conn_idx, wp in paths.items():
        for i in range(1, len(wp.points) - 1):
            dx1 = wp.points[i][0] - wp.points[i - 1][0]
            dy1 = wp.points[i][1] - wp.points[i - 1][1]
            dx2 = wp.points[i + 1][0] - wp.points[i][0]
            dy2 = wp.points[i + 1][1] - wp.points[i][1]
            # 直线段（无转弯）跳过
            if abs(dx1 - dx2) <= 1e-9 and abs(dy1 - dy2) <= 1e-9:
                continue
            seg1_len = (dx1**2 + dy1**2) ** 0.5
            if seg1_len >= min_bend_radius_um:
                continue
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

    使用 shapely 几何运算检测器件重叠与间距违规，
    检查波导路径弯曲半径违规。

    工具来源: shapely https://shapely.readthedocs.io/
    """
    pls = list(placements.values())
    overlap, spacing, overlap_details = _check_device_overlaps(pls, min_spacing_um)
    bend_violations, bend_details = _check_bend_radius(paths, min_bend_radius_um)
    return DRCReport(
        overlap_violations=overlap,
        spacing_violations=spacing,
        min_bend_radius_violations=bend_violations,
        details=[*overlap_details, *bend_details],
    )
