"""PoLaRIS Web Server - 预设电路模块（polaris-gui 子模块）。

从 ``web_server.py`` 拆分而来，包含预设电路定义与构建:
- MZI 干涉仪电路
- Ring Resonator 环形谐振器电路

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- Clements et al., "Optimal design for universal multiport interferometers",
  Optica 2016 https://doi.org/10.1364/OPTICA.3.001460
- Reck et al., "Experimental realization of any discrete unitary operator",
  PRL 1994 https://doi.org/10.1103/PhysRevLett.73.58
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://www.cambridge.org/core/books/silicon-photonics-design/
- gdsfactory 预设电路 https://github.com/gdsfactory/gdsfactory
- Knill-Laflamme-Milburn (KLM) 线性光学量子计算
  https://www.nature.com/articles/35051009

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

def _get_presets() -> list[dict]:
    """获取预设电路列表。"""
    return [
        {
            "id": "mzi",
            "name": "MZI 干涉仪",
            "description": "马赫-曾德尔干涉仪（2x2 MMI + 波导臂）",
            "devices": 5,
            "platform": "SOI",
        },
        {
            "id": "ring",
            "name": "微环谐振器",
            "description": "单微环 + 总线波导",
            "devices": 4,
            "platform": "SOI",
        },
        {
            "id": "clements_4x4",
            "name": "Clements 4x4 光矩阵",
            "description": "可编程光子线性计算单元（4x4）",
            "devices": 28,
            "platform": "SOI",
        },
    ]


def _mzi_circuit():
    """构建 MZI 干涉仪电路。

    端口名对齐 PDK 定义：
    - mmi_1x2: in, out1, out2（来源: polaris.pdk.soi.couplers._make_mmi_1x2_ports）
    - mmi_2x2: in1, in2, out1, out2（来源: polaris.pdk.soi.couplers._make_mmi_2x2_ports）
    """
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="MZI",
        canvas_w=1000,
        canvas_h=600,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            # 波导 length 参数 = width_um（光传播方向为较长维度）
            # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5, params={"length": 100.0, "length_um": 100.0}),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5, params={"length": 120.0, "length_um": 120.0}),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
    )


def _ring_circuit():
    """构建微环谐振器电路。"""
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="Ring",
        canvas_w=800,
        canvas_h=600,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            # 波导 length 参数 = width_um（光传播方向为较长维度）
            # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
            DeviceSpec("wg1", "strip_waveguide", 200, 0.5, params={"length": 200.0, "length_um": 200.0}),
            DeviceSpec("ring1", "ring_resonator", 30, 30),
            DeviceSpec("gc2", "grating_coupler", 10, 10),
        ],
        connections=[
            ("gc1", "out", "wg1", "in"),
            ("wg1", "out", "ring1", "bus_in"),
            ("ring1", "bus_out", "gc2", "in"),
        ],
    )


_PRESET_BUILDERS = {
    "mzi": _mzi_circuit,
    "ring": _ring_circuit,
}


def _build_circuit(preset_id: str):
    """根据预设 ID 构建电路规格。"""
    if preset_id in _PRESET_BUILDERS:
        return _PRESET_BUILDERS[preset_id]()
    if preset_id == "clements_4x4":
        raise ImportError(
            "_build_circuit('clements_4x4') 需要 polaris_orchestrator 子模块提供 "
            "_default_demo_circuit（v5.0 polaris_orchestrator 未迁移该函数，"
            "R03 禁止 fall-back）。请在 polaris_gui 内联构建 Clements 电路。"
        )
    raise ValueError(f"未知预设: {preset_id}")



__all__ = ["_get_presets", "_build_circuit"]
