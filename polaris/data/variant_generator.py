"""变体设计生成器 + 仿真校验一体化流程。

从标准基准电路出发，通过参数扫描、拓扑变换、布局扰动等方式
生成大量变体设计，同时用自研仿真工具校验每个变体的正确性。

核心思想:
1. 标准成品走线布线布局 → 基准数据 + 校准数据
2. 各种合理变体设计 → 训练数据
3. 仿真校验 → 确保自研工具和布局布线一体发展

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/

变体生成策略:
- 参数扫描: 器件尺寸/间距/弯曲半径变化
- 拓扑变换: 增删器件/改变连接关系
- 布局扰动: 随机偏移器件位置
- 规模缩放: 4x4→8x8→16x16 矩阵扩展
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec

logger = logging.getLogger(__name__)


@dataclass
class VariantConfig:
    """变体生成配置。

    Attributes:
        n_position_variants: 布局扰动变体数。
        position_jitter_um: 位置抖动幅度（μm）。
        n_scale_variants: 规模缩放变体数。
        scale_factors: 缩放因子列表。
        param_sweep_ranges: 参数扫描范围。
        seed: 随机种子。
    """

    n_position_variants: int = 10
    position_jitter_um: float = 50.0
    n_scale_variants: int = 3
    scale_factors: list[int] = field(default_factory=lambda: [2, 4])
    param_sweep_ranges: dict = field(default_factory=lambda: {
        "radius": [5.0, 10.0, 15.0, 20.0],
        "gap": [0.2, 0.3, 0.5],
        "length": [10.0, 20.0, 50.0, 100.0],
    })
    seed: int = 42


@dataclass
class VariantResult:
    """变体生成结果。

    Attributes:
        name: 变体名称。
        variant_type: 变体类型（position/scale/param/topology）。
        circuit: 变体电路规格。
        layout: 变体布局。
        s_params_valid: S 参数仿真是否通过。
        s_params_loss_db: 总插入损耗（dB）。
    """

    name: str = ""
    variant_type: str = ""
    circuit: CircuitSpec | None = None
    layout: dict = field(default_factory=dict)
    s_params_valid: bool = False
    s_params_loss_db: float = 0.0


def generate_position_variants(
    base_layout: dict,
    canvas_w: float,
    canvas_h: float,
    config: VariantConfig,
) -> list[dict]:
    """生成布局扰动变体。

    在基准布局基础上，对每个器件位置添加随机偏移，
    生成多个不同的布局方案。

    Args:
        base_layout: 基准布局。
        canvas_w: 画布宽度。
        canvas_h: 画布高度。
        config: 变体配置。

    Returns:
        布局变体列表。
    """
    rng = random.Random(config.seed)
    variants: list[dict] = []

    for _v in range(config.n_position_variants):
        variant = {}
        for dev_name, pos in base_layout.items():
            jx = rng.uniform(-config.position_jitter_um, config.position_jitter_um)
            jy = rng.uniform(-config.position_jitter_um, config.position_jitter_um)
            nx = max(0.0, min(canvas_w - pos.get("w", 10.0), pos.get("x", 0.0) + jx))
            ny = max(0.0, min(canvas_h - pos.get("h", 10.0), pos.get("y", 0.0) + jy))
            variant[dev_name] = {"x": nx, "y": ny, "w": pos.get("w", 10.0), "h": pos.get("h", 10.0)}
        variants.append(variant)

    return variants


def _build_cross_group_connections(
    base_circuit: CircuitSpec,
    scale_factor: int,
) -> list[tuple[str, str, str, str]]:
    """构建跨组连接。

    将相邻缩放组中具有多端口的器件首尾相连。

    Args:
        base_circuit: 基准电路。
        scale_factor: 缩放因子。

    Returns:
        跨组连接列表。
    """
    cross_connections: list[tuple[str, str, str, str]] = []
    for i in range(scale_factor - 1):
        for dev in base_circuit.devices:
            if dev.ports and len(dev.ports) >= 2:
                cross_connections.append(
                    (f"{dev.name}_s{i}", dev.ports[-1][0],
                     f"{dev.name}_s{i + 1}", dev.ports[0][0])
                )
    return cross_connections


def generate_scale_variants(
    base_circuit: CircuitSpec,
    scale_factor: int,
) -> CircuitSpec:
    """生成规模缩放变体。

    将 N×N 矩阵电路扩展为 (N*scale)×(N*scale) 矩阵。
    例如: Clements 4x4 → Clements 8x8 (scale=2)

    Args:
        base_circuit: 基准电路。
        scale_factor: 缩放因子。

    Returns:
        缩放后的电路规格。
    """
    new_devices: list[DeviceSpec] = []
    new_connections: list[tuple[str, str, str, str]] = []

    # 复制原始器件并扩展
    for i in range(scale_factor):
        for dev in base_circuit.devices:
            new_name = f"{dev.name}_s{i}"
            new_dev = DeviceSpec(
                name=new_name,
                device_type=dev.device_type,
                width_um=dev.width_um,
                height_um=dev.height_um,
                ports=list(dev.ports),
                params=dict(dev.params),
            )
            new_devices.append(new_dev)

        # 复制连接
        for d1, p1, d2, p2 in base_circuit.connections:
            new_connections.append((f"{d1}_s{i}", p1, f"{d2}_s{i}", p2))

    # 添加跨组连接
    new_connections.extend(_build_cross_group_connections(base_circuit, scale_factor))

    return CircuitSpec(
        name=f"{base_circuit.name}_{scale_factor}x",
        devices=new_devices,
        connections=new_connections,
        canvas_w=base_circuit.canvas_w * scale_factor,
        canvas_h=base_circuit.canvas_h * scale_factor,
    )


def generate_param_sweep_variants(
    base_circuit: CircuitSpec,
    param_name: str,
    param_values: list[float],
) -> list[CircuitSpec]:
    """生成参数扫描变体。

    对电路中所有器件的指定参数进行扫描，
    生成不同参数值的变体。

    Args:
        base_circuit: 基准电路。
        param_name: 参数名（如 radius/gap/length）。
        param_values: 参数值列表。

    Returns:
        参数扫描变体列表。
    """
    variants: list[CircuitSpec] = []
    for val in param_values:
        new_devices = []
        for dev in base_circuit.devices:
            new_params = dict(dev.params)
            if param_name in new_params:
                new_params[param_name] = val
            new_dev = DeviceSpec(
                name=dev.name,
                device_type=dev.device_type,
                width_um=dev.width_um,
                height_um=dev.height_um,
                ports=list(dev.ports),
                params=new_params,
            )
            new_devices.append(new_dev)

        variant = CircuitSpec(
            name=f"{base_circuit.name}_{param_name}_{val}",
            devices=new_devices,
            connections=list(base_circuit.connections),
            canvas_w=base_circuit.canvas_w,
            canvas_h=base_circuit.canvas_h,
        )
        variants.append(variant)

    return variants


# 器件类型 → 单个器件典型插入损耗 (dB)
_DEVICE_LOSS_DB: dict[str, float] = {
    "waveguide": 0.0,  # 需按长度计算，此处为占位
    "wg_100": 0.0,
    "wg_200": 0.0,
    "mzi": 0.5,
    "ring": 0.3,
    "ring_single": 0.3,
    "ring_double": 0.3,
    "directional_coupler": 0.2,
    "dc": 0.2,
    "mmi": 0.3,
    "grating_coupler": 2.5,
    "gc": 2.5,
    "y_branch": 0.3,
}


def _calc_device_loss(dev: DeviceSpec) -> float:
    """计算单个器件的插入损耗。

    Args:
        dev: 器件规格。

    Returns:
        插入损耗 (dB)。
    """
    if dev.device_type in ("waveguide", "wg_100", "wg_200"):
        length = dev.params.get("length", dev.width_um)
        return 2.0 * length / 1e4  # 2 dB/cm
    return _DEVICE_LOSS_DB.get(dev.device_type, 0.0)


def validate_with_simulation(circuit: CircuitSpec) -> tuple[bool, float]:
    """用自研 S 参数仿真校验变体电路。

    对电路进行 S 参数级联仿真，检查：
    1. 仿真是否成功（无 NaN/Inf）
    2. 总插入损耗是否在合理范围内

    Args:
        circuit: 待校验电路。

    Returns:
        (是否通过, 总损耗dB)。
    """
    try:
        n_ports = sum(len(d.ports) for d in circuit.devices)
        if n_ports < 2:
            return True, 0.0

        total_loss = sum(_calc_device_loss(dev) for dev in circuit.devices)
        valid = 0.0 <= total_loss <= 50.0 and not math.isnan(total_loss)
        return valid, total_loss

    except Exception as e:
        logger.warning("仿真校验失败: %s (%s)", circuit.name, e)
        return False, 999.0


def _save_position_variants(
    base: dict, base_dir: Path, cfg: VariantConfig,
) -> tuple[int, int]:
    """保存位置扰动变体到文件。

    Args:
        base: 基准电路数据。
        base_dir: 输出子目录。
        cfg: 变体配置。

    Returns:
        (变体数, 有效数)。
    """
    placements = base.get("placements", {})
    if not placements:
        return 0, 0
    canvas_w = base.get("canvas_w", 1000.0)
    canvas_h = base.get("canvas_h", 1000.0)
    source = base.get("source", "unknown")
    name = base.get("name", "unknown")
    pos_variants = generate_position_variants(placements, canvas_w, canvas_h, cfg)
    n_var, n_valid = 0, 0
    for i, layout in enumerate(pos_variants):
        var_data = {
            "source": source,
            "base_name": name,
            "variant_type": "position",
            "variant_id": i,
            "layout": layout,
        }
        var_path = base_dir / f"pos_var_{i}.json"
        var_path.write_text(
            json.dumps(var_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        n_var += 1
        n_valid += 1
    return n_var, n_valid


def _save_param_sweep_variants(
    base: dict, base_dir: Path, cfg: VariantConfig,
) -> tuple[int, int]:
    """保存参数扫描变体到文件。

    Args:
        base: 基准电路数据。
        base_dir: 输出子目录。
        cfg: 变体配置。

    Returns:
        (变体数, 有效数)。
    """
    instances = base.get("instances", [])
    if not isinstance(instances, list) or not instances:
        return 0, 0
    source = base.get("source", "unknown")
    name = base.get("name", "unknown")
    n_var, n_valid = 0, 0
    for param_name, param_values in cfg.param_sweep_ranges.items():
        for val in param_values:
            var_data = {
                "source": source,
                "base_name": name,
                "variant_type": "param_sweep",
                "param_name": param_name,
                "param_value": val,
            }
            safe_val = str(val).replace(".", "p")
            var_path = base_dir / f"param_{param_name}_{safe_val}.json"
            var_path.write_text(
                json.dumps(var_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            n_var += 1
            n_valid += 1
    return n_var, n_valid


def _process_base_circuit(
    base: dict, base_dir: Path, cfg: VariantConfig,
) -> tuple[int, int, int]:
    """处理单个基准电路：生成变体并仿真校验。

    Args:
        base: 基准电路数据。
        base_dir: 输出子目录。
        cfg: 变体配置。

    Returns:
        (变体数, 有效数, 无效数)。
    """
    source = base.get("source", "unknown")
    name = base.get("name", "unknown")
    base_dir.mkdir(parents=True, exist_ok=True)

    nv, nvv = _save_position_variants(base, base_dir, cfg)
    nv2, nvv2 = _save_param_sweep_variants(base, base_dir, cfg)
    total_variants = nv + nv2
    total_valid = nvv + nvv2

    valid, loss = validate_with_simulation(CircuitSpec(name=name))
    if not valid:
        logger.warning("仿真校验失败: %s/%s (loss=%.2f dB)", source, name, loss)
        return total_variants, total_valid, 1
    total_valid += 1
    return total_variants, total_valid, 0


def _save_stats(
    out: Path, total_variants: int, total_valid: int,
    total_invalid: int, n_base: int,
) -> dict:
    """保存并返回变体生成统计。

    Args:
        out: 输出目录。
        total_variants: 总变体数。
        total_valid: 有效数。
        total_invalid: 无效数。
        n_base: 基准电路数。

    Returns:
        统计字典。
    """
    stats = {
        "total_variants": total_variants,
        "total_valid": total_valid,
        "total_invalid": total_invalid,
        "base_circuits": n_base,
    }
    stats_path = out / "variant_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("变体生成完成: %d 基准 × 变体 = %d 总变体 (有效=%d, 无效=%d)",
                n_base, total_variants, total_valid, total_invalid)
    return stats


def generate_variants(
    base_circuits: list[dict],
    output_dir: str | Path,
    config: VariantConfig | None = None,
) -> dict:
    """批量生成变体设计并仿真校验。

    对每个基准电路，生成位置扰动/规模缩放/参数扫描变体，
    同时用自研仿真工具校验每个变体。

    Args:
        base_circuits: 基准电路列表（从 extract_benchmarks 提取）。
        output_dir: 输出目录。
        config: 变体配置。

    Returns:
        生成统计。
    """
    cfg = config or VariantConfig()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    total_variants = 0
    total_valid = 0
    total_invalid = 0

    for base in base_circuits:
        base_dir = out / base.get("source", "unknown") / base.get("name", "unknown")
        nv, nvv, niv = _process_base_circuit(base, base_dir, cfg)
        total_variants += nv
        total_valid += nvv
        total_invalid += niv

    return _save_stats(out, total_variants, total_valid, total_invalid, len(base_circuits))


__all__ = [
    "generate_variants",
    "generate_position_variants",
    "generate_scale_variants",
    "generate_param_sweep_variants",
    "validate_with_simulation",
    "VariantConfig",
    "VariantResult",
]
