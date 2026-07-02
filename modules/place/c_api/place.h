/**
 * @file place.h
 * @brief PoLaRIS polaris-place 子模块 C ABI 接口声明
 *
 * 与 Python API（place_circuit/compute_hpwl）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h
 * （polaris_circuit_t / polaris_placement_result_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_placement_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - ppo_gnn 模式无 checkpoint 返回 POLARIS_ERR_NOTFOUND
 *     （对应 Python 端 raise RuntimeError，R03 禁止 fall-back）
 *   - mode 非法返回 POLARIS_ERR_INVALID
 *
 * 来源:
 * - DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
 * - AlphaChip: Mirhoseini et al., Nature 2021
 *   https://www.nature.com/articles/s41586-021-03544-w
 * - HPWL 指标: Kahng & Lienig IEEE TCAD 2009
 *   https://ieeexplore.ieee.org/document/4685534
 * - numpy ndarray C API:
 *   https://numpy.org/doc/stable/reference/c-api/types-and-structures.html
 * - klayout db API:
 *   https://www.klayout.de/klayout.doc/programming/database_api.html
 */
#ifndef POLARIS_PLACE_H
#define POLARIS_PLACE_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_place_circuit: 对电路执行布局
 * @param circuit 电路规格
 * @param mode 布局模式 "analytical" 或 "ppo_gnn"
 * @param out 输出布局结果
 * @return POLARIS_OK 或错误码（ppo_gnn 无 checkpoint 返回 POLARIS_ERR_NOTFOUND）
 */
polaris_error_t polaris_place_circuit(
    const polaris_circuit_t* circuit,
    const char* mode,
    polaris_placement_result_t* out
);

/* polaris_place_compute_hpwl: 计算半周长线长
 * @param circuit 电路规格
 * @param placements 布局结果
 * @param hpwl_out 输出 HPWL 值
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_place_compute_hpwl(
    const polaris_circuit_t* circuit,
    const polaris_placement_result_t* placements,
    double* hpwl_out
);

#ifdef __cplusplus
}
#endif
#endif
