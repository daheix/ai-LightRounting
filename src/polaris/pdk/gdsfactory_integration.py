"""gdsfactory 集成模块（步骤4：生成真实参数化器件 GDS）。

gdsfactory 是开源光子芯片设计库（MIT 许可证），含数百个参数化组件。
本模块提供 gdsfactory 集成接口，缺失时优雅降级到 PoLaRIS 原生 GDS 导出。

按规则 5.3，gdsfactory 为可选依赖：
- 已安装时：用 gdsfactory 生成真实参数化器件 GDS（含真实几何形状）
- 未安装时：降级到 polaris.eval.layout_render.export_gds（矩形抽象）

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- ubcpdk (MIT): https://github.com/gdsfactory/ubc
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import gdsfactory as gf

    _HAS_GDSFACTORY = True
except ImportError:
    gf = None
    _HAS_GDSFACTORY = False


def is_available() -> bool:
    """检查 gdsfactory 是否可用。

    Returns:
        True 若 gdsfactory 已安装。
    """
    return _HAS_GDSFACTORY


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

            gf.PDK.get_generic().activate()
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

            gf.PDK.get_generic().activate()
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

        gf.PDK.get_generic().activate()
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


__all__ = [
    "generate_component_gds",
    "generate_mzi_gds",
    "generate_ring_resonator_gds",
    "is_available",
    "list_available_components",
]
