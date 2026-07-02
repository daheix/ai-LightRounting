/**
 * @file bpm.h
 * @brief PoLaRIS polaris-bpm 子模块 C ABI 接口声明
 *
 * 与 Python API（solve_bpm）一一对应。类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 求解失败（NaN）返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Feit & Fleck, Appl. Opt. 17(24), 1978（光束传播法）
 *   https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
 * - Crank & Nicolson, Math. Proc. Cambridge 43(1), 1947（隐式差分）
 * - Lumerical varFDTD/BPM
 *   https://optics.ansys.com/hc/en-us/articles/360034902433
 * - scipy.linalg.solve_banded（三对角求解）
 *   https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
 * - Chung & Dagli, IEEE JQE 26(8), 1990（ADI 扩展）
 *   https://ieeexplore.ieee.org/document/59635
 * - NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
 */
#ifndef POLARIS_BPM_H
#define POLARIS_BPM_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_bpm_solve: Crank-Nicolson BPM 求解
 * @param width_um 波导宽度（μm）
 * @param length_um 传播长度（μm）
 * @param wavelength_um 波长（μm）
 * @param n_core 芯折射率（Si 3.476）
 * @param n_clad 包层折射率（SiO2 1.444）
 * @param dz_um 纵向步长（μm）
 * @param dx_um 横向步长（μm）
 * @param out 输出结果（JSON: field_z/transmission_db/n_steps/grid_info）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_bpm_solve(
    double width_um, double length_um, double wavelength_um,
    double n_core, double n_clad,
    double dz_um, double dx_um,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
