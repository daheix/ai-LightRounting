"""polaris-gui GUI/Web/教育平台子模块 smoke test。

测试覆盖（≥3 个 smoke test，R13 强制自测）：
- test_module_import: 包加载与 __version__ / __all__ 完整性
- test_layout_editor_api: LayoutEditor 核心功能（add_device/render/undo）
- test_interactive_api: interactive 模块（CommandStack/SnapEngine/MacroIDE/ViewerGuard）
- test_education_knowledge_graph: KnowledgeGraph 构建（add_node/add_edge/bfs）
- test_education_tfidf_retriever: TFIDFRetriever 检索（search 返回 doc_id + score）
- test_education_pagerank: PageRank 排序（compute 返回 dict）
- test_education_irt3pl: IRT3PL 三参数逻辑斯蒂概率计算
- test_lazy_export_raises_on_missing_flow: lazy 导出 WebServer 在 polaris-flow 缺失时 raise

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- KLayout 编辑器文档: https://www.klayout.de/doc-qt5/manual/editor.html
- Manning IR book (TF-IDF): https://nlp.stanford.edu/IR-book/
- PageRank 论文: http://ilpubs.stanford.edu:8090/422/
- Lord IRT 1980（IRT3PL 三参数模型）
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
# polaris-gui 依赖 polaris-flow（WebServer lazy 导出），统一加入 sys.path
_MODULES = Path(__file__).resolve().parents[2]
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# polaris-flow 源码树（WebServer 依赖 polaris_flow.*）
_FLOW_SRC = str(_MODULES / "flow" / "src")
if _FLOW_SRC not in sys.path:
    sys.path.insert(0, _FLOW_SRC)

import polaris_gui  # noqa: E402


def test_module_import() -> None:
    """smoke test 1: 包加载与 __version__ / __all__ 完整性。"""
    assert polaris_gui.__version__ == "5.0.0"
    # 核心版图编辑器 API 必须在 __all__ 中
    required = {
        # 版图编辑器
        "LayoutEditor", "EditorConfig", "DeviceInstance", "DRCHighlight",
        # 交互式编辑
        "ObjectType", "LayoutObject", "evaluate_object",
        "CommandStack", "SnapEngine", "SnapResult",
        "AirlineRouter", "AirlineSegment",
        "MacroIDE", "MacroDebugger", "ViewerGuard",
        # Web Server（lazy 导出）
        "WebServer", "run_server",
        # 教育平台
        "KnowledgeGraph", "KGNode",
        "TFIDFRetriever", "PageRank", "IRT3PL",
    }
    missing = required - set(polaris_gui.__all__)
    assert not missing, f"__all__ 缺少核心 API: {missing}"


def test_layout_editor_api() -> None:
    """smoke test 2: LayoutEditor 核心功能（add_device/render/undo）。"""
    editor = polaris_gui.LayoutEditor()
    assert editor is not None

    # 添加器件（mmi_1x2 在 _DEFAULT_DEVICE_SIZE 中）
    dev_id = editor.add_device(
        device_type="mmi_1x2",
        position=(10.0, 20.0),
        rotation=0.0,
        category="passive",
    )
    assert dev_id >= 0

    # get_device 返回 DeviceInstance
    dev = editor.get_device(dev_id)
    assert dev.device_type == "mmi_1x2"
    assert dev.category == "passive"

    # render() 返回场景 dict（含 devices/routes/drc_highlights/view_transform）
    scene = editor.render()
    assert "devices" in scene
    assert "routes" in scene
    assert "drc_highlights" in scene
    assert "view_transform" in scene
    assert len(scene["devices"]) == 1
    assert scene["devices"][0]["device_id"] == dev_id

    # undo 撤销 add_device
    assert editor.undo() is True
    scene_after_undo = editor.render()
    assert len(scene_after_undo["devices"]) == 0

    # redo 重做
    assert editor.redo() is True
    scene_after_redo = editor.render()
    assert len(scene_after_redo["devices"]) == 1


def test_interactive_api() -> None:
    """smoke test 3: interactive 模块核心类实例化。"""
    # CommandStack 实例化（max_steps 必须 >0）
    stack = polaris_gui.CommandStack(max_steps=50)
    assert stack is not None
    # 非法 max_steps 必须 raise（R03 禁止 fall-back）
    with pytest.raises(ValueError):
        polaris_gui.CommandStack(max_steps=0)

    # SnapEngine 实例化
    snap = polaris_gui.SnapEngine(grid_size=0.1)
    assert snap is not None

    # AirlineRouter 实例化
    router = polaris_gui.AirlineRouter()
    assert router is not None

    # MacroIDE 实例化
    ide = polaris_gui.MacroIDE()
    assert ide is not None

    # ViewerGuard 实例化
    guard = polaris_gui.ViewerGuard()
    assert guard is not None

    # ObjectType 枚举可访问
    assert hasattr(polaris_gui.ObjectType, "POLYGON") or \
        len(list(polaris_gui.ObjectType)) > 0


def test_education_knowledge_graph() -> None:
    """smoke test 4: KnowledgeGraph 构建（add_node/add_edge/bfs）。"""
    kg = polaris_gui.KnowledgeGraph()
    assert kg is not None

    # 添加节点
    kg.add_node("mzi", label="MZI 干涉仪", node_type="device")
    kg.add_node("mmi", label="MMI 耦合器", node_type="device")
    kg.add_node("waveguide", label="波导", node_type="device")

    # 添加边
    kg.add_edge("mzi", "mmi", relation="contains")
    kg.add_edge("mmi", "waveguide", relation="related")

    # 节点数与边数
    assert kg.node_count == 3
    assert kg.edge_count == 2

    # BFS 遍历（从 mzi 出发应能到达所有节点）
    bfs_result = kg.bfs("mzi")
    assert "mzi" in bfs_result
    assert len(bfs_result) == 3

    # 最短路径
    path = kg.shortest_path("mzi", "waveguide")
    assert path[0] == "mzi"
    assert path[-1] == "waveguide"


def test_education_tfidf_retriever() -> None:
    """smoke test 5: TFIDFRetriever 检索（search 返回 doc_id + score）。"""
    documents = [
        "MZI Mach-Zehnder Interferometer photonic integrated circuit",
        "MMI multimode interference coupler silicon photonics",
        "Ring resonator wavelength filter optical",
        "Grating coupler fiber chip coupling",
    ]
    retriever = polaris_gui.TFIDFRetriever(documents)
    assert retriever is not None

    # 检索 "MZI interferometer"
    results = retriever.search("MZI interferometer", top_k=3)
    assert len(results) > 0
    # 结果是 (doc_id, score) 元组列表
    doc_id, score = results[0]
    assert isinstance(doc_id, int)
    assert isinstance(score, float)
    # 第一个结果应是 MZI 文档（doc_id=0）
    assert doc_id == 0
    assert score > 0.0

    # 空文档集必须 raise（R03 禁止 fall-back）
    with pytest.raises(ValueError):
        polaris_gui.TFIDFRetriever([])


def test_education_pagerank() -> None:
    """smoke test 6: PageRank 排序（compute 返回 dict）。"""
    edges = [
        ("A", "B"),
        ("B", "C"),
        ("C", "A"),
        ("A", "C"),
    ]
    pr = polaris_gui.PageRank(edges, damping=0.85)
    assert pr is not None

    # 计算 PageRank
    scores = pr.compute()
    assert isinstance(scores, dict)
    assert len(scores) == 3  # 节点 A/B/C
    # 所有分数之和应接近 1（PageRank 性质）
    total = sum(scores.values())
    assert abs(total - 1.0) < 0.01, f"PageRank 总和应接近 1，实际 {total}"
    # 每个分数为正
    for node, score in scores.items():
        assert score > 0, f"节点 {node} PageRank 为负: {score}"

    # 自环边必须 raise（R03 禁止 fall-back）
    with pytest.raises(ValueError):
        polaris_gui.PageRank([("A", "A")])

    # 空边列表必须 raise
    with pytest.raises(ValueError):
        polaris_gui.PageRank([])


def test_education_irt3pl() -> None:
    """smoke test 7: IRT3PL 三参数逻辑斯蒂概率计算。"""
    # 实例化（a>0, 0<=c<1）
    irt = polaris_gui.IRT3PL(a=1.5, b=0.0, c=0.1)
    assert irt is not None

    # probability_single: theta=b 时 P 应接近 c + (1-c)*0.5 = 0.55
    p = irt.probability_single(0.0)
    assert isinstance(p, float)
    assert 0.0 < p < 1.0
    expected = 0.1 + (1.0 - 0.1) / (1.0 + 1.0)  # c + (1-c)/(1+exp(0)) = 0.55
    assert abs(p - expected) < 1e-6, f"theta=b 时 P 期望 {expected}，实际 {p}"

    # theta >> b 时 P 应接近 1
    p_high = irt.probability_single(10.0)
    assert p_high > 0.99

    # theta << b 时 P 应接近 c
    p_low = irt.probability_single(-10.0)
    assert abs(p_low - 0.1) < 0.01

    # 静态方法 probability 可处理数组
    import numpy as np
    thetas = np.array([-2.0, 0.0, 2.0])
    probs = polaris_gui.IRT3PL.probability(thetas, a=1.5, b=0.0, c=0.1)
    assert probs.shape == (3,)
    # 单调递增（theta 越大，P 越大）
    assert probs[0] < probs[1] < probs[2]

    # 非法参数必须 raise（R03）
    with pytest.raises(ValueError):
        polaris_gui.IRT3PL(a=0, b=0.0, c=0.1)  # a 必须 >0
    with pytest.raises(ValueError):
        polaris_gui.IRT3PL(a=1.0, b=0.0, c=1.0)  # c 必须 <1


def test_lazy_export_raises_on_missing_flow() -> None:
    """smoke test 8: lazy 导出 WebServer 在 polaris-flow 缺失时 raise（R03）。

    polaris-flow 未安装时，访问 WebServer 应 raise ImportError
    （而非返回 None 或假数据）。
    """
    try:
        import polaris_flow  # noqa: F401
        polaris_flow_available = True
    except ImportError:
        polaris_flow_available = False

    if not polaris_flow_available:
        # polaris-flow 缺失：访问 lazy 导出必须 raise（R03）
        with pytest.raises((ImportError, AttributeError)):
            _ = polaris_gui.WebServer
    else:
        # polaris-flow 可用：lazy 导出应正常工作
        assert polaris_gui.WebServer is not None
