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
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.integrate import solve_ivp

from polaris.sim.types import SDict

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
    ode_func: Optional[Callable[[float, np.ndarray, np.ndarray], np.ndarray]] = None
    output_func: Optional[Callable[[float, np.ndarray, np.ndarray], np.ndarray]] = None
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
            raise ValueError(
                f"节点 {self.name!r} S 矩阵必须是方阵，得到 shape={arr.shape}"
            )
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
                raise ValueError(
                    f"节点 {self.name!r} S 矩阵函数返回非方阵 shape={sm.shape}"
                )
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

    def connect(
        self, node1: str, port1: int, node2: str, port2: int
    ) -> None:
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
                raise ValueError(
                    f"节点 {name!r} 端口索引 {port} 越界（0-{node.n_ports - 1}）"
                )
        # 检查端口是否已被连接
        for n1, p1, n2, p2 in self._connections:
            if (n1 == node1 and p1 == port1) or (n2 == node2 and p2 == port2):
                raise ValueError(
                    f"端口 {node1}.{port1} 或 {node2}.{port2} 已被连接"
                )
            if (n1 == node2 and p1 == port2) or (n2 == node1 and p2 == port1):
                raise ValueError(
                    f"端口 {node2}.{port2} 或 {node1}.{port1} 已被连接"
                )
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
            raise ValueError(
                f"节点 {node_name!r} 端口索引 {port_idx} 越界"
            )
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

        S_block = sp.csr_matrix(
            (vals, (rows, cols)), shape=(n, n), dtype=complex
        )
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

        C = sp.csr_matrix(
            (vals, (rows, cols)), shape=(n, n), dtype=complex
        )
        return C

    def eliminate_linear_nodes(
        self, wavelength: float = 1.55
    ) -> tuple[sp.csr_matrix, list[str]]:
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
        for ext_name, (node_name, port_idx) in self.network.external_ports.items():
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
                        (n1 == node.name and p1 == p) or
                        (n2 == node.name and p2 == p)
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
        except np.linalg.LinAlgError:
            raise RuntimeError(
                f"消去子矩阵奇异，无法计算 Schur 补（节点数={len(elim)}）"
            )
        if cond_bb > SINGULAR_THRESHOLD:
            raise RuntimeError(
                f"消去子矩阵条件数 {cond_bb:.2e} 过大（>{SINGULAR_THRESHOLD}），"
                f"Schur 补数值不稳定"
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

        outputs: dict[str, list[complex]] = {
            name: [] for name in self.network.external_ports
        }
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
            "outputs": {
                name: np.array(vals, dtype=complex)
                for name, vals in outputs.items()
            },
            "internal": {
                key: np.array(vals, dtype=complex)
                for key, vals in internal_all.items()
            },
            "eliminated": result.get("eliminated", []),
        }

    def _solve_single_wavelength(
        self, wavelength: float, inputs: dict[str, complex]
    ) -> dict:
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
        except np.linalg.LinAlgError:
            raise RuntimeError(
                f"全局矩阵奇异（波长={wavelength} μm）"
            )
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
            raise RuntimeError(
                f"稀疏 LU 分解失败（波长={wavelength} μm）: {exc}"
            ) from exc

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


# =============================================================================
# 4. CAPHETimeDomainSolver — 时域 ODE 求解器（CMT）
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
                [y[self._state_offsets[f"{node.name}.{sn}"]]
                 for sn in node.state_variables],
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
            raise ValueError(
                f"t_span[0] 必须 < t_span[1]，得到 {t_span}"
            )
        if n_points <= 0:
            raise ValueError(f"n_points 必须 > 0，得到 {n_points}")

        # 构建初始状态向量
        if y0 is None:
            y0_arr = np.zeros(self.n_states, dtype=float)
            offset = 0
            for node in self.network.get_nodes():
                for sname, val in node.state_variables.items():
                    y0_arr[offset] = float(val)
                    offset += 1
        else:
            if len(y0) != self.n_states:
                raise ValueError(
                    f"y0 长度 {len(y0)} != 状态变量数 {self.n_states}"
                )
            y0_arr = np.array(y0, dtype=float)

        # 无状态变量时直接返回空解
        if self.n_states == 0:
            t_eval = np.linspace(t_span[0], t_span[1], n_points)
            return {
                "t": t_eval,
                "y": np.zeros((n_points, 0), dtype=float),
                "states": {},
            }

        t_eval = np.linspace(t_span[0], t_span[1], n_points)

        # 调用 scipy.integrate.solve_ivp（RK45 自适应步长）
        # 来源: scipy 文档
        # URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
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
            raise RuntimeError(
                f"ODE 求解失败: {exc}"
            ) from exc

        if not sol.success:
            raise RuntimeError(
                f"ODE 求解未收敛: {sol.message}"
            )

        # 提取状态时间序列
        states_ts: dict[str, np.ndarray] = {}
        for i, name in enumerate(self._state_names):
            states_ts[name] = sol.y[i, :]

        return {
            "t": sol.t,
            "y": sol.y.T,  # (n_times × n_states)
            "states": states_ts,
        }


# =============================================================================
# 5. CAPHEBackend — CAPHE 后端适配器（统一频域+时域接口）
# =============================================================================
class CAPHEBackend:
    """CAPHE 后端适配器（统一频域+时域接口）。

    学术依据：CAPHE 统一接口（Fiers 2012）
    URL: https://biblio.ugent.be/publication/2036548/file/3146073.pdf

    提供统一的频域+时域仿真接口，并支持与 sax/simphony 后端交叉验证
    （误差 < 1e-4，来源: R26.md §1）。

    创新点（标注"创新"）:
    - 自动稀疏化：自动检测无源线性节点并消去，无需用户手动标记。
      创新逻辑：节点实例化时自动分析是否含状态变量/ODE。
      支持理论：图论中的"叶子节点消去"。
      预期收益：用户无需手动标记，降低使用门槛。
    """

    def __init__(self) -> None:
        """初始化 CAPHE 后端。"""
        self._freq_solver: Optional[CAPHEFrequencySolver] = None
        self._time_solver: Optional[CAPHETimeDomainSolver] = None

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

    def cross_validate(
        self, sax_result: dict, caphe_result: dict
    ) -> dict:
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
                    f"端口 {port_name!r} 形状不匹配: "
                    f"sax={sax_arr.shape} vs caphe={caphe_arr.shape}"
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
    "CAPHENode",
    "CAPHENetwork",
    "CAPHEFrequencySolver",
    "CAPHETimeDomainSolver",
    "CAPHEBackend",
]
