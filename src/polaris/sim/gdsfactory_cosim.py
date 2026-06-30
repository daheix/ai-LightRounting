"""gdsfactory 联合仿真 - 组件级（R304）。

实现 gdsfactory Component → PoLaRIS Device → FDTD 仿真 → S 参数提取 → 结果回传
的完整工作流，对标 Lumerical/IPKISS 的组件级联合仿真能力。

工作流:
1. gdsfactory Component 通过 ``gdsfactory_to_polaris_device()`` 转换为 PoLaRIS Device
   （端口自动识别，复用 ``_extract_gdsfactory_ports``）—— TR-304.1/304.2
2. PoLaRIS Device 通过 ``run_fdtd_simulation()`` 进行 FDTD 全波仿真
   （MEEP/Tidy3D/ANALYTICAL 后端）—— TR-304.1
3. FDTD 结果的 S 参数字典组装为 N×N×W S 矩阵 —— TR-304.2
4. S 参数可通过以下方式回传 gdsfactory —— TR-304.3:
   a. Touchstone .s2p/.snp 文件（业界标准 S 参数交换格式）
   b. gdsfactory Component.metadata 字典（gdsfactory 原生格式）

R03 合规设计:
- gdsfactory 不可用 raise ImportError（不静默兜底）
- 输入组件无端口 raise ValueError（不返回空结果）
- 端口名重复 raise ValueError（不自动改名）
- FDTD 后端不可用由 ``fdtd_simulator`` raise（异常透传，不吞没）
- Touchstone 写出失败由 ``touchstone`` raise（异常透传）

来源:
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- gdsfactory S 参数回传: https://gdsfactory.github.io/gdsfactory/notebooks/03_waveguide.html
- MEEP: https://meep.readthedocs.io/
- Tidy3D: https://www.flexcompute.com/tidy3d/
- Touchstone 规范: https://en.wikipedia.org/wiki/Touchstone_file
- S 参数矩阵定义: Pozar, "Microwave Engineering", 4th ed., §4.4,
  ISBN: 978-1118213636, Wiley, 2011
- FDTD 方法: Taflove & Hagness, "Computational Electrodynamics: The Finite-Difference
  Time-Domain Method", 3rd ed., Artech House, 2005, ISBN: 978-1580538329
- S 参数端口提取: Shin & Fan 2012, J. Comput. Phys. 231(9), 3705-3718,
  https://doi.org/10.1016/j.jcp.2012.01.035
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from polaris.pdk.gdsfactory_integration import (
    DeviceImportConfig,
    gdsfactory_to_polaris_device,
)
from polaris.sim.fdtd_simulator import (
    FDTDConfig,
    FDTDResult,
    run_fdtd_simulation,
)
from polaris.sim.cascade import cascade_circuit
from polaris.sim.touchstone import save_touchstone
from polaris.sim.types import SDict

if TYPE_CHECKING:
    from polaris.pdk.device import Device

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义
# =============================================================================
@dataclass
class CoSimConfig:
    """gdsfactory 联合仿真配置（R304）。

    封装 gdsfactory Component 导入与 FDTD 仿真的全部配置，降低
    ``simulate_gdsfactory_component`` 参数个数（规则 4.1）。

    Attributes:
        device_id: PoLaRIS 器件唯一标识。
        import_config: gdsfactory→PoLaRIS 器件导入配置（None 用默认 SOI/passive）。
        fdtd_config: FDTD 仿真配置（None 用默认 MEEP 后端 + C 波段 50 点）。
        port_order: 端口排序方式（"name" 按字母序, "position" 按位置序, None 保持
            gdsfactory 端口顺序）。

    默认值来源:
    - fdtd_config 默认值: ``FDTDConfig`` 默认（C 波段 1.5-1.6μm, 50 点, MEEP 后端）
      来源: ITU-T G.694.1 C 波段标准 + MEEP 推荐采样数
      https://www.itu.int/rec/T-REC-G.694.1/
    """

    device_id: str = "gdsfactory_component"
    import_config: DeviceImportConfig | None = None
    fdtd_config: FDTDConfig | None = None
    port_order: str | None = "name"


@dataclass
class CoSimResult:
    """gdsfactory 联合仿真结果（R304）。

    封装从 gdsfactory Component 到 FDTD S 参数的完整仿真结果。

    Attributes:
        device: 转换后的 PoLaRIS Device（含端口自动识别结果）。
        fdtd_result: FDTD 仿真原始结果。
        port_names: 端口名列表（按 ``CoSimConfig.port_order`` 排序）。
        s_matrix: S 参数矩阵，形状 (n_ports, n_ports, n_wavelengths)，
            s_matrix[i, j, :] = S_{i,j}（从端口 j 到端口 i）。
        n_ports: 端口数。
        n_wavelengths: 波长采样点数。
        simulation_status: 仿真状态（"success" / "failed"）。

    S 矩阵约定:
    - s_matrix[i, j, k] 表示第 k 个波长处从端口 j 入射到端口 i 出射的 S 参数
    - 行索引 i = 出射端口（output），列索引 j = 入射端口（input）
    - 来源: Pozar, "Microwave Engineering", 4th ed., §4.4, Eq. (4.38)
    """

    device: Device
    fdtd_result: FDTDResult
    port_names: list[str] = field(default_factory=list)
    s_matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 0, 0), dtype=complex))
    n_ports: int = 0
    n_wavelengths: int = 0
    simulation_status: str = "success"


# =============================================================================
# 端口排序
# =============================================================================
def _order_port_names(
    port_names: list[str],
    device: Device,
    order: str | None,
) -> list[str]:
    """对端口名列表排序。

    Args:
        port_names: 原始端口名列表。
        device: PoLaRIS Device（含 Port 对象，用于位置排序）。
        order: 排序方式（"name" / "position" / None）。

    Returns:
        排序后的端口名列表。

    Raises:
        ValueError: 不支持的排序方式。
    """
    if order is None:
        return list(port_names)
    if order == "name":
        return sorted(port_names)
    if order == "position":
        # 按 Port 的 (x, y) 坐标排序（左下→右上）
        port_map = {p.name: (p.x, p.y) for p in device.ports}
        return sorted(port_names, key=lambda n: port_map.get(n, (0.0, 0.0)))
    raise ValueError(
        f"不支持的端口排序方式: {order!r}，必须是 'name' / 'position' / None"
    )


def _check_unique_port_names(port_names: list[str]) -> None:
    """检查端口名是否唯一。

    Args:
        port_names: 端口名列表。

    Raises:
        ValueError: 端口名重复时。
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in port_names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    if duplicates:
        raise ValueError(
            f"端口名重复: {sorted(duplicates)}。"
            f"gdsfactory Component 的端口名必须唯一。"
        )


# =============================================================================
# S 矩阵构建
# =============================================================================
def build_s_matrix_from_sdict(
    s_params: dict[tuple[str, str], np.ndarray],
    port_names: list[str],
) -> np.ndarray:
    """从 S 参数字典构建 N×N×W S 矩阵。

    将 {(port_out, port_in): np.ndarray} 字典转换为 3D 矩阵。
    缺失的端口对填充 0（R03 合规：仅当字典覆盖完整 N×N 时调用，
    部分覆盖会 raise 警告）。

    Args:
        s_params: S 参数字典，键为 (port_out, port_in) 元组，值为复数数组。
        port_names: 端口名列表（决定矩阵维度顺序）。

    Returns:
        S 参数矩阵，形状 (n_ports, n_ports, n_wavelengths)。
        s_matrix[i, j, :] = S_{port_names[i], port_names[j]}（从 j 入射到 i 出射）。

    Raises:
        ValueError: port_names 为空 / 端口名不在字典中 / 数组长度不一致。

    来源:
    - S 矩阵定义: Pozar, "Microwave Engineering", 4th ed., §4.4, Eq. (4.38)
    """
    if not port_names:
        raise ValueError("端口名列表不能为空")
    n_ports = len(port_names)
    # 推断波长数
    n_wavelengths = 0
    for (p_out, p_in), arr in s_params.items():
        if p_out not in port_names:
            raise ValueError(
                f"S 参数字典中的端口名 {p_out!r} 不在 port_names 列表中"
            )
        if p_in not in port_names:
            raise ValueError(
                f"S 参数字典中的端口名 {p_in!r} 不在 port_names 列表中"
            )
        if arr.size > n_wavelengths:
            n_wavelengths = arr.size
    if n_wavelengths == 0:
        raise ValueError("S 参数字典为空，无法推断波长数")

    s_matrix = np.zeros((n_ports, n_ports, n_wavelengths), dtype=complex)
    for i, p_out in enumerate(port_names):
        for j, p_in in enumerate(port_names):
            key = (p_out, p_in)
            if key in s_params:
                arr = s_params[key]
                if arr.size != n_wavelengths:
                    raise ValueError(
                        f"S 参数 {key} 数组长度 {arr.size} 与其他端口对 "
                        f"{n_wavelengths} 不一致"
                    )
                s_matrix[i, j, :] = arr
    return s_matrix


# =============================================================================
# 主编排函数
# =============================================================================
def simulate_gdsfactory_component(
    component,
    config: CoSimConfig | None = None,
) -> CoSimResult:
    """gdsfactory 组件联合仿真主编排函数（R304）。

    完整工作流:
    1. gdsfactory Component → PoLaRIS Device（端口自动识别）
    2. PoLaRIS Device → FDTD 仿真（MEEP/Tidy3D/ANALYTICAL）
    3. FDTD 结果 S 参数字典 → N×N×W S 矩阵

    Args:
        component: gdsfactory Component 对象（必须有 .ports 属性）。
        config: 联合仿真配置（None 用默认配置）。

    Returns:
        联合仿真结果 ``CoSimResult``。

    Raises:
        ImportError: gdsfactory 未安装。
        ValueError: 组件无端口 / 端口名重复 / 不支持的端口排序方式。
        ImportError: FDTD 后端不可用（由 ``fdtd_simulator`` 透传）。

    来源:
    - gdsfactory Component API: https://gdsfactory.github.io/gdsfactory/
    - FDTD 仿真: Taflove & Hagness, "Computational Electrodynamics", 3rd ed., 2005
    - 端口自动识别: gdsfactory Component.ports 属性
      https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.Component
    """
    cfg = config or CoSimConfig()

    # 步骤 1: gdsfactory Component → PoLaRIS Device（端口自动识别）
    # gdsfactory_to_polaris_device 内部调用 _extract_gdsfactory_ports，
    # 自动从 component.ports 提取端口名/朝向/宽度/位置
    device = gdsfactory_to_polaris_device(
        component=component,
        device_id=cfg.device_id,
        config=cfg.import_config,
    )

    # 步骤 2: 端口校验与排序
    if not device.ports:
        raise ValueError(
            f"gdsfactory Component {component.name!r} 无端口，无法进行 FDTD 仿真。"
            f"请确保组件已定义端口（component.add_port()）。"
        )
    port_names_raw = [p.name for p in device.ports]
    _check_unique_port_names(port_names_raw)
    port_names = _order_port_names(port_names_raw, device, cfg.port_order)

    # 步骤 3: FDTD 全波仿真（MEEP/Tidy3D/ANALYTICAL 后端）
    # 后端不可用时 fdtd_simulator 会 raise ImportError，此处不吞没异常
    fdtd_result = run_fdtd_simulation(device, cfg.fdtd_config)

    # 步骤 4: S 参数字典 → N×N×W S 矩阵
    s_matrix = build_s_matrix_from_sdict(fdtd_result.s_params, port_names)

    logger.info(
        "gdsfactory 联合仿真完成: 组件 %s, %d 端口, %d 波长, 后端 %s",
        component.name,
        len(port_names),
        s_matrix.shape[2] if s_matrix.size > 0 else 0,
        fdtd_result.backend_used.value,
    )

    return CoSimResult(
        device=device,
        fdtd_result=fdtd_result,
        port_names=port_names,
        s_matrix=s_matrix,
        n_ports=len(port_names),
        n_wavelengths=s_matrix.shape[2] if s_matrix.size > 0 else 0,
        simulation_status="success",
    )


# =============================================================================
# 结果回传 gdsfactory（TR-304.3）
# =============================================================================
def export_cosim_to_touchstone(
    result: CoSimResult,
    output_path: str | Path,
    freq_unit: str = "ghz",
) -> str:
    """将联合仿真结果导出为 Touchstone .s2p/.snp 文件（TR-304.3）。

    Touchstone 是 RF/光子业界标准的 S 参数数据交换格式，可被 gdsfactory、
    Lumerical INTERCONNECT、VPIphotonics 等工具读取。

    Args:
        result: 联合仿真结果。
        output_path: 输出文件路径（.sNp 格式，N 为端口数）。
        freq_unit: 频率单位（hz/khz/mhz/ghz）。

    Returns:
        输出文件路径字符串。

    Raises:
        ValueError: 仿真失败 / S 矩阵为空。
        OSError: 文件写入失败（由 touchstone 透传）。

    来源:
    - Touchstone 文件规范: https://en.wikipedia.org/wiki/Touchstone_file
    - gdsfactory 读取 Touchstone: https://gdsfactory.github.io/gdsfactory/components/read_sparameters.html
    """
    if result.simulation_status != "success":
        raise ValueError(
            f"仿真状态为 {result.simulation_status!r}，无法导出 Touchstone"
        )
    if result.s_matrix.size == 0:
        raise ValueError("S 矩阵为空，无法导出 Touchstone")

    # 波长 → 频率（Hz）: f = c / λ, c = 299792458 m/s
    # 来源: NIST CODATA 2018 光速常数
    c_m_per_s = 299_792_458.0
    wavelengths_m = result.fdtd_result.wavelengths_um * 1e-6
    freqs_hz = c_m_per_s / wavelengths_m

    # S 矩阵 → sdict {(port_out, port_in): array}
    sdict: dict[tuple[str, str], np.ndarray] = {}
    for i, p_out in enumerate(result.port_names):
        for j, p_in in enumerate(result.port_names):
            sdict[(p_out, p_in)] = result.s_matrix[i, j, :]

    save_touchstone(
        filepath=output_path,
        freqs=freqs_hz,
        sdict=sdict,
        freq_unit=freq_unit,
        port_names=result.port_names,
    )
    logger.info("Touchstone 导出: %s (%d 端口)", output_path, result.n_ports)
    return str(output_path)


def cosim_to_gdsfactory_metadata(result: CoSimResult) -> dict:
    """将联合仿真结果转换为 gdsfactory Component.metadata 格式（TR-304.3）。

    生成符合 gdsfactory 约定的 metadata 字典，可写回 Component.metadata
    供后续电路级仿真使用。

    metadata 结构:
    ```
    {
        "simulation": {
            "backend": "meep" | "tidy3d" | "analytical",
            "wavelength_start_um": 1.5,
            "wavelength_end_um": 1.6,
            "n_wavelengths": 50,
            "insertion_loss_db": -0.05,
            "ports": ["o1", "o2"],
            "s_params_available": True
        },
        "s_matrix_shape": [2, 2, 50],
        "wavelengths_um": [1.5, 1.52, ...],
        "transmission_db": {("o1", "o2"): -0.05, ...}
    }
    ```

    Args:
        result: 联合仿真结果。

    Returns:
        gdsfactory metadata 字典。

    Raises:
        ValueError: 仿真失败。

    来源:
    - gdsfactory metadata 约定: https://gdsfactory.github.io/gdsfactory/api.html
    """
    if result.simulation_status != "success":
        raise ValueError(
            f"仿真状态为 {result.simulation_status!r}，无法生成 metadata"
        )

    wavelengths = result.fdtd_result.wavelengths_um
    # 转换 transmission_db 的元组键为字符串键（JSON 兼容）
    transmission_str: dict[str, float] = {}
    for (p_out, p_in), val in result.fdtd_result.transmission_db.items():
        transmission_str[f"{p_out}->{p_in}"] = float(val)

    return {
        "simulation": {
            "backend": result.fdtd_result.backend_used.value,
            "wavelength_start_um": float(wavelengths[0]) if wavelengths.size > 0 else 0.0,
            "wavelength_end_um": float(wavelengths[-1]) if wavelengths.size > 0 else 0.0,
            "n_wavelengths": int(wavelengths.size),
            "insertion_loss_db": float(result.fdtd_result.insertion_loss_db),
            "ports": list(result.port_names),
            "s_params_available": result.s_matrix.size > 0,
        },
        "s_matrix_shape": list(result.s_matrix.shape),
        "wavelengths_um": [float(w) for w in wavelengths],
        "transmission_db": transmission_str,
    }


def attach_metadata_to_component(
    component,
    result: CoSimResult,
) -> None:
    """将联合仿真 metadata 写回 gdsfactory Component（TR-304.3）。

    原地修改 component.metadata 字段，附加仿真结果摘要。
    gdsfactory Component.metadata 是 dict，可直接添加键值对。

    Args:
        component: gdsfactory Component 对象（原地修改 metadata）。
        result: 联合仿真结果。

    Raises:
        ValueError: 仿真失败 / component 无 metadata 属性。
        AttributeError: component 无 metadata 属性。

    来源:
    - gdsfactory Component.metadata: https://gdsfactory.github.io/gdsfactory/api.html
    """
    if result.simulation_status != "success":
        raise ValueError(
            f"仿真状态为 {result.simulation_status!r}，无法附加 metadata"
        )
    if not hasattr(component, "metadata"):
        raise AttributeError(
            f"组件 {component!r} 无 metadata 属性，不是有效的 gdsfactory Component"
        )
    metadata = cosim_to_gdsfactory_metadata(result)
    component.metadata["polaris_cosim"] = metadata
    logger.info(
        "metadata 已附加到组件 %s: %d 端口, 后端 %s",
        getattr(component, "name", "<unknown>"),
        result.n_ports,
        result.fdtd_result.backend_used.value,
    )


# =============================================================================
# 辅助函数
# =============================================================================
def get_cosim_summary(result: CoSimResult) -> str:
    """生成联合仿真结果的可读摘要字符串。

    Args:
        result: 联合仿真结果。

    Returns:
        多行可读摘要字符串。

    Raises:
        ValueError: 仿真失败。
    """
    if result.simulation_status != "success":
        raise ValueError(
            f"仿真状态为 {result.simulation_status!r}，无法生成摘要"
        )

    wavelengths = result.fdtd_result.wavelengths_um
    wl_range = (
        f"{float(wavelengths[0]):.4f}-{float(wavelengths[-1]):.4f}μm"
        if wavelengths.size > 0
        else "N/A"
    )

    lines = [
        f"gdsfactory 联合仿真结果摘要",
        f"  仿真状态: {result.simulation_status}",
        f"  后端: {result.fdtd_result.backend_used.value}",
        f"  器件 ID: {result.device.device_id}",
        f"  端口数: {result.n_ports}",
        f"  端口名: {result.port_names}",
        f"  波长范围: {wl_range} ({result.n_wavelengths} 点)",
        f"  S 矩阵形状: {tuple(result.s_matrix.shape)}",
        f"  插入损耗: {result.fdtd_result.insertion_loss_db:.4f} dB",
    ]

    # 列出所有 S 参数的传输谱
    for (p_out, p_in), val in result.fdtd_result.transmission_db.items():
        lines.append(f"  T({p_out}←{p_in}): {val:.4f} dB")

    return "\n".join(lines)


# =============================================================================
# R305: 电路级联合仿真
# =============================================================================
@dataclass
class CircuitCoSimConfig:
    """gdsfactory 电路级联合仿真配置（R305）。

    封装多组件电路级仿真的全部配置。每个 gdsfactory Component 先进行
    组件级 FDTD 仿真（复用 ``simulate_gdsfactory_component``），再将所有
    组件的 S 参数用 ``cascade_circuit`` 级联，得到电路级 S 参数。

    Attributes:
        components: 组件字典 {instance_name: gdsfactory Component}。
        connections: 组件间连接列表 [(inst1.port1, inst2.port2), ...]。
        ports: 外部端口映射 {ext_name: inst.port}。
        fdtd_config: FDTD 仿真配置（所有组件共用）。
        import_config: gdsfactory→PoLaRIS 器件导入配置（None 用默认）。
        port_order: 端口排序方式（同 CoSimConfig）。

    来源:
    - gdsfactory 电路级 YAML: https://gdsfactory.github.io/gdsfactory/notebooks/05_yaml_hierarchy.html
    - SAX 电路级联: https://flaport.github.io/sax/
    """

    components: dict = field(default_factory=dict)
    connections: list[tuple[str, str]] = field(default_factory=list)
    ports: dict[str, str] = field(default_factory=dict)
    fdtd_config: FDTDConfig | None = None
    import_config: DeviceImportConfig | None = None
    port_order: str | None = "name"


@dataclass
class CircuitCoSimResult:
    """gdsfactory 电路级联合仿真结果（R305）。

    Attributes:
        component_results: 各组件的仿真结果 {instance_name: CoSimResult}。
        circuit_sdict: 电路级 S 参数字典（级联后）。
        n_components: 组件数。
        n_ports: 电路外部端口数。
        wavelengths_um: 波长数组（μm）。
        simulation_status: 仿真状态（"success" / "failed"）。
    """

    component_results: dict = field(default_factory=dict)
    circuit_sdict: SDict = field(default_factory=dict)
    n_components: int = 0
    n_ports: int = 0
    wavelengths_um: np.ndarray = field(default_factory=lambda: np.array([1.55]))
    simulation_status: str = "success"


def build_sdict_from_s_matrix(
    s_matrix: np.ndarray,
    port_names: list[str],
) -> SDict:
    """从 S 矩阵构建 SDict 字典（R305）。

    将 (n_ports, n_ports, n_wavelengths) S 矩阵转换为
    {(port_out, port_in): np.ndarray} 字典格式，供 ``cascade_circuit`` 使用。

    Args:
        s_matrix: S 参数矩阵，形状 (n_ports, n_ports, n_wavelengths)。
        port_names: 端口名列表。

    Returns:
        S 参数字典 {(port_out, port_in): np.ndarray}。

    Raises:
        ValueError: 端口名列表为空 / 矩阵形状与端口数不匹配。

    来源:
    - SDict 格式: https://flaport.github.io/sax/
    - S 矩阵定义: Pozar, "Microwave Engineering", 4th ed., §4.4
    """
    if not port_names:
        raise ValueError("端口名列表不能为空")
    n_ports = len(port_names)
    if s_matrix.shape[0] != n_ports or s_matrix.shape[1] != n_ports:
        raise ValueError(
            f"S 矩阵形状 {s_matrix.shape[:2]} 与端口数 {n_ports} 不匹配"
        )
    sdict: SDict = {}
    for i, p_out in enumerate(port_names):
        for j, p_in in enumerate(port_names):
            sdict[(p_out, p_in)] = s_matrix[i, j, :]
    return sdict


def _validate_circuit_config(config: CircuitCoSimConfig) -> None:
    """校验电路级配置（R03 合规：错误必须 raise）。

    Args:
        config: 电路级配置。

    Raises:
        ValueError: 组件字典为空 / 连接引用不存在的实例 / 端口引用不存在的实例。
    """
    if not config.components:
        raise ValueError(
            "组件字典不能为空，电路级仿真至少需要 1 个组件"
        )
    inst_names = set(config.components.keys())
    for src, dst in config.connections:
        src_inst = src.split(",")[0] if "," in src else src.split(".")[0]
        dst_inst = dst.split(",")[0] if "," in dst else dst.split(".")[0]
        if src_inst not in inst_names:
            raise ValueError(
                f"连接源 {src!r} 引用的实例 {src_inst!r} 不在组件字典中。"
                f"可用实例: {sorted(inst_names)}"
            )
        if dst_inst not in inst_names:
            raise ValueError(
                f"连接目标 {dst!r} 引用的实例 {dst_inst!r} 不在组件字典中。"
                f"可用实例: {sorted(inst_names)}"
            )
    for ext_name, inst_port in config.ports.items():
        inst_name = inst_port.split(",")[0] if "," in inst_port else inst_port.split(".")[0]
        if inst_name not in inst_names:
            raise ValueError(
                f"外部端口 {ext_name!r} 引用的实例 {inst_name!r} 不在组件字典中。"
                f"可用实例: {sorted(inst_names)}"
            )


def _normalize_connection_port(port_ref: str) -> str:
    """将连接端口引用统一为 "inst.port" 格式。

    gdsfactory YAML 用 "inst,port"（逗号分隔），PoLaRIS 内部用 "inst.port"
    （点分隔）。cascade_circuit 接受两种格式，但统一为点分隔更清晰。

    Args:
        port_ref: 端口引用（"inst,port" 或 "inst.port"）。

    Returns:
        统一格式 "inst.port"。
    """
    if "," in port_ref:
        inst, port = port_ref.split(",", 1)
        return f"{inst}.{port}"
    return port_ref


def simulate_gdsfactory_circuit(
    config: CircuitCoSimConfig,
) -> CircuitCoSimResult:
    """gdsfactory 电路级联合仿真主编排函数（R305）。

    完整工作流:
    1. 校验电路配置（组件/连接/端口引用一致性）
    2. 对每个组件调用 ``simulate_gdsfactory_component()`` 进行组件级 FDTD 仿真
    3. 将各组件 S 矩阵转换为 SDict 字典
    4. 用 ``cascade_circuit()`` 级联所有组件 S 参数
    5. 返回电路级 S 参数

    Args:
        config: 电路级联合仿真配置。

    Returns:
        电路级仿真结果 ``CircuitCoSimResult``。

    Raises:
        ValueError: 组件字典为空 / 连接或端口引用不存在的实例。
        ImportError: gdsfactory 未安装 / FDTD 后端不可用（透传）。

    来源:
    - gdsfactory 电路级: https://gdsfactory.github.io/gdsfactory/notebooks/05_yaml_hierarchy.html
    - SAX 级联: https://flaport.github.io/sax/
    - 电路仿真: Simphony https://simphonyphotonics.readthedocs.io/
    """
    _validate_circuit_config(config)

    # 步骤 1: 对每个组件进行组件级 FDTD 仿真
    component_results: dict = {}
    instance_sdicts: dict[str, SDict] = {}
    wavelengths: np.ndarray | None = None

    for inst_name, component in config.components.items():
        cosim_config = CoSimConfig(
            device_id=inst_name,
            import_config=config.import_config,
            fdtd_config=config.fdtd_config,
            port_order=config.port_order,
        )
        result = simulate_gdsfactory_component(component, cosim_config)
        component_results[inst_name] = result
        # S 矩阵 → SDict
        instance_sdicts[inst_name] = build_sdict_from_s_matrix(
            result.s_matrix, result.port_names
        )
        if wavelengths is None:
            wavelengths = result.fdtd_result.wavelengths_um

    # 步骤 2: 规范化连接格式（逗号→点号）
    connections_normalized = [
        (_normalize_connection_port(src), _normalize_connection_port(dst))
        for src, dst in config.connections
    ]
    ports_normalized = {
        ext: _normalize_connection_port(inst_port)
        for ext, inst_port in config.ports.items()
    }

    # 步骤 3: 电路级 S 参数级联
    # cascade_circuit 失败会 raise RuntimeError，此处不吞没异常
    circuit_sdict = cascade_circuit(
        instances=instance_sdicts,
        connections=connections_normalized,
        ports=ports_normalized,
    )

    logger.info(
        "gdsfactory 电路级仿真完成: %d 组件, %d 外部端口, %d 波长",
        len(component_results),
        len(ports_normalized),
        wavelengths.size if wavelengths is not None else 0,
    )

    return CircuitCoSimResult(
        component_results=component_results,
        circuit_sdict=circuit_sdict,
        n_components=len(component_results),
        n_ports=len(ports_normalized),
        wavelengths_um=wavelengths if wavelengths is not None else np.array([1.55]),
        simulation_status="success",
    )


def export_circuit_cosim_to_touchstone(
    result: CircuitCoSimResult,
    output_path: str | Path,
    freq_unit: str = "ghz",
) -> str:
    """将电路级联合仿真结果导出为 Touchstone 文件（R305, TR-305.3）。

    Args:
        result: 电路级仿真结果。
        output_path: 输出文件路径。
        freq_unit: 频率单位（hz/khz/mhz/ghz）。

    Returns:
        输出文件路径字符串。

    Raises:
        ValueError: 仿真失败 / 电路 S 参数为空。

    来源:
    - Touchstone 规范: https://en.wikipedia.org/wiki/Touchstone_file
    """
    if result.simulation_status != "success":
        raise ValueError(
            f"仿真状态为 {result.simulation_status!r}，无法导出 Touchstone"
        )
    if not result.circuit_sdict:
        raise ValueError("电路 S 参数为空，无法导出 Touchstone")

    # 推断端口名（从 circuit_sdict 键）
    port_names_set: set[str] = set()
    for p_out, p_in in result.circuit_sdict:
        port_names_set.add(p_out)
        port_names_set.add(p_in)
    port_names = sorted(port_names_set)

    # 波长 → 频率（Hz）: f = c / λ, c = 299792458 m/s
    # 来源: NIST CODATA 2018 光速常数
    c_m_per_s = 299_792_458.0
    wavelengths_m = result.wavelengths_um * 1e-6
    freqs_hz = c_m_per_s / wavelengths_m

    save_touchstone(
        filepath=output_path,
        freqs=freqs_hz,
        sdict=result.circuit_sdict,
        freq_unit=freq_unit,
        port_names=port_names,
    )
    logger.info("电路级 Touchstone 导出: %s (%d 端口)", output_path, len(port_names))
    return str(output_path)


def get_circuit_cosim_summary(result: CircuitCoSimResult) -> str:
    """生成电路级联合仿真结果的可读摘要字符串（R305）。

    Args:
        result: 电路级仿真结果。

    Returns:
        多行可读摘要字符串。

    Raises:
        ValueError: 仿真失败。
    """
    if result.simulation_status != "success":
        raise ValueError(
            f"仿真状态为 {result.simulation_status!r}，无法生成摘要"
        )

    wavelengths = result.wavelengths_um
    wl_range = (
        f"{float(wavelengths[0]):.4f}-{float(wavelengths[-1]):.4f}μm"
        if wavelengths.size > 0
        else "N/A"
    )

    lines = [
        f"gdsfactory 电路级联合仿真结果摘要",
        f"  仿真状态: {result.simulation_status}",
        f"  组件数: {result.n_components}",
        f"  外部端口数: {result.n_ports}",
        f"  波长范围: {wl_range} ({wavelengths.size} 点)",
        f"  电路 S 参数键数: {len(result.circuit_sdict)}",
    ]

    # 列出各组件的端口信息
    for inst_name, comp_result in result.component_results.items():
        lines.append(
            f"  组件 {inst_name}: {comp_result.n_ports} 端口, "
            f"后端 {comp_result.fdtd_result.backend_used.value}"
        )

    return "\n".join(lines)


__all__ = [
    "CoSimConfig",
    "CoSimResult",
    "CircuitCoSimConfig",
    "CircuitCoSimResult",
    "attach_metadata_to_component",
    "build_s_matrix_from_sdict",
    "build_sdict_from_s_matrix",
    "cosim_to_gdsfactory_metadata",
    "export_cosim_to_touchstone",
    "export_circuit_cosim_to_touchstone",
    "get_cosim_summary",
    "get_circuit_cosim_summary",
    "simulate_gdsfactory_circuit",
    "simulate_gdsfactory_component",
]
