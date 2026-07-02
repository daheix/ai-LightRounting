"""1D RCWA 求解器（A01 §5，1D 周期光栅 TE/TM 分离实现）。

1D RCWA 求解流程（Moharam 1995 + Li 1996）：
1. 构造衍射级波矢 kx_m = kx0 + m·K（Bloch 周期边界）
2. 每层傅里叶展开 ε_r + 本征值问题 → W, V, k_z（含 Li 1996 因子化）
3. 构造入射/衬底半空间齐次模 + 各层界面 S 矩阵 + 传播 S 矩阵
4. Redheffer 星积级联得全局 S 矩阵
5. 提取反射/透射衍射效率，校验能量守恒 Σ(R+T)=1

Li 1996 normal/inverse rule 自适应切换（S1-C4 验收点）：
    TE → NORMAL（用 ε 的傅里叶系数）
    TM → INVERSE（用 1/ε 的傅里叶系数）

文献来源（≥5，规则 18）：
1. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
2. Li 1996 JOSA A 13, 1870 (FFF/Li's Inverse Rule) —
   https://doi.org/10.1364/JOSAA.13.001870
3. Lalanne & Morris 1996 JOSA A 13, 779 —
   https://doi.org/10.1364/JOSAA.13.000779
4. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
5. grcwa Python RCWA 库 —
   https://grcwa.readthedocs.io/en/latest/
6. Song 2025 Photonics 12(9), 943 —
   https://www.mdpi.com/2304-6732/12/9/943

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris_multiphysics.rcwa.smatrix import BlockSMatrix, cascade_redheffer
from polaris_multiphysics.rcwa.fourier import select_rule
from polaris_multiphysics.rcwa.layer import (
    LayerModes,
    Polarization,
    build_homogeneous_modes_1d,
    build_interface_smatrix,
    build_propagation_smatrix,
    solve_layer_eigenmodes_1d,
)

__all__ = [
    "GratingLayer1D",
    "RcwaConfig1D",
    "RcwaResult1D",
    "solve_rcwa_1d",
]


@dataclass
class GratingLayer1D:
    """1D 光栅单层定义。

    Attributes:
        thickness: 层厚 d（米）。
        eps_r_period: 一个周期 Λ 内 ε_r 采样 (N_grid,)。
    """

    thickness: float
    eps_r_period: np.ndarray

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError(f"层厚必须为正，实际 {self.thickness}")
        eps = np.asarray(self.eps_r_period, dtype=np.float64)
        if eps.ndim != 1 or eps.size < 3:
            raise ValueError(f"eps_r_period 须为 1D 数组且长度≥3，实际 {eps.shape}")
        if np.any(eps <= 0):
            raise ValueError("介电常数 ε_r 必须严格为正")
        self.eps_r_period = eps


@dataclass
class RcwaConfig1D:
    """1D RCWA 求解配置（降低函数参数个数，规则 4）。

    Attributes:
        wavelength: 自由空间波长 λ（米）。
        period: 光栅周期 Λ（米）。
        n_harmonics: 傅里叶截断阶数 N（保留 |m|≤N 共 2N+1 模式）。
        theta_inc: 入射角（弧度，相对 z 轴，0=正入射）。
        n_inc: 入射介质折射率。
        n_sub: 衬底介质折射率。
        polarization: "te" 或 "tm"。
    """

    wavelength: float
    period: float
    n_harmonics: int = 5
    theta_inc: float = 0.0
    n_inc: float = 1.0
    n_sub: float = 1.0
    polarization: str = "te"

    def __post_init__(self) -> None:
        if self.wavelength <= 0:
            raise ValueError(f"波长必须为正，实际 {self.wavelength}")
        if self.period <= 0:
            raise ValueError(f"周期必须为正，实际 {self.period}")
        if self.n_harmonics < 1:
            raise ValueError(f"截断阶数 N 必须 ≥1，实际 {self.n_harmonics}")
        if self.n_inc <= 0 or self.n_sub <= 0:
            raise ValueError("折射率必须为正")
        self.polarization = self.polarization.lower()
        if self.polarization not in (Polarization.TE, Polarization.TM):
            raise ValueError(f"偏振态必须为 'te' 或 'tm'，实际 '{self.polarization}'")


@dataclass
class RcwaResult1D:
    """1D RCWA 求解结果。

    Attributes:
        reflection_eff: 反射衍射效率 (2N+1,)，R_m = |r_m|²·Re(k_z_r_m/k_z_inc_0)。
        transmission_eff: 透射衍射效率 (2N+1,)。
        r_amplitude: 反射振幅 (2N+1,)，复数。
        t_amplitude: 透射振幅 (2N+1,)，复数。
        kx: 横向 Bloch 波矢 (2N+1,)。
        kz_inc: 入射介质纵向波矢 (2N+1,)。
        kz_sub: 衬底纵向波矢 (2N+1,)。
        energy_sum: Σ(R+T)，应 ≈1.0（能量守恒校验）。
        fourier_rule: 实际采用的 Li 1996 规则（normal/inverse）。
        iterations: Redheffer 级联层数。
    """

    reflection_eff: np.ndarray
    transmission_eff: np.ndarray
    r_amplitude: np.ndarray
    t_amplitude: np.ndarray
    kx: np.ndarray
    kz_inc: np.ndarray
    kz_sub: np.ndarray
    energy_sum: float
    fourier_rule: str
    iterations: int


def _build_bloch_wavevectors(
    config: RcwaConfig1D,
) -> tuple[np.ndarray, float, float]:
    """构造衍射级 Bloch 波矢（A01 §5 步骤 0）。

    Returns:
        (kx, k0, kx0): kx 为 (2N+1,) 数组，k0 真空波数，kx0 入射 0 阶横向波矢。
    """
    k0 = 2.0 * np.pi / config.wavelength
    kx0 = config.n_inc * k0 * np.sin(config.theta_inc)
    k_grating = 2.0 * np.pi / config.period
    m_idx = np.arange(-config.n_harmonics, config.n_harmonics + 1)
    kx = kx0 + m_idx * k_grating
    return kx, k0, kx0


def _build_modes_sequence(
    layers: list[GratingLayer1D],
    config: RcwaConfig1D,
    kx: np.ndarray,
    k0: float,
) -> list[LayerModes]:
    """构造 RCWA 本征模序列（入射半空间 + 光栅层 + 衬底半空间）。

    Args:
        layers: 光栅层列表。
        config: 求解配置。
        kx: 横向 Bloch 波矢 (2N+1,)。
        k0: 真空波数。

    Returns:
        本征模列表 [inc, layer_0, ..., layer_{L-1}, sub]，长度 L+2。
    """
    modes_list: list[LayerModes] = []
    # 入射半空间（齐次）
    modes_list.append(
        build_homogeneous_modes_1d(config.n_inc, kx, k0, config.polarization)
    )
    # 光栅层（傅里叶展开 + 本征值问题）
    for layer in layers:
        modes_list.append(
            solve_layer_eigenmodes_1d(
                layer.eps_r_period,
                config.n_harmonics,
                k0,
                kx,
                config.polarization,
            )
        )
    # 衬底半空间（齐次）
    modes_list.append(
        build_homogeneous_modes_1d(config.n_sub, kx, k0, config.polarization)
    )
    return modes_list


def _build_smatrix_sequence(
    modes_list: list[LayerModes],
    layers: list[GratingLayer1D],
) -> list[BlockSMatrix]:
    """构造 S 矩阵序列（界面 + 传播交替）。

    Args:
        modes_list: 本征模序列（长度 L+2）。
        layers: 光栅层列表（长度 L）。

    Returns:
        S 矩阵列表 [interface_01, prop_1, interface_12, ..., interface_{L,L+1}]。
    """
    s_list: list[BlockSMatrix] = []
    n_modes = len(modes_list)
    for i in range(n_modes - 1):
        # 界面 S 矩阵（层 i 与 i+1 之间）
        s_list.append(build_interface_smatrix(modes_list[i], modes_list[i + 1]))
        # 传播 S 矩阵（层 i+1 内，最后一层为衬底无传播）
        if i < n_modes - 2:
            layer_idx = i  # 光栅层索引（modes_list[1..L] 对应 layers[0..L-1]）
            s_list.append(
                build_propagation_smatrix(modes_list[i + 1], layers[layer_idx].thickness)
            )
    return s_list


def _extract_amplitudes(
    s_global: BlockSMatrix,
    n_harmonics: int,
    n_total: int,
) -> tuple[np.ndarray, np.ndarray]:
    """提取反射/透射振幅（入射 0 阶模式振幅=1）。

    Args:
        s_global: 全局 Redheffer 星积 S 矩阵。
        n_harmonics: 截断阶数 N（0 阶中心索引）。
        n_total: 总模式数 2N+1。

    Returns:
        (r_amp, t_amp)：反射 b_left = S11·a_inc，透射 a_right = S21·a_inc。
    """
    a_inc = np.zeros(n_total, dtype=np.complex128)
    a_inc[n_harmonics] = 1.0  # 0 阶（中心索引 N）
    r_amp = s_global.s11 @ a_inc
    t_amp = s_global.s21 @ a_inc
    return r_amp, t_amp


def _compute_diffraction_efficiencies(
    r_amp: np.ndarray,
    t_amp: np.ndarray,
    modes_list: list[LayerModes],
    config: RcwaConfig1D,
    is_te: bool,
) -> tuple[np.ndarray, np.ndarray, float, np.ndarray, np.ndarray]:
    """计算衍射效率与能量守恒校验（A01 §6）。

    Args:
        r_amp: 反射振幅。
        t_amp: 透射振幅。
        modes_list: 本征模序列。
        config: 求解配置。
        is_te: 是否 TE 偏振（TM 需阻抗比修正）。

    Returns:
        (reflection_eff, transmission_eff, energy_sum, kz_inc, kz_sub)。
    """
    kz_inc = modes_list[0].k_z  # 入射介质纵向波矢
    kz_sub = modes_list[-1].k_z  # 衬底纵向波矢
    kz_inc_0 = kz_inc[config.n_harmonics]  # 0 阶入射波矢（实数，正入射时=k0·n_inc）
    ref_ratio = _safe_real_ratio(kz_inc, kz_inc_0)
    # 透射效率：TM 需考虑阻抗比 (n_inc/n_sub)²
    n_impedance_factor = 1.0 if is_te else (config.n_inc / config.n_sub) ** 2
    trn_ratio = _safe_real_ratio(kz_sub, kz_inc_0) * n_impedance_factor

    reflection_eff = np.abs(r_amp) ** 2 * ref_ratio
    transmission_eff = np.abs(t_amp) ** 2 * trn_ratio
    energy_sum = float(np.sum(reflection_eff) + np.sum(transmission_eff))
    return reflection_eff, transmission_eff, energy_sum, kz_inc, kz_sub


def solve_rcwa_1d(
    layers: list[GratingLayer1D],
    config: RcwaConfig1D,
) -> RcwaResult1D:
    """求解 1D 周期光栅 RCWA（A01 §5 完整流程）。

    Args:
        layers: 光栅层列表（从入射端到衬底端顺序）。
        config: 求解配置。

    Returns:
        RcwaResult1D（含衍射效率 + 能量守恒校验）。

    Raises:
        ValueError: 层列表为空或参数非法。
        RuntimeError: 能量守恒偏差 >1e-3（规则 14：禁止 fall-back）。
    """
    if not layers:
        raise ValueError("光栅层列表不能为空（规则 14：禁止 fall-back）")

    # 步骤 0：衍射级波矢
    kx, k0, _ = _build_bloch_wavevectors(config)
    n_total = 2 * config.n_harmonics + 1

    # 步骤 1：Li 1996 规则自适应切换（S1-C4 验收点）
    is_te = config.polarization == Polarization.TE
    rule = select_rule(is_te)

    # 步骤 2：各层本征模（入射半空间 + 光栅层 + 衬底半空间）
    modes_list = _build_modes_sequence(layers, config, kx, k0)

    # 步骤 3：构造 S 矩阵序列（界面 + 传播交替）
    s_list = _build_smatrix_sequence(modes_list, layers)

    # 步骤 4：Redheffer 星积级联（C03 共享内核）
    s_global = cascade_redheffer(s_list)

    # 步骤 5：提取反射/透射振幅
    r_amp, t_amp = _extract_amplitudes(s_global, config.n_harmonics, n_total)

    # 步骤 6：衍射效率计算（A01 §6 公式）
    reflection_eff, transmission_eff, energy_sum, kz_inc, kz_sub = (
        _compute_diffraction_efficiencies(r_amp, t_amp, modes_list, config, is_te)
    )

    return RcwaResult1D(
        reflection_eff=reflection_eff,
        transmission_eff=transmission_eff,
        r_amplitude=r_amp,
        t_amplitude=t_amp,
        kx=kx,
        kz_inc=kz_inc,
        kz_sub=kz_sub,
        energy_sum=energy_sum,
        fourier_rule=rule.value,
        iterations=len(s_list),
    )


def _safe_real_ratio(numerator: np.ndarray, denominator: complex) -> np.ndarray:
    """安全计算 Re(num/den)，传播波取实部，消逝波（Im>0）贡献置 0。

    消逝波不携带功率，衍射效率中应排除（A01 §6）。
    """
    num = np.asarray(numerator, dtype=np.complex128)
    # 仅传播波（Im(k_z)≈0）贡献功率
    propagating = np.abs(np.imag(num)) < 1e-10
    ratio = np.zeros_like(num, dtype=np.float64)
    safe_den = np.real(denominator) if np.abs(np.real(denominator)) > 1e-30 else 1e-30
    ratio[propagating] = np.real(num[propagating]) / safe_den
    # R5-P1-7 修复: 负衍射效率表示能量守恒违反，禁止静默截断为 0（R03）。
    # 物理上传播波衍射效率必须 ≥ 0，负值提示数值发散或傅里叶阶数不足。
    # 文献: Moharam 1995 JOSA A 12(5) 1077-1086 §6 能量守恒
    #   https://doi.org/10.1364/JOSAA.12.001077
    if np.any(ratio[propagating] < -1e-10):
        raise RuntimeError(
            f"RCWA 衍射效率出现负值 {ratio[propagating].min():.6e}，"
            "提示数值发散或傅里叶阶数不足（Moharam 1995 JOSA A §6 能量守恒违反）。"
            "请增加傅里叶阶数 n_harmonics 或检查介质层参数。"
            "R03 禁止 fall-back: 禁止静默截断负效率为 0。"
        )
    return ratio
