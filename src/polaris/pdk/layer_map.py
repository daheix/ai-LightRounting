"""GDS Layer Map —— 真实 foundry 工艺层映射（止血7）。

借鉴开源 PDK 的真实 GDS layer 编号，替代 ``layout_render.py`` 中的占位符
``layer(1,0)/layer(2,0)/...``，使 PoLaRIS 导出的 GDS 文件与主流 foundry
PDK 兼容，支持 netlist 提取与 DRC 验证。

来源（均为 MIT 许可证，与 PoLaRIS 兼容）：
- SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- ubcpdk (MIT, gdsfactory): https://github.com/gdsfactory/ubc/blob/main/ubcpdk/tech.py
- gdsfactory generic_pdk (MIT, PsiQuantum):
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/gpdk/layer_map.py
- SiEPIC OpenEBL layer table: https://github.com/SiEPIC/openEBL-2024-10
- 教科书: Chrostowski & Hochberg, "Silicon Photonics Design",
  Cambridge University Press 2015, p.353

约定 (layer_number, datatype)：
- datatype=0: 物理流片层 / 标准 virtual 层
- datatype=10: PinRec 光学端口（netlist 提取）
- datatype=11: PinRecM 电气端口
- datatype=99: 波导引导形状（仅长度计算，不流片）

学术诚信（规则 18）：
- 所有 layer 编号均来自上述开源仓库的实际源码，禁止编造
- SiEPIC 与 gdsfactory generic_pdk 在 TEXT/FLOORPLAN 编号上有差异，
  本模块采用 SiEPIC 实际流片标准（TEXT=(10,0), FLOORPLAN=(99,0)）


## 补充文献（R02 学术诚信补齐）
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, ISBN 978-1-107-08345-6: https://www.cambridge.org/9781107083456
- gdsfactory 文档: https://gdsfactory.github.io/gdsfactory/
- Matres et al. 2024 GDSFactory paper: https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GDSLayer:
    """GDS 层定义（layer number + datatype + 语义）。

    Attributes:
        layer: GDS layer number（0-255）。
        datatype: GDS datatype（0-255）。
        name: 层名称（如 ``"WG"``）。
        purpose: 用途说明（如 ``"220nm Silicon core 波导"``）。
        fabricated: 是否为物理流片层（True 流片，False 为 virtual 层）。
    """

    layer: int
    datatype: int
    name: str
    purpose: str
    fabricated: bool = True


# PoLaRIS GDS Layer Map（借鉴 SiEPIC EBeam PDK + ubcpdk + gdsfactory generic_pdk）
#
# 所有 layer 编号均来自实际检索的开源仓库源码（见模块 docstring 来源）。
POLARIS_GDS_LAYER_MAP: dict[str, GDSLayer] = {
    # === 物理流片层（SOI 220nm） ===
    "WG": GDSLayer(1, 0, "WG", "220nm Silicon core 波导（passive/active 器件几何）"),
    "SLAB150": GDSLayer(2, 0, "SLAB150", "150nm Si slab（浅刻蚀，grating coupler）"),
    "SLAB90": GDSLayer(3, 0, "SLAB90", "90nm Si slab（调制器）"),
    "DEEPTRENCH": GDSLayer(4, 0, "DEEPTRENCH", "深刻蚀沟槽"),
    "GE": GDSLayer(5, 0, "GE", "锗（探测器）"),
    "UNDERCUT": GDSLayer(6, 0, "UNDERCUT", "悬空 undercut / Oxide open to BOX"),
    # === SiN 平台层 ===
    "WGN": GDSLayer(34, 0, "WGN", "SiN 波导（SiN 平台核心层）"),
    "WGN_CLAD": GDSLayer(36, 0, "WGN_CLAD", "SiN 包层"),
    # === 掺杂层（电光调制器） ===
    "N": GDSLayer(20, 0, "N", "N 掺杂"),
    "P": GDSLayer(21, 0, "P", "P 掺杂"),
    "NP": GDSLayer(22, 0, "NP", "N+ 掺杂"),
    "PP": GDSLayer(23, 0, "PP", "P+ 掺杂"),
    "NPP": GDSLayer(24, 0, "NPP", "N++ 掺杂"),
    "PPP": GDSLayer(25, 0, "PPP", "P++ 掺杂"),
    # === 金属层 ===
    "M1_HEATER": GDSLayer(11, 0, "M1_HEATER", "加热器金属（SiEPIC 风格）"),
    "M2_ROUTER": GDSLayer(12, 0, "M2_ROUTER", "金属 2 布线"),
    "PAD_OPEN": GDSLayer(13, 0, "PAD_OPEN", "焊盘开口"),
    "HEATER": GDSLayer(47, 0, "HEATER", "加热电阻（gdsfactory 风格，备用）"),
    "M1": GDSLayer(41, 0, "M1", "金属 1（gdsfactory 风格，备用）"),
    "M2": GDSLayer(45, 0, "M2", "金属 2（gdsfactory 风格，备用）"),
    "M3": GDSLayer(49, 0, "M3", "金属 3 / 顶层"),
    "VIAC": GDSLayer(40, 0, "VIAC", "Via 接触孔"),
    "VIA1": GDSLayer(44, 0, "VIA1", "Via1"),
    "VIA2": GDSLayer(43, 0, "VIA2", "Via2"),
    # === Virtual 层（netlist/验证/可视化，不流片） ===
    "PORT": GDSLayer(1, 10, "PORT", "PinRec 光学端口（必须，netlist 提取）", fabricated=False),
    "PORTE": GDSLayer(1, 11, "PORTE", "PinRecM 电气端口", fabricated=False),
    # SiEPIC 真实版图验证（RingResonator.gds）：pin Path + pin名 Text 均在 (69,0)
    # 来源: SiEPIC EBeam PDK Examples, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    "PIN": GDSLayer(69, 0, "PIN", "SiEPIC pin 标记层（Path+Text，netlist 提取）", fabricated=False),
    "WAVEGUIDE_PATH": GDSLayer(
        1, 99, "WAVEGUIDE_PATH", "波导引导形状（长度计算）", fabricated=False
    ),
    "DEVREC": GDSLayer(68, 0, "DEVREC", "器件识别层（必须，连接性/验证）", fabricated=False),
    "TEXT": GDSLayer(10, 0, "TEXT", "文本标注（SiEPIC 标准）", fabricated=False),
    "FLOORPLAN": GDSLayer(99, 0, "FLOORPLAN", "版图设计区域（SiEPIC 标准）", fabricated=False),
    "PADDING": GDSLayer(67, 0, "PADDING", "padding", fabricated=False),
    "DICING": GDSLayer(100, 0, "DICING", "切割道（gdsfactory 风格；SiEPIC 用 210）"),
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


# PoLaRIS 器件类别 → GDS layer 映射
# 将 PoLaRIS 的 passive/active/source/detector 类别映射到真实 foundry 层。
# 来源: SiEPIC EBeam PDK + ubcpdk + gdsfactory generic_pdk（见模块 docstring）
POLARIS_CATEGORY_LAYER_MAP: dict[str, str] = {
    "passive": "WG",  # 无源器件（Y分支/MMI/DC）画在 Si 核心层
    "active": "WG",  # 有源器件（调制器）也画在 Si 核心层，掺杂另画
    "source": "SOURCE",  # 光源标记层
    "detector": "GE",  # 探测器画在锗层
    "waveguide": "WG",  # 波导画在 Si 核心层（与器件同层）
    "port": "PORT",  # 端口画在 PinRec 层
    "devrec": "DEVREC",  # 器件识别层
    "text": "TEXT",  # 文本标注层
    "floorplan": "FLOORPLAN",  # 版图区域层
}


def get_layer_tuple(name: str) -> tuple[int, int]:
    """按名称获取 GDS (layer, datatype) 元组。

    Args:
        name: 层名称（如 ``"WG"``/``"PORT"``/``"DEVREC"``）。

    Returns:
        ``(layer_number, datatype)`` 元组。

    Raises:
        KeyError: 名称不在 ``POLARIS_GDS_LAYER_MAP`` 中时。
    """
    gl = POLARIS_GDS_LAYER_MAP[name]
    return (gl.layer, gl.datatype)


def get_category_layer_tuple(category: str) -> tuple[int, int]:
    """按器件类别获取 GDS (layer, datatype) 元组。

    将 PoLaRIS 器件类别（passive/active/source/detector/waveguide/port）
    映射到真实 foundry 层编号。未知类别默认使用 ``WG`` 层。

    Args:
        category: 器件类别（如 ``"passive"``/``"detector"``）。

    Returns:
        ``(layer_number, datatype)`` 元组。
    """
    name = POLARIS_CATEGORY_LAYER_MAP.get(category, "WG")
    return get_layer_tuple(name)


__all__ = [
    "GDSLayer",
    "POLARIS_CATEGORY_LAYER_MAP",
    "POLARIS_GDS_LAYER_MAP",
    "get_category_layer_tuple",
    "get_layer_tuple",
]
