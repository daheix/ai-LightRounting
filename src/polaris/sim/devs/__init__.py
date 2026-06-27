"""C05-DEVS：Zeigler 经典 DEVS 离散事件系统规范包。

提供经典 DEVS 形式化的 Python 实现：
- AtomicDEVS: 原子模型基类
- CoupledDEVS: 耦合模型（网络模型）
- Simulator: 原子模型仿真器
- Coordinator: 耦合模型协调器
- Generator / Queue / Accumulator: 常用原子模型示例

文献来源（≥5）：
1. Zeigler BP, Praehofer H, Kim TG. "Theory of Modeling and Simulation."
   2nd ed., Academic Press (2000).
   https://www.elsevier.com/books/theory-of-modeling-and-simulation/zeigler/978-0-12-778455-7
2. Zeigler BP. "Theory of Modeling and Simulation." 1st ed., Wiley (1976).
3. Chow AC, Zeigler BP. "Parallel DEVS: a parallel, hierarchical, modular
   modeling formalism." WSC '94 (1994).
   https://doi.org/10.1109/WSC.1994.717431
4. Van Tendeloo Y, Vangheluwe H. "An evaluation of DEVS simulation tools."
   SIMULATION 93(2), 103-121 (2017).
   https://doi.org/10.1177/0037549716676811
5. Wainer GA. "Discrete-Event Modeling and Simulation." CRC Press (2009).
6. Nutaro JJ. "Building Software for Simulation." Wiley (2010).

规则依据：R03 无 fall-back / 纯 numpy/scipy / 中文注释
"""

from polaris.sim.devs.solver import (
    INFINITY,
    Accumulator,
    AtomicDEVS,
    Coordinator,
    CoupledDEVS,
    DEVSMessage,
    Generator,
    Queue,
    Simulator,
)

__all__ = [
    "INFINITY",
    "DEVSMessage",
    "AtomicDEVS",
    "CoupledDEVS",
    "Simulator",
    "Coordinator",
    "Generator",
    "Queue",
    "Accumulator",
]
