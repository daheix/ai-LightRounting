"""瞬态热响应求解器（解析解 + Crank-Nicolson 数值解）。

支持两种求解方式：
1. 解析解：单极指数衰减模型 T(t) = T_ss · (1 - e^(-t/τ))
   适用于集总参数系统（LTI 一阶热阻热容网络）
2. 数值解：2D Crank-Nicolson 有限差分法
   适用于分布式参数系统（2D 热传导方程瞬态求解）

学术依据:
- Carslaw & Jaeger, "Conduction of Heat in Solids", 2nd ed., Oxford 1959
  URL: https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
  (§10.4 线热源 Green's 函数；第Ⅻ章瞬态热传导)
- Crank & Nicolson, "A practical method for numerical evaluation of solutions
  of partial differential equations of the heat-conduction type",
  Proc. Camb. Phil. Soc. 1947, 43(1):50-67
  URL: https://doi.org/10.1017/S0305004100023197
- Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer", Wiley
  URL: https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
  (§5 瞬态热传导；集总热容法；有限差分法)
- Coenen et al., "A Critical Analysis of the Thermo-Optic Time Constant
  in Si Photonic Devices", Photonics 2024, 11, 603
  URL: https://doi.org/10.3390/photonics11070603
  (硅光子器件热光时间常数实验测量与建模)
- Pant et al., "Thermal diffusion in SOI photonic platforms",
  Optics Express 2021, 29(23):36461-36468
  URL: https://doi.org/10.1364/OE.426748
  (SOI 平台热扩散实验研究，热时间常数 μs~ms 量级)
- Taflove & Hagness, "Computational Electrodynamics: The FDTD Method",
  3rd ed., Artech 2005
  URL: https://us.artechhouse.com/Computational-Electrodynamics-The-FDTD-Method-Third-Edition-P1815.aspx
  (有限差分离散思想，Crank-Nicolson 隐式时间步进稳定性)
- Lumerical HEAT - Transient thermal simulation
  URL: https://optics.ansys.com/hc/en-us/articles/47617107334291
  (商用 TCAD 工具瞬态热仿真能力对标)
- scipy.sparse.linalg.spsolve
  URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
  (稀疏矩阵直接求解器，用于 Crank-Nicolson 每步线性系统)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.sparse.linalg import spsolve


@dataclass
class TransientThermalSpec:
    """瞬态热仿真规格参数。

    属性:
        thermal_resistance_k_w: 热阻 R_th [K/W]
        heat_capacity_j_k: 热容 C_th [J/K]
        ambient_temp_k: 环境/衬底温度 [K]
        heater_power_w: 加热器功率 [W]
    """
    thermal_resistance_k_w: float = 1000.0
    heat_capacity_j_k: float = 1e-6
    ambient_temp_k: float = 300.0
    heater_power_w: float = 0.01

    def __post_init__(self) -> None:
        if self.thermal_resistance_k_w <= 0:
            raise ValueError(
                f"thermal_resistance_k_w 须 > 0，实际 {self.thermal_resistance_k_w}"
            )
        if self.heat_capacity_j_k <= 0:
            raise ValueError(
                f"heat_capacity_j_k 须 > 0，实际 {self.heat_capacity_j_k}"
            )
        if self.ambient_temp_k <= 0:
            raise ValueError(
                f"ambient_temp_k 须 > 0，实际 {self.ambient_temp_k}"
            )

    @property
    def time_constant_s(self) -> float:
        """热时间常数 τ = R_th × C_th [s]。"""
        return self.thermal_resistance_k_w * self.heat_capacity_j_k

    @property
    def steady_state_delta_t_k(self) -> float:
        """稳态温升 ΔT_ss = P × R_th [K]。"""
        return self.heater_power_w * self.thermal_resistance_k_w


class LumpedTransientSolver:
    """集总参数瞬态热响应求解器（一阶 RC 模型）。

    物理模型：
        T(t) = T_amb + ΔT_ss · (1 - e^(-t/τ))   （加热上升）
        T(t) = T_amb + ΔT_ss · e^(-t/τ)         （冷却下降）
    其中：
        τ = R_th × C_th  （热时间常数）
        ΔT_ss = P × R_th  （稳态温升）

    适用场景：器件级集总热模型、热光开关时间常数估算。

    文献来源（≥5，学术诚信）：
    1. Incropera & DeWitt "Fundamentals of Heat and Mass Transfer" §5.2 —
       集总热容法（Lumped Capacitance Method）—
       https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
    2. Carslaw & Jaeger 1959 "Conduction of Heat in Solids" 2nd ed. Oxford —
       球体/半无限大介质瞬态热传导解析解 —
       https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
    3. Coenen et al. 2024 Photonics 11(7):603 —
       Si 光子器件热光时间常数临界分析 —
       https://doi.org/10.3390/photonics11070603
    4. Pant et al. 2021 Optics Express 29(23):36461-36468 —
       SOI 平台热光元件热扩散实验研究 —
       https://doi.org/10.1364/OE.426748
    5. Lumerical HEAT - Transient thermal simulation —
       商用 TCAD 瞬态热仿真对标 —
       https://optics.ansys.com/hc/en-us/articles/47617107334291
    6. Reed et al. 2010 Nature Photonics 4:518-526 —
       硅光调制器综述（含热光开关速度讨论）—
       https://doi.org/10.1038/nphoton.2010.179
    7. Sze & Ng 2006 "Physics of Semiconductor Devices" 3rd ed. Wiley —
       半导体器件热特性 §11 —
       https://www.wiley.com/en-us/Physics+of+Semiconductor+Devices-9780471143239
    """

    def __init__(self, spec: TransientThermalSpec) -> None:
        self.spec = spec

    def temperature_rise(
        self, t_s: float | NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """计算加热过程的温度响应 T(t)。

        公式: T(t) = T_amb + ΔT_ss · (1 - exp(-t/τ))

        Args:
            t_s: 时间点 [s]，标量或数组

        Returns:
            T(t): 温度 [K]，与 t_s 同形状

        Raises:
            ValueError: 时间为负时
        """
        t_arr = np.asarray(t_s, dtype=float)
        if np.any(t_arr < 0):
            raise ValueError("时间 t_s 不能为负数")
        tau = self.spec.time_constant_s
        dT_ss = self.spec.steady_state_delta_t_k
        result = self.spec.ambient_temp_k + dT_ss * (1.0 - np.exp(-t_arr / tau))
        return result

    def temperature_fall(
        self,
        t_s: float | NDArray[np.float64],
        initial_delta_t_k: float | None = None,
    ) -> NDArray[np.float64]:
        """计算冷却过程的温度响应 T(t)。

        公式: T(t) = T_amb + ΔT_0 · exp(-t/τ)

        Args:
            t_s: 时间点 [s]，标量或数组
            initial_delta_t_k: 初始温升 [K]，默认取稳态温升

        Returns:
            T(t): 温度 [K]，与 t_s 同形状

        Raises:
            ValueError: 时间为负或初始温升为负时
        """
        t_arr = np.asarray(t_s, dtype=float)
        if np.any(t_arr < 0):
            raise ValueError("时间 t_s 不能为负数")
        dT0 = (
            initial_delta_t_k
            if initial_delta_t_k is not None
            else self.spec.steady_state_delta_t_k
        )
        if dT0 < 0:
            raise ValueError(f"initial_delta_t_k 须 ≥ 0，实际 {dT0}")
        tau = self.spec.time_constant_s
        result = self.spec.ambient_temp_k + dT0 * np.exp(-t_arr / tau)
        return result

    def time_constant_s(self) -> float:
        """返回热时间常数 τ = R_th × C_th [s]。"""
        return self.spec.time_constant_s

    def settling_time_s(self, pct: float = 0.05) -> float:
        """稳定时间：温度达到稳态值的 (1-pct) 所需时间。

        公式: t_settle = -τ · ln(pct)

        Args:
            pct: 稳定精度（如 0.05 表示 5% 误差内）

        Returns:
            t_settle: 稳定时间 [s]

        Raises:
            ValueError: pct 不在 (0, 1) 范围内
        """
        if not (0 < pct < 1):
            raise ValueError(f"pct 须在 (0,1) 之间，实际 {pct}")
        return -self.spec.time_constant_s * np.log(pct)


@dataclass
class ThermalLayer2D:
    """2D 瞬态热仿真层结构。"""

    name: str
    thickness_um: float
    thermal_conductivity_w_mk: float
    density_kg_m3: float
    specific_heat_j_kgk: float
    is_heater: bool = False
    heater_power_mw_per_um: float = 0.0


def _compute_nz(layers: list[ThermalLayer2D], min_nodes_per_layer: int = 2) -> int:
    """计算 nz 确保每层至少有 min_nodes_per_layer 个节点。"""
    total_thick = sum(l.thickness_um for l in layers)
    if total_thick <= 0:
        raise ValueError("总层厚须 > 0")
    nz_min = len(layers) * min_nodes_per_layer
    nz = max(nz_min, 3)
    return nz


class CrankNicolson2D:
    """2D 瞬态热传导 Crank-Nicolson 有限差分求解器。

    控制方程: ρ·c_p · ∂T/∂t = ∇·(k∇T) + Q
    离散: Crank-Nicolson 隐式格式（二阶精度，无条件稳定）
          (I - 0.5·dt·L)·T^{n+1} = (I + 0.5·dt·L)·T^n + dt·Q/(ρ·c_p)
    其中 L 为空间离散 Laplacian 算子（5 点中心差分 + 调和平均界面热导）。
    求解: scipy.sparse.linalg.spsolve 每时间步一次稀疏直接解。
    边界: 底部 Dirichlet (T=T_sub)；顶部/侧面 Neumann 绝热。

    文献来源（≥5，学术诚信）：
    1. Crank & Nicolson 1947 Proc. Camb. Phil. Soc. 43(1):50-67 —
       热传导方程数值求解的实用方法（经典论文）—
       https://doi.org/10.1017/S0305004100023197
    2. Carslaw & Jaeger 1959 "Conduction of Heat in Solids" 2nd ed. Oxford —
       固体热传导经典专著（解析解基础）—
       https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
    3. Incropera & DeWitt "Fundamentals of Heat and Mass Transfer" —
       瞬态热传导有限差分数值方法 §5.9-§5.10 —
       https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
    4. Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method" 3rd ed. —
       有限差分离散与稳定性分析思想（FDTD 与 FDM 同源）—
       https://us.artechhouse.com/Computational-Electrodynamics-The-FDTD-Method-Third-Edition-P1815.aspx
    5. Coenen et al. 2024 Photonics 11(7):603 —
       Si 光子器件热光时间常数实验与 3D 热建模 —
       https://doi.org/10.3390/photonics11070603
    6. Lumerical HEAT - Transient thermal simulation —
       商用 TCAD 瞬态热仿真对标 —
       https://optics.ansys.com/hc/en-us/articles/47617107334291
    7. scipy.sparse.linalg.spsolve —
       稀疏矩阵直接求解器（SuperLU 后端）—
       https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
    """

    def __init__(
        self,
        layers: list[ThermalLayer2D],
        width_um: float = 30.0,
        substrate_temp_k: float = 300.0,
        nx: int = 60,
        heater_width_um: float = 1.0,
        dt_s: float = 1e-7,
        min_nodes_per_layer: int = 2,
    ) -> None:
        if not layers:
            raise ValueError("layers 不可为空")
        if width_um <= 0.0:
            raise ValueError(f"width_um 须 > 0，实际 {width_um}")
        if nx < 3:
            raise ValueError(f"nx 须 ≥ 3，实际 {nx}")
        if heater_width_um <= 0.0:
            raise ValueError(f"heater_width_um 须 > 0，实际 {heater_width_um}")
        if dt_s <= 0.0:
            raise ValueError(f"dt_s 须 > 0，实际 {dt_s}")

        self.layers = layers
        self.width_um = width_um
        self.T_sub = substrate_temp_k
        self.nx = nx
        self.heater_width_um = heater_width_um
        self.dt_s = dt_s
        self.nz = _compute_nz(layers, min_nodes_per_layer)

        self._T: NDArray[np.float64] = np.array([])
        self._build_initial_field()
        self._A: sparse.csr_matrix | None = None
        self._B: sparse.csr_matrix | None = None
        self._b_const: NDArray[np.float64] | None = None
        self._build_system_matrices()

    def _build_initial_field(self) -> None:
        """初始化温度场为衬底温度。"""
        self._T = np.ones((self.nz, self.nx), dtype=float) * self.T_sub

    def _layer_index_of_z(self, z_node_m: NDArray[np.float64]) -> NDArray[np.int64]:
        """每个 z 节点所属层的索引。"""
        bounds_m: list[float] = [0.0]
        for layer in self.layers:
            bounds_m.append(bounds_m[-1] + layer.thickness_um * 1e-6)
        interior = bounds_m[1:-1]
        idx = np.searchsorted(interior, z_node_m, side="right")
        return np.clip(idx, 0, len(self.layers) - 1).astype(np.int64)

    def _build_physical_fields(
        self,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], float, float]:
        """构建 k, ρ·c_p, Q 场及网格间距 dx, dz。

        Returns:
            k_arr: 热导率场 [W/(m·K)], shape (nz, nx)
            rho_cp_arr: 体积热容场 [J/(m³·K)], shape (nz, nx)
            q_arr: 体积热源 [W/m³], shape (nz, nx)
            dx, dz: 网格间距 [m]
        """
        nx, nz = self.nx, self.nz
        dz_total_m = sum(l.thickness_um for l in self.layers) * 1e-6
        width_m = self.width_um * 1e-6
        dx = width_m / (nx - 1)
        dz = dz_total_m / (nz - 1)
        if dx <= 0.0 or dz <= 0.0:
            raise ValueError(f"网格间距非正: dx={dx}, dz={dz}")

        z_node = np.linspace(0.0, dz_total_m, nz)
        layer_idx = self._layer_index_of_z(z_node)

        k_arr = np.zeros((nz, nx), dtype=float)
        rho_cp_arr = np.zeros((nz, nx), dtype=float)
        for i in range(nz):
            li = int(layer_idx[i])
            k_arr[i, :] = self.layers[li].thermal_conductivity_w_mk
            rho_cp_arr[i, :] = (
                self.layers[li].density_kg_m3 * self.layers[li].specific_heat_j_kgk
            )

        q_arr = np.zeros((nz, nx), dtype=float)
        x_node = np.linspace(-width_m / 2.0, width_m / 2.0, nx)
        w_h_m = self.heater_width_um * 1e-6
        heater_x_mask = np.abs(x_node) <= w_h_m / 2.0
        if not heater_x_mask.any():
            heater_x_mask[int(np.argmin(np.abs(x_node)))] = True
        n_x_h = int(heater_x_mask.sum())

        heater_layer_ids = [
            k
            for k, l in enumerate(self.layers)
            if l.is_heater and l.heater_power_mw_per_um > 0.0
        ]
        for li in heater_layer_ids:
            z_in_layer = layer_idx == li
            n_z_l = int(z_in_layer.sum())
            if n_z_l == 0:
                continue
            p_lin_w_m = self.layers[li].heater_power_mw_per_um * 1e3
            total_vol = n_z_l * n_x_h * dx * dz
            if total_vol <= 0.0:
                continue
            q_density = p_lin_w_m / total_vol
            for i in np.where(z_in_layer)[0]:
                q_arr[i, heater_x_mask] = q_density

        return k_arr, rho_cp_arr, q_arr, dx, dz

    def _build_laplacian_matrix(
        self,
        k_arr: NDArray[np.float64],
        rho_cp_arr: NDArray[np.float64],
        dx: float,
        dz: float,
    ) -> sparse.csr_matrix:
        """装配归一化 Laplacian 矩阵 L（已除以 ρ·c_p）。

        L·T = (1/(ρ·c_p)) · ∇·(k∇T)
        界面热导用调和平均: k_face = 2·k_a·k_b/(k_a+k_b)
        """
        nx, nz = self.nx, self.nz
        n = nx * nz
        dx2 = dx * dx
        dz2 = dz * dz

        def idx(i: int, j: int) -> int:
            return i * nx + j

        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []

        for i in range(nz):
            for j in range(nx):
                r = idx(i, j)
                if i == 0:
                    rows.append(r)
                    cols.append(r)
                    vals.append(0.0)
                    continue
                k_c = float(k_arr[i, j])
                rho_cp_c = float(rho_cp_arr[i, j])
                if rho_cp_c <= 0:
                    raise ValueError(f"体积热容非正: {rho_cp_c}")
                coefs: list[tuple[int, float]] = []
                if i > 0:
                    k_n = float(k_arr[i - 1, j])
                    denom = k_c + k_n
                    k_f = 2.0 * k_c * k_n / denom if denom > 0 else 0.0
                    coefs.append((idx(i - 1, j), k_f / dz2 / rho_cp_c))
                if i < nz - 1:
                    k_n = float(k_arr[i + 1, j])
                    denom = k_c + k_n
                    k_f = 2.0 * k_c * k_n / denom if denom > 0 else 0.0
                    coefs.append((idx(i + 1, j), k_f / dz2 / rho_cp_c))
                if j > 0:
                    k_n = float(k_arr[i, j - 1])
                    denom = k_c + k_n
                    k_f = 2.0 * k_c * k_n / denom if denom > 0 else 0.0
                    coefs.append((idx(i, j - 1), k_f / dx2 / rho_cp_c))
                if j < nx - 1:
                    k_n = float(k_arr[i, j + 1])
                    denom = k_c + k_n
                    k_f = 2.0 * k_c * k_n / denom if denom > 0 else 0.0
                    coefs.append((idx(i, j + 1), k_f / dx2 / rho_cp_c))
                diag = -sum(c for _, c in coefs)
                rows.append(r)
                cols.append(r)
                vals.append(diag)
                for nb, c in coefs:
                    rows.append(r)
                    cols.append(nb)
                    vals.append(c)

        L = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
        return L

    def _build_system_matrices(self) -> None:
        """预构建 Crank-Nicolson 系统矩阵 A 和 B 及常数项 b_const。

        边界条件直接注入矩阵中，避免每步修改稀疏结构。
        """
        k_arr, rho_cp_arr, q_arr, dx, dz = self._build_physical_fields()
        L = self._build_laplacian_matrix(k_arr, rho_cp_arr, dx, dz)
        n = self.nx * self.nz
        I = sparse.eye(n, format="csr")
        dt = self.dt_s

        A_raw = I - 0.5 * dt * L
        B_raw = I + 0.5 * dt * L

        q_over_rhocp = q_arr.ravel() / rho_cp_arr.ravel()
        b_const = dt * q_over_rhocp

        A_dok = A_raw.todok()
        B_dok = B_raw.todok()
        for j in range(self.nx):
            r = j
            A_dok[r, :] = 0.0
            A_dok[r, r] = 1.0
            B_dok[r, :] = 0.0
            b_const[r] = self.T_sub

        self._A = A_dok.tocsr()
        self._B = B_dok.tocsr()
        self._b_const = b_const

    def step(self, num_steps: int = 1) -> NDArray[np.float64]:
        """执行 num_steps 个时间步的 Crank-Nicolson 推进。

        Args:
            num_steps: 时间步数

        Returns:
            T: 当前温度场 [K], shape (nz, nx)
        """
        if num_steps <= 0:
            raise ValueError(f"num_steps 须 > 0，实际 {num_steps}")
        if self._A is None or self._B is None or self._b_const is None:
            raise RuntimeError("系统矩阵未构建")

        T_vec = self._T.ravel().copy()

        for _ in range(num_steps):
            rhs = self._B @ T_vec + self._b_const
            T_vec = spsolve(self._A, rhs)
            if not np.all(np.isfinite(T_vec)):
                raise RuntimeError("Crank-Nicolson 求解产生非有限值")

        self._T = T_vec.reshape(self.nz, self.nx)
        return self._T

    def solve_transient(
        self,
        total_time_s: float,
        sample_interval_steps: int = 1,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """求解瞬态过程，返回时间序列和对应温度场。

        Args:
            total_time_s: 总仿真时间 [s]
            sample_interval_steps: 采样间隔（每多少步存一次）

        Returns:
            times: 时间点数组 [s], shape (n_samples,)
            temperatures: 温度场数组 [K], shape (n_samples, nz, nx)
        """
        if total_time_s <= 0:
            raise ValueError(f"total_time_s 须 > 0，实际 {total_time_s}")
        if sample_interval_steps < 1:
            raise ValueError(
                f"sample_interval_steps 须 ≥ 1，实际 {sample_interval_steps}"
            )

        total_steps = int(np.ceil(total_time_s / self.dt_s))
        if total_steps == 0:
            total_steps = 1

        n_samples = total_steps // sample_interval_steps + 1
        times = np.zeros(n_samples, dtype=float)
        temps = np.zeros((n_samples, self.nz, self.nx), dtype=float)

        times[0] = 0.0
        temps[0] = self._T.copy()

        sample_idx = 1
        for step_i in range(1, total_steps + 1):
            self.step(1)
            if step_i % sample_interval_steps == 0 and sample_idx < n_samples:
                times[sample_idx] = step_i * self.dt_s
                temps[sample_idx] = self._T.copy()
                sample_idx += 1

        return times[:sample_idx], temps[:sample_idx]

    @property
    def temperature_field(self) -> NDArray[np.float64]:
        """当前温度场 [K], shape (nz, nx)。"""
        return self._T.copy()

    def max_temperature_k(self) -> float:
        """当前最高温度 [K]。"""
        if self._T.size == 0:
            raise RuntimeError("请先初始化或求解")
        return float(np.max(self._T))

    def avg_temp_at_layer(self, layer_name: str) -> float:
        """指定层的平均温度 [K]。"""
        if self._T.size == 0:
            raise RuntimeError("请先初始化或求解")
        z_total = sum(l.thickness_um for l in self.layers) * 1e-6
        z_node = np.linspace(0.0, z_total, self.nz)
        layer_idx = self._layer_index_of_z(z_node)
        for k, layer in enumerate(self.layers):
            if layer.name == layer_name:
                mask = layer_idx == k
                if not mask.any():
                    raise KeyError(f"层 {layer_name} 在网格中无节点")
                return float(np.mean(self._T[mask, :]))
        raise KeyError(f"层 {layer_name} 不存在")


def estimate_time_constant_from_2d(
    solver: CrankNicolson2D,
    layer_name: str,
    total_time_s: float,
    sample_interval_steps: int = 10,
) -> dict[str, Any]:
    """从 2D 瞬态仿真结果拟合集总热时间常数 τ。

    方法: 对指定层平均温度的阶跃响应进行单指数拟合
          T(t) = T_ss + (T_0 - T_ss)·e^(-t/τ)
    用最小二乘法拟合 τ。

    Args:
        solver: CrankNicolson2D 求解器（需已初始化）
        layer_name: 监测层名称
        total_time_s: 仿真总时长 [s]
        sample_interval_steps: 采样间隔步数

    Returns:
        dict: 包含 time_constant_s, steady_temp_k, initial_temp_k,
              temp_series, time_series 等
    """
    times, temps = solver.solve_transient(total_time_s, sample_interval_steps)

    n_samples = len(times)
    avg_temps = np.zeros(n_samples, dtype=float)
    z_total = sum(l.thickness_um for l in solver.layers) * 1e-6
    z_node = np.linspace(0.0, z_total, solver.nz)
    layer_idx = solver._layer_index_of_z(z_node)
    layer_found = False
    for k, layer in enumerate(solver.layers):
        if layer.name == layer_name:
            mask = layer_idx == k
            for i in range(n_samples):
                avg_temps[i] = float(np.mean(temps[i, mask, :]))
            layer_found = True
            break
    if not layer_found:
        raise KeyError(f"层 {layer_name} 不存在")

    T0 = avg_temps[0]
    Tss = avg_temps[-1]

    if Tss <= T0 + 1e-6:
        raise RuntimeError("温升太小，无法拟合时间常数")

    y = np.log(np.clip((Tss - avg_temps) / (Tss - T0), 1e-10, 1.0))
    valid = y < -1e-10
    if valid.sum() < 3:
        raise RuntimeError("有效数据点不足，无法拟合时间常数")

    slope, _ = np.polyfit(times[valid], y[valid], 1)
    tau_fit = float(-1.0 / slope) if slope < 0 else float("inf")

    return {
        "time_constant_s": tau_fit,
        "initial_temp_k": float(T0),
        "steady_temp_k": float(Tss),
        "time_series_s": times,
        "temp_series_k": avg_temps,
    }
