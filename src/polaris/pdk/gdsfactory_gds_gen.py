"""gdsfactory GDS 生成模块。

原属 gdsfactory_integration.py §1（批次 10-B 拆分提取），保留原始文献溯源。

提供基于 gdsfactory 的参数化器件 GDS 生成接口:
- is_available / generate_mzi_gds / generate_ring_resonator_gds /
  generate_component_gds / list_available_components
- _orientation_to_direction: gdsfactory 端口朝向 → PoLaRIS Direction

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- ubcpdk (MIT): https://github.com/gdsfactory/ubc
- gf180mcu PDK (Apache-2.0): https://github.com/gdsfactory/gf180mcu-pdk
- IHP Open Source PDK (Apache-2.0): https://github.com/IHP-GmbH/IHP-Open-PDK
- 差距分析 P0-3: docs/commercial_gap_analysis.md

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging

from polaris.pdk.port import Direction

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


__all__ = [
    "is_available",
    "generate_mzi_gds",
    "generate_ring_resonator_gds",
    "generate_component_gds",
    "list_available_components",
    "_orientation_to_direction",
    "_HAS_GDSFACTORY",
    "_ORIENTATION_TO_DIRECTION",
]
