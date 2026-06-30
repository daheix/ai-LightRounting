"""R325 GDSII 网格对齐检查器测试。

覆盖:
- check_grid_alignment: on-grid/off-grid 检测（polygon/box/子 cell 递归）
- generate_grid_check_report: text/markdown 报告
- GridViolation / GridCheckReport: 数据类
- R03 错误处理（文件不存在/grid_um<=0/top_cell 不存在/不支持格式）
- R02 学术诚信（docstring URL/__all__/默认值）
- 集成测试（端到端 + 与 R324 变换后检查）

来源:
- KLayout DRC grid check:
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref.html
- KLayout Polygon class:
  https://www.klayout.org/doc-qt5/code/class_Polygon.html
- KLayout Box class:
  https://www.klayout.org/doc-qt5/code/class_Box.html
- KLayout Shape class:
  https://www.klayout.org/doc-qt4/code/class_Shape.html
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_grid_alignment_checker import (
    GridCheckReport,
    GridViolation,
    check_grid_alignment,
    generate_grid_check_report,
)


# =============================================================================
# 辅助函数: 直接用 klayout API 创建含 Box 的 GDSII
# =============================================================================
def _create_gds_with_box(
    output_path: Path,
    box_specs: list[dict],
    dbu_um: float = 0.001,
    top_cell_name: str = "TOP",
) -> Path:
    """直接用 klayout API 创建含 Box shape 的 GDSII。

    create_gdsii_layout_from_cells 不支持 box 字段，故用 klayout API 直接构造。

    Args:
        output_path: 输出路径。
        box_specs: box 规格列表，每个含 layer/datatype/left/bottom/right/top
                   （单位 μm）。
        dbu_um: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。

    Returns:
        GDSII 文件路径。
    """
    import klayout.db as db

    ly = db.Layout()
    ly.dbu = dbu_um
    top = ly.create_cell(top_cell_name)
    for spec in box_specs:
        layer = int(spec["layer"])
        datatype = int(spec["datatype"])
        li = ly.layer(layer, datatype)
        # μm → dbu（用 round 保持精度，与 grid 检查一致）
        left_dbu = int(round(spec["left"] / dbu_um))
        bottom_dbu = int(round(spec["bottom"] / dbu_um))
        right_dbu = int(round(spec["right"] / dbu_um))
        top_dbu = int(round(spec["top"] / dbu_um))
        box = db.Box(left_dbu, bottom_dbu, right_dbu, top_dbu)
        top.shapes(li).insert(box)
    ly.write(str(output_path))
    return output_path


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def on_grid_polygon_gds(tmp_path: Path) -> Path:
    """创建所有顶点在 5nm grid 上的 polygon GDSII（三角形）。

    三角形: (0,0)-(10,0)-(5,5) μm，所有坐标是 5nm 的倍数。
    grid_um=0.005 → grid_dbu=5，应无违规。

    注: 用三角形（3 点）而非矩形（4 点），因为 KLayout GDSII writer 会把
    4 点矩形 polygon 优化成 BOX record（shape.is_box()=True），导致无法
    测试 polygon 路径。三角形不会被优化，确保 is_polygon()=True。
    来源: KLayout GDSII writer 矩形优化
    https://www.klayout.org/doc-qt5/code/class_Layout.html
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
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "on_grid.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def off_grid_polygon_gds(tmp_path: Path) -> Path:
    """创建含 off-grid 顶点的 polygon GDSII（三角形）。

    三角形顶点: (0,0), (0.007,0), (0.007,0.005) μm
    0.007μm = 7dbu，grid_dbu=5 时 7%5=2 → off-grid
    0.005μm = 5dbu，5%5=0 → on-grid
    预期违规: 顶点 (7,0) 和 (7,5)（X 方向 off=2）

    注: 用三角形（3 点）而非矩形（4 点），因为 KLayout GDSII writer 会把
    4 点矩形 polygon 优化成 BOX record（shape.is_box()=True），导致无法
    测试 polygon 路径。三角形不会被优化，确保 is_polygon()=True。
    来源: KLayout GDSII writer 矩形优化
    https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [
                        [0, 0],
                        [0.007, 0],
                        [0.007, 0.005],
                    ],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "off_grid.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def on_grid_box_gds(tmp_path: Path) -> Path:
    """创建所有顶点在 5nm grid 上的 Box GDSII。

    Box: (0,0)-(10,5) μm，所有角点是 5nm 的倍数。
    """
    out = tmp_path / "on_grid_box.gds"
    _create_gds_with_box(
        out,
        [{"layer": 1, "datatype": 0, "left": 0, "bottom": 0, "right": 10, "top": 5}],
    )
    return out


@pytest.fixture
def off_grid_box_gds(tmp_path: Path) -> Path:
    """创建含 off-grid 顶点的 Box GDSII。

    Box: (0,0)-(0.007, 0.005) μm
    0.007μm = 7dbu，grid_dbu=5 时 7%5=2 → off-grid
    预期违规: 角点 (7,0) 和 (7,5)
    """
    out = tmp_path / "off_grid_box.gds"
    _create_gds_with_box(
        out,
        [
            {
                "layer": 1,
                "datatype": 0,
                "left": 0,
                "bottom": 0,
                "right": 0.007,
                "top": 0.005,
            }
        ],
    )
    return out


@pytest.fixture
def child_cell_off_grid_gds(tmp_path: Path) -> Path:
    """创建子 cell 实例中含 off-grid 顶点的 GDSII（三角形）。

    TOP cell:
    - 自己的 polygon: (0,0)-(10,0)-(5,5)（on-grid 三角形）
    - 实例化 CHILD cell（放在 (20, 0) μm 位置）
    CHILD cell:
    - polygon: (0,0)-(0.007,0)-(0.007,0.005)（off-grid 三角形）

    实例 placement (20,0)μm = (20000, 0)dbu，20000%5=0 → on-grid
    CHILD 顶点 (7,0)dbu + placement (20000,0)dbu = (20007, 0)dbu
    20007 % 5 = 2 → off-grid（递归检测应发现）

    注: 用三角形（3 点）而非矩形（4 点），避免 KLayout 把矩形优化成 Box。
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [0.007, 0], [0.007, 0.005]],
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
    out = tmp_path / "child_off_grid.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_off_grid_gds(tmp_path: Path) -> Path:
    """创建多层含 off-grid 顶点的 GDSII。

    Layer 1 (WG): (0,0)-(0.007,0.005) off-grid
    Layer 5 (METAL): (0,0)-(0.007,0.005) off-grid
    """
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [0.007, 0], [0.007, 0.005]],
                },
                {
                    "layer": 5,
                    "datatype": 0,
                    "points": [[0, 0], [0.007, 0], [0.007, 0.005]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_off_grid.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestCheckGridAlignment: 基本检查
# =============================================================================
class TestCheckGridAlignment:
    """check_grid_alignment 函数测试。"""

    def test_returns_report(self, on_grid_polygon_gds: Path) -> None:
        """返回 GridCheckReport。"""
        report = check_grid_alignment(on_grid_polygon_gds)
        assert isinstance(report, GridCheckReport)
        assert report.file_path == str(on_grid_polygon_gds)
        assert report.top_cell_name == "TOP"
        assert report.dbu == pytest.approx(0.001, abs=1e-9)

    def test_default_grid_5nm(self, on_grid_polygon_gds: Path) -> None:
        """默认 grid_um=0.005μm（5nm），grid_dbu=5。"""
        report = check_grid_alignment(on_grid_polygon_gds)
        assert report.grid_um == pytest.approx(0.005, abs=1e-9)
        assert report.grid_dbu == 5

    def test_on_grid_no_violations(self, on_grid_polygon_gds: Path) -> None:
        """on-grid polygon 无违规。"""
        report = check_grid_alignment(on_grid_polygon_gds)
        assert report.total_violations == 0
        assert report.violations == []

    def test_off_grid_polygon_detected(self, off_grid_polygon_gds: Path) -> None:
        """off-grid polygon 顶点被检测。

        polygon (0,0),(7,0),(7,5),(0,5) dbu，grid_dbu=5
        顶点 (0,0): 0%5=0, 0%5=0 → on
        顶点 (7,0): 7%5=2, 0%5=0 → off (X=2)
        顶点 (7,5): 7%5=2, 5%5=0 → off (X=2)
        顶点 (0,5): 0%5=0, 5%5=0 → on
        预期: 2 个违规
        """
        report = check_grid_alignment(off_grid_polygon_gds)
        assert report.total_violations == 2
        # 所有违规 X 偏移应为 2
        for v in report.violations:
            assert v.x_off_dbu == 2
            assert v.y_off_dbu == 0
            assert v.shape_type == "polygon"

    def test_off_grid_violation_coordinates(
        self, off_grid_polygon_gds: Path
    ) -> None:
        """违规顶点坐标正确（μm）。"""
        report = check_grid_alignment(off_grid_polygon_gds)
        xs_um = sorted(v.x_um for v in report.violations)
        # 7dbu = 0.007μm
        assert xs_um == [pytest.approx(0.007, abs=1e-9)] * 2
        ys_um = sorted(v.y_um for v in report.violations)
        # 0dbu=0μm 和 5dbu=0.005μm
        assert ys_um == [pytest.approx(0.0, abs=1e-9), pytest.approx(0.005, abs=1e-9)]

    def test_on_grid_box_no_violations(self, on_grid_box_gds: Path) -> None:
        """on-grid Box 无违规。"""
        report = check_grid_alignment(on_grid_box_gds)
        assert report.total_violations == 0

    def test_off_grid_box_detected(self, off_grid_box_gds: Path) -> None:
        """off-grid Box 角点被检测。

        Box (0,0)-(7,5) dbu，grid_dbu=5
        角点: (0,0),(7,0),(7,5),(0,5)
        (7,0): 7%5=2 → off
        (7,5): 7%5=2 → off
        预期: 2 个违规，shape_type='box'
        """
        report = check_grid_alignment(off_grid_box_gds)
        assert report.total_violations == 2
        for v in report.violations:
            assert v.shape_type == "box"
            assert v.x_off_dbu == 2

    def test_child_cell_off_grid_detected(
        self, child_cell_off_grid_gds: Path
    ) -> None:
        """子 cell 实例中的 off-grid 顶点被递归检测。

        CHILD polygon (0,0),(7,0),(7,5),(0,5) dbu
        实例 placement (20,0)μm = (20000,0)dbu
        世界坐标顶点: (20000,0),(20007,0),(20007,5),(20000,5)
        20007 % 5 = 2 → off-grid
        预期: 2 个违规，cell_name='CHILD'
        """
        report = check_grid_alignment(child_cell_off_grid_gds)
        assert report.total_violations == 2
        for v in report.violations:
            assert v.cell_name == "CHILD"
            assert v.x_off_dbu == 2
            # 世界坐标 X = 20007dbu = 20.007μm
            assert v.x_um == pytest.approx(20.007, abs=1e-6)

    def test_layers_to_check_filter(
        self, multi_layer_off_grid_gds: Path
    ) -> None:
        """layers_to_check 过滤指定层。

        multi_layer_gds 有 WG(1,0) 和 METAL(5,0) 两层都有 off-grid。
        只检查 WG 时，违规只在 WG 层。
        """
        report = check_grid_alignment(
            multi_layer_off_grid_gds, layers_to_check=["WG"]
        )
        assert report.total_violations == 2
        for v in report.violations:
            assert v.layer_name == "WG"
            assert v.gds_layer == 1

    def test_layers_to_check_metal(
        self, multi_layer_off_grid_gds: Path
    ) -> None:
        """layers_to_check 过滤 METAL 层。"""
        report = check_grid_alignment(
            multi_layer_off_grid_gds, layers_to_check=["METAL"]
        )
        assert report.total_violations == 2
        for v in report.violations:
            assert v.layer_name == "METAL"
            assert v.gds_layer == 5

    def test_grid_um_1nm(self, off_grid_polygon_gds: Path) -> None:
        """grid_um=0.001μm（1nm），原 off-grid 顶点变 on-grid。

        7dbu 顶点，grid_dbu=1，7%1=0 → on-grid
        """
        report = check_grid_alignment(off_grid_polygon_gds, grid_um=0.001)
        assert report.grid_dbu == 1
        assert report.total_violations == 0

    def test_grid_um_10nm(self, off_grid_polygon_gds: Path) -> None:
        """grid_um=0.010μm（10nm），更多顶点 off-grid。

        三角形 (0,0),(7,0),(7,5) dbu，grid_dbu=10:
        (0,0): 0,0 → on
        (7,0): 7%10=7, 0%10=0 → off (X=7)
        (7,5): 7%10=7, 5%10=5 → off (X=7, Y=5)
        预期: 2 个违规
        """
        report = check_grid_alignment(off_grid_polygon_gds, grid_um=0.010)
        assert report.grid_dbu == 10
        assert report.total_violations == 2

    def test_custom_layer_map(self, off_grid_polygon_gds: Path) -> None:
        """自定义 layer_map。"""
        custom_map = {(1, 0): "CUSTOM_WG"}
        report = check_grid_alignment(
            off_grid_polygon_gds, layer_map=custom_map
        )
        assert report.violations[0].layer_name == "CUSTOM_WG"

    def test_unknown_layer_default_name(self, tmp_path: Path) -> None:
        """未映射的层用默认名 LAYER_<layer>_<datatype>。"""
        cells_spec = [
            {
                "name": "TOP",
                "polygons": [
                    {
                        "layer": 99,
                        "datatype": 7,
                        "points": [[0, 0], [0.007, 0], [0.007, 0.005]],
                    },
                ],
                "is_top": True,
            }
        ]
        out = tmp_path / "unknown.gds"
        export_gdsii_from_cells(cells_spec, out)
        report = check_grid_alignment(out)
        assert report.total_violations == 2
        assert report.violations[0].layer_name == "LAYER_99_7"

    def test_total_shapes_checked(self, multi_layer_off_grid_gds: Path) -> None:
        """total_shapes_checked 包含所有检查的 shape。"""
        report = check_grid_alignment(multi_layer_off_grid_gds)
        # 2 个 polygon（WG + METAL）
        assert report.total_shapes_checked == 2

    def test_violations_sorted(self, off_grid_box_gds: Path) -> None:
        """违规按 gds_layer → gds_datatype → y_um → x_um 排序。"""
        report = check_grid_alignment(off_grid_box_gds)
        ys = [v.y_um for v in report.violations]
        assert ys == sorted(ys)

    def test_layer_violation_counts(self, multi_layer_off_grid_gds: Path) -> None:
        """layer_violation_counts 按层名分组。"""
        report = check_grid_alignment(multi_layer_off_grid_gds)
        assert report.layer_violation_counts == {"WG": 2, "METAL": 2}

    def test_top_cell_name_specified(self, on_grid_polygon_gds: Path) -> None:
        """指定 top_cell_name。"""
        report = check_grid_alignment(
            on_grid_polygon_gds, top_cell_name="TOP"
        )
        assert report.top_cell_name == "TOP"


# =============================================================================
# TestGenerateGridCheckReport: 报告生成
# =============================================================================
class TestGenerateGridCheckReport:
    """generate_grid_check_report 函数测试。"""

    def test_text_format_no_violations(self, on_grid_polygon_gds: Path) -> None:
        """text 格式无违规报告。"""
        report = generate_grid_check_report(on_grid_polygon_gds)
        assert isinstance(report, str)
        assert "GDSII 网格对齐检查报告" in report
        assert "违规总数: 0" in report
        assert "TOP" in report

    def test_text_format_with_violations(self, off_grid_polygon_gds: Path) -> None:
        """text 格式含违规报告。"""
        report = generate_grid_check_report(off_grid_polygon_gds)
        assert "违规总数: 2" in report
        assert "WG" in report
        assert "polygon" in report

    def test_markdown_format_no_violations(
        self, on_grid_polygon_gds: Path
    ) -> None:
        """markdown 格式无违规报告。"""
        report = generate_grid_check_report(
            on_grid_polygon_gds, output_format="markdown"
        )
        assert "# GDSII 网格对齐检查报告" in report
        assert "**违规总数**: 0" in report

    def test_markdown_format_with_violations(
        self, off_grid_polygon_gds: Path
    ) -> None:
        """markdown 格式含违规报告。"""
        report = generate_grid_check_report(
            off_grid_polygon_gds, output_format="markdown"
        )
        assert "| WG |" in report
        assert "| polygon |" in report
        assert "0.0070" in report

    def test_markdown_layer_counts(self, multi_layer_off_grid_gds: Path) -> None:
        """markdown 含按层分组计数表。"""
        report = generate_grid_check_report(
            multi_layer_off_grid_gds, output_format="markdown"
        )
        assert "## 按层分组违规计数" in report
        assert "| WG | 2 |" in report
        assert "| METAL | 2 |" in report

    def test_report_contains_grid_info(self, on_grid_polygon_gds: Path) -> None:
        """报告含 grid 信息。"""
        report = generate_grid_check_report(on_grid_polygon_gds)
        assert "grid:" in report
        assert "0.005" in report
        assert "5 dbu" in report

    def test_report_contains_dbu(self, on_grid_polygon_gds: Path) -> None:
        """报告含 dbu 信息。"""
        report = generate_grid_check_report(on_grid_polygon_gds)
        assert "dbu:" in report
        assert "0.001" in report

    def test_unsupported_format_raises(
        self, on_grid_polygon_gds: Path
    ) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_grid_check_report(
                on_grid_polygon_gds, output_format="html"
            )


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试：失败即 raise，禁止静默兜底。"""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        fake = tmp_path / "nonexistent.gds"
        with pytest.raises(FileNotFoundError, match="不存在"):
            check_grid_alignment(fake)

    def test_path_is_directory_raises(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            check_grid_alignment(tmp_path)

    def test_grid_um_zero_raises(self, on_grid_polygon_gds: Path) -> None:
        """grid_um=0 raise ValueError。"""
        with pytest.raises(ValueError, match="grid_um 必须 > 0"):
            check_grid_alignment(on_grid_polygon_gds, grid_um=0.0)

    def test_grid_um_negative_raises(self, on_grid_polygon_gds: Path) -> None:
        """grid_um<0 raise ValueError。"""
        with pytest.raises(ValueError, match="grid_um 必须 > 0"):
            check_grid_alignment(on_grid_polygon_gds, grid_um=-0.005)

    def test_grid_um_smaller_than_dbu_raises(
        self, on_grid_polygon_gds: Path
    ) -> None:
        """grid_um < dbu 导致 grid_dbu<1 raise ValueError。

        dbu=0.001μm，grid_um=0.0005μm → grid_dbu=0（round(0.5)=0）
        """
        with pytest.raises(ValueError, match="grid_dbu"):
            check_grid_alignment(on_grid_polygon_gds, grid_um=0.0005)

    def test_top_cell_name_not_found_raises(
        self, on_grid_polygon_gds: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            check_grid_alignment(
                on_grid_polygon_gds, top_cell_name="NONEXISTENT"
            )

    def test_unsupported_format_raises_value_error(
        self, on_grid_polygon_gds: Path
    ) -> None:
        """不支持格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_grid_check_report(
                on_grid_polygon_gds, output_format="xml"
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试：所有 API 用法可溯源。"""

    def test_module_docstring_has_urls(self) -> None:
        """模块 docstring 含 KLayout 官方文档 URL。"""
        from polaris.verification import gdsii_grid_alignment_checker as mod

        doc = mod.__doc__ or ""
        assert "klayout.org" in doc
        assert "class_Polygon.html" in doc
        assert "class_Box.html" in doc
        assert "class_Shape.html" in doc
        assert "drc_ref" in doc

    def test_all_exported_symbols(self) -> None:
        """__all__ 含 4 个公开符号。"""
        from polaris.verification import gdsii_grid_alignment_checker as mod

        assert set(mod.__all__) == {
            "GridViolation",
            "GridCheckReport",
            "check_grid_alignment",
            "generate_grid_check_report",
        }

    def test_default_grid_um_5nm(self) -> None:
        """默认 grid_um=0.005μm（5nm，SiEPIC 标准）。

        来源: SiEPIC EBeam PDK grid 规则
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        import inspect

        sig = inspect.signature(check_grid_alignment)
        assert sig.parameters["grid_um"].default == 0.005

    def test_default_layer_map_is_siepic(self) -> None:
        """默认 layer_map 为 None 时用 SiEPIC 标准。"""
        import inspect

        sig = inspect.signature(check_grid_alignment)
        assert sig.parameters["layer_map"].default is None

    def test_check_grid_alignment_docstring_has_urls(self) -> None:
        """check_grid_alignment docstring 含 KLayout URL。"""
        doc = check_grid_alignment.__doc__ or ""
        assert "klayout.org" in doc
        assert "drc_ref" in doc
        assert "class_Polygon" in doc

    def test_no_silent_fallback(self) -> None:
        """源码无 silent fall-back（无 except: pass / return None）。"""
        from polaris.verification import gdsii_grid_alignment_checker as mod

        src = open(mod.__file__).read()
        # 禁止 bare except
        assert "except:" not in src
        # 禁止 except Exception 后 return None/[]
        assert "except Exception:\n            return" not in src
        # 禁止 return None / return []
        assert "return None" not in src
        assert "return []" not in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_end_to_end_polygon_check(self, tmp_path: Path) -> None:
        """端到端: 创建 GDSII → 检查 → 报告。"""
        cells_spec = [
            {
                "name": "TOP",
                "polygons": [
                    {
                        "layer": 1,
                        "datatype": 0,
                        "points": [[0, 0], [0.007, 0], [0.007, 0.005]],
                    },
                ],
                "is_top": True,
            }
        ]
        gds = tmp_path / "e2e.gds"
        export_gdsii_from_cells(cells_spec, gds)

        report = check_grid_alignment(gds)
        assert report.total_violations == 2
        text_report = generate_grid_check_report(gds)
        assert "违规总数: 2" in text_report

    def test_end_to_end_box_check(self, tmp_path: Path) -> None:
        """端到端: 创建含 Box 的 GDSII → 检查。"""
        gds = tmp_path / "e2e_box.gds"
        _create_gds_with_box(
            gds,
            [
                {
                    "layer": 1,
                    "datatype": 0,
                    "left": 0,
                    "bottom": 0,
                    "right": 0.007,
                    "top": 0.005,
                }
            ],
        )
        report = check_grid_alignment(gds)
        assert report.total_violations == 2
        assert all(v.shape_type == "box" for v in report.violations)

    def test_transformed_gds_grid_check(self, tmp_path: Path) -> None:
        """与 R324 变换后做网格检查。

        创建 on-grid GDSII → R324 平移 on-grid 距离 → 网格检查应无违规。
        """
        from polaris.verification.gdsii_geometry_transformer import (
            TransformParams,
            transform_gdsii_geometry,
        )

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
        src_gds = tmp_path / "src.gds"
        export_gdsii_from_cells(cells_spec, src_gds)

        out_gds = tmp_path / "out.gds"
        # 平移 100μm = 100000dbu，100000%5=0 → on-grid
        transform_gdsii_geometry(
            src_gds,
            out_gds,
            params=TransformParams(translate_x_um=100.0, translate_y_um=50.0),
        )
        report = check_grid_alignment(out_gds)
        assert report.total_violations == 0

    def test_full_report_round_trip(self, off_grid_polygon_gds: Path) -> None:
        """完整报告往返: check → text → markdown。"""
        report = check_grid_alignment(off_grid_polygon_gds)
        assert report.total_violations == 2

        text = generate_grid_check_report(off_grid_polygon_gds, output_format="text")
        md = generate_grid_check_report(
            off_grid_polygon_gds, output_format="markdown"
        )
        # 两种格式都含相同违规数
        assert "违规总数: 2" in text
        assert "**违规总数**: 2" in md


# =============================================================================
# TestDataclassTest: 数据类
# =============================================================================
class TestDataclassTest:
    """数据类字段测试。"""

    def test_grid_violation_fields(self) -> None:
        """GridViolation 含所有必要字段。"""
        v = GridViolation(
            layer_name="WG",
            gds_layer=1,
            gds_datatype=0,
            x_um=0.007,
            y_um=0.0,
            x_off_dbu=2,
            y_off_dbu=0,
            cell_name="TOP",
            shape_type="polygon",
        )
        assert v.layer_name == "WG"
        assert v.gds_layer == 1
        assert v.gds_datatype == 0
        assert v.x_um == 0.007
        assert v.y_um == 0.0
        assert v.x_off_dbu == 2
        assert v.y_off_dbu == 0
        assert v.cell_name == "TOP"
        assert v.shape_type == "polygon"

    def test_grid_check_report_fields(self) -> None:
        """GridCheckReport 含所有必要字段。"""
        report = GridCheckReport(
            file_path="/tmp/test.gds",
            dbu=0.001,
            grid_um=0.005,
            grid_dbu=5,
            top_cell_name="TOP",
        )
        assert report.file_path == "/tmp/test.gds"
        assert report.dbu == 0.001
        assert report.grid_um == 0.005
        assert report.grid_dbu == 5
        assert report.top_cell_name == "TOP"
        assert report.violations == []
        assert report.total_violations == 0
        assert report.layer_violation_counts == {}
        assert report.total_shapes_checked == 0

    def test_grid_check_report_defaults(self) -> None:
        """GridCheckReport 默认值。"""
        report = GridCheckReport(file_path="/tmp/test.gds")
        assert report.dbu == 0.0
        assert report.grid_um == 0.0
        assert report.grid_dbu == 1
        assert report.top_cell_name == ""
        assert report.violations == []
        assert report.total_violations == 0
        assert report.layer_violation_counts == {}
        assert report.total_shapes_checked == 0

    def test_grid_violation_mutable(self) -> None:
        """GridViolation 是可变数据类。"""
        v = GridViolation(
            layer_name="WG",
            gds_layer=1,
            gds_datatype=0,
            x_um=0.0,
            y_um=0.0,
            x_off_dbu=0,
            y_off_dbu=0,
            cell_name="TOP",
            shape_type="polygon",
        )
        v.x_off_dbu = 3
        v.cell_name = "CHILD"
        assert v.x_off_dbu == 3
        assert v.cell_name == "CHILD"
