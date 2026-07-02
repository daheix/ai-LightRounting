/**
 * @file gdsio.h
 * @brief PoLaRIS polaris-gdsio 子模块 C ABI 接口声明
 *
 * v5.1 从 polaris-pdk 拆分，单一职责：GDSII 导入导出。
 * 与 Python API（export_gds/import_gds）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h
 * （polaris_circuit_t / polaris_result_t 等 POD 结构）。
 *
 * === Input / Process / Output 三段式文档 ===
 *
 * Input:
 * - polaris_gdsio_export(circuit, output_path)
 *     circuit      : polaris_circuit_t（与 polaris_core.make_circuit 一致）
 *     output_path  : GDSII 输出文件路径
 * - polaris_gdsio_import(gds_path)
 *     gds_path     : GDSII 文件路径
 *
 * Process:
 * - klayout.db 创建 Layout（dbu=0.001μm=1nm，gdsfactory 默认）
 * - export: 顶层 cell + 每器件子 cell（box 在 WG 层 (1,0)）+ 实例放置
 *           + 写 GDSII + 读回验证
 * - import: 读取 GDSII + 层号映射 (gds_layer, gds_datatype) → polaris_name
 *           + 顶层 bbox
 * - 层映射: (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
 *           / (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
 *
 * Output:
 * - polaris_gdsio_export -> JSON 含
 *     {path, file_size_bytes, n_structures, n_layers, loadable}
 * - polaris_gdsio_import -> JSON 含
 *     {n_structures, n_layers,
 *      layers: [{gds_layer, gds_datatype, polaris_name, n_shapes}],
 *      bbox_um: {xmin, ymin, xmax, ymax}}
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致：
 *     klayout 读写失败 → POLARIS_ERR_IO（对应 Python raise RuntimeError）
 *     circuit 无效     → POLARIS_ERR_INVALID
 *     文件不存在       → POLARIS_ERR_NOTFOUND
 *   （R03 禁止 fall-back，C 端不输出假数据）
 *
 * 来源（R02 学术诚信，均经 WebSearch 验证可访问）:
 * - klayout Layout Database API:
 *   https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
 * - gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
 * - GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
 * - GDSII 层次结构（cell/SREF/AREF）:
 *   https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
 * - gdsfactory PDK import 层映射:
 *   https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
 * - KLayout CellInstArray:
 *   https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
 */
#ifndef POLARIS_GDSIO_H
#define POLARIS_GDSIO_H
#include "../_c_abi/polaris_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* polaris_gdsio_export: 导出 GDSII
 * @param circuit 电路规格（polaris_circuit_t，与 polaris_core.make_circuit 一致）
 * @param output_path 输出文件路径
 * @param out 输出结果（JSON 含 path/file_size_bytes/n_structures/n_layers/loadable）
 * @return POLARIS_OK / POLARIS_ERR_INVALID / POLARIS_ERR_IO
 *
 * 与 Python polaris_gdsio.export_gds(circuit, output_path) -> dict 一致；
 * Python 端 klayout 写入失败 raise RuntimeError（R03 禁止 fall-back），
 * C 端返回 POLARIS_ERR_IO（不输出假数据）。
 */
polaris_error_t polaris_gdsio_export(const polaris_circuit_t* circuit,
                                     const char* output_path,
                                     polaris_result_t* out);

/* polaris_gdsio_import: 导入 GDSII
 * @param gds_path GDSII 文件路径
 * @param out 输出结果（JSON 含 n_structures/n_layers/layers/bbox_um）
 * @return POLARIS_OK / POLARIS_ERR_NOTFOUND / POLARIS_ERR_IO
 *
 * 与 Python polaris_gdsio.import_gds(gds_path) -> dict 一致；
 * Python 端文件不存在 raise FileNotFoundError，klayout 读取失败 raise
 * RuntimeError（R03 禁止 fall-back），C 端分别返回
 * POLARIS_ERR_NOTFOUND / POLARIS_ERR_IO。
 */
polaris_error_t polaris_gdsio_import(const char* gds_path,
                                     polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_GDSIO_H */
