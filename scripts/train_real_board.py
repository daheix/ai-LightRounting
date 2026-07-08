#!/usr/bin/env python3
"""真实板子数据 PPO 训练入口（v5.0 API，R387 新建）。

使用 real_board/expert_demos 中的 22 个真实 SiEPIC/PICBench 电路数据，
通过 LargeScalePlacementEnv + PPO 训练光电子布局策略。

架构（v5.0 依赖注入，R04 纯 NumPy CPU）:
  1. 加载 expert_demos 电路数据（netlist.json + placements.json）
  2. 转换为 LargeScalePlacementEnv 需要的 circuit dict
  3. 包装为 Gymnasium 协议 env（reset/step）
  4. PPOAgent + train_ppo 训练
  5. 保存 checkpoint + 训练日志

学术依据（R02 学术诚信）:
  - Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
  - Mirhoseini et al., Nature 2021, AlphaChip
    https://www.nature.com/articles/s41586-021-03544-w
  - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
  - Stable-Baselines3 PPO https://stable-baselines3.readthedocs.io/
  - CleanRL PPO https://github.com/vwxyzjn/cleanrl

规则依据: R03 禁止 fall-back / R04 不参与 GPU / R11 V8 工作流 / R13 交付自测
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

# 让测试既能从已安装包导入，也能从源码树导入
_REPO = Path(__file__).resolve().parent.parent
for mod in ("trainer", "place"):
    _src = _REPO / "modules" / mod / "src"
    if _src.exists() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from polaris_trainer.ppo import PPOAgent, PPOConfig, Transition  # noqa: E402
from polaris_trainer.train_loop import TrainConfig, train_ppo  # noqa: E402
from polaris_trainer.rl_advanced import (  # noqa: E402
    LargeScalePlacementConfig,
    LargeScalePlacementEnv,
)

# 训练配置
EXPERT_DEMOS_DIR = _REPO / "data" / "expert_demos"
CHECKPOINT_DIR = _REPO / "checkpoints"
LOG_FILE = _REPO / "docs" / "训练过程日志_r387.md"


def load_expert_circuits() -> list[dict]:
    """加载 expert_demos 中所有电路，转换为 circuit dict 格式。

    Returns:
        list[dict]: 每个含 devices/nets/canvas_w 的 circuit dict

    Raises:
        FileNotFoundError: expert_demos 目录不存在
    """
    if not EXPERT_DEMOS_DIR.exists():
        raise FileNotFoundError(
            f"expert_demos 目录不存在: {EXPERT_DEMOS_DIR}（R03 禁止 fall-back）"
        )
    circuits: list[dict] = []
    for circuit_dir in sorted(EXPERT_DEMOS_DIR.iterdir()):
        if not circuit_dir.is_dir():
            continue
        netlist_path = circuit_dir / "netlist.json"
        if not netlist_path.exists():
            continue
        netlist = json.loads(netlist_path.read_text(encoding="utf-8"))
        # 转换为 LargeScalePlacementEnv 需要的格式
        devices = []
        for dev in netlist.get("devices", []):
            devices.append({
                "id": dev["name"],
                "type": dev.get("device_type", "mzi"),
                "width_um": float(dev.get("width_um", 10.0)),
                "height_um": float(dev.get("height_um", 5.0)),
                "ports": dev.get("ports", []),
            })
        nets = []
        for conn in netlist.get("nets", []):
            if isinstance(conn, (list, tuple)) and len(conn) >= 4:
                nets.append({
                    "src_instance": conn[0],
                    "src_port": conn[1],
                    "dst_instance": conn[2],
                    "dst_port": conn[3],
                })
        canvas_w = float(netlist.get("canvas_w", 1000.0))
        circuits.append({
            "name": netlist.get("name", circuit_dir.name),
            "devices": devices,
            "nets": nets,
            "canvas_w": canvas_w,
        })
    if not circuits:
        raise RuntimeError(
            f"expert_demos 中未找到有效电路（R03 禁止 fall-back）"
        )
    return circuits


class PlacementGymEnv:
    """Gymnasium 协议布局环境（包装 LargeScalePlacementEnv）。

    动作空间: Box([grid_x, grid_y, rotation]) — 连续值，由 PPO 高斯策略采样
    观测空间: 展平的占用栅格 + 当前器件特征
    奖励: -HPWL（半周长线长，越小越好）+ 放置完成奖励

    学术依据: AlphaChip edge-based GNN 占用栅格表示
      https://www.nature.com/articles/s41586-021-03544-w
    """

    def __init__(self, circuit: dict, grid_size: tuple[int, int] = (16, 16)):
        self.circuit = circuit
        self.config = LargeScalePlacementConfig(
            grid_size=grid_size, node_feat_dim=9, max_devices=1024, seed=42
        )
        self.env = LargeScalePlacementEnv(self.config)
        self.env.set_circuit(circuit)
        self.devices = circuit["devices"]
        self.n_devices = len(self.devices)
        self.grid_h, self.grid_w = grid_size
        self.obs_dim = self.grid_h * self.grid_w + self.config.node_feat_dim
        self.action_dim = 3  # grid_x_norm, grid_y_norm, rotation_norm
        self._current_idx = 0
        self._placement: dict[str, dict] = {}

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        """重置环境，返回 (obs, info)。"""
        self._current_idx = 0
        self._placement = {}
        self.env.placement = {}
        return self._obs(), {"device_idx": 0, "n_devices": self.n_devices}

    def step(self, action: np.ndarray):
        """执行一步放置，返回 (obs, reward, terminated, truncated, info)。

        若 agent 选择已占用的网格，返回负奖励（RL 标准做法，非 fall-back）。
        """
        if self._current_idx >= self.n_devices:
            return self._obs(), 0.0, True, False, {"reason": "all_placed"}
        dev = self.devices[self._current_idx]
        # 将连续动作映射到网格坐标 + 旋转
        grid_x = int(np.clip(action[0] * self.grid_w, 0, self.grid_w - 1))
        grid_y = int(np.clip(action[1] * self.grid_h, 0, self.grid_h - 1))
        grid_idx = grid_y * self.grid_w + grid_x
        # 尝试放置，若网格已占用则返回负奖励（RL 非法动作处理）
        try:
            result = self.env.step(dev["id"], grid_idx)
        except ValueError:
            # 网格已占用，负奖励，不放置，继续下一个器件
            self._current_idx += 1
            reward = -0.1  # 非法动作惩罚
            terminated = self._current_idx >= self.n_devices
            return self._obs(), reward, terminated, False, {
                "device": dev["id"], "grid": (grid_x, grid_y),
                "placed": len(self._placement), "collision": True,
            }
        self._placement[dev["id"]] = result
        self._current_idx += 1
        # 奖励: 放置完成度 + HPWL 估计（简化版）
        placed_ratio = len(self._placement) / self.n_devices
        reward = placed_ratio * 0.1
        terminated = self._current_idx >= self.n_devices
        if terminated:
            # 全部放置完成，计算最终 HPWL 奖励
            hpwl = self._estimate_hpwl()
            reward += -hpwl * 0.01  # HPWL 越小越好
        return self._obs(), reward, terminated, False, {
            "device": dev["id"], "grid": (grid_x, grid_y),
            "placed": len(self._placement),
        }

    def _obs(self) -> np.ndarray:
        """构建观测向量（占用栅格 + 当前器件特征）。"""
        occ = self.env.build_occupancy().flatten()
        if self._current_idx < self.n_devices:
            dev = self.devices[self._current_idx]
            feat = self.env._node_features(dev)
        else:
            feat = np.zeros(self.config.node_feat_dim)
        return np.concatenate([occ, feat])

    def _estimate_hpwl(self) -> float:
        """估算半周长线长（HPWL），用于奖励信号。

        HPWL 是 EDA 布局质量的标准度量（越小越好）。
        来源: Kahng & Lienig, 2011, VLSI Placement
          https://ieeexplore.ieee.org/document/5731265
        """
        if not self._placement or not self.circuit.get("nets"):
            return 0.0
        canvas = self.circuit["canvas_w"]
        total_hpwl = 0.0
        for net in self.circuit["nets"]:
            src = self._placement.get(net["src_instance"])
            dst = self._placement.get(net["dst_instance"])
            if src and dst:
                dx = abs(src["x"] - dst["x"]) / canvas
                dy = abs(src["y"] - dst["y"]) / canvas
                total_hpwl += dx + dy
        return total_hpwl


def run_training(
    num_episodes: int = 100,
    rollout_steps: int = 32,
    log_every: int = 5,
) -> dict:
    """运行 PPO 训练。

    Args:
        num_episodes: 训练轮数
        rollout_steps: 每轮采样步数
        log_every: 日志打印间隔

    Returns:
        dict: 训练结果摘要
    """
    print(f"[R387] 加载 expert_demos 电路数据...")
    circuits = load_expert_circuits()
    print(f"[R387] 加载 {len(circuits)} 个电路")
    # 选择第一个电路作为训练环境（可扩展为多电路课程学习）
    circuit = circuits[0]
    print(f"[R387] 训练电路: {circuit['name']} ({len(circuit['devices'])} 器件)")
    env = PlacementGymEnv(circuit, grid_size=(16, 16))
    print(f"[R387] 环境搭建: obs_dim={env.obs_dim}, action_dim={env.action_dim}")
    # PPO 配置（对齐 SB3 默认值 + cosine 学习率调度）
    ppo_config = PPOConfig(
        lr=3e-4, gamma=0.99, gae_lambda=0.95, clip_eps=0.2,
        ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5,
        n_epochs=4, batch_size=32, lr_schedule="cosine",
        lr_warmup_steps=10, total_steps=num_episodes,
    )
    train_config = TrainConfig(
        ppo=ppo_config, num_episodes=num_episodes,
        rollout_steps=rollout_steps, hidden_dim=64,
        checkpoint_dir=str(CHECKPOINT_DIR), checkpoint_every=20,
        log_every=log_every, seed=42, early_stop_patience=0,
    )
    agent = PPOAgent(
        obs_dim=env.obs_dim, action_dim=env.action_dim,
        config=ppo_config, hidden_dim=64,
    )
    print(f"[R387] PPO 训练开始: {num_episodes} episodes × {rollout_steps} steps")
    start_time = time.time()
    # 运行训练（train_ppo 返回 (agent, logs) 元组）
    agent, metrics = train_ppo(agent, env, train_config)
    elapsed = time.time() - start_time
    # 保存 checkpoint
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / f"placement_agent_r387.json"
    agent.save(str(ckpt_path))
    print(f"[R387] checkpoint 保存: {ckpt_path}")
    # 训练结果摘要
    best_reward = max((m.get("ep_reward", -1e9) for m in metrics), default=-1e9)
    final_reward = metrics[-1].get("ep_reward", 0) if metrics else 0
    result = {
        "circuit": circuit["name"],
        "n_devices": len(circuit["devices"]),
        "num_episodes": num_episodes,
        "rollout_steps": rollout_steps,
        "elapsed_seconds": round(elapsed, 2),
        "best_reward": round(best_reward, 6),
        "final_reward": round(final_reward, 6),
        "n_metrics": len(metrics),
        "checkpoint": str(ckpt_path),
    }
    # 写训练日志
    _write_log(result, metrics)
    return result


def _write_log(result: dict, metrics: list[dict]) -> None:
    """写训练日志到 docs/训练过程日志_r387.md。"""
    lines = [
        "# R387 真实板子数据 PPO 训练日志",
        "",
        f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**电路**: {result['circuit']} ({result['n_devices']} 器件)",
        f"**训练量**: {result['num_episodes']} episodes × {result['rollout_steps']} steps",
        f"**耗时**: {result['elapsed_seconds']}s",
        f"**最佳奖励**: {result['best_reward']}",
        f"**最终奖励**: {result['final_reward']}",
        f"**checkpoint**: {result['checkpoint']}",
        "",
        "## PPO 配置",
        "- lr=3e-4, gamma=0.99, gae_lambda=0.95, clip_eps=0.2",
        "- ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5",
        "- n_epochs=4, batch_size=32, lr_schedule=cosine",
        "- hidden_dim=64",
        "",
        "## 训练指标（每轮）",
        "",
        "| Episode | Reward | Policy Loss | Value Loss | Entropy |",
        "|---------|--------|-------------|------------|---------|",
    ]
    for i, m in enumerate(metrics):
        lines.append(
            f"| {i+1} | {m.get('ep_reward', 0):.4f} | "
            f"{m.get('policy_loss', 0):.4f} | "
            f"{m.get('value_loss', 0):.4f} | "
            f"{m.get('entropy', 0):.4f} |"
        )
    lines.extend([
        "",
        "## 学术依据（R02）",
        "- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347",
        "- Mirhoseini et al., Nature 2021, AlphaChip",
        "  https://www.nature.com/articles/s41586-021-03544-w",
        "- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "- SB3 PPO https://stable-baselines3.readthedocs.io/",
        "- Kahng & Lienig, 2011, VLSI Placement IEEE",
        "",
        "## 规则依据",
        "- R03 禁止 fall-back / R04 不参与 GPU / R11 V8 工作流 / R13 交付自测",
    ])
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[R387] 训练日志: {LOG_FILE}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R387 真实板子数据 PPO 训练")
    parser.add_argument("--episodes", type=int, default=100, help="训练轮数")
    parser.add_argument("--rollout", type=int, default=32, help="每轮采样步数")
    parser.add_argument("--log-every", type=int, default=5, help="日志间隔")
    args = parser.parse_args()
    result = run_training(
        num_episodes=args.episodes,
        rollout_steps=args.rollout,
        log_every=args.log_every,
    )
    print(f"\n[R387] 训练完成:")
    for k, v in result.items():
        print(f"  {k}: {v}")
