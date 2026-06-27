"""tests/test_layout_editor.py — R19 L-Edit 风格 GUI 版图编辑器测试。

覆盖：配置验证、器件增删移动旋转、场景渲染、DRC 高亮、撤销/重做、
视图仿射变换、网格对齐、KLayout 脚本导出（含真实执行验证）。

文献来源同 ``src/polaris/gui/layout_editor.py`` docstring（R02 学术诚信）。
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from polaris.gui import (
    DeviceInstance,
    DRCHighlight,
    EditorConfig,
    LayoutEditor,
)


# --------------------------------------------------------------------------
# 1. 配置验证
# --------------------------------------------------------------------------
def test_config_validation():
    """默认配置 + 自定义配置字段正确传递。"""
    cfg_default = EditorConfig()
    assert cfg_default.grid_size == pytest.approx(0.1)
    assert cfg_default.snap_to_grid is True
    assert cfg_default.dbu == pytest.approx(0.001)
    assert cfg_default.min_spacing == pytest.approx(1.0)
    assert cfg_default.max_undo_steps == 100

    cfg = EditorConfig(grid_size=0.05, snap_to_grid=False, max_undo_steps=10)
    editor = LayoutEditor(cfg)
    assert editor.config.grid_size == pytest.approx(0.05)
    assert editor.config.snap_to_grid is False
    assert editor.config.max_undo_steps == 10


# --------------------------------------------------------------------------
# 2. 器件添加
# --------------------------------------------------------------------------
def test_add_device():
    """添加器件返回自增 ID，器件类型/尺寸/参数正确。"""
    editor = LayoutEditor()
    dev_id = editor.add_device(
        "mzi", (10.0, 20.0), rotation=90.0, params={"fsr": 1.4e12}
    )
    assert dev_id == 1
    dev = editor.get_device(dev_id)
    assert dev.device_type == "mzi"
    assert dev.position == (10.0, 20.0)
    assert dev.rotation == pytest.approx(90.0)
    assert dev.size == (30.0, 10.0)  # _DEFAULT_DEVICE_SIZE["mzi"]
    assert dev.params == {"fsr": 1.4e12}

    # 第二个器件 ID 自增
    dev_id2 = editor.add_device("bend", (0.0, 0.0))
    assert dev_id2 == 2


# --------------------------------------------------------------------------
# 3. 器件移动
# --------------------------------------------------------------------------
def test_move_device():
    """移动器件到新位置，位置更新正确。"""
    editor = LayoutEditor()
    dev_id = editor.add_device("straight", (0.0, 0.0))
    editor.move_device(dev_id, (50.0, 70.0))
    assert editor.get_device(dev_id).position == (50.0, 70.0)


# --------------------------------------------------------------------------
# 4. 器件旋转
# --------------------------------------------------------------------------
def test_rotate_device():
    """旋转器件叠加角度，多次旋转累计。"""
    editor = LayoutEditor()
    dev_id = editor.add_device("crossing", (0.0, 0.0), rotation=0.0)
    editor.rotate_device(dev_id, 45.0)
    assert editor.get_device(dev_id).rotation == pytest.approx(45.0)
    editor.rotate_device(dev_id, 90.0)
    assert editor.get_device(dev_id).rotation == pytest.approx(135.0)


# --------------------------------------------------------------------------
# 5. 器件删除
# --------------------------------------------------------------------------
def test_delete_device():
    """删除器件后 get_device raise KeyError（R03 禁止 fall-back）。"""
    editor = LayoutEditor()
    dev_id = editor.add_device("y_branch", (0.0, 0.0))
    editor.delete_device(dev_id)
    with pytest.raises(KeyError):
        editor.get_device(dev_id)


# --------------------------------------------------------------------------
# 6. 场景渲染
# --------------------------------------------------------------------------
def test_render():
    """渲染返回结构化 dict，含器件/路由/DRC/视图变换/配置。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 10.0))
    editor.add_device("ring_resonator", (50.0, 10.0))
    editor.set_routes([{"conn_id": 0, "points": [(10.0, 10.0), (50.0, 10.0)]}])
    scene = editor.render()
    assert "layers" in scene
    assert "devices" in scene
    assert "routes" in scene
    assert "drc_highlights" in scene
    assert "view_transform" in scene
    assert "config" in scene
    assert len(scene["devices"]) == 2
    assert len(scene["routes"]) == 1
    # 器件 corners 为 4×2 列表（仿射变换后的四角）
    assert len(scene["devices"][0]["corners"]) == 4
    assert len(scene["devices"][0]["corners"][0]) == 2
    # view_transform.matrix 为 3×3
    assert len(scene["view_transform"]["matrix"]) == 3
    assert len(scene["view_transform"]["matrix"][0]) == 3


# --------------------------------------------------------------------------
# 7. DRC 错误高亮
# ----------
def test_highlight_drc():
    """DRC 错误列表转换为 DRCHighlight 并出现在渲染结果中。"""
    editor = LayoutEditor()
    editor.highlight_drc(
        [
            {
                "x": 5.0,
                "y": 5.0,
                "width": 2.0,
                "height": 1.0,
                "rule": "MIN_SPACING",
                "severity": "error",
            },
            {
                "x": 15.0,
                "y": 15.0,
                "rule": "MIN_WIDTH",
            },
        ]
    )
    scene = editor.render()
    assert len(scene["drc_highlights"]) == 2
    assert scene["drc_highlights"][0]["rule"] == "MIN_SPACING"
    assert scene["drc_highlights"][0]["severity"] == "error"
    # 缺省 severity/widht/height 默认值
    assert scene["drc_highlights"][1]["severity"] == "error"
    assert scene["drc_highlights"][1]["width"] == pytest.approx(1.0)


def test_clear_drc():
    """clear_drc 清除全部高亮。"""
    editor = LayoutEditor()
    editor.highlight_drc([{"x": 0.0, "y": 0.0, "rule": "R"}])
    assert len(editor.render()["drc_highlights"]) == 1
    editor.clear_drc()
    assert len(editor.render()["drc_highlights"]) == 0


# --------------------------------------------------------------------------
# 8. 撤销
# --------------------------------------------------------------------------
def test_undo():
    """撤销 add_device 后器件消失，无操作时返回 False。"""
    editor = LayoutEditor()
    assert editor.undo() is False  # 空栈
    dev_id = editor.add_device("taper", (0.0, 0.0))
    assert editor.undo() is True
    with pytest.raises(KeyError):
        editor.get_device(dev_id)


def test_undo_move():
    """撤销 move_device 恢复原位置。"""
    editor = LayoutEditor()
    dev_id = editor.add_device("straight", (10.0, 10.0))
    editor.move_device(dev_id, (50.0, 50.0))
    assert editor.get_device(dev_id).position == (50.0, 50.0)
    editor.undo()
    assert editor.get_device(dev_id).position == (10.0, 10.0)


# --------------------------------------------------------------------------
# 9. 重做
# --------------------------------------------------------------------------
def test_redo():
    """重做恢复撤销的操作，新操作清空 redo 栈。"""
    editor = LayoutEditor()
    assert editor.redo() is False  # 空栈
    dev_id = editor.add_device("mzi", (0.0, 0.0))
    editor.undo()
    assert editor.redo() is True
    # redo 后器件恢复
    assert editor.get_device(dev_id).device_type == "mzi"


def test_undo_redo_sequence():
    """多步操作撤销/重做序列状态一致。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (0.0, 0.0))
    editor.add_device("bend", (10.0, 0.0))
    assert len(editor.render()["devices"]) == 2
    editor.undo()  # 撤销 d2
    assert len(editor.render()["devices"]) == 1
    editor.undo()  # 撤销 d1
    assert len(editor.render()["devices"]) == 0
    editor.redo()  # 重做 d1
    assert len(editor.render()["devices"]) == 1
    editor.redo()  # 重做 d2
    assert len(editor.render()["devices"]) == 2
    # 新操作清空 redo 栈
    editor.add_device("crossing", (20.0, 0.0))
    assert editor.redo() is False


def test_new_action_clears_redo():
    """新增操作后 redo 栈被清空。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (0.0, 0.0))
    editor.undo()
    assert len(editor._redo_stack) == 1  # undo 后 redo 可用
    editor.redo()
    editor.undo()
    assert len(editor._redo_stack) == 1
    # 新操作清空 redo 栈
    editor.add_device("bend", (10.0, 0.0))
    assert len(editor._redo_stack) == 0
    assert editor.redo() is False


# --------------------------------------------------------------------------
# 10. KLayout 脚本导出
# --------------------------------------------------------------------------
def test_export_klayout_script():
    """导出 KLayout 脚本含器件/路由/层定义。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 10.0))
    editor.add_device("bend", (50.0, 10.0), rotation=90.0)
    editor.set_routes([{"conn_id": 0, "points": [(10.0, 10.0), (50.0, 10.0)]}])
    editor.highlight_drc([{"x": 30.0, "y": 10.0, "rule": "MIN_SPACE"}])
    script = editor.export_klayout_script(output_gds="out.gds")
    assert "import klayout.db as db" in script
    assert "ly = db.Layout()" in script
    assert 'ly.write("out.gds")' in script
    assert "layer_wg = ly.layer(1, 0)" in script
    assert "device 1" in script
    assert "device 2" in script
    assert "MIN_SPACE" in script


def test_export_klayout_script_executes(tmp_path):
    """导出的 KLayout 脚本可真实执行生成 GDS（验证深度编辑模式可用）。

    这是 *创新* 的 Web+KLayout 双模式集成的核心验证：导出脚本必须在
    KLayout 中可执行，否则双模式集成是假的（R03 禁止 fall-back）。
    """
    import klayout.db as db  # noqa: F401  确认依赖可用

    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 10.0))
    editor.add_device("bend", (50.0, 10.0), rotation=90.0)
    gds_path = str(tmp_path / "rt.gds")
    script = editor.export_klayout_script(output_gds=gds_path)
    # 写脚本到临时文件并执行
    script_path = tmp_path / "gen.py"
    script_path.write_text(script, encoding="utf-8")
    # 在隔离命名空间执行脚本
    ns: dict = {"__name__": "__klayout_gen__"}
    exec(compile(script, str(script_path), "exec"), ns)
    assert os.path.exists(gds_path)
    assert os.path.getsize(gds_path) > 0
    # 验证 GDS 可被 klayout 重新读回
    ly_chk = db.Layout()
    ly_chk.read(gds_path)
    top_cells = list(ly_chk.top_cells())
    assert len(top_cells) == 1


# --------------------------------------------------------------------------
# 11. 视图变换
# --------------------------------------------------------------------------
def test_view_transform():
    """view_transform 返回 3×3 仿射矩阵，纯平移/缩放/旋转元素正确。"""
    editor = LayoutEditor()
    mat = editor.view_transform((10.0, 20.0), 2.0, 0.0)
    assert mat.shape == (3, 3)
    # 纯平移+缩放（rotation=0）：[[2,0,10],[0,2,20],[0,0,1]]
    assert mat[0, 0] == pytest.approx(2.0)
    assert mat[1, 1] == pytest.approx(2.0)
    assert mat[0, 2] == pytest.approx(10.0)
    assert mat[1, 2] == pytest.approx(20.0)
    assert mat[0, 1] == pytest.approx(0.0)


def test_view_transform_rotation():
    """视图变换旋转 90° 时矩阵元素为 [0,-1;1,0]*zoom。"""
    editor = LayoutEditor()
    mat = editor.view_transform((0.0, 0.0), 1.0, 90.0)
    assert mat[0, 0] == pytest.approx(0.0, abs=1e-9)
    assert mat[0, 1] == pytest.approx(-1.0)
    assert mat[1, 0] == pytest.approx(1.0)
    assert mat[1, 1] == pytest.approx(0.0, abs=1e-9)


def test_view_transform_invalid_zoom_raises():
    """zoom<=0 必须 raise（R03 禁止 fall-back）。"""
    editor = LayoutEditor()
    with pytest.raises(ValueError):
        editor.view_transform((0.0, 0.0), 0.0)
    with pytest.raises(ValueError):
        editor.view_transform((0.0, 0.0), -1.0)


def test_world_to_view():
    """world_to_view 应用当前视图变换到点集。"""
    editor = LayoutEditor()
    editor.view_transform((10.0, 20.0), 2.0, 0.0)
    pts = np.array([[0.0, 0.0], [1.0, 1.0]])
    out = editor.world_to_view(pts)
    # (0,0) -> (10,20), (1,1) -> (12,22)
    assert out[0, 0] == pytest.approx(10.0)
    assert out[0, 1] == pytest.approx(20.0)
    assert out[1, 0] == pytest.approx(12.0)
    assert out[1, 1] == pytest.approx(22.0)


# --------------------------------------------------------------------------
# 12. 网格对齐
# --------------------------------------------------------------------------
def test_snap_to_grid():
    """snap_to_grid=True 时位置对齐到网格，False 时保持原值。"""
    cfg = EditorConfig(grid_size=0.5, snap_to_grid=True)
    editor = LayoutEditor(cfg)
    # 10.3 -> round(10.3/0.5)*0.5 = round(20.6)*0.5 = 21*0.5 = 10.5
    dev_id = editor.add_device("mzi", (10.3, 7.1))
    assert editor.get_device(dev_id).position == (10.5, 7.0)

    # move 也对齐
    editor.move_device(dev_id, (0.26, 0.51))
    assert editor.get_device(dev_id).position == (0.5, 0.5)


def test_snap_disabled():
    """snap_to_grid=False 时位置保持原值（不对齐）。"""
    cfg = EditorConfig(grid_size=0.5, snap_to_grid=False)
    editor = LayoutEditor(cfg)
    dev_id = editor.add_device("mzi", (10.3, 7.1))
    assert editor.get_device(dev_id).position == (10.3, 7.1)


# --------------------------------------------------------------------------
# 13. R03 禁止 fall-back：缺失器件必须 raise
# --------------------------------------------------------------------------
def test_get_device_missing_raises():
    """get_device 不存在 ID 必须 raise KeyError（禁止 fall-back 返回 None）。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError):
        editor.get_device(999)


def test_move_device_missing_raises():
    """move_device 不存在 ID 必须 raise。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError):
        editor.move_device(999, (0.0, 0.0))


def test_rotate_device_missing_raises():
    """rotate_device 不存在 ID 必须 raise。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError):
        editor.rotate_device(999, 90.0)


def test_delete_device_missing_raises():
    """delete_device 不存在 ID 必须 raise。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError):
        editor.delete_device(999)


# --------------------------------------------------------------------------
# 14. 器件旋转几何（四角坐标）
# --------------------------------------------------------------------------
def test_device_corners_rotation():
    """旋转 90° 后器件四角坐标正确变换（仿射几何验证）。"""
    from polaris.gui.layout_editor import _device_corners

    dev = DeviceInstance(
        device_id=1,
        device_type="straight",
        position=(0.0, 0.0),
        rotation=90.0,
        size=(10.0, 2.0),
    )
    corners = _device_corners(dev)
    # 原始四角 (-5,-1),(5,-1),(5,1),(-5,1) 旋转 90° -> (1,-5),(1,5),(-1,5),(-1,-5)
    xs = sorted(corners[:, 0].tolist())
    ys = sorted(corners[:, 1].tolist())
    assert xs == pytest.approx([-1.0, -1.0, 1.0, 1.0])
    assert ys == pytest.approx([-5.0, -5.0, 5.0, 5.0])


def test_render_corners_reflect_rotation():
    """render 输出的 corners 反映旋转后的包围盒。

    straight 默认尺寸 (10.0, 0.5)，旋转 90° 后 x 范围 [-0.25,0.25]，y 范围 [-5,5]。
    """
    editor = LayoutEditor()
    editor.add_device("straight", (0.0, 0.0), rotation=90.0)
    scene = editor.render()
    corners = np.array(scene["devices"][0]["corners"])
    assert corners[:, 0].min() == pytest.approx(-0.25)
    assert corners[:, 0].max() == pytest.approx(0.25)
    assert corners[:, 1].min() == pytest.approx(-5.0)
    assert corners[:, 1].max() == pytest.approx(5.0)


# --------------------------------------------------------------------------
# 15. 撤销栈深度限制
# --------------------------------------------------------------------------
def test_undo_stack_limit():
    """撤销栈超过 max_undo_steps 时丢弃最旧操作。"""
    editor = LayoutEditor(EditorConfig(max_undo_steps=3))
    for i in range(5):
        editor.add_device("mzi", (float(i), 0.0))
    # 只能撤销最近 3 次
    for _ in range(3):
        assert editor.undo() is True
    assert editor.undo() is False
    # 还剩 2 个器件（5-3=2）
    assert len(editor.render()["devices"]) == 2


# --------------------------------------------------------------------------
# 16. 布线设置
# --------------------------------------------------------------------------
def test_set_routes():
    """set_routes 后渲染输出布线路径。"""
    editor = LayoutEditor()
    editor.set_routes(
        [
            {"conn_id": 1, "points": [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]},
            {"conn_id": 2, "points": [(5.0, 5.0), (15.0, 5.0)]},
        ]
    )
    routes = editor.render()["routes"]
    assert len(routes) == 2
    assert routes[0]["conn_id"] == 1
    assert len(routes[0]["points"]) == 3


# --------------------------------------------------------------------------
# 17. DRCHighlight 数据类
# --------------------------------------------------------------------------
def test_drc_highlight_dataclass():
    """DRCHighlight 数据类字段正确。"""
    h = DRCHighlight(x=1.0, y=2.0, width=3.0, height=4.0, rule="R", severity="warning")
    assert h.x == 1.0
    assert h.severity == "warning"
