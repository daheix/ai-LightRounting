#!/usr/bin/env python3
"""DRC 通过率快速验证脚本（轻量级，仅跑 place + DRC）。

用于验证 DRC 误报修复效果，不跑完整 EDA flow（省时）。

## 用法
    python scripts/verify_drc_pass_rate.py                    # 默认 6 拓扑 × 5 规模 × 2 = 60 电路
    python scripts/verify_drc_pass_rate.py --topos clements_matrix,reck_matrix
    python scripts/verify_drc_pass_rate.py --scales XS,S
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "drc" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "place" / "src"))

import polaris_drc  # noqa: E402
import polaris_place  # noqa: E402
from polaris_place.analytical import place_analytical  # noqa: E402

GENERATED_DIR = PROJECT_ROOT / "data" / "benchmarks" / "generated"

# 6 矩阵拓扑（用户任务指定）
MATRIX_TOPOS = [
    "clements_matrix", "reck_matrix", "spanke_matrix",
    "mmi_array", "dc_array", "polarization_array",
]
ALL_SCALES = ["XS", "S", "M", "L", "XL"]


def load_index() -> list[dict]:
    """加载电路索引。"""
    idx_path = GENERATED_DIR / "index.json"
    if not idx_path.exists():
        raise RuntimeError(f"索引不存在: {idx_path}")
    return json.loads(idx_path.read_text(encoding="utf-8")).get("circuits", [])


def verify_one(circuit_path: Path) -> dict:
    """对单个电路跑 place + DRC，返回结果 dict。"""
    circuit = json.loads(circuit_path.read_text(encoding="utf-8"))
    # place_analytical 直接接受 circuit dict
    placements = place_analytical(circuit)
    # run_drc 返回 {n_rules, n_violations, n_passed, pass_rate, violations}
    drc = polaris_drc.run_drc(circuit, placements)
    violations = drc.get("violations", [])
    rule_counter = Counter(v["rule_name"] for v in violations)
    return {
        "name": circuit.get("name", circuit_path.stem),
        "topology": circuit.get("topology", "?"),
        "scale": circuit.get("scale", "?"),
        "platform": circuit.get("platform", "?"),
        "n_devices": len(circuit.get("devices", [])),
        "drc_passed": drc.get("n_violations", 0) == 0,
        "n_violations": drc.get("n_violations", 0),
        "violations": dict(rule_counter),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DRC 通过率快速验证")
    parser.add_argument("--topos", type=str, default=",".join(MATRIX_TOPOS),
                        help="逗号分隔拓扑名")
    parser.add_argument("--scales", type=str, default=",".join(ALL_SCALES),
                        help="逗号分隔规模名")
    parser.add_argument("--per-cell", type=int, default=2,
                        help="每 (拓扑, 规模) 抽样数（默认 2）")
    args = parser.parse_args()

    topos = [t.strip() for t in args.topos.split(",")]
    scales = [s.strip() for s in args.scales.split(",")]
    per_cell = max(1, int(args.per_cell))

    index = load_index()

    # 按 (topology, scale) 分组，每组取 per_cell 个
    by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for entry in index:
        key = (entry["topology"], entry["scale"])
        by_cell[key].append(entry)

    selected: list[dict] = []
    for topo in topos:
        for scale in scales:
            entries = by_cell.get((topo, scale), [])
            if not entries:
                print(f"  [WARN] 无电路: {topo}/{scale}")
                continue
            # 取前 per_cell 个（按 name 排序保证可复现）
            entries_sorted = sorted(entries, key=lambda e: e["name"])[:per_cell]
            selected.extend(entries_sorted)

    print(f"抽样: {len(selected)} 电路 ({len(topos)} 拓扑 × {len(scales)} 规模 × {per_cell})")
    print("=" * 70)

    results: list[dict] = []
    rule_total = Counter()
    pass_by_scale: dict[str, list[bool]] = defaultdict(list)
    pass_by_topo: dict[str, list[bool]] = defaultdict(list)

    for entry in selected:
        path = GENERATED_DIR / entry["path"]
        try:
            r = verify_one(path)
        except Exception as e:
            r = {
                "name": entry["name"], "topology": entry["topology"],
                "scale": entry["scale"], "platform": entry.get("platform", "?"),
                "n_devices": 0, "drc_passed": False, "n_violations": -1,
                "violations": {"_ERROR": 1}, "_error": str(e),
            }
        results.append(r)
        for rule, cnt in r["violations"].items():
            rule_total[rule] += cnt
        pass_by_scale[r["scale"]].append(r["drc_passed"])
        pass_by_topo[r["topology"]].append(r["drc_passed"])
        status = "PASS" if r["drc_passed"] else "FAIL"
        viol_str = ",".join(f"{k}={v}" for k, v in r["violations"].items()) or "-"
        print(f"  [{status}] {r['name']:50s} viol={viol_str}")

    print("=" * 70)
    total = len(results)
    passed = sum(1 for r in results if r["drc_passed"])
    print(f"总计: {passed}/{total} = {100.0*passed/max(total,1):.1f}%")
    print(f"违规统计: {dict(rule_total)}")

    print("\n按规模:")
    for scale in scales:
        pl = pass_by_scale.get(scale, [])
        if pl:
            print(f"  {scale}: {sum(pl)}/{len(pl)}")

    print("\n按拓扑:")
    for topo in topos:
        pl = pass_by_topo.get(topo, [])
        if pl:
            print(f"  {topo}: {sum(pl)}/{len(pl)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
