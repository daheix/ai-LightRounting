/**
 * @file multiphysics.h
 * @brief PoLaRIS polaris-multiphysics 子模块 C ABI 接口声明
 *
 * 与 Python API（DDMSolver/HeatSolver/VarFDTDSolver/RCWASolver/FETDSolver/
 * ThermalSolver2D 等）一一对应。类型定义见 ../_c_abi/polaris_types.h
 * （polaris_result_t / polaris_error_t）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致:
 *   - 参数非法返回 POLARIS_ERR_INVALID
 *   - 仿真失败（如 NaN/不收敛）返回 POLARIS_ERR_SIMULATION
 *
 * 来源（R02 学术诚信，≥5 个文献 URL）:
 * - Scharfetter & Gummel 1969 IEEE TED https://doi.org/10.1109/T-ED.1969.16766
 * - Cocorullo 1999 IEEE JSTQE https://doi.org/10.1109/2944.788409
 * - Soref & Bennett 1987 IEEE JQE https://doi.org/10.1109/JQE.1987.1073206
 * - Moharam 1995 JOSA A 12 1077 https://doi.org/10.1364/JOSAA.12.001077
 * - Chang 1980 IEEE TMTT 28(8) 889 https://doi.org/10.1109/TMTT.1980.1130551
 * - Newmark 1959 ASCE J Eng Mech Div https://doi.org/10.1061/JMCEA3.0000097
 * - Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
 * - Carslaw & Jaeger 1959 Conduction of Heat in Solids
 */
#ifndef POLARIS_MULTIPHYSICS_H
#define POLARIS_MULTIPHYSICS_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_mp_ddm_solve: 漂移扩散求解器（PN 结稳态，牛顿法）
 * @param nx 网格 x 节点数
 * @param dx 网格间距 [m]
 * @param va/anode_v 阳极电压 [V]
 * @param vc/cathode_v 阴极电压 [V]
 * @param out 输出结果（JSON: potential/n/p/current_density 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_mp_ddm_solve(
    int32_t nx, double dx, double va, double vc,
    polaris_result_t* out
);

/* polaris_mp_heat_solve: 稳态热传导求解器（5 点有限差分）
 * @param nx/nz 网格节点数
 * @param dx/dz 网格间距 [m]
 * @param t_sub 衬底温度 [K]
 * @param out 输出结果（JSON: temperature/max_temp 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_mp_heat_solve(
    int32_t nx, int32_t nz, double dx, double dz, double t_sub,
    polaris_result_t* out
);

/* polaris_mp_varfdtd_solve: 2.5D VarFDTD 求解器（EIM + 2D Yee leapfrog）
 * @param wavelength_um 波长 [μm]
 * @param dx_um 网格步长 [μm]
 * @param n_steps 时间步数
 * @param out 输出结果（JSON: n_eff/s21/energy 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_mp_varfdtd_solve(
    double wavelength_um, double dx_um, int32_t n_steps,
    polaris_result_t* out
);

/* polaris_mp_rcwa_solve_1d: 1D RCWA 光栅求解器（TE/TM，Moharam 1995 ETM）
 * @param wavelength_um 波长 [μm]
 * @param n_harmonics 谐波数
 * @param out 输出结果（JSON: t_eff/r_eff/te_tm 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_mp_rcwa_solve_1d(
    double wavelength_um, int32_t n_harmonics,
    polaris_result_t* out
);

/* polaris_mp_fetd_step: FETD 单步 Newmark-β 时间积分
 * @param dt 时间步 [s]
 * @param out 输出结果（JSON: e_field/energy 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_mp_fetd_step(
    double dt, polaris_result_t* out
);

/* polaris_mp_thermal_2d: TCAD 2D 稳态热仿真（ThermalSolver2D）
 * @param width_um 器件宽度 [μm]
 * @param nx 网格节点数
 * @param t_sub 衬底温度 [K]
 * @param out 输出结果（JSON: temperature/max_temp/avg_temp 等）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_mp_thermal_2d(
    double width_um, int32_t nx, double t_sub,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif
