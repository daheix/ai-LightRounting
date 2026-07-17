"""HOM 干涉（Hong-Ou-Mandel）模块 — 双光子量子干涉（与玻色采样紧密相关）。

Input-Process-Output 三段式文档
================================

**Input**:
- ``theta``: 可分辨性/时间延迟参数（θ=0 → 完全不可区分 → dip_depth=1.0）。

**Process**:
- 两个光子输入 50:50 分束器，高斯波包重叠模型（Hong-Ou-Mandel 1987）：

      overlap²(θ) = exp(-θ² / (2σ²))        σ=1 归一化波包宽度
      P_coinc(θ)  = 0.5 × (1 - overlap²(θ))  量子符合计数率
      dip_depth(θ) = overlap²(θ) = 1 - P_coinc/0.5   HOM dip 深度（可见度）

- 物理含义:
    θ=0  → 完全不可区分 → P_coinc=0,   dip_depth=1.0（HOM dip，量子干涉）
    θ→∞ → 完全可分辨   → P_coinc=0.5, dip_depth=0.0（经典极限）

**Output**:
- ``{coincidence_prob: float, dip_depth: float, verified: bool}``
  - coincidence_prob: 符合计数率 P_coinc(θ) ∈ [0, 0.5]。
  - dip_depth: HOM dip 深度 ∈ [0, 1]，θ=0 时为 1.0。
  - verified: 输出物理合法域校验（有限性 + 值域，非恒真，R390 标准）。

R03 合规: dip_depth 由模型实算，verified 校验输出物理合法域（非恒真）。
🚫不参与 GPU（R04）：纯 math 实现。

学术诚信（R02，≥5 文献 URL 溯源）:
- Hong, Ou, Mandel, "Measurement of subpicosecond time intervals between
  two photons by interference", PRL 59, 2044 (1987).
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Bouwmeester et al., "The Physics of Quantum Information", Springer 2000, §3.1
  URL: https://doi.org/10.1007/978-3-662-04209-0
- Sanaka et al., "Experimental non-classical interference without overlap
  in the time domain", PRA 64, 023817 (2001).
  URL: https://doi.org/10.1103/PhysRevA.64.023817
- Knill, Laflamme, Milburn, Nature 409, 46 (2001).
  URL: https://www.nature.com/articles/35051009
- Pan et al., "Experimental entanglement swapping", PRL 80, 3891 (1998).
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.80.3891
- Scarcelli et al., "HOM interference with independent photons",
  PRA 74, 033820 (2006). URL: https://doi.org/10.1103/PhysRevA.74.033820
"""

from __future__ import annotations

import math

# 经典（完全可分辨）符合计数率: 两个独立光子各 50% 概率走不同端口
_CLASSICAL_COINCIDENCE = 0.5
# 归一化高斯波包宽度平方（σ²=1）
_WAVEPACKET_SIGMA_SQ = 1.0


def hom_interference(theta: float = 0.0) -> dict:
    """HOM 干涉仿真，返回符合计数率、dip 深度与验证结果。

    两个光子输入 50:50 分束器，可分辨性参数 theta 控制干涉可见度。
    theta=0 → 完全不可区分 → 完全 HOM dip（dip_depth=1.0）。

    物理模型（高斯波包重叠，Hong-Ou-Mandel 1987）:
        overlap²(θ) = exp(-θ²/(2σ²))
        P_coinc(θ)  = 0.5 × (1 - overlap²(θ))
        dip_depth(θ) = overlap²(θ) = 1 - P_coinc/0.5

    来源: Hong, Ou, Mandel, PRL 59, 2044 (1987).
         URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

    Args:
        theta: 可分辨性/时间延迟参数（θ=0 → 完全不可区分 → dip_depth=1.0）。

    Returns:
        {coincidence_prob: float, dip_depth: float, verified: bool}
        - coincidence_prob: 符合计数率 P_coinc(θ) ∈ [0, 0.5]。
        - dip_depth: HOM dip 深度（可见度）∈ [0, 1]，θ=0 时为 1.0。
        - verified: 输出物理合法域校验（非恒真，见下方实现注释）。
    """
    overlap_sq = math.exp(-(theta * theta) / (2.0 * _WAVEPACKET_SIGMA_SQ))
    coincidence_prob = _CLASSICAL_COINCIDENCE * (1.0 - overlap_sq)
    dip_depth = overlap_sq  # = 1 - coincidence_prob / classical
    # R390 标准（与 klm/gates.py 对齐）: verified 必须是非恒真校验。
    # 原实现 abs(dip_depth - (1 - P/0.5)) < 1e-12 是代数恒等式（恒真，假验证），
    # 已删除。改为校验输出物理合法域：有限性 + 值域。θ=NaN 等非法输入
    # 会导致 exp 产生 NaN，值域比较对 NaN 恒 False → verified=False，
    # 真实反映模型输出合法性（R02 学术诚信 / R03 无假验证）。
    # 注: θ=±Inf 是合法极限（exp(-Inf)=0 → 经典极限 P=0.5, dip=0），
    # 输出仍在合法域内，verified=True。
    verified = (
        math.isfinite(coincidence_prob)
        and math.isfinite(dip_depth)
        and 0.0 <= coincidence_prob <= _CLASSICAL_COINCIDENCE
        and 0.0 <= dip_depth <= 1.0
    )
    return {
        "coincidence_prob": float(coincidence_prob),
        "dip_depth": float(dip_depth),
        "verified": bool(verified),
    }


__all__ = ["hom_interference"]
