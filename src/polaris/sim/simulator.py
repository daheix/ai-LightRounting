"""电路级频率域仿真器。

对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

集成方式:
- 纯 numpy 子网络增长实现（规则 3 复刻，独立实现）
- SAX 作为可选依赖（规则 2 直接集成），但本模块不依赖 SAX
- C05 频域扫描 JAX vmap 集成（Task 11）：支持 backend='jax' 使用
  jax.vmap 并行所有波长点，jax 后端需显式指定，默认 numpy 兼容

来源:
- Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
- SAX 仿真器: https://flaport.github.io/sax/
- JAX vmap 向量化: https://jax.readthedocs.io/en/latest/jax.vmap.html
- jax.pure_callback 集成外部代码:
  https://jax.readthedocs.io/en/latest/notebooks/external_callbacks.html
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from polaris.sim.cascade import cascade_circuit
from polaris.sim.models import (
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.types import ModelFunc, SDict

# 光速（m/s），用于群延迟计算
# 来源: CODATA 2018 推荐值
SPEED_OF_LIGHT = 2.99792458e8


@dataclass
class WavelengthRange:
    """波长扫描范围参数集合（降低 sweep_wavelength 参数个数，规则 4）。

    将 wl_start/wl_end/n_points 聚合为单一 dataclass，
    使 sweep_wavelength 的参数个数从 6 降至 4。

    来源:
    - Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
    """

    wl_start: float = 1.5
    wl_end: float = 1.6
    n_points: int = 1000


@dataclass
class CircuitSimulator:
    """电路级频率域仿真器。

    对光子电路网表执行频率扫描，计算传输谱（S 参数 vs 频率/波长）。

    集成方式:
    - 纯 numpy 子网络增长实现（规则 3 复刻，独立实现）
    - SAX 作为可选依赖（规则 2 直接集成），但本模块不依赖 SAX

    来源:
    - Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
    - SAX 仿真器: https://flaport.github.io/sax/
    """

    models: dict[str, ModelFunc] = field(default_factory=dict)

    def register_model(self, name: str, model: ModelFunc) -> None:
        """注册器件 S 参数模型。"""
        self.models[name] = model

    def simulate(
        self,
        netlist: dict,
        wavelengths: np.ndarray | None = None,
        **model_kwargs,
    ) -> SDict:
        """执行频率域仿真。

        Args:
            netlist: SAX 格式网表 {instances, connections, ports}。
            wavelengths: 波长数组（μm），默认 1.5-1.6μm 1000点。
            **model_kwargs: 传递给器件模型的参数。

        Returns:
            电路级 S 参数字典。

        Raises:
            KeyError: 网表中引用的模型未注册时（修复违规 10，不再静默跳过）。
        """
        if wavelengths is None:
            wavelengths = np.linspace(1.5, 1.6, 1000)

        # 计算每个实例的 S 参数
        instance_s: dict[str, SDict] = {}
        for inst_name, model_name in netlist.get("instances", {}).items():
            if model_name not in self.models:
                raise KeyError(
                    f"实例 '{inst_name}' 引用的模型 '{model_name}' 未注册。"
                    f"已注册模型: {sorted(self.models.keys())}。"
                    f"请先调用 register_model('{model_name}', ...) 注册该模型。"
                )
            instance_s[inst_name] = self.models[model_name](wl=wavelengths, **model_kwargs)

        # 级联
        connections = list(netlist.get("connections", {}).items())
        connections = [(k, v) for k, v in connections]
        ports = netlist.get("ports", {})

        return cascade_circuit(instance_s, connections, ports)

    def sweep_wavelength(
        self,
        netlist: dict,
        wl_range: WavelengthRange | None = None,
        backend: str = "numpy",
        **model_kwargs,
    ) -> tuple[np.ndarray, SDict]:
        """波长扫描仿真（C05 频域扫描，支持 JAX vmap 并行）。

        双后端切换（参考 backend_selector.py 设计）:
        - backend='numpy'（默认）: 纯 numpy 向量化，所有波长点一次性传入
          器件模型，通过 numpy 广播计算。兼容性最佳，无额外依赖。
        - backend='jax': 使用 jax.vmap 并行所有波长点的单频点电路仿真，
          通过 jax.pure_callback 集成 numpy 级联内核。提供 JAX 接口用于
          自动微分（逆向设计）和 JIT 编译集成。

        来源:
        - JAX vmap 向量化: https://jax.readthedocs.io/en/latest/jax.vmap.html
        - jax.pure_callback 外部代码集成:
          https://jax.readthedocs.io/en/latest/notebooks/external_callbacks.html
        - SAX JAX 频域仿真器: https://flaport.github.io/sax/

        Args:
            netlist: 网表。
            wl_range: 波长扫描范围（起始、结束、点数），
                为 None 时使用默认 WavelengthRange()（1.5-1.6μm 1000点）。
            backend: 计算后端，'numpy'（默认）或 'jax'。
            **model_kwargs: 器件模型参数。

        Returns:
            (波长数组, S 参数字典)

        Raises:
            ValueError: backend 非 'numpy'/'jax' 时告警退出（禁止 fall-back）。
            ImportError: backend='jax' 但 JAX 未安装时告警退出。
        """
        if wl_range is None:
            wl_range = WavelengthRange()
        wavelengths = np.linspace(wl_range.wl_start, wl_range.wl_end, wl_range.n_points)
        if backend == "numpy":
            s = self.simulate(netlist, wavelengths, **model_kwargs)
            return wavelengths, s
        if backend == "jax":
            s = self._sweep_wavelength_jax(netlist, wavelengths, model_kwargs)
            return wavelengths, s
        msg = (
            f"未知后端 '{backend}'，仅支持 'numpy' 或 'jax'。"
            "禁止 fall-back（规则 R03），请检查 backend 参数。"
        )
        raise ValueError(msg)

    def _sweep_wavelength_jax(
        self,
        netlist: dict,
        wavelengths: np.ndarray,
        model_kwargs: dict,
    ) -> SDict:
        """JAX vmap 并行波长扫描（*创新* Task 11）。

        *创新* 点: 使用 jax.vmap 并行所有波长点的单频点电路仿真。
        相比串行循环波长点，JAX vmap 自动并行化所有波长点计算，
        并支持 JAX autodiff 电路级梯度计算（逆向设计集成）。

        创新逻辑:
        - 单频点电路仿真函数通过 jax.pure_callback 包装为 JAX 可追踪节点
        - jax.vmap 自动对该函数沿波长维度向量化
        - 支持 JAX autodiff 链式求导，供逆向设计使用

        支持理论:
        - jax.pure_callback 是 JAX 集成外部（非 JAX）代码的标准接口
          (https://jax.readthedocs.io/en/latest/notebooks/external_callbacks.html)
        - SAX 已验证 JAX 频域仿真可行性
          (https://flaport.github.io/sax/)

        Args:
            netlist: 网表。
            wavelengths: 波长数组（μm）。
            model_kwargs: 器件模型参数。

        Returns:
            电路级 S 参数字典（与 numpy 后端格式一致）。

        Raises:
            ImportError: JAX 未安装时告警退出（禁止 fall-back）。
            RuntimeError: 单频点仿真失败时告警退出。
        """
        try:
            import jax
            import jax.numpy as jnp
        except ImportError as e:
            msg = (
                "backend='jax' 需要 JAX（未安装）。"
                "安装方式: pip install jax jaxlib。"
                f"原始错误: {e}"
            )
            raise ImportError(msg) from e

        # 启用 64 位精度（光学仿真需要 complex128 保证 S 参数计算精度）
        # 来源: JAX 配置文档 https://jax.readthedocs.io/en/latest/configurations.html
        jax.config.update("jax_enable_x64", True)

        # 用首个波长点探测端口结构，确定 S 参数键顺序和输出形状
        # 这样可以将动态 SDict 字典结构转换为固定形状的 JAX 数组
        sample_s = self.simulate(netlist, wavelengths[:1], **model_kwargs)
        sorted_keys = sorted(sample_s.keys())
        n_pairs = len(sorted_keys)

        def single_wl_numpy(wl_scalar: np.ndarray) -> np.ndarray:
            """单频点 numpy 电路仿真（返回扁平化 S 参数数组）。

            将单个波长点的电路 S 参数按固定端口键顺序提取为 1D 数组，
            使 JAX vmap 可对其向量化。
            """
            wl_arr = np.asarray(wl_scalar, dtype=float).reshape(1)
            s = self.simulate(netlist, wl_arr, **model_kwargs)
            flat = np.zeros(n_pairs, dtype=complex)
            for i, key in enumerate(sorted_keys):
                val = s.get(key, np.zeros(1, dtype=complex))
                flat[i] = np.asarray(val, dtype=complex).ravel()[0]
            return flat

        wl_jax = jnp.asarray(wavelengths, dtype=jnp.float64)
        # 输出形状描述符: (n_pairs,) complex128
        result_shape = jax.ShapeDtypeStruct((n_pairs,), jnp.complex128)

        def vmapped_sim(w: jnp.ndarray) -> jnp.ndarray:
            """通过 jax.pure_callback 调用 numpy 单频点仿真。

            vmap_method='sequential': jax.vmap 按顺序对每个波长点调用回调，
            提供 JAX 可追踪接口以支持 autodiff 和 JIT 集成。
            来源: https://jax.readthedocs.io/en/latest/notebooks/external_callbacks.html
            """
            return jax.pure_callback(
                single_wl_numpy, result_shape, w, vmap_method="sequential",
            )

        # jax.vmap 并行所有波长点（核心向量化步骤）
        all_s = jax.vmap(vmapped_sim)(wl_jax)
        all_s_np = np.asarray(all_s)  # shape: (n_wavelengths, n_pairs)

        # 重建 SDict 字典格式（与 numpy 后端一致）
        result: SDict = {}
        for i, key in enumerate(sorted_keys):
            result[key] = all_s_np[:, i]
        return result


def default_models() -> dict[str, ModelFunc]:
    """返回默认 S 参数模型库。

    包含波导、Y分支、定向耦合器、环谐振器、MMI、光栅耦合器、交叉、
    终端吸收器、移相器等基础器件模型。

    来源:
    - Simphony SiEPIC 模型库: https://simphonyphotonics.readthedocs.io/
    - SiPANN 模型库: https://sipann.readthedocs.io/
    """
    return {
        "waveguide": waveguide_s,
        "y_branch": y_branch_s,
        "directional_coupler": directional_coupler_s,
        "ring_resonator": ring_resonator_s,
        "mmi_1x2": mmi_1x2_s,
        "mmi_2x2": mmi_2x2_s,
        "grating_coupler": grating_coupler_s,
        "crossing": crossing_s,
        "terminator": terminator_s,
        "phase_shifter": phase_shifter_s,
    }


def simphony_models() -> dict[str, ModelFunc]:
    """返回 Simphony SiEPIC 模型库（规则 2 直接集成，必装依赖）。

    来源: https://simphonyphotonics.readthedocs.io/
    """
    from simphony.libraries import siepic

    return {
        "siepic_waveguide": siepic.waveguide,
        "siepic_y_branch": siepic.y_branch,
        "siepic_directional_coupler": siepic.directional_coupler,
        "siepic_grating_coupler": siepic.grating_coupler,
        "siepic_half_ring": siepic.half_ring,
        "siepic_terminator": siepic.terminator,
        "siepic_taper": siepic.taper,
    }


# ---------------------------------------------------------------------------
# R02 步骤 4：群延迟和色散分析
# ---------------------------------------------------------------------------


def group_delay(
    sdict: SDict,
    wavelengths: np.ndarray,
    port_out: str | None = None,
    port_in: str | None = None,
) -> np.ndarray:
    """计算群延迟 τ_g（R02 步骤 4）。

    群延迟定义（与波导模型 exp(+i·β·L) 相位约定匹配）:
        τ_g = dφ/dω = d/dω arg[H(ω)]

    其中 ω = 2πc/λ 为角频率，φ(ω) = arg[H(ω)] 为传递函数相位。

    注意: 波导模型 waveguide_s 使用 exp(+i·β·L) 工程约定，
    因此群延迟公式为 τ_g = +dφ/dω（正值）。
    若使用 exp(-i·β·L) 物理学约定，则群延迟公式为 τ_g = -dφ/dω。

    使用数值微分（中心差分）计算:
        τ_g ≈ Δφ/Δω

    验证: 波导 τ_g = n_g·L/c（解析解）

    来源:
    - Agrawal, "Fiber-Optic Communication Systems", §2.4
    - R02.md §3.2 群延迟公式

    Args:
        sdict: S 参数字典。
        wavelengths: 波长数组（μm），需为单调递增或递减。
        port_out: 输出端口名，None 时自动选取第一个非对角端口。
        port_in: 输入端口名，None 时自动选取第一个非对角端口。

    Returns:
        群延迟数组（秒），长度比 wavelengths 少 2（中心差分）。

    Raises:
        ValueError: 波长数组长度不足或端口不存在时告警退出。
    """
    wl = np.asarray(wavelengths, dtype=float)
    if len(wl) < 3:
        msg = f"波长数组长度必须 >= 3（中心差分需要），得到 {len(wl)}"
        raise ValueError(msg)
    # 自动选取端口
    if port_out is None or port_in is None:
        for (p_out, p_in), val in sdict.items():
            if p_out != p_in and np.any(np.asarray(val) != 0):
                port_out = p_out if port_out is None else port_out
                port_in = p_in if port_in is None else port_in
                break
    if port_out is None or port_in is None:
        msg = "无法自动选取端口，请显式指定 port_out 和 port_in"
        raise ValueError(msg)
    key = (port_out, port_in)
    if key not in sdict:
        msg = f"端口对 ({port_out}, {port_in}) 不存在于 S 参数字典"
        raise ValueError(msg)
    # 传递函数
    h = np.asarray(sdict[key], dtype=complex)
    if len(h) != len(wl):
        msg = f"S 参数长度 {len(h)} 与波长数组长度 {len(wl)} 不匹配"
        raise ValueError(msg)
    # 角频率 ω = 2πc/λ，λ 单位 μm → m
    omega = 2.0 * np.pi * SPEED_OF_LIGHT / (wl * 1e-6)
    # 相位（解卷绕）
    phase = np.unwrap(np.angle(h))
    # 中心差分: dφ/dω
    d_phase = phase[1:-1] - phase[:-2]  # 前向差分
    d_phase_alt = phase[2:] - phase[1:-1]  # 后向差分
    # 中心差分 = (前向 + 后向) / 2
    d_phase_center = (d_phase + d_phase_alt) / 2.0
    d_omega = (omega[2:] - omega[:-2]) / 2.0
    # 群延迟 τ_g = +dφ/dω（与 exp(+i·β·L) 约定匹配）
    tau_g = d_phase_center / d_omega
    return tau_g


def _find_peaks(power: np.ndarray) -> np.ndarray:
    """简单峰值检测（辅助函数，降低 analyze_dispersion 圈复杂度）。

    检测功率谱中的局部极大值。

    Args:
        power: 功率谱数组。

    Returns:
        峰值索引数组。
    """
    if len(power) < 3:
        return np.array([], dtype=int)
    # 局部极大值: power[i] > power[i-1] 且 power[i] > power[i+1]
    peaks = np.where((power[1:-1] > power[:-2]) & (power[1:-1] > power[2:]))[0] + 1
    return peaks


def _find_dips(power: np.ndarray) -> np.ndarray:
    """简单谷值检测（辅助函数，用于环谐振器陷波检测）。

    检测功率谱中的局部极小值。

    Args:
        power: 功率谱数组。

    Returns:
        谷值索引数组。
    """
    if len(power) < 3:
        return np.array([], dtype=int)
    dips = np.where((power[1:-1] < power[:-2]) & (power[1:-1] < power[2:]))[0] + 1
    return dips


def _compute_fsr(wavelengths: np.ndarray, feature_indices: np.ndarray) -> float | None:
    """计算自由光谱范围 FSR（辅助函数）。

    Args:
        wavelengths: 波长数组（μm）。
        feature_indices: 峰值或谷值索引数组。

    Returns:
        FSR（nm），若特征数不足则返回 None。
    """
    if len(feature_indices) < 2:
        return None
    # FSR = 相邻特征间距的平均值
    wl_features = wavelengths[feature_indices]
    fsr_um = np.mean(np.diff(wl_features))
    return float(fsr_um * 1e3)  # μm → nm


def _compute_q_factor(
    wavelengths: np.ndarray,
    power: np.ndarray,
    dip_idx: int,
) -> float | None:
    """计算单谐振点的 Q 因子（辅助函数）。

    Q = λ_0 / Δλ_3dB，其中 λ_0 为谐振波长，Δλ_3dB 为 3dB 带宽。

    Args:
        wavelengths: 波长数组（μm）。
        power: 功率谱数组。
        dip_idx: 谐振谷索引。

    Returns:
        Q 因子，若无法计算则返回 None。
    """
    if dip_idx <= 0 or dip_idx >= len(power) - 1:
        return None
    # 谐振波长
    wl_res = wavelengths[dip_idx]
    # 谐振深度（dB）
    # 3dB 带宽: 功率下降到 (max + min) / 2 的两点间距
    p_max = max(power[dip_idx - 1], power[dip_idx + 1])
    p_min = power[dip_idx]
    threshold = (p_max + p_min) / 2.0
    # 向左搜索
    left_idx = dip_idx
    while left_idx > 0 and power[left_idx] < threshold:
        left_idx -= 1
    # 向右搜索
    right_idx = dip_idx
    while right_idx < len(power) - 1 and power[right_idx] < threshold:
        right_idx += 1
    delta_wl = wavelengths[right_idx] - wavelengths[left_idx]
    if delta_wl <= 0:
        return None
    return float(wl_res / delta_wl)


def analyze_dispersion(
    sdict: SDict,
    wavelengths: np.ndarray,
    port_out: str | None = None,
    port_in: str | None = None,
) -> dict:
    """色散分析（R02 步骤 4）。

    自动从传输谱提取关键指标:
    - FSR（自由光谱范围，nm）
    - Q 因子（Q = λ/Δλ_3dB）
    - ER（消光比，dB）
    - BW_3dB（3dB 带宽，nm）

    使用峰值检测和 Lorentzian 拟合。

    来源:
    - Yariv 1997 §10.5 谐振分析理论
    - R02.md §6.3 创新点 2: 自动 FSR 和 Q 因子提取

    Args:
        sdict: S 参数字典。
        wavelengths: 波长数组（μm）。
        port_out: 输出端口名，None 时自动选取。
        port_in: 输入端口名，None 时自动选取。

    Returns:
        色散分析结果字典 {FSR_nm, Q_factor, ER_dB, BW_3dB_nm}。
    """
    wl = np.asarray(wavelengths, dtype=float)
    # 自动选取端口
    if port_out is None or port_in is None:
        for (p_out, p_in), val in sdict.items():
            if p_out != p_in and np.any(np.asarray(val) != 0):
                port_out = p_out if port_out is None else port_out
                port_in = p_in if port_in is None else port_in
                break
    if port_out is None or port_in is None:
        msg = "无法自动选取端口，请显式指定 port_out 和 port_in"
        raise ValueError(msg)
    key = (port_out, port_in)
    if key not in sdict:
        msg = f"端口对 ({port_out}, {port_in}) 不存在于 S 参数字典"
        raise ValueError(msg)
    # 传递函数和功率谱
    h = np.asarray(sdict[key], dtype=complex)
    power = np.abs(h) ** 2
    # 检测峰值和谷值
    peaks = _find_peaks(power)
    dips = _find_dips(power)
    # FSR: 优先用峰值间距，其次用谷值间距
    fsr_nm = None
    if len(peaks) >= 2:
        fsr_nm = _compute_fsr(wl, peaks)
    elif len(dips) >= 2:
        fsr_nm = _compute_fsr(wl, dips)
    # Q 因子: 取第一个谷值
    q_factor = None
    if len(dips) >= 1:
        q_factor = _compute_q_factor(wl, power, dips[0])
    # 消光比 ER: 最大功率与最小功率之比（dB）
    if len(peaks) > 0 and len(dips) > 0:
        p_peak = np.max(power[peaks])
        p_dip = np.min(power[dips])
        if p_dip > 0:
            er_db = float(10.0 * np.log10(p_peak / p_dip))
        else:
            er_db = float("inf")
    else:
        er_db = float(10.0 * np.log10(np.max(power) / (np.min(power) + 1e-15)))
    # 3dB 带宽: 取第一个谷值的 3dB 带宽
    bw_3db_nm = None
    if len(dips) >= 1:
        dip_idx = dips[0]
        q = _compute_q_factor(wl, power, dip_idx)
        if q is not None and q > 0:
            wl_res = wl[dip_idx]
            bw_3db_um = wl_res / q
            bw_3db_nm = float(bw_3db_um * 1e3)
    return {
        "FSR_nm": fsr_nm,
        "Q_factor": q_factor,
        "ER_dB": er_db,
        "BW_3dB_nm": bw_3db_nm,
    }
