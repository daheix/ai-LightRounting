"""polaris-gds-tools 深度测试（覆盖全部 66 个公开 API）。

测试分层:
1. 数据模型（纯 Python）: Point/Shape/Instance/Cell/LayerInfo/FormatLayout
2. layouts_equal 语义比较
3. 常量与映射: SUPPORTED_FORMATS/OPENACCESS_LAYER_MAP/get_default_layer_map
4. MultiFormatIO 往返: CIF/Gerber/OpenAccess + 错误路径
5. OpenAccessDB 类方法
6. 渲染: RenderOptions/LayoutRender/render_layout/export_oasis
7. 原子写入: atomic_write_text/atomic_write_klayout
8. GDSII 工程化工具（klayout 依赖）: 统计/健康检查/扁平化/裁剪/层操作/
   合并/缩放/层级分析/重命名/布尔/几何变换/sizing/diff/密度/网格/边缘/
   端口/文本/连通性/流片预检/批量流水线/DRC area

R03 合规: klayout 依赖功能用 pytest.importorskip 跳过（不伪造）。
R02 学术诚信: 所有断言基于源码 docstring 公开契约，不臆造行为。

来源（R02 学术诚信，均经 WebSearch 验证可访问）:
- pytest 文档: https://docs.pytest.org/
- KLayout Database API: https://www.klayout.org/doc-qt5/code/
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- OASIS 格式: https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
- Si2 OpenAccess 22.60 API: https://si2.org/openaccess/
- CIF 格式（Mead & Conway 1980）:
  https://en.wikipedia.org/wiki/Caltech_Intermediate_Format
- matplotlib Figure 内存管理: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.close.html
- POSIX rename(2) 原子性:
  https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_gds_tools as pgt
from polaris_gds_tools import (
    OPENACCESS_LAYER_MAP,
    SUPPORTED_FORMATS,
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    MultiFormatIO,
    OpenAccessDB,
    Point,
    RenderOptions,
    Shape,
    atomic_write_text,
    get_default_layer_map,
    layouts_equal,
)


# ---------------------------------------------------------------------------
# 测试辅助：构造 FormatLayout 与 GDSII 文件
# ---------------------------------------------------------------------------
def _make_layout() -> FormatLayout:
    """构造测试用 FormatLayout（含 rect/polygon/path/text/circle 五类原语）。"""
    layers = {
        "WG": LayerInfo(name="WG", number=1, datatype=0),
        "TEXT": LayerInfo(name="TEXT", number=10, datatype=0),
    }
    cell = Cell(
        name="TOP",
        shapes=[
            Shape("rect", "WG", [Point(0.0, 0.0)], width=2.0, height=1.0),
            Shape("polygon", "WG",
                  [Point(0.0, 0.0), Point(2.0, 0.0), Point(2.0, 2.0)]),
            Shape("path", "WG", [Point(0.0, 0.0), Point(3.0, 3.0)], width=0.5),
            Shape("text", "TEXT", [Point(1.0, 1.0)], text="hello"),
            Shape("circle", "WG", [Point(5.0, 5.0)], width=2.0),
        ],
    )
    return FormatLayout(
        name="test", cells=[cell], layers=layers, top_cell="TOP", unit="um",
    )


def _make_simple_layout() -> FormatLayout:
    """构造仅含 rect 的简单 FormatLayout（用于 CIF 等不支持 circle/text 的格式）。"""
    layers = {"WG": LayerInfo(name="WG", number=1, datatype=0)}
    cell = Cell(name="TOP", shapes=[
        Shape("rect", "WG", [Point(0.0, 0.0)], width=10, height=5),
    ])
    return FormatLayout(name="simple", cells=[cell], layers=layers,
                        top_cell="TOP", unit="um")


@pytest.fixture(scope="module")
def klayout_db():
    """klayout.db 模块 fixture（未安装则跳过本模块所有 klayout 依赖测试）。

    用 importorskip("klayout.db") 直接导入子模块（klayout 顶层包不自动暴露 .db）。
    """
    return pytest.importorskip("klayout.db")


@pytest.fixture
def test_gds(tmp_path, klayout_db):
    """创建测试 GDSII 文件（顶层 cell + 1 子 cell + WG 层 box）。

    顶层 cell TOP 含子 cell CHILD 的实例，CHILD 在 WG 层 (1,0) 有 10×10μm box。
    """
    db = klayout_db
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    child = ly.create_cell("CHILD")
    wg = ly.layer(1, 0)
    child.shapes(wg).insert(db.Box(0, 0, 10000, 10000))  # 10×10μm
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(0, 0)))
    # 顶层也加一个 box
    top.shapes(wg).insert(db.Box(0, 0, 5000, 5000))  # 5×5μm
    out = tmp_path / "test.gds"
    ly.write(str(out))
    return out


@pytest.fixture
def two_layer_gds(tmp_path, klayout_db):
    """创建两层 GDSII（WG (1,0) + SLAB150 (2,0) 重叠 box），用于布尔/连通性测试。"""
    db = klayout_db
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    wg = ly.layer(1, 0)
    slab = ly.layer(2, 0)
    top.shapes(wg).insert(db.Box(0, 0, 10000, 10000))
    top.shapes(slab).insert(db.Box(5000, 5000, 15000, 15000))
    out = tmp_path / "two_layer.gds"
    ly.write(str(out))
    return out


# ===========================================================================
# 1. 数据模型（纯 Python）
# ===========================================================================
def test_point_construction():
    """Point 二维点构造与属性。"""
    p = Point(1.5, 2.5)
    assert p.x == 1.5
    assert p.y == 2.5


def test_shape_rect_defaults():
    """Shape rect 默认值（width/height/text/angle 为 0/空）。"""
    s = Shape("rect", "WG", [Point(0.0, 0.0)])
    assert s.shape_type == "rect"
    assert s.layer == "WG"
    assert s.width == 0.0
    assert s.height == 0.0
    assert s.text == ""
    assert s.angle == 0.0
    assert len(s.points) == 1


def test_shape_all_types():
    """Shape 五类原语构造。"""
    types = ["rect", "polygon", "path", "circle", "text"]
    for t in types:
        s = Shape(t, "WG", [Point(0.0, 0.0)], width=1.0, height=2.0,
                  text="t", angle=45.0)
        assert s.shape_type == t
        assert s.width == 1.0
        assert s.height == 2.0


def test_instance_construction():
    """Instance 构造与默认变换参数。"""
    inst = Instance(name="i1", cell_name="CHILD", origin=Point(1.0, 2.0))
    assert inst.name == "i1"
    assert inst.cell_name == "CHILD"
    assert inst.origin.x == 1.0
    assert inst.angle == 0.0
    assert inst.mirror is False
    assert inst.mag == 1.0


def test_cell_default_empty():
    """Cell 默认 shapes/instances 为空列表。"""
    c = Cell(name="TOP")
    assert c.name == "TOP"
    assert c.shapes == []
    assert c.instances == []


def test_layer_info_defaults():
    """LayerInfo 默认 number/datatype/purpose。"""
    li = LayerInfo(name="WG")
    assert li.name == "WG"
    assert li.number == 0
    assert li.datatype == 0
    assert li.purpose == ""


def test_format_layout_defaults():
    """FormatLayout 默认 unit='um'，cells/layers 为空。"""
    fl = FormatLayout(name="x")
    assert fl.name == "x"
    assert fl.cells == []
    assert fl.layers == {}
    assert fl.top_cell == ""
    assert fl.unit == "um"


def test_format_layout_full():
    """FormatLayout 完整构造（含 layers dict）。"""
    layout = _make_layout()
    assert layout.top_cell == "TOP"
    assert len(layout.cells) == 1
    assert len(layout.cells[0].shapes) == 5
    assert layout.layers["WG"].number == 1
    shape_types = {s.shape_type for s in layout.cells[0].shapes}
    assert shape_types == {"rect", "polygon", "path", "text", "circle"}


# ===========================================================================
# 2. layouts_equal 语义比较
# ===========================================================================
def test_layouts_equal_identical():
    """相同 layout 相等。"""
    a = _make_layout()
    b = _make_layout()
    assert layouts_equal(a, b) is True


def test_layouts_equal_different_shape_count():
    """形状数不同 → 不相等。"""
    a = _make_layout()
    b = _make_layout()
    b.cells[0].shapes.pop()
    assert layouts_equal(a, b) is False


def test_layouts_equal_different_layers():
    """层名集合不同 → 不相等。"""
    a = _make_layout()
    b = _make_layout()
    b.layers = {"WG": LayerInfo(name="WG", number=1, datatype=0)}
    assert layouts_equal(a, b) is False


def test_layouts_equal_different_cell_count():
    """cell 数不同 → 不相等。"""
    a = _make_layout()
    b = _make_layout()
    b.cells.append(Cell(name="EXTRA"))
    assert layouts_equal(a, b) is False


# ===========================================================================
# 3. 常量与映射
# ===========================================================================
def test_default_layer_map():
    """SiEPIC 13 层标准映射（R02 溯源 SiEPIC EBeam PDK）。"""
    lm = get_default_layer_map()
    assert len(lm) == 13
    assert lm[(1, 0)] == "WG"
    assert lm[(68, 0)] == "DEVREC"
    assert lm[(69, 0)] == "PIN"
    assert lm[(99, 0)] == "PORT_GEOM"


def test_default_layer_map_immutable_contract():
    """get_default_layer_map 每次返回新 dict（不共享可变状态）。"""
    a = get_default_layer_map()
    b = get_default_layer_map()
    a[(999, 0)] = "HACK"
    assert (999, 0) not in b, "层映射应每次返回独立 dict"


def test_supported_formats_contains_core():
    """SUPPORTED_FORMATS 含 cif/gerber/dxf/openaccess 核心格式。"""
    assert "cif" in SUPPORTED_FORMATS
    assert "gerber" in SUPPORTED_FORMATS
    assert "dxf" in SUPPORTED_FORMATS
    assert "openaccess" in SUPPORTED_FORMATS
    assert SUPPORTED_FORMATS == sorted(set(SUPPORTED_FORMATS))


def test_openaccess_layer_map_contents():
    """OPENACCESS_LAYER_MAP 含 WG/SLAB150/TEXT 等核心层。"""
    assert OPENACCESS_LAYER_MAP["WG"] == (1, 0)
    assert OPENACCESS_LAYER_MAP["SLAB150"] == (2, 0)
    assert OPENACCESS_LAYER_MAP["TEXT"] == (10, 0)
    assert isinstance(OPENACCESS_LAYER_MAP["WG"], tuple)


def test_version_string():
    """__version__ 为 x.y.z 格式。"""
    assert isinstance(pgt.__version__, str)
    parts = pgt.__version__.split(".")
    assert len(parts) >= 3


def test_exports_accessible():
    """__all__ 中所有符号均可在模块上访问（R03 禁止 fall-back）。"""
    missing = [name for name in pgt.__all__ if not hasattr(pgt, name)]
    assert missing == [], f"__all__ 中不可访问的符号: {missing}"


# ===========================================================================
# 4. MultiFormatIO 往返与错误路径
# ===========================================================================
def test_multi_format_cif_roundtrip(tmp_path):
    """CIF write→read 往返（CIF 不支持 circle，用 rect+polygon）。"""
    layers = {"WG": LayerInfo(name="WG", number=1, datatype=0)}
    cell = Cell(name="TOP", shapes=[
        Shape("rect", "WG", [Point(0.0, 0.0)], width=10, height=5),
        Shape("polygon", "WG",
              [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]),
    ])
    layout = FormatLayout(name="cif_test", cells=[cell], layers=layers,
                          top_cell="TOP", unit="centimicron")
    out = tmp_path / "test.cif"
    MultiFormatIO.write(layout, str(out), "cif")
    assert out.exists() and out.stat().st_size > 0
    read_back = MultiFormatIO.read(str(out), "cif")
    assert len(read_back.cells) >= 1
    assert sum(len(c.shapes) for c in read_back.cells) >= 2


def test_multi_format_oa_roundtrip(tmp_path):
    """OpenAccess write→read 往返（保留五类原语）。"""
    layout = _make_layout()
    out = tmp_path / "test.oa"
    MultiFormatIO.write(layout, str(out), "openaccess")
    assert out.exists() and out.stat().st_size > 0
    read_back = MultiFormatIO.read(str(out), "openaccess")
    assert len(read_back.cells) >= 1
    assert sum(len(c.shapes) for c in read_back.cells) >= 5


def test_multi_format_gerber_roundtrip(tmp_path):
    """Gerber write→read 往返（不支持 text，用 rect/path/circle）。"""
    layers = {"WG": LayerInfo(name="WG", number=1, datatype=0)}
    cell = Cell(name="TOP", shapes=[
        Shape("rect", "WG", [Point(0.0, 0.0)], width=2.0, height=1.0),
        Shape("path", "WG", [Point(0.0, 0.0), Point(3.0, 3.0)], width=0.5),
        Shape("circle", "WG", [Point(5.0, 5.0)], width=2.0),
    ])
    layout = FormatLayout(name="gerber_test", cells=[cell], layers=layers,
                          top_cell="TOP", unit="mm")
    out = tmp_path / "test.gbr"
    MultiFormatIO.write(layout, str(out), "gerber")
    assert out.exists() and out.stat().st_size > 0
    read_back = MultiFormatIO.read(str(out), "gerber")
    assert len(read_back.cells) == 1
    assert len(read_back.cells[0].shapes) >= 1


def test_multi_format_dxf_roundtrip(tmp_path):
    """DXF write→read 往返。"""
    layers = {"WG": LayerInfo(name="WG", number=1, datatype=0)}
    cell = Cell(name="TOP", shapes=[
        Shape("rect", "WG", [Point(0.0, 0.0)], width=10, height=5),
    ])
    layout = FormatLayout(name="dxf_test", cells=[cell], layers=layers,
                          top_cell="TOP", unit="um")
    out = tmp_path / "test.dxf"
    MultiFormatIO.write(layout, str(out), "dxf")
    assert out.exists() and out.stat().st_size > 0
    read_back = MultiFormatIO.read(str(out), "dxf")
    assert len(read_back.cells) >= 1


def test_multi_format_unsupported_raises(tmp_path):
    """不支持的格式 raise ValueError（R03 禁止 fall-back）。"""
    layout = _make_simple_layout()
    with pytest.raises(ValueError, match="不支持"):
        MultiFormatIO.write(layout, str(tmp_path / "x.xyz"), "xyz")


def test_multi_format_read_not_found():
    """读取不存在文件 raise FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        MultiFormatIO.read("/nonexistent/path/file.cif", "cif")


def test_multi_format_unsupported_read(tmp_path):
    """读取不支持的格式 raise ValueError。"""
    out = tmp_path / "x.cif"
    out.write_text("DS 1 1 1; 9 WG; B 10 5 0 0; DF; E;")
    with pytest.raises(ValueError, match="不支持"):
        MultiFormatIO.read(str(out), "unknown_fmt")


# ===========================================================================
# 5. OpenAccessDB 类
# ===========================================================================
def test_openaccess_db_layer_number():
    """OpenAccessDB.layer_number 查询层号。"""
    db = OpenAccessDB()
    assert db.layer_number("WG") == (1, 0)
    assert db.layer_number("TEXT") == (10, 0)


def test_openaccess_db_custom_layer_map():
    """OpenAccessDB 支持自定义层映射。"""
    custom = {"FOO": (100, 0)}
    db = OpenAccessDB(layer_map=custom)
    assert db.layer_map == custom
    assert db.layer_number("FOO") == (100, 0)


def test_openaccess_db_layer_number_missing():
    """OpenAccessDB.layer_number 未知层 raise KeyError。"""
    db = OpenAccessDB()
    with pytest.raises(KeyError):
        db.layer_number("NONEXISTENT")


def test_openaccess_unknown_command_raises():
    """OpenAccess 解析未知命令 raise ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="未知命令"):
        OpenAccessDB().read("CELL TOP ;\n  BOGUS 1 2 3 ;\nEND TOP\nEND_OA\n")


# ===========================================================================
# 6. 渲染（RenderOptions/LayoutRender/render_layout/export_oasis）
# ===========================================================================
def test_render_options_defaults():
    """RenderOptions 默认值。"""
    opts = RenderOptions()
    assert opts.title == "PoLaRIS Layout"
    assert opts.save_path is None


def test_render_options_custom():
    """RenderOptions 自定义值。"""
    opts = RenderOptions(title="My Layout", save_path="/tmp/x.png")
    assert opts.title == "My Layout"
    assert opts.save_path == "/tmp/x.png"


def test_render_layout_returns_fig_ax(tmp_path):
    """render_layout 返回 LayoutRender（含 fig/ax）。"""
    pytest.importorskip("matplotlib")
    from polaris_gds_tools import render_layout
    layout = _make_layout()
    result = render_layout(layout)
    assert result.fig is not None
    assert result.ax is not None


def test_render_layout_save_png(tmp_path):
    """render_layout 保存 PNG（savefig 后 close 释放内存）。"""
    pytest.importorskip("matplotlib")
    from polaris_gds_tools import render_layout
    layout = _make_layout()
    out = tmp_path / "layout.png"
    opts = RenderOptions(title="Smoke Test", save_path=str(out))
    render_layout(layout, options=opts)
    assert out.exists(), "PNG 文件未生成"
    assert out.stat().st_size > 0, "PNG 文件为空"


def test_export_oasis(tmp_path, klayout_db):
    """FormatLayout → OASIS 导出（klayout.db，原子写入）。"""
    from polaris_gds_tools import export_oasis
    layout = _make_layout()
    out = tmp_path / "layout.oas"
    result = export_oasis(layout, str(out), dbu=0.001)
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


# ===========================================================================
# 7. 原子写入
# ===========================================================================
def test_atomic_write_text(tmp_path):
    """atomic_write_text 原子写入文本（临时文件 + os.replace）。"""
    out = tmp_path / "atom.txt"
    atomic_write_text("hello world\n你好", str(out))
    assert out.read_text(encoding="utf-8") == "hello world\n你好"


def test_atomic_write_text_overwrite(tmp_path):
    """atomic_write_text 覆盖已存在文件。"""
    out = tmp_path / "atom2.txt"
    out.write_text("old")
    atomic_write_text("new content", str(out))
    assert out.read_text(encoding="utf-8") == "new content"


def test_atomic_write_klayout(tmp_path, klayout_db):
    """atomic_write_klayout 原子写入 GDSII（klayout Layout）。"""
    from polaris_gds_tools import atomic_write_klayout
    db = klayout_db
    ly = db.Layout()
    ly.dbu = 0.001
    ly.create_cell("TOP")
    out = tmp_path / "atom.gds"
    result = atomic_write_klayout(ly, str(out))
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


# ===========================================================================
# 8. GDSII 工程化工具（klayout 依赖）
# ===========================================================================
def test_generate_gdsii_statistics(test_gds):
    """generate_gdsii_statistics 返回 StatisticsReport。"""
    from polaris_gds_tools import generate_gdsii_statistics
    report = generate_gdsii_statistics(str(test_gds))
    assert report.file_path == str(test_gds)
    assert report.file_size_bytes > 0
    assert report.dbu == pytest.approx(0.001)
    assert report.total_cells >= 2  # TOP + CHILD
    assert len(report.top_cell_names) >= 1
    assert report.total_polygons + report.total_boxes > 0


def test_generate_statistics_report_text(test_gds):
    """generate_statistics_report text 格式返回字符串。"""
    from polaris_gds_tools import generate_statistics_report
    txt = generate_statistics_report(str(test_gds), output_format="text")
    assert isinstance(txt, str)
    assert len(txt) > 0


def test_generate_statistics_report_json(test_gds):
    """generate_statistics_report json 格式可被 json.loads 解析。"""
    from polaris_gds_tools import generate_statistics_report
    txt = generate_statistics_report(str(test_gds), output_format="json")
    data = json.loads(txt)
    assert isinstance(data, dict)
    assert "total_cells" in data or "total_polygons" in data


def test_generate_gdsii_statistics_not_found():
    """文件不存在 raise FileNotFoundError（R03）。"""
    from polaris_gds_tools import generate_gdsii_statistics
    with pytest.raises(FileNotFoundError):
        generate_gdsii_statistics("/nonexistent/file.gds")


def test_check_gdsii_health(test_gds):
    """check_gdsii_health 返回 HealthCheckReport。"""
    from polaris_gds_tools import check_gdsii_health
    report = check_gdsii_health(str(test_gds))
    assert hasattr(report, "issues")
    assert hasattr(report, "passed")
    assert hasattr(report, "checks_run")
    assert isinstance(report.passed, bool)


def test_check_gdsii_health_not_found():
    """check_gdsii_health 文件不存在 raise FileNotFoundError。"""
    from polaris_gds_tools import check_gdsii_health
    with pytest.raises(FileNotFoundError):
        check_gdsii_health("/nonexistent/file.gds")


def test_flatten_gdsii(tmp_path, test_gds):
    """flatten_gdsii 扁平化层次结构并写出 GDSII。"""
    from polaris_gds_tools import flatten_gdsii
    out = tmp_path / "flat.gds"
    report = flatten_gdsii(str(test_gds), str(out))
    assert out.exists() and out.stat().st_size > 0
    assert hasattr(report, "input_path")


def test_generate_flatten_report(tmp_path, test_gds):
    """generate_flatten_report 返回报告字符串。"""
    from polaris_gds_tools import generate_flatten_report
    out = tmp_path / "flat2.gds"
    txt = generate_flatten_report(str(test_gds), str(out), output_format="text")
    assert isinstance(txt, str)
    assert len(txt) > 0
    assert out.exists()


def test_clip_gdsii(tmp_path, test_gds):
    """clip_gdsii 裁剪指定矩形区域。"""
    from polaris_gds_tools import clip_gdsii
    out = tmp_path / "clip.gds"
    report = clip_gdsii(str(test_gds), str(out), (0.0, 0.0, 8.0, 8.0))
    assert out.exists() and out.stat().st_size > 0
    assert hasattr(report, "clipped_cell_name")


def test_multi_clip_gdsii(tmp_path, test_gds):
    """multi_clip_gdsii 多区域裁剪返回报告列表。"""
    from polaris_gds_tools import multi_clip_gdsii
    out_dir = tmp_path / "clips"
    out_dir.mkdir()
    reports = multi_clip_gdsii(
        str(test_gds), str(out_dir),
        [(0.0, 0.0, 5.0, 5.0), (0.0, 0.0, 10.0, 10.0)],
    )
    assert isinstance(reports, list)
    assert len(reports) == 2
    # 每个裁剪生成一个 GDS 文件
    gds_files = list(out_dir.glob("*.gds"))
    assert len(gds_files) >= 2


def test_copy_layer(tmp_path, test_gds):
    """copy_layer 复制 WG 层到新层。

    LayerOpReport 实际字段（源码 dataclass）: source_layers/target_layer/
    shapes_moved/layers_before/layers_after（无 source_layer 单数）。
    """
    from polaris_gds_tools import copy_layer
    out = tmp_path / "copied.gds"
    report = copy_layer(str(test_gds), str(out), (1, 0), (200, 0))
    assert out.exists() and out.stat().st_size > 0
    assert hasattr(report, "source_layers")
    assert hasattr(report, "layers_after")


def test_delete_layers(tmp_path, test_gds):
    """delete_layers 删除指定层。

    LayerOpReport 实际字段: source_layers/layers_after（删除后 layers_after 为空）。
    """
    from polaris_gds_tools import delete_layers
    out = tmp_path / "deleted.gds"
    report = delete_layers(str(test_gds), str(out), [(1, 0)])
    assert out.exists() and out.stat().st_size > 0
    assert hasattr(report, "source_layers")
    assert hasattr(report, "layers_after")
    assert report.layers_after == []  # 删除后该层已无


def test_merge_layers(tmp_path, two_layer_gds):
    """merge_layers 合并多层到目标层。"""
    from polaris_gds_tools import merge_layers
    out = tmp_path / "merged.gds"
    report = merge_layers(str(two_layer_gds), str(out),
                          [(1, 0), (2, 0)], (100, 0))
    assert out.exists() and out.stat().st_size > 0


def test_merge_gdsii(tmp_path, test_gds, klayout_db):
    """merge_gdsii 合并多个 GDSII 到单一顶层 cell。

    Layout.read 是追加模式：若两文件含同名 top cell，第二次 read 不会新增顶层
    cell（cell 已存在），源码会 raise ValueError（R03 禁止 fall-back）。
    故必须用一个 top cell 名不同的第二文件作为输入。

    来源: KLayout Layout.read 追加语义
      https://www.klayout.de/doc-qt5/code/class_Layout.html#method15
    """
    from polaris_gds_tools import merge_gdsii
    db = klayout_db
    # 构造第二文件，top cell 名与 test_gds 的 "TOP" 不同
    ly2 = db.Layout()
    ly2.dbu = 0.001
    second_top = ly2.create_cell("SECOND_TOP")
    wg2 = ly2.layer(2, 0)
    second_top.shapes(wg2).insert(db.Box(0, 0, 8000, 8000))
    second_gds = tmp_path / "second.gds"
    ly2.write(str(second_gds))

    out = tmp_path / "merged_top.gds"
    report = merge_gdsii([str(test_gds), str(second_gds)], str(out),
                         top_cell_name="MERGED")
    assert out.exists() and out.stat().st_size > 0
    assert hasattr(report, "input_count") or hasattr(report, "merged_cells")


def test_scale_gdsii(tmp_path, test_gds):
    """scale_gdsii 缩放版图。"""
    from polaris_gds_tools import scale_gdsii
    out = tmp_path / "scaled.gds"
    report = scale_gdsii(str(test_gds), str(out), 2.0)
    assert out.exists() and out.stat().st_size > 0


def test_analyze_cell_hierarchy(test_gds):
    """analyze_cell_hierarchy 返回层级分析报告。"""
    from polaris_gds_tools import analyze_cell_hierarchy
    report = analyze_cell_hierarchy(str(test_gds))
    assert hasattr(report, "total_cells") or hasattr(report, "cells")
    assert hasattr(report, "max_depth") or hasattr(report, "max_hierarchy_depth")


def test_detect_circular_references(test_gds):
    """detect_circular_references 返回循环引用链列表。

    源码签名: detect_circular_references(...) -> list[list[str]]
    每个 list[str] 是一条循环引用链（首尾相同表示闭合环）。
    无循环引用时返回空列表 []。
    来源: gdsii_cell_hierarchy_analyzer.py L365-368
    """
    from polaris_gds_tools import detect_circular_references
    report = detect_circular_references(str(test_gds))
    assert isinstance(report, list)
    # 无循环引用时为空列表
    for chain in report:
        assert isinstance(chain, list)
        assert all(isinstance(name, str) for name in chain)


def test_rename_cells(tmp_path, test_gds):
    """rename_cells 批量重命名 cell。"""
    from polaris_gds_tools import rename_cells
    out = tmp_path / "renamed.gds"
    report = rename_cells(str(test_gds), str(out), {"CHILD": "CHILD_NEW"})
    assert out.exists() and out.stat().st_size > 0


def test_boolean_operation(tmp_path, two_layer_gds):
    """boolean_operation 执行布尔运算（and）。"""
    from polaris_gds_tools import boolean_operation
    out = tmp_path / "bool.gds"
    report = boolean_operation(str(two_layer_gds), str(out), "and",
                               (1, 0), (2, 0), (50, 0))
    assert out.exists() and out.stat().st_size > 0


def test_transform_gdsii_geometry(tmp_path, test_gds):
    """transform_gdsii_geometry 应用几何变换。"""
    from polaris_gds_tools import transform_gdsii_geometry
    out = tmp_path / "transformed.gds"
    report = transform_gdsii_geometry(str(test_gds), str(out))
    assert out.exists() and out.stat().st_size > 0


def test_size_layer(tmp_path, test_gds):
    """size_layer 对层做 sizing。

    源码约束: layer 和 layer_result 不能相同（源码 L242 raise ValueError，R03）。
    必须用不同的源层与结果层（如 (1,0)→(50,0)）。
    """
    from polaris_gds_tools import size_layer
    out = tmp_path / "sized.gds"
    report = size_layer(str(test_gds), str(out), (1, 0), (50, 0),
                        size_x_um=0.5, size_y_um=0.5)
    assert out.exists() and out.stat().st_size > 0


def test_compare_gdsii_files(test_gds):
    """compare_gdsii_files 比较相同文件（无差异）。

    DiffReport 实际字段（源码 dataclass）: is_identical/total_added_area_um2/
    total_removed_area_um2/total_added_count/total_removed_count（无 identical/differences）。
    """
    from polaris_gds_tools import compare_gdsii_files
    report = compare_gdsii_files(str(test_gds), str(test_gds))
    assert hasattr(report, "is_identical")
    assert report.is_identical is True  # 相同文件无差异


def test_generate_diff_report(test_gds):
    """generate_diff_report 返回报告字符串。"""
    from polaris_gds_tools import generate_diff_report
    txt = generate_diff_report(str(test_gds), str(test_gds), output_format="text")
    assert isinstance(txt, str)
    assert len(txt) > 0


def test_compute_layer_density(test_gds):
    """compute_layer_density 返回 DensityReport。"""
    from polaris_gds_tools import compute_layer_density
    report = compute_layer_density(str(test_gds))
    assert hasattr(report, "layer_densities") or hasattr(report, "layers")


def test_compute_density_map(test_gds):
    """compute_density_map 返回 DensityMap（网格密度图）。"""
    from polaris_gds_tools import compute_density_map
    dm = compute_density_map(str(test_gds), "WG", cell_size_um=5.0)
    assert hasattr(dm, "grid") or hasattr(dm, "density_map") or hasattr(dm, "rows")


def test_check_density_rules(test_gds):
    """check_density_rules 返回违规列表。"""
    from polaris_gds_tools import check_density_rules
    violations = check_density_rules(
        str(test_gds), [("WG", "max_density", 0.99)]
    )
    assert isinstance(violations, list)


def test_check_grid_alignment(test_gds):
    """check_grid_alignment 返回 GridCheckReport。

    GridCheckReport 实际字段（源码 dataclass）: grid_um/grid_dbu/top_cell_name/
    violations/total_violations/layer_violation_counts/total_shapes_checked
    （无 misaligned_count/issues）。
    """
    from polaris_gds_tools import check_grid_alignment
    report = check_grid_alignment(str(test_gds), grid_um=0.001)
    assert hasattr(report, "total_violations")
    assert hasattr(report, "violations")
    assert hasattr(report, "total_shapes_checked")


def test_extract_edges(tmp_path, test_gds):
    """extract_edges 从 WG 层提取边缘。

    EdgeExtractionReport 实际字段（源码 dataclass）: input_path/output_path/layer/
    total_edges_before/total_edges_after/sample_edges（无 edges/edge_count）。
    """
    from polaris_gds_tools import extract_edges
    report = extract_edges(str(test_gds), (1, 0))
    assert hasattr(report, "total_edges_before")
    assert hasattr(report, "sample_edges")
    assert isinstance(report.sample_edges, list)


def test_extract_ports(test_gds):
    """extract_ports 提取端口（无 PORT 层应返回空报告）。"""
    from polaris_gds_tools import extract_ports
    report = extract_ports(str(test_gds))
    assert hasattr(report, "ports") or hasattr(report, "port_count")


def test_extract_text_labels(test_gds):
    """extract_text_labels 提取文本标签。"""
    from polaris_gds_tools import extract_text_labels
    report = extract_text_labels(str(test_gds))
    assert hasattr(report, "labels") or hasattr(report, "text_count")


def test_analyze_layer_connectivity(test_gds):
    """analyze_layer_connectivity 分析单层连通性。

    ConnectivityReport 实际字段（源码 dataclass）: top_cell_name/layer_results/
    total_components/total_isolated（无 nets/connected_components）。
    来源: gdsii_connectivity_analyzer.py L134-152
    """
    from polaris_gds_tools import analyze_layer_connectivity
    report = analyze_layer_connectivity(str(test_gds))
    assert hasattr(report, "layer_results")
    assert hasattr(report, "total_components")
    assert isinstance(report.layer_results, list)


def test_analyze_cross_layer_connectivity(two_layer_gds):
    """analyze_cross_layer_connectivity 分析跨层连通性。

    源码签名（必填 layer_pairs）:
      analyze_cross_layer_connectivity(gds_path, layer_pairs, ...) ->
      dict[str, list[set[str]]]
    layer_pairs 是层对连接规则（如 [('WG','SLAB150')] 表示两层通过重叠连通）。
    返回字典 {layer_name: [set_of_component_ids]}，非 report 对象。
    来源: gdsii_connectivity_analyzer.py L374-422
    并查集算法: Tarjan JACM 1975, DOI: 10.1145/321879.321884
    """
    from polaris_gds_tools import analyze_cross_layer_connectivity
    # two_layer_gds 含 WG(1,0) + SLAB150(2,0) 重叠 box，适合跨层连通测试
    report = analyze_cross_layer_connectivity(
        str(two_layer_gds), layer_pairs=[("WG", "SLAB150")]
    )
    assert isinstance(report, dict)
    # 每个值是 list[set[str]]
    for layer_name, components in report.items():
        assert isinstance(layer_name, str)
        assert isinstance(components, list)


def test_list_isolated_polygons(test_gds):
    """list_isolated_polygons 列出孤立多边形。

    源码签名: list_isolated_polygons(...) -> list[ConnectedComponent]
    返回孤立多边形分量列表（非 report 对象）。
    来源: gdsii_connectivity_analyzer.py L551
    """
    from polaris_gds_tools import list_isolated_polygons
    report = list_isolated_polygons(str(test_gds))
    assert isinstance(report, list)
    # 每个元素是 ConnectedComponent（含 component_id/layer_name/area_um2 等字段）
    for comp in report:
        assert hasattr(comp, "component_id")
        assert hasattr(comp, "layer_name")


def test_tapeout_precheck(test_gds):
    """tapeout_precheck 流片前综合预检查。"""
    from polaris_gds_tools import tapeout_precheck
    report = tapeout_precheck(str(test_gds))
    assert hasattr(report, "passed") or hasattr(report, "issues")
    assert hasattr(report, "checks_run")


def test_run_batch_pipeline(test_gds):
    """run_batch_pipeline 批量执行验证流水线。"""
    from polaris_gds_tools import run_batch_pipeline
    report = run_batch_pipeline([str(test_gds)])
    assert hasattr(report, "results") or hasattr(report, "file_results")


def test_check_area(test_gds):
    """check_area 对 WG 层执行最小面积检查。"""
    from polaris_gds_tools import check_area
    report = check_area(str(test_gds), (1, 0), min_area_um2=1.0)
    assert hasattr(report, "violations") or hasattr(report, "violation_count")


def test_check_area_finds_violations(test_gds):
    """check_area 高阈值时报告违规（box 面积 < 阈值）。"""
    from polaris_gds_tools import check_area
    # WG 层 box 最大 100μm²，设阈值 10000 应有违规
    report = check_area(str(test_gds), (1, 0), min_area_um2=10000.0)
    n_viol = (len(report.violations) if hasattr(report, "violations")
              else getattr(report, "violation_count", 0))
    assert n_viol > 0, "高面积阈值应报告违规"
