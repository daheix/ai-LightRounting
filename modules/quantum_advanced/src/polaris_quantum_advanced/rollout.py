"""PPO Rollout 采集与 GAE 优势估计（纯 NumPy，R04 不参与 GPU）。

从 distributed_ppo.py 拆分而来（R11 质量门禁：文件≤800行），保留原始文献溯源。

本模块包含 PPO 训练中的 rollout 采集逻辑与 GAE 优势估计，作为独立函数提供，
供 DistributedPPOTrainer 调用。

学术依据（R02）:
- Schulman et al., "High-Dimensional Continuous Control Using
  Generalized Advantage Estimation", ICLR 2016.
  URL: https://arxiv.org/abs/1506.02438
- Schulman et al., "Proximal Policy Optimization Algorithms", arXiv:1707.06347, 2017.
  URL: https://arxiv.org/abs/1707.06347
- Sutton & Barto, "Reinforcement Learning: An Introduction", 2nd ed., 2018.
  URL: http://incompleteideas.net/book/the-book-2nd.html
- Mnih et al., "Asynchronous Methods for Deep Reinforcement Learning", ICML 2016.
  URL: http://proceedings.mlr.press/v48/mniha16.html
- Sutton, "Learning to Predict by the Methods of Temporal Differences", MLJ 1988.
  URL: https://link.springer.com/article/10.1007/BF00115009
- OpenAI Gym/Gymnasium API 标准
  URL: https://gymnasium.farama.org/api/env/
- Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
  URL: https://refactoring.com/catalog/extractFunction.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def compute_gae(
    rewards: NDArray[np.float64],
    values: NDArray[np.float64],
    next_values: NDArray[np.float64],
    dones: NDArray[np.bool_],
    gamma: float = 0.99,
    lam: float = 0.95,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Generalized Advantage Estimation (GAE)。

    δ_t = r_t + γ V(s_{t+1}) · (1 - done_t) - V(s_t)
    Â_t = Σ_{l=0}^∞ (γλ)^l δ_{t+l}

    终止状态处理:
    - 若 done_t=True，则 s_{t+1} 为终止状态，V(s_{t+1}) 不参与 bootstrap（乘 0）
    - 若 done_t=False，则用 V(s_{t+1}) 进行 bootstrap

    Args:
        rewards: 即时奖励序列 r_t。
        values: V(s_t) 价值估计序列。
        next_values: V(s_{t+1}) 下一状态价值估计序列。
        dones: 终止标志序列（True 表示该步为 episode 最后一步）。
        gamma: 折扣因子 γ ∈ [0, 1)。
        lam: GAE 参数 λ ∈ [0, 1]。

    Returns:
        (advantages, returns) 元组：
        - advantages: 标准化后的 GAE 优势 Â_t
        - returns: 价值回归目标 R_t = Â_t + V(s_t)

    Raises:
        ValueError: 空序列或数组长度不一致。

    文献:
    - Schulman et al., "High-Dimensional Continuous Control Using
      Generalized Advantage Estimation", ICLR 2016.
      URL: https://arxiv.org/abs/1506.02438
    - Sutton & Barto, "Reinforcement Learning: An Introduction", 2nd ed., 2018.
      URL: http://incompleteideas.net/book/the-book-2nd.html
    - Schulman et al., "Proximal Policy Optimization Algorithms", arXiv:1707.06347, 2017.
      URL: https://arxiv.org/abs/1707.06347
    - Mnih et al., "Asynchronous Methods for Deep Reinforcement Learning", ICML 2016.
      URL: http://proceedings.mlr.press/v48/mniha16.html
    - Sutton, "Learning to Predict by the Methods of Temporal Differences", MLJ 1988.
      URL: https://link.springer.com/article/10.1007/BF00115009
    """
    n = len(rewards)
    if n == 0:
        raise ValueError("GAE: 空序列")
    if len(values) != n or len(next_values) != n or len(dones) != n:
        raise ValueError("GAE: 输入数组长度不一致")

    advantages_raw = np.zeros(n, dtype=np.float64)
    last_adv = 0.0
    not_done = (~dones).astype(np.float64)

    for t in reversed(range(n)):
        delta = rewards[t] + gamma * next_values[t] * not_done[t] - values[t]
        last_adv = delta + gamma * lam * not_done[t] * last_adv
        advantages_raw[t] = last_adv

    returns = advantages_raw + values

    advantages = advantages_raw.copy()
    if np.std(advantages) > 1e-8:
        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

    return advantages, returns


def aggregate_rollouts(rollouts: list) -> tuple:
    """聚合各 worker rollout 为统一张量（Extract Method）。

    Args:
        rollouts: 各 worker 的 rollout 字典列表（每个含 obs/next_obs/actions/
            rewards/old_log_probs/dones 等键）。

    Returns:
        (all_obs, all_next_obs, all_actions, all_rewards,
         all_old_log_probs, all_dones) 六元组。

    Raises:
        ValueError: rollouts 为空列表。

    文献:
    - Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
      URL: https://refactoring.com/catalog/extractFunction.html
    """
    if not rollouts:
        raise ValueError("rollouts 不能为空")
    all_obs = np.vstack([r["obs"] for r in rollouts])
    all_next_obs = np.vstack([r["next_obs"] for r in rollouts])
    all_actions = np.concatenate([r["actions"] for r in rollouts])
    all_rewards = np.concatenate([r["rewards"] for r in rollouts])
    all_old_log_probs = np.concatenate([r["old_log_probs"] for r in rollouts])
    all_dones = np.concatenate([r["dones"] for r in rollouts])
    return (all_obs, all_next_obs, all_actions, all_rewards,
            all_old_log_probs, all_dones)


def synthetic_env_step(
    obs: NDArray[np.float64],
    action: int,
    n_devices: int,
    step: int,
    rng: np.random.Generator,
    action_dim: int,
    obs_dim: int,
) -> tuple[NDArray[np.float64], float, bool]:
    """合成测试环境步进（仅用于 PPO 算法单元测试，非真实布局环境）。

    警告（R02 学术诚信）:
        本函数是一个**合成测试夹具**（synthetic test fixture），用于验证
        PPO-Clip + GAE 算法实现是否正确（梯度截断、终止状态边界、
        多 episode 分离等）。奖励公式中的常数（20.0、0.01、0.05、0.5、
        1.0、-2.0）是**任意设定的测试信号**，不来自任何文献，**不能**
        作为真实布局布线环境的奖励函数。

        真实训练必须注入 FloorplanEnv（来自 polaris.engine.floorplan_env），
        通过 set_real_env(env) 方法设置；若未注入而调用 training_step，
        将 raise RuntimeError 拒绝运行（R03 禁止 fall-back：禁止用合成
        环境冒充真实环境训练出"看似可用"的策略）。

    合成奖励设计（无文献依据，仅保证 PPO 能收敛的测试信号）:
        reward = -hpwl_test - congestion_test + legal_test
        - hpwl_test: 随 step 指数衰减的测试信号（模拟"线长逐渐收敛"）
        - congestion_test: 偏离 action=3 时的测试惩罚（任意中点）
        - legal_test: 边界 action 的测试奖励/惩罚

    Args:
        obs: 当前观测向量。
        action: 离散动作索引。
        n_devices: 电路器件数（合成环境未使用，保留接口）。
        step: 当前 episode 内步数。
        rng: NumPy 随机数生成器。
        action_dim: 动作空间维度。
        obs_dim: 观测空间维度。

    Returns:
        (next_obs, reward, done) 三元组。
    """
    # 合成测试信号（无文献依据）
    hpwl_test = 20.0 * np.exp(-step * 0.01) * (1.0 - action * 0.05)
    congestion_test = abs(action - 3) * 0.5
    legal_test = 1.0 if action < action_dim - 1 else -2.0
    reward = -hpwl_test - congestion_test + legal_test
    # 状态转移（合成随机游走）
    next_obs = obs + rng.normal(0, 0.1, obs_dim)
    next_obs = np.clip(next_obs, -1.0, 1.0)
    done = (step >= 20)
    return next_obs, float(reward), done


def collect_rollout(
    n_episodes: int,
    worker_id: int,
    global_step: int,
    policy: Any,
    config: Any,
    real_env: Any,
    use_synthetic: bool,
) -> dict[str, Any]:
    """单个 worker 采集 rollout 数据。

    R05 v4.0-FAKE-ENV-P0（第3轮迭代发现）:
        守门逻辑 — 若未注入真实环境（real_env is None）且
        synthetic_env_mode=False（默认），则 raise RuntimeError 拒绝采集。
        禁止用合成环境冒充真实环境训练出"看似可用"的策略（R03）。
        算法单元测试需显式设置 synthetic_env_mode=True 才能使用
        synthetic_env_step（任意测试信号，无文献依据）。

    Args:
        n_episodes: 本 worker 采集的回合数。
        worker_id: Worker 编号（用于设置 RNG 种子）。
        global_step: 全局训练步数（用于设置 RNG 种子）。
        policy: 策略网络实例（_PolicyNetwork）。
        config: DistributedPPOConfig 实例。
        real_env: 真实环境实例（None 表示未注入）。
        use_synthetic: 是否使用合成测试环境（仅算法单元测试允许 True）。

    Returns:
        rollout 字典，含 obs/next_obs/actions/rewards/old_log_probs/dones/
        mean_reward/n_episodes/n_steps 键。

    Raises:
        RuntimeError: real_env is None 且 use_synthetic=False（R03）。

    文献:
    - Schulman et al., "PPO", arXiv:1707.06347, 2017
      URL: https://arxiv.org/abs/1707.06347
    - OpenAI Gymnasium API: https://gymnasium.farama.org/api/env/
    """
    # 守门: 真实环境 vs 合成测试环境
    if real_env is None and not use_synthetic:
        raise RuntimeError(
            "未注入真实布局布线环境（real_env is None）且 "
            "synthetic_env_mode=False。R03 禁止 fall-back：禁止用合成环境"
            "冒充真实环境训练。请: 1) 调用 set_real_env(env) 注入 "
            "FloorplanEnv; 或 2) 仅在 PPO 算法单元测试中显式设置 "
            "DistributedPPOConfig(synthetic_env_mode=True)。"
        )

    rng = np.random.default_rng(global_step * 100 + worker_id)
    (obs_list, next_obs_list, action_list, reward_list,
     log_prob_list, done_list, total_reward) = _run_rollout_episodes(
        n_episodes, policy, config, real_env, use_synthetic, rng,
    )
    return _assemble_rollout_result(
        obs_list, next_obs_list, action_list, reward_list,
        log_prob_list, done_list, total_reward, n_episodes,
    )


def _run_rollout_episodes(
    n_episodes: int,
    policy: Any,
    config: Any,
    real_env: Any,
    use_synthetic: bool,
    rng: np.random.Generator,
) -> tuple[list, list, list, list, list, list, float]:
    """运行 n_episodes 个回合采集 rollout 数据（Extract Method，R11 质量门禁）。

    Returns:
        (obs_list, next_obs_list, action_list, reward_list, log_prob_list,
         done_list, total_reward)。
    """
    obs_list, next_obs_list = [], []
    action_list, reward_list, log_prob_list, done_list = [], [], [], []
    total_reward = 0.0
    for _ep in range(n_episodes):
        if use_synthetic:
            obs = rng.normal(0, 0.3, config.obs_dim)
        else:
            obs = real_env.reset(n_devices=config.n_devices_per_circuit)
        ep_reward = 0.0
        for step in range(20):
            action, log_prob = policy.act(obs, rng)
            if use_synthetic:
                next_obs, reward, done = synthetic_env_step(
                    obs, action, config.n_devices_per_circuit, step, rng,
                    config.action_dim, config.obs_dim,
                )
            else:
                step_out = real_env.step(action)
                # Gymnasium: (obs, reward, terminated, truncated, info)
                # Gym: (obs, reward, done, info)
                if len(step_out) == 5:
                    next_obs, reward, terminated, _trunc, _info = step_out
                    done = bool(terminated or _trunc)
                else:
                    next_obs, reward, done, _info = step_out
            obs_list.append(obs)
            next_obs_list.append(next_obs)
            action_list.append(action)
            reward_list.append(reward)
            log_prob_list.append(log_prob)
            done_list.append(done)
            ep_reward += reward
            obs = next_obs
            if done:
                break
        total_reward += ep_reward
    return (obs_list, next_obs_list, action_list, reward_list,
            log_prob_list, done_list, total_reward)


def _assemble_rollout_result(
    obs_list: list,
    next_obs_list: list,
    action_list: list,
    reward_list: list,
    log_prob_list: list,
    done_list: list,
    total_reward: float,
    n_episodes: int,
) -> dict[str, Any]:
    """组装 rollout 结果字典（Extract Method，R11 质量门禁）。"""
    return {
        "obs": np.array(obs_list, dtype=np.float64),
        "next_obs": np.array(next_obs_list, dtype=np.float64),
        "actions": np.array(action_list, dtype=np.int64),
        "rewards": np.array(reward_list, dtype=np.float64),
        "old_log_probs": np.array(log_prob_list, dtype=np.float64),
        "dones": np.array(done_list, dtype=bool),
        "mean_reward": total_reward / max(n_episodes, 1),
        "n_episodes": n_episodes,
        "n_steps": len(obs_list),
    }


__all__ = [
    "compute_gae",
    "aggregate_rollouts",
    "synthetic_env_step",
    "collect_rollout",
]
