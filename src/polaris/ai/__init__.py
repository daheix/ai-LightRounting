"""PoLaRIS AI 模块（AI 驱动逆向设计 + 强化学习）。

目录结构：
    polaris/ai/
        __init__.py            — 包入口，统一导出
        inverse_design.py      — R29 AI 驱动逆向设计（RL + GAN + Diffusion）
        pdk_device_sampler.py  — 真实 SiEPIC EBeam PDK 器件采样（Bug #v3.3-AI-6）

R29 交付：对齐 lumopt + Stanford GAN + MIT Diffusion 逆向设计 SOTA。
综合得分目标 8.75 → 8.85。

Bug #v3.3-AI-6 修复: GAN/Diffusion 训练数据改用真实 SiEPIC PDK 器件，
禁止 np.random 合成数据 fall-back（R03）。

来源:
- Sutton & Barto 2018, Reinforcement Learning
  URL: http://incompleteideas.net/book/RLbook2020.pdf
- Liu et al., "Generative model for the inverse design of photonic nanodevices",
  Nanophotonics 2024, DOI: 10.1515/nanoph-2023-0683
- Liu et al., "PDN: A Diffusion Model for Photonic Device Inverse Design",
  arXiv:2407.03028, URL: https://arxiv.org/abs/2407.03028
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from polaris.ai.inverse_design import (
    DiffusionInverseDesignConfig,
    DiffusionInverseDesigner,
    GANInverseDesignConfig,
    GANInverseDesigner,
    InverseDesignEvaluator,
    PDKDeviceSampler,
    RLInverseDesignConfig,
    RLInverseDesigner,
)
from polaris.ai.pdk_device_sampler import PDKDevice

__all__ = [
    # R29 AI 驱动逆向设计
    "RLInverseDesignConfig",
    "RLInverseDesigner",
    "GANInverseDesignConfig",
    "GANInverseDesigner",
    "DiffusionInverseDesignConfig",
    "DiffusionInverseDesigner",
    "InverseDesignEvaluator",
    # Bug #v3.3-AI-6: 真实 SiEPIC PDK 器件采样
    "PDKDevice",
    "PDKDeviceSampler",
]
