/**
 * @file fde.h
 * @brief PoLaRIS polaris-fde 子模块 C ABI 接口声明
 *
 * 与 Python API（solve_modes）一一对应。类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 特征值求解失败返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Smit & van Dam, IEEE/OSA JLT 14(7), 1996（模式展开理论）
 *   https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
 * - Silvester & Ferrari, "Finite Elements for Electrical Engineers",
 *   Cambridge 1996（FD/FEM 本征模求解）
 * - Soref 1993 IEEE JQE（Si/SiO2 折射率 3.476/1.444）
 *   https://ieeexplore.ieee.org/document/1148303
 * - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
 *   https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
 * - Lumerical MODE FDE 求解器
 *   https://optics.ansys.com/hc/en-us/articles/360034902413
 * - NIST CODATA 2018（光速常数）
 *   https://physics.nist.gov/cuu/Constants/
 */
#ifndef POLARIS_FDE_H
#define POLARIS_FDE_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_fde_solve_modes: 2D FD 本征模求解
 * @param width_um 波导宽度（μm，如 0.5）
 * @param height_um 波导高度（μm，如 0.22）
 * @param wavelength_um 波长（μm，如 1.55）
 * @param n_core 芯区折射率（Si 3.476）
 * @param n_clad 包层折射率（SiO2 1.444）
 * @param n_modes 求解模式数
 * @param out 输出结果（JSON: modes/n_modes/wavelength_um/grid_info）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_fde_solve_modes(
    double width_um, double height_um, double wavelength_um,
    double n_core, double n_clad, int32_t n_modes,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
