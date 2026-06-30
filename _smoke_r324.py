"""R324 冒烟测试: 验证 KLayout Cell.transform API。"""
from pathlib import Path
import sys
sys.path.insert(0, "/workspace/src")

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells

# 构造测试 GDSII
cells_spec = [
    {
        "name": "TOP",
        "polygons": [
            {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
        ],
        "texts": [
            {"layer": 10, "datatype": 0, "string": "lbl", "x": 5.0, "y": 2.5},
        ],
        "is_top": True,
    }
]
src = Path("/workspace/_smoke_r324_src.gds")
export_gdsii_from_cells(cells_spec, src)
print(f"源 GDSII: {src}")

import klayout.db as db

# 读取
ly = db.Layout()
ly.read(str(src))
print(f"dbu = {ly.dbu} μm")

# 找 top cell
top_cells = [ly.cell(int(ci)) for ci in ly.each_top_cell()]
top = top_cells[0]
print(f"top cell = {top.name}")

# 输出变换前的 polygon
print("\n=== 变换前 ===")
for li in ly.layer_indices():
    info = ly.get_info(li)
    print(f"层 {info.layer}/{info.datatype}:")
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        if shape.is_text():
            pos = shape.text_pos
            print(f"  TEXT '{shape.text_string}' at ({pos.x}, {pos.y}) dbu = ({float(pos.x)*ly.dbu}, {float(pos.y)*ly.dbu}) μm")
        else:
            box = shape.bbox()
            print(f"  shape bbox=({box.left},{box.bottom})-({box.right},{box.top}) dbu = ({float(box.left)*ly.dbu},{float(box.bottom)*ly.dbu})-({float(box.right)*ly.dbu},{float(box.top)*ly.dbu}) μm")
        it.next()

# 测试 1: DCplxTrans 构造
# db.DCplxTrans(mag, rot, mirr, x, y) - 缩放/角度/镜像/平移（μm）
t_translate = db.DCplxTrans(1.0, 0.0, False, 100.0, 50.0)
print(f"\n平移变换: {t_translate}")

t_rotate = db.DCplxTrans(1.0, 90.0, False, 0.0, 0.0)
print(f"旋转变换: {t_rotate}")

t_mirror = db.DCplxTrans(1.0, 0.0, True, 0.0, 0.0)
print(f"镜像变换: {t_mirror}")

t_scale = db.DCplxTrans(2.0, 0.0, False, 0.0, 0.0)
print(f"缩放变换: {t_scale}")

# 测试 2: Cell.transform(trans)
# 这是关键 API - 对 cell 内所有 shapes 应用变换（原地修改）
print("\n=== 测试 Cell.transform ===")
try:
    top.transform(t_translate)
    print("Cell.transform(translate) 成功")
except Exception as e:
    print(f"Cell.transform 失败: {type(e).__name__}: {e}")

# 输出变换后的 polygon
print("\n=== 变换后（平移 100,50）===")
for li in ly.layer_indices():
    info = ly.get_info(li)
    print(f"层 {info.layer}/{info.datatype}:")
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        if shape.is_text():
            pos = shape.text_pos
            print(f"  TEXT '{shape.text_string}' at ({pos.x}, {pos.y}) dbu = ({float(pos.x)*ly.dbu}, {float(pos.y)*ly.dbu}) μm")
        else:
            box = shape.bbox()
            print(f"  shape bbox=({box.left},{box.bottom})-({box.right},{box.top}) dbu = ({float(box.left)*ly.dbu},{float(box.bottom)*ly.dbu})-({float(box.right)*ly.dbu},{float(box.top)*ly.dbu}) μm")
        it.next()

# 写出
out = Path("/workspace/_smoke_r324_out.gds")
ly.write(str(out))
print(f"\n变换后 GDSII: {out}")

# 重新读取验证
ly2 = db.Layout()
ly2.read(str(out))
top2 = ly2.cell(int(list(ly2.each_top_cell())[0]))
print("\n=== 重新读取验证 ===")
for li in ly2.layer_indices():
    info = ly2.get_info(li)
    print(f"层 {info.layer}/{info.datatype}:")
    it = top2.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        if shape.is_text():
            pos = shape.text_pos
            print(f"  TEXT '{shape.text_string}' at ({float(pos.x)*ly2.dbu}, {float(pos.y)*ly2.dbu}) μm")
        else:
            box = shape.bbox()
            print(f"  shape bbox=({float(box.left)*ly2.dbu},{float(box.bottom)*ly2.dbu})-({float(box.right)*ly2.dbu},{float(box.top)*ly2.dbu}) μm")
        it.next()
