/**
 * @file route.h
 * @brief PoLaRIS polaris-route 子模块 C ABI 接口声明
 *
 * 与 Python API（route_circuit/compute_path_loss）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h
 * （polaris_circuit_t / polaris_placement_result_t / polaris_routing_result_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_routing_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - mode 非法返回 POLARIS_ERR_INVALID
 *   - circuit/placements 结构非法返回 POLARIS_ERR_INVALID
 *   - 布线失败（如端口缺失）返回 POLARIS_ERR_NOTFOUND
 *
 * 来源（R02 学术诚信）:
 * - LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）
 *   https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
 * - LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing（TCAD 2025）
 *   https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
 * - SiEPIC EBeam PDK（bend_euler radius=5μm，0.05 dB/bend 上界，0.3 dB/crossing）
 *   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Klauss et al., "Euler spiral waveguide bends", Opt Express 2018
 *   https://doi.org/10.1364/OE.26.029637
 * - Fujisawa et al. 2017, "Euler bend clothoid curve low-loss waveguide"
 *   (Optics Express 25(8) 9150) https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
 * - Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm 传播损耗基准）
 *   https://ieeexplore.ieee.org/document/1148303
 * - Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
 *   https://www.cambridge.org/core/books/silicon-photonics-design/
 */
#ifndef POLARIS_ROUTE_H
#define POLARIS_ROUTE_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_route_circuit: 对已布局电路执行布线
 * @param circuit 电路规格
 * @param placements 布局结果
 * @param mode 布线模式 "curvy"
 * @param out 输出布线结果
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_route_circuit(
    const polaris_circuit_t* circuit,
    const polaris_placement_result_t* placements,
    const char* mode,
    polaris_routing_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
