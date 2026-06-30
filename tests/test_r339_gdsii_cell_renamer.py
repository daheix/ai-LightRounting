"""R339 GDSII 器件重命名工具测试。

覆盖:
- rename_cells: 基本重命名、链式重命名、实例引用更新、持久化
- generate_rename_report: text/markdown/json 报告
- _detect_cycle: 循环检测
- _topological_sort_renames: 拓扑排序
- R03 错误处理（禁止 fall-back）
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Layout.rename_cell:
  https://www.klayout.org/doc-qt5/code/class_Layout.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_cell_renamer import (
    RenameRecord,
    RenameReport,
    rename_cells,
    generate_rename_report,
    _detect_cycle,
    _topological_sort_renames,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_simple_rename_gds(path: Path) -> Path:
    """创建简单 GDSII（TOP + CHILD_A + CHILD_B，含实例引用）。

    结构:
    - TOP cell
      - CHILD_A @ (10, 20) μm
      - CHILD_B @ (30, 40) μm
    - CHILD_A cell (polygon)
    - CHILD_B cell (polygon)
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    child_a = ly.create_cell("CHILD_A")
    pts_a = [db.Point(0, 0), db.Point(2000, 0),
             db.Point(2000, 1000), db.Point(0, 1000)]
    child_a.shapes(li).insert(db.Polygon(pts_a))

    child_b = ly.create_cell("CHILD_B")
    pts_b = [db.Point(0, 0), db.Point(1500, 0),
             db.Point(1500, 800), db.Point(0, 800)]
    child_b.shapes(li).insert(db.Polygon(pts_b))

    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(10000, 20000))
    ))
    top.insert(db.CellInstArray(
        child_b.cell_index(), db.Trans(db.Point(30000, 40000))
    ))

    ly.write(str(path))
    return path


def _make_multi_cell_gds(path: Path) -> Path:
    """创建多 cell GDSII（5 个 cell + 顶层）。

    结构:
    - TOP cell
      - DEV1 @ (0, 0)
      - DEV2 @ (10, 0)
      - DEV3 @ (20, 0)
    - DEV1, DEV2, DEV3, DEV4, DEV5 cell
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    cells = {}
    for name in ["DEV1", "DEV2", "DEV3", "DEV4", "DEV5"]:
        cell = ly.create_cell(name)
        pts = [db.Point(0, 0), db.Point(1000, 0),
               db.Point(1000, 500), db.Point(0, 500)]
        cell.shapes(li).insert(db.Polygon(pts))
        cells[name] = cell

    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(
        cells["DEV1"].cell_index(), db.Trans(db.Point(0, 0))
    ))
    top.insert(db.CellInstArray(
        cells["DEV2"].cell_index(), db.Trans(db.Point(10000, 0))
    ))
    top.insert(db.CellInstArray(
        cells["DEV3"].cell_index(), db.Trans(db.Point(20000, 0))
    ))

    ly.write(str(path))
    return path


@pytest.fixture
def simple_rename_gds(tmp_path: Path) -> Path:
    """简单重命名 GDSII 文件。"""
    return _make_simple_rename_gds(tmp_path / "simple.gds")


@pytest.fixture
def multi_cell_gds(tmp_path: Path) -> Path:
    """多 cell GDSII 文件。"""
    return _make_multi_cell_gds(tmp_path / "multi.gds")


# =============================================================================
# TestRenameCells: 基本重命名
# =============================================================================
class TestRenameCells:
    """rename_cells 函数测试。"""

    def test_returns_report(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """返回 RenameReport。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert isinstance(report, RenameReport)

    def test_input_path(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """input_path 正确。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert report.input_path == str(simple_rename_gds)

    def test_output_path(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """output_path 正确。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert report.output_path == str(out)

    def test_dbu(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """dbu 正确。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_renames_requested(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """renames_requested 保存用户请求。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert report.renames_requested == {"CHILD_A": "CHILD_C"}

    def test_total_renamed(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """total_renamed 正确。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert report.total_renamed == 1

    def test_renames_applied(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """renames_applied 含 RenameRecord。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert len(report.renames_applied) == 1
        rec = report.renames_applied[0]
        assert rec.old_name == "CHILD_A"
        assert rec.new_name == "CHILD_C"

    def test_original_cell_names(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """original_cell_names 含旧名。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert "CHILD_A" in report.original_cell_names
        assert "CHILD_B" in report.original_cell_names
        assert "TOP" in report.original_cell_names

    def test_final_cell_names_has_new(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """final_cell_names 含新名。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert "CHILD_C" in report.final_cell_names

    def test_final_cell_names_no_old(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """final_cell_names 不含旧名。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert "CHILD_A" not in report.final_cell_names

    def test_cell_count_preserved(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """重命名不改变 cell 总数。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert len(report.original_cell_names) == len(report.final_cell_names)

    def test_output_file_exists(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """输出文件被创建。"""
        out = tmp_path / "out.gds"
        rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})
        assert out.exists()

    def test_same_name_skipped(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """old_name == new_name 跳过。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_A"})
        assert report.total_renamed == 0
        assert "CHILD_A" in report.final_cell_names

    def test_multiple_renames(self, multi_cell_gds: Path, tmp_path: Path) -> None:
        """多个重命名同时执行。"""
        out = tmp_path / "out.gds"
        report = rename_cells(multi_cell_gds, out, {
            "DEV1": "MMI1",
            "DEV2": "MMI2",
            "DEV3": "MMI3",
        })
        assert report.total_renamed == 3
        assert "MMI1" in report.final_cell_names
        assert "MMI2" in report.final_cell_names
        assert "MMI3" in report.final_cell_names
        assert "DEV1" not in report.final_cell_names

    def test_instance_reference_updated(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """实例引用自动更新（重新读取验证）。"""
        out = tmp_path / "out.gds"
        rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})

        # 重新读取输出文件，验证实例引用新名
        ly2 = db.Layout()
        ly2.read(str(out))
        top = ly2.cell("TOP")
        assert top is not None
        inst_cell_names = {inst.cell.name for inst in top.each_inst()}
        assert "CHILD_C" in inst_cell_names
        assert "CHILD_A" not in inst_cell_names

    def test_chain_rename_no_conflict(self, tmp_path: Path) -> None:
        """链式重命名 A→B, B→C（C 不存在）。"""
        # 创建只有 A 和 B 的 GDSII
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        for name in ["A", "B"]:
            cell = ly.create_cell(name)
            pts = [db.Point(0, 0), db.Point(1000, 0),
                   db.Point(1000, 500), db.Point(0, 500)]
            cell.shapes(li).insert(db.Polygon(pts))
        in_path = tmp_path / "chain2.gds"
        ly.write(str(in_path))

        out = tmp_path / "out.gds"
        report = rename_cells(in_path, out, {"A": "B", "B": "C"})
        # 拓扑顺序: 先 B→C，再 A→B
        assert report.total_renamed == 2
        assert "B" in report.final_cell_names  # 原 A 改名而来
        assert "C" in report.final_cell_names  # 原 B 改名而来
        assert "A" not in report.final_cell_names


# =============================================================================
# TestGenerateRenameReport: 报告生成
# =============================================================================
class TestGenerateRenameReport:
    """generate_rename_report 函数测试。"""

    def test_text_report(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """text 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_rename_report(
            simple_rename_gds, out, {"CHILD_A": "CHILD_C"},
            output_format="text"
        )
        assert isinstance(result, str)
        assert "GDSII 器件重命名报告" in result
        assert "CHILD_A" in result
        assert "CHILD_C" in result

    def test_markdown_report(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """markdown 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_rename_report(
            simple_rename_gds, out, {"CHILD_A": "CHILD_C"},
            output_format="markdown"
        )
        assert isinstance(result, str)
        assert "# GDSII 器件重命名报告" in result
        assert "| CHILD_A | CHILD_C |" in result

    def test_json_report(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """json 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_rename_report(
            simple_rename_gds, out, {"CHILD_A": "CHILD_C"},
            output_format="json"
        )
        data = json.loads(result)
        assert data["input_path"] == str(simple_rename_gds)
        assert data["output_path"] == str(out)
        assert data["total_renamed"] == 1
        assert data["renames_applied"][0]["old_name"] == "CHILD_A"
        assert data["renames_applied"][0]["new_name"] == "CHILD_C"

    def test_unsupported_format_raises(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """不支持的格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_rename_report(
                simple_rename_gds, out, {"CHILD_A": "CHILD_C"},
                output_format="xml"
            )


# =============================================================================
# TestDetectCycle: 循环检测
# =============================================================================
class TestDetectCycle:
    """_detect_cycle 内部函数测试。"""

    def test_no_cycle(self) -> None:
        """无循环返回 None。"""
        rename_map = {"A": "B", "C": "D"}
        assert _detect_cycle(rename_map) is None

    def test_simple_cycle(self) -> None:
        """简单循环 A→B, B→A。"""
        rename_map = {"A": "B", "B": "A"}
        cycle = _detect_cycle(rename_map)
        assert cycle is not None
        assert len(cycle) >= 3  # [A, B, A] 或 [B, A, B]
        assert cycle[0] == cycle[-1]  # 首尾相同

    def test_self_cycle(self) -> None:
        """自循环 A→A。"""
        # 但源代码 cycle_check_map 过滤了 old == new，所以这里测纯函数
        rename_map = {"A": "A"}
        cycle = _detect_cycle(rename_map)
        # A→A 是自循环
        assert cycle is not None

    def test_long_chain_no_cycle(self) -> None:
        """长链无循环。"""
        rename_map = {"A": "B", "B": "C", "C": "D"}
        assert _detect_cycle(rename_map) is None

    def test_long_cycle(self) -> None:
        """长循环 A→B→C→A。"""
        rename_map = {"A": "B", "B": "C", "C": "A"}
        cycle = _detect_cycle(rename_map)
        assert cycle is not None
        assert cycle[0] == cycle[-1]

    def test_empty_map(self) -> None:
        """空映射无循环。"""
        assert _detect_cycle({}) is None


# =============================================================================
# TestTopologicalSort: 拓扑排序
# =============================================================================
class TestTopologicalSort:
    """_topological_sort_renames 内部函数测试。"""

    def test_no_deps(self) -> None:
        """无依赖的拓扑排序。"""
        rename_map = {"A": "X", "B": "Y"}
        result = _topological_sort_renames(rename_map)
        assert set(result) == {"A", "B"}
        assert len(result) == 2

    def test_chain_order(self) -> None:
        """链式重命名顺序 A→B, B→C: 先 B 后 A。"""
        rename_map = {"A": "B", "B": "C"}
        result = _topological_sort_renames(rename_map)
        # B 必须在 A 之前
        assert result.index("B") < result.index("A")

    def test_long_chain_order(self) -> None:
        """长链 A→B, B→C, C→D: 顺序 C, B, A。"""
        rename_map = {"A": "B", "B": "C", "C": "D"}
        result = _topological_sort_renames(rename_map)
        assert result.index("C") < result.index("B")
        assert result.index("B") < result.index("A")

    def test_cycle_raises(self) -> None:
        """循环依赖 raise ValueError。"""
        rename_map = {"A": "B", "B": "A"}
        with pytest.raises(ValueError, match="循环依赖"):
            _topological_sort_renames(rename_map)


# =============================================================================
# TestR03ErrorHandling: 错误处理（禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError, match="不存在"):
            rename_cells(tmp_path / "nonexistent.gds", out, {"A": "B"})

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径不是文件 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不是文件"):
            rename_cells(tmp_path, out, {"A": "B"})

    def test_empty_rename_map(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """空 rename_map raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="rename_map 不能为空"):
            rename_cells(simple_rename_gds, out, {})

    def test_old_name_not_exist(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """old_name 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不存在"):
            rename_cells(simple_rename_gds, out, {"NONEXISTENT": "X"})

    def test_new_name_conflict(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """new_name 与现有 cell 冲突 raise ValueError。"""
        out = tmp_path / "out.gds"
        # CHILD_B 已存在且不被重命名
        with pytest.raises(ValueError, match="冲突"):
            rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_B"})

    def test_cycle_rename_raises(self, tmp_path: Path) -> None:
        """循环重命名 A→B, B→A raise ValueError。"""
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        for name in ["A", "B"]:
            cell = ly.create_cell(name)
            pts = [db.Point(0, 0), db.Point(1000, 0),
                   db.Point(1000, 500), db.Point(0, 500)]
            cell.shapes(li).insert(db.Polygon(pts))
        in_path = tmp_path / "cycle.gds"
        ly.write(str(in_path))

        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="循环重命名"):
            rename_cells(in_path, out, {"A": "B", "B": "A"})

    def test_empty_key_raises(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """空字符串 key raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="非空字符串"):
            rename_cells(simple_rename_gds, out, {"": "X"})

    def test_empty_value_raises(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """空字符串 value raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="非空字符串"):
            rename_cells(simple_rename_gds, out, {"CHILD_A": ""})


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_urls(self) -> None:
        """模块 docstring 含 5+ URL。"""
        from polaris.verification import gdsii_cell_renamer
        doc = gdsii_cell_renamer.__doc__ or ""
        url_count = doc.count("https://")
        assert url_count >= 5, f"模块 docstring 只有 {url_count} 个 URL，要求 ≥5"

    def test_module_docstring_has_klayout_url(self) -> None:
        """模块 docstring 含 KLayout URL。"""
        from polaris.verification import gdsii_cell_renamer
        doc = gdsii_cell_renamer.__doc__ or ""
        assert "klayout.org" in doc

    def test_module_docstring_has_api_facts(self) -> None:
        """模块 docstring 含 KLayout API 关键事实。"""
        from polaris.verification import gdsii_cell_renamer
        doc = gdsii_cell_renamer.__doc__ or ""
        assert "rename_cell" in doc
        assert "cell_index" in doc

    def test_rename_cells_docstring_has_source(self) -> None:
        """rename_cells docstring 含来源 URL。"""
        assert "klayout.org" in rename_cells.__doc__

    def test_no_fall_back_in_source(self) -> None:
        """源代码无 fall-back 模式（except: pass 等）。"""
        src_path = Path(__file__).parent.parent / "src" / "polaris" / "verification" / "gdsii_cell_renamer.py"
        src = src_path.read_text(encoding="utf-8")
        # 禁止 except: pass
        assert "except: pass" not in src
        assert "except Exception: pass" not in src
        # 禁止 return None 作为兜底（raise 是允许的）
        # 注意：内部函数 _detect_cycle 返回 None 是合法的（无循环的语义）
        # 这里只检查 except: pass 模式

    def test_raise_in_error_paths(self) -> None:
        """错误路径用 raise 而非 return None。"""
        src_path = Path(__file__).parent.parent / "src" / "polaris" / "verification" / "gdsii_cell_renamer.py"
        src = src_path.read_text(encoding="utf-8")
        assert "raise FileNotFoundError" in src
        assert "raise ValueError" in src
        assert "raise RuntimeError" in src

    def test_module_docstring_has_compliance(self) -> None:
        """模块 docstring 含合规声明。"""
        from polaris.verification import gdsii_cell_renamer
        doc = gdsii_cell_renamer.__doc__ or ""
        assert "R01" in doc
        assert "R03" in doc

    def test_internal_funcs_have_docstring(self) -> None:
        """内部函数有 docstring。"""
        assert _detect_cycle.__doc__ is not None
        assert "检测" in _detect_cycle.__doc__
        assert _topological_sort_renames.__doc__ is not None
        assert "拓扑排序" in _topological_sort_renames.__doc__


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_workflow_rename_and_verify(self, simple_rename_gds: Path, tmp_path: Path) -> None:
        """完整流程: 重命名 → 重新读取 → 验证 cell 名和实例引用。"""
        out = tmp_path / "out.gds"
        report = rename_cells(simple_rename_gds, out, {"CHILD_A": "CHILD_C"})

        # 重新读取
        ly = db.Layout()
        ly.read(str(out))

        # 验证新名存在
        assert ly.cell("CHILD_C") is not None
        # 验证旧名不存在
        assert ly.cell("CHILD_A") is None
        # 验证 CHILD_B 仍在
        assert ly.cell("CHILD_B") is not None
        # 验证 TOP 仍在
        assert ly.cell("TOP") is not None

        # 验证实例引用更新
        top = ly.cell("TOP")
        inst_names = {inst.cell.name for inst in top.each_inst()}
        assert "CHILD_C" in inst_names
        assert "CHILD_B" in inst_names
        assert "CHILD_A" not in inst_names

    def test_multiple_renames_with_instances(self, multi_cell_gds: Path, tmp_path: Path) -> None:
        """多 cell 重命名 + 实例引用更新。"""
        out = tmp_path / "out.gds"
        rename_cells(multi_cell_gds, out, {
            "DEV1": "MMI1",
            "DEV2": "MMI2",
        })

        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        inst_names = {inst.cell.name for inst in top.each_inst()}
        assert "MMI1" in inst_names
        assert "MMI2" in inst_names
        assert "DEV3" in inst_names  # 未重命名

    def test_chain_rename_persisted(self, tmp_path: Path) -> None:
        """链式重命名持久化到文件。"""
        # 创建 A, B 两个 cell
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        for name in ["A", "B"]:
            cell = ly.create_cell(name)
            pts = [db.Point(0, 0), db.Point(1000, 0),
                   db.Point(1000, 500), db.Point(0, 500)]
            cell.shapes(li).insert(db.Polygon(pts))
        in_path = tmp_path / "in.gds"
        ly.write(str(in_path))

        out = tmp_path / "out.gds"
        rename_cells(in_path, out, {"A": "B", "B": "C"})

        ly2 = db.Layout()
        ly2.read(str(out))
        # 最终: B (原 A) 和 C (原 B)
        assert ly2.cell("B") is not None
        assert ly2.cell("C") is not None
        assert ly2.cell("A") is None


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_rename_record_creation(self) -> None:
        """RenameRecord 创建。"""
        rec = RenameRecord(old_name="A", new_name="B")
        assert rec.old_name == "A"
        assert rec.new_name == "B"

    def test_rename_report_defaults(self) -> None:
        """RenameReport 默认值。"""
        report = RenameReport()
        assert report.input_path == ""
        assert report.output_path == ""
        assert report.renames_requested == {}
        assert report.renames_applied == []
        assert report.total_renamed == 0
        assert report.original_cell_names == []
        assert report.final_cell_names == []
        assert report.dbu == 0.0

    def test_rename_report_with_values(self) -> None:
        """RenameReport 赋值。"""
        report = RenameReport(
            input_path="/in.gds",
            output_path="/out.gds",
            renames_requested={"A": "B"},
            renames_applied=[RenameRecord("A", "B")],
            total_renamed=1,
            original_cell_names=["A", "TOP"],
            final_cell_names=["B", "TOP"],
            dbu=0.001,
        )
        assert report.input_path == "/in.gds"
        assert report.total_renamed == 1
        assert report.renames_applied[0].old_name == "A"
        assert report.dbu == 0.001

    def test_rename_record_is_dataclass(self) -> None:
        """RenameRecord 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(RenameRecord)

    def test_rename_report_is_dataclass(self) -> None:
        """RenameReport 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(RenameReport)

    def test_rename_report_mutable_list(self) -> None:
        """RenameReport 列表字段可变（default_factory）。"""
        report1 = RenameReport()
        report2 = RenameReport()
        report1.original_cell_names.append("A")
        assert report2.original_cell_names == []  # 独立实例

    def test_rename_report_mutable_dict(self) -> None:
        """RenameReport 字典字段可变（default_factory）。"""
        report1 = RenameReport()
        report2 = RenameReport()
        report1.renames_requested["A"] = "B"
        assert report2.renames_requested == {}  # 独立实例
