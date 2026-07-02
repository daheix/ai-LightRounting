/**
 * @file pdk.h
 * @brief PoLaRIS polaris-pdk 子模块 C ABI 接口声明
 *
 * v5.1 起 GDSII 导入导出已拆分到 polaris-gdsio（见 ../gdsio/c_api/gdsio.h）；
 * 本头文件只保留器件库查询接口（list_platforms / get_device）。
 * 类型定义见 ../_c_abi/polaris_types.h
 * （polaris_result_t 等 POD 结构）。
 *
 * === Input / Process / Output 三段式文档 ===
 *
 * Input:
 * - polaris_pdk_list_platforms()                  无参
 * - polaris_pdk_get_device(platform, device_type)
 *     platform     : 平台名（如 "SOI"）
 *     device_type  : 器件类型（如 "grating_coupler"）
 *
 * Process:
 * - 查询 4 平台 36 器件目录（SOI/SiN/InP/LNOI × 9 器件）
 * - 来源 PDK: SiEPIC EBeam PDK / Ligentec / Pattern Project / HyperLight
 * - C ABI 通过 JSON 字符串返回（caller free）
 *
 * Output:
 * - polaris_pdk_list_platforms -> JSON 数组
 *     [{platform, foundry, process_node, device_count, device_names}, ...]
 * - polaris_pdk_get_device -> JSON 对象
 *     {platform, device_type, name, category, foundry, process_node,
 *      params, source, ports, bbox_um}
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致：器件未找到返回 POLARIS_ERR_NOTFOUND
 *   （对应 Python 端 raise RuntimeError，R03 禁止 fall-back）
 * - 所有器件参数标注来源（SiEPIC EBeam PDK / Ligentec /
 *   Pattern Project / HyperLight），C ABI 通过 JSON 字符串返回
 *
 * 来源（R02 学术诚信，均经 WebSearch 验证可访问）:
 * - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Ligentec ANR PDK: https://www.ligentec.com/
 * - Pattern Project / JEPPIX InP: https://www.jeppix.eu/
 * - HyperLight LNOI PDK: https://hyperlightphotonics.com/
 * - Soares et al., Appl. Sci. 2019, 9(8), 1588:
 *   https://doi.org/10.3390/app9081588
 * - Liu et al., Light: Advanced Manufacturing 2025, 6, 47:
 *   https://doi.org/10.37188/lam.2025.047
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

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_PDK_H */
