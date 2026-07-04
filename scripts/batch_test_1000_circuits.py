#!/usr/bin/env python3
"""批量端到端测试 1200 个电路。

遍历 data/benchmarks/generated/ 全部电路，执行端到端流水线，
收集 success/drc_passed/total_loss_db/n_crossings/elapsed_s。

支持并行执行 + 断点续跑。

用法:
    python scripts/batch_test_1000_circuits.py                    # 全量测试
    python scripts/batch_test_1000_circuits.py --limit 30         # 冒烟测试(30个)
    python scripts/batch_test_1000_circuits.py --workers 4        # 4进程并行
    python scripts/batch_test_1000_circuits.py --resume           # 断点续跑
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from dataclasses import asdict, dataclass
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
logger = logging.getLogger("batch_test")

GENERATED_DIR = PROJECT_ROOT / "data" / "benchmarks" / "generated"
OUTPUT_DIR = PROJECT_ROOT / "out" / "batch_test"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"
RESULTS_FILE = OUTPUT_DIR / "results.json"


@dataclass
class TestResult:
    """单个电路测试结果。

    注意: ``__test__ = False`` 防止 pytest 将本 dataclass 误收集为测试类
    （类名以 ``Test`` 开头会触发 pytest 默认收集规则）。
    """
    # pytest 收集开关：False 表示本类不是测试类，禁止 pytest 收集
    __test__ = False

    name: str
    topology: str
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
    """加载电路索引。"""
    index_path = GENERATED_DIR / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"电路索引不存在: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return data.get("circuits", [])


def load_completed() -> dict[str, TestResult]:
    """加载已完成的测试结果（断点续跑）。"""
    if not PROGRESS_FILE.exists():
        return {}
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return {r["name"]: TestResult(**r) for r in data.get("results", [])}
    except Exception:
        return {}


def save_progress(results: dict[str, TestResult]) -> None:
    """保存进度。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "total": len(results),
        "updated": datetime.now().isoformat(),
        "results": [asdict(r) for r in results.values()],
    }
    PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def test_single_circuit(entry: dict) -> TestResult:
    """测试单个电路（工作进程函数）。

    注意: 函数名以 ``test_`` 开头会触发 pytest 默认收集规则，但本函数是
    批量测试脚本的工作进程函数（参数为 ``entry: dict``，非 pytest fixture），
    故通过 ``__test__ = False`` 显式禁止 pytest 收集。
    """
    name = entry["name"]
    topology = entry["topology"]
    scale = entry["scale"]
    platform = entry["platform"]
    circuit_path = GENERATED_DIR / entry["path"]

    # 读取电路 JSON
    try:
        circuit_data = json.loads(circuit_path.read_text(encoding="utf-8"))
    except Exception as e:
        return TestResult(
            name=name, topology=topology, scale=scale, platform=platform,
            n_devices=0, n_connections=0, success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, sim_iterations=0,
            elapsed_sec=0.0, error=f"读取电路失败: {e}",
        )

    # 构建 CircuitSpec（v5.0: polaris.data.specs → polaris_core.specs）
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
        return TestResult(
            name=name, topology=topology, scale=scale, platform=platform,
            n_devices=0, n_connections=0, success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, sim_iterations=0,
            elapsed_sec=0.0, error=f"构建 CircuitSpec 失败: {e}",
        )

    # 执行端到端流水线（v5.0: IntegratedPipeline 未迁移，改用 run_eda_flow）
    # run_eda_flow 签名: (circuit: dict, output_dir: str, skip_stages, strict) -> dict
    # 返回 {stages: [{stage_id, name, status, duration, result, error}],
    #       n_success, n_failed, n_skipped, total_duration}
    # stage 3 result = place_circuit() → {placements, hpwl, ...}
    # stage 4 result = route_circuit() → {paths, total_loss_db, n_crossings, n_bends, ...}
    # stage 6 result = {drc: {n_rules, n_violations, n_passed, pass_rate, ...}, lvs: ...}
    t0 = time.perf_counter()
    try:
        from polaris_core import circuit_to_dict
        from polaris_orchestrator.flow import run_eda_flow

        # CircuitSpec → polaris-core 风格 circuit dict（device_type 字段标准化）
        circuit_dict = circuit_to_dict(spec)

        # 输出到 /tmp（减少磁盘 I/O）
        iter_output = Path("/tmp/polaris_batch_test") / name
        iter_output.mkdir(parents=True, exist_ok=True)

        # 跳过 stage 8（逆向设计）和 stage 9（量子验证），批量测试聚焦
        # 布局/布线/DRC/仿真核心指标，省时（每电路约省 60% 时间）
        flow_result = run_eda_flow(
            circuit=circuit_dict,
            output_dir=str(iter_output),
            skip_stages=[8, 9],
            strict=False,
        )
        elapsed = time.perf_counter() - t0

        # 从 stages 提取指标（R03: stage 失败时该字段缺失，记为失败状态而非假数据）
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

        return TestResult(
            name=name, topology=topology, scale=scale, platform=platform,
            n_devices=len(spec.devices), n_connections=len(spec.connections),
            success=success, drc_passed=drc_passed,
            total_loss_db=total_loss_db, n_crossings=n_crossings,
            sim_iterations=1, elapsed_sec=elapsed,
            error=error_msg,
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        tb = traceback.format_exc()
        return TestResult(
            name=name, topology=topology, scale=scale, platform=platform,
            n_devices=len(spec.devices), n_connections=len(spec.connections),
            success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, sim_iterations=0,
            elapsed_sec=elapsed, error=f"{e}\n{tb[-500:]}",
        )


# 禁止 pytest 收集 test_single_circuit（函数名以 test_ 开头但非测试用例）
test_single_circuit.__test__ = False


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(description="批量端到端测试 1200 个电路")
    parser.add_argument("--limit", type=int, default=0, help="限制测试数量（0=全部）")
    parser.add_argument("--workers", type=int, default=0, help="并行进程数（0=自动）")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--topology", type=str, default="", help="仅测试指定拓扑")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 加载电路索引
    circuits = load_circuit_index()
    logger.info("索引: %d 个电路", len(circuits))

    # 过滤拓扑
    if args.topology:
        circuits = [c for c in circuits if c["topology"] == args.topology]
        logger.info("过滤拓扑 %s: %d 个电路", args.topology, len(circuits))

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

    results: dict[str, TestResult] = dict(completed)
    total = len(circuits)
    t_start = time.perf_counter()

    if n_workers == 1:
        # 串行模式（调试用）
        for i, entry in enumerate(circuits):
            result = test_single_circuit(entry)
            results[result.name] = result
            status = "OK" if result.success else "FAIL"
            drc = "Y" if result.drc_passed else "N"
            logger.info("[%4d/%d] %s | %s | drc=%s | loss=%.2f | %.2fs",
                        i + 1, total, result.name, status, drc,
                        result.total_loss_db, result.elapsed_sec)
            # 每 10 个保存一次进度
            if (i + 1) % 10 == 0:
                save_progress(results)
                elapsed = time.perf_counter() - t_start
                rate = (i + 1) / elapsed
                eta = (total - i - 1) / rate if rate > 0 else 0
                logger.info("进度: %d/%d (%.1f%%) | 速率: %.1f/s | ETA: %.0fs",
                            i + 1, total, 100 * (i + 1) / total, rate, eta)
    else:
        # 并行模式
        # R05 Bug 修复: worker 长时间运行后状态异常（forkserver + JAX 多进程死锁）
        # 根因: 4 worker 跑 1200 电路时，某 worker 处理 ~300 个后卡死（JAX/klayout
        # 在 forkserver 模式下多进程资源累积导致死锁）。
        # 修复: maxtasksperchild=30 让 worker 每处理 30 个电路后自动重启，
        #   释放 JAX/klayout 累积的资源；同时进度保存频率从 20 改为 5（减少崩溃丢失）。
        # 来源: Python multiprocessing.Pool maxtasksperchild 官方文档
        #   https://docs.python.org/3/library/multiprocessing.html#multiprocessing.pool.Pool
        # 回归测试: scripts/debug_stuck_circuits.py 单独跑 20 个卡住电路全部成功（0.3-2.7s）
        with Pool(n_workers, maxtasksperchild=30) as pool:
            for i, result in enumerate(pool.imap_unordered(test_single_circuit, circuits)):
                results[result.name] = result
                status = "OK" if result.success else "FAIL"
                drc = "Y" if result.drc_passed else "N"
                logger.info("[%4d/%d] %s | %s | drc=%s | loss=%.2f | %.2fs",
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

    logger.info("=" * 70)
    logger.info("批量测试完成")
    logger.info("  总数: %d", n_total)
    logger.info("  成功: %d (%.1f%%)", n_success, 100 * n_success / n_total if n_total else 0)
    logger.info("  DRC通过: %d (%.1f%%)", n_drc, 100 * n_drc / n_total if n_total else 0)
    logger.info("  总耗时: %.1fs", elapsed_total)
    logger.info("  结果: %s", RESULTS_FILE)
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
