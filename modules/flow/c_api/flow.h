#ifndef POLARIS_FLOW_H
#define POLARIS_FLOW_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_flow: 通用流程编排子模块 C ABI
 *
 * 提供商业级作业流程编排、IPKISS 兼容流程、Design Intent 引擎、
 * 分布式任务调度、AI 逆向设计与训练流水线能力的 C 接口。
 *
 * 迁移来源（v5.0 子模块化）:
 *   - polaris.flow/* (16 文件): Job/Stage/Recipe/Workspace/Tracker/Scheduler
 *     + IPKISSPCell/IPKISSView/SDLFlow/ClosedLoopValidator + DesignIntentEngine
 *   - polaris.pipeline/* (4 文件): training/curvy_router/default_simulator/_converters
 *   - polaris.system (1 文件): DistributedTaskScheduler
 *   - polaris.ai/* (3 文件): inverse_design/pdk_device_sampler/waveguide_simulator
 *
 * 设计原则:
 *   - R03 禁止 fall-back: 失败即返回 POLARIS_ERROR，无假数据
 *   - R04 不参与 GPU: 纯 NumPy/SciPy 实现
 *   - R13 不保留 v4 兼容: 内部 import 全部改为 polaris_flow.*
 */

/* === 作业流程系统 === */

/* polaris_flow_job_create: 创建作业
 *
 * @param name 作业名称
 * @param out 输出作业句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_job_create(
    const char* name,
    polaris_handle_t* out
);

/* polaris_flow_job_scheduler_submit: 提交作业到调度器
 *
 * @param scheduler 调度器句柄
 * @param job 作业句柄
 * @param out 输出作业 ID
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_job_scheduler_submit(
    polaris_handle_t scheduler,
    polaris_handle_t job,
    char* out_job_id,
    size_t job_id_size
);

/* polaris_flow_workspace_create: 创建工作区
 *
 * @param name 工作区名称
 * @param root_dir 根目录路径
 * @param out 输出工作区句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_workspace_create(
    const char* name,
    const char* root_dir,
    polaris_handle_t* out
);

/* === IPKISS 兼容流程 === */

/* polaris_flow_ipkiss_pcell_create: 创建 IPKISS 风格 PCell
 *
 * @param name PCell 名称
 * @param cell_type 器件类型（如 "mmi_1x2"、"waveguide"）
 * @param out 输出 PCell 句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_ipkiss_pcell_create(
    const char* name,
    const char* cell_type,
    polaris_handle_t* out
);

/* polaris_flow_ipkiss_sdl_run: 运行 Schematic-Driven Layout 流程
 *
 * @param pcell PCell 句柄
 * @param out 输出 SDL 结果（JSON 含 layout/netlist）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_ipkiss_sdl_run(
    polaris_handle_t pcell,
    polaris_result_t* out
);

/* === Design Intent 流程 === */

/* polaris_flow_design_intent_run: 运行 Design Intent 引擎
 *
 * 三层映射: 原理图 → 布局/布线/约束意图 → PDK 器件实例
 *
 * @param schematic 原理图（JSON 含 devices + connections）
 * @param out 输出意图结果（JSON 含 layout_intent/routing_intent/constraint_intent）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_design_intent_run(
    const char* schematic_json,
    polaris_result_t* out
);

/* === 分布式任务调度 === */

/* polaris_flow_distributed_scheduler_create: 创建分布式任务调度器
 *
 * 支持 backend: sequential / threading / asyncio
 *
 * @param backend 后端类型
 * @param num_workers worker 数量
 * @param out 输出调度器句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_distributed_scheduler_create(
    const char* backend,
    int num_workers,
    polaris_handle_t* out
);

/* polaris_flow_distributed_scheduler_submit: 提交分布式任务
 *
 * @param scheduler 调度器句柄
 * @param task_id 任务 ID
 * @param task_func 任务函数指针
 * @param task_arg 任务参数
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_flow_distributed_scheduler_submit(
    polaris_handle_t scheduler,
    const char* task_id,
    void (*task_func)(void*),
    void* task_arg
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_FLOW_H */
