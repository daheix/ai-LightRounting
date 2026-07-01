"""R307 PCell 双向兼容 — gdsfactory PCell ↔ PoLaRIS PCell。

批次 10-B 拆分说明（2026-07-01）:
    从 gdsfactory_advanced.py 抽出 R307 PCell 双向转换与往返验证模块。

来源（R02 学术诚信，≥5 文献 URL）:
1. gdsfactory PDK tutorial: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
2. gdsfactory PDK import: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
3. gdsfactory ComponentFactory: https://gdsfactory.github.io/gdsfactory/api.html
4. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
5. Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
   https://doi.org/10.1017/CBO9781316084168
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# gdsfactory 可选导入（R307 PCell 注册需要）。
try:  # pragma: no cover - 环境依赖
    import gdsfactory as gf

    _HAS_GDSFACTORY = True
except ImportError:  # pragma: no cover - 环境依赖
    gf = None  # type: ignore[assignment]
    _HAS_GDSFACTORY = False


@dataclass
class PolarisPCellSpec:
    """PoLaRIS PCell 规格（R307）。

    Attributes:
        name: PCell 名。
        parameters: 参数字典（参数名 → 值）。
        layer_map: 层映射（(layer,datatype) → 层名）。
        ports: 端口列表，每项 {name, x, y, orientation_deg, width_um}。
        builder: 可选的构建回调（返回 Device）。
    """

    name: str
    parameters: dict[str, Any]
    layer_map: dict[tuple[int, int], str]
    ports: list[dict[str, Any]]
    builder: Callable[[], Any] | None = None


@dataclass
class GDSFactoryPCellSpec:
    """gdsfactory PCell 规格（R307）。

    Attributes:
        name: PCell 名（注册到 gdsfactory PDK 的 cell 名）。
        parameters: 参数字典。
        cell_function: gdsfactory 组件工厂函数全名（如 'gf.components.mmi1x2'）。
        cross_section: 截面名（如 'strip'）。
        port_layers: 端口标记层列表。
    """

    name: str
    parameters: dict[str, Any]
    cell_function: str
    cross_section: str = "strip"
    port_layers: list[tuple[int, int]] = field(default_factory=list)


# gdsfactory orientation（度）↔ PoLaRIS 方向字符串映射
# 来源: gdsfactory Port.orientation（文献 1）
_ORIENTATION_TO_DIR: dict[float, str] = {
    0.0: "EAST",
    90.0: "NORTH",
    180.0: "WEST",
    270.0: "SOUTH",
}
_DIR_TO_ORIENTATION: dict[str, float] = {v: k for k, v in _ORIENTATION_TO_DIR.items()}


def polaris_to_gdsfactory_pcell(spec: PolarisPCellSpec) -> GDSFactoryPCellSpec:
    """PoLaRIS PCell 规格 → gdsfactory PCell 规格（R307，纯数据转换）。

    Args:
        spec: PolarisPCellSpec 实例。

    Returns:
        GDSFactoryPCellSpec 实例。

    Raises:
        ValueError: spec.name 为空或端口方向未知。
    """
    if not spec.name:
        raise ValueError("PolarisPCellSpec.name 不能为空")
    port_layers = [
        lk for lk, ln in spec.layer_map.items() if ln in ("PORT", "PORTE", "PIN")
    ]
    return GDSFactoryPCellSpec(
        name=spec.name,
        parameters=dict(spec.parameters),
        cell_function=f"polaris.cells.{spec.name}",
        cross_section="strip",
        port_layers=port_layers,
    )


def gdsfactory_to_polaris_pcell(gf_spec: GDSFactoryPCellSpec) -> PolarisPCellSpec:
    """gdsfactory PCell 规格 → PoLaRIS PCell 规格（R307，纯数据转换）。

    Args:
        gf_spec: GDSFactoryPCellSpec 实例。

    Returns:
        PolarisPCellSpec 实例（ports 为空，需后续从 GDS 提取）。

    Raises:
        ValueError: gf_spec.name 或 cell_function 为空。
    """
    if not gf_spec.name:
        raise ValueError("GDSFactoryPCellSpec.name 不能为空")
    if not gf_spec.cell_function:
        raise ValueError("GDSFactoryPCellSpec.cell_function 不能为空")
    layer_map = {pl: "PORT" for pl in gf_spec.port_layers}
    if (1, 0) not in layer_map:
        layer_map[(1, 0)] = "WG"
    return PolarisPCellSpec(
        name=gf_spec.name,
        parameters=dict(gf_spec.parameters),
        layer_map=layer_map,
        ports=[],
    )


def register_pcell_to_gdsfactory(spec: PolarisPCellSpec) -> str:
    """将 PoLaRIS PCell 注册为 gdsfactory 组件（R307，需 gdsfactory）。

    Args:
        spec: PolarisPCellSpec 实例（builder 必须可调用）。

    Returns:
        注册后的 gdsfactory cell 名。

    Raises:
        ImportError: gdsfactory 未安装（R03：不静默兜底）。
        ValueError: spec.builder 不可调用。
    """
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法注册 PCell。"
            "请执行 pip install gdsfactory 或检查 Python 版本兼容性。"
        )
    if spec.builder is None or not callable(spec.builder):
        raise ValueError(f"PCell {spec.name!r} 的 builder 不可调用")
    pdk = gf.get_active_pdk()  # type: ignore[union-attr]
    pdk.register_cells(**{spec.name: spec.builder})
    logger.info("PCell %s 已注册到 gdsfactory PDK", spec.name)
    return spec.name


def pcell_roundtrip_verify(spec: PolarisPCellSpec) -> bool:
    """PCell 双向转换往返一致性验证（R307）。

    流程: PolarisPCellSpec → GDSFactoryPCellSpec → PolarisPCellSpec，
    验证 name/parameters 一致。

    Args:
        spec: PolarisPCellSpec 实例。

    Returns:
        True 若往返一致。

    Raises:
        RuntimeError: 往返不一致（R03：不静默返回 False）。
    """
    gf_spec = polaris_to_gdsfactory_pcell(spec)
    back = gdsfactory_to_polaris_pcell(gf_spec)
    if back.name != spec.name:
        raise RuntimeError(
            f"PCell 往返 name 不一致: {spec.name!r} → {back.name!r}"
        )
    if back.parameters != spec.parameters:
        raise RuntimeError(
            f"PCell 往返 parameters 不一致: {spec.parameters} → {back.parameters}"
        )
    return True


__all__ = [
    "PolarisPCellSpec",
    "GDSFactoryPCellSpec",
    "polaris_to_gdsfactory_pcell",
    "gdsfactory_to_polaris_pcell",
    "register_pcell_to_gdsfactory",
    "pcell_roundtrip_verify",
]
