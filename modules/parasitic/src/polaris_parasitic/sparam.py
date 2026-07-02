"""R234 S 参数生成（π 型 RLC 网络 → ABCD → S，无源性/互易性验证）。

从 v4 ``polaris.sim.parasitic_sparam`` 迁移至 polaris-parasitic 子模块
（R13: 不保留 v4 兼容路径）。纯 NumPy/SciPy CPU，R04 兼容。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Pozar, "Microwave Engineering", 4th ed., §4（ABCD↔S 变换）
2. Altair SimLab Parasitics（Touchstone .sNp + SPICE 导出）
   https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm
3. Synopsys StarRC Datasheet（DSPF 频域仿真）
   https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
4. Cadence Quantus QRC（频域寄生仿真）
   https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
5. Touchstone File Format Specification v2.0（IBIS Open Forum 2009）
   https://ibis.org/connector/touchstone_spec2.pdf
6. Kurokawa, "Power Waves and the Scattering Matrix", IEEE TMTT 1965

## 规则依据

R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简 / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = ["ParasiticSParam"]


@dataclass
class ParasiticSParam:
    """R234 从寄生 RLC 生成 S 参数（π 型网络，无源/互易验证）。

    模型：对称 π 型集总网络
        端口1 ──[Z_series = R + jωL]── 端口2
                  |                    |
              [Y_shunt = jωC/2]    [Y_shunt = jωC/2]
                  |                    |
                 GND                  GND

    ABCD 矩阵级联：
        A = 1 + Z_s·Y_s/2,  B = Z_s·(1 + Z_s·Y_s/4)
        C = Y_s,            D = 1 + Z_s·Y_s/2
    S 参数从 ABCD 变换（Pozar §4）。

    来源（≥5 文献 URL）:
    - Pozar, "Microwave Engineering", 4th ed., §4（ABCD↔S 变换）
    - Altair SimLab Parasitics（Touchstone .sNp + SPICE 导出）:
      https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm
    - Synopsys StarRC Datasheet（DSPF 频域仿真）:
      https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
    - Cadence Quantus QRC（频域寄生仿真）:
      https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
    - Touchstone File Format Specification v2.0（IBIS Open Forum 2009）:
      https://ibis.org/connector/touchstone_spec2.pdf
    - Kurokawa, "Power Waves and the Scattering Matrix", IEEE TMTT 1965
    """

    @staticmethod
    def compute_s_params(
        frequencies_ghz: NDArray[np.float64] | list[float],
        resistance_ohm: float,
        inductance_ph: float,
        capacitance_ff: float,
        z0_ohm: float = 50.0,
    ) -> NDArray[np.complex128]:
        """计算 2 端口 S 参数矩阵数组。

        Args:
            frequencies_ghz: 频率数组 (GHz)。
            resistance_ohm: 串联寄生电阻 (Ω)。
            inductance_ph: 串联寄生电感 (pH)。
            capacitance_ff: 并联寄生电容 (fF)，对称分摊到两端。
            z0_ohm: 端口参考阻抗 (Ω)，默认 50。

        Returns:
            (N, 2, 2) 复数 S 参数数组，S[i] 为第 i 个频率的 2×2 矩阵。

        Raises:
            ValueError: 频率/参数非法时告警退出。
        """
        freq = np.asarray(frequencies_ghz, dtype=float)
        if freq.size == 0:
            msg = "frequencies_ghz 不能为空"
            raise ValueError(msg)
        if np.any(freq < 0):
            msg = f"频率必须 >= 0 GHz，得到 min={float(np.min(freq))}"
            raise ValueError(msg)
        if resistance_ohm < 0:
            msg = f"resistance_ohm 必须 >= 0，得到 {resistance_ohm}"
            raise ValueError(msg)
        if inductance_ph < 0:
            msg = f"inductance_ph 必须 >= 0，得到 {inductance_ph}"
            raise ValueError(msg)
        if capacitance_ff < 0:
            msg = f"capacitance_ff 必须 >= 0，得到 {capacitance_ff}"
            raise ValueError(msg)
        if z0_ohm <= 0:
            msg = f"z0_ohm 必须 > 0，得到 {z0_ohm}"
            raise ValueError(msg)
        # SI 单位换算
        omega = 2.0 * math.pi * freq * 1e9  # rad/s
        L_h = inductance_ph * 1e-12  # H
        C_f = capacitance_ff * 1e-15  # F
        # π 型网络：串联阻抗 Z_s = R + jωL，并联导纳 Y_s = jωC (C 总量，每端 C/2)
        z_s = resistance_ohm + 1j * omega * L_h
        y_s = 1j * omega * C_f
        # 对称 π 型 ABCD（每端并联 C/2）
        # A = 1 + Z_s·(jωC/2), B = Z_s, C = jωC + Z_s·(jωC/2)², D = A
        y_half = y_s / 2.0
        A = 1.0 + z_s * y_half
        B = z_s
        C = y_s + z_s * y_half * y_half
        D = A
        # ABCD → S（Pozar §4，z0=50 参考）
        z0 = z0_ohm
        denom = A + B / z0 + C * z0 + D
        # 避免 0 除
        if np.any(np.abs(denom) < 1e-30):
            msg = "ABCD→S 变换分母退化，检查 R/L/C 是否过大"
            raise ValueError(msg)
        # ABCD → S（Pozar, Microwave Engineering 4th ed., §4.4 表 4.2）
        # S11 = (A + B/Z0 - C·Z0 - D) / Δ
        # S12 = 2(AD - BC) / Δ
        # S21 = 2 / Δ
        # S22 = (-A + B/Z0 - C·Z0 + D) / Δ
        # 其中 Δ = A + B/Z0 + C·Z0 + D
        # *Bug 修复 (R05)*: 原 S22 公式符号全反，导致无源性验证失败。
        #   正确来源: Pozar §4.4，对称网络应有 S22 = S11。
        s11 = (A + B / z0 - C * z0 - D) / denom
        s12 = (2.0 * (A * D - B * C)) / denom
        s21 = 2.0 / denom
        s22 = (-A + B / z0 - C * z0 + D) / denom
        n = freq.size
        s = np.zeros((n, 2, 2), dtype=np.complex128)
        s[:, 0, 0] = s11
        s[:, 0, 1] = s12
        s[:, 1, 0] = s21
        s[:, 1, 1] = s22
        return s

    @staticmethod
    def verify_passivity(
        s: NDArray[np.complex128],
        tol: float = 1e-6,
    ) -> dict[str, object]:
        """验证 S 参数无源性（passivity）。

        无源线性网络充要条件：I - S·Sᴴ 半正定，等价于 S 的最大奇异值 ≤ 1。
        来源: Pozar §4; Kurokawa IEEE TMTT 1965。

        Args:
            s: (N, 2, 2) 或 (2, 2) S 参数数组。
            tol: 数值容差。

        Returns:
            {"passive": bool, "max_singular_value": float, "n_freqs": int}

        Raises:
            ValueError: S 参数维度非法时告警退出。
        """
        s_arr = np.asarray(s, dtype=np.complex128)
        if s_arr.ndim == 2:
            s_arr = s_arr[np.newaxis, ...]
        if s_arr.ndim != 3 or s_arr.shape[1] != s_arr.shape[2]:
            msg = f"S 参数维度必须为 (N,2,2) 或 (2,2)，得到 {s_arr.shape}"
            raise ValueError(msg)
        n = s_arr.shape[0]
        max_sv = 0.0
        for i in range(n):
            sv = np.linalg.svd(s_arr[i], compute_uv=False)
            local_max = float(np.max(sv))
            if local_max > max_sv:
                max_sv = local_max
        passive = bool(max_sv <= 1.0 + tol)
        return {
            "passive": passive,
            "max_singular_value": float(max_sv),
            "n_freqs": int(n),
        }

    @staticmethod
    def verify_reciprocity(
        s: NDArray[np.complex128],
        tol: float = 1e-9,
    ) -> dict[str, object]:
        """验证 S 参数互易性（reciprocity）。

        互易网络：S = Sᵀ（转置，非共轭）。来源: Pozar §4。

        Args:
            s: (N, 2, 2) 或 (2, 2) S 参数数组。
            tol: 数值容差。

        Returns:
            {"reciprocal": bool, "max_transpose_error": float, "n_freqs": int}

        Raises:
            ValueError: S 参数维度非法时告警退出。
        """
        s_arr = np.asarray(s, dtype=np.complex128)
        if s_arr.ndim == 2:
            s_arr = s_arr[np.newaxis, ...]
        if s_arr.ndim != 3 or s_arr.shape[1] != s_arr.shape[2]:
            msg = f"S 参数维度必须为 (N,2,2) 或 (2,2)，得到 {s_arr.shape}"
            raise ValueError(msg)
        n = s_arr.shape[0]
        max_err = 0.0
        for i in range(n):
            err = float(np.max(np.abs(s_arr[i] - s_arr[i].T)))
            if err > max_err:
                max_err = err
        reciprocal = bool(max_err <= tol)
        return {
            "reciprocal": reciprocal,
            "max_transpose_error": float(max_err),
            "n_freqs": int(n),
        }
