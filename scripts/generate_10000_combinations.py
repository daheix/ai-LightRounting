#!/usr/bin/env python3
"""PoLaRIS 10000 组合电路生成器（基于真实板子拓扑组合）。

基于 7 大拓扑组件（MZI/Ring/DC/MMI/Switch/Modulator/WDM）的组合扩展，
生成 10000 种测试电路，用于 PoLaRIS 布局布线引擎训练与评估。

组合策略（确保多样性）:
1. 二元组合 A+B（4000 个）: 7×7=49 有序对 × ~82 变种 = 4018
2. 三元组合 A+B+C（3000 个）: C(7,3)=35 无序三元 × ~86 变种 = 3010
3. 四元组合 A+B+C+D（1500 个）: C(7,4)=35 无序四元 × ~43 变种 = 1505
4. 规模扩展阵列化（1500 个）: 7 拓扑 × 4 阵列规模(N=2/4/8/16) × ~54 变种 = 1512
   总计 ≥ 10000

变种来源: 5 规模(XS/S/M/L/XL) × 4 平台(SOI/SiN/InP/LNOI) × 多种子

拓扑组件来源（真实板子数据，R02 学术诚信）:
- MZI: SiEPIC EBeam PDK MZI 阵列
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ring: SiEPIC RingResonator 环形谐振器
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- DC: SiEPIC 定向耦合器阵列（dc_array）
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- MMI: Soldano & Pennings JLT 1995 MMI 阵列
  URL: https://ieeexplore.ieee.org/document/412541
- Switch: Benes 1965 光开关矩阵; Spanke & Murphy JLT 1988
  URL: https://ieeexplore.ieee.org/document/1072908
- Modulator: SiEPIC MZM 调制器阵列; LNOI 电光调制器
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- WDM: Takada et al. 1984 AWG 复用/解复用器; SiEPIC AWG
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

参考文献（≥5 个，R02 学术诚信）:
- Clements et al., "Optimal design for universal multiport interferometers",
  Optica 3(12), 1460 (2016), https://doi.org/10.1364/OPTICA.3.001460
- Reck et al., "Experimental realization of any discrete unitary operator",
  Phys. Rev. Lett. 73, 58 (1994), https://doi.org/10.1103/PhysRevLett.73.58
- Spanke & Murphy, "Architecture for large nonblocking optical space switches",
  IEEE J. Quantum Electron. 22, 961 (1986), https://ieeexplore.ieee.org/document/1072908
- Soldano & Pennings, "Optical multi-mode interference devices based on
  self-imaging: principles and applications", JLT 13(4), 615 (1995),
  https://ieeexplore.ieee.org/document/412541
- Benes, "Mathematical Theory of Connecting Networks and Telephone Traffic",
  Academic Press (1965), ISBN 978-0120873504
- Takada et al., "Broadband signal-frequency-selection optical filter using
  arrayed waveguide grating", Electron. Lett. 20, 20 (1984)
- Madsen & Zhao, "Optical Filter Design and Analysis: A Signal Processing
  Approach", Wiley (1999), ISBN 978-0471183731
- SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory, https://gdsfactory.github.io/gdsfactory/
- PicBench, https://github.com/JeppeKlitgaard/PicBench
- LiDAR ISPD'25, https://arxiv.org/abs/2504.18813

规则依据:
- R03 禁止 fall-back: 生成失败即 raise，不静默兜底
- R02 学术诚信: 标注组件来源与文献
- R13 §3 代码清理: 只保留最新代码

用法:
    python scripts/generate_10000_combinations.py
    python scripts/generate_10000_combinations.py --target 100 --dry-run
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（支持直接运行 python scripts/xxx.py）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.generate_1000_circuits import (
    CircuitSerializer,
    MZIArrayGenerator,
    PLATFORMS,
    RingFilterGenerator,
    SCALES,
)
from scripts.generators.group_a import DCCouplerArrayGenerator, MMIArrayGenerator
from scripts.generators.group_b import (
    ModulatorArrayGenerator,
    OpticalSwitchMatrixGenerator,
    WDMMuxDemuxGenerator,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gen_10000")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "combinations"

# =============================================================================
# 7 大拓扑组件注册表（来源: 真实板子数据 + 公开 PDK）
# =============================================================================

TOPOLOGY_REGISTRY: dict[str, type] = {
    "MZI": MZIArrayGenerator,
    "Ring": RingFilterGenerator,
    "DC": DCCouplerArrayGenerator,
    "MMI": MMIArrayGenerator,
    "Switch": OpticalSwitchMatrixGenerator,
    "Modulator": ModulatorArrayGenerator,
    "WDM": WDMMuxDemuxGenerator,
}

TOPOLOGIES = list(TOPOLOGY_REGISTRY.keys())
SCALE_NAMES = list(SCALES.keys())
PLATFORM_NAMES = list(PLATFORMS.keys())

# 拓扑来源标注（R02 学术诚信）
TOPOLOGY_SOURCES: dict[str, str] = {
    "MZI": "SiEPIC EBeam PDK MZI 阵列, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    "Ring": "SiEPIC RingResonator, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    "DC": "SiEPic 定向耦合器阵列, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    "MMI": "Soldano & Pennings JLT 1995; SiEPIC MMI",
    "Switch": "Benes 1965; Spanke & Murphy JLT 1988",
    "Modulator": "SiEPIC MZM; LNOI 电光调制器",
    "WDM": "Takada et al. 1984; SiEPIC AWG",
}

# =============================================================================
# 组合目标
# =============================================================================

TARGET_BINARY = 4000
TARGET_TERNARY = 3000
TARGET_QUATERNARY = 1500
TARGET_ARRAY = 1500
TARGET_TOTAL = TARGET_BINARY + TARGET_TERNARY + TARGET_QUATERNARY + TARGET_ARRAY

ARRAY_SIZES = [2, 4, 8, 16]


# =============================================================================
# 组件构建与组合
# =============================================================================


def _find_free_ports(circuit: dict) -> tuple[list, list]:
    """查找电路中未连接的输入端口(W)和输出端口(E)。

    用于组合时识别可桥接的端口：
    - free_ins: 西向(W)未连接端口，可接收上游信号
    - free_outs: 东向(E)未连接端口，可向下游输出

    Args:
        circuit: 电路字典。

    Returns:
        (free_ins, free_outs) — 各为 [(device_name, port_name), ...] 列表。
    """
    used_ports: set[tuple[str, str]] = set()
    for conn in circuit["connections"]:
        used_ports.add((conn[0], conn[1]))
        used_ports.add((conn[2], conn[3]))

    free_ins: list[tuple[str, str]] = []
    free_outs: list[tuple[str, str]] = []

    for dev in circuit["devices"]:
        for port in dev["ports"]:
            pname = port[0]
            direction = port[3]
            key = (dev["name"], pname)
            if key not in used_ports:
                if direction == "W":
                    free_ins.append(key)
                elif direction == "E":
                    free_outs.append(key)

    return free_ins, free_outs


def build_component(
    topology_name: str,
    scale_name: str,
    platform_name: str,
    seed: int,
    prefix: str,
) -> tuple[dict, list, list, dict]:
    """构建单个拓扑组件电路（带前缀重命名）。

    Args:
        topology_name: 拓扑名（MZI/Ring/DC/MMI/Switch/Modulator/WDM）。
        scale_name: 规模名（XS/S/M/L/XL）。
        platform_name: 平台名（SOI/SiN/InP/LNOI）。
        seed: 随机种子。
        prefix: 设备名前缀（如 "c0"）。

    Returns:
        (circuit, free_ins, free_outs, source_info) 元组。
    """
    gen_cls = TOPOLOGY_REGISTRY[topology_name]
    gen = gen_cls(
        scale=SCALES[scale_name],
        platform=PLATFORMS[platform_name],
        seed=seed,
    )
    circuit = gen.generate()

    # 前缀重命名所有设备名（避免组合时命名冲突）
    rename_map: dict[str, str] = {}
    for dev in circuit["devices"]:
        old_name = dev["name"]
        new_name = f"{prefix}_{old_name}"
        dev["name"] = new_name
        rename_map[old_name] = new_name

    # 更新连接中的设备引用
    new_connections: list[list] = []
    for conn in circuit["connections"]:
        new_connections.append([
            rename_map.get(conn[0], conn[0]), conn[1],
            rename_map.get(conn[2], conn[2]), conn[3],
        ])
    circuit["connections"] = new_connections

    # 查找自由端口（重命名后）
    free_ins, free_outs = _find_free_ports(circuit)

    source_info = {
        "topology": topology_name,
        "scale": scale_name,
        "platform": platform_name,
        "seed": seed,
        "source": TOPOLOGY_SOURCES[topology_name],
    }

    return circuit, free_ins, free_outs, source_info


def combine_circuits(
    components: list[tuple[dict, list, list, dict]],
    combo_type: str,
    combo_id: int,
    extra_metadata: dict | None = None,
) -> dict:
    """将多个组件电路组合为单一电路。

    组合方式：
    - 合并所有器件与连接
    - 添加桥接连接：组件 i 的东向自由端口 → 组件 i+1 的西向自由端口
    - 桥接数量 = min(|上游 free_outs|, |下游 free_ins|)，按顺序 1-to-1 配对
    - 若无匹配端口则组件保持独立（仍合法）

    Args:
        components: [(circuit, free_ins, free_outs, source_info), ...] 列表。
        combo_type: 组合类型（binary/ternary/quaternary/array）。
        combo_id: 组合编号。
        extra_metadata: 额外元数据。

    Returns:
        组合后的电路字典。
    """
    all_devices: list[dict] = []
    all_connections: list[list] = []
    component_sources: list[dict] = []
    canvas_w_max = 0.0
    canvas_h_max = 0.0

    for circuit, _, _, source_info in components:
        all_devices.extend(circuit["devices"])
        all_connections.extend(circuit["connections"])
        component_sources.append(source_info)
        canvas_w_max = max(canvas_w_max, circuit["canvas_w"])
        canvas_h_max = max(canvas_h_max, circuit["canvas_h"])

    # 添加组件间桥接连接
    bridge_connections: list[list] = []
    for i in range(len(components) - 1):
        upstream_outs = components[i][2]  # free_outs of component i
        downstream_ins = components[i + 1][1]  # free_ins of component i+1
        n_bridges = min(len(upstream_outs), len(downstream_ins))
        for j in range(n_bridges):
            bridge_connections.append([
                upstream_outs[j][0], upstream_outs[j][1],
                downstream_ins[j][0], downstream_ins[j][1],
            ])
    all_connections.extend(bridge_connections)

    # 构建组合电路
    topo_names = [s["topology"] for s in component_sources]
    name = f"combo_{combo_type}_{'-'.join(topo_names)}_{combo_id:05d}"

    combined_canvas_w = canvas_w_max * len(components)

    metadata = {
        "combination_type": combo_type,
        "n_components": len(components),
        "component_sources": component_sources,
        "n_bridges": len(bridge_connections),
        "n_total_devices": len(all_devices),
        "n_total_connections": len(all_connections),
        "seed": combo_id,
        "source": "PoLaRIS 组合电路生成器（基于真实板子拓扑组合）",
        "references": [
            "Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460",
            "Reck et al., PRL 1994, https://doi.org/10.1103/PhysRevLett.73.58",
            "Spanke & Murphy, JLT 1988",
            "Soldano & Pennings, JLT 1995",
            "SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        ],
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    combined = {
        "name": name,
        "description": f"组合电路 ({combo_type}): {' + '.join(topo_names)}",
        "platform": component_sources[0]["platform"],
        "topology": f"combination_{combo_type}",
        "scale": component_sources[0]["scale"],
        "canvas_w": combined_canvas_w,
        "canvas_h": canvas_h_max,
        "instances": {},
        "devices": all_devices,
        "connections": all_connections,
        "metadata": metadata,
    }
    return combined


# =============================================================================
# 组合生成器
# =============================================================================


def generate_category(
    target: int,
    topology_combos: list[tuple],
    combo_type: str,
    serializer: CircuitSerializer,
    index_entries: list[dict],
    output_dir: Path,
    start_id: int,
) -> tuple[int, int]:
    """为一个组合类别生成电路，直到达到目标数量。

    迭代 (scale, platform, combo) 循环，每轮生成一个组合电路。
    种子基于 cycle + combo_index + component_index 确定性生成。

    Args:
        target: 目标数量。
        topology_combos: 拓扑组合列表。
        combo_type: 组合类型。
        serializer: 电路序列化器。
        index_entries: 索引条目列表（就地追加）。
        output_dir: 输出目录。
        start_id: 起始编号。

    Returns:
        (已生成数量, 下一个编号)。
    """
    count = 0
    combo_id = start_id
    max_cycles = 200  # 安全上限

    for cycle in range(max_cycles):
        for scale_name in SCALE_NAMES:
            for platform_name in PLATFORM_NAMES:
                for combo in topology_combos:
                    if count >= target:
                        return count, combo_id

                    seed_base = cycle * 100000 + combo_id
                    components: list[tuple[dict, list, list, dict]] = []
                    for j, topo in enumerate(combo):
                        circuit, f_ins, f_outs, src = build_component(
                            topology_name=topo,
                            scale_name=scale_name,
                            platform_name=platform_name,
                            seed=seed_base + j * 1000,
                            prefix=f"c{j}",
                        )
                        components.append((circuit, f_ins, f_outs, src))

                    combined = combine_circuits(components, combo_type, combo_id)

                    # R03: 校验失败即 raise
                    errors = serializer.validate(combined)
                    if errors:
                        raise RuntimeError(
                            f"组合电路校验失败 [{combo_type} #{combo_id}] "
                            f"{combined['name']}: {errors}"
                        )

                    filename = f"{combined['name']}.json"
                    path = serializer.serialize(combined, output_dir, filename)

                    index_entries.append({
                        "path": filename,
                        "combination_type": combo_type,
                        "topologies": [s["topology"] for s in combined["metadata"]["component_sources"]],
                        "scale": scale_name,
                        "platform": platform_name,
                        "n_devices": len(combined["devices"]),
                        "n_connections": len(combined["connections"]),
                        "n_bridges": combined["metadata"]["n_bridges"],
                        "n_components": combined["metadata"]["n_components"],
                        "name": combined["name"],
                    })

                    count += 1
                    combo_id += 1

        if count >= target:
            break

    return count, combo_id


def generate_array_scaling(
    target: int,
    serializer: CircuitSerializer,
    index_entries: list[dict],
    output_dir: Path,
    start_id: int,
) -> tuple[int, int]:
    """生成规模扩展阵列化组合电路。

    对每个拓扑，按 N=2/4/8/16 阵列规模级联 N 份同拓扑组件。
    使用 scale=XS 保持单组件小规模，阵列规模 N 提供规模扩展。
    变种: 4 平台 × 多种子循环。

    Args:
        target: 目标数量（1500）。
        serializer: 电路序列化器。
        index_entries: 索引条目列表。
        output_dir: 输出目录。
        start_id: 起始编号。

    Returns:
        (已生成数量, 下一个编号)。
    """
    count = 0
    combo_id = start_id
    configs = [(t, n) for t in TOPOLOGIES for n in ARRAY_SIZES]  # 28 configs
    max_cycles = 200

    for cycle in range(max_cycles):
        for platform_name in PLATFORM_NAMES:
            for topo, n in configs:
                if count >= target:
                    return count, combo_id

                seed_base = cycle * 100000 + combo_id
                scale_name = "XS"  # 阵列化用 XS 基础组件，N 提供规模扩展

                components: list[tuple[dict, list, list, dict]] = []
                for j in range(n):
                    circuit, f_ins, f_outs, src = build_component(
                        topology_name=topo,
                        scale_name=scale_name,
                        platform_name=platform_name,
                        seed=seed_base + j * 1000,
                        prefix=f"c{j}",
                    )
                    components.append((circuit, f_ins, f_outs, src))

                extra_meta = {"array_size": n, "base_scale": scale_name}
                combined = combine_circuits(
                    components, "array", combo_id, extra_metadata=extra_meta
                )

                # R03: 校验失败即 raise
                errors = serializer.validate(combined)
                if errors:
                    raise RuntimeError(
                        f"阵列电路校验失败 [array N={n} #{combo_id}] "
                        f"{combined['name']}: {errors}"
                    )

                filename = f"{combined['name']}.json"
                path = serializer.serialize(combined, output_dir, filename)

                index_entries.append({
                    "path": filename,
                    "combination_type": "array",
                    "topologies": [topo] * n,
                    "scale": scale_name,
                    "platform": platform_name,
                    "n_devices": len(combined["devices"]),
                    "n_connections": len(combined["connections"]),
                    "n_bridges": combined["metadata"]["n_bridges"],
                    "n_components": n,
                    "array_size": n,
                    "name": combined["name"],
                })

                count += 1
                combo_id += 1

        if count >= target:
            break

    return count, combo_id


# =============================================================================
# 索引构建
# =============================================================================


def build_index(
    index_entries: list[dict],
    output_path: Path,
    stats: dict,
) -> Path:
    """构建并保存组合电路索引。

    Args:
        index_entries: 所有电路的索引条目。
        output_path: 索引输出路径。
        stats: 统计信息。

    Returns:
        索引文件路径。
    """
    # 按拓扑统计
    topo_counts: dict[str, int] = {}
    for entry in index_entries:
        for t in entry["topologies"]:
            topo_counts[t] = topo_counts.get(t, 0) + 1

    index_data = {
        "total": len(index_entries),
        "stats": stats,
        "topology_distribution": topo_counts,
        "sources": {
            topo: TOPOLOGY_SOURCES[topo] for topo in TOPOLOGIES
        },
        "references": [
            "Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460",
            "Reck et al., PRL 1994, https://doi.org/10.1103/PhysRevLett.73.58",
            "Spanke & Murphy, JLT 1988, https://ieeexplore.ieee.org/document/1072908",
            "Soldano & Pennings, JLT 1995, https://ieeexplore.ieee.org/document/412541",
            "Benes, Bell Syst Tech J 1965",
            "Takada et al., Electron. Lett. 1984",
            "Madsen & Zhao, Optical Filter Design, Wiley 1999",
            "SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
            "gdsfactory, https://gdsfactory.github.io/gdsfactory/",
            "PicBench, https://github.com/JeppeKlitgaard/PicBench",
            "LiDAR ISPD'25, https://arxiv.org/abs/2504.18813",
        ],
        "description": (
            "PoLaRIS 10000 组合电路基准集。基于 7 大拓扑组件"
            "（MZI/Ring/DC/MMI/Switch/Modulator/WDM）的组合扩展，"
            "覆盖二元/三元/四元组合及阵列化规模扩展。"
            "所有组件来源真实板子数据（SiEPIC/gdsfactory/PicBench/LiDAR）。"
        ),
        "circuits": index_entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return output_path


# =============================================================================
# 主入口
# =============================================================================


def main() -> int:
    """主入口。返回 0 成功，1 失败。"""
    parser = argparse.ArgumentParser(
        description="PoLaRIS 10000 组合电路生成器"
    )
    parser.add_argument(
        "--target", type=int, default=TARGET_TOTAL,
        help=f"目标总数（默认 {TARGET_TOTAL}）",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=OUTPUT_DIR,
        help=f"输出目录（默认 {OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅打印计划，不生成文件",
    )
    args = parser.parse_args()

    target = args.target
    output_dir = args.output_dir

    logger.info("=" * 70)
    logger.info("PoLaRIS 10000 组合电路生成器")
    logger.info("=" * 70)
    logger.info("7 大拓扑组件: %s", TOPOLOGIES)
    logger.info("5 种规模: %s", SCALE_NAMES)
    logger.info("4 种平台: %s", PLATFORM_NAMES)
    logger.info("输出目录: %s", output_dir)
    logger.info("目标总数: %d", target)

    # 计算各类别目标（按比例分配）
    if target == TARGET_TOTAL:
        t_binary = TARGET_BINARY
        t_ternary = TARGET_TERNARY
        t_quaternary = TARGET_QUATERNARY
        t_array = TARGET_ARRAY
    else:
        ratio = target / TARGET_TOTAL
        t_binary = int(TARGET_BINARY * ratio)
        t_ternary = int(TARGET_TERNARY * ratio)
        t_quaternary = int(TARGET_QUATERNARY * ratio)
        t_array = target - t_binary - t_ternary - t_quaternary

    logger.info("二元组合目标: %d", t_binary)
    logger.info("三元组合目标: %d", t_ternary)
    logger.info("四元组合目标: %d", t_quaternary)
    logger.info("阵列化目标: %d", t_array)

    if args.dry_run:
        logger.info("DRY RUN — 不生成文件")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    serializer = CircuitSerializer()
    index_entries: list[dict] = []
    stats: dict = {}
    next_id = 0

    # 1. 二元组合 A+B（有序对，含自配对）
    binary_combos = list(itertools.product(TOPOLOGIES, repeat=2))  # 49
    logger.info("[%d] 生成二元组合: %d 种拓扑对, 目标 %d",
                1, len(binary_combos), t_binary)
    n_binary, next_id = generate_category(
        target=t_binary,
        topology_combos=binary_combos,
        combo_type="binary",
        serializer=serializer,
        index_entries=index_entries,
        output_dir=output_dir,
        start_id=next_id,
    )
    stats["binary"] = n_binary
    logger.info("二元组合完成: %d 个", n_binary)

    # 2. 三元组合 A+B+C（无序三元组）
    ternary_combos = list(itertools.combinations(TOPOLOGIES, 3))  # 35
    logger.info("[%d] 生成三元组合: %d 种拓扑三元组, 目标 %d",
                2, len(ternary_combos), t_ternary)
    n_ternary, next_id = generate_category(
        target=t_ternary,
        topology_combos=ternary_combos,
        combo_type="ternary",
        serializer=serializer,
        index_entries=index_entries,
        output_dir=output_dir,
        start_id=next_id,
    )
    stats["ternary"] = n_ternary
    logger.info("三元组合完成: %d 个", n_ternary)

    # 3. 四元组合 A+B+C+D（无序四元组）
    quaternary_combos = list(itertools.combinations(TOPOLOGIES, 4))  # 35
    logger.info("[%d] 生成四元组合: %d 种拓扑四元组, 目标 %d",
                3, len(quaternary_combos), t_quaternary)
    n_quaternary, next_id = generate_category(
        target=t_quaternary,
        topology_combos=quaternary_combos,
        combo_type="quaternary",
        serializer=serializer,
        index_entries=index_entries,
        output_dir=output_dir,
        start_id=next_id,
    )
    stats["quaternary"] = n_quaternary
    logger.info("四元组合完成: %d 个", n_quaternary)

    # 4. 规模扩展阵列化（同拓扑 N 份级联）
    logger.info("[%d] 生成阵列化组合: 7 拓扑 × 4 阵列规模, 目标 %d",
                4, t_array)
    n_array, next_id = generate_array_scaling(
        target=t_array,
        serializer=serializer,
        index_entries=index_entries,
        output_dir=output_dir,
        start_id=next_id,
    )
    stats["array"] = n_array
    logger.info("阵列化组合完成: %d 个", n_array)

    total = n_binary + n_ternary + n_quaternary + n_array
    stats["total"] = total
    logger.info("=" * 70)
    logger.info("总计生成: %d 个组合电路", total)
    logger.info("  二元: %d", n_binary)
    logger.info("  三元: %d", n_ternary)
    logger.info("  四元: %d", n_quaternary)
    logger.info("  阵列: %d", n_array)

    # 5. 构建索引
    index_path = build_index(
        index_entries=index_entries,
        output_path=output_dir / "index.json",
        stats=stats,
    )
    logger.info("索引文件: %s (%d 条目)", index_path, total)
    logger.info("=" * 70)
    logger.info("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
