"""CAPHE 电路仿真后端（R26 路标）。

对标 CAPHE（Circuit Analysis Program for Photonic Elements）的电路级仿真，
提供频率域 S 参数块对角装配与 Schur 补消去求解。

## 模块组成

1. ``CAPHENode`` — 电路节点（S 参数矩阵 + 状态变量 + ODE 函数）
2. ``CAPHENetwork`` — 电路网络（节点 + 端口连接 + 外部端口）
3. ``CAPHEFrequencySolver`` — 频率域求解器（块对角 S + Schur 消去）

时域求解器 ``CAPHETimeDomainSolver`` 与统一后端 ``CAPHEBackend`` 见
``caphe_time_domain.py``（规则 7.1 单文件 ≤800 行拆分）。

## 学术依据

- CAPHE 电路仿真器: Fiers et al., "CAPHE: a circuit-level time-domain and
  frequency-domain modeling tool for nonlinear optical components", 2012
  URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf
- Laporte et al., "Highly parallel simulation and optimization of photonic
  circuits in time and frequency domain based on the deep-learning framework
  PyTorch", Scientific Reports 2019
  URL: https://doi.org/10.1038/s41598-019-42408-2
- Luceda CAPHE 产品页: https://www.lucedaphotonics.com/products/caphe
- S 参数级联子网络增长: SAX, https://flaport.github.io/sax/
- Schur 补消去内部端口: Bogaerts et al., "Silicon microring resonators",
  Laser & Photonics Reviews 6(1), 2012, https://doi.org/10.1002/lpor.201100017

合规: 规则 14.1 禁止 fall-back；规则 18 学术诚信；规则 7.1 文件 < 800 行。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from polaris.sim.models import (
    directional_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.types import ModelFunc, SDict

# CAPHE 与 SAX 交叉验证容差（S 参数幅值最大绝对误差阈值）
# 来源: 与 fdtd_gpu_engine.CROSS_VALIDATE_TOL 一致，1e-3 为工程级仿真容差
CROSS_VALIDATE_TOL: float = 1e-3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 器件类型到 S 参数模型的映射（来源: polaris.sim.models）
# 保留供外部模块使用；新 CAPHENode 直接持有 s_matrix，不再依赖 cell_type。
# ---------------------------------------------------------------------------
_MODEL_MAP: dict[str, ModelFunc] = {
    "waveguide": waveguide_s,
    "y_branch": y_branch_s,
    "directional_coupler": directional_coupler_s,
    "ring_resonator": ring_resonator_s,
    "mmi_1x2": mmi_1x2_s,
    "mmi_2x2": mmi_2x2_s,
    "phase_shifter": phase_shifter_s,
}


# ---------------------------------------------------------------------------
# CAPHENode — 电路节点（S 参数 + 状态变量 + ODE）
# ---------------------------------------------------------------------------
@dataclass
class CAPHENode:
    """CAPHE 电路节点（器件实例 + S 参数 + 状态变量 + ODE）。

    每个节点持有器件的 S 参数矩阵（常量 ndarray 或频率依赖函数
    ``s_func(wl)->ndarray``）、端口名、状态变量初值与可选 ODE 函数。
    含 ODE 的节点自动标记为非线性（``is_linear=False``）。

    学术依据: CAPHE 节点模型,
    Fiers et al. 2012, https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    Attributes:
        name: 节点名。
        s_matrix: S 参数矩阵（ndarray）或频率依赖函数 ``s_func(wl)->ndarray``。
        port_names: 端口名列表，空时默认 ``["in", "out"]``。
        state_variables: 状态变量初值 ``{name: float}``。
        ode_func: ODE 函数 ``ode_func(t, y, s_in)->dydt``，None 表示线性。
        is_linear: 是否线性；ode_func 非 None 时强制 False。
    """

    name: str
    s_matrix: Any
    port_names: list[str] = field(default_factory=list)
    state_variables: dict = field(default_factory=dict)
    ode_func: Callable[..., np.ndarray] | None = None
    is_linear: bool = True

    def __post_init__(self) -> None:
        """初始化后补全端口名与线性标志。"""
        if not self.port_names:
            self.port_names = ["in", "out"]
        if self.ode_func is not None:
            self.is_linear = False

    @property
    def n_ports(self) -> int:
        """端口数 = len(port_names) = S 矩阵维度。"""
        return len(self.port_names)

    def get_s_matrix(self, wl: float) -> np.ndarray:
        """返回指定波长处的 S 矩阵。

        Args:
            wl: 波长（μm）。

        Returns:
            复数 S 矩阵 ndarray。

        Raises:
            ValueError: S 矩阵维度与端口数不匹配时。
        """
        if callable(self.s_matrix):
            smat = np.asarray(self.s_matrix(wl), dtype=complex)
        else:
            smat = np.asarray(self.s_matrix, dtype=complex)
        if smat.shape != (self.n_ports, self.n_ports):
            raise ValueError(
                f"节点 '{self.name}' S 矩阵形状 {smat.shape} 与端口数 "
                f"{self.n_ports} 不匹配"
            )
        return smat

    def get_state_vector(self) -> np.ndarray:
        """返回状态变量初值数组（按 state_variables.values() 顺序）。"""
        return np.array(list(self.state_variables.values()), dtype=float)


# ---------------------------------------------------------------------------
# CAPHENetwork — 电路网络（节点 + 连接 + 外部端口）
# ---------------------------------------------------------------------------
@dataclass
class CAPHENetwork:
    """CAPHE 电路网络（节点集合 + 端口连接 + 外部端口）。

    学术依据: CAPHE 网络拓扑,
    Fiers et al. 2012, https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    Attributes:
        nodes: 节点字典 ``{name: CAPHENode}``。
        connections: 连接列表，每项 ``(name1, port1, name2, port2)``。
        external_ports: 外部端口 ``{ext_name: (node_name, port_idx)}``。
    """

    nodes: dict[str, CAPHENode] = field(default_factory=dict)
    connections: list[tuple] = field(default_factory=list)
    external_ports: dict[str, tuple] = field(default_factory=dict)
    # 已连接端口集合，用于 connect() 重复连接校验（私有，不参与 repr/eq）
    _connected: set[tuple[str, int]] = field(
        default_factory=set, repr=False, compare=False
    )

    def add_node(self, node: CAPHENode) -> None:
        """添加节点。

        Raises:
            ValueError: 节点名已存在。
        """
        if node.name in self.nodes:
            raise ValueError(f"节点 '{node.name}' 已存在")
        self.nodes[node.name] = node

    def connect(self, name1: str, port1: int, name2: str, port2: int) -> None:
        """连接两节点的端口（整数端口索引）。

        Args:
            name1: 节点 1 名称。
            port1: 节点 1 端口索引。
            name2: 节点 2 名称。
            port2: 节点 2 端口索引。

        Raises:
            ValueError: 节点不存在 / 端口越界 / 端口已被连接。
        """
        if name1 not in self.nodes:
            raise ValueError(f"节点 '{name1}' 不存在")
        if name2 not in self.nodes:
            raise ValueError(f"节点 '{name2}' 不存在")
        n1, n2 = self.nodes[name1], self.nodes[name2]
        if not 0 <= port1 < n1.n_ports:
            raise ValueError(
                f"节点 '{name1}' 端口 {port1} 越界（共 {n1.n_ports} 端口）"
            )
        if not 0 <= port2 < n2.n_ports:
            raise ValueError(
                f"节点 '{name2}' 端口 {port2} 越界（共 {n2.n_ports} 端口）"
            )
        k1, k2 = (name1, port1), (name2, port2)
        if k1 in self._connected or k2 in self._connected:
            raise ValueError(f"端口 {k1}/{k2} 已被连接")
        self.connections.append((name1, port1, name2, port2))
        self._connected.add(k1)
        self._connected.add(k2)

    def add_external_port(
        self, ext_name: str, node_name: str, port_idx: int
    ) -> None:
        """添加外部端口。

        Args:
            ext_name: 外部端口名。
            node_name: 所属节点名。
            port_idx: 节点端口索引。

        Raises:
            ValueError: 节点不存在 / 端口越界。
        """
        if node_name not in self.nodes:
            raise ValueError(f"节点 '{node_name}' 不存在")
        node = self.nodes[node_name]
        if not 0 <= port_idx < node.n_ports:
            raise ValueError(
                f"节点 '{node_name}' 端口 {port_idx} 越界（共 {node.n_ports} 端口）"
            )
        self.external_ports[ext_name] = (node_name, port_idx)

    @property
    def n_nodes(self) -> int:
        """节点数。"""
        return len(self.nodes)

    def get_node(self, name: str) -> CAPHENode:
        """按名获取节点。

        Raises:
            ValueError: 节点不存在。
        """
        if name not in self.nodes:
            raise ValueError(f"节点 '{name}' 不存在")
        return self.nodes[name]

    def get_nodes(self) -> list[CAPHENode]:
        """返回所有节点列表。"""
        return list(self.nodes.values())


# ---------------------------------------------------------------------------
# CAPHEFrequencySolver — 频率域求解器（块对角 S + Schur 消去）
# ---------------------------------------------------------------------------
class CAPHEFrequencySolver:
    """CAPHE 频率域求解器（块对角 S 矩阵 + Schur 补消去内部端口）。

    学术依据: CAPHE 频域求解（Fiers 2012 §III-A），
    https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    求解思路:
        - 全局 S 矩阵为各节点 S 矩阵的块对角拼接。
        - 连接约束: 互连端口处 a_i = b_j, a_j = b_i（连接矩阵 K）。
        - 外部端口 a 已知（输入），求解 ``b = (I - S·K)^{-1}·S·a_ext``。
        - Schur 补消去内部端口得外部端口等效 S 矩阵。
    """

    def __init__(self, network: CAPHENetwork) -> None:
        """初始化频域求解器并构建端口全局索引。

        Args:
            network: 待求解网络。
        """
        self.network = network
        self._port_offset: dict[str, int] = {}
        offset = 0
        for name, node in network.nodes.items():
            self._port_offset[name] = offset
            offset += node.n_ports
        self._n_total: int = offset

    def _global_port(self, node_name: str, port_idx: int) -> int:
        """(节点名, 端口索引) -> 全局端口索引。"""
        return self._port_offset[node_name] + port_idx

    def build_global_matrix(self, wl: float) -> np.ndarray:
        """构建块对角全局 S 矩阵。

        Args:
            wl: 波长（μm）。

        Returns:
            (总端口数, 总端口数) 复数矩阵。
        """
        n = self._n_total
        s_global = np.zeros((n, n), dtype=complex)
        for name, node in self.network.nodes.items():
            off = self._port_offset[name]
            smat = node.get_s_matrix(wl)
            k = smat.shape[0]
            s_global[off:off + k, off:off + k] = smat
        return s_global

    def _build_connection_matrix(self) -> np.ndarray:
        """构建连接矩阵 K：K[g1,g2]=1 表示 a_{g1}=b_{g2}。"""
        n = self._n_total
        k_mat = np.zeros((n, n), dtype=complex)
        for (n1, p1, n2, p2) in self.network.connections:
            g1 = self._global_port(n1, p1)
            g2 = self._global_port(n2, p2)
            k_mat[g1, g2] = 1.0
            k_mat[g2, g1] = 1.0
        return k_mat

    def _external_global_indices(self) -> dict[str, int]:
        """外部端口名 -> 全局端口索引。"""
        return {
            ext: self._global_port(nname, pidx)
            for ext, (nname, pidx) in self.network.external_ports.items()
        }

    def eliminate_linear_nodes(
        self, wavelength: float
    ) -> tuple[np.ndarray, list[int]]:
        """Schur 补消去内部端口，返回外部端口等效 S 矩阵。

        M_reduced = S_ee + S_ei · K_ii · (I - S_ii·K_ii)^{-1} · S_ie

        Args:
            wavelength: 波长（μm）。

        Returns:
            (M_reduced, eliminated_port_list): 约简矩阵与被消去端口全局索引列表。
        """
        s_global = self.build_global_matrix(wavelength)
        k_mat = self._build_connection_matrix()
        ext_map = self._external_global_indices()
        ext_set = set(ext_map.values())
        n = self._n_total
        ext_idx = np.array(sorted(ext_set), dtype=int)
        internal_idx = np.array(
            [i for i in range(n) if i not in ext_set], dtype=int
        )
        if len(internal_idx) == 0:
            return s_global[np.ix_(ext_idx, ext_idx)], []
        s_ee = s_global[np.ix_(ext_idx, ext_idx)]
        s_ei = s_global[np.ix_(ext_idx, internal_idx)]
        s_ie = s_global[np.ix_(internal_idx, ext_idx)]
        s_ii = s_global[np.ix_(internal_idx, internal_idx)]
        k_ii = k_mat[np.ix_(internal_idx, internal_idx)]
        eye_i = np.eye(len(internal_idx), dtype=complex)
        a_mat = eye_i - s_ii @ k_ii
        m_reduced = s_ee + s_ei @ k_ii @ np.linalg.solve(a_mat, s_ie)
        return m_reduced, internal_idx.tolist()

    def solve(
        self,
        wavelengths: list[float],
        inputs: dict[str, complex],
    ) -> dict:
        """频率域求解：对每个波长求解外部端口输出。

        求解 ``b = (I - S·K)^{-1}·S·a_ext``，输出外部端口处的 b。

        Args:
            wavelengths: 波长列表（μm）。
            inputs: 外部端口输入 ``{ext_name: amplitude}``。

        Returns:
            ``{"wavelengths": [...], "outputs": {ext_name: complex_array}}``。

        Raises:
            ValueError: 输入端口不存在。
            numpy.linalg.LinAlgError: 矩阵奇异（电路拓扑非法）。
        """
        ext_map = self._external_global_indices()
        n = self._n_total
        for ext_name in inputs:
            if ext_name not in ext_map:
                raise ValueError(
                    f"输入端口 '{ext_name}' 不存在，可用: {list(ext_map)}"
                )
        wl_list = list(wavelengths)
        out_lists: dict[str, list[complex]] = {
            ext: [] for ext in self.network.external_ports
        }
        eye_n = np.eye(n, dtype=complex)
        for wl in wl_list:
            s_global = self.build_global_matrix(wl)
            k_mat = self._build_connection_matrix()
            a_ext = np.zeros(n, dtype=complex)
            for ext_name, val in inputs.items():
                a_ext[ext_map[ext_name]] = complex(val)
            a_mat = eye_n - s_global @ k_mat
            b_vec = np.linalg.solve(a_mat, s_global @ a_ext)
            for ext_name in self.network.external_ports:
                out_lists[ext_name].append(b_vec[ext_map[ext_name]])
        outputs = {
            ext: np.array(vals, dtype=complex)
            for ext, vals in out_lists.items()
        }
        return {"wavelengths": wl_list, "outputs": outputs}


# ---------------------------------------------------------------------------
# 向后兼容：CAPHEBackend / CAPHETimeDomainSolver 已迁移至 caphe_time_domain.py
# ---------------------------------------------------------------------------
def __getattr__(name: str):
    """PEP 562 惰性重导出。

    CAPHEBackend 与 CAPHETimeDomainSolver 已迁移至 ``caphe_time_domain.py``
    （规则 7.1 单文件 ≤800 行）。为兼容历史导入路径
    （``from polaris.sim.caphe_backend import CAPHEBackend``），在此惰性重导出，
    避免模块加载期循环导入。
    """
    if name in {"CAPHEBackend", "CAPHETimeDomainSolver"}:
        from polaris.sim.caphe_time_domain import (
            CAPHEBackend,
            CAPHETimeDomainSolver,
        )
        return {
            "CAPHEBackend": CAPHEBackend,
            "CAPHETimeDomainSolver": CAPHETimeDomainSolver,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CAPHENode",
    "CAPHENetwork",
    "CAPHEFrequencySolver",
    "CROSS_VALIDATE_TOL",
    "SDict",
    "ModelFunc",
    "waveguide_s",
    "y_branch_s",
    "directional_coupler_s",
    "ring_resonator_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "phase_shifter_s",
]
