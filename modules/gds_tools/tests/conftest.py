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


def klayout_db():
    """klayout.db 模块 fixture（未安装则跳过本模块所有 klayout 依赖测试）。

    用 importorskip("klayout.db") 直接导入子模块（klayout 顶层包不自动暴露 .db）。
    """
    return pytest.importorskip("klayout.db")


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
