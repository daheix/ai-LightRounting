"""J02 教育文档与开源生态模块验收测试。

覆盖验收标准（≥10 个测试用例）:
- M1: 知识图谱构建与查询（节点/边/BFS/DFS/最短路径）
- M2: TF-IDF 索引与搜索（关键词检索/相关性排序）
- M3: PageRank 收敛性（d=0.85 迭代收敛）
- M4: IRT 三参数逻辑斯蒂模型（3PL 概率/MLE 能力估计）

学术来源:
- Manning et al. 2008: https://nlp.stanford.edu/IR-book/
- Page et al. 1998: http://ilpubs.stanford.edu:8090/422/
- Lord 1980: Applications of Item Response Theory
- Luceda Academy: https://academy.lucedaphotonics.com/
- Brandes 2001: https://www.sciencedirect.com/science/article/pii/S0306437901000707
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.platform import IRT3PL, KnowledgeGraph, PageRank, TFIDFRetriever
from polaris.platform.education import KGNode

# =============================================================================
# M1: 知识图谱构建与查询测试
# =============================================================================


def _build_photonics_kg() -> KnowledgeGraph:
    """构建光子学概念知识图谱测试 fixture。"""
    kg = KnowledgeGraph()
    kg.add_node("waveguide", "Waveguide", "device", {"difficulty": "beginner"})
    kg.add_node("mzi", "Mach-Zehnder Interferometer", "device")
    kg.add_node("ring", "Ring Resonator", "device")
    kg.add_node("fdtd", "FDTD", "simulation")
    kg.add_node("wave_eq", "Wave Equation", "principle")
    kg.add_edge("waveguide", "mzi", "prerequisite")
    kg.add_edge("waveguide", "ring", "prerequisite")
    kg.add_edge("waveguide", "wave_eq", "related")
    kg.add_edge("mzi", "fdtd", "depends-on")
    return kg


class TestKnowledgeGraph:
    """知识图谱构建与查询测试。"""

    def test_add_node_and_count(self) -> None:
        """节点添加后节点数与边数正确。"""
        kg = _build_photonics_kg()
        assert kg.node_count == 5
        assert kg.edge_count == 4

    def test_get_node_metadata(self) -> None:
        """get_node 返回正确的节点元数据。"""
        kg = _build_photonics_kg()
        node = kg.get_node("waveguide")
        assert isinstance(node, KGNode)
        assert node.node_id == "waveguide"
        assert node.label == "Waveguide"
        assert node.node_type == "device"
        assert node.metadata["difficulty"] == "beginner"

    def test_duplicate_node_raises(self) -> None:
        """重复添加节点应抛 ValueError（fail-fast，规则 R03）。"""
        kg = KnowledgeGraph()
        kg.add_node("wg", "Waveguide", "device")
        with pytest.raises(ValueError, match="已存在"):
            kg.add_node("wg", "Waveguide 2", "device")

    def test_invalid_node_type_raises(self) -> None:
        """无效节点类型应抛 ValueError。"""
        kg = KnowledgeGraph()
        with pytest.raises(ValueError, match="node_type"):
            kg.add_node("x", "X", "invalid_type")

    def test_add_edge_missing_node_raises(self) -> None:
        """边引用不存在节点应抛 KeyError。"""
        kg = KnowledgeGraph()
        kg.add_node("a", "A", "device")
        with pytest.raises(KeyError, match="不存在"):
            kg.add_edge("a", "b", "prerequisite")

    def test_invalid_relation_raises(self) -> None:
        """无效关系类型应抛 ValueError。"""
        kg = KnowledgeGraph()
        kg.add_node("a", "A", "device")
        kg.add_node("b", "B", "device")
        with pytest.raises(ValueError, match="relation"):
            kg.add_edge("a", "b", "invalid-relation")

    def test_bfs_traversal(self) -> None:
        """BFS 遍历从 waveguide 出发应包含可达节点。"""
        kg = _build_photonics_kg()
        bfs_result = kg.bfs("waveguide")
        assert bfs_result[0] == "waveguide"
        assert set(bfs_result) == {"waveguide", "mzi", "ring", "wave_eq", "fdtd"}

    def test_dfs_traversal(self) -> None:
        """DFS 遍历从 waveguide 出发应包含可达节点。"""
        kg = _build_photonics_kg()
        dfs_result = kg.dfs("waveguide")
        assert dfs_result[0] == "waveguide"
        assert "fdtd" in dfs_result

    def test_shortest_path(self) -> None:
        """最短路径 waveguide -> fdtd 应经过 mzi。"""
        kg = _build_photonics_kg()
        path = kg.shortest_path("waveguide", "fdtd")
        assert path[0] == "waveguide"
        assert path[-1] == "fdtd"
        assert len(path) == 3  # waveguide -> mzi -> fdtd

    def test_shortest_path_no_path_raises(self) -> None:
        """无路径时应抛 ValueError。"""
        kg = _build_photonics_kg()
        # fdtd 没有出边，无法到达 waveguide
        with pytest.raises(ValueError, match="无路径"):
            kg.shortest_path("fdtd", "waveguide")

    def test_neighbors(self) -> None:
        """neighbors 返回后继节点列表。"""
        kg = _build_photonics_kg()
        neighbors = set(kg.neighbors("waveguide"))
        assert neighbors == {"mzi", "ring", "wave_eq"}


# =============================================================================
# M2: TF-IDF 索引与搜索测试
# =============================================================================


PHOTONICS_DOCS = [
    "Waveguide is the fundamental building block of photonic integrated circuits",
    "Mach-Zehnder interferometer uses two waveguides for optical interference",
    "Ring resonator couples light between a bus waveguide and a ring waveguide",
    "FDTD simulates electromagnetic wave propagation in the time domain",
    "BPM beam propagation method solves paraxial wave equation slowly",
]


class TestTFIDFRetriever:
    """TF-IDF 索引与搜索测试。"""

    def test_index_build(self) -> None:
        """TF-IDF 索引构建后词汇表非空。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        assert len(retriever._vocab) > 0
        assert retriever._tfidf_matrix is not None
        assert retriever._tfidf_matrix.shape == (len(PHOTONICS_DOCS), len(retriever._vocab))

    def test_search_returns_relevant_docs(self) -> None:
        """搜索 waveguide 应返回包含该词的文档。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        results = retriever.search("waveguide", top_k=3)
        assert len(results) > 0
        assert len(results) <= 3
        # 所有返回的得分应为正
        for _, score in results:
            assert score > 0.0

    def test_search_ranking_correctness(self) -> None:
        """搜索 ring resonator 应将 ring resonator 文档排在最前。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        results = retriever.search("ring resonator", top_k=5)
        # ring 文档（索引 2）应在 top 1
        assert results[0][0] == 2
        assert results[0][1] > results[-1][1] if len(results) > 1 else True

    def test_search_top_k_limit(self) -> None:
        """top_k 限制返回数量。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        results = retriever.search("waveguide", top_k=2)
        assert len(results) <= 2

    def test_search_empty_query_raises(self) -> None:
        """空查询应抛 ValueError（fail-fast）。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        with pytest.raises(ValueError, match="查询词为空"):
            retriever.search("")

    def test_search_unknown_terms_raises(self) -> None:
        """查询词全部不在词汇表中应抛 ValueError。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        with pytest.raises(ValueError, match="无匹配"):
            retriever.search("quantum_supremacy_xyzzy")

    def test_empty_documents_raises(self) -> None:
        """空文档集应抛 ValueError。"""
        with pytest.raises(ValueError, match="文档集不能为空"):
            TFIDFRetriever([])

    def test_invalid_top_k_raises(self) -> None:
        """top_k <= 0 应抛 ValueError。"""
        retriever = TFIDFRetriever(PHOTONICS_DOCS)
        with pytest.raises(ValueError, match="top_k"):
            retriever.search("waveguide", top_k=0)


# =============================================================================
# M3: PageRank 收敛性测试
# =============================================================================


class TestPageRank:
    """PageRank 文档重要性排序测试。"""

    def test_simple_convergence(self) -> None:
        """简单图 PageRank 收敛且 PR 值和为 1。"""
        # A -> B -> C -> A 闭环
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        pr = PageRank(edges)
        scores = pr.compute()
        assert len(scores) == 3
        # PR 值和应近似 1（含阻尼项）
        total = sum(scores.values())
        assert math.isclose(total, 1.0, rel_tol=1e-3)
        # 对称图，PR 值应接近相等
        for s in scores.values():
            assert math.isclose(s, 1.0 / 3, abs_tol=1e-3)

    def test_damping_default_value(self) -> None:
        """默认阻尼系数 d=0.85（Page 1998 原始论文值）。"""
        edges = [("A", "B"), ("B", "C")]
        pr = PageRank(edges)
        assert pr.damping == 0.85

    def test_convergence_tolerance(self) -> None:
        """收敛容差默认 1e-6。"""
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        pr = PageRank(edges)
        assert pr.tol == 1e-6
        pr.compute()
        # 应在 max_iter 次内收敛
        assert pr.iterations <= pr.max_iter

    def test_dangling_node_handling(self) -> None:
        """悬挂节点（无出边）应被正确处理（PR 不流失）。"""
        # A -> B -> C, C 无出边（悬挂）
        edges = [("A", "B"), ("B", "C")]
        pr = PageRank(edges)
        scores = pr.compute()
        assert len(scores) == 3
        total = sum(scores.values())
        # 总和应近似 1
        assert math.isclose(total, 1.0, rel_tol=1e-3)

    def test_invalid_damping_raises(self) -> None:
        """阻尼系数不在 (0,1) 应抛 ValueError。"""
        with pytest.raises(ValueError, match="阻尼系数"):
            PageRank([("A", "B")], damping=1.5)
        with pytest.raises(ValueError, match="阻尼系数"):
            PageRank([("A", "B")], damping=0.0)

    def test_empty_edges_raises(self) -> None:
        """空边列表应抛 ValueError。"""
        with pytest.raises(ValueError, match="边列表不能为空"):
            PageRank([])

    def test_self_loop_raises(self) -> None:
        """自环边应抛 ValueError。"""
        with pytest.raises(ValueError, match="自环边"):
            PageRank([("A", "A")])

    def test_higher_indegree_higher_pagerank(self) -> None:
        """被多个节点引用的节点应有更高 PageRank。"""
        # B 被 A 和 C 同时引用，B 的 PR 应高于 A 和 C
        edges = [("A", "B"), ("C", "B"), ("B", "D"), ("D", "A")]
        pr = PageRank(edges)
        scores = pr.compute()
        assert scores["B"] > scores["A"]
        assert scores["B"] > scores["C"]


# =============================================================================
# M4: IRT 三参数逻辑斯蒂模型测试
# =============================================================================


class TestIRT3PL:
    """IRT 3PL 教学评估模型测试。"""

    def test_probability_at_difficulty_equal_ability(self) -> None:
        """θ=b 时，2PL（c=0）的 P=0.5；3PL 时 P=c+0.5(1-c)。"""
        # 2PL: c=0
        p_2pl = IRT3PL.probability(theta=0.0, a=1.0, b=0.0, c=0.0)
        assert math.isclose(float(p_2pl), 0.5, abs_tol=1e-9)
        # 3PL: c=0.2, P = 0.2 + 0.5*0.8 = 0.6
        p_3pl = IRT3PL.probability(theta=0.0, a=1.0, b=0.0, c=0.2)
        assert math.isclose(float(p_3pl), 0.6, abs_tol=1e-9)

    def test_probability_monotonic_in_theta(self) -> None:
        """P(θ) 关于 θ 单调递增。"""
        thetas = np.linspace(-3, 3, 21)
        probs = IRT3PL.probability(thetas, a=1.5, b=0.0, c=0.1)
        diffs = np.diff(probs)
        assert np.all(diffs > 0), "P(θ) 应单调递增"

    def test_probability_bounds(self) -> None:
        """θ→-∞ 时 P→c；θ→+∞ 时 P→1。"""
        # θ=-100 近似 -∞
        p_low = float(IRT3PL.probability(theta=-100.0, a=1.0, b=0.0, c=0.25))
        assert math.isclose(p_low, 0.25, abs_tol=1e-6)
        # θ=+100 近似 +∞
        p_high = float(IRT3PL.probability(theta=100.0, a=1.0, b=0.0, c=0.25))
        assert math.isclose(p_high, 1.0, abs_tol=1e-6)

    def test_invalid_a_raises(self) -> None:
        """a <= 0 应抛 ValueError。"""
        with pytest.raises(ValueError, match="区分度参数 a"):
            IRT3PL(a=0.0)
        with pytest.raises(ValueError, match="区分度参数 a"):
            IRT3PL.probability(theta=0.0, a=-1.0, b=0.0, c=0.0)

    def test_invalid_c_raises(self) -> None:
        """c 不在 [0,1) 应抛 ValueError。"""
        with pytest.raises(ValueError, match="猜测参数 c"):
            IRT3PL(a=1.0, b=0.0, c=1.0)
        with pytest.raises(ValueError, match="猜测参数 c"):
            IRT3PL(a=1.0, b=0.0, c=-0.1)

    def test_classify_level(self) -> None:
        """能力分级阈值正确（对齐 Luceda Academy 三段式）。"""
        assert IRT3PL.classify_level(-2.0) == "beginner"
        assert IRT3PL.classify_level(-1.0) == "intermediate"  # 边界属于中间
        assert IRT3PL.classify_level(0.0) == "intermediate"
        assert IRT3PL.classify_level(1.0) == "intermediate"  # 边界属于中间
        assert IRT3PL.classify_level(2.0) == "advanced"

    def test_estimate_ability_medium(self) -> None:
        """中等难度题目、中等答题表现应估计出 θ ≈ 0 附近。"""
        # 4 道中等难度题目（b=0），答对 2 道
        responses = [1, 0, 1, 0]
        items = [(1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
        theta = IRT3PL.estimate_ability(responses, items)
        assert -1.0 <= theta <= 1.0, f"中等答题应估计为中间能力，实际 θ={theta}"

    def test_estimate_ability_high(self) -> None:
        """简单题目（b=-1）全对 + 中等题目（b=0）答对，θ 应偏高。"""
        responses = [1, 1, 1, 1, 0]
        items = [(1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.0, 0.0)]
        theta = IRT3PL.estimate_ability(responses, items)
        assert theta > 0.0, f"答对较多简单题应估计为较高能力，实际 θ={theta}"

    def test_estimate_ability_length_mismatch_raises(self) -> None:
        """responses 与 items 长度不一致应抛 ValueError。"""
        with pytest.raises(ValueError, match="长度不一致"):
            IRT3PL.estimate_ability([1, 0], [(1.0, 0.0, 0.0)])

    def test_estimate_ability_empty_raises(self) -> None:
        """空答题记录应抛 ValueError。"""
        with pytest.raises(ValueError, match="答题记录不能为空"):
            IRT3PL.estimate_ability([], [])

    def test_estimate_ability_all_correct_raises(self) -> None:
        """全对（极端答题）应抛 ValueError（MLE 不收敛于有限值）。"""
        responses = [1, 1, 1, 1]
        items = [(1.0, 0.0, 0.0)] * 4
        with pytest.raises(ValueError, match="MLE"):
            IRT3PL.estimate_ability(responses, items)

    def test_probability_single_with_instance(self) -> None:
        """使用实例参数的 probability_single 与静态方法一致。"""
        irt = IRT3PL(a=1.5, b=0.5, c=0.2)
        p_inst = irt.probability_single(1.0)
        p_static = float(IRT3PL.probability(1.0, 1.5, 0.5, 0.2))
        assert math.isclose(p_inst, p_static, abs_tol=1e-12)


# =============================================================================
# M5: 模块导入与导出测试
# =============================================================================


class TestModuleExport:
    """模块导出测试。"""

    def test_import_from_top_level(self) -> None:
        """从 polaris.platform 顶层导入四个核心类成功。"""
        from polaris.platform import IRT3PL as I
        from polaris.platform import KnowledgeGraph as K
        from polaris.platform import PageRank as P
        from polaris.platform import TFIDFRetriever as T

        assert I is IRT3PL
        assert K is KnowledgeGraph
        assert P is PageRank
        assert T is TFIDFRetriever
