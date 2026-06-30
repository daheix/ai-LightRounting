"""R324 调试 4: 验证 export_gdsii_from_cells 的实例 placement 单位。"""
from pathlib import Path
import sys
sys.path.insert(0, "/workspace/src")

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
import klayout.db as db

# 单个测试: x=20.0 μm
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
src = Path("/workspace/_debug4_r324.gds")
export_gdsii_from_cells(cells_spec, src)

ly = db.Layout()
ly.read(str(src))
top = ly.cell(int(list(ly.each_top_cell())[0]))
dbu = float(ly.dbu)
print(f"dbu = {dbu} μm")

for inst in top.each_inst():
    print(f"\nInstance: cell={ly.cell(inst.cell_index).name}")
    print(f"  cplx_trans (ICplxTrans, dbu) = {inst.cplx_trans}")
    print(f"  dcplx_trans (DCplxTrans, μm) = {inst.dcplx_trans}")
    print(f"  trans (Trans, dbu) = {inst.trans}")

# 用 ICplxTrans 的实际值验证
ct = inst.cplx_trans
print(f"\nICplxTrans 详情:")
print(f"  mag = {ct.mag}")
print(f"  angle = {ct.angle}")
print(f"  mirror = {ct.is_mirror}")
print(f"  disp (Vector dbu) = ({ct.disp.x}, {ct.disp.y})")
print(f"  disp (μm) = ({float(ct.disp.x) * dbu}, {float(ct.disp.y) * dbu})")
