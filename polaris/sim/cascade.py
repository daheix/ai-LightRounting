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

import numpy as np

from polaris.sim.types import SDict

# 尝试导入 SAX（规则 2 直接集成）
try:
    import sax as _sax

    _HAS_SAX = True
except ImportError:
    _sax = None
    _HAS_SAX = False


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
    all_ports_1 = set()
    for p_out, p_in in s1:
        all_ports_1.add(p_out)
        all_ports_1.add(p_in)
    all_ports_2 = set()
    for p_out, p_in in s2:
        all_ports_2.add(p_out)
        all_ports_2.add(p_in)

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

    # 构建 S 参数查找函数
    def get_s(sdict: SDict, p_out: str, p_in: str) -> np.ndarray:
        """获取 S 参数，不存在则返回 0。"""
        if (p_out, p_in) in sdict:
            return np.asarray(sdict[(p_out, p_in)], dtype=complex)
        return np.zeros(n_freq, dtype=complex)

    # 子网络增长公式
    result: SDict = {}
    for p_i in remaining:
        for p_j in remaining:
            # S_ij = S_ij_direct + sum over connected pairs
            if p_i in remaining_1 and p_j in remaining_1:
                s_direct = get_s(s1, p_i, p_j)
            elif p_i in remaining_2 and p_j in remaining_2:
                s_direct = get_s(s2, p_i, p_j)
            else:
                s_direct = np.zeros(n_freq, dtype=complex)
            # 交叉项：通过连接端口的间接传输
            s_cross = np.zeros(n_freq, dtype=complex)
            for c1, c2 in connected:
                # S_iA (从 i 到连接端口 c1)
                if p_i in remaining_1:
                    s_iA = get_s(s1, p_i, c1)
                else:
                    s_iA = get_s(s2, p_i, c2)
                # S_Bj (从连接端口到 j)
                if p_j in remaining_1:
                    s_Bj = get_s(s1, c1, p_j)
                else:
                    s_Bj = get_s(s2, c2, p_j)
                # S_AB 和 S_BA（连接端口间的反射）
                s_AB = get_s(s1, c1, c1)  # 简化：假设连接端口反射
                s_BA = get_s(s2, c2, c2)
                # 分母 1 - S_AB * S_BA
                denom = 1.0 - s_AB * s_BA
                denom = np.where(np.abs(denom) < 1e-15, 1e-15, denom)
                s_cross += s_iA * s_Bj / denom
            result[(p_i, p_j)] = s_direct + s_cross

    return result


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
        inst1_name, port1 = conn[0].split(".")
        inst2_name, port2 = conn[1].split(".")

        if inst1_name not in subnetworks or inst2_name not in subnetworks:
            continue

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
        connections = new_connections

    # 提取外部端口
    if not subnetworks:
        return {}
    final_s = next(iter(subnetworks.values()))

    if ports:
        # 重命名端口
        renamed: SDict = {}
        for ext_name, int_ref in ports.items():
            inst, port = int_ref.split(".")
            # 在最终子网络中查找该端口
            for (p_out, p_in), val in final_s.items():
                if p_out == port:
                    for ext_in, int_in in ports.items():
                        _, port_in = int_in.split(".")
                        if p_in == port_in:
                            renamed[(ext_name, ext_in)] = val
        return renamed if renamed else final_s

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
