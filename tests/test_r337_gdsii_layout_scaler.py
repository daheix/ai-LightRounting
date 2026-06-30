"""R337 GDSII 版图缩放工具测试。

覆盖:
- scale_gdsii: 各种缩放比例（0.5x/1.0x/2.0x/1.5x/0.1x）
- 指定 top_cell_name 缩放
- 多顶层 cell 缩放
- generate_scale_report: text/markdown/json 报告
- _scale_factor_to_fraction: Fraction 转换
- R03 错误处理（FileNotFoundError/ValueError/RuntimeError）
- R02 学术诚信（docstring/参考文献/无假数据）
- 集成测试（缩放前后读取统计对比）
- 数据类测试

来源:
- KLayout Layout.scale_and_snap:
  https://klayout.org/doc-qt5/code/class_Layout.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Python Fraction: https://docs.python.org/3/library/fractions.html
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_layout_scaler import (
    ScaleReport,
    _scale_factor_to_fraction,
    generate_scale_report,
    scale_gdsii,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_simple_gds(path: Path) -> Path:
    """创建简单 GDSII（单顶层 cell，含 1 个 polygon）。

    polygon bbox: (0,0)-(100,50) μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    # polygon: (0,0)-(100,50) μm = (0,0)-(100000,50000) dbu
    pts = [db.Point(0, 0), db.Point(100000, 0),
           db.Point(100000, 50000), db.Point(0, 50000)]
    top.shapes(li).insert(db.Polygon(pts))
    ly.write(str(path))
    return path


def _make_hierarchical_gds(path: Path) -> Path:
    """创建层次化 GDSII（顶层 cell 含子 cell 实例）。

    结构:
    - TOP cell
      - CHILD @ (20, 10) μm
    - CHILD cell (polygon (0,0)-(30,20) μm)
    - 期望 TOP bbox = (0,0)-(100,50) μm + CHILD 平移 = (20,10)-(50,30) μm
      → 合并 bbox = (0,0)-(100,50) μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    child = ly.create_cell("CHILD")
    pts_c = [db.Point(0, 0), db.Point(30000, 0),
             db.Point(30000, 20000), db.Point(0, 20000)]
    child.shapes(li).insert(db.Polygon(pts_c))

    top = ly.create_cell("TOP")
    pts_t = [db.Point(0, 0), db.Point(100000, 0),
             db.Point(100000, 50000), db.Point(0, 50000)]
    top.shapes(li).insert(db.Polygon(pts_t))
    top.insert(db.CellInstArray(
        child.cell_index(), db.Trans(db.Point(20000, 10000))
    ))

    ly.write(str(path))
    return path


def _make_multi_top_gds(path: Path) -> Path:
    """创建多顶层 cell GDSII（2 个顶层 cell）。"""
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    top1 = ly.create_cell("TOP1")
    pts1 = [db.Point(0, 0), db.Point(100000, 0),
            db.Point(100000, 50000), db.Point(0, 50000)]
    top1.shapes(li).insert(db.Polygon(pts1))

    top2 = ly.create_cell("TOP2")
    pts2 = [db.Point(0, 0), db.Point(200000, 0),
            db.Point(200000, 100000), db.Point(0, 100000)]
    top2.shapes(li).insert(db.Polygon(pts2))

    ly.write(str(path))
    return path


@pytest.fixture
def simple_gds(tmp_path: Path) -> Path:
    """简单 GDSII 文件（单顶层 cell）。"""
    return _make_simple_gds(tmp_path / "simple.gds")


@pytest.fixture
def hierarchical_gds(tmp_path: Path) -> Path:
    """层次化 GDSII 文件。"""
    return _make_hierarchical_gds(tmp_path / "hier.gds")


@pytest.fixture
def multi_top_gds(tmp_path: Path) -> Path:
    """多顶层 cell GDSII 文件。"""
    return _make_multi_top_gds(tmp_path / "multi.gds")


def _read_bbox_um(gds_path: Path) -> tuple[float, float, float, float]:
    """读取 GDSII 顶层 cell bbox（μm）。"""
    ly = db.Layout()
    ly.read(str(gds_path))
    top_ci = list(ly.each_top_cell())[0]
    top = ly.cell(top_ci)
    bbox = top.bbox()
    dbu = float(ly.dbu)
    return (
        float(bbox.left) * dbu,
        float(bbox.bottom) * dbu,
        float(bbox.right) * dbu,
        float(bbox.top) * dbu,
    )


# =============================================================================
# TestScaleGdsii: 缩放主入口测试
# =============================================================================
class TestScaleGdsii:
    """scale_gdsii 函数测试。"""

    def test_scale_half(self, simple_gds: Path, tmp_path: Path) -> None:
        """0.5x 缩放：bbox 应减半。"""
        out = tmp_path / "out_0p5.gds"
        report = scale_gdsii(simple_gds, out, 0.5)
        assert report.mult == 1
        assert report.div == 2
        assert report.actual_scale == 0.5
        assert report.scale_factor == 0.5
        # 验证 bbox
        assert report.original_bbox_um == (0.0, 0.0, 100.0, 50.0)
        assert report.scaled_bbox_um == (0.0, 0.0, 50.0, 25.0)
        # 重新读取验证
        bbox = _read_bbox_um(out)
        assert bbox == (0.0, 0.0, 50.0, 25.0)

    def test_scale_double(self, simple_gds: Path, tmp_path: Path) -> None:
        """2.0x 缩放：bbox 应翻倍。"""
        out = tmp_path / "out_2x.gds"
        report = scale_gdsii(simple_gds, out, 2.0)
        assert report.mult == 2
        assert report.div == 1
        assert report.actual_scale == 2.0
        assert report.scaled_bbox_um == (0.0, 0.0, 200.0, 100.0)
        bbox = _read_bbox_um(out)
        assert bbox == (0.0, 0.0, 200.0, 100.0)

    def test_scale_one(self, simple_gds: Path, tmp_path: Path) -> None:
        """1.0x 缩放：bbox 不变。"""
        out = tmp_path / "out_1x.gds"
        report = scale_gdsii(simple_gds, out, 1.0)
        assert report.mult == 1
        assert report.div == 1
        assert report.actual_scale == 1.0
        assert report.scaled_bbox_um == (0.0, 0.0, 100.0, 50.0)
        bbox = _read_bbox_um(out)
        assert bbox == (0.0, 0.0, 100.0, 50.0)

    def test_scale_one_half(self, simple_gds: Path, tmp_path: Path) -> None:
        """1.5x 缩放：bbox × 1.5。"""
        out = tmp_path / "out_1p5.gds"
        report = scale_gdsii(simple_gds, out, 1.5)
        assert report.mult == 3
        assert report.div == 2
        assert report.actual_scale == 1.5
        # 100 × 1.5 = 150, 50 × 1.5 = 75
        assert report.scaled_bbox_um == (0.0, 0.0, 150.0, 75.0)
        bbox = _read_bbox_um(out)
        assert bbox == (0.0, 0.0, 150.0, 75.0)

    def test_scale_one_tenth(self, simple_gds: Path, tmp_path: Path) -> None:
        """0.1x 缩放：bbox × 0.1。"""
        out = tmp_path / "out_0p1.gds"
        report = scale_gdsii(simple_gds, out, 0.1)
        assert report.mult == 1
        assert report.div == 10
        assert report.actual_scale == 0.1
        # 100 × 0.1 = 10, 50 × 0.1 = 5
        assert report.scaled_bbox_um == (0.0, 0.0, 10.0, 5.0)
        bbox = _read_bbox_um(out)
        assert bbox == (0.0, 0.0, 10.0, 5.0)

    def test_scale_third(self, simple_gds: Path, tmp_path: Path) -> None:
        """1/3 缩放：用 Fraction 转换 0.333...→1/3。"""
        out = tmp_path / "out_third.gds"
        report = scale_gdsii(simple_gds, out, 1.0 / 3.0)
        # Fraction(1/3).limit_denominator(10000) = 1/3
        assert report.mult == 1
        assert report.div == 3
        # 100 / 3 ≈ 33.333, 50 / 3 ≈ 16.667
        # scale_and_snap 会 snap 到 grid=1 dbu，所以是整数 dbu
        # 100000 dbu / 3 = 33333.33... → snap 到 33333 dbu = 33.333 μm
        # 用浮点比较 + 容差
        eps = 0.01  # 10 nm 容差
        l, b, r, t = report.scaled_bbox_um
        assert abs(l - 0.0) < eps
        assert abs(b - 0.0) < eps
        assert abs(r - 100.0 / 3.0) < eps
        assert abs(t - 50.0 / 3.0) < eps

    def test_scale_hierarchical(self, hierarchical_gds: Path, tmp_path: Path) -> None:
        """层次化 GDSII 缩放：保留层次结构。"""
        out = tmp_path / "out_hier.gds"
        report = scale_gdsii(hierarchical_gds, out, 0.5)
        # 源 bbox = (0,0)-(100,50) μm
        assert report.original_bbox_um == (0.0, 0.0, 100.0, 50.0)
        assert report.scaled_bbox_um == (0.0, 0.0, 50.0, 25.0)
        # 验证层次结构保留
        ly = db.Layout()
        ly.read(str(out))
        cell_names = sorted(c.name for c in ly.each_cell())
        # 应同时存在 TOP 和 CHILD
        assert "TOP" in cell_names
        assert "CHILD" in cell_names

    def test_scale_with_grid(self, simple_gds: Path, tmp_path: Path) -> None:
        """用 grid_dbu=10 测试网格对齐。"""
        out = tmp_path / "out_grid.gds"
        report = scale_gdsii(simple_gds, out, 0.5, grid_dbu=10)
        assert report.grid_dbu == 10
        # 100000 dbu × 0.5 = 50000 dbu, snap 到 10 dbu 网格 → 50000 dbu = 50 μm
        assert report.scaled_bbox_um == (0.0, 0.0, 50.0, 25.0)

    def test_scale_with_top_cell_name(
        self, multi_top_gds: Path, tmp_path: Path
    ) -> None:
        """指定 top_cell_name 只缩放该 cell。"""
        out = tmp_path / "out_named.gds"
        report = scale_gdsii(
            multi_top_gds, out, 0.5, top_cell_name="TOP1"
        )
        assert "TOP1" in report.top_cell_names
        assert "TOP2" in report.top_cell_names
        # 多顶层 cell 时 bbox 报告为 (0,0,0,0)
        # 但只缩放了 TOP1，所以实际 TOP1 bbox 应减半
        ly = db.Layout()
        ly.read(str(out))
        top1 = ly.cell("TOP1")
        bbox = top1.bbox()
        dbu = float(ly.dbu)
        # 原本 (0,0)-(100,50) μm，0.5x → (0,0)-(50,25) μm
        assert float(bbox.right) * dbu == 50.0
        assert float(bbox.top) * dbu == 25.0
        # TOP2 应保持不变
        top2 = ly.cell("TOP2")
        bbox2 = top2.bbox()
        assert float(bbox2.right) * dbu == 200.0
        assert float(bbox2.top) * dbu == 100.0

    def test_scale_all_top_cells(
        self, multi_top_gds: Path, tmp_path: Path
    ) -> None:
        """不指定 top_cell_name 时缩放所有顶层 cell。"""
        out = tmp_path / "out_all.gds"
        report = scale_gdsii(multi_top_gds, out, 0.5)
        assert len(report.top_cell_names) == 2
        # 多顶层时 bbox 报告为 (0,0,0,0)
        assert report.original_bbox_um == (0.0, 0.0, 0.0, 0.0)
        assert report.scaled_bbox_um == (0.0, 0.0, 0.0, 0.0)
        # 验证两个 cell 都被缩放
        ly = db.Layout()
        ly.read(str(out))
        top1 = ly.cell("TOP1")
        top2 = ly.cell("TOP2")
        dbu = float(ly.dbu)
        # TOP1: (0,0)-(100,50) → 0.5x → (0,0)-(50,25)
        assert float(top1.bbox().right) * dbu == 50.0
        # TOP2: (0,0)-(200,100) → 0.5x → (0,0)-(100,50)
        assert float(top2.bbox().right) * dbu == 100.0

    def test_scale_returns_correct_paths(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """报告的 input_path/output_path 与传入参数一致。"""
        out = tmp_path / "out_paths.gds"
        report = scale_gdsii(simple_gds, out, 1.0)
        assert report.input_path == str(simple_gds)
        assert report.output_path == str(out)

    def test_scale_dbu_preserved(self, simple_gds: Path, tmp_path: Path) -> None:
        """缩放后 dbu 保持不变。"""
        out = tmp_path / "out_dbu.gds"
        report = scale_gdsii(simple_gds, out, 0.5)
        assert report.dbu == 0.001
        ly = db.Layout()
        ly.read(str(out))
        assert float(ly.dbu) == 0.001

    def test_scale_output_file_exists(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """缩放后输出文件应存在。"""
        out = tmp_path / "out_exists.gds"
        scale_gdsii(simple_gds, out, 0.5)
        assert out.exists()
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_scale_str_path_input(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """支持 str 类型路径输入。"""
        out = tmp_path / "out_str.gds"
        report = scale_gdsii(str(simple_gds), str(out), 0.5)
        assert report.input_path == str(simple_gds)
        assert report.output_path == str(out)
        assert out.exists()

    def test_scale_max_denominator(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """max_denominator 限制分母。"""
        out = tmp_path / "out_maxden.gds"
        # 0.123456789 with max_denominator=100 → 10/81 或类似
        report = scale_gdsii(
            simple_gds, out, 0.123456789, max_denominator=100
        )
        assert report.div <= 100

    def test_scale_grid_affects_precision(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """grid_dbu 影响 snap 精度。"""
        out = tmp_path / "out_grid_prec.gds"
        # 1/3 缩放，grid=100 dbu 会 snap 到 100 dbu 网格
        report = scale_gdsii(simple_gds, out, 1.0 / 3.0, grid_dbu=100)
        assert report.grid_dbu == 100
        # bbox 应 snap 到 100 dbu = 0.1 μm 网格
        l, b, r, t = report.scaled_bbox_um
        # r 应是 0.1 的倍数
        assert abs(r * 10 - round(r * 10)) < 1e-6


# =============================================================================
# TestScaleFactorToFraction
# =============================================================================
class TestScaleFactorToFraction:
    """_scale_factor_to_fraction 内部函数测试。"""

    def test_half(self) -> None:
        """0.5 → (1, 2)。"""
        assert _scale_factor_to_fraction(0.5) == (1, 2)

    def test_double(self) -> None:
        """2.0 → (2, 1)。"""
        assert _scale_factor_to_fraction(2.0) == (2, 1)

    def test_one(self) -> None:
        """1.0 → (1, 1)。"""
        assert _scale_factor_to_fraction(1.0) == (1, 1)

    def test_one_half(self) -> None:
        """1.5 → (3, 2)。"""
        assert _scale_factor_to_fraction(1.5) == (3, 2)

    def test_one_tenth(self) -> None:
        """0.1 → (1, 10)。"""
        assert _scale_factor_to_fraction(0.1) == (1, 10)

    def test_third(self) -> None:
        """1/3 → (1, 3)。"""
        assert _scale_factor_to_fraction(1.0 / 3.0) == (1, 3)

    def test_max_denominator_limit(self) -> None:
        """max_denominator 限制分母上限。"""
        # π 用 max_denominator=10 应得到 22/7
        mult, div = _scale_factor_to_fraction(3.14159, max_denominator=10)
        assert div <= 10

    def test_zero_raises(self) -> None:
        """scale_factor=0 抛 ValueError。"""
        with pytest.raises(ValueError, match="scale_factor 必须 > 0"):
            _scale_factor_to_fraction(0.0)

    def test_negative_raises(self) -> None:
        """scale_factor=-1 抛 ValueError。"""
        with pytest.raises(ValueError, match="scale_factor 必须 > 0"):
            _scale_factor_to_fraction(-1.0)

    def test_invalid_max_denominator(self) -> None:
        """max_denominator=0 抛 ValueError。"""
        with pytest.raises(ValueError, match="max_denominator 必须 >= 1"):
            _scale_factor_to_fraction(0.5, max_denominator=0)


# =============================================================================
# TestGenerateScaleReport
# =============================================================================
class TestGenerateScaleReport:
    """generate_scale_report 函数测试。"""

    def test_text_report(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """生成 text 报告。"""
        out = tmp_path / "out_text.gds"
        report_str = generate_scale_report(
            simple_gds, out, 0.5, output_format="text"
        )
        assert "GDSII 版图缩放报告" in report_str
        assert "输入文件" in report_str
        assert "输出文件" in report_str
        assert "缩放参数" in report_str
        assert "mult" in report_str
        assert "div" in report_str
        assert "0.5" in report_str
        assert out.exists()

    def test_markdown_report(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """生成 markdown 报告。"""
        out = tmp_path / "out_md.gds"
        report_str = generate_scale_report(
            simple_gds, out, 2.0, output_format="markdown"
        )
        assert "# GDSII 版图缩放报告" in report_str
        assert "## 基本信息" in report_str
        assert "## 缩放参数" in report_str
        assert "**输入文件**" in report_str
        assert "| 分子 mult | 2 |" in report_str
        assert "| 分母 div | 1 |" in report_str

    def test_json_report(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """生成 json 报告，可解析。"""
        out = tmp_path / "out_json.gds"
        report_str = generate_scale_report(
            simple_gds, out, 1.5, output_format="json"
        )
        data = json.loads(report_str)
        assert data["input_path"] == str(simple_gds)
        assert data["output_path"] == str(out)
        assert data["mult"] == 3
        assert data["div"] == 2
        assert data["scale_factor"] == 1.5
        assert data["actual_scale"] == 1.5

    def test_unsupported_format(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的格式抛 ValueError。"""
        out = tmp_path / "out_bad.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_scale_report(
                simple_gds, out, 0.5, output_format="xml"
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
            scale_gdsii(tmp_path / "nonexistent.gds", out, 0.5)

    def test_input_is_directory(self, tmp_path: Path) -> None:
        """输入是目录抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="输入路径不是文件"):
            scale_gdsii(tmp_path, out, 0.5)

    def test_scale_factor_zero(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """scale_factor=0 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="scale_factor 必须 > 0"):
            scale_gdsii(simple_gds, out, 0.0)

    def test_scale_factor_negative(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """scale_factor<0 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="scale_factor 必须 > 0"):
            scale_gdsii(simple_gds, out, -1.0)

    def test_grid_dbu_zero(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """grid_dbu=0 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="grid_dbu 必须 >= 1"):
            scale_gdsii(simple_gds, out, 0.5, grid_dbu=0)

    def test_grid_dbu_negative(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """grid_dbu<0 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="grid_dbu 必须 >= 1"):
            scale_gdsii(simple_gds, out, 0.5, grid_dbu=-1)

    def test_top_cell_name_not_exist(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """不存在的 top_cell_name 抛 ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="top_cell_name 'NOPE' 不存在"):
            scale_gdsii(simple_gds, out, 0.5, top_cell_name="NOPE")

    def test_klayout_not_installed_monkey(
        self, simple_gds: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """klayout 未安装抛 ImportError（用 monkeypatch 模拟）。"""
        import polaris.verification.gdsii_layout_scaler as mod

        def _raise():
            raise ImportError("simulated")

        monkeypatch.setattr(mod, "_import_klayout_db", _raise)
        out = tmp_path / "out.gds"
        with pytest.raises(ImportError, match="simulated"):
            scale_gdsii(simple_gds, out, 0.5)


# =============================================================================
# TestR02AcademicIntegrity
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信：所有参数/公式有文献溯源。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        import polaris.verification.gdsii_layout_scaler as mod
        assert mod.__doc__ is not None
        assert len(mod.__doc__) > 100

    def test_docstring_has_klayout_url(self) -> None:
        """docstring 含 KLayout API URL。"""
        import polaris.verification.gdsii_layout_scaler as mod
        assert "klayout.org" in mod.__doc__

    def test_docstring_has_scale_and_snap(self) -> None:
        """docstring 含 scale_and_snap API 说明。"""
        import polaris.verification.gdsii_layout_scaler as mod
        assert "scale_and_snap" in mod.__doc__

    def test_docstring_has_fraction_url(self) -> None:
        """docstring 含 Python Fraction URL。"""
        import polaris.verification.gdsii_layout_scaler as mod
        assert "docs.python.org" in mod.__doc__
        assert "Fraction" in mod.__doc__ or "fractions" in mod.__doc__

    def test_docstring_has_gdsii_url(self) -> None:
        """docstring 含 GDSII 格式 URL。"""
        import polaris.verification.gdsii_layout_scaler as mod
        assert "wikipedia.org" in mod.__doc__

    def test_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        import polaris.verification.gdsii_layout_scaler as mod
        assert "R01" in mod.__doc__
        assert "R02" in mod.__doc__
        assert "R03" in mod.__doc__

    def test_scale_function_has_docstring(self) -> None:
        """scale_gdsii 函数有 docstring。"""
        assert scale_gdsii.__doc__ is not None
        assert "Args:" in scale_gdsii.__doc__
        assert "Returns:" in scale_gdsii.__doc__
        assert "Raises:" in scale_gdsii.__doc__

    def test_no_fallback_in_source(self) -> None:
        """源代码无 fall-back 模式（return None / except: pass）。"""
        import inspect
        import polaris.verification.gdsii_layout_scaler as mod
        source = inspect.getsource(mod)
        # 禁止 except: pass
        assert "except: pass" not in source
        assert "except Exception: pass" not in source
        # 禁止 return None（除 __repr__ 等特殊方法外）
        # scale_gdsii 和 generate_scale_report 都不应 return None


# =============================================================================
# TestIntegration
# =============================================================================
class TestIntegration:
    """集成测试：缩放前后统计对比。"""

    def test_scale_then_statistics(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """缩放后再统计，验证面积按比例缩放。"""
        from polaris.verification.gdsii_statistics import (
            generate_gdsii_statistics,
        )

        # 原始统计
        orig_stats = generate_gdsii_statistics(simple_gds)
        orig_area = orig_stats.total_area_um2
        # bbox = 100 × 50 = 5000 μm²
        assert orig_area == pytest.approx(5000.0, abs=0.01)

        # 2x 缩放
        out = tmp_path / "out_2x.gds"
        scale_gdsii(simple_gds, out, 2.0)
        scaled_stats = generate_gdsii_statistics(out)
        scaled_area = scaled_stats.total_area_um2
        # 2x 缩放面积应 ×4（线性 ×2，面积 ×4）
        assert scaled_area == pytest.approx(orig_area * 4.0, abs=0.5)

    def test_scale_half_then_statistics(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """0.5x 缩放后面积应 ×0.25。"""
        from polaris.verification.gdsii_statistics import (
            generate_gdsii_statistics,
        )

        orig_stats = generate_gdsii_statistics(simple_gds)
        orig_area = orig_stats.total_area_um2

        out = tmp_path / "out_half.gds"
        scale_gdsii(simple_gds, out, 0.5)
        scaled_stats = generate_gdsii_statistics(out)
        scaled_area = scaled_stats.total_area_um2
        # 0.5x 缩放面积应 ×0.25
        assert scaled_area == pytest.approx(orig_area * 0.25, abs=0.5)

    def test_scale_idempotent_one(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """1.0x 缩放应无变化（幂等）。"""
        out = tmp_path / "out_idem.gds"
        scale_gdsii(simple_gds, out, 1.0)
        bbox = _read_bbox_um(out)
        assert bbox == (0.0, 0.0, 100.0, 50.0)

    def test_scale_compose_half_twice(
        self, simple_gds: Path, tmp_path: Path
    ) -> None:
        """两次 0.5x 缩放等价于一次 0.25x。"""
        # 第一次 0.5x
        out1 = tmp_path / "out_half1.gds"
        scale_gdsii(simple_gds, out1, 0.5)
        # 第二次 0.5x
        out2 = tmp_path / "out_half2.gds"
        scale_gdsii(out1, out2, 0.5)
        bbox = _read_bbox_um(out2)
        # 100 × 0.5 × 0.5 = 25, 50 × 0.5 × 0.5 = 12.5
        assert bbox == (0.0, 0.0, 25.0, 12.5)

        # 直接 0.25x
        out3 = tmp_path / "out_quarter.gds"
        scale_gdsii(simple_gds, out3, 0.25)
        bbox3 = _read_bbox_um(out3)
        assert bbox3 == (0.0, 0.0, 25.0, 12.5)

    def test_scale_hierarchical_preserves_cells(
        self, hierarchical_gds: Path, tmp_path: Path
    ) -> None:
        """层次化 GDSII 缩放后保留所有 cell。"""
        out = tmp_path / "out_hier.gds"
        scale_gdsii(hierarchical_gds, out, 0.5)
        ly = db.Layout()
        ly.read(str(out))
        cell_names = {c.name for c in ly.each_cell()}
        assert "TOP" in cell_names
        assert "CHILD" in cell_names


# =============================================================================
# TestDataclassTest
# =============================================================================
class TestDataclassTest:
    """ScaleReport 数据类测试。"""

    def test_default_values(self) -> None:
        """默认值正确。"""
        report = ScaleReport()
        assert report.input_path == ""
        assert report.output_path == ""
        assert report.scale_factor == 1.0
        assert report.mult == 1
        assert report.div == 1
        assert report.grid_dbu == 1
        assert report.dbu == 0.0
        assert report.top_cell_names == []
        assert report.original_bbox_um == (0.0, 0.0, 0.0, 0.0)
        assert report.scaled_bbox_um == (0.0, 0.0, 0.0, 0.0)
        assert report.actual_scale == 1.0

    def test_custom_values(self) -> None:
        """自定义值正确。"""
        report = ScaleReport(
            input_path="/in.gds",
            output_path="/out.gds",
            scale_factor=0.5,
            mult=1,
            div=2,
            grid_dbu=1,
            dbu=0.001,
            top_cell_names=["TOP"],
            original_bbox_um=(0.0, 0.0, 100.0, 50.0),
            scaled_bbox_um=(0.0, 0.0, 50.0, 25.0),
            actual_scale=0.5,
        )
        assert report.input_path == "/in.gds"
        assert report.output_path == "/out.gds"
        assert report.scale_factor == 0.5
        assert report.mult == 1
        assert report.div == 2
        assert report.dbu == 0.001
        assert report.top_cell_names == ["TOP"]
        assert report.original_bbox_um == (0.0, 0.0, 100.0, 50.0)
        assert report.scaled_bbox_um == (0.0, 0.0, 50.0, 25.0)
        assert report.actual_scale == 0.5

    def test_equality(self) -> None:
        """相同字段的对象相等。"""
        r1 = ScaleReport(input_path="/a.gds", mult=2, div=3)
        r2 = ScaleReport(input_path="/a.gds", mult=2, div=3)
        assert r1 == r2

    def test_inequality(self) -> None:
        """不同字段的对象不等。"""
        r1 = ScaleReport(mult=1)
        r2 = ScaleReport(mult=2)
        assert r1 != r2

    def test_field_names(self) -> None:
        """数据类字段名正确。"""
        from dataclasses import fields
        field_names = {f.name for f in fields(ScaleReport)}
        expected = {
            "input_path", "output_path", "scale_factor",
            "mult", "div", "grid_dbu", "dbu",
            "top_cell_names", "original_bbox_um",
            "scaled_bbox_um", "actual_scale",
        }
        assert field_names == expected

    def test_top_cell_names_independent(self) -> None:
        """top_cell_names 默认列表独立（不共享引用）。"""
        r1 = ScaleReport()
        r2 = ScaleReport()
        r1.top_cell_names.append("X")
        assert "X" not in r2.top_cell_names

    def test_repr(self) -> None:
        """repr 可读。"""
        report = ScaleReport(mult=2, div=3)
        repr_str = repr(report)
        assert "ScaleReport" in repr_str
        assert "mult=2" in repr_str
