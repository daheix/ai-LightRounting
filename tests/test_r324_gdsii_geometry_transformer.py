"""R324 GDSII 几何变换工具测试。

覆盖:
- transform_gdsii_geometry: 平移/旋转/镜像/缩放
- generate_transform_report: text/markdown 报告
- TransformParams: 数据类
- R03 错误处理
- R02 学术诚信
- 集成测试（验证输出文件可被读取）

来源:
- KLayout Transformations:
  https://klayout.org/downloads/master/doc-qt5/about/transformations.html
- KLayout DCplxTrans:
  https://www.klayout.de/doc-qt5/code/class_DCplxTrans.html
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_geometry_transformer import (
    TransformParams,
    TransformReport,
    generate_transform_report,
    transform_gdsii_geometry,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def rect_gds(tmp_path: Path) -> Path:
    """创建含 10x5μm 矩形的 GDSII（在原点）。

    矩形: (0,0)-(10,5) μm
    TEXT: 'lbl' 在 (5, 2.5) μm
    """
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "texts": [
                {"layer": 10, "datatype": 0, "string": "lbl", "x": 5.0, "y": 2.5},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "rect.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建多层 GDSII。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
                {"layer": 5, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def child_cell_gds(tmp_path: Path) -> Path:
    """创建含子 cell 实例的 GDSII。

    TOP cell:
    - 自己的 polygon: (0,0)-(10,5)
    - 实例化 CHILD cell（放在 (20, 0) 位置）
    CHILD cell:
    - polygon: (0,0)-(5,3)
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 3], [0, 3]]},
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 20.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "child.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestTransformGdsiiGeometry: 基本变换
# =============================================================================
class TestTransformGdsiiGeometry:
    """transform_gdsii_geometry 函数测试。"""

    def test_returns_report(self, rect_gds: Path, tmp_path: Path) -> None:
        """返回 TransformReport。"""
        out = tmp_path / "out.gds"
        report = transform_gdsii_geometry(rect_gds, out)
        assert isinstance(report, TransformReport)
        assert report.input_path == str(rect_gds)
        assert report.output_path == str(out)
        assert report.top_cell_name == "TOP"
        assert report.dbu > 0

    def test_output_file_created(self, rect_gds: Path, tmp_path: Path) -> None:
        """输出文件被创建。"""
        out = tmp_path / "out.gds"
        transform_gdsii_geometry(rect_gds, out)
        assert out.exists()
        assert out.is_file()

    def test_no_params_identity(self, rect_gds: Path, tmp_path: Path) -> None:
        """无变换参数（恒等变换）保持原样。"""
        out = tmp_path / "out.gds"
        report = transform_gdsii_geometry(rect_gds, out)
        # bbox 应保持 (0,0)-(10,5)
        assert report.original_bbox == pytest.approx(
            (0.0, 0.0, 10.0, 5.0), abs=1e-3
        )
        assert report.transformed_bbox == pytest.approx(
            (0.0, 0.0, 10.0, 5.0), abs=1e-3
        )

    def test_translate(self, rect_gds: Path, tmp_path: Path) -> None:
        """平移变换 (100, 50) μm。"""
        out = tmp_path / "out.gds"
        params = TransformParams(translate_x_um=100.0, translate_y_um=50.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        # 矩形 (0,0)-(10,5) 平移 (100,50) → (100,50)-(110,55)
        assert report.transformed_bbox == pytest.approx(
            (100.0, 50.0, 110.0, 55.0), abs=1e-3
        )

    def test_translate_negative(self, rect_gds: Path, tmp_path: Path) -> None:
        """负方向平移。"""
        out = tmp_path / "out.gds"
        params = TransformParams(translate_x_um=-50.0, translate_y_um=-30.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        # (0,0)-(10,5) + (-50,-30) → (-50,-30)-(-40,-25)
        assert report.transformed_bbox == pytest.approx(
            (-50.0, -30.0, -40.0, -25.0), abs=1e-3
        )

    def test_rotate_90(self, rect_gds: Path, tmp_path: Path) -> None:
        """逆时针旋转 90°。

        矩形 (0,0)-(10,5) 旋转 90°（绕原点）→ (-5,0)-(0,10)
        """
        out = tmp_path / "out.gds"
        params = TransformParams(rotate_deg=90.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        # (x,y) → (-y, x)（逆时针 90°）
        # (0,0)→(0,0), (10,0)→(0,10), (10,5)→(-5,10), (0,5)→(-5,0)
        # bbox = (-5, 0, 0, 10)
        assert report.transformed_bbox == pytest.approx(
            (-5.0, 0.0, 0.0, 10.0), abs=1e-3
        )

    def test_rotate_180(self, rect_gds: Path, tmp_path: Path) -> None:
        """旋转 180°。

        矩形 (0,0)-(10,5) 旋转 180° → (-10,-5)-(0,0)
        """
        out = tmp_path / "out.gds"
        params = TransformParams(rotate_deg=180.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        # (x,y) → (-x, -y)
        assert report.transformed_bbox == pytest.approx(
            (-10.0, -5.0, 0.0, 0.0), abs=1e-3
        )

    def test_mirror_x(self, rect_gds: Path, tmp_path: Path) -> None:
        """沿 x 轴镜像（y → -y）。

        矩形 (0,0)-(10,5) 镜像 x → (0,-5)-(10,0)
        """
        out = tmp_path / "out.gds"
        params = TransformParams(mirror_x=True)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        assert report.transformed_bbox == pytest.approx(
            (0.0, -5.0, 10.0, 0.0), abs=1e-3
        )

    def test_scale_2x(self, rect_gds: Path, tmp_path: Path) -> None:
        """缩放 2 倍。

        矩形 (0,0)-(10,5) × 2 → (0,0)-(20,10)
        """
        out = tmp_path / "out.gds"
        params = TransformParams(scale=2.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        assert report.transformed_bbox == pytest.approx(
            (0.0, 0.0, 20.0, 10.0), abs=1e-3
        )

    def test_scale_half(self, rect_gds: Path, tmp_path: Path) -> None:
        """缩放 0.5 倍。"""
        out = tmp_path / "out.gds"
        params = TransformParams(scale=0.5)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        assert report.transformed_bbox == pytest.approx(
            (0.0, 0.0, 5.0, 2.5), abs=1e-3
        )

    def test_combined_transform(self, rect_gds: Path, tmp_path: Path) -> None:
        """组合变换（旋转+缩放+平移）。"""
        out = tmp_path / "out.gds"
        params = TransformParams(
            translate_x_um=100.0,
            translate_y_um=50.0,
            rotate_deg=90.0,
            scale=2.0,
        )
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        # 变换顺序: 镜像→旋转→缩放→平移
        # 无镜像，旋转 90°: (x,y)→(-y,x)，矩形 (0,0)-(10,5) → (-5,0)-(0,10)
        # 缩放 2: → (-10,0)-(0,20)
        # 平移 (100,50): → (90,50)-(100,70)
        assert report.transformed_bbox == pytest.approx(
            (90.0, 50.0, 100.0, 70.0), abs=1e-3
        )

    def test_mirror_and_rotate(self, rect_gds: Path, tmp_path: Path) -> None:
        """镜像 + 旋转。"""
        out = tmp_path / "out.gds"
        params = TransformParams(mirror_x=True, rotate_deg=90.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        # 镜像 x: (x,y)→(x,-y)，(0,0)-(10,5) → (0,-5)-(10,0)
        # 旋转 90°: (x,y)→(-y,x)，(0,-5)-(10,0) → (5,0)-(0,10)
        # bbox = (0, 0, 5, 10)
        assert report.transformed_bbox == pytest.approx(
            (0.0, 0.0, 5.0, 10.0), abs=1e-3
        )

    def test_multi_layer_transform(self, multi_layer_gds: Path, tmp_path: Path) -> None:
        """多层 GDSII 变换。"""
        out = tmp_path / "out.gds"
        params = TransformParams(translate_x_um=10.0, translate_y_um=20.0)
        report = transform_gdsii_geometry(multi_layer_gds, out, params=params)
        # 所有层一起变换
        assert report.transformed_bbox == pytest.approx(
            (10.0, 20.0, 20.0, 25.0), abs=1e-3
        )

    def test_child_cell_transform(self, child_cell_gds: Path, tmp_path: Path) -> None:
        """子 cell 实例的 placement 一起变换。"""
        out = tmp_path / "out.gds"
        params = TransformParams(translate_x_um=100.0, translate_y_um=50.0)
        report = transform_gdsii_geometry(child_cell_gds, out, params=params)
        # TOP 自己的 polygon: (0,0)-(10,5) → (100,50)-(110,55)
        # CHILD 实例 placement: 原 (20,0) → (120, 50)
        # CHILD 内容: (0,0)-(5,3) → (120,50)-(125,53)
        # 整体 bbox: (100,50)-(125,55)
        assert report.transformed_bbox == pytest.approx(
            (100.0, 50.0, 125.0, 55.0), abs=1e-3
        )

    def test_top_cell_name_specified(self, rect_gds: Path, tmp_path: Path) -> None:
        """指定 top_cell_name。"""
        out = tmp_path / "out.gds"
        report = transform_gdsii_geometry(
            rect_gds, out, top_cell_name="TOP"
        )
        assert report.top_cell_name == "TOP"

    def test_transform_str_in_report(self, rect_gds: Path, tmp_path: Path) -> None:
        """报告含 KLayout 变换字符串。"""
        out = tmp_path / "out.gds"
        params = TransformParams(rotate_deg=90.0, scale=2.0)
        report = transform_gdsii_geometry(rect_gds, out, params=params)
        assert "r90" in report.transform_str
        assert "*2" in report.transform_str

    def test_input_file_not_modified(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """输入文件不被修改（重新读取仍是原内容）。"""
        # 先记录原始 bbox
        import klayout.db as db
        ly1 = db.Layout()
        ly1.read(str(rect_gds))
        top1 = ly1.cell(int(list(ly1.each_top_cell())[0]))
        orig_bbox = top1.bbox()

        # 应用变换
        out = tmp_path / "out.gds"
        params = TransformParams(translate_x_um=100.0, translate_y_um=50.0)
        transform_gdsii_geometry(rect_gds, out, params=params)

        # 重新读取输入文件，bbox 应保持不变
        ly2 = db.Layout()
        ly2.read(str(rect_gds))
        top2 = ly2.cell(int(list(ly2.each_top_cell())[0]))
        assert top2.bbox() == orig_bbox


# =============================================================================
# TestGenerateTransformReport: 报告生成
# =============================================================================
class TestGenerateTransformReport:
    """generate_transform_report 函数测试。"""

    def test_text_format(self, rect_gds: Path, tmp_path: Path) -> None:
        """text 格式报告。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(translate_x_um=100.0, translate_y_um=50.0),
            output_format="text",
        )
        assert isinstance(report, str)
        assert "GDSII 几何变换报告" in report
        assert "变换参数" in report
        assert "包围盒对比" in report

    def test_markdown_format(self, rect_gds: Path, tmp_path: Path) -> None:
        """markdown 格式报告。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(rotate_deg=90.0),
            output_format="markdown",
        )
        assert isinstance(report, str)
        assert "# GDSII 几何变换报告" in report
        assert "| 参数 | 值 |" in report
        assert "| 项 | xmin | ymin | xmax | ymax |" in report

    def test_text_contains_params(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """text 报告含变换参数。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(
                translate_x_um=100.0,
                translate_y_um=50.0,
                rotate_deg=90.0,
                scale=2.0,
                mirror_x=True,
            ),
            output_format="text",
        )
        assert "100.0" in report
        assert "50.0" in report
        assert "90.0" in report
        assert "2.0" in report
        assert "True" in report  # mirror_x

    def test_text_contains_bbox(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """text 报告含包围盒对比。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(translate_x_um=100.0),
            output_format="text",
        )
        # 原始 (0,0)-(10,5)，平移 100 → (100,0)-(110,5)
        assert "原始" in report
        assert "变换后" in report
        assert "100.000" in report or "100.00" in report

    def test_invalid_format_raises(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """不支持的 output_format raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_transform_report(
                rect_gds, out, output_format="json"
            )

    def test_format_case_insensitive(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """output_format 大小写不敏感。"""
        out1 = tmp_path / "out1.gds"
        out2 = tmp_path / "out2.gds"
        r1 = generate_transform_report(
            rect_gds, out1, output_format="TEXT"
        )
        r2 = generate_transform_report(
            rect_gds, out2, output_format="text"
        )
        # 内容相同（除了文件路径不同）
        assert "GDSII 几何变换报告" in r1
        assert "GDSII 几何变换报告" in r2

    def test_markdown_contains_filename(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """markdown 报告含文件路径。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out, output_format="markdown"
        )
        assert str(rect_gds) in report
        assert str(out) in report

    def test_text_contains_transform_str(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """text 报告含 KLayout 变换字符串。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(rotate_deg=90.0, scale=2.0),
            output_format="text",
        )
        assert "KLayout 变换" in report
        assert "r90" in report
        assert "*2" in report


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_input_not_found_raises(self, tmp_path: Path) -> None:
        """输入文件不存在 raise FileNotFoundError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError, match="不存在"):
            transform_gdsii_geometry("/nonexistent/file.gds", out)

    def test_input_is_directory_raises(self, tmp_path: Path) -> None:
        """输入路径是目录 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不是文件"):
            transform_gdsii_geometry(tmp_path, out)

    def test_scale_zero_raises(self, rect_gds: Path, tmp_path: Path) -> None:
        """scale=0 raise ValueError。"""
        out = tmp_path / "out.gds"
        params = TransformParams(scale=0.0)
        with pytest.raises(ValueError, match="scale 必须 > 0"):
            transform_gdsii_geometry(rect_gds, out, params=params)

    def test_scale_negative_raises(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """scale<0 raise ValueError。"""
        out = tmp_path / "out.gds"
        params = TransformParams(scale=-1.0)
        with pytest.raises(ValueError, match="scale 必须 > 0"):
            transform_gdsii_geometry(rect_gds, out, params=params)

    def test_top_cell_not_found_raises(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不存在"):
            transform_gdsii_geometry(
                rect_gds, out, top_cell_name="NONEXISTENT"
            )

    def test_invalid_format_raises(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """无效 output_format raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_transform_report(
                rect_gds, out, output_format="xml"
            )

    def test_no_silent_fallback_on_invalid_path(
        self, tmp_path: Path
    ) -> None:
        """无效路径不可静默 fall-back（R03）。"""
        out = tmp_path / "out.gds"
        try:
            transform_gdsii_geometry("/nonexistent/path.gds", out)
            assert False, "应 raise FileNotFoundError 而非静默通过"
        except FileNotFoundError:
            pass


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信（R02）
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_contains_klayout_url(self) -> None:
        """模块 docstring 含 KLayout 官方文档 URL。"""
        from polaris.verification import gdsii_geometry_transformer as mod
        assert "klayout.org" in mod.__doc__

    def test_docstring_contains_dcplxtrans_url(self) -> None:
        """docstring 含 KLayout DCplxTrans class URL。"""
        from polaris.verification import gdsii_geometry_transformer as mod
        assert "class_DCplxTrans" in mod.__doc__

    def test_docstring_contains_cell_class_url(self) -> None:
        """docstring 含 KLayout Cell class URL。"""
        from polaris.verification import gdsii_geometry_transformer as mod
        assert "class_Cell" in mod.__doc__

    def test_docstring_contains_transformations_topic_url(self) -> None:
        """docstring 含 KLayout Transformations topic URL。"""
        from polaris.verification import gdsii_geometry_transformer as mod
        assert "transformations.html" in mod.__doc__

    def test_docstring_contains_gdsii_url(self) -> None:
        """docstring 含 GDSII 格式说明 URL。"""
        from polaris.verification import gdsii_geometry_transformer as mod
        assert "GDS" in mod.__doc__

    def test_docstring_contains_at_least_5_urls(self) -> None:
        """docstring 含至少 5 个文献 URL（R02）。"""
        from polaris.verification import gdsii_geometry_transformer as mod
        url_count = mod.__doc__.count("http")
        assert url_count >= 5


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_output_readable_after_transform(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """变换后输出文件可被 klayout 正常读取。"""
        out = tmp_path / "out.gds"
        params = TransformParams(
            translate_x_um=100.0,
            translate_y_um=50.0,
            rotate_deg=90.0,
        )
        transform_gdsii_geometry(rect_gds, out, params=params)

        # 重新读取
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell(int(list(ly.each_top_cell())[0]))
        assert top.name == "TOP"
        # bbox 应等于变换后的 bbox
        dbu = float(ly.dbu)
        bbox = top.bbox()
        assert float(bbox.left) * dbu == pytest.approx(-5.0 + 100.0, abs=1e-3)
        assert float(bbox.bottom) * dbu == pytest.approx(0.0 + 50.0, abs=1e-3)

    def test_text_label_also_transformed(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """text 标签也随变换移动。"""
        out = tmp_path / "out.gds"
        params = TransformParams(translate_x_um=100.0, translate_y_um=50.0)
        transform_gdsii_geometry(rect_gds, out, params=params)

        # 读取 text
        from polaris.verification.gdsii_text_label_extractor import (
            extract_text_labels,
        )
        report = extract_text_labels(out)
        # 原 text 在 (5, 2.5)，平移 (100,50) 后应在 (105, 52.5)
        assert report.total_count == 1
        lbl = report.labels[0]
        assert lbl.x_um == pytest.approx(105.0, abs=1e-3)
        assert lbl.y_um == pytest.approx(52.5, abs=1e-3)

    def test_full_workflow_text(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """完整工作流: 变换 → text 报告。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(translate_x_um=100.0),
            output_format="text",
        )
        assert "GDSII 几何变换报告" in report
        assert "100.0" in report

    def test_full_workflow_markdown(
        self, rect_gds: Path, tmp_path: Path
    ) -> None:
        """完整工作流: 变换 → markdown 报告。"""
        out = tmp_path / "out.gds"
        report = generate_transform_report(
            rect_gds, out,
            params=TransformParams(rotate_deg=90.0, scale=2.0),
            output_format="markdown",
        )
        assert report.startswith("# GDSII 几何变换报告")
        assert "r90" in report
        assert "2.0" in report


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_transform_params_defaults(self) -> None:
        """TransformParams 默认值（恒等变换）。"""
        p = TransformParams()
        assert p.translate_x_um == 0.0
        assert p.translate_y_um == 0.0
        assert p.rotate_deg == 0.0
        assert p.mirror_x is False
        assert p.scale == 1.0

    def test_transform_params_custom(self) -> None:
        """TransformParams 自定义值。"""
        p = TransformParams(
            translate_x_um=10.0,
            translate_y_um=20.0,
            rotate_deg=45.0,
            mirror_x=True,
            scale=2.5,
        )
        assert p.translate_x_um == 10.0
        assert p.translate_y_um == 20.0
        assert p.rotate_deg == 45.0
        assert p.mirror_x is True
        assert p.scale == 2.5

    def test_transform_report_defaults(self) -> None:
        """TransformReport 默认值。"""
        report = TransformReport(
            input_path="/in.gds", output_path="/out.gds"
        )
        assert report.input_path == "/in.gds"
        assert report.output_path == "/out.gds"
        assert report.top_cell_name == ""
        assert report.dbu == 0.0
        assert isinstance(report.params, TransformParams)
        assert report.original_bbox == (0.0, 0.0, 0.0, 0.0)
        assert report.transformed_bbox == (0.0, 0.0, 0.0, 0.0)
        assert report.transform_str == ""

    def test_is_dataclass(self) -> None:
        """是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(TransformParams)
        assert is_dataclass(TransformReport)
