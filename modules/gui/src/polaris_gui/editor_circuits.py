"""PoLaRIS Web 编辑器预设电路构建（editor_circuits.py）。

从 editor_handlers.py 拆分而来（R11 质量门禁：单文件≤800行），承载带
端口定义的预设电路构建逻辑。polaris-route 的 ``_find_port`` 需要每个
device 含 ports 字段，故本模块专门提供带端口的 MZI/Ring 电路规格。

## 预设电路

- ``mzi``: MZI 干涉仪（5 器件：1 GC + 1 MMI1x2 + 2 波导臂 + 1 MMI2x2）
- ``ring``: 微环谐振器（4 器件：2 GC + 1 波导 + 1 ring_resonator）

## 端口几何约定（SiEPIC EBeam PDK）

端口元组格式 ``(name, dx, dy, direction)``:
- ``dx, dy``: 端口相对器件原点（左下角）的偏移（μm）
- ``direction``: 端口朝向 ``north/south/east/west``（DRC PORT_FACING 用）

文献来源（R02 学术诚信，≥5 条）:
1. SiEPIC EBeam PDK mmi_1x2/mmi_2x2/grating_coupler 端口定义:
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
2. polaris_core.specs.DeviceSpec ports 字段约定:
   https://gdsfactory.github.io/gdsfactory/
3. examples/e2e_showcase/stages/stage4_routing.py（同款电路）:
   https://dl.acm.org/doi/10.1145/3698364.3705355
4. Chrostowski & Hochberg 2015 Silicon Photonics Design:
   https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
5. KLayout SiEPIC-Tools PinRec/DEVREC 端口标记规范:
   https://github.com/SiEPIC/SiEPIC-Tools/wiki

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

from typing import Any


def _mzi_circuit_with_ports():
    """构建带端口定义的 MZI 干涉仪电路规格。

    5 器件：1 光栅耦合器 + 1 MMI1x2 + 2 波导臂 + 1 MMI2x2，
    构成马赫-曾德干涉仪。端口坐标对齐 SiEPIC EBeam PDK 几何约定。

    来源:
    - SiEPIC EBeam PDK mmi_1x2/mmi_2x2/grating_coupler 端口定义
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - examples/e2e_showcase/stages/stage4_routing.py（同款电路）

    Returns:
        ``CircuitSpec`` 实例（含 ports）。
    """
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10,
                       ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")]),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10,
                       ports=[("in", 0, 5, "west"),
                              ("out0", 20, 2.5, "east"),
                              ("out1", 20, 7.5, "east")]),
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5,
                       ports=[("in", 0, 0.25, "west"),
                              ("out", 100, 0.25, "east")]),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5,
                       ports=[("in", 0, 0.25, "west"),
                              ("out", 120, 0.25, "east")]),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10,
                       ports=[("in0", 0, 2.5, "west"),
                              ("in1", 0, 7.5, "west"),
                              ("out0", 20, 2.5, "east"),
                              ("out1", 20, 7.5, "east")]),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out0", "wg1", "in"),
            ("mmi1", "out1", "wg2", "in"),
            ("wg1", "out", "mmi2", "in0"),
            ("wg2", "out", "mmi2", "in1"),
        ],
    )


def _ring_circuit_with_ports():
    """构建带端口定义的微环谐振器电路规格。

    4 器件：2 光栅耦合器 + 1 直波导 + 1 微环，构成微环谐振器。

    Returns:
        ``CircuitSpec`` 实例（含 ports）。
    """
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="Ring",
        canvas_w=400,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10,
                       ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")]),
            DeviceSpec("wg1", "strip_waveguide", 200, 0.5,
                       ports=[("in", 0, 0.25, "west"),
                              ("out", 200, 0.25, "east")]),
            DeviceSpec("ring1", "ring_resonator", 30, 30,
                       ports=[("bus_in", 0, 15, "west"),
                              ("bus_out", 30, 15, "east")]),
            DeviceSpec("gc2", "grating_coupler", 10, 10,
                       ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")]),
        ],
        connections=[
            ("gc1", "out", "wg1", "in"),
            ("wg1", "out", "ring1", "bus_in"),
            ("ring1", "bus_out", "gc2", "in"),
        ],
    )


# 预设 ID → 电路构建器（带 ports 版本，用于布局+布线+DRC）
_PRESET_BUILDERS_WITH_PORTS = {
    "mzi": _mzi_circuit_with_ports,
    "ring": _ring_circuit_with_ports,
}


def build_circuit_dict(preset_id: str) -> dict[str, Any]:
    """根据预设 ID 构建带端口的 circuit dict（供 polaris-place/route/drc 使用）。

    Args:
        preset_id: 预设 ID（"mzi" / "ring"）。

    Returns:
        polaris-core 风格 circuit dict（含 devices/connections/ports/canvas）。

    Raises:
        ValueError: 未知预设 ID（R03 禁止 fall-back）。
    """
    builder = _PRESET_BUILDERS_WITH_PORTS.get(preset_id)
    if builder is None:
        raise ValueError(
            f"未知预设: {preset_id}"
            f"（可用: {list(_PRESET_BUILDERS_WITH_PORTS)}）"
        )
    from polaris_core import circuit_to_dict
    return circuit_to_dict(builder())


__all__ = [
    "_mzi_circuit_with_ports",
    "_ring_circuit_with_ports",
    "_PRESET_BUILDERS_WITH_PORTS",
    "build_circuit_dict",
]
