/**
 * @file optimizer.h
 * @brief PoLaRIS 优化器子模块 C ABI（polaris-optimizer）
 *
 * 单一职责: 12 种优化器的统一 C 接口（拓扑/水平集/L-BFGS/PSO/CMA-ES/
 *           NSGA-2/NSGA-3/鲁棒/多目标/密度伴随/形状伴随/反馈适配）。
 *
 * IPO 三段式设计:
 * - Input:  polaris_tensor_t 设计变量初值 + polaris_result_t 配置 JSON
 * - Process: 调用对应优化器迭代（NumPy/SciPy/JAX-CPU，R04 不参与 GPU）
 * - Output:  polaris_result_t JSON 含 optimal_params/optimal_fom/fom_history
 *
 * 设计原则:
 * - Python 函数 ↔ C 函数一一对应（polaris_optimizer_<method>）
 * - 失败即返回非 0 错误码（R03 禁止 fall-back）
 * - 纯数据结构跨语言传递，无 Python 对象泄漏
 *
 * 学术诚信（R02，≥5 文献 URL 溯源）:
 * - Liu & Nocedal 1989 L-BFGS: https://doi.org/10.1007/BF01589116
 * - Hansen & Ostermeier 2001 CMA-ES: https://doi.org/10.1162/106365601750190398
 * - Deb et al. 2002 NSGA-II: https://doi.org/10.1109/4235.996017
 * - Deb & Jain 2014 NSGA-III: https://doi.org/10.1109/TEVC.2013.2281535
 * - Osher & Sethian 1988 Level Set: https://doi.org/10.1016/S0021-9991(88)80002-2
 * - Wang et al. 2018 Robust photonic TO: https://doi.org/10.1364/OE.26.023273
 * - Piggott 2017 Nature Photonics: https://www.nature.com/articles/nphoton.2017.102
 */
#ifndef POLARIS_OPTIMIZER_H
#define POLARIS_OPTIMIZER_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * L-BFGS 拟牛顿局部优化（Liu & Nocedal 1989）
 * ========================================================================= */
/* polaris_optimizer_lbfgs: L-BFGS 优化器
 * Input:
 *   initial_params  初始参数向量（polaris_tensor_t，1D float64）
 *   fom_grad_json   JSON 含 fom_fn/grad_fn 句柄或回调描述
 *   config_json     JSON 含 max_iterations/memory_size/convergence_threshold
 * Process:
 *   两循环递归近似逆 Hessian，Wolfe 线搜索步长（最大化 FoM）。
 * Output:
 *   out->json  含 optimal_params/optimal_fom/fom_history/iterations/converged
 * 参考: Liu & Nocedal 1989, https://doi.org/10.1007/BF01589116
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID/POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_optimizer_lbfgs(
    const polaris_tensor_t* initial_params,
    const char* fom_grad_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * PSO 粒子群全局优化（Kennedy & Eberhart 1995）
 * ========================================================================= */
polaris_error_t polaris_optimizer_pso(
    const polaris_tensor_t* initial_pos,
    const char* fom_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * CMA-ES 协方差矩阵自适应进化策略（Hansen & Ostermeier 2001）
 * ========================================================================= */
polaris_error_t polaris_optimizer_cmaes(
    const polaris_tensor_t* initial_mean,
    const char* fom_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * NSGA-II 多目标优化（Deb et al. 2002）
 * ========================================================================= */
polaris_error_t polaris_optimizer_nsga2(
    int32_t n_params,
    const char* objectives_json,
    const char* fom_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * NSGA-III 参考点法多目标优化（Deb & Jain 2014）
 * ========================================================================= */
polaris_error_t polaris_optimizer_nsga3(
    int32_t n_params,
    const char* objectives_json,
    const char* fom_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * 拓扑优化（水平集 + Hamilton-Jacobi，Osher & Sethian 1988）
 * ========================================================================= */
polaris_error_t polaris_optimizer_topology(
    const polaris_tensor_t* initial_level_set,
    const char* fom_grad_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * 鲁棒性优化（蒙特卡洛公差扰动，Wang et al. 2018）
 * ========================================================================= */
polaris_error_t polaris_optimizer_robust(
    const polaris_tensor_t* initial_params,
    const char* fom_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * 形状伴随优化（参数化几何 + Adam，lumopt 风格）
 * ========================================================================= */
polaris_error_t polaris_optimizer_shape_adjoint(
    const polaris_tensor_t* initial_params,
    const char* fom_grad_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * 密度法拓扑伴随优化（JAX autograd，Piggott 2017）
 * 注: 需安装 polaris-optimizer[density]（jax + gdstk）
 * ========================================================================= */
polaris_error_t polaris_optimizer_density_adjoint(
    const char* objective_json,
    const char* config_json,
    polaris_result_t* out);

/* =========================================================================
 * 反馈适配器（约束违规 → 布局布线建议）
 * ========================================================================= */
polaris_error_t polaris_optimizer_feedback(
    const char* violations_json,
    polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_OPTIMIZER_H */
