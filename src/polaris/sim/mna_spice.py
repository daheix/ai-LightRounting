"""MNA SPICE 求解器 — 改进节点分析法电路仿真。

来源:
- Nagel & Rohrer, "Computer Analysis of Nonlinear Circuits, Excluding Radiation",
  IEEE Transactions on Circuit Theory, 1971,
  https://ieeexplore.ieee.org/document/1083483
- Ho, Ruehli, Brennan, "The Modified Nodal Approach to Network Analysis",
  IEEE ISCAS 1974, https://ieeexplore.ieee.org/document/1084079
- Pillage, "Electronic Circuit & System Simulation Methods",
  McGraw-Hill, 1995, §4-5

MNA 核心算法:
1. 构建节点-元件关联矩阵
2. 构建 MNA 矩阵 [G B; C D] 和 RHS [I; E]
3. 求解 [v; i] = MNA^{-1} * RHS
4. DC 分析: 直接求解线性方程组
5. 瞬态分析: 后向欧拉法 (Backward Euler)

支持元件: R(电阻) C(电容) L(电感) V(电压源) I(电流源) D(二极管-线性化)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

_logger = logging.getLogger(__name__)


@dataclass
class MNACircuit:
    """MNA 电路描述。

    节点编号: 0 = GND (地), 1..N = 信号节点。
    元件列表: resistors/capacitors/inductors/vsources/isources/diodes。
    """

    n_nodes: int = 0
    resistors: list[dict[str, Any]] = field(default_factory=list)
    capacitors: list[dict[str, Any]] = field(default_factory=list)
    inductors: list[dict[str, Any]] = field(default_factory=list)
    vsources: list[dict[str, Any]] = field(default_factory=list)
    isources: list[dict[str, Any]] = field(default_factory=list)
    diodes: list[dict[str, Any]] = field(default_factory=list)

    def add_resistor(self, name: str, n1: int, n2: int, r: float) -> None:
        """添加电阻 R (Ω)。"""
        if r <= 0:
            raise ValueError(f"电阻 {name} 阻值必须 > 0, got {r}")
        self.resistors.append({"name": name, "n1": n1, "n2": n2, "r": r})

    def add_capacitor(self, name: str, n1: int, n2: int, c: float) -> None:
        """添加电容 C (F)。"""
        if c <= 0:
            raise ValueError(f"电容 {name} 容值必须 > 0, got {c}")
        self.capacitors.append({"name": name, "n1": n1, "n2": n2, "c": c})

    def add_inductor(self, name: str, n1: int, n2: int, l: float) -> None:  # noqa: E741  电感 L 物理量
        """添加电感 L (H)。"""
        if l <= 0:
            raise ValueError(f"电感 {name} 感值必须 > 0, got {l}")
        self.inductors.append({"name": name, "n1": n1, "n2": n2, "l": l})

    def add_vsource(self, name: str, n1: int, n2: int, dc: float, ac: float = 0.0, freq: float = 0.0) -> None:
        """添加电压源 V (V), 支持 DC + AC 正弦。"""
        self.vsources.append({"name": name, "n1": n1, "n2": n2, "dc": dc, "ac": ac, "freq": freq})

    def add_isource(self, name: str, n1: int, n2: int, dc: float) -> None:
        """添加电流源 I (A)。"""
        self.isources.append({"name": name, "n1": n1, "n2": n2, "dc": dc})

    def add_diode(self, name: str, n1: int, n2: int, is_: float = 1e-15, vt: float = 0.026) -> None:
        """添加二极管 D (Shockley 模型, Newton-Raphson 线性化)。

        来源: Shockley, "The Theory of p-n Junctions in Semiconductors",
          Bell System Technical Journal 1949
        """
        self.diodes.append({"name": name, "n1": n1, "n2": n2, "is": is_, "vt": vt})


@dataclass
class MNATransientResult:
    """瞬态分析结果。"""

    time: np.ndarray
    node_voltages: dict[int, np.ndarray]
    vsource_currents: dict[str, np.ndarray]
    n_points: int


@dataclass
class MNADCResult:
    """DC 分析结果。"""

    node_voltages: dict[int, float]
    vsource_currents: dict[str, float]


class MNASolver:
    """改进节点分析法 (MNA) SPICE 求解器。

    来源: Ho, Ruehli, Brennan, "The Modified Nodal Approach to Network Analysis",
      IEEE ISCAS 1974, https://ieeexplore.ieee.org/document/1084079

    MNA 矩阵结构:
        [G  B] [v]   [I]
        [C  D] [i] = [E]
    其中:
        G: 节点导纳矩阵 (n_nodes × n_nodes)
        B: 电压源-节点关联 (n_nodes × n_vsrc)
        C: B 的转置
        D: 电压源补充 (n_vsrc × n_vsrc, 通常 0)
        v: 节点电压向量
        i: 电压源电流向量
        I: 电流源注入向量
        E: 电压源值向量
    """

    def __init__(self, circuit: MNACircuit) -> None:
        """初始化 MNA 求解器。

        Args:
            circuit: 电路描述对象。
        """
        self.circuit = circuit
        self.n = circuit.n_nodes
        self.m = len(circuit.vsources)
        self.n_ind = len(circuit.inductors)
        # 未知数总数: 节点电压 + 电压源电流 + 电感电流
        self.size = self.n + self.m + self.n_ind
        # 电压源名称 → 索引映射
        self._vsrc_idx = {v["name"]: i for i, v in enumerate(circuit.vsources)}
        # 电感名称 → 索引映射
        self._ind_idx = {v["name"]: i for i, v in enumerate(circuit.inductors)}

    def _build_dc_mna(self) -> tuple[np.ndarray, np.ndarray]:
        """构建 DC 分析的 MNA 矩阵和 RHS。

        DC 分析: 电容开路 (移除), 电感短路 (0Ω 电阻 → 电压源 0V)。

        Returns:
            (A, z): MNA 矩阵 A (size×size) 和 RHS 向量 z (size)。
        """
        A = np.zeros((self.size, self.size))
        z = np.zeros(self.size)

        # 电阻: G = 1/R 注入 G 矩阵
        for r in self.circuit.resistors:
            g = 1.0 / r["r"]
            n1, n2 = r["n1"], r["n2"]
            if n1 > 0:
                A[n1 - 1, n1 - 1] += g
            if n2 > 0:
                A[n2 - 1, n2 - 1] += g
            if n1 > 0 and n2 > 0:
                A[n1 - 1, n2 - 1] -= g
                A[n2 - 1, n1 - 1] -= g

        # 电压源: B/C 矩阵 + E 向量
        for i, v in enumerate(self.circuit.vsources):
            n1, n2 = v["n1"], v["n2"]
            col = self.n + i
            if n1 > 0:
                A[n1 - 1, col] = 1.0
                A[col, n1 - 1] = 1.0
            if n2 > 0:
                A[n2 - 1, col] = -1.0
                A[col, n2 - 1] = -1.0
            z[col] = v["dc"]

        # 电流源: I 向量注入
        for src in self.circuit.isources:
            n1, n2 = src["n1"], src["n2"]
            if n1 > 0:
                z[n1 - 1] -= src["dc"]
            if n2 > 0:
                z[n2 - 1] += src["dc"]

        # 电感: DC 等效为 0V 电压源 (短路)
        for i, ind in enumerate(self.circuit.inductors):
            n1, n2 = ind["n1"], ind["n2"]
            col = self.n + self.m + i
            if n1 > 0:
                A[n1 - 1, col] = 1.0
                A[col, n1 - 1] = 1.0
            if n2 > 0:
                A[n2 - 1, col] = -1.0
                A[col, n2 - 1] = -1.0
            z[col] = 0.0  # 短路

        return A, z

    def solve_dc(self) -> MNADCResult:
        """执行 DC 工作点分析。

        Returns:
            MNADCResult 含节点电压和电压源电流。

        Raises:
            RuntimeError: 矩阵奇异（电路无解或欠约束）。
        """
        _logger.info("MNA DC 分析: %d 节点, %d 电压源, %d 电感", self.n, self.m, self.n_ind)
        A, z = self._build_dc_mna()

        # 二极管 Newton-Raphson 迭代
        if self.circuit.diodes:
            x = self._solve_dc_with_diodes(A, z)
        else:
            try:
                x = np.linalg.solve(A, z)
            except np.linalg.LinAlgError as e:
                raise RuntimeError(f"MNA DC 矩阵奇异: {e}") from e

        node_voltages = {i: float(x[i - 1]) for i in range(1, self.n + 1)}
        vsource_currents = {
            v["name"]: float(x[self.n + i]) for i, v in enumerate(self.circuit.vsources)
        }
        _logger.info("MNA DC 完成: %d 节点电压", len(node_voltages))
        return MNADCResult(node_voltages=node_voltages, vsource_currents=vsource_currents)

    def _solve_dc_with_diodes(self, A_init: np.ndarray, z_init: np.ndarray) -> np.ndarray:
        """含二极管的 DC 分析 (Newton-Raphson 迭代)。

        二极管 Shockley 模型: I = Is * (exp(V/Vt) - 1)
        线性化: I ≈ I_eq + G_eq * V, 其中
          G_eq = Is/Vt * exp(V_prev/Vt)
          I_eq = I_prev - G_eq * V_prev

        来源: Shockley 1949 BSTJ; Pillage 1995 §7
        """
        x = np.zeros(self.size)
        for iteration in range(100):
            A = A_init.copy()
            z = z_init.copy()
            for d in self.circuit.diodes:
                n1, n2 = d["n1"], d["n2"]
                v_d = (x[n1 - 1] - x[n2 - 1]) if n1 > 0 and n2 > 0 else 0.0
                exp_v = np.exp(np.clip(v_d / d["vt"], -50, 50))
                g_eq = d["is"] / d["vt"] * exp_v
                i_eq = d["is"] * (exp_v - 1.0) - g_eq * v_d
                if n1 > 0:
                    A[n1 - 1, n1 - 1] += g_eq
                    z[n1 - 1] -= i_eq
                if n2 > 0:
                    A[n2 - 1, n2 - 1] += g_eq
                    z[n2 - 1] += i_eq
                if n1 > 0 and n2 > 0:
                    A[n1 - 1, n2 - 1] -= g_eq
                    A[n2 - 1, n1 - 1] -= g_eq
            try:
                x_new = np.linalg.solve(A, z)
            except np.linalg.LinAlgError as e:
                raise RuntimeError(f"MNA DC (二极管迭代) 矩阵奇异: {e}") from e
            if np.max(np.abs(x_new - x)) < 1e-10:
                _logger.info("MNA DC 二极管收敛: %d 次迭代", iteration + 1)
                return x_new
            x = x_new
        _logger.warning("MNA DC 二极管未完全收敛 (100 次迭代)")
        return x

    def solve_transient(self, t_total: float, dt: float) -> MNATransientResult:
        """执行瞬态分析 (后向欧拉法 Backward Euler)。

        来源: Pillage, "Electronic Circuit & System Simulation Methods",
          McGraw-Hill 1995, §9 (后向欧拉稳定性)

        后向欧拉: x(t+dt) = x(t) + dt * f(x(t+dt))
        电容: I_C = C * dV/dt ≈ C/dt * (V(t+dt) - V(t))
          → G_C = C/dt 注入 G, I_C_prev = C/dt * V_prev 注入 RHS
        电感: V_L = L * dI/dt ≈ L/dt * (I(t+dt) - I(t))
          → 电压源 V_L = L/dt * I_prev, 系数 L/dt

        Args:
            t_total: 总仿真时间 (s)。
            dt: 时间步长 (s)。

        Returns:
            MNATransientResult 含时间序列和节点电压波形。

        Raises:
            RuntimeError: 矩阵奇异或时间参数无效。
        """
        if t_total <= 0 or dt <= 0:
            raise ValueError(f"时间参数无效: t_total={t_total}, dt={dt}")
        n_steps = int(np.ceil(t_total / dt)) + 1
        time = np.linspace(0, t_total, n_steps)
        _logger.info("MNA 瞬态分析: %d 步, dt=%.2e s, t_total=%.2e s", n_steps, dt, t_total)

        # DC 初始工作点
        dc = self.solve_dc()
        x = np.zeros(self.size)
        for i in range(1, self.n + 1):
            x[i - 1] = dc.node_voltages.get(i, 0.0)

        # 存储波形
        node_voltages = {i: np.zeros(n_steps) for i in range(1, self.n + 1)}
        vsource_currents = {v["name"]: np.zeros(n_steps) for v in self.circuit.vsources}
        for i in range(1, self.n + 1):
            node_voltages[i][0] = x[i - 1]
        for j, v in enumerate(self.circuit.vsources):
            vsource_currents[v["name"]][0] = x[self.n + j]

        # 瞬态迭代
        for step in range(1, n_steps):
            t = time[step]
            A, z = self._build_transient_mna(dt, t, x)
            try:
                x = np.linalg.solve(A, z)
            except np.linalg.LinAlgError as e:
                raise RuntimeError(f"MNA 瞬态步 {step} 矩阵奇异: {e}") from e
            for i in range(1, self.n + 1):
                node_voltages[i][step] = x[i - 1]
            for j, v in enumerate(self.circuit.vsources):
                vsource_currents[v["name"]][step] = x[self.n + j]

        _logger.info("MNA 瞬态完成: %d 时间点", n_steps)
        return MNATransientResult(
            time=time,
            node_voltages=node_voltages,
            vsource_currents=vsource_currents,
            n_points=n_steps,
        )

    def _build_transient_mna(self, dt: float, t: float, x_prev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """构建瞬态分析第 step 步的 MNA 矩阵 (后向欧拉)。

        Args:
            dt: 时间步长。
            t: 当前时间。
            x_prev: 前一步的状态向量。

        Returns:
            (A, z): MNA 矩阵和 RHS。
        """
        A = np.zeros((self.size, self.size))
        z = np.zeros(self.size)
        # 电阻
        for r in self.circuit.resistors:
            self._stamp_resistor(A, r)
        # 电容 (后向欧拉): G_C = C/dt, I_prev = C/dt * V_prev
        for c in self.circuit.capacitors:
            self._stamp_capacitor(A, z, c, dt, x_prev)
        # 电感 (后向欧拉): 等效电压源 V_L = L/dt * I_prev, 系数 L/dt
        for i, ind in enumerate(self.circuit.inductors):
            self._stamp_inductor(A, z, ind, i, dt, x_prev)
        # 电压源 (支持 AC 正弦)
        for i, v in enumerate(self.circuit.vsources):
            self._stamp_vsource(A, z, v, i, t)
        # 电流源
        for src in self.circuit.isources:
            self._stamp_isource(z, src)
        return A, z

    @staticmethod
    def _stamp_resistor(A: np.ndarray, r: dict) -> None:
        """电阻导纳 stamping（G = 1/R 注入 MNA 矩阵）。"""
        g = 1.0 / r["r"]
        n1, n2 = r["n1"], r["n2"]
        if n1 > 0:
            A[n1 - 1, n1 - 1] += g
        if n2 > 0:
            A[n2 - 1, n2 - 1] += g
        if n1 > 0 and n2 > 0:
            A[n1 - 1, n2 - 1] -= g
            A[n2 - 1, n1 - 1] -= g

    @staticmethod
    def _stamp_capacitor(
        A: np.ndarray, z: np.ndarray, c: dict, dt: float, x_prev: np.ndarray
    ) -> None:
        """电容后向欧拉 stamping：G_C=C/dt, I_prev=G_C·V_prev。"""
        g_c = c["c"] / dt
        n1, n2 = c["n1"], c["n2"]
        v_prev = (x_prev[n1 - 1] - x_prev[n2 - 1]) if n1 > 0 and n2 > 0 else 0.0
        i_prev = g_c * v_prev
        if n1 > 0:
            A[n1 - 1, n1 - 1] += g_c
            z[n1 - 1] += i_prev
        if n2 > 0:
            A[n2 - 1, n2 - 1] += g_c
            z[n2 - 1] -= i_prev
        if n1 > 0 and n2 > 0:
            A[n1 - 1, n2 - 1] -= g_c
            A[n2 - 1, n1 - 1] -= g_c

    def _stamp_inductor(
        self, A: np.ndarray, z: np.ndarray, ind: dict, idx: int, dt: float, x_prev: np.ndarray
    ) -> None:
        """电感后向欧拉 stamping：R_eq=L/dt, V_prev=R_eq·I_prev。

        电感等效为电阻 R_eq = L/dt 串联电压源 V_prev = R_eq * I_prev。
        """
        n1, n2 = ind["n1"], ind["n2"]
        col = self.n + self.m + idx
        r_eq = ind["l"] / dt
        i_prev = x_prev[col]
        v_prev = r_eq * i_prev
        if n1 > 0:
            A[n1 - 1, n1 - 1] += 1.0 / r_eq
            A[n1 - 1, col] = 1.0
            A[col, n1 - 1] = 1.0
            z[n1 - 1] += v_prev / r_eq
        if n2 > 0:
            A[n2 - 1, n2 - 1] += 1.0 / r_eq
            A[n2 - 1, col] = -1.0
            A[col, n2 - 1] = -1.0
            z[n2 - 1] -= v_prev / r_eq
        z[col] = 0.0

    def _stamp_vsource(
        self, A: np.ndarray, z: np.ndarray, v: dict, idx: int, t: float
    ) -> None:
        """电压源 stamping（支持 AC 正弦叠加）。"""
        n1, n2 = v["n1"], v["n2"]
        col = self.n + idx
        v_val = v["dc"]
        if v["ac"] > 0 and v["freq"] > 0:
            v_val += v["ac"] * np.sin(2 * np.pi * v["freq"] * t)
        if n1 > 0:
            A[n1 - 1, col] = 1.0
            A[col, n1 - 1] = 1.0
        if n2 > 0:
            A[n2 - 1, col] = -1.0
            A[col, n2 - 1] = -1.0
        z[col] = v_val

    @staticmethod
    def _stamp_isource(z: np.ndarray, src: dict) -> None:
        """电流源 stamping（注入 RHS）。"""
        n1, n2 = src["n1"], src["n2"]
        if n1 > 0:
            z[n1 - 1] -= src["dc"]
        if n2 > 0:
            z[n2 - 1] += src["dc"]


def build_opto_electrical_link_circuit(
    pam4_levels: np.ndarray,
    dt: float,
    t_total: float,
    r_waveguide: float = 50.0,
    r_detector: float = 1e3,
    c_detector: float = 1e-15,
    r_tia: float = 1e4,
    c_tia: float = 0.5e-12,
    v_supply: float = 3.3,
) -> tuple[MNACircuit, dict[str, int]]:
    """构建光电联合链路 MNA 电路模型。

    电路拓扑:
        V_supply → R_wg → 节点2(调制器) → 光耦合 → 节点3(探测器)
        → R_det || C_det → 节点4(TIA输入) → R_tia || C_tia → 节点5(输出)

    PAM4 信号通过 V_supply 的 AC 分量注入。

    来源: Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Args:
        pam4_levels: PAM4 符号电平序列 (V)。
        dt: 时间步长 (s)。
        t_total: 总时间 (s)。
        r_waveguide: 波导等效电阻 (Ω)。
        r_detector: 探测器等效电阻 (Ω)。
        c_detector: 探测器结电容 (F)。
        r_tia: TIA 反馈电阻 (Ω)。
        c_tia: TIA 反馈电容 (F)。
        v_supply: 供电电压 (V)。

    Returns:
        (circuit, node_map): MNA 电路和节点名称→编号映射。
    """
    circuit = MNACircuit(n_nodes=5)
    # 节点: 1=supply, 2=modulator, 3=detector, 4=tia_in, 5=output
    node_map = {"supply": 1, "modulator": 2, "detector": 3, "tia_in": 4, "output": 5}

    # PAM4 信号作为电压源 AC 分量
    # 取第一个符号作为 DC 偏置，AC 幅度为符号电平
    v_dc = float(np.mean(pam4_levels)) if len(pam4_levels) > 0 else 0.0
    v_ac = float(np.std(pam4_levels)) if len(pam4_levels) > 0 else 0.0
    freq = 1.0 / (dt * max(len(pam4_levels), 1))

    circuit.add_vsource("V_pam4", n1=1, n2=0, dc=v_supply + v_dc, ac=v_ac, freq=freq)
    circuit.add_resistor("R_wg", n1=1, n2=2, r=r_waveguide)
    circuit.add_resistor("R_mod", n1=2, n2=0, r=100.0)  # 调制器等效
    # 光耦合: 电隔离，用受控源简化为电阻分压
    circuit.add_resistor("R_optical", n1=2, n2=3, r=1e6)  # 高阻光隔离
    circuit.add_resistor("R_det", n1=3, n2=4, r=r_detector)
    circuit.add_capacitor("C_det", n1=4, n2=0, c=c_detector)
    circuit.add_resistor("R_tia", n1=4, n2=5, r=r_tia)
    circuit.add_capacitor("C_tia", n1=5, n2=0, c=c_tia)
    circuit.add_resistor("R_load", n1=5, n2=0, r=1e4)

    _logger.info(
        "光电联合电路: 5 节点, V_pam4(dc=%.3f, ac=%.3f, freq=%.2e Hz)",
        v_supply + v_dc, v_ac, freq,
    )
    return circuit, node_map
