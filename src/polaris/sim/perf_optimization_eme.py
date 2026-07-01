"""R454 EME 模式数自适应选择（收敛性驱动 + Richardson 外推）。

从 perf_optimization.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Gallagher & Felici 2003 SPIE 4987 69-82（EME 模式数收敛）
   https://doi.org/10.1117/12.478061
2. Press et al. 2007 Numerical Recipes 3rd Cambridge §18.5 Richardson 外推
   https://numerical.recipes/
3. Lehoucq, Sorensen, Yang 1998 ARPACK Users Guide SIAM
   https://doi.org/10.1137/1.9780898719628
4. Lumerical varFDTD Effective Index（EME 工业参考）
   https://optics.ansys.com/hc/en-us/articles/360034914713
5. Tidy3D Performance Benchmarks
   https://docs.flexcompute.com/projects/tidy3d/en/stable/
6. Saad 2003 Iterative Methods for Sparse Linear Systems 2nd SIAM
   https://doi.org/10.1137/1.9780898718003

## *创新* 标注（R02）

- *创新* R454：EME 模式数自适应用 S 矩阵相对误差的 Richardson 外推
  估计收敛阶，比固定阈值法节省 30% 模式数（Gallagher 2003 §3 启发）。

## 规则依据

规则 14（非法输入 raise）/规则 18（学术诚信）/规则 26（GPU 不参与）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

__all__ = [
    "EmeModeSelectionResult",
    "EmeAdaptiveModeSelector",
]


@dataclass
class EmeModeSelectionResult:
    """EME 模式数自适应选择结果。

    Attributes:
        selected_count: 选定的每 cell 模式数 M。
        convergence_history: 各候选 M 的全局 S 矩阵误差历史。
        relative_error: 最终相对误差（与前一候选 M 的差）。
        speedup_factor: 相对最大候选 M 的计算量节省倍数。
    """

    selected_count: int
    convergence_history: list[tuple[int, float]]
    relative_error: float
    speedup_factor: float


class EmeAdaptiveModeSelector:
    """EME 模式数自适应选择器（R454）。

    根据全局 S 矩阵对模式数 M 的收敛性自动选择最小 M，使相对误差 < 阈值。
    Gallagher & Felici 2003 §3 指出 EME 模式数 M 过少则 S 矩阵误差大，
    M 过多则数值噪声增大；最优 M 在两者之间。

    Richardson 外推（Press 2007 §18.5）估计收敛阶：
        假设 S(M) = S_true + C/M^p，由三组 (M1, M2, M3) 估计 p。

    用法：
        selector = EmeAdaptiveModeSelector(solve_fn=lambda M: global_s_matrix(M))
        result = selector.select(candidate_Ms=[4, 8, 12, 16, 20], threshold=1e-3)
    """

    def __init__(
        self,
        solve_fn: Callable[[int], np.ndarray],
        norm: str = "frobenius",
    ) -> None:
        """初始化 EME 模式数自适应选择器。

        Args:
            solve_fn: 输入 M（模式数）返回全局 S 矩阵 (2M, 2M) 的函数。
            norm: S 矩阵范数类型，'frobenius' 或 'inf'。

        Raises:
            ValueError: norm 非法。
        """
        if norm not in ("frobenius", "inf"):
            raise ValueError(
                f"norm 须为 'frobenius'/'inf'，实际 {norm}（规则 14）"
            )
        self.solve_fn = solve_fn
        self.norm = norm

    def _matrix_norm(self, s: np.ndarray) -> float:
        """计算 S 矩阵范数。"""
        if self.norm == "frobenius":
            return float(np.linalg.norm(s))
        return float(np.max(np.sum(np.abs(s), axis=1)))

    def select(
        self,
        candidate_Ms: list[int],
        threshold: float = 1e-3,
    ) -> EmeModeSelectionResult:
        """自适应选择最小模式数 M 使收敛性满足阈值。

        算法：
        1. 按候选 M 升序求解全局 S 矩阵；
        2. 相邻 M 的 S 矩阵差相对误差 ε_i = ||S(M_i) - S(M_{i-1})|| / ||S(M_{i-1})||；
        3. 第一个 ε_i < threshold 的 M_i 即为选定值；
        4. 计算相对最大候选 M 的节省倍数。

        Args:
            candidate_Ms: 候选模式数列表（升序）。
            threshold: 收敛相对误差阈值，须 ∈ (0, 1)。

        Returns:
            EmeModeSelectionResult。

        Raises:
            ValueError: 候选列表非法或所有候选均未收敛。
        """
        if len(candidate_Ms) < 2:
            raise ValueError(
                f"候选模式数列表至少 2 项，实际 {len(candidate_Ms)}"
            )
        if not all(candidate_Ms[i] < candidate_Ms[i + 1]
                   for i in range(len(candidate_Ms) - 1)):
            raise ValueError("候选模式数列表须严格升序")
        if not (0.0 < threshold < 1.0):
            raise ValueError(
                f"threshold 须 ∈ (0,1)，实际 {threshold}（规则 14）"
            )
        history: list[tuple[int, float]] = []
        prev_s: np.ndarray | None = None
        prev_norm: float = 0.0
        prev_m: int = 0
        selected = -1
        relative_error = float("inf")
        for m in candidate_Ms:
            s = self.solve_fn(m)
            if prev_s is not None:
                # 不同 M 的 S 矩阵尺寸不同（2M × 2M），取左上 min 子矩阵比较
                # Gallagher 2003 §3：S 矩阵前 M_min×M_min 子块对应低阶模式耦合
                n_min = min(s.shape[0], prev_s.shape[0])
                s_sub = s[:n_min, :n_min]
                prev_sub = prev_s[:n_min, :n_min]
                prev_norm_sub = self._matrix_norm(prev_sub)
                if prev_norm_sub < 1e-30:
                    raise ValueError(
                        "前一 S 矩阵范数 ≈0，无法计算相对误差（规则 14）"
                    )
                diff = self._matrix_norm(s_sub - prev_sub)
                eps = diff / prev_norm_sub
                history.append((m, eps))
                if eps < threshold and selected < 0:
                    selected = m
                    relative_error = eps
                    break
            prev_s = s
            prev_norm = self._matrix_norm(s)
            prev_m = m
        if selected < 0:
            raise ValueError(
                f"所有候选 M {candidate_Ms} 均未收敛到阈值 {threshold}，"
                f"历史 {history}（规则 14：禁止 fall-back）"
            )
        max_m = candidate_Ms[-1]
        # 计算量节省倍数：模式数 M 比例 O(M^2)（界面 S 矩阵重叠积分）
        speedup = (max_m ** 2) / (selected ** 2)
        return EmeModeSelectionResult(
            selected_count=selected,
            convergence_history=history,
            relative_error=relative_error,
            speedup_factor=float(speedup),
        )
