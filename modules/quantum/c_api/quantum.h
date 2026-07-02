#ifndef POLARIS_QUANTUM_H
#define POLARIS_QUANTUM_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_quantum_boson_sampling: 玻色采样
 * @param unitary 酉矩阵（一维展开，row-major，n*n*2 个 double，实虚交错）
 * @param n_modes 模式数
 * @param input_state 输入光子态（长度 n_modes）
 * @param out 输出结果（JSON 含 prob_distribution/prob_sum）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_quantum_boson_sampling(
    const double* unitary, int32_t n_modes,
    const int32_t* input_state,
    polaris_result_t* out
);

/* polaris_quantum_klm_cnot: KLM CNOT 门
 * @param out 输出结果（JSON 含 success_prob/verified）
 * @return POLARIS_OK
 */
polaris_error_t polaris_quantum_klm_cnot(polaris_result_t* out);

/* polaris_quantum_hom: HOM 干涉
 * @param theta 分束器角度
 * @param out 输出结果（JSON 含 coincidence_prob/dip_depth/verified）
 * @return POLARIS_OK
 */
polaris_error_t polaris_quantum_hom(double theta, polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif
