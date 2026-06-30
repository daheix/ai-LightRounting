"""R333 冒烟测试: 找到 Cell 实例计数 API 替代 num_insts。"""
import klayout.db as db
import tempfile, os

# 创建两个简单 GDSII
def make_gds(name, layer=1, dt=0):
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name)
    li = ly.layer(layer, dt)
    pts = [db.Point(0, 0), db.Point(10000, 0), db.Point(10000, 5000), db.Point(0, 5000)]
    top.shapes(li).insert(db.Polygon(pts))
    p = tempfile.mktemp(suffix='.gds')
    ly.write(p)
    return p

g1 = make_gds('CELL_A')
g2 = make_gds('CELL_B')

# 用 Layout.read() 追加模式
target = db.Layout()
target.dbu = 0.001
target.read(g1)
target.read(g2)

print("All cells after read:", [target.cell(ci).name for ci in target.each_top_cell()])
print("All cells (top_down):", [target.cell(ci).name for ci in target.each_cell_top_down()])

# 创建 wrapper cell
wrapper = target.create_cell('MERGED')
top_cells_before = [target.cell(ci) for ci in target.each_top_cell()]
print("Top cells before merge:", [c.name for c in top_cells_before])

# 实例化所有非 MERGED 的顶层 cell 到 wrapper
for c in top_cells_before:
    if c.name == 'MERGED':
        continue
    inst = db.CellInstArray(c.cell_index(), db.Trans(db.Point(0, 0)))
    wrapper.insert(inst)

# 测试各种实例计数 API
print("\n=== 实例计数 API 测试 ===")

# 测试 each_inst()
try:
    insts = list(wrapper.each_inst())
    print(f"wrapper.each_inst() OK, count={len(insts)}")
except AttributeError as e:
    print(f"wrapper.each_inst() AttributeError: {e}")

# 测试 cell_insts
try:
    n = wrapper.cell_insts
    print(f"wrapper.cell_insts = {n}")
except AttributeError as e:
    print(f"wrapper.cell_insts AttributeError: {e}")

# 测试 instances()
try:
    insts = list(wrapper.instances())
    print(f"wrapper.instances() OK, count={len(insts)}")
except AttributeError as e:
    print(f"wrapper.instances() AttributeError: {e}")

# 测试 each_parent_inst
try:
    parents = list(wrapper.each_parent_inst())
    print(f"wrapper.each_parent_inst() OK, count={len(parents)}")
except AttributeError as e:
    print(f"wrapper.each_parent_inst() AttributeError: {e}")

# 检查最终顶层 cells
print("\nFinal top cells:", [target.cell(ci).name for ci in target.each_top_cell()])

# 写出合并后的 GDSII
out = tempfile.mktemp(suffix='.gds')
target.write(out)
print(f"\n合并后写出: {out}, size={os.path.getsize(out)} bytes")

# 重新读入验证
verify = db.Layout()
verify.read(out)
print("Verify top cells:", [verify.cell(ci).name for ci in verify.each_top_cell()])
print("Verify all cells:", [verify.cell(ci).name for ci in verify.each_cell_top_down()])

# 测试 Instance 的属性
print("\n=== Instance 属性测试 ===")
verify_top = verify.cell(verify.each_top_cell().__next__())
try:
    insts = list(verify_top.each_inst())
    for i, inst in enumerate(insts):
        print(f"Inst {i}: cell={inst.cell.name}")
        # 测试常用属性
        for attr in ['cell_index', 'trans']:
            try:
                v = getattr(inst, attr)
                print(f"  .{attr} = {v}")
            except AttributeError:
                print(f"  .{attr} AttributeError")
except Exception as e:
    print(f"each_inst error: {type(e).__name__}: {e}")

# 清理
for f in [g1, g2, out]:
    os.unlink(f)
print("\nDone")
