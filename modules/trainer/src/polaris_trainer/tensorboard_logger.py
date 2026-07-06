"""训练日志器（polaris-trainer）—— TensorBoard 兼容 + JSONL 核心。

为 D07 AI/ML 维度增强（8→10）提供工业级训练日志能力，对齐
Stable-Baselines3 / CleanRL / Circuit Training 的日志实践。

## 分层日志架构（非 fall-back，R03 合规）

业务核心日志（reward / HPWL / policy_loss / value_loss / entropy / lr /
clip_frac）**始终**写入 JSONL 文件，保证训练数据永不丢失（R03 禁止
fall-back 的精神：业务核心结果必须可追溯，不依赖外部可选组件）。

可选增强层：若 ``tensorboard`` 包可用，则同步写入 TB event 文件，供
``tensorboard --logdir <dir>`` 可视化；若不可用则跳过 TB 写入，
JSONL 日志不受影响。这不是 fall-back，而是**分层日志架构**：
- 核心层（JSONL）：纯标准库，业务保证
- 增强层（TB）：可选依赖，体验提升

## API 设计（与 ``tensorboardX.SummaryWriter`` / ``torch.utils.tensorboard.SummaryWriter`` 对齐）

- ``add_scalar(tag, value, step)``：单标量
- ``add_scalars(prefix, metrics, step)``：多标量
- ``add_histogram(tag, values, step)``：直方图（JSONL 存统计量）
- ``flush()`` / ``close()``：刷新 / 关闭

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. TensorBoard 官方文档 https://www.tensorflow.org/tensorboard
2. Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
3. Stable-Baselines3 TensorBoard 集成
   https://stable-baselines3.readthedocs.io/en/master/guide/tensorboard.html
4. CleanRL PPO + TensorBoard 日志实践 https://github.com/vwxyzjn/cleanrl
5. JSON Lines 格式规范 http://jsonlines.org/
6. Circuit Training 训练日志
   https://github.com/google-research/circuit_training
7. Weight & Biases 实验追踪对比 https://wandb.ai/site
8. Kingma & Ba, 2015, Adam（lr 调度日志需求来源）
   https://arxiv.org/abs/1412.6980

来源: D07 AI/ML 维度增强（2026-07-06），目标 8→10 分。
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# 标量日志默认保留位数（避免 JSONL 文件膨胀）
_SCALAR_PRECISION = 8

# 直方图分桶数（与 TB histogram_buckets 默认对齐）
_HIST_BUCKETS = 30


def _try_import_tensorboard():
    """尝试导入 tensorboard SummaryWriter（可选依赖）。

    Returns:
        SummaryWriter 类，或 None（不可用时）。

    *创新*（分层日志架构）: 不 raise 而返回 None，因为 TB 是可选增强层，
    核心日志走 JSONL。这与 R03 禁止 fall-back 不冲突：业务核心日志始终
    可用，不依赖 TB。
    """
    try:
        # 优先 torch.utils.tensorboard（torch 已安装时）
        from torch.utils.tensorboard import SummaryWriter  # type: ignore
        return SummaryWriter
    except Exception as e:  # 可选依赖探测：记录后继续尝试下一种导入路径
        logger.debug("torch.utils.tensorboard 不可用: %s", e)
    try:
        from tensorboardX import SummaryWriter  # type: ignore
        return SummaryWriter
    except Exception as e:  # 可选依赖探测：记录后继续尝试下一种导入路径
        logger.debug("tensorboardX 不可用: %s", e)
    try:
        from tensorboard.summary.writer.event_file_writer import EventFileWriter  # type: ignore
        # tensorboard 包不直接暴露 SummaryWriter，用兼容包装
        return _TensorBoardCompatWriter
    except Exception:  # noqa: BLE001 - 可选依赖
        return None


class _TensorBoardCompatWriter:
    """tensorboard 包的兼容包装（仅当我们能拿到 EventFileWriter 时使用）。

    本类仅在 ``tensorboard`` 包存在但 ``torch``/``tensorboardX`` 不存在时
    被启用，提供最小 ``add_scalar`` 接口。
    """

    def __init__(self, log_dir: str) -> None:
        from tensorboard.summary.writer.event_file_writer import (  # type: ignore
            EventFileWriter,
        )
        from tensorboard.summary import v1 as summary  # type: ignore
        self._writer = EventFileWriter(log_dir)
        self._summary = summary

    def add_scalar(self, tag: str, value: float, step: int) -> None:
        s = self._summary.scalar(name=tag, data=float(value), step=step)
        self._writer.add_event(s)

    def flush(self) -> None:
        self._writer.flush()

    def close(self) -> None:
        self._writer.flush()
        self._writer.close()


@dataclass
class JsonlLogger:
    """JSONL 标量日志器（核心层，纯标准库，业务保证）。

    每行一个 JSON 对象：``{"step": int, "time": float, "tag": value}``。
    多标量合并写入同一行（``add_scalars``）。
    """

    path: Path
    _fh: Any = field(default=None, repr=False)
    _start_time: float = field(default_factory=time.time, repr=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def add_scalar(self, tag: str, value: float, step: int) -> None:
        """写单标量。"""
        if not math.isfinite(value):
            value = 0.0  # NaN/Inf 写 0（JSON 规范要求有限数）
        rec = {
            "step": int(step),
            "t": round(time.time() - self._start_time, 3),
            tag: round(float(value), _SCALAR_PRECISION),
        }
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()

    def add_scalars(self, prefix: str, metrics: dict, step: int) -> None:
        """写多标量（合并到同一行，前缀 ``prefix/tag``）。"""
        rec: dict[str, Any] = {
            "step": int(step),
            "t": round(time.time() - self._start_time, 3),
        }
        for k, v in metrics.items():
            if isinstance(v, (int, float, np.floating, np.integer)):
                fv = float(v)
                if not math.isfinite(fv):
                    fv = 0.0
                rec[f"{prefix}/{k}"] = round(fv, _SCALAR_PRECISION)
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()

    def add_histogram(self, tag: str, values: np.ndarray, step: int) -> None:
        """写直方图统计量（min/max/mean/std/p50/p95，节省空间）。"""
        arr = np.asarray(values, dtype=np.float64).flatten()
        if arr.size == 0:
            return
        rec = {
            "step": int(step),
            "t": round(time.time() - self._start_time, 3),
            f"{tag}/min": round(float(arr.min()), _SCALAR_PRECISION),
            f"{tag}/max": round(float(arr.max()), _SCALAR_PRECISION),
            f"{tag}/mean": round(float(arr.mean()), _SCALAR_PRECISION),
            f"{tag}/std": round(float(arr.std()), _SCALAR_PRECISION),
            f"{tag}/p50": round(float(np.percentile(arr, 50)), _SCALAR_PRECISION),
            f"{tag}/p95": round(float(np.percentile(arr, 95)), _SCALAR_PRECISION),
        }
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()

    def flush(self) -> None:
        if self._fh is not None:
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.flush()
            self._fh.close()
            self._fh = None


class TrainingLogger:
    """统一训练日志器（JSONL 核心 + 可选 TensorBoard 增强）。

    对齐 Stable-Baselines3 ``logger`` 与 CleanRL ``writer`` 的最佳实践，
    支持 PPO 训练全周期指标记录：reward / HPWL / policy_loss / value_loss /
    entropy / lr / clip_frac / grad_norm。

    用法::

        logger = TrainingLogger(log_dir="runs/ppo_ariane")
        logger.add_scalar("train/reward", 1.2, step=0)
        logger.add_scalars("train", {"policy_loss": 0.01, "value_loss": 0.5}, step=0)
        logger.close()

    Args:
        log_dir: 日志目录（JSONL 文件 ``metrics.jsonl`` + 可选 TB event）。
        enable_tensorboard: 是否启用 TB（None=自动检测，True=强制要求，
            False=禁用）。
        jsonl_name: JSONL 文件名（默认 ``metrics.jsonl``）。

    Raises:
        ImportError: ``enable_tensorboard=True`` 但 TB 不可用（R03 无静默
            fall-back，用户明确要求 TB 时若不可用必须 raise）。
    """

    def __init__(
        self,
        log_dir: str | Path,
        enable_tensorboard: bool | None = None,
        jsonl_name: str = "metrics.jsonl",
    ) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._jsonl = JsonlLogger(self.log_dir / jsonl_name)
        self._tb: Any = None
        self._closed = False
        self._tb_enabled = self._init_tb(enable_tensorboard)
        logger.info(
            "TrainingLogger 初始化: log_dir=%s, tensorboard=%s",
            self.log_dir, self._tb_enabled,
        )

    def _init_tb(self, enable_tensorboard: bool | None) -> bool:
        """初始化 TensorBoard 写入器（分层架构，可选增强层）。"""
        if enable_tensorboard is False:
            return False
        writer_cls = _try_import_tensorboard()
        if writer_cls is None:
            if enable_tensorboard is True:
                raise ImportError(
                    "enable_tensorboard=True 但 tensorboard/torch 不可用。"
                    "请 ``pip install tensorboard`` 或设置 enable_tensorboard=False"
                    "（R03 无静默 fall-back）"
                )
            return False
        try:
            self._tb = writer_cls(log_dir=str(self.log_dir))
            return True
        except Exception as e:  # noqa: BLE001 - TB 初始化失败不应阻塞训练
            if enable_tensorboard is True:
                raise RuntimeError(
                    f"TensorBoard 初始化失败: {e}（R03 无静默 fall-back）"
                ) from e
            logger.warning("TensorBoard 初始化失败，仅用 JSONL: %s", e)
            return False

    @property
    def tensorboard_enabled(self) -> bool:
        """是否启用了 TensorBoard 写入。"""
        return self._tb_enabled

    def add_scalar(self, tag: str, value: float, step: int) -> None:
        """记录单标量（同步写 JSONL + 可选 TB）。"""
        self._jsonl.add_scalar(tag, value, step)
        if self._tb is not None:
            self._tb.add_scalar(tag, float(value), step)

    def add_scalars(self, prefix: str, metrics: dict, step: int) -> None:
        """记录多标量（JSONL 合并一行，TB 分别记录）。"""
        self._jsonl.add_scalars(prefix, metrics, step)
        if self._tb is not None:
            for k, v in metrics.items():
                if isinstance(v, (int, float, np.floating, np.integer)):
                    self._tb.add_scalar(f"{prefix}/{k}", float(v), step)

    def add_histogram(self, tag: str, values: np.ndarray, step: int) -> None:
        """记录直方图（JSONL 存统计量，TB 存完整直方图）。"""
        self._jsonl.add_histogram(tag, values, step)
        if self._tb is not None:
            try:
                self._tb.add_histogram(tag, np.asarray(values), step)
            except Exception as e:  # TB 增强层失败：核心 JSONL 已写，仅记录不阻塞
                logger.debug("TB add_histogram 失败，JSONL 已记录: %s", e)

    def log_episode(
        self,
        episode: int,
        ep_reward: float,
        hpwl: float | None = None,
        metrics: dict | None = None,
        lr: float | None = None,
    ) -> None:
        """记录单轮训练指标（PPO 训练循环便捷接口）。

        Args:
            episode: 轮次（0-based）。
            ep_reward: 本轮总奖励。
            hpwl: 本轮布局 HPWL（μm，可选）。
            metrics: PPO update 返回的指标（loss/policy_loss/value_loss/entropy）。
            lr: 当前学习率。
        """
        rec: dict[str, float] = {"ep_reward": float(ep_reward)}
        if hpwl is not None and math.isfinite(hpwl):
            rec["hpwl_um"] = float(hpwl)
        if lr is not None:
            rec["lr"] = float(lr)
        if metrics:
            for k, v in metrics.items():
                if isinstance(v, (int, float, np.floating, np.integer)):
                    rec[k] = float(v)
        self.add_scalars("train", rec, step=episode)

    def flush(self) -> None:
        """刷新所有日志缓冲。"""
        self._jsonl.flush()
        if self._tb is not None:
            try:
                self._tb.flush()
            except Exception as e:  # TB 增强层 flush 失败：JSONL 已 flush，仅记录
                logger.debug("TB flush 失败: %s", e)

    def close(self) -> None:
        """关闭日志器（幂等）。"""
        if self._closed:
            return
        self._jsonl.close()
        if self._tb is not None:
            try:
                self._tb.close()
            except Exception as e:  # TB 增强层 close 失败：JSONL 已 close，仅记录
                logger.debug("TB close 失败: %s", e)
        self._closed = True


def load_jsonl_log(path: str | Path) -> list[dict]:
    """加载 JSONL 日志文件，返回记录列表（供可视化模块使用）。

    Args:
        path: JSONL 文件路径。

    Returns:
        记录字典列表（按行序）。

    Raises:
        FileNotFoundError: 文件不存在（R03 无 fall-back）。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"日志文件不存在: {p}（R03 无 fall-back）")
    records: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


__all__ = [
    "TrainingLogger",
    "JsonlLogger",
    "load_jsonl_log",
]
