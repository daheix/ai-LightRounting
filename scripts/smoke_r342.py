"""R342 冒烟测试：确认 KLayout db.Edges / db.Region.edges API。

测试内容:
- db.Region(...).edges(): 从 Region 提取边
- db.Edges(...): 直接从 layout 提取边
- edge.length(): 边长度
- edges.with_length(min, max): 按长度过滤
- edges.length(): Edges 总长度
- edges.count(): Edges 总边数
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import klayout.db as db


def build_gds(path: Path) -> None:
    """构造 2x3 矩形 GDSII 在 layer (1, 0)."""
    ly = db.Layout()
    ly.dbu = 0.001  # 1 nm
    top = ly.create_cell("TOP")
    li = ly.layer(1, 0)
    # 矩形 (0,0) - (2000, 3000) dbu = 2um x 3um
    box = db.Box(0, 0, 2000, 3000)
    top.shapes(li).insert(box)
    ly.write(str(path))


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="r342_smoke_"))
    gds = tmpdir / "test.gds"
    build_gds(gds)

    ly = db.Layout()
    ly.read(str(gds))
    top = ly.top_cell()
    li = ly.layer(1, 0)
    dbu = float(ly.dbu)

    print(f"dbu={dbu} um")

    # 1) Region.edges()
    r = db.Region(top.begin_shapes_rec(li))
    print(f"Region area={r.area()} count={r.count()}")
    edges_from_region = r.edges()
    print(f"Region.edges() count={edges_from_region.count()} length={edges_from_region.length()}")

    # 2) db.Edges 直接构造
    edges_direct = db.Edges(top.begin_shapes_rec(li))
    print(f"db.Edges count={edges_direct.count()} length={edges_direct.length()}")

    # 3) Edges 迭代（每条 Edge）
    total_len_iter = 0
    n_iter = 0
    for e in edges_direct.each():
        total_len_iter += e.length()
        n_iter += 1
    print(f"each() iter: n={n_iter} total_len={total_len_iter}")

    # 4) Edges.with_length 过滤
    # 矩形 2um x 3um 的边: 2 条 2000 dbu + 2 条 3000 dbu = 10000 dbu 总
    # 注意: with_length(length, inverse) 是单参数过滤(长度==length)
    #       with_length(min, max, inverse) 是范围过滤(长度在 [min, max])
    # 传 2 个 int 会被当作 (length, inverse)，所以要用 3 个参数
    edges_short = edges_direct.with_length(0, 2500, False)
    print(f"with_length(0,2500,False) count={edges_short.count()} length={edges_short.length()}")

    edges_long = edges_direct.with_length(2500, 999999, False)
    print(f"with_length(2500,999999,False) count={edges_long.count()} length={edges_long.length()}")

    # 单参数形式不支持，必须传 inverse
    # with_length(length, inverse): 长度==length 的边（inverse=False）
    edges_eq_2000 = edges_direct.with_length(2000, False)
    print(f"with_length(2000,False) count={edges_eq_2000.count()} length={edges_eq_2000.length()}")
    # 期望 2 条 2000 dbu 边 = 4000 总长

    edges_eq_3000 = edges_direct.with_length(3000, False)
    print(f"with_length(3000,False) count={edges_eq_3000.count()} length={edges_eq_3000.length()}")
    # 期望 2 条 3000 dbu 边 = 6000 总长

    # 5) Edges.with_length(less_than) 单参数形式?
    try:
        edges_lt = edges_direct.with_length(less_than=2500)
        print(f"with_length(less_than=2500) count={edges_lt.count()}")
    except Exception as e:
        print(f"with_length(less_than=...) 失败: {type(e).__name__}: {e}")

    # 6) Edge 对象属性
    first_edge = next(edges_direct.each())
    print(f"first_edge: p1={first_edge.p1} p2={first_edge.p2} length={first_edge.length()}")

    # 7) Edges 是否有 move/transform?
    print(f"Edges class methods: {[m for m in dir(edges_direct) if not m.startswith('_')]}")

    # 8) Region.edges() 与 db.Edges 一致性
    assert edges_from_region.count() == edges_direct.count(), "Region.edges() 和 db.Edges 数量应一致"
    assert edges_from_region.length() == edges_direct.length(), "Region.edges() 和 db.Edges 长度应一致"

    # 9) 单层 + 多 polygon 测试
    top2 = ly.create_cell("TOP2")
    li2 = ly.layer(2, 0)
    top2.shapes(li2).insert(db.Box(0, 0, 1000, 1000))
    top2.shapes(li2).insert(db.Box(5000, 5000, 6500, 6500))
    r2 = db.Region(top2.begin_shapes_rec(li2))
    e2 = r2.edges()
    print(f"2-rect layer: region count={r2.count()} edges count={e2.count()} length={e2.length()}")
    # 2 个 1x1 矩形，每个 4 条 1000 dbu 边 = 8 条 8000 dbu

    print("R342 冒烟测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
