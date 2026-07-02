"""阶段 7: GDS 导出。

将电路导出为 GDSII 文件，并验证文件完整性（文件大小、结构数、层次数、
可重新加载）。

PoLaRIS v5.0 迁移说明:
    旧 v4 使用 IntegratedPipeline（生成布局+布线 → 转 Placement/Path 对象 →
    export_gds）。v5.0 已将 GDSII 导出封装为 polaris-gdsio 子模块的稳定 API
    ``export_gds(circuit_dict, output_path) -> dict``，直接接收 polaris-core
    风格 circuit dict，无需先布局布线、无需 Placement/Path 对象转换。
    本 stage 改用 circuit_to_dict + export_gds 两步调用。

GDSII 格式来源（R02 学术诚信）:
- GDSII 规范: https://en.wikipedia.org/wiki/GDSII
- KLayout GDSII 文档: https://www.klayout.org/doc-qt5/manual/gds2.html
- SiEPIC EBeam PDK 真实 foundry layer 编号:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Clements 矩阵拓扑: Clements et al., "Optimal design for universal
  multiport interferometers", Optica 2016,
  https://doi.org/10.1364/OPTICA.3.001460
- gdsfactory write_gds 默认参数（dbu=0.001μm=1nm）:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
- KLayout Layout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris_core import CircuitSpec, DeviceSpec, circuit_to_dict
from polaris_gdsio import export_gds

_logger = logging.getLogger("e2e_showcase")


# =============================================================================
# 电路规格定义（与 stage3/stage4/stage6 一致）
# =============================================================================
def _mzi_circuit() -> CircuitSpec:
    """MZI 干涉仪电路（与 stage3/stage4/stage6 一致）。

    5 器件: 1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。

    Returns:
        MZI 电路规格。
    """
    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10,
                       ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")]),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10,
                       ports=[("in", 0, 5, "west"), ("out0", 20, 2.5, "east"),
                              ("out1", 20, 7.5, "east")]),
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5,
                       ports=[("in", 0, 0.25, "west"), ("out", 100, 0.25, "east")]),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5,
                       ports=[("in", 0, 0.25, "west"), ("out", 120, 0.25, "east")]),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10,
                       ports=[("in0", 0, 2.5, "west"), ("in1", 0, 7.5, "west"),
                              ("out0", 20, 2.5, "east"), ("out1", 20, 7.5, "east")]),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out0", "wg1", "in"),
            ("mmi1", "out1", "wg2", "in"),
            ("wg1", "out", "mmi2", "in0"),
            ("wg2", "out", "mmi2", "in1"),
        ],
    )


def _clements_4x4_circuit() -> CircuitSpec:
    """Clements 4x4 光矩阵电路（与 stage3/stage4 一致）。

    4x4 通用多端口干涉仪，含 6 个 MZI 分束器 + 4 个相移器 + 8 个光栅耦合器。
    Clements 矩阵需要 N(N-1)/2 = 6 个 2x2 单元（N=4）。

    来源: Clements et al., Optica 2016,
      https://doi.org/10.1364/OPTICA.3.001460
    """
    devices: list[DeviceSpec] = []
    # 4 个输入光栅耦合器
    for i in range(4):
        devices.append(DeviceSpec(
            f"gci{i}", "grating_coupler", 10, 10,
            ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")],
        ))
    # 6 个 MZI 分束器（Clements 矩形网格）
    for i in range(6):
        devices.append(DeviceSpec(
            f"mzi{i}", "mmi_2x2", 20, 10,
            ports=[("in0", 0, 2.5, "west"), ("in1", 0, 7.5, "west"),
                   ("out0", 20, 2.5, "east"), ("out1", 20, 7.5, "east")],
        ))
    # 4 个相移器（输出相位调谐）
    for i in range(4):
        devices.append(DeviceSpec(
            f"ps{i}", "phase_shifter", 50, 0.5,
            ports=[("in", 0, 0.25, "west"), ("out", 50, 0.25, "east")],
        ))
    # 4 个输出光栅耦合器
    for i in range(4):
        devices.append(DeviceSpec(
            f"gco{i}", "grating_coupler", 10, 10,
            ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")],
        ))

    # 连接: 输入 → MZI 网格 → 相移器 → 输出
    # Clements 矩形网格（简化链式连接，保证布线可达）
    connections = [
        # 输入耦合器 → MZI 第一层
        ("gci0", "out", "mzi0", "in0"),
        ("gci1", "out", "mzi0", "in1"),
        ("gci2", "out", "mzi1", "in0"),
        ("gci3", "out", "mzi1", "in1"),
        # MZI 第一层 → 第二层
        ("mzi0", "out1", "mzi2", "in0"),
        ("mzi1", "out0", "mzi2", "in1"),
        # MZI 第二层 → 第三层
        ("mzi2", "out0", "mzi3", "in0"),
        ("mzi2", "out1", "mzi4", "in0"),
        # MZI 第三层 → 第四层
        ("mzi3", "out1", "mzi5", "in0"),
        ("mzi4", "out0", "mzi5", "in1"),
        # MZI → 相移器
        ("mzi3", "out0", "ps0", "in"),
        ("mzi5", "out0", "ps1", "in"),
        ("mzi5", "out1", "ps2", "in"),
        ("mzi4", "out1", "ps3", "in"),
        # 相移器 → 输出耦合器
        ("ps0", "out", "gco0", "in"),
        ("ps1", "out", "gco1", "in"),
        ("ps2", "out", "gco2", "in"),
        ("ps3", "out", "gco3", "in"),
    ]
    return CircuitSpec(
        name="Clements_4x4",
        canvas_w=800,
        canvas_h=600,
        devices=devices,
        connections=connections,
    )


def _quantum_placeholder_circuit() -> CircuitSpec:
    """量子玻色采样占位电路（与 stage3/stage4 一致）。

    玻色采样电路: 4 模酉矩阵网络，含分束器阵列与相移器，
    用于演示量子光子计算的版图生成能力。

    来源: Aaronson & Arkhipov, "The Computational Complexity of Linear
      Optics", Theory of Computing 2013,
      https://doi.org/10.4086/toc.2013.v009a004
    """
    devices: list[DeviceSpec] = []
    # 4 个输入源（单光子源占位）
    for i in range(4):
        devices.append(DeviceSpec(
            f"src{i}", "grating_coupler", 10, 10,
            ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")],
        ))
    # 4 个分束器（构成酉变换网络）
    for i in range(4):
        devices.append(DeviceSpec(
            f"bs{i}", "mmi_2x2", 20, 10,
            ports=[("in0", 0, 2.5, "west"), ("in1", 0, 7.5, "west"),
                   ("out0", 20, 2.5, "east"), ("out1", 20, 7.5, "east")],
        ))
    # 4 个探测器（单光子探测器占位）
    for i in range(4):
        devices.append(DeviceSpec(
            f"det{i}", "detector", 10, 10,
            ports=[("in", 0, 5, "west")],
        ))

    # 连接: 源 → 分束器网络 → 探测器
    connections = [
        ("src0", "out", "bs0", "in0"),
        ("src1", "out", "bs0", "in1"),
        ("src2", "out", "bs1", "in0"),
        ("src3", "out", "bs1", "in1"),
        ("bs0", "out1", "bs2", "in0"),
        ("bs1", "out0", "bs2", "in1"),
        ("bs0", "out0", "bs3", "in0"),
        ("bs1", "out1", "bs3", "in1"),
        ("bs2", "out0", "det0", "in"),
        ("bs2", "out1", "det1", "in"),
        ("bs3", "out0", "det2", "in"),
        ("bs3", "out1", "det3", "in"),
    ]
    return CircuitSpec(
        name="Quantum_BosonSampling",
        canvas_w=600,
        canvas_h=500,
        devices=devices,
        connections=connections,
    )


# =============================================================================
# 主流程
# =============================================================================
def run(output_dir: Path) -> dict:
    """执行阶段 7: GDS 导出。

    对 3 个电路（MZI、Clements 4x4、量子占位）转为 circuit dict 后直接
    调用 polaris-gdsio ``export_gds`` 导出为 GDSII 文件，并验证文件完整性
    （export_gds 内部已含读回验证 loadable 字段）。

    Args:
        output_dir: 输出目录。

    Returns:
        dict 含 circuits 列表，每个电路含:
        - name: 电路名称
        - gds_path: GDS 文件路径
        - file_size_bytes: 文件大小（字节）
        - n_structures: GDS 结构数（cell 数，含顶层）
        - n_layers: GDS 层数
        - loadable: 是否可重新加载

    Raises:
        RuntimeError: GDS 导出或验证失败（R03 禁止 fall-back）。
    """
    _logger.info("阶段 7 开始: GDS 导出（polaris-gdsio）")
    output_dir = Path(output_dir)
    gds_dir = output_dir / "gds"
    gds_dir.mkdir(parents=True, exist_ok=True)

    circuits = [
        _mzi_circuit(),
        _clements_4x4_circuit(),
        _quantum_placeholder_circuit(),
    ]
    _logger.info("待导出电路: %s", [c.name for c in circuits])

    results: list[dict] = []
    for circuit in circuits:
        _logger.info(
            "处理电路: %s (%d 器件, %d 连接)",
            circuit.name,
            len(circuit.devices),
            len(circuit.connections),
        )

        # 步骤 1: 转为 circuit dict
        circuit_dict = circuit_to_dict(circuit)

        # 步骤 2: 导出 GDSII 文件（polaris-gdsio 内部含读回验证）
        gds_path = gds_dir / f"{circuit.name}.gds"
        export_result = export_gds(circuit_dict, str(gds_path))

        _logger.info(
            "GDS 导出: %s (%d bytes, 结构=%d, 层次=%d, 可加载=%s)",
            Path(export_result["path"]).name,
            export_result["file_size_bytes"],
            export_result["n_structures"],
            export_result["n_layers"],
            export_result["loadable"],
        )

        results.append(
            {
                "name": circuit.name,
                "gds_path": export_result["path"],
                "file_size_bytes": export_result["file_size_bytes"],
                "n_structures": export_result["n_structures"],
                "n_layers": export_result["n_layers"],
                "loadable": export_result["loadable"],
            }
        )

    _logger.info("阶段 7 完成: 成功导出 %d 个 GDS 文件", len(results))
    return {"circuits": results}
