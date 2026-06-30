"""R338 冒烟测试：验证 KLayout Cell 实例替换 API。

测试:
1. 创建 GDS（TOP 含 CHILD_A × 2 实例）
2. 创建新 cell CHILD_B
3. 把 TOP 中引用 CHILD_A 的实例替换为 CHILD_B
4. 写出 + 重新读取验证

KLayout 候选 API:
- Instance.cell_index = new_ci  # 直接修改？
- Cell.replace_insts(...)  # 批量替换？
- 或者删除旧实例 + 插入新实例

来源:
- KLayout Instance class:
  https://www.klayout.org/doc-qt5/code/class_Instance.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def main() -> int:
    print("=" * 60)
    print("R338 冒烟测试: Cell 实例替换 API 验证")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        src_gds = td_path / "src.gds"
        out_gds = td_path / "out.gds"

        # 1. 创建源 GDS: TOP 含 CHILD_A × 2 实例
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)

        child_a = ly.create_cell("CHILD_A")
        pts_a = [db.Point(0, 0), db.Point(10000, 0),
                 db.Point(10000, 5000), db.Point(0, 5000)]
        child_a.shapes(li).insert(db.Polygon(pts_a))

        child_b = ly.create_cell("CHILD_B")
        pts_b = [db.Point(0, 0), db.Point(20000, 0),
                 db.Point(20000, 10000), db.Point(0, 10000)]
        child_b.shapes(li).insert(db.Polygon(pts_b))

        top = ly.create_cell("TOP")
        top.insert(db.CellInstArray(
            child_a.cell_index(), db.Trans(db.Point(0, 0))
        ))
        top.insert(db.CellInstArray(
            child_a.cell_index(), db.Trans(db.Point(20000, 0))
        ))
        ly.write(str(src_gds))
        print(f"[1] 源 GDS 已创建: CHILD_A × 2 实例")

        # 2. 读取并替换
        ly2 = db.Layout()
        ly2.read(str(src_gds))
        top2 = ly2.cell("TOP")
        child_b2 = ly2.cell("CHILD_B")
        child_a_ci = ly2.cell("CHILD_A").cell_index()
        child_b_ci = child_b2.cell_index()
        print(f"[2] 读取后: CHILD_A ci={child_a_ci}, CHILD_B ci={child_b_ci}")

        # 方法 1: 用 Instance.cell_index = new_ci 直接修改
        # 注意：each_inst() 返回的是副本，修改可能不生效
        # 方法 2: 收集旧实例信息，删除后重新插入
        # 方法 3: KLayout 可能有 replace_cell API

        # 尝试方法 1: 遍历实例，记录变换，删除后重新插入
        instances_to_replace = []
        for inst in top2.each_inst():
            if int(inst.cell_index) == child_a_ci:
                instances_to_replace.append((
                    inst.trans,  # 保存变换
                ))

        print(f"[3] 找到 {len(instances_to_replace)} 个 CHILD_A 实例")

        # 删除 TOP 中所有实例
        # KLayout Cell.clear_insts() 会删除所有实例
        top2.clear_insts()

        # 重新插入：用 CHILD_B 替换
        for trans, in instances_to_replace:
            top2.insert(db.CellInstArray(child_b_ci, trans))

        ly2.write(str(out_gds))
        print(f"[4] 替换后 GDS 已写出: {out_gds}")

        # 3. 验证
        ly3 = db.Layout()
        ly3.read(str(out_gds))
        top3 = ly3.cell("TOP")
        child_a_count = 0
        child_b_count = 0
        for inst in top3.each_inst():
            cell_name = inst.cell.name
            if cell_name == "CHILD_A":
                child_a_count += 1
            elif cell_name == "CHILD_B":
                child_b_count += 1
        print(f"[5] 验证: CHILD_A × {child_a_count}, CHILD_B × {child_b_count}")

        if child_a_count == 0 and child_b_count == 2:
            print(f"[6] ✓ 替换成功: 2 个 CHILD_A → 2 个 CHILD_B")
        else:
            print(f"[6] ✗ 替换失败")
            return 1

        # 4. 测试保留变换
        print()
        print("-" * 60)
        print("附加测试: 验证实例变换保留")
        print("-" * 60)
        # 原 CHILD_A @ (0,0) 和 (20,0) μm
        # 替换后 CHILD_B 应在相同位置
        positions = []
        for inst in top3.each_inst():
            if inst.cell.name == "CHILD_B":
                disp = inst.trans.disp
                dbu = float(ly3.dbu)
                positions.append((float(disp.x) * dbu, float(disp.y) * dbu))
        positions.sort()
        print(f"CHILD_B 实例位置: {positions}")
        expected = [(0.0, 0.0), (20.0, 0.0)]
        if positions == expected:
            print(f"✓ 变换保留成功: {expected}")
        else:
            print(f"✗ 变换保留失败: 得到 {positions}, 期望 {expected}")
            return 1

    print()
    print("=" * 60)
    print("R338 冒烟测试全部通过 ✓")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
