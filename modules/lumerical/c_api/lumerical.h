/**
 * @file lumerical.h
 * @brief PoLaRIS polaris-lumerical 子模块 C ABI 接口声明
 *
 * 与 Python API（LumericalFDTDBackend/ModeSolver/CHARGESimulator/
 * INTERCONNECTSimulator/Tidy3DBackend/MeepAdjointBackend/PhotoelectricCoSim/
 * CMLCompiler 等）一一对应。类型定义见 ../_c_abi/polaris_types.h
 * （polaris_result_t / polaris_error_t）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 商业软件未安装/未授权返回 POLARIS_ERR_UNAVAILABLE
 *   - 仿真失败（如 NaN/不收敛）返回 POLARIS_ERR_SIMULATION
 * - R03 禁止 fall-back：商业后端缺失即返回错误码，不静默降级
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Yee 1966 IEEE TAP 14(3) 302 https://doi.org/10.1109/TAP.1966.1138693
 * - Taflove & Hagness 2005 Computational Electrodynamics FDTD 3rd ed
 * - Roden & Gedney 2000 MPRL CPML IEEE MGWL 10(12) 484
 *   https://doi.org/10.1109/7261.892828
 * - Soref & Bennett 1987 IEEE JQE 23(1) 123 https://doi.org/10.1109/JQE.1987.1073206
 * - Marcatili 1969 Bell Syst Tech J 48 2071 https://doi.org/10.1002/j.1538-7305.1969.tb01163.x
 * - Ansys Lumerical FDTD https://www.ansys.com/products/optics/fdtd
 * - Ansys Lumerical MODE https://www.ansys.com/products/optics/mode
 * - Ansys Lumerical CHARGE https://www.ansys.com/products/optics/charge
 * - Ansys Lumerical INTERCONNECT https://www.ansys.com/products/optics/interconnect
 * - Tidy3D 文档 https://docs.flexcompute.com/projects/tidy3d/en/latest/
 * - MEEP 文档 https://meep.readthedocs.io/en/latest/
 * - Chrostowski 2015 Silicon Photonics Design Cambridge
 *   https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
 * - Coldren & Corzine 1995 Diode Lasers and Photonic Integrated Circuits Wiley
 * - Agrawal 2010 Fiber-Optic Communication Systems 4th ed Wiley
 * - Sze & Ng 2007 Physics of Semiconductor Devices 3rd ed Wiley
 * - ITU-T O.150 PRBS 标准 https://www.itu.int/rec/T-REC-O.150
 */
#ifndef POLARIS_LUMERICAL_H
#define POLARIS_LUMERICAL_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_lum_fdtd_solve: Lumerical FDTD 3D 求解（Yee leapfrog + CPML + TFSF）
 * @param wavelength_um 波长 [μm]
 * @param dx_um/dy_um/dz_um 网格步长 [μm]
 * @param n_steps 时间步数
 * @param out 输出结果（JSON: s_params/energy/field 等）
 * @return POLARIS_OK 或错误码（商业后端缺失返回 POLARIS_ERR_UNAVAILABLE）
 */
polaris_error_t polaris_lum_fdtd_solve(
    double wavelength_um,
    double dx_um, double dy_um, double dz_um,
    int32_t n_steps,
    polaris_result_t* out
);

/* polaris_lum_mode_solve: Lumerical MODE 波导模式求解（Marcatili + FDFD）
 * @param wavelength_um 波长 [μm]
 * @param width_um 波导宽度 [μm]
 * @param height_um 波导高度 [μm]
 * @param core_index 核心折射率
 * @param cladding_index 包层折射率
 * @param out 输出结果（JSON: n_eff/n_group/dispersion 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_lum_mode_solve(
    double wavelength_um,
    double width_um, double height_um,
    double core_index, double cladding_index,
    polaris_result_t* out
);

/* polaris_lum_charge_solve: Lumerical CHARGE PN 结电光协同求解
 * @param temperature_K 温度 [K]
 * @param doping_n N 区掺杂 [1/cm³]
 * @param doping_p P 区掺杂 [1/cm³]
 * @param voltage_V 偏置电压 [V]
 * @param out 输出结果（JSON: depletion_width/capacitance/bandwidth/dn_eff 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_lum_charge_solve(
    double temperature_K,
    double doping_n, double doping_p,
    double voltage_V,
    polaris_result_t* out
);

/* polaris_lum_interconnect_run: Lumerical INTERCONNECT 光链路仿真
 * @param bit_rate_bps 比特率 [bps]
 * @param n_bits 仿真比特数
 * @param osnr_db 光信噪比 [dB]
 * @param modulation 调制格式（0=NRZ, 1=PAM4, 2=QAM16）
 * @param out 输出结果（JSON: ber/eye_diagram/osnr 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_lum_interconnect_run(
    double bit_rate_bps,
    int32_t n_bits,
    double osnr_db,
    int32_t modulation,
    polaris_result_t* out
);

/* polaris_lum_tidy3d_run: Tidy3D 云/本地 FDTD 仿真
 * @param wavelength_um 波长 [μm]
 * @param dx_um 网格步长 [μm]
 * @param use_cloud 1=云 API，0=本地
 * @param out 输出结果（JSON: s_params/field 等）
 * @return POLARIS_OK 或错误码（无 API key 返回 POLARIS_ERR_UNAVAILABLE）
 */
polaris_error_t polaris_lum_tidy3d_run(
    double wavelength_um,
    double dx_um,
    int32_t use_cloud,
    polaris_result_t* out
);

/* polaris_lum_meep_run: MEEP 伴随优化仿真
 * @param wavelength_um 波长 [μm]
 * @param dx_um 网格步长 [μm]
 * @param n_steps 时间步数
 * @param out 输出结果（JSON: gradient/objective/field 等）
 * @return POLARIS_OK 或错误码（MEEP 未安装返回 POLARIS_ERR_UNAVAILABLE）
 */
polaris_error_t polaris_lum_meep_run(
    double wavelength_um,
    double dx_um,
    int32_t n_steps,
    polaris_result_t* out
);

/* polaris_lum_photoelectric_cosim: 光电协同仿真（MZM + PD + Laser）
 * @param vpi MZM 半波电压 [V]
 * @param responsivity PD 响应度 [A/W]
 * @param threshold_current 激光器阈值电流 [A]
 * @param out 输出结果（JSON: waveform/verilog_a/spice_netlist 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_lum_photoelectric_cosim(
    double vpi,
    double responsivity,
    double threshold_current,
    polaris_result_t* out
);

/* polaris_lum_cml_compile: CML Compiler 紧凑模型库编译
 * @param n_ports 端口数
 * @param n_freq 频率点数
 * @param s_matrix_re/s_matrix_im S 参数矩阵实部/虚部（n_freq*n_ports*n_ports）
 * @param out 输出结果（JSON: component/fingerprint/passivity_ok 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_lum_cml_compile(
    int32_t n_ports, int32_t n_freq,
    const double* s_matrix_re, const double* s_matrix_im,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
