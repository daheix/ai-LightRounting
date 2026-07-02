/**
 * @file polaris_types.h
 * @brief PoLaRIS C ABI 公共类型定义
 *
 * 所有子模块共享的统一数据结构，用于 Python ↔ C 跨语言传递。
 * 设计原则：
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - row-major 内存布局（与 numpy 一致）
 * - 显式生命周期（caller 负责 free）
 *
 * 来源: numpy ndarray C API + klayout db API 设计参考
 */
#ifndef POLARIS_TYPES_H
#define POLARIS_TYPES_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 错误码（所有函数返回 polaris_error_t，0=成功，非0=错误码）
 * ========================================================================= */
typedef int32_t polaris_error_t;

#define POLARIS_OK              0    /* 成功 */
#define POLARIS_ERR_INVALID     1    /* 参数非法 */
#define POLARIS_ERR_NOMEM       2    /* 内存不足 */
#define POLARIS_ERR_NOTFOUND    3    /* 资源未找到（如 PDK/器件） */
#define POLARIS_ERR_SIMULATION  4    /* 仿真失败（如 FDTD 不收敛） */
#define POLARIS_ERR_VERIFICATION 5   /* 验证失败（如 DRC 违规） */
#define POLARIS_ERR_IO          6    /* 文件 IO 失败 */
#define POLARIS_ERR_UNSUPPORTED 7    /* 功能不支持 */

/* =========================================================================
 * 张量结构（替代 numpy ndarray 跨语言传递）
 * ========================================================================= */
typedef enum {
    POLARIS_DTYPE_F32 = 0,   /* float32 */
    POLARIS_DTYPE_F64 = 1,   /* float64 */
    POLARIS_DTYPE_I32 = 2,   /* int32 */
    POLARIS_DTYPE_I64 = 3,   /* int64 */
    POLARIS_DTYPE_C64 = 4,   /* complex64 (实部+虚部交错) */
    POLARIS_DTYPE_C128 = 5,  /* complex128 (实部+虚部交错) */
} polaris_dtype_t;

typedef struct {
    void* data;              /* 数据指针（row-major，与 numpy 一致） */
    int32_t ndim;            /* 维度数 */
    int64_t* shape;          /* 形状数组（长度 ndim，caller 分配/free） */
    int32_t dtype;           /* polaris_dtype_t */
    int32_t owns_data;       /* 1=本结构 owns data（free 时需 free data），0=外部 owns */
} polaris_tensor_t;

/* =========================================================================
 * 端口结构（器件端口定义）
 * ========================================================================= */
typedef struct {
    char* name;              /* 端口名（如 "in", "out1"） */
    double dx_um;            /* 相对器件原点的 x 偏移 (μm) */
    double dy_um;            /* 相对器件原点的 y 偏移 (μm) */
    char* direction;         /* 方向: "north"/"south"/"east"/"west" */
} polaris_port_t;

/* =========================================================================
 * 器件规格（替代 DeviceSpec）
 * ========================================================================= */
typedef struct {
    char* name;              /* 器件实例名（如 "gc1"） */
    char* device_type;       /* 器件类型（如 "grating_coupler"） */
    double width_um;         /* 器件宽度 (μm) */
    double height_um;        /* 器件高度 (μm) */
    int32_t n_ports;         /* 端口数 */
    polaris_port_t* ports;   /* 端口数组 */
    int32_t n_params;        /* 参数键值对数 */
    char** param_keys;       /* 参数键数组（长度 n_params） */
    char** param_values;     /* 参数值数组（字符串形式，长度 n_params） */
    char* process_node;      /* 工艺节点（如 "220nm SOI"），可为 NULL */
} polaris_device_spec_t;

/* =========================================================================
 * 连接结构（替代 CircuitSpec.connections 元组）
 * ========================================================================= */
typedef struct {
    char* dev1_name;         /* 器件 1 名 */
    char* port1_name;        /* 器件 1 端口名 */
    char* dev2_name;         /* 器件 2 名 */
    char* port2_name;        /* 器件 2 端口名 */
} polaris_connection_t;

/* =========================================================================
 * 电路规格（替代 CircuitSpec）
 * ========================================================================= */
typedef struct {
    char* name;              /* 电路名（如 "MZI"） */
    int32_t n_devices;       /* 器件数 */
    polaris_device_spec_t* devices;  /* 器件数组 */
    int32_t n_connections;   /* 连接数 */
    polaris_connection_t* connections; /* 连接数组 */
    double canvas_w_um;      /* 画布宽度 (μm) */
    double canvas_h_um;      /* 画布高度 (μm) */
    char* process_node;      /* 工艺节点，可为 NULL */
    double optical_wavelength_nm; /* 工作波长 (nm) */
} polaris_circuit_t;

/* =========================================================================
 * 布局结果（place_circuit 输出）
 * ========================================================================= */
typedef struct {
    char* device_name;       /* 器件名 */
    double x;                /* 左下角 x (μm) */
    double y;                /* 左下角 y (μm) */
    double w;                /* 宽度 (μm) */
    double h;                /* 高度 (μm) */
} polaris_placement_t;

typedef struct {
    int32_t n_placements;             /* 布局数 */
    polaris_placement_t* placements;  /* 布局数组 */
    double hpwl;                      /* 半周长线长 (μm) */
    char* placement_mode;             /* 布局模式（如 "ppo_gnn_init"） */
    int32_t checkpoint_loaded;        /* 是否加载预训练 checkpoint */
} polaris_placement_result_t;

/* =========================================================================
 * 布线结果（route_circuit 输出）
 * ========================================================================= */
typedef struct {
    char* dev1_name;
    char* port1_name;
    char* dev2_name;
    char* port2_name;
    int32_t n_points;        /* 路径点数 */
    double* xs;              /* x 坐标数组 (μm) */
    double* ys;              /* y 坐标数组 (μm) */
    double loss_db;          /* 该路径损耗 (dB) */
    int32_t n_bends;         /* 弯曲数 */
    int32_t n_crossings;     /* 交叉数 */
} polaris_path_t;

typedef struct {
    int32_t n_paths;         /* 路径数 */
    polaris_path_t* paths;   /* 路径数组 */
    double total_loss_db;    /* 总损耗 (dB) */
    char* router_type;       /* 路由器类型（如 "curvy"） */
} polaris_routing_result_t;

/* =========================================================================
 * 通用结果（仿真/验证等，用 dict 表达，C 用 JSON 字符串）
 * ========================================================================= */
typedef struct {
    char* json;              /* JSON 字符串结果（caller 负责 free） */
    int32_t success;         /* 1=成功，0=失败 */
    char* error_message;     /* 错误信息（失败时），可为 NULL */
} polaris_result_t;

/* =========================================================================
 * 内存管理函数（caller 用这些 free 子模块返回的结构）
 * ========================================================================= */
void polaris_tensor_free(polaris_tensor_t* t);
void polaris_circuit_free(polaris_circuit_t* c);
void polaris_placement_result_free(polaris_placement_result_t* r);
void polaris_routing_result_free(polaris_routing_result_t* r);
void polaris_result_free(polaris_result_t* r);

#ifdef __cplusplus
}
#endif

#endif /* POLARIS_TYPES_H */
