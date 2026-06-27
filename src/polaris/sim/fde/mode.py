"""FDE 模式数据类（A04 §11.2 创新点：统一数据结构供下游零成本复用）。

Mode 数据类封装 FDE 求解输出：6 场分量 + β + n_eff + TE/TM 分数 + 损耗 + 归一化标志。
EME/FDFD/2.5D-FDTD/FDTD 模式注入通过此数据类直接消费 FDE 结果，避免格式壁垒。

规则依据：project_rules.md 规则 18（学术诚信，无造假）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["Mode"]


@dataclass
class Mode:
    """FDE 求解得到的单个本征模。

    场分量形状均为 (Nx, Ny)，复数（含相位）。已按 1W 功率归一化。

    Attributes:
        ex, ey, ez: 电场三分量（V/m）。
        hx, hy, hz: 磁场三分量（A/m）。
        beta: 传播常数 β = k₀ · n_eff（rad/m，复数，虚部为损耗）。
        n_eff: 有效折射率 β/k₀（复数）。
        te_fraction: TE 分量分数 ∈ [0,1]，= |E_y|²/(|E_x|²+|E_y|²)（横向主场主导度）。
        tm_fraction: TM 分量分数 ∈ [0,1]，= |E_x|²/(|E_x|²+|E_y|²)，满足 te+tm=1。
            半矢量 TE（E_x=0）下 te_fraction=1.0；半矢量 TM（E_y=0）下 tm_fraction=1.0。
            不用纵向 E_z 定义（半矢量近似下 E_z 是数值导数推导量，高对比度界面噪声大）。
        loss_db_cm: 模式损耗（dB/cm），由 Im(n_eff) 换算。
        wavelength: 自由空间波长（米）。
        normalized: 是否已按 1W 功率归一化。
    """

    ex: np.ndarray
    ey: np.ndarray
    ez: np.ndarray
    hx: np.ndarray
    hy: np.ndarray
    hz: np.ndarray
    beta: complex
    n_eff: complex
    te_fraction: float
    tm_fraction: float
    loss_db_cm: float
    wavelength: float
    normalized: bool = True

    def __post_init__(self) -> None:
        for name in ("ex", "ey", "ez", "hx", "hy", "hz"):
            field_val = getattr(self, name)
            if field_val.ndim != 2:
                raise ValueError(f"{name} 必须为 2D 数组，实际 {field_val.ndim}D")
        if self.te_fraction < 0.0 or self.te_fraction > 1.0:
            raise ValueError(f"te_fraction 须 ∈ [0,1]，实际 {self.te_fraction}")
        if self.tm_fraction < 0.0 or self.tm_fraction > 1.0:
            raise ValueError(f"tm_fraction 须 ∈ [0,1]，实际 {self.tm_fraction}")

    @property
    def shape(self) -> tuple[int, int]:
        """场分量网格形状 (Nx, Ny)。"""
        return self.ex.shape  # type: ignore[return-value]

    def power_integral(self, dx: float, dy: float) -> float:
        """计算坡印廷功率积分 0.5·Re∫(E×H*)·ẑ dA（W）。

        向量化实现（python代码开发规则.md §4 禁止循环）：
            P = 0.5 · Re[Σ(E_x · H_y* - E_y · H_x*)] · dx · dy

        Args:
            dx, dy: 网格间距（米）。

        Returns:
            功率（W）。归一化后应为 1.0 ± 1e-10。
        """
        poynting = 0.5 * np.real(
            np.sum(self.ex * np.conj(self.hy) - self.ey * np.conj(self.hx))
        )
        return float(poynting * dx * dy)

    def overlap(self, other: Mode, dx: float, dy: float) -> float:
        """与另一模式的功率重叠积分 η_{m→n}（耦合效率）。

        η = |0.5·∫(E_m × H_n*)·ẑ dA|² / (|P_m| · |P_n|)

        其中 P = 0.5·∫(E × H*)·ẑ dA 为复数坡印廷积分（取模归一化）。
        分母用复数模 |P_m|·|P_n| 保证自重叠 η=1.0（严格归一），
        对有损模式（β 复数，P 含无功虚部）也自洽。

        自重叠推导（m=n）::
            η = |Z|² / (|Z|·|Z|) = 1.0   （Z = 0.5·∫(E×H*)·dA）

        若分母取实部 Re[Z]（有功功率），则 η = (Re²+Im²)/Re² > 1（有损模式），
        物理不自洽。本实现用模归一化，与 Gallagher & Felici 2003 §3 一致。

        供 EME 界面 S 矩阵与 FDE 模式匹配复用（A04 §7 公式）。
        文献：Gallagher & Felici 2003 SPIE 4987 §3 —
            https://doi.org/10.1117/12.478061

        Args:
            other: 另一模式。
            dx, dy: 网格间距。

        Returns:
            耦合效率 ∈ [0,1]（自重叠=1.0 ± 1e-6）。
        """
        if self.shape != other.shape:
            raise ValueError(
                f"模式形状不匹配 {self.shape} vs {other.shape}，无法计算重叠积分"
            )
        # 交叉重叠积分 Z_{mn} = 0.5·∫(E_m × H_n*)·ẑ dA（复数，含无功功率）
        # 0.5 因子来源于坡印廷矢量时间平均，与 overlap_matrix 的 0.5 约定一致
        cross_mn = 0.5 * np.sum(
            self.ex * np.conj(other.hy) - self.ey * np.conj(other.hx)
        ) * dx * dy
        # 自功率积分 Z_{mm}, Z_{nn}（复数，取模归一化保证自重叠=1.0）
        cross_mm = 0.5 * np.sum(
            self.ex * np.conj(self.hy) - self.ey * np.conj(self.hx)
        ) * dx * dy
        cross_nn = 0.5 * np.sum(
            other.ex * np.conj(other.hy) - other.ey * np.conj(other.hx)
        ) * dx * dy
        p_m = abs(cross_mm)
        p_n = abs(cross_nn)
        denom = p_m * p_n
        if denom <= 0.0:
            raise ValueError(
                "模式功率积分模为零，无法归一化重叠积分（检查模式归一化）"
            )
        return float(np.abs(cross_mn) ** 2 / denom)
