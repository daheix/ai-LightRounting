"""R949-R950 曲线感知 A* 布线示例。

演示：CurvyAStarRouter 弯曲半径约束布线 + 障碍物绕行 + 路径平滑。

学术依据（R02）：
- LiDAR ISPD'25 §3.1-3.2（曲线感知 A* 布线）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Hart Nilsson Raphael 1968 IEEE SSC（A* 算法原始论文）
  https://doi.org/10.1109/TSSC.1968.300136
- SOI 波导最小弯曲半径约束: Chrostowski & Hochberg 2015 §3.3

运行: PYTHONPATH=src python examples/curvy_routing.py
"""

from __future__ import annotations

import numpy as np

from polaris.router.curvy_astar_core import CurvyAStarConfig, CurvyAStarRouter


def main() -> None:
    """运行曲线感知 A* 布线示例。"""
    # SOI 平台典型配置：5μm 弯曲半径，1μm 网格
    config = CurvyAStarConfig(
        grid_size=1.0,
        bend_radius=5.0,
        n_directions=8,
        w_bend=1.0,
        w_length=1.0,
        w_cross=10.0,
    )
    router = CurvyAStarRouter(config)

    print("=== 曲线感知 A* 布线 ===")
    print(f"  网格: {config.grid_size}μm, 弯曲半径: {config.bend_radius}μm, "
          f"方向数: {config.n_directions}")

    # 1) 简单直线路径
    print("\n--- 场景1: 直线布线 (0,0) -> (50,0) ---")
    path1 = router.route(start=(0.0, 0.0), end=(50.0, 0.0))
    print(f"  路径点数: {len(path1)}")
    print(f"  起终点: {path1[0]} -> {path1[-1]}")
    print(f"  路径长度: {_path_length(path1):.2f} μm")

    # 2) L 形路径（含一次转弯）
    print("\n--- 场景2: L形布线 (0,0) -> (30,40) ---")
    path2 = router.route(start=(0.0, 0.0), end=(30.0, 40.0))
    print(f"  路径点数: {len(path2)}")
    print(f"  路径长度: {_path_length(path2):.2f} μm")
    print(f"  曼哈顿距离: {abs(30) + abs(40):.2f} μm")

    # 3) 带障碍物的绕行
    print("\n--- 场景3: 障碍物绕行 (0,0) -> (50,0)，中间有障碍 ---")
    obstacles = [(20.0, -5.0, 10.0, 10.0)]  # (x, y, w, h)
    path3 = router.route(start=(0.0, 0.0), end=(50.0, 0.0), obstacles=obstacles)
    print(f"  障碍物: {obstacles}")
    print(f"  路径点数: {len(path3)}")
    print(f"  路径长度: {_path_length(path3):.2f} μm (绕行比直线长)")
    # 验证路径不穿过障碍物
    _verify_no_obstacle_collision(path3, obstacles)

    # 4) 多方向（16方向）更平滑路径
    print("\n--- 场景4: 16方向平滑布线 ---")
    config16 = CurvyAStarConfig(
        grid_size=1.0, bend_radius=5.0, n_directions=16, w_cross=10.0
    )
    router16 = CurvyAStarRouter(config16)
    path4 = router16.route(start=(0.0, 0.0), end=(25.0, 25.0))
    print(f"  路径点数: {len(path4)}")
    print(f"  路径长度: {_path_length(path4):.2f} μm")


def _path_length(path: list[tuple[float, float]]) -> float:
    """计算路径总长度（μm）。"""
    total = 0.0
    for i in range(1, len(path)):
        dx = path[i][0] - path[i - 1][0]
        dy = path[i][1] - path[i - 1][1]
        total += float(np.hypot(dx, dy))
    return total


def _verify_no_obstacle_collision(
    path: list[tuple[float, float]],
    obstacles: list[tuple[float, float, float, float]],
) -> None:
    """验证路径不与障碍物相交。"""
    for x, y in path:
        for ox, oy, ow, oh in obstacles:
            if ox <= x <= ox + ow and oy <= y <= oy + oh:
                raise AssertionError(f"路径点 ({x},{y}) 落入障碍物内")
    print("  障碍物规避验证通过 ✓")


if __name__ == "__main__":
    main()
