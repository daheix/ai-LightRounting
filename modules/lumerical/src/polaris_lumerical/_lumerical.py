"""Lumerical FDTD/MODE/CHARGE/INTERCONNECT + 全流程集成（章节1-5）。

从 v4 旧包 sim/ 迁移 Lumerical 系列核心 API，纯 NumPy 实现。

学术依据（R02 ≥5 文献 URL）:
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Soref & Bennett 1987 IEEE JQE https://doi.org/10.1109/JQE.1987.1073206
- Marcatili 1969 Bell Syst Tech J https://doi.org/10.1002/j.1538-7305.1969.tb01163.x
- Sze & Ng 2007 Physics of Semiconductor Devices §3.4-3.5
- Agrawal 2010 Fiber-Optic Communication Systems §4.5-4.7
- ITU-T O.150 PRBS https://www.itu.int/rec/T-REC-O.150
- Chrostowski 2015 Silicon Photonics Design Cambridge
- Ansys Lumerical https://optics.ansys.com/hc/en-us

设计原则: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy CPU /
R05 无 TODO / R13 不保留 v4 兼容 / 函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 物理常数（CODATA 2018 / SiEPIC EBeam PDK，来源 lumerical_constants.py）
_C0 = 2.99792458e8          # 真空光速 m/s (CODATA 2018)
_Q = 1.602176634e-19        # 电子电荷 C (CODATA 2018，精确值)
_KB = 1.380649e-23          # 玻尔兹曼常数 J/K (CODATA 2018)
_EPS0 = 8.8541878128e-12    # 真空介电常数 F/m (CODATA 2018)
_EPS_SI = 11.7              # 硅相对介电常数 (Sze & Ng Table 1.1)
_N_SILICON = 3.48           # 硅折射率 @ 1550nm (SiEPIC EBeam PDK)
_N_SIO2 = 1.44              # 二氧化硅折射率 @ 1550nm
# Soref & Bennett 1987 硅等离子色散系数 @ λ=1550nm (https://doi.org/10.1109/JQE.1987.1073206)
_SOREF_DN_AN = -8.8e-22     # 电子系数 (cm³)
_SOREF_DN_AP = -8.5e-18     # 空穴系数 (cm³，比电子大 ~4 个数量级)


# =============================================================================
# 1. Lumerical FDTD 3D（API 定义 + CFL 稳定条件，完整引擎在 polaris-fdtd）
# =============================================================================
@dataclass
class FDTD3DConfig:
    """Lumerical FDTD 3D 配置（对标 Ansys Lumerical FDTD）。

    学术依据: Yee 1966 / Taflove 2005 §3-§6
    URL: https://www.ansys.com/products/optics/fdtd
    """
    wavelength_um: float = 1.55
    dx_um: float = 0.05
    dy_um: float = 0.05
    dz_um: float = 0.05
    n_steps: int = 1000
    cfl: float = 0.99
    pml_layers: int = 8


def courant_dt_3d(dx: float, dy: float, dz: float, cfl: float = 0.99) -> float:
    """3D CFL 稳定条件时间步长。Δt ≤ 1/(c·√(1/Δx²+1/Δy²+1/Δz²))。

    学术依据: Yee 1966 / Taflove 2005 §4.2
    """
    if min(dx, dy, dz) <= 0:
        raise ValueError(f"网格步长须 > 0，得到 dx={dx} dy={dy} dz={dz}")
    if not 0 < cfl <= 1:
        raise ValueError(f"CFL 因子须在 (0,1]，得到 {cfl}")
    dt_max = 1.0 / (_C0 * np.sqrt(1.0 / dx**2 + 1.0 / dy**2 + 1.0 / dz**2))
    return float(cfl * dt_max)


class LumericalFDTDBackend:
    """Lumerical FDTD 3D 后端（API 定义 + 调用逻辑）。

    完整 3D Yee leapfrog + 6 面 CPML + Drude ADE + TFSF 3D 引擎实现位于
    polaris-fdtd 子模块。本类提供 Lumerical 对标 API 定义与参数校验。

    学术依据: Yee 1966 / Roden & Gedney 2000 CPML / Taflove 2005 §5.5 §9.3
    """

    def __init__(self, config: FDTD3DConfig) -> None:
        self.config = config
        self._grid_set = False

    def set_grid_3d(self) -> None:
        """设置 3D Yee 网格并初始化更新系数。"""
        self._dt = courant_dt_3d(
            self.config.dx_um * 1e-6, self.config.dy_um * 1e-6,
            self.config.dz_um * 1e-6, self.config.cfl,
        )
        self._grid_set = True

    def run(self) -> dict:
        """运行 3D FDTD 仿真。

        Raises:
            RuntimeError: 完整 3D Yee 引擎位于 polaris-fdtd 子模块。
        """
        if not self._grid_set:
            self.set_grid_3d()
        raise RuntimeError(
            "LumericalFDTDBackend.run: 完整 3D Yee leapfrog + CPML + TFSF 引擎"
            "位于 polaris-fdtd 子模块（modules/fdtd/）。本子模块仅提供"
            "Lumerical 对标 API 定义与参数校验（R13 不保留 v4 兼容）。"
            "请使用: from polaris_fdtd import FDTDSolver"
        )


# =============================================================================
# 2. Lumerical MODE（Marcatili + FDFD 特征值分解，纯 NumPy 完整实现）
# =============================================================================
@dataclass
class ModeConfig:
    """Lumerical MODE Solutions 配置。URL: https://www.ansys.com/products/optics/mode"""
    wavelength: float = 1.55
    grid_size: tuple = (0.05, 0.05)
    n_modes: int = 4
    boundary: str = "PML"
    window_size: tuple = (1.6, 1.6)


class ModeSolver:
    """Lumerical MODE Solutions 对齐（波导模式求解器）。

    学术依据: Marcatili 1969 / Ansys Lumerical MODE
    求解标量波动方程 ∇²E + k₀²n²(r)E = k₀²n_eff²E 的特征值问题。
    """

    def __init__(self, config: ModeConfig) -> None:
        self.config = config
        self.wavelength = config.wavelength
        self.dx, self.dy = config.grid_size
        self.wx, self.wy = config.window_size
        self.nx = int(round(self.wx / self.dx))
        self.ny = int(round(self.wy / self.dy))

    def compute_neff(
        self, width: float, core_index: float, cladding_index: float,
        wavelength: float | None = None, height: float = 0.22,
    ) -> float:
        """有效折射率（Marcatili 近似 + Goos-Hänchen 修正）。

        公式: n_eff² = n_core² - (π/(w·k₀+π/n_core))² - (π/(h·k₀+π/n_core))²
        来源: Marcatili 1969 Bell Syst Tech J 48 2071

        局限性说明（R02 学术诚信）:
        Marcatili 近似忽略角落区域渐逝场，对深蚀刻小波导（如 500×220nm SOI）
        会高估 n_eff（典型偏差 +0.4~+0.5）。例如对 500×220nm SOI 波导
        （n_core=3.48, n_clad=1.44, λ=1.55μm），Marcatili 给出 n_eff≈2.81，
        而实际值 ≈ 2.34（SiEPIC EBeam PDK 实测 / Soref 1991 IEEE JQE）。
        对高精度 n_eff，应使用 solve_waveguide() 的 FDFD 特征值分解或
        Lumerical MODE 全波求解器。
        """
        wl = wavelength if wavelength is not None else self.wavelength
        k0 = 2.0 * np.pi / wl
        w_eff = width * k0 + np.pi / core_index
        h_eff = height * k0 + np.pi / core_index
        n_eff_sq = core_index**2 - (np.pi / w_eff) ** 2 - (np.pi / h_eff) ** 2
        if n_eff_sq < cladding_index**2:
            raise ValueError(
                f"模式截止: n_eff²={n_eff_sq:.6e} < n_clad²={cladding_index**2:.6e}"
                f"（w={width}μm, h={height}μm, λ={wl}μm），波导尺寸过小或波长过长。"
            )
        return float(np.sqrt(n_eff_sq))

    def _build_index_grid(self, width: float, height: float,
                          core_index: float, cladding_index: float) -> np.ndarray:
        n_grid = np.full((self.nx, self.ny), cladding_index, dtype=np.float64)
        x = np.arange(self.nx) * self.dx
        y = np.arange(self.ny) * self.dy
        cx, cy = self.nx * self.dx / 2.0, self.ny * self.dy / 2.0
        core_mask = (np.abs(x - cx)[:, None] <= width / 2.0) & (
            np.abs(y - cy)[None, :] <= height / 2.0)
        n_grid[core_mask] = core_index
        return n_grid

    def _build_fdfd_matrix(self, n_grid: np.ndarray) -> np.ndarray:
        """FDFD 特征值矩阵（标量波动方程离散化）。"""
        nx, ny = n_grid.shape
        N = nx * ny
        k0 = 2.0 * np.pi / self.wavelength
        main_diag = -2.0 / self.dx**2 - 2.0 / self.dy**2 + k0**2 * n_grid.flatten()**2
        A = np.diag(main_diag)
        if N > ny:
            idx = np.arange(N - ny)
            A[idx, idx + ny] = A[idx + ny, idx] = 1.0 / self.dx**2
        if N > 1:
            idx = np.arange(N - 1)
            idx = idx[(idx + 1) % ny != 0]
            A[idx, idx + 1] = A[idx + 1, idx] = 1.0 / self.dy**2
        return A

    def solve_waveguide(self, width: float, height: float,
                        core_index: float, cladding_index: float) -> dict:
        """求解矩形波导模式（FDFD 特征值分解）。"""
        n_grid = self._build_index_grid(width, height, core_index, cladding_index)
        A = self._build_fdfd_matrix(n_grid)
        k0 = 2.0 * np.pi / self.wavelength
        eigenvalues, eigenvectors = np.linalg.eigh(A)
        n_eff_sq = eigenvalues / k0**2
        mask = (n_eff_sq > cladding_index**2) & (n_eff_sq < core_index**2)
        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            raise ValueError(
                f"未找到导模（n_clad={cladding_index}, n_core={core_index}, "
                f"w={width}μm, h={height}μm），请检查波导参数。")
        valid_indices = valid_indices[np.argsort(-eigenvalues[valid_indices])][: self.config.n_modes]
        n_eff = float(np.sqrt(n_eff_sq[valid_indices[0]]))
        mode_profile = eigenvectors[:, valid_indices[0]].reshape(self.nx, self.ny)
        norm = np.sqrt(np.sum(np.abs(mode_profile) ** 2))
        if norm > 0:
            mode_profile = mode_profile / norm
        return {"n_eff": n_eff, "mode_profile": mode_profile,
                "n_modes_found": len(valid_indices)}


# =============================================================================
# 3. Lumerical CHARGE（PN 结耗尽近似 + Soref-Bennett 等离子色散）
# =============================================================================
@dataclass
class CHARGEConfig:
    """Lumerical CHARGE 配置。URL: https://www.ansys.com/products/optics/charge"""
    temperature: float = 300.0
    doping_n: float = 1e18
    doping_p: float = 1e18
    confinement_factor: float = 0.3


class CHARGESimulator:
    """Lumerical CHARGE 对齐（电光协同仿真）。

    学术依据: Sze & Ng 2007 §3.4-3.5 / Soref & Bennett 1987 IEEE JQE
    """

    def __init__(self, config: CHARGEConfig) -> None:
        self.config = config
        self.T = config.temperature
        self.N_D = config.doping_n * 1e6  # cm⁻³ → m⁻³
        self.N_A = config.doping_p * 1e6
        self.Gamma = config.confinement_factor
        self.eps = _EPS_SI * _EPS0
        self.n_i = self._compute_intrinsic_carrier()

    def _compute_intrinsic_carrier(self) -> float:
        """本征载流子浓度 n_i = sqrt(N_C·N_V)·exp(-E_g/(2kT))。来源: Sze & Ng §1.4。"""
        E_g = 1.12 * _Q
        return float(np.sqrt(2.8e25 * 1.04e25) * np.exp(-E_g / (2.0 * _KB * self.T)))

    def _compute_build_in_potential(self) -> float:
        """内建电势 V_bi = (kT/q)·ln(N_A·N_D/n_i²)。来源: Sze & Ng §3.4。"""
        return float((_KB * self.T / _Q) * np.log(self.N_A * self.N_D / self.n_i**2))

    def compute_depletion_width(self, va: float = 0.0) -> float:
        """耗尽区宽度 W = sqrt(2ε(V_bi-V_a)/q · (1/N_A+1/N_D))。来源: Sze & Ng §3.4。"""
        v_bi = self._compute_build_in_potential()
        v_total = v_bi - va
        if v_total <= 0:
            raise ValueError(
                f"耗尽区消失: v_total={v_total:.4e} V ≤ 0（V_bi={v_bi:.4e}, "
                f"V_a={va:.4e}），PN 结正向导通，耗尽近似不成立。")
        return float(np.sqrt(
            2.0 * self.eps * v_total / _Q * (1.0 / self.N_A + 1.0 / self.N_D)))

    def compute_junction_capacitance(self, area: float, va: float = 0.0) -> float:
        """结电容 C_j = εA/W。来源: Sze & Ng §3.5。"""
        w = self.compute_depletion_width(va)
        if w < 1e-12:
            raise ValueError(f"耗尽区宽度 {w:.3e} m < 1e-12 m，非物理值。")
        return float(self.eps * area / w)

    def compute_modulator_bandwidth(self, r_series: float, c_j: float) -> float:
        """调制器带宽 f_3dB = 1/(2πRC)。来源: Sze & Ng §10.3。"""
        if r_series * c_j < 1e-30:
            raise ValueError(f"RC={r_series*c_j:.3e} s < 1e-30 s，非物理值。")
        return float(1.0 / (2.0 * np.pi * r_series * c_j))

    def electro_optic_simulation(self, modulator_config: dict) -> dict:
        """电光协同仿真（电压→Δn→相位调制）。

        物理流程（Sze & Ng §3.4 + Soref & Bennett 1987）:
        V → ΔW → ΔN_e=ΔP_h=N_eff·ΔW → Δn=dn_An·ΔN_e+dn_Ap·ΔP_h
        → Δn_eff=Γ·Δn → Δφ=(2π/λ)·Δn_eff·L
        """
        voltage = modulator_config.get("voltage", 1.0)
        length = modulator_config.get("length", 100.0)  # μm
        wavelength = modulator_config.get("wavelength", 1.55)  # μm
        width = modulator_config.get("width", 0.5)  # μm
        w_0 = self.compute_depletion_width(0.0)
        w_v = self.compute_depletion_width(-abs(voltage))
        delta_w = w_v - w_0
        n_eff_doping_cm3 = (self.N_D * self.N_A / (self.N_D + self.N_A)) * 1e-6
        delta_n_carrier = n_eff_doping_cm3 * delta_w * 1e2
        delta_n = _SOREF_DN_AN * delta_n_carrier + _SOREF_DN_AP * delta_n_carrier
        delta_n_eff = self.Gamma * delta_n
        delta_phi = (2.0 * np.pi / wavelength) * delta_n_eff * length
        area = width * 1e-6 * length * 1e-6 * 220e-9
        c_j = self.compute_junction_capacitance(area, -abs(voltage))
        r_series = 0.01 * 1e-2 * length * 1e-6 / area
        f_3db = self.compute_modulator_bandwidth(r_series, c_j)
        return {"voltage": voltage, "delta_w": delta_w, "delta_n": float(delta_n),
                "delta_n_eff": float(delta_n_eff), "phase_shift": float(delta_phi),
                "bandwidth": f_3db, "capacitance": c_j, "confinement_factor": self.Gamma}


# =============================================================================
# 4. Lumerical INTERCONNECT（PRBS + NRZ 调制 + BER + 链路仿真）
# =============================================================================
@dataclass
class INTERCONNECTConfig:
    """Lumerical INTERCONNECT 配置。

    URL: https://www.ansys.com/products/optics/interconnect
    """
    sample_rate: float = 1e12
    bit_rate: float = 10e9
    n_bits: int = 128
    modulation: str = "NRZ"


class INTERCONNECTSimulator:
    """Lumerical INTERCONNECT 对齐（光链路系统仿真）。

    学术依据: Agrawal 2010 §4.5-4.7 / ITU-T O.150 PRBS 标准
    """

    def __init__(self, config: INTERCONNECTConfig) -> None:
        self.config = config
        self.sample_rate = config.sample_rate
        self.bit_rate = config.bit_rate
        self.n_bits = config.n_bits
        self.modulation = config.modulation
        self.spp = int(self.sample_rate / self.bit_rate)

    def generate_prbs(self, n_bits: int) -> np.ndarray:
        """PRBS7 伪随机比特序列（LFSR，x^7+x^6+1）。来源: ITU-T O.150。"""
        register = np.array([1, 0, 1, 0, 1, 0, 1], dtype=np.uint8)
        bits = np.zeros(n_bits, dtype=np.uint8)
        for i in range(n_bits):
            bits[i] = register[0]
            feedback = register[0] ^ register[6]
            register = np.roll(register, -1)
            register[-1] = feedback
        return bits

    def modulate(self, bits: np.ndarray, modulation: str = "NRZ") -> np.ndarray:
        """调制（NRZ/PAM4/QAM16）。来源: Agrawal 2010 §4.6。"""
        bits = np.asarray(bits, dtype=np.float64)
        spp = self.spp
        if modulation == "NRZ":
            return np.repeat(2.0 * bits - 1.0, spp)
        if modulation == "PAM4":
            n_symbols = len(bits) // 2
            symbols = np.zeros(n_symbols)
            for i in range(n_symbols):
                symbols[i] = 2.0 * (bits[2*i] * 2 + bits[2*i+1]) - 3.0
            return np.repeat(symbols, spp)
        if modulation == "QAM16":
            n_symbols = len(bits) // 4
            signal = np.zeros(n_symbols * spp, dtype=complex)
            for i in range(n_symbols):
                re = 2.0 * bits[4*i] + bits[4*i+1] - 1.5
                im = 2.0 * bits[4*i+2] + bits[4*i+3] - 1.5
                signal[i*spp:(i+1)*spp] = complex(re, im)
            return signal
        raise ValueError(f"不支持调制格式: {modulation}（支持 NRZ/PAM4/QAM16）")

    def compute_ber(self, signal: np.ndarray, noise_sigma: float) -> float:
        """BER 估计（Q 因子法）。来源: Agrawal 2010 §4.6。"""
        if noise_sigma <= 0:
            raise ValueError(f"noise_sigma 须 > 0，得到 {noise_sigma}")
        threshold = np.mean(signal)
        high = signal[signal > threshold]
        low = signal[signal <= threshold]
        mean_high = float(np.mean(high)) if len(high) > 0 else 0.0
        mean_low = float(np.mean(low)) if len(low) > 0 else 0.0
        q_factor = abs(mean_high - mean_low) / (2.0 * noise_sigma)
        from scipy.special import erfc
        return float(0.5 * erfc(q_factor / np.sqrt(2.0)))

    def run_link_simulation(self, link_config: dict) -> dict:
        """运行完整光链路仿真（PRBS→调制→噪声→检测→BER）。

        来源: Agrawal 2010 §4.5-4.7 / Ansys Lumerical INTERCONNECT
        """
        n_bits = link_config.get("n_bits", self.n_bits)
        osnr_db = link_config.get("osnr_db", 30.0)
        modulation = link_config.get("modulation", self.modulation)
        bits = self.generate_prbs(n_bits)
        signal = self.modulate(bits, modulation)
        # ASE 噪声（Agrawal §4.5 OSNR → noise_sigma）
        noise_sigma = float(1.0 / (10.0 ** (osnr_db / 20.0)))
        noisy = signal + np.random.default_rng(42).normal(0, noise_sigma, signal.shape)
        ber = self.compute_ber(noisy.real if np.iscomplexobj(noisy) else noisy, noise_sigma)
        return {"ber": ber, "osnr_db": osnr_db, "n_bits": n_bits,
                "modulation": modulation, "signal_length": len(signal)}


# =============================================================================
# 5. LumericalIntegration（全流程 facade）
# =============================================================================
class LumericalIntegration:
    """Lumerical 全流程统一接口（MODE + CHARGE + INTERCONNECT）。

    学术依据: Ansys Lumerical 多物理场协同
    URL: https://optics.ansys.com/hc/en-us/articles/360042414214
    """

    def __init__(self) -> None:
        self.mode_solver: ModeSolver | None = None
        self.interconnect_sim: INTERCONNECTSimulator | None = None
        self.charge_sim: CHARGESimulator | None = None

    def full_flow(self, waveguide_config: dict, modulator_config: dict,
                  link_config: dict) -> dict:
        """运行完整 Lumerical 流程（MODE → CHARGE → INTERCONNECT）。"""
        mode_cfg = ModeConfig(
            wavelength=waveguide_config.get("wavelength", 1.55),
            grid_size=waveguide_config.get("grid_size", (0.05, 0.05)),
            n_modes=waveguide_config.get("n_modes", 4),
            window_size=waveguide_config.get("window_size", (1.6, 1.6)))
        self.mode_solver = ModeSolver(mode_cfg)
        mode_result = self.mode_solver.solve_waveguide(
            width=waveguide_config["width"],
            height=waveguide_config.get("height", 0.22),
            core_index=waveguide_config.get("core_index", _N_SILICON),
            cladding_index=waveguide_config.get("cladding_index", _N_SIO2))
        charge_cfg = CHARGEConfig(
            temperature=modulator_config.get("temperature", 300.0),
            doping_n=modulator_config.get("doping_n", 1e18),
            doping_p=modulator_config.get("doping_p", 1e18))
        self.charge_sim = CHARGESimulator(charge_cfg)
        eo_result = self.charge_sim.electro_optic_simulation(modulator_config)
        ic_cfg = INTERCONNECTConfig(
            sample_rate=link_config.get("sample_rate", 1e12),
            bit_rate=link_config.get("bit_rate", 10e9),
            n_bits=link_config.get("n_bits", 128),
            modulation=link_config.get("modulation", "NRZ"))
        self.interconnect_sim = INTERCONNECTSimulator(ic_cfg)
        link_result = self.interconnect_sim.run_link_simulation(link_config)
        return {"mode_result": mode_result, "eo_result": eo_result,
                "link_result": link_result}
