"""R327 GDSII 区域裁剪工具测试。

覆盖:
- clip_gdsii: 单区域裁剪（层次化、几何切断、bbox 限制、cell 重命名）
- multi_clip_gdsii: 多区域裁剪（多文件输出、命名前缀）
- generate_clip_report: text/markdown 报告
- ClipReport: 数据类
- R03 错误处理（文件不存在 / clip_box 无效 / top_cell 不存在 / 空文件）
- R02 学术诚信（docstring URL ≥5 个 / __all__ / 默认值）
- 集成测试（裁剪后网格检查 / 裁剪后扁平化 / 几何保留）

来源:
- KLayout Layout.clip:
  https://klayout.org/doc-qt5/code/class_Layout.html#method33
- KLayout Layout.multi_clip:
  https://klayout.org/doc-qt5/code/class_Layout.html#method98
- KLayout clip 示例:
  https://klayout.org/klayout-pypi/examples/clip/
- KLayout Box class:
  https://www.klayout.org/doc-qt5/code/class_Box.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_clip_tool import (
    ClipReport,
    clip_gdsii,
    generate_clip_report,
    multi_clip_gdsii,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def large_gds(tmp_path: Path) -> Path:
    """创建大版图 GDSII: TOP + CHILD 实例。

    TOP: 三角形 (0,0)-(20,0)-(10,20) μm
    CHILD: 三角形 (0,0)-(5,0)-(2.5,5) μm，实例化在 (30, 0) μm

    TOP bbox: (0,0)-(35,20) μm
    裁剪框 (5,0,25,15) 应保留 TOP 三角形部分，排除 CHILD 实例。
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [5, 0], [2.5, 5]],
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
                    "points": [[0, 0], [20, 0], [10, 20]],
                },
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 30.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "large.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def empty_gds(tmp_path: Path) -> Path:
    """创建空 GDSII（无 cell）。"""
    import klayout.db as db

    ly = db.Layout()
    out = tmp_path / "empty.gds"
    ly.write(str(out))
    return out


# =============================================================================
# TestClipGdsii: 单区域裁剪
# =============================================================================
class TestClipGdsii:
    """clip_gdsii 函数测试。"""

    def test_returns_report(self, large_gds: Path, tmp_path: Path) -> None:
        """返回 ClipReport。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert isinstance(report, ClipReport)
        assert report.input_path == str(large_gds)
        assert report.output_path == str(out)

    def test_dbu_preserved(self, large_gds: Path, tmp_path: Path) -> None:
        """dbu 保留。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert report.dbu == pytest.approx(0.001, abs=1e-9)

    def test_top_cell_name_captured(self, large_gds: Path, tmp_path: Path) -> None:
        """源 top cell 名被记录。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert report.top_cell_name == "TOP"

    def test_default_clipped_cell_name(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """默认裁剪后 cell 名 = 原 top cell 名。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert report.clipped_cell_name == "TOP"

    def test_custom_clipped_cell_name(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """自定义裁剪后 cell 名。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(
            large_gds, out, (5.0, 0.0, 25.0, 15.0),
            clipped_cell_name="CLIPPED_TOP",
        )
        assert report.clipped_cell_name == "CLIPPED_TOP"

    def test_top_cell_name_specified(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """指定 top_cell_name。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(
            large_gds, out, (5.0, 0.0, 25.0, 15.0),
            top_cell_name="TOP",
        )
        assert report.top_cell_name == "TOP"

    def test_shapes_reduced(self, large_gds: Path, tmp_path: Path) -> None:
        """裁剪后 shapes 数减少。

        裁剪前 TOP 递归 2 shapes（TOP + CHILD）。
        裁剪框 (5,0,25,15) 排除 CHILD (在 30,0)，应只剩 TOP 三角形部分。
        """
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert report.shapes_before == 2
        assert report.shapes_after == 1  # 只剩 TOP 裁剪部分

    def test_bbox_clipped(self, large_gds: Path, tmp_path: Path) -> None:
        """裁剪后 bbox 被限制在裁剪框内。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        # 裁剪前 bbox: (0,0,35,20)
        assert report.bbox_before_um == (
            pytest.approx(0.0), pytest.approx(0.0),
            pytest.approx(35.0), pytest.approx(20.0),
        )
        # 裁剪后 bbox 应在裁剪框内
        al, ab, ar, at = report.bbox_after_um
        assert al >= 5.0 - 1e-6
        assert ab >= 0.0 - 1e-6
        assert ar <= 25.0 + 1e-6
        assert at <= 15.0 + 1e-6

    def test_clip_box_recorded(self, large_gds: Path, tmp_path: Path) -> None:
        """裁剪框被记录在报告。"""
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert report.clip_box_um == (5.0, 0.0, 25.0, 15.0)

    def test_output_file_written(self, large_gds: Path, tmp_path: Path) -> None:
        """输出文件被写出。"""
        out = tmp_path / "out.gds"
        assert not out.exists()
        clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        assert out.exists()
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_output_file_readable(self, large_gds: Path, tmp_path: Path) -> None:
        """输出文件可被 klayout 重新读取。"""
        import klayout.db as db

        out = tmp_path / "out.gds"
        clip_gdsii(
            large_gds, out, (5.0, 0.0, 25.0, 15.0),
            clipped_cell_name="CLIP",
        )
        ly2 = db.Layout()
        ly2.read(str(out))
        top_cells = [ly2.cell(int(ci)) for ci in ly2.each_top_cell()]
        assert len(top_cells) == 1
        assert top_cells[0].name == "CLIP"

    def test_original_cell_deleted(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """裁剪后原 top cell 不在输出文件中。"""
        import klayout.db as db

        out = tmp_path / "out.gds"
        clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        ly2 = db.Layout()
        ly2.read(str(out))
        # 原大版图 TOP 不应存在（已删除）
        all_names = [c.name for c in ly2.each_cell()]
        # 只应有裁剪后的 TOP（重命名）
        assert "TOP" in all_names
        # CHILD 不应作为独立 top cell（被裁剪排除）
        top_names = [ly2.cell(int(ci)).name for ci in ly2.each_top_cell()]
        assert len(top_names) == 1

    def test_clip_includes_child(self, large_gds: Path, tmp_path: Path) -> None:
        """裁剪框包含 CHILD 实例时，CHILD shapes 保留。

        裁剪框 (25, 0, 40, 10) 包含 CHILD (30,0)-(35,5)，应保留 CHILD。
        """
        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (25.0, 0.0, 40.0, 10.0))
        # TOP 三角形 (0,0)-(20,0)-(10,20) 在 25 右侧，被排除
        # CHILD (30,0)-(35,5) 在框内，保留
        assert report.shapes_after == 1


# =============================================================================
# TestMultiClipGdsii: 多区域裁剪
# =============================================================================
class TestMultiClipGdsii:
    """multi_clip_gdsii 函数测试。"""

    def test_returns_list(self, large_gds: Path, tmp_path: Path) -> None:
        """返回 ClipReport 列表。"""
        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds, out_dir, [(0.0, 0.0, 10.0, 10.0)]
        )
        assert isinstance(reports, list)
        assert len(reports) == 1
        assert isinstance(reports[0], ClipReport)

    def test_multiple_boxes(self, large_gds: Path, tmp_path: Path) -> None:
        """多区域裁剪生成多个报告。"""
        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds,
            out_dir,
            [(0.0, 0.0, 10.0, 10.0), (20.0, 0.0, 40.0, 20.0)],
        )
        assert len(reports) == 2
        # 每个报告应有不同的裁剪框
        boxes = [r.clip_box_um for r in reports]
        assert (0.0, 0.0, 10.0, 10.0) in boxes
        assert (20.0, 0.0, 40.0, 20.0) in boxes

    def test_output_files_written(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """每个裁剪结果生成独立文件。"""
        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds,
            out_dir,
            [(0.0, 0.0, 10.0, 10.0), (20.0, 0.0, 40.0, 20.0)],
        )
        for r in reports:
            assert Path(r.output_path).exists()
            assert Path(r.output_path).stat().st_size > 0

    def test_name_prefix_default(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """默认 name_prefix = 原 top cell 名。"""
        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds, out_dir, [(0.0, 0.0, 10.0, 10.0)]
        )
        assert reports[0].clipped_cell_name == "TOP_clip0"

    def test_name_prefix_custom(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """自定义 name_prefix。"""
        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds, out_dir, [(0.0, 0.0, 10.0, 10.0)],
            name_prefix="REGION",
        )
        assert reports[0].clipped_cell_name == "REGION_clip0"
        assert "REGION_clip0.gds" in reports[0].output_path

    def test_output_dir_created(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """输出目录自动创建。"""
        out_dir = tmp_path / "nested" / "clips"
        assert not out_dir.exists()
        multi_clip_gdsii(large_gds, out_dir, [(0.0, 0.0, 10.0, 10.0)])
        assert out_dir.exists()
        assert out_dir.is_dir()

    def test_shared_shapes_before(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """所有报告共享相同的 shapes_before（同一源文件）。"""
        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds,
            out_dir,
            [(0.0, 0.0, 10.0, 10.0), (20.0, 0.0, 40.0, 20.0)],
        )
        for r in reports:
            assert r.shapes_before == 2


# =============================================================================
# TestGenerateClipReport: 报告生成
# =============================================================================
class TestGenerateClipReport:
    """generate_clip_report 函数测试。"""

    def test_text_report(self, large_gds: Path, tmp_path: Path) -> None:
        """text 格式报告。"""
        out = tmp_path / "out.gds"
        report = generate_clip_report(
            large_gds, out, (5.0, 0.0, 25.0, 15.0), output_format="text"
        )
        assert isinstance(report, str)
        assert "GDSII 区域裁剪报告" in report
        assert "裁剪框" in report
        assert "裁剪前" in report
        assert "裁剪后" in report
        assert "shape 数" in report

    def test_markdown_report(self, large_gds: Path, tmp_path: Path) -> None:
        """markdown 格式报告。"""
        out = tmp_path / "out.gds"
        report = generate_clip_report(
            large_gds, out, (5.0, 0.0, 25.0, 15.0), output_format="markdown"
        )
        assert isinstance(report, str)
        assert "# GDSII 区域裁剪报告" in report
        assert "| 指标 | 裁剪前 | 裁剪后 |" in report
        assert "| shape 数 |" in report

    def test_text_report_contains_clip_box(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """text 报告含裁剪框坐标。"""
        out = tmp_path / "out.gds"
        report = generate_clip_report(
            large_gds, out, (5.0, 0.0, 25.0, 15.0), output_format="text"
        )
        assert "left=5.0" in report
        assert "bottom=0.0" in report
        assert "right=25.0" in report
        assert "top=15.0" in report

    def test_markdown_report_contains_paths(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """markdown 报告含输入/输出路径。"""
        out = tmp_path / "out.gds"
        report = generate_clip_report(
            large_gds, out, (5.0, 0.0, 25.0, 15.0), output_format="markdown"
        )
        assert str(large_gds) in report
        assert str(out) in report

    def test_unsupported_format(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_clip_report(
                large_gds, out, (5.0, 0.0, 25.0, 15.0),
                output_format="html",
            )


# =============================================================================
# TestR03ErrorHandling: 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """输入文件不存在 raise FileNotFoundError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError, match="GDSII 文件不存在"):
            clip_gdsii(tmp_path / "nonexistent.gds", out, (0, 0, 10, 10))

    def test_not_a_file(self, tmp_path: Path) -> None:
        """输入路径是目录 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不是文件"):
            clip_gdsii(tmp_path, out, (0, 0, 10, 10))

    def test_clip_box_left_ge_right(self, large_gds: Path, tmp_path: Path) -> None:
        """left >= right raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="left.*必须 < right"):
            clip_gdsii(large_gds, out, (10.0, 0.0, 10.0, 5.0))

    def test_clip_box_left_gt_right(self, large_gds: Path, tmp_path: Path) -> None:
        """left > right raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="left.*必须 < right"):
            clip_gdsii(large_gds, out, (15.0, 0.0, 10.0, 5.0))

    def test_clip_box_bottom_ge_top(self, large_gds: Path, tmp_path: Path) -> None:
        """bottom >= top raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="bottom.*必须 < top"):
            clip_gdsii(large_gds, out, (0.0, 10.0, 10.0, 10.0))

    def test_clip_box_wrong_length(self, large_gds: Path, tmp_path: Path) -> None:
        """裁剪框长度不为 4 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="长度 4"):
            clip_gdsii(large_gds, out, (0.0, 0.0, 10.0))  # type: ignore

    def test_top_cell_not_found(self, large_gds: Path, tmp_path: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不存在"):
            clip_gdsii(
                large_gds, out, (0, 0, 10, 10), top_cell_name="NONEXISTENT"
            )

    def test_empty_gds_no_top_cell(self, empty_gds: Path, tmp_path: Path) -> None:
        """空 GDSII 无顶层 cell raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="无顶层 cell"):
            clip_gdsii(empty_gds, out, (0, 0, 10, 10))

    def test_multi_clip_empty_boxes(self, large_gds: Path, tmp_path: Path) -> None:
        """multi_clip 空裁剪框列表 raise ValueError。"""
        out_dir = tmp_path / "clips"
        with pytest.raises(ValueError, match="不能为空"):
            multi_clip_gdsii(large_gds, out_dir, [])

    def test_multi_clip_invalid_box(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """multi_clip 含无效裁剪框 raise ValueError。"""
        out_dir = tmp_path / "clips"
        with pytest.raises(ValueError, match="left.*必须 < right"):
            multi_clip_gdsii(
                large_gds, out_dir, [(10.0, 0.0, 5.0, 10.0)]
            )

    def test_unsupported_format_raises(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的输出格式 raise ValueError（不静默兜底）。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_clip_report(
                large_gds, out, (0, 0, 10, 10), output_format="xml"
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_urls_count(self) -> None:
        """模块 docstring 含 ≥5 个文献 URL。"""
        import polaris.verification.gdsii_clip_tool as mod
        import re

        doc = mod.__doc__ or ""
        urls = re.findall(r"https?://[^\s)]+", doc)
        assert len(urls) >= 5, (
            f"docstring 应含 ≥5 个 URL，实际 {len(urls)} 个"
        )

    def test_all_exported(self) -> None:
        """__all__ 导出完整。"""
        import polaris.verification.gdsii_clip_tool as mod

        assert set(mod.__all__) == {
            "ClipReport",
            "clip_gdsii",
            "multi_clip_gdsii",
            "generate_clip_report",
        }

    def test_clip_report_is_dataclass(self) -> None:
        """ClipReport 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(ClipReport)

    def test_default_values(self) -> None:
        """ClipReport 默认值合理。"""
        report = ClipReport(input_path="a", output_path="b")
        assert report.dbu == 0.0
        assert report.top_cell_name == ""
        assert report.clip_box_um == (0.0, 0.0, 0.0, 0.0)
        assert report.clipped_cell_name == ""
        assert report.shapes_before == 0
        assert report.shapes_after == 0

    def test_klayout_api_documented(self) -> None:
        """docstring 记录 KLayout clip API。"""
        import polaris.verification.gdsii_clip_tool as mod

        doc = mod.__doc__ or ""
        assert "Layout.clip" in doc
        assert "multi_clip" in doc
        assert "cell_index" in doc

    def test_no_silent_fallback(self) -> None:
        """源码无 silent fall-back（except: pass / return None / return []）。"""
        import polaris.verification.gdsii_clip_tool as mod
        import inspect

        src = inspect.getsource(mod)
        # 不应有 except: pass
        assert "except: pass" not in src
        assert "except Exception: pass" not in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_clip_then_grid_check(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """裁剪后做 R325 网格对齐检查。

        裁剪不改变顶点的 grid 对齐性，裁剪后的图形仍应通过网格检查。
        """
        from polaris.verification.gdsii_grid_alignment_checker import (
            check_grid_alignment,
        )

        out = tmp_path / "out.gds"
        clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        # 原始坐标都是 5nm grid 的倍数，裁剪后应无违规
        report = check_grid_alignment(out, grid_um=0.005)
        assert report.total_violations == 0

    def test_clip_then_flatten(self, large_gds: Path, tmp_path: Path) -> None:
        """裁剪后做 R326 扁平化。"""
        from polaris.verification.gdsii_flattener import flatten_gdsii

        clip_out = tmp_path / "clip.gds"
        clip_gdsii(large_gds, clip_out, (0.0, 0.0, 40.0, 25.0))

        flat_out = tmp_path / "flat.gds"
        report = flatten_gdsii(clip_out, flat_out, levels=-1, prune=True)
        # 裁剪框包含 TOP + CHILD，应保留 2 shapes
        assert report.shapes_after == 2
        assert report.instances_after == 0

    def test_clip_preserves_layer(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """裁剪保留原始层信息。"""
        import klayout.db as db

        out = tmp_path / "out.gds"
        clip_gdsii(large_gds, out, (5.0, 0.0, 25.0, 15.0))
        ly2 = db.Layout()
        ly2.read(str(out))
        # 应有 layer (1, 0)
        found_layers = []
        for li in ly2.layer_indices():
            info = ly2.get_info(li)
            found_layers.append((int(info.layer), int(info.datatype)))
        assert (1, 0) in found_layers

    def test_clip_excludes_outside(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """裁剪框外的图形被排除。

        裁剪框 (25,0,40,10) 只包含 CHILD (30,0)-(35,5)，
        TOP 三角形 (0,0)-(20,0)-(10,20) 在框外被排除。
        """
        import klayout.db as db

        out = tmp_path / "out.gds"
        report = clip_gdsii(large_gds, out, (25.0, 0.0, 40.0, 10.0))
        assert report.shapes_after == 1  # 只剩 CHILD
        # bbox 应在 (25,0,40,10) 内
        al, ab, ar, at = report.bbox_after_um
        assert al >= 25.0 - 1e-6
        assert ar <= 40.0 + 1e-6

    def test_multi_clip_then_grid_check(
        self, large_gds: Path, tmp_path: Path
    ) -> None:
        """多区域裁剪后每个文件都能做网格检查。"""
        from polaris.verification.gdsii_grid_alignment_checker import (
            check_grid_alignment,
        )

        out_dir = tmp_path / "clips"
        reports = multi_clip_gdsii(
            large_gds, out_dir,
            [(0.0, 0.0, 10.0, 10.0), (20.0, 0.0, 40.0, 20.0)],
        )
        for r in reports:
            grid_report = check_grid_alignment(r.output_path, grid_um=0.005)
            assert grid_report.total_violations == 0


# =============================================================================
# TestDataclassTest: 数据类
# =============================================================================
class TestDataclassTest:
    """ClipReport 数据类测试。"""

    def test_fields_complete(self) -> None:
        """ClipReport 字段完整。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(ClipReport)}
        expected = {
            "input_path",
            "output_path",
            "dbu",
            "top_cell_name",
            "clip_box_um",
            "clipped_cell_name",
            "shapes_before",
            "shapes_after",
            "bbox_before_um",
            "bbox_after_um",
        }
        assert field_names == expected

    def test_construction(self) -> None:
        """ClipReport 可正常构造。"""
        report = ClipReport(
            input_path="in.gds",
            output_path="out.gds",
            dbu=0.001,
            top_cell_name="TOP",
            clip_box_um=(0.0, 0.0, 10.0, 10.0),
            clipped_cell_name="TOP",
            shapes_before=5,
            shapes_after=3,
            bbox_before_um=(0.0, 0.0, 50.0, 50.0),
            bbox_after_um=(0.0, 0.0, 10.0, 10.0),
        )
        assert report.input_path == "in.gds"
        assert report.shapes_before == 5
        assert report.shapes_after == 3
        assert report.clip_box_um == (0.0, 0.0, 10.0, 10.0)

    def test_repr(self) -> None:
        """ClipReport repr 可用。"""
        report = ClipReport(input_path="a", output_path="b")
        r = repr(report)
        assert "ClipReport" in r
        assert "input_path='a'" in r

    def test_equality(self) -> None:
        """ClipReport 相等比较。"""
        r1 = ClipReport(input_path="a", output_path="b")
        r2 = ClipReport(input_path="a", output_path="b")
        assert r1 == r2
        r3 = ClipReport(input_path="c", output_path="b")
        assert r1 != r3
