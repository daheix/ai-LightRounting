"""诊断 Reck_8x8 布局结构."""
import sys
from pathlib import Path

MODULES = Path("/workspace/modules")
for sub in ("core", "place", "drc", "nn", "flow"):
    p = str(MODULES / sub / "src")
    if p not in sys.path:
        sys.path.insert(0, p)

from polaris_nn.data._other_formats import load_picbench
from polaris_flow.stage_serializers import _circuit_to_dict
from polaris_place import place_circuit
from polaris_drc import run_drc

spec = load_picbench("/workspace/data/benchmarks/picbench_Reck_8x8.json")
circuit = _circuit_to_dict(spec)
result = place_circuit(circuit, mode="analytical")
plac = result["placements"]

# 按拓扑深度排序输出布局
from polaris_place.analytical import _topological_depth
names = list(plac.keys())
name_to_idx = {nm: i for i, nm in enumerate(names)}
idx_conns = []
for conn in circuit["connections"]:
    d1, _, d2, _ = conn
    if d1 in name_to_idx and d2 in name_to_idx:
        idx_conns.append((name_to_idx[d1], name_to_idx[d2]))
depth = _topological_depth(len(names), idx_conns)

# 按 y 坐标分行显示
print("布局（按 y 分行）:")
rows = {}
for nm, p in plac.items():
    y_round = round(p["y"] / 60) * 60  # 按 60μm 分行
    rows.setdefault(y_round, []).append((nm, p, depth[name_to_idx[nm]]))
for y in sorted(rows.keys()):
    print(f"  行 y={y}:")
    for nm, p, d in sorted(rows[y], key=lambda x: x[1]["x"]):
        print(f"    {nm}: x={p['x']:.0f} y={p['y']:.0f} w={p['w']:.0f} h={p['h']:.0f} depth={d}")

# 分析违规连接的器件对
drc = run_drc(circuit, plac)
print(f"\n违规连接分析 ({drc['n_violations']} 个):")
dev_map = {d["name"]: d for d in circuit["devices"]}
for v in drc["violations"][:5]:
    msg = v["message"]
    # 解析连接名
    import re
    m = re.search(r"连接 (\S+)", msg)
    if m:
        conn_str = m.group(1)
        # 找到连接的器件对
        for conn in circuit["connections"]:
            d1, p1, d2, p2 = conn
            if f"{d1}.{p1}" in conn_str and f"{d2}.{p2}" in conn_str:
                p1info = plac[d1]
                p2info = plac[d2]
                print(f"  {conn_str}:")
                print(f"    {d1}: x={p1info['x']:.0f} y={p1info['y']:.0f} (depth={depth[name_to_idx[d1]]})")
                print(f"    {d2}: x={p2info['x']:.0f} y={p2info['y']:.0f} (depth={depth[name_to_idx[d2]]})")
                # 端口绝对坐标
                dev1 = dev_map[d1]
                dev2 = dev_map[d2]
                for port in dev1.get("ports", []):
                    if port[0] == p1:
                        abs1x = p1info["x"] + port[1]
                        abs1y = p1info["y"] + port[2]
                        print(f"    {d1}.{p1} abs=({abs1x:.0f},{abs1y:.0f}) dir={port[3]}")
                for port in dev2.get("ports", []):
                    if port[0] == p2:
                        abs2x = p2info["x"] + port[1]
                        abs2y = p2info["y"] + port[2]
                        print(f"    {d2}.{p2} abs=({abs2x:.0f},{abs2y:.0f}) dir={port[3]}")
                break

# 画布利用率
total_area = sum(p["w"] * p["h"] for p in plac.values())
canvas_area = circuit["canvas_w"] * circuit["canvas_h"]
print(f"\n画布: {circuit['canvas_w']}x{circuit['canvas_h']}μm, 利用率={total_area/canvas_area*100:.2f}%")
print(f"器件总面积: {total_area:.0f}μm², 画布面积: {canvas_area:.0f}μm²")
