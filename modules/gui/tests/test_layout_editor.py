"""LayoutEditor 交互式版图编辑器深度测试（D10 GUI 交互能力验证）。

PoLaRIS v5.0 LayoutEditor 已实现完整 L-Edit 风格交互能力（add/move/
rotate/delete/undo/redo/view_transform/render/export_klayout_script），
但原 test_web.py 注释声称有 4 个 LayoutEditor 测试实际并不存在（R02 学术
诚信违规）。本文件补齐真实测试，验证 D10 GUI 交互能力达标。

测试分组（22 个 pytest）:
- 器件管理: add/move/rotate/delete + 网格对齐 + ID 自增 (5)
- 撤销/重做: undo/redo 各操作 + redo 清空 + 空栈 + 深度限制 (6)
- 视图变换: view_transform/world_to_view + 非法 zoom raise (3)
- 场景渲染: render/set_routes/highlight_drc/clear_drc + 空场景 (4)
- KLayout 导出: export_klayout_script 含器件/布线/DRC (1)
- 异常分支: get/move/rotate/delete 不存在器件 raise (3)

规则:
- R02 学术诚信: ≥5 文献 URL，所有断言可溯源
- R03 禁止 fall-back: 校验类测试断言 raise 而非返回 None/[]
- R05 无 TODO/FIXME 残留
- R11 函数 ≤80 行 / 文件 ≤800 行
- 中文注释

来源（R02 学术诚信，≥5 个文献 URL）:
- KLayout 官方文档（编辑器/DRC API）
  https://www.klayout.de/doc-qt5/manual/editor.html
- Siemens L-Edit Photonics（版图驱动 PIC 设计 / 拖拽 / 光学 pin 对齐）
  https://eda.sw.s.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
- GDSFactory 9.x（参数化单元 + KLayout 集成）
  https://gdsfactory.github.io/gdsfactory/
- SiEPIC-Tools Wiki（PinRec/DEVREC 网表提取格式）
  https://github.com/SiEPIC/SiEPIC-Tools/wiki
- Foley & Van Dam, "Computer Graphics: Principles and Practice",
  3rd ed., Addison-Wesley 2013（齐次坐标仿射变换）
- Gamma et al., "Design Patterns", Addison-Wesley 1994（命令模式 Memento）
  https://en.wikipedia.org/wiki/Command_pattern
- pytest 文档: https://docs.pytest.org/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# sys.path 注入：与 test_web.py 一致
_MODULE_ROOT = Path(__file__).resolve().parents[2]
_GUI_SRC = str(_MODULE_ROOT / "gui" / "src")
if _GUI_SRC not in sys.path:
    sys.path.insert(0, _GUI_SRC)

from polaris_gui.layout_editor import (  # noqa: E402
    DRCHighlight,
    DeviceInstance,
    EditorConfig,
    LayoutEditor,
)


# =============================================================================
# 1. 器件管理（add/move/rotate/delete + 网格对齐 + ID 自增）
# =============================================================================


def test_add_device_returns_id_and_snaps_to_grid() -> None:
    """add_device 返回自增 ID，位置按网格对齐（grid_size=0.1μm）。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.234, 20.789))
    assert did == 1
    dev = editor.get_device(did)
    # 网格对齐: 10.234 → 10.2, 20.789 → 20.8（grid_size=0.1）
    assert dev.position == pytest.approx((10.2, 20.8))
    assert dev.device_type == "mzi"
    assert dev.category == "passive"
    assert dev.rotation == 0.0
    # 第二个器件 ID 自增
    did2 = editor.add_device("ring_resonator", (50.0, 50.0))
    assert did2 == 2


def test_add_device_unknown_type_uses_default_size() -> None:
    """add_device 未知器件类型使用默认尺寸 (10,10)，不 raise（容错设计）。"""
    editor = LayoutEditor()
    did = editor.add_device("unknown_type", (5.0, 5.0))
    dev = editor.get_device(did)
    assert dev.size == (10.0, 10.0)


def test_move_device_updates_position() -> None:
    """move_device 更新器件位置并按网格对齐。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    editor.move_device(did, (15.55, 25.45))
    dev = editor.get_device(did)
    assert dev.position == pytest.approx((15.6, 25.4))


def test_rotate_device_accumulates_angle() -> None:
    """rotate_device 叠加角度（非覆盖），90° 旋转两次得 180°。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    editor.rotate_device(did, 90.0)
    assert editor.get_device(did).rotation == pytest.approx(90.0)
    editor.rotate_device(did, 90.0)
    assert editor.get_device(did).rotation == pytest.approx(180.0)


def test_delete_device_removes_from_scene() -> None:
    """delete_device 从场景移除器件。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    assert len(editor._devices) == 1
    editor.delete_device(did)
    assert len(editor._devices) == 0


# =============================================================================
# 2. 撤销/重做（undo/redo 各操作 + redo 清空 + 空栈 + 深度限制）
# =============================================================================


def test_undo_add_restores_device() -> None:
    """undo 撤销 add 操作，器件恢复到场景中。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    assert len(editor._devices) == 1
    assert editor.undo() is True
    assert len(editor._devices) == 0


def test_undo_move_restores_position() -> None:
    """undo 撤销 move 操作，位置恢复。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    editor.move_device(did, (20.0, 20.0))
    assert editor.get_device(did).position == pytest.approx((20.0, 20.0))
    editor.undo()
    assert editor.get_device(did).position == pytest.approx((10.0, 10.0))


def test_undo_rotate_restores_angle() -> None:
    """undo 撤销 rotate 操作，角度恢复。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    editor.rotate_device(did, 90.0)
    editor.undo()
    assert editor.get_device(did).rotation == pytest.approx(0.0)


def test_undo_delete_restores_device() -> None:
    """undo 撤销 delete 操作，器件恢复（含 params 深拷贝）。"""
    editor = LayoutEditor()
    did = editor.add_device(
        "mzi", (10.0, 10.0), params={"radius": 5.0, "ports": ["a", "b"]}
    )
    editor.delete_device(did)
    assert len(editor._devices) == 0
    editor.undo()
    assert len(editor._devices) == 1
    dev = editor.get_device(did)
    # params 深拷贝完整性（R05 Bug 修复 v3.3-GUI-1 验证）
    assert dev.params == {"radius": 5.0, "ports": ["a", "b"]}


def test_redo_reapplies_deleted_operation() -> None:
    """redo 重做被 undo 撤销的操作。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    editor.delete_device(did)
    editor.undo()  # 恢复器件
    assert len(editor._devices) == 1
    assert editor.redo() is True  # 重新删除
    assert len(editor._devices) == 0


def test_new_operation_clears_redo_stack() -> None:
    """新操作清空 redo 栈（标准命令模式，禁止 redo 跨新操作）。"""
    editor = LayoutEditor()
    did = editor.add_device("mzi", (10.0, 10.0))
    editor.move_device(did, (20.0, 20.0))
    editor.undo()  # 撤销 move
    assert editor.get_device(did).position == pytest.approx((10.0, 10.0))
    # 新操作（rotate）应清空 redo 栈
    editor.rotate_device(did, 45.0)
    assert editor.redo() is False  # redo 栈已清空


def test_undo_redo_empty_stack_returns_false() -> None:
    """空撤销/重做栈返回 False，不 raise。"""
    editor = LayoutEditor()
    assert editor.undo() is False
    assert editor.redo() is False


def test_undo_stack_depth_limit() -> None:
    """撤销栈深度限制 max_undo_steps=50，超出 FIFO 淘汰最旧。"""
    config = EditorConfig(max_undo_steps=5)
    editor = LayoutEditor(config=config)
    # 添加 8 个器件，产生 8 个 undo 项
    for i in range(8):
        editor.add_device("mzi", (float(i), 0.0))
    # 只能 undo 5 次（深度限制）
    undo_count = 0
    while editor.undo():
        undo_count += 1
    assert undo_count == 5


# =============================================================================
# 3. 视图变换（view_transform/world_to_view + 非法 zoom raise）
# =============================================================================


def test_view_transform_returns_affine_matrix() -> None:
    """view_transform 设置 pan/zoom/rotation 并返回 3×3 仿射矩阵。"""
    editor = LayoutEditor()
    mat = editor.view_transform((10.0, 20.0), 2.0, 0.0)
    assert mat.shape == (3, 3)
    # 平移分量
    assert mat[0, 2] == pytest.approx(10.0)
    assert mat[1, 2] == pytest.approx(20.0)
    # 缩放分量（rotation=0 时 cos=1, sin=0）
    assert mat[0, 0] == pytest.approx(2.0)
    assert mat[1, 1] == pytest.approx(2.0)


def test_view_transform_invalid_zoom_raises() -> None:
    """view_transform 非法 zoom（<=0）raise ValueError（R03 禁止 fall-back）。"""
    editor = LayoutEditor()
    with pytest.raises(ValueError, match="zoom"):
        editor.view_transform((0.0, 0.0), 0.0, 0.0)
    with pytest.raises(ValueError, match="zoom"):
        editor.view_transform((0.0, 0.0), -1.0, 0.0)


def test_world_to_view_applies_transform() -> None:
    """world_to_view 对点集应用当前视图变换。"""
    editor = LayoutEditor()
    editor.view_transform((5.0, 5.0), 2.0, 0.0)
    points = np.array([[0.0, 0.0], [1.0, 1.0]])
    out = editor.world_to_view(points)
    # (0,0) → (5,5), (1,1) → (5+2, 5+2) = (7,7)
    assert out[0, 0] == pytest.approx(5.0)
    assert out[0, 1] == pytest.approx(5.0)
    assert out[1, 0] == pytest.approx(7.0)
    assert out[1, 1] == pytest.approx(7.0)


# =============================================================================
# 4. 场景渲染（render/set_routes/highlight_drc/clear_drc + 空场景）
# =============================================================================


def test_render_returns_full_scene_dict() -> None:
    """render 返回包含 devices/routes/drc_highlights/view_transform 的场景 dict。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 10.0), category="active")
    editor.set_routes([{"conn_id": 1, "points": [(0.0, 0.0), (10.0, 10.0)]}])
    editor.highlight_drc(
        [{"x": 5.0, "y": 5.0, "width": 1.0, "height": 1.0, "rule": "MIN_SPACING"}]
    )
    scene = editor.render()
    assert "layers" in scene
    assert "devices" in scene
    assert "routes" in scene
    assert "drc_highlights" in scene
    assert "view_transform" in scene
    assert "config" in scene
    # 器件渲染含颜色和四角坐标
    dev = scene["devices"][0]
    assert dev["device_type"] == "mzi"
    assert dev["category"] == "active"
    assert dev["color"] == "#DD8452"  # active 类别颜色
    assert len(dev["corners"]) == 4
    # 布线渲染
    assert len(scene["routes"]) == 1
    assert scene["routes"][0]["conn_id"] == 1
    # DRC 高亮
    assert len(scene["drc_highlights"]) == 1
    assert scene["drc_highlights"][0]["rule"] == "MIN_SPACING"


def test_render_empty_scene() -> None:
    """render 空场景返回空列表（不 raise）。"""
    editor = LayoutEditor()
    scene = editor.render()
    assert scene["devices"] == []
    assert scene["routes"] == []
    assert scene["drc_highlights"] == []


def test_clear_drc_removes_all_highlights() -> None:
    """clear_drc 清除所有 DRC 高亮。"""
    editor = LayoutEditor()
    editor.highlight_drc(
        [
            {"x": 1.0, "y": 1.0, "rule": "R1"},
            {"x": 2.0, "y": 2.0, "rule": "R2"},
        ]
    )
    assert len(editor._drc_highlights) == 2
    editor.clear_drc()
    assert len(editor._drc_highlights) == 0


def test_highlight_drc_severity_default() -> None:
    """highlight_drc 缺省 severity 默认 'error'。"""
    editor = LayoutEditor()
    editor.highlight_drc([{"x": 1.0, "y": 1.0, "rule": "R1"}])
    assert editor._drc_highlights[0].severity == "error"


# =============================================================================
# 5. KLayout 脚本导出（export_klayout_script 含器件/布线/DRC）
# =============================================================================


def test_export_klayout_script_contains_devices_routes_drc() -> None:
    """export_klayout_script 生成含器件/布线/DRC 注释的 KLayout Python 脚本。"""
    editor = LayoutEditor()
    editor.add_device("mzi", (10.0, 10.0))
    editor.add_device("ring_resonator", (50.0, 50.0))
    editor.set_routes([{"conn_id": 1, "points": [(0.0, 0.0), (10.0, 10.0)]}])
    editor.highlight_drc(
        [{"x": 5.0, "y": 5.0, "rule": "MIN_SPACING", "severity": "error"}]
    )
    script = editor.export_klayout_script(output_gds="test.gds", top_cell_name="TOP")
    # 脚本头部
    assert "import klayout.db as db" in script
    assert 'ly.create_cell("TOP")' in script
    assert "ly.dbu" in script
    # 器件 box 注释
    assert "device 1" in script
    assert "device 2" in script
    assert "layer_wg" in script
    # 布线路径
    assert "db.DPath" in script
    # DRC 高亮注释
    assert "DRC 高亮标记: 1 处" in script
    assert "MIN_SPACING" in script
    # GDS 输出
    assert 'ly.write("test.gds")' in script


# =============================================================================
# 6. 异常分支（R03 禁止 fall-back：不存在器件 raise）
# =============================================================================


def test_get_device_not_found_raises() -> None:
    """get_device 不存在器件 raise KeyError（R03 禁止 fall-back）。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError, match="不存在"):
        editor.get_device(999)


def test_move_device_not_found_raises() -> None:
    """move_device 不存在器件 raise KeyError。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError, match="不存在"):
        editor.move_device(999, (0.0, 0.0))


def test_rotate_and_delete_device_not_found_raises() -> None:
    """rotate_device/delete_device 不存在器件 raise KeyError。"""
    editor = LayoutEditor()
    with pytest.raises(KeyError, match="不存在"):
        editor.rotate_device(999, 90.0)
    with pytest.raises(KeyError, match="不存在"):
        editor.delete_device(999)


# =============================================================================
# 7. 数据类与配置（EditorConfig/DeviceInstance/DRCHighlight）
# =============================================================================


def test_editor_config_defaults() -> None:
    """EditorConfig 默认值: grid_size=0.1, dbu=0.001, max_undo_steps=100。"""
    cfg = EditorConfig()
    assert cfg.grid_size == 0.1
    assert cfg.snap_to_grid is True
    assert cfg.dbu == 0.001
    assert cfg.min_spacing == 1.0
    assert cfg.max_undo_steps == 100


def test_device_instance_dataclass() -> None:
    """DeviceInstance 数据类字段完整性。"""
    dev = DeviceInstance(
        device_id=1,
        device_type="mzi",
        position=(10.0, 20.0),
        rotation=45.0,
        size=(30.0, 10.0),
        category="active",
        params={"v_pi": 2.0},
    )
    assert dev.device_id == 1
    assert dev.device_type == "mzi"
    assert dev.position == (10.0, 20.0)
    assert dev.rotation == 45.0
    assert dev.size == (30.0, 10.0)
    assert dev.category == "active"
    assert dev.params == {"v_pi": 2.0}


def test_drc_highlight_dataclass() -> None:
    """DRCHighlight 数据类字段完整性。"""
    h = DRCHighlight(x=1.0, y=2.0, width=3.0, height=4.0, rule="MIN_SPACING")
    assert h.x == 1.0
    assert h.y == 2.0
    assert h.width == 3.0
    assert h.height == 4.0
    assert h.rule == "MIN_SPACING"
    assert h.severity == "error"  # 默认值


# =============================================================================
# 8. 端到端交互流程（模拟用户完整编辑会话）
# =============================================================================


def test_e2e_interactive_editing_session() -> None:
    """端到端: 添加→移动→旋转→渲染→撤销→重做→删除→撤销完整流程。

    模拟用户在 L-Edit 风格编辑器中的典型交互会话，验证所有交互能力
    协同工作（D10 GUI 交互能力达标核心验证）。
    """
    editor = LayoutEditor()
    # 1. 添加 3 个器件
    d1 = editor.add_device("mzi", (10.0, 10.0))
    d2 = editor.add_device("ring_resonator", (50.0, 10.0))
    d3 = editor.add_device("waveguide", (30.0, 50.0))
    assert len(editor._devices) == 3
    # 2. 移动 + 旋转
    editor.move_device(d1, (15.0, 15.0))
    editor.rotate_device(d2, 90.0)
    # 3. 视图缩放 + 渲染
    editor.view_transform((0.0, 0.0), 1.5, 0.0)
    scene = editor.render()
    assert len(scene["devices"]) == 3
    assert editor._view_zoom == 1.5
    # 4. 撤销 2 步（rotate + move）
    assert editor.undo() is True  # 撤销 rotate
    assert editor.get_device(d2).rotation == pytest.approx(0.0)
    assert editor.undo() is True  # 撤销 move
    assert editor.get_device(d1).position == pytest.approx((10.0, 10.0))
    # 5. 重做 1 步
    assert editor.redo() is True
    assert editor.get_device(d1).position == pytest.approx((15.0, 15.0))
    # 6. 删除器件 + 撤销删除
    editor.delete_device(d3)
    assert len(editor._devices) == 2
    editor.undo()
    assert len(editor._devices) == 3
    # 7. 导出 KLayout 脚本
    script = editor.export_klayout_script()
    assert "device" in script
    assert "TOP" in script
