"""扩展测试（从 test_gui.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_gui.py。
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


def test_layout_editor_view_and_export() -> None:
    """LayoutEditor: view_transform/world_to_view + export_klayout_script。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 20.0))
    # view_transform 返回 3×3 仿射矩阵
    mat = editor.view_transform((5.0, 5.0), zoom=2.0, rotation=90.0)
    assert mat.shape == (3, 3)
    # world_to_view 应用变换
    points = np.array([[10.0, 20.0]])
    view_pts = editor.world_to_view(points)
    assert view_pts.shape == (1, 2)
    # zoom <=0 → raise
    with pytest.raises(ValueError):
        editor.view_transform((0.0, 0.0), zoom=-1.0)
    # export_klayout_script 生成可执行脚本
    script = editor.export_klayout_script(
        output_gds="test_output.gds", top_cell_name="TOP_CELL"
    )
    assert "import klayout.db as db" in script
    assert "test_output.gds" in script
    assert "TOP_CELL" in script
    assert "ly.dbu" in script
    # 空场景也能导出
    editor2 = LayoutEditor()
    script2 = editor2.export_klayout_script()
    assert "import klayout.db as db" in script2


def test_editor_config_device_drc() -> None:
    """EditorConfig/DeviceInstance/DRCHighlight 数据类默认值与自定义。"""
    # EditorConfig 默认值
    config = EditorConfig()
    assert config.grid_size == 0.1
    assert config.snap_to_grid is True
    assert config.dbu == 0.001
    assert config.min_spacing == 1.0
    assert config.max_undo_steps == 100
    # 自定义配置
    config2 = EditorConfig(
        grid_size=0.5, snap_to_grid=False, dbu=0.01,
        min_spacing=2.0, max_undo_steps=50,
    )
    assert config2.grid_size == 0.5
    assert config2.snap_to_grid is False
    assert config2.dbu == 0.01
    # DeviceInstance
    dev = DeviceInstance(
        device_id=1, device_type="mzi", position=(10.0, 20.0),
        rotation=90.0, size=(30.0, 10.0),
    )
    assert dev.device_id == 1
    assert dev.device_type == "mzi"
    assert dev.position == (10.0, 20.0)
    assert dev.rotation == 90.0
    assert dev.size == (30.0, 10.0)
    assert dev.category == "passive"  # 默认
    assert dev.params == {}  # 默认
    # DRCHighlight 默认 severity
    drc = DRCHighlight(x=5.0, y=10.0, width=2.0, height=2.0, rule="min_spacing")
    assert drc.x == 5.0
    assert drc.severity == "error"  # 默认
    drc2 = DRCHighlight(
        x=0.0, y=0.0, width=1.0, height=1.0,
        rule="width", severity="warning",
    )
    assert drc2.severity == "warning"


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


def test_lazy_export_behavior() -> None:
    """lazy 导出：不存在的属性 raise AttributeError + WebServer 行为。"""
    # 不存在的属性 → AttributeError（R03）
    with pytest.raises(AttributeError):
        _ = polaris_gui.NonExistentAPI
    # WebServer/run_server 在 _LAZY_EXPORTS 中
    assert "WebServer" in polaris_gui._LAZY_EXPORTS
    assert "run_server" in polaris_gui._LAZY_EXPORTS
    # 访问 WebServer：成功（依赖可用）或 raise（依赖缺失）均为 R03 合规
    try:
        ws = polaris_gui.WebServer
        assert ws is not None
    except (ImportError, AttributeError, ModuleNotFoundError):
        pass  # 依赖不可用，R03 合规 raise