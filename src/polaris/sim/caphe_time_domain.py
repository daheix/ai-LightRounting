"""R31 路标：CAPHE 时域求解器与统一后端适配器。

从 caphe_backend.py 拆分而来（规则 7.1 单文件 ≤800 行）。

包含:
1. CAPHETimeDomainSolver: 时域 ODE 求解器（scipy.integrate.solve_ivp）
2. CAPHEBackend: 统一后端适配器（频域+时域+交叉验证）

学术依据:
- Fiers et al., "CAPHE: a circuit-level time-domain and frequency-domain
  modeling tool for nonlinear optical components", 2012
  URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf
- Laporte et al., "Highly parallel simulation and optimization of photonic
  circuits in time and frequency domain based on the deep-learning
  framework PyTorch", Scientific Reports 2019
  URL: https://doi.org/10.1038/s41598-019-42408-2

合规: 规则 14.1 禁止 fall-back；规则 18 学术诚信；规则 7.1 文件 < 800 行。
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np
from scipy.integrate import solve_ivp

from polaris.sim.caphe_backend import CROSS_VALIDATE_TOL, CAPHENetwork

logger = logging.getLogger(__name__)

# 学术来源 URL 常量（规则 18 学术诚信）
_URL_CAPHE_2012 = "https://biblio.ugent.be/publication/2036548/file/3146073.pdf"
_URL_BOGAERTS_2012 = "https://doi.org/10.1002/lpor.201100017"


def _ring_cmt_solve(
    detuning_ghz: float = 0.0,
    photon_lifetime_ps: float = 100.0,
    coupling: float = 0.1,
    t_span_ps: tuple[float, float] = (0.0, 100.0),
    n_steps: int = 100,
) -> dict:
    """环谐振器 CMT 时域仿真（模块级共享函数）。

    学术依据: Bogaerts et al., "Silicon microring resonators",
    Laser & Photonics Reviews 6(1), 2012,
    URL: https://doi.org/10.1002/lpor.201100017

    全通环 CMT 方程（拆实部虚部求解）:
        da/dt = (j·Δω - 1/τ)·a + √(2κ/τ)·s_in
        s_through = s_in - √(2κ/τ)·a

    Args:
        detuning_ghz: 失谐（GHz）。
        photon_lifetime_ps: 光子寿命（ps）。
        coupling: 功率耦合比。
        t_span_ps: 时间范围（ps）。
        n_steps: 输出时间点数。

    Returns:
        {"time": array_ps, "output_power": array}。

    Raises:
        RuntimeError: ODE 求解失败。
    """
    detuning_radps = 2.0 * np.pi * detuning_ghz * 1e9  # GHz → rad/s
    tau_s = photon_lifetime_ps * 1e-12  # ps → s
    t0_s = float(t_span_ps[0]) * 1e-12
    t1_s = float(t_span_ps[1]) * 1e-12
    t_eval_s = np.linspace(t0_s, t1_s, n_steps)
    sqrt_2k_tau = np.sqrt(2.0 * coupling / tau_s)

    def ode(t: float, y: np.ndarray) -> list[float]:
        ar, ai = y[0], y[1]
        dar = -ar / tau_s - detuning_radps * ai + sqrt_2k_tau
        dai = detuning_radps * ar - ai / tau_s
        return [dar, dai]

    sol = solve_ivp(
        ode, (t0_s, t1_s), [0.0, 0.0], t_eval=t_eval_s, method="RK45"
    )
    if not sol.success:
        raise RuntimeError(f"环时域 ODE 求解失败: {sol.message}")

    a = sol.y[0] + 1j * sol.y[1]
    s_through = 1.0 - sqrt_2k_tau * a
    output_power = np.abs(s_through) ** 2
    return {
        "time": sol.t * 1e12,  # s → ps
        "output_power": output_power,
    }


# =============================================================================
# 1. CAPHETimeDomainSolver — 时域 ODE 求解器（CMT）
# =============================================================================
class CAPHETimeDomainSolver:
    """CAPHE 时域 ODE 求解器（基于 CMT 耦合模理论）。

    学术依据：CAPHE 时域 CMT 求解（Fiers 2012 §III-B）
    URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    时域下，节点输出包含线性 + 非线性部分：
        s_out,i(t) = Σ_j S_ij · s_in,j(t) + g_i(a(t), s_in(t), t)
    状态变量 ODE：
        da_k(t)/dt = f_k(a(t), s_in(t), t)

    使用 scipy.integrate.solve_ivp（RK45 自适应步长）求解 ODE 系统。
    来源: scipy.integrate.solve_ivp 文档
    URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
    """

    def __init__(self, network: CAPHENetwork) -> None:
        """初始化时域求解器。

        Args:
            network: CAPHE 网络。
        """
        self.network = network
        self._state_names: list[str] = []
        self._state_offsets: dict[str, int] = {}
        self._build_state_index()

    def _build_state_index(self) -> None:
        """构建状态变量全局索引。

        将所有节点的状态变量展平为全局状态向量。
        """
        offset = 0
        for node in self.network.get_nodes():
            for sname in node.state_variables:
                global_key = f"{node.name}.{sname}"
                self._state_names.append(global_key)
                self._state_offsets[global_key] = offset
                offset += 1

    @property
    def n_states(self) -> int:
        """全局状态变量数。"""
        return len(self._state_names)

    def build_ode_system(
        self, t: float, y: np.ndarray, inputs: Callable[[float], dict[str, complex]]
    ) -> np.ndarray:
        """构建 ODE 系统 dy/dt = f(t, y, inputs)。

        学术依据：CAPHE 时域 CMT 求解（Fiers 2012 §III-B）

        Args:
            t: 当前时间。
            y: 全局状态向量。
            inputs: 输入函数 t -> {ext_name: amplitude}。

        Returns:
            状态导数向量 dy/dt。
        """
        if self.n_states == 0:
            return np.array([], dtype=float)

        dydt = np.zeros(self.n_states, dtype=float)
        current_inputs = inputs(t) if callable(inputs) else inputs

        # 计算各节点输入（简化：仅外部输入直接作用）
        for node in self.network.get_nodes():
            if node.ode_func is None:
                continue
            # 提取该节点的状态子向量
            node_state = np.array(
                [y[self._state_offsets[f"{node.name}.{sn}"]] for sn in node.state_variables],
                dtype=float,
            )
            # 构造节点输入向量（外部激励 + 连接端口输入）
            s_in = np.zeros(node.n_ports, dtype=complex)
            for ext_name, (n_name, p_idx) in self.network.external_ports.items():
                if n_name == node.name and ext_name in current_inputs:
                    s_in[p_idx] = complex(current_inputs[ext_name])

            # 调用节点 ODE 函数
            dstate = node.ode_func(t, node_state, s_in)
            for i, sname in enumerate(node.state_variables):
                global_key = f"{node.name}.{sname}"
                dydt[self._state_offsets[global_key]] = float(dstate[i])

        return dydt

    def extract_states(self, y: np.ndarray) -> dict[str, float]:
        """从解向量提取状态变量。

        Args:
            y: 全局状态向量。

        Returns:
            状态变量字典 {global_key: value}。
        """
        states: dict[str, float] = {}
        for i, name in enumerate(self._state_names):
            states[name] = float(y[i])
        return states

    def _build_initial_state(self, y0: list[float] | None) -> np.ndarray:
        """构建初始状态向量。

        y0 为 None 时用各节点 state_variables 默认值填充。

        Raises:
            ValueError: y0 长度与状态变量数不匹配。
        """
        if y0 is None:
            y0_arr = np.zeros(self.n_states, dtype=float)
            offset = 0
            for node in self.network.get_nodes():
                for _sname, val in node.state_variables.items():
                    y0_arr[offset] = float(val)
                    offset += 1
            return y0_arr
        if len(y0) != self.n_states:
            raise ValueError(f"y0 长度 {len(y0)} != 状态变量数 {self.n_states}")
        return np.array(y0, dtype=float)

    def _solve_ode(
        self,
        t_span: tuple[float, float],
        y0_arr: np.ndarray,
        t_eval: np.ndarray,
        inputs: Callable[[float], dict[str, complex]],
    ):
        """调用 scipy.integrate.solve_ivp（RK45 自适应步长）。

        来源: scipy 文档
        URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html

        Raises:
            RuntimeError: ODE 求解失败或未收敛。
        """
        try:
            sol = solve_ivp(
                fun=lambda t, y: self.build_ode_system(t, y, inputs),
                t_span=t_span,
                y0=y0_arr,
                method="RK45",
                t_eval=t_eval,
                rtol=1e-6,
                atol=1e-9,
            )
        except Exception as exc:
            raise RuntimeError(f"ODE 求解失败: {exc}") from exc
        if not sol.success:
            raise RuntimeError(f"ODE 求解未收敛: {sol.message}")
        return sol

    def solve(
        self,
        t_span: tuple[float, float],
        inputs: Callable[[float], dict[str, complex]],
        y0: list[float] | None = None,
        n_points: int = 100,
    ) -> dict:
        """时域 ODE 求解。

        学术依据：CAPHE 时域 CMT 求解（Fiers 2012 §III-B）
        URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

        使用 scipy.integrate.solve_ivp（RK45 自适应步长）。

        Args:
            t_span: 时间范围 (t_start, t_end)。
            inputs: 输入函数 t -> {ext_name: amplitude}。
            y0: 初始状态向量（None 则用各节点 state_variables 默认值）。
            n_points: 输出时间点数。

        Returns:
            求解结果字典：
            {
                "t": 时间数组,
                "y": 状态向量数组 (n_times × n_states),
                "states": 时间序列状态字典 {global_key: 数组},
            }

        Raises:
            ValueError: 时间范围非法。
            RuntimeError: ODE 求解失败。
        """
        if t_span[0] >= t_span[1]:
            raise ValueError(f"t_span[0] 必须 < t_span[1]，得到 {t_span}")
        if n_points <= 0:
            raise ValueError(f"n_points 必须 > 0，得到 {n_points}")
        # 无状态变量时直接返回空解
        if self.n_states == 0:
            t_eval = np.linspace(t_span[0], t_span[1], n_points)
            return {
                "t": t_eval,
                "y": np.zeros((n_points, 0), dtype=float),
                "states": {},
            }
        y0_arr = self._build_initial_state(y0)
        t_eval = np.linspace(t_span[0], t_span[1], n_points)
        sol = self._solve_ode(t_span, y0_arr, t_eval, inputs)
        # 提取状态时间序列
        states_ts: dict[str, np.ndarray] = {
            name: sol.y[i, :] for i, name in enumerate(self._state_names)
        }
        return {
            "t": sol.t,
            "y": sol.y.T,  # (n_times × n_states)
            "states": states_ts,
        }

    def solve_ring(
        self,
        t_span_ps: tuple[float, float] = (0.0, 100.0),
        n_steps: int = 100,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        **kwargs,
    ) -> dict:
        """环谐振器时域 CMT 仿真（兼容旧 API）。

        学术依据: Bogaerts et al., "Silicon microring resonators",
        Laser & Photonics Reviews 6(1), 2012,
        URL: https://doi.org/10.1002/lpor.201100017

        全通环 CMT 方程（Bogaerts 2012 §2.1）:
            da/dt = (j·Δω - 1/τ)·a + √(2κ/τ)·s_in
            s_through = s_in - √(2κ/τ)·a

        Args:
            t_span_ps: 时间范围（ps）。
            n_steps: 输出时间点数。
            detuning_ghz: 失谐（GHz）。
            photon_lifetime_ps: 光子寿命（ps）。
            coupling: 功率耦合比。

        Returns:
            {"time": array_ps, "output_power": array}。
        """
        return _ring_cmt_solve(
            detuning_ghz=detuning_ghz,
            photon_lifetime_ps=photon_lifetime_ps,
            coupling=coupling,
            t_span_ps=t_span_ps,
            n_steps=n_steps,
        )


# =============================================================================
# 2. CAPHEBackend — CAPHE 后端适配器（统一频域+时域接口）
# =============================================================================
class CAPHEBackend:
    """CAPHE 后端适配器（统一频域+时域接口）。

    学术依据：CAPHE 统一接口（Fiers 2012）
    URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    提供统一的频域+时域仿真接口，并支持与 sax/simphony 后端交叉验证
    （误差 < 1e-4，来源: R26.md §1）。

    兼容旧 API:
        - ``CAPHEBackend(network=net)``: 构造时传入网络。
        - ``CAPHEBackend.from_netlist(netlist)``: 从 SAX 网表构建。
        - ``backend.network``: 网络属性。
        - ``backend.frequency_domain(wavelengths=...)``: 旧 API 频域扫描。
        - ``backend.time_domain(...)``: 旧 API 环谐振器 CMT 时域。

    创新点（标注"创新"）:
    - 自动稀疏化：自动检测无源线性节点并消去，无需用户手动标记。
      创新逻辑：节点实例化时自动分析是否含状态变量/ODE。
      支持理论：图论中的"叶子节点消去"。
      预期收益：用户无需手动标记，降低使用门槛。
    """

    def __init__(self, network: CAPHENetwork | None = None) -> None:
        """初始化 CAPHE 后端。

        Args:
            network: 可选的 CAPHE 网络（兼容旧 API ``CAPHEBackend(network=net)``）。
        """
        self._network: CAPHENetwork | None = network
        self._freq_solver: object | None = None
        self._time_solver: CAPHETimeDomainSolver | None = None

    @property
    def network(self) -> CAPHENetwork | None:
        """关联的 CAPHE 网络（兼容旧 API）。"""
        return self._network

    @classmethod
    def from_netlist(cls, netlist: dict) -> CAPHEBackend:
        """从 SAX 网表构建 CAPHE 后端（兼容旧 API）。

        Args:
            netlist: SAX 网表字典（见 CAPHENetwork.from_netlist）。

        Returns:
            CAPHEBackend 实例。
        """
        network = CAPHENetwork.from_netlist(netlist)
        return cls(network=network)

    def frequency_domain(
        self,
        wavelengths: list[float] | np.ndarray | None = None,
        **kwargs,
    ) -> tuple[np.ndarray, dict]:
        """频域仿真（旧 API 兼容）。

        对 self.network 做波长扫描，返回外部端口等效 S 参数。

        Args:
            wavelengths: 波长列表/数组（μm），或通过 kwargs 传入。

        Returns:
            (wavelengths, sdict)，sdict = {(port_out, port_in): array}。

        Raises:
            ValueError: 未提供 network / wavelengths。
        """
        if self._network is None:
            raise ValueError("未提供 network，无法调用 frequency_domain")
        from polaris.sim.caphe_backend import CAPHEFrequencySolver

        wl = kwargs.get("wavelengths", wavelengths)
        if wl is None:
            raise ValueError("必须提供 wavelengths")
        solver = CAPHEFrequencySolver(self._network)
        return solver.solve(wl)  # 旧 API 模式（无 inputs）

    def time_domain(self, **kwargs) -> dict:
        """时域仿真（旧 API 兼容，环谐振器 CMT）。

        学术依据: Bogaerts 2012, URL: https://doi.org/10.1002/lpor.201100017

        Args:
            detuning_ghz: 失谐（GHz）。
            photon_lifetime_ps: 光子寿命（ps）。
            coupling: 功率耦合比。
            t_span_ps: 时间范围（ps）。
            n_steps: 输出时间点数。

        Returns:
            {"time": array_ps, "output_power": array}。
        """
        return _ring_cmt_solve(**kwargs)

    def simulate_frequency(
        self,
        network: CAPHENetwork,
        wavelengths: list[float],
        inputs: dict[str, complex],
    ) -> dict:
        """频域仿真。

        Args:
            network: CAPHE 网络。
            wavelengths: 波长列表（μm）。
            inputs: 外部端口输入字典 {ext_name: amplitude}。

        Returns:
            频域求解结果（见 CAPHEFrequencySolver.solve）。
        """
        # 延迟导入 CAPHEFrequencySolver 避免循环导入
        from polaris.sim.caphe_backend import CAPHEFrequencySolver

        self._freq_solver = CAPHEFrequencySolver(network)
        return self._freq_solver.solve(wavelengths, inputs)

    def simulate_time(
        self,
        network: CAPHENetwork,
        t_span: tuple[float, float],
        inputs: Callable[[float], dict[str, complex]],
        y0: list[float] | None = None,
        n_points: int = 100,
    ) -> dict:
        """时域仿真。

        Args:
            network: CAPHE 网络。
            t_span: 时间范围 (t_start, t_end)。
            inputs: 输入函数 t -> {ext_name: amplitude}。
            y0: 初始状态向量。
            n_points: 输出时间点数。

        Returns:
            时域求解结果（见 CAPHETimeDomainSolver.solve）。
        """
        self._time_solver = CAPHETimeDomainSolver(network)
        return self._time_solver.solve(t_span, inputs, y0, n_points)

    def cross_validate(self, sax_result: dict, caphe_result: dict) -> dict:
        """与 sax 后端交叉验证。

        学术依据：R26.md §1，与 sax/simphony 后端误差 < 1e-4。

        Args:
            sax_result: sax 后端求解结果，格式 {"outputs": {ext_name: array}}。
            caphe_result: CAPHE 后端求解结果。

        Returns:
            交叉验证结果：
            {
                "max_error": 最大绝对误差,
                "mean_error": 平均绝对误差,
                "passed": 是否通过（误差 < 1e-4）,
                "per_port": 各端口误差,
            }
        """
        if "outputs" not in sax_result or "outputs" not in caphe_result:
            raise ValueError("sax_result 和 caphe_result 必须包含 'outputs' 键")

        per_port: dict[str, float] = {}
        max_err = 0.0
        total_err = 0.0
        count = 0

        for port_name, caphe_arr in caphe_result["outputs"].items():
            if port_name not in sax_result["outputs"]:
                raise ValueError(f"sax 结果缺少端口 {port_name!r}")
            sax_arr = np.asarray(sax_result["outputs"][port_name], dtype=complex)
            caphe_arr = np.asarray(caphe_arr, dtype=complex)
            if sax_arr.shape != caphe_arr.shape:
                raise ValueError(
                    f"端口 {port_name!r} 形状不匹配: sax={sax_arr.shape} vs caphe={caphe_arr.shape}"
                )
            err = float(np.max(np.abs(sax_arr - caphe_arr)))
            per_port[port_name] = err
            max_err = max(max_err, err)
            total_err += float(np.sum(np.abs(sax_arr - caphe_arr)))
            count += sax_arr.size

        mean_err = total_err / max(count, 1)
        return {
            "max_error": max_err,
            "mean_error": mean_err,
            "passed": max_err < CROSS_VALIDATE_TOL,
            "per_port": per_port,
        }


__all__ = [
    "CAPHETimeDomainSolver",
    "CAPHEBackend",
]
