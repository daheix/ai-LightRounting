"""解析法布局器 - 优化核心模块（polaris-place 子模块）。

从 ``analytical.py`` 拆分而来，包含 DREAMPlace 风格的连续优化算法:
- 加权平均初始布局
- 平滑 HPWL 梯度（log-sum-exp 近似）
- O(n²) 密度惩罚梯度（成对排斥力）
- Adam 优化器一步更新
- HPWL 收敛判定
- 拓扑深度（Kahn 算法）

仅依赖 numpy（R04: 不参与 GPU）。

## 来源（R02 学术诚信）

- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020 (Lin et al.): https://arxiv.org/abs/2004.10746
- DREAMPlace 开源: https://github.com/limbo018/DREAMPlace
- log-sum-exp 平滑: Nesterov 2005 "Smooth minimization of non-smooth functions"
- log-sum-exp 数值稳定 trick: Blanchard et al. arXiv:2106.14588
  https://arxiv.org/abs/2106.14588
- Adam 优化器: Kingma & Ba 2014 https://arxiv.org/abs/1412.6980
- Kahn 1962 拓扑排序 https://doi.org/10.1145/368996.369025
"""

from __future__ import annotations

from collections import deque

import numpy as np

__all__ = [
    "initial_placement",
    "smooth_hpwl_gradient",
    "density_gradient",
    "adam_step",
    "compute_hpwl_pos",
    "topological_depth",
]


def initial_placement(
    n: int,
    connections: list[tuple[int, int]],
    canvas_w: float,
    canvas_h: float,
    seed: int,
) -> np.ndarray:
    """加权平均初始布局（DREAMPlace TCAD 2020 §III-A）。

    每个器件初始位置 = 连接对端的加权平均 + 画布中心偏移；无连接的器件放
    画布中心。使用固定种子 RNG 保证可复现（DREAMPlace torch.manual_seed 约定）。

    Args:
        n: 器件数。
        connections: 索引化连接列表。
        canvas_w: 画布宽。
        canvas_h: 画布高。
        seed: 随机种子。

    Returns:
        初始坐标 ``(n, 2)``，列 0=x，列 1=y（中心坐标）。
    """
    pos = np.zeros((n, 2), dtype=np.float64)
    cx, cy = canvas_w / 2.0, canvas_h / 2.0
    neighbor_cnt = np.zeros(n, dtype=np.float64)
    for src, dst in connections:
        neighbor_cnt[src] += 1
        neighbor_cnt[dst] += 1
    rng = np.random.default_rng(seed)
    for i in range(n):
        if neighbor_cnt[i] == 0:
            pos[i] = [cx, cy]
        else:
            # 固定种子扰动，避免全重合
            pos[i] = [cx + rng.uniform(-10, 10), cy + rng.uniform(-10, 10)]
    # 迭代加权平均（3 轮收敛）
    for _ in range(3):
        new_pos = pos.copy()
        for src, dst in connections:
            new_pos[src] += pos[dst]
            new_pos[dst] += pos[src]
        for i in range(n):
            if neighbor_cnt[i] > 0:
                new_pos[i] /= neighbor_cnt[i] + 1.0
        pos = new_pos
    pos[:, 0] = np.clip(pos[:, 0], 0.0, canvas_w)
    pos[:, 1] = np.clip(pos[:, 1], 0.0, canvas_h)
    return pos


def smooth_hpwl_gradient(
    pos: np.ndarray,
    connections: list[tuple[int, int]],
    gamma: float,
) -> np.ndarray:
    """平滑 HPWL 梯度（log-sum-exp 近似，数值稳定 trick）。

    对每条连接，HPWL = max(xs) - min(xs) + max(ys) - min(ys)。
    平滑: max(xs) ≈ γ·log(Σ exp(xs/γ))；min(xs) ≈ -γ·log(Σ exp(-xs/γ))。
    数值稳定: exp((x - max_x)/γ) 防止溢出（Blanchard et al. arXiv:2106.14588）。

    Args:
        pos: 当前坐标 ``(n, 2)``。
        connections: 索引化连接列表。
        gamma: 平滑系数。

    Returns:
        HPWL 梯度 ``(n, 2)``。

    Raises:
        RuntimeError: 梯度含 NaN/Inf（优化发散，R03 禁止 fall-back）。
    """
    grad = np.zeros_like(pos)
    for src, dst in connections:
        x1, y1 = pos[src]
        x2, y2 = pos[dst]
        xs = np.array([x1, x2])
        ys = np.array([y1, y2])
        max_x, min_x = xs.max(), xs.min()
        max_y, min_y = ys.max(), ys.min()
        exp_x = np.exp((xs - max_x) / gamma)
        exp_neg_x = np.exp((-xs + min_x) / gamma)
        exp_y = np.exp((ys - max_y) / gamma)
        exp_neg_y = np.exp((-ys + min_y) / gamma)
        sum_exp_x = max(exp_x.sum(), 1e-300)
        sum_exp_neg_x = max(exp_neg_x.sum(), 1e-300)
        sum_exp_y = max(exp_y.sum(), 1e-300)
        sum_exp_neg_y = max(exp_neg_y.sum(), 1e-300)
        # d(HPWL)/d(x_i) = softmax_max - softmax_min（最小化→负梯度方向，外部 Adam 取负）
        for idx in (src, dst):
            i = 0 if idx == src else 1
            grad[idx, 0] += exp_x[i] / sum_exp_x - exp_neg_x[i] / sum_exp_neg_x
            grad[idx, 1] += exp_y[i] / sum_exp_y - exp_neg_y[i] / sum_exp_neg_y
    if not np.all(np.isfinite(grad)):
        raise RuntimeError(
            f"HPWL 梯度含非有限值（NaN/Inf），优化可能发散: "
            f"max={np.nanmax(grad)}, min={np.nanmin(grad)} "
            f"（R03 禁止 fall-back，请检查学习率/坐标范围）"
        )
    return grad


def density_gradient(
    pos: np.ndarray,
    n: int,
    bandwidth: float,
) -> np.ndarray:
    """O(n²) 成对排斥力密度梯度（DREAMPlace TCAD 2020 公式 7-9）。

    距离 < bandwidth 的器件对施加与距离反比的排斥力。

    Args:
        pos: 当前坐标 ``(n, 2)``。
        n: 器件数。
        bandwidth: 密度场带宽。

    Returns:
        密度梯度 ``(n, 2)``。
    """
    grad = np.zeros_like(pos)
    bw2 = bandwidth * bandwidth
    for i in range(n):
        for j in range(i + 1, n):
            dx = pos[i, 0] - pos[j, 0]
            dy = pos[i, 1] - pos[j, 1]
            dist_sq = dx * dx + dy * dy
            if dist_sq < bw2 and dist_sq > 1e-6:
                dist = np.sqrt(dist_sq)
                force = (bandwidth - dist) / dist
                grad[i, 0] += force * dx
                grad[i, 1] += force * dy
                grad[j, 0] -= force * dx
                grad[j, 1] -= force * dy
    return grad


def adam_step(
    pos: np.ndarray,
    grad: np.ndarray,
    m: np.ndarray,
    v: np.ndarray,
    t: int,
    lr: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Adam 优化器一步更新（Kingma & Ba 2014）。

    Args:
        pos: 当前坐标。
        grad: 梯度（最小化方向，已含正负号）。
        m: 一阶矩。
        v: 二阶矩。
        t: 时间步。
        lr: 学习率。

    Returns:
        ``(new_pos, new_m, new_v)``。
    """
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    new_m = beta1 * m + (1 - beta1) * grad
    new_v = beta2 * v + (1 - beta2) * grad * grad
    m_hat = new_m / (1 - beta1**t)
    v_hat = new_v / (1 - beta2**t)
    new_pos = pos - lr * m_hat / (np.sqrt(v_hat) + eps)
    return new_pos, new_m, new_v


def compute_hpwl_pos(
    pos: np.ndarray,
    connections: list[tuple[int, int]],
) -> float:
    """计算当前坐标的真实 HPWL（非平滑，用于收敛判定）。

    Args:
        pos: 坐标 ``(n, 2)``。
        connections: 索引化连接列表。

    Returns:
        HPWL 总线长（μm）。
    """
    total = 0.0
    for src, dst in connections:
        total += abs(pos[src, 0] - pos[dst, 0]) + abs(pos[src, 1] - pos[dst, 1])
    return total


def topological_depth(
    n: int,
    connections: list[tuple[int, int]],
) -> list[int]:
    """计算每个器件的拓扑深度（Kahn 算法 + 最长路径）。

    拓扑深度 = 从源器件（入度=0）到当前器件的最长路径长度。源器件 depth=0，
    下游器件 depth = max(上游 depth) + 1。用于 FFDH 合法化时保证信号流
    方向 x 递增（拓扑序靠后的器件 x 坐标更大，避免后端器件被塞到前端
    器件的行内空隙导致物理重叠与 DRC 违规）。

    算法: Kahn 算法（Kahn 1962）逐层剥离入度=0 的节点，同时维护最长路径
    depth。可检测环（电路连接不应有环，有环则 raise，R03 禁止 fall-back）。

    Args:
        n: 器件数。
        connections: 索引化连接列表 ``[(src_idx, dst_idx), ...]``。

    Returns:
        每个器件的拓扑深度列表 ``[depth_0, depth_1, ...]``。

    Raises:
        RuntimeError: 连接存在环（无法拓扑排序，R03 禁止 fall-back）。

    来源（R02 学术诚信）:
        - Kahn 1962 "Topological Sorting of Large Networks"
          https://doi.org/10.1145/368996.369025
        - CLRS Introduction to Algorithms 3rd ed. §22.4 Topological sort
        - Topological sorting (Wikipedia)
          https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
        - Longest path in DAG
          https://en.wikipedia.org/wiki/Longest_path_problem#Acyclic_graphs
        - DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746
    """
    adj: list[list[int]] = [[] for _ in range(n)]
    indeg = [0] * n
    for src, dst in connections:
        adj[src].append(dst)
        indeg[dst] += 1
    depth = [0] * n
    queue: deque[int] = deque(i for i in range(n) if indeg[i] == 0)
    processed = 0
    while queue:
        u = queue.popleft()
        processed += 1
        for v in adj[u]:
            if depth[u] + 1 > depth[v]:
                depth[v] = depth[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if processed != n:
        raise RuntimeError(
            f"电路连接存在环，无法拓扑排序（processed={processed}/"
            f"{n}，R03 禁止 fall-back，请检查 connections 是否含环）"
        )
    return depth
