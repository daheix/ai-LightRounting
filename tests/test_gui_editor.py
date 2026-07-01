"""tests/test_gui_editor.py — P0-3 GUI 版图编辑器交互功能测试。

覆盖：曲线多边形创建/顶点编辑、命令栈 undo/redo、吸附引擎（grid/vertex/
midpoint/endpoint）、飞线路由、宏 IDE（断点/单步/控制台/监视）、
错误处理（R03 禁止 fall-back）、查看器只读模式。

文献来源同 ``src/polaris/gui/interactive.py`` docstring（R02 学术诚信）。
规则 14.1：禁止 fall-back，测试失败必须告警。
"""

from __future__ import annotations

import pytest

from polaris.gui.interactive import (
    AddObjectCommand,
    AirlineRouter,
    CommandStack,
    InsertVertexCommand,
    LayoutObject,
    MacroIDE,
    MoveObjectCommand,
    MoveVertexCommand,
    ObjectType,
    RemoveObjectCommand,
    RemoveVertexCommand,
    SnapEngine,
    ViewerGuard,
    _de_casteljau,
    evaluate_object,
)


# =============================================================================
# 1. LayoutObject 数据模型验证
# =============================================================================

def test_layout_object_validation():
    """LayoutObject 校验：obj_id<=0 raise，未知类型 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="obj_id"):
        LayoutObject(0, "polygon")
    with pytest.raises(ValueError, match="obj_id"):
        LayoutObject(-1, "polygon")
    with pytest.raises(ValueError, match="未知对象类型"):
        LayoutObject(1, "unknown_type")
    # 合法对象正常构造
    obj = LayoutObject(1, "polygon", [(0.0, 0.0), (1.0, 0.0)])
    assert obj.obj_id == 1
    assert obj.layer == "WG"


# =============================================================================
# 2. 曲线多边形创建与求值
# =============================================================================

def test_polygon_creation_and_evaluate():
    """多边形创建并求值，结果应闭合（首尾点相同）。"""
    obj = LayoutObject(1, "polygon", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    pts = evaluate_object(obj)
    # 多边形求值自动闭合：末尾追加首点
    assert len(pts) == 4
    assert pts[0] == (0.0, 0.0)
    assert pts[-1] == (0.0, 0.0)


def test_bezier_evaluate_endpoints():
    """贝塞尔曲线求值：t=0 返回首控制点，t=1 返回末控制点。"""
    ctrl = [(0.0, 0.0), (10.0, 20.0), (20.0, 0.0)]
    obj = LayoutObject(2, "bezier", ctrl)
    pts = evaluate_object(obj, n_samples=10)
    assert pts[0] == pytest.approx((0.0, 0.0))
    assert pts[-1] == pytest.approx((20.0, 0.0))
    # De Casteljau 直接验证
    assert _de_casteljau(ctrl, 0.0) == pytest.approx((0.0, 0.0))
    assert _de_casteljau(ctrl, 1.0) == pytest.approx((20.0, 0.0))


def test_spline_evaluate_passes_through_control_points():
    """Catmull-Rom 样条求值穿过所有控制点（首尾点匹配）。"""
    ctrl = [(0.0, 0.0), (5.0, 10.0), (10.0, 0.0), (15.0, 10.0)]
    obj = LayoutObject(3, "spline", ctrl)
    pts = evaluate_object(obj, n_samples=20)
    assert pts[0] == pytest.approx(ctrl[0])
    assert pts[-1] == pytest.approx(ctrl[-1])


def test_arc_evaluate():
    """圆弧求值：起点/终点角度匹配，半径正确。"""
    obj = LayoutObject(
        4, "arc", [],
        attrs={"center": (0.0, 0.0), "radius": 5.0,
               "start_angle": 0.0, "end_angle": 90.0})
    pts = evaluate_object(obj, n_samples=4)
    # 起点 (5,0)，终点 (0,5)
    assert pts[0] == pytest.approx((5.0, 0.0), abs=1e-9)
    assert pts[-1] == pytest.approx((0.0, 5.0), abs=1e-9)


def test_ellipse_evaluate():
    """椭圆求值：a≠b 时 x/y 半轴不同。"""
    obj = LayoutObject(
        5, "ellipse", [],
        attrs={"center": (0.0, 0.0), "a": 10.0, "b": 5.0,
               "start_angle": 0.0, "end_angle": 360.0})
    pts = evaluate_object(obj, n_samples=4)
    # n_samples=4 → 5 个采样点 k=0..4，角度 0/90/180/270/360
    # 0° → (10, 0)，90° → (0, 5)
    assert pts[0] == pytest.approx((10.0, 0.0), abs=1e-9)
    assert pts[1] == pytest.approx((0.0, 5.0), abs=1e-9)


# =============================================================================
# 3. 命令栈 undo/redo
# =============================================================================

def test_command_stack_add_undo_redo():
    """AddObjectCommand：do/undo/redo 状态正确。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "point", [(0.0, 0.0)])
    stack.execute(AddObjectCommand(obj), scene)
    assert 1 in scene
    assert stack.undo_depth == 1
    # undo
    assert stack.undo(scene) is True
    assert 1 not in scene
    assert stack.redo_depth == 1
    # redo
    assert stack.redo(scene) is True
    assert 1 in scene
    assert stack.redo_depth == 0


def test_command_stack_move_undo_with_center():
    """MoveObjectCommand undo 恢复原位置，含 center 属性同步。

    R05 Bug 修复 R1000: AddObjectCommand.do() 使用 deepcopy 隔离场景对象
    （避免外部修改导致撤销/重做副作用，Gamma 1994 命令模式）。
    测试需通过 scene[obj_id] 访问实际对象，而非原始引用 obj。
    """
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(
        1, "arc", [(0.0, 0.0)],
        attrs={"center": (5.0, 5.0), "radius": 3.0})
    stack.execute(AddObjectCommand(obj), scene)
    stack.execute(MoveObjectCommand(1, 10.0, 20.0), scene)
    # AddObjectCommand 使用 deepcopy，需通过 scene 访问实际对象
    scene_obj = scene[1]
    assert scene_obj.points[0] == (10.0, 20.0)
    assert scene_obj.attrs["center"] == (15.0, 25.0)
    # undo 恢复
    stack.undo(scene)
    assert scene_obj.points[0] == (0.0, 0.0)
    assert scene_obj.attrs["center"] == (5.0, 5.0)


def test_command_stack_redo_clears_on_new_command():
    """新命令清空 redo 栈。"""
    scene: dict = {}
    stack = CommandStack()
    stack.execute(AddObjectCommand(LayoutObject(1, "point", [(0.0, 0.0)])), scene)
    stack.undo(scene)
    assert stack.redo_depth == 1
    # 新命令清空 redo
    stack.execute(AddObjectCommand(LayoutObject(2, "point", [(1.0, 1.0)])), scene)
    assert stack.redo_depth == 0
    assert stack.redo(scene) is False


def test_command_stack_overflow():
    """命令栈溢出 max_steps 时丢弃最旧命令。"""
    scene: dict = {}
    stack = CommandStack(max_steps=3)
    for i in range(1, 6):
        stack.execute(
            AddObjectCommand(LayoutObject(i, "point", [(0.0, 0.0)])), scene)
    # 最多保留 3 个 undo
    assert stack.undo_depth == 3


# =============================================================================
# 4. 顶点编辑命令（Insert/Remove/Move Vertex）
# =============================================================================

def test_insert_vertex_command():
    """InsertVertexCommand do/undo：插入后顶点数+1，撤销恢复。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "polygon", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    stack.execute(AddObjectCommand(obj), scene)
    stack.execute(InsertVertexCommand(1, 1, (5.0, 0.0)), scene)
    assert len(obj.points) == 4
    assert obj.points[1] == (5.0, 0.0)
    # undo
    stack.undo(scene)
    assert len(obj.points) == 3
    assert obj.points[1] == (10.0, 0.0)


def test_remove_vertex_command():
    """RemoveVertexCommand do/undo：删除后顶点数-1，撤销恢复。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "polyline", [(0.0, 0.0), (5.0, 5.0), (10.0, 0.0)])
    stack.execute(AddObjectCommand(obj), scene)
    stack.execute(RemoveVertexCommand(1, 1, (0.0, 0.0)), scene)
    assert len(obj.points) == 2
    assert obj.points[1] == (10.0, 0.0)
    # undo
    stack.undo(scene)
    assert len(obj.points) == 3
    assert obj.points[1] == (5.0, 5.0)


def test_move_vertex_command():
    """MoveVertexCommand do/undo：移动顶点后撤销恢复原坐标。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "polygon", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    stack.execute(AddObjectCommand(obj), scene)
    # old_vertex 在 do 时被实际值 (10,0) 覆盖
    stack.execute(MoveVertexCommand(1, 1, (0.0, 0.0), (15.0, 5.0)), scene)
    assert obj.points[1] == (15.0, 5.0)
    # undo 恢复为 do 时记录的 old_vertex=(10,0)
    stack.undo(scene)
    assert obj.points[1] == (10.0, 0.0)


# =============================================================================
# 5. 吸附引擎（grid/vertex/midpoint/endpoint）
# =============================================================================

def test_snap_grid_mode():
    """SnapEngine grid 模式：对齐到网格。"""
    engine = SnapEngine(grid_size=0.5, threshold=0.0, modes=["grid"])
    result = engine.snap((10.3, 7.1))
    assert result.mode == "grid"
    assert result.point == pytest.approx((10.5, 7.0))


def test_snap_vertex_mode():
    """SnapEngine vertex 模式：吸附到最近顶点。"""
    obj = LayoutObject(1, "polygon", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    engine = SnapEngine(grid_size=0.1, threshold=0.5, modes=["vertex", "grid"])
    # 距 (10,0) 0.3 单位，threshold=0.5 内
    result = engine.snap((10.3, 0.0), [obj])
    assert result.mode == "vertex"
    assert result.point == (10.0, 0.0)


def test_snap_midpoint_mode():
    """SnapEngine midpoint 模式：吸附到边中点。"""
    obj = LayoutObject(1, "polyline", [(0.0, 0.0), (10.0, 0.0)])
    engine = SnapEngine(grid_size=0.1, threshold=0.5, modes=["midpoint", "grid"])
    # 中点 (5,0)，距 (5.2, 0.0) 0.2 单位
    result = engine.snap((5.2, 0.0), [obj])
    assert result.mode == "midpoint"
    assert result.point == (5.0, 0.0)


def test_snap_endpoint_mode():
    """SnapEngine endpoint 模式：吸附到端点。"""
    obj = LayoutObject(1, "polyline", [(0.0, 0.0), (10.0, 0.0)])
    engine = SnapEngine(grid_size=0.1, threshold=0.5, modes=["endpoint", "grid"])
    # 端点 (10,0)，距 (9.8, 0.1) 约 0.22 单位
    result = engine.snap((9.8, 0.1), [obj])
    assert result.mode == "endpoint"
    assert result.point == (10.0, 0.0)


def test_snap_priority_vertex_over_grid():
    """SnapEngine 优先级：vertex > grid（同时满足时选 vertex）。"""
    obj = LayoutObject(1, "point", [(5.0, 5.0)])
    engine = SnapEngine(grid_size=1.0, threshold=0.5,
                        modes=["vertex", "grid"])
    # (5.3, 5.0) 距顶点 (5,5) 0.3，距 grid (5,5) 0.3，优先 vertex
    result = engine.snap((5.3, 5.0), [obj])
    assert result.mode == "vertex"


# =============================================================================
# 6. 飞线路由器（AirlineRouter）
# =============================================================================

def test_airline_router_pairs_by_net_id():
    """AirlineRouter 按 net_id 自动配对端口生成飞线。"""
    ports = [
        LayoutObject(1, "port", [(0.0, 0.0)], attrs={"net_id": "netA"}),
        LayoutObject(2, "port", [(10.0, 0.0)], attrs={"net_id": "netA"}),
        LayoutObject(3, "port", [(0.0, 10.0)], attrs={"net_id": "netB"}),
        LayoutObject(4, "port", [(10.0, 10.0)], attrs={"net_id": "netB"}),
    ]
    router = AirlineRouter()
    segments = router.route(ports)
    assert len(segments) == 2
    nets = {s.net_id for s in segments}
    assert nets == {"netA", "netB"}
    # netA: port 1 -> port 2
    net_a = [s for s in segments if s.net_id == "netA"][0]
    assert net_a.start == (0.0, 0.0)
    assert net_a.end == (10.0, 0.0)


def test_airline_router_explicit_netlist_chain():
    """AirlineRouter 显式 netlist：3 端口同 net 形成 2 段飞线链。"""
    ports = [
        LayoutObject(1, "port", [(0.0, 0.0)]),
        LayoutObject(2, "port", [(10.0, 0.0)]),
        LayoutObject(3, "port", [(20.0, 0.0)]),
    ]
    router = AirlineRouter()
    segments = router.route(ports, netlist={"netX": [1, 2, 3]})
    assert len(segments) == 2
    assert segments[0].start == (0.0, 0.0)
    assert segments[0].end == (10.0, 0.0)
    assert segments[1].start == (10.0, 0.0)
    assert segments[1].end == (20.0, 0.0)


def test_airline_router_single_port_no_segment():
    """AirlineRouter：单端口 net 不生成飞线段。"""
    ports = [LayoutObject(1, "port", [(0.0, 0.0)], attrs={"net_id": "solo"})]
    router = AirlineRouter()
    segments = router.route(ports)
    assert len(segments) == 0


# =============================================================================
# 7. 宏 IDE（断点/单步/控制台/监视）
# =============================================================================

_MACRO_SOURCE = "x = 0\nx = x + 1\nx = x + 2\ny = x * 10\n"


def test_macro_ide_load_and_run():
    """MacroIDE 加载脚本并运行到结束（无断点，continue 模式）。"""
    ide = MacroIDE()
    ide.load_script("test_macro.py", _MACRO_SOURCE)
    paused = ide.run(step_mode="continue")
    assert paused is False
    assert ide.namespace["x"] == 3
    assert ide.namespace["y"] == 30
    # 执行了全部 4 行
    assert len(ide.executed_lines) == 4


def test_macro_ide_breakpoint():
    """MacroIDE 断点：在第 3 行暂停，paused_at 正确。"""
    ide = MacroIDE()
    ide.load_script("test_macro.py", _MACRO_SOURCE)
    ide.set_breakpoint(3)  # x = x + 2
    paused = ide.run(step_mode="continue")
    assert paused is True
    assert ide.paused_at == ("test_macro.py", 3)
    # 执行了第 1、2、3 行（第 3 行暂停于执行前）
    assert ("test_macro.py", 1) in ide.executed_lines
    assert ("test_macro.py", 2) in ide.executed_lines
    assert ("test_macro.py", 3) in ide.executed_lines
    # 断点处 x 已执行 x=0, x=x+1 → x=1（第 3 行未执行）
    assert ide.namespace["x"] == 1


def test_macro_ide_step_mode():
    """MacroIDE step 模式：第 1 行即暂停。"""
    ide = MacroIDE()
    ide.load_script("test_macro.py", _MACRO_SOURCE)
    paused = ide.run(step_mode="step")
    assert paused is True
    assert ide.paused_at == ("test_macro.py", 1)
    assert ide.executed_lines == [("test_macro.py", 1)]


def test_macro_ide_console_eval():
    """MacroIDE 控制台：表达式返回结果，语句返回 None。"""
    ide = MacroIDE()
    # 表达式
    assert ide.console_eval("1 + 1") == 2
    # 语句（赋值）
    assert ide.console_eval("z = 5") is None
    # 后续表达式可访问
    assert ide.console_eval("z * 2") == 10


def test_macro_ide_watch_expressions():
    """MacroIDE 监视表达式：断点处捕获变量值。"""
    ide = MacroIDE()
    ide.load_script("test_macro.py", _MACRO_SOURCE)
    ide.add_watch("x")
    ide.set_breakpoint(3)  # x = x + 2 执行前
    ide.run(step_mode="continue")
    # 断点处 x=1（执行了 x=0, x=x+1）
    assert ide.watch_values["x"] == 1


def test_macro_ide_conditional_breakpoint():
    """MacroIDE 条件断点：条件为 True 时暂停。"""
    ide = MacroIDE()
    # 循环脚本：i 从 0 到 4
    src = "i = 0\nwhile i < 5:\n    i = i + 1\n"
    ide.load_script("test_cond.py", src)
    ide.set_breakpoint(3, cond="i == 3")  # 第 3 行 i==3 时暂停
    paused = ide.run(step_mode="continue")
    assert paused is True
    assert ide.paused_at == ("test_cond.py", 3)
    assert ide.namespace["i"] == 3


# =============================================================================
# 8. 查看器只读模式（ViewerGuard）
# =============================================================================

def test_viewer_guard_editable_by_default():
    """ViewerGuard 默认可编辑，require_editable 不 raise。"""
    guard = ViewerGuard()
    assert guard.viewer_mode is False
    guard.require_editable()  # 不 raise


def test_viewer_guard_blocks_edit_in_viewer_mode():
    """ViewerGuard viewer_mode=True 时 require_editable raise PermissionError。"""
    guard = ViewerGuard(viewer_mode=True)
    assert guard.viewer_mode is True
    with pytest.raises(PermissionError, match="查看器模式"):
        guard.require_editable()
    # 切换回可编辑
    guard.set_viewer_mode(False)
    guard.require_editable()  # 不 raise


# =============================================================================
# 9. 拖放（drag-drop = snap + move 组合）
# =============================================================================

def test_drag_drop_with_snap_and_move():
    """拖放：snap 目标点后整体平移对象（snap-to-grid grab-move）。"""
    scene: dict = {}
    stack = CommandStack()
    snap = SnapEngine(grid_size=0.5, threshold=0.0, modes=["grid"])
    obj = LayoutObject(1, "polygon", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    stack.execute(AddObjectCommand(obj), scene)
    # 拖放到 (5.3, 0.1)，snap 到 (5.5, 0.0)
    target = (5.3, 0.1)
    snapped = snap.snap(target, list(scene.values()))
    cx, cy = obj.points[0]
    dx = snapped.point[0] - cx
    dy = snapped.point[1] - cy
    stack.execute(MoveObjectCommand(1, dx, dy), scene)
    assert obj.points[0] == pytest.approx((5.5, 0.0))
    assert obj.points[1] == pytest.approx((15.5, 0.0))
    # undo 恢复
    stack.undo(scene)
    assert obj.points[0] == (0.0, 0.0)


# =============================================================================
# 10. 错误处理（R03 禁止 fall-back）
# =============================================================================

def test_evaluate_object_missing_points_raises():
    """evaluate_object POINT 缺少 points 必须 raise（禁止 fall-back）。"""
    obj = LayoutObject(1, "point", [])
    with pytest.raises(ValueError, match="缺少 points"):
        evaluate_object(obj)


def test_de_casteljau_invalid_t_raises():
    """_de_casteljau 无效 t 必须 raise。"""
    with pytest.raises(ValueError, match="参数 t"):
        _de_casteljau([(0.0, 0.0), (1.0, 1.0)], 1.5)


def test_insert_vertex_invalid_index_raises():
    """InsertVertexCommand 索引越界必须 raise。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "polyline", [(0.0, 0.0), (10.0, 0.0)])
    stack.execute(AddObjectCommand(obj), scene)
    with pytest.raises(IndexError):
        stack.execute(InsertVertexCommand(1, 99, (5.0, 0.0)), scene)


def test_insert_vertex_non_poly_raises():
    """InsertVertexCommand 对非折线/多边形对象必须 raise。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "bezier", [(0.0, 0.0), (10.0, 0.0)])
    stack.execute(AddObjectCommand(obj), scene)
    with pytest.raises(ValueError, match="仅折线/多边形"):
        stack.execute(InsertVertexCommand(1, 1, (5.0, 0.0)), scene)


def test_remove_vertex_too_few_raises():
    """RemoveVertexCommand 顶点数 ≤2 时必须 raise（禁止删空）。"""
    scene: dict = {}
    stack = CommandStack()
    obj = LayoutObject(1, "polyline", [(0.0, 0.0), (10.0, 0.0)])
    stack.execute(AddObjectCommand(obj), scene)
    with pytest.raises(ValueError, match="至少保留 2 个顶点"):
        stack.execute(RemoveVertexCommand(1, 0, (0.0, 0.0)), scene)


def test_command_missing_object_raises():
    """MoveObjectCommand 不存在 ID 必须 raise KeyError（禁止 fall-back）。"""
    scene: dict = {}
    stack = CommandStack()
    with pytest.raises(KeyError):
        stack.execute(MoveObjectCommand(999, 1.0, 1.0), scene)


def test_airline_router_non_port_raises():
    """AirlineRouter 非 PORT 对象必须 raise。"""
    obj = LayoutObject(1, "polygon", [(0.0, 0.0)])
    router = AirlineRouter()
    with pytest.raises(ValueError, match="非 PORT"):
        router.route([obj])


def test_airline_router_missing_net_id_raises():
    """AirlineRouter PORT 缺少 net_id 自动推断时必须 raise。"""
    port = LayoutObject(1, "port", [(0.0, 0.0)])  # 无 net_id
    router = AirlineRouter()
    with pytest.raises(ValueError, match="net_id"):
        router.route([port])


def test_macro_ide_run_without_load_raises():
    """MacroIDE 未加载脚本就 run 必须 raise（禁止 fall-back）。"""
    ide = MacroIDE()
    with pytest.raises(RuntimeError, match="尚未加载"):
        ide.run()


def test_macro_ide_console_empty_input_raises():
    """MacroIDE console_eval 空输入必须 raise。"""
    ide = MacroIDE()
    with pytest.raises(ValueError):
        ide.console_eval("")


def test_snap_engine_invalid_grid_size_raises():
    """SnapEngine grid_size<=0 必须 raise。"""
    with pytest.raises(ValueError, match="grid_size"):
        SnapEngine(grid_size=0.0)
    with pytest.raises(ValueError, match="grid_size"):
        SnapEngine(grid_size=-1.0)


def test_command_stack_invalid_max_steps_raises():
    """CommandStack max_steps<=0 必须 raise。"""
    with pytest.raises(ValueError, match="max_steps"):
        CommandStack(max_steps=0)
