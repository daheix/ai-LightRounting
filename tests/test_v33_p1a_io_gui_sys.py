"""Bug #v3.3-IO-2 / #v3.3-GUI-1 / #v3.3-SYS-2 回归测试。

覆盖 3 个 P1-A 算法 Bug 修复验收标准：

#v3.3-IO-2: GDS/OASIS（实际为 OpenAccess/LEF-DEF/CIF）读写不对称
- OpenAccess Instance mirror/mag 字段对称读写
- LEF/DEF Instance angle/mirror 完整 8 种 orient 对称读写
- LEF/DEF mag != 1.0 raise（标准不支持 magnification）
- CIF mag != 1.0 raise（标准不支持 magnification）

#v3.3-GUI-1: RemoveObjectCommand / delete_device 浅拷贝
- layout_editor.delete_device 撤销时 params 嵌套结构不被外部修改污染
- _copy_device 使用 copy.deepcopy 保证快照独立

#v3.3-SYS-2: TaskResult._future 字段未声明
- 确认 _future 字段已声明、有类型注解、默认 None
- 确认 submit() 在 threading 后端正确赋值 _future

学术来源（R02 学术诚信，≥5 条）：
- Python copy 模块 deepcopy: https://docs.python.org/3/library/copy.html#copy.deepcopy
- 浅拷贝陷阱: https://docs.python.org/3/library/copy.html#shallow-vs-deep-copy
- KLayout 变换 (mirror/mag/angle): https://www.klayout.org/downloads/master/doc-qt5/about/transformations.html
- LEF/DEF 5.8 Language Reference §Components:
  http://coriolis.lip6.fr/doc/lefdef/lefdefref/DEFSyntax.html
- Si2 OpenAccess 22.60 API Reference: https://si2.org/openaccess/
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980, Appendix C: CIF
- Gamma et al., "Design Patterns", Addison-Wesley 1994 (Command Pattern)
  https://en.wikipedia.org/wiki/Command_pattern
"""

from __future__ import annotations

import time
from concurrent.futures import Future

import pytest

from polaris.gui.layout_editor import (
    DeviceInstance,
    EditorConfig,
    LayoutEditor,
    _copy_device,
)
from polaris.io._cif import write_cif
from polaris.io._lef_def import (
    _lef_def_orient,
    _lef_def_parse_orient,
    read_lef_def,
    write_lef_def,
)
from polaris.io.multi_format import (
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    Point,
    Shape,
)
from polaris.io.openaccess import read_oa, write_oa
from polaris.system import (
    DistributedConfig,
    DistributedTaskScheduler,
    TaskResult,
    TaskStatus,
)


# =============================================================================
# #v3.3-GUI-1: delete_device / _copy_device 浅拷贝 → deepcopy 回归测试
# =============================================================================


class TestGuiShallowCopyBug:
    """layout_editor.py 浅拷贝 Bug 回归测试（v3.3-GUI-1）。"""

    def test_copy_device_deepcopies_nested_params(self) -> None:
        """_copy_device 必须深拷贝 params 嵌套可变对象。

        复现路径：原 dev.params 含嵌套 list，深拷贝后修改原 list，
        快照的 list 不应被污染（旧实现 dict() 浅拷贝会污染）。
        """
        dev = DeviceInstance(
            device_id=1,
            device_type="mzi",
            position=(10.0, 20.0),
            rotation=0.0,
            size=(30.0, 10.0),
            category="passive",
            params={"coupling_gap": 0.1, "ports": ["in", "out", "dc"]},
        )
        snapshot = _copy_device(dev)
        # 修改原 dev 的嵌套 list
        dev.params["ports"].append("extra")
        # 快照不应被污染
        assert snapshot.params["ports"] == ["in", "out", "dc"]
        assert dev.params["ports"] == ["in", "out", "dc", "extra"]
        assert snapshot.params["ports"] is not dev.params["ports"]

    def test_delete_device_undo_preserves_nested_params(self) -> None:
        """delete_device 撤销时 params 嵌套结构保持独立。

        复现路径：
        1. 添加器件 params={"tags": ["a"]}
        2. delete_device（snapshot 保存）
        3. 修改原器件 params 的 tags（通过外部引用）
        4. undo 恢复器件
        5. 验证恢复的器件 params.tags 不被污染
        """
        editor = LayoutEditor(EditorConfig(snap_to_grid=False))
        original_params = {"tags": ["a", "b"], "config": {"radius": 5.0}}
        dev_id = editor.add_device(
            "mzi", (10.0, 20.0), params=original_params
        )
        # 拿到器件引用，模拟外部持有
        dev_ref = editor.get_device(dev_id)
        # 删除器件（触发 snapshot 深拷贝）
        editor.delete_device(dev_id)
        # 通过外部引用修改原 params 嵌套结构
        dev_ref.params["tags"].append("polluted")
        dev_ref.params["config"]["radius"] = 999.0
        # 撤销删除，恢复器件
        assert editor.undo() is True
        # 恢复的器件 params 必须是删除前的原始值，不被污染
        restored = editor.get_device(dev_id)
        assert restored.params["tags"] == ["a", "b"]
        assert restored.params["config"]["radius"] == 5.0

    def test_add_device_deepcopies_input_params(self) -> None:
        """add_device 必须深拷贝传入的 params，避免外部修改污染内部状态。"""
        editor = LayoutEditor(EditorConfig(snap_to_grid=False))
        input_params = {"ports": ["in", "out"]}
        dev_id = editor.add_device("mzi", (0.0, 0.0), params=input_params)
        # 修改输入 params
        input_params["ports"].append("extra")
        # 编辑器内部器件不应被污染
        dev = editor.get_device(dev_id)
        assert dev.params["ports"] == ["in", "out"]

    def test_undo_redo_state_independence(self) -> None:
        """undo/redo 多次往返后 params 嵌套结构保持独立（深拷贝保证）。

        验证：delete→undo→redo→undo 往返后，恢复的器件 params 仍为
        原始值。注意：命令模式下 redo 会把"当前状态"作为下次 undo 的
        目标，故不在 redo 前修改状态（那是命令模式的预期行为），
        而是验证多次往返后深拷贝仍保证 params 完整性。
        """
        editor = LayoutEditor(EditorConfig(snap_to_grid=False))
        original_params = {"nested": {"value": 1}, "tags": ["a"]}
        dev_id = editor.add_device("mzi", (0.0, 0.0), params=original_params)
        # delete → undo → redo → undo 完整往返
        editor.delete_device(dev_id)
        assert editor.undo() is True  # 恢复器件
        assert editor.redo() is True  # 再次删除
        assert editor.undo() is True  # 再次恢复
        # 恢复后的器件 params 必须是原始值
        restored = editor.get_device(dev_id)
        assert restored.params["nested"]["value"] == 1
        assert restored.params["tags"] == ["a"]
        # 修改原 params 不应影响已恢复的器件
        original_params["tags"].append("polluted")
        original_params["nested"]["value"] = 999
        assert restored.params["tags"] == ["a"]
        assert restored.params["nested"]["value"] == 1


# =============================================================================
# #v3.3-IO-2: OpenAccess Instance mirror/mag 读写对称
# =============================================================================


class TestOpenAccessIOSymmetry:
    """OpenAccess ASCII Instance 读写对称性测试（v3.3-IO-2）。"""

    def _build_layout_with_instance(
        self, angle: float = 0.0, mirror: bool = False, mag: float = 1.0
    ) -> FormatLayout:
        """构造含 Instance 的 FormatLayout。"""
        cell = Cell(name="TOP", shapes=[
            Shape("rect", "WG", [Point(5.0, 5.0)], width=10.0, height=10.0)
        ])
        inst = Instance(
            name="i1", cell_name="TOP", origin=Point(100.0, 200.0),
            angle=angle, mirror=mirror, mag=mag,
        )
        sub = Cell(name="SUB", instances=[inst])
        return FormatLayout(
            name="oa_layout",
            cells=[cell, sub],
            layers={"WG": LayerInfo(name="WG", number=1, datatype=0)},
            top_cell="SUB",
            unit="dbu",
        )

    def test_mirror_mag_roundtrip(self) -> None:
        """mirror=True + mag=2.0 写入后读取必须保持一致。"""
        layout = self._build_layout_with_instance(
            angle=45.0, mirror=True, mag=2.0
        )
        text = write_oa(layout)
        restored = read_oa(text)
        # 找到 Instance
        assert len(restored.cells) == 2
        sub_cell = next(c for c in restored.cells if c.name == "SUB")
        assert len(sub_cell.instances) == 1
        inst = sub_cell.instances[0]
        assert inst.name == "i1"
        assert inst.cell_name == "TOP"
        assert inst.origin.x == pytest.approx(100.0)
        assert inst.origin.y == pytest.approx(200.0)
        assert inst.angle == pytest.approx(45.0)
        assert inst.mirror is True
        assert inst.mag == pytest.approx(2.0)

    def test_default_values_roundtrip(self) -> None:
        """默认值（mirror=False, mag=1.0, angle=0）写入后读取保持默认。"""
        layout = self._build_layout_with_instance()
        text = write_oa(layout)
        restored = read_oa(text)
        sub_cell = next(c for c in restored.cells if c.name == "SUB")
        inst = sub_cell.instances[0]
        assert inst.mirror is False
        assert inst.mag == pytest.approx(1.0)
        assert inst.angle == pytest.approx(0.0)

    def test_angle_only_roundtrip(self) -> None:
        """仅 angle != 0 时写入读取对称。"""
        layout = self._build_layout_with_instance(angle=90.0)
        text = write_oa(layout)
        restored = read_oa(text)
        inst = next(c for c in restored.cells if c.name == "SUB").instances[0]
        assert inst.angle == pytest.approx(90.0)
        assert inst.mirror is False
        assert inst.mag == pytest.approx(1.0)


# =============================================================================
# #v3.3-IO-2: LEF/DEF Instance angle/mirror 读写对称 + mag raise
# =============================================================================


class TestLefDefIOSymmetry:
    """LEF/DEF Instance 读写对称性测试（v3.3-IO-2）。"""

    def _build_lef_def_layout(
        self, angle: float = 0.0, mirror: bool = False, mag: float = 1.0
    ) -> FormatLayout:
        """构造含 Instance 的 LEF/DEF FormatLayout。"""
        macro = Cell(name="INV", shapes=[
            Shape("rect", "M1", [Point(0.0, 0.0)], width=2.0, height=4.0)
        ])
        inst = Instance(
            name="u1", cell_name="INV", origin=Point(10.0, 20.0),
            angle=angle, mirror=mirror, mag=mag,
        )
        top = Cell(name="TOP", instances=[inst])
        return FormatLayout(
            name="lef_def_layout",
            cells=[macro, top],
            layers={"M1": LayerInfo(name="M1", number=41, datatype=0)},
            top_cell="TOP",
            unit="um",
        )

    @pytest.mark.parametrize(
        "angle,mirror,orient",
        [
            (0.0, False, "N"),
            (90.0, False, "E"),
            (180.0, False, "S"),
            (270.0, False, "W"),
            (0.0, True, "FN"),
            (90.0, True, "FE"),
            (180.0, True, "FS"),
            (270.0, True, "FW"),
        ],
    )
    def test_all_8_orient_roundtrip(
        self, angle: float, mirror: bool, orient: str
    ) -> None:
        """LEF/DEF 5.8 全部 8 种 orient 读写对称。

        LEF/DEF 读取时 instance 按 cell_name 归属到对应 MACRO
        （见 _lef_def_attach_instances），故在 INV macro 上查找。
        """
        # 验证正向映射
        assert _lef_def_orient(angle, mirror) == orient
        # 验证反向映射
        a, m = _lef_def_parse_orient(orient)
        assert a == pytest.approx(angle)
        assert m == mirror
        # 验证完整 write→read 往返
        layout = self._build_lef_def_layout(angle=angle, mirror=mirror)
        text = write_lef_def(layout)
        restored = read_lef_def(text)
        # instance 按 cell_name 归属到 INV macro
        inv_cell = next(c for c in restored.cells if c.name == "INV")
        assert len(inv_cell.instances) == 1
        inst = inv_cell.instances[0]
        assert inst.name == "u1"
        assert inst.cell_name == "INV"
        assert inst.origin.x == pytest.approx(10.0)
        assert inst.origin.y == pytest.approx(20.0)
        assert inst.angle == pytest.approx(angle)
        assert inst.mirror == mirror

    def test_mag_nonunity_raises(self) -> None:
        """LEF/DEF 5.8 不支持 magnification，mag != 1.0 必须 raise。"""
        layout = self._build_lef_def_layout(mag=2.0)
        with pytest.raises(ValueError, match="不支持 magnification"):
            write_lef_def(layout)

    def test_arbitrary_angle_raises(self) -> None:
        """LEF/DEF 5.8 仅支持 0/90/180/270 正交角度，任意角度 raise。"""
        with pytest.raises(ValueError, match="仅支持 0/90/180/270"):
            _lef_def_orient(45.0, False)

    def test_unknown_orient_raises(self) -> None:
        """未知 orient 字符串 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="未知 orient"):
            _lef_def_parse_orient("XYZ")


# =============================================================================
# #v3.3-IO-2: CIF mag != 1.0 raise（CIF 标准不支持 magnification）
# =============================================================================


class TestCifIOSymmetry:
    """CIF Instance 读写对称性测试（v3.3-IO-2）。"""

    def test_cif_mag_nonunity_raises(self) -> None:
        """CIF 标准不支持 magnification，mag != 1.0 必须 raise。"""
        cell = Cell(name="TOP", shapes=[
            Shape("rect", "WG", [Point(0.0, 0.0)], width=10, height=10)
        ])
        sub = Cell(name="SUB", instances=[
            Instance(
                name="i1", cell_name="TOP", origin=Point(0.0, 0.0),
                mag=2.0,  # CIF 不支持
            )
        ])
        layout = FormatLayout(
            name="cif_layout",
            cells=[cell, sub],
            layers={"WG": LayerInfo(name="WG")},
            top_cell="SUB",
            unit="centimicron",
        )
        with pytest.raises(ValueError, match="不支持 magnification"):
            write_cif(layout)

    def test_cif_mirror_roundtrip(self) -> None:
        """CIF mirror=True 写入读取对称（mag=1.0 默认）。"""
        from polaris.io._cif import read_cif

        cell = Cell(name="TOP", shapes=[
            Shape("rect", "WG", [Point(0.0, 0.0)], width=10, height=10)
        ])
        sub = Cell(name="SUB", instances=[
            Instance(
                name="i1", cell_name="TOP", origin=Point(100.0, 200.0),
                mirror=True,
            )
        ])
        layout = FormatLayout(
            name="cif_layout",
            cells=[cell, sub],
            layers={"WG": LayerInfo(name="WG")},
            top_cell="SUB",
            unit="centimicron",
        )
        text = write_cif(layout)
        restored = read_cif(text)
        # 找到含 Instance 的 cell
        sub_cell = next(c for c in restored.cells if c.name == "SUB")
        assert len(sub_cell.instances) == 1
        inst = sub_cell.instances[0]
        assert inst.mirror is True
        assert inst.mag == pytest.approx(1.0)


# =============================================================================
# #v3.3-SYS-2: TaskResult._future 字段声明验证
# =============================================================================


class TestSysFutureFieldDeclared:
    """TaskResult._future 字段声明验证（v3.3-SYS-2）。

    确认 _future 字段已声明、有类型注解、默认 None，
    且 threading 后端 submit() 正确赋值 Future 对象。
    """

    def test_future_field_declared_with_default_none(self) -> None:
        """_future 字段必须存在且默认 None。"""
        result = TaskResult(task_id="t1")
        assert hasattr(result, "_future")
        assert result._future is None

    def test_future_field_has_type_annotation(self) -> None:
        """_future 字段必须有类型注解（Any）。"""
        from dataclasses import fields
        future_field = next(
            f for f in fields(TaskResult) if f.name == "_future"
        )
        assert future_field.type is not None
        # 默认值必须是 None
        assert future_field.default is None
        # 不参与构造函数（init=False）
        assert future_field.init is False
        # 不参与 repr（repr=False，避免泄露内部状态）
        assert future_field.repr is False

    def test_future_field_assignable(self) -> None:
        """_future 字段必须可赋值 Future 对象。"""
        result = TaskResult(task_id="t1")
        fut = Future()
        result._future = fut
        assert result._future is fut

    def test_threading_backend_assigns_future(self) -> None:
        """threading 后端 submit() 必须为 _future 赋值 Future 对象。

        验证 submit() 第 213 行 `result._future = future` 正确执行。
        """
        scheduler = DistributedTaskScheduler(
            DistributedConfig(backend="threading", num_workers=1)
        )
        try:
            task_id = scheduler.submit("t1", lambda: 42)
            # 等待任务完成
            assert scheduler.wait_all(timeout=5.0)
            result = scheduler.get_result(task_id)
            assert result is not None
            assert result.status == TaskStatus.COMPLETED
            # _future 必须被赋值为 Future 对象
            assert result._future is not None
            assert hasattr(result._future, "result")
            assert hasattr(result._future, "done")
        finally:
            scheduler.shutdown()

    def test_sequential_backend_future_remains_none(self) -> None:
        """sequential 后端不使用线程池，_future 保持 None。"""
        scheduler = DistributedTaskScheduler(
            DistributedConfig(backend="sequential")
        )
        try:
            task_id = scheduler.submit("t1", lambda: 42)
            result = scheduler.get_result(task_id)
            assert result is not None
            assert result.status == TaskStatus.COMPLETED
            # sequential 后端不创建 Future
            assert result._future is None
        finally:
            scheduler.shutdown()
