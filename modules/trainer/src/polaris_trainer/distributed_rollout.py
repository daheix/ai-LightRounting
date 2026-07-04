"""R35 CPU 多进程并行 rollout（polaris-trainer）。

实现 PPO on-policy 多 env 并行采样框架，基于 Python 标准库
``concurrent.futures.ProcessPoolExecutor``（CPU 单机多进程），无需 Ray/Horovod
等重型分布式框架。每个 worker 进程独立运行一个 env 实例，采集
``(state, action, reward, next_state, done)`` 轨迹，主进程聚合为统一 batch 列表。

对标 Stable-Baselines3 ``SubprocVecEnv`` + ``PPO(n_envs=N)`` 的多环境并行采样
范式，以及 Google Circuit Training 的多 env rollout 设计。

==================================================================
Input（输入）
==================================================================
- ``agent``：策略智能体，须实现 ``get_action(obs) -> (action, logprob, value)``
  且可 pickle（``PPOAgent`` 为纯 NumPy 实现，天然满足）。rollout 期间 agent
  只读不更新（on-policy 单次采样），各 worker 共享同一份策略快照。
- ``env_configs``：``list[dict]``，每个 dict 是可 pickle 的 env 构造参数，
  须含 ``type`` 字段指向已注册的 env 工厂（内置 ``"mock"`` 用于测试/演示）。
- ``n_steps``：每个 worker 采样的轨迹步数。
- ``n_workers``：worker 进程数，默认 ``None`` → ``min(cpu_count, len(env_configs))``。

==================================================================
Process（处理）
==================================================================
1. 主进程校验输入（R03：非法即 raise）。
2. 用 ``ProcessPoolExecutor(initializer=_worker_init, initargs=(agent,))`` 启动
   worker 池：每个 worker 启动时接收一次 agent（仅 pickle 一次，避免每任务重复
   序列化大权重；fork 模式下 COW 共享内存）。
3. 主进程为每个 env_config 提交一个 ``_rollout_worker`` 任务（顶层函数，可 pickle）。
4. 每个 worker：构造 env → reset → 循环 n_steps 采样 → 终止则 reset →
   打包为 ``RolloutBatch`` 返回。
5. 主进程用 ``concurrent.futures.as_completed`` 收集结果，保持提交顺序。
6. worker 内异常通过 ``future.result()`` 重新抛出（R03）；worker 进程崩溃
   → ``BrokenProcessPool`` → 包装为 ``RuntimeError`` raise（R03，不静默跳过）。

==================================================================
Output（输出）
==================================================================
- ``list[RolloutBatch]``：每个 worker 一个 batch，含 ``states/actions/rewards/
  next_states/dones`` numpy 数组与 ``worker_id``。

==================================================================
R04 战略（不可撤销）
==================================================================
🚫不参与 GPU 多卡分布式：禁止 Ray/Horovod/torch.distributed/CuPy/CUDA/ROCm。
本模块仅用 ``concurrent.futures.ProcessPoolExecutor``（CPU 单机多进程）。
GPU 多卡分布式功能点不计入覆盖率。

==================================================================
R03 禁止 fall-back
==================================================================
- 输入校验失败 → ``raise ValueError``
- worker 内异常 → ``future.result()`` 重新抛出
- worker 进程崩溃 → ``raise RuntimeError``
- 禁止 ``except`` 块静默空语句 / ``return None`` / 跳过崩溃 worker

==================================================================
学术依据（R02 学术诚信，≥5 个文献 URL）
==================================================================
1. Schulman et al., 2017, PPO（on-policy 多 env 采样原始论文）
   https://arxiv.org/abs/1707.06347
2. Mirhoseini et al., Nature 2021, AlphaChip（预训练-微调范式起源）
   https://www.nature.com/articles/s41586-021-03544-w
3. Google Circuit Training（AlphaChip 开源实现，多 env rollout）
   https://github.com/google-research/circuit_training
4. Python concurrent.futures 官方文档（ProcessPoolExecutor / initializer）
   https://docs.python.org/3/library/concurrent.futures.html
5. Stable-Baselines3 SubprocVecEnv + PPO Multiprocessing（多 env 并行采样范式）
   https://stable-baselines3.readthedocs.io/en/master/guide/examples.html
6. Mayor et al., ICML 2025, On-Policy Parallelized Data Collection
   （实证：scaling parallel envs 优于增加 rollout length）
   https://arxiv.org/abs/2506.03404
7. CleanRL PPO 单文件实现（多 env 采样参考）
   https://github.com/vwxyzjn/cleanrl

来源: R35 路标任务（AlphaChip 预训练 + CPU 分布式训练），新建模块。
"""

from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

# R04 战略声明：🚫不参与 GPU 多卡分布式，纯 CPU 单机多进程
GPU_DISABLED_R04: bool = True

# CPU 多进程上下文：用 fork start method。
# 理由：PPOAgent 内部 _nn.Tensor._backward 为 lambda（autograd 闭包），不可 pickle。
# fork 模式下 worker 通过 fork 继承父进程内存，initializer 的 initargs=(agent,)
# 无需 pickle（forkserver/spawn 模式下会 pickle 失败）。fork 是 CPU 单机多进程的
# 经典模式，R04 合规（纯 CPU，无 GPU 多卡）。
# 来源: Python multiprocessing start methods
#   https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
_MP_CONTEXT = multiprocessing.get_context("fork")

# worker 进程全局 agent（由 _worker_init 注入，避免每任务 pickle 大权重）
_WORKER_AGENT: Any = None


# ===========================================================================
# RolloutBatch：单 worker 采集的轨迹批次（可 pickle dataclass）
# ===========================================================================


@dataclass
class RolloutBatch:
    """单个 worker 采集的 rollout 批次。

    所有数组第一维 = 轨迹步数 T（= n_steps，除非提前 done 不补齐）。
    dataclass + numpy 数组，天然可 pickle（ProcessPoolExecutor 返回值要求）。

    Attributes:
        states: 状态数组 [T, obs_dim]。
        actions: 动作数组 [T, action_dim]。
        rewards: 奖励数组 [T]。
        next_states: 下一状态数组 [T, obs_dim]。
        dones: 终止标志数组 [T]（bool，0/1）。
        worker_id: 采集该 batch 的 worker 索引（用于调试与顺序保持）。
    """

    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    next_states: np.ndarray
    dones: np.ndarray
    worker_id: int = 0

    def __len__(self) -> int:
        """返回轨迹步数 T。"""
        return int(self.states.shape[0])

    def total_reward(self) -> float:
        """返回累计奖励 Σ rewards。"""
        return float(np.sum(self.rewards))

    def total_steps(self) -> int:
        """返回有效步数（= T）。"""
        return len(self)


# ===========================================================================
# 内置 Mock env（测试/演示用，遵循 Gymnasium 协议，纯 NumPy 可 pickle）
# ===========================================================================


class _MockRolloutEnv:
    """内置 mock env（遵循 Gymnasium 协议，纯 NumPy，可 pickle）。

    供测试与演示使用，不依赖 gymnasium。``reset→(obs,{})``，``step→5-tuple``。
    每个 episode 固定 ``max_steps`` 步后 terminated=True，自动 reset 由 worker 处理。

    学术依据: Gymnasium API 规范 https://gymnasium.farama.org/
    """

    def __init__(
        self,
        obs_dim: int = 8,
        action_dim: int = 2,
        max_steps: int = 5,
        seed: int = 0,
    ) -> None:
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.max_steps = int(max_steps)
        self._rng = np.random.default_rng(int(seed))
        self._step = 0

    def reset(self):
        """重置环境，返回 (obs, info)。"""
        self._step = 0
        obs = self._rng.standard_normal(self.obs_dim)
        return obs, {}

    def step(self, action):
        """执行动作，返回 (obs, reward, terminated, truncated, info)。"""
        self._step += 1
        obs = self._rng.standard_normal(self.obs_dim)
        reward = float(self._rng.standard_normal())
        terminated = self._step >= self.max_steps
        return obs, reward, terminated, False, {}


# ===========================================================================
# env 工厂注册表（fork 模式下子进程继承；spawn 模式重新执行模块级注册）
# ===========================================================================

ENV_FACTORIES: dict[str, Callable[[dict], Any]] = {}


def register_env_factory(name: str, factory: Callable[[dict], Any]) -> None:
    """注册 env 工厂（名称非法或重复即 raise，R03）。

    Args:
        name: 工厂名（如 ``"mock"``）。
        factory: ``dict → env`` 的可调用对象（须可 pickle 或在 fork 模式下使用）。

    Raises:
        ValueError: name 为空或已注册（R03 无 fall-back）。
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"工厂名非法: {name!r}（R03 无 fall-back）")
    if name in ENV_FACTORIES:
        raise ValueError(f"工厂 {name!r} 已注册（R03 无 fall-back，禁止覆盖）")
    ENV_FACTORIES[name] = factory


def _mock_env_factory(cfg: dict) -> _MockRolloutEnv:
    """mock env 工厂（从 cfg 构造 _MockRolloutEnv）。"""
    return _MockRolloutEnv(
        obs_dim=int(cfg.get("obs_dim", 8)),
        action_dim=int(cfg.get("action_dim", 2)),
        max_steps=int(cfg.get("max_steps", 5)),
        seed=int(cfg.get("seed", 0)),
    )


# 模块级注册 mock 工厂（fork 继承 / spawn 重新执行）
register_env_factory("mock", _mock_env_factory)


def _make_env(env_config: dict) -> Any:
    """根据 env_config['type'] 查找工厂构造 env（类型缺失即 raise，R03）。

    Args:
        env_config: env 构造参数 dict，须含 ``type`` 字段。

    Returns:
        env 实例（遵循 Gymnasium 协议）。

    Raises:
        ValueError: env_config 非 dict / 缺 type / type 未注册（R03 无 fall-back）。
    """
    if not isinstance(env_config, dict):
        raise ValueError(
            f"env_config 须为 dict，得到 {type(env_config).__name__}（R03 无 fall-back）"
        )
    env_type = env_config.get("type")
    if not env_type:
        raise ValueError("env_config 缺 'type' 字段（R03 无 fall-back）")
    if env_type not in ENV_FACTORIES:
        raise ValueError(
            f"env 工厂 {env_type!r} 未注册，可选 {list(ENV_FACTORIES)}（R03 无 fall-back）"
        )
    return ENV_FACTORIES[env_type](env_config)


# ===========================================================================
# worker 进程初始化与顶层 worker 函数（ProcessPoolExecutor pickle 要求）
# ===========================================================================


def _worker_init(agent: Any) -> None:
    """worker 进程初始化：注入 agent 到全局变量（避免每任务 pickle 大权重）。

    每个 worker 启动时由 ``ProcessPoolExecutor(initializer=_worker_init, ...)``
    调用一次，agent 仅 pickle 一次传给该 worker。fork 模式下 COW 共享内存，
    spawn 模式下每个 worker 独立持有 agent 副本。

    Args:
        agent: 策略智能体（须可 pickle，如 ``PPOAgent``）。
    """
    global _WORKER_AGENT
    _WORKER_AGENT = agent


def _obs_to_vec(obs: Any) -> np.ndarray:
    """将 Gymnasium dict/array 观测展平为 float64 向量（worker 自洽，不依赖外部 import）。

    与 ``train_loop.obs_to_vector`` 同源逻辑，复制以避免 worker 子进程 import 链
    依赖（健壮性优先，docstring 标注同源）。
    """
    if isinstance(obs, dict):
        parts = [np.asarray(v, dtype=np.float64).flatten() for v in obs.values()]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float64)
    return np.asarray(obs, dtype=np.float64).flatten()


def _run_single_env_rollout(
    agent: Any,
    env: Any,
    n_steps: int,
) -> tuple[list, list, list, list, list]:
    """在单个 env 上执行 n_steps rollout（提取降低 _rollout_worker 圈复杂度）。

    Args:
        agent: 策略智能体（须有 ``get_action(obs) -> (action, logprob, value)``）。
        env: Gymnasium 协议 env。
        n_steps: 采样步数。

    Returns:
        (states, actions, rewards, next_states, dones) 五个列表。

    Raises:
        AttributeError: agent 缺 get_action（R03 无 fall-back）。
    """
    if not hasattr(agent, "get_action"):
        raise AttributeError(
            "agent 须实现 get_action(obs) -> (action, logprob, value)（R03 无 fall-back）"
        )
    states: list = []
    actions: list = []
    rewards: list = []
    next_states: list = []
    dones: list = []
    obs, _info = env.reset()
    obs_vec = _obs_to_vec(obs)
    for _ in range(n_steps):
        action, _logprob, _value = agent.get_action(obs_vec)
        next_obs, reward, terminated, truncated, _info = env.step(action)
        next_vec = _obs_to_vec(next_obs)
        states.append(obs_vec)
        actions.append(np.asarray(action, dtype=np.float64).flatten())
        rewards.append(float(reward))
        next_states.append(next_vec)
        dones.append(bool(terminated or truncated))
        if terminated or truncated:
            obs, _info = env.reset()
            obs_vec = _obs_to_vec(obs)
        else:
            obs_vec = next_vec
    return states, actions, rewards, next_states, dones


def _rollout_worker(env_config: dict, n_steps: int, seed: int, worker_id: int) -> RolloutBatch:
    """顶层 worker 函数（ProcessPoolExecutor pickle 要求，不可为 lambda/闭包）。

    在 worker 进程内：从全局 ``_WORKER_AGENT`` 取 agent → 构造 env →
    执行 n_steps rollout → 打包为 ``RolloutBatch`` 返回。

    Args:
        env_config: env 构造参数 dict（可 pickle）。
        n_steps: 采样步数。
        seed: worker 随机种子（用于 env 多样性）。
        worker_id: worker 索引（写入 batch.worker_id）。

    Returns:
        该 worker 采集的 ``RolloutBatch``。

    Raises:
        RuntimeError: worker 未初始化 agent（R03 无 fall-back）。
        ValueError: env_config 非法（由 _make_env 传播，R03）。
    """
    agent = _WORKER_AGENT
    if agent is None:
        raise RuntimeError(
            f"worker {worker_id} 未初始化 agent（_WORKER_AGENT 为 None，R03 无 fall-back）"
        )
    np.random.seed(int(seed) % (2**32))
    env = _make_env(env_config)
    states, actions, rewards, next_states, dones = _run_single_env_rollout(
        agent, env, n_steps
    )
    return RolloutBatch(
        states=np.asarray(states, dtype=np.float64),
        actions=np.asarray(actions, dtype=np.float64),
        rewards=np.asarray(rewards, dtype=np.float64),
        next_states=np.asarray(next_states, dtype=np.float64),
        dones=np.asarray(dones, dtype=bool),
        worker_id=worker_id,
    )


# ===========================================================================
# ParallelRolloutCollector：CPU 多进程并行 rollout 收集器
# ===========================================================================


class ParallelRolloutCollector:
    """CPU 多进程并行 rollout 收集器（R04: 纯 CPU，基于 ProcessPoolExecutor）。

    对标 Stable-Baselines3 ``SubprocVecEnv``：每个 worker 进程独立运行一个 env
    实例，并行采集 on-policy 轨迹，主进程聚合。适用于 PPO on-policy 多 env 采样
    （Schulman 2017 arXiv:1707.06347）。

    *创新*：CPU 单机多进程 rollout 框架，零外部依赖（纯标准库 concurrent.futures）。
    - 底层逻辑：PPO on-policy 天然支持多 env 采样（SB3 SubprocVecEnv + n_envs），
      每个 env 独立采集 n_steps 轨迹，聚合后 batch_size = n_envs × n_steps。
      Mayor et al. ICML 2025（arXiv:2506.03404）实证 scaling parallel envs 优于
      增加 rollout length。本框架用 ProcessPoolExecutor 实现等价语义，无需 Ray。
    - initializer 注入 agent：每个 worker 仅 pickle 一次 agent 权重，避免每任务
      重复序列化大权重（fork 模式下 COW 零拷贝）。
    - R03 严格错误传播：worker 异常经 future.result() 重新抛出，进程崩溃
      （BrokenProcessPool）包装为 RuntimeError，绝不静默跳过。

    学术依据: PPO https://arxiv.org/abs/1707.06347 / SB3 SubprocVecEnv
    https://stable-baselines3.readthedocs.io/en/master/guide/examples.html /
    concurrent.futures https://docs.python.org/3/library/concurrent.futures.html /
    Mayor 2025 https://arxiv.org/abs/2506.03404

    Attributes:
        n_workers: worker 进程数（None → collect 时按 min(cpu, len(configs)) 定）。
    """

    def __init__(self, n_workers: int | None = None) -> None:
        """初始化收集器。

        Args:
            n_workers: worker 进程数。None 表示 collect 时自动取
                ``min(cpu_count, len(env_configs))``。

        Raises:
            ValueError: n_workers <= 0（R03 无 fall-back）。
        """
        if n_workers is not None and n_workers <= 0:
            raise ValueError(
                f"n_workers 须 > 0 或 None，得到 {n_workers}（R03 无 fall-back）"
            )
        self.n_workers = n_workers

    def _resolve_n_workers(self, n_envs: int) -> int:
        """解析实际 worker 数（默认 = min(cpu_count, n_envs)，避免空进程）。

        Args:
            n_envs: env 配置数。

        Returns:
            实际 worker 数。

        Raises:
            ValueError: n_envs <= 0（R03）。
        """
        if n_envs <= 0:
            raise ValueError(f"n_envs 须 > 0，得到 {n_envs}（R03 无 fall-back）")
        cpu = os.cpu_count() or 1
        default = min(cpu, n_envs)
        if self.n_workers is None:
            return default
        return min(int(self.n_workers), n_envs)

    def _validate_inputs(
        self, agent: Any, env_configs: list[dict], n_steps: int
    ) -> None:
        """校验 collect 输入（R03：非法即 raise）。"""
        if agent is None:
            raise ValueError("agent 不能为 None（R03 无 fall-back）")
        if not isinstance(env_configs, list):
            raise ValueError(
                f"env_configs 须为 list，得到 {type(env_configs).__name__}（R03 无 fall-back）"
            )
        if len(env_configs) == 0:
            raise ValueError("env_configs 不能为空（R03 无 fall-back）")
        if n_steps <= 0:
            raise ValueError(f"n_steps 须 > 0，得到 {n_steps}（R03 无 fall-back）")
        # 每个 env_config 须为 dict（主进程需读 seed；type 字段校验在 worker _make_env）
        for i, cfg in enumerate(env_configs):
            if not isinstance(cfg, dict):
                raise ValueError(
                    f"env_configs[{i}] 须为 dict，得到 {type(cfg).__name__}（R03 无 fall-back）"
                )

    def _dispatch_and_gather(
        self,
        agent: Any,
        env_configs: list[dict],
        n_steps: int,
        n_workers: int,
    ) -> list[RolloutBatch]:
        """提交任务并收集结果（保持提交顺序，worker 崩溃即 raise，R03）。

        Returns:
            按 env_configs 顺序排列的 RolloutBatch 列表。

        Raises:
            RuntimeError: worker 进程崩溃（BrokenProcessPool）或 worker 内异常
                （经 future.result() 传播，R03 不静默跳过）。
        """
        batches: list[RolloutBatch | None] = [None] * len(env_configs)
        with ProcessPoolExecutor(
            max_workers=n_workers,
            mp_context=_MP_CONTEXT,
            initializer=_worker_init,
            initargs=(agent,),
        ) as executor:
            future_to_idx: dict = {}
            for idx, cfg in enumerate(env_configs):
                seed = int(cfg.get("seed", 0)) + idx
                fut = executor.submit(_rollout_worker, cfg, n_steps, seed, idx)
                future_to_idx[fut] = idx
            try:
                for fut in as_completed(future_to_idx):
                    idx = future_to_idx[fut]
                    # R03: worker 内异常在此重新抛出，不静默跳过
                    batches[idx] = fut.result()
            except BrokenProcessPool as exc:
                # worker 进程崩溃（segfault/OOM/初始化失败）→ R03 raise
                raise RuntimeError(
                    f"worker 进程崩溃（BrokenProcessPool）: {exc}（R03 无 fall-back）"
                ) from exc
        # 校验全部 batch 已收集（R03：None 表示逻辑错误，禁止 fall-back）
        for i, b in enumerate(batches):
            if b is None:
                raise RuntimeError(
                    f"worker {i} 的 batch 未收集（逻辑错误，R03 无 fall-back）"
                )
        return batches  # type: ignore[return-value]

    def collect(
        self,
        agent: Any,
        env_configs: list[dict],
        n_steps: int,
    ) -> list[RolloutBatch]:
        """主入口：并行采集 rollout（每个 env_config 一个 worker）。

        Args:
            agent: 策略智能体（须可 pickle 且有 get_action）。
            env_configs: env 构造参数 dict 列表（每个须含 ``type`` 字段）。
            n_steps: 每个 worker 采样步数。

        Returns:
            ``list[RolloutBatch]``，按 env_configs 顺序排列。

        Raises:
            ValueError: 输入非法（R03 无 fall-back）。
            RuntimeError: worker 进程崩溃或 worker 内异常（R03 无 fall-back）。
        """
        self._validate_inputs(agent, env_configs, n_steps)
        n_workers = self._resolve_n_workers(len(env_configs))
        return self._dispatch_and_gather(agent, env_configs, n_steps, n_workers)

    def collect_async_wait(
        self,
        agent: Any,
        env_configs: list[dict],
        n_steps: int,
        timeout: float | None = None,
    ) -> list[RolloutBatch]:
        """并行采集（wait 模式，支持 timeout；超时即 raise，R03）。

        与 ``collect`` 区别：用 ``concurrent.futures.wait`` 替代 ``as_completed``，
        支持全局超时。超时未完成的 worker 视为崩溃 → raise RuntimeError。

        Args:
            agent: 策略智能体。
            env_configs: env 构造参数列表。
            n_steps: 采样步数。
            timeout: 全局超时秒数（None 表示不限）。

        Returns:
            按 env_configs 顺序排列的 RolloutBatch 列表。

        Raises:
            TimeoutError: 超时（R03 无 fall-back）。
            RuntimeError: worker 崩溃（R03 无 fall-back）。
        """
        self._validate_inputs(agent, env_configs, n_steps)
        n_workers = self._resolve_n_workers(len(env_configs))
        batches: list[RolloutBatch | None] = [None] * len(env_configs)
        with ProcessPoolExecutor(
            max_workers=n_workers,
            mp_context=_MP_CONTEXT,
            initializer=_worker_init,
            initargs=(agent,),
        ) as executor:
            future_to_idx: dict = {}
            for idx, cfg in enumerate(env_configs):
                seed = int(cfg.get("seed", 0)) + idx
                fut = executor.submit(_rollout_worker, cfg, n_steps, seed, idx)
                future_to_idx[fut] = idx
            done, not_done = wait(future_to_idx.keys(), timeout=timeout)
            if not_done:
                raise TimeoutError(
                    f"{len(not_done)} 个 worker 超时（timeout={timeout}s，R03 无 fall-back）"
                )
            try:
                for fut in done:
                    idx = future_to_idx[fut]
                    batches[idx] = fut.result()
            except BrokenProcessPool as exc:
                raise RuntimeError(
                    f"worker 进程崩溃: {exc}（R03 无 fall-back）"
                ) from exc
        for i, b in enumerate(batches):
            if b is None:
                raise RuntimeError(
                    f"worker {i} 的 batch 未收集（R03 无 fall-back）"
                )
        return batches  # type: ignore[return-value]


# ===========================================================================
# 模块级主入口函数
# ===========================================================================


def collect_rollouts_parallel(
    agent: Any,
    env_configs: list[dict],
    n_steps: int,
    n_workers: int | None = None,
) -> list[RolloutBatch]:
    """主入口：CPU 多进程并行 rollout（PPO on-policy 多 env 采样）。

    便捷封装，等价于 ``ParallelRolloutCollector(n_workers).collect(...)``。
    n_workers 默认 = ``min(cpu_count, len(env_configs))``，避免空进程。

    Args:
        agent: 策略智能体（须可 pickle 且有 ``get_action``，如 ``PPOAgent``）。
        env_configs: env 构造参数 dict 列表（每个须含 ``type`` 字段，如 ``"mock"``）。
        n_steps: 每个 worker 采样步数。
        n_workers: worker 进程数（None → min(cpu_count, len(env_configs))）。

    Returns:
        ``list[RolloutBatch]``，按 env_configs 顺序排列，每个 batch 含
        states/actions/rewards/next_states/dones numpy 数组。

    Raises:
        ValueError: 输入非法（R03 无 fall-back）。
        RuntimeError: worker 进程崩溃或 worker 内异常（R03 无 fall-back）。

    示例::

        from polaris_trainer import PPOAgent, collect_rollouts_parallel
        agent = PPOAgent(obs_dim=8, action_dim=2, hidden_dim=16)
        env_configs = [{"type": "mock", "obs_dim": 8, "action_dim": 2, "seed": i}
                       for i in range(4)]
        batches = collect_rollouts_parallel(agent, env_configs, n_steps=16)
        # batches: 4 个 RolloutBatch，每个含 16 步轨迹
    """
    collector = ParallelRolloutCollector(n_workers=n_workers)
    return collector.collect(agent, env_configs, n_steps)


__all__ = [
    "GPU_DISABLED_R04",
    "RolloutBatch",
    "ParallelRolloutCollector",
    "collect_rollouts_parallel",
    "register_env_factory",
    "ENV_FACTORIES",
]
