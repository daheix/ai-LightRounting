/**
 * @file inverse.h
 * @brief PoLaRIS polaris-inverse 子模块 C ABI 接口声明
 *
 * 与 Python API（optimize_waveguide_width）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_result_t / polaris_error_t POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - n_iterations/learning_rate 非法返回 POLARIS_ERR_INVALID
 *   - JAX 不可用或优化出现 NaN 返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Yee 1966 IEEE TAP "Numerical solution of initial boundary value problems
 *   involving Maxwell's equations in isotropic media"
 *   https://doi.org/10.1109/TAP.1966.1138693
 * - Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method"
 * - Mahau 2024 arXiv:2412.12360 "Differentiable FDTD for inverse design"
 *   https://arxiv.org/abs/2412.12360
 * - Polyak 1964 "Some methods of speeding up the convergence of iteration methods"
 * - Jensen & Sigmund 2011 "Topology optimization for nano-photonics"
 *   https://doi.org/10.1002/lpor.201000014
 * - lumopt（Lumerical 逆向设计）https://github.com/chriskeraly/lumopt
 * - Gedney 1996 IEEE TAP（单轴各向异性 PML）
 *   https://doi.org/10.1109/8.546249
 */
#ifndef POLARIS_INVERSE_H
#define POLARIS_INVERSE_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_inverse_optimize_width: JAX Adjoint 优化波导宽度
 * @param n_iterations 迭代次数（默认50）
 * @param learning_rate 学习率（默认0.5）
 * @param out 输出结果（JSON 含 initial_width_nm/optimal_width_nm/fom_history/converged/improvement_db）
 * @return POLARIS_OK 或 POLARIS_ERR_SIMULATION（如 JAX 不可用或 NaN）
 */
polaris_error_t polaris_inverse_optimize_width(
    int32_t n_iterations, double learning_rate,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
