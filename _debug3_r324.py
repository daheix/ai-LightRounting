"""R324 调试 3: 验证 it.trans() 与 begin_shapes_rec 的世界坐标。"""
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
src = Path("/workspace/_debug3_r324.gds")
export_gdsii_from_cells(cells_spec, src)

ly = db.Layout()
ly.read(str(src))
top = ly.cell(int(list(ly.each_top_cell())[0]))
dbu = float(ly.dbu)

# 变换前看 it.trans()
print("=== 变换前 ===")
for li in ly.layer_indices():
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        local = shape.bbox()
        trans = it.trans()
        world = trans * local
        print(f"  cell={it.cell().name}, local={local}, trans={trans}, world={world}")
        it.next()

# 应用变换
print("\n=== 变换后 ===")
trans_t = db.DCplxTrans(1.0, 0.0, False, 100.0, 50.0)
top.transform(trans_t)
for li in ly.layer_indices():
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        local = shape.bbox()
        trans = it.trans()
        world = trans * local
        print(f"  cell={it.cell().name}, local={local}, trans={trans}, world={world}")
        it.next()

# instances
print("\ninstances:")
for inst in top.each_inst():
    print(f"  cell={ly.cell(inst.cell_index).name}, cplx_trans={inst.cplx_trans}")
