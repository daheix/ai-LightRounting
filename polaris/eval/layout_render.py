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


def render_layout(
    placements: dict[str, Placement],
    paths: dict[int, WaveguidePath] | None = None,
    congestion: np.ndarray | None = None,
    title: str = "PoLaRIS Layout",
    show_ports: bool = True,
    save_path: str | None = None,
) -> LayoutRender:
    """渲染版图（matplotlib）。

    Args:
        placements: 器件放置结果。
        paths: 波导路径（conn_idx -> WaveguidePath）。
        congestion: 拥塞热力图（可选叠加）。
        title: 图标题。
        show_ports: 是否标记端口位置。
        save_path: 保存路径（None 则不保存）。

    Returns:
        ``LayoutRender``（含 fig/ax）。
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    # 拥塞热力图背景
    if congestion is not None:
        im = ax.imshow(
            congestion,
            origin="lower",
            extent=[0, congestion.shape[1], 0, congestion.shape[0]],
            alpha=0.3,
            cmap="YlOrRd",
        )
        plt.colorbar(im, ax=ax, label="Congestion")

    # 器件矩形
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
            (xmin, ymin), w, h,
            linewidth=1, edgecolor="black", facecolor=color, alpha=0.7,
        )
        ax.add_patch(rect)
        ax.text(
            xmin + w / 2, ymin + h / 2, inst_id,
            ha="center", va="center", fontsize=7, rotation=45,
        )
        # 端口标记
        if show_ports:
            ports = pl.port_positions()
            for _, (px, py) in ports.items():
                ax.plot(px, py, "r.", markersize=4)

    # 波导路径
    if paths:
        for wp in paths.values():
            if len(wp.points) >= 2:
                xs = [p[0] for p in wp.points]
                ys = [p[1] for p in wp.points]
                ax.plot(xs, ys, "g-", linewidth=1.5, alpha=0.8)

    ax.set_aspect("equal")
    ax.set_xlabel("X (μm)")
    ax.set_ylabel("Y (μm)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
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

    # 层定义（按平台/类别）
    layer_passive = ly.layer(1, 0)  # GDS layer 1 datatype 0
    layer_active = ly.layer(2, 0)
    layer_source = ly.layer(3, 0)
    layer_detector = ly.layer(4, 0)
    layer_waveguide = ly.layer(5, 0)
    layer_port = ly.layer(10, 0)

    cat_layers = {
        "passive": layer_passive,
        "active": layer_active,
        "source": layer_source,
        "detector": layer_detector,
    }

    # 器件矩形
    for pl in placements.values():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        x0 = _um_to_dbu(xmin, dbu)
        y0 = _um_to_dbu(ymin, dbu)
        x1 = _um_to_dbu(xmax, dbu)
        y1 = _um_to_dbu(ymax, dbu)
        layer = cat_layers.get(pl.device.category, layer_passive)
        box = db.Box(x0, y0, x1, y1)
        top.shapes(layer).insert(box)
        # 端口标记（小矩形）
        for _, (px, py) in pl.port_positions().items():
            ps = _um_to_dbu(0.5, dbu)
            pbox = db.Box(
                _um_to_dbu(px, dbu) - ps,
                _um_to_dbu(py, dbu) - ps,
                _um_to_dbu(px, dbu) + ps,
                _um_to_dbu(py, dbu) + ps,
            )
            top.shapes(layer_port).insert(pbox)

    # 波导路径（多边形带宽度）
    if paths:
        for wp in paths.values():
            if len(wp.points) < 2:
                continue
            pts = [
                db.DPoint(p[0], p[1]) for p in wp.points
            ]
            path = db.DPath(pts, 0.5)  # 0.5μm 宽
            top.shapes(layer_waveguide).insert(path)

    # 写入 GDS
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

    layer_passive = ly.layer(1, 0)
    layer_active = ly.layer(2, 0)
    layer_source = ly.layer(3, 0)
    layer_detector = ly.layer(4, 0)
    layer_waveguide = ly.layer(5, 0)
    cat_layers = {
        "passive": layer_passive,
        "active": layer_active,
        "source": layer_source,
        "detector": layer_detector,
    }

    for pl in placements.values():
        xmin, ymin, xmax, ymax = pl.bbox_abs()
        box = db.Box(
            _um_to_dbu(xmin, dbu), _um_to_dbu(ymin, dbu),
            _um_to_dbu(xmax, dbu), _um_to_dbu(ymax, dbu),
        )
        layer = cat_layers.get(pl.device.category, layer_passive)
        top.shapes(layer).insert(box)

    if paths:
        for wp in paths.values():
            if len(wp.points) < 2:
                continue
            pts = [db.DPoint(p[0], p[1]) for p in wp.points]
            path = db.DPath(pts, 0.5)
            top.shapes(layer_waveguide).insert(path)

    # OASIS 写入
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
        return (
            self.overlap_violations
            + self.spacing_violations
            + self.min_bend_radius_violations
        )

    @property
    def passed(self) -> bool:
        return self.total_violations == 0


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
    from shapely.geometry import box as shapely_box

    report = DRCReport()
    # 器件重叠检查
    pls = list(placements.values())
    for i in range(len(pls)):
        a = pls[i].bbox_abs()
        sa = shapely_box(a[0], a[1], a[2], a[3])
        for j in range(i + 1, len(pls)):
            b = pls[j].bbox_abs()
            sb = shapely_box(b[0], b[1], b[2], b[3])
            if sa.intersects(sb):
                report.overlap_violations += 1
                report.details.append(
                    f"重叠: {pls[i].instance_id} & {pls[j].instance_id}"
                )
            elif sa.distance(sb) < min_spacing_um:
                report.spacing_violations += 1
                report.details.append(
                    f"间距不足: {pls[i].instance_id} & {pls[j].instance_id} "
                    f"距离 {sa.distance(sb):.3f}μm < {min_spacing_um}μm"
                )
    # 弯曲半径检查（简化：检测直角转弯）
    if paths:
        for conn_idx, wp in paths.items():
            for i in range(1, len(wp.points) - 1):
                dx1 = wp.points[i][0] - wp.points[i - 1][0]
                dy1 = wp.points[i][1] - wp.points[i - 1][1]
                dx2 = wp.points[i + 1][0] - wp.points[i][0]
                dy2 = wp.points[i + 1][1] - wp.points[i][1]
                if abs(dx1 - dx2) > 1e-9 or abs(dy1 - dy2) > 1e-9:
                    # 转弯，检查是否满足弯曲半径（简化：标记为需检查）
                    seg1_len = (dx1 ** 2 + dy1 ** 2) ** 0.5
                    if seg1_len < min_bend_radius_um:
                        report.min_bend_radius_violations += 1
                        report.details.append(
                            f"弯曲半径不足: 连接 {conn_idx} 在 {wp.points[i]} "
                            f"段长 {seg1_len:.3f}μm < {min_bend_radius_um}μm"
                        )
    return report
