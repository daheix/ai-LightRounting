/*
 * polaris-verify-advanced C ABI 头文件
 *
 * PoLaRIS 高级验证子模块的 C 语言接口声明，用于 FFI / ctypes / pybind11 桥接。
 *
 * 学术依据（≥5 文献 URL，R02 学术诚信）:
 * - He et al. 2023, "OpenDRC", DAC 2023, https://doi.org/10.1109/DAC56929.2023.10247734
 * - Siemens Calibre eqDRC:
 *   https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
 * - Siemens Calibre xACT: https://eda.sw.siemens.com/en-US/calibre/
 * - Wang et al., SPIE 6349, 63492Z (2006), doi:10.1117/12.685727
 * - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 * - KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html
 * - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
 *
 * 合规: R02 / R03 / R04（纯 CPU）/ R05 无 TODO。
 */

#ifndef POLARIS_VERIFY_ADVANCED_H
#define POLARIS_VERIFY_ADVANCED_H

#ifdef __cplusplus
extern "C" {
#endif

/* ===========================================================================
 * 1. 版本信息
 * =========================================================================== */

#define POLARIS_VERIFY_ADVANCED_VERSION_MAJOR 1
#define POLARIS_VERIFY_ADVANCED_VERSION_MINOR 0
#define POLARIS_VERIFY_ADVANCED_VERSION_PATCH 0
#define POLARIS_VERIFY_ADVANCED_VERSION "1.0.0"

/* ===========================================================================
 * 2. 错误码（R03: 失败即返回非零，禁止静默兜底）
 * =========================================================================== */

typedef enum {
    POLARIS_VA_OK = 0,              /* 成功 */
    POLARIS_VA_ERR_NULL_PTR = 1,    /* 空指针 */
    POLARIS_VA_ERR_INVALID_ARG = 2, /* 非法参数 */
    POLARIS_VA_ERR_FILE_NOT_FOUND = 3, /* 文件不存在 */
    POLARIS_VA_ERR_KLAYOUT_MISSING = 4, /* klayout 不可用 */
    POLARIS_VA_ERR_PARSE_FAILED = 5,   /* GDS 解析失败 */
    POLARIS_VA_ERR_EMPTY_LAYOUT = 6,   /* 空版图 */
    POLARIS_VA_ERR_INTERNAL = 99       /* 内部错误 */
} polaris_va_error_t;

/* ===========================================================================
 * 3. DRC 检查类型（对齐 Python DRCCheckType 枚举）
 *    来源: KLayout DRC API https://www.klayout.de/doc-qt5/manual/drc_runsets.html
 * =========================================================================== */

typedef enum {
    POLARIS_VA_DRC_WIDTH = 0,
    POLARIS_VA_DRC_SPACE = 1,
    POLARIS_VA_DRC_NOTCH = 2,
    POLARIS_VA_DRC_ENCLOSE = 3,
    POLARIS_VA_DRC_AREA = 4,
    POLARIS_VA_DRC_DENSITY = 5,
    POLARIS_VA_DRC_VIA = 6
} polaris_va_drc_check_type_t;

/* ===========================================================================
 * 4. LVS 不匹配类型（对齐 Python LVSMismatchType 枚举）
 * =========================================================================== */

typedef enum {
    POLARIS_VA_LVS_NET_COUNT = 0,
    POLARIS_VA_LVS_NODE_COUNT = 1,
    POLARIS_VA_LVS_NET_NAME = 2,
    POLARIS_VA_LVS_DEVICE_PARAM = 3,
    POLARIS_VA_LVS_CONNECTIVITY = 4
} polaris_va_lvs_mismatch_type_t;

/* ===========================================================================
 * 5. DRC 违规结果结构体
 * =========================================================================== */

typedef struct {
    int rule_id;            /* 规则 ID */
    int check_type;         /* polaris_va_drc_check_type_t */
    int layer_number;       /* GDS layer number */
    int layer_datatype;     /* GDS datatype */
    double location_x_um;   /* 违规位置 X (μm) */
    double location_y_um;   /* 违规位置 Y (μm) */
    double measured_value;  /* 实测值 */
    double threshold_value; /* 阈值 */
    int severity;           /* 0=error, 1=warning */
} polaris_va_drc_violation_t;

/* ===========================================================================
 * 6. 核心函数声明
 *
 * 注: 当前以 Python 实现为主，C ABI 为未来 pybind11/cffi 桥接预留。
 *     所有函数返回 polaris_va_error_t，非零表示失败（R03 禁止 fall-back）。
 * =========================================================================== */

/*
 * 获取版本字符串。
 * 返回: 静态字符串指针，无需释放。
 */
const char *polaris_va_get_version(void);

/*
 * 对 GDS 文件运行 KLayout DRC runset（对齐 KLayoutDRCRunner.run_gds）。
 *
 * 参数:
 *   gds_path     - GDS 文件路径（UTF-8）
 *   runset_name  - runset 名（"SiEPIC_EBeam" 或 "custom"）
 *   out_violations - 输出违规数组指针（调用方分配）
 *   out_count    - 输出违规数量
 *   out_passed   - 输出通过规则数
 *   out_total    - 输出总规则数
 *
 * 返回: POLARIS_VA_OK 成功，非零失败。
 * 来源: KLayout DRC API https://www.klayout.de/doc-qt5/manual/drc_runsets.html
 */
polaris_va_error_t polaris_va_run_klayout_drc(
    const char *gds_path,
    const char *runset_name,
    polaris_va_drc_violation_t *out_violations,
    int *out_count,
    int *out_passed,
    int *out_total
);

/*
 * 运行图同构 LVS 比对（对齐 GraphIsomorphismLVSComparer）。
 *
 * 参数:
 *   reference_gds  - 参考网表 GDS 路径
 *   extracted_gds  - 提取网表 GDS 路径
 *   out_mismatch_count - 输出不匹配数
 *
 * 返回: POLARIS_VA_OK 成功，非零失败。
 * 来源: VF2 同构算法, Cordella et al., IEEE TPAMI 26(10), 2004,
 *       doi:10.1109/TPAMI.2004.75
 */
polaris_va_error_t polaris_va_run_graph_lvs(
    const char *reference_gds,
    const char *extracted_gds,
    int *out_mismatch_count
);

/*
 * 从 GDS 文件提取寄生参数（对齐 ParasiticExtractor.extract）。
 *
 * 参数:
 *   gds_path      - GDS 文件路径
 *   out_total_r   - 输出总电阻 (Ω)
 *   out_total_c   - 输出总电容 (F)
 *   out_element_count - 输出元件数
 *
 * 返回: POLARIS_VA_OK 成功，非零失败。
 * 来源: Calibre xACT https://eda.sw.siemens.com/en-US/calibre/
 *       Banerjee ECE 225, 寄生电容公式
 */
polaris_va_error_t polaris_va_extract_parasitics(
    const char *gds_path,
    double *out_total_r,
    double *out_total_c,
    int *out_element_count
);

/*
 * 运行光刻友好设计检查（对齐 LithoFriendlyChecker.check）。
 *
 * 参数:
 *   gds_path    - GDS 文件路径
 *   out_score   - 输出光刻友好度评分 (0-100)
 *   out_hotspot_count - 输出热点数
 *
 * 返回: POLARIS_VA_OK 成功，非零失败。
 * 来源: Wang et al., SPIE 6349, 63492Z (2006), doi:10.1117/12.685727
 */
polaris_va_error_t polaris_va_check_litho_friendly(
    const char *gds_path,
    double *out_score,
    int *out_hotspot_count
);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* POLARIS_VERIFY_ADVANCED_H */
