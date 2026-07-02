/**
 * @file fdtd.h
 * @brief PoLaRIS polaris-fdtd 子模块 C ABI 接口声明
 *
 * 与 Python API（simulate_waveguide_fdtd / simulate_mmi_fdtd）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_result_t / polaris_error_t）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 仿真失败（如 NaN）返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
 * - Gedney 1996 IEEE TAP https://doi.org/10.1109/8.546249
 * - Taflove & Hagness 2005 "Computational Electrodynamics"
 * - Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
 * - NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
 * - Lumerical FDTD https://optics.ansys.com/hc/en-us/articles/360034914833
 */
#ifndef POLARIS_FDTD_H
#define POLARIS_FDTD_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_fdtd_waveguide: 波导 FDTD 仿真
 * @param dx_um 网格步长（μm）
 * @param n_steps 时间步数
 * @param wavelength_um 波长（μm）
 * @param out 输出结果（JSON: transmission_db/T_fdtd/fdtd_duration_s/...）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_fdtd_waveguide(
    double dx_um, int32_t n_steps, double wavelength_um,
    polaris_result_t* out
);

/* polaris_fdtd_mmi: MMI 1×2 FDTD 仿真
 * @param dx_um 网格步长（μm）
 * @param n_steps 时间步数
 * @param wavelength_um 波长（μm）
 * @param out 输出结果（JSON: split_ratio/T_fdtd/transmission_db/...）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_fdtd_mmi(
    double dx_um, int32_t n_steps, double wavelength_um,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
