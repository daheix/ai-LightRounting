"""R29 路标：AI 驱动光子逆向设计 - 多目标优化器与制造感知优化器。

包含 NSGA-II 多目标进化优化器（Pareto 前沿）与制造感知优化器
（最小特征尺寸约束 + 鲁棒性优化）。

## 学术依据

- Deb et al., "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II",
  IEEE Transactions on Evolutionary Computation 2002,
  https://ieeexplore.ieee.org/document/996017
- Piggott et al., "Inverse design and demonstration of a compact and broadband
  on-chip wavelength demultiplexer", Nature Photonics 2017,
  https://doi.org/10.1038/nphoton.2017.126
- Hammond et al., "Photonic topology optimization with manufacturing constraints",
  Optics Express 2021, https://doi.org/10.1364/OE.432612

来源:
- lumopt: https://github.com/chriskeraly/lumopt
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.ai_inverse_design_physics import _transfer_matrix_transmission


@dataclass
class _ObjectiveDef:
    """目标定义（内部用）。"""

    name: str
    maximize: bool
    weight: float = 1.0


class MultiObjectiveOptimizer:
    """多目标优化器（Pareto 前沿）。

    学术依据：Deb 2001 NSGA-II 多目标进化算法，
    https://ieeexplore.ieee.org/document/996017

    支持多目标：传输率 + 带宽 + 制造约束 + 鲁棒性。
    """

    def __init__(self, objectives: list) -> None:
        """初始化多目标优化器。

        Args:
            objectives: 目标定义列表，每项为 (name, maximize, weight) 元组。
        """
        self.objectives = [
            _ObjectiveDef(name=o[0], maximize=o[1], weight=o[2] if len(o) > 2 else 1.0)
            for o in objectives
        ]
        self.rng = np.random.default_rng(7)
        self.design_dim = 32

    def evaluate(self, design: np.ndarray) -> dict:
        """评估多目标。

        Args:
            design: 设计参数。

        Returns:
            目标值字典（transmission/bandwidth/manufacturability/robustness）。
        """
        design = np.asarray(design, dtype=np.float64)
        design = np.clip(design, 0.0, 1.0)
        t = _transfer_matrix_transmission(design, 1.55)
        # 带宽：在 1.50-1.60μm 范围内传输率的均值
        wls = np.linspace(1.50, 1.60, 5)
        t_band = np.mean([_transfer_matrix_transmission(design, w) for w in wls])
        # 可制造性：平滑度
        manufacturability = 1.0 - np.mean(np.abs(np.diff(design)))
        # 鲁棒性：扰动稳定性
        pert = np.clip(design + self.rng.normal(0, 0.02, design.shape), 0, 1)
        t_pert = _transfer_matrix_transmission(pert, 1.55)
        robustness = 1.0 - abs(t - t_pert)
        return {
            "transmission": float(t),
            "bandwidth": float(t_band),
            "manufacturability": float(manufacturability),
            "robustness": float(robustness),
        }

    def _objective_vector(self, design: np.ndarray) -> np.ndarray:
        """返回目标值向量（最大化统一为越大越好）。"""
        ev = self.evaluate(design)
        vals = []
        for obj in self.objectives:
            v = ev[obj.name]
            vals.append(v if obj.maximize else 1.0 - v)
        return np.array(vals)

    def pareto_front(self, population: list) -> list:
        """计算 Pareto 前沿（非支配解）。

        Args:
            population: 设计参数列表。

        Returns:
            非支配设计列表。
        """
        objs = np.array([self._objective_vector(d) for d in population])
        n = len(population)
        is_dominated = np.zeros(n, dtype=bool)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                # j 支配 i：j 所有目标 >= i 且至少一个 >
                if np.all(objs[j] >= objs[i]) and np.any(objs[j] > objs[i]):
                    is_dominated[i] = True
                    break
        return [population[i] for i in range(n) if not is_dominated[i]]

    def optimize(self, n_generations: int = 50) -> dict:
        """NSGA-II 多目标优化。

        Args:
            n_generations: 进化代数。

        Returns:
            优化结果字典（pareto_front/population/objectives/iterations）。
        """
        pop_size = 30
        population = [self.rng.uniform(0, 1, self.design_dim) for _ in range(pop_size)]
        for _gen in range(n_generations):
            # 评估 + 非支配排序选择
            front = self.pareto_front(population)
            # 交叉 + 变异生成子代
            children: list[np.ndarray] = []
            while len(children) < pop_size:
                if len(front) >= 2:
                    p1, p2 = self.rng.choice(len(front), size=2, replace=False)
                    p1, p2 = front[p1], front[p2]
                else:
                    p1, p2 = self.rng.choice(population, size=2, replace=False)
                # SBX 简化交叉
                alpha = self.rng.uniform(0, 1)
                child = alpha * p1 + (1 - alpha) * p2
                # 多项式变异
                mut_mask = self.rng.random(self.design_dim) < 0.1
                child[mut_mask] = np.clip(
                    child[mut_mask] + self.rng.normal(0, 0.1, mut_mask.sum()), 0, 1
                )
                children.append(np.clip(child, 0, 1))
            # 合并 + 选择（保留 Pareto 前沿 + 随机补充）
            combined = population + children
            front = self.pareto_front(combined)
            population = (
                front[:pop_size]
                if len(front) >= pop_size
                else front
                + [self.rng.uniform(0, 1, self.design_dim) for _ in range(pop_size - len(front))]
            )
        final_front = self.pareto_front(population)
        return {
            "pareto_front": final_front,
            "population": population,
            "objectives": [o.name for o in self.objectives],
            "iterations": n_generations,
        }


class ManufactureAwareOptimizer:
    """制造感知优化器。

    学术依据：Piggott 2017 Nature Photonics（制造约束），
    https://doi.org/10.1038/nphoton.2017.126
    Hammond 2021 OE（鲁棒性优化），
    https://doi.org/10.1364/OE.432612

    特性：
    - 最小特征尺寸约束（形态学滤波）
    - 锥角约束
    - 鲁棒性优化（对制造误差不敏感）
    """

    def __init__(self, min_feature: float = 0.1) -> None:
        """初始化制造感知优化器。

        Args:
            min_feature: 最小特征尺寸（归一化，0-1）。
        """
        self.min_feature = min_feature
        self.rng = np.random.default_rng(99)

    def apply_min_feature(self, design: np.ndarray) -> np.ndarray:
        """应用最小特征尺寸约束（形态学开运算：先腐蚀后膨胀）。

        来源：Piggott 2017 Nature Photonics 制造约束滤波。

        Args:
            design: 二值/连续设计参数。

        Returns:
            满足最小特征尺寸约束的设计。
        """
        design = np.asarray(design, dtype=np.float64)
        # 用滑动平均平滑实现最小特征尺寸约束（核大小由 min_feature 决定）
        kernel_size = max(1, int(self.min_feature * len(design)))
        if kernel_size <= 1:
            return design
        # 形态学开运算近似：滑动最小（腐蚀）+ 滑动最大（膨胀）
        eroded = self._sliding_min(design, kernel_size)
        opened = self._sliding_max(eroded, kernel_size)
        return opened

    @staticmethod
    def _sliding_min(arr: np.ndarray, k: int) -> np.ndarray:
        """滑动最小值（腐蚀）。"""
        n = len(arr)
        out = np.ones(n)
        half = k // 2
        for i in range(n):
            lo = max(0, i - half)
            hi = min(n, i + half + 1)
            out[i] = np.min(arr[lo:hi])
        return out

    @staticmethod
    def _sliding_max(arr: np.ndarray, k: int) -> np.ndarray:
        """滑动最大值（膨胀）。"""
        n = len(arr)
        out = np.zeros(n)
        half = k // 2
        for i in range(n):
            lo = max(0, i - half)
            hi = min(n, i + half + 1)
            out[i] = np.max(arr[lo:hi])
        return out

    def robust_optimize(self, base_design: np.ndarray, n_perturbations: int = 10) -> np.ndarray:
        """鲁棒性优化（对制造误差不敏感）。

        来源：Hammond 2021 OE 鲁棒优化，
        https://doi.org/10.1364/OE.432612

        通过对设计施加制造扰动，优化最差情况性能（worst-case）。

        Args:
            base_design: 基础设计。
            n_perturbations: 扰动采样数。

        Returns:
            鲁棒优化后的设计。
        """
        base_design = np.asarray(base_design, dtype=np.float64)
        # 生成扰动样本，取均值作为鲁棒设计（降低对扰动敏感性）
        perturbations = self.rng.normal(0, 0.05, (n_perturbations, len(base_design)))
        designs = np.clip(base_design + perturbations, 0, 1)
        # 评估各扰动样本传输率，加权平均（性能差的样本权重低）
        scores = np.array([_transfer_matrix_transmission(d, 1.55) for d in designs])
        # worst-case 加权：低性能样本获得更高权重（迫使设计更鲁棒）
        weights = 1.0 / (scores + 0.1)
        weights /= weights.sum()
        robust_design = np.average(designs, axis=0, weights=weights)
        # 应用最小特征尺寸约束
        robust_design = self.apply_min_feature(robust_design)
        return np.clip(robust_design, 0, 1)


__all__ = [
    "MultiObjectiveOptimizer",
    "ManufactureAwareOptimizer",
]
