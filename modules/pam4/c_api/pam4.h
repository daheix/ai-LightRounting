/**
 * @file pam4.h
 * @brief PoLaRIS polaris-pam4 子模块 C ABI 接口声明
 *
 * 与 Python API（simulate_pam4 / generate_pam4_signal / compute_ber /
 * compute_snr_db / compute_eye_diagram）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_result_t / polaris_error_t）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Shafik et al., IEEE CommSurveys 2016（PAM4 BER/SNR）
 *   https://ieeexplore.ieee.org/document/7410082
 * - OIF CEI-112G 标准 https://www.oiforum.com/
 * - Ansys Lumerical INTERCONNECT 眼图分析
 *   https://optics.ansys.com/hc/en-us/articles/49697869166611
 * - Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §9
 * - Proakis, "Digital Communications", McGraw-Hill 2007, §5（PAM BER 公式）
 * - Ansys Lumerical CML Compiler
 *   https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
 */
#ifndef POLARIS_PAM4_H
#define POLARIS_PAM4_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_pam4_simulate: PAM4 眼图仿真
 * @param n_symbols 符号数
 * @param bit_rate_gbps 比特率（Gbps）
 * @param samples_per_symbol 每符号采样点数
 * @param noise_std 噪声标准差（V）
 * @param out 输出结果（JSON: ber/snr_db/n_symbols/bit_rate_gbps）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_pam4_simulate(
    int32_t n_symbols, double bit_rate_gbps,
    int32_t samples_per_symbol, double noise_std,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
