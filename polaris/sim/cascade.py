"""S 参数级联器（纯 Python 复刻 SAX 子网络增长算法，规则 3）。

子网络增长算法核心：当端口 A（子网络1）与端口 B（子网络2）连接时，
消去 A 和 B，剩余端口的 S 参数更新为：
    S'_ij = S_ij + S_iA * S_Bj / (1 - S_AB * S_BA)
其中 S_iA 是从端口 i 到 A 的传输，S_Bj 是从 B 到 j 的传输。

来源:
- SAX 子网络增长: https://flaport.github.io/sax/
- 光子电路 S 参数级联理论: 标准微波网络理论

集成方式（遵守 project_rules.md 规则 2/3）：
- 优先使用 SAX（规则 2 直接集成）
- 回退到纯 numpy 子网络增长（规则 3 复刻）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.types import SDict

# 尝试导入 SAX（规则 2 直接集成）
try:
    import sax as _sax

    _HAS_SAX = True
except ImportError:
    _sax = None
    _HAS_SAX = False


@dataclass
class CascadeContext:
    """级联计算上下文（将 _compute_cross_term 的参数打包，降低函数参数个数）。

    Attributes:
        remaining_1: 子网络1的剩余端口集合。
        connected: 连接端口对列表 [(c1, c2), ...]。
        n_freq: 频率维度长度。
    """

    remaining_1: set[str]
    connected: list[tuple[str, str]]
    n_freq: int


def _collect_ports(sdict: SDict) -> set[str]:
    """从 S 参数字典收集所有端口名。

    Args:
        sdict: S 参数字典，键为 (port_out, port_in) 元组。

    Returns:
        该字典中出现的所有端口名集合。
    """
    ports: set[str] = set()
    for p_out, p_in in sdict:
        ports.add(p_out)
        ports.add(p_in)
    return ports


def _get_s_value(sdict: SDict, p_out: str, p_in: str, n_freq: int) -> np.ndarray:
    """获取 S 参数，不存在则返回零数组。

    Args:
        sdict: S 参数字典。
        p_out: 输出端口名。
        p_in: 输入端口名。
        n_freq: 频率维度长度（用于构造零数组）。

    Returns:
        对应端口的复数 S 参数数组，不存在时返回零数组。
    """
    if (p_out, p_in) in sdict:
        return np.asarray(sdict[(p_out, p_in)], dtype=complex)
    return np.zeros(n_freq, dtype=complex)


def _compute_single_cross_term(
    s1: SDict,
    s2: SDict,
    p_i: str,
    p_j: str,
    c1: str,
    c2: str,
    i_in_1: bool,
    j_in_1: bool,
    n_freq: int,
) -> np.ndarray:
    """计算单个连接对的交叉项 S_iA * S_Bj / (1 - S_AB * S_BA)。

    来源:
    - SAX 子网络增长: https://flaport.github.io/sax/
    """
    s_iA = _get_s_value(s1, p_i, c1, n_freq) if i_in_1 else _get_s_value(s2, p_i, c2, n_freq)
    s_Bj = _get_s_value(s1, c1, p_j, n_freq) if j_in_1 else _get_s_value(s2, c2, p_j, n_freq)
    s_AB = _get_s_value(s1, c1, c1, n_freq)
    s_BA = _get_s_value(s2, c2, c2, n_freq)
    denom = 1.0 - s_AB * s_BA
    denom = np.where(np.abs(denom) < 1e-15, 1e-15, denom)
    return s_iA * s_Bj / denom


def _compute_cross_term(
    s1: SDict,
    s2: SDict,
    p_i: str,
    p_j: str,
    ctx: CascadeContext,
) -> np.ndarray:
    """计算通过连接端口的间接传输交叉项。

    来源:
    - SAX 子网络增长: https://flaport.github.io/sax/
    - 光子电路 S 参数级联理论: 标准微波网络理论

    Args:
        s1: 子网络1的 S 参数。
        s2: 子网络2的 S 参数。
        p_i: 当前剩余端口 i。
        p_j: 当前剩余端口 j。
        ctx: 级联上下文（剩余端口/连接对/频率维度）。

    Returns:
        交叉项 S_iA * S_Bj / (1 - S_AB * S_BA) 的累加结果。
    """
    i_in_1 = p_i in ctx.remaining_1
    j_in_1 = p_j in ctx.remaining_1
    s_cross = np.zeros(ctx.n_freq, dtype=complex)
    for c1, c2 in ctx.connected:
        s_cross += _compute_single_cross_term(
            s1, s2, p_i, p_j, c1, c2, i_in_1, j_in_1, ctx.n_freq
        )
    return s_cross


def _get_direct_s(
    s1: SDict,
    s2: SDict,
    p_i: str,
    p_j: str,
    remaining_1: set[str],
    remaining_2: set[str],
    n_freq: int,
) -> np.ndarray:
    """获取直接传输 S 参数（用卫语句降低圈复杂度）。"""
    if p_i in remaining_1 and p_j in remaining_1:
        return _get_s_value(s1, p_i, p_j, n_freq)
    if p_i in remaining_2 and p_j in remaining_2:
        return _get_s_value(s2, p_i, p_j, n_freq)
    return np.zeros(n_freq, dtype=complex)


def _connect_ports(s1: SDict, s2: SDict, connections: list[tuple[str, str]]) -> SDict:
    """连接两个 S 参数子网络的指定端口对（纯 numpy 实现）。

    来源:
    - SAX 子网络增长: https://flaport.github.io/sax/
    - 光子电路 S 参数级联理论: 标准微波网络理论

    Args:
        s1: 子网络1的 S 参数。
        s2: 子网络2的 S 参数。
        connections: 要连接的端口对列表 [(port_in_s1, port_in_s2), ...]。

    Returns:
        连接后剩余端口的 S 参数字典。
    """
    # 合并两个子网络的所有端口
    all_ports_1 = _collect_ports(s1)
    all_ports_2 = _collect_ports(s2)

    # 连接的端口
    connected_1 = {c[0] for c in connections}
    connected_2 = {c[1] for c in connections}

    # 剩余端口
    remaining_1 = all_ports_1 - connected_1
    remaining_2 = all_ports_2 - connected_2

    # 构建合并后的 S 参数字典
    remaining = list(remaining_1) + list(remaining_2)
    connected = [(c[0], c[1]) for c in connections]

    if not remaining:
        return {}

    # 获取频率维度
    first_val = next(iter(s1.values()))
    n_freq = len(first_val) if hasattr(first_val, "__len__") else 1

    ctx = CascadeContext(remaining_1=remaining_1, connected=connected, n_freq=n_freq)
    result: SDict = {}
    for p_i in remaining:
        for p_j in remaining:
            s_direct = _get_direct_s(s1, s2, p_i, p_j, remaining_1, remaining_2, n_freq)
            s_cross = _compute_cross_term(s1, s2, p_i, p_j, ctx)
            result[(p_i, p_j)] = s_direct + s_cross

    return result


def _merge_subnetworks(
    subnetworks: dict[str, SDict],
    connections: list[tuple[str, str]],
    conn: tuple[str, str],
) -> list[tuple[str, str]]:
    """合并连接 conn 涉及的两个子网络，返回更新后的连接列表。

    在 subnetworks 字典上原地修改（删除旧子网络、添加合并后的子网络）。

    来源:
    - SAX 子网络增长: https://flaport.github.io/sax/

    Args:
        subnetworks: 子网络字典（原地修改）。
        connections: 当前连接列表。
        conn: 当前要处理的连接 (inst1.port, inst2.port)。

    Returns:
        更新后的连接列表（实例名已替换为合并后的新名）。
    """
    inst1_name, port1 = conn[0].split(".")
    inst2_name, port2 = conn[1].split(".")

    if inst1_name not in subnetworks or inst2_name not in subnetworks:
        return connections

    s1 = subnetworks[inst1_name]
    s2 = subnetworks[inst2_name]

    # 连接 port1 和 port2
    merged = _connect_ports(s1, s2, [(port1, port2)])

    # 合并后的子网络
    new_name = f"{inst1_name}+{inst2_name}"
    subnetworks[new_name] = merged
    del subnetworks[inst1_name]
    del subnetworks[inst2_name]

    # 更新剩余连接中的实例名
    new_connections = []
    for c in connections:
        c0 = c[0].replace(inst1_name, new_name).replace(inst2_name, new_name)
        c1 = c[1].replace(inst1_name, new_name).replace(inst2_name, new_name)
        if c0.split(".")[0] != c1.split(".")[0]:  # 跳过已合并的
            new_connections.append((c0, c1))
    return new_connections


def _rename_ports(final_s: SDict, ports: dict[str, str]) -> SDict:
    """将最终子网络的端口重命名为外部端口名。

    来源:
    - SAX circuit 端口映射: https://flaport.github.io/sax/

    Args:
        final_s: 最终子网络的 S 参数字典。
        ports: 外部端口映射 {external_name: instance.port}。

    Returns:
        重命名后的 S 参数字典；若无法重命名则返回原字典。
    """
    # 构建 内部端口 → 外部端口名列表 的映射
    int_to_exts: dict[str, list[str]] = {}
    for ext_name, int_ref in ports.items():
        _, port = int_ref.split(".")
        int_to_exts.setdefault(port, []).append(ext_name)

    renamed: SDict = {}
    for (p_out, p_in), val in final_s.items():
        if p_out in int_to_exts and p_in in int_to_exts:
            for ext_out in int_to_exts[p_out]:
                for ext_in in int_to_exts[p_in]:
                    renamed[(ext_out, ext_in)] = val
    return renamed if renamed else final_s


def cascade_circuit(
    instances: dict[str, SDict],
    connections: list[tuple[str, str]],
    ports: dict[str, str] | None = None,
) -> SDict:
    """级联多个器件 S 参数组成电路（纯 numpy 子网络增长）。

    逐步将器件两两连接，消去内部端口，保留外部端口。

    来源:
    - SAX circuit 级联: https://flaport.github.io/sax/
    - 子网络增长算法: 标准微波网络理论

    Args:
        instances: 器件实例字典 {instance_name: SDict}。
        connections: 连接列表 [(instance1.port, instance2.port), ...]。
        ports: 外部端口映射 {external_name: instance.port}。

    Returns:
        电路级 S 参数字典。
    """
    # 如果有 SAX，优先使用（规则 2 直接集成）
    if _HAS_SAX and ports is not None:
        try:
            return _cascade_with_sax(instances, connections, ports)
        except Exception:
            pass  # 回退到纯 numpy 实现

    # 纯 numpy 子网络增长（规则 3 复刻）
    # 初始化：每个实例是一个独立子网络
    subnetworks = dict(instances)

    # 逐步合并连接的子网络
    for conn in connections:
        connections = _merge_subnetworks(subnetworks, connections, conn)

    # 提取外部端口
    if not subnetworks:
        return {}
    final_s = next(iter(subnetworks.values()))

    if ports:
        return _rename_ports(final_s, ports)

    return final_s


def _cascade_with_sax(
    instances: dict[str, SDict],
    connections: list[tuple[str, str]],
    ports: dict[str, str],
) -> SDict:
    """使用 SAX 的电路级联器（规则 2 直接集成）。

    来源: https://flaport.github.io/sax/
    """
    # 构建 SAX 网表
    netlist_instances: dict[str, str] = {}
    models: dict = {}

    for name, sdict in instances.items():
        model_name = f"model_{name}"
        netlist_instances[name] = model_name

        # 创建 SAX 模型函数
        def make_model(sd):
            def model(**kwargs):
                return sd

            return model

        models[model_name] = make_model(sdict)

    netlist = {
        "instances": netlist_instances,
        "connections": {c[0]: c[1] for c in connections},
        "ports": ports,
    }

    circuit, _ = _sax.circuit(netlist=netlist, models=models)
    return circuit()
