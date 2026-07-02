#ifndef POLARIS_QUANTUM_ADVANCED_H
#define POLARIS_QUANTUM_ADVANCED_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_qa_gbs_probability: Gaussian Boson Sampling 输出概率
 * Input:
 *   covariance      协方差矩阵（一维展开，row-major，M*M 个 double）
 *   n_modes         模式数 M
 *   output_state    输出模式（长度 n_modes）
 * Process:
 *   Hafnian(A_s)² / det(σ+εI)，暴力枚举完美匹配（Björklund 2012）。
 * Output:
 *   out->json       JSON 含 probability / n_modes
 * 参考: Hamilton et al. PRL 119, 170501 (2017)
 *       https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID
 */
polaris_error_t polaris_qa_gbs_probability(
    const double* covariance, int32_t n_modes,
    const int32_t* output_state,
    polaris_result_t* out
);

/* polaris_qa_lossy_boson_sampling: 含光子损失的玻色采样分布
 * Input:
 *   unitary         M×M 酉矩阵（row-major，复数实虚交错，2*M*M 个 double）
 *   n_modes         模式数 M
 *   input_state     输入光子态（长度 n_modes）
 *   loss_rate       光子损失率 [0,1]
 * Process:
 *   二项分布混合存活光子数 + 各存活数下的理想玻色采样分布。
 *   量子优越性阈值: N_detected >= sqrt(N) (García-Patrón 2019)。
 * Output:
 *   out->json       JSON 含 output_distribution / total_prob (=1.0) / qa_held
 * 参考: García-Patrón et al., Quantum 3, 169 (2019)
 *       https://arxiv.org/abs/1712.10037
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION
 */
polaris_error_t polaris_qa_lossy_boson_sampling(
    const double* unitary, int32_t n_modes,
    const int32_t* input_state, double loss_rate,
    polaris_result_t* out
);

/* polaris_qa_bb84_simulate: BB84 量子密钥分发协议仿真
 * Input:
 *   key_length       目标密钥长度（≥8）
 *   eavesdrop        是否模拟 intercept-resend 窃听（1=是, 0=否）
 *   channel_loss_db  信道损耗 (dB，城域网典型 2-5 dB)
 * Process:
 *   Alice 随机比特+基矢 → Eve intercept-resend → Bob 测量 → 基矢比对
 *   → QBER 估算 → 阈值 11% 判定安全 (Shor-Preskill 2000)。
 * Output:
 *   out->json        JSON 含 qber / is_secure / final_key_hex / sifted_bits
 * 参考: Bennett & Brassard 1984 https://doi.org/10.1145/358340.358342
 *       Shor & Preskill 2000 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.85.441
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID
 */
polaris_error_t polaris_qa_bb84_simulate(
    int32_t key_length, int32_t eavesdrop, double channel_loss_db,
    polaris_result_t* out
);

/* polaris_qa_e91_simulate: E91 量子密钥分发协议仿真（Bell 不等式）
 * Input:
 *   key_length       目标密钥长度（≥8）
 *   eavesdrop_prob   窃听概率 [0,1]
 * Process:
 *   EPR 对分发 → Alice/Bob 三基测量 → CHSH-Bell S 参数安全检测
 *   → S>2 违反 Bell 不等式则无窃听 → Acín 2006 成码率下界提取密钥。
 *   Tsirelson 界 S<=2√2，局域隐变量 S<=2。
 * Output:
 *   out->json        JSON 含 bell_parameter / qber / is_secure / secret_key_rate
 * 参考: Ekert 1991 PRL 67, 661 https://doi.org/10.1103/PhysRevLett.67.661
 *       Acín et al. 2006 PRL 97, 230503 https://doi.org/10.1103/PhysRevLett.97.230503
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_VERIFICATION
 */
polaris_error_t polaris_qa_e91_simulate(
    int32_t key_length, double eavesdrop_prob,
    polaris_result_t* out
);

/* polaris_qa_cv_gaussian_vacuum: CV 高斯真空态构造
 * Input:
 *   n_modes          模式数 N (≥1)
 * Process:
 *   协方差矩阵 V = I/2 (2N×2N)，平均向量 d = 0 (Weedbrook 2012 §II)。
 *   辛形式 Ω = [[0,I],[-I,0]]，不确定性关系 V + iΩ/2 ≥ 0 校验。
 * Output:
 *   out->json        JSON 含 covariance / mean / n_modes / uncertainty_ok
 * 参考: Weedbrook et al. 2012 Rev Mod Phys 84, 621
 *       https://doi.org/10.1103/RevModPhys.84.621
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID
 */
polaris_error_t polaris_qa_cv_gaussian_vacuum(
    int32_t n_modes, polaris_result_t* out
);

/* polaris_qa_steane_correct: Steane [[7,4,3]] 纠错码单比特纠错
 * Input:
 *   received         7 维 0/1 接收字（int32 数组）
 * Process:
 *   Hamming [7,4] 校验矩阵 H (3×7)，症状 s = H·r mod 2，
 *   症状非零组合定位错误比特并翻转纠正 (Steane 1996 CSS 构造)。
 * Output:
 *   out->json        JSON 含 corrected (list[int]) / syndrome / error_pos
 * 参考: Steane 1996 PRL 77, 793 https://doi.org/10.1103/PhysRevLett.77.793
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID / POLARIS_ERR_VERIFICATION
 */
polaris_error_t polaris_qa_steane_correct(
    const int32_t* received, polaris_result_t* out
);

/* polaris_qa_photon_loss_channel: 光子损耗通道（Kraus 算子）
 * Input:
 *   rho              密度矩阵（row-major，复数实虚交错，(N+1)^2*2 个 double）
 *   n_state          维度 N+1
 *   eta              透射率 (0,1]
 * Process:
 *   解析 Kraus 求和 ρ'_mn = η^((m+n)/2) Σ_k sqrt(C(m+k,k)C(n+k,k))(1-η)^k ρ_{m+k,n+k}
 *   保迹 CPTP，Beer-Lambert η=exp(-αL) (Kok & Lovett 2010 §3.2)。
 * Output:
 *   out->json        JSON 含 rho_out / trace (≈1.0) / mean_photon_after
 * 参考: Kok & Lovett 2010 https://www.cambridge.org/9780521191356
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID
 */
polaris_error_t polaris_qa_photon_loss_channel(
    const double* rho, int32_t n_state, double eta,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_QUANTUM_ADVANCED_H */
