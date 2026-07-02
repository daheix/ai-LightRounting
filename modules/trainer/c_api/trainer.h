/**
 * @file trainer.h
 * @brief PoLaRIS polaris-trainer 子模块 C ABI 接口声明
 *
 * 与 Python API（train_ppo / PPOAgent / CheckpointManager）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h
 * （polaris_tensor_t / polaris_result_t 等 POD 结构）。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构（polaris_result_free）
 * - 错误码语义与 Python 异常一致（R03 禁止 fall-back）:
 *   - 检查点不存在返回 POLARIS_ERR_NOTFOUND
 *   - 参数非法返回 POLARIS_ERR_INVALID
 * - R04: 不参与 GPU，纯 NumPy CPU 实现
 *
 * 来源（R02 学术诚信）:
 * - Schulman 2017 PPO https://arxiv.org/abs/1707.06347
 * - Schulman 2015 GAE https://arxiv.org/abs/1506.02438
 * - Mirhoseini 2021 Nature AlphaChip
 *   https://www.nature.com/articles/s41586-021-03544-w
 * - Stable-Baselines3 PPO https://stable-baselines3.readthedocs.io/
 * - numpy ndarray C API:
 *   https://numpy.org/doc/stable/reference/c-api/types-and-structures.html
 */
#ifndef POLARIS_TRAINER_H
#define POLARIS_TRAINER_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_trainer_train_ppo: PPO 训练循环（单 env）
 * Input:
 *   agent_state     PPO 智能体参数张量（actor-critic 权重，row-major）
 *   obs_dim         观测维度
 *   action_dim      动作维度
 *   env_handle      调用方注入的 Gymnasium env 句柄（C 侧 opaque 指针）
 *   num_episodes    训练轮数
 *   rollout_steps   每轮采样步数
 * Process:
 *   rollout 采样 → GAE 优势估计 → 多 epoch 小批量 clipped surrogate 更新 →
 *   学习率调度 → 梯度裁剪 → 早停 → 周期 checkpoint。
 * Output:
 *   out->json       JSON 含 trained_params / training_log / final_lr
 * 参考: https://arxiv.org/abs/1707.06347
 * @return POLARIS_OK 或错误码（POLARIS_ERR_INVALID / POLARIS_ERR_SIMULATION）
 */
polaris_error_t polaris_trainer_train_ppo(
    const polaris_tensor_t* agent_state,
    int32_t obs_dim,
    int32_t action_dim,
    void* env_handle,
    int32_t num_episodes,
    int32_t rollout_steps,
    polaris_result_t* out
);

/* polaris_trainer_ppo_update: 单步 PPO 更新（GAE + clipped surrogate）
 * Input:
 *   rollout         rollout 张量集（obs/actions/rewards/logprobs/values/dones）
 *   config_json     PPO 超参数 JSON（lr/gamma/gae_lambda/clip_eps/...）
 * Process:
 *   GAE 优势估计 → 标准化 → clipped policy loss + value loss + 熵正则。
 * Output:
 *   out->json       JSON 含 policy_loss / value_loss / entropy / clip_frac
 * 参考: https://arxiv.org/abs/1707.06347
 * @return POLARIS_OK 或 POLARIS_ERR_INVALID（rollout 字段缺失）
 */
polaris_error_t polaris_trainer_ppo_update(
    const polaris_tensor_t* rollout,
    const char* config_json,
    polaris_result_t* out
);

/* polaris_trainer_checkpoint_save: 保存预训练 checkpoint
 * Input:
 *   agent_state     PPO 智能体参数张量
 *   path            checkpoint 文件路径
 *   metadata_json   预训练元信息 JSON（platform/circuit_template/...）
 * Process:
 *   序列化 actor-critic 权重 + 追加 pretrain_metadata。
 * Output:
 *   out->json       JSON 含 checkpoint_path / version
 * 参考: https://www.nature.com/articles/s41586-021-03544-w
 * @return POLARIS_OK 或 POLARIS_ERR_IO（路径不可写）
 */
polaris_error_t polaris_trainer_checkpoint_save(
    const polaris_tensor_t* agent_state,
    const char* path,
    const char* metadata_json,
    polaris_result_t* out
);

/* polaris_trainer_checkpoint_load: 加载预训练 checkpoint（断点续训）
 * Input:
 *   path            checkpoint 文件路径
 * Process:
 *   反序列化 actor-critic 权重 + 读取 pretrain_metadata。
 * Output:
 *   out->json       JSON 含 agent_params / pretrain_metadata
 * 参考: https://www.nature.com/articles/s41586-021-03544-w
 * @return POLARIS_OK 或 POLARIS_ERR_NOTFOUND（checkpoint 不存在，R03 禁止 fall-back）
 */
polaris_error_t polaris_trainer_checkpoint_load(
    const char* path,
    polaris_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_TRAINER_H */
