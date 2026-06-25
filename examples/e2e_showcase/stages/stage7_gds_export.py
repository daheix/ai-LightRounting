"""阶段 7: GDS 导出。

将布局布线结果导出为 GDSII 文件，并验证文件完整性（文件大小、结构数、
层次数、可重新加载）。

对应路标: R06（GDSII 导出）/ R22（OASIS 导出）

GDSII 格式来源（学术诚信，规则 18）:
- GDSII 规范: https://en.wikipedia.org/wiki/GDSII
- KLayout GDSII 文档: https://www.klayout.org/doc-qt5/manual/gds2.html
- SiEPIC EBeam PDK 真实 foundry layer 编号:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Clements 矩阵拓扑: Clements et al., "Optimal design for universal
  multiport interferometers", Optica 2016,
  https://doi.org/10.1364/OPTICA.3.001460
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.eval.layout_render import export_gds
from polaris.pipeline._converters import convert_to_paths, convert_to_placements
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

_logger = logging.getLogger("e2e_showcase")


# =============================================================================
# 电路规格定义（与 stage3 一致）
# =============================================================================
def _mzi_circuit() -> CircuitSpec:
    """MZI 干涉仪电路（与 stage3 一致）。

    5 器件: 1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。
    """
    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            DeviceSpec(
                "wg1", "strip_waveguide", 100, 0.5,
                params={"length": 100.0},
            ),
            DeviceSpec(
                "wg2", "strip_waveguide", 120, 0.5,
                params={"length": 120.0},
            ),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
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
    """Clements 4x4 光矩阵电路（与 stage3 一致）。

    4x4 通用多端口干涉仪，含 6 个 MZI 分束器 + 4 个相移器 + 8 个光栅耦合器。
    Clements 矩阵需要 N(N-1)/2 = 6 个 2x2 单元（N=4）。

    来源: Clements et al., Optica 2016,
      https://doi.org/10.1364/OPTICA.3.001460
    """
    devices: list[DeviceSpec] = []
    # 4 个输入光栅耦合器
    for i in range(4):
        devices.append(DeviceSpec(f"gci{i}", "grating_coupler", 10, 10))
    # 6 个 MZI 分束器（Clements 矩形网格）
    for i in range(6):
        devices.append(DeviceSpec(f"mzi{i}", "mmi_2x2", 20, 10))
    # 4 个相移器（输出相位调谐）
    for i in range(4):
        devices.append(DeviceSpec(f"ps{i}", "strip_waveguide", 50, 0.5, params={"length": 50.0}))
    # 4 个输出光栅耦合器
    for i in range(4):
        devices.append(DeviceSpec(f"gco{i}", "grating_coupler", 10, 10))

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
    """量子玻色采样占位电路（与 stage3 一致）。

    玻色采样电路: 4 模酉矩阵网络，含分束器阵列与相移器，
    用于演示量子光子计算的版图生成能力。

    来源: Aaronson & Arkhipov, "The Computational Complexity of Linear
      Optics", Theory of Computing 2013,
      https://doi.org/10.4086/toc.2013.v009a004
    """
    devices: list[DeviceSpec] = []
    # 4 个输入源（单光子源占位）
    for i in range(4):
        devices.append(DeviceSpec(f"src{i}", "grating_coupler", 10, 10))
    # 4 个分束器（构成酉变换网络）
    for i in range(4):
        devices.append(DeviceSpec(f"bs{i}", "mmi_2x2", 20, 10))
    # 4 个探测器（单光子探测器占位）
    for i in range(4):
        devices.append(DeviceSpec(f"det{i}", "grating_coupler", 10, 10))

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
# GDS 验证
# =============================================================================
def _verify_gds(gds_path: Path) -> tuple[int, int, bool]:
    """验证 GDS 文件可重新加载，返回 (结构数, 层次数, 可加载)。

    用 klayout.db 重新读取 GDS 文件，统计 top cell 数（GDSII 结构数）
    与使用的 layer 数。读取失败时 raise（规则 14.1: 无 fall-back）。

    GDSII 术语: "structure" = cell（单元格），GDSII 文件由若干 structure 组成。
    来源: GDSII 规范 https://en.wikipedia.org/wiki/GDSII

    Args:
        gds_path: GDS 文件路径。

    Returns:
        (n_structures, n_layers, loadable) 元组。loadable=True 表示成功重新加载。

    Raises:
        RuntimeError: GDS 读取失败或无 top cell。
    """
    import klayout.db as db

    try:
        ly = db.Layout()
        ly.read(str(gds_path))
        top_cells = list(ly.top_cells())
        if not top_cells:
            raise RuntimeError(f"GDS 无 top cell: {gds_path}")
        # GDSII 结构数 = top cell 数（每个 top cell 是一个独立结构）
        n_structures = len(top_cells)
        # 层数 = 使用的 layer info 数（WG/DEVREC/PIN 等）
        n_layers = len(list(ly.layer_infos()))
        return n_structures, n_layers, True
    except RuntimeError:
        # 重新抛出 RuntimeError（无 fall-back）
        raise
    except Exception as e:
        # 其他异常包装为 RuntimeError（无 fall-back，禁止返回假数据）
        raise RuntimeError(f"GDS 验证失败: {gds_path}: {e}") from e


# =============================================================================
# 主流程
# =============================================================================
def run(output_dir: Path) -> dict:
    """执行阶段 7: GDS 导出。

    对 3 个电路（MZI、Clements 4x4、量子占位）执行 IntegratedPipeline
    生成布局+布线，导出为 GDSII 文件，并验证文件完整性。

    Args:
        output_dir: 输出目录。

    Returns:
        dict 含 circuits 列表，每个电路含:
        - name: 电路名称
        - gds_path: GDS 文件路径
        - file_size_bytes: 文件大小（字节）
        - n_structures: GDS 结构数（top cell 数）
        - n_layers: GDS 层次数
        - loadable: 是否可重新加载

    Raises:
        RuntimeError: GDS 导出或验证失败（规则 14.1: 无 fall-back）。
    """
    _logger.info("阶段 7 开始: GDS 导出")
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

        # 步骤 1: 运行 IntegratedPipeline 生成布局+布线
        cfg = PipelineConfig(
            canvas_w=circuit.canvas_w,
            canvas_h=circuit.canvas_h,
            max_sim_iterations=1,
            output_dir=str(output_dir / "pipeline" / circuit.name),
        )
        pipeline = IntegratedPipeline(cfg)
        pipe_result = pipeline.run(circuit)
        _logger.info(
            "布局布线完成: %s (器件=%d, 路径=%d, 损耗=%.2f dB)",
            circuit.name,
            len(pipe_result.placements),
            len(pipe_result.paths),
            pipe_result.total_loss_db,
        )

        # 步骤 2: 转换为 Placement/WaveguidePath 对象
        placements = convert_to_placements(circuit, pipe_result.placements)
        paths = convert_to_paths(pipe_result.paths)
        _logger.info(
            "对象转换: %s (Placement=%d, WaveguidePath=%d)",
            circuit.name,
            len(placements),
            len(paths),
        )

        # 步骤 3: 导出 GDSII 文件
        gds_path = gds_dir / f"{circuit.name}.gds"
        export_gds(placements, paths, str(gds_path))
        file_size = gds_path.stat().st_size
        _logger.info(
            "GDS 导出: %s (%d bytes)",
            gds_path.name,
            file_size,
        )

        # 步骤 4: 验证 GDS 可重新加载
        n_structures, n_layers, loadable = _verify_gds(gds_path)
        _logger.info(
            "GDS 验证: %s (结构=%d, 层次=%d, 可加载=%s)",
            circuit.name,
            n_structures,
            n_layers,
            loadable,
        )

        results.append(
            {
                "name": circuit.name,
                "gds_path": str(gds_path),
                "file_size_bytes": file_size,
                "n_structures": n_structures,
                "n_layers": n_layers,
                "loadable": loadable,
            }
        )

    _logger.info("阶段 7 完成: 成功导出 %d 个 GDS 文件", len(results))
    return {"circuits": results}
