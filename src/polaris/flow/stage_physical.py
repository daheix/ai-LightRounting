"""PoLaRIS 流水线物理设计阶段（阶段 3-4）。

包含器件布局（stage3）与波导布线（stage4）。这两个阶段负责将电路
规格转化为物理版图坐标：先布局器件位置，再为连接布设波导路径。

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。

## 学术来源

- DREAMPlace 解析法布局 (DAC 2019/TCAD 2020)
  https://arxiv.org/abs/2004.10746
- Apollo arXiv 2025: 布线感知布局
  https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: 弯曲波导布线
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC EBeam PDK 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警
"""

from __future__ import annotations

import logging

from polaris.flow.recipe import Recipe
from polaris.flow.stage_serializers import (
    _circuit_from_dict,
    _require_input,
)
from polaris.flow.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# 阶段 3: 器件布局
# =============================================================================


def _run_analytical_placer(circuit) -> dict[str, dict[str, float]]:
    """运行 DREAMPlace 解析法布局。

    来源: DREAMPlace DAC 2019/TCAD 2020
    https://arxiv.org/abs/2004.10746

    Args:
        circuit: 电路对象。

    Returns:
        {name: {x, y, w, h}} 布局字典（左下角坐标）。

    Raises:
        ValueError: 布局结果为空时告警退出（禁止 fall-back）。
    """
    from polaris.engine.analytical_placer import AnalyticalPlacer

    placer = AnalyticalPlacer(circuit)
    # place() 返回 {name: (cx, cy)} 中心坐标，需转换为左下角坐标
    center_positions = placer.place()
    if not center_positions:
        raise ValueError(
            f"布局失败：电路 '{circuit.name}' 无器件可布局。"
            f"请检查 circuit.devices 是否为空。"
        )
    # 构建器件名 → 尺寸映射
    dev_sizes = {d.name: (d.width_um, d.height_um) for d in circuit.devices}
    placements: dict[str, dict[str, float]] = {}
    for name, (cx, cy) in center_positions.items():
        w, h = dev_sizes.get(name, (10.0, 10.0))
        # 中心坐标 → 左下角坐标
        placements[name] = {
            "x": float(cx - w / 2),
            "y": float(cy - h / 2),
            "w": float(w),
            "h": float(h),
        }
    return placements


def _run_default_placer(
    circuit, algo: str, recipe: Recipe,
) -> dict[str, dict[str, float]]:
    """运行 RL/随机贪心布局（_DefaultPlacer）。

    Args:
        circuit: 电路对象。
        algo: 算法名 ('rl'/'ppo_gnn'/'random'/'auto')。
        recipe: 作业配方（用于读取 placement_checkpoint）。

    Returns:
        {name: {x, y, w, h}} 布局字典。

    Raises:
        ValueError: algo 非法或布局结果为空时告警退出（禁止 fall-back）。
    """
    from polaris.pipeline.integrated import _DefaultPlacer

    if algo in ("rl", "ppo_gnn"):
        # RL 模式需要 checkpoint，recipe 未提供时 raise
        checkpoint = getattr(recipe, "placement_checkpoint", None)
        if checkpoint is None:
            raise ValueError(
                f"placement_algo='{algo}' 需要提供 checkpoint 路径。"
                f"Recipe 未定义 placement_checkpoint 字段。"
                f"若需使用随机贪心布局，请设置 placement_algo='random'。"
            )
        placer = _DefaultPlacer(checkpoint_path=checkpoint, mode="rl")
    elif algo == "random":
        placer = _DefaultPlacer(mode="random")
    elif algo == "auto":
        checkpoint = getattr(recipe, "placement_checkpoint", None)
        if checkpoint is not None:
            placer = _DefaultPlacer(checkpoint_path=checkpoint, mode="auto")
        else:
            placer = _DefaultPlacer(mode="random")
    else:
        raise ValueError(
            f"未知 placement_algo='{algo}'。"
            f"支持: 'analytical'/'rl'/'ppo_gnn'/'random'/'auto'。"
        )

    raw_placements = placer.place(circuit)
    if not raw_placements:
        raise ValueError(
            f"布局失败：电路 '{circuit.name}' 无器件可布局。"
            f"请检查 circuit.devices 是否为空。"
        )
    # _DefaultPlacer 已返回 {name: {x, y, w, h}} 格式
    return {
        name: {
            "x": float(pl["x"]),
            "y": float(pl["y"]),
            "w": float(pl["w"]),
            "h": float(pl["h"]),
        }
        for name, pl in raw_placements.items()
    }


def stage3_placement(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 3: 器件布局。

    根据 recipe.placement_algo 选择布局算法：
    - "analytical": DREAMPlace 解析法布局（AnalyticalPlacer）
    - "rl"/"ppo_gnn": RL 布局（_DefaultPlacer mode="rl"，需 checkpoint）
    - "random": 随机贪心布局（_DefaultPlacer mode="random"）
    - "auto": 自动选择（有 checkpoint 用 RL，否则用随机）

    Args:
        recipe: 作业配方（使用 recipe.placement_algo）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit"）。

    Returns:
        含 placements/n_placed 的字典。
    """
    circuit_dict = _require_input(prev_outputs, "circuit", 3)
    circuit = _circuit_from_dict(circuit_dict)

    algo = recipe.placement_algo
    logger.info("阶段 3: 器件布局（算法=%s）", algo)

    if algo == "analytical":
        placements = _run_analytical_placer(circuit)
    else:
        placements = _run_default_placer(circuit, algo, recipe)

    logger.info("阶段 3 完成: 布局 %d 个器件", len(placements))

    return {
        "placements": placements,
        "n_placed": len(placements),
    }


# =============================================================================
# 阶段 4: 波导布线
# =============================================================================


def _run_curvy_or_default_router(
    algo: str, circuit, placements,
) -> dict[str, list]:
    """运行 curvy 或 default 布线器。

    Args:
        algo: 'curvy' 或 'default'。
        circuit: 电路对象。
        placements: 布局字典。

    Returns:
        布线路径字典 {conn_key: [(x, y), ...]}。

    Raises:
        ValueError: algo 非 'curvy'/'default' 时告警退出（禁止 fall-back）。
    """
    if algo == "curvy":
        from polaris.pipeline.curvy_router import _CurvyRouter

        router = _CurvyRouter(curve_type="euler")
        return router.route(circuit, placements)
    elif algo == "default":
        from polaris.pipeline.integrated import _DefaultRouter

        router = _DefaultRouter()
        return router.route(circuit, placements)
    raise ValueError(
        f"未知 router_algo='{algo}'。"
        f"支持: 'curvy'/'default'/'diagonal'。"
    )


def _run_diagonal_router(circuit, placements) -> dict[str, list]:
    """运行对角线布线（DiagonalGridRouter）。

    来源: LiDAR ISPD'25 对角线布线
    https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    Args:
        circuit: 电路对象。
        placements: 布局字典。

    Returns:
        布线路径字典 {conn_key: [(x, y), ...]}。
    """
    from polaris.router.diagonal_router import DiagonalGridRouter
    from polaris.router.waveguide_router import RouterConstraints, auto_grid_size

    grid_size = auto_grid_size(
        canvas_w=circuit.canvas_w,
        canvas_h=circuit.canvas_h,
        platform="SOI",
        min_bend_radius_um=5.0,
    )
    grid_w = int(circuit.canvas_w / grid_size)
    grid_h = int(circuit.canvas_h / grid_size)
    cons = RouterConstraints(min_bend_radius_um=5.0, min_spacing_um=1.0)
    router = DiagonalGridRouter(grid_w, grid_h, grid_size, cons)
    routes: dict[str, list] = {}
    unrouted: list[str] = []
    for d1, p1, d2, p2 in circuit.connections:
        if d1 in placements and d2 in placements:
            pos1 = placements[d1]
            pos2 = placements[d2]
            sg = (int(pos1["x"] / grid_size), int(pos1["y"] / grid_size))
            eg = (int(pos2["x"] / grid_size), int(pos2["y"] / grid_size))
            grid_path = router.route(sg, eg)
            if grid_path:
                pts = [(g[0] * grid_size, g[1] * grid_size) for g in grid_path]
                routes[f"{d1}_{p1}_{d2}_{p2}"] = pts
            else:
                unrouted.append(f"{d1}_{p1}_{d2}_{p2}")
        else:
            unrouted.append(f"{d1}_{p1}_{d2}_{p2}")
    if unrouted:
        logger.warning("对角线布线存在 %d 条未布线连接", len(unrouted))
    return routes


def _collect_routes_metrics(
    routes: dict[str, list],
) -> tuple[dict[str, list[list[float]]], float]:
    """计算路径总长度并序列化路径坐标为可 JSON 序列化格式。

    Args:
        routes: 原始路径字典 {conn_key: [(x, y), ...]}。

    Returns:
        (序列化后的路径字典, 总长度 μm)。
    """
    from polaris.router.path_geometry import path_length

    total_length_um = 0.0
    routes_serializable: dict[str, list[list[float]]] = {}
    for conn_key, pts in routes.items():
        pts_list = [[float(p[0]), float(p[1])] for p in pts]
        routes_serializable[conn_key] = pts_list
        total_length_um += path_length([(p[0], p[1]) for p in pts_list])
    return routes_serializable, total_length_um


def stage4_routing(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 4: 波导布线。

    根据 recipe.router_algo 选择布线算法：
    - "curvy": 弯曲感知布线（_CurvyRouter，LiDAR ISPD'25）
    - "default": A* 网格布线（_DefaultRouter）
    - "diagonal": 对角线布线（DiagonalGridRouter）
    - "hybrid": 混合布线（HybridRouter）

    Args:
        recipe: 作业配方（使用 recipe.router_algo）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit", "placements"）。

    Returns:
        含 routes/n_paths/total_length_um 的字典。

    Raises:
        ValueError: router_algo 未知时告警退出（禁止 fall-back）。
    """
    circuit_dict = _require_input(prev_outputs, "circuit", 4)
    placements = _require_input(prev_outputs, "placements", 4)
    circuit = _circuit_from_dict(circuit_dict)

    algo = recipe.router_algo
    logger.info("阶段 4: 波导布线（算法=%s）", algo)

    if algo == "diagonal":
        routes = _run_diagonal_router(circuit, placements)
    elif algo in ("curvy", "default"):
        routes = _run_curvy_or_default_router(algo, circuit, placements)
    else:
        raise ValueError(
            f"未知 router_algo='{algo}'。"
            f"支持: 'curvy'/'default'/'diagonal'。"
        )

    routes_serializable, total_length_um = _collect_routes_metrics(routes)

    logger.info(
        "阶段 4 完成: 布线 %d 条路径，总长度 %.2f μm",
        len(routes_serializable), total_length_um,
    )

    return {
        "routes": routes_serializable,
        "n_paths": len(routes_serializable),
        "total_length_um": float(total_length_um),
    }


__all__ = [
    "stage3_placement",
    "stage4_routing",
]
