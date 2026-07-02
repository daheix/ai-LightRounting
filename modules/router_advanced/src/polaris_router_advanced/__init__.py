"""PoLaRIS 高级布线子模块（polaris-router-advanced）。

提供 17 种高级光波导布线算法与连接器，覆盖 JPS 跳点搜索、任意角度欧拉
弯曲、Bundle 并行等长、Dubins 路径、自适应交叉、CurvyA* 曲线感知、
OptoDesigner Autorouting、Advanced Connectors（Euler/PhaseMatched/RFGSG/
Bus/Bezier/LengthDefined）、Global GCell 全局布线、Hybrid 多波导型混合、
MultiLayer OTV 跨层、光电协同、Commercial 综合策略、Diagonal 对角、
GdsfactoryStyle 风格集合、RIP-Reroute 撕裂重布、RL RoutingEnv。

## IPO 三段式设计

### Input（输入）
- 已布局电路: placements（器件左下角坐标 + 尺寸）+ netlist/connections
  （端口对连接关系），与 polaris-core/polaris-place 输出一致
- 布线约束: 弯曲半径、波导间距、网格分辨率、层栈（OTV via）、波导型
  （SOI/SiN strip/rib）、拥塞阈值、损耗系数
- 障碍/拥塞图: ObstacleGrid 障碍栅格 + congestion_map 拥塞分布

### Process（处理）
- JPS 跳点搜索（Harabor 2011）: 在线剪枝网格图，节点扩展数减少 70-90%
- AllAngle 任意角度: 曼哈顿 L 骨架 + euler_bend 平滑 + 自适应交叉插入
- Bundle 并行等长: 端口排序 + JPS 单路布线 + equalize_length 等长 +
  Dubins 路径 + auto_taper
- CurvyA* 曲线感知（LiDAR ISPD'25）: 弯曲半径约束 A* + OptoDesigner
  Autorouting + DRV-free 验证 + 拥塞感知网序 + 自适应交叉
- Advanced Connectors（Synopsys OptoDesigner 对齐）: EulerBend 超低损耗、
  LengthDefined 等长、PhaseMatched 相位匹配、RFGSG 电极、Bus 总线、
  HighOrderBezier 任意角度
- Global GCell: 全局布线（GCell 划分 + 拥塞代价 + 网序排序）
- Hybrid 多波导型: strip/rib 混合 + 过渡段
- MultiLayer: 跨层 OTV via + 层间布线
- OptoElectrical: 光电协同布线
- RIP-Reroute: 撕裂重布（冲突网拆解重布）
- RL RoutingEnv: Gymnasium 接口强化学习布线环境

### Output（输出）
- 波导路径: WaveguidePath（点序列 + length_um + loss_db + num_bends +
  num_crossings）/ 路径点列表
- 多层结果: MultiLayerRouteResult（分层路径 + via 列表）
- 布线环境: RoutingEnv（Gymnasium Env，供 RL 训练）

## 设计原则
- 纯 NumPy/SciPy 实现（R04: 不参与 GPU），禁止 CuPy/CUDA
- 禁止 fall-back（R03）: 布线失败 raise，不返回哨兵值/空路径/假数据
- 学术诚信（R02）: 所有参数/公式可溯源，创新点标注 *创新*
- 不保留 v4 兼容（R13）: curvy-aware 路由已迁至 polaris-route，本模块
  仅提供其余 17 种高级路由

## 来源（R02 学术诚信，≥5 个文献 URL）
- Harabor & Grastien, "Online Graph Pruning for Pathfinding on Grid Maps",
  AAAI 2011（JPS 跳点搜索原始论文）
  https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
- LiDAR: Automated Curvy Waveguide Detailed Routing, ISPD 2025
  （曲线感知 A* 光波导详细布线）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Dubins, "On Curves of Minimal Length with a Constraint on Average
  Curvature", American J. Math. 1957, 79(3):497-516（Dubins 路径）
  https://www.jstor.org/stable/2372560
- Hong et al., "Euler弯曲波导设计", Photonics Research 2021（欧拉弯曲超低损耗）
  https://doi.org/10.1364/PRJ.437726
- Synopsys OptoDesigner Advanced Connectors Module（高级连接器对齐基准）
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
- gdsfactory routing strategies（Bundle/AllAngle/Manhattan 布线对齐）
  https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html
- Hart, Nilsson & Raphael, "A Formal Basis for the Heuristic Determination
  of Minimum Cost Paths", IEEE SSSC 1968（A* 搜索原始论文）
  https://ieeexplore.ieee.org/document/4082128
- Fujisawa et al., "Euler bend clothoid curve low-loss waveguide",
  Optics Express 25(8) 9150, 2017（欧拉弯曲损耗模型）
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Ghione & Naldi, "A analytical Formulas for Coplanar Lines in Hybrid
  MIC", IEEE TMTT 35(3) 1987（RF GSG 电极模型）
  https://doi.org/10.1109/TMTT.1987.1133623
"""

from __future__ import annotations

# 基础设施: 障碍栅格 + 路径几何 + 网格 A* 布线器
from .obstacle_grid import ObstacleGrid, auto_grid_size
from .path_geometry import (
    arc_bend,
    check_min_spacing,
    count_crossings,
    equalize_length,
    euler_bend,
    path_length,
    path_loss,
    s_bend,
)
from .waveguide_router import (
    GridRouter,
    ObstacleGrid as _ObstacleGrid_reexport,
    PLATFORM_CONSTRAINTS,
    RouteConnectionConfig,
    RouterConstraints,
    WaveguidePath,
    WaveguideRouter,
    arc_bend as _arc_bend_reexport,
    auto_grid_size as _auto_grid_size_reexport,
    check_min_spacing as _check_min_spacing_reexport,
    count_crossings as _count_crossings_reexport,
    equalize_length as _equalize_length_reexport,
    euler_bend as _euler_bend_reexport,
    get_platform_constraints,
    path_length as _path_length_reexport,
    path_loss as _path_loss_reexport,
    route_connection,
    s_bend as _s_bend_reexport,
)

# JPS 跳点搜索（Harabor 2011）
from .jps_router import JPSRouter

# 任意角度欧拉弯曲布线
from .all_angle_router import AllAngleRouter

# Bundle 并行等长布线 + Dubins + AutoTaper
from .bundle_router import (
    auto_taper,
    dubins_path,
    route_bundle,
    route_bundle_from_waypoints,
    route_bundle_path_length_match,
)

# 对角布线
from .diagonal_router import DiagonalGridRouter

# 多层跨层布线（OTV via）
from .multilayer import (
    LayerSpec,
    MultiLayerRouteResult,
    MultiLayerRouter,
    OTVSpec,
)

# 混合多波导型布线
from .hybrid_router import (
    HybridNetConnection,
    HybridRouter,
    HybridRouterConfig,
    HybridRouteResult,
    TransitionSegment,
    WaveguideType,
)

# 光电协同布线
from .opto_electrical import (
    ElectricalNet,
    ElectricalPath,
    OptoElectricalResult,
    OptoElectricalRouter,
)

# RIP 撕裂重布
from .rip_reroute import (
    GridSpec,
    NetConnection,
    RipRerouteConfig,
    RipRerouteContext,
    route_with_rip_reroute,
)

# Advanced Connectors（Synopsys OptoDesigner 对齐）
from .advanced_connectors import (
    BusRouter,
    EulerBend,
    EulerBendConfig,
    HighOrderBezierConnector,
    LengthDefinedConnector,
    PhaseMatchedRouter,
    RFGSGRouter,
)

# CurvyA* 曲线感知 A* 核心 + OptoDesigner Autorouting + DRV 验证 + 几何
from .curvy_astar_core import CurvyAStarConfig, CurvyAStarRouter
from .curvy_geometry import CurveType
from .curvy_optodesigner import (
    AdaptiveCrossingInserter,
    CongestionAwareNetOrdering,
    OptoDesignerAutorouter,
)
from .curvy_validator import DRVFreeValidator

# Commercial 综合策略布线
from .commercial_router import CommercialRouter, CommercialRouterConfig

# GdsfactoryStyle 风格布线集合
from .gdsfactory_style import (
    GdsfactoryStyleRouter,
    Port as GfPort,
    RouteConfig as GfRouteConfig,
)

# Global GCell 全局布线
from .global_router import (
    CanvasSize,
    GCell,
    GlobalRoute,
    GlobalRouter,
    GlobalRouterConfig,
    run_global_routing,
)

# RL 布线环境（Gymnasium）
from .routing_env import RoutingEnv, RoutingEnvConfig, RoutingState

__version__ = "5.0.0"

__all__ = [
    "__version__",
    # 基础设施
    "ObstacleGrid",
    "auto_grid_size",
    "GridRouter",
    "WaveguideRouter",
    "WaveguidePath",
    "RouterConstraints",
    "RouteConnectionConfig",
    "route_connection",
    "get_platform_constraints",
    "PLATFORM_CONSTRAINTS",
    "s_bend",
    "euler_bend",
    "arc_bend",
    "check_min_spacing",
    "count_crossings",
    "equalize_length",
    "path_length",
    "path_loss",
    # JPS 跳点搜索
    "JPSRouter",
    # 任意角度
    "AllAngleRouter",
    # Bundle 并行等长
    "route_bundle",
    "route_bundle_path_length_match",
    "route_bundle_from_waypoints",
    "auto_taper",
    "dubins_path",
    # 对角
    "DiagonalGridRouter",
    # 多层
    "MultiLayerRouter",
    "MultiLayerRouteResult",
    "LayerSpec",
    "OTVSpec",
    # 混合多波导型
    "HybridRouter",
    "HybridRouterConfig",
    "HybridNetConnection",
    "HybridRouteResult",
    "TransitionSegment",
    "WaveguideType",
    # 光电协同
    "OptoElectricalRouter",
    "OptoElectricalResult",
    "ElectricalNet",
    "ElectricalPath",
    # RIP 撕裂重布
    "route_with_rip_reroute",
    "RipRerouteConfig",
    "RipRerouteContext",
    "GridSpec",
    "NetConnection",
    # Advanced Connectors
    "EulerBend",
    "EulerBendConfig",
    "LengthDefinedConnector",
    "PhaseMatchedRouter",
    "RFGSGRouter",
    "BusRouter",
    "HighOrderBezierConnector",
    # CurvyA* + OptoDesigner + DRV + 几何
    "CurvyAStarConfig",
    "CurvyAStarRouter",
    "CurveType",
    "AdaptiveCrossingInserter",
    "CongestionAwareNetOrdering",
    "OptoDesignerAutorouter",
    "DRVFreeValidator",
    # Commercial
    "CommercialRouter",
    "CommercialRouterConfig",
    # GdsfactoryStyle
    "GdsfactoryStyleRouter",
    "GfPort",
    "GfRouteConfig",
    # Global
    "GlobalRouter",
    "GlobalRouterConfig",
    "GlobalRoute",
    "GCell",
    "CanvasSize",
    "run_global_routing",
    # RL 布线环境
    "RoutingEnv",
    "RoutingEnvConfig",
    "RoutingState",
]
