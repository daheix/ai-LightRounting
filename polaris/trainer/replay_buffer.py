"""离线 RL 经验回放缓冲区（ChiPFormer ICML'23 方向）。

支持从离线数据学习可迁移策略，提升训练效率和跨芯片迁移能力。

方法参考：
- ChiPFormer (ICML'23): Transferable Chip Placement via Offline Decision Transformer
  Lai et al., HKU/ZJU/Huawei
  https://arxiv.org/pdf/2306.14744.pdf
- CleanRL DQN Replay Buffer: https://github.com/vwxyzjn/cleanrl
- Stable-Baselines3 ReplayBuffer: https://stable-baselines3.readthedocs.io/

核心思想：
1. 经验回放缓冲区：存储 (obs, action, reward, next_obs, done) 转移
2. 优先级采样：高 TD 误差的转移被更频繁采样
3. 离线数据加载：从已保存的专家轨迹加载训练数据
4. 跨芯片迁移：将历史芯片的布局经验迁移到新芯片
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Transition:
    """单步转移数据。

    Attributes:
        obs: 观测向量。
        action: 动作向量。
        reward: 奖励标量。
        next_obs: 下一观测向量。
        done: 是否终止。
        priority: 优先级（用于优先级回放）。
    """

    obs: np.ndarray
    action: np.ndarray
    reward: float
    next_obs: np.ndarray
    done: bool
    priority: float = 1.0


@dataclass
class ReplayBufferConfig:
    """经验回放缓冲区配置。

    Attributes:
        capacity: 缓冲区容量（转移数）。
        alpha: 优先级指数（0=均匀采样，1=完全优先级）。
        beta: 重要性采样指数（0=无校正，1=完全校正）。
        beta_increment: beta 每次采样的增量。
    """

    capacity: int = 10000
    alpha: float = 0.6
    beta: float = 0.4
    beta_increment: float = 0.001


class ReplayBuffer:
    """优先级经验回放缓冲区（ChiPFormer 方向）。

    支持优先级采样和离线数据加载，用于提升 PPO 训练效率
    和实现跨芯片迁移学习。

    来源:
    - ChiPFormer (ICML'23): https://arxiv.org/pdf/2306.14744.pdf
    - Schaul et al., 2016, Prioritized Experience Replay
      https://arxiv.org/abs/1511.05952
    """

    def __init__(self, config: ReplayBufferConfig | None = None) -> None:
        self.config = config or ReplayBufferConfig()
        self.buffer: list[Transition] = []
        self.pos = 0

    def add(self, transition: Transition) -> None:
        """添加一条转移数据。

        Args:
            transition: 单步转移数据。
        """
        if len(self.buffer) < self.config.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.pos] = transition
        self.pos = (self.pos + 1) % self.config.capacity

    def sample(self, batch_size: int) -> tuple[np.ndarray, ...]:
        """优先级采样一批转移数据。

        Args:
            batch_size: 批量大小。

        Returns:
            (obs, actions, rewards, next_obs, dones, weights, indices)。
        """
        n = len(self.buffer)
        if n == 0:
            raise RuntimeError("经验回放缓冲区为空，无法采样")

        # 计算采样概率
        priorities = np.array([t.priority for t in self.buffer])
        probs = priorities**self.config.alpha
        probs = probs / probs.sum()

        # 采样
        indices = np.random.choice(n, size=min(batch_size, n), replace=False, p=probs)
        obs = np.array([self.buffer[i].obs for i in indices])
        actions = np.array([self.buffer[i].action for i in indices])
        rewards = np.array([self.buffer[i].reward for i in indices])
        next_obs = np.array([self.buffer[i].next_obs for i in indices])
        dones = np.array([self.buffer[i].done for i in indices], dtype=np.float64)

        # 重要性采样权重
        weights = (n * probs[indices]) ** (-self.config.beta)
        weights = weights / weights.max()

        # 递增 beta
        self.config.beta = min(1.0, self.config.beta + self.config.beta_increment)

        return obs, actions, rewards, next_obs, dones, weights, indices

    def update_priorities(self, indices: np.ndarray, priorities: np.ndarray) -> None:
        """更新指定转移的优先级。"""
        for idx, pri in zip(indices, priorities):
            if 0 <= idx < len(self.buffer):
                self.buffer[idx].priority = float(pri) + 1e-6

    def __len__(self) -> int:
        return len(self.buffer)

    def save(self, path: str | Path) -> None:
        """保存缓冲区到文件（离线数据持久化）。"""
        data = []
        for t in self.buffer:
            data.append(
                {
                    "obs": t.obs.tolist(),
                    "action": t.action.tolist(),
                    "reward": t.reward,
                    "next_obs": t.next_obs.tolist(),
                    "done": t.done,
                    "priority": t.priority,
                }
            )
        Path(path).write_text(json.dumps(data), encoding="utf-8")
        logger.info("经验回放缓冲区已保存: %d 条转移 → %s", len(data), path)

    def load(self, path: str | Path) -> None:
        """从文件加载缓冲区（离线数据/专家轨迹）。"""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in raw:
            self.add(
                Transition(
                    obs=np.array(item["obs"], dtype=np.float64),
                    action=np.array(item["action"], dtype=np.float64),
                    reward=item["reward"],
                    next_obs=np.array(item["next_obs"], dtype=np.float64),
                    done=item["done"],
                )
            )
        logger.info("经验回放缓冲区已加载: %d 条转移 ← %s", len(raw), path)


class OfflineDataLoader:
    """离线数据加载器（ChiPFormer 方向）。

    从已保存的专家轨迹或历史训练数据加载转移数据，
    用于离线 RL 训练或迁移学习。

    来源:
    - ChiPFormer (ICML'23): https://arxiv.org/pdf/2306.14744.pdf
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def list_episodes(self) -> list[Path]:
        """列出所有可用的离线数据文件。"""
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.glob("episode_*.json"))

    def load_to_buffer(self, buffer: ReplayBuffer, max_episodes: int = 0) -> int:
        """加载离线数据到经验回放缓冲区。

        Args:
            buffer: 目标缓冲区。
            max_episodes: 最大加载轮次数（0=全部）。

        Returns:
            加载的转移数。
        """
        episodes = self.list_episodes()
        if max_episodes > 0:
            episodes = episodes[:max_episodes]
        total = 0
        for ep_path in episodes:
            raw = json.loads(ep_path.read_text(encoding="utf-8"))
            for item in raw:
                buffer.add(
                    Transition(
                        obs=np.array(item["obs"], dtype=np.float64),
                        action=np.array(item["action"], dtype=np.float64),
                        reward=item["reward"],
                        next_obs=np.array(item["next_obs"], dtype=np.float64),
                        done=item["done"],
                    )
                )
                total += 1
        logger.info("离线数据加载完成: %d 条转移（%d 个文件）", total, len(episodes))
        return total


__all__ = [
    "ReplayBuffer",
    "ReplayBufferConfig",
    "Transition",
    "OfflineDataLoader",
]
