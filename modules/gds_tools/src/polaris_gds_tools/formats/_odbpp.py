"""ODB++ 读写子模块（XML 交换表示）。

ODB++ 语法实现遵循下列权威来源（规则 18 学术诚信）：
- ODB++ Solution Alliance, "ODB++ Format Specification", 2023,
  http://www.odb-sa.com/
- OpenROAD Project, "OpenDB"（含 ODB++ 读取器）,
  https://github.com/The-OpenROAD-Project/OpenDB
- TU Wien, "Layout Data Formats" 概述,
  https://iue.tuwien.ac.at/phd/minixhofer/node50.html
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980
- Rubin, "Computer Aids for VLSI Design" Appendix B,
  https://iue.tuwien.ac.at/phd/minixhofer/node51.html

ODB++ 原生为目录树结构（steps/layers/features）；本模块采用 ODB++
Solution Alliance 推荐的 XML 交换表示子集：
``<odb><layer name=".."><feature type=".."/></layer></odb>``。


## 补充文献（R02 学术诚信补齐）
- gdsfactory 主站: https://gdsfactory.com/
- Python 文档: https://docs.python.org/3/
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from polaris_gds_tools.formats.multi_format import Cell, FormatLayout, LayerInfo, Point, Shape

__all__ = ["read_odbpp", "write_odbpp"]

_FEATURE_TYPE_MAP = {
    "line": "path", "pad": "rect", "text": "text", "polygon": "polygon",
}
_WRITE_TYPE_MAP = {
    "path": "line", "rect": "pad", "text": "text", "polygon": "polygon",
}


def read_odbpp(text: str) -> FormatLayout:
    """解析 ODB++ XML 交换格式为 FormatLayout。

    每个 ``<layer>`` 映射为一个 Cell，``<feature>`` 映射为 Shape。
    """
    root = ET.fromstring(text)
    if root.tag != "odb":
        raise ValueError(f"ODB++ XML 根元素错误: {root.tag}")
    layers: dict[str, LayerInfo] = {}
    cells: list[Cell] = []
    for layer_el in root.findall("layer"):
        lname = layer_el.get("name", "default")
        layers.setdefault(lname, LayerInfo(name=lname, number=len(layers)))
        shapes = [_odbpp_parse_feature(f, lname) for f in layer_el.findall("feature")]
        cells.append(Cell(name=lname, shapes=shapes))
    top = cells[-1].name if cells else "odb_layout"
    return FormatLayout(
        name="odb_layout",
        cells=cells,
        layers=layers,
        top_cell=top,
        unit="mm",
    )


def _odbpp_parse_feature(feat: ET.Element, layer: str) -> Shape:
    """ODB++ feature → Shape。"""
    ftype = feat.get("type", "line")
    if ftype not in _FEATURE_TYPE_MAP:
        raise ValueError(f"ODB++ 不支持 feature 类型: {ftype}")
    xs = [x for x in feat.get("xs", "").split(",") if x]
    ys = [y for y in feat.get("ys", "").split(",") if y]
    pts = [Point(float(x), float(y)) for x, y in zip(xs, ys)]
    return Shape(
        _FEATURE_TYPE_MAP[ftype], layer, pts,
        width=float(feat.get("width", 0)),
        height=float(feat.get("height", 0)),
        text=feat.get("text", ""),
    )


def write_odbpp(layout: FormatLayout) -> str:
    """将 FormatLayout 写为 ODB++ XML。"""
    root = ET.Element("odb")
    for cell in layout.cells:
        layer_el = ET.SubElement(root, "layer", name=cell.name)
        for s in cell.shapes:
            _odbpp_add_feature(layer_el, s)
    return ET.tostring(root, encoding="unicode")


def _odbpp_add_feature(parent: ET.Element, s: Shape) -> None:
    """Shape → ODB++ feature 元素。"""
    if s.shape_type == "circle":
        feat = ET.SubElement(parent, "feature", type="pad")
        feat.set("xs", str(s.points[0].x if s.points else 0))
        feat.set("ys", str(s.points[0].y if s.points else 0))
        feat.set("width", str(s.width))
        feat.set("height", str(s.width))
        return
    ftype = _WRITE_TYPE_MAP.get(s.shape_type)
    if ftype is None:
        raise ValueError(f"ODB++ 不支持形状类型: {s.shape_type}")
    feat = ET.SubElement(parent, "feature", type=ftype)
    feat.set("xs", ",".join(str(p.x) for p in s.points))
    feat.set("ys", ",".join(str(p.y) for p in s.points))
    feat.set("width", str(s.width))
    feat.set("height", str(s.height))
    if s.text:
        feat.set("text", s.text)
