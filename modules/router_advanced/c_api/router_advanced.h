/**
 * @file router_advanced.h
 * @brief PoLaRIS polaris-router-advanced 子模块 C ABI 接口声明
 *
 * 与 Python API（JPSRouter/AllAngleRouter/route_bundle/EulerBend/
 * CurvyAStarRouter/GlobalRouter 等）一一对应。类型定义见
 * ../_c_abi/polaris_types.h（polaris_circuit_t / polaris_placement_result_t /
 * polaris_routing_result_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_routing_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 网格/画布结构非法返回 POLARIS_ERR_INVALID
 *   - 无可行路径返回 POLARIS_ERR_NOTFOUND（R03 禁止 fall-back，不返回空路径）
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Harabor & Grastien, "Online Graph Pruning for Pathfinding on Grid Maps",
 *   AAAI 2011（JPS 跳点搜索）
 *   https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
 * - LiDAR: Automated Curvy Waveguide Detailed Routing, ISPD 2025
 *   https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
 * - Dubins, American J. Math. 1957, 79(3):497-516（Dubins 路径）
 *   https://www.jstor.org/stable/2372560
 * - Hong et al., Photonics Research 2021（欧拉弯曲超低损耗）
 *   https://doi.org/10.1364/PRJ.437726
 * - Synopsys OptoDesigner Advanced Connectors Module
 *   https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
 * - gdsfactory routing strategies
 *   https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html
 * - Hart, Nilsson & Raphael, IEEE SSSC 1968（A* 搜索）
 *   https://ieeexplore.ieee.org/document/4082128
 * - Fujisawa et al., Optics Express 25(8) 9150, 2017（欧拉弯曲损耗模型）
 *   https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
 * - Ghione & Naldi, IEEE TMTT 35(3) 1987（RF GSG 电极模型）
 *   https://doi.org/10.1109/TMTT.1987.1133623
 */
#ifndef POLARIS_ROUTER_ADVANCED_H
#define POLARIS_ROUTER_ADVANCED_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_router_jps: JPS 跳点搜索网格布线（Harabor 2011）
 * @param grid_w/grid_h 网格宽高
 * @param start/goal 起止网格坐标
 * @param out 输出布线结果
 * @return POLARIS_OK 或错误码（无可行路径返回 POLARIS_ERR_NOTFOUND）
 */
polaris_error_t polaris_router_jps(
    int grid_w, int grid_h,
    polaris_point_t start, polaris_point_t goal,
    polaris_routing_result_t* out
);

/* polaris_router_all_angle: 任意角度欧拉弯曲布线
 * @param start_port/end_port 起止端口 (x, y, angle_deg)
 * @param bend_radius 欧拉弯曲半径 (μm)
 * @param out 输出布线结果
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_router_all_angle(
    polaris_port_t start_port, polaris_port_t end_port,
    float bend_radius,
    polaris_routing_result_t* out
);

/* polaris_router_bundle: Bundle 并行等长布线
 * @param ports1/ports2 端口对数组（长度 n）
 * @param n 端口对数
 * @param separation 波导间距 (μm)
 * @param out 输出布线结果
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_router_bundle(
    const polaris_port_t* ports1, const polaris_port_t* ports2, int n,
    float separation,
    polaris_routing_result_t* out
);

/* polaris_router_euler_bend: 欧拉弯曲连接器路径生成（Hong 2021）
 * @param radius 有效弯曲半径 (μm)
 * @param angle 弯曲角度 (度)
 * @param out 输出路径点序列
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_router_euler_bend(
    float radius, float angle,
    polaris_path_t* out
);

/* polaris_router_curvy_astar: CurvyA* 曲线感知布线（LiDAR ISPD'25）
 * @param start/end 起止坐标 (μm)
 * @param min_bend_radius 最小弯曲半径 (μm)
 * @param out 输出布线结果
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_router_curvy_astar(
    polaris_point_t start, polaris_point_t end,
    float min_bend_radius,
    polaris_routing_result_t* out
);

/* polaris_router_global: Global GCell 全局布线
 * @param circuit 电路规格
 * @param placements 布局结果
 * @param out 输出布线结果
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_router_global(
    const polaris_circuit_t* circuit,
    const polaris_placement_result_t* placements,
    polaris_routing_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
