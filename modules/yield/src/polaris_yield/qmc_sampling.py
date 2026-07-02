"""准蒙特卡洛 (QMC) 采样框架（polaris-yield 子模块）。

从 v4 ``polaris.sim.qmc_sampling`` 迁移；R13 不保留 v4 兼容路径。

## 核心功能

1. ``generate_qmc_samples``: 拉丁超立方 / Sobol / Halton 准随机样本
2. ``transform_to_distribution``: 逆变换采样到目标分布
3. ``qmc_monte_carlo``: QMC 蒙特卡洛仿真（方差减少）
4. ``compare_qmc_convergence``: QMC vs 朴素 MC 收敛对比

## 学术依据（R02 学术诚信，≥5 文献 URL）

- McKay, Beckman & Conover 1979, "A Comparison of Three Methods for
  Selecting Values of Input Variables in the Analysis of Output from a
  Computer Code", Technometrics 21(2):239-245,
  https://doi.org/10.1080/00401706.1979.10489755
- Sobol 1967, "Distribution of points in a cube and approximate
  evaluation of integrals", USSR Comput. Math. Math. Phys. 7(4):86-112,
  https://doi.org/10.1016/0041-5553(67)90144-9
- Halton 1960, "On the efficiency of certain quasi-random sequences of
  points in evaluating multi-dimensional integrals",
  Numer. Math. 2:84-90, https://doi.org/10.1007/BF01386213
- Niederreiter 1992, "Random Number Generation and Quasi-Monte Carlo
  Methods", SIAM, https://doi.org/10.1137/1.9781611970081
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer, https://doi.org/10.1007/978-0-387-21617-1
- SciPy QMC: https://docs.scipy.org/doc/scipy/reference/stats.qmc.html

合规: R02 / R03 / R04 / R09。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.stats import norm, qmc, uniform

logger = logging.getLogger(__name__)


class QMCSamplerType(Enum):
    """QMC 采样器类型。

    对标商业工具:
    - Lumerical INTERCONNECT: Monte Carlo with LHS option
    - Luceda Circuit Analyzer: QMC sampling
    - Calibre YieldOptimizer: LHS / Sobol / Halton
    """

    LATIN_HYPERCUBE = "latin_hypercube"
    SOBOL = "sobol"
    HALTON = "halton"


@dataclass
class QMCSampleResult:
    """QMC 采样结果。

    Attributes:
        samples: 样本数组 (n_samples, d)，值域 [0, 1]。
        sampler_type: 采样器类型。
        n_samples: 样本数。
        n_dimensions: 维度数。
        discrepancy: 星偏差 (star discrepancy)。
        seed: 随机种子。
    """

    samples: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    sampler_type: QMCSamplerType = QMCSamplerType.SOBOL
    n_samples: int = 0
    n_dimensions: int = 0
    discrepancy: float = 0.0
    seed: int | None = None


@dataclass
class QMCMonteCarloResult:
    """QMC 蒙特卡洛仿真结果。

    Attributes:
        outputs: 仿真输出数组 (n_samples,)。
        mean: 输出均值。
        std: 输出标准差。
        n_samples: 样本数。
        sampler_type: 采样器类型。
        n_evaluations: 总模型评估次数。
        discrepancy: 采样星偏差。
    """

    outputs: np.ndarray = field(default_factory=lambda: np.empty(0))
    mean: float = 0.0
    std: float = 0.0
    n_samples: int = 0
    sampler_type: QMCSamplerType = QMCSamplerType.SOBOL
    n_evaluations: int = 0
    discrepancy: float = 0.0


def generate_qmc_samples(
    n_samples: int,
    n_dimensions: int,
    sampler_type: QMCSamplerType = QMCSamplerType.SOBOL,
    seed: int | None = None,
) -> QMCSampleResult:
    """生成 QMC 准随机样本。

    Args:
        n_samples: 样本数（Sobol 必须为 2 的幂）。
        n_dimensions: 维度数 d。
        sampler_type: 采样器类型。
        seed: 随机种子。

    Returns:
        QMCSampleResult。

    Raises:
        ValueError: n_samples <= 0 / n_dimensions <= 0 / Sobol 类型非 2 幂。
        RuntimeError: SciPy QMC 采样失败。

    学术依据:
    - LHS: McKay et al. 1979, DOI: 10.1080/00401706.1979.10489755
    - Sobol 序列: Sobol 1967
    - Halton 序列: Halton 1960
    """
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if n_dimensions <= 0:
        raise ValueError(f"n_dimensions 必须 > 0，得到 {n_dimensions}")

    if sampler_type == QMCSamplerType.SOBOL:
        if (n_samples & (n_samples - 1)) != 0:
            raise ValueError(
                f"Sobol 采样器要求 n_samples 为 2 的幂，得到 {n_samples}。"
                f"建议: 128, 256, 512, 1024, 2048, 4096。"
            )

    try:
        if sampler_type == QMCSamplerType.LATIN_HYPERCUBE:
            sampler = qmc.LatinHypercube(d=n_dimensions, seed=seed)
            samples = sampler.random(n=n_samples)
        elif sampler_type == QMCSamplerType.SOBOL:
            m = int(np.log2(n_samples))
            sampler = qmc.Sobol(d=n_dimensions, seed=seed)
            samples = sampler.random_base2(m=m)
        elif sampler_type == QMCSamplerType.HALTON:
            sampler = qmc.Halton(d=n_dimensions, seed=seed)
            samples = sampler.random(n=n_samples)
        else:
            raise ValueError(f"不支持的采样器类型: {sampler_type}")
    except Exception as e:
        raise RuntimeError(
            f"SciPy QMC 采样失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    try:
        disc = float(qmc.discrepancy(samples))
    except Exception as e:
        raise RuntimeError(
            f"星偏差计算失败: {type(e).__name__}: {e}。禁止 fall-back。"
        ) from e

    return QMCSampleResult(
        samples=samples,
        sampler_type=sampler_type,
        n_samples=int(samples.shape[0]),
        n_dimensions=n_dimensions,
        discrepancy=disc,
        seed=seed,
    )


def transform_to_distribution(
    uniform_samples: np.ndarray,
    distributions: list[dict],
) -> np.ndarray:
    """将 [0,1] 均匀样本转换为目标分布（逆变换采样 X = F⁻¹(U)）。

    Args:
        uniform_samples: 均匀样本 (n_samples, d)，值域 [0, 1]。
        distributions: 目标分布规格列表。

    Returns:
        转换后的样本 (n_samples, d)。

    Raises:
        ValueError: 分布规格无效或维度不匹配。

    学术依据: https://en.wikipedia.org/wiki/Inverse_transform_sampling
    """
    uniform_samples = np.asarray(uniform_samples, dtype=float)
    if uniform_samples.ndim != 2:
        raise ValueError(
            f"uniform_samples 必须为 2D 数组 (n_samples, d)，"
            f"得到 shape {uniform_samples.shape}"
        )
    n, d = uniform_samples.shape
    if len(distributions) != d:
        raise ValueError(
            f"distributions 长度 {len(distributions)} 与样本维度 {d} 不匹配"
        )

    transformed = np.empty_like(uniform_samples)
    for j in range(d):
        spec = distributions[j]
        dist_type = spec.get("type", "")
        u = np.clip(uniform_samples[:, j], 1e-10, 1.0 - 1e-10)
        if dist_type == "norm":
            dist = norm(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
            transformed[:, j] = dist.ppf(u)
        elif dist_type == "uniform":
            loc = spec.get("loc", 0.0)
            scale = spec.get("scale", 1.0)
            dist = uniform(loc=loc, scale=scale)
            transformed[:, j] = dist.ppf(u)
        else:
            raise ValueError(
                f"不支持的分布类型: '{dist_type}'。支持: 'norm', 'uniform'。"
            )
    return transformed


def qmc_monte_carlo(
    func: Callable[[np.ndarray], float],
    n_samples: int,
    distributions: list[dict],
    sampler_type: QMCSamplerType = QMCSamplerType.SOBOL,
    seed: int | None = None,
) -> QMCMonteCarloResult:
    """QMC 蒙特卡洛仿真。

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar。
        n_samples: 样本数（Sobol 必须为 2 的幂）。
        distributions: 参数分布规格列表。
        sampler_type: 采样器类型。
        seed: 随机种子。

    Returns:
        QMCMonteCarloResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: QMC 采样或仿真失败。

    学术依据: Niederreiter 1992, DOI: 10.1137/1.9781611970081
    """
    d = len(distributions)
    if d == 0:
        raise ValueError("distributions 不能为空")

    sample_result = generate_qmc_samples(
        n_samples=n_samples,
        n_dimensions=d,
        sampler_type=sampler_type,
        seed=seed,
    )

    transformed = transform_to_distribution(
        uniform_samples=sample_result.samples,
        distributions=distributions,
    )

    outputs = np.empty(sample_result.n_samples, dtype=float)
    for i in range(sample_result.n_samples):
        try:
            outputs[i] = float(func(transformed[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（R03）。"
            ) from e

    return QMCMonteCarloResult(
        outputs=outputs,
        mean=float(np.mean(outputs)),
        std=(
            float(np.std(outputs, ddof=1))
            if sample_result.n_samples > 1
            else 0.0
        ),
        n_samples=sample_result.n_samples,
        sampler_type=sampler_type,
        n_evaluations=sample_result.n_samples,
        discrepancy=sample_result.discrepancy,
    )


@dataclass
class QMCConvergenceComparison:
    """QMC vs 朴素 MC 收敛对比结果。

    Attributes:
        sample_sizes: 样本数序列。
        mc_errors: 朴素 MC 在各样本数的相对误差。
        qmc_errors: QMC 在各样本数的相对误差。
        true_value: 真值。
        sampler_type: QMC 采样器类型。
        mc_final_error: 朴素 MC 最终误差。
        qmc_final_error: QMC 最终误差。
        speedup_factor: 加速因子 = mc_final_error / qmc_final_error。
    """

    sample_sizes: list[int] = field(default_factory=list)
    mc_errors: list[float] = field(default_factory=list)
    qmc_errors: list[float] = field(default_factory=list)
    true_value: float = 0.0
    sampler_type: QMCSamplerType = QMCSamplerType.SOBOL
    mc_final_error: float = 0.0
    qmc_final_error: float = 0.0
    speedup_factor: float = 0.0


def _mc_sample_naive(
    rng: np.random.Generator,
    distributions: list[dict],
    n: int,
    d: int,
) -> np.ndarray:
    """朴素 MC i.i.d. 采样（内部辅助）。"""
    samples = np.empty((n, d))
    for j in range(d):
        spec = distributions[j]
        if spec.get("type") == "norm":
            samples[:, j] = rng.normal(
                loc=spec.get("loc", 0.0),
                scale=spec.get("scale", 1.0),
                size=n,
            )
        elif spec.get("type") == "uniform":
            samples[:, j] = rng.uniform(
                low=spec.get("loc", 0.0),
                high=spec.get("loc", 0.0) + spec.get("scale", 1.0),
                size=n,
            )
        else:
            raise ValueError(f"不支持的分布类型: '{spec.get('type')}'")
    return samples


def _relative_error(estimate: float, true_value: float) -> float:
    """相对误差（true_value=0 时退化为绝对误差）。"""
    if true_value != 0:
        return abs(estimate - true_value) / abs(true_value)
    return abs(estimate - true_value)


def compare_qmc_convergence(
    func: Callable[[np.ndarray], float],
    distributions: list[dict],
    true_value: float,
    sample_sizes: list[int],
    sampler_type: QMCSamplerType = QMCSamplerType.SOBOL,
    seed: int | None = None,
) -> QMCConvergenceComparison:
    """对比 QMC 与朴素 MC 的收敛速率。

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar。
        distributions: 参数分布规格列表。
        true_value: 真值。
        sample_sizes: 样本数列表。
        sampler_type: QMC 采样器类型。
        seed: 随机种子。

    Returns:
        QMCConvergenceComparison。

    Raises:
        ValueError: 参数无效。

    学术依据: Glasserman 2003, Ch.5 (方差减少技术对比)
    """
    d = len(distributions)
    if d == 0:
        raise ValueError("distributions 不能为空")
    if not sample_sizes:
        raise ValueError("sample_sizes 不能为空")

    rng = np.random.default_rng(seed)
    mc_errors: list[float] = []
    qmc_errors: list[float] = []

    for n in sample_sizes:
        mc_samples = _mc_sample_naive(rng, distributions, n, d)
        mc_outputs = np.array(
            [float(func(mc_samples[i])) for i in range(n)]
        )
        mc_mean = float(np.mean(mc_outputs))
        mc_errors.append(_relative_error(mc_mean, true_value))

        qmc_result = qmc_monte_carlo(
            func=func,
            n_samples=n,
            distributions=distributions,
            sampler_type=sampler_type,
            seed=seed,
        )
        qmc_errors.append(_relative_error(qmc_result.mean, true_value))

    mc_final = mc_errors[-1]
    qmc_final = qmc_errors[-1]
    speedup = mc_final / qmc_final if qmc_final > 0 else float("inf")

    return QMCConvergenceComparison(
        sample_sizes=list(sample_sizes),
        mc_errors=mc_errors,
        qmc_errors=qmc_errors,
        true_value=true_value,
        sampler_type=sampler_type,
        mc_final_error=mc_final,
        qmc_final_error=qmc_final,
        speedup_factor=speedup,
    )


__all__ = [
    "QMCConvergenceComparison",
    "QMCMonteCarloResult",
    "QMCSampleResult",
    "QMCSamplerType",
    "compare_qmc_convergence",
    "generate_qmc_samples",
    "qmc_monte_carlo",
    "transform_to_distribution",
]
