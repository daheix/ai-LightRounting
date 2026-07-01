"""R231 寄生电阻提取（片电阻 + 一阶/二阶温度系数 TC1/TC2）。

从 parasitic_advanced.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。对齐 Synopsys StarRC 电阻提取方法学。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Synopsys StarRC Datasheet（RLCK 模型，TC1/TC2）
   https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
2. Synopsys StarRC Resistance Extraction（RPSQ × L/W 片电阻公式）
   https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
3. StarRC TC1/TC2 温度系数提取配置
   https://wenku.csdn.net/answer/3t8nxpm1me
4. Banerjee ECE 225 UCSB（互连电阻温度系数建模）
   http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
5. SiEPIC EBeam PDK（波导金属接触片电阻典型值）
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 规则依据

R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["ParasiticResistor"]


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
