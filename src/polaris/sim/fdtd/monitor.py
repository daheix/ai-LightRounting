"""DFT 监视器与 S 参数提取（A09 §9）。

DFT 监视器：在指定网格点对时域场做离散傅里叶变换（DFT），提取指定频率的
复振幅。采用在线累加（每步 O(1)），避免存储完整时域波形（O(N) 内存）。

    DFT(f) = Σ_n E(n·Δt) · exp(-i·2π·f·n·Δt)        （e^{-iωt} 约定）

离散傅里叶变换的物理依据：连续 FT 的矩形窗采样近似，
    ∫ E(t) e^{-iωt} dt ≈ Δt · Σ_n E(nΔt) e^{-iωnΔt}
对 S 参数（比值）Δt 与窗因子在分子分母对消，故监视器仅存裸和即可。

S 参数（散射参数）提取：
    S21 = DFT_out / DFT_in   （透射，输出端口/输入端口）
    S11 = DFT_refl / DFT_in  （反射）
复数 S 同时含幅度（dB）与相位（rad）信息，是光子器件频域特性的标准描述
（与 Lumerical/S-Touchstone 接口一致）。

*创新*：在线累加 DFT——避免存储每个监视点的完整时域序列（典型 1e4~1e6 步），
内存从 O(N_steps·N_mon) 降至 O(N_mon)，且每步仅一次复数乘加。
- 底层逻辑：累加器 spectrum += E·exp(-iωnΔt)，最后归一化为复振幅。
- 支持理论：Taflove 2005 §5.3 推荐运行时 DFT 替代离线 FFT 以省内存。
- 案例：SOI 环透射谱（M4 验收，S21 vs 解析公式 <1e-3）。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.3（运行时 DFT）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
3. Moharam 1995 JOSA A 12(5) 1077-1086（RCWA S 参数，FDTD 验收基准）—
   https://doi.org/10.1364/JOSAA.12.001077
4. Lumerical FDTD 监视器 —
   https://optics.ansys.com/hc/en-us/categories/360001366534
5. MEEP FDTD 频域监视器 —
   https://meep.readthedocs.io/en/latest/Python_Tutorials/
6. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301
7. Pozar, Microwave Engineering, 4th ed. (2011) §4（S 参数定义）—
   https://www.wiley.com/en-us/Microwave+Engineering%2C+4th+Edition-p-9780470631553

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["DftMonitor", "SParamExtractor", "s_param_db"]

_TWO_PI = 2.0 * np.pi


@dataclass
class DftMonitor:
    """时域场 DFT 监视器（在线累加，A09 §9）。

    Attributes:
        position: 监视点网格索引 (i, j)。
        frequency: 监视频率 f（Hz），>0。
        field_component: 监视场分量，2D TEz 仅 'ez'。
        name: 监视器名称（供 S 参数提取引用）。
    """

    position: tuple[int, int]
    frequency: float
    field_component: str = "ez"
    name: str = ""
    # 在线累加状态（私有，由 record/reset 维护）
    _spectrum: complex = field(default=0.0 + 0.0j, repr=False)
    _n_samples: int = field(default=0, repr=False)
    _omega_dt: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        if self.frequency <= 0.0:
            raise ValueError(f"frequency 须 >0，实际 {self.frequency}")
        if self.field_component != "ez":
            raise ValueError(
                f"2D TEz 仅支持 'ez' 分量，实际 '{self.field_component}'"
            )
        ix, iy = self.position
        if ix < 0 or iy < 0:
            raise ValueError(f"位置索引须非负，实际 {self.position}")

    def configure(self, dt: float) -> None:
        """设置时间步并重置累加器（求解器在 run() 起始调用）。"""
        if dt <= 0.0:
            raise ValueError(f"dt 须 >0，实际 {dt}")
        self._omega_dt = _TWO_PI * self.frequency * dt
        self._spectrum = 0.0 + 0.0j
        self._n_samples = 0

    def record(self, field_value: float, n: int) -> None:
        """累加一个时间步的场采样（n 为步索引，从 0 起）。

        spectrum += E(nΔt) · exp(-i·2π·f·n·Δt)
        """
        if self._omega_dt == 0.0:
            raise RuntimeError("DftMonitor 未 configure(dt)，禁止记录")
        self._spectrum += field_value * np.exp(-1j * self._omega_dt * n)
        self._n_samples += 1

    @property
    def spectrum(self) -> complex:
        """归一化复振幅 DFT(f)（除以采样数，消除窗长依赖）。"""
        if self._n_samples == 0:
            raise RuntimeError("DftMonitor 无采样，先 record 后取谱")
        return self._spectrum / self._n_samples

    @property
    def raw_spectrum(self) -> complex:
        """裸 DFT 和（未归一化，含 Δt 尺度，比值对消）。"""
        if self._n_samples == 0:
            raise RuntimeError("DftMonitor 无采样")
        return self._spectrum

    @property
    def n_samples(self) -> int:
        """已累加采样数。"""
        return self._n_samples


def s_param_db(s_complex: complex) -> float:
    """S 参数幅度（dB）：20·log10|S|。

    Args:
        s_complex: 复 S 参数。

    Returns:
        幅度（dB），|S|=0 返回 -inf。
    """
    mag = abs(s_complex)
    if mag == 0.0:
        return float("-inf")
    return float(20.0 * np.log10(mag))


@dataclass
class SParamExtractor:
    """S 参数提取器（双监视器比值，A09 §9）。

    Attributes:
        name: S 参数名（如 'S21'、'S11'）。
        input_monitor: 输入（入射）参考监视器。
        output_monitor: 输出（透射/反射）监视器。
    """

    name: str
    input_monitor: DftMonitor
    output_monitor: DftMonitor

    def __post_init__(self) -> None:
        if self.input_monitor is self.output_monitor:
            raise ValueError("输入/输出监视器不能为同一对象")

    def compute(self) -> complex:
        """计算复 S 参数 = DFT_out / DFT_in。

        Returns:
            复 S 参数。

        Raises:
            ValueError: 输入监视器 DFT 为 0（无入射信号，规则 14 禁止 fall-back）。
        """
        s_in = self.input_monitor.spectrum
        if abs(s_in) == 0.0:
            raise ValueError(
                f"输入监视器 DFT=0，无法计算 {self.name}（检查源/位置）"
            )
        return self.output_monitor.spectrum / s_in
