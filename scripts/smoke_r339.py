"""R339 冒烟测试：验证 KLayout Cell 重命名 API。

测试:
1. 创建 GDS（TOP + CHILD_A + CHILD_B）
2. 用 Layout.rename_cell(cell_index, new_name) 重命名 CHILD_A → CHILD_C
3. 写出 + 重新读取验证

候选 API:
- Layout.rename_cell(cell_index, name)
- Cell.name = "new"  # 可能只读

来源:
- KLayout Layout class: https://www.klayout.org/doc-qt5/code/class_Layout.html
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def main() -> int:
    print("=" * 60)
    print("R339 冒烟测试: Cell 重命名 API 验证")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        src_gds = td_path / "src.gds"
        out_gds = td_path / "out.gds"

        # 1. 创建源 GDS
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
            child_b.cell_index(), db.Trans(db.Point(50000, 0))
        ))
        ly.write(str(src_gds))
        print(f"[1] 源 GDS 已创建: TOP + CHILD_A + CHILD_B")

        # 2. 读取并重命名
        ly2 = db.Layout()
        ly2.read(str(src_gds))
        child_a2 = ly2.cell("CHILD_A")
        child_a_ci = int(child_a2.cell_index())
        print(f"[2] 读取后 CHILD_A ci={child_a_ci}")

        # 尝试 rename_cell
        print(f"[3] 调用 ly2.rename_cell({child_a_ci}, 'CHILD_C')")
        try:
            ly2.rename_cell(child_a_ci, "CHILD_C")
            print(f"    成功")
        except Exception as e:
            print(f"    失败: {type(e).__name__}: {e}")
            return 1

        # 验证
        cell_c = ly2.cell("CHILD_C")
        if cell_c is None:
            print(f"[4] ✗ 重命名后查不到 CHILD_C")
            return 1
        print(f"[4] ✓ CHILD_C 存在")

        cell_a = ly2.cell("CHILD_A")
        if cell_a is not None:
            print(f"[5] ✗ CHILD_A 仍存在（应该已重命名）")
            return 1
        print(f"[5] ✓ CHILD_A 已不存在")

        # 3. 写出 + 重新读取
        ly2.write(str(out_gds))
        ly3 = db.Layout()
        ly3.read(str(out_gds))
        cell_names = sorted(c.name for c in ly3.each_cell())
        print(f"[6] 重新读取后 cell 名: {cell_names}")
        if "CHILD_C" in cell_names and "CHILD_A" not in cell_names:
            print(f"    ✓ 重命名持久化成功")
        else:
            print(f"    ✗ 重命名未持久化")
            return 1

        # 4. 验证实例引用正确（实例应引用 CHILD_C，不是 CHILD_A）
        top3 = ly3.cell("TOP")
        ref_names = set()
        for inst in top3.each_inst():
            ref_names.add(inst.cell.name)
        print(f"[7] TOP 实例引用: {ref_names}")
        if "CHILD_C" in ref_names and "CHILD_A" not in ref_names:
            print(f"    ✓ 实例引用已更新")
        else:
            print(f"    ✗ 实例引用未更新")
            return 1

    print()
    print("=" * 60)
    print("R339 冒烟测试全部通过 ✓")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
