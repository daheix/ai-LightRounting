#ifndef POLARIS_KLM_H
#define POLARIS_KLM_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_klm_cnot: KLM CNOT 门（Ralph 2002 简化 4-BS 电路）
 * Input:
 *   无（固定电路，参数来自 Ralph 2002 PRA 65, 062324）
 * Process:
 *   4 模式 (control/target/aux1/aux2) 4 个分束器:
 *     θ₁=θ₂=arccos(√(2/3)), θ₃=π/4, θ₄=arccos(√(1/3))
 *   验证电路酉性 U·U† = I（误差 < 1e-10）。
 * Output:
 *   out->json   JSON 含 success_prob (=1/9≈0.1111) / verified (true)
 * 参考: Ralph et al., PRA 65, 062324 (2002), 表 I.
 *       https://doi.org/10.1103/PhysRevA.65.062324
 * @return POLARIS_OK 或 POLARIS_ERR_VERIFICATION（酉性校验失败）
 */
polaris_error_t polaris_klm_cnot(polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_KLM_H */
