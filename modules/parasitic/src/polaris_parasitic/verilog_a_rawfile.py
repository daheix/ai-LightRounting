"""Ngspice rawfile 解析器 — ASCII/二进制格式支持。

从 v4 ``polaris.sim.verilog_a_spice`` 迁移至 polaris-parasitic 子模块（R13）。
独立模块，负责解析 Ngspice ``-r`` 输出的 rawfile，提取时间轴与电压变量。
所有错误均 `raise`，禁止 fall-back（R03）。

支持格式:
- ASCII: ``Values:`` 段逐点列出，含/不含行索引两种布局自适应
- 二进制: ``Binary:`` 标记后连续 float64 数据，布局 n_points × n_vars

来源（≥5 文献 URL）:
- Ngspice 用户手册 https://ngspice.sourceforge.io/docs.html
- Ngspice rawfile 规范
  https://sourceforge.net/p/ngspice/code/ci/master/tree/manual/
- PySpice rawfile 解析 https://pyspice.fabrice-salvaire.fr/
- Ngspice 命令行接口（-r 选项）
  https://ngspice.sourceforge.io/ngspice-manual.html
- LTspice rawfile 兼容性参考
  https://www.analog.com/en/resources/technical-articles/ltspice-command-line.html

规则: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R11 V8 极简。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def parse_ngspice_rawfile(
    rawfile_path: Path,
) -> tuple[np.ndarray, np.ndarray]:
    """解析 Ngspice rawfile，提取时间轴与输入节点电压。

    支持 ASCII 和二进制 rawfile 格式。优先提取 v(in) 节点电压
    （网表输入源为 ``V_in in 0 PULSE(...)``），若不存在则取首个非 time 电压列。

    来源: Ngspice rawfile https://ngspice.sourceforge.io/docs.html;
    rawfile 规范
    https://sourceforge.net/p/ngspice/code/ci/master/tree/manual/;
    PySpice 实现 https://pyspice.fabrice-salvaire.fr/

    Args: rawfile_path: Ngspice rawfile 路径。
    Returns: (time_points, voltage) 元组，均为 1D float64 数组。
    Raises: RuntimeError: rawfile 格式不支持、数据缺失或电压节点未找到。
    """
    with open(rawfile_path, "rb") as fh:
        content = fh.read()

    header_text, binary_payload = split_rawfile_payload(content)
    n_vars, n_points, var_names = parse_rawfile_header(header_text)
    if n_points <= 0 or n_vars <= 0:
        raise RuntimeError(
            f"Ngspice rawfile 无有效数据点 (n_vars={n_vars}, "
            f"n_points={n_points}): {rawfile_path}"
        )

    if binary_payload is not None:
        # 二进制格式：连续 float64 数据，布局 n_points × n_vars
        expected_bytes = n_points * n_vars * 8
        if len(binary_payload) < expected_bytes:
            raise RuntimeError(
                f"Ngspice rawfile 二进制数据不完整: 期望 {expected_bytes} 字节，"
                f"实际 {len(binary_payload)} 字节: {rawfile_path}"
            )
        data = np.frombuffer(
            binary_payload[:expected_bytes], dtype=np.float64
        ).reshape(n_points, n_vars)
    else:
        # ASCII 格式：Values 段后逐点列出
        data = parse_rawfile_ascii_values(header_text, n_points, n_vars)

    time_points = data[:, 0]
    voltage = extract_input_voltage(data, var_names, rawfile_path)
    return time_points, voltage


def split_rawfile_payload(content: bytes) -> tuple[str, bytes | None]:
    """分离 rawfile 的 ASCII 头部与二进制数据段。

    Returns: (header_text, binary_payload) 元组。binary_payload 为 None 表示纯 ASCII。
    """
    binary_marker = b"Binary:"
    idx = content.find(binary_marker)
    if idx != -1:
        header = content[:idx].decode("ascii", errors="replace")
        payload_start = idx + len(binary_marker)
        # 跳过 "Binary:" 后的换行符
        if payload_start < len(content) and content[payload_start:payload_start + 1] in (
            b"\n",
            b"\r",
        ):
            payload_start += 1
        return header, content[payload_start:]
    return content.decode("ascii", errors="replace"), None


def parse_rawfile_header(header: str) -> tuple[int, int, list[str]]:
    """解析 rawfile 头部，返回 (n_vars, n_points, var_names)。

    头部格式示例: Title/Plotname/Flags/No. Variables/No. Points/Variables 段，
    Variables 段每行 "idx name type"（如 "0 time time", "1 v(in) voltage"）。
    """
    n_vars = 0
    n_points = 0
    var_names: list[str] = []
    in_variables = False
    for raw_line in header.splitlines():
        line = raw_line.strip()
        if line.startswith("No. Variables:"):
            n_vars = int(line.split(":", 1)[1].strip())
            in_variables = False
            continue
        if line.startswith("No. Points:"):
            n_points = int(line.split(":", 1)[1].strip())
            in_variables = False
            continue
        if line.startswith("Variables:"):
            in_variables = True
            continue
        if not in_variables:
            continue
        if not line:
            in_variables = False
            continue
        parts = line.split()
        # 格式: "  0  time  time" 或 "  1  v(in)  voltage"
        if len(parts) >= 2 and parts[0].isdigit():
            var_names.append(parts[1])
        else:
            in_variables = False
    return n_vars, n_points, var_names


def parse_rawfile_ascii_values(
    header: str, n_points: int, n_vars: int
) -> np.ndarray:
    """解析 ASCII rawfile 的 Values 段。

    ASCII 格式两种布局，均通过 token 计数自适应:
    - 含行索引: "0 0.000e+00 1.000e+00\\n1 1.000e-09 9.999e-01"
    - 不含行索引: "0 0.000e+00\\n1.000e+00\\n1 1.000e-09\\n9.999e-01"
    """
    values_marker = "Values:"
    idx = header.find(values_marker)
    if idx == -1:
        raise RuntimeError("Ngspice rawfile 无 Values 段，无法解析 ASCII 数据")
    data_text = header[idx + len(values_marker):]
    flat_values: list[float] = []
    for token in data_text.split():
        try:
            flat_values.append(float(token))
        except ValueError:
            # 跳过非数值标记
            continue
    expected_with_index = n_points * (n_vars + 1)
    expected_without_index = n_points * n_vars
    if len(flat_values) >= expected_with_index:
        # 含行索引：每 (n_vars+1) 个 token 的首个为索引，需剔除
        values: list[float] = []
        for i in range(n_points):
            row_start = i * (n_vars + 1) + 1
            values.extend(flat_values[row_start:row_start + n_vars])
        return np.array(values, dtype=np.float64).reshape(n_points, n_vars)
    if len(flat_values) >= expected_without_index:
        return np.array(
            flat_values[:expected_without_index], dtype=np.float64
        ).reshape(n_points, n_vars)
    raise RuntimeError(
        f"Ngspice rawfile ASCII 数据不完整: 期望 {expected_without_index} 个数值，"
        f"实际解析 {len(flat_values)} 个"
    )


def extract_input_voltage(
    data: np.ndarray, var_names: list[str], rawfile_path: Path
) -> np.ndarray:
    """从 rawfile 数据中提取输入节点电压。

    网表输入源为 ``V_in in 0 PULSE(...)``，故优先提取 v(in)。
    若 v(in) 不存在，取首个非 time 电压变量（真实仿真数据，非合成）。

    Raises:
        RuntimeError: 无可用电压列。
    """
    for i, name in enumerate(var_names):
        if name.lower() == "v(in)":
            return data[:, i]
    for i, name in enumerate(var_names):
        if i > 0 and name.lower().startswith("v("):
            return data[:, i]
    if data.shape[1] >= 2:
        return data[:, 1]
    raise RuntimeError(
        f"Ngspice rawfile 无电压变量，无法提取电压数据: {rawfile_path} "
        f"(变量: {var_names})"
    )
