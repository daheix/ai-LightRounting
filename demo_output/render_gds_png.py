"""用 KLayout 渲染 GDS 版图为 PNG 成品图。"""
import klayout.db as db
import klayout.rdb as rdb
import os
from pathlib import Path

GDS_DIR = Path("demo_output/gds")
OUT = Path("demo_output/figures")
OUT.mkdir(exist_ok=True)

gds_files = ["MZI.gds", "Clements_4x4.gds", "Quantum_BosonSampling.gds"]

for gds_name in gds_files:
    gds_path = GDS_DIR / gds_name
    if not gds_path.exists():
        print(f"[SKIP] {gds_name} not found")
        continue
    # 加载 GDS
    ly = db.Layout()
    ly.read(str(gds_path))
    # 获取顶层 cell
    top_cells = ly.top_cells()
    if not top_cells:
        print(f"[SKIP] {gds_name} no top cell")
        continue
    top = top_cells[0]
    # 获取版图边界
    bbox = top.bbox()
    print(f"[INFO] {gds_name}: cell={top.name}, bbox={bbox}, layers={ly.layer_infos()}")
    # 渲染成 PNG
    png_name = gds_name.replace(".gds", "_layout.png")
    png_path = OUT / png_name
    try:
        # KLayout 渲染 API
        view = db.LayoutToImage()
        view.layout = ly
        view.cell = top
        view.width = 2000
        view.height = 1500
        view.render(str(png_path))
        print(f"[OK] {png_name}")
    except Exception as e:
        print(f"[WARN] LayoutToImage failed: {e}, trying alternative...")
        try:
            # 替代方案：用 PixelRenderer
            img = db.LayoutToImage().render(ly, top, 2000, 1500)
            img.save(str(png_path))
            print(f"[OK] {png_name} (alt)")
        except Exception as e2:
            print(f"[ERROR] {gds_name} render failed: {e2}")
            # 最终方案：用 matplotlib 手动绘制 GDS 多边形
            render_with_matplotlib(ly, top, png_path, gds_name)

def render_with_matplotlib(ly, top_cell, png_path, title):
    """用 matplotlib 手动绘制 GDS 多边形作为最终方案。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon
    from matplotlib.collections import PatchCollection
    import numpy as np

    fig, ax = plt.subplots(figsize=(14, 10))
    colors = plt.cm.tab20(np.linspace(0, 1, 20))
    layer_color_map = {}
    polygons = []
    color_idx = 0

    # 递归遍历所有多边形
    def collect_polygons(cell, trans):
        nonlocal color_idx
        # 遍历多边形
        for i in range(cell.shapes()):
            layer = cell.layer(i)
            if layer not in layer_color_map:
                layer_color_map[layer] = colors[color_idx % 20]
                color_idx += 1
            shape_iter = cell.shapes(layer).each()
            for shape in shape_iter:
                if shape.is_polygon():
                    poly = shape.polygon
                    pts = [(p.x * trans.disp.x + trans.mag * p.x,
                            p.y * trans.disp.y + trans.mag * p.y) for p in poly.each_point()]
                    if len(pts) >= 3:
                        polygons.append((pts, layer_color_map[layer]))
                elif shape.is_path():
                    path = shape.path
                    pts = [(p.x, p.y) for p in path.each_point()]
                    if len(pts) >= 2:
                        ax.plot([p[0] for p in pts], [p[1] for p in pts],
                                "-", color=layer_color_map[layer], linewidth=1.5)
        # 递归子 cell
        for ci in range(cell.child_instances()):
            inst = cell.child_inst(ci)
            child = inst.cell
            child_trans = trans * inst.complex_trans
            collect_polygons(child, child_trans)

    # 简化：直接遍历顶层 cell 的多边形
    for i in range(top_cell.shapes()):
        layer = top_cell.layer(i)
        if layer not in layer_color_map:
            layer_color_map[layer] = colors[color_idx % 20]
            color_idx += 1
        try:
            shape_iter = top_cell.shapes(layer).each()
            for shape in shape_iter:
                if shape.is_polygon():
                    poly = shape.polygon
                    pts = [(p.x, p.y) for p in poly.each_point()]
                    if len(pts) >= 3:
                        mpl_poly = MplPolygon(pts, closed=True)
                        ax.add_patch(mpl_poly)
                        ax.fill([p[0] for p in pts], [p[1] for p in pts],
                                color=layer_color_map[layer], alpha=0.7)
                elif shape.is_path():
                    path = shape.path
                    pts = [(p.x, p.y) for p in path.each_point()]
                    if len(pts) >= 2:
                        ax.plot([p[0] for p in pts], [p[1] for p in pts],
                                "-", color=layer_color_map[layer], linewidth=2)
        except Exception as e:
            print(f"  shape iter error: {e}")

    # 递归子实例
    for ci in range(top_cell.child_instances()):
        inst = top_cell.child_inst(ci)
        child = inst.cell
        ctrans = inst.complex_trans
        for j in range(child.shapes()):
            layer = child.layer(j)
            if layer not in layer_color_map:
                layer_color_map[layer] = colors[color_idx % 20]
                color_idx += 1
            try:
                for shape in child.shapes(layer).each():
                    if shape.is_polygon():
                        poly = shape.polygon
                        pts = [(p.x * ctrans.mag + ctrans.disp.x,
                                p.y * ctrans.mag + ctrans.disp.y) for p in poly.each_point()]
                        if len(pts) >= 3:
                            ax.fill([p[0] for p in pts], [p[1] for p in pts],
                                    color=layer_color_map[layer], alpha=0.7)
                    elif shape.is_path():
                        path = shape.path
                        pts = [(p.x * ctrans.mag + ctrans.disp.x,
                                p.y * ctrans.mag + ctrans.disp.y) for p in path.each_point()]
                        if len(pts) >= 2:
                            ax.plot([p[0] for p in pts], [p[1] for p in pts],
                                    "-", color=layer_color_map[layer], linewidth=2)
            except Exception:
                pass

    ax.set_aspect("equal")
    ax.set_title(f"GDS Layout: {title}", fontsize=14, fontweight="bold")
    ax.set_xlabel("X (DBU)")
    ax.set_ylabel("Y (DBU)")
    ax.grid(True, alpha=0.3)
    ax.relim()
    ax.autoscale_view()
    fig.tight_layout()
    fig.savefig(str(png_path), dpi=150)
    plt.close(fig)
    print(f"[OK] {png_path.name} (matplotlib render, {len(polygons)} polygons)")

print("\nDone!")
