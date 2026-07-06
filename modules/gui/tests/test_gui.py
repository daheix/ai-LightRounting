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


def test_module_import_and_all() -> None:
    """包加载、__version__ 与 __all__ 核心 API 完整性。"""
    assert polaris_gui.__version__ == "5.0.0"
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


# =============================================================================
# 2. ObjectType 枚举与 LayoutObject 校验
# =============================================================================


def test_object_type_and_layout_object() -> None:
    """ObjectType 枚举 8 个值 + LayoutObject 校验（obj_id/obj_type）。"""
    # 枚举值完整性（对齐 KLayout Shapes + L-Edit Drawing Tools）
    expected = {
        ObjectType.POINT, ObjectType.POLYLINE, ObjectType.POLYGON,
        ObjectType.BEZIER, ObjectType.SPLINE, ObjectType.ARC,
        ObjectType.ELLIPSE, ObjectType.PORT,
    }
    assert set(ObjectType) == expected
    assert len(list(ObjectType)) == 8
    # LayoutObject 有效构造
    obj = LayoutObject(obj_id=1, obj_type="point", points=[(0.0, 0.0)])
    assert obj.obj_id == 1
    assert obj.layer == "WG"  # 默认图层
    # obj_id 必须 >0
    with pytest.raises(ValueError):
        LayoutObject(obj_id=0, obj_type="point")
    with pytest.raises(ValueError):
        LayoutObject(obj_id=-1, obj_type="point")
    # obj_type 必须在枚举中
    with pytest.raises(ValueError):
        LayoutObject(obj_id=1, obj_type="unknown_type")


# =============================================================================
# 3. evaluate_object 求值（8 种对象类型）
# =============================================================================


def test_evaluate_point_polyline_polygon() -> None:
    """evaluate_object: POINT/PORT 返回单点；POLYLINE 开放；POLYGON 闭合。"""
    # POINT 返回单个点
    p = LayoutObject(obj_id=1, obj_type="point", points=[(5.0, 5.0)])
    assert evaluate_object(p) == [(5.0, 5.0)]
    # PORT 返回端口位置
    port = LayoutObject(obj_id=2, obj_type="port", points=[(10.0, 20.0)])
    assert evaluate_object(port) == [(10.0, 20.0)]
    # POLYLINE 开放折线（不闭合）
    pl = LayoutObject(
        obj_id=3, obj_type="polyline",
        points=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)],
    )
    result_pl = evaluate_object(pl)
    assert len(result_pl) == 3  # 不闭合，3 个顶点
    assert result_pl[0] == (0.0, 0.0)
    assert result_pl[-1] == (10.0, 10.0)
    # POLYGON 闭合多边形（追加首点闭合）
    pg = LayoutObject(
        obj_id=4, obj_type="polygon",
        points=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)],
    )
    result_pg = evaluate_object(pg)
    assert len(result_pg) == 4  # 3 顶点 + 闭合首点
    assert result_pg[0] == result_pg[-1]
    # POINT 无 points → raise（R03）
    with pytest.raises(ValueError):
        evaluate_object(LayoutObject(obj_id=5, obj_type="point"))
    # POLYLINE 顶点 <2 → raise
    with pytest.raises(ValueError):
        evaluate_object(
            LayoutObject(obj_id=6, obj_type="polyline", points=[(0.0, 0.0)])
        )


def test_evaluate_bezier_and_spline() -> None:
    """evaluate_object: BEZIER (De Casteljau) 线性插值 + SPLINE (Catmull-Rom)。"""
    # BEZIER 两控制点 → 线性插值（端点为控制点端点）
    bz = LayoutObject(
        obj_id=1, obj_type="bezier", points=[(0.0, 0.0), (10.0, 10.0)]
    )
    result = evaluate_object(bz, n_samples=10)
    assert len(result) == 11  # n_samples + 1
    assert result[0] == (0.0, 0.0)
    assert result[-1] == (10.0, 10.0)
    # t=0.5 中点 = (5, 5)
    mid = result[5]
    assert abs(mid[0] - 5.0) < 1e-6
    assert abs(mid[1] - 5.0) < 1e-6
    # BEZIER 四控制点（三次贝塞尔）
    bz2 = LayoutObject(
        obj_id=2, obj_type="bezier",
        points=[(0.0, 0.0), (3.0, 10.0), (7.0, 10.0), (10.0, 0.0)],
    )
    result2 = evaluate_object(bz2, n_samples=4)
    assert len(result2) == 5
    assert result2[0] == (0.0, 0.0)
    assert result2[-1] == (10.0, 0.0)
    # SPLINE Catmull-Rom：穿过所有控制点
    sp = LayoutObject(
        obj_id=3, obj_type="spline",
        points=[(0.0, 0.0), (5.0, 5.0), (10.0, 0.0)],
    )
    result_sp = evaluate_object(sp, n_samples=10)
    # 2 段 × 10 采样 + 1 端点 = 21
    assert len(result_sp) == 21
    assert result_sp[0] == (0.0, 0.0)
    assert result_sp[-1] == (10.0, 0.0)
    # BEZIER 控制点 <2 → raise
    with pytest.raises(ValueError):
        evaluate_object(
            LayoutObject(obj_id=4, obj_type="bezier", points=[(0.0, 0.0)])
        )


def test_evaluate_arc_and_ellipse() -> None:
    """evaluate_object: ARC 圆弧 + ELLIPSE 椭圆参数曲线采样。"""
    # ARC 整圆（0°→360°），半径 5
    arc = LayoutObject(
        obj_id=1, obj_type="arc", points=[],
        attrs={"center": (0.0, 0.0), "radius": 5.0,
               "start_angle": 0.0, "end_angle": 360.0},
    )
    result = evaluate_object(arc, n_samples=4)
    assert len(result) == 5  # n_samples + 1
    # 0° → (5, 0)
    assert abs(result[0][0] - 5.0) < 1e-6
    assert abs(result[0][1]) < 1e-6
    # ELLIPSE 整椭圆，a=3 b=2
    ell = LayoutObject(
        obj_id=2, obj_type="ellipse", points=[],
        attrs={"center": (0.0, 0.0), "a": 3.0, "b": 2.0,
               "start_angle": 0.0, "end_angle": 360.0},
    )
    result_ell = evaluate_object(ell, n_samples=4)
    assert len(result_ell) == 5
    # 0° → (3, 0)
    assert abs(result_ell[0][0] - 3.0) < 1e-6
    assert abs(result_ell[0][1]) < 1e-6
    # 四分之一弧（0°→90°），半径 1
    arc_q = LayoutObject(
        obj_id=3, obj_type="arc", points=[],
        attrs={"center": (0.0, 0.0), "radius": 1.0,
               "start_angle": 0.0, "end_angle": 90.0},
    )
    result_q = evaluate_object(arc_q, n_samples=2)
    assert len(result_q) == 3
    assert abs(result_q[0][0] - 1.0) < 1e-6  # 0° → (1, 0)
    assert abs(result_q[-1][1] - 1.0) < 1e-6  # 90° → (0, 1)
    # n_samples <1 → raise
    with pytest.raises(ValueError):
        evaluate_object(arc, n_samples=0)


# =============================================================================
# 4. CommandStack 命令模式（Gamma 1994）
# =============================================================================


def test_command_stack_add_move() -> None:
    """CommandStack: AddObjectCommand + MoveObjectCommand undo/redo。"""
    stack = CommandStack(max_steps=50)
    scene: dict[int, LayoutObject] = {}
    # 非法 max_steps → raise（R03）
    with pytest.raises(ValueError):
        CommandStack(max_steps=0)
    # 添加对象
    obj = LayoutObject(obj_id=1, obj_type="point", points=[(0.0, 0.0)])
    stack.execute(AddObjectCommand(obj), scene)
    assert 1 in scene
    assert stack.undo_depth == 1
    assert stack.redo_depth == 0
    # 撤销添加
    assert stack.undo(scene) is True
    assert 1 not in scene
    assert stack.redo_depth == 1
    # 重做添加
    assert stack.redo(scene) is True
    assert 1 in scene
    assert stack.redo_depth == 0
    # 移动对象
    move_cmd = MoveObjectCommand(obj_id=1, dx=5.0, dy=10.0)
    stack.execute(move_cmd, scene)
    assert scene[1].points[0] == (5.0, 10.0)
    # 撤销移动
    stack.undo(scene)
    assert scene[1].points[0] == (0.0, 0.0)
    # 重做移动
    stack.redo(scene)
    assert scene[1].points[0] == (5.0, 10.0)
    # 空栈 undo/redo 返回 False
    stack2 = CommandStack()
    assert stack2.undo({}) is False
    assert stack2.redo({}) is False


def test_command_stack_vertex_commands() -> None:
    """CommandStack: InsertVertex/RemoveVertex/MoveVertex 命令。"""
    stack = CommandStack()
    scene: dict[int, LayoutObject] = {}
    obj = LayoutObject(
        obj_id=1, obj_type="polyline",
        points=[(0.0, 0.0), (10.0, 0.0)],
    )
    stack.execute(AddObjectCommand(obj), scene)
    # 插入顶点
    insert_cmd = InsertVertexCommand(obj_id=1, index=1, vertex=(5.0, 5.0))
    stack.execute(insert_cmd, scene)
    assert scene[1].points == [(0.0, 0.0), (5.0, 5.0), (10.0, 0.0)]
    stack.undo(scene)
    assert scene[1].points == [(0.0, 0.0), (10.0, 0.0)]
    stack.redo(scene)
    assert scene[1].points == [(0.0, 0.0), (5.0, 5.0), (10.0, 0.0)]
    # 移动顶点
    move_vtx = MoveVertexCommand(
        obj_id=1, index=1, old_vertex=(5.0, 5.0), new_vertex=(7.0, 7.0)
    )
    stack.execute(move_vtx, scene)
    assert scene[1].points[1] == (7.0, 7.0)
    stack.undo(scene)
    assert scene[1].points[1] == (5.0, 5.0)
    # 删除顶点
    remove_vtx = RemoveVertexCommand(obj_id=1, index=1, vertex=(5.0, 5.0))
    stack.execute(remove_vtx, scene)
    assert len(scene[1].points) == 2
    stack.undo(scene)
    assert len(scene[1].points) == 3
    # 仅 2 顶点时删除 → raise（至少保留 2 个）
    obj2 = LayoutObject(
        obj_id=2, obj_type="polyline", points=[(0.0, 0.0), (10.0, 0.0)]
    )
    stack.execute(AddObjectCommand(obj2), scene)
    with pytest.raises(ValueError):
        stack.execute(
            RemoveVertexCommand(obj_id=2, index=0, vertex=(0.0, 0.0)), scene
        )
    # 非折线/多边形插入顶点 → raise
    obj3 = LayoutObject(obj_id=3, obj_type="point", points=[(0.0, 0.0)])
    stack.execute(AddObjectCommand(obj3), scene)
    with pytest.raises(ValueError):
        stack.execute(
            InsertVertexCommand(obj_id=3, index=0, vertex=(1.0, 1.0)), scene
        )


def test_command_stack_overflow_and_redo_clear() -> None:
    """CommandStack: max_steps 溢出淘汰 + 新命令清空 redo 栈。"""
    stack = CommandStack(max_steps=3)
    scene: dict[int, LayoutObject] = {}
    for i in range(1, 5):
        stack.execute(
            AddObjectCommand(
                LayoutObject(obj_id=i, obj_type="point", points=[(0.0, 0.0)])
            ),
            scene,
        )
    # max_steps=3，4 条命令后 undo 栈仅保留最近 3 条
    assert stack.undo_depth == 3
    # 4 个对象都在场景中
    assert len(scene) == 4
    # 撤销 1 条 → redo 栈有 1 条
    stack.undo(scene)
    assert stack.redo_depth == 1
    assert 4 not in scene
    # 新命令清空 redo 栈
    stack.execute(
        AddObjectCommand(
            LayoutObject(obj_id=10, obj_type="point", points=[(0.0, 0.0)])
        ),
        scene,
    )
    assert stack.redo_depth == 0


# =============================================================================
# 5. SnapEngine 吸附引擎
# =============================================================================


def test_snap_engine_modes() -> None:
    """SnapEngine: grid/vertex/midpoint/endpoint 四种吸附模式。"""
    # grid 模式（无对象在阈值内）
    engine = SnapEngine(grid_size=1.0, threshold=0.5)
    result = engine.snap((10.3, 20.6))
    assert isinstance(result, SnapResult)
    assert result.mode == "grid"
    assert result.point == (10.0, 21.0)
    # vertex 模式（对象顶点在阈值内）
    obj = LayoutObject(
        obj_id=1, obj_type="polyline", points=[(10.4, 20.5)]
    )
    result_v = engine.snap((10.3, 20.6), objects=[obj])
    assert result_v.mode == "vertex"
    assert result_v.point == (10.4, 20.5)
    # midpoint 模式
    obj2 = LayoutObject(
        obj_id=2, obj_type="polyline", points=[(0.0, 0.0), (10.0, 0.0)]
    )
    engine_mid = SnapEngine(grid_size=1.0, threshold=0.5, modes=["midpoint", "grid"])
    result_m = engine_mid.snap((5.1, 0.0), objects=[obj2])
    assert result_m.mode == "midpoint"
    assert result_m.point == (5.0, 0.0)
    # endpoint 模式
    engine_ep = SnapEngine(grid_size=1.0, threshold=0.5, modes=["endpoint", "grid"])
    result_e = engine_ep.snap((0.1, 0.0), objects=[obj2])
    assert result_e.mode == "endpoint"
    assert result_e.point == (0.0, 0.0)
    # 无模式 → none
    engine_none = SnapEngine(grid_size=1.0, modes=[])
    result_n = engine_none.snap((10.3, 20.6))
    assert result_n.mode == "none"
    assert result_n.point == (10.3, 20.6)


def test_snap_engine_validation() -> None:
    """SnapEngine: 非法参数与未知模式 raise（R03）。"""
    # grid_size <=0
    with pytest.raises(ValueError):
        SnapEngine(grid_size=0.0)
    with pytest.raises(ValueError):
        SnapEngine(grid_size=-1.0)
    # threshold <0
    with pytest.raises(ValueError):
        SnapEngine(grid_size=1.0, threshold=-1.0)
    # 未知模式 → _snap_mode raise
    engine = SnapEngine(grid_size=1.0, modes=["unknown_mode"])
    with pytest.raises(ValueError):
        engine.snap((0.0, 0.0))


# =============================================================================
# 6. AirlineRouter / AirlineSegment
# =============================================================================


def test_airline_router_pairing() -> None:
    """AirlineRouter: 同 net_id 端口顺序配对生成飞线段。"""
    router = AirlineRouter()
    # 4 个端口，2 个 net（A/B），每 net 2 端口
    p1 = LayoutObject(obj_id=1, obj_type="port", points=[(0.0, 0.0)],
                      attrs={"net_id": "A"})
    p2 = LayoutObject(obj_id=2, obj_type="port", points=[(10.0, 0.0)],
                      attrs={"net_id": "A"})
    p3 = LayoutObject(obj_id=3, obj_type="port", points=[(20.0, 0.0)],
                      attrs={"net_id": "B"})
    p4 = LayoutObject(obj_id=4, obj_type="port", points=[(30.0, 0.0)],
                      attrs={"net_id": "B"})
    segments = router.route([p1, p2, p3, p4])
    assert len(segments) == 2  # A: 1-2, B: 3-4
    # 按端口 ID 排序配对
    net_a = [s for s in segments if s.net_id == "A"]
    net_b = [s for s in segments if s.net_id == "B"]
    assert len(net_a) == 1
    assert len(net_b) == 1
    assert isinstance(net_a[0], AirlineSegment)
    assert net_a[0].start == (0.0, 0.0)
    assert net_a[0].end == (10.0, 0.0)
    # 3 端口同 net → 链式配对（P5-P6, P6-P7）
    p5 = LayoutObject(obj_id=5, obj_type="port", points=[(0.0, 0.0)],
                      attrs={"net_id": "C"})
    p6 = LayoutObject(obj_id=6, obj_type="port", points=[(10.0, 0.0)],
                      attrs={"net_id": "C"})
    p7 = LayoutObject(obj_id=7, obj_type="port", points=[(20.0, 0.0)],
                      attrs={"net_id": "C"})
    segments2 = router.route([p5, p6, p7])
    net_c = [s for s in segments2 if s.net_id == "C"]
    assert len(net_c) == 2  # 5-6, 6-7
    # 显式 netlist
    segments3 = router.route([p1, p2], netlist={"A": [1, 2]})
    assert len(segments3) == 1
    assert segments3[0].net_id == "A"


def test_airline_router_validation() -> None:
    """AirlineRouter: 非 PORT 对象/空位置/缺 net_id/不存在端口 raise。"""
    router = AirlineRouter()
    # 非 PORT 对象 → raise
    obj = LayoutObject(obj_id=1, obj_type="point", points=[(0.0, 0.0)])
    with pytest.raises(ValueError):
        router.route([obj])
    # PORT 无 points → raise
    p_empty = LayoutObject(obj_id=2, obj_type="port", points=[])
    with pytest.raises(ValueError):
        router.route([p_empty])
    # PORT 缺 net_id（推断 netlist 时）→ raise
    p_no_net = LayoutObject(obj_id=3, obj_type="port", points=[(0.0, 0.0)])
    with pytest.raises(ValueError):
        router.route([p_no_net])
    # 显式 netlist 引用不存在的端口 → raise
    p1 = LayoutObject(obj_id=1, obj_type="port", points=[(0.0, 0.0)],
                      attrs={"net_id": "A"})
    with pytest.raises(KeyError):
        router.route([p1], netlist={"A": [1, 99]})


# =============================================================================
# 7. MacroDebugger（sys.settrace 行级跟踪，bdb 底层机制）
# =============================================================================


def test_macro_debugger_breakpoint() -> None:
    """MacroDebugger: 设置断点、运行命中、监视表达式求值。"""
    debugger = MacroDebugger()
    source = "x = 1\ny = 2\nz = x + y\n"
    filename = "<test_breakpoint>"
    code_obj = compile(source, filename, "exec")
    # 在第 2 行设断点
    debugger.set_breakpoint(filename, 2)
    debugger.add_watch("x")
    paused = debugger.run(code_obj, {"__name__": "__test__"}, step_mode="continue")
    # 命中断点
    assert paused is True
    assert debugger.paused_at == (filename, 2)
    # 第 1 行已执行，第 2 行暂停（line 事件在执行前触发）
    assert (filename, 1) in debugger.executed_lines
    assert (filename, 2) in debugger.executed_lines
    # 第 3 行未执行
    assert (filename, 3) not in debugger.executed_lines
    # 监视 x：在第 2 行时 x=1（第 1 行已赋值）
    assert debugger.watch_values["x"] == 1
    # 断点存在性
    assert (filename, 2) in debugger.breakpoints


def test_macro_debugger_step_and_watch() -> None:
    """MacroDebugger: step 模式首行暂停 + watch/clear + 校验。"""
    debugger = MacroDebugger()
    source = "a = 10\nb = 20\nc = 30\n"
    filename = "<test_step>"
    code_obj = compile(source, filename, "exec")
    debugger.add_watch("a")
    # step 模式：首行即暂停
    paused = debugger.run(code_obj, {"__name__": "__test__"}, step_mode="continue")
    # 改用 step 模式
    debugger2 = MacroDebugger()
    debugger2.add_watch("a")
    paused2 = debugger2.run(code_obj, {"__name__": "__test2"}, step_mode="step")
    assert paused2 is True
    assert debugger2.paused_at == (filename, 1)
    # 第 1 行尚未执行，a 未定义 → watch 返回错误字符串
    assert "a" in debugger2.watch_values
    assert isinstance(debugger2.watch_values["a"], str)
    assert "error" in debugger2.watch_values["a"].lower()
    # clear_watches
    debugger2.clear_watches()
    assert debugger2.watch_values == {}
    # set/clear breakpoint
    debugger2.set_breakpoint(filename, 1)
    assert (filename, 1) in debugger2.breakpoints
    debugger2.clear_breakpoint(filename, 1)
    assert (filename, 1) not in debugger2.breakpoints
    # 重复 clear → raise
    with pytest.raises(KeyError):
        debugger2.clear_breakpoint(filename, 1)
    # 非法 step_mode → raise
    with pytest.raises(ValueError):
        debugger2.run(code_obj, {"__name__": "__test3"}, step_mode="invalid")
    # 非法断点行号 → raise
    with pytest.raises(ValueError):
        debugger2.set_breakpoint(filename, 0)
    # 非法断点条件 → raise
    with pytest.raises(ValueError):
        debugger2.set_breakpoint(filename, 1, cond="")
    # 非法监视表达式 → raise
    with pytest.raises(ValueError):
        debugger2.add_watch("")


# =============================================================================
# 8. MacroIDE（KLayout Macro IDE 风格）
# =============================================================================


def test_macro_ide_load_run_console() -> None:
    """MacroIDE: load_script + run + console_eval（表达式/语句）。"""
    ide = MacroIDE()
    source = "result = 40 + 2\n"
    ide.load_script("test_macro.py", source)
    # 无断点运行到结束
    paused = ide.run(step_mode="continue")
    assert paused is False
    assert ide.namespace["result"] == 42
    # console_eval 表达式
    val = ide.console_eval("result + 8")
    assert val == 50
    # console_eval 语句（赋值）
    ret = ide.console_eval("result = 100")
    assert ret is None
    assert ide.namespace["result"] == 100
    # debugger 属性可访问
    assert ide.debugger is not None
    # load_script 校验
    with pytest.raises(ValueError):
        ide.load_script("x.py", "")
    with pytest.raises(ValueError):
        ide.load_script("x.py", "   ")
    # console_eval 校验
    with pytest.raises(ValueError):
        ide.console_eval("")
    # 未加载脚本时 run → raise
    ide2 = MacroIDE()
    with pytest.raises(RuntimeError):
        ide2.run()


def test_macro_ide_breakpoint() -> None:
    """MacroIDE: 通过 IDE 设置断点 + 运行命中。"""
    ide = MacroIDE()
    source = "x = 1\ny = 2\nz = 3\n"
    ide.load_script("test_bp.py", source)
    ide.set_breakpoint(2)  # 第 2 行
    ide.add_watch("x")
    paused = ide.run(step_mode="continue")
    assert paused is True
    assert ide.paused_at == ("test_bp.py", 2)
    # 第 1 行已执行 x=1
    assert ide.watch_values["x"] == 1
    # 清除断点
    ide.clear_breakpoint(2)
    # 未加载脚本时 set_breakpoint → raise
    ide2 = MacroIDE()
    with pytest.raises(RuntimeError):
        ide2.set_breakpoint(1)


# =============================================================================
# 9. ViewerGuard（查看器只读模式守卫）
# =============================================================================


def test_viewer_guard_modes() -> None:
    """ViewerGuard: 默认可编辑 + 切换只读模式 + require_editable 守卫。"""
    # 默认可编辑
    guard = ViewerGuard()
    assert guard.viewer_mode is False
    guard.require_editable()  # 不 raise
    # 切换到只读模式
    guard.set_viewer_mode(True)
    assert guard.viewer_mode is True
    with pytest.raises(PermissionError):
        guard.require_editable()
    # 切回可编辑
    guard.set_viewer_mode(False)
    assert guard.viewer_mode is False
    guard.require_editable()  # 不 raise
    # 构造时指定只读
    guard_ro = ViewerGuard(viewer_mode=True)
    assert guard_ro.viewer_mode is True
    with pytest.raises(PermissionError):
        guard_ro.require_editable()


# =============================================================================
# 10. LayoutEditor（L-Edit 风格版图编辑器）
# =============================================================================


def test_layout_editor_device_ops() -> None:
    """LayoutEditor: add/move/rotate/delete + 网格吸附 + get_device。"""
    # 网格吸附测试（grid_size=1.0）
    editor = LayoutEditor(EditorConfig(grid_size=1.0, snap_to_grid=True))
    dev_id = editor.add_device("mzi", (10.6, 20.3))
    assert dev_id >= 1
    dev = editor.get_device(dev_id)
    assert dev.device_type == "mzi"
    assert dev.position == (11.0, 20.0)  # 吸附到 1.0 网格
    assert dev.category == "passive"
    # 不吸附模式
    editor_ns = LayoutEditor(EditorConfig(snap_to_grid=False))
    dev_id2 = editor_ns.add_device("ring_resonator", (10.6, 20.3))
    assert editor_ns.get_device(dev_id2).position == (10.6, 20.3)
    # move_device
    editor.move_device(dev_id, (30.0, 40.0))
    assert editor.get_device(dev_id).position == (30.0, 40.0)
    # rotate_device
    editor.rotate_device(dev_id, 90.0)
    assert editor.get_device(dev_id).rotation == 90.0
    # 再次旋转叠加
    editor.rotate_device(dev_id, 45.0)
    assert editor.get_device(dev_id).rotation == 135.0
    # delete_device
    editor.delete_device(dev_id)
    with pytest.raises(KeyError):
        editor.get_device(dev_id)
    # get_device 不存在 → raise（R03）
    with pytest.raises(KeyError):
        editor.get_device(999)
    # move/rotate/delete 不存在 → raise
    with pytest.raises(KeyError):
        editor.move_device(999, (0.0, 0.0))
    with pytest.raises(KeyError):
        editor.rotate_device(999, 0.0)
    with pytest.raises(KeyError):
        editor.delete_device(999)


def test_layout_editor_undo_redo() -> None:
    """LayoutEditor: undo/redo for add/move/delete 操作。"""
    editor = LayoutEditor()
    dev_id = editor.add_device("mzi", (10.0, 20.0))
    assert len(editor.render()["devices"]) == 1
    # undo add
    assert editor.undo() is True
    assert len(editor.render()["devices"]) == 0
    # redo add
    assert editor.redo() is True
    assert len(editor.render()["devices"]) == 1
    # move + undo
    editor.move_device(dev_id, (30.0, 40.0))
    assert editor.get_device(dev_id).position == (30.0, 40.0)
    assert editor.undo() is True
    assert editor.get_device(dev_id).position == (10.0, 20.0)
    # redo move
    assert editor.redo() is True
    assert editor.get_device(dev_id).position == (30.0, 40.0)
    # delete + undo
    editor.delete_device(dev_id)
    assert len(editor.render()["devices"]) == 0
    assert editor.undo() is True
    assert len(editor.render()["devices"]) == 1
    assert editor.get_device(dev_id).position == (30.0, 40.0)
    # redo delete
    assert editor.redo() is True
    assert len(editor.render()["devices"]) == 0
    # 空栈 undo/redo 返回 False
    editor2 = LayoutEditor()
    assert editor2.undo() is False
    assert editor2.redo() is False


def test_layout_editor_render_routes_drc() -> None:
    """LayoutEditor: render() 场景图 + set_routes + highlight_drc/clear_drc。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 20.0))
    editor.add_device("ring_resonator", (50.0, 60.0))
    # set_routes
    routes = [{"conn_id": 1, "points": [(10.0, 20.0), (50.0, 60.0)]}]
    editor.set_routes(routes)
    # highlight_drc
    drc_errors = [
        {"x": 30.0, "y": 40.0, "width": 2.0, "height": 2.0,
         "rule": "min_spacing", "severity": "error"}
    ]
    editor.highlight_drc(drc_errors)
    scene = editor.render()
    assert len(scene["devices"]) == 2
    assert len(scene["routes"]) == 1
    assert scene["routes"][0]["conn_id"] == 1
    assert len(scene["drc_highlights"]) == 1
    assert scene["drc_highlights"][0]["rule"] == "min_spacing"
    assert scene["drc_highlights"][0]["severity"] == "error"
    assert "view_transform" in scene
    assert "config" in scene
    assert "layers" in scene
    # 设备渲染包含颜色和角点
    dev0 = scene["devices"][0]
    assert "color" in dev0
    assert "corners" in dev0
    assert "size" in dev0
    # clear_drc
    editor.clear_drc()
    assert len(editor.render()["drc_highlights"]) == 0


