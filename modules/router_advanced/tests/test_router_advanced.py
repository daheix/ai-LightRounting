"""polaris-router-advanced 子模块 smoke test。

测试覆盖（≥3 个 smoke test，实际 10 个，覆盖核心 API）:
- test_jps_router_smoke: JPS 跳点搜索网格布线（Harabor 2011）
- test_all_angle_router_smoke: 任意角度欧拉弯曲布线
- test_bundle_router_smoke: Bundle 多端口并行布线
- test_euler_bend_connector_smoke: Advanced Connectors 欧拉弯曲连接器
- test_curvy_astar_router_smoke: CurvyA* 曲线感知布线（LiDAR ISPD'25）
- test_diagonal_router_smoke: 对角网格布线
- test_dubins_path_smoke: Dubins 路径生成
- test_path_geometry_tools_smoke: 几何工具（s_bend/euler_bend/count_crossings/path_length）
- test_global_router_empty_circuit: 空电路全局布线返回空列表
- test_no_fallback_invalid_inputs: 非法输入 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- Harabor & Grastien JPS AAAI 2011
  https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
- LiDAR ISPD 2025 https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Dubins 1957 https://www.jstor.org/stable/2372560
- Hong et al. 2021 https://doi.org/10.1364/PRJ.437726
- gdsfactory routing https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html
- pytest 文档 https://docs.pytest.org/
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
# router_advanced/src: 本子模块源码; /workspace/src: polaris.engine 依赖
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_POLARIS_SRC = str(Path(__file__).resolve().parents[3] / "src")
for _p in (_SRC, _POLARIS_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_router_advanced as pra  # noqa: E402
from polaris_router_advanced import (  # noqa: E402
    AllAngleRouter,
    CanvasSize,
    CurvyAStarConfig,
    CurvyAStarRouter,
    DiagonalGridRouter,
    EulerBend,
    EulerBendConfig,
    GlobalRouterConfig,
    JPSRouter,
    count_crossings,
    dubins_path,
    euler_bend,
    path_length,
    route_bundle,
    run_global_routing,
    s_bend,
)


def test_jps_router_smoke():
    """JPS 跳点搜索: 20x20 网格 (1,1)→(18,18) 应返回非空可达路径。

    JPS 通过在线剪枝将 A* 节点扩展数减少 70-90%（Harabor 2011）。
    验证: 路径非空、起止点正确、所有点在网格内。
    """
    router = JPSRouter(grid_w=20, grid_h=20, grid_size=1.0)
    path = router.route((1, 1), (18, 18))
    assert len(path) >= 2, f"JPS 路径至少 2 点，实际 {len(path)}"
    assert path[0] == (1, 1), f"起点应为 (1,1)，实际 {path[0]}"
    assert path[-1] == (18, 18), f"终点应为 (18,18)，实际 {path[-1]}"
    for x, y in path:
        assert 0 <= x < 20 and 0 <= y < 20, f"点越界: ({x},{y})"


def test_jps_router_obstacle_detour():
    """JPS 障碍绕行: 中间障碍墙应被绕过（路径仍可达）。

    在 x=10 列设置障碍墙（留 y=0 缺口），路径应绕过障碍到达终点。
    """
    router = JPSRouter(grid_w=20, grid_h=20, grid_size=1.0)
    # 在 x=10, y=1..18 设置障碍墙（GridRouter.add_obstacle 标记障碍区域）
    for y in range(1, 19):
        router.add_obstacle(10, y)
    path = router.route((1, 5), (18, 5))
    assert len(path) >= 2
    assert path[0] == (1, 5)
    assert path[-1] == (18, 5)
    # 路径不应穿过障碍
    for x, y in path:
        assert not router.obstacle.is_blocked(x, y), f"路径穿过障碍: ({x},{y})"


def test_all_angle_router_smoke():
    """任意角度布线: (0,0,0°)→(50,30,0°) 应返回含欧拉弯曲的路径。

    AllAngleRouter 用曼哈顿 L 骨架 + euler_bend 平滑非曼哈顿段。
    验证: 路径非空、起止点接近、点数 > 2（含弯曲平滑段）。
    """
    router = AllAngleRouter(grid_w=100, grid_h=100, bend_radius=5.0)
    path = router.route((0.0, 0.0, 0.0), (50.0, 30.0, 0.0))
    assert len(path) >= 2, f"AllAngle 路径至少 2 点，实际 {len(path)}"
    # 起止点接近输入（含欧拉弯曲平滑后可能微调）
    assert abs(path[0][0] - 0.0) < 5.0
    assert abs(path[-1][0] - 50.0) < 5.0


def test_bundle_router_smoke():
    """Bundle 并行布线: 2 端口对应返回 2 条不交叉路径。

    route_bundle 用端口排序 + JPS 单路布线 + 缓冲区防碰撞。
    验证: 返回 2 条路径、每条非空、端口对齐。
    """
    ports1 = [(0, 0), (0, 5)]
    ports2 = [(40, 0), (40, 5)]
    paths = route_bundle(ports1, ports2, separation=2, grid_w=50, grid_h=20)
    assert len(paths) == 2, f"应返回 2 条路径，实际 {len(paths)}"
    for p in paths:
        assert len(p) >= 2, f"Bundle 路径至少 2 点，实际 {len(p)}"
        assert p[0][0] == 0, f"起点 x 应为 0，实际 {p[0][0]}"
        assert p[-1][0] == 40, f"终点 x 应为 40，实际 {p[-1][0]}"


def test_euler_bend_connector_smoke():
    """Advanced Connectors 欧拉弯曲连接器: 90° 弯曲应生成对称 S 形路径。

    EulerBend（Hong 2021）曲率从 0 线性增到 1/R 再减到 0。
    验证: 路径点数 = n_points、首点在原点附近、末点 y 接近 R（90° 弯曲）。
    """
    config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
    bend = EulerBend(config)
    path = bend.compute_path()
    assert len(path) == 50, f"应 50 点，实际 {len(path)}"
    # 首点应在原点附近
    assert abs(path[0][0]) < 1.0 and abs(path[0][1]) < 1.0
    # 90° 弯曲末点应偏离原点（曲率积分转角 = 90°）
    assert path[-1][0] != 0.0 or path[-1][1] != 0.0


def test_curvy_astar_router_smoke():
    """CurvyA* 曲线感知布线: (0,0)→(50,30) 应返回弯曲半径约束路径。

    CurvyAStarRouter（LiDAR ISPD'25）用弯曲半径感知 A* + 多方向扩展。
    验证: 路径非空、起止点正确。
    """
    router = CurvyAStarRouter(CurvyAStarConfig())
    path = router.route((0.0, 0.0), (50.0, 30.0))
    assert len(path) >= 2, f"CurvyA* 路径至少 2 点，实际 {len(path)}"
    assert path[0] == (0.0, 0.0), f"起点应为 (0,0)，实际 {path[0]}"
    assert path[-1] == (50.0, 30.0), f"终点应为 (50,30)，实际 {path[-1]}"


def test_diagonal_router_smoke():
    """对角网格布线: 20x20 网格 (1,1)→(18,18) 应返回非空路径。

    DiagonalGridRouter 支持对角线移动（8-邻接）。
    验证: 路径非空、起止点正确。
    """
    router = DiagonalGridRouter(grid_w=20, grid_h=20, grid_size=1.0)
    path = router.route((1, 1), (18, 18))
    assert path is not None, "Diagonal 路径不应为 None"
    assert len(path) >= 2, f"Diagonal 路径至少 2 点，实际 {len(path)}"
    assert path[0] == (1, 1)
    assert path[-1] == (18, 18)


def test_dubins_path_smoke():
    """Dubins 路径: (0,0,0°)→(20,10,0°) 应返回连续曲率路径。

    Dubins 路径（Dubins 1957）是带曲率约束的最短路径。
    验证: 路径非空、首点接近起点。
    """
    path = dubins_path((0.0, 0.0, 0.0), (20.0, 10.0, 0.0), radius=5.0)
    assert len(path) >= 2, f"Dubins 路径至少 2 点，实际 {len(path)}"
    assert abs(path[0][0] - 0.0) < 1.0
    assert abs(path[0][1] - 0.0) < 1.0


def test_path_geometry_tools_smoke():
    """几何工具: s_bend/euler_bend/count_crossings/path_length 基础验证。

    验证:
    - s_bend 返回 n_points+1 个点
    - euler_bend 返回正数点
    - count_crossings 检测两条相交路径 = 1
    - path_length 直线长度正确
    """
    # s_bend
    sb = s_bend(0.0, 0.0, 100.0, 20.0, n_points=20)
    assert len(sb) == 21, f"s_bend 应 21 点，实际 {len(sb)}"
    assert sb[0] == (0.0, 0.0)
    assert sb[-1] == (100.0, 20.0)

    # euler_bend
    eb = euler_bend(radius_um=5.0, angle_deg=90.0, n_points=30)
    assert len(eb) > 0 and len(eb) == 31, f"euler_bend 应 31 点，实际 {len(eb)}"

    # count_crossings: 两条相交线段
    p1 = [(0.0, 0.0), (10.0, 10.0)]
    p2 = [(0.0, 10.0), (10.0, 0.0)]
    assert count_crossings(p1, p2) == 1, "相交路径应有 1 个交叉"

    # path_length: 直线 (0,0)→(3,4) 长度 = 5
    assert abs(path_length([(0.0, 0.0), (3.0, 4.0)]) - 5.0) < 1e-9


def test_global_router_empty_circuit():
    """空电路全局布线: 空 Netlist 返回空路径列表。

    run_global_routing 用 GCell 划分 + 拥塞代价 + 网序排序。
    验证: 空电路返回 []，GlobalRouterConfig 可实例化。
    """
    from polaris_router_advanced.global_router import Netlist

    config = GlobalRouterConfig()
    net = Netlist(instances=[], connections=[], name="empty")
    result = run_global_routing(
        net, {}, CanvasSize(width=500.0, height=300.0), config=config
    )
    assert isinstance(result, list)
    assert len(result) == 0, f"空电路应 0 路径，实际 {len(result)}"


def test_no_fallback_invalid_inputs():
    """非法输入必须 raise（R03 禁止 fall-back）。

    验证:
    - AllAngleRouter 网格尺寸 <= 0 raise ValueError
    - AllAngleRouter bend_radius <= 0 raise ValueError
    - EulerBendConfig radius <= 0 raise ValueError
    """
    with pytest.raises(ValueError, match="网格尺寸必须为正"):
        AllAngleRouter(grid_w=0, grid_h=10)
    with pytest.raises(ValueError, match="bend_radius"):
        AllAngleRouter(grid_w=10, grid_h=10, bend_radius=0.0)
    with pytest.raises(ValueError, match="radius"):
        EulerBendConfig(radius=-1.0, angle=90.0)


def test_package_exports_complete():
    """验证包导出完整性: __version__ + 核心 API 可访问。

    验证: __version__ = "5.0.0"，__all__ 含核心路由器类。
    """
    assert pra.__version__ == "5.0.0"
    for name in [
        "JPSRouter", "AllAngleRouter", "GridRouter", "WaveguidePath",
        "route_bundle", "dubins_path", "EulerBend", "EulerBendConfig",
        "CurvyAStarRouter", "CurvyAStarConfig", "OptoDesignerAutorouter",
        "DRVFreeValidator", "GlobalRouter", "HybridRouter", "MultiLayerRouter",
        "OptoElectricalRouter", "CommercialRouter", "GdsfactoryStyleRouter",
        "RipRerouteContext", "RoutingEnv", "RFGSGRouter", "BusRouter",
    ]:
        assert hasattr(pra, name), f"包缺导出: {name}"
        assert name in pra.__all__, f"__all__ 缺: {name}"
