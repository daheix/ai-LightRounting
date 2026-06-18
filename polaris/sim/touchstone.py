"""Touchstone .s2p/.snp 文件加载与保存。

Touchstone 格式是 RF/光子业界标准的 S 参数数据交换格式。
文件结构：
- 注释行以 ! 开头
- 选项行以 # 开头（频率单位、S 参数格式等）
- 数据行：频率 S11 S21 S12 S22 ...（实部 虚部 对）

来源:
- Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file
- scikit-rf Touchstone 加载: https://scikit-rf.readthedocs.io/
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from polaris.sim.types import SDict


def _parse_option_line(line: str, freq_unit: str, s_format: str) -> tuple[str, str]:
    """解析 Touchstone 选项行，返回更新后的 (频率单位, S 参数格式)。

    选项行格式: # frequency_unit S parameter_format R impedance

    来源:
    - Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file

    Args:
        line: 选项行文本（以 # 开头）。
        freq_unit: 当前频率单位（保留未指定时沿用）。
        s_format: 当前 S 参数格式（保留未指定时沿用）。

    Returns:
        更新后的 (freq_unit, s_format) 元组。
    """
    parts = line[1:].strip().lower().split()
    for p in parts:
        if p in ("hz", "khz", "mhz", "ghz"):
            freq_unit = p
        elif p in ("ri", "ma", "db"):
            s_format = p
    return freq_unit, s_format


def _convert_s_value(re: float, im: float, s_format: str) -> complex:
    """根据格式将 S 参数实部/虚部转换为复数值。

    支持的格式：
    - ri: 实部-虚部直角坐标
    - ma: 幅度-角度（度）
    - db: 分贝-角度（度）

    来源:
    - Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file

    Args:
        re: 实部（或幅度/分贝值）。
        im: 虚部（或角度，单位度）。
        s_format: S 参数格式（ri/ma/db）。

    Returns:
        转换后的复数 S 参数值。
    """
    if s_format == "ri":
        return complex(re, im)
    if s_format == "ma":
        return re * np.exp(1j * np.radians(im))
    if s_format == "db":
        return 10.0 ** (re / 20.0) * np.exp(1j * np.radians(im))
    return complex(re, im)


def _build_sdict(s_matrix: np.ndarray, n_ports: int) -> SDict:
    """将 S 参数矩阵转换为 SDict 格式。

    端口名按 port_1, port_2, ... 编号。

    来源:
    - SAX 类型系统: https://flaport.github.io/sax/

    Args:
        s_matrix: S 参数矩阵，形状 (n_freq, n_ports, n_ports)。
        n_ports: 端口数。

    Returns:
        S 参数字典，键为 (port_out, port_in) 元组。
    """
    port_names = [f"port_{i + 1}" for i in range(n_ports)]
    sdict: SDict = {}
    for j in range(n_ports):
        for k in range(n_ports):
            sdict[(port_names[j], port_names[k])] = s_matrix[:, j, k]
    return sdict


def _read_touchstone_lines(
    filepath: Path,
) -> tuple[list[float], list[list[float]], int, str, str]:
    """读取 Touchstone 文件，返回原始频率、S 数据与格式信息。

    来源:
    - Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file

    Args:
        filepath: Touchstone 文件路径。

    Returns:
        (频率列表, S 数据列表, 端口数, 频率单位, S 参数格式)。
    """
    freqs: list[float] = []
    s_data: list[list[float]] = []
    n_ports = 0
    freq_unit = "ghz"  # 默认 GHz
    s_format = "ri"  # 默认实部-虚部格式

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            if line.startswith("#"):
                # 选项行: # frequency_unit S parameter_format R impedance
                freq_unit, s_format = _parse_option_line(line, freq_unit, s_format)
                continue
            # 数据行
            parts = line.split()
            freqs.append(float(parts[0]))
            s_vals = [float(x) for x in parts[1:]]
            s_data.append(s_vals)
            if n_ports == 0:
                n_ports = int(math.isqrt(len(s_vals) // 2))

    return freqs, s_data, n_ports, freq_unit, s_format


def _build_s_matrix(
    freqs_arr: np.ndarray,
    s_data: list[list[float]],
    n_ports: int,
    s_format: str,
) -> np.ndarray:
    """从原始 S 数据构建 S 参数矩阵。

    来源:
    - Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file

    Args:
        freqs_arr: 频率数组（已转换单位）。
        s_data: 每行原始 S 参数实部/虚部列表。
        n_ports: 端口数。
        s_format: S 参数格式（ri/ma/db）。

    Returns:
        S 参数矩阵，形状 (n_freq, n_ports, n_ports)。
    """
    s_matrix = np.zeros((len(freqs_arr), n_ports, n_ports), dtype=complex)
    for i, svals in enumerate(s_data):
        idx = 0
        for j in range(n_ports):
            for k in range(n_ports):
                re = svals[idx]
                im = svals[idx + 1]
                idx += 2
                s_matrix[i, j, k] = _convert_s_value(re, im, s_format)
    return s_matrix


def load_touchstone(filepath: str | Path) -> tuple[np.ndarray, SDict]:
    """加载 Touchstone S 参数文件（.s2p/.s3p/.snp 格式）。

    来源:
    - Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file
    - scikit-rf Touchstone 加载: https://scikit-rf.readthedocs.io/

    Args:
        filepath: Touchstone 文件路径。

    Returns:
        (频率数组, S 参数字典)，频率单位 Hz，S 参数为复数数组。
    """
    filepath = Path(filepath)
    # 读取文件（提取为辅助函数降低函数行数与圈复杂度，规则 4.1/4.3）
    freqs, s_data, n_ports, freq_unit, s_format = _read_touchstone_lines(filepath)

    freqs_arr = np.array(freqs)
    # 频率单位转换到 Hz
    unit_mult = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
    freqs_arr = freqs_arr * unit_mult.get(freq_unit, 1e9)

    # 解析 S 参数（提取为辅助函数降低函数行数与圈复杂度，规则 4.1/4.3）
    s_matrix = _build_s_matrix(freqs_arr, s_data, n_ports, s_format)

    # 转换为 SDict 格式
    return freqs_arr, _build_sdict(s_matrix, n_ports)


def save_touchstone(
    filepath: str | Path,
    freqs: np.ndarray,
    sdict: SDict,
    freq_unit: str = "ghz",
    port_names: list[str] | None = None,
) -> None:
    """保存 S 参数到 Touchstone 文件。

    来源: Touchstone 文件规范 https://en.wikipedia.org/wiki/Touchstone_file

    Args:
        filepath: 输出文件路径。
        freqs: 频率数组（Hz）。
        sdict: S 参数字典。
        freq_unit: 频率单位（hz/khz/mhz/ghz）。
        port_names: 端口名列表（决定端口顺序）。
    """
    filepath = Path(filepath)
    if port_names is None:
        # 从 sdict 键推断端口名
        names = set()
        for p_out, p_in in sdict:
            names.add(p_out)
            names.add(p_in)
        port_names = sorted(names)
    n_ports = len(port_names)

    unit_div = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
    div = unit_div.get(freq_unit, 1e9)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {freq_unit} S RI R 50\n")
        f.write(f"! PoLaRIS generated Touchstone file ({n_ports} ports)\n")
        for i, freq in enumerate(freqs):
            parts = [f"{freq / div:.6e}"]
            for p_out in port_names:
                for p_in in port_names:
                    key = (p_out, p_in)
                    val = sdict.get(key, np.zeros(len(freqs), dtype=complex))[i]
                    parts.append(f"{val.real:.6e}")
                    parts.append(f"{val.imag:.6e}")
            f.write(" ".join(parts) + "\n")
