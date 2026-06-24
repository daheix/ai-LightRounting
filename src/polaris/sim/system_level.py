"""R14 路标：VPIphotonics 系统级光子电路仿真（频域+时域混合框架）。

对齐 VPIcomponentMaker Photonic Circuits 核心架构：
"无源子电路用频域 S-matrix 精确建模，时域仅处理有源接口"。

核心组件: SignalFlowGraph(Mason)/TLLMLaser(RK4)/TimeDomainSimulator/
HybridSimulator(FFT)/OpticalLink(NRZ,PAM4,QAM16)/BerEvaluator(Q-factor)/
to_time_domain【创新】。

来源:
- Mason, Proc. IRE 44(7), 920-926 (1956) https://ieeexplore.ieee.org/document/4052034
- Lowery et al., IEE Proc. J 134(5), 281-289 (1987) https://digital-library.theiet.org/
- Mingaleev et al., SPIE 9516, 951602 (2015)
  https://mingaleev.nanoscience.by/papers/pdf/SPIE_2015_9516_951602.pdf
- VPIphotonics 白皮书 https://www.vpiphotonics.com/Tools/PhotonicCircuits/
- ITU-T G.977 https://www.itu.int/rec/T-REC-G.977
- Oppenheim & Willsky, Signals and Systems, 2nd ed., §3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from polaris.sim.types import SDict


@dataclass
class SignalFlowGraph:
    """信号流图（Mason 增益公式计算系统传递函数）。

    H = sum(P_k * Delta_k) / Delta
    Delta = 1 - sum(L_i) + sum(L_i*L_j) - sum(L_i*L_j*L_k) + ...

    来源: Mason, "Feedback Theory: Further Properties of Signal Flow Graphs",
    Proc. IRE 44(7), 920-926 (1956).
    """

    nodes: set[str] = field(default_factory=set)
    edges: dict[tuple[str, str], complex] = field(default_factory=dict)

    def add_edge(self, src: str, dst: str, gain: complex) -> None:
        """添加有向边 src→dst，增益为 gain。"""
        self.nodes.add(src)
        self.nodes.add(dst)
        self.edges[(src, dst)] = gain

    def _successors(self, node: str) -> list[tuple[str, complex]]:
        """返回 node 的所有后继节点及增益。"""
        return [(dst, g) for (src, dst), g in self.edges.items() if src == node]

    def _find_forward_paths(self, start: str, end: str) -> list[list[str]]:
        """DFS 找所有从 start 到 end 的前向路径（节点不重复）。"""
        paths: list[list[str]] = []
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if node == end and len(path) > 1:
                paths.append(path)
                continue
            for dst, _ in self._successors(node):
                if dst not in path:
                    stack.append((dst, path + [dst]))
        if not paths:
            msg = f"无前向路径: {start} → {end}"
            raise ValueError(msg)
        return paths

    def _find_loops(self) -> list[list[str]]:
        """找所有自环（起点=终点，中间节点不重复）。"""
        loops: list[list[str]] = []
        for start in self.nodes:
            stack: list[tuple[str, list[str]]] = [(start, [start])]
            while stack:
                node, path = stack.pop()
                for dst, _ in self._successors(node):
                    if dst == start and len(path) >= 1:
                        loops.append(path + [dst])
                    elif dst not in path:
                        stack.append((dst, path + [dst]))
        # 去重（同一环路不同起点视为相同）
        unique: list[list[str]] = []
        seen: set[frozenset] = set()
        for loop in loops:
            key = frozenset(loop[:-1])
            if key not in seen and len(key) == len(loop) - 1:
                seen.add(key)
                unique.append(loop)
        return unique

    def _path_gain(self, path: list[str]) -> complex:
        """计算路径增益（各边增益乘积）。"""
        gain: complex = 1.0 + 0.0j
        for i in range(len(path) - 1):
            gain *= self.edges[(path[i], path[i + 1])]
        return gain

    def _loop_nodes(self, loop: list[str]) -> set[str]:
        """返回环路包含的节点集合（不含重复的终点）。"""
        return set(loop[:-1])

    def _graph_determinant(self, exclude_nodes: set[str] | None = None) -> complex:
        """计算图行列式 Δ（排除指定节点后的子图）。

        Δ = 1 - ΣL_i + ΣL_iL_j - ΣL_iL_jL_k + ...（仅非接触环路组合）
        """
        exclude = exclude_nodes or set()
        all_loops = self._find_loops()
        valid_loops = [lp for lp in all_loops if not (self._loop_nodes(lp) & exclude)]
        if not valid_loops:
            return 1.0 + 0.0j
        gains = [self._path_gain(lp) for lp in valid_loops]
        node_sets = [self._loop_nodes(lp) for lp in valid_loops]
        delta: complex = 1.0 + 0.0j
        n = len(valid_loops)
        for order in range(1, n + 1):
            sign = (-1) ** order
            total: complex = 0.0 + 0.0j
            for combo in combinations(range(n), order):
                all_nodes: set[str] = set()
                ok = True
                for idx in combo:
                    if all_nodes & node_sets[idx]:
                        ok = False
                        break
                    all_nodes |= node_sets[idx]
                if ok:
                    prod: complex = 1.0 + 0.0j
                    for idx in combo:
                        prod *= gains[idx]
                    total += prod
            delta += sign * total
        return delta

    def transfer_function(self, input_node: str, output_node: str) -> complex:
        """用 Mason 增益公式计算 input→output 的传递函数。

        Raises:
            ValueError: 无前向路径或图行列式奇异时告警退出（禁止 fall-back）。
        """
        forward_paths = self._find_forward_paths(input_node, output_node)
        delta = self._graph_determinant()
        if abs(delta) < 1e-15:
            msg = f"图行列式 Δ≈0，系统奇异（input={input_node}, output={output_node})"
            raise ValueError(msg)
        numerator: complex = 0.0 + 0.0j
        for path in forward_paths:
            p_k = self._path_gain(path)
            delta_k = self._graph_determinant(exclude_nodes=set(path))
            numerator += p_k * delta_k
        return numerator / delta


@dataclass
class TLLMLaser:
    """TLLM 激光器模型（Lowery 1987 速率方程，RK4 积分）。

    dN/dt = I/(qV) - N/tau_n - v_g*G(N)*S
    dS/dt = Gamma*v_g*G(N)*S - S/tau_p + beta*N/tau_n

    默认参数为典型 InGaAsP 激光器值（R14.md §3.2）。

    来源: Lowery et al., "Transmission-line laser model",
    IEE Proc. J 134(5), 281-289 (1987).
    """

    I: float = 0.05  # 注入电流 (A)  # noqa: E741
    q: float = 1.6e-19  # 电子电荷 (C)
    V: float = 1e-10  # 有源区体积 (cm^3)
    tau_n: float = 1e-9  # 载流子寿命 (s)
    tau_p: float = 1e-12  # 光子寿命 (s)
    v_g: float = 7.5e9  # 群速度 (cm/s)
    a: float = 2e-16  # 增益系数 (cm^2)
    N_0: float = 1.5e18  # 透明载流子浓度 (cm^-3)
    Gamma: float = 0.3  # 限制因子
    beta: float = 1e-5  # 自发辐射因子

    def gain(self, N: float) -> float:
        """增益函数 G(N) = a*(N - N_0)。"""
        return self.a * (N - self.N_0)

    def _derivatives(self, N: float, S: float, I: float) -> tuple[float, float]:  # noqa: E741
        """计算速率方程右端项。"""
        G = self.gain(N)
        dN = I / (self.q * self.V) - N / self.tau_n - self.v_g * G * S
        dS = self.Gamma * self.v_g * G * S - S / self.tau_p + self.beta * N / self.tau_n
        return dN, dS

    def step(self, N: float, S: float, dt: float) -> tuple[float, float]:
        """单步 RK4 积分速率方程。

        Raises:
            RuntimeError: 数值不稳定（非有限或负值）时告警退出（禁止 fall-back）。
        """
        I = self.I  # noqa: E741
        k1n, k1s = self._derivatives(N, S, I)
        k2n, k2s = self._derivatives(N + 0.5 * dt * k1n, S + 0.5 * dt * k1s, I)
        k3n, k3s = self._derivatives(N + 0.5 * dt * k2n, S + 0.5 * dt * k2s, I)
        k4n, k4s = self._derivatives(N + dt * k3n, S + dt * k3s, I)
        N_new = N + dt / 6.0 * (k1n + 2 * k2n + 2 * k3n + k4n)
        S_new = S + dt / 6.0 * (k1s + 2 * k2s + 2 * k3s + k4s)
        if not (np.isfinite(N_new) and np.isfinite(S_new)):
            msg = f"TLLM 数值不稳定: N={N_new}, S={S_new}（非有限值）"
            raise RuntimeError(msg)
        if N_new < 0 or S_new < 0:
            msg = f"TLLM 数值不稳定: N={N_new}, S={S_new}（负值，dt={dt} 过大）"
            raise RuntimeError(msg)
        return N_new, S_new


class TimeDomainSimulator:
    """时域仿真器（TLLM 风格）。

    对激光器进行瞬态仿真，记录 N(t)、S(t)、P_out(t)。
    输出功率 P_out ∝ S（简化模型）。

    来源: VPIphotonics 白皮书; Lowery 1987.
    """

    def __init__(self, dt: float = 1e-12, n_steps: int = 10000):
        """初始化时域仿真器。

        Args:
            dt: 时间步长 (s)，需满足 Nyquist 采样。
            n_steps: 仿真步数。
        """
        self.dt = dt
        self.n_steps = n_steps

    def simulate_laser(self, laser: TLLMLaser, I_drive: np.ndarray) -> dict:
        """仿真激光器瞬态响应。

        Args:
            laser: TLLM 激光器模型。
            I_drive: 注入电流波形 (A)，长度为 n_steps。

        Returns:
            {"t": np.ndarray, "N": np.ndarray, "S": np.ndarray, "P_out": np.ndarray}

        Raises:
            ValueError: I_drive 长度与 n_steps 不匹配时告警退出。
        """
        if len(I_drive) != self.n_steps:
            msg = f"I_drive 长度 {len(I_drive)} != n_steps {self.n_steps}"
            raise ValueError(msg)
        t = np.arange(self.n_steps) * self.dt
        N_arr = np.zeros(self.n_steps)
        S_arr = np.zeros(self.n_steps)
        N = laser.N_0 * 1.1  # 初始载流子浓度略高于透明值
        S = 1e-3  # 自发辐射种子
        for k in range(self.n_steps):
            laser.I = float(I_drive[k])
            N, S = laser.step(N, S, self.dt)
            N_arr[k] = N
            S_arr[k] = S
        P_out = 1e-5 * S_arr  # 输出功率 P_out ∝ S
        return {"t": t, "N": N_arr, "S": S_arr, "P_out": P_out}


class HybridSimulator:
    """频域-时域混合仿真器（VPI 风格）。

    无源子电路用频域 S-matrix，有源器件用 TLLM 时域。
    通过 FFT/IFFT 耦合：
        a_active(t) = IFFT{ S_passive(ω) · FFT{ b_active(t) } }

    来源: Mingaleev 2015 SPIE 951602; VPIphotonics 白皮书.
    """

    def __init__(self, freq_sdict: SDict, time_device: TLLMLaser):
        """初始化混合仿真器。

        Args:
            freq_sdict: 无源子电路频域 S 参数。
            time_device: 有源器件（TLLM 激光器）。
        """
        self.freq_sdict = freq_sdict
        self.time_device = time_device

    def run(self, input_signal: np.ndarray, dt: float) -> np.ndarray:
        """混合仿真：input_signal → 频域 S → IFFT → 时域器件 → 输出。

        Raises:
            ValueError: 频域 S 参数为空时告警退出。
        """
        if not self.freq_sdict:
            msg = "频域 S 参数为空，无法进行混合仿真"
            raise ValueError(msg)
        n = len(input_signal)
        key = next(iter(self.freq_sdict.keys()))
        s_freq = np.asarray(self.freq_sdict[key], dtype=complex)
        if len(s_freq) != n:
            # 频域重采样到信号长度
            x_old = np.linspace(0, 1, len(s_freq))
            x_new = np.linspace(0, 1, n)
            s_freq = np.interp(x_new, x_old, s_freq.real) + 1j * np.interp(
                x_new, x_old, s_freq.imag
            )
        # FFT → 频域相乘 → IFFT
        spectrum_in = np.fft.fft(input_signal)
        spectrum_out = spectrum_in * s_freq
        time_signal = np.fft.ifft(spectrum_out).real
        # 时域器件处理：激光器增益调制
        N = self.time_device.N_0 * 1.1
        S = 1e-3
        output = np.zeros(n)
        for k in range(n):
            self.time_device.I = abs(time_signal[k]) * 0.1 + 0.05
            N, S = self.time_device.step(N, S, dt)
            output[k] = time_signal[k] * (1.0 + 1e-3 * S)
        return output


@dataclass
class OpticalLink:
    """光通信链路（发射机→光纤→接收机）。支持 NRZ/PAM4/QAM16 调制。
    来源: VPIphotonics 系统级仿真."""

    tx_modulation: str  # "NRZ" / "PAM4" / "QAM16"
    bit_rate: float = 10e9  # bit/s
    fiber_length: float = 1e3  # m
    fiber_loss: float = 0.2  # dB/km
    laser_power: float = 0.0  # dBm
    samples_per_bit: int = 16
    noise_sigma: float = 0.05  # 接收机噪声标准差

    def __post_init__(self) -> None:
        """校验调制格式。"""
        if self.tx_modulation not in ("NRZ", "PAM4", "QAM16"):
            msg = f"未知调制格式: {self.tx_modulation}（支持 NRZ/PAM4/QAM16）"
            raise ValueError(msg)

    def generate_bits(self, n_bits: int) -> np.ndarray:
        """随机生成比特序列（固定种子保证可复现）。"""
        rng = np.random.default_rng(seed=42)
        return rng.integers(0, 2, size=n_bits).astype(np.int8)

    def modulate(self, bits: np.ndarray) -> np.ndarray:
        """将比特序列调制为电平信号并上采样。

        NRZ: 1 bit/symbol, 电平 {0, 1}
        PAM4: 2 bit/symbol, 电平 {-3, -1, +1, +3}
        QAM16: 4 bit/symbol, 取实部传输
        """
        if self.tx_modulation == "NRZ":
            symbols = bits.astype(float)
        elif self.tx_modulation == "PAM4":
            b = np.append(bits, 0) if len(bits) % 2 != 0 else bits
            pairs = b.reshape(-1, 2)
            symbols = 2 * (2 * pairs[:, 0] + pairs[:, 1]) - 3  # -3,-1,+1,+3
        else:  # QAM16
            pad = (4 - len(bits) % 4) % 4
            b = np.append(bits, np.zeros(pad)) if pad else bits
            quads = b.reshape(-1, 4)
            real_idx = 2 * quads[:, 0] + quads[:, 1]
            symbols = 2 * real_idx - 3  # 取实部
        return np.repeat(symbols, self.samples_per_bit)

    def transmit(self, signal: np.ndarray) -> np.ndarray:
        """光纤传输：施加损耗 + 加性高斯噪声。"""
        total_loss_db = self.fiber_loss * (self.fiber_length / 1e3)
        gain_linear = 10 ** (-total_loss_db / 20)
        rng = np.random.default_rng(seed=123)
        noise = rng.normal(0, self.noise_sigma, size=len(signal))
        return signal * gain_linear + noise

    def receive(self, signal: np.ndarray) -> np.ndarray:
        """接收机判决：下采样 + 阈值判决。"""
        n_symbols = len(signal) // self.samples_per_bit
        sampled = signal[: n_symbols * self.samples_per_bit].reshape(n_symbols, -1).mean(axis=1)
        levels = np.array([-3, -1, 1, 3])
        if self.tx_modulation == "NRZ":
            return (sampled > 0.5).astype(np.int8)
        idx = np.argmin(np.abs(sampled[:, None] - levels[None, :]), axis=1)
        return idx.astype(np.int8)

    def ber(self, tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
        """计算误码率 BER。

        Raises:
            ValueError: 比特序列为空时告警退出。
        """
        n = min(len(tx_bits), len(rx_bits))
        if n == 0:
            msg = "比特序列为空，无法计算 BER"
            raise ValueError(msg)
        errors = np.sum(tx_bits[:n] != rx_bits[:n])
        return float(errors) / n


class BerEvaluator:
    """BER 评估器（Q-factor 法）。来源: ITU-T G.977."""

    @staticmethod
    def q_factor(eye_signal: np.ndarray) -> float:
        """从眼图信号计算 Q-factor = |μ1 - μ0| / (σ1 + σ0)。

        Raises:
            ValueError: 样本不足或分母为零时告警退出。
        """
        if len(eye_signal) < 4:
            msg = f"眼图样本不足: {len(eye_signal)} < 4"
            raise ValueError(msg)
        median = np.median(eye_signal)
        high = eye_signal[eye_signal > median]
        low = eye_signal[eye_signal <= median]
        if len(high) < 2 or len(low) < 2:
            msg = "眼图高低电平样本不足，无法计算 Q-factor"
            raise ValueError(msg)
        mu1, sigma1 = float(np.mean(high)), float(np.std(high))
        mu0, sigma0 = float(np.mean(low)), float(np.std(low))
        denom = sigma1 + sigma0
        if denom < 1e-15:
            msg = f"σ1+σ0≈0，Q-factor 奇异（sigma1={sigma1}, sigma0={sigma0}）"
            raise ValueError(msg)
        return abs(mu1 - mu0) / denom

    @staticmethod
    def ber_from_q(q: float) -> float:
        """从 Q-factor 计算 BER: BER = 0.5 * erfc(Q / sqrt(2))。

        来源: ITU-T G.977.
        """
        from scipy.special import erfc

        return 0.5 * float(erfc(q / np.sqrt(2.0)))

    @staticmethod
    def osnr_to_ber(osnr_db: float, bit_rate: float, bandwidth: float) -> float:
        """OSNR → BER 转换（高斯近似，ITU-T G.977 附录）。

        Q ≈ 2 * sqrt(OSNR_linear * bandwidth / bit_rate)

        Raises:
            ValueError: OSNR 非正时告警退出。
        """
        if osnr_db <= 0:
            msg = f"OSNR 必须为正: osnr_db={osnr_db}"
            raise ValueError(msg)
        osnr_linear = 10 ** (osnr_db / 10.0)
        q = 2.0 * np.sqrt(osnr_linear * bandwidth / bit_rate)
        return BerEvaluator.ber_from_q(float(q))


def to_time_domain(sdict: SDict, wavelengths: np.ndarray, t_array: np.ndarray) -> dict:
    """【创新】频域 S 参数 → 时域脉冲响应一键转换。

    将频域 S(λ) 通过 IFFT 转换为时域脉冲响应 h(t)。
    波长 λ 转换为频率 f = c/λ，再按频率均匀重采样后 IFFT。

    创新逻辑: VPI 需用户手动切换频域/时域，本函数提供一键转换 API，
    支持任意脉冲激励仿真。支持理论: LTI 频域-时域对偶（Oppenheim & Willsky §3）。
    案例预估: 10 Gb/s NRZ 通过 MZI 的时域响应，频域 1000 点 + IFFT < 100 ms。

    Args:
        sdict: 频域 S 参数字典，键为 (port_out, port_in)。
        wavelengths: 波长数组 (m)，长度需与 S 参数数组一致。
        t_array: 输出时间数组 (s)。

    Returns:
        字典 {port_pair: h_t_array}，时域脉冲响应。

    Raises:
        ValueError: 波长/时间数组长度不足或不匹配时告警退出。
    """
    c = 2.99792458e8  # 光速 (m/s)
    if len(wavelengths) < 2:
        msg = f"波长数组长度需 ≥ 2，当前 {len(wavelengths)}"
        raise ValueError(msg)
    freqs = c / np.asarray(wavelengths, dtype=float)
    sort_idx = np.argsort(freqs)
    freqs_sorted = freqs[sort_idx]
    n_t = len(t_array)
    if n_t < 2:
        msg = f"时间数组长度需 ≥ 2，当前 {n_t}"
        raise ValueError(msg)
    dt = float(t_array[1] - t_array[0])
    if dt <= 0:
        msg = f"时间步长需为正: dt={dt}"
        raise ValueError(msg)
    freq_uniform = np.fft.fftfreq(n_t, d=dt)
    result: dict[tuple[str, str], np.ndarray] = {}
    for key, s_vals in sdict.items():
        s_arr = np.asarray(s_vals, dtype=complex)
        if len(s_arr) != len(wavelengths):
            msg = f"S 参数 {key} 长度 {len(s_arr)} != 波长数组长度 {len(wavelengths)}"
            raise ValueError(msg)
        s_sorted = s_arr[sort_idx]
        s_uniform = np.interp(freq_uniform, freqs_sorted, s_sorted.real) + 1j * np.interp(
            freq_uniform, freqs_sorted, s_sorted.imag
        )
        result[key] = np.fft.ifft(s_uniform)
    return result
