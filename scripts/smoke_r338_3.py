"""R338 冒烟测试 3：列出 Instance 对象的所有属性和方法。"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def main() -> int:
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

        top = ly.create_cell("TOP")
        top.insert(db.CellInstArray(
            child_a.cell_index(), db.Trans(db.Point(0, 0))
        ))
        # 数组实例
        top.insert(db.CellInstArray(
            child_a.cell_index(),
            db.Trans(db.Point(100000, 0)),
            db.Vector(20000, 0),
            db.Vector(0, 30000),
            2, 3,
        ))
        ly.write(str(src_gds))

        ly2 = db.Layout()
        ly2.read(str(src_gds))
        top2 = ly2.cell("TOP")

        print("=" * 60)
        print("Instance 对象属性和方法")
        print("=" * 60)
        inst_list = list(top2.each_inst())
        print(f"实例数: {len(inst_list)}")
        print()

        for i, inst in enumerate(inst_list):
            print(f"--- 实例 {i} ---")
            print(f"  type: {type(inst).__name__}")
            # 列出所有属性
            attrs = [a for a in dir(inst) if not a.startswith("_")]
            print(f"  attrs: {attrs}")
            print()

            # 尝试访问常见属性
            for attr in ["cell_index", "cell", "trans", "name",
                         "is_regular_array", "is_array", "array_size",
                         "na", "nb", "a", "b",
                         "prop_id", "parent_cell", "parent",
                         "cell_inst", "cxx_id", "id"]:
                try:
                    val = getattr(inst, attr)
                    if callable(val):
                        try:
                            val = val()
                            print(f"  {attr}() = {val}")
                        except Exception as e:
                            print(f"  {attr}() error: {e}")
                    else:
                        print(f"  {attr} = {val}")
                except AttributeError:
                    pass
                except Exception as e:
                    print(f"  {attr} error: {type(e).__name__}: {e}")
            print()

        # 也看下 CellInstArray 的属性
        print("=" * 60)
        print("CellInstArray 对象属性")
        print("=" * 60)
        arr = db.CellInstArray(
            child_a.cell_index(),
            db.Trans(db.Point(0, 0)),
            db.Vector(20000, 0),
            db.Vector(0, 30000),
            2, 3,
        )
        attrs = [a for a in dir(arr) if not a.startswith("_")]
        print(f"attrs: {attrs}")
        for attr in attrs:
            try:
                val = getattr(arr, attr)
                if callable(val):
                    try:
                        val = val()
                        print(f"  {attr}() = {val}")
                    except Exception as e:
                        print(f"  {attr}() error: {e}")
                else:
                    print(f"  {attr} = {val}")
            except Exception as e:
                print(f"  {attr} error: {type(e).__name__}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
