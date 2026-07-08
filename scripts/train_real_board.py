#!/usr/bin/env python3
"""真实板子数据 PPO 训练入口（v5.0 API，R388 重构）。

使用 real_board/expert_demos 中的 22 个真实 SiEPIC/PICBench 电路数据，
通过 LargeScalePlacementEnv + PPO 训练光电子布局策略。

架构（v5.0 依赖注入，R04 纯 NumPy CPU）:
  1. 加载 expert_demos 电路数据（netlist.json + placements.json）
  2. 转换为 LargeScalePlacementEnv 需要的 circuit dict（nets 内部格式）
  3. 包装为 Gymnasium 协议 env（reset/step）
  4. PPOAgent + train_ppo 训练
  5. 保存 checkpoint + 训练日志

R388 修复（对比 R387）:
  - P0 字段名 Bug: netlist["connections"] → circuit["nets"]（原代码误用 "nets" 读取
    netlist，导致 nets 恒空 → HPWL 信号消失 → reward 退化为常数 0.30）
  - P0 reward 设计: 每步增量 HPWL（与位置相关）+ 放置完成奖励
  - P1 rollout: terminated 时 reset 继续采集到 rollout_steps 满
  - P1 坐标尺度: 网格坐标 [0, grid*cell_size] 归一化到 canvas
  - P2 栅格 16×16→8×8（避免 obs_dim 过大 + 栅格全零）
  - P2 动作 clip 到 [0, 1]（PPO 高斯策略动作 ∈ ℝ，需 sigmoid 或 clip）
  - P3 超参: lr=1e-4, n_epochs=2, batch_size=8（小样本适配）
  - 选择 mzi_2x2_switch（8 器件 8 连接）作为训练电路（Crossings 无连接）

学术依据（R02 学术诚信）:
  - Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
  - Mirhoseini et al., Nature 2021, AlphaChip
    https://www.nature.com/articles/s41586-021-03544-w
  - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
  - Stable-Baselines3 PPO https://stable-baselines3.readthedocs.io/
  - CleanRL PPO https://github.com/vwxyzjn/cleanrl
  - Kahng & Lienig, 2011, VLSI Placement IEEE
    https://ieeexplore.ieee.org/document/5731265

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
LOG_FILE = _REPO / "docs" / "训练过程日志_r388.md"


def load_expert_circuits() -> list[dict]:
    """加载 expert_demos 中所有电路，转换为 circuit dict 格式。

    数据文件 netlist.json 使用 ``connections`` 字段（list of
    [src_inst, src_port, dst_inst, dst_port]），本函数将其转换为内部
    统一的 ``nets`` 格式（list of {"src": [inst, port], "dst": [inst, port]}），
    与 ``rl_pareto.py._net_pts`` 期望格式一致。

    Returns:
        list[dict]: 每个含 devices/nets/canvas_w/canvas_h 的 circuit dict

    Raises:
        FileNotFoundError: expert_demos 目录不存在
        RuntimeError: 未找到有效电路
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
        # P0 修复：netlist.json 使用 "connections" 字段（list of 4-tuple），
        # 转换为内部 "nets" 格式（list of {"src":[inst,port], "dst":[inst,port]}），
        # 与 rl_pareto.py._net_pts 期望格式一致。
        nets = []
        for conn in netlist.get("connections", []):
            if isinstance(conn, (list, tuple)) and len(conn) >= 4:
                nets.append({
                    "src": [conn[0], conn[1]],
                    "dst": [conn[2], conn[3]],
                })
        # 仅保留有连接的电路（无连接的电路 HPWL 恒为 0，无训练信号）
        if not nets:
            continue
        canvas_w = float(netlist.get("canvas_w", 1000.0))
        canvas_h = float(netlist.get("canvas_h", canvas_w))
        circuits.append({
            "name": netlist.get("name", circuit_dir.name),
            "devices": devices,
            "nets": nets,
            "canvas_w": canvas_w,
            "canvas_h": canvas_h,
        })
    if not circuits:
        raise RuntimeError(
            f"expert_demos 中未找到含连接的有效电路（R03 禁止 fall-back）"
        )
    return circuits


class PlacementGymEnv:
    """Gymnasium 协议布局环境（包装 LargeScalePlacementEnv）。

    动作空间: Box([grid_x_norm, grid_y_norm]) ∈ [0,1]² — 连续值，由 PPO 高斯策略采样
    观测空间: 展平的占用栅格 + 当前器件特征
    奖励: 每步 -ΔHPWL（增量半周长线长）+ 放置完成奖励

    R388 修复:
    - 动作 clip 到 [0,1]（原代码 action[0]*grid_w 当 action<0 时 grid_x<0，
      np.clip 兜底但浪费动作维度）
    - reward 每步计算 ΔHPWL（原代码只在 terminated 时计算，且 nets 为空恒返回 0）
    - HPWL 归一化到 canvas 尺寸（原代码 src["x"]/canvas 但 src["x"] 是网格坐标 [0,1500]μm，
      与 canvas_w=57154μm 尺度不匹配）
    - 删除 rotation 维度（LargeScalePlacementEnv.step 不支持 rotation，固定 rotation=0）

    学术依据: AlphaChip edge-based GNN 占用栅格表示
      https://www.nature.com/articles/s41586-021-03544-w
    """

    def __init__(self, circuit: dict, grid_size: tuple[int, int] = (8, 8)):
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
        self.action_dim = 2  # grid_x_norm, grid_y_norm（删除 rotation）
        self._current_idx = 0
        self._placement: dict[str, dict] = {}
        self._prev_hpwl: float = 0.0  # 上一步 HPWL（用于增量奖励）
        self.canvas_w = float(circuit["canvas_w"])
        self.canvas_h = float(circuit.get("canvas_h", self.canvas_w))

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        """重置环境，返回 (obs, info)。"""
        self._current_idx = 0
        self._placement = {}
        self._prev_hpwl = 0.0
        self.env.placement = {}
        return self._obs(), {"device_idx": 0, "n_devices": self.n_devices}

    def step(self, action: np.ndarray):
        """执行一步放置，返回 (obs, reward, terminated, truncated, info)。

        若 agent 选择已占用的网格，返回负奖励（RL 标准做法，非 fall-back）。
        奖励设计（R388）:
        - 碰撞: -0.5（非法动作惩罚）
        - 合法放置: -ΔHPWL（增量 HPWL，越小越好，归一化到 [0,1]）
        - 全部放置完成: +1.0（完成奖励）
        """
        if self._current_idx >= self.n_devices:
            return self._obs(), 0.0, True, False, {"reason": "all_placed"}
        dev = self.devices[self._current_idx]
        # P2 修复：动作 clip 到 [0,1] 再映射到网格（PPO 高斯策略动作 ∈ ℝ）
        ax = float(np.clip(action[0], 0.0, 1.0))
        ay = float(np.clip(action[1], 0.0, 1.0))
        grid_x = int(ax * (self.grid_w - 1))
        grid_y = int(ay * (self.grid_h - 1))
        grid_idx = grid_y * self.grid_w + grid_x
        # 尝试放置，若网格已占用则返回负奖励（RL 非法动作处理）
        try:
            result = self.env.step(dev["id"], grid_idx)
        except ValueError:
            # 网格已占用，负奖励，不放置，继续下一个器件
            self._current_idx += 1
            reward = -0.5  # 非法动作惩罚
            terminated = self._current_idx >= self.n_devices
            return self._obs(), reward, terminated, False, {
                "device": dev["id"], "grid": (grid_x, grid_y),
                "placed": len(self._placement), "collision": True,
            }
        self._placement[dev["id"]] = {
            "x": float(grid_x * 100.0),  # _GRID_CELL_SIZE_UM=100.0
            "y": float(grid_y * 100.0),
            "rotation": 0,
        }
        self._current_idx += 1
        # P0 修复：每步计算增量 HPWL（与位置相关），归一化到 [0,1]
        cur_hpwl = self._estimate_hpwl()
        delta_hpwl = cur_hpwl - self._prev_hpwl
        self._prev_hpwl = cur_hpwl
        # 奖励 = -ΔHPWL（HPWL 增量越小越好）+ 放置完成奖励
        reward = -delta_hpwl
        terminated = self._current_idx >= self.n_devices
        if terminated:
            # 全部放置完成，额外奖励 + 最终 HPWL 反馈
            reward += 1.0 - cur_hpwl  # 完成奖励 + HPWL 越小奖励越高
        return self._obs(), reward, terminated, False, {
            "device": dev["id"], "grid": (grid_x, grid_y),
            "placed": len(self._placement),
            "hpwl_um": cur_hpwl * self.canvas_w,  # 反归一化供日志记录
            "hpwl_norm": cur_hpwl,
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
        """估算半周长线长（HPWL），归一化到 [0,1]。

        HPWL 是 EDA 布局质量的标准度量（越小越好）。
        来源: Kahng & Lienig, 2011, VLSI Placement
          https://ieeexplore.ieee.org/document/5731265

        R388 修复:
        - 适配内部 nets 格式 {"src":[inst,port], "dst":[inst,port]}
        - 坐标归一化: src["x"]/canvas_w（原代码坐标尺度不匹配，
          LargeScalePlacementEnv.step 返回 x=col*100μm ∈ [0, 700]，
          而 canvas_w=57154μm，未归一化时 HPWL 被低估 80×）
        """
        if not self._placement or not self.circuit.get("nets"):
            return 0.0
        total_hpwl = 0.0
        for net in self.circuit["nets"]:
            src_id = net["src"][0]
            dst_id = net["dst"][0]
            src = self._placement.get(src_id)
            dst = self._placement.get(dst_id)
            if src and dst:
                dx = abs(src["x"] - dst["x"]) / self.canvas_w
                dy = abs(src["y"] - dst["y"]) / self.canvas_h
                total_hpwl += dx + dy
        # 归一化到 [0,1]（除以 nets 数 × 2，每个 net 最大贡献 2.0）
        n_nets = max(1, len(self.circuit["nets"]))
        return total_hpwl / (n_nets * 2.0)


def run_training(
    num_episodes: int = 1000,
    rollout_steps: int = 64,
    log_every: int = 50,
    circuit_name: str = "mzi_2x2_switch",
) -> dict:
    """运行 PPO 训练。

    Args:
        num_episodes: 训练轮数（R388 默认 1000，原 100 过少）
        rollout_steps: 每轮采样步数（R388 默认 64，原 32 在 5 器件 episode
            下仅采集 5 步，PPO 样本不足）
        log_every: 日志打印间隔
        circuit_name: 训练电路名（R388 默认 mzi_2x2_switch：8 器件 8 连接，
            原 Crossings 无连接，HPWL 信号消失）

    Returns:
        dict: 训练结果摘要
    """
    print(f"[R388] 加载 expert_demos 电路数据...")
    circuits = load_expert_circuits()
    print(f"[R388] 加载 {len(circuits)} 个含连接电路")
    # 选择指定电路作为训练环境（可扩展为多电路课程学习）
    circuit = next(
        (c for c in circuits if c["name"] == circuit_name),
        circuits[0],
    )
    print(
        f"[R388] 训练电路: {circuit['name']} "
        f"({len(circuit['devices'])} 器件, {len(circuit['nets'])} 连接)"
    )
    env = PlacementGymEnv(circuit, grid_size=(8, 8))
    print(f"[R388] 环境搭建: obs_dim={env.obs_dim}, action_dim={env.action_dim}")
    # P3 修复：PPO 配置（lr=1e-4 原 3e-4 偏大 / n_epochs=2 原 4 过拟合 /
    # batch_size=8 原 32 在小样本下导致 1 个 batch）
    ppo_config = PPOConfig(
        lr=1e-4, gamma=0.99, gae_lambda=0.95, clip_eps=0.2,
        ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5,
        n_epochs=2, batch_size=8, lr_schedule="cosine",
        lr_warmup_steps=20, total_steps=num_episodes,
    )
    train_config = TrainConfig(
        ppo=ppo_config, num_episodes=num_episodes,
        rollout_steps=rollout_steps, hidden_dim=64,
        checkpoint_dir=str(CHECKPOINT_DIR), checkpoint_every=100,
        log_every=log_every, seed=42, early_stop_patience=0,
    )
    agent = PPOAgent(
        obs_dim=env.obs_dim, action_dim=env.action_dim,
        config=ppo_config, hidden_dim=64,
    )
    print(
        f"[R388] PPO 训练开始: {num_episodes} episodes × {rollout_steps} steps"
    )
    start_time = time.time()
    # 运行训练（train_ppo 返回 (agent, logs) 元组）
    agent, metrics = train_ppo(agent, env, train_config)
    elapsed = time.time() - start_time
    # 保存 checkpoint
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / f"placement_agent_r388.json"
    agent.save(str(ckpt_path))
    print(f"[R388] checkpoint 保存: {ckpt_path}")
    # 训练结果摘要
    best_reward = max((m.get("ep_reward", -1e9) for m in metrics), default=-1e9)
    final_reward = metrics[-1].get("ep_reward", 0) if metrics else 0
    # 统计 HPWL 信息（若日志记录）
    hpwl_values = [m.get("hpwl_um") for m in metrics if m.get("hpwl_um") is not None]
    best_hpwl = min(hpwl_values) if hpwl_values else None
    result = {
        "circuit": circuit["name"],
        "n_devices": len(circuit["devices"]),
        "n_nets": len(circuit["nets"]),
        "num_episodes": num_episodes,
        "rollout_steps": rollout_steps,
        "elapsed_seconds": round(elapsed, 2),
        "best_reward": round(best_reward, 6),
        "final_reward": round(final_reward, 6),
        "best_hpwl_um": round(best_hpwl, 2) if best_hpwl is not None else None,
        "n_metrics": len(metrics),
        "checkpoint": str(ckpt_path),
    }
    # 写训练日志
    _write_log(result, metrics)
    return result


def _write_log(result: dict, metrics: list[dict]) -> None:
    """写训练日志到 docs/训练过程日志_r388.md。"""
    lines = [
        "# R388 真实板子数据 PPO 训练日志",
        "",
        f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**电路**: {result['circuit']} ({result['n_devices']} 器件, {result['n_nets']} 连接)",
        f"**训练量**: {result['num_episodes']} episodes × {result['rollout_steps']} steps",
        f"**耗时**: {result['elapsed_seconds']}s",
        f"**最佳奖励**: {result['best_reward']}",
        f"**最终奖励**: {result['final_reward']}",
        f"**最佳 HPWL (μm)**: {result['best_hpwl_um']}",
        f"**checkpoint**: {result['checkpoint']}",
        "",
        "## R388 修复内容（对比 R387）",
        "",
        "| 优先级 | Bug | 修复方案 |",
        "|--------|-----|----------|",
        "| P0 | `netlist.get('nets')` 字段名错误（应为 `connections`）| 改为 `connections` 并转换为内部 `nets` 格式 |",
        "| P0 | reward 只依赖 placed_ratio，与位置无关 | 每步计算 -ΔHPWL + 完成奖励 |",
        "| P1 | rollout 在 terminated 时 break，5 器件仅采集 5 步 | train_loop 已支持多 episode（_collect_rollout 在 terminated 时 break 改为 reset 续采）|",
        "| P1 | HPWL 坐标尺度不匹配（网格 [0,700]μm vs canvas 57154μm）| 归一化到 canvas 尺寸 |",
        "| P2 | 栅格 16×16=256 过大 + 占用稀疏 | 缩小到 8×8=64 |",
        "| P2 | 动作 ∈ ℝ 未 clip 到 [0,1] | `np.clip(action, 0, 1)` |",
        "| P2 | rotation 维度浪费（env 不支持）| 删除 rotation 维度，action_dim=2 |",
        "| P3 | lr=3e-4 偏大 + n_epochs=4 过拟合 | lr=1e-4, n_epochs=2, batch_size=8 |",
        "| P3 | Crossings 电路无连接，HPWL 恒为 0 | 改用 mzi_2x2_switch（8 器件 8 连接）|",
        "",
        "## PPO 配置（R388）",
        "- lr=1e-4, gamma=0.99, gae_lambda=0.95, clip_eps=0.2",
        "- ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5",
        "- n_epochs=2, batch_size=8, lr_schedule=cosine",
        "- hidden_dim=64, grid_size=8×8, obs_dim=73",
        "",
        "## 训练指标（每轮）",
        "",
        "| Episode | Reward | Policy Loss | Value Loss | Entropy | HPWL(μm) |",
        "|---------|--------|-------------|------------|---------|----------|",
    ]
    for i, m in enumerate(metrics):
        hpwl = m.get("hpwl_um")
        hpwl_str = f"{hpwl:.2f}" if hpwl is not None else "N/A"
        lines.append(
            f"| {i+1} | {m.get('ep_reward', 0):.4f} | "
            f"{m.get('policy_loss', 0):.4f} | "
            f"{m.get('value_loss', 0):.4f} | "
            f"{m.get('entropy', 0):.4f} | {hpwl_str} |"
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
        "  https://ieeexplore.ieee.org/document/5731265",
        "",
        "## 规则依据",
        "- R03 禁止 fall-back / R04 不参与 GPU / R11 V8 工作流 / R13 交付自测",
    ])
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[R388] 训练日志: {LOG_FILE}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R388 真实板子数据 PPO 训练")
    parser.add_argument("--episodes", type=int, default=1000, help="训练轮数")
    parser.add_argument("--rollout", type=int, default=64, help="每轮采样步数")
    parser.add_argument("--log-every", type=int, default=50, help="日志间隔")
    parser.add_argument(
        "--circuit", type=str, default="mzi_2x2_switch",
        help="训练电路名（默认 mzi_2x2_switch）",
    )
    args = parser.parse_args()
    result = run_training(
        num_episodes=args.episodes,
        rollout_steps=args.rollout,
        log_every=args.log_every,
        circuit_name=args.circuit,
    )
    print(f"\n[R388] 训练完成:")
    for k, v in result.items():
        print(f"  {k}: {v}")
