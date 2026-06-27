"""R32 路标：Ansys Lumerical INTERCONNECT 对齐（光链路系统仿真）。

提供 Lumerical INTERCONNECT 的光链路系统仿真能力，覆盖 PRBS 生成、
调制（NRZ/PAM4/QAM16）、ASE 噪声叠加、阈值检测、BER/眼图/OSNR 评估，
对标商业 INTERCONNECT 端到端链路仿真流程。

## 学术依据

- Ansys Lumerical INTERCONNECT: https://www.ansys.com/products/optics/interconnect
- Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010
  - §4.5 OSNR / ASE 噪声
  - §4.6 直接检测与 BER
  - §4.7 眼图分析
- ITU-T O.150 标准（PRBS7 多项式 x^7 + x^6 + 1）
  URL: https://www.itu.int/rec/T-REC-O.150

## 🚫不参与 GPU（R04）

纯 NumPy 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class INTERCONNECTConfig:
    """Lumerical INTERCONNECT 配置。

    学术依据：Ansys Lumerical INTERCONNECT
    URL: https://www.ansys.com/products/optics/interconnect

    Attributes:
        sample_rate: 采样率（Hz）。
        bit_rate: 比特率（bps）。
        n_bits: 仿真比特数。
        modulation: 调制格式（"NRZ"/"PAM4"/"QAM16"）。
    """

    sample_rate: float = 1e12
    bit_rate: float = 10e9
    n_bits: int = 128
    modulation: str = "NRZ"


class INTERCONNECTSimulator:
    """Lumerical INTERCONNECT 对齐（光链路系统仿真）。

    学术依据：
    - Ansys Lumerical INTERCONNECT 官方文档
      https://www.ansys.com/products/optics/interconnect
    - Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010

    特性：
    - 时域波形仿真（PRBS + 调制 + 噪声 + 检测）
    - 眼图分析
    - BER 评估
    - OSNR 分析
    """

    def __init__(self, config: INTERCONNECTConfig) -> None:
        """初始化 INTERCONNECT 仿真器。

        Args:
            config: INTERCONNECT 配置。
        """
        self.config = config
        self.sample_rate = config.sample_rate
        self.bit_rate = config.bit_rate
        self.n_bits = config.n_bits
        self.modulation = config.modulation
        self.spp = int(self.sample_rate / self.bit_rate)  # 每比特采样点数

    def generate_prbs(self, n_bits: int) -> np.ndarray:
        """生成 PRBS 伪随机比特序列（LFSR 实现）。

        学术依据：ITU-T O.150 标准，PRBS7 多项式 x^7 + x^6 + 1
        URL: https://www.itu.int/rec/T-REC-O.150

        Args:
            n_bits: 比特数。

        Returns:
            比特数组（0/1）。
        """
        # PRBS7：7 级 LFSR，反馈多项式 x^7 + x^6 + 1
        register = np.array([1, 0, 1, 0, 1, 0, 1], dtype=np.uint8)  # 初始种子
        bits = np.zeros(n_bits, dtype=np.uint8)
        for i in range(n_bits):
            bits[i] = register[0]
            # 反馈：bit0 XOR bit6
            feedback = register[0] ^ register[6]
            register = np.roll(register, -1)
            register[-1] = feedback
        return bits

    def modulate(self, bits: np.ndarray, modulation: str = "NRZ") -> np.ndarray:
        """调制（NRZ/PAM4/QAM16）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010

        Args:
            bits: 比特数组。
            modulation: 调制格式。

        Returns:
            调制信号波形。
        """
        bits = np.asarray(bits, dtype=np.float64)
        spp = self.spp
        if modulation == "NRZ":
            # NRZ：bit 0 → -1, bit 1 → +1
            symbols = 2.0 * bits - 1.0
            signal = np.repeat(symbols, spp)
        elif modulation == "PAM4":
            # PAM4：2 bits → 4 levels {-3, -1, +1, +3}
            n_symbols = len(bits) // 2
            symbols = np.zeros(n_symbols)
            for i in range(n_symbols):
                val = bits[2 * i] * 2 + bits[2 * i + 1]
                symbols[i] = 2.0 * val - 3.0
            signal = np.repeat(symbols, spp)
        elif modulation == "QAM16":
            # QAM16：4 bits → 16 QAM（实部 + 虚部）
            n_symbols = len(bits) // 4
            symbols = np.zeros(n_symbols, dtype=complex)
            for i in range(n_symbols):
                re = 2.0 * (bits[4 * i] * 2 + bits[4 * i + 1]) - 3.0
                im = 2.0 * (bits[4 * i + 2] * 2 + bits[4 * i + 3]) - 3.0
                symbols[i] = re + 1.0j * im
            signal = np.repeat(symbols, spp)
        else:
            raise ValueError(f"不支持的调制格式: {modulation}")
        return signal

    def add_noise(self, signal: np.ndarray, osnr: float) -> np.ndarray:
        """添加 ASE 噪声（给定 OSNR）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.5
        OSNR = P_signal / P_noise（线性），噪声为高斯白噪声。

        Args:
            signal: 信号波形。
            osnr: 光信噪比（线性，非 dB）。

        Returns:
            含噪信号。
        """
        signal = np.asarray(signal, dtype=np.float64)
        signal_power = np.mean(np.abs(signal) ** 2)
        noise_power = signal_power / max(osnr, 1e-15)
        rng = np.random.default_rng(42)
        if np.iscomplexobj(signal):
            noise = rng.normal(0, np.sqrt(noise_power / 2), signal.shape) + 1.0j * rng.normal(
                0, np.sqrt(noise_power / 2), signal.shape
            )
        else:
            noise = rng.normal(0, np.sqrt(noise_power), signal.shape)
        return signal + noise

    def detect(self, signal: np.ndarray) -> np.ndarray:
        """检测（阈值判决）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.6

        Args:
            signal: 接收信号波形。

        Returns:
            检测比特数组（0/1）。
        """
        signal = np.asarray(signal, dtype=np.float64)
        spp = self.spp
        n_bits = len(signal) // spp
        bits = np.zeros(n_bits, dtype=np.uint8)
        for i in range(n_bits):
            # 在每比特中间采样
            sample = signal[i * spp + spp // 2]
            # 阈值判决（0 阈值，适用于 NRZ）
            bits[i] = 1 if sample.real > 0 else 0
        return bits

    def compute_ber(self, tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
        """计算 BER（误比特率）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.6

        Args:
            tx_bits: 发送比特。
            rx_bits: 接收比特。

        Returns:
            BER 值。
        """
        tx = np.asarray(tx_bits)
        rx = np.asarray(rx_bits)
        n = min(len(tx), len(rx))
        if n == 0:
            return 0.5
        errors = np.sum(tx[:n] != rx[:n])
        return float(errors) / float(n)

    def compute_eye_diagram(self, signal: np.ndarray, n_bits: int) -> dict:
        """计算眼图。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.7
        将信号按比特周期折叠，计算眼图开口、眼高、眼宽。

        Args:
            signal: 信号波形。
            n_bits: 比特数。

        Returns:
            包含 eye_data/eye_height/eye_width 的字典。
        """
        signal = np.asarray(signal, dtype=np.float64)
        spp = self.spp
        n_bits = min(n_bits, len(signal) // spp)
        # 按比特周期折叠
        eye_data = np.zeros((n_bits, spp))
        for i in range(n_bits):
            eye_data[i, :] = signal[i * spp : (i + 1) * spp]
        # 眼高：最大值与最小值之差
        eye_height = float(np.max(eye_data) - np.min(eye_data))
        # 眼宽：在阈值交叉点附近，信号过零的时间宽度
        threshold = np.mean(eye_data)
        crossings = []
        for i in range(n_bits):
            row = eye_data[i, :]
            for j in range(spp - 1):
                if (row[j] - threshold) * (row[j + 1] - threshold) < 0:
                    crossings.append(j)
        eye_width = float(np.std(crossings)) if len(crossings) > 1 else float(spp) / 2.0
        return {
            "eye_data": eye_data,
            "eye_height": eye_height,
            "eye_width": eye_width,
            "n_bits": n_bits,
        }

    def compute_osnr(self, signal: np.ndarray, noise: np.ndarray) -> float:
        """计算 OSNR（光信噪比）。

        学术依据：Agrawal, "Fiber-Optic Communication Systems", 4th ed., §4.5
        OSNR = P_signal / P_noise

        Args:
            signal: 信号波形。
            noise: 噪声波形。

        Returns:
            OSNR 值（线性）。
        """
        signal_power = float(np.mean(np.abs(np.asarray(signal)) ** 2))
        noise_power = float(np.mean(np.abs(np.asarray(noise)) ** 2))
        if noise_power < 1e-15:
            return 1e15
        return signal_power / noise_power

    def run_link_simulation(self, link_config: dict) -> dict:
        """运行完整光链路仿真。

        学术依据：Ansys Lumerical INTERCONNECT 端到端仿真流程
        URL: https://www.ansys.com/products/optics/interconnect

        流程：PRBS 生成 → 调制 → 添加噪声 → 检测 → BER/眼图/OSNR 评估

        Args:
            link_config: 链路配置（含 osnr/n_bits/modulation）。

        Returns:
            仿真结果字典。
        """
        osnr = link_config.get("osnr", 20.0)
        n_bits = link_config.get("n_bits", self.n_bits)
        modulation = link_config.get("modulation", self.modulation)
        # 1. 生成 PRBS
        tx_bits = self.generate_prbs(n_bits)
        # 2. 调制
        tx_signal = self.modulate(tx_bits, modulation)
        # 3. 添加噪声
        rx_signal = self.add_noise(tx_signal, osnr)
        # 4. 检测
        rx_bits = self.detect(rx_signal)
        # 5. 评估
        ber = self.compute_ber(tx_bits, rx_bits)
        eye = self.compute_eye_diagram(rx_signal, n_bits)
        # 噪声波形
        noise = rx_signal - tx_signal[: len(rx_signal)]
        osnr_measured = self.compute_osnr(tx_signal[: len(rx_signal)], noise)
        return {
            "tx_bits": tx_bits,
            "rx_bits": rx_bits,
            "ber": ber,
            "eye_diagram": eye,
            "osnr_target": osnr,
            "osnr_measured": osnr_measured,
            "modulation": modulation,
            "n_bits": n_bits,
        }
