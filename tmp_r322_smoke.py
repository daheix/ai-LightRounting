"""R322 冒烟测试: 验证 KLayout cell hierarchy API 调用。"""
import sys
sys.path.insert(0, "/workspace/src")

import klayout.db as db
from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
import tempfile, os

# 创建含层级 cell 的 GDSII: TOP -> CHILD_A, CHILD_B; CHILD_A -> CHILD_B
tmp = tempfile.mkdtemp()
cells_spec = [
    {
        "name": "CHILD_B",
        "polygons": [
            {"layer": 1, "datatype": 0, "points": [[0, 0], [2, 0], [2, 2], [0, 2]]},
        ],
        "is_top": False,
    },
    {
        "name": "CHILD_A",
        "polygons": [
            {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
        ],
        "instances": [
            {"cell_name": "CHILD_B", "x": 10, "y": 10},
        ],
        "is_top": False,
    },
    {
        "name": "TOP",
        "polygons": [],
        "instances": [
            {"cell_name": "CHILD_A", "x": 0, "y": 0},
            {"cell_name": "CHILD_B", "x": 20, "y": 20},
        ],
        "is_top": True,
    },
]
out = os.path.join(tmp, "hier.gds")
export_gdsii_from_cells(cells_spec, out)
print(f"GDSII written: {out}")

# 用 KLayout 直接读取验证 API
ly = db.Layout()
ly.read(out)
print(f"dbu: {ly.dbu}")
print(f"top cells: {[ly.cell(int(ci)).name for ci in ly.each_top_cell()]}")
# each_cell 返回 Cell 对象
print(f"all cells: {[cell.name for cell in ly.each_cell()]}")
for cell in ly.each_cell():
    print(f"  cell {cell.name} (idx={int(cell.cell_index())}):")
    print(f"    hierarchy_levels: {int(cell.hierarchy_levels())}")
    print(f"    child_cells: {[ly.cell(int(c)).name for c in cell.each_child_cell()]}")
    print(f"    parent_cells: {[ly.cell(int(p)).name for p in cell.each_parent_cell()]}")
    print(f"    instances:")
    for inst in cell.each_inst():
        child_name = ly.cell(int(inst.cell_index)).name
        try:
            sx = int(inst.size_x)
            sy = int(inst.size_y)
        except Exception as e:
            sx = -1
            sy = -1
            print(f"      size_x/size_y error: {e}")
        print(f"      -> {child_name} (size_x={sx}, size_y={sy})")

# 测试 analyze_cell_hierarchy
print("\n=== analyze_cell_hierarchy ===")
from polaris.verification.gdsii_cell_hierarchy_analyzer import (
    analyze_cell_hierarchy,
)
report = analyze_cell_hierarchy(out)
print(f"file: {report.file_path}")
print(f"top cells: {report.top_cell_names}")
print(f"total cells: {report.total_cell_count}")
print(f"max depth: {report.max_hierarchy_depth}")
print(f"circular: {report.has_circular_reference}")
print("cells:")
for c in report.cells:
    print(f"  {c.cell_name}: depth={c.hierarchy_depth}, top={c.is_top_cell}, "
          f"direct={c.direct_instance_count}, recursive={c.recursive_instance_count}, "
          f"parents={c.parent_cell_names}, children={c.child_cell_names}")
