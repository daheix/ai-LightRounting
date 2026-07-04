#!/usr/bin/env python3
"""批量端到端测试 10000 个组合电路。

遍历 data/benchmarks/combinations/ 全部电路，执行端到端流水线，
收集 success/drc_passed/total_loss_db/n_crossings/elapsed_sec。

数据源字段与 batch_test_1000_circuits.py 不同：
- 原 index: {name, topology, scale, platform, path}
- 新 index: {name, combination_type, topologies[list], scale, platform, path, ...}

按 combination_type (binary/ternary/quaternary/array) 分组统计。

支持 4 进程并行 + 断点续跑 + maxtasksperchild=30 防 worker 长跑死锁。

文献溯源：
- Python multiprocessing.Pool maxtasksperchild:
  https://docs.python.org/3/library/multiprocessing.html#multiprocessing.pool.Pool
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Clements et al., Optica 2016: https://doi.org/10.1364/OPTICA.3.001460
- Reck et al., PRL 1994: https://doi.org/10.1103/PhysRevLett.73.58
- Spanke & Murphy, JLT 1988: https://ieeexplore.ieee.org/document/1072908

用法:
    python scripts/test_combinations.py                  # 全量测试
    python scripts/test_combinations.py --limit 30       # 冒烟测试
    python scripts/test_combinations.py --workers 4      # 4进程并行
    python scripts/test_combinations.py --resume         # 断点续跑
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("combo_test")

COMBINATIONS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "combinations"
OUTPUT_DIR = PROJECT_ROOT / "out" / "combinations_test"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"
RESULTS_FILE = OUTPUT_DIR / "results.json"


@dataclass
class ComboTestResult:
    """单个组合电路测试结果。

    注意: ``__test__ = False`` 防止 pytest 将本 dataclass 误收集为测试类。
    """
    __test__ = False

    name: str
    combination_type: str          # binary / ternary / quaternary / array
    topologies: str                # 形如 "MZI+Ring"，便于分组
    scale: str
    platform: str
    n_devices: int
    n_connections: int
    success: bool
    drc_passed: bool
    total_loss_db: float
    n_crossings: int
    sim_iterations: int
    elapsed_sec: float
    error: str = ""


def load_circuit_index() -> list[dict]:
    """加载组合电路索引。"""
    index_path = COMBINATIONS_DIR / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"组合电路索引不存在: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return data.get("circuits", [])


def load_completed() -> dict[str, ComboTestResult]:
    """加载已完成的测试结果（断点续跑）。"""
    if not PROGRESS_FILE.exists():
        return {}
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return {r["name"]: ComboTestResult(**r) for r in data.get("results", [])}
    except Exception:
        return {}


def save_progress(results: dict[str, ComboTestResult]) -> None:
    """保存进度。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    n_total = len(results)
    n_success = sum(1 for r in results.values() if r.success)
    n_drc = sum(1 for r in results.values() if r.drc_passed)
    data = {
        "total": n_total,
        "n_success": n_success,
        "n_drc_passed": n_drc,
        "success_rate": (n_success / n_total) if n_total else 0.0,
        "drc_rate": (n_drc / n_total) if n_total else 0.0,
        "updated": datetime.now().isoformat(),
        "results": [asdict(r) for r in results.values()],
    }
    PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def test_single_combo(entry: dict) -> ComboTestResult:
    """测试单个组合电路（工作进程函数）。

    entry 字段: {name, combination_type, topologies, scale, platform, path, ...}
    """
    name = entry["name"]
    combination_type = entry.get("combination_type", "unknown")
    topologies = "+".join(entry.get("topologies", []))
    scale = entry.get("scale", "")
    platform = entry.get("platform", "")
    circuit_path = COMBINATIONS_DIR / entry["path"]

    # 读取电路 JSON
    try:
        circuit_data = json.loads(circuit_path.read_text(encoding="utf-8"))
    except Exception as e:
        return ComboTestResult(
            name=name, combination_type=combination_type, topologies=topologies,
            scale=scale, platform=platform,
            n_devices=0, n_connections=0, success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, sim_iterations=0,
            elapsed_sec=0.0, error=f"读取电路失败: {e}",
        )

    # 构建 CircuitSpec（v5.0: polaris_core.specs）
    try:
        from polaris_core.specs import CircuitSpec, DeviceSpec

        instances = circuit_data.get("instances", {})
        devices = []
        for dev in circuit_data.get("devices", []):
            ports = [(p[0], float(p[1]), float(p[2]), p[3]) for p in dev.get("ports", [])]
            params = dict(dev.get("params", {}))
            inst = instances.get(dev["name"], {})
            params.update(inst.get("settings", {}))
            devices.append(DeviceSpec(
                name=dev["name"], device_type=dev["type"],
                width_um=float(dev["width_um"]), height_um=float(dev["height_um"]),
                ports=ports, params=params,
            ))
        connections = [tuple(c) for c in circuit_data.get("connections", [])]
        spec = CircuitSpec(
            name=circuit_data.get("name", name),
            devices=devices, connections=connections,
            canvas_w=float(circuit_data.get("canvas_w", 300.0)),
            canvas_h=float(circuit_data.get("canvas_h", 200.0)),
        )
    except Exception as e:
        return ComboTestResult(
            name=name, combination_type=combination_type, topologies=topologies,
            scale=scale, platform=platform,
            n_devices=0, n_connections=0, success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, sim_iterations=0,
            elapsed_sec=0.0, error=f"构建 CircuitSpec 失败: {e}",
        )

    # 执行端到端流水线
    t0 = time.perf_counter()
    try:
        from polaris_core import circuit_to_dict
        from polaris_orchestrator.flow import run_eda_flow

        circuit_dict = circuit_to_dict(spec)
        iter_output = Path("/tmp/polaris_combo_test") / name
        iter_output.mkdir(parents=True, exist_ok=True)

        # 跳过 stage 8（逆向设计）和 stage 9（量子验证），批量测试聚焦布局/布线/DRC
        flow_result = run_eda_flow(
            circuit=circuit_dict,
            output_dir=str(iter_output),
            skip_stages=[8, 9],
            strict=False,
        )
        elapsed = time.perf_counter() - t0

        # R03: stage 失败时该字段缺失，记为失败状态而非假数据
        stages = {s["stage_id"]: s for s in flow_result["stages"]}
        place_res = stages.get(3, {}).get("result") or {}
        route_res = stages.get(4, {}).get("result") or {}
        drc_lvs_res = stages.get(6, {}).get("result") or {}
        if isinstance(drc_lvs_res, dict):
            drc_res = drc_lvs_res.get("drc", {}) or {}
        else:
            drc_res = {}

        # success: 关键 stage（2验证/3布局/4布线/6DRC）全部成功
        critical_ids = [2, 3, 4, 6]
        success = all(
            stages.get(sid, {}).get("status") == "success" for sid in critical_ids
        )
        # DRC 通过 = 无违规（n_violations == 0）；stage 失败时 drc_res 为空 → False
        drc_passed = bool(drc_res) and drc_res.get("n_violations", -1) == 0
        total_loss_db = float(route_res.get("total_loss_db", 0.0)) if route_res else 0.0
        n_crossings = int(route_res.get("n_crossings", 0)) if route_res else 0

        # 失败时收集错误信息（R03: 失败即告警，不假数据）
        error_msg = ""
        if not success:
            failed_stages = [
                f"stage{s['stage_id']}({s['name']}): {s.get('error') or s['status']}"
                for s in flow_result["stages"]
                if s["status"] != "success" and s["status"] != "skipped"
            ]
            error_msg = "; ".join(failed_stages) if failed_stages else "未知失败"

        return ComboTestResult(
            name=name, combination_type=combination_type, topologies=topologies,
            scale=scale, platform=platform,
            n_devices=len(spec.devices), n_connections=len(spec.connections),
            success=success, drc_passed=drc_passed,
            total_loss_db=total_loss_db, n_crossings=n_crossings,
            sim_iterations=1, elapsed_sec=elapsed,
            error=error_msg,
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        tb = traceback.format_exc()
        return ComboTestResult(
            name=name, combination_type=combination_type, topologies=topologies,
            scale=scale, platform=platform,
            n_devices=len(spec.devices), n_connections=len(spec.connections),
            success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, sim_iterations=0,
            elapsed_sec=elapsed, error=f"{e}\n{tb[-500:]}",
        )


# 禁止 pytest 收集 test_single_combo（函数名以 test_ 开头但非测试用例）
test_single_combo.__test__ = False


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(description="批量端到端测试 10000 个组合电路")
    parser.add_argument("--limit", type=int, default=0, help="限制测试数量（0=全部）")
    parser.add_argument("--workers", type=int, default=0, help="并行进程数（0=自动）")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--combo-type", type=str, default="",
                        help="仅测试指定组合类型（binary/ternary/quaternary/array）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 加载组合电路索引
    circuits = load_circuit_index()
    logger.info("索引: %d 个组合电路", len(circuits))

    # 过滤组合类型
    if args.combo_type:
        circuits = [c for c in circuits if c.get("combination_type") == args.combo_type]
        logger.info("过滤组合类型 %s: %d 个电路", args.combo_type, len(circuits))

    # 限制数量
    if args.limit > 0:
        circuits = circuits[:args.limit]
        logger.info("限制: %d 个电路", len(circuits))

    # 断点续跑
    completed = load_completed() if args.resume else {}
    if completed:
        logger.info("已完成: %d 个电路（断点续跑）", len(completed))
        circuits = [c for c in circuits if c["name"] not in completed]

    if not circuits:
        logger.info("无待测试电路")
        return 0

    logger.info("待测试: %d 个电路", len(circuits))

    # 并行测试
    n_workers = args.workers if args.workers > 0 else min(cpu_count(), 4)
    logger.info("并行进程: %d", n_workers)

    results: dict[str, ComboTestResult] = dict(completed)
    total = len(circuits)
    t_start = time.perf_counter()

    if n_workers == 1:
        # 串行模式（调试用）
        for i, entry in enumerate(circuits):
            result = test_single_combo(entry)
            results[result.name] = result
            status = "OK" if result.success else "FAIL"
            drc = "Y" if result.drc_passed else "N"
            logger.info("[%5d/%d] %s | %s | drc=%s | loss=%.2f | %.2fs",
                        i + 1, total, result.name, status, drc,
                        result.total_loss_db, result.elapsed_sec)
            if (i + 1) % 10 == 0:
                save_progress(results)
                elapsed = time.perf_counter() - t_start
                rate = (i + 1) / elapsed
                eta = (total - i - 1) / rate if rate > 0 else 0
                logger.info("进度: %d/%d (%.1f%%) | 速率: %.1f/s | ETA: %.0fs",
                            i + 1, total, 100 * (i + 1) / total, rate, eta)
    else:
        # 并行模式（R05 Bug 修复: maxtasksperchild=30 防 worker 长跑死锁）
        with Pool(n_workers, maxtasksperchild=30) as pool:
            for i, result in enumerate(pool.imap_unordered(test_single_combo, circuits)):
                results[result.name] = result
                status = "OK" if result.success else "FAIL"
                drc = "Y" if result.drc_passed else "N"
                logger.info("[%5d/%d] %s | %s | drc=%s | loss=%.2f | %.2fs",
                            i + 1, total, result.name, status, drc,
                            result.total_loss_db, result.elapsed_sec)
                # 每 5 个保存一次进度（R05: 减少崩溃时丢失的结果数）
                if (i + 1) % 5 == 0:
                    save_progress(results)
                    elapsed = time.perf_counter() - t_start
                    rate = (i + 1) / elapsed
                    eta = (total - i - 1) / rate if rate > 0 else 0
                    logger.info("进度: %d/%d (%.1f%%) | 速率: %.1f/s | ETA: %.0fs",
                                i + 1, total, 100 * (i + 1) / total, rate, eta)

    # 保存最终结果
    save_progress(results)
    final_data = {
        "total": len(results),
        "updated": datetime.now().isoformat(),
        "results": [asdict(r) for r in results.values()],
    }
    RESULTS_FILE.write_text(json.dumps(final_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # 汇总
    elapsed_total = time.perf_counter() - t_start
    n_success = sum(1 for r in results.values() if r.success)
    n_drc = sum(1 for r in results.values() if r.drc_passed)
    n_total = len(results)

    # 按组合类型分组统计
    by_type: dict[str, dict] = {}
    for r in results.values():
        t = r.combination_type
        if t not in by_type:
            by_type[t] = {"total": 0, "success": 0, "drc_passed": 0}
        by_type[t]["total"] += 1
        if r.success:
            by_type[t]["success"] += 1
        if r.drc_passed:
            by_type[t]["drc_passed"] += 1

    logger.info("=" * 70)
    logger.info("组合电路批量测试完成")
    logger.info("  总数: %d", n_total)
    logger.info("  成功: %d (%.1f%%)", n_success, 100 * n_success / n_total if n_total else 0)
    logger.info("  DRC通过: %d (%.1f%%)", n_drc, 100 * n_drc / n_total if n_total else 0)
    logger.info("  总耗时: %.1fs", elapsed_total)
    logger.info("  按组合类型分组:")
    for t, st in sorted(by_type.items()):
        sr = 100 * st["success"] / st["total"] if st["total"] else 0
        dr = 100 * st["drc_passed"] / st["total"] if st["total"] else 0
        logger.info("    %s: total=%d success=%d(%.1f%%) drc=%d(%.1f%%)",
                    t, st["total"], st["success"], sr, st["drc_passed"], dr)
    logger.info("  结果: %s", RESULTS_FILE)
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
