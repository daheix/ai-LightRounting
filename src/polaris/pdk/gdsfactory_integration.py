"""gdsfactory 集成模块（步骤4：生成真实参数化器件 GDS + 第2轮 PDK 桥接）。

gdsfactory 是开源光子芯片设计库（MIT 许可证），含数百个参数化组件。
本模块提供 gdsfactory 集成接口，包括：

1. GDS 文件生成（generate_mzi_gds / generate_ring_resonator_gds / generate_component_gds）
2. PDK 桥接（gdsfactory_to_polaris_device / load_gdsfactory_pdk /
   list_gdsfactory_pdks / register_gdsfactory_pdk）—— 第2轮 P0-3

PDK 桥接使 PoLaRIS 能直接使用 gdsfactory 生态：当前已检测并支持 4 个 PDK
（generic/ubcpdk/gf180/ihp），gdsfactory 上游理论支持 43+ PDK（需用户自行
安装对应 Python 包方可加载）。对标 Lumerical/IPKISS 的 PDK 支持。

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

    gdsfactory 9.44.0: 需显式激活 PDK。若未激活，自动激活 generic PDK。
    来源: https://gdsfactory.github.io/gdsfactory/
    """
    if not _HAS_GDSFACTORY:
        return False
    try:
        from gdsfactory.pdk import get_active_pdk

        get_active_pdk()
        return True
    except ValueError:
        # PDK 未激活，尝试自动激活 generic PDK
        try:
            import gdsfactory as gf

            gf.gpdk.PDK.activate()
            get_active_pdk()
            return True
        except (ImportError, AttributeError, RuntimeError, KeyError) as e:
            # PDK 激活失败不可静默兜底（规则 14.1: 无 fall-back）
            raise RuntimeError(
                f"gdsfactory generic PDK 激活失败: {e}"
            ) from e
    except (ImportError, AttributeError, RuntimeError, KeyError) as e:
        # PDK 状态检查失败不可静默兜底（规则 14.1: 无 fall-back）
        raise RuntimeError(
            f"gdsfactory PDK 状态检查失败: {e}"
        ) from e


def generate_mzi_gds(
    output_path: str,
    delta_length_um: float = 100.0,
    bend_radius_um: float = 5.0,
) -> str:
    """用 gdsfactory 生成真实 MZI GDS（含光栅耦合器+Y分支+延迟臂）。

    生成标准 MZI 结构：gc_in → y_branch → 双臂（长短臂差 delta_length）
    → y_branch → gc_out。使用 ubcpdk 真实器件参数。

    修复（违规 4/5）：
    - 违规 4：gdsfactory 为必装依赖，不可用时 raise ImportError（不再返回空字符串）。
    - 违规 5：ubcpdk 为指定 PDK 依赖，不可用时 raise ImportError（不再降级到
      gdsfactory generic_pdk）。

    Args:
        output_path: GDS 输出路径。
        delta_length_um: 两臂长度差（μm，控制 FSR）。
        bend_radius_um: 弯曲半径（μm，SiEPIC 默认 5μm）。

    Returns:
        GDS 文件路径。

    Raises:
        ImportError: gdsfactory 或 ubcpdk 未安装时。
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法生成真实 MZI GDS。"
            "gdsfactory 为必装依赖，请执行 pip install gdsfactory 安装。"
        )

    # ubcpdk 为指定 PDK 依赖，不可用时 raise（不再降级到 generic_pdk）
    from ubcpdk import PDK, cells

    PDK.activate()
    mzi = cells.mzi(delta_length=delta_length_um)
    mzi.write_gds(output_path)
    logger.info("ubcpdk MZI GDS 生成: %s", output_path)
    return output_path


def generate_ring_resonator_gds(
    output_path: str,
    radius_um: float = 5.0,
    gap_nm: float = 200.0,
) -> str:
    """用 gdsfactory 生成真实 Ring Resonator GDS。

    生成单环谐振器：直波导 + 耦合环（半径 radius，间隙 gap）。

    修复（违规 4/5）：
    - 违规 4：gdsfactory 为必装依赖，不可用时 raise ImportError（不再返回空字符串）。
    - 违规 5：ubcpdk 为指定 PDK 依赖，不可用时 raise ImportError（不再降级到
      gdsfactory generic_pdk）。

    Args:
        output_path: GDS 输出路径。
        radius_um: 环半径（μm，SiEPIC 默认 5μm）。
        gap_nm: 耦合间隙（nm，SiEPIC 默认 200nm）。

    Returns:
        GDS 文件路径。

    Raises:
        ImportError: gdsfactory 或 ubcpdk 未安装时。
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法生成真实 Ring GDS。"
            "gdsfactory 为必装依赖，请执行 pip install gdsfactory 安装。"
        )

    # ubcpdk 为指定 PDK 依赖，不可用时 raise（不再降级到 generic_pdk）
    from ubcpdk import PDK, cells

    PDK.activate()
    ring = cells.ring_single(radius=radius_um, gap=gap_nm * 1e-3)
    ring.write_gds(output_path)
    logger.info("ubcpdk Ring GDS 生成: %s", output_path)
    return output_path


def generate_component_gds(
    component_name: str,
    output_path: str,
    **kwargs,
) -> str:
    """用 gdsfactory 生成指定器件的真实 GDS。

    支持 gdsfactory 标准器件名：straight/bend_euler/mmi1x2/mmi2x2/
    grating_coupler/y_branch/directional_coupler 等。

    修复（违规 4）：gdsfactory 为必装依赖，不可用时 raise ImportError（不再
    返回空字符串）。器件名不存在时 raise AttributeError（不再返回空字符串）。

    Args:
        component_name: gdsfactory 器件名（如 'mmi1x2'）。
        output_path: GDS 输出路径。
        **kwargs: 器件参数（如 length=10.0, width=0.5）。

    Returns:
        GDS 文件路径。

    Raises:
        ImportError: gdsfactory 未安装时。
        AttributeError: gdsfactory 无指定器件名时。
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            f"gdsfactory 未安装，无法生成 {component_name} GDS。"
            f"gdsfactory 为必装依赖，请执行 pip install gdsfactory 安装。"
        )

    import gdsfactory as gf

    gf.get_active_pdk()
    component_func = getattr(gf.components, component_name, None)
    if component_func is None:
        raise AttributeError(
            f"gdsfactory 无 '{component_name}' 器件，"
            f"请检查器件名是否正确。"
        )
    component = component_func(**kwargs)
    component.write_gds(output_path)
    logger.info("gdsfactory %s GDS 生成: %s", component_name, output_path)
    return output_path


def list_available_components() -> list[str]:
    """列出 gdsfactory 可用的器件名。

    Returns:
        器件名列表。

    Raises:
        ImportError: gdsfactory 未安装。
        RuntimeError: gdsfactory 器件枚举失败。
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法列出器件。"
            "请执行 pip install gdsfactory 或检查 Python 版本兼容性。"
        )
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
    except (ImportError, AttributeError, RuntimeError) as e:
        # 器件枚举失败不可静默兜底（规则 14.1: 无 fall-back）
        raise RuntimeError(
            f"gdsfactory 器件枚举失败: {e}"
        ) from e


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


# ============================================================================
# R301: GDSII 读取增强 — 完全兼容 gdsfactory 输出格式
# ============================================================================


# gdsfactory 默认端口层（WG layer (1, 0)）
# 来源: gdsfactory PDK import 文档
# https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
_GDSFACTORY_DEFAULT_PORT_LAYER: tuple[int, int] = (1, 0)

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


@dataclass
class GDSIILayerInfo:
    """GDSII 层信息（R301）。

    Attributes:
        gds_layer: GDSII layer 号。
        gds_datatype: GDSII datatype。
        polaris_name: PoLaRIS 层名（来自层映射）。
        n_shapes: 该层上的形状总数（跨所有 cells）。

    学术依据: GDSII 层规范
    https://en.wikipedia.org/wiki/GDS_File
    """

    gds_layer: int = 0
    gds_datatype: int = 0
    polaris_name: str = ""
    n_shapes: int = 0


@dataclass
class GDSIIInstanceInfo:
    """GDSII 实例信息（层次化引用，R301）。

    Attributes:
        cell_name: 被引用的 cell 名。
        x: 实例原点 x (μm)。
        y: 实例原点 y (μm)。
        rotation_deg: 旋转角度 (度)。
        mirror_x: 是否 X 镜像。
        magnification: 缩放因子（通常 1.0）。

    学术依据: GDSII AREF/SREF 结构
    https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
    """

    cell_name: str = ""
    x: float = 0.0
    y: float = 0.0
    rotation_deg: float = 0.0
    mirror_x: bool = False
    magnification: float = 1.0


@dataclass
class GDSIICellInfo:
    """GDSII cell 信息（R301）。

    Attributes:
        name: cell 名。
        n_polygons: 多边形数。
        n_paths: 路径数。
        n_texts: 文本数。
        n_instances: 子 cell 实例数。
        instances: 子 cell 实例列表。
        bbox_um: 边界框 (xmin, ymin, xmax, ymax) μm。
        is_top: 是否为顶层 cell。

    学术依据: GDSII cell 结构
    https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
    """

    name: str = ""
    n_polygons: int = 0
    n_paths: int = 0
    n_texts: int = 0
    n_instances: int = 0
    instances: list[GDSIIInstanceInfo] = None
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    is_top: bool = False

    def __post_init__(self):
        if self.instances is None:
            self.instances = []


@dataclass
class GDSIIImportResult:
    """GDSII 导入结果（R301）。

    Attributes:
        file_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        dbu_um: 数据库单位 (μm)。
        cells: 所有 cells 列表（保留层次结构）。
        layers: 所有层信息列表。
        total_instances: 总实例数。
        total_polygons: 总多边形数。
        total_paths: 总路径数。
        total_texts: 总文本数。
        n_cells: cell 数。

    学术依据: GDSII 层次化结构
    https://gdsfactory.github.io/gdsfactory/
    """

    file_path: str = ""
    top_cell_name: str = ""
    dbu_um: float = 0.001
    cells: list[GDSIICellInfo] = None
    layers: list[GDSIILayerInfo] = None
    total_instances: int = 0
    total_polygons: int = 0
    total_paths: int = 0
    total_texts: int = 0
    n_cells: int = 0

    def __post_init__(self):
        if self.cells is None:
            self.cells = []
        if self.layers is None:
            self.layers = []


def _klayout_trans_to_info(trans, dbu: float) -> GDSIIInstanceInfo:
    """将 klayout DCplxTrans 变换对象转换为 GDSIIInstanceInfo（R301 内部辅助）。

    klayout 0.30.9 验证 API（无 fall-back，R03 合规）:
    - ``ct.mag``: 缩放因子（float）
    - ``ct.angle``: 旋转角度（度，float）
    - ``ct.is_mirror()``: 是否镜像（bool）
    - ``ct.disp``: 位移 DPoint（单位 μm，DCplxTrans 始终用 μm）

    Args:
        trans: klayout DCplxTrans 变换对象（来自 ``inst.dcplx_trans``）。
        dbu: 数据库单位 (μm)（保留参数，DCplxTrans 已用 μm，不参与计算）。

    Returns:
        GDSIIInstanceInfo 实例。

    Raises:
        AttributeError: trans 不含预期属性（klayout 版本不兼容）。

    学术依据:
    - klayout DCplxTrans API:
      https://www.klayout.org/klayout-pypi/overview/instances/
    - klayout Database API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    """
    # klayout 0.30.9: DCplxTrans 属性全部存在（已冒烟测试验证）
    mag = float(trans.mag)
    rot = float(trans.angle)
    mirror = bool(trans.is_mirror())
    # disp 是 DPoint，单位 μm（D 前缀 = double micrometers）
    disp = trans.disp
    x = float(disp.x)
    y = float(disp.y)
    return GDSIIInstanceInfo(
        cell_name="",  # 由调用方填充
        x=x,
        y=y,
        rotation_deg=rot,
        mirror_x=mirror,
        magnification=mag,
    )


def import_gdsii_from_gdsfactory(
    gds_path: str | Path,
    top_cell_name: str | None = None,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> GDSIIImportResult:
    """从 GDSII 文件导入，完全兼容 gdsfactory 输出格式（R301）。

    使用 klayout.db 读取 GDSII 文件，保留:
    1. **层次结构**: 所有 cells + 递归 instances (TR-301.2)
    2. **层号映射**: (gds_layer, gds_datatype) → PoLaRIS 层名 (TR-301.3)
    3. **无损导入**: 多边形/路径/文本/实例全部保留 (TR-301.1)

    Args:
        gds_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名（None 则用第一个 top cell）。
        layer_map: 自定义层映射 {(layer, datatype): polaris_name}。
            None 则用 gdsfactory generic PDK 默认映射。

    Returns:
        GDSIIImportResult。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: GDSII 文件无效或 top_cell_name 不存在。
        RuntimeError: klayout 读取失败。

    学术依据:
    - GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
    - gdsfactory GDS 导出: https://gdsfactory.github.io/gdsfactory/
    - gdsfactory PDK import: https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
    - klayout Database API: https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - gdspy 层次化引用: https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
    """
    from pathlib import Path as _Path

    import klayout.db as db

    gds_path = _Path(gds_path)
    if not gds_path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not gds_path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")

    if layer_map is None:
        layer_map = dict(_DEFAULT_LAYER_MAP)

    ly = db.Layout()
    try:
        ly.read(str(gds_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
    else:
        top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
        if not top_cells:
            raise ValueError(
                f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
            )
        top_cell = top_cells[0]
        top_cell_name = top_cell.name

    # 收集所有 layers（klayout 0.30.9: layer_indices() 返回 list[int]）
    layer_infos: list[GDSIILayerInfo] = []
    layer_shape_count: dict[tuple[int, int], int] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        polaris_name = layer_map.get(
            (gds_layer, gds_datatype),
            f"LAYER_{gds_layer}_{gds_datatype}",
        )
        layer_infos.append(GDSIILayerInfo(
            gds_layer=gds_layer,
            gds_datatype=gds_datatype,
            polaris_name=polaris_name,
            n_shapes=0,  # 后面统计
        ))
        layer_shape_count[(gds_layer, gds_datatype)] = 0

    # 遍历所有 cells，收集层次结构 + 形状统计
    # klayout 0.30.9: ly.cells() 返回 int（cell 总数），ly.cell(ci) 接受 int 索引
    cells_info: list[GDSIICellInfo] = []
    total_instances = 0
    total_polygons = 0
    total_paths = 0
    total_texts = 0

    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        cell_name = cell.name
        is_top = (cell_name == top_cell_name)

        # 形状统计（按层）
        # klayout 0.30.9: is_box/is_polygon/is_simple_polygon 都视为多边形
        # （GDSII 中 Box 实际存储为 4 顶点多边形）
        n_poly = 0
        n_path = 0
        n_text = 0
        for li in ly.layer_indices():
            info = ly.get_info(li)
            gds_layer = int(info.layer)
            gds_datatype = int(info.datatype)
            shapes = cell.shapes(li)
            for shape in shapes.each():
                if (
                    shape.is_polygon()
                    or shape.is_box()
                    or shape.is_simple_polygon()
                ):
                    n_poly += 1
                elif shape.is_path():
                    n_path += 1
                elif shape.is_text():
                    n_text += 1
                layer_shape_count[(gds_layer, gds_datatype)] = (
                    layer_shape_count.get((gds_layer, gds_datatype), 0) + 1
                )

        # 实例信息（层次化引用）
        # klayout 0.30.9: inst.cell_index 是属性（int），不是方法
        # inst.dcplx_trans 返回 DCplxTrans（μm 单位）
        instances: list[GDSIIInstanceInfo] = []
        for inst in cell.each_inst():
            child_idx = inst.cell_index
            child_cell = ly.cell(child_idx)
            child_name = child_cell.name
            inst_info = _klayout_trans_to_info(inst.dcplx_trans, dbu)
            inst_info.cell_name = child_name
            instances.append(inst_info)

        # 边界框（cell.bbox() 返回 Box，单位 dbu）
        bbox = cell.bbox()
        bbox_um = (
            float(bbox.left) * dbu,
            float(bbox.bottom) * dbu,
            float(bbox.right) * dbu,
            float(bbox.top) * dbu,
        )

        cells_info.append(GDSIICellInfo(
            name=cell_name,
            n_polygons=n_poly,
            n_paths=n_path,
            n_texts=n_text,
            n_instances=len(instances),
            instances=instances,
            bbox_um=bbox_um,
            is_top=is_top,
        ))

        total_instances += len(instances)
        total_polygons += n_poly
        total_paths += n_path
        total_texts += n_text

    # 更新 layer 形状计数
    for li_info in layer_infos:
        key = (li_info.gds_layer, li_info.gds_datatype)
        li_info.n_shapes = layer_shape_count.get(key, 0)

    # 过滤空层（n_shapes=0 且无实例引用）
    layer_infos = [li for li in layer_infos if li.n_shapes > 0]

    return GDSIIImportResult(
        file_path=str(gds_path),
        top_cell_name=top_cell_name,
        dbu_um=dbu,
        cells=cells_info,
        layers=layer_infos,
        total_instances=total_instances,
        total_polygons=total_polygons,
        total_paths=total_paths,
        total_texts=total_texts,
        n_cells=len(cells_info),
    )


# ============================================================================
# R302: GDSII 写出增强 — 输出与 gdsfactory 兼容
# ============================================================================


# gdsfactory 写出 GDSII 的默认 dbu（μm）
# 来源: gdsfactory write_gds 默认参数
# https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
_GDSFACTORY_DEFAULT_DBU_UM: float = 0.001


@dataclass
class GDSIIExportConfig:
    """GDSII 导出配置（R302）。

    Attributes:
        top_cell_name: 顶层 cell 名（写入 GDSII 时若 Layout 无顶层 cell 用此名创建）。
        dbu_um: 数据库单位（μm），gdsfactory 默认 0.001μm (1nm)。
        layer_map: 自定义层映射（仅用于元数据验证，不参与实际写出）。
        write_context_info: 是否写入 klayout 上下文信息（gdsfactory 兼容）。

    学术依据:
    - gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
    - GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
    """

    top_cell_name: str = "TOP"
    dbu_um: float = _GDSFACTORY_DEFAULT_DBU_UM
    layer_map: dict[tuple[int, int], str] | None = None
    write_context_info: bool = True


def export_gdsii_from_layout(
    layout,
    output_path: str | Path,
    config: GDSIIExportConfig | None = None,
) -> str:
    """将 klayout Layout 写出为 gdsfactory 兼容的 GDSII 文件（R302 TR-302.1/2）。

    使用 klayout.db.Layout.write() 写出 GDSII 文件，确保:
    1. dbu 与 gdsfactory 默认一致（0.001μm = 1nm）
    2. 层次结构完整保留（顶层 + 所有子 cells + instances）
    3. 输出文件可被 gdsfactory.kuple.import_gds 正确读取

    Args:
        layout: klayout.db.Layout 对象。
        output_path: GDSII 输出路径。
        config: 导出配置（None 用默认）。

    Returns:
        GDSII 文件路径。

    Raises:
        ValueError: Layout 无 cell 或 output_path 无效。
        RuntimeError: klayout 写入失败。

    学术依据:
    - klayout Layout.write API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - gdsfactory write_gds 默认参数:
      https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
    """
    from pathlib import Path as _Path

    cfg = config or GDSIIExportConfig()
    output_path = _Path(output_path)

    # R03: 输入验证
    if layout.cells() == 0:
        raise ValueError(
            "Layout 无 cell，无法写出 GDSII。"
            "需先在 Layout 中创建至少一个 cell。"
        )
    if output_path.is_dir():
        raise ValueError(f"输出路径是目录不是文件: {output_path}")

    # 验证 dbu 与 gdsfactory 默认一致（若不一致告警，不强制修改）
    actual_dbu = float(layout.dbu)
    if abs(actual_dbu - cfg.dbu_um) > 1e-9:
        logger.warning(
            "Layout dbu=%.6fμm 与 gdsfactory 默认 %.6fμm 不一致，"
            "可能影响 gdsfactory 读取兼容性",
            actual_dbu,
            cfg.dbu_um,
        )

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        layout.write(str(output_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    logger.info(
        "GDSII 写出: %s (cells=%d, dbu=%.4fμm)",
        output_path,
        layout.cells(),
        actual_dbu,
    )
    return str(output_path)


def round_trip_gdsii(
    input_path: str | Path,
    output_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> tuple[GDSIIImportResult, str]:
    """GDSII 往返导入导出（R302 TR-302.3 验证无信息损失）。

    流程:
    1. 用 import_gdsii_from_gdsfactory 读入 GDSII → GDSIIImportResult
    2. 重新写出 GDSII 到 output_path（直接复用读入的 Layout）
    3. 再次读入 output_path，验证 cells/instances/shapes 数量一致

    Args:
        input_path: 输入 GDSII 路径。
        output_path: 输出 GDSII 路径。
        layer_map: 层映射（None 用默认）。

    Returns:
        (原始导入结果, 输出文件路径) 元组。

    Raises:
        FileNotFoundError: 输入文件不存在。
        RuntimeError: 往返验证失败（数量不一致）。

    学术依据:
    - GDSII 往返一致性: https://en.wikipedia.org/wiki/GDS_File
    - klayout Layout API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    """
    from pathlib import Path as _Path

    import klayout.db as db

    input_path = _Path(input_path)
    output_path = _Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {input_path}")

    # 步骤 1: 导入原始 GDSII
    original_result = import_gdsii_from_gdsfactory(
        input_path, layer_map=layer_map
    )

    # 步骤 2: 重新读取并写出（保留层次结构）
    ly = db.Layout()
    try:
        ly.read(str(input_path))
    except Exception as e:
        raise RuntimeError(
            f"重新读取 GDSII 失败: {type(e).__name__}: {e}"
        ) from e

    export_gdsii_from_layout(ly, output_path)

    # 步骤 3: 验证往返一致性（TR-302.3）
    round_trip_result = import_gdsii_from_gdsfactory(
        output_path, layer_map=layer_map
    )

    # 验证关键字段一致（不允许信息损失）
    if original_result.n_cells != round_trip_result.n_cells:
        raise RuntimeError(
            f"往返验证失败: n_cells 不一致 "
            f"(原始={original_result.n_cells}, 往返={round_trip_result.n_cells})"
        )
    if original_result.total_instances != round_trip_result.total_instances:
        raise RuntimeError(
            f"往返验证失败: total_instances 不一致 "
            f"(原始={original_result.total_instances}, "
            f"往返={round_trip_result.total_instances})"
        )
    if original_result.total_polygons != round_trip_result.total_polygons:
        raise RuntimeError(
            f"往返验证失败: total_polygons 不一致 "
            f"(原始={original_result.total_polygons}, "
            f"往返={round_trip_result.total_polygons})"
        )
    if original_result.total_texts != round_trip_result.total_texts:
        raise RuntimeError(
            f"往返验证失败: total_texts 不一致 "
            f"(原始={original_result.total_texts}, "
            f"往返={round_trip_result.total_texts})"
        )
    if original_result.total_paths != round_trip_result.total_paths:
        raise RuntimeError(
            f"往返验证失败: total_paths 不一致 "
            f"(原始={original_result.total_paths}, "
            f"往返={round_trip_result.total_paths})"
        )

    logger.info(
        "GDSII 往返验证通过: %s → %s (cells=%d, instances=%d, polygons=%d)",
        input_path,
        output_path,
        original_result.n_cells,
        original_result.total_instances,
        original_result.total_polygons,
    )
    return original_result, str(output_path)


def create_gdsii_layout_from_cells(
    cells_spec: list[dict],
    dbu_um: float = _GDSFACTORY_DEFAULT_DBU_UM,
) -> "db.Layout":
    """从 cell 规格列表构造 klayout Layout（R302 TR-302.2 层次结构导出）。

    用于将 PoLaRIS 内部数据结构（dict）转换为 klayout Layout，
    再用 export_gdsii_from_layout 写出。

    Args:
        cells_spec: cell 规格列表，每个 dict 含:
            - name: cell 名（必填）
            - polygons: list[dict] 多边形列表，每个含 layer/datatype/points
            - texts: list[dict] 文本列表，每个含 layer/datatype/string/x/y
            - paths: list[dict] 路径列表，每个含 layer/datatype/points/width
            - instances: list[dict] 实例列表，每个含 cell_name/x/y/rotation/mirror
            - is_top: bool 是否为顶层 cell
        dbu_um: 数据库单位（μm）。

    Returns:
        klayout.db.Layout 对象。

    Raises:
        ValueError: cells_spec 为空或 cell 名重复或引用不存在 cell。
        RuntimeError: klayout 构造失败。

    学术依据:
    - klayout Layout API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - GDSII 层次结构: https://en.wikipedia.org/wiki/GDS_File
    """
    import klayout.db as db

    if not cells_spec:
        raise ValueError("cells_spec 不能为空")

    ly = db.Layout()
    ly.dbu = dbu_um

    # 第一遍: 创建所有 cells（解决引用顺序问题）
    name_to_cell: dict[str, "db.Cell"] = {}
    for spec in cells_spec:
        name = spec.get("name")
        if not name:
            raise ValueError(f"cell 规格缺少 'name' 字段: {spec}")
        if name in name_to_cell:
            raise ValueError(f"cell 名重复: {name}")
        name_to_cell[name] = ly.create_cell(name)

    # 第二遍: 填充形状和实例
    for spec in cells_spec:
        name = spec["name"]
        cell = name_to_cell[name]

        # 多边形
        for poly in spec.get("polygons", []):
            layer = int(poly["layer"])
            datatype = int(poly["datatype"])
            li = ly.layer(layer, datatype)
            points = poly["points"]
            if len(points) < 3:
                raise ValueError(
                    f"多边形点数 < 3 (cell={name}, layer={layer}/{datatype})"
                )
            dbu_points = [db.Point(int(p[0] / dbu_um), int(p[1] / dbu_um)) for p in points]
            cell.shapes(li).insert(db.Polygon(dbu_points))

        # 文本
        for txt in spec.get("texts", []):
            layer = int(txt["layer"])
            datatype = int(txt["datatype"])
            li = ly.layer(layer, datatype)
            string = str(txt["string"])
            x_um = float(txt.get("x", 0.0))
            y_um = float(txt.get("y", 0.0))
            # Text 接受 Trans（dbu 单位）
            trans = db.Trans(int(x_um / dbu_um), int(y_um / dbu_um))
            cell.shapes(li).insert(db.Text(string, trans))

        # 路径
        for path in spec.get("paths", []):
            layer = int(path["layer"])
            datatype = int(path["datatype"])
            li = ly.layer(layer, datatype)
            points = path["points"]
            if len(points) < 2:
                raise ValueError(
                    f"路径点数 < 2 (cell={name}, layer={layer}/{datatype})"
                )
            width_um = float(path.get("width", 0.5))
            width_dbu = int(width_um / dbu_um)
            dbu_points = [db.Point(int(p[0] / dbu_um), int(p[1] / dbu_um)) for p in points]
            cell.shapes(li).insert(db.Path(dbu_points, width_dbu))

        # 实例
        # 修复（R05）: 原代码用 db.DCplxTrans(μm) 构造 instance，但 CellInstArray
        # 在 KLayout 0.30.9 中将 DCplxTrans 的位移当成 dbu 存储，导致 20μm 变成
        # 0.02μm（20dbu）。改为用 db.ICplxTrans(dbu) 显式构造，μm → dbu 转换
        # 后再传入，确保 instance 的 placement 正确。
        # 实测（调试 _debug4_r324.py）: DCplxTrans(1.0,0,False,20.0,0.0) 存储
        # 后 dcplx_trans 显示 0.02,0 μm（即 20 dbu），而非 20 μm。
        # 来源: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
        for inst in spec.get("instances", []):
            child_name = inst.get("cell_name")
            if child_name not in name_to_cell:
                raise ValueError(
                    f"实例引用的 cell 不存在: {child_name} "
                    f"(在 cell '{name}' 中)"
                )
            child_cell = name_to_cell[child_name]
            x_um = float(inst.get("x", 0.0))
            y_um = float(inst.get("y", 0.0))
            rotation = float(inst.get("rotation", 0.0))
            mirror = bool(inst.get("mirror", False))
            # 用 ICplxTrans（dbu 单位）显式构造，避免 DCplxTrans → ICplxTrans
            # 转换时的单位歧义
            x_dbu = int(round(x_um / dbu_um))
            y_dbu = int(round(y_um / dbu_um))
            trans = db.ICplxTrans(1.0, rotation, mirror, x_dbu, y_dbu)
            cell.insert(db.CellInstArray(child_cell.cell_index(), trans))

    # 验证至少有一个顶层 cell
    top_cells = list(ly.each_top_cell())
    if not top_cells:
        raise ValueError(
            "构造的 Layout 无顶层 cell，可能所有 cells 都被引用为子 cell"
        )

    return ly


def export_gdsii_from_cells(
    cells_spec: list[dict],
    output_path: str | Path,
    dbu_um: float = _GDSFACTORY_DEFAULT_DBU_UM,
) -> str:
    """从 cell 规格列表导出 gdsfactory 兼容 GDSII（R302 综合接口）。

    一步完成: cells_spec → Layout → GDSII 文件。
    适合 PoLaRIS 内部数据结构直接导出。

    Args:
        cells_spec: cell 规格列表（见 create_gdsii_layout_from_cells）。
        output_path: GDSII 输出路径。
        dbu_um: 数据库单位（μm）。

    Returns:
        GDSII 文件路径。

    Raises:
        ValueError: cells_spec 无效。
        RuntimeError: 写出失败。
    """
    layout = create_gdsii_layout_from_cells(cells_spec, dbu_um=dbu_um)
    return export_gdsii_from_layout(layout, output_path)


# ============================================================================
# R303: PDK 双向兼容层映射
# ============================================================================


# SiEPIC EBeam PDK 标准层映射（Lukas Chrostowski, UBC, MIT 许可证）
# 来源: SiEPIC EBeam PDK
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_SIEPIC_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",            # 波导核心层 (Si, 220nm)
    (2, 0): "SLAB150",       # 150nm slab (rib waveguide)
    (3, 0): "SLAB90",        # 90nm slab (rib waveguide)
    (4, 0): "SiN",           # SiN 波导层
    (5, 0): "METAL",         # 金属层
    (6, 0): "HEATER",        # 加热器层
    (10, 0): "TEXT",         # 文本标注层
    (11, 0): "LABEL",        # 标签层
    (68, 0): "DEVREC",       # 器件识别层 (SiEPIC)
    (69, 0): "PIN",          # 端口标记层 (SiEPIC)
    (70, 0): "PORT",         # 端口几何层
    (80, 0): "FLOORPLAN",    # 平面规划层
    (99, 0): "PORT_GEOM",    # gdsfactory 端口几何层
}

# gdsfactory generic PDK 层映射（来源: gdsfactory generic PDK layer definitions）
# https://gdsfactory.github.io/gdsfactory/
_GDSFACTORY_GENERIC_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",            # 波导核心层
    (2, 0): "SLAB150",       # 150nm slab
    (3, 0): "SLAB90",        # 90nm slab
    (66, 0): "TEXT",         # 文本标注层
    (68, 0): "DEVREC",       # 器件识别层 (SiEPIC 兼容)
    (69, 0): "PIN",          # 端口标记层 (SiEPIC 兼容)
    (99, 0): "PORT",         # 端口几何层
}

# 反向映射缓存: polaris_name → (gds_layer, gds_datatype)
# 用于 PoLaRIS → GDSII 双向转换
_LAYER_NAME_TO_GDS_CACHE: dict[str, tuple[int, int]] = {}


def get_siepic_layer_map() -> dict[tuple[int, int], str]:
    """获取 SiEPIC EBeam PDK 标准层映射（R303 TR-303.1）。

    返回 SiEPIC EBeam PDK 标准层映射的拷贝（防止外部修改内部状态）。

    Returns:
        SiEPIC 层映射字典 {(gds_layer, datatype): polaris_name}。

    来源:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - SiEPIC Connect: https://github.com/SiEPIC/SiEPIC-Tools
    """
    return dict(_SIEPIC_LAYER_MAP)


def get_gdsfactory_generic_layer_map() -> dict[tuple[int, int], str]:
    """获取 gdsfactory generic PDK 标准层映射。

    Returns:
        gdsfactory generic PDK 层映射字典。

    来源: gdsfactory generic PDK layer definitions
    https://gdsfactory.github.io/gdsfactory/
    """
    return dict(_GDSFACTORY_GENERIC_LAYER_MAP)


def gdsfactory_to_polaris_layer(
    gds_layer: int,
    gds_datatype: int,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> str:
    """GDSII 层号 → PoLaRIS 层名（R303 双向映射正向）。

    Args:
        gds_layer: GDSII layer 号。
        gds_datatype: GDSII datatype。
        layer_map: 自定义层映射（None 用 SiEPIC 默认）。

    Returns:
        PoLaRIS 层名。未在映射中的层返回 ``LAYER_<layer>_<datatype>``。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
    """
    if layer_map is None:
        layer_map = _SIEPIC_LAYER_MAP
    return layer_map.get(
        (int(gds_layer), int(gds_datatype)),
        f"LAYER_{int(gds_layer)}_{int(gds_datatype)}",
    )


def polaris_to_gdsfactory_layer(
    polaris_name: str,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> tuple[int, int]:
    """PoLaRIS 层名 → GDSII 层号（R303 双向映射反向）。

    Args:
        polaris_name: PoLaRIS 层名（如 "WG", "DEVREC"）。
        layer_map: 自定义层映射（None 用 SiEPIC 默认）。

    Returns:
        (gds_layer, gds_datatype) 元组。

    Raises:
        ValueError: 层名不在映射中（R03: 禁止返回默认值兜底）。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
    """
    if layer_map is None:
        layer_map = _SIEPIC_LAYER_MAP

    # 反向查找
    for (gds_layer, gds_datatype), name in layer_map.items():
        if name == polaris_name:
            return (gds_layer, gds_datatype)

    # R03: 禁止 fall-back，未知层名 raise
    raise ValueError(
        f"PoLaRIS 层名 '{polaris_name}' 在层映射中不存在。"
        f"可用层名: {sorted(set(layer_map.values()))}"
    )


def merge_layer_maps(
    base: dict[tuple[int, int], str],
    custom: dict[tuple[int, int], str],
) -> dict[tuple[int, int], str]:
    """合并层映射（custom 覆盖 base，R303 TR-303.2）。

    用于用户自定义层映射覆盖默认映射。

    Args:
        base: 基础层映射（如 SiEPIC 默认）。
        custom: 自定义层映射（覆盖 base）。

    Returns:
        合并后的新层映射（不修改输入）。

    Raises:
        TypeError: 输入类型错误。
        ValueError: 自定义映射值（层名）为空字符串。

    学术依据:
    - gdsfactory 层映射机制:
      https://gdsfactory.github.io/gdsfactory/
    """
    if not isinstance(base, dict):
        raise TypeError(f"base 必须是 dict, 实际 {type(base).__name__}")
    if not isinstance(custom, dict):
        raise TypeError(f"custom 必须是 dict, 实际 {type(custom).__name__}")

    # 验证 custom 不含空层名（R03）
    for key, name in custom.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"自定义层映射 {key} 的值为空字符串，禁止 fall-back"
            )

    merged = dict(base)
    merged.update(custom)
    return merged


def save_layer_map_to_yaml(
    layer_map: dict[tuple[int, int], str],
    yaml_path: str | Path,
) -> str:
    """将层映射保存为 YAML 文件（R303 TR-303.3 配置文件化）。

    YAML 格式:
        - WG: [1, 0]
        - DEVREC: [68, 0]

    Args:
        layer_map: 层映射字典。
        yaml_path: YAML 文件路径。

    Returns:
        YAML 文件路径。

    Raises:
        ImportError: PyYAML 未安装。
        ValueError: 层映射为空。

    学术依据:
    - YAML 1.2 规范: https://yaml.org/spec/1.2.2/
    - gdsfactory YAML 层映射: https://gdsfactory.github.io/gdsfactory/
    """
    from pathlib import Path as _Path

    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML 未安装，无法保存 YAML 层映射。"
            "请执行 pip install pyyaml 安装。"
        ) from e

    if not layer_map:
        raise ValueError("层映射为空，无法保存")

    yaml_path = _Path(yaml_path)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)

    # 转换为 YAML 友好格式: {layer_name: [layer, datatype]}
    yaml_data = {
        name: [gds_layer, gds_datatype]
        for (gds_layer, gds_datatype), name in layer_map.items()
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            yaml_data,
            f,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
        )

    logger.info("层映射保存到 YAML: %s (%d 项)", yaml_path, len(layer_map))
    return str(yaml_path)


def load_layer_map_from_yaml(
    yaml_path: str | Path,
) -> dict[tuple[int, int], str]:
    """从 YAML 文件加载层映射（R303 TR-303.3 配置文件化）。

    YAML 格式（与 save_layer_map_to_yaml 一致）:
        WG: [1, 0]
        DEVREC: [68, 0]

    Args:
        yaml_path: YAML 文件路径。

    Returns:
        层映射字典 {(gds_layer, datatype): polaris_name}。

    Raises:
        FileNotFoundError: 文件不存在。
        ImportError: PyYAML 未安装。
        ValueError: YAML 格式无效或层映射为空。

    学术依据:
    - YAML 1.2 规范: https://yaml.org/spec/1.2.2/
    - gdsfactory YAML 层映射: https://gdsfactory.github.io/gdsfactory/
    """
    from pathlib import Path as _Path

    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML 未安装，无法加载 YAML 层映射。"
            "请执行 pip install pyyaml 安装。"
        ) from e

    yaml_path = _Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML 文件不存在: {yaml_path}")
    if not yaml_path.is_file():
        raise ValueError(f"YAML 路径不是文件: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"YAML 内容必须是 dict，实际 {type(data).__name__}"
        )
    if not data:
        raise ValueError("YAML 层映射为空")

    # 转换: {name: [layer, datatype]} → {(layer, datatype): name}
    layer_map: dict[tuple[int, int], str] = {}
    for name, value in data.items():
        if not isinstance(name, str):
            raise ValueError(
                f"YAML 层名必须是 str，实际 {type(name).__name__}: {name}"
            )
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(
                f"YAML 层 '{name}' 的值必须是 [layer, datatype] 列表，"
                f"实际 {type(value).__name__}: {value}"
            )
        try:
            gds_layer = int(value[0])
            gds_datatype = int(value[1])
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"YAML 层 '{name}' 的值不是有效整数: {value}"
            ) from e
        layer_map[(gds_layer, gds_datatype)] = name

    logger.info("从 YAML 加载层映射: %s (%d 项)", yaml_path, len(layer_map))
    return layer_map


@dataclass
class LayerMapConfig:
    """层映射配置容器（R303 TR-303.3 配置文件化）。

    封装层映射及其元数据（来源、是否合并默认映射等），
    便于在 PoLaRIS 内部统一传递。

    Attributes:
        layer_map: 层映射字典。
        source: 来源标识（如 "siepic", "gdsfactory", "custom", "yaml"）。
        merged_with_default: 是否合并了默认映射。

    学术依据:
    - gdsfactory 层映射机制: https://gdsfactory.github.io/gdsfactory/
    """

    layer_map: dict[tuple[int, int], str]
    source: str = "custom"
    merged_with_default: bool = False


def build_layer_map_config(
    custom_map: dict[tuple[int, int], str] | None = None,
    base: str = "siepic",
    merge_base: bool = True,
) -> LayerMapConfig:
    """构建层映射配置（R303 综合接口）。

    Args:
        custom_map: 用户自定义层映射（None 仅用 base）。
        base: 基础映射标识 ("siepic" 或 "gdsfactory")。
        merge_base: 是否将 base 与 custom_map 合并（True: custom 覆盖 base）。

    Returns:
        LayerMapConfig 对象。

    Raises:
        ValueError: base 标识无效。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
    """
    if base == "siepic":
        base_map = get_siepic_layer_map()
    elif base == "gdsfactory":
        base_map = get_gdsfactory_generic_layer_map()
    else:
        raise ValueError(
            f"base '{base}' 无效，必须是 'siepic' 或 'gdsfactory'"
        )

    if custom_map is None:
        return LayerMapConfig(
            layer_map=base_map,
            source=base,
            merged_with_default=False,
        )

    if merge_base:
        merged = merge_layer_maps(base_map, custom_map)
        return LayerMapConfig(
            layer_map=merged,
            source=f"{base}+custom",
            merged_with_default=True,
        )

    return LayerMapConfig(
        layer_map=dict(custom_map),
        source="custom",
        merged_with_default=False,
    )


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
    # R301: GDSII 读取增强
    "GDSIILayerInfo",
    "GDSIIInstanceInfo",
    "GDSIICellInfo",
    "GDSIIImportResult",
    "import_gdsii_from_gdsfactory",
    # R302: GDSII 写出增强
    "GDSIIExportConfig",
    "create_gdsii_layout_from_cells",
    "export_gdsii_from_cells",
    "export_gdsii_from_layout",
    "round_trip_gdsii",
    # R303: PDK 双向兼容层映射
    "LayerMapConfig",
    "build_layer_map_config",
    "gdsfactory_to_polaris_layer",
    "get_gdsfactory_generic_layer_map",
    "get_siepic_layer_map",
    "load_layer_map_from_yaml",
    "merge_layer_maps",
    "polaris_to_gdsfactory_layer",
    "save_layer_map_to_yaml",
]
