/**
 * @file lvs.h
 * @brief PoLaRIS polaris-lvs 子模块 C ABI 接口声明（LVS 网表一致性比对）
 *
 * Input → Process → Output 三段式：
 *
 * Input:
 *   - circuit: polaris_circuit_t* 电路规格（含 devices/connections）
 *   - netlist: 可选提取网表（NULL 时用 circuit 自身派生网表自比对）
 *
 * Process:
 *   1. 从 circuit 提取参考网表（器件名+类型 + 拓扑连接）
 *   2. 与提取网表比对: 器件集合差集 + 器件类型一致性 + 连接集合差集
 *   3. 连接归一化为有序对去重（消除方向差异）
 *
 * Output:
 *   polaris_result_t* out，JSON 含:
 *     {
 *       "is_consistent": bool,  // true 表示版图与原理图拓扑一致
 *       "n_mismatches": int,
 *       "mismatches": list[dict],
 *       "n_devices": int,
 *       "n_connections": int
 *     }
 *
 * 与 Python API（polaris_lvs.run_lvs）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - circuit/netlist 结构非法返回 POLARIS_ERR_INVALID
 *   - LVS 不一致不视为错误（返回 POLARIS_OK，不一致信息在 out.json 中）
 *   - 严重校验失败返回 POLARIS_ERR_VERIFICATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - KLayout LVS API: https://www.klayout.org/doc-qt5/manual/lvs.html
 * - SiEPIC EBeam PDK DEVREC 标准（器件识别层 layer 68）
 *   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
 *   https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
 * - gdsfactory PDK 文档（网表提取）
 *   https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
 * - Luceda IPKISS（光子电路网表验证）
 *   https://www.lucedaphotonics.com/en/products/ipkiss
 * - Calibre nmLVS（工业 LVS 比对算法）
 *   https://eda.sw.siemens.com/en-US/calibre/
 */
#ifndef POLARIS_LVS_H
#define POLARIS_LVS_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_lvs_run: 执行 LVS 网表比对
 * @param circuit 电路规格
 * @param out 输出结果（JSON 含 is_consistent/n_mismatches/mismatches/n_devices/n_connections）
 * @return POLARIS_OK 或 POLARIS_ERR_VERIFICATION
 *
 * LVS 不一致不视为错误（POLARIS_OK），不一致详情写入 out.json。
 * 仅当 circuit 结构非法时返回 POLARIS_ERR_VERIFICATION。
 */
polaris_error_t polaris_lvs_run(
    const polaris_circuit_t* circuit,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
