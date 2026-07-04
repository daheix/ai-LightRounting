#!/usr/bin/env python3
"""调试卡住的电路 - 串行跑未完成的 20 个电路，每个 stage 单独计时 + 超时。

定位 batch_test 卡死的根因（哪个 stage 在大规模电路上死循环）。
"""
from __future__ import annotations

import json
import signal
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GENERATED_DIR = PROJECT_ROOT / "data" / "benchmarks" / "generated"
PROGRESS_FILE = PROJECT_ROOT / "out" / "batch_test" / "progress.json"


class TimeoutError_(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError_("stage 超时")


def run_one_with_stage_timing(name: str, timeout: int = 60) -> dict:
    """单电路 + stage 级别计时 + 总超时。"""
    # 找电路文件
    idx = json.loads((GENERATED_DIR / "index.json").read_text(encoding="utf-8"))
    entry = next(c for c in idx["circuits"] if c["name"] == name)
    circuit_data = json.loads((GENERATED_DIR / entry["path"]).read_text(encoding="utf-8"))

    from polaris_core.specs import CircuitSpec, DeviceSpec
    from polaris_core import circuit_to_dict
    from polaris_orchestrator import flow as flow_mod

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
    circuit_dict = circuit_to_dict(spec)

    import tempfile
    out_dir = tempfile.mkdtemp(prefix=f"debug_{name}_")

    # stage 级别计时
    skip_set = {8, 9}
    ctx = {"output_dir": out_dir, "placements": None, "hpwl": None}
    stage_times = {}
    signal.signal(signal.SIGALRM, _timeout_handler)
    for stage_id, st_name, stage_fn in flow_mod._STAGE_LIST:
        if stage_id in skip_set:
            continue
        t0 = time.perf_counter()
        signal.alarm(timeout)
        try:
            result = stage_fn(circuit_dict, ctx)
            elapsed = time.perf_counter() - t0
            stage_times[st_name] = f"OK ({elapsed:.2f}s)"
            if stage_id == 3:
                ctx["placements"] = result["placements"]
                ctx["hpwl"] = result["hpwl"]
        except TimeoutError_ as e:
            signal.alarm(0)
            stage_times[st_name] = f"TIMEOUT ({timeout}s)"
            return {"name": name, "ok": False, "stages": stage_times, "error": f"{st_name} 超时"}
        except Exception as e:
            signal.alarm(0)
            elapsed = time.perf_counter() - t0
            stage_times[st_name] = f"FAIL ({elapsed:.2f}s): {type(e).__name__}: {str(e)[:80]}"
            return {"name": name, "ok": False, "stages": stage_times, "error": f"{st_name}: {e}"}
        signal.alarm(0)
    return {"name": name, "ok": True, "stages": stage_times}


def main():
    # 找未完成的 20 个电路
    prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    done = {r["name"] for r in prog.get("results", [])}
    idx = json.loads((GENERATED_DIR / "index.json").read_text(encoding="utf-8"))
    undone = [c["name"] for c in idx["circuits"] if c["name"] not in done]
    print(f"未完成: {len(undone)} 个电路")
    for name in undone:
        print(f"\n=== {name} ===")
        t0 = time.perf_counter()
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(90)
            r = run_one_with_stage_timing(name, timeout=30)
            signal.alarm(0)
            print(f"  结果: ok={r['ok']} 耗时={time.perf_counter()-t0:.1f}s")
            for s, v in r["stages"].items():
                print(f"    {s}: {v}")
            if not r["ok"]:
                print(f"  错误: {r['error'][:120]}")
        except Exception as e:
            signal.alarm(0)
            print(f"  外层超时/异常: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
