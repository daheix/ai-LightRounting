"""R31 路标：Ansys Lumerical MODE Solutions 对齐（波导模式求解器）。

提供 Lumerical MODE Solutions 的波导模式求解能力，使用有限差分频域（FDFD）
特征值分解方法求解 Maxwell 方程，对标商业 MODE 求解器。

## 学术依据

- Ansys Lumerical MODE Solutions: https://www.ansys.com/products/optics/mode
- Silvester & Ferrari, "Finite Elements for Electrical Engineers", 1996
- Marcatili, Bell Syst. Tech. J. 48, 2071 (1969)
- Snyder & Love, "Optical Waveguide Theory", 1983, §13.5
- Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010, §2.4

## 求解方法

将标量波动方程 ∇²E + k₀²n²(r)E = k₀²n_eff²E 离散化为矩阵特征值问题
A·E = λ·E，其中 λ = k₀²n_eff²，用 numpy.linalg.eigh 求解实对称矩阵特征值。

## 物理常数

共享常量定义在 ``lumerical_constants`` 模块，本模块仅引用 ``_C0``/``_N_SILICON``
/``_N_SIO2``。

## 🚫不参与 GPU（R04）

纯 NumPy 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from polaris.sim.lumerical_constants import _C0, _N_SILICON, _N_SIO2

logger = logging.getLogger(__name__)


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
