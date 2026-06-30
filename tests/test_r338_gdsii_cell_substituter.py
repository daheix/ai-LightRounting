"""R338 GDSII 器件替换工具测试。

覆盖:
- substitute_cell_instances: 普通实例/数组实例/多 cell/指定 top_cell_name
- generate_substitute_report: text/markdown/json 报告
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Instance: https://www.klayout.org/doc-qt5/code/class_Instance.html
- KLayout CellInstArray:
  https://www.klayout.org/doc-qt5/code/class_CellInstArray.html
"""
from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_cell_substituter import (
    SubstituteReport,
    SubstitutionRecord,
    generate_substitute_report,
    substitute_cell_instances,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_simple_subst_gds(path: Path) -> Path:
    """创建简单替换 GDSII（TOP 含 CHILD_A × 2 实例 + CHILD_B cell 已存在）。

    结构:
    - TOP cell
      - CHILD_A @ (0, 0) μm, r0
      - CHILD_A @ (20, 0) μm, r0
    - CHILD_A cell (polygon)
    - CHILD_B cell (polygon)
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    child_a = ly.create_cell("CHILD_A")
    pts_a = [db.Point(0, 0), db.Point(10000, 0),
             db.Point(10000, 5000), db.Point(0, 5000)]
    child_a.shapes(li).insert(db.Polygon(pts_a))

    child_b = ly.create_cell("CHILD_B")
    pts_b = [db.Point(0, 0), db.Point(20000, 0),
             db.Point(20000, 10000), db.Point(0, 10000)]
    child_b.shapes(li).insert(db.Polygon(pts_b))

    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(0, 0))
    ))
    top.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(20000, 0))
    ))
    ly.write(str(path))
    return path


def _make_array_subst_gds(path: Path) -> Path:
    """创建含数组实例的 GDSII。

    结构:
    - TOP cell
      - CHILD_A @ (0, 0) μm 普通实例
      - CHILD_A @ (100, 0) μm 数组实例 2×3 (间距 20, 30) μm
    - CHILD_A cell
    - CHILD_B cell
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    child_a = ly.create_cell("CHILD_A")
    pts_a = [db.Point(0, 0), db.Point(10000, 0),
             db.Point(10000, 5000), db.Point(0, 5000)]
    child_a.shapes(li).insert(db.Polygon(pts_a))

    child_b = ly.create_cell("CHILD_B")
    pts_b = [db.Point(0, 0), db.Point(20000, 0),
             db.Point(20000, 10000), db.Point(0, 10000)]
    child_b.shapes(li).insert(db.Polygon(pts_b))

    top = ly.create_cell("TOP")
    # 普通实例
    top.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(0, 0))
    ))
    # 数组实例: 2×3
    top.insert(db.CellInstArray(
        child_a.cell_index(),
        db.Trans(db.Point(100000, 0)),
        db.Vector(20000, 0),
        db.Vector(0, 30000),
        2, 3,
    ))
    ly.write(str(path))
    return path


def _make_multi_cell_subst_gds(path: Path) -> Path:
    """创建多 cell 嵌套 GDSII。

    结构:
    - TOP cell
      - CHILD_A @ (0, 0) μm
      - CHILD_B @ (50, 0) μm (CHILD_B 内含 CHILD_A 实例)
    - CHILD_A cell
    - CHILD_B cell
      - CHILD_A @ (5, 5) μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    child_a = ly.create_cell("CHILD_A")
    pts_a = [db.Point(0, 0), db.Point(10000, 0),
             db.Point(10000, 5000), db.Point(0, 5000)]
    child_a.shapes(li).insert(db.Polygon(pts_a))

    child_b = ly.create_cell("CHILD_B")
    pts_b = [db.Point(0, 0), db.Point(20000, 0),
             db.Point(20000, 10000), db.Point(0, 10000)]
    child_b.shapes(li).insert(db.Polygon(pts_b))
    child_b.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(5000, 5000))
    ))

    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(0, 0))
    ))
    top.insert(db.CellInstArray(
        child_b.cell_index(), db.Trans(db.Point(50000, 0))
    ))
    ly.write(str(path))
    return path


@pytest.fixture
def simple_subst_gds(tmp_path: Path) -> Path:
    """简单替换 GDSII。"""
    return _make_simple_subst_gds(tmp_path / "simple.gds")


@pytest.fixture
def array_subst_gds(tmp_path: Path) -> Path:
    """含数组实例的 GDSII。"""
    return _make_array_subst_gds(tmp_path / "array.gds")


@pytest.fixture
def multi_cell_subst_gds(tmp_path: Path) -> Path:
    """多 cell 嵌套 GDSII。"""
    return _make_multi_cell_subst_gds(tmp_path / "multi.gds")


def _count_instances_by_name(gds_path: Path, parent_cell_name: str) -> dict[str, int]:
    """统计指定 parent cell 中各引用 cell 名的实例数。"""
    ly = db.Layout()
    ly.read(str(gds_path))
    parent = ly.cell(parent_cell_name)
    if parent is None:
        return {}
    counts: dict[str, int] = {}
    for inst in parent.each_inst():
        name = inst.cell.name
        counts[name] = counts.get(name, 0) + 1
    return counts


# =============================================================================
# TestSubstituteCellInstances
# =============================================================================
class TestSubstituteCellInstances:
    """substitute_cell_instances 函数测试。"""

    def test_basic_substitution(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """基本替换：CHILD_A → CHILD_B。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        assert report.total_instances_replaced == 2
        assert "TOP" in report.cells_affected
        # 验证输出文件
        counts = _count_instances_by_name(out, "TOP")
        assert counts.get("CHILD_A", 0) == 0
        assert counts.get("CHILD_B", 0) == 2

    def test_no_match_substitution(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """替换不存在的 cell：无实例被替换。"""
        out = tmp_path / "out.gds"
        # CHILD_B 在文件中存在但 TOP 没引用它
        report = substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_B": "CHILD_A"}
        )
        assert report.total_instances_replaced == 0
        assert report.cells_affected == []
        # 文件结构不变
        counts = _count_instances_by_name(out, "TOP")
        assert counts.get("CHILD_A", 0) == 2

    def test_array_substitution(
        self, array_subst_gds: Path, tmp_path: Path
    ) -> None:
        """数组实例替换：保留数组属性。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            array_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        # 1 普通 + 1 数组 = 2 个实例被替换
        assert report.total_instances_replaced == 2
        # 验证数组实例保留
        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        array_count = 0
        child_b_count = 0
        for inst in top.each_inst():
            if inst.cell.name == "CHILD_B":
                child_b_count += 1
                if inst.is_regular_array():
                    array_count += 1
                    # 验证数组维度
                    assert int(inst.na) >= 1
                    assert int(inst.nb) >= 1
        assert child_b_count == 2
        assert array_count == 1

    def test_multi_cell_substitution(
        self, multi_cell_subst_gds: Path, tmp_path: Path
    ) -> None:
        """多 cell 替换：TOP 和 CHILD_B 都有 CHILD_A 实例。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            multi_cell_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        # TOP 中 1 个 CHILD_A + CHILD_B 中 1 个 CHILD_A = 2
        assert report.total_instances_replaced == 2
        assert "TOP" in report.cells_affected
        assert "CHILD_B" in report.cells_affected

    def test_top_cell_name_restriction(
        self, multi_cell_subst_gds: Path, tmp_path: Path
    ) -> None:
        """指定 top_cell_name 只替换该 cell 的实例。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            multi_cell_subst_gds, out,
            {"CHILD_A": "CHILD_B"},
            top_cell_name="TOP",
        )
        # 只替换 TOP 中的 CHILD_A 实例，CHILD_B 中的不变
        assert report.total_instances_replaced == 1
        assert report.cells_affected == ["TOP"]
        # 验证 CHILD_B 中仍有 CHILD_A 实例
        counts_child_b = _count_instances_by_name(out, "CHILD_B")
        assert counts_child_b.get("CHILD_A", 0) == 1

    def test_returns_correct_paths(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """报告的 input_path/output_path 与传入参数一致。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        assert report.input_path == str(simple_subst_gds)
        assert report.output_path == str(out)

    def test_dbu_preserved(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """替换后 dbu 保持不变。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        assert report.dbu == 0.001
        ly = db.Layout()
        ly.read(str(out))
        assert float(ly.dbu) == 0.001

    def test_output_file_exists(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """替换后输出文件应存在。"""
        out = tmp_path / "out.gds"
        substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        assert out.exists()
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_str_path_input(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """支持 str 类型路径输入。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            str(simple_subst_gds), str(out), {"CHILD_A": "CHILD_B"}
        )
        assert report.input_path == str(simple_subst_gds)
        assert report.output_path == str(out)
        assert out.exists()

    def test_multiple_substitutions(
        self, tmp_path: Path
    ) -> None:
        """多个替换同时进行。"""
        # 创建含 CHILD_A, CHILD_B, CHILD_C 的 GDS
        src = tmp_path / "multi_sub.gds"
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        for name in ["CHILD_A", "CHILD_B", "CHILD_C", "CHILD_D", "CHILD_E"]:
            c = ly.create_cell(name)
            c.shapes(li).insert(db.Polygon([
                db.Point(0, 0), db.Point(10000, 0),
                db.Point(10000, 5000), db.Point(0, 5000),
            ]))
        top = ly.create_cell("TOP")
        top.insert(db.CellInstArray(
            ly.cell("CHILD_A").cell_index(), db.Trans(db.Point(0, 0))
        ))
        top.insert(db.CellInstArray(
            ly.cell("CHILD_C").cell_index(), db.Trans(db.Point(20000, 0))
        ))
        ly.write(str(src))

        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            src, out,
            {"CHILD_A": "CHILD_D", "CHILD_C": "CHILD_E"},
        )
        assert report.total_instances_replaced == 2
        counts = _count_instances_by_name(out, "TOP")
        assert counts.get("CHILD_D", 0) == 1
        assert counts.get("CHILD_E", 0) == 1
        assert counts.get("CHILD_A", 0) == 0
        assert counts.get("CHILD_C", 0) == 0

    def test_substitution_record_is_array(
        self, array_subst_gds: Path, tmp_path: Path
    ) -> None:
        """替换记录的 is_array 字段正确。"""
        out = tmp_path / "out.gds"
        report = substitute_cell_instances(
            array_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        # 应有 2 条记录：1 普通 + 1 数组
        assert len(report.substitutions_applied) == 2
        array_records = [r for r in report.substitutions_applied if r.is_array]
        normal_records = [r for r in report.substitutions_applied if not r.is_array]
        assert len(array_records) == 1
        assert len(normal_records) == 1

    def test_preserves_instance_position(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """替换后实例位置保持不变。"""
        out = tmp_path / "out.gds"
        substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        dbu = float(ly.dbu)
        positions = []
        for inst in top.each_inst():
            if inst.cell.name == "CHILD_B":
                disp = inst.trans.disp
                positions.append((float(disp.x) * dbu, float(disp.y) * dbu))
        positions.sort()
        assert positions == [(0.0, 0.0), (20.0, 0.0)]

    def test_preserves_rotation(
        self, tmp_path: Path
    ) -> None:
        """替换后实例旋转保持不变。"""
        src = tmp_path / "rot.gds"
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        child_a = ly.create_cell("CHILD_A")
        child_a.shapes(li).insert(db.Polygon([
            db.Point(0, 0), db.Point(10000, 0),
            db.Point(10000, 5000), db.Point(0, 5000),
        ]))
        child_b = ly.create_cell("CHILD_B")
        child_b.shapes(li).insert(db.Polygon([
            db.Point(0, 0), db.Point(20000, 0),
            db.Point(20000, 10000), db.Point(0, 10000),
        ]))
        top = ly.create_cell("TOP")
        # r90 旋转
        top.insert(db.CellInstArray(
            child_a.cell_index(),
            db.Trans(db.Trans.R90, db.Point(30000, 0))
        ))
        ly.write(str(src))

        out = tmp_path / "out.gds"
        substitute_cell_instances(src, out, {"CHILD_A": "CHILD_B"})
        ly2 = db.Layout()
        ly2.read(str(out))
        top2 = ly2.cell("TOP")
        for inst in top2.each_inst():
            assert inst.cell.name == "CHILD_B"
            # r90 → angle=1
            assert int(inst.trans.angle) == 1


# =============================================================================
# TestGenerateSubstituteReport
# =============================================================================
class TestGenerateSubstituteReport:
    """generate_substitute_report 函数测试。"""

    def test_text_report(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """生成 text 报告。"""
        out = tmp_path / "out.gds"
        report_str = generate_substitute_report(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"},
            output_format="text",
        )
        assert "GDSII 器件替换报告" in report_str
        assert "输入文件" in report_str
        assert "输出文件" in report_str
        assert "替换统计" in report_str
        assert "CHILD_A" in report_str
        assert "CHILD_B" in report_str
        assert out.exists()

    def test_markdown_report(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """生成 markdown 报告。"""
        out = tmp_path / "out.gds"
        report_str = generate_substitute_report(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"},
            output_format="markdown",
        )
        assert "# GDSII 器件替换报告" in report_str
        assert "## 基本信息" in report_str
        assert "## 替换统计" in report_str
        assert "**输入文件**" in report_str
        assert "| CHILD_A | CHILD_B |" in report_str

    def test_json_report(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """生成 json 报告，可解析。"""
        out = tmp_path / "out.gds"
        report_str = generate_substitute_report(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"},
            output_format="json",
        )
        data = json.loads(report_str)
        assert data["input_path"] == str(simple_subst_gds)
        assert data["output_path"] == str(out)
        assert data["substitutions_requested"] == {"CHILD_A": "CHILD_B"}
        assert data["total_instances_replaced"] == 2
        assert "TOP" in data["cells_affected"]

    def test_unsupported_format(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的格式抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_substitute_report(
                simple_subst_gds, out, {"CHILD_A": "CHILD_B"},
                output_format="xml",
            )


# =============================================================================
# TestR03ErrorHandling
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理：失败即 raise，禁止 fall-back。"""

    def test_input_not_exist(self, tmp_path: Path) -> None:
        """输入文件不存在抛 FileNotFoundError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError, match="输入 GDSII 文件不存在"):
            substitute_cell_instances(
                tmp_path / "nonexistent.gds", out, {"A": "B"}
            )

    def test_input_is_directory(self, tmp_path: Path) -> None:
        """输入是目录抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="输入路径不是文件"):
            substitute_cell_instances(tmp_path, out, {"A": "B"})

    def test_empty_substitutions(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """空 substitutions 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="substitutions 不能为空"):
            substitute_cell_instances(simple_subst_gds, out, {})

    def test_old_cell_not_exist(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """旧 cell 名不存在抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="旧 cell 名 'NOPE' 不存在"):
            substitute_cell_instances(
                simple_subst_gds, out, {"NOPE": "CHILD_B"}
            )

    def test_new_cell_not_exist(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """新 cell 名不存在抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="新 cell 名 'NOPE' 不存在"):
            substitute_cell_instances(
                simple_subst_gds, out, {"CHILD_A": "NOPE"}
            )

    def test_top_cell_name_not_exist(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """不存在的 top_cell_name 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="top_cell_name 'NOPE' 不存在"):
            substitute_cell_instances(
                simple_subst_gds, out, {"CHILD_A": "CHILD_B"},
                top_cell_name="NOPE",
            )

    def test_klayout_not_installed_monkey(
        self, simple_subst_gds: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """klayout 未安装抛 ImportError（用 monkeypatch 模拟）。"""
        import polaris.verification.gdsii_cell_substituter as mod

        def _raise():
            raise ImportError("simulated")

        monkeypatch.setattr(mod, "_import_klayout_db", _raise)
        out = tmp_path / "out.gds"
        with pytest.raises(ImportError, match="simulated"):
            substitute_cell_instances(
                simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
            )


# =============================================================================
# TestR02AcademicIntegrity
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信：所有参数/公式有文献溯源。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        import polaris.verification.gdsii_cell_substituter as mod
        assert mod.__doc__ is not None
        assert len(mod.__doc__) > 100

    def test_docstring_has_klayout_url(self) -> None:
        """docstring 含 KLayout API URL。"""
        import polaris.verification.gdsii_cell_substituter as mod
        assert "klayout.org" in mod.__doc__

    def test_docstring_has_instance_class(self) -> None:
        """docstring 含 Instance 类说明。"""
        import polaris.verification.gdsii_cell_substituter as mod
        assert "Instance" in mod.__doc__

    def test_docstring_has_cellinstarray(self) -> None:
        """docstring 含 CellInstArray 说明。"""
        import polaris.verification.gdsii_cell_substituter as mod
        assert "CellInstArray" in mod.__doc__

    def test_docstring_has_gdsii_url(self) -> None:
        """docstring 含 GDSII 格式 URL。"""
        import polaris.verification.gdsii_cell_substituter as mod
        assert "wikipedia.org" in mod.__doc__

    def test_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        import polaris.verification.gdsii_cell_substituter as mod
        assert "R01" in mod.__doc__
        assert "R02" in mod.__doc__
        assert "R03" in mod.__doc__

    def test_substitute_function_has_docstring(self) -> None:
        """substitute_cell_instances 函数有 docstring。"""
        assert substitute_cell_instances.__doc__ is not None
        assert "Args:" in substitute_cell_instances.__doc__
        assert "Returns:" in substitute_cell_instances.__doc__
        assert "Raises:" in substitute_cell_instances.__doc__

    def test_no_fallback_in_source(self) -> None:
        """源代码无 fall-back 模式。"""
        import inspect
        import polaris.verification.gdsii_cell_substituter as mod
        source = inspect.getsource(mod)
        assert "except: pass" not in source
        assert "except Exception: pass" not in source


# =============================================================================
# TestIntegration
# =============================================================================
class TestIntegration:
    """集成测试：替换前后统计对比。"""

    def test_substitute_then_statistics(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """替换后统计 cell 数不变。"""
        from polaris.verification.gdsii_statistics import (
            generate_gdsii_statistics,
        )

        orig_stats = generate_gdsii_statistics(simple_subst_gds)
        out = tmp_path / "out.gds"
        substitute_cell_instances(
            simple_subst_gds, out, {"CHILD_A": "CHILD_B"}
        )
        new_stats = generate_gdsii_statistics(out)
        # cell 数不变（CHILD_A 仍存在，只是不再被引用）
        assert new_stats.total_cells == orig_stats.total_cells

    def test_substitute_idempotent(
        self, simple_subst_gds: Path, tmp_path: Path
    ) -> None:
        """对已替换的文件再次替换（反向）应可逆。"""
        out1 = tmp_path / "out1.gds"
        substitute_cell_instances(
            simple_subst_gds, out1, {"CHILD_A": "CHILD_B"}
        )
        counts1 = _count_instances_by_name(out1, "TOP")
        assert counts1.get("CHILD_A", 0) == 0
        assert counts1.get("CHILD_B", 0) == 2

        # 反向替换
        out2 = tmp_path / "out2.gds"
        substitute_cell_instances(
            out1, out2, {"CHILD_B": "CHILD_A"}
        )
        counts2 = _count_instances_by_name(out2, "TOP")
        assert counts2.get("CHILD_A", 0) == 2
        assert counts2.get("CHILD_B", 0) == 0

    def test_substitute_preserves_unrelated_instances(
        self, tmp_path: Path
    ) -> None:
        """替换不影响其他 cell 的实例。"""
        src = tmp_path / "mixed.gds"
        ly = db.Layout()
        ly.dbu = 0.001
        li = ly.layer(1, 0)
        for name in ["CHILD_A", "CHILD_B", "CHILD_C"]:
            c = ly.create_cell(name)
            c.shapes(li).insert(db.Polygon([
                db.Point(0, 0), db.Point(10000, 0),
                db.Point(10000, 5000), db.Point(0, 5000),
            ]))
        top = ly.create_cell("TOP")
        top.insert(db.CellInstArray(
            ly.cell("CHILD_A").cell_index(), db.Trans(db.Point(0, 0))
        ))
        top.insert(db.CellInstArray(
            ly.cell("CHILD_C").cell_index(), db.Trans(db.Point(20000, 0))
        ))
        ly.write(str(src))

        out = tmp_path / "out.gds"
        substitute_cell_instances(src, out, {"CHILD_A": "CHILD_B"})
        counts = _count_instances_by_name(out, "TOP")
        # CHILD_A 被替换为 CHILD_B
        assert counts.get("CHILD_A", 0) == 0
        assert counts.get("CHILD_B", 0) == 1
        # CHILD_C 不受影响
        assert counts.get("CHILD_C", 0) == 1


# =============================================================================
# TestDataclassTest
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_substitute_report_default(self) -> None:
        """SubstituteReport 默认值。"""
        report = SubstituteReport()
        assert report.input_path == ""
        assert report.output_path == ""
        assert report.substitutions_requested == {}
        assert report.substitutions_applied == []
        assert report.total_instances_replaced == 0
        assert report.cells_affected == []
        assert report.dbu == 0.0
        assert report.top_cell_names == []

    def test_substitution_record_default(self) -> None:
        """SubstitutionRecord 默认值。"""
        rec = SubstitutionRecord(
            parent_cell_name="TOP",
            old_cell_name="A",
            new_cell_name="B",
            instance_count=1,
            is_array=False,
        )
        assert rec.parent_cell_name == "TOP"
        assert rec.old_cell_name == "A"
        assert rec.new_cell_name == "B"
        assert rec.instance_count == 1
        assert rec.is_array is False

    def test_substitute_report_equality(self) -> None:
        """相同字段的对象相等。"""
        r1 = SubstituteReport(total_instances_replaced=2)
        r2 = SubstituteReport(total_instances_replaced=2)
        assert r1 == r2

    def test_substitute_report_inequality(self) -> None:
        """不同字段的对象不等。"""
        r1 = SubstituteReport(total_instances_replaced=1)
        r2 = SubstituteReport(total_instances_replaced=2)
        assert r1 != r2

    def test_substitute_report_field_names(self) -> None:
        """SubstituteReport 字段名正确。"""
        from dataclasses import fields
        field_names = {f.name for f in fields(SubstituteReport)}
        expected = {
            "input_path", "output_path", "substitutions_requested",
            "substitutions_applied", "total_instances_replaced",
            "cells_affected", "dbu", "top_cell_names",
        }
        assert field_names == expected

    def test_substitution_record_field_names(self) -> None:
        """SubstitutionRecord 字段名正确。"""
        from dataclasses import fields
        field_names = {f.name for f in fields(SubstitutionRecord)}
        expected = {
            "parent_cell_name", "old_cell_name", "new_cell_name",
            "instance_count", "is_array",
        }
        assert field_names == expected

    def test_lists_independent(self) -> None:
        """默认列表字段独立。"""
        r1 = SubstituteReport()
        r2 = SubstituteReport()
        r1.cells_affected.append("X")
        assert "X" not in r2.cells_affected
        r1.substitutions_applied.append(
            SubstitutionRecord("P", "A", "B", 1, False)
        )
        assert len(r2.substitutions_applied) == 0

    def test_repr(self) -> None:
        """repr 可读。"""
        report = SubstituteReport(total_instances_replaced=5)
        repr_str = repr(report)
        assert "SubstituteReport" in repr_str
        assert "total_instances_replaced=5" in repr_str
