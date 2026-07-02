"""阶段 6: DRC/LVS 验证。

对 MZI 电路执行 DRC（设计规则检查）与 LVS（版图与原理图一致性比对），
输出违规清单、DRC 通过率、一致性布尔结果与差异清单。

PoLaRIS v5.0 迁移说明:
    旧 v4 直接操作 KLayout（生成 GDS → 跑 DRC runset → 比对网表）。
    v5.0 已将 DRC / LVS 能力封装为 polaris-drc / polaris-lvs 两个子模块的
    稳定 API:
      - ``polaris_drc.run_drc(circuit_dict, placements) -> dict``
      - ``polaris_lvs.run_lvs(circuit_dict, netlist=None) -> dict``
    两个 API 均接收 polaris-core 风格的 JSON-serializable circuit dict，
    无需生成 GDS 文件、无需 KLayout 依赖。本 stage 改用 place_circuit +
    run_drc + run_lvs 三步调用。

DRC 规则来源:
- SiEPIC EBeam PDK DRC runset
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC 文档
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  https://doi.org/10.1109/DAC56929.2023.10247734
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  https://doi.org/10.1007/978-3-540-77974-2

LVS 来源:
- KLayout LVS API
  https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK DEVREC 标准
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory PDK 文档（网表提取）
  https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS（光子电路网表验证）
  https://www.lucedaphotonics.com/en/products/ipkiss
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from polaris_core import CircuitSpec, DeviceSpec, circuit_to_dict
from polaris_place import place_circuit
from polaris_drc import run_drc
from polaris_lvs import run_lvs

_logger = logging.getLogger("e2e_showcase")


def _mzi_circuit() -> CircuitSpec:
    """构建 MZI 电路规格（含端口，供 DRC/LVS 检查使用）。

    器件清单:
        - gc1: 光栅耦合器 (10×10μm)
        - mmi1: MMI 1x2 分束器 (20×10μm)
        - wg1: 条形波导臂 1 (100×0.5μm)
        - wg2: 条形波导臂 2 (120×0.5μm)
        - mmi2: MMI 2x2 合束器 (20×10μm)

    端口定义与 stage3/stage4 保持一致，确保 DRC 的 port_alignment /
    port_connectivity / port_facing 规则可正确评估。

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


def run(output_dir: Path) -> dict:
    """执行阶段 6: DRC/LVS 验证。

    流程:
    1. 构建 MZI 电路规格（含端口定义）
    2. circuit_to_dict 转为 polaris-core 风格 circuit dict
    3. place_circuit 获取布局（解析法），供 DRC 检查使用
    4. run_drc 执行 12 条 SiEPIC EBeam PDK DRC 规则
    5. run_lvs 执行 LVS 网表自比对（验证拓扑一致性）
    6. 保存 DRC/LVS 报告到 JSON

    Args:
        output_dir: 输出目录（含 reports/ 子目录）。

    Returns:
        含 drc / lvs 两个子 dict 的结果。

    Raises:
        RuntimeError: 布局 / DRC / LVS 任一步失败（R03 禁止 fall-back）。
    """
    _logger.info("阶段 6 开始: DRC/LVS 验证（polaris-drc + polaris-lvs）")

    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. 构建 MZI 电路并转为 circuit dict
    circuit = _mzi_circuit()
    circuit_dict = circuit_to_dict(circuit)

    # 2. 布局（解析法），获取 placements 供 DRC 使用
    placement_result = place_circuit(circuit_dict, mode="analytical")
    placements = placement_result["placements"]
    _logger.info(
        "MZI 布局完成: hpwl=%.2f μm, 模式=%s",
        placement_result["hpwl"],
        placement_result["placement_mode"],
    )

    # 3. DRC 检查（12 条 SiEPIC EBeam PDK 规则）
    # 来源: polaris-drc 子模块，AABB 几何算法（Ericson §5.1.3）
    drc_result = run_drc(circuit_dict, placements)
    _logger.info(
        "DRC 结果: %d 项规则, %d 项通过, %d 项违规, 通过率 %.1f%%",
        drc_result["n_rules"],
        drc_result["n_passed"],
        drc_result["n_violations"],
        drc_result["pass_rate"] * 100,
    )

    # 4. LVS 网表自比对（netlist=None 时用 circuit 自身派生网表）
    # 来源: polaris-lvs 子模块，器件集合差集 + 连接集合差集比对
    lvs_result = run_lvs(circuit_dict, netlist=None)
    _logger.info(
        "LVS 结果: is_consistent=%s, n_mismatches=%d, 器件=%d, 连接=%d",
        lvs_result["is_consistent"],
        lvs_result["n_mismatches"],
        lvs_result["n_devices"],
        lvs_result["n_connections"],
    )

    # 5. 保存 DRC/LVS 报告到 JSON
    report_path = reports_dir / "drc_lvs_report.json"
    report_data = {
        "drc": drc_result,
        "lvs": lvs_result,
        "circuit_name": circuit.name,
        "placement_hpwl": placement_result["hpwl"],
        "placement_mode": placement_result["placement_mode"],
        "drc_source": "polaris-drc (SiEPIC EBeam PDK), "
                      "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "lvs_source": "polaris-lvs (KLayout LVS), "
                      "https://www.klayout.org/doc-qt5/manual/lvs.html",
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    _logger.info("DRC/LVS 报告已保存: %s", report_path)
    _logger.info("阶段 6 完成: DRC/LVS 验证")

    return {
        "drc": drc_result,
        "lvs": lvs_result,
    }
