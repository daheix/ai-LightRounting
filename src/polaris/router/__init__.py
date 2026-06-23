"""布线引擎子包。

负责波导约束布线（A*/Lee 基线）、弯曲半径/间距/等长约束检查
以及布线环境（Gymnasium 接口）。

R10 路标新增：gdsfactory routing strategies 对齐
（JPS/Bundle/AllAngle/Dubins/AutoTaper/LengthMatch/自适应交叉）。
"""

from polaris.router.all_angle_router import AllAngleRouter
from polaris.router.bundle_router import (
    auto_taper,
    dubins_path,
    route_bundle,
    route_bundle_from_waypoints,
    route_bundle_path_length_match,
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
]
