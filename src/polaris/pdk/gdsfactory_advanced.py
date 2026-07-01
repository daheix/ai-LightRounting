"""gdsfactory 深度集成进阶模块（R305-R310）。

在 R301-R304 基础（GDSII 读写/层映射/组件级联合仿真）之上，本模块实现
6 个进阶功能，对标 Lumerical Interconnect/IPKISS/KLayout 商业链路：

- R305 PDK 双向兼容增强：SiEPIC/Generic/Custom PDK 配置文件（YAML）支持
- R306 电路级联合仿真：多组件级联 S 参数仿真（Redheffer star product），自动端口识别
- R307 PCell 双向兼容：gdsfactory PCell ↔ PoLaRIS PCell 数据结构转换与往返验证
- R308 KLayout DRC 集成：调用 klayout.db.Region 几何引擎执行 DRC 规则集
- R309 gdsfactory 插件接口：将 PoLaRIS 组件注册为 gdsfactory 第三方插件
- R310 往返导入导出增强：多轮 GDSII 往返 + 几何哈希一致性验证

学术诚信（R02）：所有参数/公式/算法可溯源，docstring 含 10 个文献 URL。
禁止 fall-back（R03）：gdsfactory 不可用时相关功能 raise ImportError；
业务错误 raise 明确异常，无静默兜底，无假数据。
不参与 GPU（R04）：纯 NumPy/SciPy/KLayout(CPU) 实现。

文献来源:
1. gdsfactory PDK tutorial (Matres et al., gdsfactory):
   https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
2. gdsfactory PDK import (add ports from pins):
   https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
3. gdsfactory circuit simulators (SAX / Lumerical Interconnect):
   https://gdsfactory.github.io/gplugins/plugins_circuits.html
4. KLayout DRC Reference Manual:
   https://www.klayout.org/downloads/master/doc-qt4/about/drc_ref.html
5. KLayout Database API (Layout/Cell/Region):
   https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
6. SiEPIC EBeam PDK (Chrostowski, UBC, MIT):
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
7. GDSII binary format specification:
   https://en.wikipedia.org/wiki/GDS_File
8. Redheffer star product (Redheffer 1962, S-matrix cascade):
   https://en.wikipedia.org/wiki/Redheffer_star_product
9. Krinke, Fischbach, Lienig. "Layout Verification Using Open-Source Software",
   ISPD'24, ACM, 2024. DOI: 10.1145/3626184.3635289
   https://doi.org/10.1145/3626184.3635289
10. Matres et al. "GDSFactory: An Open-Source Python Library for Chip Design
    and Simulation", CLEO 2026:
    https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf

创新点（R02 标注 *创新*）:
- *创新* R306: 用 Redheffer star product（Redheffer 1962）实现任意多端口
  S 参数级联，纯 NumPy 实现，不依赖 sax/JAX（避免 GPU 依赖，符合 R04）。
  底层逻辑：散射矩阵级联的标准数学方法，将两个多端口网络合成一个，
  公式见文献 8；与 SAX（文献 3）的 sdict 级联等价但无 JAX 依赖。
- *创新* R308: 基于 klayout.db.Region 几何运算的程序化 DRC 引擎，不依赖
  Ruby DRC DSL，规则集用 Python dataclass 定义可序列化 YAML。底层逻辑：
  KLayout DRC 引擎底层即 Region 的 width_check/space_check/notch_check 等形态
  运算（文献 4/5），直接调用等价于 DRC 但可程序化组合，对标 Calibre/KLayout
  商业 DRC（文献 9 ISPD'24 论证 KLayout DRC 可替代商业工具）。

批次 10-B 拆分说明（2026-07-01）:
    原文件 1337 行超过质量门禁（AGENTS.md §8 文件 ≤ 800 行），按 Extract Module
    模式拆分为 6 个子模块，本文件作为瘦壳 re-export 公共符号以保持向后兼容：
    - polaris.pdk.gdsfactory_advanced_pdk_config: R305 PDK 兼容配置
    - polaris.pdk.gdsfactory_advanced_circuit_sim: R306 电路级联仿真
    - polaris.pdk.gdsfactory_advanced_pcell: R307 PCell 双向兼容
    - polaris.pdk.gdsfactory_advanced_drc: R308 KLayout DRC 引擎
    - polaris.pdk.gdsfactory_advanced_plugin: R309 gdsfactory 插件注册
    - polaris.pdk.gdsfactory_advanced_roundtrip: R310 GDSII 往返验证

来源:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html
"""

from __future__ import annotations

# 批次 10-B: 从拆分后的子模块 re-export 公共符号（保持向后兼容）。
# 任何外部代码 `from polaris.pdk.gdsfactory_advanced import X`
# 仍可直接使用，无需修改 import 路径。
from polaris.pdk.gdsfactory_advanced_pdk_config import (
    GENERIC_PDK_CONFIG,
    PDKCompatibilityConfig,
    SIEPIC_PDK_CONFIG,
    get_preset_pdk_config,
    load_pdk_config,
    merge_pdk_configs,
    save_pdk_config,
    validate_pdk_compatibility,
)
from polaris.pdk.gdsfactory_advanced_circuit_sim import (
    CircuitNetlist,
    SParameterModel,
    auto_identify_ports,
    cascade_two_ports,
    redheffer_star,
    simulate_circuit,
)
from polaris.pdk.gdsfactory_advanced_pcell import (
    GDSFactoryPCellSpec,
    PolarisPCellSpec,
    _HAS_GDSFACTORY,
    gdsfactory_to_polaris_pcell,
    pcell_roundtrip_verify,
    polaris_to_gdsfactory_pcell,
    register_pcell_to_gdsfactory,
)
from polaris.pdk.gdsfactory_advanced_drc import (
    DEFAULT_DRC_RULESET,
    DRCResult,
    DRCRule,
    DRCViolation,
    build_drc_ruleset_from_yaml,
    run_klayout_drc,
)
from polaris.pdk.gdsfactory_advanced_plugin import (
    GDSFactoryPluginEntry,
    declare_plugin,
    get_plugin,
    list_registered_plugins,
    register_as_gdsfactory_plugin,
)
from polaris.pdk.gdsfactory_advanced_roundtrip import (
    RoundTripReport,
    geometric_hash,
    round_trip_gdsii_advanced,
)

__all__ = [
    # R305
    "PDKCompatibilityConfig",
    "GENERIC_PDK_CONFIG",
    "SIEPIC_PDK_CONFIG",
    "get_preset_pdk_config",
    "load_pdk_config",
    "save_pdk_config",
    "merge_pdk_configs",
    "validate_pdk_compatibility",
    # R306
    "SParameterModel",
    "CircuitNetlist",
    "redheffer_star",
    "cascade_two_ports",
    "auto_identify_ports",
    "simulate_circuit",
    # R307
    "PolarisPCellSpec",
    "GDSFactoryPCellSpec",
    "polaris_to_gdsfactory_pcell",
    "gdsfactory_to_polaris_pcell",
    "register_pcell_to_gdsfactory",
    "pcell_roundtrip_verify",
    # R308
    "DRCRule",
    "DRCViolation",
    "DRCResult",
    "DEFAULT_DRC_RULESET",
    "run_klayout_drc",
    "build_drc_ruleset_from_yaml",
    # R309
    "GDSFactoryPluginEntry",
    "declare_plugin",
    "register_as_gdsfactory_plugin",
    "list_registered_plugins",
    "get_plugin",
    # R310
    "RoundTripReport",
    "geometric_hash",
    "round_trip_gdsii_advanced",
]
