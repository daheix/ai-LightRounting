"""R231-R235 寄生提取进阶模块（对齐 Synopsys StarRC / Cadence Quantus QRC）。

在 layout_aware.ParasiticExtractor 基础上扩展：
- R231 寄生电阻提取（片电阻 + 一阶/二阶温度系数 TC1/TC2）
- R232 寄生电容提取（平行板 + 侧边/边缘电容修正 + 多导体耦合电容矩阵）
- R233 寄生电感提取（Grover/Wheeler 自感解析公式 + Neumann 互感）
- R234 S 参数生成（从 RLC 寄生构建 π 型网络 → ABCD → S，无源性/互易性验证）
- R235 SPICE 网表输出（生成兼容 SPICE 的 .subckt，含 TC1/TC2）

学术依据（≥5 文献 URL，R02 学术诚信）:
- Synopsys StarRC Datasheet（Gold Standard 寄生提取，RLCK 模型，TC1/TC2）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Synopsys StarRC Resistance Extraction Blog（RPSQ × L/W 片电阻公式）:
  https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
- Synopsys StarRC Custom Datasheet（Rapid3D 场求解，3D 耦合电容）:
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-custom-ds.pdf
- Cadence Quantus QRC 3D 场求解器精度研究:
  https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
- Cadence PCB 互容/互感解析（奇偶模阻抗法）:
  https://resources.pcb.cadence.com/blog/mutual-capacitance-and-mutual-inductance-calculation
- UCLA ECE902 电容提取教程（电容矩阵，2.5D 基础，耦合电容屏蔽效应）:
  http://eda.ee.ucla.edu/ECE902_pd/cap1.pdf
- Banerjee ECE 225 UCSB Lecture 6（边缘电容 arcosh 模型，VLSI 互连）:
  http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
- Arora et al., IEEE TCAD 15(1), 1996（互连电容建模，doi:10.1109/43.534256）:
  https://www.stanford.edu/class/archive/ee/ee371/ee371.1066/handouts/arora96.pdf
- Wheeler, "Inductance Formulas for Single-Layer Coils", Proc. IRE 1928:
  https://ieeexplore.ieee.org/document/1654891
- Grover, "Inductance Calculations: Working Formulas and Tables", 1946（互感 Neumann 公式）
- Rosa, "The Self and Mutual Inductances of Linear Conductors", NIST BS 1908:
  https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
- Pozar, "Microwave Engineering", 4th ed., §4 (ABCD → S 参数变换)
- Altair SimLab Parasitics Extraction（Touchstone .sNp 导出 + SPICE 导出）:
  https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

# 物理常数（SI 单位）
# 来源: NIST CODATA 2018
_EPS_0 = 8.8541878128e-12  # 真空介电常数 (F/m)
_MU_0 = 1.25663706212e-6  # 真空磁导率 (H/m)


# =============================================================================
# R231 寄生电阻提取（片电阻 + 温度系数 TC1/TC2）
# =============================================================================
@dataclass
class ParasiticResistor:
    """R231 寄生电阻提取（片电阻模型 + 一阶/二阶温度系数）。

    对齐 Synopsys StarRC 电阻提取方法学：
    - 规则法（rule-based）：R = RPSQ × L / W
    - 温度系数：R(T) = R0 × (1 + TC1×ΔT + TC2×ΔT²)

    来源（≥5 文献 URL）:
    - Synopsys StarRC Datasheet（RLCK 模型）:
      https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
    - Synopsys StarRC Resistance Extraction（RPSQ × L/W 片电阻公式）:
      https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
    - StarRC TC1/TC2 温度系数提取配置:
      https://wenku.csdn.net/answer/3t8nxpm1me
    - Banerjee ECE 225 UCSB（互连电阻温度系数建模）:
      http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
    - SiEPIC EBeam PDK（波导金属接触片电阻典型值）:
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Attributes:
        sheet_resistance_ohm_sq: 片电阻 RPSQ (Ω/□)，硅光 TiN heater 典型值 ~5 Ω/□，
                                 铝互连 ~0.05 Ω/□。
        tc1: 一阶温度系数 (1/°C)，金属典型 +0.0039，TiN ~ -0.0005。
        tc2: 二阶温度系数 (1/°C²)，多数金属 < 1e-6，可置 0。
        t_ref: 参考温度 (°C)，默认 25。
    """

    sheet_resistance_ohm_sq: float
    tc1: float = 0.0
    tc2: float = 0.0
    t_ref: float = 25.0

    def __post_init__(self) -> None:
        """参数 schema 验证（R03 禁止 fall-back）。

        Raises:
            ValueError: 片电阻非正或温度系数非法时告警退出。
        """
        if self.sheet_resistance_ohm_sq <= 0:
            msg = f"sheet_resistance_ohm_sq 必须 > 0，得到 {self.sheet_resistance_ohm_sq}"
            raise ValueError(msg)
        if not math.isfinite(self.tc1) or not math.isfinite(self.tc2):
            msg = f"温度系数必须有限，得到 tc1={self.tc1}, tc2={self.tc2}"
            raise ValueError(msg)

    def extract(
        self,
        length_um: float,
        width_um: float,
        temperature_c: float | None = None,
    ) -> dict[str, float]:
        """提取波导/金属寄生电阻。

        R = RPSQ × L / W
        R(T) = R0 × (1 + TC1×ΔT + TC2×ΔT²)  （StarRC TC1/TC2 模型）

        Args:
            length_um: 导线长度 (μm)。
            width_um: 导线宽度 (μm)。
            temperature_c: 工作温度 (°C)，None 时使用参考温度。

        Returns:
            {"resistance_ohm": float, "n_squares": float,
             "temperature_c": float, "temp_factor": float}

        Raises:
            ValueError: 长度/宽度非正时告警退出。
        """
        if length_um <= 0:
            msg = f"length_um 必须 > 0，得到 {length_um}"
            raise ValueError(msg)
        if width_um <= 0:
            msg = f"width_um 必须 > 0，得到 {width_um}"
            raise ValueError(msg)
        n_sq = length_um / width_um
        r0 = self.sheet_resistance_ohm_sq * n_sq
        t_op = self.t_ref if temperature_c is None else float(temperature_c)
        if not math.isfinite(t_op):
            msg = f"temperature_c 必须有限，得到 {t_op}"
            raise ValueError(msg)
        delta_t = t_op - self.t_ref
        # StarRC TC1/TC2 二阶温度模型
        temp_factor = 1.0 + self.tc1 * delta_t + self.tc2 * delta_t * delta_t
        r_at_t = r0 * temp_factor
        return {
            "resistance_ohm": float(r_at_t),
            "resistance_nominal_ohm": float(r0),
            "n_squares": float(n_sq),
            "temperature_c": float(t_op),
            "temp_factor": float(temp_factor),
        }


# =============================================================================
# R232 寄生电容提取（平行板 + 侧边电容修正 + 耦合电容矩阵）
# =============================================================================
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


# =============================================================================
# R233 寄生电感提取（自感解析 + 互感 Neumann）
# =============================================================================
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


# =============================================================================
# R234 S 参数生成（π 型 RLC 网络 → ABCD → S，无源/互易验证）
# =============================================================================
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


# =============================================================================
# R235 SPICE 网表输出（兼容 SPICE .subckt，含 TC1/TC2）
# =============================================================================
class SpiceNetlistWriter:
    """R235 SPICE 网表输出（生成兼容 SPICE 的 .subckt，含温度系数）。

    对齐 Synopsys StarRC DSPF 输出与 SPICE 语法：
    - 电阻：R<name> n1 n2 <value> [TC1=<tc1>] [TC2=<tc2>]
    - 电容：C<name> n1 n2 <value>
    - 电感：L<name> n1 n2 <value>
    - 互感：K<name> L<name1> L<name2> <coupling>

    来源（≥5 文献 URL）:
    - Synopsys StarRC Datasheet（DSPF 寄生网表输出）:
      https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
    - StarRC TC1/TC2 SPICE 输出格式:
      https://wenku.csdn.net/answer/3t8nxpm1me
    - Berkeley SPICE3f5 用户手册（R/L/C/互感语法）:
      https://bwrcs.eecs.berkeley.edu/Classes/IcBook/SPICE/
    - ngspice 用户手册 §1.1（无源元件语法）:
      https://ngspice.sourceforge.io/docs.html
    - Altair SimLab SPICE 导出:
      https://help.altair.com/simlab/help/en_us/topics/analysis/ParasiticParametersExtraction/PE_Result_Request.htm
    - Qucs-S Spice4qucs 子电路语法:
      https://qucs-help.readthedocs.io/en/spice4qucs/SubLib.html
    """

    def __init__(self, subckt_name: str = "parasitic_net") -> None:
        """初始化网表写入器。

        Args:
            subckt_name: 子电路名称，默认 "parasitic_net"。

        Raises:
            ValueError: 子电路名非法时告警退出。
        """
        if not subckt_name or not subckt_name.replace("_", "").isalnum():
            msg = f"subckt_name 必须为字母数字下划线，得到 '{subckt_name}'"
            raise ValueError(msg)
        self.subckt_name = subckt_name
        self._lines: list[str] = []
        self._nodes: set[str] = set()

    def _check_node(self, node: str) -> None:
        """校验节点名合法性（R03）。"""
        if not node:
            msg = "节点名不能为空"
            raise ValueError(msg)
        if not node.replace("_", "").replace(".", "").isalnum():
            msg = f"节点名非法 '{node}'，须为字母数字下划线/点"
            raise ValueError(msg)

    def add_resistor(
        self,
        name: str,
        node1: str,
        node2: str,
        value_ohm: float,
        tc1: float | None = None,
        tc2: float | None = None,
    ) -> None:
        """添加电阻元件。

        Args:
            name: 元件名（不含前缀 R）。
            node1: 节点 1。
            node2: 节点 2。
            value_ohm: 电阻值 (Ω)。
            tc1: 一阶温度系数 (1/°C)，可选。
            tc2: 二阶温度系数 (1/°C²)，可选。

        Raises:
            ValueError: 名称/节点/值非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"电阻名非法 '{name}'"
            raise ValueError(msg)
        self._check_node(node1)
        self._check_node(node2)
        if value_ohm < 0:
            msg = f"电阻值必须 >= 0，得到 {value_ohm}"
            raise ValueError(msg)
        line = f"R{name} {node1} {node2} {value_ohm:.6g}"
        if tc1 is not None:
            line += f" tc1={tc1:.6g}"
        if tc2 is not None:
            line += f" tc2={tc2:.6g}"
        self._lines.append(line)
        self._nodes.add(node1)
        self._nodes.add(node2)

    def add_capacitor(
        self,
        name: str,
        node1: str,
        node2: str,
        value_f: float,
    ) -> None:
        """添加电容元件。

        Args:
            name: 元件名（不含前缀 C）。
            node1: 节点 1。
            node2: 节点 2。
            value_f: 电容值 (F)。

        Raises:
            ValueError: 名称/节点/值非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"电容名非法 '{name}'"
            raise ValueError(msg)
        self._check_node(node1)
        self._check_node(node2)
        if value_f < 0:
            msg = f"电容值必须 >= 0，得到 {value_f}"
            raise ValueError(msg)
        line = f"C{name} {node1} {node2} {value_f:.6g}"
        self._lines.append(line)
        self._nodes.add(node1)
        self._nodes.add(node2)

    def add_inductor(
        self,
        name: str,
        node1: str,
        node2: str,
        value_h: float,
    ) -> None:
        """添加电感元件。

        Args:
            name: 元件名（不含前缀 L）。
            node1: 节点 1。
            node2: 节点 2。
            value_h: 电感值 (H)。

        Raises:
            ValueError: 名称/节点/值非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"电感名非法 '{name}'"
            raise ValueError(msg)
        self._check_node(node1)
        self._check_node(node2)
        if value_h < 0:
            msg = f"电感值必须 >= 0，得到 {value_h}"
            raise ValueError(msg)
        line = f"L{name} {node1} {node2} {value_h:.6g}"
        self._lines.append(line)
        self._nodes.add(node1)
        self._nodes.add(node2)

    def add_mutual(
        self,
        name: str,
        inductor1: str,
        inductor2: str,
        coupling: float,
    ) -> None:
        """添加互感耦合（K 元件）。

        K = M / sqrt(L1·L2)，取值范围 [0, 1]。

        Args:
            name: 元件名（不含前缀 K）。
            inductor1: 第一个电感元件名（不含前缀 L）。
            inductor2: 第二个电感元件名（不含前缀 L）。
            coupling: 耦合系数 K，范围 [0, 1]。

        Raises:
            ValueError: 名称/耦合系数非法时告警退出。
        """
        if not name or not name.replace("_", "").isalnum():
            msg = f"互感名非法 '{name}'"
            raise ValueError(msg)
        if not inductor1 or not inductor2:
            msg = "电感元件名不能为空"
            raise ValueError(msg)
        if coupling < 0 or coupling > 1:
            msg = f"耦合系数必须在 [0, 1]，得到 {coupling}"
            raise ValueError(msg)
        line = f"K{name} L{inductor1} L{inductor2} {coupling:.6g}"
        self._lines.append(line)

    def add_pi_network(
        self,
        node1: str,
        node2: str,
        resistance_ohm: float,
        inductance_h: float,
        capacitance_f: float,
        tc1: float | None = None,
        tc2: float | None = None,
        suffix: str = "",
    ) -> None:
        """添加 π 型 RLC 寄生网络（串联 R+L，两端并联 C/2）。

        节点：node1 --[R+L]-- internal --[C/2]-- gnd
                                internal --[R+L]-- node2（这里简化为单段串联）
        实际布线：node1 --[R_series + L_series]-- node2，
                  node1 --[C/2]-- gnd，node2 --[C/2]-- gnd

        Args:
            node1: 端口 1 节点。
            node2: 端口 2 节点。
            resistance_ohm: 串联电阻 (Ω)。
            inductance_h: 串联电感 (H)。
            capacitance_f: 总电容 (F)，每端 C/2。
            tc1: 电阻一阶温度系数 (1/°C)，可选。
            tc2: 电阻二阶温度系数 (1/°C²)，可选。
            suffix: 元件名后缀，避免重名。

        Raises:
            ValueError: 参数非法时告警退出。
        """
        self._check_node(node1)
        self._check_node(node2)
        if resistance_ohm < 0 or inductance_h < 0 or capacitance_f < 0:
            msg = (
                f"R/L/C 必须 >= 0，得到 R={resistance_ohm}, "
                f"L={inductance_h}, C={capacitance_f}"
            )
            raise ValueError(msg)
        # 串联 R + L
        if resistance_ohm > 0:
            self.add_resistor(
                f"rs{suffix}", node1, node2, resistance_ohm, tc1, tc2
            )
        if inductance_h > 0:
            self.add_inductor(f"ls{suffix}", node1, node2, inductance_h)
        # 两端并联 C/2
        if capacitance_f > 0:
            half_c = capacitance_f / 2.0
            self.add_capacitor(f"cp1{suffix}", node1, "0", half_c)
            self.add_capacitor(f"cp2{suffix}", node2, "0", half_c)

    def to_string(self, ports: list[str] | None = None) -> str:
        """生成完整 SPICE 子电路网表字符串。

        Args:
            ports: 子电路端口节点列表，默认使用所有已添加节点的字母序首个+末个。

        Returns:
            SPICE 网表字符串。

        Raises:
            ValueError: 端口非法时告警退出。
        """
        if ports is None:
            if not self._nodes:
                msg = "网表为空，未添加任何元件"
                raise ValueError(msg)
            sorted_nodes = sorted(self._nodes)
            if "0" in sorted_nodes:
                # 去除地节点
                non_gnd = [n for n in sorted_nodes if n != "0"]
                if len(non_gnd) >= 2:
                    ports = [non_gnd[0], non_gnd[-1]]
                elif len(non_gnd) == 1:
                    ports = [non_gnd[0], "0"]
                else:
                    ports = ["0"]
            else:
                ports = [sorted_nodes[0], sorted_nodes[-1]] if len(sorted_nodes) >= 2 else sorted_nodes
        if not ports:
            msg = "端口列表不能为空"
            raise ValueError(msg)
        for p in ports:
            self._check_node(p)
        header = f".SUBCKT {self.subckt_name} {' '.join(ports)}"
        body = "\n".join(self._lines)
        footer = ".ENDS"
        return f"{header}\n{body}\n{footer}\n"

    def reset(self) -> None:
        """清空已添加的元件与节点。"""
        self._lines = []
        self._nodes = set()


# =============================================================================
# 一站式寄生提取器：综合 R231-R235
# =============================================================================
@dataclass
class AdvancedParasiticExtractor:
    """一站式寄生提取器：综合 R231-R235，输出 RLC + S 参数 + SPICE 网表。

    工作流：
        1. extract_resistance (R231) → R + 温度系数
        2. extract_capacitance (R232) → C_pp + C_fringe + C_coupling
        3. extract_inductance (R233) → L_self + M_mutual
        4. compute_s_params (R234) → 频域 S 参数
        5. write_spice_netlist (R235) → .subckt 文本

    来源（≥5 文献 URL）见各组件类 docstring。
    """

    resistor: ParasiticResistor = field(default_factory=lambda: ParasiticResistor(0.05))
    capacitor: ParasiticCapacitor = field(
        default_factory=lambda: ParasiticCapacitor(eps_r=3.9, metal_thickness_um=0.5, dielectric_thickness_um=1.0)
    )
    inductor: ParasiticInductor = field(
        default_factory=lambda: ParasiticInductor(metal_thickness_um=0.5)
    )

    def extract_all(
        self,
        length_um: float,
        width_um: float,
        temperature_c: float | None = None,
    ) -> dict[str, object]:
        """一次性提取 R/L/C 寄生参数。

        Args:
            length_um: 导线长度 (μm)。
            width_um: 导线宽度 (μm)。
            temperature_c: 工作温度 (°C)，可选。

        Returns:
            {"resistance": dict, "capacitance": dict, "inductance": dict}

        Raises:
            ValueError: 几何参数非法时告警退出。
        """
        return {
            "resistance": self.resistor.extract(length_um, width_um, temperature_c),
            "capacitance": self.capacitor.extract_self(length_um, width_um),
            "inductance": self.inductor.extract_self(length_um, width_um),
        }

    def compute_s_params(
        self,
        frequencies_ghz: NDArray[np.float64] | list[float],
        resistance_ohm: float,
        inductance_ph: float,
        capacitance_ff: float,
        z0_ohm: float = 50.0,
    ) -> NDArray[np.complex128]:
        """计算 S 参数（委托 ParasiticSParam）。"""
        return ParasiticSParam.compute_s_params(
            frequencies_ghz, resistance_ohm, inductance_ph, capacitance_ff, z0_ohm
        )

    def write_spice_netlist(
        self,
        node1: str,
        node2: str,
        resistance_ohm: float,
        inductance_h: float,
        capacitance_f: float,
        tc1: float | None = None,
        tc2: float | None = None,
        subckt_name: str = "parasitic_net",
    ) -> str:
        """生成 SPICE 子电路网表。

        Args:
            node1: 端口 1 节点。
            node2: 端口 2 节点。
            resistance_ohm: 串联电阻 (Ω)。
            inductance_h: 串联电感 (H)。
            capacitance_f: 总电容 (F)。
            tc1: 电阻一阶温度系数 (1/°C)，可选。
            tc2: 电阻二阶温度系数 (1/°C²)，可选。
            subckt_name: 子电路名。

        Returns:
            SPICE 网表字符串。
        """
        writer = SpiceNetlistWriter(subckt_name=subckt_name)
        writer.add_pi_network(
            node1, node2, resistance_ohm, inductance_h, capacitance_f, tc1, tc2
        )
        return writer.to_string(ports=[node1, node2])
