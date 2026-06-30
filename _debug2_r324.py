"""R324 调试 2: 验证 transform 后 begin_shapes_rec 的行为。"""
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
src = Path("/workspace/_debug2_r324.gds")
export_gdsii_from_cells(cells_spec, src)

ly = db.Layout()
ly.read(str(src))
top = ly.cell(int(list(ly.each_top_cell())[0]))
dbu = float(ly.dbu)

print(f"dbu = {dbu}")

# 变换前
print("\n=== 变换前 ===")
print(f"TOP.bbox() = {top.bbox()} (dbu) = ({float(top.bbox().left)*dbu}, {float(top.bbox().bottom)*dbu})-({float(top.bbox().right)*dbu}, {float(top.bbox().top)*dbu}) μm")
print(f"TOP.dbbox() = {top.dbbox()} (μm)")

# 遍历所有 shapes 看 bbox
print("遍历 shapes:")
for li in ly.layer_indices():
    info = ly.get_info(li)
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        box = shape.bbox()
        print(f"  layer {info.layer}/{info.datatype}: shape.bbox = {box} dbu = ({float(box.left)*dbu},{float(box.bottom)*dbu})-({float(box.right)*dbu},{float(box.top)*dbu}) μm, cell={it.cell().name}")
        it.next()

# 应用变换
trans = db.DCplxTrans(1.0, 0.0, False, 100.0, 50.0)
top.transform(trans)

print("\n=== 变换后 ===")
print(f"TOP.bbox() = {top.bbox()} (dbu) = ({float(top.bbox().left)*dbu}, {float(top.bbox().bottom)*dbu})-({float(top.bbox().right)*dbu}, {float(top.bbox().top)*dbu}) μm")
print(f"TOP.dbbox() = {top.dbbox()} (μm)")
print("遍历 shapes:")
for li in ly.layer_indices():
    info = ly.get_info(li)
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        box = shape.bbox()
        print(f"  layer {info.layer}/{info.datatype}: shape.bbox = {box} dbu = ({float(box.left)*dbu},{float(box.bottom)*dbu})-({float(box.right)*dbu},{float(box.top)*dbu}) μm, cell={it.cell().name}")
        it.next()
print("instances:")
for inst in top.each_inst():
    print(f"  inst: cell={ly.cell(inst.cell_index).name}, cplx_trans={inst.cplx_trans}")

# CHILD cell 的内容是否被变换？
print("\n=== CHILD cell 内容 ===")
child = ly.cell("CHILD")
print(f"CHILD.bbox() = {child.bbox()} dbu = ({float(child.bbox().left)*dbu},{float(child.bbox().bottom)*dbu})-({float(child.bbox().right)*dbu},{float(child.bbox().top)*dbu}) μm")
