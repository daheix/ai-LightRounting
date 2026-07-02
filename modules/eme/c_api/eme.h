/**
 * @file eme.h
 * @brief PoLaRIS polaris-eme 子模块 C ABI 接口声明
 *
 * 与 Python API（solve_eme）一一对应。类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 求解失败返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Smit & van Dam, IEEE/OSA JLT 14(7), 1996（EME 理论）
 *   https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
 * - Lumerical EME 求解器
 *   https://optics.ansys.com/hc/en-us/articles/360034902433
 * - Bienstman 2001 PhD（Redheffer 星积）
 *   https://www.photonics.intec.ugent.be/publications/PhD_Bienstman.pdf
 * - Sztefanka & Kapon 1993 JLT（模式匹配）
 *   https://ieeexplore.ieee.org/document/247559
 * - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
 *   https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
 * - NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
 */
#ifndef POLARIS_EME_H
#define POLARIS_EME_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_eme_solve: EME 多段波导级联求解
 * @param n_sections 段数
 * @param widths_um 段宽度数组（μm）
 * @param lengths_um 段长度数组（μm）
 * @param n_cores 芯折射率数组
 * @param n_clads 包层折射率数组
 * @param wavelength_um 波长（μm）
 * @param out 输出结果（JSON: transmission/transmission_db/s_matrix）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_eme_solve(
    int32_t n_sections,
    const double* widths_um, const double* lengths_um,
    const double* n_cores, const double* n_clads,
    double wavelength_um,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
