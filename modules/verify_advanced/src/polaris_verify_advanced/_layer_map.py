"""GDS Layer Map 内化模块（从 polaris.pdk.layer_map 迁移，消除旧包依赖）。

借鉴开源 PDK 的真实 GDS layer 编号，使子模块独立于 polaris.pdk 重依赖链。

来源（均为 MIT 许可证，与 PoLaRIS 兼容）：
- SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- ubcpdk (MIT, gdsfactory): https://github.com/gdsfactory/ubc/blob/main/ubcpdk/tech.py
- gdsfactory generic_pdk (MIT, PsiQuantum):
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/gpdk/layer_map.py
- SiEPIC OpenEBL layer table: https://github.com/SiEPIC/openEBL-2024-10
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/9781107083456

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GDSLayer:
    """GDS 层定义（layer number + datatype + 语义）。"""

    layer: int
    datatype: int
    name: str
    purpose: str
    fabricated: bool = True


POLARIS_GDS_LAYER_MAP: dict[str, GDSLayer] = {
    "WG": GDSLayer(1, 0, "WG", "220nm Silicon core 波导"),
    "SLAB150": GDSLayer(2, 0, "SLAB150", "150nm Si slab"),
    "SLAB90": GDSLayer(3, 0, "SLAB90", "90nm Si slab"),
    "DEEPTRENCH": GDSLayer(4, 0, "DEEPTRENCH", "深刻蚀沟槽"),
    "GE": GDSLayer(5, 0, "GE", "锗（探测器）"),
    "UNDERCUT": GDSLayer(6, 0, "UNDERCUT", "悬空 undercut"),
    "WGN": GDSLayer(34, 0, "WGN", "SiN 波导"),
    "WGN_CLAD": GDSLayer(36, 0, "WGN_CLAD", "SiN 包层"),
    "N": GDSLayer(20, 0, "N", "N 掺杂"),
    "P": GDSLayer(21, 0, "P", "P 掺杂"),
    "NP": GDSLayer(22, 0, "NP", "N+ 掺杂"),
    "PP": GDSLayer(23, 0, "PP", "P+ 掺杂"),
    "NPP": GDSLayer(24, 0, "NPP", "N++ 掺杂"),
    "PPP": GDSLayer(25, 0, "PPP", "P++ 掺杂"),
    "M1_HEATER": GDSLayer(11, 0, "M1_HEATER", "加热器金属"),
    "M2_ROUTER": GDSLayer(12, 0, "M2_ROUTER", "金属 2 布线"),
    "PAD_OPEN": GDSLayer(13, 0, "PAD_OPEN", "焊盘开口"),
    "HEATER": GDSLayer(47, 0, "HEATER", "加热电阻"),
    "M1": GDSLayer(41, 0, "M1", "金属 1"),
    "M2": GDSLayer(45, 0, "M2", "金属 2"),
    "M3": GDSLayer(49, 0, "M3", "金属 3 / 顶层"),
    "VIAC": GDSLayer(40, 0, "VIAC", "Via 接触孔"),
    "VIA1": GDSLayer(44, 0, "VIA1", "Via1"),
    "VIA2": GDSLayer(43, 0, "VIA2", "Via2"),
    "PORT": GDSLayer(1, 10, "PORT", "PinRec 光学端口", fabricated=False),
    "PORTE": GDSLayer(1, 11, "PORTE", "PinRecM 电气端口", fabricated=False),
    "PIN": GDSLayer(69, 0, "PIN", "SiEPIC pin 标记层", fabricated=False),
    "WAVEGUIDE_PATH": GDSLayer(1, 99, "WAVEGUIDE_PATH", "波导引导形状", fabricated=False),
    "DEVREC": GDSLayer(68, 0, "DEVREC", "器件识别层", fabricated=False),
    "TEXT": GDSLayer(10, 0, "TEXT", "文本标注", fabricated=False),
    "FLOORPLAN": GDSLayer(99, 0, "FLOORPLAN", "版图设计区域", fabricated=False),
    "PADDING": GDSLayer(67, 0, "PADDING", "padding", fabricated=False),
    "DICING": GDSLayer(100, 0, "DICING", "切割道"),
    "SHOW_PORTS": GDSLayer(1, 12, "SHOW_PORTS", "端口可视化", fabricated=False),
    "LABEL_INSTANCE": GDSLayer(206, 0, "LABEL_INSTANCE", "实例标签", fabricated=False),
    "LABEL_SETTINGS": GDSLayer(202, 0, "LABEL_SETTINGS", "设置标签", fabricated=False),
    "TE": GDSLayer(203, 0, "TE", "TE 模式标签", fabricated=False),
    "TM": GDSLayer(204, 0, "TM", "TM 模式标签", fabricated=False),
    "DRC_MARKER": GDSLayer(205, 0, "DRC_MARKER", "DRC 标记", fabricated=False),
    "SOURCE": GDSLayer(110, 0, "SOURCE", "光源标记", fabricated=False),
    "MONITOR": GDSLayer(101, 0, "MONITOR", "监视器标记", fabricated=False),
    "WAFER": GDSLayer(999, 0, "WAFER", "wafer 标记", fabricated=False),
}

POLARIS_CATEGORY_LAYER_MAP: dict[str, str] = {
    "passive": "WG",
    "active": "WG",
    "source": "SOURCE",
    "detector": "GE",
    "waveguide": "WG",
    "port": "PORT",
    "devrec": "DEVREC",
    "text": "TEXT",
    "floorplan": "FLOORPLAN",
}


def get_layer_tuple(name: str) -> tuple[int, int]:
    """按名称获取 GDS (layer, datatype) 元组。

    Raises:
        KeyError: 名称不在 POLARIS_GDS_LAYER_MAP 中时。
    """
    gl = POLARIS_GDS_LAYER_MAP[name]
    return (gl.layer, gl.datatype)


def get_category_layer_tuple(category: str) -> tuple[int, int]:
    """按器件类别获取 GDS (layer, datatype) 元组。"""
    name = POLARIS_CATEGORY_LAYER_MAP.get(category, "WG")
    return get_layer_tuple(name)


__all__ = [
    "GDSLayer",
    "POLARIS_CATEGORY_LAYER_MAP",
    "POLARIS_GDS_LAYER_MAP",
    "get_category_layer_tuple",
    "get_layer_tuple",
]
