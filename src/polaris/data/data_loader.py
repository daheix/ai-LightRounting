"""外部数据源加载器（公开 API）。

支持从 LiDAR PIC IR (YAML)、PICBench (YAML/JSON)、
GDSFactory (*.pic.yml)、PhIDO (YAML/JSON) 等格式加载光子电路训练数据。

格式特定的解析器拆分到：
- ``_pic_ir.py``: LiDAR PIC IR 格式
- ``_other_formats.py``: GDSFactory / PICBench / PhIDO 格式
- ``_common.py``: 共享工具函数

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- PhIDO: https://github.com/JPPhotonics/PhIDO-Release
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris.data._other_formats import (
    load_gdsfactory_yaml,
    load_phido,
    load_picbench,
)
from polaris.data._pic_ir import load_pic_ir
from polaris.data.specs import CircuitSpec

logger = logging.getLogger(__name__)


def load_directory(
    path: str | Path,
    fmt: str = "auto",
) -> list[CircuitSpec]:
    """批量加载目录下的所有电路文件。

    Args:
        path: 目录路径。
        fmt: 格式（auto/pic_ir/gdsfactory/picbench/phido）。

    Returns:
        CircuitSpec 列表。
    """
    p = Path(path)
    if not p.exists():
        logger.error("数据目录不存在: %s", path)
        return []

    circuits: list[CircuitSpec] = []
    for fp in sorted(p.glob("*.y*ml")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    for fp in sorted(p.glob("*.json")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    logger.info("从 %s 加载了 %d 个电路", path, len(circuits))
    return circuits


def _load_file(fp: Path, fmt: str) -> CircuitSpec:
    """根据格式加载单个文件。

    Args:
        fp: 文件路径。
        fmt: 格式（auto/pic_ir/gdsfactory/picbench/phido）。

    Returns:
        CircuitSpec。

    Raises:
        ValueError: auto 模式下无法识别格式时。
    """
    if fmt == "pic_ir":
        return load_pic_ir(fp)
    if fmt == "gdsfactory":
        return load_gdsfactory_yaml(fp)
    if fmt == "picbench":
        return load_picbench(fp)
    if fmt == "phido":
        return load_phido(fp)
    # auto: 尝试所有格式
    for loader in [load_pic_ir, load_gdsfactory_yaml, load_picbench, load_phido]:
        try:
            return loader(fp)
        except Exception:
            continue
    raise ValueError(f"无法识别文件格式: {fp}")


def circuit_spec_to_netlist_dict(circuit: CircuitSpec) -> dict:
    """将 CircuitSpec 转换为 Netlist 解析器期望的 dict 格式。

    ``polaris.engine.netlist.parse_netlist`` 接受 dict 格式
    ``{name, instances: {id: {component, settings}}, connections: [...]}``。
    本函数将 ``CircuitSpec`` 转换为该格式，打通数据加载→布局环境链路。

    LiDAR benchmark 使用的 gdsfactory 器件名（如 ``mmi1x2``/``mzi``/
    ``grating_coupler_elliptical_lumerical``）需映射到 PoLaRIS PDK
    catalog 中的标准器件名（如 ``soi_mmi_1x2``/``soi_mzi``/
    ``soi_grating_coupler_2d``）。

    Args:
        circuit: CircuitSpec 数据类。

    Returns:
        Netlist dict，可直接传给 ``parse_netlist`` 或 ``load_netlist``。
    """
    instances: dict[str, dict] = {}
    for dev in circuit.devices:
        component = _LIDAR_TO_POLARIS_DEVICE_MAP.get(dev.device_type, dev.device_type)
        instances[dev.name] = {
            "component": component,
            "settings": {
                "width_um": dev.width_um,
                "height_um": dev.height_um,
                "ports": [
                    {"name": p[0], "x": p[1], "y": p[2], "direction": p[3]} for p in dev.ports
                ],
                **dev.params,
            },
        }
    connections = [
        [src_dev, src_port, dst_dev, dst_port]
        for src_dev, src_port, dst_dev, dst_port in circuit.connections
    ]
    return {
        "name": circuit.name,
        "instances": instances,
        "connections": connections,
    }


# LiDAR gdsfactory 器件名 → PoLaRIS PDK catalog 器件名映射。
# 来源: LiDAR benchmarks/ 目录实际使用的 component 名
#   https://github.com/ScopeX-ASU/LiDAR/tree/main/src/picroute/benchmarks
# 映射目标: src/polaris/pdk/soi/ 下的标准器件
_LIDAR_TO_POLARIS_DEVICE_MAP: dict[str, str] = {
    "grating_coupler_elliptical_lumerical": "soi_grating_coupler_2d",
    "mmi1x2": "soi_mmi_1x2",
    "mmi2x2": "soi_mmi_2x2",
    "mmi": "soi_mmi_2x2",
    "mzi": "soi_mzi",
    "mzi1x2": "soi_mzi",
    "mzi2x2_2x2_phase_shifter": "soi_mzi",
    "ring_single_pn": "soi_ring_resonator",
    "ring_double_pn": "soi_double_ring_filter",
    "ring_single": "soi_ring_resonator",
    "ring_double": "soi_double_ring_filter",
    "straight": "soi_strip_waveguide",
    "straight_heater_metal_undercut": "soi_thermo_optic_phase_shifter",
    "y_branch": "soi_y_branch",
    "crossing": "soi_crossing",
    "directional_coupler": "soi_directional_coupler",
    "dc": "soi_directional_coupler",
    "terminator": "soi_edge_coupler",
    "heater": "soi_thermo_optic_phase_shifter",
    "rectangle": "soi_strip_waveguide",
}


__all__ = [
    "load_pic_ir",
    "load_gdsfactory_yaml",
    "load_picbench",
    "load_phido",
    "load_directory",
    "circuit_spec_to_netlist_dict",
]
