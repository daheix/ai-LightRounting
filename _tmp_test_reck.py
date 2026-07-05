"""复现 Reck_8x8 / Spanke_8x8 DRC 失败."""
import sys
import json
from pathlib import Path

# 添加源码路径
MODULES = Path("/workspace/modules")
for sub in ("core", "place", "drc", "nn", "flow"):
    p = str(MODULES / sub / "src")
    if p not in sys.path:
        sys.path.insert(0, p)

from polaris_nn.data._other_formats import load_picbench
from polaris_flow.stage_serializers import _circuit_to_dict
from polaris_place import place_circuit
from polaris_drc import run_drc


def test_one(name: str):
    fp = Path(f"/workspace/data/benchmarks/picbench_{name}.json")
    if not fp.exists():
        print(f"[{name}] 文件不存在: {fp}")
        return
    spec = load_picbench(fp)
    circuit = _circuit_to_dict(spec)
    n_dev = len(circuit["devices"])
    n_conn = len(circuit["connections"])
    cw, ch = circuit["canvas_w"], circuit["canvas_h"]
    print(f"\n=== {name} ===")
    print(f"  devices={n_dev}, connections={n_conn}, canvas={cw}x{ch}")
    sizes = set((d["width_um"], d["height_um"]) for d in circuit["devices"])
    print(f"  device sizes: {sizes}")
    sample = circuit["devices"][0]
    print(f"  sample dev: {sample.get('name')} type={sample.get('device_type')} ports={sample.get('ports')}")
    try:
        result = place_circuit(circuit, mode="analytical")
        plac = result["placements"]
        xs = [(p["x"], p["y"], p["x"]+p["w"], p["y"]+p["h"]) for p in plac.values()]
        overlap = 0
        for i in range(len(xs)):
            for j in range(i+1, len(xs)):
                a, b = xs[i], xs[j]
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    overlap += 1
        oob = 0
        for nm, p in plac.items():
            if p["x"] < 0 or p["y"] < 0 or p["x"]+p["w"] > cw or p["y"]+p["h"] > ch:
                oob += 1
        print(f"  placements={len(plac)}, hpwl={result['hpwl']:.1f}, overlap={overlap}, oob={oob}")
    except Exception as e:
        print(f"  PLACE ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    try:
        drc = run_drc(circuit, plac)
        print(f"  DRC: violations={drc['n_violations']}, passed={drc['n_passed']}/{drc['n_rules']}, rate={drc['pass_rate']:.2f}")
        from collections import Counter
        cnt = Counter(v["rule_name"] for v in drc["violations"])
        for rule, c in cnt.most_common():
            print(f"    {rule}: {c}")
        for v in drc["violations"][:3]:
            print(f"    -> {v['rule_name']}: {v['message']}")
    except Exception as e:
        print(f"  DRC ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


for nm in ["Reck_4x4", "Reck_8x8", "Spanke_4x4", "Spanke_8x8", "Clements_4x4", "Clements_8x8"]:
    test_one(nm)
