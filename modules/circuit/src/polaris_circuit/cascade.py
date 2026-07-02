"""S 参数级联器（纯 numpy 子网络增长算法）。

子网络增长算法核心：当端口 A（子网络1）与端口 B（子网络2）连接时，
消去 A 和 B，剩余端口的 S 参数更新为：
    S'_ij = S_ij + S_iA * S_Bj / (1 - S_AB * S_BA)

来源:
- SAX 子网络增长: https://flaport.github.io/sax/
- Filipsson 1978, "A new general computer algorithm for S-matrix calculation
  of interconnected multiports", Proc. Eur. Microw. Conf.,
  https://doi.org/10.1109/EUMA.1978.332681
- Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85,
  https://arxiv.org/abs/2009.05146

合规: R02 学术诚信 / R03 禁止 fall-back（分母趋零 raise，不兜底）/
R04 纯 NumPy / R05 无 TODO / R13 不保留 v4 兼容（去掉 sax 必装依赖）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from polaris_circuit.types import SDict

logger = logging.getLogger(__name__)

# 子网络增长算法分母接近零的阈值（来源: Simphony 论文 §3.3）
# 当 |1 - S_AB·S_BA| < DENOM_MIN 时，谐振陷波分母趋零，告警退出
DENOM_MIN = 1e-15


@dataclass
class _CascadeContext:
    """级联计算上下文（降低函数参数个数）。"""

    remaining_1: set[str]
    remaining_2: set[str]
    connected: list[tuple[str, str]]
    n_freq: int


def _collect_ports(sdict: SDict) -> set[str]:
    """从 S 参数字典收集所有端口名。"""
    ports: set[str] = set()
    for p_out, p_in in sdict:
        ports.add(p_out)
        ports.add(p_in)
    return ports


def _get_s_value(sdict: SDict, p_out: str, p_in: str, n_freq: int) -> np.ndarray:
    """获取 S 参数，不存在则返回零数组。"""
    if (p_out, p_in) in sdict:
        return np.asarray(sdict[(p_out, p_in)], dtype=complex)
    return np.zeros(n_freq, dtype=complex)


def _compute_cross_term(
    s1: SDict, s2: SDict, p_i: str, p_j: str, ctx: _CascadeContext
) -> np.ndarray:
    """计算通过连接端口的间接传输交叉项（子网络增长算法）。

    来源: SAX 子网络增长 https://flaport.github.io/sax/

    i、j 同子网络时需经对侧端口反射折返（乘 reflect），不同子网络时直接交叉。
    """
    i_in_1 = p_i in ctx.remaining_1
    j_in_1 = p_j in ctx.remaining_1
    same_subnet = i_in_1 == j_in_1
    s_cross = np.zeros(ctx.n_freq, dtype=complex)
    for c1, c2 in ctx.connected:
        s_iA = _get_s_value(s1, p_i, c1, ctx.n_freq) if i_in_1 else _get_s_value(s2, p_i, c2, ctx.n_freq)
        s_Bj = _get_s_value(s1, c1, p_j, ctx.n_freq) if j_in_1 else _get_s_value(s2, c2, p_j, ctx.n_freq)
        s_AA = _get_s_value(s1, c1, c1, ctx.n_freq)
        s_BB = _get_s_value(s2, c2, c2, ctx.n_freq)
        denom = 1.0 - s_AA * s_BB
        denom_abs = np.abs(denom)
        if np.any(denom_abs < DENOM_MIN):
            min_denom = float(np.min(denom_abs))
            msg = (
                f"子网络增长算法分母趋零（|1-S_AB·S_BA|={min_denom:.3e} < {DENOM_MIN:.0e}），"
                "电路存在强谐振或反馈环路，数值不稳定。"
                "请检查电路设计或使用更精细的频率采样。"
            )
            logger.error(msg)
            raise RuntimeError(msg)
        if same_subnet:
            reflect = s_BB if i_in_1 else s_AA
            s_cross += s_iA * reflect * s_Bj / denom
        else:
            s_cross += s_iA * s_Bj / denom
    return s_cross


def _get_direct_s(
    s1: SDict, s2: SDict, p_i: str, p_j: str, ctx: _CascadeContext
) -> np.ndarray:
    """获取直接传输 S 参数（用卫语句降低圈复杂度）。"""
    if p_i in ctx.remaining_1 and p_j in ctx.remaining_1:
        return _get_s_value(s1, p_i, p_j, ctx.n_freq)
    if p_i in ctx.remaining_2 and p_j in ctx.remaining_2:
        return _get_s_value(s2, p_i, p_j, ctx.n_freq)
    return np.zeros(ctx.n_freq, dtype=complex)


def _connect_ports(s1: SDict, s2: SDict, connections: list[tuple[str, str]]) -> SDict:
    """连接两个 S 参数子网络的指定端口对（纯 numpy 实现）。

    来源: SAX 子网络增长 https://flaport.github.io/sax/
    """
    all_ports_1 = _collect_ports(s1)
    all_ports_2 = _collect_ports(s2)
    connected_1 = {c[0] for c in connections}
    connected_2 = {c[1] for c in connections}
    remaining_1 = all_ports_1 - connected_1
    remaining_2 = all_ports_2 - connected_2
    remaining = list(remaining_1) + list(remaining_2)
    connected = [(c[0], c[1]) for c in connections]
    if not remaining:
        return {}
    first_val = next(iter(s1.values()))
    n_freq = len(first_val) if hasattr(first_val, "__len__") else 1
    ctx = _CascadeContext(remaining_1, remaining_2, connected, n_freq)
    result: SDict = {}
    for p_i in remaining:
        for p_j in remaining:
            s_direct = _get_direct_s(s1, s2, p_i, p_j, ctx)
            s_cross = _compute_cross_term(s1, s2, p_i, p_j, ctx)
            result[(p_i, p_j)] = s_direct + s_cross
    return result


def _replace_instance_name(ref: str, old1: str, old2: str, new: str) -> str:
    """精确替换端口引用中的实例名（避免子串误替换）。"""
    parts = ref.split(".", 1)
    if len(parts) == 2:
        inst, port = parts
        if inst == old1 or inst == old2:
            return f"{new}.{port}"
        return ref
    return ref


def _merge_subnetworks(
    subnetworks: dict[str, SDict],
    connections: list[tuple[str, str]],
    conn: tuple[str, str],
) -> list[tuple[str, str]]:
    """合并连接 conn 涉及的两个子网络，返回更新后的连接列表。"""
    inst1_name, port1 = conn[0].split(".")
    inst2_name, port2 = conn[1].split(".")
    if inst1_name not in subnetworks or inst2_name not in subnetworks:
        return connections
    s1 = subnetworks[inst1_name]
    s2 = subnetworks[inst2_name]
    merged = _connect_ports(s1, s2, [(port1, port2)])
    new_name = f"{inst1_name}+{inst2_name}"
    subnetworks[new_name] = merged
    del subnetworks[inst1_name]
    del subnetworks[inst2_name]
    new_connections = []
    for c in connections:
        c0 = _replace_instance_name(c[0], inst1_name, inst2_name, new_name)
        c1 = _replace_instance_name(c[1], inst1_name, inst2_name, new_name)
        if c0.split(".")[0] != c1.split(".")[0]:
            new_connections.append((c0, c1))
    return new_connections


def _rename_ports(final_s: SDict, ports: dict[str, str]) -> SDict:
    """将最终子网络的端口重命名为外部端口名。

    来源: SAX circuit 端口映射 https://flaport.github.io/sax/
    """
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
    - Filipsson 1978 Eur. Microw. Conf.

    Args:
        instances: 器件实例字典 {instance_name: SDict}。
        connections: 连接列表 [(instance1.port, instance2.port), ...]。
        ports: 外部端口映射 {external_name: instance.port}。

    Returns:
        电路级 S 参数字典。

    Raises:
        RuntimeError: 数值不稳定（分母趋零）时告警退出（禁止 fall-back）。
    """
    subnetworks = dict(instances)
    for conn in connections:
        connections = _merge_subnetworks(subnetworks, connections, conn)
    if not subnetworks:
        return {}
    final_s = next(iter(subnetworks.values()))
    if ports:
        return _rename_ports(final_s, ports)
    return final_s


__all__ = ["cascade_circuit"]
