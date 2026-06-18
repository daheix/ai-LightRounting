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
                parts = line[1:].strip().lower().split()
                for p in parts:
                    if p in ("hz", "khz", "mhz", "ghz"):
                        freq_unit = p
                    elif p in ("ri", "ma", "db"):
                        s_format = p
                continue
            # 数据行
            parts = line.split()
            freq = float(parts[0])
            freqs.append(freq)
            s_vals = [float(x) for x in parts[1:]]
            s_data.append(s_vals)
            if n_ports == 0:
                n_ports = int(math.isqrt(len(s_vals) // 2))

    freqs_arr = np.array(freqs)
    # 频率单位转换到 Hz
    unit_mult = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
    freqs_arr = freqs_arr * unit_mult.get(freq_unit, 1e9)

    # 解析 S 参数
    s_matrix = np.zeros((len(freqs_arr), n_ports, n_ports), dtype=complex)
    for i, svals in enumerate(s_data):
        idx = 0
        for j in range(n_ports):
            for k in range(n_ports):
                re = svals[idx]
                im = svals[idx + 1]
                idx += 2
                if s_format == "ri":
                    s_matrix[i, j, k] = complex(re, im)
                elif s_format == "ma":
                    s_matrix[i, j, k] = re * np.exp(1j * np.radians(im))
                elif s_format == "db":
                    s_matrix[i, j, k] = 10.0 ** (re / 20.0) * np.exp(1j * np.radians(im))

    # 转换为 SDict 格式
    port_names = [f"port_{i + 1}" for i in range(n_ports)]
    sdict: SDict = {}
    for j in range(n_ports):
        for k in range(n_ports):
            sdict[(port_names[j], port_names[k])] = s_matrix[:, j, k]

    return freqs_arr, sdict


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
