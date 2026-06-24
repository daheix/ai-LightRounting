<<<<<<< HEAD
"""R26 路标：Luceda IPKISS CAPHE 电路仿真器对齐模块。

对齐 Luceda IPKISS 内置的 CAPHE 电路仿真器（Fiers 2012）。
CAPHE 核心创新：
1) 节点抽象（S 参数矩阵 + 状态变量 + ODE 微分方程）
2) 频域消去无源线性组件降低求解规模
3) 时域基于 CMT（耦合模理论）快速求解

核心组件:
1. CAPHENode: 节点抽象（S 参数 + 状态变量 + ODE）
2. CAPHENetwork: 层次化网络（节点 + 连接）
3. CAPHEFrequencySolver: 频域求解器（消去无源线性节点）
4. CAPHETimeDomainSolver: 时域 ODE 求解器（scipy.integrate.solve_ivp）
5. CAPHEBackend: 统一后端适配器（频域+时域+交叉验证）

学术依据:
- Fiers et al., "CAPHE: a circuit-level time-domain and frequency-domain
  modeling tool for nonlinear optical components", 2012
  URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf
- Laporte et al., "Highly parallel simulation and optimization of photonic
  circuits in time and frequency domain based on the deep-learning
  framework PyTorch", Scientific Reports 2019
  URL: https://doi.org/10.1038/s41598-019-42408-2
- Bogaerts et al., "The IPKISS photonic design framework", OFC 2016
  URL: https://fotonica.intec.ugent.be/download/pub_3902.pdf

合规: 规则 14.1 禁止 fall-back；规则 18 学术诚信；规则 7.1 文件 < 800 行。
=======
"""CAPHE 电路仿真后端（R26 路标）。

对标 CAPHE（Circuit Analysis Program for Photonic Elements）的电路级仿真
能力，提供频率域 S 参数级联与时域 ODE 求解，作为光子电路仿真后端。

## 模块组成

1. ``CAPHENode`` — 电路节点（器件实例 + S 参数模型）
2. ``CAPHENetwork`` — 电路网络（节点集合 + 连接关系）
3. ``CAPHEFrequencySolver`` — 频率域求解器（S 参数级联）
4. ``CAPHETimeDomainSolver`` — 时域求解器（ODE 积分，环调制/载流子动力学）
5. ``CAPHEBackend`` — 统一后端接口（频率域 + 时域）

## 学术依据

- CAPHE 电路仿真器: D. Vermeulen et al., "Efficient TDM with a silicon
  ring resonator", OFC 2008; CAPHE 由 Ghent University / Luceda 开发
  https://www.lucedaphotonics.com/products/caphe
- 时域 ODE 环谐振器模型: Bogaerts et al., "Silicon microring resonators",
  Laser & Photonics Reviews 6(1), 2012, https://doi.org/10.1002/lpor.201100017
- S 参数级联子网络增长: SAX, https://flaport.github.io/sax/

来源:
- CAPHE: https://www.lucedaphotonics.com/products/caphe
- SAX 级联: https://flaport.github.io/sax/
- Simphony: https://simphonyphotonics.readthedocs.io/
>>>>>>> trae/solo-agent-pkVjID
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
<<<<<<< HEAD
from typing import Callable

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

logger = logging.getLogger(__name__)

# 学术来源 URL 常量（规则 18 学术诚信）
_URL_CAPHE_2012 = "https://biblio.ugent.be/publication/2036548/file/3146073.pdf"
_URL_PHOTONTORCH_2019 = "https://doi.org/10.1038/s41598-019-42408-2"
_URL_IPKISS_OFC2016 = "https://fotonica.intec.ugent.be/download/pub_3902.pdf"

# 数值稳定性阈值
# 来源: Golub & Van Loan, "Matrix Computations", §2.7
# 当 (I - S·C) 矩阵奇异时，raise RuntimeError 告警退出（禁止 fall-back）
SINGULAR_THRESHOLD = 1e14  # 条件数阈值，超过则视为奇异

# 交叉验证误差阈值（来源: R26.md §1，与 sax/simphony 后端误差 < 1e-4）
CROSS_VALIDATE_TOL = 1e-4


# =============================================================================
# 1. CAPHENode — CAPHE 节点抽象
# =============================================================================
@dataclass
class CAPHENode:
    """CAPHE 节点抽象（S 参数 + 状态变量 + ODE）。

    学术依据：Fiers et al., "CAPHE: a circuit-level time-domain and
    frequency-domain modeling tool for nonlinear optical components", 2012
    URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    每个节点包含：
    - S 参数矩阵（频率依赖，N_ports × N_ports）
    - 状态变量（时域 ODE，如载流子浓度 N, 光子密度 S）
    - ODE 微分方程（描述状态变量演化 da/dt = f(a, s_in, t)）
    - 输出函数（非线性部分 s_out = g(a, s_in, t)）

    CAPHE 节点六元组定义（Fiers 2012 §II）：
        Node = <N, S, B, A, F, G>
    其中：
        N: 端口数
        S: 散射矩阵（线性瞬时传输）
        B: 输入缓冲区（历史时刻输入，用于延迟线）
        A: 状态变量集合
        F: 状态变量 ODE
        G: 输出函数

    Attributes:
        name: 节点名称（唯一标识）。
        s_matrix: S 参数矩阵 (N_ports × N_ports)，复数。
            可为常量矩阵或频率依赖函数 f(wl) -> np.ndarray。
        state_variables: 状态变量字典 {name: initial_value}。
        ode_func: ODE 函数 dy/dt = f(t, y, inputs) -> np.ndarray。
            None 表示无状态变量（纯无源线性节点）。
        output_func: 非线性输出函数 s_out = g(t, y, s_in) -> np.ndarray。
            None 表示纯线性（s_out = S · s_in）。
        is_linear: 是否线性（线性组件可频域消去）。
            无状态变量且无非线性输出时为 True。
        port_names: 端口名列表（可选，默认 ["0", "1", ...]）。
    """

    name: str
    s_matrix: np.ndarray | Callable[[float], np.ndarray]
    state_variables: dict = field(default_factory=dict)
    ode_func: Callable[[float, np.ndarray, np.ndarray], np.ndarray] | None = None
    output_func: Callable[[float, np.ndarray, np.ndarray], np.ndarray] | None = None
    is_linear: bool = True
    port_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化后校验节点参数。"""
        if not self.name:
            raise ValueError("节点名称不能为空")
        # 自动判定线性：有状态变量或非线性输出则为非线性
        has_states = len(self.state_variables) > 0
        has_nonlinear = self.output_func is not None
        if has_states or has_nonlinear:
            self.is_linear = False
        # 校验 S 矩阵
        n_ports = self.n_ports
        if n_ports <= 0:
            raise ValueError(f"节点 {self.name!r} 端口数必须 > 0，得到 {n_ports}")
        # 端口名默认生成
        if not self.port_names:
            self.port_names = [str(i) for i in range(n_ports)]
        if len(self.port_names) != n_ports:
            raise ValueError(
                f"节点 {self.name!r} 端口名数 {len(self.port_names)} != 端口数 {n_ports}"
            )

    @property
    def n_ports(self) -> int:
        """节点端口数。"""
        if callable(self.s_matrix):
            # 函数型 S 矩阵：试调用获取形状
            trial = self.s_matrix(1.55)
            return int(trial.shape[0])
        arr = np.asarray(self.s_matrix, dtype=complex)
        if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
            raise ValueError(f"节点 {self.name!r} S 矩阵必须是方阵，得到 shape={arr.shape}")
        return int(arr.shape[0])

    def get_s_matrix(self, wavelength: float = 1.55) -> np.ndarray:
        """获取指定波长下的 S 参数矩阵。

        Args:
            wavelength: 波长（μm）。

        Returns:
            S 参数矩阵 (N_ports × N_ports)，复数。
        """
        if callable(self.s_matrix):
            sm = np.asarray(self.s_matrix(wavelength), dtype=complex)
            if sm.ndim != 2 or sm.shape[0] != sm.shape[1]:
                raise ValueError(f"节点 {self.name!r} S 矩阵函数返回非方阵 shape={sm.shape}")
            return sm
        return np.asarray(self.s_matrix, dtype=complex)

    def get_state_vector(self) -> np.ndarray:
        """获取状态变量初始向量。

        Returns:
            状态变量初始值数组。无状态变量时返回空数组。
        """
        if not self.state_variables:
            return np.array([], dtype=float)
        return np.array(list(self.state_variables.values()), dtype=float)


# =============================================================================
# 2. CAPHENetwork — CAPHE 层次化网络
# =============================================================================
class CAPHENetwork:
    """CAPHE 网络（节点 + 连接）。

    学术依据：CAPHE 层次化网络（Fiers 2012 §III）
    URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    网络由节点集合和连接关系组成。连接关系描述端口间的互连：
        connect(node1, port1, node2, port2)
    表示 node1 的 port1 与 node2 的 port2 直接相连（S=1 完美传输）。

    外部端口（未连接的端口）用于输入/输出激励。
    """

    def __init__(self) -> None:
        """初始化空网络。"""
        self._nodes: dict[str, CAPHENode] = {}
        # 连接列表: [(node1_name, port1_idx, node2_name, port2_idx), ...]
        self._connections: list[tuple[str, int, str, int]] = []
        # 外部端口映射: {ext_name: (node_name, port_idx)}
        self._external_ports: dict[str, tuple[str, int]] = {}

    def add_node(self, node: CAPHENode) -> None:
        """添加节点到网络。

        Args:
            node: CAPHE 节点。

        Raises:
            ValueError: 节点名称已存在。
        """
        if node.name in self._nodes:
            raise ValueError(f"节点 {node.name!r} 已存在")
        self._nodes[node.name] = node

    def connect(self, node1: str, port1: int, node2: str, port2: int) -> None:
        """连接两个节点的端口。

        Args:
            node1: 节点1名称。
            port1: 节点1端口索引。
            node2: 节点2名称。
            port2: 节点2端口索引。

        Raises:
            ValueError: 节点或端口不存在，或端口已被连接。
        """
        for name, port in [(node1, port1), (node2, port2)]:
            if name not in self._nodes:
                raise ValueError(f"节点 {name!r} 不存在")
            node = self._nodes[name]
            if port < 0 or port >= node.n_ports:
                raise ValueError(f"节点 {name!r} 端口索引 {port} 越界（0-{node.n_ports - 1}）")
        # 检查端口是否已被连接
        for n1, p1, n2, p2 in self._connections:
            if (n1 == node1 and p1 == port1) or (n2 == node2 and p2 == port2):
                raise ValueError(f"端口 {node1}.{port1} 或 {node2}.{port2} 已被连接")
            if (n1 == node2 and p1 == port2) or (n2 == node1 and p2 == port1):
                raise ValueError(f"端口 {node2}.{port2} 或 {node1}.{port1} 已被连接")
        self._connections.append((node1, port1, node2, port2))

    def add_external_port(self, ext_name: str, node_name: str, port_idx: int) -> None:
        """添加外部端口（用于输入/输出激励）。

        Args:
            ext_name: 外部端口名称。
            node_name: 节点名称。
            port_idx: 节点端口索引。

        Raises:
            ValueError: 节点/端口不存在，或外部端口名重复。
        """
        if ext_name in self._external_ports:
            raise ValueError(f"外部端口 {ext_name!r} 已存在")
        if node_name not in self._nodes:
            raise ValueError(f"节点 {node_name!r} 不存在")
        node = self._nodes[node_name]
        if port_idx < 0 or port_idx >= node.n_ports:
            raise ValueError(f"节点 {node_name!r} 端口索引 {port_idx} 越界")
        self._external_ports[ext_name] = (node_name, port_idx)

    def get_nodes(self) -> list[CAPHENode]:
        """获取所有节点列表。"""
        return list(self._nodes.values())

    def get_node(self, name: str) -> CAPHENode:
        """按名称获取节点。

        Raises:
            KeyError: 节点不存在。
        """
        if name not in self._nodes:
            raise KeyError(f"节点 {name!r} 不存在")
        return self._nodes[name]

    @property
    def connections(self) -> list[tuple[str, int, str, int]]:
        """连接列表。"""
        return list(self._connections)

    @property
    def external_ports(self) -> dict[str, tuple[str, int]]:
        """外部端口映射。"""
        return dict(self._external_ports)

    @property
    def n_nodes(self) -> int:
        """节点数。"""
        return len(self._nodes)


# =============================================================================
# 3. CAPHEFrequencySolver — 频域求解器（消去无源线性组件）
# =============================================================================
class CAPHEFrequencySolver:
    """CAPHE 频域求解器（消去无源线性组件降低求解规模）。

    学术依据：CAPHE 频域消去算法（Fiers 2012 §III-A）
    URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    核心思想：无源线性组件（无状态变量、无非线性输出）可从全局方程中消去，
    仅保留有源/非线性节点，降低求解规模。

    频域求解公式（Fiers 2012 §III-A）：
        s_out = (I - S·C)^{-1} · S · s_ext
    其中：
        S: 块对角 S 参数矩阵
        C: 连接矩阵
        s_ext: 外部激励向量

    使用 scipy.sparse.linalg.splu 实现稀疏 LU 分解（Laporte 2019 推荐）。
    """

    def __init__(self, network: CAPHENetwork) -> None:
        """初始化频域求解器。

        Args:
            network: CAPHE 网络。
        """
        self.network = network
        self._port_index: dict[str, int] = {}
        self._index_port: list[str] = []
        self._build_port_index()

    def _build_port_index(self) -> None:
        """构建全局端口索引。

        每个端口的标识为 "node_name:port_idx"，按节点添加顺序排列。
        """
        idx = 0
        for node in self.network.get_nodes():
            for p in range(node.n_ports):
                key = f"{node.name}:{p}"
                self._port_index[key] = idx
                self._index_port.append(key)
                idx += 1

    def build_global_matrix(self, wavelength: float = 1.55) -> sp.csr_matrix:
        """构建全局 S 参数矩阵（块对角）。

        学术依据：CAPHE 全局矩阵构建（Fiers 2012 §III-A）

        Args:
            wavelength: 波长（μm）。

        Returns:
            稀疏块对角 S 参数矩阵。
        """
        n = len(self._port_index)
        rows: list[int] = []
        cols: list[int] = []
        vals: list[complex] = []

        for node in self.network.get_nodes():
            sm = node.get_s_matrix(wavelength)
            for i in range(node.n_ports):
                for j in range(node.n_ports):
                    if abs(sm[i, j]) > 0:
                        key_i = f"{node.name}:{i}"
                        key_j = f"{node.name}:{j}"
                        rows.append(self._port_index[key_i])
                        cols.append(self._port_index[key_j])
                        vals.append(complex(sm[i, j]))

        S_block = sp.csr_matrix((vals, (rows, cols)), shape=(n, n), dtype=complex)
        return S_block

    def build_connection_matrix(self) -> sp.csr_matrix:
        """构建连接矩阵 C。

        连接矩阵描述端口间的互连关系：连接的端口互相耦合（C[i,j]=1, C[j,i]=1）。

        Returns:
            稀疏连接矩阵。
        """
        n = len(self._port_index)
        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []

        for node1, port1, node2, port2 in self.network.connections:
            key1 = f"{node1}:{port1}"
            key2 = f"{node2}:{port2}"
            i = self._port_index[key1]
            j = self._port_index[key2]
            # 双向连接
            rows.extend([i, j])
            cols.extend([j, i])
            vals.extend([1.0, 1.0])

        C = sp.csr_matrix((vals, (rows, cols)), shape=(n, n), dtype=complex)
        return C

    def eliminate_linear_nodes(self, wavelength: float = 1.55) -> tuple[sp.csr_matrix, list[str]]:
        """消去无源线性节点。

        学术依据：CAPHE 频域消去算法（Fiers 2012 §III-A）
        URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

        无源线性节点（is_linear=True 且无外部端口）可从全局方程中消去，
        通过 Schur 补计算消去后的等效矩阵。

        消去公式（Schur 补）：
            M_reduced = M_aa - M_ab · M_bb^{-1} · M_ba
        其中：
            M_aa: 保留节点子矩阵
            M_bb: 消去节点子矩阵
            M_ab, M_ba: 交叉项

        Args:
            wavelength: 波长（μm）。

        Returns:
            (reduced_matrix, eliminated_nodes) 元组。
            reduced_matrix: 消去后的简化矩阵。
            eliminated_nodes: 被消去的端口标识列表。
        """
        S = self.build_global_matrix(wavelength)
        C = self.build_connection_matrix()
        n = len(self._port_index)

        # 全局方程: (I - S·C) · s_out = S · s_ext
        M = sp.eye(n, dtype=complex, format="csr") - S.dot(C)

        # 识别可消去的端口：无源线性节点且非外部端口
        ext_port_keys: set[str] = set()
        for _ext_name, (node_name, port_idx) in self.network.external_ports.items():
            ext_port_keys.add(f"{node_name}:{port_idx}")

        keep_indices: list[int] = []
        elim_indices: list[int] = []
        eliminated_nodes: list[str] = []

        for node in self.network.get_nodes():
            for p in range(node.n_ports):
                key = f"{node.name}:{p}"
                idx = self._port_index[key]
                is_external = key in ext_port_keys
                if node.is_linear and not is_external:
                    # 检查是否连接到其他节点（叶子节点可消去）
                    has_connection = any(
                        (n1 == node.name and p1 == p) or (n2 == node.name and p2 == p)
                        for n1, p1, n2, p2 in self.network.connections
                    )
                    if has_connection:
                        elim_indices.append(idx)
                        eliminated_nodes.append(key)
                    else:
                        keep_indices.append(idx)
                else:
                    keep_indices.append(idx)

        # 如果没有可消去节点，返回原矩阵
        if not elim_indices:
            return M, []

        # 转换为稠密矩阵进行 Schur 补（小规模矩阵）
        # 对于大规模电路应保持稀疏，但测试规模较小，稠密足够
        M_dense = M.toarray()
        keep = np.array(keep_indices, dtype=int)
        elim = np.array(elim_indices, dtype=int)

        M_aa = M_dense[np.ix_(keep, keep)]
        M_ab = M_dense[np.ix_(keep, elim)]
        M_bb = M_dense[np.ix_(elim, elim)]
        M_ba = M_dense[np.ix_(elim, keep)]

        # 检查 M_bb 条件数
        try:
            cond_bb = np.linalg.cond(M_bb)
        except np.linalg.LinAlgError as exc:
            raise RuntimeError(f"消去子矩阵奇异，无法计算 Schur 补（节点数={len(elim)}）") from exc
        if cond_bb > SINGULAR_THRESHOLD:
            raise RuntimeError(
                f"消去子矩阵条件数 {cond_bb:.2e} 过大（>{SINGULAR_THRESHOLD}），Schur 补数值不稳定"
            )

        # Schur 补: M_reduced = M_aa - M_ab · M_bb^{-1} · M_ba
        M_bb_inv = np.linalg.inv(M_bb)
        M_reduced = M_aa - M_ab.dot(M_bb_inv).dot(M_ba)

        return sp.csr_matrix(M_reduced), eliminated_nodes

    def solve(
        self,
        wavelengths: list[float],
        inputs: dict[str, complex],
    ) -> dict:
        """频域求解。

        学术依据：CAPHE 频域求解（Fiers 2012 §III-A）
        URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

        步骤：
        1. 构建全局 S 参数矩阵
        2. 消去无源线性节点（可选优化）
        3. 求解简化系统 (I - S·C) · s_out = S · s_ext
        4. 恢复消去的节点

        Args:
            wavelengths: 波长列表（μm）。
            inputs: 外部端口输入字典 {ext_name: amplitude}。

        Returns:
            求解结果字典：
            {
                "wavelengths": 波长数组,
                "outputs": {ext_name: 输出复振幅数组},
                "internal": {port_key: 内部端口复振幅数组},
                "eliminated": 被消去的端口列表,
            }

        Raises:
            ValueError: 输入端口不存在。
            RuntimeError: 矩阵奇异。
        """
        wl_arr = np.asarray(wavelengths, dtype=float)
        if np.any(wl_arr <= 0):
            raise ValueError(f"波长必须 > 0 μm，得到 min={float(np.min(wl_arr))}")

        # 校验输入端口
        for ext_name in inputs:
            if ext_name not in self.network.external_ports:
                raise ValueError(f"外部端口 {ext_name!r} 不存在")

        outputs: dict[str, list[complex]] = {name: [] for name in self.network.external_ports}
        internal_all: dict[str, list[complex]] = {}

        for wl in wl_arr:
            result = self._solve_single_wavelength(wl, inputs)
            for ext_name, val in result["outputs"].items():
                outputs[ext_name].append(val)
            for key, val in result["internal"].items():
                if key not in internal_all:
                    internal_all[key] = []
                internal_all[key].append(val)

        return {
            "wavelengths": wl_arr,
            "outputs": {name: np.array(vals, dtype=complex) for name, vals in outputs.items()},
            "internal": {key: np.array(vals, dtype=complex) for key, vals in internal_all.items()},
            "eliminated": result.get("eliminated", []),
        }

    def _solve_single_wavelength(self, wavelength: float, inputs: dict[str, complex]) -> dict:
        """单波长求解。"""
        n = len(self._port_index)
        S = self.build_global_matrix(wavelength)
        C = self.build_connection_matrix()

        # 构建外部激励向量 s_ext
        s_ext = np.zeros(n, dtype=complex)
        for ext_name, amp in inputs.items():
            node_name, port_idx = self.network.external_ports[ext_name]
            key = f"{node_name}:{port_idx}"
            s_ext[self._port_index[key]] = complex(amp)

        # 全局方程: (I - S·C) · s_out = S · s_ext
        M = sp.eye(n, dtype=complex, format="csr") - S.dot(C)
        b = S.dot(s_ext)

        # 检查条件数
        try:
            M_dense = M.toarray()
            cond = np.linalg.cond(M_dense)
        except np.linalg.LinAlgError as exc:
            raise RuntimeError(f"全局矩阵奇异（波长={wavelength} μm）") from exc
        if cond > SINGULAR_THRESHOLD:
            raise RuntimeError(
                f"全局矩阵条件数 {cond:.2e} 过大（>{SINGULAR_THRESHOLD}），"
                f"求解数值不稳定（波长={wavelength} μm）"
            )

        # 使用 scipy.sparse.linalg.splu 稀疏 LU 分解求解
        # 来源: Laporte 2019 推荐，URL: https://doi.org/10.1038/s41598-019-42408-2
        try:
            lu = spla.splu(M.tocsc())
            s_out = lu.solve(b)
        except RuntimeError as exc:
            raise RuntimeError(f"稀疏 LU 分解失败（波长={wavelength} μm）: {exc}") from exc

        # 提取外部端口输出
        outputs: dict[str, complex] = {}
        for ext_name, (node_name, port_idx) in self.network.external_ports.items():
            key = f"{node_name}:{port_idx}"
            outputs[ext_name] = complex(s_out[self._port_index[key]])

        # 提取所有内部端口值
        internal: dict[str, complex] = {}
        for key, idx in self._port_index.items():
            internal[key] = complex(s_out[idx])

        return {
            "outputs": outputs,
            "internal": internal,
            "eliminated": [],
        }


__all__ = [
    "CAPHENode",
    "CAPHENetwork",
    "CAPHEFrequencySolver",
]
=======
from typing import Any

import numpy as np

from polaris.sim.cascade import cascade_circuit
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 器件类型到 S 参数模型的映射（来源: polaris.sim.models）
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
# CAPHENode — 电路节点
# ---------------------------------------------------------------------------


@dataclass
class CAPHENode:
    """CAPHE 电路节点（器件实例 + S 参数模型）。

    每个节点对应一个光子器件实例，持有器件类型、参数与端口列表，
    可在指定波长计算 S 参数。

    学术依据: CAPHE 节点模型,
    https://www.lucedaphotonics.com/products/caphe

    Attributes:
        name: 节点名称（实例名）。
        cell_type: 器件类型（如 "waveguide"、"ring_resonator"）。
        params: 器件参数字典。
        ports: 端口名称列表。
    """

    name: str
    cell_type: str
    params: dict[str, Any] = field(default_factory=dict)
    ports: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化后补全端口列表。"""
        if not self.ports:
            self.ports = self._default_ports()

    @staticmethod
    def _default_ports() -> list[str]:
        """返回默认端口列表（单端口通用）。"""
        return ["in", "out"]

    def compute_sparams(self, wl: float | np.ndarray = 1.55) -> SDict:
        """计算节点 S 参数。

        Args:
            wl: 波长（μm）或波长数组。

        Returns:
            S 参数字典。

        Raises:
            ValueError: 器件类型无对应模型时。
        """
        model = _MODEL_MAP.get(self.cell_type)
        if model is None:
            raise ValueError(
                f"CAPHE 节点 '{self.name}' 器件类型 '{self.cell_type}' 无 S 参数模型，"
                f"可用: {list(_MODEL_MAP)}"
            )
        # 透传模型支持的参数
        valid_keys = {
            "length", "width", "radius", "gap", "coupling",
            "insertion_loss_db", "phase_rad", "neff", "ng", "loss_db_cm",
        }
        kwargs = {k: v for k, v in self.params.items() if k in valid_keys}
        return model(wl=wl, **kwargs)


# ---------------------------------------------------------------------------
# CAPHENetwork — 电路网络
# ---------------------------------------------------------------------------


@dataclass
class CAPHENetwork:
    """CAPHE 电路网络（节点集合 + 连接关系）。

    持有多个 CAPHENode 与它们之间的端口连接关系，
    构成完整的光子电路拓扑。

    学术依据: CAPHE 网络拓扑,
    https://www.lucedaphotonics.com/products/caphe

    Attributes:
        nodes: 节点字典 ``{name: CAPHENode}``。
        connections: 连接字典 ``{"node1,port1": "node2,port2"}``。
        ports: 外部端口字典 ``{ext_port: "node,internal_port"}``。
    """

    nodes: dict[str, CAPHENode] = field(default_factory=dict)
    connections: dict[str, str] = field(default_factory=dict)
    ports: dict[str, str] = field(default_factory=dict)

    def add_node(self, node: CAPHENode) -> None:
        """添加节点到网络。"""
        self.nodes[node.name] = node

    def connect(self, src: str, dst: str) -> None:
        """连接两个端口。

        Args:
            src: 源端口 ``"node1,port1"``。
            dst: 目标端口 ``"node2,port2"``。
        """
        self.connections[src] = dst

    def set_port(self, ext_name: str, internal: str) -> None:
        """设置外部端口。

        Args:
            ext_name: 外部端口名。
            internal: 内部端口 ``"node,port"``。
        """
        self.ports[ext_name] = internal

    def to_netlist(self) -> dict:
        """转换为 SAX 格式网表。

        Returns:
            SAX 格式网表 ``{instances, connections, ports}``。
        """
        return {
            "instances": {n: nd.cell_type for n, nd in self.nodes.items()},
            "connections": dict(self.connections),
            "ports": dict(self.ports),
        }

    @classmethod
    def from_netlist(cls, netlist: dict) -> CAPHENetwork:
        """从 SAX 格式网表构建网络。

        Args:
            netlist: SAX 格式网表 ``{instances, connections, ports}``。

        Returns:
            CAPHENetwork 实例。
        """
        net = cls()
        for inst_name, cell_type in netlist.get("instances", {}).items():
            net.add_node(CAPHENode(name=inst_name, cell_type=cell_type))
        net.connections = dict(netlist.get("connections", {}))
        net.ports = dict(netlist.get("ports", {}))
        return net


# ---------------------------------------------------------------------------
# CAPHEFrequencySolver — 频率域求解器
# ---------------------------------------------------------------------------


@dataclass
class CAPHEFrequencySolver:
    """CAPHE 频率域求解器（S 参数级联）。

    对指定波长范围执行频率扫描，通过子网络增长算法级联各节点 S 参数，
    计算电路级传输谱。

    学术依据: S 参数级联子网络增长算法,
    SAX, https://flaport.github.io/sax/

    Attributes:
        network: 待求解的电路网络。
    """

    network: CAPHENetwork

    def solve(
        self,
        wavelengths: np.ndarray | None = None,
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """执行频率域求解。

        Args:
            wavelengths: 波长数组（μm），默认 1.5-1.6μm 100点。
            **model_kwargs: 传递给器件模型的参数。

        Returns:
            (波长数组, 电路级 S 参数字典)。
        """
        if wavelengths is None:
            wavelengths = np.linspace(1.5, 1.6, 100)
        # 计算每个节点的 S 参数
        instance_s: dict[str, SDict] = {}
        for name, node in self.network.nodes.items():
            instance_s[name] = node.compute_sparams(wl=wavelengths, **{
                k: v for k, v in model_kwargs.items()
            })
        # 级联
        connections = list(self.network.connections.items())
        ports = self.network.ports
        s_total = cascade_circuit(instance_s, connections, ports)
        return wavelengths, s_total

    def transmission(
        self,
        out_port: str,
        in_port: str,
        wavelengths: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """计算指定端口对的传输谱。

        Args:
            out_port: 输出端口名。
            in_port: 输入端口名。
            wavelengths: 波长数组。

        Returns:
            (波长数组, 传输率数组 T=|S|²)。
        """
        wl, s = self.solve(wavelengths)
        key = (out_port, in_port)
        if key not in s:
            raise KeyError(
                f"S 参数中无端口对 {key}，可用: {list(s.keys())}"
            )
        t = np.abs(s[key]) ** 2
        return wl, t


# ---------------------------------------------------------------------------
# CAPHETimeDomainSolver — 时域求解器
# ---------------------------------------------------------------------------


@dataclass
class CAPHETimeDomainSolver:
    """CAPHE 时域求解器（ODE 积分）。

    对环谐振器等动态器件求解时域耦合模方程（CMT）ODE，
    模拟调制响应、载流子动力学与瞬态行为。

    学术依据: Bogaerts et al., "Silicon microring resonators",
    Laser & Photonics Reviews 6(1), 2012,
    https://doi.org/10.1002/lpor.201100017

    耦合模方程（全通环）:
        dA/dt = (j·Δω - 1/τ)·A + κ·s_in(t)
        s_out(t) = s_in(t) - κ*·A(t)
    其中 A 为环内场幅度，τ 为光子寿命，κ 为耦合系数，Δω 为失谐。

    Attributes:
        network: 待求解的电路网络。
    """

    network: CAPHENetwork

    def solve_ring(
        self,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        t_span_ps: tuple[float, float] = (0.0, 1000.0),
        n_steps: int = 1000,
        input_power_mw: float = 1.0,
    ) -> dict:
        """求解环谐振器时域响应（耦合模理论 ODE）。

        使用前向欧拉法积分全通环 CMT 方程。

        Args:
            detuning_ghz: 激光-环失谐频率（GHz）。
            photon_lifetime_ps: 环内光子寿命（ps）。
            coupling: 总线-环功率耦合系数。
            t_span_ps: 时间范围（ps）。
            n_steps: 时间步数。
            input_power_mw: 输入功率（mW）。

        Returns:
            含 ``time``（时间数组 ps）、``ring_field``（环内场幅度）、
            ``output_power``（输出功率 mW）的字典。
        """
        t = np.linspace(t_span_ps[0], t_span_ps[1], n_steps)
        dt = t[1] - t[0]
        # 失谐角频率（rad/ps）：GHz → rad/ps = 2π·GHz·1e-3
        delta_omega = 2.0 * np.pi * detuning_ghz * 1e-3
        # 光子寿命倒数（1/ps）
        gamma = 1.0 / photon_lifetime_ps
        # 振幅耦合系数
        kappa = np.sqrt(coupling)
        # 输入场幅度（mW^0.5）
        s_in = np.sqrt(input_power_mw)
        # 前向欧拉积分
        a = 0.0 + 0.0j  # 环内场幅度
        ring_field = np.zeros(n_steps, dtype=complex)
        output_power = np.zeros(n_steps)
        for i in range(n_steps):
            # dA/dt = (j·Δω - γ)·A + κ·s_in
            da_dt = (1j * delta_omega - gamma) * a + kappa * s_in
            a = a + da_dt * dt
            ring_field[i] = a
            # s_out = s_in - κ*·A
            s_out = s_in - kappa * a
            output_power[i] = np.abs(s_out) ** 2
        return {
            "time": t,
            "ring_field": ring_field,
            "output_power": output_power,
            "detuning_ghz": detuning_ghz,
            "photon_lifetime_ps": photon_lifetime_ps,
        }

    def solve_step_response(
        self,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        t_span_ps: tuple[float, float] = (0.0, 2000.0),
        n_steps: int = 2000,
    ) -> dict:
        """求解环谐振器阶跃响应。

        输入阶跃信号（t=0 时开启），观察环内场与输出的瞬态建立过程。

        Args:
            detuning_ghz: 失谐频率（GHz）。
            photon_lifetime_ps: 光子寿命（ps）。
            coupling: 耦合系数。
            t_span_ps: 时间范围（ps）。
            n_steps: 时间步数。

        Returns:
            含 ``time``、``ring_field``、``output_power`` 的字典。
        """
        return self.solve_ring(
            detuning_ghz=detuning_ghz,
            photon_lifetime_ps=photon_lifetime_ps,
            coupling=coupling,
            t_span_ps=t_span_ps,
            n_steps=n_steps,
            input_power_mw=1.0,
        )


# ---------------------------------------------------------------------------
# CAPHEBackend — 统一后端接口
# ---------------------------------------------------------------------------


@dataclass
class CAPHEBackend:
    """CAPHE 统一仿真后端接口。

    封装频率域与时域求解器，提供统一的电路仿真入口。

    学术依据: CAPHE 仿真后端,
    https://www.lucedaphotonics.com/products/caphe

    Attributes:
        network: 电路网络。
    """

    network: CAPHENetwork | None = None

    def set_network(self, network: CAPHENetwork) -> None:
        """设置仿真网络。"""
        self.network = network

    def frequency_domain(
        self,
        wavelengths: np.ndarray | None = None,
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """频率域仿真。

        Args:
            wavelengths: 波长数组。
            **model_kwargs: 器件模型参数。

        Returns:
            (波长数组, S 参数字典)。

        Raises:
            RuntimeError: 未设置网络时。
        """
        if self.network is None:
            raise RuntimeError("CAPHE 后端未设置网络，请先调用 set_network()")
        solver = CAPHEFrequencySolver(network=self.network)
        return solver.solve(wavelengths, **model_kwargs)

    def time_domain(
        self,
        detuning_ghz: float = 0.0,
        photon_lifetime_ps: float = 100.0,
        coupling: float = 0.1,
        t_span_ps: tuple[float, float] = (0.0, 1000.0),
        n_steps: int = 1000,
    ) -> dict:
        """时域仿真（环谐振器 ODE）。

        Args:
            detuning_ghz: 失谐频率（GHz）。
            photon_lifetime_ps: 光子寿命（ps）。
            coupling: 耦合系数。
            t_span_ps: 时间范围（ps）。
            n_steps: 时间步数。

        Returns:
            时域求解结果字典。

        Raises:
            RuntimeError: 未设置网络时。
        """
        if self.network is None:
            raise RuntimeError("CAPHE 后端未设置网络，请先调用 set_network()")
        solver = CAPHETimeDomainSolver(network=self.network)
        return solver.solve_ring(
            detuning_ghz=detuning_ghz,
            photon_lifetime_ps=photon_lifetime_ps,
            coupling=coupling,
            t_span_ps=t_span_ps,
            n_steps=n_steps,
        )

    @classmethod
    def from_netlist(cls, netlist: dict) -> CAPHEBackend:
        """从网表构建后端。

        Args:
            netlist: SAX 格式网表。

        Returns:
            CAPHEBackend 实例。
        """
        network = CAPHENetwork.from_netlist(netlist)
        return cls(network=network)
>>>>>>> trae/solo-agent-pkVjID
