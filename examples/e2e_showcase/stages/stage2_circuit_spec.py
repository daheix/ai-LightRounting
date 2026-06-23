"""阶段 2: 电路规格定义。

定义 3 个演示电路规格：MZI 干涉仪、Clements 4x4 光矩阵、量子玻色采样电路。

电路清单:
- MZI 干涉仪: 5 器件（1 光栅耦合器 + 1x2 MMI + 2 直波导臂 + 2x2 MMI）
- Clements 4x4: 6 分束器 + 4 相移器 = 10 器件
- 量子玻色采样: 4 模酉矩阵网络（不构造 CircuitSpec，量子电路无传统器件）

来源:
- Clements 矩阵: Clements et al., "Optimal design for universal multiport
  interferometers", Optica 2016, https://doi.org/10.1364/OPTICA.3.001460
- MZI 干涉仪: Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://www.cambridge.org/core/books/silicon-photonics-design/
- 玻色采样: Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.sim.quantum_photonics import clements_unitary

_logger = logging.getLogger("e2e_showcase")

# SOI 工艺节点（阶段 1 PDK 数据一致）
_PROCESS_NODE_SOI = "220nm SOI"


# =============================================================================
# 电路 1: MZI 干涉仪（5 器件）
# =============================================================================


def _build_mzi_circuit() -> CircuitSpec:
    """构建 MZI 干涉仪电路规格（5 器件）。

    器件清单:
        - gc1: 光栅耦合器（输入耦合）
        - mmi1: 1x2 MMI（分束）
        - wg1: 直波导臂 L=100μm
        - wg2: 直波导臂 L=120μm
        - mmi2: 2x2 MMI（合束）

    连接拓扑:
        gc1 → mmi1 → wg1/wg2 → mmi2

    来源:
        - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015

    Returns:
        MZI 干涉仪电路规格。
    """
    devices = [
        DeviceSpec(
            name="gc1",
            device_type="grating_coupler",
            width_um=20.0,
            height_um=20.0,
            ports=[
                ("in", 0.0, 10.0, "west"),
                ("out", 20.0, 10.0, "east"),
            ],
            params={
                "insertion_loss_db": 1.9,
                "wavelength_nm": 1550,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ),
        DeviceSpec(
            name="mmi1",
            device_type="mmi_1x2",
            width_um=20.0,
            height_um=5.0,
            ports=[
                ("in", 0.0, 2.5, "west"),
                ("out1", 20.0, 1.5, "east"),
                ("out2", 20.0, 3.5, "east"),
            ],
            params={
                "insertion_loss_db": 0.4,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ),
        DeviceSpec(
            name="wg1",
            device_type="strip_waveguide",
            width_um=100.0,
            height_um=0.5,
            ports=[
                ("in", 0.0, 0.25, "west"),
                ("out", 100.0, 0.25, "east"),
            ],
            params={
                "length_um": 100.0,
                "width_nm": 500,
                "loss_db_cm": 3.0,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ),
        DeviceSpec(
            name="wg2",
            device_type="strip_waveguide",
            width_um=120.0,
            height_um=0.5,
            ports=[
                ("in", 0.0, 0.25, "west"),
                ("out", 120.0, 0.25, "east"),
            ],
            params={
                "length_um": 120.0,
                "width_nm": 500,
                "loss_db_cm": 3.0,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ),
        DeviceSpec(
            name="mmi2",
            device_type="mmi_2x2",
            width_um=20.0,
            height_um=5.0,
            ports=[
                ("in1", 0.0, 1.5, "west"),
                ("in2", 0.0, 3.5, "west"),
                ("out1", 20.0, 1.5, "east"),
                ("out2", 20.0, 3.5, "east"),
            ],
            params={
                "insertion_loss_db": 0.5,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ),
    ]

    connections = [
        ("gc1", "out", "mmi1", "in"),
        ("mmi1", "out1", "wg1", "in"),
        ("mmi1", "out2", "wg2", "in"),
        ("wg1", "out", "mmi2", "in1"),
        ("wg2", "out", "mmi2", "in2"),
    ]

    return CircuitSpec(
        name="MZI 干涉仪",
        devices=devices,
        connections=connections,
        canvas_w=500.0,
        canvas_h=300.0,
        process_node=_PROCESS_NODE_SOI,
        optical_wavelength_nm=1550.0,
    )


# =============================================================================
# 电路 2: Clements 4x4 光矩阵（10 器件）
# =============================================================================


def _build_clements_circuit() -> CircuitSpec:
    """构建 Clements 4x4 光矩阵电路规格（10 器件）。

    器件清单:
        - bs1-bs6: 2x2 MMI 分束器（6 个）
        - ps1-ps4: 相移器（4 个）

    连接拓扑（Clements 矩形网格，4 模）:
        列 0: bs1(模 0,1), bs2(模 2,3)
        列 1: bs3(模 1,2)
        列 2: bs4(模 0,1), bs5(模 2,3)
        列 3: bs6(模 1,2)
        输出: ps1-ps4 分别作用于模 0-3

    来源:
        - Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460

    Returns:
        Clements 4x4 电路规格。
    """
    devices: list[DeviceSpec] = []

    # 6 个分束器（mmi_2x2），每个 4 端口
    for i in range(1, 7):
        devices.append(DeviceSpec(
            name=f"bs{i}",
            device_type="mmi_2x2",
            width_um=20.0,
            height_um=5.0,
            ports=[
                ("in1", 0.0, 1.5, "west"),
                ("in2", 0.0, 3.5, "west"),
                ("out1", 20.0, 1.5, "east"),
                ("out2", 20.0, 3.5, "east"),
            ],
            params={
                "insertion_loss_db": 0.5,
                "splitting_ratio": 0.5,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ))

    # 4 个相移器，每个 2 端口
    for i in range(1, 5):
        devices.append(DeviceSpec(
            name=f"ps{i}",
            device_type="phase_shifter",
            width_um=10.0,
            height_um=0.5,
            ports=[
                ("in", 0.0, 0.25, "west"),
                ("out", 10.0, 0.25, "east"),
            ],
            params={
                "vpi_v": 3.0,
                "loss_db": 0.1,
                "source": "SiEPIC EBeam PDK",
                "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            },
            process_node=_PROCESS_NODE_SOI,
        ))

    # Clements 4x4 矩形网格拓扑连接（4 模，6 分束器 + 4 相移器）
    # 信号流: 输入 → 列0(bs1,bs2) → 列1(bs3) → 列2(bs4,bs5) → 列3(bs6) → 输出相移器
    # 来源: Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460
    connections = [
        # 列 0 → 列 1: bs1.out2→bs3.in1（模 1）, bs2.out1→bs3.in2（模 2）
        ("bs1", "out2", "bs3", "in1"),
        ("bs2", "out1", "bs3", "in2"),
        # 列 0 → 列 2: bs1.out1→bs4.in1（模 0）, bs2.out2→bs5.in2（模 3）
        ("bs1", "out1", "bs4", "in1"),
        ("bs2", "out2", "bs5", "in2"),
        # 列 1 → 列 2: bs3.out1→bs4.in2（模 1）, bs3.out2→bs5.in1（模 2）
        ("bs3", "out1", "bs4", "in2"),
        ("bs3", "out2", "bs5", "in1"),
        # 列 2 → 列 3: bs4.out2→bs6.in1（模 1）, bs5.out1→bs6.in2（模 2）
        ("bs4", "out2", "bs6", "in1"),
        ("bs5", "out1", "bs6", "in2"),
        # 输出相移器: 模 0→ps1, 模 1→ps2, 模 2→ps3, 模 3→ps4
        ("bs4", "out1", "ps1", "in"),
        ("bs6", "out1", "ps2", "in"),
        ("bs6", "out2", "ps3", "in"),
        ("bs5", "out2", "ps4", "in"),
    ]

    return CircuitSpec(
        name="Clements 4x4 光矩阵",
        devices=devices,
        connections=connections,
        canvas_w=800.0,
        canvas_h=600.0,
        process_node=_PROCESS_NODE_SOI,
        optical_wavelength_nm=1550.0,
    )


# =============================================================================
# 电路 3: 量子玻色采样电路（4 模酉矩阵）
# =============================================================================


# 4 模 Clements 分解的 6 个分束器角度（θ）与相位（φ）
# 来源: Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460
# 这些是演示用的固定参数，生成可复现的 4x4 酉矩阵
_BOSON_SAMPLING_THETAS = np.array([
    math.pi / 8,  # bs1 角度
    math.pi / 6,  # bs2 角度
    math.pi / 4,  # bs3 角度
    math.pi / 3,  # bs4 角度
    math.pi / 8,  # bs5 角度
    math.pi / 6,  # bs6 角度
])

_BOSON_SAMPLING_PHIS = np.array([
    0.0,          # bs1 相位
    math.pi / 4,  # bs2 相位
    math.pi / 2,  # bs3 相位
    3 * math.pi / 4,  # bs4 相位
    math.pi,      # bs5 相位
    5 * math.pi / 4,  # bs6 相位
])


def _build_boson_sampling_unitary() -> np.ndarray:
    """构建量子玻色采样 4x4 酉矩阵。

    使用 Clements 分解生成 4 模酉矩阵，6 个分束器角度与相位为固定值
    （可复现），用于玻色采样演示。

    来源:
        - Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460
        - Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698

    Returns:
        4x4 复数酉矩阵。
    """
    U = clements_unitary(
        n_modes=4,
        thetas=_BOSON_SAMPLING_THETAS,
        phis=_BOSON_SAMPLING_PHIS,
    )
    # 验证酉性（规则 14.1: 无 fall-back，酉性失败必须 raise）
    identity = np.eye(4, dtype=complex)
    if not np.allclose(U @ U.conj().T, identity, atol=1e-6):
        raise ValueError(
            f"玻色采样酉矩阵不满足酉性: U@U† 偏离单位矩阵，"
            f"最大误差 {np.max(np.abs(U @ U.conj().T - identity)):.2e}"
        )
    return U


def _save_unitary_to_json(U: np.ndarray, output_dir: Path) -> Path:
    """将酉矩阵保存为 JSON 文件。

    Args:
        U: 4x4 复数酉矩阵。
        output_dir: 输出根目录，文件保存至 output_dir/reports/。

    Returns:
        保存的 JSON 文件路径。
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "boson_sampling_unitary.json"

    data = {
        "circuit_name": "量子玻色采样电路",
        "n_modes": 4,
        "thetas": _BOSON_SAMPLING_THETAS.tolist(),
        "phis": _BOSON_SAMPLING_PHIS.tolist(),
        "unitary_real": U.real.tolist(),
        "unitary_imag": U.imag.tolist(),
        "source": "Clements et al., Optica 2016",
        "source_url": "https://doi.org/10.1364/OPTICA.3.001460",
        "note": "4 模酉矩阵，由 Clements 分解生成，用于玻色采样演示",
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return json_path


# =============================================================================
# 主入口
# =============================================================================


def run(output_dir: Path) -> dict:
    """执行阶段 2: 电路规格定义。

    定义 3 个演示电路规格:
        1. MZI 干涉仪（5 器件，500×300 画布）
        2. Clements 4x4 光矩阵（10 器件，800×600 画布）
        3. 量子玻色采样电路（4x4 酉矩阵，无传统器件）

    Args:
        output_dir: 输出目录，酉矩阵 JSON 保存至 output_dir/reports/。

    Returns:
        结果字典，含以下字段:
        - circuits: 3 电路信息列表，每项含 name/n_devices/n_connections/canvas
        - unitary_matrix_shape: 酉矩阵形状 [4, 4]
    """
    _logger.info("阶段 2 开始: 定义 3 个演示电路规格")

    circuits: list[dict] = []

    # 电路 1: MZI 干涉仪
    mzi = _build_mzi_circuit()
    mzi_info = {
        "name": mzi.name,
        "n_devices": len(mzi.devices),
        "n_connections": len(mzi.connections),
        "canvas": {"w": mzi.canvas_w, "h": mzi.canvas_h},
    }
    circuits.append(mzi_info)
    _logger.info(
        "电路 1: %s — %d 器件, %d 连接, 画布 %.0f×%.0f",
        mzi.name,
        len(mzi.devices),
        len(mzi.connections),
        mzi.canvas_w,
        mzi.canvas_h,
    )
    _logger.info("  器件: %s", [d.name for d in mzi.devices])
    _logger.info("  连接: %s", mzi.connections)

    # 电路 2: Clements 4x4 光矩阵
    clements = _build_clements_circuit()
    clements_info = {
        "name": clements.name,
        "n_devices": len(clements.devices),
        "n_connections": len(clements.connections),
        "canvas": {"w": clements.canvas_w, "h": clements.canvas_h},
    }
    circuits.append(clements_info)
    _logger.info(
        "电路 2: %s — %d 器件, %d 连接, 画布 %.0f×%.0f",
        clements.name,
        len(clements.devices),
        len(clements.connections),
        clements.canvas_w,
        clements.canvas_h,
    )
    _logger.info("  器件: %s", [d.name for d in clements.devices])

    # 电路 3: 量子玻色采样电路（4x4 酉矩阵）
    U = _build_boson_sampling_unitary()
    json_path = _save_unitary_to_json(U, output_dir)
    boson_info = {
        "name": "量子玻色采样电路",
        "n_devices": 0,
        "n_connections": 0,
        "canvas": {"w": 0.0, "h": 0.0},
        "note": "4 模酉矩阵描述，不构造 CircuitSpec（量子电路无传统器件）",
        "unitary_file": str(json_path),
    }
    circuits.append(boson_info)
    _logger.info(
        "电路 3: %s — 4x4 酉矩阵, 已保存至 %s",
        boson_info["name"],
        json_path,
    )
    _logger.info("  酉矩阵形状: %s", list(U.shape))

    return {
        "circuits": circuits,
        "unitary_matrix_shape": list(U.shape),
    }
