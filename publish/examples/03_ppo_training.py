"""示例 3：PPO 训练快速入门。

演示如何用 PPO 训练布局 agent，包含：
- 创建 FloorplanEnv（注入 ExpertRewardShaper 专家知识奖励）
- 创建 PPOAgentDiscrete（离散动作 PPO）
- 运行少量 episode 训练循环
- 保存/加载 checkpoint

运行方式：
    python publish/examples/03_ppo_training.py

注意：本示例仅展示训练流程，完整训练请使用 scripts/train_2m.py。

来源:
- PPO: Schulman et al., arXiv 1707.06347
  https://arxiv.org/abs/1707.06347
- ExpertRewardShaper: ICLR'26 Expertise-Enhanced RL
  https://openreview.net/forum?id=yqvNwfxRR6
"""

from __future__ import annotations

import numpy as np

from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
from polaris.engine.netlist import load_netlist
from polaris.trainer.dataset import DatasetConfig, generate_dataset
from polaris.trainer.reward_shaping import ExpertRewardShaper
from polaris.trainer.train_loop import _infer_obs_dim, _obs_to_vector, _pad_obs


def _flatten_multidiscrete(action_space) -> int:
    """MultiDiscrete([w,h,4]) → w*h*4。"""
    return int(np.prod(action_space.nvec))


def _flat_to_multidiscrete(flat_action: int, action_space) -> np.ndarray:
    """flat_action → [gx, gy, rot]。"""
    nvec = action_space.nvec
    result = np.zeros(len(nvec), dtype=np.int64)
    remaining = flat_action
    for i in range(len(nvec) - 1, -1, -1):
        result[i] = remaining % nvec[i]
        remaining = remaining // nvec[i]
    return result


def main() -> None:
    """运行 PPO 训练快速入门示例。"""
    print("=" * 60)
    print("PoLaRIS 示例 3：PPO 训练快速入门")
    print("=" * 60)

    # 1. 生成训练数据集
    print("\n[步骤 1] 生成训练数据集")
    ds_cfg = DatasetConfig(num_netlists=5, min_devices=3, max_devices=6, seed=42)
    netlists = generate_dataset(ds_cfg)
    print(f"  生成 {len(netlists)} 个网表")

    # 2. 创建环境（注入专家奖励）
    print("\n[步骤 2] 创建 FloorplanEnv（注入 ExpertRewardShaper）")
    net0, devices0, _ = load_netlist(netlists[0])
    shaper = ExpertRewardShaper()
    env_cfg = FloorplanEnvConfig(
        canvas_w=200.0,
        canvas_h=200.0,
        grid_size=20.0,
        expert_shaper=shaper,
    )
    env0 = FloorplanEnv(net0, devices0, config=env_cfg)
    obs_dim = _infer_obs_dim(env0)
    n_actions = _flatten_multidiscrete(env0.action_space)
    print(f"  obs_dim={obs_dim}, n_actions={n_actions}")

    # 3. 创建 PPO agent
    print("\n[步骤 3] 创建 PPOAgentDiscrete")
    try:
        from polaris.trainer.ppo_torch import PPOAgentDiscrete, PPOConfig, Transition

        config = PPOConfig(
            lr=3e-4, gamma=0.99, gae_lambda=0.95, clip_eps=0.2,
            ent_coef=0.1, vf_coef=0.5, max_grad_norm=0.5,
            n_epochs=4, batch_size=32,
        )
        agent = PPOAgentDiscrete(
            obs_dim=obs_dim, n_actions=n_actions, config=config, hidden_dim=64,
        )
        print("  使用 PyTorch PPO")
    except ImportError:
        from polaris.trainer.ppo import PPOAgent, PPOConfig, Transition

        config = PPOConfig(lr=3e-4, gamma=0.99, gae_lambda=0.95)
        agent = PPOAgent(
            obs_dim=obs_dim, n_actions=n_actions, config=config, hidden_dim=64,
        )
        print("  使用 NumPy PPO")

    # 4. 训练循环（少量 episode 演示）
    print("\n[步骤 4] 训练 5 个 episode")
    rewards = []
    for ep in range(5):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        env = FloorplanEnv(net, devices, config=env_cfg)
        obs, _ = env.reset()
        ep_reward = 0.0
        for _ in range(32):
            obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim)
            flat_action, logprob, value = agent.get_action(obs_vec)
            disc_action = _flat_to_multidiscrete(flat_action, env.action_space)
            obs, reward, done, _, _ = env.step(disc_action)
            ep_reward += reward
            agent.store(Transition(obs_vec, flat_action, reward, logprob, value, done))
            if done:
                break
        rewards.append(ep_reward)
        print(f"  ep{ep}: reward={ep_reward:.3f}")

    # 5. 更新 agent
    print("\n[步骤 5] PPO 更新")
    metrics = agent.update(last_value=0.0)
    print(f"  policy_loss={metrics.get('policy_loss', 0):.4f}")
    print(f"  value_loss={metrics.get('value_loss', 0):.4f}")

    print(f"\n[总结] 平均 reward: {sum(rewards) / len(rewards):.3f}")
    print("\n示例 3 完成。完整训练请使用: python scripts/train_2m.py")


if __name__ == "__main__":
    main()
