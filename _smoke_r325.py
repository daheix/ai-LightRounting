"""R325 冒烟测试: 验证 KLayout 多边形顶点提取 API。"""
from pathlib import Path
import sys
sys.path.insert(0, "/workspace/src")

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
import klayout.db as db

# 含 on-grid 和 off-grid 顶点的 GDSII
# on-grid: 0.001μm grid, 所有点都是 1000 的倍数 dbu
# off-grid: 加一个 1500 dbu 的点（0.15μm，不在 0.001μm grid 上？实际 1500 是 0.001 的倍数）
# 用 0.005μm grid 测试: 5000 dbu = 5μm on-grid, 1500 dbu = 1.5μm 不在 5μm grid
cells_spec = [
    {
        "name": "TOP",
        "polygons": [
            # 矩形 (0,0)-(10,5) μm = (0,0)-(10000,5000) dbu，全 on-grid for 1nm grid
            {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            # 含 off-grid 顶点的多边形: (0.0015, 0) 不在 0.001μm grid... 实际 1.5nm 在 1nm grid 上是 off-grid
            # 但 export 用 int(x/dbu) 会截断，所以用 0.0015 → int(1.5) = 1 dbu，是 on-grid
            # 改用更大的 off-grid: 0.007 μm = 7 dbu，在 5nm grid 上 off-grid
            {"layer": 2, "datatype": 0, "points": [[0, 0], [0.007, 0], [0.007, 0.007], [0, 0.007]]},
        ],
        "is_top": True,
    }
]
src = Path("/workspace/_smoke_r325.gds")
export_gdsii_from_cells(cells_spec, src)

ly = db.Layout()
ly.read(str(src))
top = ly.cell(int(list(ly.each_top_cell())[0]))
dbu = float(ly.dbu)
print(f"dbu = {dbu} μm")

# 遍历 polygons 提取顶点
for li in ly.layer_indices():
    info = ly.get_info(li)
    print(f"\n=== 层 {info.layer}/{info.datatype} ===")
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        if shape.is_polygon():
            poly = shape.polygon()
            print(f"  Polygon: {poly}")
            # 遍历顶点
            for i in range(poly.num_points()):
                pt = poly.point(i)
                x_dbu = int(pt.x)
                y_dbu = int(pt.y)
                x_um = float(pt.x) * dbu
                y_um = float(pt.y) * dbu
                print(f"    point {i}: ({x_dbu}, {y_dbu}) dbu = ({x_um}, {y_um}) μm")
        elif shape.is_box():
            box = shape.bbox()
            print(f"  Box: {box}")
            # box 的 4 个角
            corners = [(box.left, box.bottom), (box.right, box.bottom), (box.right, box.top), (box.left, box.top)]
            for cx, cy in corners:
                print(f"    corner: ({cx}, {cy}) dbu = ({float(cx)*dbu}, {float(cy)*dbu}) μm")
        it.next()

# 测试 grid check 逻辑
print("\n=== Grid Check (grid=0.005μm = 5nm = 5 dbu) ===")
grid_um = 0.005
grid_dbu = int(round(grid_um / dbu))
print(f"grid = {grid_um} μm = {grid_dbu} dbu")
for li in ly.layer_indices():
    info = ly.get_info(li)
    print(f"\n层 {info.layer}/{info.datatype}:")
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        if shape.is_polygon():
            poly = shape.polygon()
            for i in range(poly.num_points()):
                pt = poly.point(i)
                x_dbu = int(pt.x)
                y_dbu = int(pt.y)
                x_off = x_dbu % grid_dbu
                y_off = y_dbu % grid_dbu
                if x_off != 0 or y_off != 0:
                    print(f"  OFF-GRID point {i}: ({x_dbu}, {y_dbu}) dbu, off=({x_off}, {y_off})")
        elif shape.is_box():
            box = shape.bbox()
            corners = [(box.left, box.bottom), (box.right, box.bottom), (box.right, box.top), (box.left, box.top)]
            for cx, cy in corners:
                x_off = int(cx) % grid_dbu
                y_off = int(cy) % grid_dbu
                if x_off != 0 or y_off != 0:
                    print(f"  OFF-GRID corner: ({cx}, {cy}) dbu, off=({x_off}, {y_off})")
        it.next()
