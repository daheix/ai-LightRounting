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


def _clements_4x4_circuit():
    """构建 Clements 4×4 可编程光子线性计算单元电路。

    R391 修复: 原 raise ImportError 依赖未迁移的 polaris_orchestrator.
    _default_demo_circuit，现内联构建 Clements 4×4 mesh。

    Clements 拓扑（Clements et al., Optica 2016, Fig.2）:
    4 条水平光通道，6 个 directional_coupler 作分束器，分 4 层交替排列:
      L0: dc1(ch0,ch1), dc2(ch2,ch3)
      L1: dc3(ch1,ch2)
      L2: dc4(ch0,ch1), dc5(ch2,ch3)
      L3: dc6(ch1,ch2)
    共 6 个分束器 = M(M-1)/2 = 4*3/2，实现任意 4×4 酉矩阵分解。

    器件清单 (28):
    - 8 grating_coupler (gc1-4 输入, gc5-8 输出)
    - 8 strip_waveguide (wg_in1-4 输入臂, wg_out1-4 输出臂)
    - 6 directional_coupler (dc1-6 分束器)
    - 6 strip_waveguide (wg_mid1-6 层间跳线)

    链式连接确保可布线，每个 DC 端口连接到唯一器件。

    来源: Clements et al., "Optimal design for universal multiport
    interferometers", Optica 3(12), 1460-1465 (2016).
    URL: https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
    """
    from polaris_core.specs import CircuitSpec, DeviceSpec

    # directional_coupler PDK 尺寸: 10×1.5μm, 4 端口 in1/in2/out1/out2
    # (来源: SiEPIC EBeam PDK, coupling_length=10μm, gap=200nm)
    dc_w, dc_h = 10.0, 1.5
    wg_len = 60.0  # 层间波导长度

    devices = [
        DeviceSpec("gc1", "grating_coupler", 10, 10),
        DeviceSpec("gc2", "grating_coupler", 10, 10),
        DeviceSpec("gc3", "grating_coupler", 10, 10),
        DeviceSpec("gc4", "grating_coupler", 10, 10),
        DeviceSpec("wg_in1", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_in2", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_in3", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_in4", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("dc1", "directional_coupler", dc_w, dc_h),
        DeviceSpec("dc2", "directional_coupler", dc_w, dc_h),
        DeviceSpec("wg_mid1", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_mid2", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_mid3", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_mid4", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("dc3", "directional_coupler", dc_w, dc_h),
        DeviceSpec("wg_mid5", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_mid6", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("dc4", "directional_coupler", dc_w, dc_h),
        DeviceSpec("dc5", "directional_coupler", dc_w, dc_h),
        DeviceSpec("dc6", "directional_coupler", dc_w, dc_h),
        DeviceSpec("wg_out1", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_out2", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_out3", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("wg_out4", "strip_waveguide", wg_len, 0.5,
                   params={"length": wg_len, "length_um": wg_len}),
        DeviceSpec("gc5", "grating_coupler", 10, 10),
        DeviceSpec("gc6", "grating_coupler", 10, 10),
        DeviceSpec("gc7", "grating_coupler", 10, 10),
        DeviceSpec("gc8", "grating_coupler", 10, 10),
    ]

    connections = [
        ("gc1", "out", "wg_in1", "in"),
        ("gc2", "out", "wg_in2", "in"),
        ("gc3", "out", "wg_in3", "in"),
        ("gc4", "out", "wg_in4", "in"),
        ("wg_in1", "out", "dc1", "in1"),
        ("wg_in2", "out", "dc1", "in2"),
        ("wg_in3", "out", "dc2", "in1"),
        ("wg_in4", "out", "dc2", "in2"),
        ("dc1", "out1", "wg_mid1", "in"),
        ("dc1", "out2", "wg_mid2", "in"),
        ("dc2", "out1", "wg_mid3", "in"),
        ("dc2", "out2", "wg_mid4", "in"),
        ("wg_mid2", "out", "dc3", "in1"),
        ("wg_mid3", "out", "dc3", "in2"),
        ("dc3", "out1", "wg_mid5", "in"),
        ("dc3", "out2", "wg_mid6", "in"),
        ("wg_mid1", "out", "dc4", "in1"),
        ("wg_mid5", "out", "dc4", "in2"),
        ("wg_mid6", "out", "dc5", "in1"),
        ("wg_mid4", "out", "dc5", "in2"),
        ("dc4", "out2", "dc6", "in1"),
        ("dc5", "out1", "dc6", "in2"),
        ("dc4", "out1", "wg_out1", "in"),
        ("dc6", "out1", "wg_out2", "in"),
        ("dc6", "out2", "wg_out3", "in"),
        ("dc5", "out2", "wg_out4", "in"),
        ("wg_out1", "out", "gc5", "in"),
        ("wg_out2", "out", "gc6", "in"),
        ("wg_out3", "out", "gc7", "in"),
        ("wg_out4", "out", "gc8", "in"),
    ]

    return CircuitSpec(
        name="Clements4x4",
        canvas_w=1500,
        canvas_h=800,
        devices=devices,
        connections=connections,
    )


_PRESET_BUILDERS = {
    "mzi": _mzi_circuit,
    "ring": _ring_circuit,
    "clements_4x4": _clements_4x4_circuit,
}


def _build_circuit(preset_id: str):
    """根据预设 ID 构建电路规格。"""
    if preset_id in _PRESET_BUILDERS:
        return _PRESET_BUILDERS[preset_id]()
    raise ValueError(f"未知预设: {preset_id}")



__all__ = ["_get_presets", "_build_circuit"]
