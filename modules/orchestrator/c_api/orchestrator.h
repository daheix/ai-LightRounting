#ifndef POLARIS_ORCHESTRATOR_H
#define POLARIS_ORCHESTRATOR_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_orchestrator_run_eda_flow: 一键运行完整 EDA 流程
 *
 * 9 个 stage 顺序执行（对应 9 个子模块，polaris_pdk 用于 stage 1，polaris_gdsio 用于 stage 7）:
 *   1. PDK 目录           (polaris_pdk.list_platforms)
 *   2. 电路验证           (polaris_core.validate_circuit)
 *   3. AI 布局            (polaris_place.place_circuit mode="analytical")
 *   4. 智能布线           (polaris_route.route_circuit)
 *   5. 仿真验证           (polaris_sim.simulate_mzi_sparam +
 *                          compute_clements_unitary + simulate_pam4)
 *   6. DRC / LVS          (polaris_drc.run_drc + polaris_lvs.run_lvs)
 *   7. GDS 导出           (polaris_gdsio.export_gds)
 *   8. 逆向设计           (polaris_inverse.optimize_waveguide_width
 *                          n_iterations=10 省时)
 *   9. 量子验证           (polaris_quantum.klm_cnot + hom_interference)
 *
 * 默认 strict=False: 某 stage 失败仅记录 error 但不中断（编排策略，
 * 非 R03 业务 fall-back；子模块内部仍禁止 fall-back）。
 *
 * @param circuit 电路规格（polaris_circuit_t）
 * @param output_dir 输出目录路径（GDS 等产物落盘位置）
 * @param out 输出结果（JSON 含 stages / n_success / n_failed / total_duration）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_orchestrator_run_eda_flow(
    const polaris_circuit_t* circuit,
    const char* output_dir,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_ORCHESTRATOR_H */
