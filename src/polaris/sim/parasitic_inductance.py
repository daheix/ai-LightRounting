"""R233 寄生电感提取（Grover/Wheeler 自感解析 + Neumann 互感）。

从 parasitic_advanced.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。对齐 Synopsys StarRC RLCK 模型（电感 + 互感，DSPF 输出）。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Synopsys StarRC Datasheet（RLCK 模型，DSPF 电感输出）
   https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
2. Wheeler, "Inductance Formulas for Single-Layer Coils", Proc. IRE 1928
   https://ieeexplore.ieee.org/document/1654891
3. Rosa, "Self and Mutual Inductances of Linear Conductors", NIST BS 1908
   https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
4. Grover, "Inductance Calculations", 1946（互感查表与公式）
5. Cadence PCB 互感计算（奇偶模阻抗法）
   https://resources.pcb.cadence.com/blog/mutual-capacitance-and-mutual-inductance-calculation
6. SemiEngineering Multi-Die Signoff（StarRC RLCK 互感）
   https://semiengineering.com/achieving-successful-multi-die-signoff/

## 规则依据

R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = ["ParasiticInductor"]

# 物理常数（SI 单位）
# 来源: NIST CODATA 2018
_MU_0 = 1.25663706212e-6  # 真空磁导率 (H/m)


@dataclass
class ParasiticInductor:
    """R233 寄生电感提取（Grover/Wheeler 自感 + Neumann 互感）。

    对齐 Synopsys StarRC RLCK 模型（电感 + 互感，DSPF 输出）。
    - 自感：L_self = μ0·L/(2π)·[ln(2L/(W+H)) + 0.5 + (W+H)/(6L)]
           （Rosa 1908 矩形截面导线公式，Wheeler 1928 简化）
    - 互感：M = μ0/(2π)·[L·ln((L+√(L²+d²))/d) - √(L²+d²) + d]
           （Neumann 公式两平行线段，Rosa 1908 NIST）

    来源（≥5 文献 URL）:
    - Synopsys StarRC Datasheet（RLCK 模型，DSPF 电感输出）:
      https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
    - Wheeler, "Inductance Formulas for Single-Layer Coils", Proc. IRE 1928:
      https://ieeexplore.ieee.org/document/1654891
    - Rosa, "Self and Mutual Inductances of Linear Conductors", NIST BS 1908:
      https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
    - Grover, "Inductance Calculations", 1946（互感查表与公式）
    - Cadence PCB 互感计算（奇偶模阻抗法）:
      https://resources.pcb.cadence.com/blog/mutual-capacitance-and-mutual-inductance-calculation
    - SemiEngineering Multi-Die Signoff（StarRC RLCK 互感）:
      https://semiengineering.com/achieving-successful-multi-die-signoff/

    Attributes:
        metal_thickness_um: 金属厚度 H (μm)。
    """

    metal_thickness_um: float

    def __post_init__(self) -> None:
        """参数 schema 验证（R03）。

        Raises:
            ValueError: 金属厚度非法时告警退出。
        """
        if self.metal_thickness_um <= 0:
            msg = f"metal_thickness_um 必须 > 0，得到 {self.metal_thickness_um}"
            raise ValueError(msg)

    def extract_self(
        self,
        length_um: float,
        width_um: float,
    ) -> dict[str, float]:
        """提取单根直导线自感（Rosa 1908 矩形截面公式）。

        L_self = μ0·L/(2π)·[ln(2L/(W+H)) + 0.5 + (W+H)/(6L)]

        Args:
            length_um: 导线长度 (μm)。
            width_um: 导线宽度 (μm)。

        Returns:
            {"inductance_ph": float}

        Raises:
            ValueError: 几何参数非法时告警退出。
        """
        if length_um <= 0:
            msg = f"length_um 必须 > 0，得到 {length_um}"
            raise ValueError(msg)
        if width_um <= 0:
            msg = f"width_um 必须 > 0，得到 {width_um}"
            raise ValueError(msg)
        L_m = length_um * 1e-6
        W_m = width_um * 1e-6
        H_m = self.metal_thickness_um * 1e-6
        # Rosa 1908 矩形截面导线自感公式
        ratio = 2.0 * L_m / (W_m + H_m)
        if ratio <= 1.0:
            msg = f"2L/(W+H) 必须 > 1 以保证 ln 有效，得到 {ratio}"
            raise ValueError(msg)
        bracket = math.log(ratio) + 0.5 + (W_m + H_m) / (6.0 * L_m)
        l_self = _MU_0 * L_m / (2.0 * math.pi) * bracket
        return {"inductance_ph": float(l_self * 1e12)}

    def extract_mutual(
        self,
        length_um: float,
        spacing_um: float,
    ) -> dict[str, float]:
        """提取两根等长平行导线间互感（Neumann 公式）。

        M = μ0/(2π)·[L·ln((L+√(L²+d²))/d) - √(L²+d²) + d]

        Args:
            length_um: 平行段长度 (μm)。
            spacing_um: 两导线中心距 (μm)。

        Returns:
            {"mutual_inductance_ph": float}

        Raises:
            ValueError: 间距过小或长度非法时告警退出。

        Note:
            R05 Bug 修复 v5.0-P1-3R1: 删除错误的 coupling_coefficient_hint 字段。
            耦合系数 K = M/√(L1·L2) 是无量纲的，原代码返回 m*1e12（pH 值）量纲错误。
            本方法不持有自感 L1/L2，无法计算 K。如需 K 请用 extract_inductance_matrix
            （返回完整 L 矩阵后可计算 K = M_ij/√(L_ii·L_jj)）。
        """
        if length_um <= 0:
            msg = f"length_um 必须 > 0，得到 {length_um}"
            raise ValueError(msg)
        if spacing_um <= 0:
            msg = f"spacing_um 必须 > 0，得到 {spacing_um}"
            raise ValueError(msg)
        L_m = length_um * 1e-6
        d_m = spacing_um * 1e-6
        # Neumann 公式两平行等长线段互感（Rosa 1908 NIST）
        sqrt_term = math.sqrt(L_m * L_m + d_m * d_m)
        m = _MU_0 / (2.0 * math.pi) * (
            L_m * math.log((L_m + sqrt_term) / d_m) - sqrt_term + d_m
        )
        return {
            "mutual_inductance_ph": float(m * 1e12),
        }

    def extract_inductance_matrix(
        self,
        wires: list[dict[str, float]],
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """提取多导体电感矩阵（自感 + 互感）。

        Args:
            wires: 导线列表，每项 {"length_um": L, "width_um": W,
                   "spacing_um": S}，spacing_um 为到下一根导线的中心距。

        Returns:
            (L_self_diag, M_offdiag) 自感对角矩阵 (n,) 与互感矩阵 (n,n)。
            互感矩阵非对角线 M[i,j]，对角线为 0。

        Raises:
            ValueError: 导线列表空或几何非法时告警退出。
        """
        if not wires:
            msg = "wires 列表不能为空"
            raise ValueError(msg)
        n = len(wires)
        l_self = np.zeros(n, dtype=float)
        m_mutual = np.zeros((n, n), dtype=float)
        for i, w in enumerate(wires):
            if "length_um" not in w or "width_um" not in w:
                msg = f"wires[{i}] 缺少 length_um 或 width_um"
                raise ValueError(msg)
            self_l = self.extract_self(w["length_um"], w["width_um"])
            l_self[i] = self_l["inductance_ph"]
        # 相邻互感
        for i in range(n - 1):
            w_i = wires[i]
            spacing = w_i.get("spacing_um")
            if spacing is None:
                continue
            if spacing <= 0:
                msg = f"wires[{i}].spacing_um 必须 > 0，得到 {spacing}"
                raise ValueError(msg)
            mutual = self.extract_mutual(w_i["length_um"], spacing)
            m_val = mutual["mutual_inductance_ph"]
            m_mutual[i, i + 1] = m_val
            m_mutual[i + 1, i] = m_val
        return l_self, m_mutual
