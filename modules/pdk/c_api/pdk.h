/**
 * @file pdk.h
 * @brief PoLaRIS polaris-pdk 子模块 C ABI 接口声明
 *
 * 与 Python API（list_platforms/get_device/export_gds/import_gds）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_circuit_t / polaris_result_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致：器件未找到返回 POLARIS_ERR_NOTFOUND
 *   （对应 Python 端 raise RuntimeError，R03 禁止 fall-back）
 * - 所有器件参数标注来源（SiEPIC EBeam PDK / Ligentec /
 *   Pattern Project / HyperLight），C ABI 通过 JSON 字符串返回
 *
 * 来源:
 * - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Ligentec ANR PDK: https://www.ligentec.com/
 * - Pattern Project / JEPPIX InP: https://www.jeppix.eu/
 * - HyperLight LNOI PDK: https://hyperlightphotonics.com/
 * - klayout Database API:
 *   https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
 * - GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
 * - gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
 */
#ifndef POLARIS_PDK_H
#define POLARIS_PDK_H
#include "../_c_abi/polaris_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* polaris_pdk_list_platforms: 列出所有 PDK 平台
 * @param out 输出结果（JSON 字符串，caller free）
 *   JSON 格式: [{"platform":"SOI","foundry":"SiEPIC",
 *   "process_node":"220nm SOI","device_count":9,
 *   "device_names":[...]}, ...]
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_pdk.list_platforms() -> list[dict] 一致；
 * 返回 4 平台（SOI/SiN/InP/LNOI）。
 */
polaris_error_t polaris_pdk_list_platforms(polaris_result_t* out);

/* polaris_pdk_get_device: 获取指定平台的指定器件
 * @param platform 平台名（如 "SOI"）
 * @param device_type 器件类型（如 "grating_coupler"）
 * @param out 输出结果（JSON 字符串，含 params 来源标注/source 溯源/ports/bbox_um）
 * @return POLARIS_OK 或 POLARIS_ERR_NOTFOUND
 *
 * 与 Python polaris_pdk.get_device(platform, device_type) -> dict 一致；
 * Python 端器件未找到 raise RuntimeError（R03 禁止 fall-back），
 * C 端返回 POLARIS_ERR_NOTFOUND（不输出假数据）。
 */
polaris_error_t polaris_pdk_get_device(const char* platform,
                                       const char* device_type,
                                       polaris_result_t* out);

/* polaris_pdk_export_gds: 导出 GDSII
 * @param circuit 电路规格（polaris_circuit_t，与 polaris_core.make_circuit 一致）
 * @param output_path 输出文件路径
 * @param out 输出结果（JSON 含 path/file_size_bytes/n_structures/n_layers/loadable）
 * @return POLARIS_OK 或错误码（POLARIS_ERR_INVALID/POLARIS_ERR_IO）
 *
 * 与 Python polaris_pdk.export_gds(circuit, output_path) -> dict 一致；
 * Python 端 klayout 写入失败 raise RuntimeError（R03 禁止 fall-back），
 * C 端返回 POLARIS_ERR_IO。
 */
polaris_error_t polaris_pdk_export_gds(const polaris_circuit_t* circuit,
                                       const char* output_path,
                                       polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_PDK_H */
