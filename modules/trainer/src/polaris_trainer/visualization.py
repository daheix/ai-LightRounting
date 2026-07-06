"""训练曲线可视化（polaris-trainer）—— 纯 CPU matplotlib。

为 D07 AI/ML 维度增强（8→10）提供训练结果可视化能力，对齐
Stable-Baselines3 / CleanRL / TensorBoard 的可视化实践。

## 核心能力

- ``plot_reward_curve``: 奖励曲线（含滑动平均）
- ``plot_hpwl_convergence``: HPWL 收敛曲线（布局质量）
- ``plot_policy_entropy``: Policy entropy 曲线（探索-利用平衡）
- ``plot_learning_rate``: 学习率调度曲线
- ``plot_training_dashboard``: 综合仪表盘（4 合 1 子图）
- ``save_dashboard``: 保存仪表盘到 PNG

## 数据来源

从 ``TrainingLogger`` 写入的 JSONL 日志文件加载，或直接接收训练日志
列表（``train_ppo`` 返回的 ``logs``）。两种模式均支持。

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. matplotlib 官方文档 https://matplotlib.org/stable/contents.html
2. TensorBoard 可视化 https://www.tensorflow.org/tensorboard
3. Stable-Baselines3 训练可视化
   https://stable-baselines3.readthedocs.io/en/master/guide/tensorboard.html
4. CleanRL 训练曲线绘制 https://github.com/vwxyzjn/cleanrl
5. Schulman et al., 2017, PPO（entropy 系数与探索）
   https://arxiv.org/abs/1707.06347
6. Loshchilov & Hutter, 2017, SGDR（学习率调度可视化）
   https://arxiv.org/abs/1608.03983
7. Williams & Peng, 1991, Policy entropy 与探索
   https://doi.org/10.1162/neco.1991.3.3.291

来源: D07 AI/ML 维度增强（2026-07-06），目标 8→10 分。
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

# matplotlib 后端切换为 Agg（无显示环境也能保存 PNG，CI 友好）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from polaris_trainer.tensorboard_logger import load_jsonl_log  # noqa: E402


def _extract_metric(
    records: list[dict],
    key: str,
    prefix: str = "train",
) -> tuple[np.ndarray, np.ndarray]:
    """从日志记录提取 (steps, values)。

    Args:
        records: 日志记录列表。
        key: 指标名（如 ep_reward / hpwl_um / entropy）。
        prefix: 前缀（默认 train，对应 train/<key>）。

    Returns:
        (steps, values) 数组。
    """
    steps: list[int] = []
    values: list[float] = []
    full_key = f"{prefix}/{key}" if prefix else key
    for rec in records:
        if full_key in rec:
            steps.append(int(rec.get("step", 0)))
            values.append(float(rec[full_key]))
        elif key in rec:  # 兼容无前缀格式
            steps.append(int(rec.get("step", 0)))
            values.append(float(rec[key]))
    return np.array(steps), np.array(values)


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """计算滑动平均（窗口大小 window，边界用截断窗口）。

    Args:
        values: 值数组。
        window: 窗口大小（≥1）。

    Returns:
        滑动平均数组（与 values 等长）。
    """
    if window < 1:
        raise ValueError(f"window 必须 ≥1: {window}（R03 无 fall-back）")
    if len(values) == 0:
        return values
    window = min(window, len(values))
    # 截断窗口滑动平均（边界用更短窗口，避免 NaN）
    cumsum = np.cumsum(np.insert(values, 0, 0.0))
    ma = (cumsum[window:] - cumsum[:-window]) / window
    # 边界填充：前 window-1 个用累计平均
    result = np.empty_like(values, dtype=np.float64)
    result[window - 1:] = ma
    for i in range(window - 1):
        result[i] = values[: i + 1].mean()
    return result


def plot_reward_curve(
    logs: list[dict] | str | Path,
    window: int = 10,
    ax: plt.Axes | None = None,
    title: str = "Reward Curve",
) -> plt.Axes:
    """绘制奖励曲线（含滑动平均）。

    Args:
        logs: 训练日志列表，或 JSONL 日志文件路径。
        window: 滑动平均窗口大小。
        ax: matplotlib Axes（None 创建新图）。
        title: 图标题。

    Returns:
        matplotlib Axes。
    """
    records = _load_logs(logs)
    steps, rewards = _extract_metric(records, "ep_reward")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    if len(rewards) > 0:
        ax.plot(steps, rewards, alpha=0.3, color="blue", label="Episode reward")
        if len(rewards) >= 2:
            ma = _moving_average(rewards, min(window, len(rewards)))
            ax.plot(steps, ma, color="red", linewidth=2,
                    label=f"Moving avg (w={window})")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Reward")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def plot_hpwl_convergence(
    logs: list[dict] | str | Path,
    ax: plt.Axes | None = None,
    title: str = "HPWL Convergence",
) -> plt.Axes:
    """绘制 HPWL 收敛曲线（布局质量）。

    Args:
        logs: 训练日志列表，或 JSONL 日志文件路径。
        ax: matplotlib Axes（None 创建新图）。
        title: 图标题。

    Returns:
        matplotlib Axes。
    """
    records = _load_logs(logs)
    steps, hpwl = _extract_metric(records, "hpwl_um")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    if len(hpwl) > 0:
        ax.plot(steps, hpwl, color="green", linewidth=2, marker="o", markersize=3)
    ax.set_xlabel("Episode")
    ax.set_ylabel("HPWL (μm)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    return ax


def plot_policy_entropy(
    logs: list[dict] | str | Path,
    ax: plt.Axes | None = None,
    title: str = "Policy Entropy",
) -> plt.Axes:
    """绘制 Policy entropy 曲线（探索-利用平衡）。

    来源: Schulman 2017 PPO entropy 系数；Williams & Peng 1991 policy entropy。

    Args:
        logs: 训练日志列表，或 JSONL 日志文件路径。
        ax: matplotlib Axes（None 创建新图）。
        title: 图标题。

    Returns:
        matplotlib Axes。
    """
    records = _load_logs(logs)
    steps, entropy = _extract_metric(records, "entropy")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    if len(entropy) > 0:
        ax.plot(steps, entropy, color="purple", linewidth=2, marker="s", markersize=3)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Policy Entropy")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    return ax


def plot_learning_rate(
    logs: list[dict] | str | Path,
    ax: plt.Axes | None = None,
    title: str = "Learning Rate Schedule",
) -> plt.Axes:
    """绘制学习率调度曲线（cosine/linear 衰减可视化）。

    来源: Loshchilov & Hutter, 2017, SGDR https://arxiv.org/abs/1608.03983

    Args:
        logs: 训练日志列表，或 JSONL 日志文件路径。
        ax: matplotlib Axes（None 创建新图）。
        title: 图标题。

    Returns:
        matplotlib Axes。
    """
    records = _load_logs(logs)
    steps, lr = _extract_metric(records, "lr")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    if len(lr) > 0:
        ax.plot(steps, lr, color="orange", linewidth=2, marker="^", markersize=3)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Learning Rate")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    return ax


def _load_logs(logs: list[dict] | str | Path) -> list[dict]:
    """加载日志：list 直接返回，str/Path 从 JSONL 文件加载。"""
    if isinstance(logs, (str, Path)):
        return load_jsonl_log(logs)
    return list(logs)


def plot_training_dashboard(
    logs: list[dict] | str | Path,
    figsize: tuple[float, float] = (14, 10),
    title: str = "PPO Training Dashboard",
) -> plt.Figure:
    """绘制综合训练仪表盘（4 合 1 子图）。

    子图布局::
        ┌──────────────┬──────────────┐
        │ Reward Curve  │ HPWL Converge │
        ├──────────────┼──────────────┤
        │ Policy Entropy│ Learning Rate │
        └──────────────┴──────────────┘

    Args:
        logs: 训练日志列表，或 JSONL 日志文件路径。
        figsize: 图尺寸。
        title: 总标题。

    Returns:
        matplotlib Figure。
    """
    records = _load_logs(logs)
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle(title, fontsize=14, fontweight="bold")
    plot_reward_curve(records, ax=axes[0, 0], title="Reward Curve")
    plot_hpwl_convergence(records, ax=axes[0, 1], title="HPWL Convergence")
    plot_policy_entropy(records, ax=axes[1, 0], title="Policy Entropy")
    plot_learning_rate(records, ax=axes[1, 1], title="Learning Rate")
    plt.tight_layout()
    return fig


def save_dashboard(
    logs: list[dict] | str | Path,
    output_path: str | Path,
    figsize: tuple[float, float] = (14, 10),
    title: str = "PPO Training Dashboard",
) -> Path:
    """保存训练仪表盘到 PNG 文件。

    Args:
        logs: 训练日志列表，或 JSONL 日志文件路径。
        output_path: 输出 PNG 路径。
        figsize: 图尺寸。
        title: 总标题。

    Returns:
        输出文件路径。
    """
    fig = plot_training_dashboard(logs, figsize=figsize, title=title)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_benchmark_comparison(
    reports: Sequence[dict],
    ax: plt.Axes | None = None,
    title: str = "TILOS Benchmark Comparison",
) -> plt.Axes:
    """绘制 benchmark 对比柱状图（归一化 HPWL，越低越好）。

    Args:
        reports: BenchmarkReport.to_dict() 列表。
        ax: matplotlib Axes（None 创建新图）。
        title: 图标题。

    Returns:
        matplotlib Axes。
    """
    if not reports:
        raise ValueError("reports 不能为空（R03 无 fall-back）")
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))
    names = [r["benchmark_name"] for r in reports]
    our_hpwl = [r["normalized_hpwl"] for r in reports]
    # 提取基线
    methods = [b["method"] for b in reports[0]["baselines"]]
    baseline_data: dict[str, list[float]] = {m: [] for m in methods}
    for r in reports:
        for b in r["baselines"]:
            baseline_data[b["method"]].append(b["normalized_hpwl"])
    x = np.arange(len(names))
    width = 0.8 / (1 + len(methods))
    ax.bar(x - 0.4 + width / 2, our_hpwl, width, label="PoLaRIS", color="red")
    for i, m in enumerate(methods):
        ax.bar(
            x - 0.4 + width * (i + 2) / 2,
            baseline_data[m],
            width,
            label=m,
            alpha=0.7,
        )
    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1, label="Target (1.0)")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("Normalized HPWL (lower is better)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    return ax


__all__ = [
    "plot_reward_curve",
    "plot_hpwl_convergence",
    "plot_policy_entropy",
    "plot_learning_rate",
    "plot_training_dashboard",
    "save_dashboard",
    "plot_benchmark_comparison",
]
