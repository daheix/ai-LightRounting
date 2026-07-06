/**
 * @file fdfd.h
 * @brief PoLaRIS polaris-fdfd 子模块 C ABI 接口声明
 *
 * 与 Python API（solve_fdfd）一一对应。类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 求解失败（NaN/奇异）返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Taflove & Hagness, "Computational Electrodynamics", Artech 2005
 * - Shin & Fan, Opt. Express 2014（FDFD 2D 求解）
 *   https://opg.optica.org/oe/fulltext.cfm?uri=oe-22-5-5230
 * - scipy.sparse.linalg.spsolve（UMFPACK 直接求解）
 *   https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
 * - Lumerical FDFD https://optics.ansys.com/hc/en-us/articles/360034902393
 * - Soref 1993 IEEE JQE（Si/SiO2 折射率）
 *   https://ieeexplore.ieee.org/document/1148303
 * - NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
 */
#ifndef POLARIS_FDFD_H
#define POLARIS_FDFD_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_fdfd_solve: 2D FDFD 求解
 * @param width_um 波导宽度（μm）
 * @param length_um 传播长度（μm）
 * @param wavelength_um 波长（μm）
 * @param n_core 芯折射率（Si 3.476）
 * @param n_clad 包层折射率（SiO2 1.444）
 * @param dx_um 网格步长（μm）
 * @param out 输出结果（JSON: field_2d/transmission_db/n_grid）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_fdfd_solve(
    double width_um, double length_um, double wavelength_um,
    double n_core, double n_clad,
    double dx_um,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
