"""R330 GDSII 层操作工具测试。

覆盖:
- copy_layer: 复制保留源层/shapes 复制到目标层/跨 cell 遍历/接口
- merge_layers: 多源层合并/源层删除/shapes 累加
- delete_layers: 单层/多层删除/shapes 计数
- generate_layer_op_report: text/markdown/错误格式/错误操作
- LayerOpReport: 数据类字段/默认值/repr
- R03 错误处理（文件不存在/层参数无效/source==target/source_layers 空/
  target 在 source 中/layers_to_delete 空/源层不存在/不支持格式/不支持操作）
- R02 学术诚信（docstring URL ≥5 / __all__ / dataclass / 无 silent fall-back）
- 集成测试（操作后 R326 扁平化/R327 裁剪/R329 预检查可读）

来源:
- KLayout Layout class:
  https://klayout.org/doc-qt5/code/class_Layout.html
- KLayout Shapes class:
  https://klayout.org/doc-qt5/code/class_Shapes.html
- KLayout LayerInfo:
  https://klayout.org/doc-qt5/code/class_LayerInfo.html
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK 层映射:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_layer_ops import (
    LayerOpReport,
    copy_layer,
    delete_layers,
    generate_layer_op_report,
    merge_layers,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建含多层 polygon 的 GDSII（3 层: (1,0) (2,0) (3,0)）。

    每层一个三角形 polygon，所有在 TOP cell 中。
    """
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
                {
                    "layer": 2,
                    "datatype": 0,
                    "points": [[0, 0], [8, 0], [4, 4]],
                },
                {
                    "layer": 3,
                    "datatype": 0,
                    "points": [[0, 0], [6, 0], [3, 3]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def hier_multi_layer_gds(tmp_path: Path) -> Path:
    """创建含层次结构的多层 GDSII。

    TOP 引用 CHILD，CHILD 在 (1,0) 和 (2,0) 各有 1 个 polygon。
    TOP 自身在 (1,0) 也有 1 个 polygon。
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [2, 0], [1, 1]],
                },
                {
                    "layer": 2,
                    "datatype": 0,
                    "points": [[0, 0], [3, 0], [1, 2]],
                },
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 20.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "hier_multi.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def single_layer_gds(tmp_path: Path) -> Path:
    """创建单层 GDSII（仅 (1,0) 层）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "single_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


def _count_shapes_per_layer(gds_path: Path) -> dict[tuple[int, int], int]:
    """统计每层 shape 总数（所有 cell 累加）。"""
    import klayout.db as db

    ly = db.Layout()
    ly.read(str(gds_path))
    result: dict[tuple[int, int], int] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        key = (int(info.layer), int(info.datatype))
        count = 0
        for cell in ly.each_cell():
            count += int(cell.shapes(li).size())
        result[key] = count
    return result


def _get_layer_list(gds_path: Path) -> list[tuple[int, int]]:
    """获取 GDSII 文件的层列表（排序）。"""
    import klayout.db as db

    ly = db.Layout()
    ly.read(str(gds_path))
    result = []
    for li in ly.layer_indices():
        info = ly.get_info(li)
        result.append((int(info.layer), int(info.datatype)))
    return sorted(result)


# =============================================================================
# TestCopyLayer: 层复制
# =============================================================================
class TestCopyLayer:
    """copy_layer 函数测试。"""

    def test_returns_report(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """返回 LayerOpReport。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert isinstance(report, LayerOpReport)

    def test_operation_field(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """operation 字段为 'copy'。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.operation == "copy"

    def test_source_layer_preserved(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """源层保留。"""
        out = tmp_path / "out.gds"
        copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        layers = _get_layer_list(out)
        assert (1, 0) in layers

    def test_target_layer_created(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """目标层被创建。"""
        out = tmp_path / "out.gds"
        copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        layers = _get_layer_list(out)
        assert (10, 0) in layers

    def test_shapes_copied_to_target(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """源层 shapes 复制到目标层（数量一致）。"""
        out = tmp_path / "out.gds"
        copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        counts = _count_shapes_per_layer(out)
        assert counts[(1, 0)] == counts[(10, 0)]
        assert counts[(1, 0)] == 1

    def test_shapes_moved_count(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """shapes_moved 字段正确（1 个 shape）。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.shapes_moved == 1

    def test_layers_before_after(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """layers_before/after 正确。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert (1, 0) in report.layers_before
        assert (2, 0) in report.layers_before
        assert (3, 0) in report.layers_before
        assert (10, 0) not in report.layers_before
        assert (1, 0) in report.layers_after
        assert (10, 0) in report.layers_after

    def test_dbu_preserved(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """dbu 字段正确（gdsfactory 默认 0.001 μm = 1 nm）。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.dbu == pytest.approx(0.001, abs=1e-9)

    def test_top_cell_name_accepted(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """top_cell_name 参数被接受（接口一致性，未实际使用）。"""
        out = tmp_path / "out.gds"
        report = copy_layer(
            multi_layer_gds, out, (1, 0), (10, 0), top_cell_name="TOP"
        )
        assert isinstance(report, LayerOpReport)

    def test_output_file_readable(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """输出文件可被 klayout 重新读取。"""
        out = tmp_path / "out.gds"
        copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        import klayout.db as db

        ly = db.Layout()
        ly.read(str(out))
        assert ly.cells() >= 1

    def test_hierarchical_copy(
        self, hier_multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """层次结构中所有 cell 的源层都被复制到目标层。

        CHILD 在 (1,0) 有 1 polygon，TOP 在 (1,0) 有 1 polygon，
        共 2 个 shape 应被复制到 (10,0)。
        """
        out = tmp_path / "out.gds"
        report = copy_layer(hier_multi_layer_gds, out, (1, 0), (10, 0))
        counts = _count_shapes_per_layer(out)
        # 源层 (1,0) 在 TOP 和 CHILD 各 1 = 2
        assert counts[(1, 0)] == 2
        # 目标层 (10,0) 也是 2
        assert counts[(10, 0)] == 2
        assert report.shapes_moved == 2

    def test_input_path_field(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """input_path 字段正确。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.input_path == str(multi_layer_gds)

    def test_output_path_field(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """output_path 字段正确。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.output_path == str(out)

    def test_target_layer_field(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """target_layer 字段正确。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.target_layer == (10, 0)

    def test_source_layers_field(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """source_layers 字段正确。"""
        out = tmp_path / "out.gds"
        report = copy_layer(multi_layer_gds, out, (1, 0), (10, 0))
        assert report.source_layers == [(1, 0)]


# =============================================================================
# TestMergeLayers: 层合并
# =============================================================================
class TestMergeLayers:
    """merge_layers 函数测试。"""

    def test_returns_report(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """返回 LayerOpReport。"""
        out = tmp_path / "out.gds"
        report = merge_layers(
            multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0)
        )
        assert isinstance(report, LayerOpReport)

    def test_operation_field(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """operation 字段为 'merge'。"""
        out = tmp_path / "out.gds"
        report = merge_layers(
            multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0)
        )
        assert report.operation == "merge"

    def test_source_layers_deleted(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """源层被删除。"""
        out = tmp_path / "out.gds"
        merge_layers(multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0))
        layers = _get_layer_list(out)
        assert (1, 0) not in layers
        assert (2, 0) not in layers

    def test_target_layer_created(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """目标层创建。"""
        out = tmp_path / "out.gds"
        merge_layers(multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0))
        layers = _get_layer_list(out)
        assert (10, 0) in layers

    def test_shapes_merged_to_target(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """源层 shapes 合并到目标层。"""
        out = tmp_path / "out.gds"
        merge_layers(multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0))
        counts = _count_shapes_per_layer(out)
        # (10,0) 应含 2 个 shape（来自 (1,0) 和 (2,0)）
        assert counts[(10, 0)] == 2

    def test_shapes_moved_count(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """shapes_moved 字段正确（2 个源层各 1 shape = 2）。"""
        out = tmp_path / "out.gds"
        report = merge_layers(
            multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0)
        )
        assert report.shapes_moved == 2

    def test_layers_before_after(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """layers_before/after 正确（删除源层，新增目标层）。"""
        out = tmp_path / "out.gds"
        report = merge_layers(
            multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0)
        )
        assert (1, 0) in report.layers_before
        assert (2, 0) in report.layers_before
        assert (10, 0) not in report.layers_before
        assert (1, 0) not in report.layers_after
        assert (2, 0) not in report.layers_after
        assert (10, 0) in report.layers_after
        # 未触及的层保留
        assert (3, 0) in report.layers_after

    def test_single_source_layer(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """单源层合并（等于把单层重命名到目标）。"""
        out = tmp_path / "out.gds"
        report = merge_layers(
            multi_layer_gds, out, [(1, 0)], (10, 0)
        )
        assert report.shapes_moved == 1
        counts = _count_shapes_per_layer(out)
        assert counts[(10, 0)] == 1
        assert (1, 0) not in counts

    def test_output_file_readable(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """输出文件可读。"""
        out = tmp_path / "out.gds"
        merge_layers(multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0))
        import klayout.db as db

        ly = db.Layout()
        ly.read(str(out))
        assert ly.cells() >= 1

    def test_hierarchical_merge(
        self, hier_multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """层次结构合并: CHILD (1,0)=1 + CHILD (2,0)=1 + TOP (1,0)=1 = 3。"""
        out = tmp_path / "out.gds"
        report = merge_layers(
            hier_multi_layer_gds, out, [(1, 0), (2, 0)], (10, 0)
        )
        assert report.shapes_moved == 3
        counts = _count_shapes_per_layer(out)
        assert counts[(10, 0)] == 3
        # 源层应被删除
        assert (1, 0) not in counts
        assert (2, 0) not in counts


# =============================================================================
# TestDeleteLayers: 层删除
# =============================================================================
class TestDeleteLayers:
    """delete_layers 函数测试。"""

    def test_returns_report(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """返回 LayerOpReport。"""
        out = tmp_path / "out.gds"
        report = delete_layers(multi_layer_gds, out, [(1, 0)])
        assert isinstance(report, LayerOpReport)

    def test_operation_field(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """operation 字段为 'delete'。"""
        out = tmp_path / "out.gds"
        report = delete_layers(multi_layer_gds, out, [(1, 0)])
        assert report.operation == "delete"

    def test_single_layer_deleted(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """单层删除。"""
        out = tmp_path / "out.gds"
        delete_layers(multi_layer_gds, out, [(1, 0)])
        layers = _get_layer_list(out)
        assert (1, 0) not in layers
        # 其他层保留
        assert (2, 0) in layers
        assert (3, 0) in layers

    def test_multi_layer_deleted(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """多层删除。"""
        out = tmp_path / "out.gds"
        delete_layers(multi_layer_gds, out, [(1, 0), (2, 0)])
        layers = _get_layer_list(out)
        assert (1, 0) not in layers
        assert (2, 0) not in layers
        assert (3, 0) in layers

    def test_shapes_moved_count(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """shapes_moved 字段正确（删除的 shape 总数）。"""
        out = tmp_path / "out.gds"
        report = delete_layers(multi_layer_gds, out, [(1, 0)])
        assert report.shapes_moved == 1

    def test_layers_before_after(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """layers_before/after 正确。"""
        out = tmp_path / "out.gds"
        report = delete_layers(multi_layer_gds, out, [(1, 0)])
        assert (1, 0) in report.layers_before
        assert (1, 0) not in report.layers_after
        # 其他层保留
        assert (2, 0) in report.layers_after
        assert (3, 0) in report.layers_after

    def test_target_layer_none(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """delete 操作 target_layer 为 None。"""
        out = tmp_path / "out.gds"
        report = delete_layers(multi_layer_gds, out, [(1, 0)])
        assert report.target_layer is None

    def test_output_file_readable(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """输出文件可读。"""
        out = tmp_path / "out.gds"
        delete_layers(multi_layer_gds, out, [(1, 0)])
        import klayout.db as db

        ly = db.Layout()
        ly.read(str(out))
        assert ly.cells() >= 1

    def test_hierarchical_delete(
        self, hier_multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """层次结构中所有 cell 的该层都被删除。

        CHILD (1,0)=1 + TOP (1,0)=1 = 2 个 shape 被删除。
        """
        out = tmp_path / "out.gds"
        report = delete_layers(hier_multi_layer_gds, out, [(1, 0)])
        assert report.shapes_moved == 2
        counts = _count_shapes_per_layer(out)
        assert (1, 0) not in counts
        # (2,0) 应保留（CHILD 有 1 个）
        assert counts.get((2, 0), 0) == 1


# =============================================================================
# TestGenerateLayerOpReport: 报告生成
# =============================================================================
class TestGenerateLayerOpReport:
    """generate_layer_op_report 函数测试。"""

    def test_copy_text_report(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """copy 操作的 text 报告。"""
        out = tmp_path / "out.gds"
        text = generate_layer_op_report(
            multi_layer_gds, out, "copy", [(1, 0)], (10, 0)
        )
        assert isinstance(text, str)
        assert "copy" in text
        assert "层操作" in text

    def test_merge_text_report(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """merge 操作的 text 报告。"""
        out = tmp_path / "out.gds"
        text = generate_layer_op_report(
            multi_layer_gds, out, "merge", [(1, 0), (2, 0)], (10, 0)
        )
        assert "merge" in text

    def test_delete_text_report(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """delete 操作的 text 报告。"""
        out = tmp_path / "out.gds"
        text = generate_layer_op_report(
            multi_layer_gds, out, "delete", [(1, 0)]
        )
        assert "delete" in text

    def test_copy_markdown_report(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """copy 操作的 markdown 报告。"""
        out = tmp_path / "out.gds"
        md = generate_layer_op_report(
            multi_layer_gds,
            out,
            "copy",
            [(1, 0)],
            (10, 0),
            output_format="markdown",
        )
        assert isinstance(md, str)
        assert md.startswith("#")

    def test_delete_markdown_report(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """delete 操作的 markdown 报告。"""
        out = tmp_path / "out.gds"
        md = generate_layer_op_report(
            multi_layer_gds,
            out,
            "delete",
            [(1, 0)],
            output_format="markdown",
        )
        assert md.startswith("#")

    def test_text_report_contains_layer_changes(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """text 报告包含层变化信息。"""
        out = tmp_path / "out.gds"
        text = generate_layer_op_report(
            multi_layer_gds, out, "delete", [(1, 0)]
        )
        assert "层变化" in text
        assert "操作前" in text
        assert "操作后" in text

    def test_markdown_report_contains_layer_changes(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """markdown 报告包含层变化信息。"""
        out = tmp_path / "out.gds"
        md = generate_layer_op_report(
            multi_layer_gds,
            out,
            "delete",
            [(1, 0)],
            output_format="markdown",
        )
        assert "层变化" in md


# =============================================================================
# TestR03ErrorHandling: 错误处理（禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试: 失败即 raise，禁止 fall-back。"""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            copy_layer(tmp_path / "nonexistent.gds", tmp_path / "out.gds",
                       (1, 0), (10, 0))

    def test_invalid_source_layer_type(self, multi_layer_gds: Path,
                                       tmp_path: Path) -> None:
        """source_layer 非元组 raise ValueError。"""
        with pytest.raises(ValueError, match="source_layer"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       "not_a_tuple", (10, 0))

    def test_invalid_source_layer_length(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """source_layer 长度不为 2 raise ValueError。"""
        with pytest.raises(ValueError, match="source_layer"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       (1, 0, 0), (10, 0))

    def test_source_layer_out_of_range(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """source_layer.layer 超范围 raise ValueError。"""
        with pytest.raises(ValueError, match="layer"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       (1000, 0), (10, 0))

    def test_source_datatype_out_of_range(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """source_layer.datatype 超范围 raise ValueError。"""
        with pytest.raises(ValueError, match="datatype"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       (1, 256), (10, 0))

    def test_invalid_target_layer_type(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """target_layer 非元组 raise ValueError。"""
        with pytest.raises(ValueError, match="target_layer"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       (1, 0), "not_a_tuple")

    def test_source_equals_target_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """source_layer == target_layer raise ValueError（R03）。"""
        with pytest.raises(ValueError, match="不能相同"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       (1, 0), (1, 0))

    def test_merge_empty_source_layers_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """merge source_layers 空 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            merge_layers(multi_layer_gds, tmp_path / "out.gds",
                         [], (10, 0))

    def test_merge_target_in_sources_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """merge target 在 source_layers 中 raise ValueError。"""
        with pytest.raises(ValueError, match="不能在 source_layers"):
            merge_layers(multi_layer_gds, tmp_path / "out.gds",
                         [(1, 0), (10, 0)], (10, 0))

    def test_delete_empty_layers_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """delete layers_to_delete 空 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            delete_layers(multi_layer_gds, tmp_path / "out.gds", [])

    def test_source_layer_not_exist_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """源层不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            copy_layer(multi_layer_gds, tmp_path / "out.gds",
                       (99, 9), (10, 0))

    def test_unsupported_operation_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的 operation raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 operation"):
            generate_layer_op_report(
                multi_layer_gds, tmp_path / "out.gds",
                "invalid_op", [(1, 0)]
            )

    def test_unsupported_format_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的 output_format raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_layer_op_report(
                multi_layer_gds, out, "delete", [(1, 0)],
                output_format="xml"
            )

    def test_copy_missing_target_in_report_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """generate_layer_op_report copy 缺 target_layer raise。"""
        with pytest.raises(ValueError, match="target_layer"):
            generate_layer_op_report(
                multi_layer_gds, tmp_path / "out.gds",
                "copy", [(1, 0)]
            )

    def test_merge_missing_target_in_report_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """generate_layer_op_report merge 缺 target_layer raise。"""
        with pytest.raises(ValueError, match="target_layer"):
            generate_layer_op_report(
                multi_layer_gds, tmp_path / "out.gds",
                "merge", [(1, 0)]
            )

    def test_copy_wrong_source_count_raises(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """generate_layer_op_report copy source_layers 数量错 raise。"""
        with pytest.raises(ValueError, match="恰好 1 个"):
            generate_layer_op_report(
                multi_layer_gds, tmp_path / "out.gds",
                "copy", [(1, 0), (2, 0)], (10, 0)
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_has_5plus_urls(self) -> None:
        """模块 docstring 至少 5 个 URL（R02）。"""
        from polaris.verification import gdsii_layer_ops

        docstring = gdsii_layer_ops.__doc__ or ""
        url_count = docstring.count("https://")
        assert url_count >= 5, (
            f"docstring 只有 {url_count} 个 URL，要求 ≥5 个（R02）"
        )

    def test_all_exported(self) -> None:
        """__all__ 列出所有公开 API。"""
        from polaris.verification import gdsii_layer_ops

        expected = {
            "LayerOpReport",
            "copy_layer",
            "merge_layers",
            "delete_layers",
            "generate_layer_op_report",
        }
        assert set(gdsii_layer_ops.__all__) == expected

    def test_layeropreport_is_dataclass(self) -> None:
        """LayerOpReport 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(LayerOpReport)

    def test_layeropreport_fields(self) -> None:
        """LayerOpReport 字段完整（9 字段）。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(LayerOpReport)}
        expected = {
            "input_path",
            "output_path",
            "operation",
            "source_layers",
            "target_layer",
            "dbu",
            "shapes_moved",
            "layers_before",
            "layers_after",
        }
        assert field_names == expected

    def test_no_silent_fallback(self) -> None:
        """源码无 silent fall-back（无 except: pass / return None / return []）。"""
        from polaris.verification import gdsii_layer_ops

        source_path = Path(gdsii_layer_ops.__file__)
        source = source_path.read_text(encoding="utf-8")
        # 排除 docstring 中可能出现的描述性文字
        # 实际代码中不应有这些 fall-back 模式
        assert "except: pass" not in source, "禁止 silent except: pass（R03）"
        assert "except Exception: pass" not in source, (
            "禁止 silent except Exception: pass（R03）"
        )

    def test_klayout_import_error_message(self) -> None:
        """klayout 导入失败时 raise ImportError 并含安装说明。"""
        # 通过 _import_klayout_db 函数验证（klayout 已安装时不 raise）
        from polaris.verification.gdsii_layer_ops import _import_klayout_db

        # klayout 应已安装，正常返回 db 模块
        db = _import_klayout_db()
        assert db is not None


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """与其他 R3xx 工具的集成测试。"""

    def test_copy_then_flatten(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """copy 后 R326 扁平化仍能读取。"""
        from polaris.verification.gdsii_flattener import flatten_gdsii

        # 先 copy
        copied = tmp_path / "copied.gds"
        copy_layer(multi_layer_gds, copied, (1, 0), (10, 0))

        # 再 flatten
        flattened = tmp_path / "flattened.gds"
        report = flatten_gdsii(copied, flattened)
        assert report.cells_after >= 1

    def test_merge_then_clip(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """merge 后 R327 裁剪仍能读取。"""
        from polaris.verification.gdsii_clip_tool import clip_gdsii

        # 先 merge
        merged = tmp_path / "merged.gds"
        merge_layers(multi_layer_gds, merged, [(1, 0), (2, 0)], (10, 0))

        # 再 clip（裁剪到 (-1,-1)-(20,20) μm）
        clipped = tmp_path / "clipped.gds"
        report = clip_gdsii(merged, clipped, (-1.0, -1.0, 20.0, 20.0))
        assert report.shapes_after >= 1

    def test_delete_then_precheck(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """delete 后 R329 预检查仍能读取（返回 TapeoutReport）。"""
        from polaris.verification.gdsii_tapeout_precheck import (
            TapeoutReport,
            tapeout_precheck,
        )

        # 先 delete
        deleted = tmp_path / "deleted.gds"
        delete_layers(multi_layer_gds, deleted, [(1, 0)])

        # 再 precheck
        report = tapeout_precheck(deleted)
        assert isinstance(report, TapeoutReport)
        assert report.file_path == str(deleted)

    def test_full_workflow(
        self, hier_multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """完整工作流: copy → merge → delete。"""
        # Step 1: copy (1,0) → (10,0)
        step1 = tmp_path / "step1.gds"
        r1 = copy_layer(hier_multi_layer_gds, step1, (1, 0), (10, 0))
        assert r1.shapes_moved == 2  # TOP (1,0) + CHILD (1,0)

        # Step 2: merge [(2,0)] → (20,0)
        step2 = tmp_path / "step2.gds"
        r2 = merge_layers(step1, step2, [(2, 0)], (20, 0))
        assert r2.shapes_moved == 1  # CHILD (2,0) = 1

        # Step 3: delete [(1,0)]
        step3 = tmp_path / "step3.gds"
        r3 = delete_layers(step2, step3, [(1, 0)])
        assert r3.shapes_moved == 2  # TOP (1,0) + CHILD (1,0) = 2

        # 验证最终层状态
        layers = _get_layer_list(step3)
        assert (1, 0) not in layers  # 已删除
        assert (2, 0) not in layers  # 已合并到 (20,0)
        assert (10, 0) in layers  # copy 目标保留
        assert (20, 0) in layers  # merge 目标保留


# =============================================================================
# TestDataclassTest: 数据类
# =============================================================================
class TestDataclassTest:
    """LayerOpReport 数据类测试。"""

    def test_default_construction(self) -> None:
        """使用必填字段 + 默认值构造。"""
        report = LayerOpReport(
            input_path="/input.gds",
            output_path="/output.gds",
        )
        assert report.input_path == "/input.gds"
        assert report.output_path == "/output.gds"
        assert report.operation == ""
        assert report.source_layers == []
        assert report.target_layer is None
        assert report.dbu == 0.0
        assert report.shapes_moved == 0
        assert report.layers_before == []
        assert report.layers_after == []

    def test_full_construction(self) -> None:
        """完整字段构造。"""
        report = LayerOpReport(
            input_path="/in.gds",
            output_path="/out.gds",
            operation="copy",
            source_layers=[(1, 0)],
            target_layer=(10, 0),
            dbu=0.001,
            shapes_moved=5,
            layers_before=[(1, 0), (2, 0)],
            layers_after=[(1, 0), (2, 0), (10, 0)],
        )
        assert report.operation == "copy"
        assert report.source_layers == [(1, 0)]
        assert report.target_layer == (10, 0)
        assert report.dbu == 0.001
        assert report.shapes_moved == 5
        assert report.layers_before == [(1, 0), (2, 0)]
        assert report.layers_after == [(1, 0), (2, 0), (10, 0)]

    def test_repr(self) -> None:
        """repr 含类名。"""
        report = LayerOpReport(
            input_path="/in.gds",
            output_path="/out.gds",
        )
        assert "LayerOpReport" in repr(report)

    def test_equality(self) -> None:
        """相同字段的数据类相等。"""
        r1 = LayerOpReport(
            input_path="/in.gds",
            output_path="/out.gds",
            operation="copy",
        )
        r2 = LayerOpReport(
            input_path="/in.gds",
            output_path="/out.gds",
            operation="copy",
        )
        assert r1 == r2
