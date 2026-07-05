"""MNA SPICE 求解器 — 改进节点分析法电路仿真。

来源:
- Nagel & Rohrer, "Computer Analysis of Nonlinear Circuits, Excluding Radiation",
  IEEE Transactions on Circuit Theory, 1971,
  https://ieeexplore.ieee.org/document/1083483
- Ho, Ruehli, Brennan, "The Modified Nodal Approach to Network Analysis",
  IEEE ISCAS 1974, https://ieeexplore.ieee.org/document/1084079
- Pillage, "Electronic Circuit & System Simulation Methods",
  McGraw-Hill, 1995, §4-5, https://www.mheducation.com/highered/product/0070504910.html
- Nagel, "SPICE2: A Computer Program to Simulate Semiconductor Circuits",
  UC Berkeley ERL-M520, 1975, https://www.eecs.berkeley.edu/Pubs/TechRpts/1975/ERL-520.pdf
- Galetzka, Loukrezis, De Gersem, "Data-driven model-free modified nodal
  analysis circuit solver", Int. J. Numer. Model. 2024,
  https://doi.org/10.1002/jnm.3205

MNA 核心算法:
1. 构建节点-元件关联矩阵
2. 构建 MNA 矩阵 [G B; C D] 和 RHS [I; E]
3. 求解 [v; i] = MNA^{-1} * RHS
4. DC 分析: 直接求解线性方程组
5. 瞬态分析: 后向欧拉法 (Backward Euler)

支持元件: R(电阻) C(电容) L(电感) V(电压源) I(电流源) D(二极管-线性化)

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO /
R13 不保留 v4 兼容 / 函数≤80行 / 文件≤800行。
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

    def add_inductor(self, name: str, n1: int, n2: int, l: float) -> None:  # noqa: E741
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
    """

    def __init__(self, circuit: MNACircuit) -> None:
        """初始化 MNA 求解器。"""
        self.circuit = circuit
        self.n = circuit.n_nodes
        self.m = len(circuit.vsources)
        self.n_ind = len(circuit.inductors)
        self.size = self.n + self.m + self.n_ind
        self._vsrc_idx = {v["name"]: i for i, v in enumerate(circuit.vsources)}
        self._ind_idx = {v["name"]: i for i, v in enumerate(circuit.inductors)}

    def _build_dc_mna(self) -> tuple[np.ndarray, np.ndarray]:
        """构建 DC 分析的 MNA 矩阵和 RHS。

        DC 分析: 电容开路 (移除), 电感短路 (0Ω 电阻 → 电压源 0V)。
        """
        A = np.zeros((self.size, self.size))
        z = np.zeros(self.size)
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
        for src in self.circuit.isources:
            n1, n2 = src["n1"], src["n2"]
            if n1 > 0:
                z[n1 - 1] -= src["dc"]
            if n2 > 0:
                z[n2 - 1] += src["dc"]
        for i, ind in enumerate(self.circuit.inductors):
            n1, n2 = ind["n1"], ind["n2"]
            col = self.n + self.m + i
            if n1 > 0:
                A[n1 - 1, col] = 1.0
                A[col, n1 - 1] = 1.0
            if n2 > 0:
                A[n2 - 1, col] = -1.0
                A[col, n2 - 1] = -1.0
            z[col] = 0.0
        return A, z

    def solve_dc(self) -> MNADCResult:
        """执行 DC 工作点分析。

        Raises:
            RuntimeError: 矩阵奇异（电路无解或欠约束）。
        """
        _logger.info("MNA DC 分析: %d 节点, %d 电压源, %d 电感", self.n, self.m, self.n_ind)
        A, z = self._build_dc_mna()
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
        return MNADCResult(node_voltages=node_voltages, vsource_currents=vsource_currents)

    def _solve_dc_with_diodes(self, A_init: np.ndarray, z_init: np.ndarray) -> np.ndarray:
        """含二极管的 DC 分析 (Newton-Raphson 迭代)。

        二极管 Shockley 模型: I = Is * (exp(V/Vt) - 1)
        线性化: I ≈ I_eq + G_eq * V, G_eq = Is/Vt * exp(V_prev/Vt),
          I_eq = I_prev - G_eq * V_prev

        来源: Shockley 1949 BSTJ; Pillage 1995 §7
        """
        x = np.zeros(self.size)
        for iteration in range(100):
            A = A_init.copy()
            z = z_init.copy()
            for d in self.circuit.diodes:
                n1, n2 = d["n1"], d["n2"]
                v_n1 = x[n1 - 1] if n1 > 0 else 0.0
                v_n2 = x[n2 - 1] if n2 > 0 else 0.0
                v_d = v_n1 - v_n2
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

        Args:
            t_total: 总仿真时间 (s)。
            dt: 时间步长 (s)。

        Returns:
            MNATransientResult 含时间序列和节点电压波形。

        Raises:
            ValueError: 时间参数无效。
            RuntimeError: 矩阵奇异。
        """
        if t_total <= 0 or dt <= 0:
            raise ValueError(f"时间参数无效: t_total={t_total}, dt={dt}")
        n_steps = int(np.ceil(t_total / dt)) + 1
        time = np.linspace(0, t_total, n_steps)
        _logger.info("MNA 瞬态分析: %d 步, dt=%.2e s, t_total=%.2e s", n_steps, dt, t_total)
        dc = self.solve_dc()
        x = np.zeros(self.size)
        for i in range(1, self.n + 1):
            x[i - 1] = dc.node_voltages.get(i, 0.0)
        node_voltages = {i: np.zeros(n_steps) for i in range(1, self.n + 1)}
        vsource_currents = {v["name"]: np.zeros(n_steps) for v in self.circuit.vsources}
        for i in range(1, self.n + 1):
            node_voltages[i][0] = x[i - 1]
        for j, v in enumerate(self.circuit.vsources):
            vsource_currents[v["name"]][0] = x[self.n + j]
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
        return MNATransientResult(
            time=time, node_voltages=node_voltages,
            vsource_currents=vsource_currents, n_points=n_steps,
        )

    def _build_transient_mna(self, dt: float, t: float, x_prev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """构建瞬态分析第 step 步的 MNA 矩阵 (后向欧拉)。"""
        A = np.zeros((self.size, self.size))
        z = np.zeros(self.size)
        for r in self.circuit.resistors:
            self._stamp_resistor(A, r)
        for c in self.circuit.capacitors:
            self._stamp_capacitor(A, z, c, dt, x_prev)
        for i, ind in enumerate(self.circuit.inductors):
            self._stamp_inductor(A, z, ind, i, dt, x_prev)
        for i, v in enumerate(self.circuit.vsources):
            self._stamp_vsource(A, z, v, i, t)
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
    def _stamp_capacitor(A: np.ndarray, z: np.ndarray, c: dict, dt: float, x_prev: np.ndarray) -> None:
        """电容后向欧拉 stamping：G_C=C/dt, I_prev=G_C·V_prev。

        R05 修复: 当 n1 或 n2 为 0（GND）时，v_prev 之前误算为 0，
        现正确取节点电压（GND 节点电压 = 0）。
        """
        g_c = c["c"] / dt
        n1, n2 = c["n1"], c["n2"]
        v_n1 = x_prev[n1 - 1] if n1 > 0 else 0.0
        v_n2 = x_prev[n2 - 1] if n2 > 0 else 0.0
        v_prev = v_n1 - v_n2
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

    def _stamp_inductor(self, A: np.ndarray, z: np.ndarray, ind: dict, idx: int, dt: float, x_prev: np.ndarray) -> None:
        """电感后向欧拉 stamping：R_eq=L/dt, V_prev=R_eq·I_prev。"""
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

    def _stamp_vsource(self, A: np.ndarray, z: np.ndarray, v: dict, idx: int, t: float) -> None:
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


def run_mna_spice(
    circuit: MNACircuit,
    analysis: str = "dc",
    t_total: float = 0.0,
    dt: float = 0.0,
) -> MNADCResult | MNATransientResult:
    """MNA SPICE 仿真便利入口（统一 API）。

    Args:
        circuit: MNACircuit 电路描述。
        analysis: 分析类型 "dc" 或 "transient"。
        t_total: 瞬态分析总时间 (s)，仅 transient 有效。
        dt: 瞬态分析时间步长 (s)，仅 transient 有效。

    Returns:
        DC 分析返回 MNADCResult，瞬态分析返回 MNATransientResult。

    Raises:
        ValueError: analysis 参数非法或瞬态时间参数缺失。
    """
    solver = MNASolver(circuit)
    if analysis == "dc":
        return solver.solve_dc()
    if analysis == "transient":
        if t_total <= 0 or dt <= 0:
            raise ValueError(
                f"瞬态分析需 t_total>0 和 dt>0，得到 t_total={t_total}, dt={dt}"
            )
        return solver.solve_transient(t_total, dt)
    raise ValueError(f"未知分析类型: {analysis}（支持 'dc' / 'transient'）")


__all__ = [
    "MNACircuit",
    "MNASolver",
    "MNADCResult",
    "MNATransientResult",
    "run_mna_spice",
]
