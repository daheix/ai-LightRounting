"""Rip-up & Reroute 布线增强（2025 增强）。

实现布线失败时的冲突路径移除重布机制，显著提升整体布线成功率。

方法参考（方案检索，见项目规则 1.1）：
- LiDAR (ISPD 2025) congestion-aware net ordering + rip-up & reroute
  来源: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 分层曲线波导布线（冲突检测 + 重布）
  来源: https://arxiv.org/html/2505.17239v2
- 经典 EDA Rip-up & Reroute 算法
  来源: Pathak & Hu, "A Parallel Legalization Algorithm for Standard Cell Layout"
        IEEE TCAD 2014, https://ieeexplore.ieee.org/document/6814146
- Lillis & Dutt, "New algorithms for performance-driven routing of VLSI circuits",
  DAC 1999, https://dl.acm.org/doi/10.1145/309847.309970
  (经典 Rip-up & Reroute 框架，本模块核心方法来源)
- SiEPIC EBeam PDK strip waveguide 1550nm 损耗 3.0 dB/cm
  来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
  (loss_db_cm=3.0 默认值依据，与 waveguide_router._PLATFORM_LOSS_DB_CM 一致)
- Hart, Nilsson & Raphael, "A Formal Basis for the Heuristic Determination of
  Minimum Cost Paths", IEEE SSSC 1968, https://ieeexplore.ieee.org/document/4082128
  (A* 搜索原始论文，本模块单网布线底层算法)

核心思想：
1. 拥塞感知网排序：按连接难度（曼哈顿距离/障碍密度）排序，先布难连接
2. 顺序布线：每条连接用 A* 布线，将路径标记为障碍
3. 冲突重布：若某连接布线失败，移除冲突路径后重布
4. 迭代：最多 max_iterations 轮，直到全部成功或达到上限
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .waveguide_router import (
    GridRouter,
    RouterConstraints,
    WaveguidePath,
    path_length,
    path_loss,
)

logger = logging.getLogger(__name__)


@dataclass
class RipRerouteConfig:
    """Rip-up & Reroute 配置。

    Attributes:
        max_iterations: 最大重布迭代次数。
        allow_diagonal: 是否允许 8 方向（对角线）布线。
        congestion_weight: 拥塞感知排序权重。
        loss_db_cm: 波导传播损耗（dB/cm）。
    """

    max_iterations: int = 3
    allow_diagonal: bool = True
    congestion_weight: float = 1.0
    # 默认 3.0 dB/cm: SiEPIC EBeam PDK strip waveguide 1550nm 传播损耗典型值
    # (https://github.com/SiEPIC/SiEPIC_EBeam_PDK;
    #  Chrostowski 2015 §6.4)。与 waveguide_router._PLATFORM_LOSS_DB_CM["SOI"]=3.0
    #  和 pipeline/_converters.py soi_loss_db_cm=3.0 保持一致
    loss_db_cm: float = 3.0


@dataclass
class RipRerouteContext:
    """Rip-up & Reroute 运行时上下文（参数打包，降低函数参数个数）。

    Attributes:
        router: 网格路由器。
        grid_size: 网格尺寸（μm）。
        config: 配置。
        constraints: 路由器几何约束。
    """

    router: GridRouter
    grid_size: float
    config: RipRerouteConfig
    constraints: RouterConstraints


@dataclass
class GridSpec:
    """网格规格（参数打包，降低函数参数个数）。

    Attributes:
        grid_w: 网格宽度。
        grid_h: 网格高度。
        grid_size: 网格尺寸（μm）。
    """

    grid_w: int
    grid_h: int
    grid_size: float = 1.0


@dataclass
class NetConnection:
    """单条网连接（起点 + 终点 + 标识）。"""

    net_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    platform: str = "SOI"


def _manhattan_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    """计算两点曼哈顿距离（用于网排序）。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _net_difficulty(
    net: NetConnection,
    obstacle_density: float,
    weight: float,
) -> float:
    """计算网布线难度（距离 + 拥塞权重）。

    难度越高越优先布线（LiDAR congestion-aware net ordering）。
    """
    dist = _manhattan_distance(net.start, net.end)
    return dist + weight * obstacle_density * dist


def _sort_nets_by_difficulty(
    nets: list[NetConnection],
    router: GridRouter,
    weight: float,
) -> list[NetConnection]:
    """按布线难度降序排序网（先布难连接，LiDAR 2025 方法）。

    R05 Bug 修复: 原实现 ``router.obstacle.sum() / router.obstacle.size`` 调用了
    numpy.ndarray 接口，但 ``router.obstacle`` 是 ``ObstacleGrid`` 实例（非 ndarray），
    在稀疏存储模式下没有 ``sum()`` 方法和 ``size`` 属性，会抛 ``AttributeError``。
    修复后统一通过 ``blocked_cells()`` 迭代器和 ``total_cells`` 属性计算障碍密度，
    对稠密与稀疏存储均兼容。

    来源: LiDAR ISPD'25 congestion-aware net ordering
      https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    """
    # R05 修复: ObstacleGrid 无 sum()/size 属性，使用 blocked_cells() + total_cells
    blocked_count = sum(1 for _ in router.obstacle.blocked_cells())
    total = router.obstacle.total_cells
    # 防御性除零保护：total_cells 在 __init__ 已校验 > 0，此处仍显式处理
    if total <= 0:
        raise RuntimeError(
            f"ObstacleGrid.total_cells={total} 非正数，路由器初始化异常"
        )
    obstacle_density = blocked_count / total
    return sorted(
        nets,
        key=lambda n: _net_difficulty(n, obstacle_density, weight),
        reverse=True,
    )


def _path_to_grid_cells(
    path: list[tuple[float, float]],
    grid_size: float,
) -> set[tuple[int, int]]:
    """将画布坐标路径转为网格单元集合（用于标记障碍）。"""
    return {(int(p[0] / grid_size), int(p[1] / grid_size)) for p in path}


def _mark_path_as_obstacle(
    router: GridRouter,
    path_cells: set[tuple[int, int]],
) -> None:
    """将路径网格单元标记为障碍（防止后续布线重叠）。"""
    for gx, gy in path_cells:
        if 0 <= gx < router.grid_w and 0 <= gy < router.grid_h:
            router.obstacle[gy, gx] = 1


def _unmark_path_obstacle(
    router: GridRouter,
    path_cells: set[tuple[int, int]],
) -> None:
    """移除路径障碍标记（rip-up 操作）。"""
    for gx, gy in path_cells:
        if 0 <= gx < router.grid_w and 0 <= gy < router.grid_h:
            router.obstacle[gy, gx] = 0


def _route_single_net(
    net: NetConnection,
    ctx: RipRerouteContext,
    path_cells_map: dict[str, set[tuple[int, int]]],
) -> WaveguidePath | None:
    """布线单条网（含 rip-up 重布尝试）。"""
    sg = (int(net.start[0] / ctx.grid_size), int(net.start[1] / ctx.grid_size))
    eg = (int(net.end[0] / ctx.grid_size), int(net.end[1] / ctx.grid_size))
    grid_path = ctx.router.route(sg, eg)
    if grid_path is None:
        logger.warning("网 %s 布线失败，尝试 rip-up 重布", net.net_id)
        _try_rip_and_reroute(net, ctx, path_cells_map)
        grid_path = ctx.router.route(sg, eg)
        if grid_path is None:
            logger.error("网 %s rip-up 后仍失败", net.net_id)
            return None
    return _finalize_path(net, grid_path, ctx, path_cells_map)


def _finalize_path(
    net: NetConnection,
    grid_path: list[tuple[int, int]],
    ctx: RipRerouteContext,
    path_cells_map: dict[str, set[tuple[int, int]]],
) -> WaveguidePath:
    """将网格路径转为画布路径并标记障碍。"""
    pts = [(g[0] * ctx.grid_size, g[1] * ctx.grid_size) for g in grid_path]
    if pts:
        pts[0] = net.start
        pts[-1] = net.end
    cells = _path_to_grid_cells(pts, ctx.grid_size)
    path_cells_map[net.net_id] = cells
    _mark_path_as_obstacle(ctx.router, cells)
    loss_db = path_loss(pts, loss_db_cm=ctx.config.loss_db_cm)
    return WaveguidePath(points=pts, length_um=path_length(pts), loss_db=loss_db)


def route_with_rip_reroute(
    nets: list[NetConnection],
    grid_spec: GridSpec,
    constraints: RouterConstraints | None = None,
    config: RipRerouteConfig | None = None,
) -> dict[str, WaveguidePath | None]:
    """批量布线 + Rip-up & Reroute（LiDAR 2025 方法）。

    Args:
        nets: 待布线网连接列表。
        grid_spec: 网格规格（宽/高/尺寸）。
        constraints: 路由器几何约束。
        config: Rip-up & Reroute 配置。

    Returns:
        网名到布线路径的映射，失败网为 None。
    """
    cfg = config or RipRerouteConfig()
    cons = constraints or RouterConstraints()
    router = GridRouter(grid_spec.grid_w, grid_spec.grid_h, grid_spec.grid_size, cons)
    ctx = RipRerouteContext(
        router=router, grid_size=grid_spec.grid_size, config=cfg, constraints=cons
    )
    sorted_nets = _sort_nets_by_difficulty(nets, router, cfg.congestion_weight)
    results: dict[str, WaveguidePath | None] = {}
    path_cells_map: dict[str, set[tuple[int, int]]] = {}
    for iteration in range(cfg.max_iterations):
        logger.info(
            "Rip-up & Reroute 迭代 %d/%d, 待布网 %d",
            iteration + 1,
            cfg.max_iterations,
            len(sorted_nets),
        )
        failed = _route_iteration(sorted_nets, ctx, results, path_cells_map)
        if not failed:
            logger.info("全部 %d 条网布线成功（迭代 %d）", len(nets), iteration + 1)
            break
        sorted_nets = failed
    _mark_failed_nets(nets, results)
    success = sum(1 for v in results.values() if v is not None)
    logger.info("Rip-up & Reroute 完成: %d/%d 成功", success, len(nets))
    return results


def _route_iteration(
    nets: list[NetConnection],
    ctx: RipRerouteContext,
    results: dict[str, WaveguidePath | None],
    path_cells_map: dict[str, set[tuple[int, int]]],
) -> list[NetConnection]:
    """执行一轮布线迭代，返回失败网列表。"""
    failed: list[NetConnection] = []
    for net in nets:
        if net.net_id in results and results[net.net_id] is not None:
            continue
        path = _route_single_net(net, ctx, path_cells_map)
        if path is None:
            failed.append(net)
        else:
            results[net.net_id] = path
    return failed


def _mark_failed_nets(
    nets: list[NetConnection],
    results: dict[str, WaveguidePath | None],
) -> None:
    """标记未布线成功的网为 None。"""
    for net in nets:
        if net.net_id not in results:
            results[net.net_id] = None
            logger.error("网 %s 最终布线失败", net.net_id)


def _try_rip_and_reroute(
    net: NetConnection,
    ctx: RipRerouteContext,
    path_cells_map: dict[str, set[tuple[int, int]]],
) -> bool:
    """尝试移除冲突路径后重布（rip-up 操作）。"""
    sg = (int(net.start[0] / ctx.grid_size), int(net.start[1] / ctx.grid_size))
    eg = (int(net.end[0] / ctx.grid_size), int(net.end[1] / ctx.grid_size))
    x_min = min(sg[0], eg[0]) - 2
    x_max = max(sg[0], eg[0]) + 2
    y_min = min(sg[1], eg[1]) - 2
    y_max = max(sg[1], eg[1]) + 2
    ripped = 0
    for cells in path_cells_map.values():
        if any(x_min <= c[0] <= x_max and y_min <= c[1] <= y_max for c in cells):
            _unmark_path_obstacle(ctx.router, cells)
            ripped += 1
    if not ripped:
        return False
    logger.info("网 %s rip-up %d 条冲突路径", net.net_id, ripped)
    return True


__all__ = [
    "RipRerouteConfig",
    "RipRerouteContext",
    "GridSpec",
    "NetConnection",
    "route_with_rip_reroute",
]
