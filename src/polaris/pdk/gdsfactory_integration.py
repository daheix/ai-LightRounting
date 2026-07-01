"""gdsfactory 集成模块（步骤4：生成真实参数化器件 GDS + 第2轮 PDK 桥接）。

gdsfactory 是开源光子芯片设计库（MIT 许可证），含数百个参数化组件。
本模块提供 gdsfactory 集成接口，包括：

1. GDS 文件生成（generate_mzi_gds / generate_ring_resonator_gds / generate_component_gds）
2. PDK 桥接（gdsfactory_to_polaris_device / load_gdsfactory_pdk /
   list_gdsfactory_pdks / register_gdsfactory_pdk）—— 第2轮 P0-3

PDK 桥接使 PoLaRIS 能直接使用 gdsfactory 生态：当前已检测并支持 4 个 PDK
（generic/ubcpdk/gf180/ihp），gdsfactory 上游理论支持 43+ PDK（需用户自行
安装对应 Python 包方可加载）。对标 Lumerical/IPKISS 的 PDK 支持。

注：gdsfactory 8.18.0 锁定 pydantic<2.10，而 pydantic<2.10 的 pydantic-core
无 Python 3.14 wheel，因此在 Python 3.14 环境下 gdsfactory 可能 import 失败。
这是上游版本锁定问题，非项目代码问题。在其他 Python 版本（3.10-3.13）下
gdsfactory 可正常安装使用。

批次 10-B 拆分说明（2026-07-01）:
    原文件 1742 行超过质量门禁（AGENTS.md §8 文件 ≤ 800 行），按 Extract Module
    模式拆分为 5 个子模块，本文件作为瘦壳 re-export 公共符号以保持向后兼容：
    - polaris.pdk.gdsfactory_gds_gen: _HAS_GDSFACTORY / _ORIENTATION_TO_DIRECTION /
      GDS 生成函数 / _orientation_to_direction
    - polaris.pdk.gdsfactory_pdk_loader: DeviceImportConfig / PDK 桥接
    - polaris.pdk.gdsii_importer: GDSII 导入 (R301) + _DEFAULT_LAYER_MAP
    - polaris.pdk.gdsii_exporter: GDSII 导出 + 往返 + cell-based (R302)
    - polaris.pdk.gdsii_layer_map: 层映射 (R303) + LayerMapConfig

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- ubcpdk (MIT): https://github.com/gdsfactory/ubc
- gf180mcu PDK (Apache-2.0): https://github.com/gdsfactory/gf180mcu-pdk
- IHP Open Source PDK (Apache-2.0): https://github.com/IHP-GmbH/IHP-Open-PDK
- 差距分析 P0-3: docs/commercial_gap_analysis.md
"""

from __future__ import annotations

import logging

# 批次 10-B: 从拆分后的子模块 re-export 公共符号（保持向后兼容）。
# 任何外部代码 `from polaris.pdk.gdsfactory_integration import X`
# 仍可直接使用，无需修改 import 路径。
from polaris.pdk.gdsfactory_gds_gen import (
    _HAS_GDSFACTORY,
    _ORIENTATION_TO_DIRECTION,
    _orientation_to_direction,
    generate_component_gds,
    generate_mzi_gds,
    generate_ring_resonator_gds,
    is_available,
    list_available_components,
)
from polaris.pdk.gdsfactory_pdk_loader import (
    DeviceImportConfig,
    gdsfactory_to_polaris_device,
    list_gdsfactory_pdks,
    load_gdsfactory_pdk,
    register_gdsfactory_pdk,
)
from polaris.pdk.gdsii_importer import (
    _DEFAULT_LAYER_MAP,
    _GDSFACTORY_DEFAULT_PORT_LAYER,
    GDSIICellInfo,
    GDSIIImportResult,
    GDSIIInstanceInfo,
    GDSIILayerInfo,
    import_gdsii_from_gdsfactory,
)
from polaris.pdk.gdsii_exporter import (
    GDSIIExportConfig,
    create_gdsii_layout_from_cells,
    export_gdsii_from_cells,
    export_gdsii_from_layout,
    round_trip_gdsii,
)
from polaris.pdk.gdsii_layer_map import (
    LayerMapConfig,
    build_layer_map_config,
    gdsfactory_to_polaris_layer,
    get_gdsfactory_generic_layer_map,
    get_siepic_layer_map,
    load_layer_map_from_yaml,
    merge_layer_maps,
    polaris_to_gdsfactory_layer,
    save_layer_map_to_yaml,
)

logger = logging.getLogger(__name__)

__all__ = [
    # GDS 生成
    "generate_component_gds",
    "generate_mzi_gds",
    "generate_ring_resonator_gds",
    "is_available",
    "list_available_components",
    # PDK 桥接（第2轮 P0-3）
    "DeviceImportConfig",
    "gdsfactory_to_polaris_device",
    "list_gdsfactory_pdks",
    "load_gdsfactory_pdk",
    "register_gdsfactory_pdk",
    # R301: GDSII 读取增强
    "GDSIILayerInfo",
    "GDSIIInstanceInfo",
    "GDSIICellInfo",
    "GDSIIImportResult",
    "import_gdsii_from_gdsfactory",
    # R302: GDSII 写出增强
    "GDSIIExportConfig",
    "create_gdsii_layout_from_cells",
    "export_gdsii_from_cells",
    "export_gdsii_from_layout",
    "round_trip_gdsii",
    # R303: PDK 双向兼容层映射
    "LayerMapConfig",
    "build_layer_map_config",
    "gdsfactory_to_polaris_layer",
    "get_gdsfactory_generic_layer_map",
    "get_siepic_layer_map",
    "load_layer_map_from_yaml",
    "merge_layer_maps",
    "polaris_to_gdsfactory_layer",
    "save_layer_map_to_yaml",
]
