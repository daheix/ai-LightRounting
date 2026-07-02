/**
 * @file drc.h
 * @brief PoLaRIS polaris-drc 子模块 C ABI 接口声明（DRC 设计规则检查）
 *
 * Input → Process → Output 三段式：
 *
 * Input:
 *   - circuit: polaris_circuit_t* 电路规格（含 devices/connections/canvas_w/canvas_h）
 *   - placements: polaris_placement_result_t* 布局结果（{name: {x, y, w, h}}，μm）
 *
 * Process:
 *   12 条 SiEPIC EBeam PDK DRC 规则（min_spacing 1.0μm / min_width 0.5μm /
 *   min_height 0.4μm / min_area 0.1μm² / boundary / no_overlap /
 *   port_alignment(5μm) / port_direction / port_connectivity / port_facing /
 *   density_max(80%) / density_min(0.01%))，AABB 几何算法（Ericson §5.1.3）。
 *
 * Output:
 *   polaris_result_t* out，JSON 含:
 *     {
 *       "n_rules": int(12),
 *       "n_violations": int,
 *       "n_passed": int,
 *       "pass_rate": float,  // [0, 1]，1.0 表示 DRC clean
 *       "violations": list[dict]
 *     }
 *
 * 与 Python API（polaris_drc.run_drc）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - circuit/placements 结构非法返回 POLARIS_ERR_INVALID
 *   - DRC 违规不视为错误（返回 POLARIS_OK，违规信息在 out.json 中）
 *   - 严重校验失败返回 POLARIS_ERR_VERIFICATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH/WG_MIN_SPACE 等真实工艺规则）
 *   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
 *   https://www.cambridge.org/core/books/silicon-photonics-design/
 * - KLayout DRC 文档（width_check/space_check/area_check）
 *   https://www.klayout.org/doc-qt5/manual/drc_runsets.html
 * - OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
 *   https://doi.org/10.1109/DAC56929.2023.10247734
 * - Berg et al. 2014, "Computational Geometry", Springer（AABB 几何）
 *   https://doi.org/10.1007/978-3-540-77974-2
 * - Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离公式 §5.1.3）
 *   https://realtimecollisiondetection.net/
 */
#ifndef POLARIS_DRC_H
#define POLARIS_DRC_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_drc_run: 执行 DRC 设计规则检查
 * @param circuit 电路规格
 * @param placements 布局结果
 * @param out 输出结果（JSON 含 n_rules/n_violations/n_passed/pass_rate/violations）
 * @return POLARIS_OK 或 POLARIS_ERR_VERIFICATION
 *
 * DRC 违规不视为错误（POLARIS_OK），违规详情写入 out.json。
 * 仅当 circuit/placements 结构非法时返回 POLARIS_ERR_VERIFICATION。
 */
polaris_error_t polaris_drc_run(
    const polaris_circuit_t* circuit,
    const polaris_placement_result_t* placements,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
