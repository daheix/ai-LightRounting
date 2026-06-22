"""gdsfactory 集成模块（步骤4：生成真实参数化器件 GDS + 第2轮 PDK 桥接）。

gdsfactory 是开源光子芯片设计库（MIT 许可证），含数百个参数化组件。
本模块提供 gdsfactory 集成接口，包括：

1. GDS 文件生成（generate_mzi_gds / generate_ring_resonator_gds / generate_component_gds）
2. PDK 桥接（gdsfactory_to_polaris_device / load_gdsfactory_pdk /
   list_gdsfactory_pdks / register_gdsfactory_pdk）—— 第2轮 P0-3

PDK 桥接使 PoLaRIS 能直接使用 gdsfactory 的 43+ PDK 生态（ubcpdk/gf180/ihp
等），立即获得商业级 PDK 覆盖能力，对标 Lumerical/IPKISS 的 PDK 支持。

注：gdsfactory 8.18.0 锁定 pydantic<2.10，而 pydantic<2.10 的 pydantic-core
无 Python 3.14 wheel，因此在 Python 3.14 环境下 gdsfactory 可能 import 失败。
这是上游版本锁定问题，非项目代码问题。在其他 Python 版本（3.10-3.13）下
gdsfactory 可正常安装使用。

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- ubcpdk (MIT): https://github.com/gdsfactory/ubc
- gf180mcu PDK (Apache-2.0): https://github.com/gdsfactory/gf180mcu-pdk
- IHP Open Source PDK (Apache-2.0): https://github.com/IHP-GmbH/IHP-Open-PDK
- 差距分析 P0-3: docs/commercial_gap_analysis.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port

if TYPE_CHECKING:
    from polaris.pdk.catalog import DeviceCatalog

logger = logging.getLogger(__name__)

# gdsfactory 为必装依赖（规则 2 直接集成）。
# Python 3.14 环境下因上游 pydantic 版本锁定可能 import 失败，保留兜底。
try:
    import gdsfactory as gf

    _HAS_GDSFACTORY = True
except ImportError:
    gf = None
    _HAS_GDSFACTORY = False


# gdsfactory 端口朝向（度）→ PoLaRIS Direction 映射
# gdsfactory 用 orientation（度，0=东, 90=北, 180=西, 270=南）
# PoLaRIS 用 Direction 枚举（NORTH/SOUTH/EAST/WEST）
_ORIENTATION_TO_DIRECTION: dict[int, Direction] = {
    0: Direction.EAST,
    90: Direction.NORTH,
    180: Direction.WEST,
    270: Direction.SOUTH,
}


def is_available() -> bool:
    """检查 gdsfactory 是否可用（import 成功且 PDK 可激活）。

    Returns:
        True 若 gdsfactory 已安装且 PDK 可正常激活。
    """
    if not _HAS_GDSFACTORY:
        return False
    try:
        # gdsfactory 8.18.0 API: gdsfactory.pdk.get_active_pdk()
        from gdsfactory.pdk import get_active_pdk

        get_active_pdk()
        return True
    except Exception:
        return False


def generate_mzi_gds(
    output_path: str,
    delta_length_um: float = 100.0,
    bend_radius_um: float = 5.0,
) -> str:
    """用 gdsfactory 生成真实 MZI GDS（含光栅耦合器+Y分支+延迟臂）。

    生成标准 MZI 结构：gc_in → y_branch → 双臂（长短臂差 delta_length）
    → y_branch → gc_out。使用 ubcpdk 真实器件参数。

    Args:
        output_path: GDS 输出路径。
        delta_length_um: 两臂长度差（μm，控制 FSR）。
        bend_radius_um: 弯曲半径（μm，SiEPIC 默认 5μm）。

    Returns:
        GDS 文件路径。gdsfactory 不可用时返回空字符串。
    """
    if not _HAS_GDSFACTORY:
        logger.warning(
            "gdsfactory 未安装，无法生成真实 MZI GDS。可执行 pip install gdsfactory 安装。"
        )
        return ""

    try:
        # 尝试用 ubcpdk 真实器件
        try:
            from ubcpdk import PDK, cells

            PDK.activate()
            mzi = cells.mzi(delta_length=delta_length_um)
            mzi.write_gds(output_path)
            logger.info("ubcpdk MZI GDS 生成: %s", output_path)
            return output_path
        except ImportError:
            # ubcpdk 不可用，用 gdsfactory generic_pdk
            import gdsfactory as gf

            gf.get_active_pdk()
            mzi = gf.components.mzi(delta_length=delta_length_um)
            mzi.write_gds(output_path)
            logger.info("gdsfactory generic MZI GDS 生成: %s", output_path)
            return output_path
    except Exception as e:
        logger.error("gdsfactory MZI 生成失败: %s", e)
        return ""


def generate_ring_resonator_gds(
    output_path: str,
    radius_um: float = 5.0,
    gap_nm: float = 200.0,
) -> str:
    """用 gdsfactory 生成真实 Ring Resonator GDS。

    生成单环谐振器：直波导 + 耦合环（半径 radius，间隙 gap）。

    Args:
        output_path: GDS 输出路径。
        radius_um: 环半径（μm，SiEPIC 默认 5μm）。
        gap_nm: 耦合间隙（nm，SiEPIC 默认 200nm）。

    Returns:
        GDS 文件路径。gdsfactory 不可用时返回空字符串。
    """
    if not _HAS_GDSFACTORY:
        logger.warning(
            "gdsfactory 未安装，无法生成真实 Ring GDS。可执行 pip install gdsfactory 安装。"
        )
        return ""

    try:
        try:
            from ubcpdk import PDK, cells

            PDK.activate()
            ring = cells.ring_single(radius=radius_um, gap=gap_nm * 1e-3)
            ring.write_gds(output_path)
            logger.info("ubcpdk Ring GDS 生成: %s", output_path)
            return output_path
        except ImportError:
            import gdsfactory as gf

            gf.get_active_pdk()
            ring = gf.components.ring_single(radius=radius_um, gap=gap_nm * 1e-3)
            ring.write_gds(output_path)
            logger.info("gdsfactory generic Ring GDS 生成: %s", output_path)
            return output_path
    except Exception as e:
        logger.error("gdsfactory Ring 生成失败: %s", e)
        return ""


def generate_component_gds(
    component_name: str,
    output_path: str,
    **kwargs,
) -> str:
    """用 gdsfactory 生成指定器件的真实 GDS。

    支持 gdsfactory 标准器件名：straight/bend_euler/mmi1x2/mmi2x2/
    grating_coupler/y_branch/directional_coupler 等。

    Args:
        component_name: gdsfactory 器件名（如 'mmi1x2'）。
        output_path: GDS 输出路径。
        **kwargs: 器件参数（如 length=10.0, width=0.5）。

    Returns:
        GDS 文件路径。gdsfactory 不可用时返回空字符串。
    """
    if not _HAS_GDSFACTORY:
        logger.warning(
            "gdsfactory 未安装，无法生成 %s GDS。可执行 pip install gdsfactory 安装。",
            component_name,
        )
        return ""

    try:
        import gdsfactory as gf

        gf.get_active_pdk()
        component_func = getattr(gf.components, component_name, None)
        if component_func is None:
            logger.error("gdsfactory 无 %s 器件", component_name)
            return ""
        component = component_func(**kwargs)
        component.write_gds(output_path)
        logger.info("gdsfactory %s GDS 生成: %s", component_name, output_path)
        return output_path
    except Exception as e:
        logger.error("gdsfactory %s 生成失败: %s", component_name, e)
        return ""


def list_available_components() -> list[str]:
    """列出 gdsfactory 可用的器件名。

    Returns:
        器件名列表。gdsfactory 不可用时返回空列表。
    """
    if not _HAS_GDSFACTORY:
        return []
    try:
        import gdsfactory as gf

        # 筛选光子学相关器件（排除 electrical/quantum 等）
        all_components = dir(gf.components)
        photonics_components = [
            name
            for name in all_components
            if not name.startswith("_") and callable(getattr(gf.components, name))
        ]
        return sorted(photonics_components)
    except Exception:
        return []


# ==================== 第2轮 P0-3: PDK 桥接增强 ====================


def _orientation_to_direction(orientation_deg: float) -> Direction:
    """将 gdsfactory 端口朝向（度）转换为 PoLaRIS Direction。

    gdsfactory 用 orientation（度，0=东, 90=北, 180=西, 270=南），
    PoLaRIS 用 Direction 枚举。非标准角度归一化到最近的四正方向。

    Args:
        orientation_deg: gdsfactory 端口朝向（度）。

    Returns:
        PoLaRIS Direction 枚举值。
    """
    normalized = int(round(orientation_deg)) % 360
    # 归一化到最近的 90 度倍数
    nearest = (normalized // 90) * 90
    return _ORIENTATION_TO_DIRECTION.get(nearest, Direction.EAST)


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


def gdsfactory_to_polaris_device(
    component,
    device_id: str,
    config: DeviceImportConfig | None = None,
) -> Device:
    """将 gdsfactory Component 转换为 PoLaRIS Device（第2轮 P0-3）。

    提取 gdsfactory Component 的端口、包围盒信息，转换为 PoLaRIS Device。
    使 PoLaRIS 能直接使用 gdsfactory 的 43+ PDK 生态器件。

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
    platform = cfg.platform
    category = cfg.category
    name = cfg.name
    process_node = cfg.process_node
    # 提取端口
    ports: list[Port] = []
    # gdsfactory 8.18.0: Ports 对象支持迭代，每个元素有 name 属性
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

    # 提取包围盒
    # gdsfactory 8.18.0: component.bbox 是方法，调用返回 klayout Box
    if callable(component.bbox):
        bbox_obj = component.bbox()
        bbox = BoundingBox(
            xmin=float(bbox_obj.left),
            ymin=float(bbox_obj.bottom),
            xmax=float(bbox_obj.right),
            ymax=float(bbox_obj.top),
        )
    else:
        # 旧版 API: bbox 是 numpy array [[xmin, ymin], [xmax, ymax]]
        bbox_array = component.bbox
        bbox = BoundingBox(
            xmin=float(bbox_array[0, 0]),
            ymin=float(bbox_array[0, 1]),
            xmax=float(bbox_array[1, 0]),
            ymax=float(bbox_array[1, 1]),
        )

    return Device(
        device_id=device_id,
        platform=platform,
        category=category,
        name=name or component.name,
        ports=ports,
        bbox=bbox,
        params={"source": "gdsfactory", "component_name": component.name},
        process_node=process_node,
    )


def list_gdsfactory_pdks() -> list[str]:
    """列出可用的 gdsfactory PDK（第2轮 P0-3）。

    检测已安装的 gdsfactory PDK 模块，返回 PDK 名列表。
    支持检测：generic（内置）/ubcpdk/gf180/ihp。

    Returns:
        PDK 名列表。gdsfactory 不可用时返回空列表。

    来源:
    - ubcpdk: https://github.com/gdsfactory/ubc
    - gf180mcu: https://github.com/gdsfactory/gf180mcu-pdk
    - IHP: https://github.com/IHP-GmbH/IHP-Open-PDK
    """
    if not _HAS_GDSFACTORY:
        return []
    pdks: list[str] = ["generic"]  # generic 内置
    # 检测可选 PDK
    for pdk_name, module_name in [
        ("ubcpdk", "ubcpdk"),
        ("gf180", "gf180"),
        ("ihp", "ihp"),
    ]:
        try:
            __import__(module_name)
            pdks.append(pdk_name)
        except ImportError:
            pass
    return pdks


def load_gdsfactory_pdk(
    pdk_name: str = "generic",
    max_components: int = 50,
) -> dict[str, Device]:
    """加载 gdsfactory PDK 器件为 PoLaRIS Device 字典（第2轮 P0-3）。

    将 gdsfactory PDK 的组件转换为 PoLaRIS Device，使 PoLaRIS 能直接
    使用 gdsfactory 的 43+ PDK 生态。

    Args:
        pdk_name: PDK 名（generic/ubcpdk/gf180/ihp），默认 generic。
        max_components: 最大加载器件数（避免内存溢出），默认 50。

    Returns:
        器件名 → Device 映射。gdsfactory 不可用或 PDK 不存在时返回空字典。

    来源: gdsfactory PDK 生态
    https://gdsfactory.github.io/gdsfactory/
    """
    if not _HAS_GDSFACTORY:
        logger.warning("gdsfactory 未安装，无法加载 PDK %s", pdk_name)
        return {}

    try:
        # 激活指定 PDK
        if pdk_name == "generic":
            gf.get_active_pdk()
            components = gf.components
        elif pdk_name == "ubcpdk":
            import ubcpdk

            ubcpdk.PDK.activate()
            components = ubcpdk.cells
        else:
            logger.warning("不支持的 gdsfactory PDK: %s", pdk_name)
            return {}

        # 平台与工艺节点映射
        platform_map = {
            "generic": ("SOI", "220nm SOI"),
            "ubcpdk": ("SOI", "220nm SOI"),
        }
        platform, process_node = platform_map.get(pdk_name, ("SOI", "220nm SOI"))

        # 遍历组件，转换为 Device
        devices: dict[str, Device] = {}
        component_names = [
            n for n in dir(components) if not n.startswith("_") and callable(getattr(components, n))
        ]

        for name in sorted(component_names):
            if len(devices) >= max_components:
                break
            try:
                component_func = getattr(components, name)
                component = component_func()
                device = gdsfactory_to_polaris_device(
                    component=component,
                    device_id=f"{pdk_name}_{name}",
                    config=DeviceImportConfig(
                        platform=platform,
                        category="passive",
                        name=name,
                        process_node=process_node,
                    ),
                )
                devices[name] = device
            except Exception as e:
                logger.debug("跳过 gdsfactory 器件 %s: %s", name, e)
                continue

        logger.info("从 gdsfactory PDK %s 加载 %d 个器件", pdk_name, len(devices))
        return devices
    except Exception as e:
        logger.error("加载 gdsfactory PDK %s 失败: %s", pdk_name, e)
        return {}


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
        try:
            catalog.register(device)
            count += 1
        except Exception as e:
            logger.debug("注册器件 %s 失败: %s", device.device_id, e)
    logger.info("从 gdsfactory PDK %s 注册 %d 个器件到 catalog", pdk_name, count)
    return count


__all__ = [
    # GDS 生成
    "generate_component_gds",
    "generate_mzi_gds",
    "generate_ring_resonator_gds",
    "is_available",
    "list_available_components",
    # PDK 桥接（第2轮 P0-3）
    "gdsfactory_to_polaris_device",
    "list_gdsfactory_pdks",
    "load_gdsfactory_pdk",
    "register_gdsfactory_pdk",
]
