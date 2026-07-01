"""R232 寄生电容提取（平行板 + 侧边/边缘电容修正 + 多导体耦合电容矩阵）。

从 parasitic_advanced.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。对齐 Cadence Quantus QRC / Synopsys StarRC ScanBand 方法。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Cadence Quantus QRC 3D 场求解
   https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
2. Synopsys StarRC Custom（Rapid3D，3D 耦合电容）
   https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-custom-ds.pdf
3. UCLA ECE902 电容提取（2.5D 基础，耦合屏蔽）
   http://eda.ee.ucla.edu/ECE902_pd/cap1.pdf
4. Banerjee ECE 225 UCSB Lecture 6（arcosh 边缘电容模型）
   http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
5. Arora et al., IEEE TCAD 15(1), 1996（互连电容解析建模）
   https://www.stanford.edu/class/archive/ee/ee371/ee371.1066/handouts/arora96.pdf
6. Cadence PCB 互容/互感计算（奇偶模阻抗法）
   https://resources.pcb.cadence.com/blog/mutual-capacitance-and-mutual-inductance-calculation

## 规则依据

R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = ["ParasiticCapacitor"]

# 物理常数（SI 单位）
# 来源: NIST CODATA 2018
_EPS_0 = 8.8541878128e-12  # 真空介电常数 (F/m)


@dataclass
class ParasiticCapacitor:
    """R232 寄生电容提取（平行板 + 侧边/边缘修正 + 多导体耦合电容）。

    对齐 Cadence Quantus QRC / Synopsys StarRC ScanBand 方法：
    - 平行板电容：C_pp = ε_r·ε_0·W·L / d
    - 侧边/边缘电容：C_fringe = 2π·ε·L / arcosh(2d/H + 1)（Banerjee 圆柱模型）
    - 耦合电容：相邻同层导线，基于 2.5D 屏蔽基础（UCLA ECE902 Foundation IV）

    来源（≥5 文献 URL）:
    - Cadence Quantus QRC 3D 场求解:
      https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
    - Synopsys StarRC Custom（Rapid3D，3D 耦合电容）:
      https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-custom-ds.pdf
    - UCLA ECE902 电容提取（2.5D 基础，耦合屏蔽）:
      http://eda.ee.ucla.edu/ECE902_pd/cap1.pdf
    - Banerjee ECE 225 UCSB Lecture 6（arcosh 边缘电容模型）:
      http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
    - Arora et al., IEEE TCAD 15(1), 1996（互连电容解析建模）:
      https://www.stanford.edu/class/archive/ee/ee371/ee371.1066/handouts/arora96.pdf
    - Cadence PCB 互容/互感计算（奇偶模阻抗法）:
      https://resources.pcb.cadence.com/blog/mutual-capacitance-and-mutual-inductance-calculation

    Attributes:
        eps_r: 介质相对介电常数（SiO2=3.9，Si=11.7）。
        metal_thickness_um: 金属厚度 H (μm)。
        dielectric_thickness_um: 介质厚度 d (μm)。
    """

    eps_r: float
    metal_thickness_um: float
    dielectric_thickness_um: float

    def __post_init__(self) -> None:
        """参数 schema 验证（R03）。

        Raises:
            ValueError: 介电常数/厚度非法时告警退出。
        """
        if self.eps_r <= 0:
            msg = f"eps_r 必须 > 0，得到 {self.eps_r}"
            raise ValueError(msg)
        if self.metal_thickness_um <= 0:
            msg = f"metal_thickness_um 必须 > 0，得到 {self.metal_thickness_um}"
            raise ValueError(msg)
        if self.dielectric_thickness_um <= 0:
            msg = f"dielectric_thickness_um 必须 > 0，得到 {self.dielectric_thickness_um}"
            raise ValueError(msg)

    def extract_self(
        self,
        length_um: float,
        width_um: float,
    ) -> dict[str, float]:
        """提取单根导线对地寄生电容（平行板 + 侧边修正）。

        C_pp = ε_r·ε_0·W·L / d
        C_fringe = 2π·ε_r·ε_0·L / arcosh(2d/H + 1)  （Banerjee 圆柱模型，
                 2π 已含左右两侧边缘场，无需再 ×2）

        Args:
            length_um: 导线长度 (μm)。
            width_um: 导线宽度 (μm)。

        Returns:
            {"capacitance_ff": float, "capacitance_area_ff": float,
             "capacitance_fringe_ff": float}

        Raises:
            ValueError: 几何参数非法时告警退出。
        """
        if length_um <= 0:
            msg = f"length_um 必须 > 0，得到 {length_um}"
            raise ValueError(msg)
        if width_um <= 0:
            msg = f"width_um 必须 > 0，得到 {width_um}"
            raise ValueError(msg)
        # 统一 SI 单位 (m)
        L_m = length_um * 1e-6
        W_m = width_um * 1e-6
        d_m = self.dielectric_thickness_um * 1e-6
        H_m = self.metal_thickness_um * 1e-6
        eps = self.eps_r * _EPS_0
        # 平行板电容
        c_area = eps * W_m * L_m / d_m
        # 侧边/边缘电容（Banerjee arcosh 模型）
        # arcosh(2d/H + 1)，当 2d/H+1 > 1 时有效
        arg = 2.0 * d_m / H_m + 1.0
        if arg <= 1.0:
            msg = f"介质/金属厚度比非法，arcosh 参数 {arg} ≤ 1"
            raise ValueError(msg)
        acosh_val = math.acosh(arg)
        if acosh_val <= 1e-18:
            msg = f"arcosh 退化，参数 arg={arg}"
            raise ValueError(msg)
        c_fringe = 2.0 * math.pi * eps * L_m / acosh_val
        c_total = c_area + c_fringe
        # F = F/m × m = F；fF = F × 1e15
        return {
            "capacitance_ff": float(c_total * 1e15),
            "capacitance_area_ff": float(c_area * 1e15),
            "capacitance_fringe_ff": float(c_fringe * 1e15),
        }

    def extract_coupling(
        self,
        length_um: float,
        width_um: float,
        spacing_um: float,
    ) -> dict[str, float]:
        """提取两根平行同层导线间的耦合电容。

        基于同层相邻导线耦合模型（UCLA ECE902 Foundation IV：仅最近邻相关，
        非紧邻可忽略）。采用 Sakurai-Tamaru 经验公式（IEEE JSSC 1983）：
        C_couple ≈ ε·L·[1.10·(W/S) + 0.77·ln(1 + 2H/S) + 1.41·(H/S)^0.5]

        当 S → 0 时公式发散，物理上限制 S ≥ 0.01 μm。

        来源:
        - UCLA ECE902 Foundation IV（仅最近邻耦合）:
          http://eda.ee.ucla.edu/ECE902_pd/cap1.pdf
        - Sakurai & Tamaru, IEEE JSSC 18(4), 1983（同层耦合经验公式）
        - Arora et al., IEEE TCAD 15(1), 1996（耦合电容建模）

        Args:
            length_um: 平行段长度 (μm)。
            width_um: 导线宽度 (μm)。
            spacing_um: 两导线间距 (μm)。

        Returns:
            {"coupling_capacitance_ff": float, "spacing_um": float}

        Raises:
            ValueError: 间距过小或几何非法时告警退出。
        """
        if length_um <= 0:
            msg = f"length_um 必须 > 0，得到 {length_um}"
            raise ValueError(msg)
        if width_um <= 0:
            msg = f"width_um 必须 > 0，得到 {width_um}"
            raise ValueError(msg)
        if spacing_um < 0.01:
            msg = f"spacing_um 不得 < 0.01 μm（避免耦合发散），得到 {spacing_um}"
            raise ValueError(msg)
        L_m = length_um * 1e-6
        W_m = width_um * 1e-6
        S_m = spacing_um * 1e-6
        H_m = self.metal_thickness_um * 1e-6
        eps = self.eps_r * _EPS_0
        # Sakurai-Tamaru 同层耦合经验公式（每单位长度）
        # 系数来源: Sakurai & Tamaru, IEEE JSSC 18(4), 1983
        w_over_s = W_m / S_m
        log_term = math.log(1.0 + 2.0 * H_m / S_m)
        sqrt_term = math.sqrt(H_m / S_m)
        c_per_len = eps * (1.10 * w_over_s + 0.77 * log_term + 1.41 * sqrt_term)
        c_couple = c_per_len * L_m
        return {
            "coupling_capacitance_ff": float(c_couple * 1e15),
            "spacing_um": float(spacing_um),
        }

    def extract_capacitance_matrix(
        self,
        wires: list[dict[str, float]],
    ) -> NDArray[np.float64]:
        """提取多导体电容矩阵（n×n，自容 + 互容）。

        矩阵约定（UCLA ECE902 电容矩阵）：
        - 对角线 C[i,i] = 第 i 根导线对地自容
        - 非对角线 C[i,j] = 第 i, j 根导线间耦合电容（取负号遵循 SPICE 约定）

        Args:
            wires: 导线列表，每项 {"length_um": L, "width_um": W,
                   "spacing_um": S}，spacing_um 为到下一根导线的间距
                   （最后一根可省略）。

        Returns:
            n×n 电容矩阵 (fF)，n = len(wires)。

        Raises:
            ValueError: 导线列表空或几何非法时告警退出。
        """
        if not wires:
            msg = "wires 列表不能为空"
            raise ValueError(msg)
        n = len(wires)
        cmat = np.zeros((n, n), dtype=float)
        for i, w in enumerate(wires):
            if "length_um" not in w or "width_um" not in w:
                msg = f"wires[{i}] 缺少 length_um 或 width_um 字段"
                raise ValueError(msg)
            self_cap = self.extract_self(w["length_um"], w["width_um"])
            cmat[i, i] = self_cap["capacitance_ff"]
        # 相邻耦合（Foundation IV：仅最近邻）
        for i in range(n - 1):
            w_i = wires[i]
            spacing = w_i.get("spacing_um")
            if spacing is None:
                continue
            if spacing <= 0:
                msg = f"wires[{i}].spacing_um 必须 > 0，得到 {spacing}"
                raise ValueError(msg)
            coup = self.extract_coupling(
                w_i["length_um"], w_i["width_um"], spacing
            )
            c_ij = coup["coupling_capacitance_ff"]
            # SPICE 约定：非对角线取负
            cmat[i, i + 1] = -c_ij
            cmat[i + 1, i] = -c_ij
        return cmat
