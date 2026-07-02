"""polaris-gds-tools 子模块 smoke test。

测试覆盖（≥3 个 pytest，R03 禁止 fall-back）:
- test_default_layer_map: SiEPIC 13 层标准映射
- test_data_model: FormatLayout/Cell/Shape 数据模型构造
- test_multi_format_cif_roundtrip: CIF write→read 往返
- test_multi_format_oa_roundtrip: OpenAccess write→read 往返
- test_multi_format_gerber_roundtrip: Gerber write→read 往返
- test_layouts_equal: layouts_equal 语义比较
- test_render_options: RenderOptions 默认值
- test_exports_accessible: __all__ 符号均可访问
- test_export_oasis: FormatLayout → OASIS 导出（klayout）
- test_render_layout_save: render_layout 保存 PNG（matplotlib）

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- KLayout Database API: https://www.klayout.org/doc-qt5/code/
- OASIS 格式: https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard
- matplotlib: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.close.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_gds_tools as pgt
from polaris_gds_tools import (
    Cell,
    FormatLayout,
    LayerInfo,
    MultiFormatIO,
    Point,
    RenderOptions,
    Shape,
    export_oasis,
    get_default_layer_map,
    layouts_equal,
    render_layout,
)


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


# ---------------------------------------------------------------------------
# 基础设施 + 数据模型
# ---------------------------------------------------------------------------
def test_default_layer_map():
    """SiEPIC 13 层标准映射（R02 溯源 SiEPIC EBeam PDK）。"""
    lm = get_default_layer_map()
    assert len(lm) == 13, f"层映射应为 13 层，实际 {len(lm)}"
    assert lm[(1, 0)] == "WG"
    assert lm[(68, 0)] == "DEVREC"
    assert lm[(69, 0)] == "PIN"


def test_data_model():
    """FormatLayout/Cell/Shape 数据模型构造。"""
    layout = _make_layout()
    assert layout.top_cell == "TOP"
    assert len(layout.cells) == 1
    assert len(layout.cells[0].shapes) == 5
    assert layout.layers["WG"].number == 1
    shape_types = {s.shape_type for s in layout.cells[0].shapes}
    assert shape_types == {"rect", "polygon", "path", "text", "circle"}


def test_layouts_equal():
    """layouts_equal 语义比较（相同 True / 不同 False）。"""
    a = _make_layout()
    b = _make_layout()
    assert layouts_equal(a, b) is True
    # 修改 b 的形状数 → 不相等
    b.cells[0].shapes.pop()
    assert layouts_equal(a, b) is False


def test_render_options():
    """RenderOptions 默认值。"""
    opts = RenderOptions()
    assert opts.title == "PoLaRIS Layout"
    assert opts.save_path is None


def test_exports_accessible():
    """__all__ 中所有符号均可在模块上访问（R03 禁止 fall-back）。"""
    missing = [name for name in pgt.__all__ if not hasattr(pgt, name)]
    assert missing == [], f"__all__ 中不可访问的符号: {missing}"


# ---------------------------------------------------------------------------
# 多格式 IO 往返（纯 Python，不依赖 klayout）
# ---------------------------------------------------------------------------
def test_multi_format_cif_roundtrip(tmp_path):
    """CIF write→read 往返（CIF 不支持 mag/circle，用 rect+polygon）。"""
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
    """OpenAccess write→read 往返。"""
    layout = _make_layout()
    out = tmp_path / "test.oa"
    MultiFormatIO.write(layout, str(out), "openaccess")
    assert out.exists() and out.stat().st_size > 0
    read_back = MultiFormatIO.read(str(out), "openaccess")
    assert len(read_back.cells) >= 1
    # OA 往返保留 rect/polygon/path/circle/text 几何
    assert sum(len(c.shapes) for c in read_back.cells) >= 5


def test_multi_format_gerber_roundtrip(tmp_path):
    """Gerber write→read 往返（Gerber 扁平格式，不支持 text，用 rect/path）。"""
    # Gerber 仅支持 rect/polygon/path/circle，不支持 text（R03 正确 raise）
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


# ---------------------------------------------------------------------------
# OASIS 导出 + 版图渲染（依赖 klayout / matplotlib，已声明为运行依赖）
# ---------------------------------------------------------------------------
def test_export_oasis(tmp_path):
    """FormatLayout → OASIS 导出（klayout.db，原子写入）。"""
    layout = _make_layout()
    out = tmp_path / "layout.oas"
    result = export_oasis(layout, str(out), dbu=0.001)
    assert result == str(out)
    assert out.exists(), "OASIS 文件未生成"
    assert out.stat().st_size > 0, "OASIS 文件为空"


def test_render_layout_save(tmp_path):
    """render_layout 保存 PNG（matplotlib，savefig 后 close 释放内存）。"""
    layout = _make_layout()
    out = tmp_path / "layout.png"
    opts = RenderOptions(title="Smoke Test", save_path=str(out))
    result = render_layout(layout, options=opts)
    assert result.fig is not None
    assert result.ax is not None
    assert out.exists(), "PNG 文件未生成"
    assert out.stat().st_size > 0, "PNG 文件为空"
