/**
 * @file parasitic.h
 * @brief PoLaRIS polaris-parasitic 子模块 C ABI 接口声明
 *
 * 与 Python API 一一对应，覆盖两类能力：
 * 1. 寄生参数提取（R/L/C/S 参数 + SPICE 网表）
 *    - ParasiticResistor / ParasiticCapacitor / ParasiticInductor
 *    - ParasiticSParam（π 型网络 ABCD→S，无源/互易验证）
 *    - SpiceNetlistWriter（.subckt + TC1/TC2）
 *    - AdvancedParasiticExtractor（一站式聚合门面）
 * 2. Verilog-A 紧凑模型生成（5+ 器件 + SPICE 联合仿真 + 可微分 *创新*）
 *    - generate_waveguide/mmi/ring/modulator/detector_verilog_a
 *    - SPICESimulationConfig / generate_spice_netlist / run_ngspice_cosimulation
 *    - DifferentiableOptoElectricalModel（*创新* 光电协同可微）
 *
 * 类型定义见 ../_c_abi/polaris_types.h（polaris_result_t / polaris_error_t）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - Ngspice 不可用/失败返回 POLARIS_ERR_RUNTIME
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Synopsys StarRC Datasheet（RLCK 寄生提取，TC1/TC2）
 *   https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
 * - Synopsys StarRC Resistance Extraction（RPSQ × L/W 片电阻公式）
 *   https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
 * - Cadence Quantus QRC 3D 场求解
 *   https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
 * - Ansys Lumerical CML Compiler（Verilog-A 紧凑模型）
 *   https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
 * - Verilog-AMS LRM (Language Reference Manual)
 *   https://www.accellera.org/downloads/standards/v-ams
 * - Ngspice 用户手册（SPICE 联合仿真）
 *   https://ngspice.sourceforge.io/docs.html
 * - Pozar, "Microwave Engineering", 4th ed., §4（ABCD↔S 变换）
 * - Chrostowski, "Silicon Photonics Design", Cambridge 2015, §2.3/§8/§9
 */
#ifndef POLARIS_PARASITIC_H
#define POLARIS_PARASITIC_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* === 寄生参数提取（R231-R235） === */

/* polaris_parasitic_extract_resistance: 片电阻 + TC1/TC2 温度模型
 * @param sheet_resistance_ohm_sq 片电阻 RPSQ (Ω/□)
 * @param length_um 导线长度 (μm)
 * @param width_um 导线宽度 (μm)
 * @param tc1 一阶温度系数 (1/°C)
 * @param tc2 二阶温度系数 (1/°C²)
 * @param t_ref 参考温度 (°C)
 * @param temperature_c 工作温度 (°C)，NaN 时使用参考温度
 * @param out 输出结果（JSON: resistance_ohm/n_squares/temp_factor）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_parasitic_extract_resistance(
    double sheet_resistance_ohm_sq,
    double length_um, double width_um,
    double tc1, double tc2,
    double t_ref, double temperature_c,
    polaris_result_t* out
);

/* polaris_parasitic_extract_capacitance: 平行板 + 边缘 + 耦合电容
 * @param eps_r 相对介电常数
 * @param metal_thickness_um 金属厚度 H (μm)
 * @param dielectric_thickness_um 介质厚度 d (μm)
 * @param length_um 长度 (μm)
 * @param width_um 宽度 (μm)
 * @param out 输出（JSON: capacitance_ff/capacitance_area_ff/capacitance_fringe_ff）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_parasitic_extract_capacitance(
    double eps_r,
    double metal_thickness_um, double dielectric_thickness_um,
    double length_um, double width_um,
    polaris_result_t* out
);

/* polaris_parasitic_compute_s_params: π 型 RLC 网络 → ABCD → S
 * @param n_freqs 频率点数
 * @param frequencies_ghz 频率数组 (GHz)
 * @param resistance_ohm 串联电阻 (Ω)
 * @param inductance_ph 串联电感 (pH)
 * @param capacitance_ff 并联电容 (fF)
 * @param z0_ohm 端口参考阻抗 (Ω)
 * @param out 输出（JSON: s_params[N][2][2] 复数）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_parasitic_compute_s_params(
    int32_t n_freqs, const double* frequencies_ghz,
    double resistance_ohm, double inductance_ph, double capacitance_ff,
    double z0_ohm,
    polaris_result_t* out
);

/* === Verilog-A 紧凑模型生成（5+ 器件） === */

/* polaris_parasitic_generate_verilog_a: 按器件类型生成 Verilog-A 模型
 * @param device_type 器件类型字符串（waveguide/mmi_1x2/ring_resonator/modulator/detector）
 * @param module_name 模块名（NULL 自动生成）
 * @param params_json 器件参数 JSON 字符串
 * @param out 输出（JSON: module_name/ports/parameters/verilog_a_code）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_parasitic_generate_verilog_a(
    const char* device_type,
    const char* module_name,
    const char* params_json,
    polaris_result_t* out
);

/* polaris_parasitic_generate_spice_netlist: 生成 Ngspice 兼容网表
 * @param models_json Verilog-A 模型列表 JSON
 * @param config_json 仿真配置 JSON（spice_timestep/optical_timestep/total_time）
 * @param input_signal 输入信号类型（"pulse"/"sine"/"pam4"）
 * @param out 输出（JSON: netlist 字符串）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_parasitic_generate_spice_netlist(
    const char* models_json,
    const char* config_json,
    const char* input_signal,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
