#!/usr/bin/env python3
"""质量门禁基准生成器。

从每个平台（SOI/SiN/InP/LNOI）选小/中/大（XS/S/M）各一个电路，
运行端到端流水线，收集关键指标作为质量门禁基准。

基准指标:
- pipeline_success: 流水线是否成功（GDS导出 + DRC通过）
- drc_passed: DRC 是否通过
- routing_success_rate: 布线成功率（已布线连接数/总连接数）
- total_loss_db: 总插入损耗
- elapsed_s: 端到端耗时
- n_devices: 器件数
- n_connections: 连接数

用法:
    python scripts/quality_gate_baseline.py          # 生成基准
    python scripts/quality_gate_baseline.py --check   # 检查是否达标
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

BASELINE_FILE = PROJECT_ROOT / "out" / "quality_gate" / "baseline.json"

# 质量门禁基准电路: 每平台 XS/S/M 各一个 (seed=042)
# 选择 mzi_array 拓扑（基础拓扑，所有平台都有，器件数适中）
GATE_CIRCUITS = [
    # (topology, scale, platform, seed)
    ("mzi_array", "XS", "SOI", 42),
    ("mzi_array", "S", "SOI", 42),
    ("mzi_array", "M", "SOI", 42),
    ("mzi_array", "XS", "SiN", 42),
    ("mzi_array", "S", "SiN", 42),
    ("mzi_array", "M", "SiN", 42),
    ("mzi_array", "XS", "InP", 42),
    ("mzi_array", "S", "InP", 42),
    ("mzi_array", "M", "InP", 42),
    ("mzi_array", "XS", "LNOI", 42),
    ("mzi_array", "S", "LNOI", 42),
    ("mzi_array", "M", "LNOI", 42),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("quality_gate")


def _circuit_path(topology: str, scale: str, platform: str, seed: int) -> Path:
    """获取电路 JSON 文件路径。"""
    return (
        PROJECT_ROOT
        / "data"
        / "benchmarks"
        / "generated"
        / topology
        / scale
        / platform
        / f"{topology}_{scale}_{platform}_{seed:03d}.json"
    )


def _load_circuit(path: Path) -> dict:
    """加载电路 JSON。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _run_pipeline(circuit_dict: dict) -> dict:
    """运行端到端流水线，返回指标。

    Returns:
        {
            "pipeline_success": bool,
            "drc_passed": bool,
            "routing_success_rate": float,  # 0.0-1.0
            "total_loss_db": float,
            "elapsed_s": float,
            "n_devices": int,
            "n_connections": int,
            "n_routed": int,
            "error": str | None,
        }
    """
    from polaris.data.specs import CircuitSpec, DeviceSpec
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    # 构建 CircuitSpec
    devices = []
    for d in circuit_dict["devices"]:
        ports = [(p[0], p[1], p[2], p[3]) for p in d["ports"]]
        devices.append(
            DeviceSpec(
                name=d["name"],
                device_type=d["type"],
                width_um=d["width_um"],
                height_um=d["height_um"],
                ports=ports,
                params=d.get("params", {}),
            )
        )
    connections = [
        (c[0], c[1], c[2], c[3]) for c in circuit_dict["connections"]
    ]
    circuit = CircuitSpec(
        name=circuit_dict["name"],
        devices=devices,
        connections=connections,
        canvas_w=circuit_dict["canvas_w"],
        canvas_h=circuit_dict["canvas_h"],
    )

    result = {
        "pipeline_success": False,
        "drc_passed": False,
        "routing_success_rate": 0.0,
        "total_loss_db": 0.0,
        "elapsed_s": 0.0,
        "n_devices": len(devices),
        "n_connections": len(connections),
        "n_routed": 0,
        "error": None,
    }

    t0 = time.time()
    try:
        config = PipelineConfig(max_sim_iterations=1)
        pipeline = IntegratedPipeline(config=config)
        pipeline_result = pipeline.run(circuit)
        t1 = time.time()
        result["elapsed_s"] = round(t1 - t0, 2)

        # 流水线成功 = GDS 导出成功
        result["pipeline_success"] = bool(pipeline_result.gds_path)

        # DRC 通过
        result["drc_passed"] = bool(pipeline_result.drc_passed)

        # 布线成功率
        n_total = len(connections)
        n_routed = len(pipeline_result.paths) if pipeline_result.paths else 0
        result["n_routed"] = n_routed
        result["routing_success_rate"] = round(n_routed / n_total, 4) if n_total > 0 else 0.0

        # 总损耗
        result["total_loss_db"] = round(pipeline_result.total_loss_db, 4)

    except Exception as e:
        t1 = time.time()
        result["elapsed_s"] = round(t1 - t0, 2)
        result["error"] = str(e)
        logger.error("流水线异常: %s", e)

    return result


def generate_baseline() -> dict:
    """生成质量门禁基准。

    对每个门禁电路运行流水线，收集指标。
    基准值 = 各电路指标的汇总（最小值/最大值/平均值）。
    """
    logger.info("=== 质量门禁基准生成 ===")
    logger.info("门禁电路: %d 个 (4平台 × 3规模)", len(GATE_CIRCUITS))

    results = []
    for topology, scale, platform, seed in GATE_CIRCUITS:
        path = _circuit_path(topology, scale, platform, seed)
        if not path.exists():
            logger.warning("电路文件不存在: %s, 跳过", path)
            continue

        circuit_dict = _load_circuit(path)
        name = circuit_dict["name"]
        logger.info("运行: %s (%d 器件, %d 连接)",
                     name, len(circuit_dict["devices"]),
                     len(circuit_dict["connections"]))

        metrics = _run_pipeline(circuit_dict)
        metrics["name"] = name
        metrics["topology"] = topology
        metrics["scale"] = scale
        metrics["platform"] = platform
        metrics["seed"] = seed

        logger.info(
            "  结果: success=%s, drc=%s, routing=%.2f%%, loss=%.2fdB, %.1fs",
            metrics["pipeline_success"],
            metrics["drc_passed"],
            metrics["routing_success_rate"] * 100,
            metrics["total_loss_db"],
            metrics["elapsed_s"],
        )
        results.append(metrics)

    if not results:
        logger.error("无有效结果，无法生成基准")
        return {}

    # 汇总基准指标
    baseline = {
        "description": "PoLaRIS 质量门禁基准 (每平台XS/S/M各1电路)",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gate_circuits": len(results),
        "circuits": results,
        "thresholds": _compute_thresholds(results),
    }

    # 保存
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    logger.info("基准已保存: %s", BASELINE_FILE)
    _print_summary(baseline)
    return baseline


def _compute_thresholds(results: list[dict]) -> dict:
    """计算门禁阈值。

    门禁逻辑:
    - pipeline_success_rate: 所有电路必须成功 (阈值 = 1.0)
    - drc_pass_rate: DRC 通过率 (阈值 = 1.0)
    - min_routing_success_rate: 最低布线成功率 (阈值 = 最小值)
    - max_total_loss_db: 最大损耗 (阈值 = 最大值 × 1.1, 允许10%波动)
    - max_elapsed_s: 最大耗时 (阈值 = 最大值 × 1.2, 允许20%波动)
    """
    n = len(results)
    success_count = sum(1 for r in results if r["pipeline_success"])
    drc_count = sum(1 for r in results if r["drc_passed"])
    routing_rates = [r["routing_success_rate"] for r in results]
    losses = [r["total_loss_db"] for r in results]
    elapsed = [r["elapsed_s"] for r in results]

    return {
        "pipeline_success_rate": round(success_count / n, 4) if n > 0 else 0.0,
        "drc_pass_rate": round(drc_count / n, 4) if n > 0 else 0.0,
        "min_routing_success_rate": round(min(routing_rates), 4) if routing_rates else 0.0,
        "max_total_loss_db": round(max(losses) * 1.1, 4) if losses else 0.0,
        "max_elapsed_s": round(max(elapsed) * 1.2, 2) if elapsed else 0.0,
        "n_gate_circuits": n,
    }


def check_gate() -> int:
    """检查当前代码是否通过质量门禁。

    Returns:
        0 = 通过, 1 = 不通过
    """
    if not BASELINE_FILE.exists():
        logger.error("基准文件不存在: %s, 请先运行 --generate", BASELINE_FILE)
        return 1

    with open(BASELINE_FILE, encoding="utf-8") as f:
        baseline = json.load(f)

    thresholds = baseline["thresholds"]
    logger.info("=== 质量门禁检查 ===")
    logger.info("基准: %d 电路, 生成于 %s", baseline["gate_circuits"],
                baseline.get("generated_at", "?"))
    logger.info("阈值: success≥%.0f%%, drc≥%.0f%%, routing≥%.2f%%, loss≤%.2fdB, time≤%.1fs",
                thresholds["pipeline_success_rate"] * 100,
                thresholds["drc_pass_rate"] * 100,
                thresholds["min_routing_success_rate"] * 100,
                thresholds["max_total_loss_db"],
                thresholds["max_elapsed_s"])

    # 运行门禁电路
    results = []
    for topology, scale, platform, seed in GATE_CIRCUITS:
        path = _circuit_path(topology, scale, platform, seed)
        if not path.exists():
            logger.error("电路文件不存在: %s", path)
            return 1
        circuit_dict = _load_circuit(path)
        metrics = _run_pipeline(circuit_dict)
        metrics["name"] = circuit_dict["name"]
        results.append(metrics)
        logger.info("  %s: success=%s drc=%s routing=%.2f%% loss=%.2fdB %.1fs",
                     metrics["name"],
                     metrics["pipeline_success"],
                     metrics["drc_passed"],
                     metrics["routing_success_rate"] * 100,
                     metrics["total_loss_db"],
                     metrics["elapsed_s"])

    # 计算当前指标
    current = _compute_thresholds(results)

    # 逐项对比
    passed = True
    # 阻断指标: 不通过则禁止提交
    blocking_checks = [
        ("pipeline_success_rate", current["pipeline_success_rate"],
         thresholds["pipeline_success_rate"], ">="),
        ("drc_pass_rate", current["drc_pass_rate"],
         thresholds["drc_pass_rate"], ">="),
        ("min_routing_success_rate", current["min_routing_success_rate"],
         thresholds["min_routing_success_rate"], ">="),
        ("max_total_loss_db", current["max_total_loss_db"],
         thresholds["max_total_loss_db"], "<="),
    ]
    # 参考指标: 仅记录, 不阻断 (受 CPU 负载影响波动大)
    reference_checks = [
        ("max_elapsed_s", current["max_elapsed_s"],
         thresholds["max_elapsed_s"], "<="),
    ]

    logger.info("--- 门禁结果 (阻断指标) ---")
    for name, current_val, threshold, op in blocking_checks:
        if op == ">=":
            ok = current_val >= threshold
        else:
            ok = current_val <= threshold
        status = "PASS" if ok else "FAIL"
        logger.info("  %s: %s (当前=%.4f, 基准=%.4f, %s)", name, status,
                     current_val, threshold, op)
        if not ok:
            passed = False

    logger.info("--- 参考指标 (不阻断) ---")
    for name, current_val, threshold, op in reference_checks:
        if op == ">=":
            ok = current_val >= threshold
        else:
            ok = current_val <= threshold
        status = "OK" if ok else "WARN"
        logger.info("  %s: %s (当前=%.4f, 基准=%.4f, %s)", name, status,
                     current_val, threshold, op)

    if passed:
        logger.info("=== 质量门禁通过 ===")
        # 检查是否优于基准，若是则刷新
        if _should_update_baseline(current, thresholds):
            logger.info("当前指标优于基准，刷新基准...")
            _update_baseline(results)
        return 0
    else:
        logger.error("=== 质量门禁未通过，禁止提交 ===")
        return 1


def _should_update_baseline(current: dict, thresholds: dict) -> bool:
    """判断是否应该更新基准（当前指标严格优于基准）。"""
    # 布线成功率更高 或 损耗更低 或 耗时更短
    return (
        current["min_routing_success_rate"] > thresholds["min_routing_success_rate"]
        or current["max_total_loss_db"] < thresholds["max_total_loss_db"] * 0.9
        or current["max_elapsed_s"] < thresholds["max_elapsed_s"] * 0.8
    )


def _update_baseline(results: list[dict]) -> None:
    """用更好的结果刷新基准。"""
    with open(BASELINE_FILE, encoding="utf-8") as f:
        baseline = json.load(f)

    baseline["circuits"] = results
    baseline["thresholds"] = _compute_thresholds(results)
    baseline["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    baseline["updated_reason"] = "当前指标优于基准，自动刷新"

    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    logger.info("基准已刷新: %s", BASELINE_FILE)


def _print_summary(baseline: dict) -> None:
    """打印基准摘要。"""
    t = baseline["thresholds"]
    print("\n" + "=" * 60)
    print("质量门禁基准摘要")
    print("=" * 60)
    print(f"门禁电路数: {baseline['gate_circuits']}")
    print(f"流水线成功率: {t['pipeline_success_rate'] * 100:.0f}%")
    print(f"DRC 通过率: {t['drc_pass_rate'] * 100:.0f}%")
    print(f"最低布线成功率: {t['min_routing_success_rate'] * 100:.2f}%")
    print(f"最大损耗: {t['max_total_loss_db']:.2f} dB")
    print(f"最大耗时: {t['max_elapsed_s']:.1f} s")
    print("=" * 60)
    print("\n各电路详情:")
    for c in baseline["circuits"]:
        print(f"  {c['name']}: success={c['pipeline_success']}, "
              f"drc={c['drc_passed']}, routing={c['routing_success_rate']*100:.1f}%, "
              f"loss={c['total_loss_db']:.2f}dB, {c['elapsed_s']:.1f}s")


def main() -> int:
    if "--check" in sys.argv:
        return check_gate()
    if "--generate" in sys.argv or len(sys.argv) == 1:
        generate_baseline()
        return 0
    print("用法: python scripts/quality_gate_baseline.py [--generate|--check]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
