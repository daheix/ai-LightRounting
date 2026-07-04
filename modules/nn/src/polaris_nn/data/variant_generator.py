"""PoLaRIS 变体数据集生成器（DR 设计 + Curriculum Learning）。

基于基准电路生成规模变体（Curriculum Learning）和参数扫描变体（Domain Randomization），
用于训练具备规模泛化能力和参数鲁棒性的 RL 布局布线智能体。

设计方法:
1. **规模变体**: 基于 Curriculum Learning 思想，按器件数分阶段生成
   小/中/大/超大四个级别的电路，支持从小规模到大规模的渐进训练。
2. **参数扫描变体**: 基于 Domain Randomization 思想，对器件物理参数
   （radius/gap/length 等）进行扫描，提升策略对参数变化的鲁棒性。
3. **参数化 PDK 工厂**: 根据器件类型和参数动态生成 DeviceSpec。

来源:
- Bengio et al., "Curriculum Learning", ICML 2009
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- OpenAI, "Solving Rubik's Cube with a Robot Hand" (ADR), 2019
  https://ar5iv.labs.arxiv.org/html/1910.07113
- CircuitNet 3.0, ICLR 2026 https://github.com/sklp-eda-lab/iclr-circuitnet_3.0/
- LiDAR 2.0, 2025 https://arxiv.org/pdf/2505.17239v1.pdf
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path

from polaris_nn.data.dataset_generator import generate_layout
from polaris_nn.data.specs import CircuitSpec, DeviceSpec
from polaris_nn.data.standard_devices import STANDARD_DEVICES

logger = logging.getLogger(__name__)


# =============================================================================
# 课程学习级别定义（Bengio 2009）
# =============================================================================


@dataclass
class CurriculumLevel:
    """课程学习级别（Bengio et al., ICML 2009）。

    按器件数分阶段，从小规模到大规模渐进训练。

    Attributes:
        name: 级别名称。
        n_devices_min: 器件数下限。
        n_devices_max: 器件数上限。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
    """

    name: str
    n_devices_min: int
    n_devices_max: int
    canvas_w: float
    canvas_h: float


@dataclass
class VariantConfig:
    """变体数据集生成配置（用于训练流水线集成）。

    Attributes:
        enabled: 是否启用变体生成。
        output_dir: 变体输出目录。
        n_per_level: 每个课程级别的规模变体数。
        n_sweeps: 每个基准电路的参数扫描变体数。
        seed: 随机种子。
    """

    enabled: bool = False
    output_dir: str = "data/variants"
    n_per_level: int = 10
    n_sweeps: int = 10
    seed: int = 42


# 四级课程：小→中→大→超大
# 来源: Bengio 2009 Curriculum Learning + DeepPR 2021 渐进训练思想
CURRICULUM_LEVELS: list[CurriculumLevel] = [
    CurriculumLevel("small", 5, 10, 500.0, 500.0),
    CurriculumLevel("medium", 20, 50, 1000.0, 1000.0),
    CurriculumLevel("large", 80, 120, 2000.0, 2000.0),
    CurriculumLevel("xlarge", 150, 200, 3000.0, 3000.0),
    CurriculumLevel("huge", 500, 1000, 5000.0, 5000.0),
]


# =============================================================================
# 参数化 PDK 工厂函数（Domain Randomization 基础）
# =============================================================================


# 器件参数扫描范围（来源: SiEPIC EBeam PDK 典型值）
# 来源: SiEPIC_EBeam_PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
PARAM_SWEEP_RANGES: dict[str, dict[str, list[float]]] = {
    "ring_single": {"radius": [5.0, 10.0, 15.0, 20.0]},
    "ring_double": {"radius": [5.0, 10.0, 15.0, 20.0]},
    "dc": {"gap": [0.1, 0.2, 0.3, 0.5], "length": [5.0, 10.0, 15.0, 20.0]},
    "heater": {"length": [50.0, 80.0, 100.0, 150.0]},
    "wg_100": {"length": [50.0, 100.0, 200.0, 500.0]},
    "wg_200": {"length": [100.0, 200.0, 400.0, 800.0]},
    "mzi": {"delta_length": [5.0, 10.0, 20.0, 50.0]},
}


def make_device_with_params(
    device_key: str,
    name: str,
    param_overrides: dict | None = None,
) -> DeviceSpec:
    """参数化 PDK 工厂函数。

    根据器件类型和参数覆盖生成 DeviceSpec，支持 Domain Randomization。

    Args:
        device_key: STANDARD_DEVICES 中的器件键名。
        name: 新器件名称。
        param_overrides: 参数覆盖字典（如 {"radius": 15.0}）。

    Returns:
        新的 DeviceSpec，params 按 param_overrides 更新。

    Raises:
        KeyError: device_key 不在 STANDARD_DEVICES 中。
    """
    if device_key not in STANDARD_DEVICES:
        raise KeyError(f"未知器件类型: {device_key}")
    base = STANDARD_DEVICES[device_key]
    new_params = dict(base.params)
    if param_overrides:
        new_params.update(param_overrides)
    return DeviceSpec(
        name=name,
        device_type=base.device_type,
        width_um=base.width_um,
        height_um=base.height_um,
        ports=list(base.ports),
        params=new_params,
    )


# =============================================================================
# 规模变体生成（Curriculum Learning）
# =============================================================================


def _scale_mzi_lattice(stages: int, name: str = "mzi_lattice") -> CircuitSpec:
    """生成指定级数的 MZI 格型滤波器。

    结构: gc → (dc → wg → dc)*stages → gc

    Args:
        stages: 级数（决定器件数 = 2*stages + 2）。
        name: 电路名称。

    Returns:
        CircuitSpec。
    """
    devs: list[DeviceSpec] = [make_device_with_params("gc", "gc_in")]
    conns: list[tuple[str, str, str, str]] = []
    prev_name, prev_port = "gc_in", "o1"
    for i in range(stages):
        dc_name, wg_name = f"dc_{i}", f"wg_{i}"
        devs.append(make_device_with_params("dc", dc_name))
        devs.append(make_device_with_params("wg_100", wg_name))
        conns.append((prev_name, prev_port, dc_name, "o1"))
        conns.append((dc_name, "o3", wg_name, "o1"))
        prev_name, prev_port = wg_name, "o2"
    devs.append(make_device_with_params("gc", "gc_out"))
    conns.append((prev_name, prev_port, "gc_out", "o1"))
    return CircuitSpec(name=name, devices=devs, connections=conns)


def _scale_splitter_tree(levels: int, name: str = "splitter_tree") -> CircuitSpec:
    """生成指定层数的分束器树。

    结构: gc → mmi1x2 → (mmi1x2, mmi1x2) → ...
    器件数 = 2^levels - 1 个 mmi + 2^levels 个输出 gc + 1 个输入 gc

    Args:
        levels: 树的层数。
        name: 电路名称。

    Returns:
        CircuitSpec。
    """
    devs: list[DeviceSpec] = [make_device_with_params("gc", "gc_in")]
    conns: list[tuple[str, str, str, str]] = []
    n_splitters = 2**levels - 1
    for i in range(n_splitters):
        devs.append(make_device_with_params("mmi1x2", f"mmi_{i}"))
    conns.append(("gc_in", "o1", "mmi_0", "o1"))
    for i in range(n_splitters):
        left, right = 2 * i + 1, 2 * i + 2
        if left < n_splitters:
            conns.append((f"mmi_{i}", "o2", f"mmi_{left}", "o1"))
        if right < n_splitters:
            conns.append((f"mmi_{i}", "o3", f"mmi_{right}", "o1"))
    for i in range(n_splitters):
        left, right = 2 * i + 1, 2 * i + 2
        if left >= n_splitters:
            gc_name = f"gc_out_{i}_l"
            devs.append(make_device_with_params("gc", gc_name))
            conns.append((f"mmi_{i}", "o2", gc_name, "o1"))
        if right >= n_splitters:
            gc_name = f"gc_out_{i}_r"
            devs.append(make_device_with_params("gc", gc_name))
            conns.append((f"mmi_{i}", "o3", gc_name, "o1"))
    return CircuitSpec(name=name, devices=devs, connections=conns)


def _scale_switch_chain(n_stages: int, name: str = "switch_chain") -> CircuitSpec:
    """生成指定级数的光开关链。

    结构: gc → (mzi)*n_stages → gc

    Args:
        n_stages: MZI 级数。
        name: 电路名称。

    Returns:
        CircuitSpec。
    """
    devs: list[DeviceSpec] = [make_device_with_params("gc", "gc_in")]
    conns: list[tuple[str, str, str, str]] = []
    prev_name, prev_port = "gc_in", "o1"
    for i in range(n_stages):
        mzi_name = f"mzi_{i}"
        devs.append(make_device_with_params("mzi", mzi_name))
        conns.append((prev_name, prev_port, mzi_name, "o1"))
        prev_name, prev_port = mzi_name, "o2"
    devs.append(make_device_with_params("gc", "gc_out"))
    conns.append((prev_name, prev_port, "gc_out", "o1"))
    return CircuitSpec(name=name, devices=devs, connections=conns)


def _scale_random_circuit(
    n_devices: int,
    seed: int = 42,
    name: str = "random",
) -> CircuitSpec:
    """生成指定器件数的随机光子电路。

    支持大规模电路（100/200 器件），用于 Curriculum Learning 的 large/xlarge 级别。
    连接策略：链式连接 + 随机分支，保证连通性。

    Args:
        n_devices: 器件数量。
        seed: 随机种子。
        name: 电路名称。

    Returns:
        CircuitSpec。
    """
    rng = random.Random(seed)
    # 大规模电路偏向使用基础器件（gc/y_branch/mmi/wg），避免过多复杂器件
    if n_devices <= 50:
        device_keys = list(STANDARD_DEVICES.keys())
    else:
        device_keys = ["gc", "y_branch", "mmi1x2", "wg_100", "dc", "heater", "ring_single"]
    devs: list[DeviceSpec] = []
    for i in range(n_devices):
        dt = rng.choice(device_keys)
        devs.append(make_device_with_params(dt, f"{dt}_{i}"))
    # 链式连接保证连通性 + 随机分支增加复杂度
    conns: list[tuple[str, str, str, str]] = []
    for i in range(1, len(devs)):
        d, prev = devs[i], devs[i - 1]
        if d.ports and prev.ports:
            conns.append((prev.name, prev.ports[-1][0], d.name, d.ports[0][0]))
    # 随机额外连接（增加拓扑复杂度，模拟真实电路的多端口连接）
    n_extra = max(0, n_devices // 10)
    for _ in range(n_extra):
        i = rng.randint(0, len(devs) - 2)
        j = rng.randint(i + 1, len(devs) - 1)
        di, dj = devs[i], devs[j]
        if len(di.ports) >= 2 and len(dj.ports) >= 2:
            conns.append((di.name, di.ports[1][0], dj.name, dj.ports[1][0]))
    return CircuitSpec(name=name, devices=devs, connections=conns)


def _build_scale_circuit(level: CurriculumLevel, seed: int) -> CircuitSpec:
    """根据课程级别构建规模变体电路。

    Args:
        level: 课程级别。
        seed: 随机种子。

    Returns:
        CircuitSpec。
    """
    rng = random.Random(seed)
    n_devices = rng.randint(level.n_devices_min, level.n_devices_max)
    # 按比例选择模板电路
    if n_devices <= 10:
        template = rng.choice(["mzi_lattice", "switch_chain", "random"])
        if template == "mzi_lattice":
            stages = max(1, n_devices // 2)
            circuit = _scale_mzi_lattice(stages)
        elif template == "switch_chain":
            circuit = _scale_switch_chain(max(1, n_devices - 2))
        else:
            circuit = _scale_random_circuit(n_devices, seed)
    else:
        circuit = _scale_random_circuit(n_devices, seed)
    circuit.name = f"{level.name}_{circuit.name}_s{seed}"
    circuit.canvas_w = level.canvas_w
    circuit.canvas_h = level.canvas_h
    return circuit


def generate_scale_variants(
    output_dir: str | Path,
    n_per_level: int = 10,
    levels: list[CurriculumLevel] | None = None,
) -> dict:
    """生成规模变体数据集（Curriculum Learning）。

    按课程级别生成不同规模的电路变体，每个级别生成 n_per_level 个变体。

    Args:
        output_dir: 输出目录。
        n_per_level: 每个级别的变体数。
        levels: 课程级别列表（None 用默认 CURRICULUM_LEVELS）。

    Returns:
        生成统计 {"total_circuits": N, "total_variants": M, "levels": [...]}。
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    levels = levels or CURRICULUM_LEVELS
    total = 0
    level_stats: list[dict] = []
    for level in levels:
        n_gen = _generate_level_variants(out, level, n_per_level)
        total += n_gen
        level_stats.append(_make_level_stats(level, n_per_level))
        logger.info(
            "课程级别 %s: %d 变体 (器件 %d-%d)",
            level.name,
            n_per_level,
            level.n_devices_min,
            level.n_devices_max,
        )
    stats = {
        "total_circuits": total,
        "total_variants": total,
        "levels": level_stats,
        "method": "Curriculum Learning (Bengio 2009)",
    }
    _save_stats(out, stats)
    return stats


def _make_level_stats(level: CurriculumLevel, n_per_level: int) -> dict:
    """构建单个课程级别的统计字典。"""
    return {
        "level": level.name,
        "n_devices_range": [level.n_devices_min, level.n_devices_max],
        "n_variants": n_per_level,
    }


def _generate_level_variants(
    out: Path,
    level: CurriculumLevel,
    n_per_level: int,
) -> int:
    """为单个课程级别生成变体，返回生成数量。"""
    level_dir = out / level.name
    level_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for seed in range(n_per_level):
        circuit = _build_scale_circuit(level, seed)
        layout = generate_layout(circuit, seed=seed)
        var_data = _build_variant_data(circuit, layout, level.name, seed)
        var_path = level_dir / f"{circuit.name}.json"
        var_path.write_text(
            json.dumps(var_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        count += 1
    return count


# =============================================================================
# 参数扫描变体生成（Domain Randomization）
# =============================================================================


def _sweep_circuit_params(
    base_circuit: CircuitSpec,
    param_sweep: dict[str, dict[str, float]],
) -> CircuitSpec:
    """对电路中的器件参数进行扫描。

    Args:
        base_circuit: 基准电路。
        param_sweep: {device_name: {param_name: new_value}}。

    Returns:
        参数扫描后的新 CircuitSpec。
    """
    new_devs: list[DeviceSpec] = []
    for dev in base_circuit.devices:
        if dev.name in param_sweep:
            new_params = dict(dev.params)
            new_params.update(param_sweep[dev.name])
            new_devs.append(
                DeviceSpec(
                    name=dev.name,
                    device_type=dev.device_type,
                    width_um=dev.width_um,
                    height_um=dev.height_um,
                    ports=list(dev.ports),
                    params=new_params,
                )
            )
        else:
            new_devs.append(dev)
    return CircuitSpec(
        name=base_circuit.name + "_sweep",
        devices=new_devs,
        connections=list(base_circuit.connections),
        canvas_w=base_circuit.canvas_w,
        canvas_h=base_circuit.canvas_h,
    )


def _build_param_sweep_for_circuit(
    circuit: CircuitSpec,
    rng: random.Random,
) -> dict[str, dict[str, float]]:
    """为电路中的可扫描器件随机采样参数。

    Args:
        circuit: 基准电路。
        rng: 随机数生成器。

    Returns:
        {device_name: {param_name: sampled_value}}。
    """
    sweep: dict[str, dict[str, float]] = {}
    for dev in circuit.devices:
        # 通过 device_type 反查 STANDARD_DEVICES 键名
        dev_key = _find_device_key(dev)
        if dev_key is None or dev_key not in PARAM_SWEEP_RANGES:
            continue
        ranges = PARAM_SWEEP_RANGES[dev_key]
        sampled: dict[str, float] = {}
        for param_name, values in ranges.items():
            sampled[param_name] = rng.choice(values)
        sweep[dev.name] = sampled
    return sweep


def _find_device_key(dev: DeviceSpec) -> str | None:
    """根据 DeviceSpec 反查 STANDARD_DEVICES 键名。

    Args:
        dev: 器件规格。

    Returns:
        STANDARD_DEVICES 中的键名，未找到返回 None。
    """
    for key, std_dev in STANDARD_DEVICES.items():
        if std_dev.device_type == dev.device_type:
            return key
    # 合法：DeviceSpec 类型不在 STANDARD_DEVICES 字典中，调用方据此跳过
    # 该器件的参数扫描（generate_param_sweep_variants 检测 None 后 continue）。
    # 非 fall-back：未命中字典是合法查找结果，不伪造键名。
    return None


def generate_param_sweep_variants(
    output_dir: str | Path,
    base_circuits: list[CircuitSpec] | None = None,
    n_sweeps: int = 10,
    seed: int = 42,
) -> dict:
    """生成参数扫描变体数据集（Domain Randomization）。

    对基准电路的器件参数进行随机扫描，生成参数鲁棒的训练数据。

    Args:
        output_dir: 输出目录。
        base_circuits: 基准电路列表（None 用默认 MZI + ring + switch）。
        n_sweeps: 每个基准电路的参数扫描变体数。
        seed: 随机种子。

    Returns:
        生成统计 {"total_circuits": N, "total_variants": M}。
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if base_circuits is None:
        base_circuits = _default_base_circuits()
    rng = random.Random(seed)
    total_circuits = 0
    total_variants = 0
    for circuit in base_circuits:
        n_gen = _generate_sweeps_for_circuit(out, circuit, rng, n_sweeps, seed)
        total_circuits += n_gen
        total_variants += n_gen
    stats = {
        "total_circuits": total_circuits,
        "total_variants": total_variants,
        "n_base_circuits": len(base_circuits),
        "n_sweeps_per_circuit": n_sweeps,
        "method": "Domain Randomization (OpenAI ADR 2019)",
    }
    _save_stats(out, stats)
    return stats


def _default_base_circuits() -> list[CircuitSpec]:
    """默认基准电路列表。"""
    return [
        _scale_mzi_lattice(3, "mzi_lattice_3"),
        _scale_switch_chain(3, "switch_3"),
        _scale_random_circuit(15, seed=0, name="random_15"),
    ]


def _generate_sweeps_for_circuit(
    out: Path,
    circuit: CircuitSpec,
    rng: random.Random,
    n_sweeps: int,
    seed: int,
) -> int:
    """为单个基准电路生成参数扫描变体，返回生成数量。"""
    count = 0
    for i in range(n_sweeps):
        param_sweep = _build_param_sweep_for_circuit(circuit, rng)
        swept = _sweep_circuit_params(circuit, param_sweep)
        swept.name = f"{circuit.name}_sweep{i}"
        layout = generate_layout(swept, seed=seed + i)
        var_data = _build_variant_data(swept, layout, "param_sweep", i)
        var_data["param_sweep"] = param_sweep
        var_path = out / f"{swept.name}.json"
        var_path.write_text(
            json.dumps(var_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        count += 1
    return count


# =============================================================================
# 辅助函数
# =============================================================================


def _build_variant_data(
    circuit: CircuitSpec,
    layout: dict,
    category: str,
    variant_id: int,
) -> dict:
    """构建变体数据字典。

    Args:
        circuit: 电路规格。
        layout: 布局字典。
        category: 变体类别（如 "small"/"param_sweep"）。
        variant_id: 变体编号。

    Returns:
        变体数据字典。
    """
    return {
        "circuit_name": circuit.name,
        "category": category,
        "variant_id": variant_id,
        "canvas_w": circuit.canvas_w,
        "canvas_h": circuit.canvas_h,
        "n_devices": len(circuit.devices),
        "devices": [
            {
                "name": d.name,
                "type": d.device_type,
                "width_um": d.width_um,
                "height_um": d.height_um,
                "ports": d.ports,
                "params": d.params,
                "placement": layout.get(d.name, {}),
            }
            for d in circuit.devices
        ],
        "connections": circuit.connections,
    }


def _save_stats(out: Path, stats: dict) -> None:
    """保存数据集统计信息。"""
    stats_path = out / "variant_stats.json"
    stats_path.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(
        "变体数据集生成完成: %d 电路, %d 变体 → %s",
        stats["total_circuits"],
        stats["total_variants"],
        out,
    )


__all__ = [
    "CURRICULUM_LEVELS",
    "CurriculumLevel",
    "PARAM_SWEEP_RANGES",
    "VariantConfig",
    "generate_param_sweep_variants",
    "generate_scale_variants",
    "make_device_with_params",
]
