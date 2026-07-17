"""polaris-pdk-advanced — PoLaRIS 高级 PDK 子模块（v5.1.0）。

从 v4 旧包 src/polaris/pdk/ 迁移高级 PDK 功能，作为 polaris-pdk（基础
catalog）的对偶子模块。polaris-pdk 仅含 4 平台 36 器件的纯 dict 目录，
本子模块承载互操作/参数化/配置/管理/版图驱动设计等高级能力。

=== Input / Process / Output 三段式文档 ===

Input:
- gdsfactory PDK 互操作: 48 PDK 注册表、LayerStack/CrossSection 转换、
  .pic.yml YAML 布局解析、PDK 互操作层（注册表+冲突检测+反向转换+版本兼容）
- PCell 多视图参数化: @polaris_cell 装饰器（LRU 缓存+类型校验+命名唯一性）、
  三视图架构（Layout/Circuit/Netlist，Observer Pattern 自动同步）、
  TransformMatrix 仿射/贝塞尔变换引擎、AI 辅助 PCell 代码生成
- YAML PDK 配置: 五段 schema（pdk/layers/layer_stack/cross_sections/cells），
  解析/序列化/校验/构建 PolarisPDK
- 多 PDK 管理: 激活/切换/快照/合并（Active Record + Memento + Composite）
- OptoDesigner 版图驱动: Design Intent（单层→多层掩膜）、PyCell 工厂
  （10 种器件）、Any-angle flexConnector（贝塞尔曲线）、层级化设计（无限嵌套）、
  PDAflow 互操作（SPT 导出）
- 基础数据类: Direction/Port/BoundingBox/Device/Source

Process:
- 互操作层模式（Fowler 2002 PoEAA）+ Registry 模式：gdsfactory 无统一注册表，
  PoLaRIS 提供独立注册表与冲突检测（*创新*）
- Observer Pattern（Gamma 1994）：PCell 三视图自动同步（*创新*）
- 贝塞尔曲线变换引擎（Farin 2002）：gdsfactory 仅支持仿射+欧拉弯曲，
  PoLaRIS 用贝塞尔实现任意曲率（*创新*）
- AI 辅助 PCell 代码生成（PhIDO arXiv:2508.14123）：gdsfactory 无此能力，
  PoLaRIS 用模板生成 PCell 代码（*创新*）
- Design Intent 机制（Synopsys OptoDesigner）：单层中心路径→多层掩膜自动生成
- Memento + Composite Pattern：PDK 快照/恢复与多 PDK 合并

Output:
- 6 个子模块 60+ 公开符号（见下方 __all__）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问，≥5 文献 URL）:
1. gdsfactory (MIT License) — https://gdsfactory.github.io/gdsfactory/
2. Matres et al., "GDSFactory", CLEO 2026 —
   https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
3. Synopsys OptoDesigner —
   https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
4. Synopsys Photonic Solutions Newsletter 2023.12（PyCell + flexConnector）—
   https://www.synopsys.com/photonic-solutions/e-news/2023-december.html
5. Luceda IPKISS（多视图 PCell）—
   https://www.lucedaphotonics.com/en/products/ipkiss
6. Fowler, "Patterns of Enterprise Application Architecture", 2002（互操作层/Active Record）—
   https://martinfowler.com/books/eaa.html
7. Gamma et al., "Design Patterns", 1994（Observer/Memento/Composite）—
   https://en.wikipedia.org/wiki/Design_Patterns
8. Farin, "Curves and Surfaces for CAGD", 5th ed., 2002（贝塞尔曲线 Bernstein 多项式）—
   https://www.elsevier.com/books/curves-and-surfaces-for-cagd/farin/978-0-12-460521-2
9. PDAflow API 标准（光子设计自动化互操作）— http://pdaflow.org/
10. SiEPIC EBeam PDK — https://github.com/SiEPIC/SiEPIC_EBeam_PDK
11. Weste & Harris, "CMOS VLSI Design", 4th ed., 2010（层级化设计）—
    https://www.pearson.com/us/higher-education/program/Weste-CMOS-VLSI-Design-A-Circuits-and-Systems-Perspective-4th-Edition/PGM320852.html
12. PhIDO arXiv:2508.14123（AI 辅助 PCell 生成理论）—
    https://arxiv.org/abs/2508.14123

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯 NumPy/SciPy）/
R05 Bug 必修 / R13 不保留 v4 兼容（迁移即重写 imports）。
"""

from __future__ import annotations

from polaris_pdk_advanced._base import (
    BoundingBox,
    Device,
    Direction,
    Port,
    Source,
)
from polaris_pdk_advanced.gdsfactory_bridge import (
    GDSFACTORY_PDK_REGISTRY,
    PDKConflict,
    PDKInfo,
    PicYamlConnection,
    PicYamlInstance,
    PicYamlRoute,
    PicYamlSpec,
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisPDKRegistry,
    PolarisSection,
    VersionCompatibility,
    check_gdsfactory_version_compatibility,
    convert_crosssection,
    convert_layerstack,
    get_gdsfactory_pdk,
    list_gdsfactory_pdks,
    parse_pic_yaml,
    polaris_to_gdsfactory_component,
)
from polaris_pdk_advanced.multi_pdk_manager import (
    MultiPDKManager,
    PDKMetadata,
    PDKSnapshot,
)
from polaris_pdk_advanced.optodesigner import (
    DesignIntent,
    DesignIntentEngine,
    FlexConnector,
    HierarchyDesign,
    PDAflowInterop,
    PyCell,
    PyCellFactory,
    TechnologyRule,
)
from polaris_pdk_advanced.pcell import (
    PCellCache,
    PCellMultiView,
    TransformMatrix,
    ai_generate_pcell,
    clear_pcell_cache,
    polaris_cell,
)
from polaris_pdk_advanced.pdk_model_params import (
    PDK_MODEL_PARAMS_REGISTRY,
    PDKModelParameters,
    get_pdk_model_params,
    list_available_pdk_model_params,
)
from polaris_pdk_advanced.yaml_config import (
    PDKYamlConfig,
    YamlCellSpec,
    YamlCrossSectionSpec,
    YamlLayerLevelSpec,
    YamlLayerSpec,
    YamlSectionSpec,
    build_polaris_cross_section,
    build_polaris_layer_stack,
    build_polaris_pdk_from_yaml,
    parse_pdk_yaml,
    serialize_pdk_yaml,
    validate_pdk_yaml,
)

__version__ = "5.1.0"

__all__ = [
    # _base
    "BoundingBox",
    "Device",
    "Direction",
    "Port",
    "Source",
    # gdsfactory_bridge
    "GDSFACTORY_PDK_REGISTRY",
    "PDKConflict",
    "PDKInfo",
    "PicYamlConnection",
    "PicYamlInstance",
    "PicYamlRoute",
    "PicYamlSpec",
    "PolarisCrossSection",
    "PolarisLayerLevel",
    "PolarisLayerStack",
    "PolarisPDK",
    "PolarisPDKRegistry",
    "PolarisSection",
    "VersionCompatibility",
    "check_gdsfactory_version_compatibility",
    "convert_crosssection",
    "convert_layerstack",
    "get_gdsfactory_pdk",
    "list_gdsfactory_pdks",
    "parse_pic_yaml",
    "polaris_to_gdsfactory_component",
    # multi_pdk_manager
    "MultiPDKManager",
    "PDKMetadata",
    "PDKSnapshot",
    # optodesigner
    "DesignIntent",
    "DesignIntentEngine",
    "FlexConnector",
    "HierarchyDesign",
    "PDAflowInterop",
    "PyCell",
    "PyCellFactory",
    "TechnologyRule",
    # pcell
    "PCellCache",
    "PCellMultiView",
    "TransformMatrix",
    "ai_generate_pcell",
    "clear_pcell_cache",
    "polaris_cell",
    # pdk_model_params
    "PDK_MODEL_PARAMS_REGISTRY",
    "PDKModelParameters",
    "get_pdk_model_params",
    "list_available_pdk_model_params",
    # yaml_config
    "PDKYamlConfig",
    "YamlCellSpec",
    "YamlCrossSectionSpec",
    "YamlLayerLevelSpec",
    "YamlLayerSpec",
    "YamlSectionSpec",
    "build_polaris_cross_section",
    "build_polaris_layer_stack",
    "build_polaris_pdk_from_yaml",
    "parse_pdk_yaml",
    "serialize_pdk_yaml",
    "validate_pdk_yaml",
    # version
    "__version__",
]
