/**
 * @file sim.h
 * @brief PoLaRIS polaris-sim 子模块 C ABI 接口声明
 *
 * 与 Python API（simulate_mzi_sparam / compute_clements_unitary / simulate_pam4）
 * 一一对应。类型定义见 ../_c_abi/polaris_types.h（polaris_result_t / polaris_error_t）。
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
 * - Shafik et al., IEEE CommSurveys 2016（PAM4 BER/SNR）
 *   https://ieeexplore.ieee.org/document/7410082
 * - Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
 */
#ifndef POLARIS_SIM_H
#define POLARIS_SIM_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_sim_mzi_sparam: MZI S参数扫描
 * @param wl_start_nm 起始波长
 * @param wl_stop_nm 终止波长
 * @param n_points 扫描点数
 * @param out 输出结果（JSON 含 resonant_wavelength_nm/extinction_ratio_db）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_sim_mzi_sparam(
    double wl_start_nm, double wl_stop_nm, int32_t n_points,
    polaris_result_t* out
);

/* polaris_sim_clements_unitary: Clements 酉矩阵
 * @param n_modes 模式数
 * @param out 输出结果（JSON 含 unitary/unitarity_error/is_unitary）
 * @return POLARIS_OK
 */
polaris_error_t polaris_sim_clements_unitary(int32_t n_modes, polaris_result_t* out);

/* polaris_sim_pam4: PAM4 眼图仿真
 * @param n_symbols 符号数
 * @param bit_rate_gbps 比特率
 * @param out 输出结果（JSON 含 ber/snr_db）
 * @return POLARIS_OK
 */
polaris_error_t polaris_sim_pam4(
    int32_t n_symbols, double bit_rate_gbps,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
