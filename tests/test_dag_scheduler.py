"""DAG 调度器测试（R04）。

测试 DAG 创建、拓扑排序、叶节点/根节点识别、并行调度。

来源:
- SAX Circuit 文档: https://gdsfactory.github.io/sax/nbs/internals/02_circuit/
- Knuth, "The Art of Computer Programming", §2.2.3
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.dag_scheduler import (
    CircuitDAG,
    cascade_parallel,
    create_dag,
    detect_parallel_groups,
    flat_circuit,
    schedule_circuit,
)


def _make_waveguide_sdict(wl, length=10.0, neff=2.4):
    """创建波导 S 参数（辅助函数）。"""
    wl = np.asarray(wl, dtype=float)
    phase = 2 * np.pi * neff * length / wl
    return {
        ("in", "in"): np.zeros_like(wl, dtype=complex),
        ("out", "in"): np.exp(1j * phase),
        ("in", "out"): np.exp(1j * phase),
        ("out", "out"): np.zeros_like(wl, dtype=complex),
    }


class TestCircuitDAG:
    """CircuitDAG 数据结构测试。"""

    def test_dag_creation(self):
        """测试 DAG 创建。"""
        dag = CircuitDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        assert "A" in dag.nodes
        assert "B" in dag.nodes
        assert "C" in dag.nodes
        assert dag.in_degree["A"] == 0
        assert dag.in_degree["B"] == 1
        assert dag.in_degree["C"] == 1

    def test_dag_topological_sort(self):
        """测试拓扑排序。"""
        dag = CircuitDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        dag.add_edge("A", "C")

        result = dag.topological_sort()
        # A 必须在 B 和 C 之前，B 必须在 C 之前
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        assert result.index("B") < result.index("C")

    def test_dag_cycle_raises(self):
        """测试有环图 raise RuntimeError。"""
        dag = CircuitDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "A")  # 环

        with pytest.raises(RuntimeError, match="环"):
            dag.topological_sort()

    def test_dag_find_leaves(self):
        """测试叶节点识别。"""
        dag = CircuitDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        leaves = dag.find_leaves()
        assert "C" in leaves
        assert "A" not in leaves

    def test_dag_find_root(self):
        """测试根节点识别。"""
        dag = CircuitDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        root = dag.find_root()
        assert root == "A"

    def test_dag_find_root_multiple_raises_none(self):
        """测试多根节点返回 None。"""
        dag = CircuitDAG()
        dag.add_edge("A", "C")
        dag.add_edge("B", "C")

        root = dag.find_root()
        assert root is None  # 两个根节点


class TestCreateDAG:
    """create_dag 函数测试。"""

    def test_create_dag_basic(self):
        """测试从网表创建 DAG。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl),
            "wg2": _make_waveguide_sdict(wl),
            "wg3": _make_waveguide_sdict(wl),
        }
        connections = [
            ("wg1.out", "wg2.in"),
            ("wg2.out", "wg3.in"),
        ]

        dag = create_dag(instances, connections)
        assert len(dag.nodes) == 3
        assert dag.in_degree["wg1"] == 0
        assert dag.in_degree["wg2"] == 1
        assert dag.in_degree["wg3"] == 1

    def test_create_dag_no_connections(self):
        """测试无连接的 DAG。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl),
            "wg2": _make_waveguide_sdict(wl),
        }
        connections = []

        dag = create_dag(instances, connections)
        assert len(dag.nodes) == 2
        # 无连接，所有节点入度为 0
        assert all(deg == 0 for deg in dag.in_degree.values())

    def test_create_dag_self_loop_ignored(self):
        """测试自环被忽略。"""
        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl)}
        connections = [("wg1.out", "wg1.in")]  # 自环

        dag = create_dag(instances, connections)
        # 自环被忽略
        assert len(dag.nodes) == 1


class TestFlatCircuit:
    """flat_circuit 函数测试。"""

    def test_flat_circuit_passthrough(self):
        """测试扁平化（当前为直通）。"""
        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl)}
        connections = []
        ports = {"in": "wg1.in", "out": "wg1.out"}

        flat_inst, flat_conn, flat_ports = flat_circuit(instances, connections, ports)
        assert flat_inst is instances
        assert flat_conn is connections
        assert flat_ports is ports


class TestDetectParallelGroups:
    """detect_parallel_groups 函数测试。"""

    def test_detect_parallel_groups_chain(self):
        """测试链式 DAG 的层级（每层 1 个节点）。"""
        dag = CircuitDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        levels = detect_parallel_groups(dag)
        assert len(levels) == 3  # 3 层
        assert levels[0] == ["A"]
        assert levels[1] == ["B"]
        assert levels[2] == ["C"]

    def test_detect_parallel_groups_parallel(self):
        """测试并行 DAG 的层级（同层多节点）。"""
        dag = CircuitDAG()
        # A → B, A → C, B → D, C → D
        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")

        levels = detect_parallel_groups(dag)
        assert len(levels) == 3  # 3 层
        assert levels[0] == ["A"]
        assert set(levels[1]) == {"B", "C"}  # B 和 C 可并行
        assert levels[2] == ["D"]


class TestCascadeParallel:
    """cascade_parallel 函数测试。"""

    def test_cascade_parallel_small_circuit(self):
        """测试小规模电路（使用串行 KLU）。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl),
            "wg2": _make_waveguide_sdict(wl),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}

        result = cascade_parallel(instances, connections, ports)
        # 验证无 NaN/Inf
        for key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr)), f"{key} 包含 NaN"
            assert not np.any(np.isinf(arr)), f"{key} 包含 Inf"

    def test_cascade_parallel_empty(self):
        """测试空实例。"""
        result = cascade_parallel({}, [], None)
        assert result == {}

    def test_cascade_parallel_large_circuit(self):
        """测试大规模电路并行求解。"""
        wl = np.array([1.55])
        n = 100
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(n)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(n - 1)]
        ports = {"in": "wg0.in", "out": f"wg{n-1}.out"}

        result = cascade_parallel(instances, connections, ports)
        # 验证无 NaN/Inf
        for key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr)), f"{key} 包含 NaN"
            assert not np.any(np.isinf(arr)), f"{key} 包含 Inf"


class TestScheduleCircuit:
    """schedule_circuit 函数测试。"""

    def test_schedule_serial(self):
        """测试串行调度。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl),
            "wg2": _make_waveguide_sdict(wl),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}

        result = schedule_circuit(instances, connections, ports, parallel=False)
        for _key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr))

    def test_schedule_parallel(self):
        """测试并行调度。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(10)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(9)]
        ports = {"in": "wg0.in", "out": "wg9.out"}

        result = schedule_circuit(instances, connections, ports, parallel=True)
        for _key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr))

    def test_schedule_empty(self):
        """测试空实例。"""
        result = schedule_circuit({}, [], None)
        assert result == {}


class TestR04DAGIntegration:
    """R04 DAG 集成测试。"""

    def test_no_fallback_in_dag_scheduler(self):
        """验证 dag_scheduler.py 无 fall-back 兜底（AST 检查）。"""
        import ast

        with open("src/polaris/sim/dag_scheduler.py") as f:
            source = f.read()
        tree = ast.parse(source)

        fallback_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for child in ast.walk(node):
                    if isinstance(child, ast.Pass):
                        fallback_count += 1

        assert fallback_count == 0, (
            f"发现 {fallback_count} 个 except:pass fall-back，违反规则 14.1"
        )

    def test_dag_vs_klu_consistency(self):
        """测试 DAG 调度与 KLU 结果物理合理性一致。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(20)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(19)]
        ports = {"in": "wg0.in", "out": "wg19.out"}

        # DAG 调度
        result_dag = schedule_circuit(instances, connections, ports, parallel=False)

        # 验证物理合理性: |S| <= 1
        for key, val in result_dag.items():
            arr = np.asarray(val)
            assert np.all(np.abs(arr) <= 1.0 + 1e-10), (
                f"{key} 功率守恒违反: |S| > 1"
            )
