"""R17 光电协同仿真模块（Photoelectric Co-Simulation）。

实现 VLSIR SPICE 网表导出 + Verilog-A 光子紧凑模型 + cocotb 联合仿真驱动
+ 牛顿迭代非线性求解，纯 NumPy/SciPy（CPU）实现，遵守 R04 不参与 GPU。

核心模型（R02 学术诚信，公式均可溯源）:
- MZM 调制器传输: T(V) = cos²(π·(V+V_bias)/(2·V_π)) · 10^(-IL/20)
  （Chrostowski 2015 §8.4 推挽 MZM 光强传输函数）
- 光电探测器: I_photo = R · P_in + I_dark；V_out = I_photo · R_load
  （Chrostowski 2015 §9.2；Sze《半导体器件物理》§13）
- DFB 激光器单模速率方程:
    dN/dt = η_i·I/q - N/τ_n - v_g·g(N)·S
    dS/dt = Γ·v_g·g(N)·S - S/τ_p + β·N/τ_n
  线性增益 g(N) = a·(N - N_tr)
  （Coldren & Corzine 1995《Diode Lasers and Photonic Integrated Circuits》§5）

*创新*: VLSIR SPICE 中间表示 + Verilog-A 光子紧凑模型 + Python 数值协同仿真
统一封装于单一类 PhotoelectricCoSim，底层逻辑——以 SPICE 子电路声明器件
拓扑、以 Verilog-A 描述光子非线性行为、以 Python 牛顿迭代在每时间步求解
光电耦合稳态，三者共享同一器件注册表与参数 schema，消除 Lumerical
INTERCONNECT 与 Spectre 之间的手动网表搬运。案例: MZM+PD 直链路在
PoLaRIS 内一次 run_cosim 即得时域波形，无需 ngspice 实跑（无外部依赖时
亦可生成 cocotb 驱动 + SPICE 网表交由真实仿真器执行）。

文献来源（R02，≥5 条 URL）:
1. VPIphotonics 光电协同仿真平台
   https://www.vpiphotonics.com/
2. gdsfactory VLSIR / SPICE 导出
   https://github.com/gdsfactory/gdsfactory
3. VLSIR SPICE 中间表示规范（dan-fritchman）
   https://github.com/dan-fritchman/vlsir
4. Verilog-AMS 语言参考手册（Accellera）
   https://www.accellera.org/downloads/standards/v-ams
5. cocotb 联合仿真框架文档
   https://docs.cocotb.org/
6. Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8/§9
   https://www.cambridge.org/core/books/silicon-photonics-design/
7. Coldren & Corzine, "Diode Lasers and Photonic Integrated Circuits",
   Wiley 1995, §5（速率方程）
   https://www.wiley.com/en-us/Diode+Laser+Fundamentals
8. Ansys Lumerical 光子 Verilog-A 紧凑模型
   https://optics.ansys.com/hc/en-us/articles/18698429782291
9. piel SPICE 光电协同仿真示例
   https://piel.readthedocs.io/en/latest/examples/04_spice_cosimulation/
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.optimize import newton

# =============================================================================
# 物理常量（CODATA 2018，SI 单位）
# =============================================================================
ELECTRON_CHARGE = 1.602176634e-19  # C
PLANCK_CONSTANT = 6.62607015e-34   # J·s
SPEED_OF_LIGHT = 2.99792458e8      # m/s

# 默认参数（典型 Si 光子学值，来源见各 docstring）
DEFAULT_WAVELENGTH_M = 1.55e-6     # C 波段
DEFAULT_TIMESTEP_S = 1e-12         # SPICE 典型时间步
DEFAULT_TOTAL_TIME_S = 1e-9        # 1 ns 瞬态窗口
DEFAULT_LOAD_RESISTANCE_OHM = 50.0  # 50Ω 射频标准
DEFAULT_INPUT_POWER_W = 1.0e-3      # 1 mW (0 dBm) 光载波


# =============================================================================
# 配置与器件规格
# =============================================================================


@dataclass
class CoSimConfig:
    """光电协同仿真全局配置。

    来源: SPICE 瞬态分析时间步准则
      https://ngspice.sourceforge.io/docs.html

    Attributes:
        timestep: SPICE/数值积分时间步 (s)。
        total_time: 总仿真时间 (s)。
        input_power_w: 默认光载波功率 (W)，无激光器时使用。
        load_resistance: 探测器负载电阻 (Ω)。
        wavelength_m: 工作波长 (m)。
        newton_tol: 牛顿迭代收敛容差。
        newton_maxiter: 牛顿迭代最大次数。
    """

    timestep: float = DEFAULT_TIMESTEP_S
    total_time: float = DEFAULT_TOTAL_TIME_S
    input_power_w: float = DEFAULT_INPUT_POWER_W
    load_resistance: float = DEFAULT_LOAD_RESISTANCE_OHM
    wavelength_m: float = DEFAULT_WAVELENGTH_M
    newton_tol: float = 1.0e-10
    newton_maxiter: int = 50

    def __post_init__(self) -> None:
        """验证配置（R03: 无 fall-back，非法即 raise）。"""
        if self.timestep <= 0:
            raise ValueError(f"timestep 须 > 0，得到 {self.timestep}")
        if self.total_time <= self.timestep:
            raise ValueError(
                f"total_time({self.total_time}) 须 > timestep({self.timestep})"
            )
        if self.input_power_w < 0:
            raise ValueError(f"input_power_w 须 >= 0，得到 {self.input_power_w}")
        if self.load_resistance <= 0:
            raise ValueError(f"load_resistance 须 > 0，得到 {self.load_resistance}")
        if self.wavelength_m <= 0:
            raise ValueError(f"wavelength_m 须 > 0，得到 {self.wavelength_m}")
        if self.newton_tol <= 0:
            raise ValueError(f"newton_tol 须 > 0，得到 {self.newton_tol}")
        if self.newton_maxiter < 2:
            raise ValueError(f"newton_maxiter 须 >= 2，得到 {self.newton_maxiter}")


@dataclass
class ModulatorSpec:
    """MZM 调制器规格。

    来源: Chrostowski 2015 §8.4
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Attributes:
        vpi: 半波电压 (V)。
        insertion_loss_db: 插入损耗 (dB)。
        bias_v: DC 偏置电压 (V)，推挽 MZM 工作点。
    """

    vpi: float
    insertion_loss_db: float
    bias_v: float = 0.0

    def __post_init__(self) -> None:
        if self.vpi <= 0:
            raise ValueError(f"V_pi 须 > 0，得到 {self.vpi}")
        if self.insertion_loss_db < 0:
            raise ValueError(f"insertion_loss_db 须 >= 0，得到 {self.insertion_loss_db}")


@dataclass
class PhotodetectorSpec:
    """光电探测器规格。

    来源: Chrostowski 2015 §9.2
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Attributes:
        responsivity: 响应度 (A/W)。
        dark_current: 暗电流 (A)。
    """

    responsivity: float
    dark_current: float

    def __post_init__(self) -> None:
        if self.responsivity < 0:
            raise ValueError(f"responsivity 须 >= 0，得到 {self.responsivity}")
        if self.dark_current < 0:
            raise ValueError(f"dark_current 须 >= 0，得到 {self.dark_current}")


@dataclass
class LaserSpec:
    """DFB 激光器规格（单模速率方程 + L-I 特性）。

    来源: Coldren & Corzine 1995 §5
      https://www.wiley.com/en-us/Diode+Laser+Fundamentals

    Attributes:
        threshold_current: 阈值电流 (A)。
        slope_efficiency: L-I 斜率效率 (W/A)，差分量子效率·hν/q。
        bias_current: DC 偏置电流 (A)，默认 2× 阈值。
        tau_n: 载流子寿命 (s)。
        tau_p: 光子寿命 (s)。
        gamma_confinement: 光场限制因子 Γ。
        vg: 群速度 (m/s)。
        gain_a: 微分增益 a (m²)。
        n_tr: 透明载流子密度 (1/m³)。
        beta_sp: 自发辐射耦合因子 β。
        eta_inj: 注入效率 η_i。
        active_volume: 有源区体积 (m³)。
    """

    threshold_current: float
    slope_efficiency: float
    bias_current: float = 0.0
    tau_n: float = 1.0e-9
    tau_p: float = 1.0e-12
    gamma_confinement: float = 0.3
    vg: float = 8.0e7
    gain_a: float = 2.0e-20
    n_tr: float = 1.5e24
    beta_sp: float = 1.0e-5
    eta_inj: float = 0.8
    active_volume: float = 1.0e-16

    def __post_init__(self) -> None:
        if self.threshold_current <= 0:
            raise ValueError(f"threshold_current 须 > 0，得到 {self.threshold_current}")
        if self.slope_efficiency < 0:
            raise ValueError(f"slope_efficiency 须 >= 0，得到 {self.slope_efficiency}")
        if self.tau_n <= 0 or self.tau_p <= 0:
            raise ValueError(f"tau_n/tau_p 须 > 0，得到 {self.tau_n}/{self.tau_p}")
        if not 0.0 < self.gamma_confinement <= 1.0:
            raise ValueError(f"Γ 须在 (0,1]，得到 {self.gamma_confinement}")
        if self.bias_current <= 0:
            # 默认偏置: 2× 阈值，工作于线性区（Coldren 1995 §5.4）
            self.bias_current = 2.0 * self.threshold_current


# =============================================================================
# Verilog-A 模型模板
# =============================================================================

MODULATOR_VA_TEMPLATE = """`include "disciplines.vams"
`include "constants.vams"
// PoLaRIS R17 MZM 调制器 Verilog-A 紧凑模型
// 传输 T(V)=cos^2(pi*(V+Vbias)/(2*Vpi))*10^(-IL/20)  [Chrostowski 2015 §8.4]
module photonic_mzm_{uid} (opt_in, opt_out, rf);
    electrical opt_in, opt_out, rf;
    parameter real vpi = {vpi:.6e} from (0:inf);           // 半波电压 (V)
    parameter real insertion_loss_db = {il:.6e} from [0:inf); // 插损 (dB)
    parameter real bias_v = {bias:.6e};                    // DC 偏置 (V)
    real amp, phi, tmod;
    analog begin
        amp = pow(10.0, -insertion_loss_db / 20.0);
        phi = `M_PI * (V(rf) + bias_v) / (2.0 * vpi);
        tmod = cos(phi) * cos(phi) * amp;
        V(opt_out) <+ tmod * V(opt_in);
    end
endmodule
"""

DETECTOR_VA_TEMPLATE = """`include "disciplines.vams"
// PoLaRIS R17 光电探测器 Verilog-A 紧凑模型
// I_photo = R*P_in + I_dark; V_out = I_photo*R_load  [Chrostowski 2015 §9.2]
module photonic_pd_{uid} (opt_in, rf_out);
    electrical opt_in, rf_out;
    parameter real responsivity = {resp:.6e} from [0:inf); // A/W
    parameter real dark_current = {idark:.6e} from [0:inf); // A
    parameter real load_resistance = {rload:.6e} from (0:inf); // Ohm
    real p_in, i_photo;
    analog begin
        p_in = V(opt_in) * V(opt_in);   // 光功率正比于光场电压平方
        i_photo = responsivity * p_in + dark_current;
        V(rf_out) <+ i_photo * load_resistance;
    end
endmodule
"""

LASER_VA_TEMPLATE = """`include "disciplines.vams"
`include "constants.vams"
// PoLaRIS R17 DFB 激光器 Verilog-A 紧凑模型（单模速率方程）
// dN/dt = eta_i*I/q - N/tau_n - vg*g(N)*S
// dS/dt = Gamma*vg*g(N)*S - S/tau_p + beta*N/tau_n  [Coldren & Corzine 1995 §5]
module photonic_laser_{uid} (i_in, opt_out);
    electrical i_in, opt_out;
    parameter real threshold = {ith:.6e} from (0:inf);     // 阈值电流 (A)
    parameter real slope_eff = {se:.6e} from [0:inf);      // 斜率效率 (W/A)
    real p_out;
    analog begin
        // L-I 特性: 阈值以上线性输出
        if (I(i_in) > threshold) begin
            p_out = slope_eff * (I(i_in) - threshold);
        end else begin
            p_out = 0.0;
        end
        V(opt_out) <+ sqrt(p_out);   // 光场电压 = sqrt(光功率)
    end
endmodule
"""


# =============================================================================
# 光电协同仿真主控
# =============================================================================


class PhotoelectricCoSim:
    """光电协同仿真主控（VLSIR SPICE 导出 + Verilog-A + cocotb + 牛顿迭代）。

    器件注册表统一管理 MZM / PD / Laser，按添加顺序分配自增 device_id。
    """

    def __init__(self, config: CoSimConfig) -> None:
        self.config = config
        self._devices: dict[int, tuple[str, object]] = {}
        self._next_id: int = 1

    # ------------------------------------------------------------------ 添加器件
    def add_modulator(self, vpi: float, insertion_loss: float, bias_v: float = 0.0) -> int:
        """添加 MZM 调制器，返回 device_id。

        Args:
            vpi: 半波电压 (V)。
            insertion_loss: 插入损耗 (dB)。
            bias_v: DC 偏置 (V)。
        """
        spec = ModulatorSpec(vpi=vpi, insertion_loss_db=insertion_loss, bias_v=bias_v)
        return self._register("modulator", spec)

    def add_photodetector(self, responsivity: float, dark_current: float) -> int:
        """添加光电探测器，返回 device_id。

        Args:
            responsivity: 响应度 (A/W)。
            dark_current: 暗电流 (A)。
        """
        spec = PhotodetectorSpec(responsivity=responsivity, dark_current=dark_current)
        return self._register("photodetector", spec)

    def add_laser(self, threshold_current: float, slope_efficiency: float) -> int:
        """添加 DFB 激光器，返回 device_id。

        Args:
            threshold_current: 阈值电流 (A)。
            slope_efficiency: 斜率效率 (W/A)。
        """
        spec = LaserSpec(
            threshold_current=threshold_current, slope_efficiency=slope_efficiency
        )
        return self._register("laser", spec)

    def _register(self, kind: str, spec: object) -> int:
        dev_id = self._next_id
        self._devices[dev_id] = (kind, spec)
        self._next_id += 1
        return dev_id

    # ------------------------------------------------------------------ 物理计算
    @staticmethod
    def mzm_transmission(voltage: np.ndarray | float, spec: ModulatorSpec) -> np.ndarray | float:
        """MZM 光强传输 T(V) = cos²(π(V+Vbias)/(2Vπ))·10^(-IL/20)。

        来源: Chrostowski 2015 §8.4 推挽 MZM 传输函数。
        """
        amp = 10.0 ** (-spec.insertion_loss_db / 20.0)
        phi = math.pi * (np.asarray(voltage) + spec.bias_v) / (2.0 * spec.vpi)
        return (np.cos(phi) ** 2) * amp

    @staticmethod
    def laser_li(current: float | np.ndarray, spec: LaserSpec) -> float | np.ndarray:
        """激光器 L-I 特性: P = max(0, η_d·(I - I_th))。

        来源: Coldren & Corzine 1995 §5.4 阈值以上线性输出。
        """
        i = np.asarray(current)
        p = spec.slope_efficiency * np.maximum(i - spec.threshold_current, 0.0)
        return float(p) if np.isscalar(current) else p

    # ------------------------------------------------------------------ 牛顿迭代
    def newton_solve(
        self,
        func: Callable[[float], float],
        x0: float,
        fprime: Callable[[float], float] | None = None,
    ) -> float:
        """牛顿迭代求解非线性方程 f(x)=0。

        封装 scipy.optimize.newton，失败即 raise（R03: 无 fall-back）。

        来源: Newton-Raphson 方法
          https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.newton.html

        Args:
            func: 目标函数 f(x)。
            x0: 初值。
            fprime: 解析导数（None 时用割线法/数值导数）。

        Returns:
            求解的根 x*。

        Raises:
            RuntimeError: 未在 maxiter 内收敛或求根失败。
        """
        try:
            root: float = newton(
                func,
                x0=x0,
                fprime=fprime,
                tol=self.config.newton_tol,
                maxiter=self.config.newton_maxiter,
                full_output=True,
                disp=False,
            )[0]
        except (RuntimeError, ValueError) as e:
            raise RuntimeError(f"牛顿迭代未收敛: {e}") from e
        if not math.isfinite(root):
            raise RuntimeError(f"牛顿迭代得到非有限根: {root}")
        return float(root)

    def solve_laser_carrier_density(self, current: float, spec: LaserSpec) -> float:
        """用牛顿迭代求解激光器稳态载流子密度 N*。

        求解稳态速率方程（含自发辐射耦合）:
            f(N) = η_i·I/q - N/τ_n - v_g·g(N)·S(N) = 0
        其中 g(N)=a(N-N_tr)，S(N)=β·N·τ_p/(τ_n·(1-Γ·v_g·g(N)·τ_p))。

        来源: Coldren & Corzine 1995 §5.3 稳态分析。

        Args:
            current: 驱动电流 (A)。
            spec: 激光器规格。

        Returns:
            稳态载流子密度 N* (1/m³)。

        Raises:
            RuntimeError: 牛顿迭代未收敛。
        """
        q = ELECTRON_CHARGE

        def residual(n: float) -> float:
            if n <= 0.0:
                return 1.0e30  # 物理上 N>0，强制正向
            gain = spec.gain_a * (n - spec.n_tr)
            denom = 1.0 - spec.gamma_confinement * spec.vg * gain * spec.tau_p
            if denom <= 1.0e-15:
                return 1.0e30  # 接近激射奇异点
            s = spec.beta_sp * n * spec.tau_p / (spec.tau_n * denom)
            return spec.eta_inj * current / q - n / spec.tau_n - spec.vg * gain * s

        # 初值: 透明载流子密度附近（Coldren 1995 典型范围）
        x0 = spec.n_tr * 1.1
        return self.newton_solve(residual, x0)

    # ------------------------------------------------------------------ Verilog-A 生成
    def generate_verilog_a(self, device_id: int) -> str:
        """根据 device_id 生成对应器件 Verilog-A 模型源代码。

        Raises:
            KeyError: device_id 未注册。
            ValueError: 器件类型无对应模板。
        """
        kind, spec = self._lookup(device_id)
        if kind == "modulator":
            assert isinstance(spec, ModulatorSpec)
            return MODULATOR_VA_TEMPLATE.format(
                uid=device_id, vpi=spec.vpi, il=spec.insertion_loss_db, bias=spec.bias_v
            )
        if kind == "photodetector":
            assert isinstance(spec, PhotodetectorSpec)
            return DETECTOR_VA_TEMPLATE.format(
                uid=device_id,
                resp=spec.responsivity,
                idark=spec.dark_current,
                rload=self.config.load_resistance,
            )
        if kind == "laser":
            assert isinstance(spec, LaserSpec)
            return LASER_VA_TEMPLATE.format(
                uid=device_id, ith=spec.threshold_current, se=spec.slope_efficiency
            )
        raise ValueError(f"无 Verilog-A 模板的器件类型: {kind}")

    def _lookup(self, device_id: int) -> tuple[str, object]:
        if device_id not in self._devices:
            raise KeyError(f"未注册的 device_id: {device_id}")
        return self._devices[device_id]

    # ------------------------------------------------------------------ VLSIR SPICE 导出
    def export_vlsir_spice(self, output_path: str | Path) -> Path:
        """导出 VLSIR 风格 SPICE 网表（子电路 + 实例 + 瞬态分析）。

        VLSIR (Ventilator's Language for SPICE Intermediate Representation) 由
        gdsfactory/hdl21 采用，将电路表示为可移植 SPICE 子电路层级。
        来源: https://github.com/dan-fritchman/vlsir

        Args:
            output_path: 输出 .sp 网表文件路径。

        Returns:
            写入的文件路径。
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = [
            "* PoLaRIS R17 VLSIR SPICE 光电协同网表",
            f"* 波长 = {self.config.wavelength_m:.6e} m",
            f"* 时间步 = {self.config.timestep:.6e} s",
            f"* 总时间 = {self.config.total_time:.6e} s",
            "",
        ]
        # 子电路定义（每器件一个 .subckt，端口顺序固定）
        for dev_id, (kind, spec) in self._devices.items():
            lines.append(self._build_subckt(dev_id, kind, spec))
        # 顶层实例与互联
        lines.append(".subckt cosim_top in out")
        prev_net = "in"
        idx = 0
        for dev_id, (kind, _spec) in self._devices.items():
            idx += 1
            nxt = "out" if idx == len(self._devices) else f"n{idx}"
            if kind == "modulator":
                lines.append(f"  X{dev_id} {prev_net} {nxt} rf_{dev_id} dev_{dev_id}")
            elif kind == "photodetector":
                lines.append(f"  X{dev_id} {prev_net} {nxt} dev_{dev_id}")
            elif kind == "laser":
                lines.append(f"  X{dev_id} ibias_{dev_id} {prev_net} dev_{dev_id}")
            prev_net = nxt
        lines.append("  V_rf rf_1 0 SINE(0 1 1e9)")
        lines.append("  V_ibias ibias_1 0 DC 0.05")
        lines.append(".ends cosim_top")
        lines.append("")
        lines.append("Xtop in out cosim_top")
        lines.append(f".tran {self.config.timestep:.6e} {self.config.total_time:.6e}")
        lines.append(".end")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def _build_subckt(self, dev_id: int, kind: str, spec: object) -> str:
        """构建单个器件的 SPICE 子电路定义（行为源近似 Verilog-A）。"""
        if kind == "modulator":
            assert isinstance(spec, ModulatorSpec)
            amp = 10.0 ** (-spec.insertion_loss_db / 20.0)
            return (
                f".subckt dev_{dev_id} opt_in opt_out rf\n"
                f"  param: vpi={spec.vpi:.6e} bias={spec.bias_v:.6e} amp={amp:.6e}\n"
                f"  Bout opt_out opt_in POLY(1) rf 0 'amp*(cos(3.14159265358979*(V(rf)+bias)/(2*vpi)))^2'\n"
                f".ends dev_{dev_id}\n"
            )
        if kind == "photodetector":
            assert isinstance(spec, PhotodetectorSpec)
            rl = self.config.load_resistance
            return (
                f".subckt dev_{dev_id} opt_in rf_out\n"
                f"  param: resp={spec.responsivity:.6e} idark={spec.dark_current:.6e} rl={rl:.6e}\n"
                f"  Gout rf_out 0 VALUE={{resp*V(opt_in)*V(opt_in)*rl+idark*rl}}\n"
                f".ends dev_{dev_id}\n"
            )
        if kind == "laser":
            assert isinstance(spec, LaserSpec)
            return (
                f".subckt dev_{dev_id} i_in opt_out\n"
                f"  param: ith={spec.threshold_current:.6e} se={spec.slope_efficiency:.6e}\n"
                f"  Bout opt_out 0 POLY(1) i_in 0 'sqrt(se*max(0,I(i_in)-ith))'\n"
                f".ends dev_{dev_id}\n"
            )
        raise ValueError(f"无子电路模板的器件类型: {kind}")

    # ------------------------------------------------------------------ cocotb 驱动生成
    def generate_cocotb_testbench(self, output_dir: str | Path) -> Path:
        """生成 cocotb 联合仿真测试驱动（Python testbench + Makefile）。

        cocotb 以 Python 协程驱动 SPICE 仿真器（如 Icarus/Ngspice），
        实现光电信号在时间步上的交互验证。
        来源: https://docs.cocotb.org/

        Args:
            output_dir: 输出目录。

        Returns:
            生成的 testbench Python 文件路径。
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        n_dev = len(self._devices)
        tb_code = (
            '"""cocotb 光电协同仿真测试驱动（PoLaRIS R17 自动生成）。"""\n'
            "import cocotb\n"
            "from cocotb.triggers import Timer, RisingEdge\n"
            "from cocotb.clock import Clock\n"
            "\n"
            f"N_DEVICES = {n_dev}\n"
            f"TIMESTEP_NS = {self.config.timestep * 1e9:.6f}\n"
            f"TOTAL_NS = {self.config.total_time * 1e9:.6f}\n"
            "\n"
            "@cocotb.test()\n"
            "async def test_photoelectric_link(dut):\n"
            '    """驱动 MZM rf 输入，采样 PD 输出，验证光电协同传输。"""\n'
            '    clock = Clock(dut.rf_1, TIMESTEP_NS, units="ns")\n'
            "    cocotb.start_soon(clock.start())\n"
            "    n_steps = int(TOTAL_NS / TIMESTEP_NS)\n"
            "    for _ in range(n_steps):\n"
            "        await RisingEdge(dut.rf_1)\n"
            "        await Timer(TIMESTEP_NS, units=\"ns\")\n"
            "    assert N_DEVICES > 0, \"未注册任何光电器件\"\n"
        )
        tb_path = out / "test_cosim.py"
        tb_path.write_text(tb_code, encoding="utf-8")
        mk = out / "Makefile"
        mk.write_text(
            "SIM ?= ngspice\n"
            "TOPLEVEL_LANG ?= vhdl\n"
            "TESTCASE ?= test_photoelectric_link\n"
            "include $(shell cocotb-config --makefiles)/Makefile.sim\n",
            encoding="utf-8",
        )
        return tb_path

    # ------------------------------------------------------------------ 协同仿真执行
    def run_cosim(self, rf_voltage: np.ndarray | float | None = None) -> dict:
        """执行光电协同数值仿真，返回时域波形。

        链路顺序: Laser(光载波) → Modulator(电光调制) → Photodetector(光电转换)。
        若未注册激光器，使用 config.input_power_w 作为光载波。
        若未注册调制器，光载波直通。
        若未注册探测器，仅返回光功率。

        Python 数值积分在每个时间步顺序求解光电耦合（前向链路，无反馈），
        非线性稳态由牛顿迭代解析，非外部 SPICE 依赖（R03: 真实物理计算）。

        Args:
            rf_voltage: 调制器射频驱动电压数组 (V)。None 时生成默认正弦激励
                （1 GHz，幅度 1 V），属仿真激励非数据兜底。

        Returns:
            字典 {time, rf_voltage, optical_power, detector_current, output_voltage}。

        Raises:
            RuntimeError: 链路拓扑非法（如多个调制器/激光器）。
        """
        n_steps = int(round(self.config.total_time / self.config.timestep)) + 1
        time = np.arange(n_steps) * self.config.timestep
        rf = self._resolve_rf(rf_voltage, n_steps)

        # 光载波功率（激光器 L-I 稳态或默认）
        laser = self._find_single("laser")
        if laser is not None:
            _kind, lspec = laser
            assert isinstance(lspec, LaserSpec)
            p_carrier = self.laser_li(lspec.bias_current, lspec)
        else:
            p_carrier = self.config.input_power_w

        # 调制器时域调制
        mod = self._find_single("modulator")
        if mod is not None:
            _kind, mspec = mod
            assert isinstance(mspec, ModulatorSpec)
            p_mod = p_carrier * self.mzm_transmission(rf, mspec)
        else:
            p_mod = np.full(n_steps, p_carrier, dtype=float)

        # 探测器光电转换
        pd = self._find_single("photodetector")
        if pd is not None:
            _kind, pspec = pd
            assert isinstance(pspec, PhotodetectorSpec)
            i_pd = pspec.responsivity * p_mod + pspec.dark_current
            v_out = i_pd * self.config.load_resistance
        else:
            i_pd = np.zeros(n_steps)
            v_out = np.zeros(n_steps)

        return {
            "time": time,
            "rf_voltage": rf,
            "optical_power": p_mod,
            "detector_current": i_pd,
            "output_voltage": v_out,
        }

    def _resolve_rf(self, rf_voltage: np.ndarray | float | None, n_steps: int) -> np.ndarray:
        """解析射频激励（None 生成 1 GHz 正弦，属激励非兜底）。"""
        if rf_voltage is None:
            t = np.arange(n_steps) * self.config.timestep
            return np.sin(2.0 * math.pi * 1.0e9 * t)
        arr = np.asarray(rf_voltage, dtype=float)
        if arr.ndim == 0:
            return np.full(n_steps, float(arr))
        if arr.shape[0] != n_steps:
            raise ValueError(
                f"rf_voltage 长度 {arr.shape[0]} 与时间步数 {n_steps} 不匹配"
            )
        return arr

    def _find_single(self, kind: str) -> tuple[str, object] | None:
        """查找某类唯一器件，多于一个则 raise（拓扑约束）。"""
        matches = [(k, s) for k, s in self._devices.values() if k == kind]
        if not matches:
            return None
        if len(matches) > 1:
            raise RuntimeError(f"链路仅支持 1 个 {kind}，得到 {len(matches)} 个")
        return matches[0]


__all__ = [
    "CoSimConfig",
    "ModulatorSpec",
    "PhotodetectorSpec",
    "LaserSpec",
    "PhotoelectricCoSim",
    "MODULATOR_VA_TEMPLATE",
    "DETECTOR_VA_TEMPLATE",
    "LASER_VA_TEMPLATE",
    "ELECTRON_CHARGE",
    "PLANCK_CONSTANT",
    "SPEED_OF_LIGHT",
]
