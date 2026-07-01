"""R552"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R249"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Ste"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0>"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2,"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) ->"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = ["""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] ="""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0,"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.k"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.kron(I, Z), Z)
        return [zz12, zz23]


class BitFlipError:
    """比特翻转错误 X。"""

    def __init__(self, qubit:"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.kron(I, Z), Z)
        return [zz12, zz23]


class BitFlipError:
    """比特翻转错误 X。"""

    def __init__(self, qubit: int) -> None:
        if qubit not in (0, 1, 2):
            raise ValueError(f"qubit 须"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.kron(I, Z), Z)
        return [zz12, zz23]


class BitFlipError:
    """比特翻转错误 X。"""

    def __init__(self, qubit: int) -> None:
        if qubit not in (0, 1, 2):
            raise ValueError(f"qubit 须 0/1/2，实际 {qubit}")
"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.kron(I, Z), Z)
        return [zz12, zz23]


class BitFlipError:
    """比特翻转错误 X。"""

    def __init__(self, qubit: int) -> None:
        if qubit not in (0, 1, 2):
            raise ValueError(f"qubit 须 0/1/2，实际 {qubit}")
        self.qubit = qubit

    def apply(self, state: np.ndarray) -> np.ndarray:
        """应用 X 门到指定量子"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.kron(I, Z), Z)
        return [zz12, zz23]


class BitFlipError:
    """比特翻转错误 X。"""

    def __init__(self, qubit: int) -> None:
        if qubit not in (0, 1, 2):
            raise ValueError(f"qubit 须 0/1/2，实际 {qubit}")
        self.qubit = qubit

    def apply(self, state: np.ndarray) -> np.ndarray:
        """应用 X 门到指定量子比特。"""
        I = np.eye(2, dtype=np.complex128)
        X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
        ops = [I, I, I]
