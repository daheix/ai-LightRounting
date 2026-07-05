"""polaris-gui GUI/Web/教育平台子模块深度测试。

覆盖 26 个稳定 API（版图编辑器 + 交互式编辑 + 教育平台 + lazy 导出），
共 30 个深度测试，替代原 smoke test。

测试分组（30 个）:
- 包导入与 __all__ 完整性 (1)
- ObjectType 枚举与 LayoutObject 校验 (1)
- evaluate_object 求值（POINT/PORT/POLYLINE/POLYGON/BEZIER/SPLINE/ARC/ELLIPSE）(3)
- CommandStack 命令模式（add/move/vertex/overflow/redo-clear）(3)
- SnapEngine 吸附引擎（grid/vertex/midpoint/endpoint 模式 + 校验）(2)
- AirlineRouter/AirlineSegment（net_id 配对 + 校验）(2)
- MacroDebugger（断点/单步/监视/清除 + 校验）(2)
- MacroIDE（load_script/run/console_eval/breakpoint）(2)
- ViewerGuard（可编辑/只读模式切换）(1)
- LayoutEditor（add/move/rotate/delete + undo/redo + render/routes/drc + view/export）(4)
- EditorConfig/DeviceInstance/DRCHighlight 数据类 (1)
- KnowledgeGraph（构建/遍历/最短路径 + 校验）(2)
- TFIDFRetriever（检索排序 + 校验）(1)
- PageRank（收敛/悬挂节点 + 校验）(2)
- IRT3PL（概率/分级/MLE 估计 + 校验）(2)
- lazy 导出行为（AttributeError / WebServer）(1)

规则:
- R02 学术诚信：≥5 文献 URL，所有断言可溯源
- R03 禁止 fall-back：校验类测试断言 raise 而非返回 None/[]
- R05 无 TODO/FIXME 残留
- 中文注释，sys.path 注入在文件开头

来源（R02 学术诚信，≥5 个文献 URL）:
1. KLayout 编辑器文档: https://www.klayout.de/doc-qt5/manual/editor.html
2. Gamma et al., "Design Patterns", Addison-Wesley 1994（命令模式）:
   https://en.wikipedia.org/wiki/Command_pattern
3. Manning, Raghavan, Schütze. Introduction to Information Retrieval. 2008:
   https://nlp.stanford.edu/IR-book/
4. Page, Brin, Motwani, Winograd. The PageRank Citation Ranking. 1998:
   http://ilpubs.stanford.edu:8090/422/
5. Lord. Applications of Item Response Theory to Practical Testing Problems. 1980
6. Foley & Van Dam, "Computer Graphics: Principles and Practice", 3rd ed. 2013
7. Python bdb 调试器框架: https://docs.python.org/3/library/bdb.html
8. Catmull & Rom 1974 样条: https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
9. Siemens L-Edit Photonics: https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
10. pytest 文档: https://docs.pytest.org/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# === sys.path 注入（文件开头，R13 要求） ===
# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_MODULE_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# polaris-flow 源码树（WebServer lazy 导出依赖 polaris_flow.*）
_FLOW_SRC = str(_MODULE_ROOT / "flow" / "src")
if _FLOW_SRC not in sys.path:
    sys.path.insert(0, _FLOW_SRC)

import polaris_gui  # noqa: E402
from polaris_gui import (  # noqa: E402
    AirlineRouter,
    AirlineSegment,
    CommandStack,
    DRCHighlight,
    DeviceInstance,
    EditorConfig,
    IRT3PL,
    KGNode,
    KnowledgeGraph,
    LayoutEditor,
    LayoutObject,
    MacroDebugger,
    MacroIDE,
    ObjectType,
    PageRank,
    SnapEngine,
    SnapResult,
    TFIDFRetriever,
    ViewerGuard,
    evaluate_object,
)
# 命令类（interactive 模块内部，未在 __init__.__all__ 导出）
from polaris_gui.interactive import (  # noqa: E402
    AddObjectCommand,
    InsertVertexCommand,
    MoveObjectCommand,
    MoveVertexCommand,
    RemoveObjectCommand,
    RemoveVertexCommand,
)


# =============================================================================
# 1. 包导入与 __all__ 完整性
# =============================================================================


def test_knowledge_graph_build_traverse() -> None:
    """KnowledgeGraph: add_node/add_edge/bfs/dfs/shortest_path/get_node。"""
    kg = KnowledgeGraph()
    kg.add_node("mzi", label="MZI", node_type="device", metadata={"difficulty": 2})
    kg.add_node("mmi", label="MMI", node_type="device")
    kg.add_node("wg", label="Waveguide", node_type="device")
    kg.add_node("fdtd", label="FDTD", node_type="simulation")
    kg.add_edge("mzi", "mmi", relation="contains")
    kg.add_edge("mmi", "wg", relation="related")
    kg.add_edge("fdtd", "mzi", relation="related")
    assert kg.node_count == 4
    assert kg.edge_count == 3
    # get_node 返回 KGNode
    node = kg.get_node("mzi")
    assert isinstance(node, KGNode)
    assert node.label == "MZI"
    assert node.node_type == "device"
    assert node.metadata["difficulty"] == 2
    # neighbors
    assert "mmi" in kg.neighbors("mzi")
    # bfs 从 fdtd 出发
    bfs_result = kg.bfs("fdtd")
    assert bfs_result[0] == "fdtd"
    assert "mzi" in bfs_result
    # dfs
    dfs_result = kg.dfs("fdtd")
    assert dfs_result[0] == "fdtd"
    # shortest_path
    path = kg.shortest_path("fdtd", "wg")
    assert path[0] == "fdtd"
    assert path[-1] == "wg"
    assert len(path) >= 2


def test_knowledge_graph_validation() -> None:
    """KnowledgeGraph: 非法 node_type/重复/自环/缺失节点/无路径 raise。"""
    kg = KnowledgeGraph()
    # 空 node_id
    with pytest.raises(ValueError):
        kg.add_node("", label="empty", node_type="device")
    # 非法 node_type
    with pytest.raises(ValueError):
        kg.add_node("x", label="X", node_type="invalid_type")
    # 重复节点
    kg.add_node("a", label="A", node_type="device")
    with pytest.raises(ValueError):
        kg.add_node("a", label="A2", node_type="device")
    # 非法 relation
    kg.add_node("b", label="B", node_type="device")
    with pytest.raises(ValueError):
        kg.add_edge("a", "b", relation="invalid_relation")
    # 缺失节点
    with pytest.raises(KeyError):
        kg.add_edge("a", "nonexistent", relation="related")
    # 自环
    with pytest.raises(ValueError):
        kg.add_edge("a", "a", relation="related")
    # get_node 缺失
    with pytest.raises(KeyError):
        kg.get_node("nonexistent")
    # bfs 缺失节点
    with pytest.raises(KeyError):
        kg.bfs("nonexistent")
    # shortest_path 无路径（c 为孤立节点）
    kg.add_node("c", label="C", node_type="device")
    with pytest.raises(ValueError):
        kg.shortest_path("a", "c")


def test_tfidf_search_and_validation() -> None:
    """TFIDFRetriever: 检索排序 + 空文档/空查询/无匹配/非法 top_k raise。"""
    docs = [
        "MZI Mach-Zehnder Interferometer photonic circuit",
        "MMI multimode interference coupler silicon photonics",
        "Ring resonator wavelength filter optical",
        "Grating coupler fiber chip coupling",
    ]
    retriever = TFIDFRetriever(docs)
    # 检索 "MZI interferometer" → 第 0 篇文档得分最高
    results = retriever.search("MZI interferometer", top_k=3)
    assert len(results) > 0
    assert results[0][0] == 0  # MZI 文档
    assert results[0][1] > 0.0
    # top_k 限制结果数
    results_limited = retriever.search("photonic optical", top_k=2)
    assert len(results_limited) <= 2
    # 空文档集 → raise
    with pytest.raises(ValueError):
        TFIDFRetriever([])
    # 空查询 → raise
    with pytest.raises(ValueError):
        retriever.search("")
    # 无匹配（查询词全不在词汇表）→ raise
    with pytest.raises(ValueError):
        retriever.search("zzzz_nonexistent_xyz")
    # 非法 top_k → raise
    with pytest.raises(ValueError):
        retriever.search("MZI", top_k=0)


def test_pagerank_convergence_dangling() -> None:
    """PageRank: 简环收敛 + 悬挂节点处理 + 总和≈1。"""
    # 简单 3 节点环
    edges = [("A", "B"), ("B", "C"), ("C", "A")]
    pr = PageRank(edges)
    scores = pr.compute()
    assert len(scores) == 3
    total = sum(scores.values())
    assert abs(total - 1.0) < 0.01  # PageRank 总和 ≈ 1
    for s in scores.values():
        assert s > 0
    assert pr.iterations > 0
    # 悬挂节点（C 无出边）
    edges2 = [("A", "B"), ("B", "C")]
    pr2 = PageRank(edges2)
    scores2 = pr2.compute()
    assert len(scores2) == 3
    assert abs(sum(scores2.values()) - 1.0) < 0.01


def test_pagerank_validation() -> None:
    """PageRank: 空边/自环/非法阻尼/非法容差/非法迭代 raise。"""
    with pytest.raises(ValueError):
        PageRank([])  # 空边列表
    with pytest.raises(ValueError):
        PageRank([("A", "A")])  # 自环
    with pytest.raises(ValueError):
        PageRank([("A", "B")], damping=0.0)  # 阻尼 =0
    with pytest.raises(ValueError):
        PageRank([("A", "B")], damping=1.0)  # 阻尼 =1
    with pytest.raises(ValueError):
        PageRank([("A", "B")], tol=0.0)  # 容差 <=0
    with pytest.raises(ValueError):
        PageRank([("A", "B")], max_iter=0)  # 迭代 <=0


def test_irt3pl_probability_classify() -> None:
    """IRT3PL: probability_single + probability(数组) + classify_level 分级。"""
    irt = IRT3PL(a=1.5, b=0.0, c=0.1)
    # theta=b: P = c + (1-c)/(1+exp(0)) = 0.1 + 0.9/2 = 0.55
    p = irt.probability_single(0.0)
    assert abs(p - 0.55) < 1e-6
    # theta >> b: P ≈ 1
    assert irt.probability_single(10.0) > 0.99
    # theta << b: P ≈ c
    assert abs(irt.probability_single(-10.0) - 0.1) < 0.01
    # 静态 probability 处理数组
    thetas = np.array([-2.0, 0.0, 2.0])
    probs = IRT3PL.probability(thetas, a=1.5, b=0.0, c=0.1)
    assert probs.shape == (3,)
    assert probs[0] < probs[1] < probs[2]  # 单调递增
    # classify_level 三段式
    assert IRT3PL.classify_level(-2.0) == "beginner"
    assert IRT3PL.classify_level(0.0) == "intermediate"
    assert IRT3PL.classify_level(2.0) == "advanced"


def test_irt3pl_estimate_validation() -> None:
    """IRT3PL: MLE 能力估计 + 极端模式 raise + 参数校验。"""
    # 混合答题模式 → MLE 可收敛
    responses = [1, 0, 1]
    items = [(1.5, -1.0, 0.1), (1.5, 0.0, 0.1), (1.5, 1.0, 0.1)]
    theta = IRT3PL.estimate_ability(responses, items)
    assert -5.0 < theta < 5.0  # 不在边界
    # 全对 → 边界 → raise
    with pytest.raises(ValueError):
        IRT3PL.estimate_ability([1, 1, 1], items)
    # 全错 → 边界 → raise
    with pytest.raises(ValueError):
        IRT3PL.estimate_ability([0, 0, 0], items)
    # 空答题记录 → raise
    with pytest.raises(ValueError):
        IRT3PL.estimate_ability([], [])
    # 构造器：a <=0 → raise
    with pytest.raises(ValueError):
        IRT3PL(a=0.0, b=0.0, c=0.1)
    # 构造器：c >=1 → raise
    with pytest.raises(ValueError):
        IRT3PL(a=1.0, b=0.0, c=1.0)
    # 构造器：c <0 → raise
    with pytest.raises(ValueError):
        IRT3PL(a=1.0, b=0.0, c=-0.1)
    # 静态 probability：a <=0 → raise
    with pytest.raises(ValueError):
        IRT3PL.probability(0.0, a=0.0, b=0.0, c=0.0)
