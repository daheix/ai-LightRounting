"""R324 调试: Cell.transform 对子实例的影响。"""
from pathlib import Path
import sys
sys.path.insert(0, "/workspace/src")

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
import klayout.db as db

cells_spec = [
    {
        "name": "CHILD",
        "polygons": [
            {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 3], [0, 3]]},
        ],
        "is_top": False,
    },
    {
        "name": "TOP",
        "polygons": [
            {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
        ],
        "instances": [
            {"cell_name": "CHILD", "x": 20.0, "y": 0.0, "rotation": 0.0},
        ],
        "is_top": True,
    }
]
src = Path("/workspace/_debug_r324.gds")
export_gdsii_from_cells(cells_spec, src)

ly = db.Layout()
ly.read(str(src))
top = ly.cell(int(list(ly.each_top_cell())[0]))

# 变换前 bbox
print("变换前:")
print(f"  TOP bbox = {top.bbox()}")
print(f"  TOP dbbox = {top.dbbox()}")
# 列出 TOP 的 instances
for inst in top.each_inst():
    print(f"  Instance: cell_index={inst.cell_index}, name={ly.cell(inst.cell_index).name}")
    print(f"    cplx_trans = {inst.cplx_trans}")
    print(f"    trans = {inst.trans}")

# 尝试 1: Cell.transform
print("\n=== 尝试 Cell.transform(trans) ===")
trans = db.DCplxTrans(1.0, 0.0, False, 100.0, 50.0)
top.transform(trans)
print(f"  变换后 TOP bbox = {top.bbox()}")
print(f"  变换后 TOP dbbox = {top.dbbox()}")
for inst in top.each_inst():
    print(f"  Instance: cell_index={inst.cell_index}, name={ly.cell(inst.cell_index).name}")
    print(f"    cplx_trans = {inst.cplx_trans}")
    print(f"    trans = {inst.trans}")

# 重新读取
print("\n=== 重新读取 ===")
ly2 = db.Layout()
ly2.read(str(src))
top2 = ly2.cell(int(list(ly2.each_top_cell())[0]))
print(f"  原 TOP bbox = {top2.bbox()}")
print(f"  原 TOP dbbox = {top2.dbbox()}")
for inst in top2.each_inst():
    print(f"  Instance: cell_index={inst.cell_index}, name={ly2.cell(inst.cell_index).name}")
    print(f"    cplx_trans = {inst.cplx_trans}")
