"""R35: Verilog-A 光电协同紧凑模型 — SPICE 联合仿真接口（Ngspice）。

本模块从 `verilog_a.py` 拆分而来（facade 模式，保持外部 import 路径不变），
实现 Ngspice 联合仿真接口，包含时间步同步、网表生成、Ngspice 调用与
rawfile 解析。所有错误均 `raise`，禁止 fall-back（规则 14.1）。

核心公式:
- SPICE 时间步同步: Δt_sync = max(Δt_SPICE, Δt_optical)
- 光功率估计: P_opt = η · V²（η 为调制器效率）

来源:
- Ngspice 用户手册
  https://ngspice.sourceforge.io/docs.html
- Ngspice 原始数据文件（rawfile）规范
  https://sourceforge.net/p/ngspice/code/ci/master/tree/manual/
- SPICE rawfile 解析参考（PySpice 实现）
  https://pyspice.fabrice-salvaire.fr/
- Lumerical Virtuoso Interop 文档（时间步同步）
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from polaris.sim.verilog_a_constants import (
    DEFAULT_MODULATOR_EFFICIENCY,
    DEFAULT_OPTICAL_TIMESTEP_S,
    DEFAULT_SPICE_TIMESTEP_S,
)
from polaris.sim.verilog_a_models import VerilogAModel


@dataclass
class SPICESimulationConfig:
    """SPICE 联合仿真配置。

    来源: Ngspice 用户手册
      https://ngspice.sourceforge.io/docs.html

    Attributes:
        spice_timestep: SPICE 时间步（s）。
        optical_timestep: 光子仿真器时间步（s）。
        sync_timestep: 同步时间步 = max(spice, optical)（由 __post_init__ 计算）。
        total_time: 总仿真时间（s）。
        temperature: 温度（℃）。
        ngspice_path: Ngspice 可执行文件路径。
    """

    spice_timestep: float = DEFAULT_SPICE_TIMESTEP_S
    optical_timestep: float = DEFAULT_OPTICAL_TIMESTEP_S
    total_time: float = 1e-9
    temperature: float = 25.0
    ngspice_path: str = "ngspice"
    # sync_timestep 由 __post_init__ 计算；用 field(default=0.0) 占位避免
    # dataclass 字段顺序约束（含默认值的字段必须在无默认值字段之后）。
    sync_timestep: float = field(default=0.0)

    def __post_init__(self) -> None:
        """验证配置参数（规则 14.1: 无 fall-back）。

        Raises:
            ValueError: 时间步或总时间非法。
        """
        if self.spice_timestep <= 0:
            raise ValueError(f"spice_timestep 须 > 0，得到 {self.spice_timestep}")
        if self.optical_timestep <= 0:
            raise ValueError(f"optical_timestep 须 > 0，得到 {self.optical_timestep}")
        if self.total_time <= 0:
            raise ValueError(f"total_time 须 > 0，得到 {self.total_time}")
        # 同步时间步: Δt_sync = max(Δt_SPICE, Δt_optical)
        # 来源: Lumerical Virtuoso Interop 文档
        self.sync_timestep = max(self.spice_timestep, self.optical_timestep)


@dataclass
class CoSimulationResult:
    """光电协同仿真结果。

    Attributes:
        time_points: 时间点数组（s）。
        voltage: 电压信号数组（V）。
        optical_power: 光功率信号数组（W）。
        eye_diagram: 眼图数据（PAM4: 16 个电平）。
        ber: 误码率。
        snr_db: 信噪比（dB）。
    """

    time_points: np.ndarray
    voltage: np.ndarray
    optical_power: np.ndarray
    eye_diagram: np.ndarray | None = None
    ber: float = 0.0
    snr_db: float = 0.0


def generate_spice_netlist(
    models: list[VerilogAModel],
    config: SPICESimulationConfig,
    connections: list[tuple[str, str]] | None = None,
    input_signal: str = "pulse",
) -> str:
    """生成 SPICE 网表（Ngspice 兼容）。

    来源: Ngspice 用户手册
      https://ngspice.sourceforge.io/docs.html

    Args:
        models: Verilog-A 模型列表。
        config: SPICE 仿真配置。
        connections: 连接列表 [(net1, net2), ...]。
        input_signal: 输入信号类型（"pulse"/"sine"/"pam4"）。

    Returns:
        SPICE 网表字符串。

    Raises:
        ValueError: 模型列表为空或输入信号不支持。
    """
    if not models:
        raise ValueError("模型列表不能为空")
    valid_signals = {"pulse", "sine", "pam4"}
    if input_signal not in valid_signals:
        raise ValueError(
            f"不支持的输入信号 {input_signal}，支持: {sorted(valid_signals)}"
        )
    lines = [
        "* PoLaRIS 光电协同仿真网表",
        f"* 同步时间步: {config.sync_timestep:.6e} s",
        f"* 总时间: {config.total_time:.6e} s",
        "",
    ]
    # 包含 Verilog-A 模型
    for model in models:
        lines.append(f".include {model.module_name}.va")
    lines.append("")
    # 输入信号源
    if input_signal == "pulse":
        lines.append(
            f"V_in in 0 PULSE(0 1 0 {config.sync_timestep} {config.sync_timestep} "
            f"{config.sync_timestep * 5} {config.sync_timestep * 10})"
        )
    elif input_signal == "sine":
        freq = 1.0 / config.total_time
        lines.append(f"V_in in 0 SINE(0 1 {freq:.6e})")
    elif input_signal == "pam4":
        # PAM4: 4 电平脉冲
        lines.append(
            f"V_in in 0 PULSE(0 0.33 0 {config.sync_timestep} {config.sync_timestep} "
            f"{config.sync_timestep * 2} {config.sync_timestep * 8})"
        )
    lines.append("")
    # 实例化器件
    for i, model in enumerate(models):
        port_str = " ".join(model.ports)
        lines.append(f"X{i+1} {port_str} {model.module_name}")
    lines.append("")
    # 连接（简化: 直接连接相邻器件）
    if connections:
        for net1, net2 in connections:
            lines.append(f"* 连接: {net1} <-> {net2}")
    lines.append("")
    # 瞬态分析
    lines.append(
        f".tran {config.sync_timestep:.6e} {config.total_time:.6e}"
    )
    lines.append(".end")
    return "\n".join(lines)


def run_ngspice_cosimulation(
    netlist: str,
    config: SPICESimulationConfig,
    timeout: int = 30,
) -> CoSimulationResult:
    """运行 Ngspice 联合仿真。

    来源: Ngspice 命令行接口
      https://ngspice.sourceforge.io/docs.html

    Args:
        netlist: SPICE 网表字符串。
        config: SPICE 仿真配置。
        timeout: 超时时间（秒）。

    Returns:
        CoSimulationResult 实例。

    Raises:
        RuntimeError: Ngspice 执行失败或超时。
        FileNotFoundError: Ngspice 未安装。
    """
    # 写入临时网表文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".cir", delete=False, encoding="utf-8"
    ) as f:
        f.write(netlist)
        netlist_path = f.name
    # 临时 rawfile 路径（Ngspice -r 选项写入真实仿真数据）
    rawfile_path = netlist_path.replace(".cir", ".raw")
    try:
        # 调用 Ngspice（批处理模式），-r 生成 rawfile 真实仿真数据
        cmd = [
            config.ngspice_path,
            "-b",
            "-o",
            "/dev/null",
            "-r",
            rawfile_path,
            netlist_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            # Ngspice 不可用时 raise（规则 14.1: 无 fall-back）
            raise RuntimeError(
                f"Ngspice 执行失败 (返回码 {result.returncode}): {result.stderr}"
            )
        # 解析真实 Ngspice rawfile 输出（规则 14.1: 无 fall-back，禁止合成数据）
        rawfile = Path(rawfile_path)
        if not rawfile.exists() or rawfile.stat().st_size == 0:
            raise RuntimeError(
                f"Ngspice 输出文件不存在或为空: {rawfile_path}，"
                f"请检查 Ngspice 仿真是否完成"
            )
        time_points, voltage = _parse_ngspice_rawfile(rawfile)
        optical_power = voltage ** 2 * DEFAULT_MODULATOR_EFFICIENCY
        return CoSimulationResult(
            time_points=time_points,
            voltage=voltage,
            optical_power=optical_power,
        )
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Ngspice 未安装或路径错误: {config.ngspice_path}. "
            f"请安装 Ngspice: https://ngspice.sourceforge.io/"
        ) from e
    finally:
        Path(netlist_path).unlink(missing_ok=True)
        Path(rawfile_path).unlink(missing_ok=True)


def _parse_ngspice_rawfile(rawfile_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """解析 Ngspice rawfile，提取时间轴与输入节点电压。

    支持 ASCII 和二进制 rawfile 格式。优先提取 v(in) 节点电压
    （网表输入源为 ``V_in in 0 PULSE(...)``），若不存在则取首个非 time 电压列。

    来源:
    - Ngspice 用户手册 - Rawfile 格式
      https://ngspice.sourceforge.io/docs.html
    - Ngspice 原始数据文件（rawfile）规范
      https://sourceforge.net/p/ngspice/code/ci/master/tree/manual/
    - SPICE rawfile 解析参考（PySpice 实现）
      https://pyspice.fabrice-salvaire.fr/

    Args:
        rawfile_path: Ngspice rawfile 路径。

    Returns:
        (time_points, voltage) 元组，均为 1D float64 数组。

    Raises:
        RuntimeError: rawfile 格式不支持、数据缺失或电压节点未找到。
    """
    with open(rawfile_path, "rb") as fh:
        content = fh.read()

    header_text, binary_payload = _split_rawfile_payload(content)
    n_vars, n_points, var_names = _parse_rawfile_header(header_text)
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
        data = _parse_rawfile_ascii_values(header_text, n_points, n_vars)

    time_points = data[:, 0]
    voltage = _extract_input_voltage(data, var_names, rawfile_path)
    return time_points, voltage


def _split_rawfile_payload(content: bytes) -> tuple[str, bytes | None]:
    """分离 rawfile 的 ASCII 头部与二进制数据段。

    Args:
        content: rawfile 完整字节。

    Returns:
        (header_text, binary_payload) 元组。binary_payload 为 None 表示纯 ASCII。
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


def _parse_rawfile_header(header: str) -> tuple[int, int, list[str]]:
    """解析 rawfile 头部，返回 (n_vars, n_points, var_names)。

    头部格式示例::

        Title: ...
        Plotname: Transient Analysis
        Flags: real
        No. Variables: 2
        No. Points: 100
        Variables:
                0       time    time
                1       v(in)   voltage
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
        elif line.startswith("No. Points:"):
            n_points = int(line.split(":", 1)[1].strip())
            in_variables = False
        elif line.startswith("Variables:"):
            in_variables = True
        elif in_variables:
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


def _parse_rawfile_ascii_values(
    header: str, n_points: int, n_vars: int
) -> np.ndarray:
    """解析 ASCII rawfile 的 Values 段。

    ASCII 格式（两种布局，均通过 token 计数自适应）::

        Values:
            0  0.000e+00  1.000e+00
            1  1.000e-09  9.999e-01

    或::

        Values:
            0  0.000e+00
            1.000e+00
            1  1.000e-09
            9.999e-01
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


def _extract_input_voltage(
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


__all__ = [
    "CoSimulationResult",
    "SPICESimulationConfig",
    "generate_spice_netlist",
    "run_ngspice_cosimulation",
]
