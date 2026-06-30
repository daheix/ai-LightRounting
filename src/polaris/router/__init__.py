"""布线引擎子包。

负责波导约束布线（A*/Lee 基线）、弯曲半径/间距/等长约束检查
以及布线环境（Gymnasium 接口）。

R10 路标新增：gdsfactory routing strategies 对齐
（JPS/Bundle/AllAngle/Dubins/AutoTaper/LengthMatch/自适应交叉）。

R21 路标新增：LiDAR 曲线感知 A* + OptoDesigner Autorouting 对齐
（CurvyAStarRouter/AdaptiveCrossingInserter/CongestionAwareNetOrdering/
OptoDesignerAutorouter/DRVFreeValidator）。

R22 路标新增：OptoDesigner Advanced Connectors Module 对齐
（EulerBend/LengthDefinedConnector/PhaseMatchedRouter/RFGSGRouter/
BusRouter/HighOrderBezierConnector）。

参考文献：
[1] Hart P E, Nilsson N J, Raphael B. A formal basis for the heuristic determination of minimum cost paths[J]. IEEE Transactions on Systems Science and Cybernetics, 1968, 4(2): 100-107. https://ieeexplore.ieee.org/document/4082128
[2] Harabor D, Grastien A. Online graph pruning for pathfinding on grid maps[C]//AAAI Conference on Artificial Intelligence. 2011. https://harabor.net/data/papers/harabor-grastien-aaai11.pdf
[3] Fujisawa T, et al. Euler bend waveguide for low loss and compactness[J]. Optics Express, 2017, 25(8): 9150-9160. https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
[4] Rizzo S, et al. Euler curves for robust design of silicon photonic waveguide bends[J]. Optics Letters, 2023, 48(2): 215-218. https://lightwave.ee.columbia.edu/sites/default/files/content/publications/2022/ol-48-2-215.pdf
[5] Zhou J, et al. Curvature-aware A* routing for LiDAR photonic integrated circuits[C]//International Symposium on Physical Design (ISPD). 2025. https://dl.acm.org/doi/10.1145/3698364.3705355
[6] Lee C Y. An algorithm for path connections and its applications[J]. IRE Transactions on Electronic Computers, 1961, EC-10(3): 346-365. https://doi.org/10.1109/TEC.1961.5219222
"""

from polaris.router.advanced_connectors import (
    BusRouter,
    EulerBend,
    EulerBendConfig,
    HighOrderBezierConnector,
    LengthDefinedConnector,
    PhaseMatchedRouter,
    RFGSGRouter,
)
from polaris.router.all_angle_router import AllAngleRouter
from polaris.router.bundle_router import (
    auto_taper,
    dubins_path,
    route_bundle,
    route_bundle_from_waypoints,
    route_bundle_path_length_match,
)
from polaris.router.curvy_router import (
    AdaptiveCrossingInserter,
    CongestionAwareNetOrdering,
    CurveType,
    CurvyAStarConfig,
    CurvyAStarRouter,
    CurvyPathResult,
    CurvyRouteConfig,
    CurvyRouter,
    DRVFreeValidator,
    OptoDesignerAutorouter,
    route_curvy_connection,
)
from polaris.router.gdsfactory_style import (
    GdsfactoryStyleRouter,
)
from polaris.router.gdsfactory_style import (
    Port as GfPort,
)
from polaris.router.gdsfactory_style import (
    RouteConfig as GfRouteConfig,
)
from polaris.router.jps_router import JPSRouter

__all__ = [
    # R10: gdsfactory routing strategies 对齐
    "AllAngleRouter",
    "JPSRouter",
    "auto_taper",
    "dubins_path",
    "route_bundle",
    "route_bundle_from_waypoints",
    "route_bundle_path_length_match",
    # R10: gdsfactory 风格布线策略集合（fiber_array/bundle/sbend/manhattan/cpw）
    "GdsfactoryStyleRouter",
    "GfPort",
    "GfRouteConfig",
    # R21: LiDAR 曲线感知 A* + OptoDesigner Autorouting 对齐
    "AdaptiveCrossingInserter",
    "CongestionAwareNetOrdering",
    "CurvyAStarConfig",
    "CurvyAStarRouter",
    "DRVFreeValidator",
    "OptoDesignerAutorouter",
    # R10: 向后兼容 route_curvy_connection API
    "CurvyRouter",
    "CurvyRouteConfig",
    "CurvyPathResult",
    "CurveType",
    "route_curvy_connection",
    # R22: OptoDesigner Advanced Connectors Module 对齐
    "BusRouter",
    "EulerBend",
    "EulerBendConfig",
    "HighOrderBezierConnector",
    "LengthDefinedConnector",
    "PhaseMatchedRouter",
    "RFGSGRouter",
]
