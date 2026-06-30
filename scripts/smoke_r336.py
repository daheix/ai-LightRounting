"""R336 冒烟测试: Instance API。"""
import klayout.db as db
import tempfile, os

# 创建带实例的 GDSII
ly = db.Layout()
ly.dbu = 0.001

# 创建子 cell
child = ly.create_cell('CHILD')
li = ly.layer(1, 0)
pts = [db.Point(0, 0), db.Point(1000, 0), db.Point(1000, 500), db.Point(0, 500)]
child.shapes(li).insert(db.Polygon(pts))

# 创建顶层 cell，实例化 CHILD 多次
top = ly.create_cell('TOP')
# 实例 1: 平移 (10000, 20000) = (10, 20) μm
inst1 = db.CellInstArray(child.cell_index(), db.Trans(db.Point(10000, 20000)))
top.insert(inst1)
# 实例 2: 旋转 90 度 + 平移 (30000, 0)
inst2 = db.CellInstArray(child.cell_index(), db.Trans(db.Trans.R90, db.Point(30000, 0)))
top.insert(inst2)
# 实例 3: 镜像 + 平移
inst3 = db.CellInstArray(child.cell_index(), db.Trans(db.Trans.M90, db.Point(40000, 50000)))
top.insert(inst3)

p = tempfile.mktemp(suffix='.gds')
ly.write(p)

# 重新读入验证
verify = db.Layout()
verify.read(p)
top_cell = verify.cell(verify.each_top_cell().__next__())
print(f"Top cell: {top_cell.name}")

# 遍历实例
print("\n=== Instance 属性测试 ===")
for i, inst in enumerate(top_cell.each_inst()):
    print(f"\nInst {i}:")
    print(f"  cell: {inst.cell.name}")
    print(f"  cell_index: {inst.cell_index}")
    
    # Trans 属性
    trans = inst.trans
    print(f"  trans: {trans}")
    print(f"  trans type: {type(trans).__name__}")
    
    # 测试 Trans 的属性
    for attr in ['angle', 'disp', 'rot', 'mirror', 'is_mirror', 'magn']:
        try:
            v = getattr(trans, attr)
            print(f"  trans.{attr} = {v}")
        except AttributeError:
            print(f"  trans.{attr} AttributeError")
    
    # 测试 Instance 属性
    for attr in ['trans', 'cell_inst', 'is_complex', 'size', 'array_size']:
        try:
            v = getattr(inst, attr)
            print(f"  inst.{attr} = {v}")
        except AttributeError:
            print(f"  inst.{attr} AttributeError")

# 测试 Trans 静态成员
print("\n=== Trans 静态成员 ===")
for attr in ['R0', 'R90', 'R180', 'R270', 'M0', 'M45', 'M90', 'M135']:
    try:
        v = getattr(db.Trans, attr)
        print(f"  Trans.{attr} = {v}")
    except AttributeError:
        print(f"  Trans.{attr} AttributeError")

# 测试 disp
print("\n=== Trans.disp 测试 ===")
for inst in top_cell.each_inst():
    trans = inst.trans
    disp = trans.disp
    print(f"  disp: {disp}, type={type(disp).__name__}")
    print(f"  disp.x={disp.x}, disp.y={disp.y}")
    # 转换为 μm
    dbu = verify.dbu
    print(f"  disp μm: ({disp.x * dbu}, {disp.y * dbu})")

os.unlink(p)
print("\nDone")
