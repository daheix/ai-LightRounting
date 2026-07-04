#!/usr/bin/env python3
"""测试6种矩阵拓扑所有规模DRC通过率。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path("/workspace")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "drc" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "place" / "src"))

import polaris_drc  # noqa: E402
from polaris_place.analytical import place_analytical  # noqa: E402

from scripts.generate_1000_circuits import PLATFORMS, SCALES  # noqa: E402
from scripts.generators.group_a import (  # noqa: E402
    ClementsMatrixGenerator,
    DCCouplerArrayGenerator,
    MMIArrayGenerator,
    ReckMatrixGenerator,
    SpankeMatrixGenerator,
)
from scripts.generators.group_c import PolarizationArrayGenerator  # noqa: E402

GENERATORS = {
    "clements_matrix": ClementsMatrixGenerator,
    "reck_matrix": ReckMatrixGenerator,
    "spanke_matrix": SpankeMatrixGenerator,
    "mmi_array": MMIArrayGenerator,
    "dc_array": DCCouplerArrayGenerator,
    "polarization_array": PolarizationArrayGenerator,
}


def main() -> int:
    platform = PLATFORMS["SOI"]
    seed = 42

    print("=" * 100)
    print("测试 6 种矩阵拓扑 × 5 规模 DRC 通过率")
    print("=" * 100)

    total_pass = 0
    total = 0
    for scale_name in ["XS", "S", "M", "L", "XL"]:
        scale = SCALES[scale_name]
        for topo_name, gen_cls in GENERATORS.items():
            gen = gen_cls(scale=scale, platform=platform, seed=seed)
            circuit = gen.generate()
            n_dev = len(circuit["devices"])
            n_conn = len(circuit["connections"])
            try:
                placements = place_analytical(circuit)
                drc = polaris_drc.run_drc(circuit, placements)
                violations = drc.get("violations", [])
                rule_counter = Counter(v["rule_name"] for v in violations)
                passed = drc.get("n_violations", 0) == 0
                status = "PASS" if passed else "FAIL"
                viol_str = dict(rule_counter) if rule_counter else "-"
                print(f"  [{status}] {scale_name:3s} {topo_name:25s} dev={n_dev:3d} conn={n_conn:3d} "
                      f"pass_rate={drc.get('pass_rate', 0):.2f} viol={viol_str}")
                if passed:
                    total_pass += 1
            except Exception as e:
                print(f"  [ERROR] {scale_name:3s} {topo_name:25s} dev={n_dev} conn={n_conn} "
                      f"exception={type(e).__name__}: {e}")
            total += 1
        print("-" * 100)

    print("=" * 100)
    print(f"总计: {total_pass}/{total} = {100.0 * total_pass / max(total, 1):.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
