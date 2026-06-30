"""R338 冒烟测试 2：验证 Instance 属性访问与数组实例。

测试:
1. 创建 GDS（TOP 含 CHILD_A × 1 普通实例 + CHILD_B × 1 数组实例）
2. 遍历 TOP.each_inst()，验证属性:
   - cell_index / cell.name
   - trans
   - is_array()
   - 对数组: a, b, na, nb
3. 验证 clear_insts + 重新插入后属性保留

来源:
- KLayout Instance: https://www.klayout.org/doc-qt5/code/class_Instance.html
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def main() -> int:
    print("=" * 60)
    print("R338 冒烟测试 2: Instance 属性与数组实例")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        src_gds = td_path / "src.gds"

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
        # 普通实例
        top.insert(db.CellInstArray(
            child_a.cell_index(), db.Trans(db.Point(0, 0))
        ))
        # 数组实例: 2×3 数组，间距 (20, 0) 和 (0, 30) μm
        top.insert(db.CellInstArray(
            child_b.cell_index(),
            db.Trans(db.Point(100000, 0)),
            db.Vector(20000, 0),
            db.Vector(0, 30000),
            2, 3,
        ))
        ly.write(str(src_gds))
        print(f"[1] 源 GDS 已创建: 1 普通 CHILD_A + 1 数组 CHILD_B (2×3)")

        # 读取并遍历实例
        ly2 = db.Layout()
        ly2.read(str(src_gds))
        top2 = ly2.cell("TOP")

        print(f"[2] 遍历 TOP 实例:")
        instances_info = []
        for inst in top2.each_inst():
            cell_name = inst.cell.name
            cell_ci = int(inst.cell_index)
            trans = inst.trans
            is_arr = bool(inst.is_array())
            info = {
                "cell_name": cell_name,
                "cell_ci": cell_ci,
                "trans": trans,
                "is_array": is_arr,
            }
            if is_arr:
                info["a"] = inst.a
                info["b"] = inst.b
                info["na"] = int(inst.na)
                info["nb"] = int(inst.nb)
            instances_info.append(info)
            print(f"    - {cell_name} ci={cell_ci} is_array={is_arr}")
            if is_arr:
                print(f"      a=({info['a'].x},{info['a'].y}) b=({info['b'].x},{info['b'].y}) na={info['na']} nb={info['nb']}")

        if len(instances_info) != 2:
            print(f"[3] ✗ 期望 2 个实例，得到 {len(instances_info)}")
            return 1
        print(f"[3] ✓ 找到 2 个实例")

        # 验证数组实例属性
        arr_inst = next(i for i in instances_info if i["is_array"])
        if arr_inst["na"] != 2 or arr_inst["nb"] != 3:
            print(f"[4] ✗ 数组维度错误: na={arr_inst['na']}, nb={arr_inst['nb']}")
            return 1
        print(f"[4] ✓ 数组维度正确: na=2, nb=3")

        # 测试 clear + 重新插入（保留所有属性）
        print()
        print("-" * 60)
        print("测试: clear_insts + 重新插入（保留属性）")
        print("-" * 60)

        top2.clear_insts()
        # 重新插入
        for info in instances_info:
            if info["is_array"]:
                arr = db.CellInstArray(
                    info["cell_ci"], info["trans"],
                    info["a"], info["b"],
                    info["na"], info["nb"],
                )
            else:
                arr = db.CellInstArray(info["cell_ci"], info["trans"])
            top2.insert(arr)

        out_gds = td_path / "out.gds"
        ly2.write(str(out_gds))

        # 验证
        ly3 = db.Layout()
        ly3.read(str(out_gds))
        top3 = ly3.cell("TOP")
        count_a = 0
        count_b_arr = 0
        for inst in top3.each_inst():
            if inst.cell.name == "CHILD_A":
                count_a += 1
            elif inst.cell.name == "CHILD_B" and inst.is_array():
                count_b_arr += 1
                # 验证数组维度
                assert int(inst.na) == 2, f"na 期望 2, 得到 {inst.na}"
                assert int(inst.nb) == 3, f"nb 期望 3, 得到 {inst.nb}"
        print(f"重新插入后: CHILD_A 普通 × {count_a}, CHILD_B 数组 × {count_b_arr}")
        if count_a == 1 and count_b_arr == 1:
            print(f"✓ 重新插入成功，数组属性保留")
        else:
            print(f"✗ 重新插入失败")
            return 1

    print()
    print("=" * 60)
    print("R338 冒烟测试 2 全部通过 ✓")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
