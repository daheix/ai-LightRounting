"""R302 GDSII 写出增强回归测试。

覆盖 R302 三个测试需求（TR-302.1/2/3）：
- TR-302.1: 导出文件可被 gdsfactory 正确读取
- TR-302.2: 层次结构导出完整
- TR-302.3: 往返导入导出无信息损失

学术依据:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
- gdsfactory GDS 导出: https://gdsfactory.github.io/gdsfactory/
- klayout Database API: https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- klayout Layout.write: https://www.klayout.org/klayout-pypi/overview/instances/

R03 验证: 错误输入必须 raise，禁止 fall-back。
R04 验证: 纯 klayout.db（无 GPU）。
"""

from __future__ import annotations

import os
from pathlib import Path

import klayout.db as db
import pytest

from polaris.pdk.gdsfactory_integration import (
    GDSIIExportConfig,
    create_gdsii_layout_from_cells,
    export_gdsii_from_cells,
    export_gdsii_from_layout,
    import_gdsii_from_gdsfactory,
    round_trip_gdsii,
)


# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def simple_layout() -> db.Layout:
    """简单 Layout：1 cell + 1 polygon。"""
    ly = db.Layout()
    top = ly.create_cell("TOP")
    li = ly.layer(1, 0)
    top.shapes(li).insert(db.Box(0, 0, 10000, 500))
    return ly


@pytest.fixture
def hierarchical_layout() -> db.Layout:
    """层次化 Layout：顶层 + 子 cell + 1 实例。"""
    ly = db.Layout()
    top = ly.create_cell("TOP_MZI")
    child = ly.create_cell("y_branch")
    li_wg = ly.layer(1, 0)
    li_devrec = ly.layer(68, 0)
    child.shapes(li_wg).insert(db.Box(0, 0, 5000, 500))
    child.shapes(li_devrec).insert(db.Text("test", db.Trans(0, 0)))
    top.insert(db.CellInstArray(child.cell_index(), db.Vector(0, 0)))
    top.shapes(li_wg).insert(db.Box(0, 0, 10000, 500))
    return ly


@pytest.fixture
def simple_gds_path(tmp_path, simple_layout) -> Path:
    """简单 GDSII 文件路径（写出 simple_layout）。"""
    gds_path = tmp_path / "simple.gds"
    simple_layout.write(str(gds_path))
    return gds_path


@pytest.fixture
def hierarchical_gds_path(tmp_path, hierarchical_layout) -> Path:
    """层次化 GDSII 文件路径。"""
    gds_path = tmp_path / "hierarchical.gds"
    hierarchical_layout.write(str(gds_path))
    return gds_path


@pytest.fixture
def cells_spec_with_hierarchy() -> list[dict]:
    """层次化 cell 规格列表（含 polygons/texts/instances）。"""
    return [
        {
            "name": "y_branch",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [(0, 0), (5, 0), (5, 1), (0, 1)],
                }
            ],
            "texts": [
                {
                    "layer": 68,
                    "datatype": 0,
                    "string": "Lumerical_INTERCONNECT_component=ebeam_y_1550",
                    "x": 0.0,
                    "y": 0.0,
                }
            ],
        },
        {
            "name": "TOP_MZI",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [(0, 0), (10, 0), (10, 1), (0, 1)],
                }
            ],
            "instances": [
                {
                    "cell_name": "y_branch",
                    "x": 5.0,
                    "y": 0.0,
                    "rotation": 0.0,
                    "mirror": False,
                }
            ],
            "is_top": True,
        },
    ]


# ============================================================================
# TR-302.1: 导出文件可被 gdsfactory 正确读取
# ============================================================================


class TestTR3021GdsfactoryCompatible:
    """TR-302.1: 导出文件可被 gdsfactory 正确读取。"""

    def test_export_creates_valid_gds(self, tmp_path, simple_layout):
        """导出生成有效 GDSII 文件。"""
        out = tmp_path / "out.gds"
        result_path = export_gdsii_from_layout(simple_layout, out)
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 0

    def test_exported_gds_readable_by_klayout(self, tmp_path, simple_layout):
        """导出的 GDS 可被 klayout 重新读取。"""
        out = tmp_path / "out.gds"
        export_gdsii_from_layout(simple_layout, out)
        # 重新读取
        ly2 = db.Layout()
        ly2.read(str(out))
        assert ly2.cells() >= 1

    def test_exported_gds_importable_by_polaris(self, tmp_path, simple_layout):
        """导出的 GDS 可被 import_gdsii_from_gdsfactory 读取。"""
        out = tmp_path / "out.gds"
        export_gdsii_from_layout(simple_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        assert result.n_cells >= 1
        assert result.total_polygons >= 1

    def test_export_returns_path(self, tmp_path, simple_layout):
        """返回的路径与输入一致。"""
        out = tmp_path / "out.gds"
        result_path = export_gdsii_from_layout(simple_layout, out)
        assert result_path == str(out)

    def test_export_default_dbu_is_gdsfactory_compatible(
        self, tmp_path, simple_layout
    ):
        """默认 dbu 与 gdsfactory 一致（0.001μm）。"""
        out = tmp_path / "out.gds"
        export_gdsii_from_layout(simple_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        assert result.dbu_um == pytest.approx(0.001)


# ============================================================================
# TR-302.2: 层次结构导出完整
# ============================================================================


class TestTR3022HierarchyComplete:
    """TR-302.2: 层次结构导出完整。"""

    def test_hierarchical_cells_preserved(self, tmp_path, hierarchical_layout):
        """层次结构中所有 cells 都保留。"""
        out = tmp_path / "hier.gds"
        export_gdsii_from_layout(hierarchical_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        assert result.n_cells == 2

    def test_hierarchical_instances_preserved(
        self, tmp_path, hierarchical_layout
    ):
        """层次结构中的 instances 保留。"""
        out = tmp_path / "hier.gds"
        export_gdsii_from_layout(hierarchical_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        assert result.total_instances == 1

    def test_hierarchical_polygons_preserved(
        self, tmp_path, hierarchical_layout
    ):
        """层次结构中的多边形保留。"""
        out = tmp_path / "hier.gds"
        export_gdsii_from_layout(hierarchical_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        # 顶层 1 + 子 cell 1 = 2
        assert result.total_polygons == 2

    def test_hierarchical_texts_preserved(self, tmp_path, hierarchical_layout):
        """层次结构中的文本保留。"""
        out = tmp_path / "hier.gds"
        export_gdsii_from_layout(hierarchical_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        assert result.total_texts == 1

    def test_top_cell_name_preserved(self, tmp_path, hierarchical_layout):
        """顶层 cell 名保留为 TOP_MZI。"""
        out = tmp_path / "hier.gds"
        export_gdsii_from_layout(hierarchical_layout, out)
        result = import_gdsii_from_gdsfactory(out)
        assert result.top_cell_name == "TOP_MZI"

    def test_create_layout_from_cells_hierarchy(
        self, cells_spec_with_hierarchy
    ):
        """create_gdsii_layout_from_cells 构造层次结构。"""
        ly = create_gdsii_layout_from_cells(cells_spec_with_hierarchy)
        assert ly.cells() == 2
        top_cells = list(ly.each_top_cell())
        assert len(top_cells) == 1
        top_cell = ly.cell(top_cells[0])
        assert top_cell.name == "TOP_MZI"


# ============================================================================
# TR-302.3: 往返导入导出无信息损失
# ============================================================================


class TestTR3023RoundTrip:
    """TR-302.3: 往返导入导出无信息损失。"""

    def test_round_trip_simple(self, tmp_path, simple_gds_path):
        """简单 GDS 往返一致性。"""
        out = tmp_path / "rt_simple.gds"
        original, rt_path = round_trip_gdsii(simple_gds_path, out)
        assert os.path.exists(rt_path)
        assert original.n_cells == 1
        assert original.total_polygons == 1

    def test_round_trip_hierarchical(
        self, tmp_path, hierarchical_gds_path
    ):
        """层次化 GDS 往返一致性。"""
        out = tmp_path / "rt_hier.gds"
        original, rt_path = round_trip_gdsii(hierarchical_gds_path, out)
        assert original.n_cells == 2
        assert original.total_instances == 1
        assert original.total_polygons == 2
        assert original.total_texts == 1

    def test_round_trip_returns_original_result(
        self, tmp_path, simple_gds_path
    ):
        """round_trip 返回原始 GDSIIImportResult。"""
        out = tmp_path / "rt.gds"
        original, _ = round_trip_gdsii(simple_gds_path, out)
        assert original is not None
        assert hasattr(original, "n_cells")
        assert hasattr(original, "total_polygons")

    def test_round_trip_returns_path(self, tmp_path, simple_gds_path):
        """round_trip 返回输出路径。"""
        out = tmp_path / "rt.gds"
        _, rt_path = round_trip_gdsii(simple_gds_path, out)
        assert rt_path == str(out)

    def test_round_trip_no_polygon_loss(self, tmp_path, hierarchical_gds_path):
        """往返无多边形损失（验证 raise 不触发）。"""
        out = tmp_path / "rt.gds"
        # 如果有损失会 raise RuntimeError
        round_trip_gdsii(hierarchical_gds_path, out)

    def test_round_trip_with_custom_layer_map(
        self, tmp_path, simple_gds_path
    ):
        """往返用自定义层映射。"""
        out = tmp_path / "rt.gds"
        custom_map = {(1, 0): "MY_WG"}
        original, _ = round_trip_gdsii(
            simple_gds_path, out, layer_map=custom_map
        )
        assert original is not None


# ============================================================================
# R03: 错误输入处理（禁止 fall-back）
# ============================================================================


class TestR03ErrorHandling:
    """R03: 错误输入必须 raise，禁止 fall-back。"""

    def test_export_empty_layout_raises(self, tmp_path):
        """空 Layout 导出 raise ValueError。"""
        ly = db.Layout()  # 无 cell
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="无 cell"):
            export_gdsii_from_layout(ly, out)

    def test_export_directory_output_raises(self, tmp_path, simple_layout):
        """输出路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="目录不是文件"):
            export_gdsii_from_layout(simple_layout, tmp_path)

    def test_round_trip_nonexistent_input_raises(self, tmp_path):
        """round_trip 不存在输入 raise FileNotFoundError。"""
        nonexistent = tmp_path / "nonexistent.gds"
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError):
            round_trip_gdsii(nonexistent, out)

    def test_create_layout_empty_spec_raises(self):
        """create_layout 空 spec raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            create_gdsii_layout_from_cells([])

    def test_create_layout_missing_name_raises(self):
        """cell spec 缺 name raise ValueError。"""
        with pytest.raises(ValueError, match="name"):
            create_gdsii_layout_from_cells([{"polygons": []}])

    def test_create_layout_duplicate_name_raises(self):
        """重复 cell 名 raise ValueError。"""
        with pytest.raises(ValueError, match="重复"):
            create_gdsii_layout_from_cells(
                [{"name": "X"}, {"name": "X"}]
            )

    def test_create_layout_invalid_polygon_raises(self):
        """多边形点数 < 3 raise ValueError。"""
        with pytest.raises(ValueError, match="点数 < 3"):
            create_gdsii_layout_from_cells(
                [
                    {
                        "name": "X",
                        "polygons": [
                            {
                                "layer": 1,
                                "datatype": 0,
                                "points": [(0, 0), (1, 1)],
                            }
                        ],
                    }
                ]
            )

    def test_create_layout_invalid_path_raises(self):
        """路径点数 < 2 raise ValueError。"""
        with pytest.raises(ValueError, match="点数 < 2"):
            create_gdsii_layout_from_cells(
                [
                    {
                        "name": "X",
                        "paths": [
                            {
                                "layer": 1,
                                "datatype": 0,
                                "points": [(0, 0)],
                                "width": 0.5,
                            }
                        ],
                    }
                ]
            )

    def test_create_layout_invalid_instance_ref_raises(self):
        """实例引用不存在 cell raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            create_gdsii_layout_from_cells(
                [
                    {
                        "name": "TOP",
                        "instances": [
                            {"cell_name": "NONEXISTENT", "x": 0, "y": 0}
                        ],
                    }
                ]
            )

    def test_export_from_cells_propagates_errors(self, tmp_path):
        """export_gdsii_from_cells 传递 create_layout 的错误。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不能为空"):
            export_gdsii_from_cells([], out)


# ============================================================================
# GDSIIExportConfig 数据类测试
# ============================================================================


class TestGDSIIExportConfig:
    """GDSIIExportConfig 默认值测试。"""

    def test_defaults(self):
        """默认配置。"""
        cfg = GDSIIExportConfig()
        assert cfg.top_cell_name == "TOP"
        assert cfg.dbu_um == 0.001
        assert cfg.layer_map is None
        assert cfg.write_context_info is True

    def test_custom_top_cell_name(self):
        """自定义 top_cell_name。"""
        cfg = GDSIIExportConfig(top_cell_name="MY_TOP")
        assert cfg.top_cell_name == "MY_TOP"

    def test_custom_dbu(self):
        """自定义 dbu。"""
        cfg = GDSIIExportConfig(dbu_um=0.0005)
        assert cfg.dbu_um == 0.0005

    def test_custom_layer_map(self):
        """自定义 layer_map。"""
        custom = {(1, 0): "WG"}
        cfg = GDSIIExportConfig(layer_map=custom)
        assert cfg.layer_map == custom


# ============================================================================
# create_gdsii_layout_from_cells 综合测试
# ============================================================================


class TestCreateLayoutFromCells:
    """create_gdsii_layout_from_cells 综合测试。"""

    def test_simple_cell_creation(self):
        """简单 cell 创建。"""
        spec = [
            {
                "name": "TOP",
                "polygons": [
                    {
                        "layer": 1,
                        "datatype": 0,
                        "points": [(0, 0), (10, 0), (10, 1), (0, 1)],
                    }
                ],
            }
        ]
        ly = create_gdsii_layout_from_cells(spec)
        assert ly.cells() == 1
        assert ly.cell(0).name == "TOP"

    def test_polygon_inserted(self):
        """多边形正确插入。"""
        spec = [
            {
                "name": "TOP",
                "polygons": [
                    {
                        "layer": 1,
                        "datatype": 0,
                        "points": [(0, 0), (10, 0), (10, 1), (0, 1)],
                    }
                ],
            }
        ]
        ly = create_gdsii_layout_from_cells(spec)
        li = ly.layer(1, 0)
        top = ly.cell(0)
        n_shapes = sum(1 for _ in top.shapes(li).each())
        assert n_shapes == 1

    def test_text_inserted(self):
        """文本正确插入。"""
        spec = [
            {
                "name": "TOP",
                "texts": [
                    {
                        "layer": 68,
                        "datatype": 0,
                        "string": "hello",
                        "x": 0.0,
                        "y": 0.0,
                    }
                ],
            }
        ]
        ly = create_gdsii_layout_from_cells(spec)
        li = ly.layer(68, 0)
        top = ly.cell(0)
        for shape in top.shapes(li).each():
            assert shape.is_text()
            assert shape.text.string == "hello"
            break

    def test_path_inserted(self):
        """路径正确插入。"""
        spec = [
            {
                "name": "TOP",
                "paths": [
                    {
                        "layer": 1,
                        "datatype": 0,
                        "points": [(0, 0), (10, 0)],
                        "width": 0.5,
                    }
                ],
            }
        ]
        ly = create_gdsii_layout_from_cells(spec)
        li = ly.layer(1, 0)
        top = ly.cell(0)
        for shape in top.shapes(li).each():
            assert shape.is_path()
            break

    def test_instance_inserted(self, cells_spec_with_hierarchy):
        """实例正确插入。"""
        ly = create_gdsii_layout_from_cells(cells_spec_with_hierarchy)
        top_cell_indices = list(ly.each_top_cell())
        top_cell = ly.cell(top_cell_indices[0])
        n_inst = sum(1 for _ in top_cell.each_inst())
        assert n_inst == 1

    def test_custom_dbu(self):
        """自定义 dbu 应用。"""
        spec = [{"name": "TOP"}]
        ly = create_gdsii_layout_from_cells(spec, dbu_um=0.0005)
        assert ly.dbu == pytest.approx(0.0005)


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """R302 集成测试。"""

    def test_export_then_import_round_trip(
        self, tmp_path, cells_spec_with_hierarchy
    ):
        """cells_spec → export → import 往返。"""
        out = tmp_path / "integration.gds"
        # 导出
        export_gdsii_from_cells(cells_spec_with_hierarchy, out)
        # 导入
        result = import_gdsii_from_gdsfactory(out)
        # 验证
        assert result.n_cells == 2
        assert result.total_instances == 1
        assert result.total_polygons == 2  # 1 + 1
        assert result.total_texts == 1
        assert result.top_cell_name == "TOP_MZI"

    def test_export_from_pdk_package(self, tmp_path, simple_layout):
        """从 polaris.pdk 顶层包可访问 export 函数。"""
        from polaris.pdk import export_gdsii_from_layout

        out = tmp_path / "from_pdk.gds"
        result_path = export_gdsii_from_layout(simple_layout, out)
        assert os.path.exists(result_path)

    def test_round_trip_preserves_layers(self, tmp_path, hierarchical_gds_path):
        """往返保留所有层。"""
        out = tmp_path / "rt.gds"
        original, _ = round_trip_gdsii(hierarchical_gds_path, out)
        # 重新读取输出
        rt_result = import_gdsii_from_gdsfactory(out)
        assert len(rt_result.layers) == len(original.layers)
        original_layer_keys = {
            (l.gds_layer, l.gds_datatype) for l in original.layers
        }
        rt_layer_keys = {
            (l.gds_layer, l.gds_datatype) for l in rt_result.layers
        }
        assert original_layer_keys == rt_layer_keys


# ============================================================================
# 学术诚信: gdsfactory 默认参数溯源
# ============================================================================


class TestAcademicIntegrity:
    """验证 R302 使用的 gdsfactory 默认参数有据可查。"""

    def test_default_dbu_matches_gdsfactory(self):
        """默认 dbu=0.001μm 与 gdsfactory write_gds 默认一致。

        来源: gdsfactory write_gds 默认参数
        https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
        """
        cfg = GDSIIExportConfig()
        assert cfg.dbu_um == 0.001  # gdsfactory 默认 1nm dbu

    def test_default_layer_map_compatible_with_gdsfactory(self):
        """默认层映射与 gdsfactory generic PDK 兼容。

        来源: gdsfactory generic PDK layer definitions
        https://gdsfactory.github.io/gdsfactory/
        """
        from polaris.pdk.gdsfactory_integration import _DEFAULT_LAYER_MAP

        # 验证关键层存在
        assert (1, 0) in _DEFAULT_LAYER_MAP  # WG
        assert (68, 0) in _DEFAULT_LAYER_MAP  # DEVREC (SiEPIC 兼容)
        assert (69, 0) in _DEFAULT_LAYER_MAP  # PIN (SiEPIC 兼容)
        assert _DEFAULT_LAYER_MAP[(1, 0)] == "WG"
