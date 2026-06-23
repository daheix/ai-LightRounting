"""PoLaRIS AI 模块（AI 驱动逆向设计 + 强化学习）。

目录结构：
    polaris/ai/
        __init__.py            — 包入口，统一导出
        inverse_design.py      — R29 AI 驱动逆向设计（RL + GAN + Diffusion）

R29 交付：对齐 lumopt + Stanford GAN + MIT Diffusion 逆向设计 SOTA。
综合得分目标 8.75 → 8.85。

来源:
- Sutton & Barto 2018, Reinforcement Learning
  URL: http://incompleteideas.net/book/RLbook2020.pdf
- Liu et al., "Generative model for the inverse design of photonic nanodevices",
  Nanophotonics 2024, DOI: 10.1515/nanoph-2023-0683
- Liu et al., "PDN: A Diffusion Model for Photonic Device Inverse Design",
  arXiv:2407.03028, URL: https://arxiv.org/abs/2407.03028
"""

from polaris.ai.inverse_design import (
    DiffusionInverseDesignConfig,
    DiffusionInverseDesigner,
    GANInverseDesignConfig,
    GANInverseDesigner,
    InverseDesignEvaluator,
    RLInverseDesignConfig,
    RLInverseDesigner,
)

__all__ = [
    # R29 AI 驱动逆向设计
    "RLInverseDesignConfig",
    "RLInverseDesigner",
    "GANInverseDesignConfig",
    "GANInverseDesigner",
    "DiffusionInverseDesignConfig",
    "DiffusionInverseDesigner",
    "InverseDesignEvaluator",
]
