#ifndef POLARIS_BOSON_H
#define POLARIS_BOSON_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_boson_sampling: 玻色采样（Aaronson-Arkhipov 2011）
 * Input:
 *   unitary        酉矩阵（一维展开，row-major，n_modes*n_modes*2 个 double，
 *                  实虚交错，与 polaris_boson.clements_unitary 输出一致）
 *   n_modes        模式数 M
 *   input_state    输入光子态（长度 n_modes）
 * Process:
 *   Glynn-Gray 公式计算 permanent，遍历光子数守恒输出态，归一化校验。
 * Output:
 *   out->json      JSON 含 prob_distribution / prob_sum (=1.0) / n_outputs
 * 参考: https://arxiv.org/abs/0910.4698
 * @return POLARIS_OK 或错误码（POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION）
 */
polaris_error_t polaris_boson_sampling(
    const double* unitary, int32_t n_modes,
    const int32_t* input_state,
    polaris_result_t* out
);

/* polaris_boson_clements: Clements M×M 酉矩阵生成（Clements 2016）
 * Input:
 *   n_modes        模式数 M
 *   seed           随机种子（可复现）
 * Process:
 *   O(M²) 分束器 + 相移器，Clements 网格交替层，左乘酉保酉性。
 * Output:
 *   out->json      JSON 含 unitary (list[list[[real,imag]]]) /
 *                  unitarity_error (<1e-10) / is_unitary (true)
 * 参考: https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
 * @return POLARIS_OK 或 POLARIS_ERR_VERIFICATION（酉性校验失败）
 */
polaris_error_t polaris_boson_clements(
    int32_t n_modes, int32_t seed,
    polaris_result_t* out
);

/* polaris_boson_hom: HOM 双光子干涉（Hong-Ou-Mandel 1987）
 * Input:
 *   theta          可分辨性/时间延迟参数（θ=0 → 完全不可区分 → dip_depth=1.0）
 * Process:
 *   高斯波包重叠 overlap²(θ)=exp(-θ²/(2σ²))，P_coinc=0.5*(1-overlap²)。
 * Output:
 *   out->json      JSON 含 coincidence_prob / dip_depth / verified
 * 参考: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
 * @return POLARIS_OK
 */
polaris_error_t polaris_boson_hom(double theta, polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_BOSON_H */
