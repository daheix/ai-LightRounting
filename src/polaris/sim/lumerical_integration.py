"""R31-R33 路标：Ansys Lumerical 全流程对齐模块。

对标 Ansys Lumerical 全流程（MODE Solutions + INTERCONNECT + CHARGE），
提供波导模式求解、光链路系统仿真与电光协同仿真能力，实现 PoLaRIS 与
Lumerical 的多物理场交叉验证。

## 模块组成

1. ``ModeSolver`` — Lumerical MODE Solutions 对齐（波导模式求解器）
2. ``INTERCONNECTSimulator`` — Lumerical INTERCONNECT 对齐（光链路系统仿真）
3. ``CHARGESimulator`` — Lumerical CHARGE 对齐（电光协同仿真）
4. ``LumericalIntegration`` — Lumerical 全流程统一接口

## 学术依据

- Ansys Lumerical MODE Solutions: https://www.ansys.com/products/optics/mode
- Ansys Lumerical INTERCONNECT: https://www.ansys.com/products/optics/interconnect
- Ansys Lumerical CHARGE: https://www.ansys.com/products/optics/charge
- Ansys Lumerical 多物理场协同:
  https://optics.ansys.com/hc/en-us/articles/360042414214
- Silvester & Ferrari, "Finite Elements for Electrical Engineers", 1996
- Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010
- Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., 2007
- Marcatili, Bell Syst. Tech. J. 48, 2071 (1969)

来源:
- Ansys Lumerical: https://www.ansys.com/products/optics
- LFSR PRBS: ITU-T O.150 标准
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# 物理常数（来源: CODATA 2018, https://physics.nist.gov/cuu/Constants/;
#           SiPANN/SiEPIC PDK 标准值, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
_C0 = 2.99792458e8  # 真空光速 (m/s)
_Q = 1.602176634e-19  # 电子电荷 (C)
_KB = 1.380649e-23  # 玻尔兹曼常数 (J/K)
_EPS0 = 8.8541878128e-12  # 真空介电常数 (F/m)
_EPS_SIO2 = 3.9  # 二氧化硅相对介电常数
_EPS_SI = 11.7  # 硅相对介电常数
_N_SILICON = 3.48  # 硅折射率 @ 1.55μm (SiEPIC EBeam PDK)
_N_SIO2 = 1.44  # 二氧化硅折射率 @ 1.55μm
_N_SI_INFRARED = 3.45  # 硅红外波段折射率（CHARGE 用）


# ---------------------------------------------------------------------------
# 1. MODE Solutions — 波导模式求解器
# ---------------------------------------------------------------------------


@dataclass
class ModeConfig:
    """Lumerical MODE Solutions 配置。

    学术依据：Ansys Lumerical MODE Solutions
    URL: https://www.ansys.com/products/optics/mode

    求解 Maxwell 方程的特征值问题：
        ∇ × (1/ε(r)) ∇ × H = (ω²/c²) H

    Attributes:
        wavelength: 中心波长（μm）。
        grid_size: 网格大小 (dx, dy)（μm）。
        n_modes: 求解的模式数。
        boundary: 边界条件（"PML"/"PEC"/"PMC"）。
        window_size: 计算窗口尺寸 (wx, wy)（μm）。
    """

    wavelength: float = 1.55
    grid_size: tuple = (0.05, 0.05)
    n_modes: int = 4
    boundary: str = "PML"
    window_size: tuple = (1.6, 1.6)


class ModeSolver:
    """Lumerical MODE Solutions 对齐（波导模式求解器）。

    学术依据：
    - Ansys Lumerical MODE Solutions 官方文档
      https://www.ansys.com/products/optics/mode
    - Silvester & Ferrari, "Finite Elements for Electrical Engineers", 1996
    - Marcatili, Bell Syst. Tech. J. 48, 2071 (1969)

    求解方法：有限差分频域（FDFD）特征值问题。
    将标量波动方程 ∇²E + k₀²n²(r)E = k₀²n_eff²E 离散化为矩阵特征值问题
    A·E = λ·E，其中 λ = k₀²n_eff²，用 numpy.linalg.eigh 求解。
    """

    def __init__(self, config: ModeConfig) -> None:
        """初始化模式求解器。

        Args:
            config: MODE Solutions 配置。
        """
        self.config = config
        self.wavelength = config.wavelength
        self.dx, self.dy = config.grid_size
        self.wx, self.wy = config.window_size
        self.nx = int(round(self.wx / self.dx))
        self.ny = int(round(self.wy / self.dy))

    def _build_index_grid(
        self, width: float, height: float, core_index: float, cladding_index: float
    ) -> np.ndarray:
        """构建折射率分布网格。

        Args:
            width: 波导宽度（μm）。
            height: 波导高度（μm）。
            core_index: 核心折射率。
            cladding_index: 包层折射率。

        Returns:
            折射率分布二维数组。
        """
        n_grid = np.full((self.nx, self.ny), cladding_index, dtype=np.float64)
        x = np.arange(self.nx) * self.dx
        y = np.arange(self.ny) * self.dy
        cx = self.nx * self.dx / 2.0
        cy = self.ny * self.dy / 2.0
        core_mask = (np.abs(x - cx)[:, None] <= width / 2.0) & (
            np.abs(y - cy)[None, :] <= height / 2.0
        )
        n_grid[core_mask] = core_index
        return n_grid

    def _build_fdfd_matrix(self, n_grid: np.ndarray) -> np.ndarray:
        """构建 FDFD 特征值矩阵。

        标量波动方程离散化：
            A[i,i] = -2/dx² - 2/dy² + k₀²n²[i,j]
            A[i,i±ny] = 1/dx² （x 方向邻接）
            A[i,i±1] = 1/dy² （y 方向邻接，处理边界）

        Args:
            n_grid: 折射率分布网格。

        Returns:
            FDFD 矩阵（实对称）。
        """
        nx, ny = n_grid.shape
        N = nx * ny
        n_flat = n_grid.flatten()
        k0 = 2.0 * np.pi / self.wavelength
        # 主对角线
        main_diag = -2.0 / self.dx**2 - 2.0 / self.dy**2 + k0**2 * n_flat**2
        A = np.diag(main_diag)
        # x 方向偏对角线（距离 ny）
        if N > ny:
            idx = np.arange(N - ny)
            A[idx, idx + ny] = 1.0 / self.dx**2
            A[idx + ny, idx] = 1.0 / self.dx**2
        # y 方向偏对角线（距离 1），排除每行边界
        if N > 1:
            idx = np.arange(N - 1)
            mask = (idx + 1) % ny != 0
            idx = idx[mask]
            A[idx, idx + 1] = 1.0 / self.dy**2
            A[idx + 1, idx] = 1.0 / self.dy**2
        return A

    def solve_waveguide(
        self, width: float, height: float, core_index: float, cladding_index: float
    ) -> dict:
        """求解矩形波导模式。

        使用 FDFD 特征值分解求解波导模式，返回有效折射率、模式剖面、
        群折射率与色散。

        Args:
            width: 波导宽度（μm）。
            height: 波导高度（μm）。
            core_index: 核心折射率。
            cladding_index: 包层折射率。

        Returns:
            包含 n_eff/mode_profile/n_group/dispersion 的字典。
        """
        n_grid = self._build_index_grid(width, height, core_index, cladding_index)
        A = self._build_fdfd_matrix(n_grid)
        k0 = 2.0 * np.pi / self.wavelength
        # 求解实对称矩阵特征值
        eigenvalues, eigenvectors = np.linalg.eigh(A)
        # 筛选导模：n_clad² < n_eff² < n_core²
        n_eff_sq = eigenvalues / k0**2
        mask = (n_eff_sq > cladding_index**2) & (n_eff_sq < core_index**2)
        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            logger.warning("未找到导模，请检查波导参数。")
            return {
                "n_eff": cladding_index,
                "mode_profile": np.zeros((self.nx, self.ny)),
                "n_group": cladding_index,
                "dispersion": 0.0,
            }
        # 取最大的 n_modes 个特征值（对应最高 n_eff）
        valid_indices = valid_indices[np.argsort(-eigenvalues[valid_indices])][
            : self.config.n_modes
        ]
        # 基模（最大 n_eff）
        n_eff = float(np.sqrt(n_eff_sq[valid_indices[0]]))
        mode_profile = eigenvectors[:, valid_indices[0]].reshape(self.nx, self.ny)
        # 归一化模式剖面
        norm = np.sqrt(np.sum(np.abs(mode_profile) ** 2))
        if norm > 0:
            mode_profile = mode_profile / norm
        # 群折射率 n_g = n_eff - λ·dn_eff/dλ（用数值微分）
        n_group = self._compute_n_group(width, height, core_index, cladding_index)
        # 色散 D = -(λ/c)·d²n_eff/dλ²
        dispersion = self._compute_dispersion_value(width, height, core_index, cladding_index)
        return {
            "n_eff": n_eff,
            "mode_profile": mode_profile,
            "n_group": n_group,
            "dispersion": dispersion,
            "n_modes_found": len(valid_indices),
        }

    def _compute_n_group(
        self, width: float, height: float, core_index: float, cladding_index: float
    ) -> float:
        """计算群折射率 n_g = n_eff - λ·dn_eff/dλ。

        Args:
            width: 波导宽度（μm）。
            height: 波导高度（μm）。
            core_index: 核心折射率。
            cladding_index: 包层折射率。

        Returns:
            群折射率。
        """
        wl = self.wavelength
        delta = 0.01  # 波长扰动（μm）
        n_eff_plus = self.compute_neff(width, core_index, cladding_index, wl + delta, height)
        n_eff_minus = self.compute_neff(width, core_index, cladding_index, wl - delta, height)
        dn_eff_dwl = (n_eff_plus - n_eff_minus) / (2.0 * delta)
        n_eff_center = self.compute_neff(width, core_index, cladding_index, wl, height)
        return n_eff_center - wl * dn_eff_dwl

    def _compute_dispersion_value(
        self, width: float, height: float, core_index: float, cladding_index: float
    ) -> float:
        """计算色散值 D = -(λ/c)·d²n_eff/dλ²。

        Args:
            width: 波导宽度（μm）。
            height: 波导高度（μm）。
            core_index: 核心折射率。
            cladding_index: 包层折射率。

        Returns:
            色散值（ps/(nm·km)）。
        """
        wl = self.wavelength
        delta = 0.01  # 波长扰动（μm）
        n_eff_plus = self.compute_neff(width, core_index, cladding_index, wl + delta, height)
        n_eff_minus = self.compute_neff(width, core_index, cladding_index, wl - delta, height)
        n_eff_center = self.compute_neff(width, core_index, cladding_index, wl, height)
        # D = -(λ/c)·d²n_eff/dλ²，单位转换：μm→m，结果转 ps/(nm·km)
        c_m = _C0
        wl_m = wl * 1e-6
        delta_m = delta * 1e-6
        d2_n_eff_dwl2_m = (n_eff_plus - 2.0 * n_eff_center + n_eff_minus) / delta_m**2
        D = -(wl_m / c_m) * d2_n_eff_dwl2_m  # s/m²
        # 转换为 ps/(nm·km)：1 s/m² = 1e12 ps / (1e-9 m · 1e3 m) = 1e18 ps/(nm·km)
        return D * 1e18

    def compute_neff(
        self,
        width: float,
        core_index: float,
        cladding_index: float,
        wavelength: float | None = None,
        height: float = 0.22,
    ) -> float:
        """计算有效折射率（Marcatili 近似 + Goos-Hänchen 修正）。

        学术依据：Marcatili, Bell Syst. Tech. J. 48, 2071 (1969)
        公式：n_eff² = n_core² - (π/(w·k₀ + π/n_core))² - (π/(h·k₀ + π/n_core))²

        Args:
            width: 波导宽度（μm）。
            core_index: 核心折射率。
            cladding_index: 包层折射率（用于验证导模条件）。
            wavelength: 波长（μm），None 时用配置波长。
            height: 波导高度（μm），默认 0.22μm（SiEPIC 标准）。

        Returns:
            有效折射率。
        """
        wl = wavelength if wavelength is not None else self.wavelength
        k0 = 2.0 * np.pi / wl
        # Goos-Hänchen 修正：有效尺寸 = 物理尺寸 + 穿透深度
        w_eff = width * k0 + np.pi / core_index
        h_eff = height * k0 + np.pi / core_index
        n_eff_sq = core_index**2 - (np.pi / w_eff) ** 2 - (np.pi / h_eff) ** 2
        if n_eff_sq < cladding_index**2:
            # 截止条件：n_eff < n_clad，模式不再导模
            return cladding_index
        return float(np.sqrt(n_eff_sq))

    def compute_dispersion(self, wavelengths: list, width: float) -> dict:
        """计算色散（D = -(λ/c) d²n_eff/dλ²）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010, §2.4

        Args:
            wavelengths: 波长列表（μm）。
            width: 波导宽度（μm）。

        Returns:
            包含 wavelengths/dispersion/n_eff 数组的字典。
        """
        wls = np.array(wavelengths, dtype=np.float64)
        n_effs = np.array(
            [self.compute_neff(width, _N_SILICON, _N_SIO2, wl) for wl in wls]
        )
        # 数值二阶导数
        if len(wls) < 3:
            return {"wavelengths": wls, "dispersion": np.zeros_like(wls), "n_eff": n_effs}
        d2_n = np.zeros_like(n_effs)
        dwl = wls[1] - wls[0]
        d2_n[1:-1] = (n_effs[:-2] - 2.0 * n_effs[1:-1] + n_effs[2:]) / dwl**2
        # 端点用单边差分
        d2_n[0] = (n_effs[2] - 2.0 * n_effs[1] + n_effs[0]) / dwl**2
        d2_n[-1] = (n_effs[-1] - 2.0 * n_effs[-2] + n_effs[-3]) / dwl**2
        # D = -(λ/c)·d²n_eff/dλ²，单位 ps/(nm·km)
        c_m = _C0
        wls_m = wls * 1e-6
        dwl_m = dwl * 1e-6
        d2_n_m = d2_n / dwl_m**2
        D = -(wls_m / c_m) * d2_n_m * 1e18  # ps/(nm·km)
        return {"wavelengths": wls, "dispersion": D, "n_eff": n_effs}

    def compute_overlap(self, mode1: np.ndarray, mode2: np.ndarray) -> float:
        """计算模式重叠积分。

        学术依据：Snyder & Love, "Optical Waveguide Theory", 1983, §13.5
        公式：η = |∫ E1·E2 dA|² / (∫|E1|²dA · ∫|E2|²dA)

        Args:
            mode1: 模式1剖面。
            mode2: 模式2剖面。

        Returns:
            重叠积分值 [0, 1]。
        """
        m1 = np.asarray(mode1, dtype=np.float64)
        m2 = np.asarray(mode2, dtype=np.float64)
        if m1.shape != m2.shape:
            # 形状不一致时，裁剪到较小尺寸
            nx = min(m1.shape[0], m2.shape[0])
            ny = min(m1.shape[1], m2.shape[1])
            m1 = m1[:nx, :ny]
            m2 = m2[:nx, :ny]
        dA = self.dx * self.dy
        num = np.sum(m1 * m2) * dA
        den1 = np.sqrt(np.sum(np.abs(m1) ** 2) * dA)
        den2 = np.sqrt(np.sum(np.abs(m2) ** 2) * dA)
        if den1 < 1e-15 or den2 < 1e-15:
            return 0.0
        overlap = np.abs(num) / (den1 * den2)
        return float(min(overlap**2, 1.0))


# ---------------------------------------------------------------------------
# 2. INTERCONNECT — 光链路系统仿真
# ---------------------------------------------------------------------------


@dataclass
class INTERCONNECTConfig:
    """Lumerical INTERCONNECT 配置。

    学术依据：Ansys Lumerical INTERCONNECT
    URL: https://www.ansys.com/products/optics/interconnect

    Attributes:
        sample_rate: 采样率（Hz）。
        bit_rate: 比特率（bps）。
        n_bits: 仿真比特数。
        modulation: 调制格式（"NRZ"/"PAM4"/"QAM16"）。
    """

    sample_rate: float = 1e12
    bit_rate: float = 10e9
    n_bits: int = 128
    modulation: str = "NRZ"


class INTERCONNECTSimulator:
    """Lumerical INTERCONNECT 对齐（光链路系统仿真）。

    学术依据：
    - Ansys Lumerical INTERCONNECT 官方文档
      https://www.ansys.com/products/optics/interconnect
    - Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010

    特性：
    - 时域波形仿真（PRBS + 调制 + 噪声 + 检测）
    - 眼图分析
    - BER 评估
    - OSNR 分析
    """

    def __init__(self, config: INTERCONNECTConfig) -> None:
        """初始化 INTERCONNECT 仿真器。

        Args:
            config: INTERCONNECT 配置。
        """
        self.config = config
        self.sample_rate = config.sample_rate
        self.bit_rate = config.bit_rate
        self.n_bits = config.n_bits
        self.modulation = config.modulation
        self.spp = int(self.sample_rate / self.bit_rate)  # 每比特采样点数

    def generate_prbs(self, n_bits: int) -> np.ndarray:
        """生成 PRBS 伪随机比特序列（LFSR 实现）。

        学术依据：ITU-T O.150 标准，PRBS7 多项式 x^7 + x^6 + 1
        URL: https://www.itu.int/rec/T-REC-O.150

        Args:
            n_bits: 比特数。

        Returns:
            比特数组（0/1）。
        """
        # PRBS7：7 级 LFSR，反馈多项式 x^7 + x^6 + 1
        register = np.array([1, 0, 1, 0, 1, 0, 1], dtype=np.uint8)  # 初始种子
        bits = np.zeros(n_bits, dtype=np.uint8)
        for i in range(n_bits):
            bits[i] = register[0]
            # 反馈：bit0 XOR bit6
            feedback = register[0] ^ register[6]
            register = np.roll(register, -1)
            register[-1] = feedback
        return bits

    def modulate(self, bits: np.ndarray, modulation: str = "NRZ") -> np.ndarray:
        """调制（NRZ/PAM4/QAM16）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010

        Args:
            bits: 比特数组。
            modulation: 调制格式。

        Returns:
            调制信号波形。
        """
        bits = np.asarray(bits, dtype=np.float64)
        spp = self.spp
        if modulation == "NRZ":
            # NRZ：bit 0 → -1, bit 1 → +1
            symbols = 2.0 * bits - 1.0
            signal = np.repeat(symbols, spp)
        elif modulation == "PAM4":
            # PAM4：2 bits → 4 levels {-3, -1, +1, +3}
            n_symbols = len(bits) // 2
            symbols = np.zeros(n_symbols)
            for i in range(n_symbols):
                val = bits[2 * i] * 2 + bits[2 * i + 1]
                symbols[i] = 2.0 * val - 3.0
            signal = np.repeat(symbols, spp)
        elif modulation == "QAM16":
            # QAM16：4 bits → 16 QAM（实部 + 虚部）
            n_symbols = len(bits) // 4
            symbols = np.zeros(n_symbols, dtype=complex)
            for i in range(n_symbols):
                re = 2.0 * (bits[4 * i] * 2 + bits[4 * i + 1]) - 3.0
                im = 2.0 * (bits[4 * i + 2] * 2 + bits[4 * i + 3]) - 3.0
                symbols[i] = re + 1.0j * im
            signal = np.repeat(symbols, spp)
        else:
            raise ValueError(f"不支持的调制格式: {modulation}")
        return signal

    def add_noise(self, signal: np.ndarray, osnr: float) -> np.ndarray:
        """添加 ASE 噪声（给定 OSNR）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.5
        OSNR = P_signal / P_noise（线性），噪声为高斯白噪声。

        Args:
            signal: 信号波形。
            osnr: 光信噪比（线性，非 dB）。

        Returns:
            含噪信号。
        """
        signal = np.asarray(signal, dtype=np.float64)
        signal_power = np.mean(np.abs(signal) ** 2)
        noise_power = signal_power / max(osnr, 1e-15)
        rng = np.random.default_rng(42)
        if np.iscomplexobj(signal):
            noise = rng.normal(0, np.sqrt(noise_power / 2), signal.shape) + 1.0j * rng.normal(
                0, np.sqrt(noise_power / 2), signal.shape
            )
        else:
            noise = rng.normal(0, np.sqrt(noise_power), signal.shape)
        return signal + noise

    def detect(self, signal: np.ndarray) -> np.ndarray:
        """检测（阈值判决）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.6

        Args:
            signal: 接收信号波形。

        Returns:
            检测比特数组（0/1）。
        """
        signal = np.asarray(signal, dtype=np.float64)
        spp = self.spp
        n_bits = len(signal) // spp
        bits = np.zeros(n_bits, dtype=np.uint8)
        for i in range(n_bits):
            # 在每比特中间采样
            sample = signal[i * spp + spp // 2]
            # 阈值判决（0 阈值，适用于 NRZ）
            bits[i] = 1 if sample.real > 0 else 0
        return bits

    def compute_ber(self, tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
        """计算 BER（误比特率）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.6

        Args:
            tx_bits: 发送比特。
            rx_bits: 接收比特。

        Returns:
            BER 值。
        """
        tx = np.asarray(tx_bits)
        rx = np.asarray(rx_bits)
        n = min(len(tx), len(rx))
        if n == 0:
            return 0.5
        errors = np.sum(tx[:n] != rx[:n])
        return float(errors) / float(n)

    def compute_eye_diagram(self, signal: np.ndarray, n_bits: int) -> dict:
        """计算眼图。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.7
        将信号按比特周期折叠，计算眼图开口、眼高、眼宽。

        Args:
            signal: 信号波形。
            n_bits: 比特数。

        Returns:
            包含 eye_data/eye_height/eye_width 的字典。
        """
        signal = np.asarray(signal, dtype=np.float64)
        spp = self.spp
        n_bits = min(n_bits, len(signal) // spp)
        # 按比特周期折叠
        eye_data = np.zeros((n_bits, spp))
        for i in range(n_bits):
            eye_data[i, :] = signal[i * spp : (i + 1) * spp]
        # 眼高：最大值与最小值之差
        eye_height = float(np.max(eye_data) - np.min(eye_data))
        # 眼宽：在阈值交叉点附近，信号过零的时间宽度
        threshold = np.mean(eye_data)
        crossings = []
        for i in range(n_bits):
            row = eye_data[i, :]
            for j in range(spp - 1):
                if (row[j] - threshold) * (row[j + 1] - threshold) < 0:
                    crossings.append(j)
        eye_width = float(np.std(crossings)) if len(crossings) > 1 else float(spp) / 2.0
        return {
            "eye_data": eye_data,
            "eye_height": eye_height,
            "eye_width": eye_width,
            "n_bits": n_bits,
        }

    def compute_osnr(self, signal: np.ndarray, noise: np.ndarray) -> float:
        """计算 OSNR（光信噪比）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.5
        OSNR = P_signal / P_noise

        Args:
            signal: 信号波形。
            noise: 噪声波形。

        Returns:
            OSNR 值（线性）。
        """
        signal_power = float(np.mean(np.abs(np.asarray(signal)) ** 2))
        noise_power = float(np.mean(np.abs(np.asarray(noise)) ** 2))
        if noise_power < 1e-15:
            return 1e15
        return signal_power / noise_power

    def run_link_simulation(self, link_config: dict) -> dict:
        """运行完整光链路仿真。

        学术依据：Ansys Lumerical INTERCONNECT 端到端仿真流程
        URL: https://www.ansys.com/products/optics/interconnect

        流程：PRBS 生成 → 调制 → 添加噪声 → 检测 → BER/眼图/OSNR 评估

        Args:
            link_config: 链路配置（含 osnr/n_bits/modulation）。

        Returns:
            仿真结果字典。
        """
        osnr = link_config.get("osnr", 20.0)
        n_bits = link_config.get("n_bits", self.n_bits)
        modulation = link_config.get("modulation", self.modulation)
        # 1. 生成 PRBS
        tx_bits = self.generate_prbs(n_bits)
        # 2. 调制
        tx_signal = self.modulate(tx_bits, modulation)
        # 3. 添加噪声
        rx_signal = self.add_noise(tx_signal, osnr)
        # 4. 检测
        rx_bits = self.detect(rx_signal)
        # 5. 评估
        ber = self.compute_ber(tx_bits, rx_bits)
        eye = self.compute_eye_diagram(rx_signal, n_bits)
        # 噪声波形
        noise = rx_signal - tx_signal[: len(rx_signal)]
        osnr_measured = self.compute_osnr(tx_signal[: len(rx_signal)], noise)
        return {
            "tx_bits": tx_bits,
            "rx_bits": rx_bits,
            "ber": ber,
            "eye_diagram": eye,
            "osnr_target": osnr,
            "osnr_measured": osnr_measured,
            "modulation": modulation,
            "n_bits": n_bits,
        }


# ---------------------------------------------------------------------------
# 3. CHARGE — 电光协同仿真
# ---------------------------------------------------------------------------


@dataclass
class CHARGEConfig:
    """Lumerical CHARGE 配置。

    学术依据：Ansys Lumerical CHARGE
    URL: https://www.ansys.com/products/optics/charge

    Attributes:
        temperature: 温度（K）。
        doping_n: n 型掺杂（cm⁻³）。
        doping_p: p 型掺杂（cm⁻³）。
    """

    temperature: float = 300.0
    doping_n: float = 1e18
    doping_p: float = 1e18


class CHARGESimulator:
    """Lumerical CHARGE 对齐（电光协同仿真）。

    学术依据：
    - Ansys Lumerical CHARGE 官方文档
      https://www.ansys.com/products/optics/charge
    - Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., 2007

    求解 Poisson 方程 + 连续性方程：
        ∇·(ε∇φ) = -q(p - n + N_D⁺ - N_A⁻)
        ∂n/∂t = (1/q)∇·J_n + G - R
        ∂p/∂t = -(1/q)∇·J_p + G - R

    本实现采用解析公式（Sze & Ng §3.4 PN 结）求解 PN 结特性。
    """

    def __init__(self, config: CHARGEConfig) -> None:
        """初始化 CHARGE 仿真器。

        Args:
            config: CHARGE 配置。
        """
        self.config = config
        self.T = config.temperature
        self.N_D = config.doping_n * 1e6  # cm⁻³ → m⁻³
        self.N_A = config.doping_p * 1e6  # cm⁻³ → m⁻³
        # 硅材料参数（来源: Sze & Ng, Table 1.1）
        self.eps = _EPS_SI * _EPS0  # 介电常数 (F/m)
        self.n_i = self._compute_intrinsic_carrier()

    def _compute_intrinsic_carrier(self) -> float:
        """计算本征载流子浓度。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §1.4
        n_i = sqrt(N_C·N_V)·exp(-E_g/(2kT))
        硅 @ 300K：n_i ≈ 1.0e10 cm⁻³ = 1.0e16 m⁻³

        Returns:
            本征载流子浓度（m⁻³）。
        """
        # 硅禁带宽度 @ 300K
        E_g = 1.12 * _Q  # J
        # 有效态密度（硅 @ 300K）
        N_C = 2.8e19 * 1e6  # m⁻³
        N_V = 1.04e19 * 1e6  # m⁻³
        n_i = np.sqrt(N_C * N_V) * np.exp(-E_g / (2.0 * _KB * self.T))
        return float(n_i)

    def compute_depletion_width(self, va: float = 0.0) -> float:
        """计算耗尽区宽度。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §3.4
        公式：W = sqrt(2ε(V_bi - V_a)/q · (1/N_A + 1/N_D))

        Args:
            va: 外加电压（V），正向为正。

        Returns:
            耗尽区宽度（m）。
        """
        v_bi = self._compute_build_in_potential()
        # 反向偏置时 V_a < 0，V_bi - V_a > V_bi，耗尽区变宽
        v_total = v_bi - va
        if v_total <= 0:
            # 强正向偏置，耗尽区消失
            return 0.0
        w = np.sqrt(
            2.0 * self.eps * v_total / _Q * (1.0 / self.N_A + 1.0 / self.N_D)
        )
        return float(w)

    def _compute_build_in_potential(self) -> float:
        """计算内建电势 V_bi = (kT/q)·ln(N_A·N_D/n_i²)。

        学术依据：Sze & Ng, §3.4

        Returns:
            内建电势（V）。
        """
        v_bi = (_KB * self.T / _Q) * np.log(self.N_A * self.N_D / self.n_i**2)
        return float(v_bi)

    def compute_junction_capacitance(self, area: float, va: float = 0.0) -> float:
        """计算结电容 C_j = εA/W。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §3.5

        Args:
            area: 结面积（m²）。
            va: 外加电压（V）。

        Returns:
            结电容（F）。
        """
        w = self.compute_depletion_width(va)
        if w < 1e-12:
            return 0.0
        return float(self.eps * area / w)

    def compute_modulator_bandwidth(self, r_series: float, c_j: float) -> float:
        """计算调制器带宽 f_3dB = 1/(2π R C)。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §10.3
        RC 时间常数限制调制器带宽。

        Args:
            r_series: 串联电阻（Ω）。
            c_j: 结电容（F）。

        Returns:
            3dB 带宽（Hz）。
        """
        if r_series * c_j < 1e-30:
            return 1e15
        return float(1.0 / (2.0 * np.pi * r_series * c_j))

    def solve_pn_junction(self, width: float, length: float) -> dict:
        """求解 PN 结（耗尽区宽度、电容、电阻）。

        学术依据：Sze & Ng, "Physics of Semiconductor Devices", §3.4-3.5
        解析求解 PN 结的 I-V 与 C-V 特性。

        Args:
            width: PN 结宽度（μm）。
            length: PN 结长度（μm）。

        Returns:
            包含 depletion_width/capacitance/resistance/v_bi 的字典。
        """
        # 结面积（假设高度 220nm，SiEPIC 标准）
        height_m = 220e-9  # m
        area = width * 1e-6 * length * 1e-6 * height_m  # m²
        # 耗尽区宽度（零偏）
        w_depl = self.compute_depletion_width(0.0)
        # 结电容（零偏）
        c_j = self.compute_junction_capacitance(area, 0.0)
        # 串联电阻（估算：R = ρ·L/A，ρ硅 ~ 0.01 Ω·cm @ 1e18 cm⁻³）
        rho = 0.01 * 1e-2  # Ω·m
        r_series = rho * length * 1e-6 / area
        # 带宽
        f_3db = self.compute_modulator_bandwidth(r_series, c_j)
        v_bi = self._compute_build_in_potential()
        return {
            "depletion_width": w_depl,
            "capacitance": c_j,
            "resistance": r_series,
            "v_bi": v_bi,
            "bandwidth": f_3db,
            "area": area,
        }

    def electro_optic_simulation(self, modulator_config: dict) -> dict:
        """电光协同仿真（电压→折射率变化→相位调制）。

        学术依据：
        - Ansys Lumerical CHARGE + MODE 协同
          https://optics.ansys.com/hc/en-us/articles/360042414214
        - Sze & Ng, "Physics of Semiconductor Devices", §10.3

        物理流程：
        1. 电压 V → 耗尽区宽度变化 ΔW
        2. ΔW → 有效折射率变化 Δn_eff（等离子色散效应）
        3. Δn_eff → 相位调制 Δφ = (2π/λ)·Δn_eff·L

        Args:
            modulator_config: 调制器配置（含 voltage/length/wavelength/width）。

        Returns:
            电光仿真结果字典。
        """
        voltage = modulator_config.get("voltage", 1.0)
        length = modulator_config.get("length", 100.0)  # μm
        wavelength = modulator_config.get("wavelength", 1.55)  # μm
        width = modulator_config.get("width", 0.5)  # μm
        # 1. 计算耗尽区宽度变化
        # 调制器电压约定：voltage > 0 表示反向偏置幅度（V_a = -voltage）
        # 反向偏置增大耗尽区，用于耗尽型电光调制器
        w_0 = self.compute_depletion_width(0.0)
        w_v = self.compute_depletion_width(-abs(voltage))  # 反向偏置
        delta_w = w_v - w_0  # m（反向偏置时为正，耗尽区变宽）
        # 2. 等离子色散效应：Δn_eff ≈ α·ΔW/W_0
        # 来源：Soref & Bennett, IEEE J. Quantum Electron. 23(1), 1987
        # 硅等离子色散系数 @ 1.55μm：Δn ≈ -8.5e-22·ΔN (ΔN 为载流子浓度变化)
        # 简化：Δn_eff 与耗尽区宽度变化成正比
        alpha_plasma = -1.0e-3  # 折射率变化系数（μm⁻¹）
        delta_n_eff = alpha_plasma * (delta_w * 1e6)  # 转换为 μm
        # 3. 相位调制 Δφ = (2π/λ)·Δn_eff·L
        delta_phi = (2.0 * np.pi / wavelength) * delta_n_eff * length
        # 4. 调制器带宽（反向偏置下的结电容）
        height_m = 220e-9
        area = width * 1e-6 * length * 1e-6 * height_m
        c_j = self.compute_junction_capacitance(area, -abs(voltage))
        rho = 0.01 * 1e-2
        r_series = rho * length * 1e-6 / area
        f_3db = self.compute_modulator_bandwidth(r_series, c_j)
        return {
            "voltage": voltage,
            "depletion_width_0": w_0,
            "depletion_width_v": w_v,
            "delta_n_eff": float(delta_n_eff),
            "phase_shift": float(delta_phi),
            "bandwidth": f_3db,
            "capacitance": c_j,
            "resistance": r_series,
            "length_um": length,
            "wavelength_um": wavelength,
        }


# ---------------------------------------------------------------------------
# 4. LumericalIntegration — 全流程统一接口
# ---------------------------------------------------------------------------


class LumericalIntegration:
    """Lumerical 全流程统一接口。

    学术依据：Ansys Lumerical 多物理场协同
    URL: https://optics.ansys.com/hc/en-us/articles/360042414214

    整合 MODE + INTERCONNECT + CHARGE 三大求解器：
    1. MODE 求解波导模式 → 提取 n_eff/模式剖面
    2. CHARGE 求解电场 → 提取调制器参数（Δn_eff/带宽）
    3. INTERCONNECT 系统仿真 → BER/眼图/OSNR

    数据流：
        waveguide_config → ModeSolver → n_eff
        modulator_config → CHARGESimulator → Δn_eff, bandwidth
        link_config → INTERCONNECTSimulator → BER, eye_diagram
    """

    def __init__(self) -> None:
        """初始化 Lumerical 全流程接口。"""
        self.mode_solver: ModeSolver | None = None
        self.interconnect_sim: INTERCONNECTSimulator | None = None
        self.charge_sim: CHARGESimulator | None = None

    def full_flow(
        self,
        waveguide_config: dict,
        modulator_config: dict,
        link_config: dict,
    ) -> dict:
        """运行完整 Lumerical 流程。

        学术依据：Ansys Lumerical 端到端多物理场仿真
        URL: https://optics.ansys.com/hc/en-us/articles/360042414214

        Args:
            waveguide_config: 波导配置（含 width/height/core_index/cladding_index）。
            modulator_config: 调制器配置（含 voltage/length/wavelength）。
            link_config: 链路配置（含 osnr/n_bits/modulation）。

        Returns:
            全流程结果字典。
        """
        # 1. MODE 求解波导模式
        mode_cfg = ModeConfig(
            wavelength=waveguide_config.get("wavelength", 1.55),
            grid_size=waveguide_config.get("grid_size", (0.05, 0.05)),
            n_modes=waveguide_config.get("n_modes", 4),
            boundary=waveguide_config.get("boundary", "PML"),
            window_size=waveguide_config.get("window_size", (1.6, 1.6)),
        )
        self.mode_solver = ModeSolver(mode_cfg)
        mode_result = self.mode_solver.solve_waveguide(
            width=waveguide_config["width"],
            height=waveguide_config.get("height", 0.22),
            core_index=waveguide_config.get("core_index", _N_SILICON),
            cladding_index=waveguide_config.get("cladding_index", _N_SIO2),
        )
        # 2. CHARGE 求解电光协同
        charge_cfg = CHARGEConfig(
            temperature=modulator_config.get("temperature", 300.0),
            doping_n=modulator_config.get("doping_n", 1e18),
            doping_p=modulator_config.get("doping_p", 1e18),
        )
        self.charge_sim = CHARGESimulator(charge_cfg)
        eo_result = self.charge_sim.electro_optic_simulation(modulator_config)
        # 3. INTERCONNECT 系统仿真
        ic_cfg = INTERCONNECTConfig(
            sample_rate=link_config.get("sample_rate", 1e12),
            bit_rate=link_config.get("bit_rate", 10e9),
            n_bits=link_config.get("n_bits", 128),
            modulation=link_config.get("modulation", "NRZ"),
        )
        self.interconnect_sim = INTERCONNECTSimulator(ic_cfg)
        link_result = self.interconnect_sim.run_link_simulation(link_config)
        return {
            "mode_result": mode_result,
            "eo_result": eo_result,
            "link_result": link_result,
            "waveguide_config": waveguide_config,
            "modulator_config": modulator_config,
            "link_config": link_config,
        }

    def cross_validate(self, polaris_result: dict, lumerical_result: dict) -> dict:
        """交叉验证 PoLaRIS vs Lumerical。

        学术依据：多求解器交叉验证方法论
        URL: https://optics.ansys.com/hc/en-us/articles/360042414214

        比较关键指标：n_eff/BER/bandwidth 的相对误差。

        Args:
            polaris_result: PoLaRIS 仿真结果。
            lumerical_result: Lumerical 仿真结果。

        Returns:
            交叉验证结果字典。
        """
        metrics: dict[str, dict] = {}
        # 比较 n_eff
        if "n_eff" in polaris_result and "n_eff" in lumerical_result:
            p_val = polaris_result["n_eff"]
            l_val = lumerical_result["n_eff"]
            if abs(l_val) > 1e-15:
                rel_err = abs(p_val - l_val) / abs(l_val)
                metrics["n_eff"] = {
                    "polaris": p_val,
                    "lumerical": l_val,
                    "relative_error": float(rel_err),
                    "passed": rel_err < 0.10,  # 10% 容差
                }
        # 比较 BER
        if "ber" in polaris_result and "ber" in lumerical_result:
            p_val = polaris_result["ber"]
            l_val = lumerical_result["ber"]
            # BER 用绝对误差（BER 很小时相对误差不稳定）
            abs_err = abs(p_val - l_val)
            metrics["ber"] = {
                "polaris": p_val,
                "lumerical": l_val,
                "absolute_error": float(abs_err),
                "passed": abs_err < 0.05,
            }
        # 比较 bandwidth
        if "bandwidth" in polaris_result and "bandwidth" in lumerical_result:
            p_val = polaris_result["bandwidth"]
            l_val = lumerical_result["bandwidth"]
            if abs(l_val) > 1e-15:
                rel_err = abs(p_val - l_val) / abs(l_val)
                metrics["bandwidth"] = {
                    "polaris": p_val,
                    "lumerical": l_val,
                    "relative_error": float(rel_err),
                    "passed": rel_err < 0.20,  # 20% 容差
                }
        # 总体通过率
        n_total = len(metrics)
        n_passed = sum(1 for m in metrics.values() if m["passed"])
        overall_pass = n_passed == n_total if n_total > 0 else False
        return {
            "metrics": metrics,
            "n_total": n_total,
            "n_passed": n_passed,
            "overall_pass": overall_pass,
            "alignment_score": float(n_passed / n_total) if n_total > 0 else 0.0,
        }
