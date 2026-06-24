"""Tidy3D 集成与 GPU FDTD 引擎（R27+R28 路标）。

对标 Tidy3D 云端 FDTD 仿真平台的集成接口，并提供本地 GPU 加速 FDTD 引擎
与多后端交叉验证能力。

## 模块组成

1. ``Tidy3DConfig`` — Tidy3D 仿真配置（网格/边界/光源/monitor）
2. ``Tidy3DAdapter`` — 器件到 FDTD 仿真对象的适配器（几何→介电常数分布）
3. ``Tidy3DAsyncRunner`` — 异步仿真运行器（提交/轮询/收集结果）
4. ``GPUFDTDConfig`` — GPU FDTD 引擎配置
5. ``GPUFDTDEngine`` — GPU 加速 FDTD 引擎（向量化 Yee 算法）
6. ``FDTDCrossValidator`` — 多后端交叉验证器（FDTD vs 解析模型）

## 学术依据

- Tidy3D FDTD 平台: https://www.flexcompute.com/tidy3d/
  Flexcompute, "Tidy3D: Fast FDTD Simulation in the Cloud"
- Yee 算法: K. S. Yee, "Numerical solution of initial boundary value
  problems involving Maxwell's equations in isotropic media",
  IEEE Trans. Antennas Propag. 14(3), 302-307, 1966,
  https://doi.org/10.1109/TAP.1966.1138693
- GPU 加速 FDTD: A. F. Oskooi et al., "MEEP: A flexible free-software
  package for electromagnetic simulations by the FDTD method",
  Computer Physics Communications 181(3), 687-702, 2010,
  https://doi.org/10.1016/j.cpc.2009.11.008
- 交叉验证方法论: D. M. Sullivan, "Electromagnetic Simulation Using
  the FDTD Method", IEEE Press, 2013, §2.5

来源:
- Tidy3D 文档: https://docs.flexcompute.com/projects/tidy3d/
- MEEP 文档: https://meep.readthedocs.io/
- Lumerical FDTD: https://www.ansys.com/products/optics/fdtd
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# 物理常数（来源: CODATA 2018, SiPANN/SiEPIC PDK 标准值）
_C0 = 2.99792458e8  # 真空光速 (m/s)
_N_SILICON = 3.48  # 硅折射率 @ 1.55μm (SiEPIC EBeam PDK)
_N_SIO2 = 1.44  # 二氧化硅折射率 @ 1.55μm
_N_AIR = 1.0  # 空气折射率


# ---------------------------------------------------------------------------
# Tidy3DConfig — Tidy3D 仿真配置
# ---------------------------------------------------------------------------


@dataclass
class Tidy3DConfig:
    """Tidy3D 仿真配置。

    对标 Tidy3D ``Simulation`` 对象的配置参数，定义网格、边界条件、
    光源与 monitor 的设置。

    学术依据: Tidy3D Simulation API,
    https://docs.flexcompute.com/projects/tidy3d/en/latest/api/

    Attributes:
        wavelength_um: 中心波长（μm）。
        wavelength_span_um: 波长范围（μm）。
        n_wavelengths: 波长采样点数。
        grid_size_um: 网格尺寸（μm），通常 λ/20。
        pml_layers: PML 吸收边界层数。
        simulation_time_fs: 仿真时长（fs）。
        boundary_type: 边界类型（"PML"）。
    """

    wavelength_um: float = 1.55
    wavelength_span_um: float = 0.1
    n_wavelengths: int = 11
    grid_size_um: float = 0.05
    pml_layers: int = 10
    simulation_time_fs: float = 100.0
    boundary_type: str = "PML"

    @property
    def wavelengths(self) -> np.ndarray:
        """波长数组（μm）。"""
        wl0 = self.wavelength_um
        span = self.wavelength_span_um
        return np.linspace(wl0 - span / 2, wl0 + span / 2, self.n_wavelengths)

    @property
    def frequency_hz(self) -> np.ndarray:
        """频率数组（Hz）。"""
        return _C0 / (self.wavelengths * 1e-6)

    @property
    def n_grid(self) -> int:
        """一维网格点数（基于仿真时长与网格尺寸）。"""
        t_total = self.simulation_time_fs * 1e-15  # s
        dx = self.grid_size_um * 1e-6  # m
        dt = dx / (2 * _C0)  # CFL 稳定条件
        return max(int(t_total / dt), 100)


# ---------------------------------------------------------------------------
# Tidy3DAdapter — 器件到 FDTD 仿真对象的适配器
# ---------------------------------------------------------------------------


@dataclass
class Tidy3DAdapter:
    """器件到 FDTD 仿真对象的适配器。

    将器件几何参数转换为 FDTD 网格上的介电常数分布（permittivity map），
    供 FDTD 引擎使用。

    学术依据: Tidy3D 结构定义,
    https://docs.flexcompute.com/projects/tidy3d/en/latest/

    Attributes:
        config: Tidy3D 仿真配置。
    """

    config: Tidy3DConfig = field(default_factory=Tidy3DConfig)

    def adapt_layered_stack(
        self,
        params: np.ndarray,
        n_low: float = _N_SIO2,
        n_high: float = _N_SILICON,
    ) -> np.ndarray:
        """将设计参数适配为一维层叠介电常数分布。

        设计参数 θ∈[0,1]^N 映射为各层折射率 n_i = n_low + θ_i·(n_high-n_low)，
        介电常数 ε_i = n_i²。

        Args:
            params: 设计参数数组 θ∈[0,1]^N。
            n_low: 低折射率材料（SiO₂）。
            n_high: 高折射率材料（Si）。

        Returns:
            介电常数数组 ε。
        """
        n = n_low + params * (n_high - n_low)
        return n ** 2

    def adapt_waveguide(
        self,
        length_um: float = 100.0,
        width_um: float = 0.5,
        n_core: float = _N_SILICON,
        n_clad: float = _N_SIO2,
    ) -> dict:
        """将波导几何适配为二维介电常数分布描述。

        Args:
            length_um: 波导长度（μm）。
            width_um: 波导宽度（μm）。
            n_core: 芯层折射率。
            n_clad: 包层折射率。

        Returns:
            含 ``eps_map``（介电常数 2D 数组）、``grid_x``、``grid_y``
            的字典。
        """
        dx = self.config.grid_size_um
        nx = max(int(length_um / dx), 10)
        ny = max(int(width_um / dx * 4), 10)
        grid_x = np.linspace(0, length_um, nx)
        grid_y = np.linspace(-width_um * 2, width_um * 2, ny)
        eps_map = np.full((ny, nx), n_clad ** 2)
        # 芯层区域
        core_mask = np.abs(grid_y) <= width_um / 2
        eps_map[core_mask, :] = n_core ** 2
        return {
            "eps_map": eps_map,
            "grid_x": grid_x,
            "grid_y": grid_y,
            "n_core": n_core,
            "n_clad": n_clad,
        }

    def build_simulation(self, params: np.ndarray) -> dict:
        """构建完整仿真任务描述。

        Args:
            params: 设计参数数组。

        Returns:
            仿真任务字典（含 config、permittivity、source、monitor）。
        """
        eps = self.adapt_layered_stack(params)
        return {
            "config": self.config,
            "permittivity": eps,
            "source": {
                "type": "gaussian_pulse",
                "wavelength_um": self.config.wavelength_um,
                "position": 0,
            },
            "monitors": [
                {"type": "transmission", "position": len(eps), "name": "out"},
            ],
        }


# ---------------------------------------------------------------------------
# Tidy3DAsyncRunner — 异步仿真运行器
# ---------------------------------------------------------------------------


@dataclass
class Tidy3DAsyncRunner:
    """Tidy3D 异步仿真运行器。

    对标 Tidy3D Web API 的异步任务提交模式：提交仿真任务后返回任务 ID，
    轮询任务状态，完成后收集结果。本地执行时使用线程实现真正的异步。

    学术依据: Tidy3D Web API,
    https://docs.flexcompute.com/projects/tidy3d/en/latest/api/web.html

    Attributes:
        adapter: Tidy3D 适配器。
        poll_interval_s: 轮询间隔（秒）。
    """

    adapter: Tidy3DAdapter = field(default_factory=Tidy3DAdapter)
    poll_interval_s: float = 0.01
    _tasks: dict[str, dict] = field(default_factory=dict, repr=False)

    def submit(self, params: np.ndarray, task_id: str | None = None) -> str:
        """提交仿真任务。

        Args:
            params: 设计参数数组。
            task_id: 自定义任务 ID，None 时自动生成。

        Returns:
            任务 ID。
        """
        if task_id is None:
            task_id = f"task_{len(self._tasks)}_{int(time.time() * 1000) % 100000}"
        sim = self.adapter.build_simulation(params)
        self._tasks[task_id] = {
            "status": "queued",
            "sim": sim,
            "result": None,
            "error": None,
        }
        # 启动后台线程执行仿真
        thread = threading.Thread(
            target=self._run_task, args=(task_id,), daemon=True
        )
        thread.start()
        return task_id

    def _run_task(self, task_id: str) -> None:
        """在后台线程中执行仿真任务。"""
        task = self._tasks[task_id]
        task["status"] = "running"
        try:
            # 使用 GPU FDTD 引擎执行仿真
            engine = GPUFDTDEngine(GPUFDTDConfig(
                wavelength_um=self.adapter.config.wavelength_um,
                n_steps=self.adapter.config.n_grid,
            ))
            params = task["sim"]["permittivity"]
            # 从介电常数反推设计参数（用于 FDTD 正向仿真）
            n = np.sqrt(np.real(params))
            n_low, n_high = _N_SIO2, _N_SILICON
            design_params = (n - n_low) / (n_high - n_low)
            result = engine.run(design_params)
            task["result"] = result
            task["status"] = "completed"
        except Exception as exc:  # noqa: BLE001
            task["error"] = str(exc)
            task["status"] = "error"

    def get_status(self, task_id: str) -> str:
        """查询任务状态。

        Args:
            task_id: 任务 ID。

        Returns:
            状态字符串（queued/running/completed/error）。

        Raises:
            KeyError: 任务 ID 不存在时。
        """
        if task_id not in self._tasks:
            raise KeyError(f"任务 '{task_id}' 不存在")
        return self._tasks[task_id]["status"]

    def get_result(self, task_id: str, timeout_s: float = 30.0) -> dict:
        """等待并获取任务结果。

        Args:
            task_id: 任务 ID。
            timeout_s: 最大等待时间（秒）。

        Returns:
            仿真结果字典。

        Raises:
            TimeoutError: 超时未完成。
            RuntimeError: 任务执行出错。
        """
        if task_id not in self._tasks:
            raise KeyError(f"任务 '{task_id}' 不存在")
        elapsed = 0.0
        while self._tasks[task_id]["status"] not in ("completed", "error"):
            if elapsed >= timeout_s:
                raise TimeoutError(f"任务 '{task_id}' 超时（{timeout_s}s）")
            time.sleep(self.poll_interval_s)
            elapsed += self.poll_interval_s
        task = self._tasks[task_id]
        if task["status"] == "error":
            raise RuntimeError(f"任务 '{task_id}' 执行失败: {task['error']}")
        return task["result"]

    def run_sync(self, params: np.ndarray) -> dict:
        """同步执行仿真（提交并等待完成）。

        Args:
            params: 设计参数数组。

        Returns:
            仿真结果字典。
        """
        task_id = self.submit(params)
        return self.get_result(task_id)


# ---------------------------------------------------------------------------
# GPUFDTDConfig — GPU FDTD 引擎配置
# ---------------------------------------------------------------------------


@dataclass
class GPUFDTDConfig:
    """GPU FDTD 引擎配置。

    定义本地向量化 FDTD 引擎的参数。引擎使用 Yee 算法在 numpy 向量化
    实现，模拟 GPU 并行计算模式。

    学术依据: Yee 1966 IEEE TAP,
    https://doi.org/10.1109/TAP.1966.1138693

    Attributes:
        wavelength_um: 中心波长（μm）。
        n_steps: FDTD 时间步数。
        dx_um: 空间步长（μm）。
        n_layers: 设计区域层数。
    """

    wavelength_um: float = 1.55
    n_steps: int = 500
    dx_um: float = 0.05
    n_layers: int = 50

    @property
    def dt_fs(self) -> float:
        """时间步长（fs），满足 CFL 稳定条件 dt < dx/(2c)。"""
        dx_m = self.dx_um * 1e-6
        dt_s = dx_m / (2.0 * _C0)
        return dt_s * 1e15


# ---------------------------------------------------------------------------
# GPUFDTDEngine — GPU 加速 FDTD 引擎
# ---------------------------------------------------------------------------


@dataclass
class GPUFDTDEngine:
    """GPU 加速 FDTD 引擎（向量化 Yee 算法）。

    使用一维 Yee 网格的向量化 numpy 实现 FDTD 电磁仿真，
    计算多层介电结构在指定波长处的传输率。

    学术依据:
    - Yee 1966: https://doi.org/10.1109/TAP.1966.1138693
    - Taflove & Hagness, "Computational Electrodynamics: The FDTD Method",
      Artech House, 3rd ed., 2005, §3

    一维 Yee 算法更新方程:
        H_z^{n+1/2}[i] = H_z^{n-1/2}[i] + (dt/(μ·dx))·(E_y^{n}[i+1] - E_y^{n}[i])
        E_y^{n+1}[i] = E_y^{n}[i] + (dt/(ε[i]·dx))·(H_z^{n+1/2}[i] - H_z^{n+1/2}[i-1])

    Attributes:
        config: GPU FDTD 配置。
    """

    config: GPUFDTDConfig = field(default_factory=GPUFDTDConfig)

    # 物理常数（SI 单位）
    _MU0: float = field(default=4e-7 * np.pi, repr=False)
    _EPS0: float = field(default=8.854e-12, repr=False)

    def _run_fdtd(
        self, eps_full: np.ndarray, dx_um: float | None = None
    ) -> tuple[float, np.ndarray]:
        """执行一维 Yee FDTD 仿真，返回探测器稳态幅度与最终电场分布。

        使用 Mur 一阶吸收边界条件（ABC）+ 边界源注入（TFSF 简化形式）
        激励已知入射平面波，等待瞬态衰减后测量探测器位置的稳态电场
        幅度（峰峰值法）。此方法确保入射波幅度不依赖结构阻抗。

        学术依据:
        - Mur 1981 一阶 ABC: G. Mur, IEEE Trans. Electromagn. Compat.
          23(4), 377-382, 1981, https://doi.org/10.1109/TEMC.1981.303970
        - Taflove & Hagness, "Computational Electrodynamics",
          Artech House, 3rd ed., 2005, §5.7 稳态幅度, §6.2 Mur ABC, §5.6 TFSF
        - TFSF 方法: Taflove 2005 §5.6, 边界源注入为 1D TFSF 简化形式

        Args:
            eps_full: 完整网格介电常数数组（含入射区/设计区/出射区/padding）。
            dx_um: 空间步长（μm），None 时使用 ``config.dx_um``。

        Returns:
            (探测器稳态电场幅度, 最终电场分布数组)。
        """
        if dx_um is None:
            dx_um = self.config.dx_um
        n_total = len(eps_full)
        n_pad = 50  # 两侧 padding

        dx = dx_um * 1e-6  # m
        # CFL 稳定条件：dt <= dx / (c · n_max)，n_max = _N_SILICON
        dt = dx / (2.0 * _C0 * _N_SILICON)
        wl = self.config.wavelength_um * 1e-6  # m
        freq = _C0 / wl
        omega = 2.0 * np.pi * freq
        period = 1.0 / freq

        det_idx = n_total - n_pad - 5  # 探测器在出射区

        # Mur 一阶 ABC 系数（来源: Mur 1981 IEEE EMC）
        n_left = float(np.sqrt(np.real(eps_full[0])))
        n_right = float(np.sqrt(np.real(eps_full[-1])))
        v_left = _C0 / n_left
        v_right = _C0 / n_right
        coef_left = (v_left * dt - dx) / (v_left * dt + dx)
        coef_right = (v_right * dt - dx) / (v_right * dt + dx)

        # CW 仿真：100 个周期，前 80 个周期等待稳态建立，后 20 个周期测量
        steps_per_period = max(int(period / dt), 20)
        n_steps = 100 * steps_per_period
        steady_start = 80 * steps_per_period

        e = np.zeros(n_total)  # 电场 E_y（实数）
        h = np.zeros(n_total - 1)  # 磁场 H_z（实数）

        # 稳态幅度测量（峰峰值法）
        det_max = 0.0
        det_min = 0.0

        for step in range(n_steps):
            t = step * dt
            # 保存边界旧值（Mur ABC 需要 n 时刻值）
            e_0_old = e[0]
            e_nm1_old = e[-1]
            e_1_old = e[1]
            e_nm2_old = e[-2]

            # 更新 H 场: H^{n+1/2} = H^{n-1/2} + (dt/(μ₀·dx))·(E^n[i+1] - E^n[i])
            h += (dt / (self._MU0 * dx)) * (e[1:] - e[:-1])
            # 更新 E 场（内部点）: E^{n+1}[i] = E^n[i] + (dt/(ε[i]·ε₀·dx))·(H^{n+1/2}[i] - H^{n+1/2}[i-1])
            e[1:-1] += (dt / (eps_full[1:-1] * self._EPS0 * dx)) * (h[1:] - h[:-1])

            # Mur 一阶 ABC + 源注入（1D TFSF 简化形式，来源: Taflove 2005 §5.6）
            # 左边界: ABC 吸收反向波 + 源注入正向波
            e[0] = e_1_old + coef_left * (e[1] - e_0_old) + np.sin(omega * t)
            # 右边界: ABC 吸收正向波
            e[-1] = e_nm2_old + coef_right * (e[-2] - e_nm1_old)

            # 稳态幅度测量（记录峰峰值）
            if step >= steady_start:
                det_val = e[det_idx]
                if det_val > det_max:
                    det_max = det_val
                if det_val < det_min:
                    det_min = det_val

        det_amplitude = (det_max - det_min) / 2.0
        return det_amplitude, e.copy()

    def run(self, params: np.ndarray) -> dict:
        """执行 FDTD 仿真（双仿真法：参考 + 样品）。

        通过运行两次仿真——参考（全空气，无结构）与样品（含设计层 + SiO₂ 基底）
        ——计算绝对传输率 T = (A_sample / A_ref)²，与传输矩阵法（TMM）的
        绝对传输率定义一致。此方法是商业 FDTD 软件（MEEP、Lumerical）的
        标准传输率提取方法。

        空间步长 ``dx_um`` 设为 TMM 四分之一波层厚度的 1/8，即每个 TMM 层
        用 8 个 FDTD cell 建模（32 cells/λ in Si），确保数值色散误差 < 0.5%
        （来源: Taflove 2005 §4.2 数值色散分析）。

        Args:
            params: 设计参数 θ∈[0,1]^N。

        Returns:
            含 ``transmission``（传输率）、``reflection``（反射率）、
            ``field``（电场分布）、``n_steps`` 的字典。
        """
        params = np.asarray(params, dtype=float)
        # 与 TMM _transfer_matrix_transmission 一致的材料映射:
        # medium = (N_AIR, N_SILICON, N_AIR, N_SIO2)
        # n_design = N_AIR + params * (N_SILICON - N_AIR)
        n_low, n_high = _N_AIR, _N_SILICON
        # 每 TMM 层的 FDTD cell 数（8 cells/layer → 32 cells/λ in Si）
        cells_per_layer = 8
        # 空间步长 = TMM 层厚度 / cells_per_layer
        tmm_layer_d = self.config.wavelength_um / (4.0 * n_high)
        dx_um = tmm_layer_d / cells_per_layer

        n_design_layers = len(params)
        n_design_cells = n_design_layers * cells_per_layer
        n_pad = 50
        n_inc = 20
        n_out = 20

        # 样品完整网格: air(padding+incident) | design | SiO₂(output+padding)
        n_sample = n_low + params * (n_high - n_low)
        # 每个 TMM 层展开为 cells_per_layer 个相同 ε 的 FDTD cell
        eps_design = np.repeat(n_sample ** 2, cells_per_layer)
        eps_sample_full = np.concatenate([
            np.ones(n_pad + n_inc) * _N_AIR ** 2,
            eps_design,
            np.ones(n_out + n_pad) * _N_SIO2 ** 2,
        ])
        # 参考完整网格: 全空气（无结构，无基底界面）
        n_total = n_pad + n_inc + n_design_cells + n_out + n_pad
        eps_ref_full = np.ones(n_total) * _N_AIR ** 2

        # 双仿真（稳态幅度法）
        amp_sample, field = self._run_fdtd(eps_sample_full, dx_um)
        amp_ref, _ = self._run_fdtd(eps_ref_full, dx_um)

        # 绝对传输率 T = (A_sample / A_ref)²
        if amp_ref > 1e-30:
            transmission = float((amp_sample / amp_ref) ** 2)
        else:
            transmission = 0.0
        # 钳制到物理范围 [0, 1]
        transmission = max(0.0, min(1.0, transmission))
        # 反射率 ≈ 1 - T（能量守恒近似）
        reflection = max(0.0, 1.0 - transmission)

        wl_m = self.config.wavelength_um * 1e-6
        dt = dx_um * 1e-6 / (2.0 * _C0 * _N_SILICON)
        steps_per_period = max(int((wl_m / _C0) / dt), 20)
        n_steps = 100 * steps_per_period
        return {
            "transmission": transmission,
            "reflection": reflection,
            "field": field,
            "n_steps": n_steps,
            "n_cells": n_total,
            "wavelength_um": self.config.wavelength_um,
        }


# ---------------------------------------------------------------------------
# FDTDCrossValidator — 多后端交叉验证器
# ---------------------------------------------------------------------------


@dataclass
class FDTDCrossValidator:
    """FDTD 多后端交叉验证器。

    交叉验证 FDTD 引擎与解析传输矩阵法的传输率结果，确保数值仿真
    的正确性。

    学术依据: D. M. Sullivan, "Electromagnetic Simulation Using the FDTD
    Method", IEEE Press, 2013, §2.5 验证方法论。

    Attributes:
        fdtd_engine: FDTD 引擎。
        tolerance: 传输率相对误差容限。
    """

    fdtd_engine: GPUFDTDEngine = field(default_factory=GPUFDTDEngine)
    tolerance: float = 0.15

    def validate_transmission(self, params: np.ndarray) -> dict:
        """交叉验证 FDTD 与解析传输矩阵法的传输率。

        Args:
            params: 设计参数 θ∈[0,1]^N。

        Returns:
            含 ``fdtd_transmission``、``analytical_transmission``、
            ``relative_error``、``passed`` 的字典。
        """
        # FDTD 仿真
        fdtd_result = self.fdtd_engine.run(params)
        fdtd_t = fdtd_result["transmission"]
        # 解析传输矩阵法（来源: polaris.sim.ai_inverse_design._transfer_matrix_transmission）
        from polaris.sim.ai_inverse_design import _transfer_matrix_transmission

        analytical_t = float(_transfer_matrix_transmission(
            params, self.fdtd_engine.config.wavelength_um
        ))
        # 相对误差
        if max(fdtd_t, analytical_t) > 1e-6:
            rel_error = abs(fdtd_t - analytical_t) / max(fdtd_t, analytical_t)
        else:
            rel_error = 0.0
        return {
            "fdtd_transmission": round(fdtd_t, 6),
            "analytical_transmission": round(analytical_t, 6),
            "relative_error": round(rel_error, 4),
            "passed": rel_error <= self.tolerance,
            "tolerance": self.tolerance,
        }

    def validate_batch(self, param_list: list[np.ndarray]) -> dict:
        """批量交叉验证。

        Args:
            param_list: 设计参数列表。

        Returns:
            含 ``results``（每个参数的验证结果）、``pass_rate``、
            ``mean_error`` 的字典。
        """
        results = [self.validate_transmission(p) for p in param_list]
        n_pass = sum(1 for r in results if r["passed"])
        pass_rate = n_pass / len(results) if results else 0.0
        mean_error = (
            sum(r["relative_error"] for r in results) / len(results)
            if results
            else 0.0
        )
        return {
            "results": results,
            "pass_rate": round(pass_rate, 4),
            "mean_error": round(mean_error, 4),
            "n_samples": len(results),
        }
