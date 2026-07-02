"""用 KLayout 读取 GDS 几何数据 + matplotlib 渲染版图 PNG 成品图。

修复 v2:
- 移除 cell.has_shapes() (KLayout Cell 无此方法)
- 用 cell.shapes(li).each() 直接遍历
- 用 inst.cplx_trans 获取实例变换（KLayout 正确属性）
- 用 db.ICplxTrans 处理变换矩阵
- 直接用 shape.polygon / shape.path / shape.text 属性
"""
import klayout.db as db
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

GDS_DIR = Path("demo_output/gds")
OUT = Path("demo_output/figures")
OUT.mkdir(exist_ok=True)
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def render_gds(gds_path: Path, png_path: Path, title: str):
    """读取 GDS 用 matplotlib 渲染成 PNG 成品图。"""
    ly = db.Layout()
    ly.read(str(gds_path))
    top = ly.top_cells()[0]
    bbox = top.bbox()
    layer_infos = list(ly.layer_infos())
    print(f"  cell={top.name}, bbox={bbox}, layers={[str(li) for li in layer_infos]}")

    fig, ax = plt.subplots(figsize=(16, 11))
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    layer_color = {}
    color_idx = [0]
    n_poly = [0]
    n_path = [0]
    n_text = [0]
    n_box = [0]

    def get_color(layer_name):
        if layer_name not in layer_color:
            layer_color[layer_name] = colors[color_idx[0] % 10]
            color_idx[0] += 1
        return layer_color[layer_name]

    def transform_point(p, cplx_trans):
        """应用复变换到点。"""
        tp = cplx_trans.trans(p)
        return (tp.x, tp.y)

    def draw_shapes(cell, cplx_trans):
        """递归绘制 cell 的所有图形。"""
        for li in layer_infos:
            layer_name = f"{li.layer}/{li.datatype}"
            shapes = cell.shapes(li)
            shape_count = 0
            for shape in shapes.each():
                shape_count += 1
            if shape_count == 0:
                continue
            color = get_color(layer_name)
            for shape in shapes.each():
                if shape.is_polygon():
                    poly = shape.polygon
                    pts = []
                    for p in poly.each_point():
                        tp = cplx_trans.trans(p)
                        pts.append((tp.x, tp.y))
                    if len(pts) >= 3:
                        ax.fill([p[0] for p in pts], [p[1] for p in pts],
                                color=color, alpha=0.75, edgecolor=color, linewidth=0.5)
                        n_poly[0] += 1
                elif shape.is_path():
                    path = shape.path
                    pts = []
                    for p in path.each_point():
                        tp = cplx_trans.trans(p)
                        pts.append((tp.x, tp.y))
                    if len(pts) >= 2:
                        ax.plot([p[0] for p in pts], [p[1] for p in pts],
                                "-", color=color, linewidth=2.5, alpha=0.9)
                        n_path[0] += 1
                elif shape.is_box():
                    box = shape.box
                    p1 = cplx_trans.trans(box.p1)
                    p2 = cplx_trans.trans(box.p2)
                    rect_x = [p1.x, p2.x, p2.x, p1.x]
                    rect_y = [p1.y, p1.y, p2.y, p2.y]
                    ax.fill(rect_x, rect_y, color=color, alpha=0.65,
                            edgecolor=color, linewidth=0.8)
                    n_box[0] += 1
                elif shape.is_text():
                    text = shape.text
                    tp = cplx_trans.trans(text)
                    ax.text(tp.x, tp.y, text.string, fontsize=5, ha="center", va="center",
                            color="black", fontweight="bold")
                    n_text[0] += 1

        # 递归子实例
        for inst in cell.each_inst():
            child = inst.cell
            # 实例的复变换 = 父变换 * 实例本地变换
            child_trans = cplx_trans * inst.cplx_trans
            draw_shapes(child, child_trans)

    # 从顶层开始绘制
    identity = db.ICplxTrans(1.0)
    draw_shapes(top, identity)

    # 图例
    handles = []
    for lname, col in sorted(layer_color.items()):
        handles.append(plt.Rectangle((0, 0), 1, 1, fc=col, alpha=0.75,
                                      label=f"Layer {lname}"))
    if handles:
        ax.legend(handles=handles, loc="upper right", fontsize=8)

    ax.set_aspect("equal")
    ax.set_title(f"GDS Layout Final Product: {title}\n"
                 f"({n_poly[0]} polygons, {n_box[0]} boxes, {n_path[0]} paths, "
                 f"{n_text[0]} texts, bbox={bbox.width}x{bbox.height} DBU)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("X (DBU)")
    ax.set_ylabel("Y (DBU)")
    ax.grid(True, alpha=0.3)
    ax.relim()
    ax.autoscale_view()
    fig.tight_layout()
    fig.savefig(str(png_path), dpi=150)
    plt.close(fig)
    print(f"  [OK] {png_path.name} ({n_poly[0]} polygons, {n_box[0]} boxes, {n_path[0]} paths, {n_text[0]} texts)")


def main():
    print("=" * 60)
    print("GDS Layout Rendering - Final Product PNG")
    print("=" * 60)
    gds_files = [
        ("MZI.gds", "07_mzi_layout.png", "MZI Mach-Zehnder Interferometer"),
        ("Clements_4x4.gds", "08_clements_4x4_layout.png", "Clements 4x4 Optical Matrix"),
        ("Quantum_BosonSampling.gds", "09_quantum_boson_sampling_layout.png",
         "Quantum Boson Sampling Circuit"),
    ]
    for gds_name, png_name, title in gds_files:
        gds_path = GDS_DIR / gds_name
        png_path = OUT / png_name
        if not gds_path.exists():
            print(f"[SKIP] {gds_name} not found")
            continue
        print(f"\nRendering {gds_name} -> {png_name}")
        try:
            render_gds(gds_path, png_path, title)
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()

    # 合并 3 张图为一张总图
    print("\n=== Generating combined layout image ===")
    import matplotlib.image as mpimg
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    for ax, (_, png_name, title) in zip(axes, gds_files):
        png_path = OUT / png_name
        if png_path.exists():
            img = mpimg.imread(str(png_path))
            ax.imshow(img)
            ax.set_title(title, fontsize=12, fontweight="bold")
        ax.axis("off")
    fig.suptitle("PoLaRIS v5.0 - Final GDS Layout Products (3 Circuits)",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(str(OUT / "10_all_layouts_combined.png"), dpi=150)
    plt.close(fig)
    print(f"[OK] 10_all_layouts_combined.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
