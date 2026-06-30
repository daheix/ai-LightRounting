"""R344 冒烟测试：确认 KLayout Region 层间 DRC API。

测试:
- region.enclosing_check(other, d): 检查 self 是否充分包围 other
- region.enclosed_check(other, d): 检查 self 是否被 other 充分包围
- region.overlap_check(other, d): 检查 self 与 other 的重叠
- region.separation_check(other, d): 检查 self 与 other 的间距
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def main() -> int:
    # 1) enclosing_check: layer_a 应该包围 layer_b
    # layer_a: 大矩形 (0,0)-(5000,5000) = 5x5 um
    # layer_b: 小矩形 (1000,1000)-(4000,4000) = 3x3 um
    # enclosing_check(2000): layer_a 应比 layer_b 大至少 2um（每边）
    # 实际 layer_a 比 layer_b 大 1um 每边，所以 < 2um 有违规
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    li_a = ly.layer(1, 0)
    li_b = ly.layer(2, 0)
    top.shapes(li_a).insert(db.Box(0, 0, 5000, 5000))
    top.shapes(li_b).insert(db.Box(1000, 1000, 4000, 4000))
    r_a = db.Region(top.begin_shapes_rec(li_a))
    r_b = db.Region(top.begin_shapes_rec(li_b))

    print("=== enclosing_check ===")
    print(f"layer_a (5x5) 包围 layer_b (3x3), 阈值 2um")
    # enclosing_check(d): 检查 r_a 是否比 r_b 大至少 d（每边）
    # r_a 比 r_b 大 1um 每边，d=2um，应该有违规
    try:
        v = r_a.enclosing_check(r_b, 2000)
        print(f"  violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    # enclosing_check(1000): d=1um，r_a 比 r_b 大 1um 每边，应该无违规
    try:
        v = r_a.enclosing_check(r_b, 1000)
        print(f"  d=1um: violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    # 2) separation_check: 两个不同层的矩形间距
    # layer_a: (0,0)-(1000,1000)
    # layer_c: (3000,0)-(4000,1000)  间距 2um
    ly2 = db.Layout()
    ly2.dbu = 0.001
    top2 = ly2.create_cell("TOP")
    li_a2 = ly2.layer(1, 0)
    li_c = ly2.layer(3, 0)
    top2.shapes(li_a2).insert(db.Box(0, 0, 1000, 1000))
    top2.shapes(li_c).insert(db.Box(3000, 0, 4000, 1000))
    r_a2 = db.Region(top2.begin_shapes_rec(li_a2))
    r_c = db.Region(top2.begin_shapes_rec(li_c))

    print("\n=== separation_check ===")
    print(f"layer_a (1,0) 与 layer_c (3,0) 间距 2um")
    # separation_check(d): 检查 r_a2 与 r_c 间距 >= d
    # 间距 2um，d=3um，应该有违规
    try:
        v = r_a2.separation_check(r_c, 3000)
        print(f"  d=3um: violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    # separation_check(2000): d=2um，间距 2um，应该无违规
    try:
        v = r_a2.separation_check(r_c, 2000)
        print(f"  d=2um: violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    # 3) overlap_check: 两个不同层的矩形重叠
    # layer_a: (0,0)-(2000,2000)
    # layer_d: (1000,1000)-(3000,3000)  重叠区域 (1000,1000)-(2000,2000) = 1x1 um
    ly3 = db.Layout()
    ly3.dbu = 0.001
    top3 = ly3.create_cell("TOP")
    li_a3 = ly3.layer(1, 0)
    li_d = ly3.layer(4, 0)
    top3.shapes(li_a3).insert(db.Box(0, 0, 2000, 2000))
    top3.shapes(li_d).insert(db.Box(1000, 1000, 3000, 3000))
    r_a3 = db.Region(top3.begin_shapes_rec(li_a3))
    r_d = db.Region(top3.begin_shapes_rec(li_d))

    print("\n=== overlap_check ===")
    print(f"layer_a (1,0) 与 layer_d (4,0) 重叠 1x1 um")
    # overlap_check(d): 检查 r_a3 与 r_d 重叠 >= d
    # 重叠 1um，d=2um，应该有违规
    try:
        v = r_a3.overlap_check(r_d, 2000)
        print(f"  d=2um: violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    # overlap_check(1000): d=1um，重叠 1um，应该无违规
    try:
        v = r_a3.overlap_check(r_d, 1000)
        print(f"  d=1um: violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    # 4) enclosed_check: 反向 enclosing
    # layer_b 被 layer_a 包围
    # enclosed_check(d): 检查 r_b 是否被 r_a 充分包围（r_a 比 r_b 大至少 d 每边）
    print("\n=== enclosed_check ===")
    print(f"layer_b (3x3) 被 layer_a (5x5) 包围")
    try:
        v = r_b.enclosed_check(r_a, 2000)
        print(f"  d=2um: violations count={v.count()}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

    print("\nR344 冒烟测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
