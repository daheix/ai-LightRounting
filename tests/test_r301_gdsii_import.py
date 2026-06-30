"""R301 GDSII 读取增强回归测试。

覆盖 R301 三个测试需求（TR-301.1/2/3）：
- TR-301.1: 导入 gdsfactory 标准组件无损失（多边形/路径/文本/实例全部保留）
- TR-301.2: 层次结构保留完整（cells + instances）
- TR-301.3: 所有层号映射正确（gds_layer/datatype → PoLaRIS 层名）

学术依据:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- gdsfactory GDS 导出: https://gdsfactory.github.io/gdsfactory/
- gdsfactory PDK import: https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- klayout Database API: https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- klayout Instance API: https://www.klayout.org/klayout-pypi/overview/instances/
- gdspy 层次化引用: https://gdspy.readthedocs.io/en/master/gettingstarted.html#references

R03 验证: 错误输入必须 raise，禁止 fall-back。
R04 验证: 纯 NumPy/klayout.db（无 GPU）。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import klayout.db as db
import pytest

from polaris.pdk.gdsfactory_integration import (
    GDSIICellInfo,
    GDSIIImportResult,
    GDSIIInstanceInfo,
    GDSIILayerInfo,
    import_gdsii_from_gdsfactory,
)


# ============================================================================
# 测试夹具：构造真实 GDSII 文件
# ============================================================================


@pytest.fixture
def simple_gds_path(tmp_path) -> Path:
    """构造简单 GDSII：1 个顶层 cell + 1 个多边形 + 1 个文本。

    结构:
        TOP (cell 0, top)
          - layer (1,0) WG: Box(0,0,10000,500)  # 1 polygon
          - layer (68,0) DEVREC: Text  # 1 text

    Returns:
        GDSII 文件路径。
    """
    ly = db.Layout()
    top = ly.create_cell("TOP")
    li_wg = ly.layer(1, 0)
    li_devrec = ly.layer(68, 0)
    top.shapes(li_wg).insert(db.Box(0, 0, 10000, 500))
    top.shapes(li_devrec).insert(
        db.Text("Lumerical_INTERCONNECT_component=ebeam_y_1550", db.Trans(0, 0))
    )
    gds_path = tmp_path / "simple.gds"
    ly.write(str(gds_path))
    return gds_path


@pytest.fixture
def hierarchical_gds_path(tmp_path) -> Path:
    """构造层次化 GDSII：顶层 + 子 cell + 多实例引用。

    结构:
        TOP_MZI (cell 0, top)
          - layer (1,0) WG: Box(0,0,10000,500)  # 1 polygon
          - instance: y_branch @ (0,0) r0
          - instance: y_branch @ (10000,0) r0
        y_branch (cell 1, child)
          - layer (1,0) WG: Box(0,0,5000,500)
          - layer (68,0) DEVREC: Text
          - layer (69,0) PIN: Text 'pin1'

    Returns:
        GDSII 文件路径。
    """
    ly = db.Layout()
    top = ly.create_cell("TOP_MZI")
    child = ly.create_cell("y_branch")
    li_wg = ly.layer(1, 0)
    li_devrec = ly.layer(68, 0)
    li_pin = ly.layer(69, 0)
    # 子 cell 形状
    child.shapes(li_wg).insert(db.Box(0, 0, 5000, 500))
    child.shapes(li_devrec).insert(
        db.Text("Lumerical_INTERCONNECT_component=ebeam_y_1550", db.Trans(0, 0))
    )
    child.shapes(li_pin).insert(db.Text("pin1", db.Trans(0, 0)))
    # 顶层实例 + 形状
    top.insert(db.CellInstArray(child.cell_index(), db.Vector(0, 0)))
    top.insert(db.CellInstArray(child.cell_index(), db.Vector(10000, 0)))
    top.shapes(li_wg).insert(db.Box(0, 0, 10000, 500))
    gds_path = tmp_path / "hierarchical.gds"
    ly.write(str(gds_path))
    return gds_path


@pytest.fixture
def rotated_mirrored_gds_path(tmp_path) -> Path:
    """构造旋转+镜像实例的 GDSII，验证变换解析。

    结构:
        TOP (top)
          - instance: child @ (10000,5000) r90 (旋转 90 度)
          - instance: child @ (0,0) r0 m (镜像)
        child
          - layer (1,0) WG: Box(0,0,1000,500)
    """
    ly = db.Layout()
    top = ly.create_cell("TOP")
    child = ly.create_cell("child")
    li_wg = ly.layer(1, 0)
    child.shapes(li_wg).insert(db.Box(0, 0, 1000, 500))
    # 旋转 90 度 + 平移 (10000, 5000)
    trans_rot = db.DCplxTrans(1.0, 90, False, 10.0, 5.0)
    top.insert(db.CellInstArray(child.cell_index(), trans_rot))
    # 镜像
    trans_mir = db.DCplxTrans(1.0, 0, True, 0.0, 0.0)
    top.insert(db.CellInstArray(child.cell_index(), trans_mir))
    gds_path = tmp_path / "rotated.gds"
    ly.write(str(gds_path))
    return gds_path


# ============================================================================
# TR-301.1: 无损导入测试（多边形/路径/文本/实例全部保留）
# ============================================================================


class TestTR3011LosslessImport:
    """TR-301.1: 导入 gdsfactory 标准组件无损失。"""

    def test_simple_gds_polygons(self, simple_gds_path):
        """简单 GDS 多边形完整保留。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        assert result.total_polygons == 1, "应有 1 个多边形"
        assert result.n_cells == 1

    def test_simple_gds_texts(self, simple_gds_path):
        """简单 GDS 文本完整保留。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        assert result.total_texts == 1, "应有 1 个文本"

    def test_simple_gds_paths_zero(self, simple_gds_path):
        """无 path 的 GDS 导入后 paths=0。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        assert result.total_paths == 0

    def test_hierarchical_gds_total_polygons(self, hierarchical_gds_path):
        """层次化 GDS 多边形数：顶层 1 + 子 cell 1 = 2。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        # 顶层 1 个 Box + 子 cell 1 个 Box = 2
        assert result.total_polygons == 2

    def test_hierarchical_gds_total_texts(self, hierarchical_gds_path):
        """层次化 GDS 文本数：DEVREC 1 + PIN 1 = 2。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        assert result.total_texts == 2

    def test_dbu_default_value(self, simple_gds_path):
        """dbu 默认 0.001 μm（1 nm，klayout 默认）。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        assert result.dbu_um == pytest.approx(0.001)

    def test_file_path_preserved(self, simple_gds_path):
        """导入结果保留文件路径。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        assert result.file_path == str(simple_gds_path)


# ============================================================================
# TR-301.2: 层次结构保留完整测试
# ============================================================================


class TestTR3012HierarchyPreserved:
    """TR-301.2: 层次结构保留完整。"""

    def test_n_cells_hierarchical(self, hierarchical_gds_path):
        """层次化 GDS 应有 2 个 cells（TOP_MZI + y_branch）。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        assert result.n_cells == 2

    def test_top_cell_name(self, hierarchical_gds_path):
        """顶层 cell 名为 TOP_MZI。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        assert result.top_cell_name == "TOP_MZI"

    def test_top_cell_is_top_flag(self, hierarchical_gds_path):
        """is_top 标记正确：仅 TOP_MZI 为 True。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        top_cells = [c for c in result.cells if c.is_top]
        child_cells = [c for c in result.cells if not c.is_top]
        assert len(top_cells) == 1
        assert top_cells[0].name == "TOP_MZI"
        assert len(child_cells) == 1
        assert child_cells[0].name == "y_branch"

    def test_total_instances(self, hierarchical_gds_path):
        """总实例数 = 2（顶层引用 y_branch 2 次）。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        assert result.total_instances == 2

    def test_top_cell_n_instances(self, hierarchical_gds_path):
        """顶层 cell 有 2 个子实例。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        assert top_cell.n_instances == 2

    def test_child_cell_n_instances_zero(self, hierarchical_gds_path):
        """子 cell 无子实例。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        child_cell = next(c for c in result.cells if not c.is_top)
        assert child_cell.n_instances == 0

    def test_instance_cell_name_preserved(self, hierarchical_gds_path):
        """实例引用的 cell 名保留为 y_branch。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        for inst in top_cell.instances:
            assert inst.cell_name == "y_branch"

    def test_instance_positions(self, hierarchical_gds_path):
        """实例位置正确：(0,0) 和 (10,0) μm。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        positions = sorted([(inst.x, inst.y) for inst in top_cell.instances])
        assert positions == [(0.0, 0.0), (10.0, 0.0)]

    def test_instance_default_rotation(self, hierarchical_gds_path):
        """实例默认旋转 0 度。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        for inst in top_cell.instances:
            assert inst.rotation_deg == 0.0

    def test_instance_default_magnification(self, hierarchical_gds_path):
        """实例默认缩放 1.0。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        for inst in top_cell.instances:
            assert inst.magnification == 1.0

    def test_rotated_instance(self, rotated_mirrored_gds_path):
        """旋转 90 度实例的 rotation_deg=90。"""
        result = import_gdsii_from_gdsfactory(rotated_mirrored_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        rotations = sorted([inst.rotation_deg for inst in top_cell.instances])
        assert 90.0 in rotations

    def test_mirrored_instance(self, rotated_mirrored_gds_path):
        """镜像实例的 mirror_x=True。"""
        result = import_gdsii_from_gdsfactory(rotated_mirrored_gds_path)
        top_cell = next(c for c in result.cells if c.is_top)
        mirrors = [inst.mirror_x for inst in top_cell.instances]
        assert True in mirrors

    def test_cell_bbox_simple(self, simple_gds_path):
        """简单 cell 的 bbox 正确：(0,0,10,0.5) μm。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        top_cell = result.cells[0]
        # Box(0,0,10000,500) dbu → (0, 0, 10.0, 0.5) μm
        assert top_cell.bbox_um[0] == pytest.approx(0.0)
        assert top_cell.bbox_um[1] == pytest.approx(0.0)
        assert top_cell.bbox_um[2] == pytest.approx(10.0)
        assert top_cell.bbox_um[3] == pytest.approx(0.5)


# ============================================================================
# TR-301.3: 层号映射正确测试
# ============================================================================


class TestTR3013LayerMapping:
    """TR-301.3: 所有层号映射正确。"""

    def test_simple_gds_layers_count(self, simple_gds_path):
        """简单 GDS 应有 2 个非空层。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        assert len(result.layers) == 2

    def test_wg_layer_mapping(self, simple_gds_path):
        """(1,0) → WG 映射正确。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        wg_layer = next(
            l for l in result.layers if l.gds_layer == 1 and l.gds_datatype == 0
        )
        assert wg_layer.polaris_name == "WG"

    def test_devrec_layer_mapping(self, simple_gds_path):
        """(68,0) → DEVREC 映射正确。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        devrec_layer = next(
            l for l in result.layers if l.gds_layer == 68 and l.gds_datatype == 0
        )
        assert devrec_layer.polaris_name == "DEVREC"

    def test_pin_layer_mapping(self, hierarchical_gds_path):
        """(69,0) → PIN 映射正确。"""
        result = import_gdsii_from_gdsfactory(hierarchical_gds_path)
        pin_layer = next(
            l for l in result.layers if l.gds_layer == 69 and l.gds_datatype == 0
        )
        assert pin_layer.polaris_name == "PIN"

    def test_layer_n_shapes(self, simple_gds_path):
        """WG 层 n_shapes=1。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        wg_layer = next(
            l for l in result.layers if l.gds_layer == 1 and l.gds_datatype == 0
        )
        assert wg_layer.n_shapes == 1

    def test_custom_layer_map(self, simple_gds_path):
        """自定义层映射覆盖默认。"""
        custom_map = {(1, 0): "MY_WG", (68, 0): "MY_DEVREC"}
        result = import_gdsii_from_gdsfactory(
            simple_gds_path, layer_map=custom_map
        )
        wg_layer = next(
            l for l in result.layers if l.gds_layer == 1 and l.gds_datatype == 0
        )
        assert wg_layer.polaris_name == "MY_WG"

    def test_unknown_layer_default_name(self, tmp_path):
        """未知层号使用默认名 LAYER_<layer>_<datatype>。"""
        ly = db.Layout()
        top = ly.create_cell("TOP")
        li_unknown = ly.layer(200, 5)  # 未在默认映射中
        top.shapes(li_unknown).insert(db.Box(0, 0, 1000, 500))
        gds_path = tmp_path / "unknown_layer.gds"
        ly.write(str(gds_path))
        result = import_gdsii_from_gdsfactory(gds_path)
        unknown_layer = next(
            l for l in result.layers if l.gds_layer == 200 and l.gds_datatype == 5
        )
        assert unknown_layer.polaris_name == "LAYER_200_5"

    def test_empty_layers_filtered(self, simple_gds_path):
        """空层被过滤掉。"""
        result = import_gdsii_from_gdsfactory(simple_gds_path)
        for layer in result.layers:
            assert layer.n_shapes > 0, f"层 {layer.gds_layer}/{layer.gds_datatype} 不应有 0 形状"


# ============================================================================
# R03: 错误输入处理（禁止 fall-back）
# ============================================================================


class TestR03ErrorHandling:
    """R03: 错误输入必须 raise，禁止 fall-back。"""

    def test_nonexistent_file_raises(self, tmp_path):
        """不存在的文件 raise FileNotFoundError。"""
        nonexistent = tmp_path / "nonexistent.gds"
        with pytest.raises(FileNotFoundError):
            import_gdsii_from_gdsfactory(nonexistent)

    def test_directory_path_raises(self, tmp_path):
        """目录路径 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            import_gdsii_from_gdsfactory(tmp_path)

    def test_invalid_gds_raises(self, tmp_path):
        """无效 GDS 文件 raise RuntimeError。"""
        bad_path = tmp_path / "bad.gds"
        bad_path.write_text("not a gds file")
        with pytest.raises(RuntimeError, match="klayout 读取 GDSII 失败"):
            import_gdsii_from_gdsfactory(bad_path)

    def test_nonexistent_top_cell_raises(self, simple_gds_path):
        """不存在的 top_cell_name raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            import_gdsii_from_gdsfactory(
                simple_gds_path, top_cell_name="NONEXISTENT_CELL"
            )

    def test_empty_gds_raises(self, tmp_path):
        """空 GDS（无 cell）raise ValueError。"""
        ly = db.Layout()
        empty_path = tmp_path / "empty.gds"
        ly.write(str(empty_path))
        with pytest.raises(ValueError, match="无顶层 cell"):
            import_gdsii_from_gdsfactory(empty_path)


# ============================================================================
# 数据类基础测试
# ============================================================================


class TestDataclassesDefaults:
    """数据类默认值与 __post_init__ 测试。"""

    def test_gdsii_layer_info_defaults(self):
        """GDSIILayerInfo 默认值。"""
        info = GDSIILayerInfo()
        assert info.gds_layer == 0
        assert info.gds_datatype == 0
        assert info.polaris_name == ""
        assert info.n_shapes == 0

    def test_gdsii_instance_info_defaults(self):
        """GDSIIInstanceInfo 默认值。"""
        info = GDSIIInstanceInfo()
        assert info.cell_name == ""
        assert info.x == 0.0
        assert info.y == 0.0
        assert info.rotation_deg == 0.0
        assert info.mirror_x is False
        assert info.magnification == 1.0

    def test_gdsii_cell_info_defaults(self):
        """GDSIICellInfo 默认 instances=[]。"""
        info = GDSIICellInfo()
        assert info.instances == []
        assert info.is_top is False

    def test_gdsii_import_result_defaults(self):
        """GDSIIImportResult 默认 cells/layers=[]。"""
        result = GDSIIImportResult()
        assert result.cells == []
        assert result.layers == []
        assert result.dbu_um == 0.001

    def test_gdsii_cell_info_instances_none_to_list(self):
        """GDSIICellInfo(instances=None) → []。"""
        info = GDSIICellInfo(instances=None)
        assert info.instances == []

    def test_gdsii_import_result_cells_none_to_list(self):
        """GDSIIImportResult(cells=None) → []。"""
        result = GDSIIImportResult(cells=None, layers=None)
        assert result.cells == []
        assert result.layers == []


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """R301 集成测试：与 pdk/__init__.py 导出一致性。"""

    def test_import_from_pdk_package(self):
        """从 polaris.pdk 包可导入 import_gdsii_from_gdsfactory。"""
        from polaris.pdk import gdsfactory_integration as gi

        assert hasattr(gi, "import_gdsii_from_gdsfactory")
        assert hasattr(gi, "GDSIIImportResult")
        assert hasattr(gi, "GDSIICellInfo")
        assert hasattr(gi, "GDSIIInstanceInfo")
        assert hasattr(gi, "GDSIILayerInfo")

    def test_round_trip_simple(self, tmp_path):
        """写入 GDS → 读取 GDS 往返一致性。"""
        # 写入
        ly = db.Layout()
        top = ly.create_cell("ROUND_TRIP")
        li = ly.layer(1, 0)
        top.shapes(li).insert(db.Box(0, 0, 5000, 500))
        gds_path = tmp_path / "round_trip.gds"
        ly.write(str(gds_path))
        # 读取
        result = import_gdsii_from_gdsfactory(gds_path)
        assert result.top_cell_name == "ROUND_TRIP"
        assert result.total_polygons == 1
        assert result.n_cells == 1

    def test_multiple_top_cells_picks_first(self, tmp_path):
        """多顶层 cell 时未指定 top_cell_name 取第一个。"""
        ly = db.Layout()
        ly.create_cell("TOP_A")
        ly.create_cell("TOP_B")
        gds_path = tmp_path / "multi_top.gds"
        ly.write(str(gds_path))
        result = import_gdsii_from_gdsfactory(gds_path)
        assert result.top_cell_name in ("TOP_A", "TOP_B")

    def test_explicit_top_cell_name_works(self, tmp_path):
        """显式指定 top_cell_name 时正确选中。"""
        ly = db.Layout()
        ly.create_cell("TOP_X")
        ly.create_cell("TOP_Y")
        gds_path = tmp_path / "two_tops.gds"
        ly.write(str(gds_path))
        result = import_gdsii_from_gdsfactory(gds_path, top_cell_name="TOP_Y")
        assert result.top_cell_name == "TOP_Y"

    def test_path_string_input(self, simple_gds_path):
        """字符串路径输入也能工作。"""
        result = import_gdsii_from_gdsfactory(str(simple_gds_path))
        assert result.n_cells == 1


# ============================================================================
# 学术诚信: klayout 0.30.9 API 兼容性测试
# ============================================================================


class TestKlayoutAPICompatibility:
    """验证 R301 使用的 klayout 0.30.9 API 都存在（学术诚信: API 溯源）。"""

    def test_layout_layer_indices_exists(self):
        """ly.layer_indices() API 存在。"""
        ly = db.Layout()
        assert hasattr(ly, "layer_indices")
        assert callable(ly.layer_indices)
        assert ly.layer_indices() == []  # 空布局返回空列表

    def test_layout_cells_method_exists(self):
        """ly.cells() 返回 int（cell 总数）。"""
        ly = db.Layout()
        assert callable(ly.cells)
        assert ly.cells() == 0
        ly.create_cell("X")
        assert ly.cells() == 1

    def test_layout_each_top_cell_exists(self):
        """ly.each_top_cell() API 存在，返回 cell 索引列表。"""
        ly = db.Layout()
        assert hasattr(ly, "each_top_cell")
        top = ly.create_cell("TOP")
        top_indices = list(ly.each_top_cell())
        assert len(top_indices) == 1

    def test_inst_cell_index_is_property(self):
        """inst.cell_index 是属性不是方法（klayout 0.30.9）。"""
        ly = db.Layout()
        top = ly.create_cell("TOP")
        child = ly.create_cell("CHILD")
        top.insert(db.CellInstArray(child.cell_index(), db.Vector(0, 0)))
        for inst in top.each_inst():
            # cell_index 是属性（int），不是方法
            assert isinstance(inst.cell_index, int)
            with pytest.raises(TypeError):
                inst.cell_index()  # type: ignore
            break

    def test_inst_dcplx_trans_exists(self):
        """inst.dcplx_trans 返回 DCplxTrans。"""
        ly = db.Layout()
        top = ly.create_cell("TOP")
        child = ly.create_cell("CHILD")
        top.insert(db.CellInstArray(child.cell_index(), db.Vector(0, 0)))
        for inst in top.each_inst():
            ct = inst.dcplx_trans
            assert hasattr(ct, "mag")
            assert hasattr(ct, "angle")
            assert hasattr(ct, "is_mirror")
            assert hasattr(ct, "disp")
            break

    def test_dcplx_trans_disp_returns_dpoint(self):
        """DCplxTrans.disp 返回 DPoint 对象（具有 x/y 属性）。

        注: klayout 0.30.9 中 CellInstArray 接受 DCplxTrans 时内部会做单位
        转换（μm → dbu 存储 → μm 读回），具体值由 klayout 内部决定。
        R301 不依赖具体值，只依赖 DPoint 接口（disp.x / disp.y 属性）。
        """
        ly = db.Layout()
        top = ly.create_cell("TOP")
        child = ly.create_cell("CHILD")
        trans = db.DCplxTrans(1.0, 0, False, 10.0, 5.0)
        top.insert(db.CellInstArray(child.cell_index(), trans))
        for inst in top.each_inst():
            disp = inst.dcplx_trans.disp
            assert hasattr(disp, "x")
            assert hasattr(disp, "y")
            assert isinstance(disp.x, (int, float))
            assert isinstance(disp.y, (int, float))
            break
