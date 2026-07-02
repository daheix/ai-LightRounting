/**
 * @file sparam.h
 * @brief PoLaRIS polaris-sparam 子模块 C ABI 接口声明
 *
 * 与 Python API（waveguide_s / mmi_1x2_s / mmi_2x2_s / grating_coupler_s /
 * simulate_mzi_sparam / compute_clements_unitary）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_result_t / polaris_error_t）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 仿真/酉性校验失败返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Saleh & Teich, "Fundamentals of Photonics", Wiley 2019, §4.4（MZI 传输率）
 * - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - Soldano & Pennings, J. Lightwave Technol. 13(4), 1995（MMI）
 *   https://ieeexplore.ieee.org/document/374358
 * - Clements et al., Optica 3(12), 1460 (2016)（Clements 酉矩阵分解）
 *   https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
 * - Simphony SiEPIC 模型库
 *   https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
 * - Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
 */
#ifndef POLARIS_SPARAM_H
#define POLARIS_SPARAM_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_sparam_waveguide: 波导频域 S 参数
 * @param wavelength_um 波长（μm）
 * @param length_um 波导长度（μm）
 * @param neff 有效折射率
 * @param loss_db_cm 传播损耗（dB/cm）
 * @param out 输出结果（JSON: 端口对 -> 复数 S 参数）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_sparam_waveguide(
    double wavelength_um, double length_um,
    double neff, double loss_db_cm,
    polaris_result_t* out
);

/* polaris_sparam_mmi_1x2: MMI 1x2 S 参数 */
polaris_error_t polaris_sparam_mmi_1x2(
    double wavelength_um, double insertion_loss_db,
    polaris_result_t* out
);

/* polaris_sparam_mmi_2x2: MMI 2x2 S 参数 */
polaris_error_t polaris_sparam_mmi_2x2(
    double wavelength_um, double insertion_loss_db,
    polaris_result_t* out
);

/* polaris_sparam_grating_coupler: 光栅耦合器 S 参数 */
polaris_error_t polaris_sparam_grating_coupler(
    double wavelength_um, double peak_wl,
    double bandwidth_3db, double insertion_loss_db,
    polaris_result_t* out
);

/* polaris_sparam_mzi: MZI S参数扫描
 * @param wl_start_nm 起始波长
 * @param wl_stop_nm 终止波长
 * @param n_points 扫描点数
 * @param out 输出结果（JSON: resonant_wavelength_nm/extinction_ratio_db）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_sparam_mzi(
    double wl_start_nm, double wl_stop_nm, int32_t n_points,
    polaris_result_t* out
);

/* polaris_sparam_clements: Clements 酉矩阵
 * @param n_modes 模式数
 * @param out 输出结果（JSON: unitary/unitarity_error/is_unitary）
 * @return POLARIS_OK
 */
polaris_error_t polaris_sparam_clements(int32_t n_modes, polaris_result_t* out);

#ifdef __cplusplus
}
#endif
#endif
