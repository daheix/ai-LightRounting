"""亚像素材料界面平滑（A09 §11，Yu-Mittra 2001 共形建模法）。

阶梯法（staircasing）将材料按 Yee 单元硬归类，弯曲/倾斜界面被近似为锯齿，
引入 O(Δh) 几何误差，使器件 S 参数/反射率对网格平移高度敏感。亚像素平滑
（subpixel smoothing）在每 Yee 单元内对材料做子网格体积平均，将界面几何
误差降至 O(Δh²)，与 leapfrog 时间二阶精度匹配（Taflove 2005 §6.7）。

本模块提供三类 ε_r 平滑（均向量化，纯 NumPy）：
- volume  : 体积（线性）平均 ε_eff = Σₖ fₖ·εₖ
            适用于切向 E 分量（2D TEz 的 E_z 位于界面切向）。
- harmonic: 谐波平均 1/ε_eff = Σₖ fₖ/εₖ
            适用于法向 E 分量（界面处 D_n 连续 ⇒ 1/ε 调和平均）。
- conformal: Yu-Mittra 共形法（介质/PEC 界面）。
            E 在 PEC 内为 0，安培面积分 ∬εE·dS = ε_diel·E·A_diel，
            故 ε_eff = ε_diel·f_diel（f_diel 为介质体积分数）。
            完全 PEC 单元 ε_eff 退化为 0（E 强制为 0，ε 物理上无关），
            此处保留 ε_diel 作占位并返回 pec_fraction=1 供调用方强制 PEC。

实现：细网格 (Nx·L, Ny·L) 按 L×L 子块 reshape 为 (Nx, L, Ny, L)，
沿子块轴求和/均值，复杂度 O(N) 一次完成，无逐元素循环（§4）。
 reshape 平均是 SciPy/NumPy 推荐的标准块降采样法
（https://numpy.org/doc/stable/reference/generated/numpy.reshape.html）。

*创新*：将三种平滑统一为“子块 reshape + 分轴聚合”单一代码路径，
仅聚合算子（mean / 1/mean倒数 / 加权介质分数）不同，避免重复 reshape。
- 底层逻辑：体积平均 = 子块 ε 均值；谐波 = 子块 1/ε 均值再倒数；
  共形 = 子块介质 ε 均值 × 介质子格占比。
- 支持理论：Yu & Mittra 2001 证明共形法使弯曲界面反射误差从 O(Δh) 降至
  O(Δh²)；Mohammadi 2005 给出 2D TEz 轮廓路径有效 ε 的相同结论。
- 案例：SOI 波导芯/包层界面平滑（M4 S 参数）、金属膜边缘（M3 反射率）。

文献来源（≥5，规则 18 学术诚信）：
1. Yu W, Mittra R, "A conformal FDTD technique for modeling curved dielectric
   surfaces," IEEE Microw. Wirel. Compon. Lett. 11(1) 25-27 (2001) —
   https://doi.org/10.1109/7260.905957
2. Taflove & Hagness 2005 Computational Electrodynamics §6.7（共形/子单元）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
3. Mohammadi A, Nadgaran H, Agio M, "Contour-path effective permittivities for
   the 2D FDTD method," Opt. Express 13(26) 10367-10381 (2005) —
   https://doi.org/10.1364/OPEX.13.010367
4. Lumerical conformal mesh 文档（Yu-Mittra method 1 工业实现）—
   https://optics.ansys.com/hc/en-us/articles/360034382594
5. MEEP Subpixel Smoothing（介质体积平均开源实现）—
   https://meep.readthedocs.io/en/latest/Subpixel_Smoothing/
6. Gedney SD, "Advanced Time Domain Modeling" ch.2 §2.5（subcell/conformal）—
   https://doi.org/10.1049/SBEW550E_ch2
7. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693

规则依据：规则 14（非法输入 raise，无 fall-back）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化，无逐元素循环）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "SubpixelConfig",
    "block_average",
    "volume_average_permittivity",
    "harmonic_average_permittivity",
    "conformal_permittivity",
    "smooth_permittivity",
]

# 支持的平滑方法
_METHODS: frozenset[str] = frozenset({"volume", "harmonic", "conformal"})


@dataclass(frozen=True)
class SubpixelConfig:
    """亚像素平滑参数（A09 §11）。

    Attributes:
        levels: 每方向子采样数 L，每个 Yee 单元划分为 L×L 子格，≥1。
            L=1 等价于不平滑（直接取细网格已对齐值）。
        method: 平滑方法，'volume'（切向 E 体积平均，默认）/
            'harmonic'（法向 E 谐波平均）/'conformal'（Yu-Mittra 共形）。
    """

    levels: int = 2
    method: str = "volume"

    def __post_init__(self) -> None:
        if self.levels < 1:
            raise ValueError(f"levels 须 ≥1，实际 {self.levels}")
        if self.method not in _METHODS:
            raise ValueError(f"method 须 ∈ {sorted(_METHODS)}，实际 '{self.method}'")


def _coarse_shape(fine_shape: tuple[int, int], levels: int) -> tuple[int, int]:
    """由细网格形状与子采样数推得粗网格形状，校验整除性。"""
    nx_f, ny_f = fine_shape
    if nx_f % levels != 0 or ny_f % levels != 0:
        raise ValueError(f"细网格 {fine_shape} 须被 levels={levels} 整除（每方向）")
    return nx_f // levels, ny_f // levels


def _reshape_blocks(arr_fine: np.ndarray, levels: int) -> np.ndarray:
    """将 (Nx·L, Ny·L) 细数组 reshape 为 (Nx, L, Ny, L) 子块视图（无拷贝）。"""
    nx, ny = _coarse_shape(arr_fine.shape, levels)
    return arr_fine[: nx * levels, : ny * levels].reshape(nx, levels, ny, levels)


def block_average(arr_fine: np.ndarray, levels: int) -> np.ndarray:
    """通用块均值降采样：(N·L, M·L) → (N, M)。

    对 L×L 子块取算术平均，适用于任意标量场（如折射率、掩码占比）。

    Args:
        arr_fine: 细网格数组 (Nx·L, Ny·L)。
        levels: 子采样数 L，≥1。

    Returns:
        粗网格均值数组 (Nx, Ny)。

    Raises:
        ValueError: levels 非正或细网格不被整除（规则 14）。
    """
    if levels < 1:
        raise ValueError(f"levels 须 ≥1，实际 {levels}")
    blocks = _reshape_blocks(np.asarray(arr_fine, dtype=np.float64), levels)
    return blocks.mean(axis=(1, 3))


def volume_average_permittivity(eps_r_fine: np.ndarray, levels: int) -> np.ndarray:
    """体积（线性）平均 ε_r —— 切向 E 分量亚像素平滑。

    ε_eff = Σₖ fₖ·εₖ = (1/L²)·Σ_{子格} ε_sub

    物理依据：界面切向 E 连续，平均 D_t = ⟨ε⟩·E_t，故 ε_eff 取体积平均
    （Mohammadi 2005 / MEEP subpixel 默认对角项）。使弯曲界面误差 O(Δh)→O(Δh²)。

    Args:
        eps_r_fine: 细网格相对介电常数 (Nx·L, Ny·L)，须 >0。
        levels: 子采样数 L，≥1。

    Returns:
        粗网格体积平均 ε_eff (Nx, Ny)，>0。

    Raises:
        ValueError: ε 非正或形状不整除（规则 14）。
    """
    eps = np.asarray(eps_r_fine, dtype=np.float64)
    if np.any(eps <= 0.0):
        raise ValueError("eps_r_fine 须严格为正（介质折射率平方）")
    blocks = _reshape_blocks(eps, levels)
    eps_coarse = blocks.mean(axis=(1, 3))
    # 浮点求和可能产生微小负值，此处 ε 已校验 >0，均值必 >0；仍断言防退化
    if np.any(eps_coarse <= 0.0):
        raise RuntimeError("体积平均产生非正 ε，输入数据异常")
    return eps_coarse


def harmonic_average_permittivity(eps_r_fine: np.ndarray, levels: int) -> np.ndarray:
    """谐波平均 ε_r —— 法向 E 分量亚像素平滑。

    1/ε_eff = Σₖ fₖ/εₖ = (1/L²)·Σ_{子格} 1/ε_sub  ⇒  ε_eff = 1/⟨1/ε⟩

    物理依据：界面法向 D_n 连续 ⇒ E_n = D_n/ε 分段，平均 E_n = D_n·⟨1/ε⟩，
    故 ε_eff 取调和平均（Taflove 2005 §6.7 法向分量）。对高对比度法向界面
    精度优于体积平均。

    Args:
        eps_r_fine: 细网格相对介电常数 (Nx·L, Ny·L)，须 >0。
        levels: 子采样数 L，≥1。

    Returns:
        粗网格谐波平均 ε_eff (Nx, Ny)，>0。

    Raises:
        ValueError: ε 非正或形状不整除（规则 14）。
    """
    eps = np.asarray(eps_r_fine, dtype=np.float64)
    if np.any(eps <= 0.0):
        raise ValueError("eps_r_fine 须严格为正")
    blocks = _reshape_blocks(eps, levels)
    inv_mean = (1.0 / blocks).mean(axis=(1, 3))
    eps_coarse = 1.0 / inv_mean
    if np.any(eps_coarse <= 0.0) or not np.all(np.isfinite(eps_coarse)):
        raise RuntimeError("谐波平均产生非正/非有限 ε，输入数据异常")
    return eps_coarse


def conformal_permittivity(
    eps_r_fine: np.ndarray,
    pec_mask_fine: np.ndarray,
    levels: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Yu-Mittra 共形平滑（介质/PEC 界面，A09 §11）。

    对含 PEC 的 Yee 单元，E 在 PEC 内为 0，安培面积分：
        ∬_cell ε·E·dS = ε_diel·E·A_diel  ⇒  ε_eff = ε_diel·f_diel
    其中 f_diel = (介质子格数)/(L²)。完全 PEC 单元 f_diel=0 → ε_eff=0，
    此时 E 物理上为 0（由调用方据 pec_fraction 强制），ε 值无关；
    本函数对完全 PEC 单元保留 ε_diel 作占位（>0，满足 YeeGrid ε>0 约束），
    并通过 pec_fraction=1 标记，供调用方施加 PEC 边界（E=0）。

    纯介质单元（pec_fraction=0）退化为体积平均 ε_eff = ⟨ε_diel⟩。

    Args:
        eps_r_fine: 细网格介质相对介电常数 (Nx·L, Ny·L)，PEC 区域内可为
            任意 >0 值（占位，仅介质子格参与平均）。须 >0。
        pec_mask_fine: 细网格 PEC 掩码 (Nx·L, Ny·L)，bool，True=PEC。
        levels: 子采样数 L，≥1。

    Returns:
        (eps_coarse, pec_fraction):
        - eps_coarse: 共形 ε_eff (Nx, Ny)，>0（完全 PEC 单元为占位介质 ε）。
        - pec_fraction: 粗网格 PEC 体积占比 (Nx, Ny) ∈ [0,1]，
          =1 表示完全 PEC（需调用方强制 E=0）。

    Raises:
        ValueError: ε 非正、掩码非布尔形状不符、形状不整除（规则 14）。
    """
    eps = np.asarray(eps_r_fine, dtype=np.float64)
    if eps.shape != pec_mask_fine.shape:
        raise ValueError(
            f"eps_r_fine 形状 {eps.shape} 与 pec_mask_fine {pec_mask_fine.shape} 不匹配"
        )
    if np.any(eps <= 0.0):
        raise ValueError("eps_r_fine 须严格为正")
    pec = np.asarray(pec_mask_fine, dtype=bool)
    eps_blk = _reshape_blocks(eps, levels)  # (Nx, L, Ny, L)
    pec_blk = _reshape_blocks(pec, levels)
    n_total = float(levels * levels)
    n_pec = pec_blk.sum(axis=(1, 3)).astype(np.float64)
    n_diel = n_total - n_pec
    pec_fraction = n_pec / n_total
    f_diel = n_diel / n_total
    # 介质子格 ε 均值（仅非 PEC 子格）；完全 PEC 单元用整体均值占位
    eps_sum = eps_blk.sum(axis=(1, 3))
    eps_diel_avg = np.where(
        n_diel > 0.0,
        np.divide(
            eps_sum - (eps_blk * pec_blk).sum(axis=(1, 3)),
            n_diel,
            out=eps_sum.copy(),
            where=n_diel > 0.0,
        ),
        eps_sum / n_total,  # 完全 PEC：占位（任意 >0），pec_fraction=1 标记
    )
    eps_coarse = eps_diel_avg * f_diel
    # 完全 PEC：f_diel=0 → eps=0，用介质均值占位（E 将被强制 0）
    full_pec = pec_fraction >= 1.0
    eps_coarse = np.where(full_pec, eps_diel_avg, eps_coarse)
    if np.any(eps_coarse <= 0.0) or not np.all(np.isfinite(eps_coarse)):
        raise RuntimeError("共形平滑产生非正/非有限 ε，输入数据异常")
    return eps_coarse, pec_fraction


def smooth_permittivity(
    eps_r_fine: np.ndarray,
    levels: int,
    method: str = "volume",
    pec_mask_fine: np.ndarray | None = None,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """亚像素平滑统一入口（按 method 分发，A09 §11）。

    Args:
        eps_r_fine: 细网格相对介电常数 (Nx·L, Ny·L)，>0。
        levels: 子采样数 L，≥1。
        method: 'volume' / 'harmonic' / 'conformal'。
        pec_mask_fine: PEC 掩码，仅 method='conformal' 时必填。

    Returns:
        - volume/harmonic: 粗网格 ε_eff (Nx, Ny)。
        - conformal: (eps_coarse, pec_fraction) 二元组。

    Raises:
        ValueError: method 非法或 conformal 缺掩码（规则 14，无 fall-back）。
    """
    if method not in _METHODS:
        raise ValueError(f"method 须 ∈ {sorted(_METHODS)}，实际 '{method}'")
    if method == "volume":
        return volume_average_permittivity(eps_r_fine, levels)
    if method == "harmonic":
        return harmonic_average_permittivity(eps_r_fine, levels)
    if pec_mask_fine is None:
        raise ValueError("conformal 方法须提供 pec_mask_fine")
    return conformal_permittivity(eps_r_fine, pec_mask_fine, levels)
