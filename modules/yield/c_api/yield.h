#ifndef POLARIS_YIELD_H
#define POLARIS_YIELD_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 回调函数指针类型（C ABI 风格，与 polaris_types.h POD 原则一致）
 *
 * 宿主（Python 等）注册回调，C 侧通过指针调用，避免 Python 对象泄漏。
 * ========================================================================= */

/* 标量仿真函数 f(params: (d,)) -> scalar */
typedef double (*polaris_yield_scalar_fn)(const double* params, int32_t d);

/* 失效区域指示函数 A: params -> bool（1=失效，0=合格） */
typedef int32_t (*polaris_yield_failure_fn)(const double* params, int32_t d);

/* 规格函数 output -> bool（1=满足规格） */
typedef int32_t (*polaris_yield_spec_fn)(double output);


/* polaris_yield_monte_carlo: 蒙特卡洛仿真（Metropolis & Ulam 1949）
 * Input:
 *   func           标量仿真函数指针 f(params) -> output
 *   base_params    标称参数 (d,)
 *   d              参数维度
 *   n_samples      采样数
 *   sigma          参数相对标准差
 *   seed           随机种子
 * Process:
 *   params_i = base · (1 + σ · ε_i), ε_i ~ N(0,1)（NumPy 向量化并行）。
 *   逐样本评估 func，统计 mean/std/min/max/p05/p95。
 * Output:
 *   out->json      JSON 含 samples / mean / std / min / max /
 *                  percentile_05 / percentile_95 / n_samples
 * 参考: https://doi.org/10.1080/01621459.1949.10483310
 * @return POLARIS_OK 或 POLARIS_ERR_SIMULATION（func 评估失败，R03 禁止 fall-back）
 */
polaris_error_t polaris_yield_monte_carlo(
    polaris_yield_scalar_fn func,
    const double* base_params, int32_t d,
    int32_t n_samples, double sigma, int32_t seed,
    polaris_result_t* out
);

/* polaris_yield_qmc: QMC 准随机蒙特卡洛（Sobol 1967 / Halton 1960 / LHS McKay 1979）
 * Input:
 *   func           标量仿真函数指针
 *   distributions  参数分布规格 JSON 数组
 *                  [{"type":"norm"|"uniform","loc":,"scale":}, ...]
 *   d              参数维度
 *   n_samples      样本数（Sobol 必须为 2 的幂）
 *   sampler_type   0=LHS, 1=Sobol, 2=Halton
 *   seed           随机种子
 * Process:
 *   1. 生成低偏差准随机样本 (n,d) ∈ [0,1]²
 *   2. 逆变换采样 X = F⁻¹(U) 转换为目标分布
 *   3. 逐样本评估 func，统计 mean/std
 *   收敛速率: O(N⁻¹ logᵈ N) vs 朴素 MC O(N⁻¹ᐟ²)
 * Output:
 *   out->json      JSON 含 outputs / mean / std / n_samples /
 *                  discrepancy (星偏差) / sampler_type
 * 参考: https://doi.org/10.1016/0041-5553(67)90144-9
 *        https://doi.org/10.1080/00401706.1979.10489755
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_yield_qmc(
    polaris_yield_scalar_fn func,
    const char* distributions, int32_t d,
    int32_t n_samples, int32_t sampler_type, int32_t seed,
    polaris_result_t* out
);

/* polaris_yield_importance_sampling: 稀有事件良率 IS 估计（Glynn-Iglehart 1989）
 * Input:
 *   failure        失效区域指示函数指针 A: params -> bool
 *   nominal_dist   标称分布 JSON [{"type":"norm"|"uniform",...}]
 *   biasing_spec   偏置规格 JSON {"method":"mean_shift"|"variance_scaling"|
 *                  "exponential_twist"|"mixture"|"cross_entropy", ...}
 *   d              参数维度
 *   n_samples      样本数（典型 10⁴-10⁵）
 *   seed           随机种子
 * Process:
 *   偏置分布 q 偏向失效区采样，似然比 W=f/q 修正权重，
 *   Ŷ = mean(𝟙_A · W)，ESS=(ΣW)²/ΣW² 退化即 raise（R03）。
 *   典型 10²-10⁴ 倍方差缩减（vs 朴素 MC）。
 * Output:
 *   out->json      JSON 含 yield_estimate / std_error / relative_error /
 *                  ci_lower / ci_upper / effective_sample_size /
 *                  speedup_vs_mc / n_failures / biasing_method
 * 参考: https://doi.org/10.1287/mnsc.35.11.1367
 *        https://doi.org/10.1007/978-0-387-21617-1 (Glasserman 2003 Ch.4)
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_yield_importance_sampling(
    polaris_yield_failure_fn failure,
    const char* nominal_dist, const char* biasing_spec,
    int32_t d, int32_t n_samples, int32_t seed,
    polaris_result_t* out
);

/* polaris_yield_stratified: 分层采样蒙特卡洛（Cochran 1977 / Neyman 1934）
 * Input:
 *   func           标量仿真函数指针
 *   nominal_dist   标称分布 JSON
 *   d              参数维度
 *   n_strata       层数 H
 *   n_samples      总样本数 n
 *   strategy       0=EQUAL, 1=PROPORTIONAL, 2=NEYMAN (两阶段)
 *   seed           随机种子
 * Process:
 *   等概率分层 bₖ=F⁻¹(k/H) → 按策略分配 nₕ → 层内逆变换采样 →
 *   μ̂ = Σ Wₕ·μ̂ₕ (Wₕ=1/H) → Var = Σ Wₕ²·σₕ²/nₕ。
 *   NEYMAN 两阶段: pilot EQUAL 估计 σ̂ₕ → main Neyman 分配。
 * Output:
 *   out->json      JSON 含 estimate / std_error / relative_error /
 *                  ci_lower / ci_upper / n_strata / n_per_stratum /
 *                  strata_means / strata_stds / variance_estimate /
 *                  variance_naive_mc / speedup_vs_mc
 * 参考: https://doi.org/10.2307/2342192 (Neyman 1934)
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_yield_stratified(
    polaris_yield_scalar_fn func,
    const char* nominal_dist, int32_t d,
    int32_t n_strata, int32_t n_samples, int32_t strategy, int32_t seed,
    polaris_result_t* out
);

/* polaris_yield_wcd: 最坏情况距离 + 良率估计（Madkour 2015）
 * Input:
 *   func           标量仿真函数指针
 *   base_params    标称参数 (d,)
 *   param_sigmas   每参数容差 σ_i (d,)
 *   d              维度
 *   spec_threshold 规格阈值 T
 *   direction      0=lower (f≥T 合格), 1=upper (f≤T 合格)
 * Process:
 *   中心差分计算灵敏度 S_i = ∂f/∂x_i；
 *   一阶方差传播 σ_f = sqrt(Σ (S_i σ_i)²)；
 *   d_wc = |μ_f - T| / σ_f (lower) 或 |T - μ_f| / σ_f (upper)；
 *   Y ≈ Φ(d_wc)（正态假设）。
 *   d_wc=3 → Y≈99.865% (3σ); d_wc=6 → Y≈99.9999998% (6σ)。
 * Output:
 *   out->json      JSON 含 wcd / yield_estimate / f_nominal /
 *                  sigma_output / spec_threshold / direction /
 *                  n_evaluations
 * 参考: https://doi.org/10.1109/TCSI.2015.2495251
 *        https://doi.org/10.1080/03052159308940948 (Parkinson 1993)
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_yield_wcd(
    polaris_yield_scalar_fn func,
    const double* base_params, const double* param_sigmas,
    int32_t d, double spec_threshold, int32_t direction,
    polaris_result_t* out
);

/* polaris_yield_allocate_tolerance: Taguchi 容差分配（Singhal-Pinel 1981）
 * Input:
 *   sensitivities  参数灵敏度 |∂f/∂x_i| (n,)
 *   n              参数数
 *   total_budget   总容差预算 B = Σ σ_i²
 * Process:
 *   Lagrange 解: σ_i² = B · (1/S_i²) / Σ(1/S_j²)，即 σ_i ∝ 1/|S_i|。
 *   高灵敏度参数给小容差（控制），低灵敏度参数放宽（节省成本）。
 * Output:
 *   out->json      JSON 含 param_names / sensitivities /
 *                  allocated_sigmas / total_budget /
 *                  expected_variance_output / variance_reduction
 * 参考: https://doi.org/10.1109/TCS.1981.1085043
 *        https://www.itl.nist.gov/div898/handbook/pri/section5/pri56.htm
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID
 */
polaris_error_t polaris_yield_allocate_tolerance(
    const double* sensitivities, int32_t n, double total_budget,
    polaris_result_t* out
);

/* polaris_yield_batch_simulate: 批量蒙特卡洛（多标称点）
 * Input:
 *   func              标量仿真函数指针
 *   base_params_list  多标称点 JSON [[p1,...,pd], ...]
 *   param_sigmas      每参数相对标准差 (d,)
 *   d                 维度
 *   n_samples         每场景样本数
 *   seed              随机种子
 * Process:
 *   对每个标称点运行 n_samples 个参数扰动样本，统计输出分布。
 *   应用: 工艺角扫描 / 温度扫描 / 多芯片统计平均。
 * Output:
 *   out->json      JSON 含 scenarios[] / n_scenarios /
 *                  n_samples_per_scenario / total_evaluations /
 *                  execution_time_s
 * 参考: https://doi.org/10.2307/2280232
 *        https://fib.intec.ugent.be/download/pub_4125.pdf (Bogaerts 2018)
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_yield_batch_simulate(
    polaris_yield_scalar_fn func,
    const char* base_params_list, const double* param_sigmas,
    int32_t d, int32_t n_samples, int32_t seed,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_YIELD_H */
