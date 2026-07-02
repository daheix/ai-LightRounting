/**
 * @file core.h
 * @brief PoLaRIS polaris-core 子模块 C ABI 接口声明
 *
 * 与 Python API（make_device/make_circuit/validate_circuit）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_circuit_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_circuit_free 等）
 * - 错误码语义与 Python 异常一致：validate 失败返回 POLARIS_ERR_INVALID
 *   （对应 Python 端 raise RuntimeError，R03 禁止 fall-back）
 *
 * 来源:
 * - numpy ndarray C API: https://numpy.org/doc/stable/reference/c-api/types-and-structures.html
 * - klayout db API: https://www.klayout.de/klayout.doc/programming/database_api.html
 * - GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
 * - SiEPIC PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - PyTorch C++ frontend: https://pytorch.org/cppdocs/
 */
#ifndef POLARIS_CORE_H
#define POLARIS_CORE_H
#include "../_c_abi/polaris_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* polaris_core_make_device: 创建器件规格
 * @param name 器件实例名
 * @param device_type 器件类型
 * @param width_um 宽度
 * @param height_um 高度
 * @param out 输出器件规格（caller 负责 free）
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_core.make_device(name, device_type, width_um,
 * height_um, ports, params, process_node) -> dict 一致；
 * ports/params/process_node 通过 out 的字段填充（caller 预分配或
 * 由本函数分配，caller 负责 polaris_circuit_free 释放）。
 */
polaris_error_t polaris_core_make_device(
    const char* name, const char* device_type,
    double width_um, double height_um,
    polaris_device_spec_t* out
);

/* polaris_core_make_circuit: 创建电路规格
 * @param name 电路名
 * @param devices 器件数组
 * @param n_devices 器件数
 * @param connections 连接数组
 * @param n_connections 连接数
 * @param canvas_w_um 画布宽
 * @param canvas_h_um 画布高
 * @param out 输出电路规格（caller 负责 free）
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_core.make_circuit(name, devices, connections,
 * canvas_w, canvas_h, process_node, optical_wavelength_nm) -> dict 一致；
 * process_node/optical_wavelength_nm 使用默认值（NULL/1550.0），如需
 * 覆盖由 caller 直接修改 out 字段。
 */
polaris_error_t polaris_core_make_circuit(
    const char* name,
    const polaris_device_spec_t* devices, int32_t n_devices,
    const polaris_connection_t* connections, int32_t n_connections,
    double canvas_w_um, double canvas_h_um,
    polaris_circuit_t* out
);

/* polaris_core_validate_circuit: 验证电路规格完整性
 * @param circuit 电路规格
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID
 *
 * 与 Python polaris_core.validate_circuit(circuit) -> bool 一致；
 * Python 端验证失败 raise RuntimeError（R03 禁止 fall-back），
 * C 端返回 POLARIS_ERR_INVALID（不输出假数据）。
 */
polaris_error_t polaris_core_validate_circuit(const polaris_circuit_t* circuit);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_CORE_H */
