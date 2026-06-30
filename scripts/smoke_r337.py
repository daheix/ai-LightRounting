"""R337 冒烟测试：验证 KLayout Layout.scale_and_snap 实际行为。

测试:
1. 创建简单 GDS（顶层 cell 含 polygon，bbox (0,0)-(100,50) μm）
2. 用 scale_and_snap(top_cell, 1, 1, 2) 缩放 0.5x
3. 写出 + 重新读取
4. 验证 bbox 是 (0,0)-(50,25) μm

来源:
- KLayout Layout.scale_and_snap:
  https://klayout.org/doc-qt5/code/class_Layout.html
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def main() -> int:
    print("=" * 60)
    print("R337 冒烟测试: scale_and_snap 行为验证")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        src_gds = td_path / "src.gds"
        scaled_gds = td_path / "scaled.gds"

        # 1. 创建源 GDS
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        top = ly.create_cell("TOP")
        # polygon: (0,0)-(100,50) μm = (0,0)-(100000,50000) dbu
        pts = [db.Point(0, 0), db.Point(100000, 0),
               db.Point(100000, 50000), db.Point(0, 50000)]
        top.shapes(li).insert(db.Polygon(pts))
        ly.write(str(src_gds))
        print(f"[1] 源 GDS 已创建: {src_gds}")
        print(f"    源 bbox (dbu): {top.bbox()}")

        # 2. 读取并缩放 0.5x: mult=1, div=2, grid=1
        ly2 = db.Layout()
        ly2.read(str(src_gds))
        # 取顶层 cell
        top_ci_list = list(ly2.each_top_cell())
        assert len(top_ci_list) == 1, f"期望 1 个顶层 cell，得到 {len(top_ci_list)}"
        top_ci = top_ci_list[0]
        top_cell = ly2.cell(top_ci)
        print(f"[2] 读取后顶层 cell: {top_cell.name}, bbox (dbu): {top_cell.bbox()}")

        # 尝试 scale_and_snap
        print(f"[3] 调用 ly2.scale_and_snap(top_cell, 1, 1, 2)  # 0.5x")
        try:
            ly2.scale_and_snap(top_cell, 1, 1, 2)
            print(f"    成功。缩放后 bbox (dbu): {top_cell.bbox()}")
        except Exception as e:
            print(f"    失败: {type(e).__name__}: {e}")
            return 1

        # 3. 写出
        ly2.write(str(scaled_gds))
        print(f"[4] 缩放后 GDS 已写出: {scaled_gds}")

        # 4. 重新读取验证
        ly3 = db.Layout()
        ly3.read(str(scaled_gds))
        top3_ci = list(ly3.each_top_cell())[0]
        top3 = ly3.cell(top3_ci)
        bbox3 = top3.bbox()
        print(f"[5] 重新读取后 bbox (dbu): {bbox3}")
        dbu = float(ly3.dbu)
        bbox_um = (
            float(bbox3.left) * dbu,
            float(bbox3.bottom) * dbu,
            float(bbox3.right) * dbu,
            float(bbox3.top) * dbu,
        )
        print(f"    bbox (μm): {bbox_um}")

        # 期望: (0, 0, 50, 25) μm
        expected = (0.0, 0.0, 50.0, 25.0)
        eps = 1e-6
        ok = all(abs(a - b) < eps for a, b in zip(bbox_um, expected))
        if ok:
            print(f"[6] ✓ 验证成功: bbox = {expected} μm (期望 0.5x 缩放)")
        else:
            print(f"[6] ✗ 验证失败: 得到 {bbox_um}, 期望 {expected}")
            return 1

        # 5. 测试 2x 缩放
        print()
        print("-" * 60)
        print("附加测试: 2.0x 缩放 (mult=2, div=1)")
        print("-" * 60)
        ly4 = db.Layout()
        ly4.read(str(src_gds))
        top4_ci = list(ly4.each_top_cell())[0]
        top4 = ly4.cell(top4_ci)
        ly4.scale_and_snap(top4, 1, 2, 1)
        out4 = td_path / "scaled_2x.gds"
        ly4.write(str(out4))
        ly5 = db.Layout()
        ly5.read(str(out4))
        top5 = ly5.cell(list(ly5.each_top_cell())[0])
        bbox5 = top5.bbox()
        dbu5 = float(ly5.dbu)
        bbox5_um = (
            float(bbox5.left) * dbu5,
            float(bbox5.bottom) * dbu5,
            float(bbox5.right) * dbu5,
            float(bbox5.top) * dbu5,
        )
        print(f"2x 缩放后 bbox (μm): {bbox5_um}")
        expected_2x = (0.0, 0.0, 200.0, 100.0)
        ok2 = all(abs(a - b) < eps for a, b in zip(bbox5_um, expected_2x))
        if ok2:
            print(f"✓ 2x 验证成功: bbox = {expected_2x} μm")
        else:
            print(f"✗ 2x 验证失败: 得到 {bbox5_um}, 期望 {expected_2x}")
            return 1

    print()
    print("=" * 60)
    print("R337 冒烟测试全部通过 ✓")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
