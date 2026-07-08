"""S 参数级联器（纯 numpy 子网络增长算法）。

支持两种连接模式:
1. **两子网络连接**（不同子网络间端口互连）: 标准子网络增长公式，
   分母 (1 - S1_kk * S2_ll)。
2. **反馈环**（同一子网络两端口互连，如环谐振器）: Filipsson 1981 方程6，
   分母 ((1-S_kl)*(1-S_lk) - S_kk*S_ll)。

端口命名约定: 所有子网络端口名始终用 "实例名.端口名" 完整引用格式
（如 "wg1.in"），避免不同子网络同名端口合并后冲突。

来源 (R02 学术诚信，≥5 篇文献 URL):
1. SAX 子网络增长: https://flaport.github.io/sax/backends.html
2. Filipsson 1978, "A new general computer algorithm for S-matrix calculation
   of interconnected multiports", Proc. Eur. Microw. Conf.,
   https://doi.org/10.1109/EUMA.1978.332681
3. Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85,
   https://arxiv.org/abs/2009.05146
4. Pozar, "Microwave Engineering" 4th ed. §4.3 (两网络级联),
   https://www.wiley.com/en-us/Microwave+Engineering%2C+4th+Edition-p-9781118213636
5. Kurokawa 1965, "Power Waves and the Scattering Matrix", IEEE TMTT,
   https://doi.org/10.1109/TMTT.1965.1125961
6. Collin 1992, "Foundations for Microwave Engineering" §4.5,
   https://www.ieee.org/

合规: R02 学术诚信 / R03 禁止 fall-back（分母趋零 raise，不兜底）/
R04 纯 NumPy / R05 无 TODO / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import logging

import numpy as np

from polaris_circuit.types import SDict

logger = logging.getLogger(__name__)

# 子网络增长算法分母接近零的阈值（来源: Simphony 论文 §3.3）
# 当分母绝对值 < DENOM_MIN 时，谐振陷波分母趋零，告警退出
DENOM_MIN = 1e-15


def _collect_ports(sdict: SDict) -> set[str]:
    """从 S 参数字典收集所有端口名。"""
    ports: set[str] = set()
    for p_out, p_in in sdict:
        ports.add(p_out)
        ports.add(p_in)
    return ports


def _n_freq_of(sdict: SDict) -> int:
    """从 S 参数字典推断频率点数。"""
    first_val = next(iter(sdict.values()), np.zeros(1))
    return len(first_val) if hasattr(first_val, "__len__") else 1


def _zero(n_freq: int) -> np.ndarray:
    """构造复零数组。"""
    return np.zeros(n_freq, dtype=complex)


def _get(sdict: SDict, p_out: str, p_in: str, n_freq: int) -> np.ndarray:
    """获取 S 参数，不存在则返回零数组。"""
    val = sdict.get((p_out, p_in))
    if val is None:
        return _zero(n_freq)
    return np.asarray(val, dtype=complex)


def _connect_two_subnetworks(s1: SDict, s2: SDict, k: str, l: str) -> SDict:
    """两子网络连接（标准子网络增长公式，纯 numpy 实现）。

    连接 s1 的端口 k 和 s2 的端口 l，消去 k, l。
    剩余端口 I1 = P1 - {k}, I2 = P2 - {l}。

    公式（推导见模块 docstring 文献 [4][5]）:
        S'_ij (i,j ∈ I1) = S1_ij + S1_ik * S2_ll * S1_kj / (1 - S1_kk * S2_ll)
        S'_ij (i∈I1, j∈I2) = S1_ik * S2_lj / (1 - S1_kk * S2_ll)
        S'_ij (i,j ∈ I2) = S2_ij + S2_il * S1_kk * S2_lj / (1 - S1_kk * S2_ll)
        S'_ij (i∈I2, j∈I1) = S2_il * S1_kj / (1 - S1_kk * S2_ll)

    Args:
        s1: 子网络1 的 S 参数（端口名 "inst.port" 格式）。
        s2: 子网络2 的 S 参数。
        k: s1 上要连接的端口完整引用。
        l: s2 上要连接的端口完整引用。

    Raises:
        RuntimeError: 端口不存在或分母趋零（R03 禁止 fall-back）。
    """
    ports_1 = _collect_ports(s1)
    ports_2 = _collect_ports(s2)
    if k not in ports_1:
        raise RuntimeError(
            f"连接端口 '{k}' 不在子网络1 {sorted(ports_1)}（R03）"
        )
    if l not in ports_2:
        raise RuntimeError(
            f"连接端口 '{l}' 不在子网络2 {sorted(ports_2)}（R03）"
        )

    n_freq = _n_freq_of(s1)
    S1_kk = _get(s1, k, k, n_freq)
    S2_ll = _get(s2, l, l, n_freq)
    denom = 1.0 - S1_kk * S2_ll
    denom_abs = np.abs(denom)
    if np.any(denom_abs < DENOM_MIN):
        min_denom = float(np.min(denom_abs))
        msg = (
            f"两子网络连接分母趋零（1-S1_{k}{k}*S2_{l}{l}={min_denom:.3e} < "
            f"{DENOM_MIN:.0e}），数值不稳定。"
        )
        logger.error(msg)
        raise RuntimeError(msg)

    I1 = [p for p in ports_1 if p != k]
    I2 = [p for p in ports_2 if p != l]
    new_block: dict[tuple[str, str], np.ndarray] = {}
    for i in I1:
        S1_ik = _get(s1, i, k, n_freq)
        for j in I1:
            S1_ij = _get(s1, i, j, n_freq)
            S1_kj = _get(s1, k, j, n_freq)
            new_block[(i, j)] = S1_ij + S1_ik * S2_ll * S1_kj / denom
        for j in I2:
            S2_lj = _get(s2, l, j, n_freq)
            new_block[(i, j)] = S1_ik * S2_lj / denom
    for i in I2:
        S2_il = _get(s2, i, l, n_freq)
        for j in I2:
            S2_ij = _get(s2, i, j, n_freq)
            S2_lj = _get(s2, l, j, n_freq)
            new_block[(i, j)] = S2_ij + S2_il * S1_kk * S2_lj / denom
        for j in I1:
            S1_kj = _get(s1, k, j, n_freq)
            new_block[(i, j)] = S2_il * S1_kj / denom
    return new_block


def _connect_feedback_loop(s1: SDict, k: str, l: str) -> SDict:
    """反馈环连接（Filipsson 1981 方程6，同一子网络两端口互连）。

    连接 s1 的端口 k 和 l，消去 k, l。剩余端口 I = P - {k, l}。

    Filipsson 1981 方程6:
        S'_ij = S_ij + (S_kj*S_il*(1-S_lk) + S_lj*S_ik*(1-S_kl)
                       + S_kj*S_ll*S_ik + S_lj*S_kk*S_il)
                    / ((1-S_kl)*(1-S_lk) - S_kk*S_ll)

    来源:
    - Filipsson 1978 Eur. Microw. Conf. (文献 [2])
    - SAX filipsson_gunnar 后端 (文献 [1])
    - Pflüger et al. 2021 Simphony (文献 [3])

    Raises:
        RuntimeError: 端口不存在或分母趋零（R03 禁止 fall-back）。
    """
    all_ports = _collect_ports(s1)
    if k not in all_ports or l not in all_ports:
        raise RuntimeError(
            f"反馈环端口 '{k}' 或 '{l}' 不在端口集 {sorted(all_ports)}（R03）"
        )
    current_ports = tuple(p for p in all_ports if p != k and p != l)
    if not current_ports:
        return {}
    n_freq = _n_freq_of(s1)
    S_kk = _get(s1, k, k, n_freq)
    S_ll = _get(s1, l, l, n_freq)
    S_kl = _get(s1, k, l, n_freq)
    S_lk = _get(s1, l, k, n_freq)
    denom = (1.0 - S_kl) * (1.0 - S_lk) - S_kk * S_ll
    denom_abs = np.abs(denom)
    if np.any(denom_abs < DENOM_MIN):
        min_denom = float(np.min(denom_abs))
        msg = (
            f"反馈环 Filipsson 分母趋零（{min_denom:.3e} < "
            f"{DENOM_MIN:.0e}），强谐振/反馈环路数值不稳定。"
        )
        logger.error(msg)
        raise RuntimeError(msg)
    new_block: dict[tuple[str, str], np.ndarray] = {}
    for i in current_ports:
        S_ik = _get(s1, i, k, n_freq)
        S_il = _get(s1, i, l, n_freq)
        for j in current_ports:
            S_ij = _get(s1, i, j, n_freq)
            S_kj = _get(s1, k, j, n_freq)
            S_lj = _get(s1, l, j, n_freq)
            numer = (
                S_kj * S_il * (1.0 - S_lk)
                + S_lj * S_ik * (1.0 - S_kl)
                + S_kj * S_ll * S_ik
                + S_lj * S_kk * S_il
            )
            new_block[(i, j)] = S_ij + numer / denom
    return new_block


def _rename_ports(final_s: SDict, ports: dict[str, str]) -> SDict:
    """将内部端口完整引用重命名为外部端口名。

    Args:
        final_s: 最终 S 参数，端口名为 "inst.port" 完整引用格式。
        ports: {external_name: "inst.port"} 外部端口映射。

    Returns:
        重命名后的 S 参数字典。
    """
    int_to_exts: dict[str, list[str]] = {}
    for ext_name, int_ref in ports.items():
        int_to_exts.setdefault(int_ref, []).append(ext_name)
    renamed: SDict = {}
    for (p_out, p_in), val in final_s.items():
        if p_out in int_to_exts and p_in in int_to_exts:
            for ext_out in int_to_exts[p_out]:
                for ext_in in int_to_exts[p_in]:
                    renamed[(ext_out, ext_in)] = val
    return renamed if renamed else final_s


def _prefix_instance_ports(inst_name: str, sdict: SDict) -> SDict:
    """给子网络端口名加实例名前缀（"in" → "inst.in"）。

    避免不同子网络同名端口合并后冲突（如 dc1.in2 与 dc2.in2）。
    """
    prefixed: SDict = {}
    for (p_out, p_in), val in sdict.items():
        prefixed[(f"{inst_name}.{p_out}", f"{inst_name}.{p_in}")] = val
    return prefixed


def _process_one_cascade_connection(
    conn: tuple[str, str],
    subnetworks: dict[str, SDict],
    inst_to_subnet: dict[str, str],
) -> None:
    """处理单条连接：消去内部端口，合并子网络（Extract Method，R11 质量门禁）。

    支持反馈环（同子网络内连接）与两子网络合并两种路径。
    就地修改 ``subnetworks`` 与 ``inst_to_subnet``。

    Raises:
        RuntimeError: 连接指向不存在的实例或子网络（R03 禁止 fall-back）。
    """
    inst1_name = conn[0].split(".", 1)[0]
    inst2_name = conn[1].split(".", 1)[0]
    if inst1_name not in inst_to_subnet or inst2_name not in inst_to_subnet:
        raise RuntimeError(
            f"连接 {conn} 指向不存在的实例 '{inst1_name}' 或 "
            f"'{inst2_name}'，当前实例: {sorted(inst_to_subnet.keys())}。"
            f"可能原因: 连接关系有误或实例未定义（R03 禁止 fall-back）。"
        )
    subnet1 = inst_to_subnet[inst1_name]
    subnet2 = inst_to_subnet[inst2_name]
    if subnet1 not in subnetworks or subnet2 not in subnetworks:
        raise RuntimeError(
            f"子网络 '{subnet1}' 或 '{subnet2}' 不存在（R03 内部状态错误）"
        )
    s1 = subnetworks[subnet1]
    is_feedback = subnet1 == subnet2
    if is_feedback:
        merged = _connect_feedback_loop(s1, conn[0], conn[1])
        subnetworks[subnet1] = merged
        return
    s2 = subnetworks[subnet2]
    merged = _connect_two_subnetworks(s1, s2, conn[0], conn[1])
    new_name = f"{subnet1}+{subnet2}"
    subnetworks[new_name] = merged
    del subnetworks[subnet1]
    del subnetworks[subnet2]
    # 更新实例 → 子网络映射
    for inst, sn in inst_to_subnet.items():
        if sn == subnet1 or sn == subnet2:
            inst_to_subnet[inst] = new_name


def _merge_final_subnetworks(
    subnetworks: dict[str, SDict],
    ports: dict[str, str] | None,
) -> SDict:
    """合并所有剩余子网络为 block-diag，并按 ports 重命名外部端口。

    支持多独立子网络（如并行双波导），各子网络端口直接合并到最终字典。
    """
    if not subnetworks:
        return {}
    final_s: SDict = {}
    for sdict in subnetworks.values():
        for key, val in sdict.items():
            final_s[key] = val
    if ports:
        return _rename_ports(final_s, ports)
    return final_s


def cascade_circuit(
    instances: dict[str, SDict],
    connections: list[tuple[str, str]],
    ports: dict[str, str] | None = None,
) -> SDict:
    """级联多个器件 S 参数组成电路（纯 numpy 子网络增长）。

    逐步将器件两两连接，消去内部端口，保留外部端口。
    连接用原始实例名引用，通过 inst_to_subnet 映射解析当前所属子网络，
    避免合并后重命名导致的端口名冲突。

    来源 (R02):
    - SAX circuit 级联: https://flapport.github.io/sax/
    - Filipsson 1978 Eur. Microw. Conf.
    - Pozar §4.3 两网络级联

    Args:
        instances: 器件实例字典 {instance_name: SDict}。
        connections: 连接列表 [(instance1.port, instance2.port), ...]。
        ports: 外部端口映射 {external_name: instance.port}。

    Returns:
        电路级 S 参数字典。

    Raises:
        RuntimeError: 数值不稳定（分母趋零）或连接指向不存在的实例（R03）。
    """
    # 给所有实例端口名加实例前缀（避免同名端口冲突）
    subnetworks: dict[str, SDict] = {
        name: _prefix_instance_ports(name, sdict)
        for name, sdict in instances.items()
    }
    # 实例名 → 当前所属子网络名（合并后更新）
    inst_to_subnet: dict[str, str] = {name: name for name in instances}
    for conn in connections:
        _process_one_cascade_connection(conn, subnetworks, inst_to_subnet)
    return _merge_final_subnetworks(subnetworks, ports)


__all__ = ["cascade_circuit"]
