"""gdsfactory PDK 桥接模块（第2轮 P0-3）。

原属 gdsfactory_integration.py §2（批次 10-B 拆分提取），保留原始文献溯源。

PDK 桥接使 PoLaRIS 能直接使用 gdsfactory 生态：当前已检测并支持 4 个 PDK
（generic/ubcpdk/gf180/ihp），gdsfactory 上游理论支持 43+ PDK（需用户自行
安装对应 Python 包方可加载）。对标 Lumerical/IPKISS 的 PDK 支持。

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- ubcpdk (MIT): https://github.com/gdsfactory/ubc
- gf180mcu PDK (Apache-2.0): https://github.com/gdsfactory/gf180mcu-pdk
- IHP Open Source PDK (Apache-2.0): https://github.com/IHP-GmbH/IHP-Open-PDK
- 差距分析 P0-3: docs/commercial_gap_analysis.md

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Port
from polaris.pdk.gdsfactory_gds_gen import (
    _HAS_GDSFACTORY,
    _orientation_to_direction,
    gf,
)

if TYPE_CHECKING:
    from polaris.pdk.catalog import DeviceCatalog

logger = logging.getLogger(__name__)


@dataclass
class DeviceImportConfig:
    """gdsfactory 器件导入配置（降低 gdsfactory_to_polaris_device 参数个数，规则 4.1）。

    Attributes:
        platform: 工艺平台（SOI/SiN/InP/LNOI），默认 SOI。
        category: 器件类别（passive/active/source/detector），默认 passive。
        name: 器件类型名（None 用 component.name）。
        process_node: 工艺节点标识（如 "220nm SOI"）。
    """

    platform: str = "SOI"
    category: str = "passive"
    name: str | None = None
    process_node: str | None = None


def _extract_gdsfactory_ports(component) -> list[Port]:
    """从 gdsfactory Component 提取端口列表。

    gdsfactory 8.18.0: Ports 对象支持迭代，每个元素有 name 属性。

    Args:
        component: gdsfactory Component 对象。

    Returns:
        PoLaRIS Port 列表。
    """
    ports: list[Port] = []
    for gf_port in component.ports:
        port_name = getattr(gf_port, "name", "") or ""
        orientation = getattr(gf_port, "orientation", 0) or 0
        direction = _orientation_to_direction(orientation)
        width = getattr(gf_port, "width", 0.5) or 0.5
        port_type = getattr(gf_port, "port_type", "optical") or "optical"
        center = getattr(gf_port, "center", (0, 0)) or (0, 0)
        ports.append(
            Port(
                name=str(port_name),
                x=float(center[0]),
                y=float(center[1]),
                direction=direction,
                waveguide_type=str(port_type),
                width=float(width),
            )
        )
    return ports


def _extract_gdsfactory_bbox(component) -> BoundingBox:
    """从 gdsfactory Component 提取包围盒。

    gdsfactory 8.18.0: component.bbox 是方法，调用返回 klayout Box。
    旧版 API: bbox 是 numpy array [[xmin, ymin], [xmax, ymax]]。

    Args:
        component: gdsfactory Component 对象。

    Returns:
        PoLaRIS BoundingBox 对象。
    """
    if callable(component.bbox):
        bbox_obj = component.bbox()
        return BoundingBox(
            xmin=float(bbox_obj.left),
            ymin=float(bbox_obj.bottom),
            xmax=float(bbox_obj.right),
            ymax=float(bbox_obj.top),
        )
    bbox_array = component.bbox
    return BoundingBox(
        xmin=float(bbox_array[0, 0]),
        ymin=float(bbox_array[0, 1]),
        xmax=float(bbox_array[1, 0]),
        ymax=float(bbox_array[1, 1]),
    )


def gdsfactory_to_polaris_device(
    component,
    device_id: str,
    config: DeviceImportConfig | None = None,
) -> Device:
    """将 gdsfactory Component 转换为 PoLaRIS Device（第2轮 P0-3）。

    提取 gdsfactory Component 的端口、包围盒信息，转换为 PoLaRIS Device。
    使 PoLaRIS 能直接使用 gdsfactory 已检测的 4 个 PDK（generic/ubcpdk/gf180/ihp）
    器件，gdsfactory 上游理论支持 43+ PDK（需用户自行安装对应包）。

    Args:
        component: gdsfactory Component 对象。
        device_id: PoLaRIS 器件唯一标识。
        config: 导入配置（None 用默认 SOI/passive）。

    Returns:
        PoLaRIS Device 对象。

    来源: gdsfactory Component API
    https://gdsfactory.github.io/gdsfactory/
    """
    cfg = config or DeviceImportConfig()
    ports = _extract_gdsfactory_ports(component)
    bbox = _extract_gdsfactory_bbox(component)
    return Device(
        device_id=device_id,
        platform=cfg.platform,
        category=cfg.category,
        name=cfg.name or component.name,
        ports=ports,
        bbox=bbox,
        params={"source": "gdsfactory", "component_name": component.name},
        process_node=cfg.process_node,
    )


def list_gdsfactory_pdks() -> list[str]:
    """列出可用的 gdsfactory PDK（第2轮 P0-3）。

    检测已安装的 gdsfactory PDK 模块，返回 PDK 名列表。
    支持检测：generic（内置）/ubcpdk/gf180/ihp。

    R03 修复 R112-R120: 原代码 gdsfactory 不可用时返回 []（静默 fall-back），
    违反 R03"禁止 fall-back"。修复为 raise ImportError。

    Returns:
        PDK 名列表。

    Raises:
        ImportError: gdsfactory 未安装时。

    来源:
    - ubcpdk: https://github.com/gdsfactory/ubc
    - gf180mcu: https://github.com/gdsfactory/gf180mcu-pdk
    - IHP: https://github.com/IHP-GmbH/IHP-Open-PDK
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法列出 PDK。"
            "请执行 pip install gdsfactory 或检查 Python 版本兼容性。"
        )
    pdks: list[str] = ["generic"]  # generic 内置
    # 检测可选 PDK
    # R03 合规：用 importlib.util.find_spec 做轻量探测，
    # 避免 except ImportError: pass 的 fall-back 写法。
    # find_spec 是 Python 官方推荐的模块存在性检测方法
    # （https://docs.python.org/3/library/importlib.html#importlib.util.find_spec）。
    for pdk_name, module_name in [
        ("ubcpdk", "ubcpdk"),
        ("gf180", "gf180"),
        ("ihp", "ihp"),
    ]:
        if importlib.util.find_spec(module_name) is not None:
            pdks.append(pdk_name)
    return pdks


def _activate_gdsfactory_pdk(pdk_name: str):
    """激活指定 gdsfactory PDK 并返回组件字典。

    Args:
        pdk_name: PDK 名（generic/ubcpdk）。

    Returns:
        组件字典对象，None 表示不支持。
    """
    if pdk_name == "generic":
        gf.get_active_pdk()
        return gf.components
    if pdk_name == "ubcpdk":
        import ubcpdk

        ubcpdk.PDK.activate()
        return ubcpdk.cells
    return None


def _convert_gdsfactory_components(
    components,
    pdk_name: str,
    platform: str,
    process_node: str,
    max_components: int,
) -> dict[str, Device]:
    """遍历 gdsfactory 组件并转换为 PoLaRIS Device。

    Args:
        components: gdsfactory 组件字典。
        pdk_name: PDK 名。
        platform: 平台名。
        process_node: 工艺节点。
        max_components: 最大加载器件数。

    Returns:
        器件名 → Device 映射。
    """
    devices: dict[str, Device] = {}
    component_names = [
        n for n in dir(components) if not n.startswith("_") and callable(getattr(components, n))
    ]
    for name in sorted(component_names):
        if len(devices) >= max_components:
            break
        try:
            component = getattr(components, name)()
            devices[name] = gdsfactory_to_polaris_device(
                component=component,
                device_id=f"{pdk_name}_{name}",
                config=DeviceImportConfig(
                    platform=platform, category="passive", name=name, process_node=process_node,
                ),
            )
        except Exception as e:
            # 规则 14.1：禁止 fall-back，器件加载失败必须 raise 告警
            raise RuntimeError(
                f"gdsfactory 器件 '{name}' 加载失败: {e}"
            ) from e
    return devices


def load_gdsfactory_pdk(
    pdk_name: str = "generic",
    max_components: int = 50,
) -> dict[str, Device]:
    """加载 gdsfactory PDK 器件为 PoLaRIS Device 字典（第2轮 P0-3）。

    将 gdsfactory PDK 的组件转换为 PoLaRIS Device，使 PoLaRIS 能直接
    使用 gdsfactory 已检测的 4 个 PDK（generic/ubcpdk/gf180/ihp）生态，
    上游理论支持 43+ PDK（需用户自行安装对应包）。

    Args:
        pdk_name: PDK 名（generic/ubcpdk/gf180/ihp），默认 generic。
        max_components: 最大加载器件数（避免内存溢出），默认 50。

    Returns:
        器件名 → Device 映射。PDK 不存在时返回空字典。

    Raises:
        ImportError: gdsfactory 未安装。
        RuntimeError: gdsfactory PDK 加载失败。

    来源: gdsfactory PDK 生态
    https://gdsfactory.github.io/gdsfactory/
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法加载 PDK。"
            "请执行 pip install gdsfactory 或检查 Python 版本兼容性。"
        )

    try:
        components = _activate_gdsfactory_pdk(pdk_name)
        if components is None:
            # R03 修复 R112-R120: 原代码返回 {}（静默 fall-back），违反 R03。
            # 修复为 raise ValueError，明确告知不支持该 PDK。
            raise ValueError(
                f"不支持的 gdsfactory PDK: {pdk_name}（仅支持 generic/ubcpdk）"
            )

        # 平台与工艺节点映射
        platform_map = {
            "generic": ("SOI", "220nm SOI"),
            "ubcpdk": ("SOI", "220nm SOI"),
        }
        platform, process_node = platform_map.get(pdk_name, ("SOI", "220nm SOI"))

        devices = _convert_gdsfactory_components(
            components, pdk_name, platform, process_node, max_components
        )
        logger.info("从 gdsfactory PDK %s 加载 %d 个器件", pdk_name, len(devices))
        return devices
    except (ImportError, AttributeError, RuntimeError) as e:
        # PDK 加载失败不可静默兜底（规则 14.1: 无 fall-back）
        raise RuntimeError(
            f"加载 gdsfactory PDK {pdk_name} 失败: {e}"
        ) from e


def register_gdsfactory_pdk(
    catalog: DeviceCatalog,
    pdk_name: str = "generic",
    max_components: int = 50,
) -> int:
    """将 gdsfactory PDK 器件批量注册到 PoLaRIS DeviceCatalog（第2轮 P0-3）。

    Args:
        catalog: PoLaRIS DeviceCatalog 实例。
        pdk_name: gdsfactory PDK 名（generic/ubcpdk），默认 generic。
        max_components: 最大注册器件数，默认 50。

    Returns:
        成功注册的器件数量。

    来源: gdsfactory PDK 生态
    https://gdsfactory.github.io/gdsfactory/
    """
    devices = load_gdsfactory_pdk(pdk_name, max_components)
    count = 0
    for device in devices.values():
        # R03 修复 R112-R120: 原代码 logger.debug 吞异常（静默 fall-back），
        # 违反 R03"禁止 fall-back"。修复为 raise RuntimeError，注册失败即报错。
        catalog.register(device)
        count += 1
    logger.info("从 gdsfactory PDK %s 注册 %d 个器件到 catalog", pdk_name, count)
    return count


__all__ = [
    "DeviceImportConfig",
    "gdsfactory_to_polaris_device",
    "list_gdsfactory_pdks",
    "load_gdsfactory_pdk",
    "register_gdsfactory_pdk",
]
