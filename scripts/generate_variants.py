#!/usr/bin/env python3
"""变体数据集生成 CLI 入口。

生成规模变体（Curriculum Learning）和参数扫描变体（Domain Randomization），
用于训练具备规模泛化能力和参数鲁棒性的 RL 布局布线智能体。

流程:
1. 规模变体: 按课程级别（小/中/大/超大）生成不同器件数的电路
2. 参数扫描变体: 对基准电路的器件参数进行随机扫描
3. 输出 JSON 格式变体数据 + 统计信息

来源:
- Bengio et al., "Curriculum Learning", ICML 2009
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- OpenAI, "Solving Rubik's Cube with a Robot Hand" (ADR), 2019
  https://ar5iv.labs.arxiv.org/html/1910.07113
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)

用法:
    # 生成全部变体（规模 + 参数扫描）
    python scripts/generate_variants.py --output data/variants

    # 仅生成规模变体，每级别 20 个
    python scripts/generate_variants.py --output data/variants \\
        --mode scale --n-per-level 20

    # 仅生成参数扫描变体，每个基准电路 15 个
    python scripts/generate_variants.py --output data/variants \\
        --mode param-sweep --n-sweeps 15
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 确保 src/ 在 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from polaris.data.variant_generator import (  # noqa: E402
    CURRICULUM_LEVELS,
    generate_param_sweep_variants,
    generate_scale_variants,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("generate_variants")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    p = argparse.ArgumentParser(description="PoLaRIS 变体数据集生成器")
    p.add_argument(
        "--output",
        type=str,
        default="data/variants",
        help="输出目录（默认 data/variants）",
    )
    p.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["all", "scale", "param-sweep"],
        help="生成模式: all=全部, scale=仅规模变体, param-sweep=仅参数扫描",
    )
    p.add_argument(
        "--n-per-level",
        type=int,
        default=10,
        help="每个课程级别的规模变体数（默认 10）",
    )
    p.add_argument(
        "--n-sweeps",
        type=int,
        default=10,
        help="每个基准电路的参数扫描变体数（默认 10）",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子（默认 42）",
    )
    return p.parse_args()


def main() -> int:
    """变体数据集生成主入口。

    Returns:
        退出码（0 成功，非 0 失败）。
    """
    args = parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    all_stats: dict = {"output_dir": str(out), "modes": {}}

    if args.mode in ("all", "scale"):
        logger.info("=" * 60)
        logger.info("生成规模变体（Curriculum Learning）")
        logger.info("=" * 60)
        scale_dir = out / "scale"
        stats = generate_scale_variants(
            scale_dir,
            n_per_level=args.n_per_level,
        )
        all_stats["modes"]["scale"] = stats
        logger.info(
            "规模变体完成: %d 电路, %d 变体",
            stats["total_circuits"],
            stats["total_variants"],
        )

    if args.mode in ("all", "param-sweep"):
        logger.info("=" * 60)
        logger.info("生成参数扫描变体（Domain Randomization）")
        logger.info("=" * 60)
        sweep_dir = out / "param_sweep"
        stats = generate_param_sweep_variants(
            sweep_dir,
            n_sweeps=args.n_sweeps,
            seed=args.seed,
        )
        all_stats["modes"]["param_sweep"] = stats
        logger.info(
            "参数扫描变体完成: %d 电路, %d 变体",
            stats["total_circuits"],
            stats["total_variants"],
        )

    # 保存汇总统计
    summary_path = out / "generation_summary.json"
    summary_path.write_text(
        json.dumps(all_stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("汇总统计已保存: %s", summary_path)
    logger.info("课程级别: %s", [lv.name for lv in CURRICULUM_LEVELS])
    return 0


if __name__ == "__main__":
    sys.exit(main())
