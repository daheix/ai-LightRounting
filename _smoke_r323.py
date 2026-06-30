"""R323 冒烟测试：验证 KLayout Text 提取 API 行为。"""
from pathlib import Path
import sys
sys.path.insert(0, "/workspace/src")

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells

# 构造含 TEXT 元素的 GDSII
cells_spec = [
    {
        "name": "TOP",
        "polygons": [
            {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
        ],
        "texts": [
            {"layer": 10, "datatype": 0, "string": "device_MZI_1", "x": 5.0, "y": 2.5},
            {"layer": 11, "datatype": 0, "string": "pin_in", "x": 0.0, "y": 2.5},
            {"layer": 11, "datatype": 0, "string": "pin_out", "x": 10.0, "y": 2.5},
        ],
        "is_top": True,
    }
]
out = Path("/workspace/_smoke_r323.gds")
export_gdsii_from_cells(cells_spec, out)
print(f"GDSII 已生成: {out}")

# 加载并提取
import klayout.db as db
ly = db.Layout()
ly.read(str(out))
print(f"dbu = {ly.dbu} μm")
print(f"layer_indices = {list(ly.layer_indices())}")
for li in ly.layer_indices():
    info = ly.get_info(li)
    print(f"  layer_index={li} layer={info.layer} datatype={info.datatype}")

# 找 top cell
top_cells = [ly.cell(int(ci)) for ci in ly.each_top_cell()]
print(f"top_cells = {[c.name for c in top_cells]}")
top = top_cells[0]

# 遍历每个层找 text
for li in ly.layer_indices():
    info = ly.get_info(li)
    print(f"\n=== 层 {info.layer}/{info.datatype} ===")
    it = top.begin_shapes_rec(li)
    count = 0
    while not it.at_end():
        shape = it.shape()
        if shape.is_text():
            text_str = str(shape.text_string)
            pos = shape.text_pos
            cell_obj = it.cell()
            cell_name = str(cell_obj.name)
            print(f"  TEXT: '{text_str}' pos=({pos.x},{pos.y}) cell={cell_name}")
            print(f"    pos type = {type(pos).__name__}")
            print(f"    x_um = {float(pos.x) * float(ly.dbu)}")
            count += 1
        else:
            print(f"  non-text shape: {shape}")
        it.next()
    print(f"  共 {count} 个 text")
