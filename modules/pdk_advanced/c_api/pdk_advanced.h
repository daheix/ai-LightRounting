/**
 * @file pdk_advanced.h
 * @brief PoLaRIS polaris-pdk-advanced 子模块 C ABI 接口声明
 *
 * v5.1 从 v4 旧包 src/polaris/pdk/ 迁移高级 PDK 功能：
 * gdsfactory 桥接（48 PDK 注册表 + LayerStack/CrossSection 转换 +
 * .pic.yml 解析 + 反向转换 + 版本兼容检测）、OptoDesigner 版图驱动设计
 * （Design Intent / PyCell / flexConnector / Hierarchy / PDAflow）、
 * PCell 多视图参数化单元（@polaris_cell 装饰器 + LRU 缓存 + 仿射/贝塞尔变换）、
 * YAML PDK 配置系统、多 PDK 实例管理器、多 foundry 平台元数据、
 * 模块库、工艺节点、SiEPIC 映射、版本兼容检测。
 *
 * R03 合规声明（2026-07-03）：删除 "VPIphotonics PDK、L-Edit GPIC iPDK"
 * 声明（src/ 下无对应实现，属声明-未实现违规）。基础 4 foundry PDK
 * （SiEPIC/Ligentec/PatternProject/HyperLight）见 ../pdk/c_api/pdk.h。
 *
 * 基础 PDK 器件库查询（4 平台 36 器件）见 ../pdk/c_api/pdk.h。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_result_t 等 POD 结构）。
 *
 * === Input / Process / Output 三段式文档 ===
 *
 * Input:
 * - polaris_pdk_advanced_list_gdsfactory_pdks()             无参
 * - polaris_pdk_advanced_get_gdsfactory_pdk(name)           PDK 名
 * - polaris_pdk_advanced_check_version_compatibility()      无参
 * - polaris_pdk_advanced_list_foundry_platforms()           无参
 * - polaris_pdk_advanced_list_process_nodes()               无参
 *
 * Process:
 * - 查询 gdsfactory PDK 注册表（48 PDK，含 source_url 溯源）
 * - 检测 gdsfactory/Python/KLayout/NumPy 版本兼容性
 * - 查询 11 个公开 foundry 平台元数据 + CMOS 工艺节点
 * - C ABI 通过 JSON 字符串返回（caller free）
 *
 * Output:
 * - polaris_pdk_advanced_list_gdsfactory_pdks -> JSON 数组
 *     [{name, platform, process_node, import_name, layer_stack_name,
 *       description, source_url}, ...]
 * - polaris_pdk_advanced_check_version_compatibility -> JSON 对象
 *     {compatible, python_version, gdsfactory_version, reason,
 *      recommended_action}
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致：PDK 未找到返回 POLARIS_ERR_NOTFOUND
 *   （对应 Python 端 raise KeyError，R03 禁止 fall-back）
 * - 所有 PDK/平台参数标注来源 URL（R02 学术诚信）
 *
 * 来源（R02 学术诚信，均经 WebSearch 验证可访问）:
 * - gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
 * - Synopsys OptoDesigner: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
 * - Luceda IPKISS: https://www.lucedaphotonics.com/en/products/ipkiss
 * - VPIphotonics VPItoolkit PDK: https://www.vpiphotonics.com/Tools/PDK/
 * - PDAflow API 标准: http://pdaflow.org/
 * - Siemens L-Edit Photonics GPIC:
 *   https://resources.sw.siemens.com/pl-PL/white-paper-layout-driven-design-with-l-edit-photonics/
 * - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - AIM Photonics: https://www.aimphotonics.com/
 * - JePPIX InP Pilot Lines: https://www.jeppix.eu/
 * - HyperLight LNOI: https://hyperlightphotonics.com/
 */
#ifndef POLARIS_PDK_ADVANCED_H
#define POLARIS_PDK_ADVANCED_H
#include "../_c_abi/polaris_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* polaris_pdk_advanced_list_gdsfactory_pdks: 列出 gdsfactory PDK 注册表
 * @param out 输出结果（JSON 数组字符串，caller free）
 *   JSON 格式: [{"name":"generic","platform":"SOI",
 *   "process_node":"220nm SOI","import_name":"gdsfactory",
 *   "layer_stack_name":"generic","description":"...",
 *   "source_url":"https://..."}, ...]
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_pdk_advanced.list_gdsfactory_pdks() -> list[dict] 一致；
 * 返回 48 个 gdsfactory PDK 元数据（含 source_url 溯源）。
 */
polaris_error_t polaris_pdk_advanced_list_gdsfactory_pdks(
    polaris_result_t* out);

/* polaris_pdk_advanced_check_version_compatibility: 检测版本兼容性
 * @param out 输出结果（JSON 对象字符串，caller free）
 *   JSON 格式: {"compatible":bool,"python_version":"3.x.y",
 *   "gdsfactory_version":"x.y.z"|null,"reason":"...",
 *   "recommended_action":"..."}
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_pdk_advanced.check_gdsfactory_version_compatibility()
 * -> dict 一致；Python 端 gdsfactory 不可用时 raise ImportError（R03）。
 */
polaris_error_t polaris_pdk_advanced_check_version_compatibility(
    polaris_result_t* out);

/* polaris_pdk_advanced_list_foundry_platforms: 列出公开 foundry 平台
 * @param out 输出结果（JSON 数组字符串，caller free）
 *   JSON 格式: [{"name":"AIM","foundry":"AIM Photonics",
 *   "process_node":"220nm SOI + 220nm SiN (300mm)",
 *   "material_platform":"SOI","waveguide_width_um":0.45,
 *   "min_bend_radius_um":5.0,"waveguide_loss_db_cm":0.25,
 *   "wafer_size_mm":300,"sources":["https://..."],"notes":"..."}, ...]
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_pdk_advanced.list_foundry_platforms() -> list[dict] 一致；
 * 返回 11 个公开 foundry 平台元数据（公开参数，非 NDA）。
 */
polaris_error_t polaris_pdk_advanced_list_foundry_platforms(
    polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_PDK_ADVANCED_H */
