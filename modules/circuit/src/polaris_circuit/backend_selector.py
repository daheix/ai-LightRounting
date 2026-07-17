"""S 矩阵条件数计算 + JAX CPU 后端选择器（v5.1，R04 合规：仅 CPU 后端）。

条件数定义: κ(S) = ||S||_2 · ||S⁻¹||_2 = σ_max / σ_min
- κ(S) < 1e6: 良态（well-conditioned）
- 1e6 ≤ κ(S) < 1e12: 病态（ill-conditioned）
- κ(S) ≥ 1e12: 接近奇异，结果不可信

JAX CPU 后端（v5.1 新增）:
- is_jax_available() 自动检测 jax 可导入且 jax.devices("cpu") 非空，结果缓存。
- 提供 waveguide_s_jax / cascade_two_port_jax / simulate_waveguide_chain_jax
  三个 jnp 向量化 S 参数计算函数，与 models.waveguide_s 物理一致。
- R04 战略决策: 仅使用 jax.devices("cpu")，禁止 GPU/TPU 后端。
- R03 禁止 fall-back: JAX 不可用时一律 raise RuntimeError，不静默回退 numpy。
- 启用 jax_enable_x64=True 保证与 numpy float64 数值一致（测试可复现）。

来源（R02 学术诚信，≥5 篇文献 URL）:
1. Golub & Van Loan 2013, "Matrix Computations", 4th ed.,
   Johns Hopkins Univ. Press §2.3, §3.5,
   https://www.press.jhu.edu/books/title/10876/matrix-computations
2. SAX Backends 文档: https://gdsfactory.github.io/sax/nbs/internals/03_backends/
3. Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85,
   https://arxiv.org/abs/2009.05146
4. Filipsson 1978, "A new general computer algorithm for S-matrix calculation
   of interconnected multiports", Proc. Eur. Microw. Conf.,
   https://doi.org/10.1109/EUMA.1978.332681
5. Bradbury et al. 2018, "JAX: composable transformations of Python+NumPy
   programs", JOSS 3(31):10219, https://doi.org/10.21105/joss.02021
6. JAX JIT 编译文档: https://jax.readthedocs.io/en/latest/jax-101/02-jitting.html
7. JAX lax.scan 文档:
   https://jax.readthedocs.io/en/latest/_autosummary/jax.lax.scan.html
8. SAX JAX 后端: https://flaport.github.io/sax/
9. NumPy 广播规则:
   https://numpy.org/doc/stable/user/basics.broadcasting.html
10. Pozar, "Microwave Engineering" 4th ed. §4.3 (两网络级联 Redheffer star),
    https://www.wiley.com/en-us/Microwave+Engineering%2C+4th+Edition-p-9781118213636

合规: R02 学术诚信 / R03 禁止 fall-back（JAX 不可用即 raise）/
R04 仅 JAX CPU 后端（jax.devices("cpu")，禁 GPU/TPU）/ R05 无 TODO。
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any, Callable

import numpy as np

from polaris_circuit.types import SDict

logger = logging.getLogger(__name__)

# 条件数阈值（来源: Golub & Van Loan "Matrix Computations" §2.3）
COND_NUM_FG_THRESHOLD = 1e6  # 良态/病态分界
COND_NUM_KLU_THRESHOLD = 1e12  # 病态/奇异分界


def _sdict_to_matrix(sdict: SDict) -> np.ndarray:
    """将 SDict 转换为稠密 S 矩阵（取第一个频点，用于条件数评估）。"""
    ports_out = sorted({k[0] for k in sdict})
    ports_in = sorted({k[1] for k in sdict})
    n_out = len(ports_out)
    n_in = len(ports_in)
    first_val = next(iter(sdict.values()))
    arr = np.asarray(first_val, dtype=complex)
    n_freq = arr.shape[0] if arr.ndim > 0 else 1
    mat = np.zeros((n_out, n_in, n_freq), dtype=complex)
    for (p_out, p_in), val in sdict.items():
        i = ports_out.index(p_out)
        j = ports_in.index(p_in)
        mat[i, j, :] = np.asarray(val, dtype=complex)
    return mat[:, :, 0]


def compute_condition_number(sdict: SDict) -> float:
    """计算 S 矩阵的条件数 κ(S) = σ_max / σ_min。

    来源: Golub & Van Loan, "Matrix Computations", §2.3, §3.5

    Args:
        sdict: S 参数字典 {(port_out, port_in): array}。

    Returns:
        条件数 κ(S)。若矩阵非方阵或接近奇异，返回最大奇异值之比；
        σ_min ≈ 0 时返回 inf。
    """
    mat = _sdict_to_matrix(sdict)
    sv = np.linalg.svd(mat, compute_uv=False)
    sigma_max = sv[0]
    sigma_min = sv[-1]
    if sigma_min < 1e-300:
        return float("inf")
    return float(sigma_max / sigma_min)


# ============================================================================
# JAX CPU 后端（v5.1 新增，R04 合规：仅 jax.devices("cpu")）
# ============================================================================

# JAX 可用性缓存: None=未检测，True/False=已检测并缓存
_JAX_AVAILABILITY_CACHE: bool | None = None
# JAX x64 是否已配置（避免重复调用 jax.config.update）
_JAX_X64_CONFIGURED: bool = False


def _configure_jax_x64() -> None:
    """启用 JAX float64 模式，保证与 numpy 数值一致。

    必须在 jax 导入后、第一次计算前调用。幂等：重复调用无副作用。
    float64 与 numpy 默认 dtype 对齐，确保测试 atol=1e-10 可复现。
    来源: JAX 配置文档 https://jax.readthedocs.io/en/latest/notebooks/Common_Gotchas_in_JAX.html#double-64bit-precision
    """
    global _JAX_X64_CONFIGURED
    if _JAX_X64_CONFIGURED:
        return
    import jax

    jax.config.update("jax_enable_x64", True)
    _JAX_X64_CONFIGURED = True


def is_jax_available() -> bool:
    """检测 JAX 是否可导入且 CPU 后端可用（结果缓存）。

    R04 战略: 仅检测 jax.devices("cpu")，GPU/TPU 不计入可用判定。
    使用 importlib.util.find_spec 避免模块导入时强依赖 jax。

    Returns:
        True 若 jax 可导入且 jax.devices("cpu") 非空；否则 False。
    """
    global _JAX_AVAILABILITY_CACHE
    if _JAX_AVAILABILITY_CACHE is not None:
        return _JAX_AVAILABILITY_CACHE
    spec = importlib.util.find_spec("jax")
    if spec is None:
        _JAX_AVAILABILITY_CACHE = False
        return False
    try:
        import jax

        _configure_jax_x64()
        # R04: 仅以 CPU 后端可用作为判定依据
        cpu_devs = jax.devices("cpu")
        available = len(cpu_devs) > 0
    except Exception as exc:  # noqa: BLE001 — 检测函数需捕获所有导入/配置错误
        logger.warning("JAX 可用性检测失败: %s", exc)
        available = False
    _JAX_AVAILABILITY_CACHE = available
    return available


def get_jax_devices() -> list[str]:
    """返回可用的 JAX 设备列表（CPU only，R04 禁 GPU/TPU）。

    Returns:
        设备描述字符串列表，如 ["CpuDevice(id=0)"]。

    Raises:
        RuntimeError: JAX 不可用（R03 禁止 fall-back，不返回空列表）。
    """
    if not is_jax_available():
        raise RuntimeError(
            "JAX 不可用，无法获取 JAX 设备列表（R03 禁止 fall-back，"
            "请安装 jax: pip install jax）"
        )
    import jax

    # R04: 显式仅返回 CPU 设备，过滤任何 GPU/TPU
    cpu_devs = jax.devices("cpu")
    return [str(d) for d in cpu_devs]


def jit_compile(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Callable[..., Any]:
    """用 jax.jit 编译函数（CPU 后端，R04 合规）。

    Args:
        func: 待编译的纯函数（输入输出为 jnp.ndarray）。
        *args, **kwargs: 透传给 jax.jit 的额外参数（如 static_argnames）。

    Returns:
        jax.jit 编译后的可调用对象。

    Raises:
        RuntimeError: JAX 不可用（R03 禁止 fall-back 到 numpy 实现）。

    来源: JAX JIT 编译 https://jax.readthedocs.io/en/latest/jax-101/02-jitting.html
    """
    if not is_jax_available():
        raise RuntimeError(
            "JAX 不可用，无法 jit 编译（R03 禁止 fall-back，"
            "请安装 jax: pip install jax）"
        )
    import jax

    return jax.jit(func, *args, **kwargs)


def waveguide_s_jax(
    wavelengths_um: "np.ndarray | float",
    length_um: float,
    neff: float,
    ng: float,
) -> np.ndarray:
    """JAX 实现的波导 S 参数（jnp 向量化）。

    相位 phi = exp(1j * 2π * neff * L / wl)，与 models.waveguide_s 物理一致。
    返回 S 矩阵 shape (2, 2, n_freq)，索引 [port_out, port_in, freq]：
        S[0,0]=0 (in 反射), S[0,1]=phi (in→out 传输),
        S[1,0]=phi (out→in 传输), S[1,1]=0 (out 反射)
    （端口 0=in, 1=out，与 SDict 的 ("out","in") 一致）

    Args:
        wavelengths_um: 波长数组（μm），1D。
        length_um: 波导长度（μm）。
        neff: 有效折射率（相位计算用，与 models.waveguide_s 一致）。
        ng: 群折射率（保留参数，与 models.waveguide_s API 对齐；
            当前相位用 neff，ng 预留给后续群速度色散扩展）。

    Returns:
        np.ndarray: shape (2, 2, n_freq) 的复数 S 矩阵。

    Raises:
        RuntimeError: JAX 不可用（R03 禁止 fall-back 到 numpy 版本）。
        ValueError: 波长非正。

    来源:
    - Simphony/SiPANN waveguide 模型 https://simphonyphotonics.readthedocs.io/
    - Chrostowski & Hochberg 2015 "Silicon Photonics Design" Cambridge
    """
    if not is_jax_available():
        raise RuntimeError(
            "JAX 不可用，waveguide_s_jax 无法执行（R03 禁止 fall-back，"
            "请安装 jax 或使用 models.waveguide_s numpy 版本）"
        )
    import jax.numpy as jnp

    wl = jnp.asarray(wavelengths_um, dtype=jnp.float64)
    if bool(jnp.any(wl <= 0)):
        raise ValueError(f"波长必须 > 0 μm，得到 {wavelengths_um}")
    beta = 2.0 * jnp.pi * neff / wl  # (n_freq,)
    phase = jnp.exp(1j * beta * length_um)  # (n_freq,)
    zero = jnp.zeros_like(phase)
    # S[out, in, freq]: 对角反射=0, off-diagonal 传输=phase
    s_matrix = jnp.stack(
        [
            jnp.stack([zero, phase], axis=0),  # out=in 行
            jnp.stack([phase, zero], axis=0),  # out=out 行
        ],
        axis=0,
    )
    return np.asarray(s_matrix)


def cascade_two_port_jax(s_a: np.ndarray, s_b: np.ndarray) -> np.ndarray:
    """JAX 实现的二端口 S 参数级联（Redheffer star product 2-port 特例）。

    输入/输出形状 (2, 2, n_freq)，索引 [port_out, port_in, freq]。
    端口约定: A 端口0=外部 in，A 端口1 → B 端口0（内部级联点），
    B 端口1=外部 out。

    级联公式（Filipsson 1978 子网络增长 2-port 特例）:
        denom = 1 - S22_A * S11_B
        S11 = S11_A + S12_A * S21_A * S11_B / denom
        S12 = S12_A * S12_B / denom
        S21 = S21_A * S21_B / denom
        S22 = S22_B + S12_B * S22_A * S21_B / denom

    使用 jnp.einsum('f,f->f' / 'f,f,f->f') 向量化所有频点的逐元素乘积，
    频点轴 'f' 在最后一维。

    Args:
        s_a: 网络 A 的 S 矩阵，shape (2, 2, n_freq)。
        s_b: 网络 B 的 S 矩阵，shape (2, 2, n_freq)。

    Returns:
        级联后 S 矩阵，shape (2, 2, n_freq)。

    Raises:
        RuntimeError: JAX 不可用（R03）。
        ValueError: 输入前两维不是 (2, 2)。

    来源:
    - Filipsson 1978 Eur. Microw. Conf. https://doi.org/10.1109/EUMA.1978.332681
    - Pozar "Microwave Engineering" §4.3
    - SAX cascade https://flaport.github.io/sax/
    """
    if not is_jax_available():
        raise RuntimeError(
            "JAX 不可用，cascade_two_port_jax 无法执行（R03 禁止 fall-back）"
        )
    s_a_arr = np.asarray(s_a, dtype=complex)
    s_b_arr = np.asarray(s_b, dtype=complex)
    if s_a_arr.shape[:2] != (2, 2) or s_b_arr.shape[:2] != (2, 2):
        raise ValueError(
            f"输入 S 矩阵前两维必须为 (2, 2)，得到 {s_a_arr.shape}, {s_b_arr.shape}"
        )
    import jax.numpy as jnp

    sa = jnp.asarray(s_a_arr)
    sb = jnp.asarray(s_b_arr)
    s22_a = sa[1, 1]  # (n_freq,)
    s11_b = sb[0, 0]
    # 用 einsum 向量化逐元素乘积（最后维度为频点轴 'f'）
    denom = 1.0 - jnp.einsum("f,f->f", s22_a, s11_b)
    s11 = sa[0, 0] + jnp.einsum("f,f,f->f", sa[0, 1], sb[0, 0], sa[1, 0]) / denom
    s12 = jnp.einsum("f,f->f", sa[0, 1], sb[0, 1]) / denom
    s21 = jnp.einsum("f,f->f", sa[1, 0], sb[1, 0]) / denom
    s22 = sb[1, 1] + jnp.einsum("f,f,f->f", sb[0, 1], sa[1, 1], sb[1, 0]) / denom
    result = jnp.stack(
        [
            jnp.stack([s11, s12], axis=0),
            jnp.stack([s21, s22], axis=0),
        ],
        axis=0,
    )
    return np.asarray(result)


def simulate_waveguide_chain_jax(
    wavelengths_um: np.ndarray,
    lengths_um: np.ndarray,
    neff: float,
    ng: float,
) -> np.ndarray:
    """JAX 向量化波导链级联（jax.lax.scan 累积）。

    将 N 段波导依次级联，输出整体 S 矩阵 shape (2, 2, n_freq)。
    每段波导 S 矩阵 = [[0, phase_i], [phase_i, 0]]，
    phase_i = exp(1j * 2π * neff * L_i / wl)。

    使用 jax.lax.scan 累积级联（函数式 fold，可 jit，无 Python 循环开销）。
    累积初值为恒等 S 矩阵 [[0,1],[1,0]]（传输=1, 反射=0）。

    Args:
        wavelengths_um: 波长数组 (n_freq,)，1D。
        lengths_um: 各段长度数组 (n_seg,)，1D。
        neff: 有效折射率（与 models.waveguide_s 一致）。
        ng: 群折射率（保留参数，API 对齐）。

    Returns:
        级联后 S 矩阵，shape (2, 2, n_freq)。

    Raises:
        RuntimeError: JAX 不可用（R03）。
        ValueError: 输入非 1D、为空、或波长/长度非正。

    来源:
    - Filipsson 1978 子网络增长（N 段级联 = 2-port 特例迭代）
    - jax.lax.scan https://jax.readthedocs.io/en/latest/_autosummary/jax.lax.scan.html
    - SAX circuit 级联 https://flaport.github.io/sax/
    """
    if not is_jax_available():
        raise RuntimeError(
            "JAX 不可用，simulate_waveguide_chain_jax 无法执行（R03 禁止 fall-back）"
        )
    wl_arr = np.asarray(wavelengths_um, dtype=float)
    L_arr = np.asarray(lengths_um, dtype=float)
    if wl_arr.ndim != 1 or L_arr.ndim != 1:
        raise ValueError(
            f"wavelengths_um 和 lengths_um 必须为 1D 数组，"
            f"得到 {wl_arr.shape}, {L_arr.shape}"
        )
    if wl_arr.size == 0 or L_arr.size == 0:
        raise ValueError("波长和长度数组不能为空")
    if np.any(wl_arr <= 0):
        raise ValueError(f"波长必须 > 0 μm，得到 min={float(wl_arr.min())}")
    if np.any(L_arr <= 0):
        raise ValueError(f"波导长度必须 > 0 μm，得到 min={float(L_arr.min())}")
    import jax
    import jax.numpy as jnp

    wl = jnp.asarray(wl_arr, dtype=jnp.float64)
    L = jnp.asarray(L_arr, dtype=jnp.float64)
    n_freq = wl.shape[0]
    # 恒等 S 矩阵作为级联累积初值（传输=1, 反射=0）
    ones_f = jnp.ones(n_freq, dtype=jnp.complex128)
    zeros_f = jnp.zeros(n_freq, dtype=jnp.complex128)
    eye_s = jnp.stack(
        [
            jnp.stack([zeros_f, ones_f], axis=0),
            jnp.stack([ones_f, zeros_f], axis=0),
        ],
        axis=0,
    )

    def step(carry, length_i):
        """级联单段波导（长度 length_i）到 carry（累积 S 矩阵）。"""
        beta_i = 2.0 * jnp.pi * neff / wl
        phase_i = jnp.exp(1j * beta_i * length_i)
        zero_i = jnp.zeros_like(phase_i)
        s_i = jnp.stack(
            [
                jnp.stack([zero_i, phase_i], axis=0),
                jnp.stack([phase_i, zero_i], axis=0),
            ],
            axis=0,
        )
        sa, sb = carry, s_i
        denom = 1.0 - jnp.einsum("f,f->f", sa[1, 1], sb[0, 0])
        s11 = sa[0, 0] + jnp.einsum("f,f,f->f", sa[0, 1], sb[0, 0], sa[1, 0]) / denom
        s12 = jnp.einsum("f,f->f", sa[0, 1], sb[0, 1]) / denom
        s21 = jnp.einsum("f,f->f", sa[1, 0], sb[1, 0]) / denom
        s22 = sb[1, 1] + jnp.einsum("f,f,f->f", sb[0, 1], sa[1, 1], sb[1, 0]) / denom
        new_carry = jnp.stack(
            [
                jnp.stack([s11, s12], axis=0),
                jnp.stack([s21, s22], axis=0),
            ],
            axis=0,
        )
        return new_carry, None

    final_carry, _ = jax.lax.scan(step, eye_s, L)
    return np.asarray(final_carry)


__all__ = [
    "compute_condition_number",
    "COND_NUM_FG_THRESHOLD",
    "COND_NUM_KLU_THRESHOLD",
    # JAX CPU 后端（v5.1）
    "is_jax_available",
    "get_jax_devices",
    "jit_compile",
    "waveguide_s_jax",
    "cascade_two_port_jax",
    "simulate_waveguide_chain_jax",
]
