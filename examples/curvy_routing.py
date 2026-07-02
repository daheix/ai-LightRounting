"""R949-R950 曲线感知布线示例（v5.0 迁移至 polaris-route 子模块）。

演示：polaris-route 子模块的曲线波导布线能力:
- 高层 API: ``route_circuit(circuit, placements, mode='curvy')`` 对完整电路布线
- 底层 API: ``CurvyRouter`` + ``CurvyRouteConfig`` 对单条连接布线
- 路径损耗模型（传播 + 弯曲 + 交叉 + 器件插入损耗）
- 弯曲数 / 交叉数统计

v5.0 迁移说明:
- 旧 ``polaris.router.curvy_astar_core.CurvyAStarConfig/CurvyAStarRouter``
  → 新 ``polaris_route.route_circuit`` (高层) / ``polaris_route.CurvyRouter`` (底层)
- 旧 CurvyAStar 的 ``obstacles`` / ``n_directions`` 参数在新 CurvyRouter 中移除
  （新架构采用 step 拓扑 S-bend，弯曲数可解析，损耗可溯源，R03 禁止 fall-back）
- 障碍物绕行场景改为多连接电路的交叉检测场景（新架构用 ``count_crossings``
  统计路径间交叉，而非绕行预定义障碍物）

学术依据（R02 学术诚信，≥5 个文献 URL）:
- LiDAR ISPD'25 §3.1-3.2（曲线感知 A* 布线）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 TCAD 2025（分层曲线波导详细布线）
  https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- Hart Nilsson Raphael 1968 IEEE SSC（A* 算法原始论文）
  https://doi.org/10.1109/TSSC.1968.300136
- SiEPIC EBeam PDK（bend_euler radius=5μm，0.05 dB/bend，0.3 dB/crossing）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref et al. 1993 IEEE Proc. 41(9)（SOI 3 dB/cm 传播损耗基准）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Klauss et al. 2018 Opt Express（Euler spiral 波导弯曲）
  https://doi.org/10.1364/OE.26.029637

运行: python examples/curvy_routing.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# v5.0 子模块 sys.path 注入（指向 modules/route/src）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules/route/src"))

from polaris_route import (
    CurvyRouteConfig,
    CurvyRouter,
    count_crossings,
    path_length,
    route_circuit,
)


def main() -> None:
    """运行曲线感知布线示例。"""
    print("=== PoLaRIS v5.0 曲线波导布线（polaris-route）===")
    print(f"  布线模式: curvy (step 拓扑 S-bend)")
    print(f"  默认最小弯曲半径: {CurvyRouteConfig().min_bend_radius_um} μm")

    # ------------------------------------------------------------------
    # 场景1: 单直线连接电路（端口同 y 对齐 → 直线路径，0 弯曲）
    # ------------------------------------------------------------------
    print("\n--- 场景1: 直线布线电路（端口同 y 对齐）---")
    circuit1 = {
        "name": "straight_demo",
        "canvas_w": 100.0,
        "canvas_h": 50.0,
        "devices": [
            {
                "name": "gc1",
                "type": "grating_coupler",
                "ports": [("waveguide", 5, 5, "east")],
                "params": {"insertion_loss_db": 1.9},
            },
            {
                "name": "gc2",
                "type": "grating_coupler",
                "ports": [("waveguide", 0, 5, "west")],
                "params": {"insertion_loss_db": 1.9},
            },
        ],
        "connections": [["gc1", "waveguide", "gc2", "waveguide"]],
    }
    placements1 = {
        "gc1": {"x": 10.0, "y": 20.0, "w": 5.0, "h": 10.0},
        "gc2": {"x": 80.0, "y": 20.0, "w": 5.0, "h": 10.0},
    }
    result1 = route_circuit(circuit1, placements1, mode="curvy")
    p1 = result1["paths"][0]
    print(f"  路径点数: {len(p1['points'])}")
    print(f"  起终点: ({p1['points'][0][0]:.1f},{p1['points'][0][1]:.1f}) -> "
          f"({p1['points'][-1][0]:.1f},{p1['points'][-1][1]:.1f})")
    print(f"  路径长度: {path_length([tuple(pt) for pt in p1['points']]):.2f} μm")
    print(f"  弯曲数: {p1['n_bends']}（直线对齐应为 0）")
    print(f"  波导损耗: {p1['loss_db']:.4f} dB")

    # ------------------------------------------------------------------
    # 场景2: L 形连接电路（端口不同 x 不同 y → step 拓扑，2 弯曲）
    # ------------------------------------------------------------------
    print("\n--- 场景2: L形布线电路（端口不同 y，step 拓扑 S-bend）---")
    circuit2 = {
        "name": "l_shape_demo",
        "canvas_w": 100.0,
        "canvas_h": 100.0,
        "devices": [
            {
                "name": "gc1",
                "type": "grating_coupler",
                "ports": [("waveguide", 5, 5, "east")],
                "params": {"insertion_loss_db": 1.9},
            },
            {
                "name": "gc2",
                "type": "grating_coupler",
                "ports": [("waveguide", 0, 0, "west")],
                "params": {"insertion_loss_db": 1.9},
            },
        ],
        "connections": [["gc1", "waveguide", "gc2", "waveguide"]],
    }
    placements2 = {
        "gc1": {"x": 10.0, "y": 60.0, "w": 5.0, "h": 10.0},
        "gc2": {"x": 70.0, "y": 10.0, "w": 5.0, "h": 10.0},
    }
    result2 = route_circuit(circuit2, placements2, mode="curvy")
    p2 = result2["paths"][0]
    pts2 = [tuple(pt) for pt in p2["points"]]
    print(f"  路径点数: {len(p2['points'])}")
    print(f"  路径长度: {path_length(pts2):.2f} μm")
    # 曼哈顿距离 = |dx| + |dy|
    dx = p2["points"][-1][0] - p2["points"][0][0]
    dy = p2["points"][-1][1] - p2["points"][0][1]
    print(f"  曼哈顿距离: {abs(dx) + abs(dy):.2f} μm（step 拓扑长度≈曼哈顿距离）")
    print(f"  弯曲数: {p2['n_bends']}（step 拓扑应为 2）")
    print(f"  波导损耗: {p2['loss_db']:.4f} dB（含 2 弯 × 0.05 dB + 传播 + gc2 插损）")

    # ------------------------------------------------------------------
    # 场景3: MZI 风格多连接电路（演示交叉检测 + 电路级总损耗汇总）
    # ------------------------------------------------------------------
    print("\n--- 场景3: MZI 风格多连接电路（交叉检测 + 总损耗汇总）---")
    circuit3 = {
        "name": "mzi_demo",
        "canvas_w": 200.0,
        "canvas_h": 100.0,
        "devices": [
            {
                "name": "gc_in",
                "type": "grating_coupler",
                "ports": [("waveguide", 5, 5, "east")],
                "params": {"insertion_loss_db": 1.9},
            },
            {
                "name": "mmi1",
                "type": "mmi_1x2",
                "ports": [
                    ("in", 0, 5, "west"),
                    ("out1", 10, 8, "east"),
                    ("out2", 10, 2, "east"),
                ],
                "params": {"insertion_loss_db": 0.4},
            },
            {
                "name": "mmi2",
                "type": "mmi_2x2",
                "ports": [
                    ("in1", 0, 8, "west"),
                    ("in2", 0, 2, "west"),
                    ("out1", 10, 5, "east"),
                ],
                "params": {"insertion_loss_db": 0.5},
            },
            {
                "name": "gc_out",
                "type": "grating_coupler",
                "ports": [("waveguide", 0, 5, "west")],
                "params": {"insertion_loss_db": 1.9},
            },
        ],
        "connections": [
            ["gc_in", "waveguide", "mmi1", "in"],
            ["mmi1", "out1", "mmi2", "in1"],
            ["mmi1", "out2", "mmi2", "in2"],
            ["mmi2", "out1", "gc_out", "waveguide"],
        ],
    }
    placements3 = {
        "gc_in": {"x": 10.0, "y": 50.0, "w": 5.0, "h": 10.0},
        "mmi1": {"x": 50.0, "y": 50.0, "w": 10.0, "h": 10.0},
        "mmi2": {"x": 130.0, "y": 50.0, "w": 10.0, "h": 10.0},
        "gc_out": {"x": 180.0, "y": 50.0, "w": 5.0, "h": 10.0},
    }
    result3 = route_circuit(circuit3, placements3, mode="curvy")
    print(f"  连接数: {len(result3['paths'])}")
    print(f"  总弯曲数: {result3['n_bends']}")
    print(f"  总交叉对数: {result3['n_crossings']}")
    print(f"  电路总损耗: {result3['total_loss_db']:.4f} dB")
    print(f"  布线器类型: {result3['router_type']}")
    # 验证: 逐路径打印
    for i, p in enumerate(result3["paths"]):
        print(f"  路径{i+1}: {p['dev1']}.{p['port1']} -> {p['dev2']}.{p['port2']}, "
              f"长度={path_length([tuple(pt) for pt in p['points']]):.2f} μm, "
              f"弯曲={p['n_bends']}, 交叉={p['n_crossings']}, 损耗={p['loss_db']:.4f} dB")

    # ------------------------------------------------------------------
    # 场景4: CurvyRouter 底层 API + 不同 min_bend_radius 配置对比
    # ------------------------------------------------------------------
    print("\n--- 场景4: CurvyRouter 底层 API + 不同最小弯曲半径配置 ---")
    start = (0.0, 0.0)
    end = (40.0, 30.0)
    for radius in [5.0, 10.0, 20.0]:
        config = CurvyRouteConfig(min_bend_radius_um=radius, n_curve_points=20)
        router = CurvyRouter(config)
        path = router.route(start, end)
        # 用 count_crossings 自检（单路径不交叉）
        self_cross_check = count_crossings(path, path)
        print(f"  min_bend_radius={radius:>5.1f}μm: 路径点数={len(path)}, "
              f"长度={path_length(path):.2f} μm, "
              f"自交叉={self_cross_check}（应为0）")

    # 场景5: 同点/对齐边界情况验证（R03 禁止 fall-back，边界必须正确处理）
    print("\n--- 场景5: 边界情况（同点 + 对齐）---")
    router_default = CurvyRouter()
    same_point = router_default.route((5.0, 5.0), (5.0, 5.0))
    aligned = router_default.route((0.0, 10.0), (50.0, 10.0))
    print(f"  同点路径: {len(same_point)} 点（零长路径，2 点保底）")
    print(f"  对齐路径: {len(aligned)} 点（同 y 直线，2 点）")


if __name__ == "__main__":
    main()
