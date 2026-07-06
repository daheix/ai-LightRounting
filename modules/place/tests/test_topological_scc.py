"""Tarjan SCC 含环拓扑排序回归测试（R05 Bug 修复）。

## 背景

6 个 SiEPIC GDS 用例（Crossings/MZI1/mzi_bends 等）在 stage3(AI布局) 失败:
```
RuntimeError: 电路连接存在环，无法拓扑排序（processed=1/N，R03 禁止 fall-back）
```

根因: GDS loader 生成无向连接（dev1,dev2），但 _extract_connections() 当有向边
(src→dst)。_topological_depth() 用 Kahn 算法要求 DAG，光子电路有反馈环
（MZI 两臂 / Crossings 双向）。analytical.py:1350 已有 try/except 容错，
但 _legalize():464 处没有保护。

## 修复方案（方案 B: Tarjan SCC）

用 Tarjan 1972 SCC 算法把含环图分解为 SCC，在 condensation DAG 上跑 Kahn，
同一 SCC 内器件 depth 相同。这是处理含环有向图拓扑排序的标准正确方法
（CLRS §22.5），非 fall-back（R03 合规）。

## 测试覆盖

1. Tarjan SCC 算法正确性（10 个图论用例: 简单环/链/混合/自环/双环/空图）
2. _topological_depth 含环安全（环内器件 depth 相同）
3. 6 个 SiEPIC GDS 端到端: 加载 → place_analytical 不抛环异常
4. place_analytical 输出合法（无重叠、在画布内）

## 6 个回归用例（来自 real_board/siepic/）

| 用例名 | 器件数 | 连接数 | 失败根因 |
|--------|--------|--------|----------|
| siepic__Crossings | 5 | 7 | Crossings 双向传输形成环 |
| siepic__Examples__Crossings | 5 | 7 | 同上 |
| siepic__Examples__CustomComponentTutorial__ebeam_taper_475_500_te1550_testcircuit | 3 | 2 | taper 反馈环 |
| siepic__Examples__MZI1 | 3 | 6 | MZI 两臂环 |
| siepic__Examples__mzi_bends_test | 4 | 17 | MZI 两臂 + 弯曲波导环 |
| siepic__MZI1 | 3 | 6 | MZI 两臂环 |

来源（R02 学术诚信，≥5 个文献 URL）:
- Tarjan, R. "Depth-first search and linear graph algorithms",
  SIAM Journal on Computing 1(2): 146-160, 1972, DOI: 10.1137/0201010
  https://doi.org/10.1137/0201010
- Kahn 1962 "Topological Sorting of Large Networks"
  https://doi.org/10.1145/368996.369025
- CLRS Introduction to Algorithms 3rd ed. §22.5 Strongly Connected Components
- Sedgewick & Wayne "Algorithms" 4th ed. §4.2.5 Strong Components
  https://algs4.cs.princeton.edu/42digraph/
- Condensation (graph theory)
  https://en.wikipedia.org/wiki/Condensation_(graph_theory)
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
_GDS_SRC = str(Path(__file__).resolve().parents[2] / "gds_tools" / "src")
for _p in (_SRC, _CORE_SRC, _GDS_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from polaris_place.analytical import place_analytical  # noqa: E402
from polaris_place.metrics import (  # noqa: E402
    _condensation_dag,
    _tarjan_scc,
    _topological_depth,
)


# ---------------------------------------------------------------------------
# 1. Tarjan SCC 算法正确性（图论单元测试）
# ---------------------------------------------------------------------------

class TestTarjanSCC:
    """Tarjan SCC 算法正确性测试。"""

    def test_simple_3_cycle(self):
        """3 节点简单环 0→1→2→0，应为 1 个 SCC {0,1,2}。"""
        sccs = _tarjan_scc(3, [(0, 1), (1, 2), (2, 0)])
        assert len(sccs) == 1
        assert frozenset(sccs[0]) == {0, 1, 2}

    def test_chain_4_nodes(self):
        """4 节点链 0→1→2→3，应为 4 个独立 SCC。"""
        sccs = _tarjan_scc(4, [(0, 1), (1, 2), (2, 3)])
        assert len(sccs) == 4
        for scc in sccs:
            assert len(scc) == 1

    def test_cycle_plus_chain(self):
        """混合图: 环 0→1→2→0 + 链 2→3→4，应为 SCC {0,1,2},{3},{4}。"""
        sccs = _tarjan_scc(5, [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)])
        scc_sets = [frozenset(s) for s in sccs]
        assert len(sccs) == 3
        assert frozenset({0, 1, 2}) in scc_sets
        assert frozenset({3}) in scc_sets
        assert frozenset({4}) in scc_sets

    def test_self_loop(self):
        """自环 0→0，应为 1 个 SCC {0}。"""
        sccs = _tarjan_scc(1, [(0, 0)])
        assert len(sccs) == 1
        assert sccs[0] == [0]

    def test_bidirectional_2_cycle(self):
        """双向边 0↔1，应为 1 个 SCC {0,1}。"""
        sccs = _tarjan_scc(2, [(0, 1), (1, 0)])
        assert len(sccs) == 1
        assert frozenset(sccs[0]) == {0, 1}

    def test_empty_graph(self):
        """空图（3 节点无边），应为 3 个独立 SCC。"""
        sccs = _tarjan_scc(3, [])
        assert len(sccs) == 3

    def test_disconnected_components(self):
        """不连通图: 0→1→0 (环) + 2→3 (链)，应为 {0,1},{2},{3}。"""
        sccs = _tarjan_scc(4, [(0, 1), (1, 0), (2, 3)])
        scc_sets = [frozenset(s) for s in sccs]
        assert len(sccs) == 3
        assert frozenset({0, 1}) in scc_sets
        assert frozenset({2}) in scc_sets
        assert frozenset({3}) in scc_sets

    def test_nested_cycles(self):
        """嵌套环: 0→1→2→0 + 1→3→1，0/1/2/3 同属一个 SCC。"""
        sccs = _tarjan_scc(4, [(0, 1), (1, 2), (2, 0), (1, 3), (3, 1)])
        assert len(sccs) == 1
        assert frozenset(sccs[0]) == {0, 1, 2, 3}

    def test_total_scc_coverage(self):
        """所有 SCC 的并集应覆盖全部节点，无重叠。"""
        n = 6
        conns = [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)]
        sccs = _tarjan_scc(n, conns)
        all_nodes = []
        for scc in sccs:
            all_nodes.extend(scc)
        assert sorted(all_nodes) == list(range(n))

    def test_large_cycle_performance(self):
        """性能: 1000 节点环（验证迭代版不递归溢出）。"""
        n = 1000
        conns = [(i, (i + 1) % n) for i in range(n)]
        sccs = _tarjan_scc(n, conns)
        # 整个环是一个 SCC
        assert len(sccs) == 1
        assert len(sccs[0]) == n


# ---------------------------------------------------------------------------
# 2. _topological_depth 含环安全测试
# ---------------------------------------------------------------------------

class TestTopologicalDepth:
    """_topological_depth 含环安全测试（核心回归点）。"""

    def test_cycle_same_depth(self):
        """环内所有器件 depth 相同（核心修复点）。"""
        # 3 节点环
        depth = _topological_depth(3, [(0, 1), (1, 2), (2, 0)])
        assert depth[0] == depth[1] == depth[2]

    def test_chain_sequential_depth(self):
        """链式连接 depth 递增。"""
        depth = _topological_depth(4, [(0, 1), (1, 2), (2, 3)])
        assert depth == [0, 1, 2, 3]

    def test_cycle_plus_chain_depth(self):
        """环 + 链: 环内 depth 相同，链上递增。"""
        depth = _topological_depth(5, [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)])
        # 环 {0,1,2} depth 相同
        assert depth[0] == depth[1] == depth[2]
        # 链 3, 4 depth 递增
        assert depth[3] == depth[0] + 1
        assert depth[4] == depth[0] + 2

    def test_mzi_two_arms_no_exception(self):
        """MZI 两臂拓扑不应抛异常（修复前会 raise）。"""
        # gc1 → mmi1 → wg1 → mmi2 → gc2
        #        mmi1 → wg2 → mmi2 (两臂)
        depth = _topological_depth(
            5, [(0, 1), (1, 2), (2, 3), (1, 4), (4, 3)]
        )
        assert len(depth) == 5
        assert all(d >= 0 for d in depth)

    def test_bidirectional_no_exception(self):
        """双向连接（Crossings 双向传输）不应抛异常。"""
        # 0 ↔ 1 ↔ 2
        depth = _topological_depth(3, [(0, 1), (1, 0), (1, 2), (2, 1)])
        assert len(depth) == 3

    def test_no_raise_on_cycle_regression(self):
        """回归测试: 含环电路不再抛 RuntimeError（修复前的 Bug）。

        修复前: ``RuntimeError: 电路连接存在环，无法拓扑排序``
        修复后: Tarjan SCC 正确处理含环图，正常返回 depth。
        若此测试抛 RuntimeError 即回归到修复前的 Bug。
        """
        # 这是 6 个失败用例的核心根因: 含环电路不应抛 RuntimeError
        depth = _topological_depth(3, [(0, 1), (1, 2), (2, 0)])
        assert len(depth) == 3
        # 环内器件 depth 相同
        assert depth[0] == depth[1] == depth[2]

    def test_empty_circuit(self):
        """空电路 depth 为空列表。"""
        assert _topological_depth(0, []) == []

    def test_single_node(self):
        """单节点无连接 depth=0。"""
        assert _topological_depth(1, []) == [0]


# ---------------------------------------------------------------------------
# 3. _condensation_dag 测试
# ---------------------------------------------------------------------------

class TestCondensationDag:
    """_condensation_dag 测试。"""

    def test_cycle_collapse(self):
        """3 节点环收缩为 1 个虚拟节点。"""
        sccs = _tarjan_scc(3, [(0, 1), (1, 2), (2, 0)])
        node_to_scc, dag_edges = _condensation_dag(3, [(0, 1), (1, 2), (2, 0)], sccs)
        assert len(sccs) == 1
        # 所有节点属于同一 SCC
        assert node_to_scc[0] == node_to_scc[1] == node_to_scc[2]
        # condensation DAG 无边（环内边被丢弃）
        assert dag_edges == []

    def test_chain_no_collapse(self):
        """链不收缩，4 个独立 SCC。"""
        conns = [(0, 1), (1, 2), (2, 3)]
        sccs = _tarjan_scc(4, conns)
        node_to_scc, dag_edges = _condensation_dag(4, conns, sccs)
        assert len(sccs) == 4
        # condensation DAG 保持 3 条边
        assert len(dag_edges) == 3

    def test_cycle_plus_chain_dag(self):
        """环 + 链: condensation DAG 为 SCC{0,1,2} → {3} → {4}。"""
        conns = [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)]
        sccs = _tarjan_scc(5, conns)
        node_to_scc, dag_edges = _condensation_dag(5, conns, sccs)
        # 3 个 SCC
        assert len(sccs) == 3
        # 环内节点同 SCC
        assert node_to_scc[0] == node_to_scc[1] == node_to_scc[2]
        # 2 条 DAG 边: 环→{3}, {3}→{4}
        assert len(dag_edges) == 2


# ---------------------------------------------------------------------------
# 4. 6 个 SiEPIC GDS 端到端回归测试
# ---------------------------------------------------------------------------

# real_board/siepic 路径
_REAL_BOARD = Path(__file__).resolve().parents[3] / "real_board" / "siepic"

# 6 个失败用例的 GDS 文件名
_SIEPIC_GDS_CASES = [
    ("Crossings.gds", 5, 7),
    ("Examples__Crossings.gds", 5, 7),
    (
        "Examples__CustomComponentTutorial__ebeam_taper_475_500_te1550_testcircuit.GDS",
        3, 2,
    ),
    ("Examples__MZI1.gds", 3, 6),
    ("Examples__mzi_bends_test.gds", 4, 17),
    ("MZI1.gds", 3, 6),
]


def _load_siepic_gds(gds_filename: str) -> dict:
    """加载 SiEPIC GDS 为 polaris-core circuit dict。

    Args:
        gds_filename: GDS 文件名（相对 real_board/siepic/）。

    Returns:
        polaris-core circuit dict。

    Raises:
        ImportError: polaris_gds_tools 未安装。
        FileNotFoundError: GDS 文件不存在。
    """
    from polaris_gds_tools.gds_loader import load_gds_to_circuit

    gds_path = _REAL_BOARD / gds_filename
    if not gds_path.exists():
        pytest.skip(f"GDS 文件不存在: {gds_path}")
    return load_gds_to_circuit(gds_path)


@pytest.mark.parametrize("gds_filename,expected_n_dev,expected_n_conn", _SIEPIC_GDS_CASES)
def test_siepic_gds_no_cycle_exception(
    gds_filename: str, expected_n_dev: int, expected_n_conn: int,
):
    """6 个 SiEPIC GDS 用例: place_analytical 不抛环异常（核心回归测试）。

    修复前: ``RuntimeError: 电路连接存在环，无法拓扑排序``
    修复后: Tarjan SCC 正确处理含环电路，place_analytical 正常返回布局。
    """
    circuit = _load_siepic_gds(gds_filename)
    assert len(circuit["devices"]) == expected_n_dev, (
        f"{gds_filename}: 器件数 {len(circuit['devices'])} != 预期 {expected_n_dev}"
    )
    assert len(circuit["connections"]) == expected_n_conn, (
        f"{gds_filename}: 连接数 {len(circuit['connections'])} != 预期 {expected_n_conn}"
    )

    # 核心回归点: 不应抛 RuntimeError（环异常已修复）
    placements = place_analytical(circuit)

    # 验证布局合法性
    assert isinstance(placements, dict), "place_analytical 应返回 dict"
    assert len(placements) == expected_n_dev, (
        f"{gds_filename}: 布局器件数 {len(placements)} != 预期 {expected_n_dev}"
    )
    canvas_w = float(circuit["canvas_w"])
    canvas_h = float(circuit["canvas_h"])
    for name, pl in placements.items():
        x, y, w, h = float(pl["x"]), float(pl["y"]), float(pl["w"]), float(pl["h"])
        assert x >= 0.0, f"{gds_filename}/{name}: x={x} < 0"
        assert y >= 0.0, f"{gds_filename}/{name}: y={y} < 0"
        assert x + w <= canvas_w + 1e-6, (
            f"{gds_filename}/{name}: x+w={x+w} > canvas_w={canvas_w}"
        )
        assert y + h <= canvas_h + 1e-6, (
            f"{gds_filename}/{name}: y+h={y+h} > canvas_h={canvas_h}"
        )


@pytest.mark.parametrize("gds_filename,expected_n_dev,expected_n_conn", _SIEPIC_GDS_CASES)
def test_siepic_gds_no_overlap(gds_filename: str, expected_n_dev: int, expected_n_conn: int):
    """6 个 SiEPIC GDS 用例: 布局无器件重叠（FFDH 合法化保证）。"""
    circuit = _load_siepic_gds(gds_filename)
    placements = place_analytical(circuit)

    # 检查所有器件对无重叠（strict，touching 不算重叠）
    items = list(placements.items())
    for i in range(len(items)):
        n1, p1 = items[i]
        aabb1 = (
            float(p1["x"]), float(p1["y"]),
            float(p1["x"]) + float(p1["w"]),
            float(p1["y"]) + float(p1["h"]),
        )
        for j in range(i + 1, len(items)):
            n2, p2 = items[j]
            aabb2 = (
                float(p2["x"]), float(p2["y"]),
                float(p2["x"]) + float(p2["w"]),
                float(p2["y"]) + float(p2["h"]),
            )
            # strict overlap: a[0] < b[2] and b[0] < a[2] and ...
            overlap = (
                aabb1[0] < aabb2[2] and aabb2[0] < aabb1[2]
                and aabb1[1] < aabb2[3] and aabb2[1] < aabb1[3]
            )
            assert not overlap, (
                f"{gds_filename}: 器件 {n1} 与 {n2} 重叠 "
                f"({aabb1} ∩ {aabb2})"
            )


@pytest.mark.parametrize("gds_filename,expected_n_dev,expected_n_conn", _SIEPIC_GDS_CASES)
def test_siepic_gds_topology_depth_safe(
    gds_filename: str, expected_n_dev: int, expected_n_conn: int,
):
    """6 个 SiEPIC GDS 用例: _topological_depth 含环安全（直接验证核心修复点）。"""
    from polaris_place.metrics import _topological_depth

    circuit = _load_siepic_gds(gds_filename)
    names = [d["name"] for d in circuit["devices"]]
    name_to_idx = {nm: i for i, nm in enumerate(names)}
    idx_conns: list[tuple[int, int]] = []
    for conn in circuit["connections"]:
        d1, _p1, d2, _p2 = conn
        if d1 in name_to_idx and d2 in name_to_idx:
            idx_conns.append((name_to_idx[d1], name_to_idx[d2]))

    # 核心回归点: 不抛环异常
    depth = _topological_depth(len(names), idx_conns)

    # 验证 depth 合法性
    assert len(depth) == len(names)
    assert all(d >= 0 for d in depth)
    # 环内器件 depth 应相同（至少有一对环内器件 depth 相等，或无环时全唯一）
    # 这里只验证不抛异常 + depth 合法范围，不强制环内相同（取决于具体拓扑）


if __name__ == "__main__":
    # 直接运行: python test_topological_scc.py
    pytest.main([__file__, "-v", "--tb=short"])
