/**
 * @file verify.h
 * @brief PoLaRIS polaris-verify 子模块 C ABI 接口声明
 *
 * 与 Python API（run_drc/run_lvs）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h
 * （polaris_circuit_t / polaris_placement_result_t / polaris_result_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - circuit/placements 结构非法返回 POLARIS_ERR_INVALID
 *   - DRC 违规不视为错误（返回 POLARIS_OK，违规信息在 out.json 中）
 *   - LVS 不一致不视为错误（返回 POLARIS_OK，不一致信息在 out.json 中）
 *   - 严重校验失败返回 POLARIS_ERR_VERIFICATION
 *
 * DRC 规则（12 条，基于 SiEPIC EBeam PDK）:
 *   min_spacing 1.0μm / min_width 0.5μm / min_height 0.4μm / min_area 0.1μm² /
 *   boundary / no_overlap / port_alignment(5μm) / port_direction /
 *   port_connectivity / port_facing / density_max(80%) / density_min(0.01%)
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH/WG_MIN_SPACE 等真实工艺规则）
 *   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
 *   https://www.cambridge.org/core/books/silicon-photonics-design/
 * - KLayout DRC 文档（width_check/space_check/area_check）
 *   https://www.klayout.org/doc-qt5/manual/drc_runsets.html
 * - KLayout LVS API（网表比对算法）
 *   https://www.klayout.org/doc-qt5/manual/lvs.html
 * - OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
 *   https://doi.org/10.1109/DAC56929.2023.10247734
 * - Banerjee, "CMOS Photonic Circuits", Springer 2024（CMP 密度规则）
 * - Berg et al. 2014, "Computational Geometry", Springer（AABB 几何）
 *   https://doi.org/10.1007/978-3-540-77974-2
 */
#ifndef POLARIS_VERIFY_H
#define POLARIS_VERIFY_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_verify_drc: 执行 DRC 设计规则检查
 * @param circuit 电路规格
 * @param placements 布局结果
 * @param out 输出结果（JSON 含 n_rules/n_violations/n_passed/pass_rate/violations）
 * @return POLARIS_OK 或 POLARIS_ERR_VERIFICATION
 *
 * DRC 违规不视为错误（POLARIS_OK），违规详情写入 out.json。
 * 仅当 circuit/placements 结构非法时返回 POLARIS_ERR_VERIFICATION。
 */
polaris_error_t polaris_verify_drc(
    const polaris_circuit_t* circuit,
    const polaris_placement_result_t* placements,
    polaris_result_t* out
);

/* polaris_verify_lvs: 执行 LVS 网表比对
 * @param circuit 电路规格
 * @param out 输出结果（JSON 含 is_consistent/n_mismatches/mismatches/n_devices/n_connections）
 * @return POLARIS_OK 或 POLARIS_ERR_VERIFICATION
 *
 * LVS 不一致不视为错误（POLARIS_OK），不一致详情写入 out.json。
 * 仅当 circuit 结构非法时返回 POLARIS_ERR_VERIFICATION。
 */
polaris_error_t polaris_verify_lvs(
    const polaris_circuit_t* circuit,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
