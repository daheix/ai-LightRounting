#!/usr/bin/env python3
"""批量生成 1000+ 电路测试集。

15 种拓扑 × 5 种规模 × 4 种平台 × 4 种子 = 1200 个电路。

用法:
    python scripts/batch_generate_1000.py
    python scripts/batch_generate_1000.py --dry-run  # 仅统计不生成
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 框架自带生成器
from scripts.generate_1000_circuits import (  # noqa: E402  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    PLATFORMS,
    SCALES,
    CircuitGenerator,
    CircuitIndex,
    CircuitSerializer,
    MZIArrayGenerator,
    RingFilterGenerator,
)

# group_a: Clements/Reck/Spanke/MMI/DC
from scripts.generators.group_a import (  # noqa: E402
    ClementsMatrixGenerator,
    DCCouplerArrayGenerator,
    MMIArrayGenerator,
    ReckMatrixGenerator,
    SpankeMatrixGenerator,
)

# group_b: WDM/Switch/Modulator/Quantum/Lattice
from scripts.generators.group_b import (  # noqa: E402
    LatticeFilterGenerator,
    ModulatorArrayGenerator,
    OpticalSwitchMatrixGenerator,
    QuantumPhotonicsGenerator,
    WDMMuxDemuxGenerator,
)

# group_c: RingDelay/Polarization/Hybrid
from scripts.generators.group_c import (  # noqa: E402
    HybridTopologyGenerator,
    PolarizationArrayGenerator,
    RingDelayLineGenerator,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("batch_gen")

# 15 种拓扑生成器注册表
ALL_GENERATORS: dict[str, type[CircuitGenerator]] = {
    # 框架自带
    "mzi_array": MZIArrayGenerator,
    "ring_filter": RingFilterGenerator,
    # group_a
    "clements_matrix": ClementsMatrixGenerator,
    "reck_matrix": ReckMatrixGenerator,
    "spanke_matrix": SpankeMatrixGenerator,
    "mmi_array": MMIArrayGenerator,
    "dc_array": DCCouplerArrayGenerator,
    # group_b
    "wdm_mux_demux": WDMMuxDemuxGenerator,
    "switch_matrix": OpticalSwitchMatrixGenerator,
    "modulator_array": ModulatorArrayGenerator,
    "quantum_photonics": QuantumPhotonicsGenerator,
    "lattice_filter": LatticeFilterGenerator,
    # group_c
    "ring_delay_line": RingDelayLineGenerator,
    "polarization_array": PolarizationArrayGenerator,
    "hybrid_topology": HybridTopologyGenerator,
}

# 生成参数：4 个种子（每种组合生成 4 个变种）
SEEDS = [42, 142, 242, 342]


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(description="批量生成 1000+ 电路测试集")
    parser.add_argument("--dry-run", action="store_true", help="仅统计不生成")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help=f"输出目录（默认 {DEFAULT_OUTPUT_DIR}）")
    parser.add_argument("--topologies", type=str, default="all",
                        help="逗号分隔拓扑名，或 all")
    parser.add_argument("--scales", type=str, default="all",
                        help="逗号分隔规模名，或 all")
    parser.add_argument("--platforms", type=str, default="all",
                        help="逗号分隔平台名，或 all")
    parser.add_argument("--seeds", type=str, default="42,142,242,342",
                        help="逗号分隔种子列表")
    args = parser.parse_args()

    # 解析参数
    topo_list = (list(ALL_GENERATORS.keys()) if args.topologies == "all"
                 else [t.strip() for t in args.topologies.split(",")])
    scale_list = (list(SCALES.keys()) if args.scales == "all"
                  else [s.strip() for s in args.scales.split(",")])
    platform_list = (list(PLATFORMS.keys()) if args.platforms == "all"
                     else [p.strip() for p in args.platforms.split(",")])
    seed_list = [int(s.strip()) for s in args.seeds.split(",")]

    # 校验
    for t in topo_list:
        if t not in ALL_GENERATORS:
            logger.error("未知拓扑: %s", t)
            return 1
    for s in scale_list:
        if s not in SCALES:
            logger.error("未知规模: %s", s)
            return 1
    for p in platform_list:
        if p not in PLATFORMS:
            logger.error("未知平台: %s", p)
            return 1

    total_planned = len(topo_list) * len(scale_list) * len(platform_list) * len(seed_list)
    logger.info("计划生成: %d 拓扑 × %d 规模 × %d 平台 × %d 种子 = %d 电路",
                len(topo_list), len(scale_list), len(platform_list),
                len(seed_list), total_planned)

    if args.dry_run:
        logger.info("dry-run 模式，不生成文件")
        return 0

    serializer = CircuitSerializer()
    index = CircuitIndex()
    total_generated = 0
    total_failed = 0

    for topology in topo_list:
        gen_cls = ALL_GENERATORS[topology]
        for scale_name in scale_list:
            scale = SCALES[scale_name]
            for platform_name in platform_list:
                platform = PLATFORMS[platform_name]
                for seed in seed_list:
                    # 生成电路
                    try:
                        gen = gen_cls(scale=scale, platform=platform, seed=seed)
                        circuit = gen.generate()
                    except Exception as e:
                        logger.error("生成失败 %s/%s/%s/seed=%d: %s",
                                     topology, scale_name, platform_name, seed, e)
                        total_failed += 1
                        continue

                    # 校验
                    errors = serializer.validate(circuit)
                    if errors:
                        logger.error("校验失败 %s: %s", circuit.get("name", "?"), errors[:3])
                        total_failed += 1
                        continue

                    # 序列化
                    output_dir = args.output_dir / topology / scale_name / platform_name
                    filename = f"{circuit['name']}.json"
                    path = serializer.serialize(circuit, output_dir, filename)

                    index.add(
                        circuit_path=path, topology=topology, scale=scale_name,
                        platform=platform_name, n_devices=len(circuit["devices"]),
                        name=circuit["name"],
                    )
                    total_generated += 1

        # 每种拓扑完成后打印进度
        logger.info("拓扑 %s 完成: 累计 %d 电路", topology, total_generated)

    # 保存索引
    index_path = index.save(args.output_dir / "index.json")
    logger.info("索引: %s (%d 电路)", index_path, total_generated)

    # 打印汇总
    logger.info("=" * 70)
    logger.info("批量生成完成")
    logger.info("  成功: %d", total_generated)
    logger.info("  失败: %d", total_failed)
    logger.info("  总计: %d", total_generated + total_failed)
    logger.info("  拓扑数: %d", len(topo_list))
    logger.info("  目标: 1000+")
    if total_generated >= 1000:
        logger.info("  状态: ✓ 达到目标")
    else:
        logger.warning("  状态: ✗ 未达到目标（差 %d）", 1000 - total_generated)
    logger.info("=" * 70)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
