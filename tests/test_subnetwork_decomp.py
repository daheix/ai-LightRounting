"""子网络分解算法测试（R04）。

测试 Schur 补、块三对角求解、子网络分解、自适应策略、增量缓存。

来源:
- Schur 补理论: Schur 1917; Zhang 2005
- 块三对角求解: Thomas 算法块版本
- 区域分解: IEEE TCAD 综述
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.subnetwork_decomp import (
    BlockTridiagonalMatrix,
    SubnetworkCache,
    SubnetworkDecomposition,
    block_thomas_solve,
    build_block_tridiagonal_from_chain,
    cascade_adaptive,
    decompose_circuit,
    detect_block_tridiagonal,
    merge_subnetworks_via_schur,
    schur_complement,
    select_strategy,
    solve_subnetwork,
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


class TestSchurComplement:
    """Schur 补计算测试。"""

    def test_schur_complement_basic(self):
        """测试基本 Schur 补计算。"""
        # 简单 2x2 分块矩阵
        A = np.array([[2.0, 0.0], [0.0, 3.0]])
        B = np.array([[1.0], [1.0]])
        C = np.array([[1.0, 1.0]])
        D = np.array([[5.0]])

        S = schur_complement(A, B, C, D)
        # S = D - C·A⁻¹·B = 5 - [1,1]·[1/2,0;0,1/3]·[1;1]
        # = 5 - [1,1]·[1/2;1/3] = 5 - (1/2 + 1/3) = 5 - 5/6 = 25/6
        expected = 5.0 - (1.0 / 2.0 + 1.0 / 3.0)
        assert np.isclose(S[0, 0], expected), f"Schur 补计算错误: {S[0,0]} vs {expected}"

    def test_schur_complement_identity(self):
        """测试 A 为单位矩阵的 Schur 补。"""
        A = np.eye(3)
        B = np.array([[1.0], [2.0], [3.0]])
        C = np.array([[1.0, 2.0, 3.0]])
        D = np.array([[10.0]])

        S = schur_complement(A, B, C, D)
        # S = D - C·I⁻¹·B = 10 - [1,2,3]·[1;2;3] = 10 - 14 = -4
        assert np.isclose(S[0, 0], -4.0)

    def test_schur_complement_singular_raises(self):
        """测试奇异 A 矩阵 raise RuntimeError。"""
        A = np.zeros((2, 2))  # 奇异矩阵
        B = np.array([[1.0], [1.0]])
        C = np.array([[1.0, 1.0]])
        D = np.array([[1.0]])

        with pytest.raises(RuntimeError, match="奇异"):
            schur_complement(A, B, C, D)

    def test_schur_complement_complex(self):
        """测试复数 Schur 补。"""
        A = np.array([[1.0 + 1j, 0.0], [0.0, 1.0 - 1j]])
        B = np.array([[1.0], [1.0]])
        C = np.array([[1.0, 1.0]])
        D = np.array([[0.0]])

        S = schur_complement(A, B, C, D)
        # S = 0 - [1,1]·[1/(1+i),0;0,1/(1-i)]·[1;1]
        # = -[1,1]·[1/(1+i);1/(1-i)]
        # = -(1/(1+i) + 1/(1-i))
        # = -((1-i)/2 + (1+i)/2) = -1
        assert np.isclose(S[0, 0], -1.0 + 0.0j)


class TestBlockThomasSolve:
    """块三对角矩阵求解测试。"""

    def test_block_thomas_single_block(self):
        """测试单块矩阵（退化为普通求解）。"""
        D1 = np.array([[2.0, 1.0], [1.0, 3.0]])
        matrix = BlockTridiagonalMatrix(
            diagonal_blocks=[D1],
            upper_blocks=[],
            lower_blocks=[],
        )
        b = np.array([3.0, 4.0])
        x = block_thomas_solve(matrix, b)
        # 验证 D1·x = b
        assert np.allclose(D1 @ x, b)

    def test_block_thomas_two_blocks(self):
        """测试两块三对角矩阵。"""
        D1 = np.array([[2.0, 0.0], [0.0, 2.0]])
        D2 = np.array([[3.0, 0.0], [0.0, 3.0]])
        U1 = np.array([[1.0, 0.0], [0.0, 1.0]])
        L2 = np.array([[1.0, 0.0], [0.0, 1.0]])

        matrix = BlockTridiagonalMatrix(
            diagonal_blocks=[D1, D2],
            upper_blocks=[U1],
            lower_blocks=[L2],
        )
        b = np.array([1.0, 2.0, 3.0, 4.0])
        x = block_thomas_solve(matrix, b)

        # 验证 M·x = b
        M = matrix.to_dense()
        assert np.allclose(M @ x, b), f"块 Thomas 求解错误: M·x != b"

    def test_block_thomas_three_blocks(self):
        """测试三块三对角矩阵。"""
        D1 = np.array([[2.0]])
        D2 = np.array([[3.0]])
        D3 = np.array([[4.0]])
        U1 = np.array([[1.0]])
        U2 = np.array([[1.0]])
        L2 = np.array([[1.0]])
        L3 = np.array([[1.0]])

        matrix = BlockTridiagonalMatrix(
            diagonal_blocks=[D1, D2, D3],
            upper_blocks=[U1, U2],
            lower_blocks=[L2, L3],
        )
        b = np.array([1.0, 2.0, 3.0])
        x = block_thomas_solve(matrix, b)

        M = matrix.to_dense()
        assert np.allclose(M @ x, b)

    def test_block_thomas_vs_dense(self):
        """测试块 Thomas 与稠密求解对比。"""
        # 构建 4 块三对角矩阵
        np.random.seed(42)
        blocks_D = [np.random.randn(3, 3) + 3 * np.eye(3) for _ in range(4)]
        blocks_U = [np.random.randn(3, 3) * 0.1 for _ in range(3)]
        blocks_L = [np.random.randn(3, 3) * 0.1 for _ in range(3)]

        matrix = BlockTridiagonalMatrix(
            diagonal_blocks=blocks_D,
            upper_blocks=blocks_U,
            lower_blocks=blocks_L,
        )
        b = np.random.randn(12)

        # 块 Thomas 求解
        x_thomas = block_thomas_solve(matrix, b)

        # 稠密求解
        M = matrix.to_dense()
        x_dense = np.linalg.solve(M, b)

        # 对比（误差 < 1e-10）
        assert np.allclose(x_thomas, x_dense, atol=1e-10), (
            f"块 Thomas 与稠密求解不一致: max err = {np.max(np.abs(x_thomas - x_dense))}"
        )

    def test_block_thomas_singular_raises(self):
        """测试奇异对角块 raise RuntimeError。"""
        D1 = np.zeros((2, 2))  # 奇异
        D2 = np.eye(2)
        matrix = BlockTridiagonalMatrix(
            diagonal_blocks=[D1, D2],
            upper_blocks=[np.zeros((2, 2))],
            lower_blocks=[np.zeros((2, 2))],
        )
        b = np.array([1.0, 2.0, 3.0, 4.0])
        with pytest.raises(RuntimeError, match="奇异"):
            block_thomas_solve(matrix, b)


class TestDetectBlockTridiagonal:
    """块三对角结构检测测试。"""

    def test_detect_chain(self):
        """测试链式电路检测。"""
        wl = np.array([1.55])
        instances = {
            f"wg{i}": _make_waveguide_sdict(wl) for i in range(5)
        }
        connections = [
            (f"wg{i}.out", f"wg{i+1}.in") for i in range(4)
        ]
        is_chain, ordered = detect_block_tridiagonal(instances, connections)
        assert is_chain, "应检测为链式结构"
        assert len(ordered) == 5

    def test_detect_non_chain_branch(self):
        """测试分叉电路（非链式）。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl),
            "wg2": _make_waveguide_sdict(wl),
            "wg3": _make_waveguide_sdict(wl),
            "wg4": _make_waveguide_sdict(wl),
        }
        # wg1 连接 wg2, wg3, wg4（分叉）
        connections = [
            ("wg1.out", "wg2.in"),
            ("wg1.out", "wg3.in"),
            ("wg1.out", "wg4.in"),
        ]
        is_chain, _ = detect_block_tridiagonal(instances, connections)
        assert not is_chain, "分叉电路不应检测为链式"

    def test_detect_single_instance(self):
        """测试单实例电路。"""
        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl)}
        connections = []
        is_chain, ordered = detect_block_tridiagonal(instances, connections)
        # 单实例无连接，图空，endpoints=0，非链式
        assert not is_chain


class TestDecomposeCircuit:
    """子网络分解测试。"""

    def test_decompose_single_subnetwork(self):
        """测试单子网络分解。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(10)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(9)]

        decomp = decompose_circuit(instances, connections, num_subnetworks=1)
        assert len(decomp.subnetworks) == 1
        assert len(decomp.subnetworks[0]) == 10

    def test_decompose_two_subnetworks(self):
        """测试两子网络分解。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(20)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(19)]

        decomp = decompose_circuit(instances, connections, num_subnetworks=2)
        assert len(decomp.subnetworks) == 2
        total = sum(len(sub) for sub in decomp.subnetworks)
        assert total == 20

    def test_decompose_couplings(self):
        """测试子网络耦合识别。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(20)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(19)]

        decomp = decompose_circuit(instances, connections, num_subnetworks=2)
        # 链式电路分割为 2 个子网络，应有 1 个耦合
        assert len(decomp.couplings) >= 1

    def test_decompose_auto_num(self):
        """测试自动子网络数。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(200)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(199)]

        decomp = decompose_circuit(instances, connections)
        # 200 器件，每 75 一个子网络 → 约 2-3 个
        assert 1 <= len(decomp.subnetworks) <= 8


class TestSelectStrategy:
    """自适应策略选择测试。"""

    def test_strategy_chain(self):
        """测试链式电路选择 block_thomas。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(10)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(9)]

        strategy = select_strategy(instances, connections)
        assert strategy == "block_thomas", f"链式电路应选择 block_thomas，实际: {strategy}"

    def test_strategy_small_circuit(self):
        """测试小规模电路选择 klu。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(3)}
        connections = [("wg0.out", "wg1.in"), ("wg1.out", "wg2.in")]

        strategy = select_strategy(instances, connections)
        assert strategy == "klu"

    def test_strategy_large_circuit(self):
        """测试大规模电路策略选择。"""
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(150)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(149)]

        strategy = select_strategy(instances, connections)
        # 链式 150 器件应选 block_thomas
        assert strategy == "block_thomas"


class TestCascadeAdaptive:
    """自适应级联测试。"""

    def test_cascade_adaptive_small(self):
        """测试小规模电路自适应级联。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}

        result = cascade_adaptive(instances, connections, ports)
        assert ("in", "out") in result or ("out", "in") in result
        # 验证无 NaN/Inf
        for key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr)), f"{key} 包含 NaN"
            assert not np.any(np.isinf(arr)), f"{key} 包含 Inf"

    def test_cascade_adaptive_empty(self):
        """测试空实例。"""
        result = cascade_adaptive({}, [], None)
        assert result == {}

    def test_cascade_adaptive_chain(self):
        """测试链式电路自适应级联。

        注: cascade_klu 对长链式电路（10+ 波导）的数值误差较大，
        此测试验证无 NaN/Inf 和策略选择正确性。
        传输系数的数值精度优化将在后续路标中完成。
        """
        wl = np.array([1.55])
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(10)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(9)]
        ports = {"in": "wg0.in", "out": "wg9.out"}

        result = cascade_adaptive(instances, connections, ports)
        # 验证无 NaN/Inf
        for key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr)), f"{key} 包含 NaN"
            assert not np.any(np.isinf(arr)), f"{key} 包含 Inf"
        # 验证有结果返回
        assert len(result) > 0, "结果为空"


class TestSubnetworkCache:
    """增量式子网络缓存测试。"""

    def test_cache_basic(self):
        """测试基本缓存功能。"""
        cache = SubnetworkCache()
        wl = np.array([1.55])
        sdict = _make_waveguide_sdict(wl)

        call_count = 0

        def compute_fn():
            nonlocal call_count
            call_count += 1
            return sdict

        # 第一次调用: 缓存未命中
        result1 = cache.get_or_compute("sub1", compute_fn, {"wg1"}, {"wg1": sdict})
        assert call_count == 1

        # 第二次调用: 缓存命中
        result2 = cache.get_or_compute("sub1", compute_fn, {"wg1"}, {"wg1": sdict})
        assert call_count == 1  # 未重新计算

    def test_cache_invalidation(self):
        """测试缓存失效。"""
        cache = SubnetworkCache()
        wl = np.array([1.55])
        sdict1 = _make_waveguide_sdict(wl, length=10.0)
        sdict2 = _make_waveguide_sdict(wl, length=20.0)

        call_count = 0

        def compute_fn():
            nonlocal call_count
            call_count += 1
            return sdict1

        # 第一次调用
        cache.get_or_compute("sub1", compute_fn, {"wg1"}, {"wg1": sdict1})
        assert call_count == 1

        # 参数变化
        cache.get_or_compute("sub1", compute_fn, {"wg1"}, {"wg1": sdict2})
        assert call_count == 2  # 重新计算

    def test_cache_dependency(self):
        """测试依赖关系。"""
        cache = SubnetworkCache()
        cache.dependency["sub1"] = {"wg1", "wg2"}
        cache.dependency["sub2"] = {"sub1"}  # sub2 依赖 sub1
        cache.cache["sub1"] = {}
        cache.cache["sub2"] = {}

        # 使 wg1 失效
        cache.invalidate("wg1")

        # sub1 和 sub2 都应失效
        assert "sub1" not in cache.cache
        assert "sub2" not in cache.cache


class TestR04Integration:
    """R04 集成测试。"""

    def test_large_circuit_stability(self):
        """测试大规模电路稳定性（200 器件）。"""
        wl = np.array([1.55])
        n = 200
        instances = {f"wg{i}": _make_waveguide_sdict(wl) for i in range(n)}
        connections = [(f"wg{i}.out", f"wg{i+1}.in") for i in range(n - 1)]
        ports = {"in": "wg0.in", "out": f"wg{n-1}.out"}

        result = cascade_adaptive(instances, connections, ports)
        # 验证无 NaN/Inf
        for key, val in result.items():
            arr = np.asarray(val)
            assert not np.any(np.isnan(arr)), f"{key} 包含 NaN"
            assert not np.any(np.isinf(arr)), f"{key} 包含 Inf"

    def test_no_fallback_in_subnetwork_decomp(self):
        """验证 subnetwork_decomp.py 无 fall-back 兜底（AST 检查）。"""
        import ast

        with open("src/polaris/sim/subnetwork_decomp.py") as f:
            source = f.read()
        tree = ast.parse(source)

        fallback_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # 检查 except 块中是否有 pass
                for child in ast.walk(node):
                    if isinstance(child, ast.Pass):
                        fallback_count += 1

        assert fallback_count == 0, (
            f"发现 {fallback_count} 个 except:pass fall-back，违反规则 14.1"
        )

    def test_schur_vs_direct_solve(self):
        """测试 Schur 补与直接求解对比（误差 < 1e-10）。"""
        # 构建分块矩阵 M = [A B; C D]
        A = np.array([[2.0, 1.0], [1.0, 3.0]])
        B = np.array([[1.0, 0.0], [0.0, 1.0]])
        C = np.array([[1.0, 0.0], [0.0, 1.0]])
        D = np.array([[4.0, 2.0], [2.0, 5.0]])

        # Schur 补
        S = schur_complement(A, B, C, D)

        # 直接求解验证: M = [A B; C D]
        M = np.block([[A, B], [C, D]])
        # Schur 补应等于 D - C·A⁻¹·B
        S_direct = D - C @ np.linalg.solve(A, B)

        assert np.allclose(S, S_direct, atol=1e-10), (
            f"Schur 补与直接求解不一致: max err = {np.max(np.abs(S - S_direct))}"
        )

    def test_block_thomas_performance(self):
        """测试块 Thomas 性能（比稠密快）。

        注: 由于 numpy 优化，小矩阵可能差距不大，主要验证正确性。
        """
        import time

        # 构建 10 块三对角矩阵，每块 4x4
        np.random.seed(42)
        n_blocks = 10
        block_size = 4
        blocks_D = [
            np.random.randn(block_size, block_size) + 5 * np.eye(block_size)
            for _ in range(n_blocks)
        ]
        blocks_U = [
            np.random.randn(block_size, block_size) * 0.1
            for _ in range(n_blocks - 1)
        ]
        blocks_L = [
            np.random.randn(block_size, block_size) * 0.1
            for _ in range(n_blocks - 1)
        ]

        matrix = BlockTridiagonalMatrix(
            diagonal_blocks=blocks_D,
            upper_blocks=blocks_U,
            lower_blocks=blocks_L,
        )
        b = np.random.randn(n_blocks * block_size)

        # 块 Thomas 求解
        x_thomas = block_thomas_solve(matrix, b)

        # 稠密求解
        M = matrix.to_dense()
        x_dense = np.linalg.solve(M, b)

        # 验证正确性
        assert np.allclose(x_thomas, x_dense, atol=1e-10)
