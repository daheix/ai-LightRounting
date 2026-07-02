/*
 * circuit.h — polaris-circuit 子模块 C API 头文件
 *
 * PoLaRIS 电路级仿真子模块 C 接口（v5.0）。
 * 提供频域/时域/SPICE MNA/系统级光子电路仿真的 C 语言调用接口。
 *
 * 对应 Python 模块: polaris_circuit
 *
 * 学术诚信（R02）文献溯源:
 * - Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85
 *   https://arxiv.org/abs/2009.05146
 * - Ho, Ruehli, Brennan 1974, "Modified Nodal Approach", IEEE ISCAS
 *   https://ieeexplore.ieee.org/document/1084079
 * - Yee 1966, IEEE TAP AP-14(3):302-307
 *   https://ieeexplore.ieee.org/document/1138693
 * - Berenger 1994, JCP 114(2):185-200
 *   https://doi.org/10.1006/jcph.1994.1159
 * - ITU-T G.977, https://www.itu.int/rec/T-REC-G.977
 *
 * 合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy（C 绑定仅暴露标量接口）
 *       R05 无 TODO / R13 不保留 v4 兼容。
 */

#ifndef POLARIS_CIRCUIT_H
#define POLARIS_CIRCUIT_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdint.h>

/* ==========================================================================
 * 版本与常量
 * ========================================================================== */

#define POLARIS_CIRCUIT_VERSION_MAJOR 5
#define POLARIS_CIRCUIT_VERSION_MINOR 0
#define POLARIS_CIRCUIT_VERSION_PATCH 0

/* 真空光速 (m/s), CODATA 2018 */
#define POLARIS_C0 2.99792458e8

/* 真空介电常数 (F/m), CODATA 2018 */
#define POLARIS_EPS0 8.8541878128e-12

/* 真空磁导率 (H/m), CODATA 2018 */
#define POLARIS_MU0 1.25663706212e-6

/* 条件数阈值 (R03: 奇异时返回错误码，不 fall-back) */
#define POLARIS_COND_FG_THRESHOLD 1e6
#define POLARIS_COND_KLU_THRESHOLD 1e12

/* 错误码 */
typedef enum {
    POLARIS_CIRCUIT_OK = 0,              /* 成功 */
    POLARIS_CIRCUIT_ERR_INVALID_ARG = 1, /* 参数非法 */
    POLARIS_CIRCUIT_ERR_SINGULAR = 2,    /* 矩阵奇异 */
    POLARIS_CIRCUIT_ERR_NUMERICAL = 3,   /* 数值不稳定 */
    POLARIS_CIRCUIT_ERR_UNKNOWN = 4      /* 未知错误 */
} polaris_circuit_error_t;

/* ==========================================================================
 * S 参数字典（C 绑定为密集矩阵）
 * ========================================================================== */

/* S 参数密集矩阵: 形状 (n_ports, n_ports, n_freq)，复数 (实部+虚部) */
typedef struct {
    double *real;     /* 实部，长度 n_ports * n_ports * n_freq */
    double *imag;     /* 虚部，长度 n_ports * n_ports * n_freq */
    size_t n_ports;   /* 端口数 */
    size_t n_freq;    /* 频率点数 */
} polaris_sdict_t;

/* ==========================================================================
 * MNA SPICE 电路描述（DC + 瞬态）
 * ========================================================================== */

/* MNA 元件类型 */
typedef enum {
    POLARIS_MNA_RESISTOR = 0,
    POLARIS_MNA_CAPACITOR = 1,
    POLARIS_MNA_INDUCTOR = 2,
    POLARIS_MNA_VSOURCE = 3,
    POLARIS_MNA_ISOURCE = 4,
    POLARIS_MNA_DIODE = 5
} polaris_mna_element_type_t;

/* MNA 元件 */
typedef struct {
    polaris_mna_element_type_t type;
    int n1;         /* 节点1 (0 = GND) */
    int n2;         /* 节点2 (0 = GND) */
    double value1;  /* 主参数: R(Ω)/C(F)/L(H)/V(V)/I(A)/Is(A) */
    double value2;  /* 副参数: V.ac / D.Vt */
    double value3;  /* 副参数: V.freq */
} polaris_mna_element_t;

/* MNA 电路 */
typedef struct {
    polaris_mna_element_t *elements;
    size_t n_elements;
    int n_nodes;
} polaris_mna_circuit_t;

/* MNA DC 分析结果 */
typedef struct {
    double *node_voltages;  /* 长度 n_nodes */
    double *vsource_currents; /* 长度 = 电压源数 */
    size_t n_vsources;
    int n_nodes;
} polaris_mna_dc_result_t;

/* MNA 瞬态分析结果 */
typedef struct {
    double *time;            /* 时间数组，长度 n_points */
    double *node_voltages;   /* 节点电压，长度 n_points * n_nodes (row-major) */
    double *vsource_currents;/* 电压源电流，长度 n_points * n_vsources */
    size_t n_points;
    size_t n_vsources;
    int n_nodes;
} polaris_mna_transient_result_t;

/* ==========================================================================
 * 函数声明
 * ========================================================================== */

/*
 * 获取版本字符串。
 * 返回: 静态字符串 "5.0.0"。
 */
const char *polaris_circuit_version(void);

/*
 * MNA SPICE DC 分析（改进节点分析法）。
 *
 * 学术依据: Ho, Ruehli, Brennan 1974 IEEE ISCAS
 *   https://ieeexplore.ieee.org/document/1084079
 *
 * 参数:
 *   circuit  - MNA 电路描述
 *   result   - 输出 DC 分析结果（调用者负责释放）
 *
 * 返回:
 *   POLARIS_CIRCUIT_OK - 成功
 *   POLARIS_CIRCUIT_ERR_INVALID_ARG - 参数非法
 *   POLARIS_CIRCUIT_ERR_SINGULAR - MNA 矩阵奇异
 */
polaris_circuit_error_t polaris_mna_solve_dc(
    const polaris_mna_circuit_t *circuit,
    polaris_mna_dc_result_t *result);

/*
 * MNA SPICE 瞬态分析（后向欧拉法）。
 *
 * 学术依据: Pillage, "Electronic Circuit & System Simulation Methods",
 *   McGraw-Hill 1995, §9
 *
 * 参数:
 *   circuit  - MNA 电路描述
 *   t_total  - 总仿真时间 (s)
 *   dt       - 时间步长 (s)
 *   result   - 输出瞬态分析结果（调用者负责释放）
 *
 * 返回:
 *   POLARIS_CIRCUIT_OK - 成功
 *   POLARIS_CIRCUIT_ERR_INVALID_ARG - 参数非法（t_total<=0 或 dt<=0）
 *   POLARIS_CIRCUIT_ERR_SINGULAR - 某步 MNA 矩阵奇异
 */
polaris_circuit_error_t polaris_mna_solve_transient(
    const polaris_mna_circuit_t *circuit,
    double t_total,
    double dt,
    polaris_mna_transient_result_t *result);

/*
 * 计算 S 矩阵条件数 κ(S) = σ_max / σ_min。
 *
 * 学术依据: Golub & Van Loan, "Matrix Computations", 4th ed., §2.3
 *   https://www.press.jhu.edu/books/title/10876/matrix-computations
 *
 * 参数:
 *   sdict - S 参数密集矩阵
 *   cond  - 输出条件数
 *
 * 返回:
 *   POLARIS_CIRCUIT_OK - 成功
 *   POLARIS_CIRCUIT_ERR_INVALID_ARG - 参数非法
 *   POLARIS_CIRCUIT_ERR_SINGULAR - σ_min ≈ 0，矩阵奇异（cond = inf）
 */
polaris_circuit_error_t polaris_compute_condition_number(
    const polaris_sdict_t *sdict,
    double *cond);

/*
 * 频域波导 S 参数计算: S_{out,in} = exp(i·β·L)。
 *
 * 学术依据: Filipsson 1978, Simphony 2021
 *   https://doi.org/10.1109/EUMA.1978.332681
 *
 * 参数:
 *   wavelengths - 波长数组 (μm)，长度 n_freq
 *   n_freq      - 频率点数
 *   length      - 波导长度 (μm)
 *   neff        - 有效折射率
 *   loss_db_cm  - 损耗 (dB/cm)，0 表示无损
 *   s_out_in_real - 输出 S_{out,in} 实部，长度 n_freq（调用者分配）
 *   s_out_in_imag - 输出 S_{out,in} 虚部，长度 n_freq（调用者分配）
 *
 * 返回: POLARIS_CIRCUIT_OK 或 POLARIS_CIRCUIT_ERR_INVALID_ARG
 */
polaris_circuit_error_t polaris_waveguide_s(
    const double *wavelengths,
    size_t n_freq,
    double length,
    double neff,
    double loss_db_cm,
    double *s_out_in_real,
    double *s_out_in_imag);

/*
 * 群延迟计算 τ_g = dφ/dω（中心差分）。
 *
 * 学术依据: Agrawal, "Fiber-Optic Communication Systems", §2.4
 *
 * 参数:
 *   s_real, s_imag - S 参数复数数组，长度 n_freq
 *   wavelengths    - 波长数组 (μm)，长度 n_freq
 *   n_freq         - 频率点数
 *   tau            - 输出群延迟 (s)，长度 n_freq - 2（调用者分配）
 *
 * 返回: POLARIS_CIRCUIT_OK 或 POLARIS_CIRCUIT_ERR_INVALID_ARG
 */
polaris_circuit_error_t polaris_group_delay(
    const double *s_real,
    const double *s_imag,
    const double *wavelengths,
    size_t n_freq,
    double *tau);

/*
 * BER 计算（Q-factor 法）: BER = 0.5 · erfc(Q / √2)。
 *
 * 学术依据: ITU-T G.977
 *   https://www.itu.int/rec/T-REC-G.977
 *
 * 参数:
 *   q   - Q-factor
 *   ber - 输出 BER
 *
 * 返回: POLARIS_CIRCUIT_OK 或 POLARIS_CIRCUIT_ERR_INVALID_ARG
 */
polaris_circuit_error_t polaris_ber_from_q(double q, double *ber);

/*
 * 释放 MNA DC 分析结果内存。
 */
void polaris_mna_dc_result_free(polaris_mna_dc_result_t *result);

/*
 * 释放 MNA 瞬态分析结果内存。
 */
void polaris_mna_transient_result_free(polaris_mna_transient_result_t *result);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* POLARIS_CIRCUIT_H */
