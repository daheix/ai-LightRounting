"""PoLaRIS 训练子模块（polaris-trainer）。

集成 PoLaRIS v4 ``trainer/``（PPO 训练框架）与 ``rl/``（AlphaChip 高级 RL
算法）的核心功能，作为 v5.0 第 19 个独立子模块。**仅依赖 numpy**（R04: 不参与
GPU；R13: 保持功能独立），PPO 自动微分由内置 ``_nn`` 纯 NumPy 复刻提供，
EDA 环境通过依赖注入接入（调用方提供 Gymnasium 协议 env）。

==================================================================
Input（输入）
==================================================================
- ``PPOConfig`` / ``TrainConfig``：PPO 超参数（lr/gamma/gae_lambda/clip_eps/
  ent_coef/lr_schedule）与训练循环配置（num_episodes/rollout_steps/
  checkpoint_dir/early_stop_patience）。
- ``env`` / ``env_factory``：遵循 Gymnasium 协议的 EDA 环境（布局/布线），
  由调用方注入（``env.reset()→(obs,info)``，``env.step(a)→5-tuple``）。
- ``circuit``：电路描述 dict（含 devices/nets），供 R351-R355 RL 环境使用。
- 预训练 ``checkpoint``：JSON 文件，供 ``CheckpointManager`` 断点续训。

==================================================================
Process（处理）
==================================================================
- PPO 训练循环（``train_ppo`` / ``train_with_env_factory``）：
  rollout 采样 → GAE 优势估计 → 多 epoch 小批量 clipped surrogate 更新 →
  学习率调度（cosine/linear）→ 梯度裁剪 → 早停 → 周期 checkpoint。
- 高级 RL 算法（R351-R355）：
  - R351 ``LargeScalePlacementEnv``：占用栅格 + 图摘要双轨状态（O(N+E)）。
  - R352 ``PPOAdvantageOptimizer``：GAE + clipped loss + 熵正则 + 余弦退火。
  - R353 ``MultiObjectiveParetoReward``：面积/时延/损耗/串扰加权 + NSGA-II Pareto。
  - R354 ``PretrainedPolicyLibrary``：启发式/随机/课程学习 3 种基础策略。
  - R355 ``HybridPlacementAgent``：fix-then-optimize 手动约束 + RL 自动布局。

==================================================================
Output（输出）
==================================================================
- 训练后的 ``PPOAgent``（含 actor-critic 网络权重）与训练日志列表。
- ``checkpoint`` JSON 文件（断点续训 / 预训练-微调范式）。
- RL 布局结果：``placement`` dict {dev_id: {x, y, rotation}} 与多目标奖励指标。

==================================================================
学术依据（R02 学术诚信，≥5 个文献 URL）
==================================================================
1. Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
2. Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
3. Mirhoseini et al., Nature 2021, AlphaChip
   https://www.nature.com/articles/s41586-021-03544-w
4. Mirhoseini et al., Nature 2024 addendum, AlphaChip
   https://www.nature.com/articles/s41586-024-08032-5
5. Stable-Baselines3 PPO 实现 https://stable-baselines3.readthedocs.io/
6. CleanRL PPO 单文件实现 https://github.com/vwxyzjn/cleanrl
7. Loshchilov & Hutter, 2017, SGDR 余弦退火 https://arxiv.org/abs/1608.03983
8. Roijers et al., 2013, 多目标 RL Pareto https://arxiv.org/abs/1302.1563
9. Deb et al., 2002 IEEE TEVC, NSGA-II https://ieeexplore.ieee.org/document/996017
10. Bengio et al., ICML 2009, Curriculum Learning
    https://dl.acm.org/doi/abs/10.1145/1553374.1553380
11. Kingma & Ba, 2015, Adam 优化器 https://arxiv.org/abs/1412.6980
12. Bogaerts et al., JLT 2013, 波导交叉损耗 DOI: 10.1109/JLT.2013.2258874
13. Reed et al., Nat. Photonics 2010, 调制器时延 DOI: 10.1038/nphoton.2010.179

来源: 迁移自 PoLaRIS v4 ``src/polaris/trainer/`` + ``src/polaris/rl/``（R13）。
"""

from __future__ import annotations

from polaris_trainer.checkpoint import (
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
    CheckpointManager,
    PLATFORM_INP,
    PLATFORM_LNOI,
    PLATFORM_SIN,
    PLATFORM_SOI,
)
from polaris_trainer.distributed_rollout import (
    ENV_FACTORIES,
    ParallelRolloutCollector,
    RolloutBatch,
    collect_rollouts_parallel,
    register_env_factory,
)
from polaris_trainer.ppo import (
    ActorCritic,
    Minibatch,
    PPOAgent,
    PPOConfig,
    RolloutBuffer,
    Transition,
    compute_gae,
)
from polaris_trainer.rl_advanced import (
    GPU_DISABLED_R04,
    LargeScalePlacementConfig,
    LargeScalePlacementEnv,
    PPOAdvConfig,
    PPOAdvantageOptimizer,
)
from polaris_trainer.rl_pareto import (
    ALL_POLICIES,
    POLICY_CURRICULUM,
    POLICY_HEURISTIC,
    POLICY_RANDOM,
    HybridPlacementAgent,
    HybridPlacementConfig,
    MultiObjectiveParetoReward,
    MultiObjectiveRewardConfig,
    PretrainedPolicyConfig,
    PretrainedPolicyLibrary,
)
from polaris_trainer.train_loop import (
    ActionTransform,
    TrainConfig,
    discretize_floorplan_action,
    infer_obs_dim,
    load_agent,
    lr_scale,
    obs_to_vector,
    pad_obs,
    train_ppo,
    train_with_env_factory,
)

__version__ = "5.0.0"

# ReplayBuffer: PPO on-policy 经验回放缓冲（RolloutBuffer 的语义别名，
# 对齐任务要求的导出 API 名称）
ReplayBuffer = RolloutBuffer

__all__ = [
    # PPO 核心
    "PPOConfig",
    "ActorCritic",
    "RolloutBuffer",
    "ReplayBuffer",
    "Transition",
    "Minibatch",
    "compute_gae",
    "PPOAgent",
    # 训练循环
    "TrainConfig",
    "ActionTransform",
    "train_ppo",
    "train_with_env_factory",
    "load_agent",
    "lr_scale",
    "obs_to_vector",
    "infer_obs_dim",
    "pad_obs",
    "discretize_floorplan_action",
    # R351-R352 高级 RL
    "GPU_DISABLED_R04",
    "LargeScalePlacementConfig",
    "LargeScalePlacementEnv",
    "PPOAdvConfig",
    "PPOAdvantageOptimizer",
    # R353-R355 多目标/预训练/混合布局
    "MultiObjectiveRewardConfig",
    "MultiObjectiveParetoReward",
    "PretrainedPolicyConfig",
    "PretrainedPolicyLibrary",
    "HybridPlacementConfig",
    "HybridPlacementAgent",
    "POLICY_HEURISTIC",
    "POLICY_RANDOM",
    "POLICY_CURRICULUM",
    "ALL_POLICIES",
    # R35 CPU 多进程并行 rollout
    "RolloutBatch",
    "ParallelRolloutCollector",
    "collect_rollouts_parallel",
    "register_env_factory",
    "ENV_FACTORIES",
    # Checkpoint 管理
    "CheckpointManager",
    "ALL_PLATFORMS",
    "CIRCUIT_TEMPLATES",
    "PLATFORM_SOI",
    "PLATFORM_SIN",
    "PLATFORM_INP",
    "PLATFORM_LNOI",
    "__version__",
]
