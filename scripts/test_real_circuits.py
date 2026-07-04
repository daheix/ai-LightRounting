#!/usr/bin/env python3
"""真实板子数据集端到端测试（448 个真实用例）。

遍历 ``real_board/`` 全部 448 个真实用例，对每个可解析为光子电路
netlist 的用例执行 place→route→sim→drc→gds 端到端流水线，统计
成功率 / DRC 通过率 / 平均损耗 / 平均耗时，并按来源分组与失败根因分类。

数据集分布（参见 ``real_board/README.md`` 与 ``real_board/index.json``）:
- siepic/       229 GDS  → GDS 解析依赖 ``polaris.data.gds_loader``，
                            V5.0 拆包后该模块已下线，本脚本跳过并记录
                            （R03: 失败即记录，不伪造）
- gdsfactory/    89 yml/json netlist（.pic.yml/.yml/gf_*.json）
- picbench/      24 JSON netlist（data.netlist.instances/connections/ports）
- lidar/          9 JSON netlist（instances + nets 字典）
- align/         56 JSON（ALIGN CMOS 电子电路，非光子电路 → 格式不兼容）
- expert_demos/  10 JSON netlist（polaris CircuitSpec 原生格式）

引用（R02 学术诚信）:
- Chrostowski & Hochberg, Silicon Photonics Design, CUP 2015,
  ISBN 9781107016838 — 真实 SiEPIC 电路来源
  https://www.cambridge.org/9781107016838
- SiEPIC EBeam PDK (UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory: https://github.com/gdsfactory/gdsfactory (MIT)
- picbench: https://github.com/TiagoCavaco/picbench (MIT)
- ALIGN: https://github.com/ALIGN-analoglayout/ALIGN (BSD-3-Clause)
- ISPD 2025 LiDAR benchmark: https://github.com/ALIGN-analoglayout/ALIGN
- Soref et al. 1993 SOI 波导传播损耗 3 dB/cm
  https://ieeexplore.ieee.org/document/1148303
- Kahng & Lienig 2009 VLSI Placement HPWL
  https://ieeexplore.ieee.org/document/4685534

规则依据:
- R03 禁止 fall-back: 测试失败即记录根因，不伪造数据
- R05 Bug 必须修复: 真实板子测试发现 bug 即修复（本脚本仅测试，不修业务代码）
- R12 时间戳规范: 所有结果带时间戳

用法:
    python scripts/test_real_circuits.py                # 全量测试
    python scripts/test_real_circuits.py --limit 20     # 冒烟测试
    python scripts/test_real_circuits.py --workers 4    # 4 进程并行
    python scripts/test_real_circuits.py --resume       # 断点续跑
    python scripts/test_real_circuits.py --source picbench  # 仅测某来源
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from collections import defaultdict
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
logger = logging.getLogger("real_test")

REAL_BOARD_DIR = PROJECT_ROOT / "real_board"
OUTPUT_DIR = PROJECT_ROOT / "out" / "real_test"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"
RESULTS_FILE = OUTPUT_DIR / "results.json"
REPORT_FILE = OUTPUT_DIR / "report.md"

# 失败根因分类（R03: 失败即记录，不静默）
FAILURE_CATEGORIES = {
    "format_incompatible": "格式不兼容（ALIGN CMOS / siepic GDS 缺解析器）",
    "parse_failed": "解析失败（JSON/YAML 结构异常或字段缺失）",
    "spec_build_failed": "构建 CircuitSpec 失败（器件/连接结构非法）",
    "pipeline_failed": "流水线执行失败（place/route/drc/sim 任一 stage 异常）",
    "drc_failed": "DRC 检查未通过（存在设计规则违规）",
}


@dataclass
class RealTestResult:
    """单个真实用例测试结果。

    ``__test__ = False`` 防止 pytest 误收集（类名以 ``Test`` 开头）。
    """
    __test__ = False

    name: str
    source: str           # siepic/gdsfactory/picbench/lidar/align/expert_demos
    fmt: str              # gds/yml/json
    path: str
    n_devices: int
    n_connections: int
    success: bool
    drc_passed: bool
    total_loss_db: float
    n_crossings: int
    elapsed_sec: float
    failure_category: str = ""   # 空=成功，否则为 FAILURE_CATEGORIES 的 key
    error: str = ""


# ---------------------------------------------------------------------------
# 端口坐标推断（光子器件命名约定）
# ---------------------------------------------------------------------------

# 常见光子器件默认尺寸（μm），用于 picbench/lidar/gdsfactory 等仅给
# component type 的来源。来源: SiEPIC EBeam PDK / gdsfactory ubcpdk 默认尺寸。
# 关键词到 (width_um, height_um) 映射；未命中则用 10×10 通用值。
_COMPONENT_DEFAULT_SIZE: dict[str, tuple[float, float]] = {
    "mmi": (10.0, 10.0),
    "mmi1x2": (10.0, 10.0),
    "mmi2x2": (10.0, 10.0),
    "mzi": (40.0, 20.0),
    "mzi_ps": (40.0, 20.0),
    "mzi_ubcpdk": (40.0, 20.0),
    "ring": (20.0, 20.0),
    "ring_resonator": (20.0, 20.0),
    "y_branch": (15.0, 7.0),
    "y_1550": (15.0, 7.0),
    "gc": (15.0, 15.0),
    "gc_te1550": (15.0, 15.0),
    "grating_coupler_1d": (15.0, 15.0),
    "dc": (20.0, 5.0),
    "directional_coupler": (20.0, 5.0),
    "crossing": (10.0, 10.0),
    "heater": (20.0, 5.0),
    "straight_heat_metal": (10.0, 2.0),
    "phase_shifter": (10.0, 2.0),
    "taper": (10.0, 5.0),
    "bend_euler": (10.0, 10.0),
    "straight": (10.0, 2.0),
    "wg": (10.0, 2.0),
}


def _component_size(component: str) -> tuple[float, float]:
    """根据 component type 名推断默认尺寸（μm），未命中返回 10×10。

    Args:
        component: component type 名（如 ``mmi1x2``、``gc_te1550``）。

    Returns:
        (width_um, height_um)。
    """
    if not component:
        return (10.0, 10.0)
    key = component.lower()
    if key in _COMPONENT_DEFAULT_SIZE:
        return _COMPONENT_DEFAULT_SIZE[key]
    # 子串匹配（如 ``mmi_2x2_te1550`` 含 ``mmi``）
    for k, v in _COMPONENT_DEFAULT_SIZE.items():
        if k in key:
            return v
    return (10.0, 10.0)


def _port_direction(name: str) -> str:
    """根据端口名推断方向（光子电路命名约定）。

    - ``o*`` / ``out*`` → ``E``（东，输出）
    - ``i*`` / ``in*`` → ``W``（西，输入）
    - ``*n*`` 含 ``north`` → ``N``
    - ``*s*`` 含 ``south`` → ``S``
    - 数字索引（如 ``1``/``2``）：偶数 → W，奇数 → E
    - 其他 → ``E``

    来源: gdsfactory/SiEPIC 端口命名约定
      https://gdsfactory.github.io/gdsfactory/notebooks/name_ports.html
    """
    n = str(name).lower().strip()
    if n.startswith("o") or n.startswith("out"):
        return "E"
    if n.startswith("i") or n.startswith("in"):
        return "W"
    if "north" in n:
        return "N"
    if "south" in n:
        return "S"
    # pin1/pin2 / 纯数字 → 按索引分（W/E 交替）
    if n.isdigit():
        return "W" if int(n) % 2 == 1 else "E"
    return "E"


def make_default_ports(
    port_names: list[str], width_um: float, height_um: float,
) -> list[tuple[str, float, float, str]]:
    """为缺失端口坐标的器件生成默认端口列表。

    按方向（W/E/N/S）分组，同方向端口在器件对应边均匀分布。

    Args:
        port_names: 端口名列表（从 connections 收集）。
        width_um: 器件宽度。
        height_um: 器件高度。

    Returns:
        ``[(name, dx, dy, direction), ...]``，dx/dy 为相对器件左下角的偏移。
    """
    if not port_names:
        return []
    # 去重保序
    seen: set[str] = set()
    names: list[str] = []
    for n in port_names:
        if n not in seen:
            seen.add(n)
            names.append(n)

    by_dir: dict[str, list[str]] = defaultdict(list)
    for n in names:
        by_dir[_port_direction(n)].append(n)

    ports: list[tuple[str, float, float, str]] = []
    for direction, group in by_dir.items():
        m = len(group)
        for i, pname in enumerate(group):
            if direction == "W":
                dx, dy = 0.0, height_um * (i + 1) / (m + 1)
            elif direction == "E":
                dx, dy = width_um, height_um * (i + 1) / (m + 1)
            elif direction == "N":
                dx, dy = width_um * (i + 1) / (m + 1), height_um
            else:  # S
                dx, dy = width_um * (i + 1) / (m + 1), 0.0
            ports.append((pname, float(dx), float(dy), direction))
    return ports


# ---------------------------------------------------------------------------
# 各来源 netlist parser
# ---------------------------------------------------------------------------

def _split_port_ref(ref: str) -> tuple[str, str]:
    """拆分 ``"inst,port"`` 引用为 (instance, port)。

    Args:
        ref: 形如 ``"mzi1,o2"`` 的引用字符串。

    Returns:
        (instance_name, port_name)。

    Raises:
        ValueError: ref 不含逗号（R03 禁止 fall-back）。
    """
    if "," not in ref:
        raise ValueError(f"端口引用非法（缺少逗号分隔）: {ref!r}")
    inst, port = ref.split(",", 1)
    inst = inst.strip()
    port = port.strip()
    if not inst or not port:
        raise ValueError(f"端口引用非法（实例或端口为空）: {ref!r}")
    return inst, port


def parse_picbench(data: dict, name: str) -> dict:
    """解析 picbench JSON 为 polaris-core circuit dict。

    picbench 结构::
        data.netlist.instances: {name: "comp" | {component, settings}}
        data.netlist.connections: {"inst,port": "inst,port"}
        data.netlist.ports: {io_name: "inst,port"}  # 顶层 IO

    Args:
        data: picbench JSON 解析后的 dict。
        name: 用例名。

    Returns:
        polaris-core 风格 circuit dict。

    Raises:
        ValueError: 结构非法或字段缺失。
    """
    netlist = data.get("data", {}).get("netlist", {})
    if not netlist:
        raise ValueError("picbench 缺 data.netlist 字段")
    instances = netlist.get("instances", {})
    connections = netlist.get("connections", {})
    io_ports = netlist.get("ports", {})

    if not instances:
        raise ValueError("picbench 无 instances")

    # 收集每个 device 实际用到的端口名
    dev_ports: dict[str, list[str]] = defaultdict(list)
    edges: list[tuple[str, str, str, str]] = []
    for ref1, ref2 in connections.items():
        i1, p1 = _split_port_ref(ref1)
        i2, p2 = _split_port_ref(ref2)
        dev_ports[i1].append(p1)
        dev_ports[i2].append(p2)
        edges.append((i1, p1, i2, p2))
    # 顶层 IO ports（虚拟外部端口，不参与布线，仅记录）
    for io_name, ref in io_ports.items():
        try:
            inst, port = _split_port_ref(ref)
            dev_ports[inst].append(port)
        except ValueError:
            continue

    # 构建 device dict
    devices: list[dict] = []
    for inst_name, inst_def in instances.items():
        if isinstance(inst_def, str):
            component = inst_def
        elif isinstance(inst_def, dict):
            component = inst_def.get("component", "unknown")
        else:
            component = "unknown"
        w, h = _component_size(component)
        ports = make_default_ports(dev_ports.get(inst_name, []), w, h)
        devices.append({
            "name": inst_name,
            "device_type": component,
            "width_um": float(w),
            "height_um": float(h),
            "ports": [list(p) for p in ports],
            "params": {},
        })

    if not edges:
        raise ValueError("picbench 无 connections（无法布线）")

    return {
        "name": data.get("name", name),
        "devices": devices,
        "connections": [list(e) for e in edges],
        "canvas_w": 1000.0,
        "canvas_h": 1000.0,
        "process_node": "220nm SOI",
        "optical_wavelength_nm": 1550.0,
    }


def parse_lidar(data: dict, name: str) -> dict:
    """解析 lidar JSON 为 polaris-core circuit dict。

    lidar 结构::
        instances: {name: {component, settings}}
        nets: {net_name: ["inst,port", "inst,port", ...]}
        placements: {} (空，由 polaris-place 布局)

    每个 net 内的多个端口形成连接（取相邻对，避免 clique 重复边）。

    Args:
        data: lidar JSON 解析后的 dict。
        name: 用例名。

    Returns:
        polaris-core 风格 circuit dict。

    Raises:
        ValueError: 结构非法或字段缺失。
    """
    instances = data.get("instances", {})
    nets = data.get("nets", {})
    if not instances:
        raise ValueError("lidar 无 instances")
    if not nets:
        raise ValueError("lidar 无 nets")

    dev_ports: dict[str, list[str]] = defaultdict(list)
    edges: list[tuple[str, str, str, str]] = []
    for net_name, refs in nets.items():
        if not isinstance(refs, list) or len(refs) < 2:
            continue
        # 相邻端口连接（链式），避免 clique 产生 n*(n-1)/2 条边
        for i in range(len(refs) - 1):
            try:
                i1, p1 = _split_port_ref(refs[i])
                i2, p2 = _split_port_ref(refs[i + 1])
            except ValueError:
                continue
            dev_ports[i1].append(p1)
            dev_ports[i2].append(p2)
            edges.append((i1, p1, i2, p2))

    devices: list[dict] = []
    for inst_name, inst_def in instances.items():
        component = (
            inst_def.get("component", "unknown")
            if isinstance(inst_def, dict) else "unknown"
        )
        w, h = _component_size(component)
        ports = make_default_ports(dev_ports.get(inst_name, []), w, h)
        devices.append({
            "name": inst_name,
            "device_type": component,
            "width_um": float(w),
            "height_um": float(h),
            "ports": [list(p) for p in ports],
            "params": {},
        })

    if not edges:
        raise ValueError("lidar 无有效连接（nets 全为单端口或解析失败）")

    return {
        "name": data.get("name", name),
        "devices": devices,
        "connections": [list(e) for e in edges],
        "canvas_w": 1000.0,
        "canvas_h": 1000.0,
        "process_node": "220nm SOI",
        "optical_wavelength_nm": 1550.0,
    }


def parse_gdsfactory_json(data: dict, name: str) -> dict:
    """解析 gdsfactory ``gf_*.json`` 为 polaris-core circuit dict。

    gf_*.json 结构::
        instances: {name: {component, settings}}
        connections: [] (通常空)
        routes: {route_name: {links: {"inst,port": "inst,port"}}}
        placements: {name: {dx, dy, ...}}  # 已有布局（不用，polaris 重新布局）

    Args:
        data: gf_*.json 解析后的 dict。
        name: 用例名。

    Returns:
        polaris-core 风格 circuit dict。

    Raises:
        ValueError: 结构非法或字段缺失。
    """
    instances = data.get("instances", {})
    routes = data.get("routes", {})
    explicit_conns = data.get("connections", [])

    if not instances:
        raise ValueError("gdsfactory 无 instances")

    dev_ports: dict[str, list[str]] = defaultdict(list)
    edges: list[tuple[str, str, str, str]] = []
    # 显式 connections（list of [inst,port,inst,port] 或 dict）
    for c in explicit_conns:
        if isinstance(c, (list, tuple)) and len(c) == 4:
            i1, p1, i2, p2 = c
            dev_ports[i1].append(p1)
            dev_ports[i2].append(p2)
            edges.append((i1, p1, i2, p2))
    # routes.links（dict: "inst,port" → "inst,port"）
    for rname, rdef in routes.items():
        if not isinstance(rdef, dict):
            continue
        links = rdef.get("links", {})
        for ref1, ref2 in links.items():
            try:
                i1, p1 = _split_port_ref(ref1)
                i2, p2 = _split_port_ref(ref2)
            except ValueError:
                continue
            dev_ports[i1].append(p1)
            dev_ports[i2].append(p2)
            edges.append((i1, p1, i2, p2))

    devices: list[dict] = []
    for inst_name, inst_def in instances.items():
        component = (
            inst_def.get("component", "unknown")
            if isinstance(inst_def, dict) else "unknown"
        )
        w, h = _component_size(component)
        ports = make_default_ports(dev_ports.get(inst_name, []), w, h)
        devices.append({
            "name": inst_name,
            "device_type": component,
            "width_um": float(w),
            "height_um": float(h),
            "ports": [list(p) for p in ports],
            "params": {},
        })

    if not edges:
        raise ValueError("gdsfactory 无有效连接（routes.links 与 connections 均空）")

    return {
        "name": data.get("name", name),
        "devices": devices,
        "connections": [list(e) for e in edges],
        "canvas_w": 1000.0,
        "canvas_h": 1000.0,
        "process_node": "220nm SOI",
        "optical_wavelength_nm": 1550.0,
    }


def parse_gdsfactory_yml(text: str, name: str) -> dict:
    """解析 gdsfactory ``.pic.yml``/``.yml`` 为 polaris-core circuit dict。

    gdsfactory YAML 结构::
        instances: {name: {component, settings}}
        nets: [{p1: "inst,port", p2: "inst,port"}, ...]
        connections: [{p1, p2}] (旧版)
        routes: (新版用 nets 代替)

    Args:
        text: YAML 文本。
        name: 用例名。

    Returns:
        polaris-core 风格 circuit dict。

    Raises:
        ValueError: 结构非法或字段缺失。
        ImportError: PyYAML 未安装。
    """
    try:
        import yaml
    except ImportError as e:
        raise ImportError(f"解析 YAML 需要 PyYAML: {e}") from e
    data = yaml.safe_load(text) or {}

    instances = data.get("instances", {})
    nets = data.get("nets", [])
    connections = data.get("connections", [])
    routes = data.get("routes", {})

    if not instances:
        raise ValueError("gdsfactory yml 无 instances")

    dev_ports: dict[str, list[str]] = defaultdict(list)
    edges: list[tuple[str, str, str, str]] = []

    def _add_link(ref1: str, ref2: str) -> None:
        try:
            i1, p1 = _split_port_ref(ref1)
            i2, p2 = _split_port_ref(ref2)
        except ValueError:
            return
        dev_ports[i1].append(p1)
        dev_ports[i2].append(p2)
        edges.append((i1, p1, i2, p2))

    for net in nets:
        if isinstance(net, dict):
            p1 = net.get("p1")
            p2 = net.get("p2")
            if p1 and p2:
                _add_link(p1, p2)
    for conn in connections:
        if isinstance(conn, dict):
            p1 = conn.get("p1")
            p2 = conn.get("p2")
            if p1 and p2:
                _add_link(p1, p2)
    if isinstance(routes, dict):
        for rname, rdef in routes.items():
            if isinstance(rdef, dict):
                links = rdef.get("links", {})
                for ref1, ref2 in links.items():
                    _add_link(ref1, ref2)

    devices: list[dict] = []
    for inst_name, inst_def in instances.items():
        component = (
            inst_def.get("component", "unknown")
            if isinstance(inst_def, dict) else str(inst_def)
        )
        w, h = _component_size(component)
        ports = make_default_ports(dev_ports.get(inst_name, []), w, h)
        devices.append({
            "name": inst_name,
            "device_type": component,
            "width_um": float(w),
            "height_um": float(h),
            "ports": [list(p) for p in ports],
            "params": {},
        })

    if not edges:
        raise ValueError("gdsfactory yml 无有效连接")

    return {
        "name": name,
        "devices": devices,
        "connections": [list(e) for e in edges],
        "canvas_w": 1000.0,
        "canvas_h": 1000.0,
        "process_node": "220nm SOI",
        "optical_wavelength_nm": 1550.0,
    }


def parse_expert_demos(data: dict, name: str) -> dict:
    """解析 expert_demos netlist.json 为 polaris-core circuit dict。

    expert_demos netlist.json 已是 polaris CircuitSpec 兼容格式::
        name, canvas_w, canvas_h,
        devices: [{name, device_type, width_um, height_um, ports, params}],
        connections: [[dev1, port1, dev2, port2], ...]

    Args:
        data: netlist.json 解析后的 dict。
        name: 用例名。

    Returns:
        polaris-core 风格 circuit dict。

    Raises:
        ValueError: 结构非法或字段缺失。
    """
    devices = data.get("devices", [])
    connections = data.get("connections", [])
    if not devices:
        raise ValueError("expert_demos 无 devices")

    out_devices: list[dict] = []
    for d in devices:
        ports = [list(p) for p in d.get("ports", [])]
        out_devices.append({
            "name": d["name"],
            "device_type": d.get("device_type", "unknown"),
            "width_um": float(d.get("width_um", 10.0)),
            "height_um": float(d.get("height_um", 10.0)),
            "ports": ports,
            "params": dict(d.get("params", {})),
        })

    return {
        "name": data.get("name", name),
        "devices": out_devices,
        "connections": [list(c) for c in connections],
        "canvas_w": float(data.get("canvas_w", 1000.0)),
        "canvas_h": float(data.get("canvas_h", 1000.0)),
        "process_node": "220nm SOI",
        "optical_wavelength_nm": 1550.0,
    }


# ---------------------------------------------------------------------------
# 用例发现与解析分发
# ---------------------------------------------------------------------------

def discover_cases() -> list[dict]:
    """枚举 real_board 全部 448 个用例，返回测试入口列表。

    每个入口 dict: {name, source, fmt, path}。
    """
    cases: list[dict] = []

    # siepic GDS（229 个）— 直接列入，由 test_single 标记格式不兼容
    siepic_dir = REAL_BOARD_DIR / "siepic"
    if siepic_dir.is_dir():
        for f in sorted(siepic_dir.iterdir()):
            if f.suffix.lower() in (".gds", ".GDS".lower()) or f.name.lower().endswith(".gds"):
                cases.append({
                    "name": f"siepic__{f.stem}",
                    "source": "siepic",
                    "fmt": "gds",
                    "path": str(f),
                })

    # gdsfactory（89 个 yml/json）
    gf_dir = REAL_BOARD_DIR / "gdsfactory"
    if gf_dir.is_dir():
        for f in sorted(gf_dir.iterdir()):
            if f.suffix.lower() == ".yml":
                cases.append({
                    "name": f"gdsfactory__{f.stem}",
                    "source": "gdsfactory",
                    "fmt": "yml",
                    "path": str(f),
                })
            elif f.suffix.lower() == ".json" and f.name.startswith("gf_"):
                cases.append({
                    "name": f"gdsfactory__{f.stem}",
                    "source": "gdsfactory",
                    "fmt": "json",
                    "path": str(f),
                })

    # picbench（24 个）
    pb_dir = REAL_BOARD_DIR / "picbench"
    if pb_dir.is_dir():
        for f in sorted(pb_dir.iterdir()):
            if f.suffix.lower() == ".json":
                cases.append({
                    "name": f"picbench__{f.stem}",
                    "source": "picbench",
                    "fmt": "json",
                    "path": str(f),
                })

    # lidar（9 个）
    ld_dir = REAL_BOARD_DIR / "lidar"
    if ld_dir.is_dir():
        for f in sorted(ld_dir.iterdir()):
            if f.suffix.lower() == ".json":
                cases.append({
                    "name": f"lidar__{f.stem}",
                    "source": "lidar",
                    "fmt": "json",
                    "path": str(f),
                })

    # align（56 个）
    al_dir = REAL_BOARD_DIR / "align"
    if al_dir.is_dir():
        for f in sorted(al_dir.iterdir()):
            if f.suffix.lower() == ".json":
                cases.append({
                    "name": f"align__{f.stem}",
                    "source": "align",
                    "fmt": "json",
                    "path": str(f),
                })

    # expert_demos（10 个目录，每个含 netlist.json）
    ed_dir = REAL_BOARD_DIR / "expert_demos"
    if ed_dir.is_dir():
        for d in sorted(ed_dir.iterdir()):
            if d.is_dir():
                nl = d / "netlist.json"
                if nl.exists():
                    cases.append({
                        "name": f"expert_demos__{d.name}",
                        "source": "expert_demos",
                        "fmt": "json",
                        "path": str(nl),
                    })

    return cases


def load_circuit_dict(entry: dict) -> dict:
    """根据 source/fmt 调用对应 parser，返回 polaris-core circuit dict。

    Raises:
        ValueError: 解析失败（结构非法）。
        ImportError: 依赖缺失。
    """
    source = entry["source"]
    fmt = entry["fmt"]
    path = Path(entry["path"])

    if source == "siepic":
        # GDS 解析依赖 polaris.data.gds_loader（V5.0 拆包后已下线）
        # R03: 不 fall-back，直接 raise 让上层标记格式不兼容
        raise ValueError(
            "siepic GDS 解析依赖 polaris.data.gds_loader，"
            "V5.0 拆包后该模块已下线（klayout 直接 netlist 提取需 SiEPIC 专用 "
            "NetlistExtractor，超出本测试范围）"
        )

    if source == "align":
        # ALIGN 是 CMOS 电子电路 EDA，与 PoLaRIS 光子电路模型不兼容
        # （器件为 NMOS/PMOS/RES/CAP，连接为电信号网，非光波导）
        raise ValueError(
            "ALIGN 是 CMOS 电子电路格式（NMOS/PMOS/RES/CAP + 电网络），"
            "与 PoLaRIS 光子电路模型（mmi/y_branch/gc/wg + 光波导连接）不兼容"
        )

    if source == "expert_demos":
        data = json.loads(path.read_text(encoding="utf-8"))
        return parse_expert_demos(data, entry["name"])

    if source == "picbench":
        data = json.loads(path.read_text(encoding="utf-8"))
        return parse_picbench(data, entry["name"])

    if source == "lidar":
        data = json.loads(path.read_text(encoding="utf-8"))
        return parse_lidar(data, entry["name"])

    if source == "gdsfactory":
        if fmt == "yml":
            text = path.read_text(encoding="utf-8")
            return parse_gdsfactory_yml(text, entry["name"])
        elif fmt == "json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return parse_gdsfactory_json(data, entry["name"])

    raise ValueError(f"未知来源/格式: {source}/{fmt}")


# ---------------------------------------------------------------------------
# 端到端测试
# ---------------------------------------------------------------------------

def test_single_case(entry: dict) -> RealTestResult:
    """测试单个真实用例（工作进程函数）。

    流程:
        1. 解析 netlist → polaris-core circuit dict
        2. 调用 run_eda_flow 执行 place→route→sim→drc→gds
        3. 提取 success/drc_passed/total_loss_db/n_crossings/elapsed

    失败根因分类（R03: 失败即记录）:
        - format_incompatible: siepic GDS / align CMOS
        - parse_failed: JSON/YAML 解析异常
        - spec_build_failed: parser 抛 ValueError
        - pipeline_failed: run_eda_flow 任一关键 stage 失败
        - drc_failed: 流水线成功但 DRC 有违规
    """
    name = entry["name"]
    source = entry["source"]
    fmt = entry["fmt"]
    path = entry["path"]

    # 1) 解析阶段
    try:
        circuit_dict = load_circuit_dict(entry)
    except ValueError as e:
        # 区分格式不兼容 vs 解析失败
        msg = str(e)
        if "不兼容" in msg or "下线" in msg:
            cat = "format_incompatible"
        else:
            cat = "parse_failed" if "结构" in msg or "字段" in msg or "无效" in msg else "spec_build_failed"
        return RealTestResult(
            name=name, source=source, fmt=fmt, path=path,
            n_devices=0, n_connections=0, success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, elapsed_sec=0.0,
            failure_category=cat, error=msg,
        )
    except Exception as e:
        return RealTestResult(
            name=name, source=source, fmt=fmt, path=path,
            n_devices=0, n_connections=0, success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, elapsed_sec=0.0,
            failure_category="parse_failed",
            error=f"{type(e).__name__}: {e}",
        )

    n_devices = len(circuit_dict.get("devices", []))
    n_connections = len(circuit_dict.get("connections", []))

    # 2) 执行端到端流水线
    t0 = time.perf_counter()
    try:
        from polaris_orchestrator.flow import run_eda_flow

        # 输出到 /tmp（减少磁盘 I/O）
        iter_output = Path("/tmp/polaris_real_test") / name
        iter_output.mkdir(parents=True, exist_ok=True)

        # 跳过 stage 8（逆向设计）和 stage 9（量子验证），与 batch_test 一致
        flow_result = run_eda_flow(
            circuit=circuit_dict,
            output_dir=str(iter_output),
            skip_stages=[8, 9],
            strict=False,
        )
        elapsed = time.perf_counter() - t0

        # 从 stages 提取指标（R03: stage 失败时 result 缺失，记为失败）
        stages = {s["stage_id"]: s for s in flow_result["stages"]}
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
        # DRC 通过 = 无违规；stage 失败时 drc_res 为空 → False
        drc_passed = bool(drc_res) and drc_res.get("n_violations", -1) == 0
        total_loss_db = float(route_res.get("total_loss_db", 0.0)) if route_res else 0.0
        n_crossings = int(route_res.get("n_crossings", 0)) if route_res else 0

        # 失败分类
        failure_category = ""
        error_msg = ""
        if not success:
            # 流水线 stage 失败
            failed_stages = [
                f"stage{s['stage_id']}({s['name']}): {s.get('error') or s['status']}"
                for s in flow_result["stages"]
                if s["status"] not in ("success", "skipped")
            ]
            error_msg = "; ".join(failed_stages) if failed_stages else "未知失败"
            failure_category = "pipeline_failed"
        elif not drc_passed:
            # 流水线成功但 DRC 有违规
            n_violations = drc_res.get("n_violations", -1)
            error_msg = f"DRC 违规 {n_violations} 处"
            failure_category = "drc_failed"

        return RealTestResult(
            name=name, source=source, fmt=fmt, path=path,
            n_devices=n_devices, n_connections=n_connections,
            success=success, drc_passed=drc_passed,
            total_loss_db=total_loss_db, n_crossings=n_crossings,
            elapsed_sec=elapsed,
            failure_category=failure_category, error=error_msg,
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        tb = traceback.format_exc()
        return RealTestResult(
            name=name, source=source, fmt=fmt, path=path,
            n_devices=n_devices, n_connections=n_connections,
            success=False, drc_passed=False,
            total_loss_db=0.0, n_crossings=0, elapsed_sec=elapsed,
            failure_category="pipeline_failed",
            error=f"{type(e).__name__}: {e}\n{tb[-400:]}",
        )


# 禁止 pytest 收集
test_single_case.__test__ = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 进度持久化
# ---------------------------------------------------------------------------

def load_completed() -> dict[str, RealTestResult]:
    """加载已完成结果（断点续跑）。"""
    if not PROGRESS_FILE.exists():
        return {}
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return {r["name"]: RealTestResult(**r) for r in data.get("results", [])}
    except Exception:
        return {}


def save_progress(results: dict[str, RealTestResult]) -> None:
    """保存进度（覆盖写）。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "total": len(results),
        "updated": datetime.now().isoformat(),
        "results": [asdict(r) for r in results.values()],
    }
    PROGRESS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------

def render_report(
    results: list[RealTestResult],
    total_cases: int,
    elapsed_total: float,
) -> str:
    """生成 Markdown 报告。"""
    n_total = len(results)
    n_success = sum(1 for r in results if r.success)
    n_drc = sum(1 for r in results if r.drc_passed)
    # 仅对成功的用例计算平均损耗/耗时
    successful = [r for r in results if r.success]
    avg_loss = (
        sum(r.total_loss_db for r in successful) / len(successful)
        if successful else 0.0
    )
    avg_elapsed = (
        sum(r.elapsed_sec for r in successful) / len(successful)
        if successful else 0.0
    )

    # 按来源分组
    by_source: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "success": 0, "drc": 0, "loss_sum": 0.0,
                 "elapsed_sum": 0.0}
    )
    for r in results:
        s = by_source[r.source]
        s["total"] += 1
        if r.success:
            s["success"] += 1
            s["loss_sum"] += r.total_loss_db
            s["elapsed_sum"] += r.elapsed_sec
        if r.drc_passed:
            s["drc"] += 1

    # 失败根因分类
    by_cat: dict[str, int] = defaultdict(int)
    for r in results:
        if not r.success:
            by_cat[r.failure_category] += 1

    # 与程序化 1200 电路对比
    # 来源: out/batch_test/progress.json (total=1200, success=1200, drc=1152)
    batch_total = 1200
    batch_success = 1200
    batch_drc = 1152
    batch_success_rate = 100.0 * batch_success / batch_total
    batch_drc_rate = 100.0 * batch_drc / batch_total

    real_success_rate = 100.0 * n_success / n_total if n_total else 0.0
    real_drc_rate = 100.0 * n_drc / n_total if n_total else 0.0

    lines: list[str] = []
    lines.append("# PoLaRIS 真实板子数据集端到端测试报告")
    lines.append("")
    lines.append(f"- 生成时间: {datetime.now().isoformat()}")
    lines.append(f"- 数据集总数: {total_cases} 个真实用例")
    lines.append(f"- 实际测试数: {n_total} 个")
    lines.append(f"- 总耗时: {elapsed_total:.1f}s")
    lines.append("")
    lines.append("## 1. 总体指标")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 总用例数 | {n_total} |")
    lines.append(f"| 成功数 | {n_success} |")
    lines.append(f"| 成功率 | {real_success_rate:.1f}% |")
    lines.append(f"| DRC 通过数 | {n_drc} |")
    lines.append(f"| DRC 通过率 | {real_drc_rate:.1f}% |")
    lines.append(f"| 平均损耗（成功用例）| {avg_loss:.3f} dB |")
    lines.append(f"| 平均耗时（成功用例）| {avg_elapsed:.3f} s |")
    lines.append("")
    lines.append("## 2. 按来源分组")
    lines.append("")
    lines.append("| 来源 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 | 平均损耗(dB) | 平均耗时(s) |")
    lines.append("|------|------|------|--------|---------|-------|--------------|-------------|")
    for src in sorted(by_source.keys()):
        s = by_source[src]
        sr = 100.0 * s["success"] / s["total"] if s["total"] else 0.0
        dr = 100.0 * s["drc"] / s["total"] if s["total"] else 0.0
        avg_l = s["loss_sum"] / s["success"] if s["success"] else 0.0
        avg_e = s["elapsed_sum"] / s["success"] if s["success"] else 0.0
        lines.append(
            f"| {src} | {s['total']} | {s['success']} | {sr:.1f}% | "
            f"{s['drc']} | {dr:.1f}% | {avg_l:.3f} | {avg_e:.3f} |"
        )
    lines.append("")
    lines.append("## 3. 失败根因分类")
    lines.append("")
    lines.append("| 根因 | 数量 | 说明 |")
    lines.append("|------|------|------|")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        desc = FAILURE_CATEGORIES.get(cat, cat)
        lines.append(f"| {cat} | {n} | {desc} |")
    lines.append("")
    lines.append("## 4. 与程序化 1200 电路对比")
    lines.append("")
    lines.append("| 测试集 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 |")
    lines.append("|--------|------|------|--------|---------|-------|")
    lines.append(
        f"| 程序化生成（batch_test_1000）| {batch_total} | {batch_success} | "
        f"{batch_success_rate:.1f}% | {batch_drc} | {batch_drc_rate:.1f}% |"
    )
    lines.append(
        f"| 真实板子（real_board）| {n_total} | {n_success} | "
        f"{real_success_rate:.1f}% | {n_drc} | {real_drc_rate:.1f}% |"
    )
    lines.append("")
    # 排除格式不兼容后的真实可测试用例成功率
    n_testable = sum(1 for r in results if r.failure_category != "format_incompatible")
    n_testable_success = sum(
        1 for r in results if r.success and r.failure_category != "format_incompatible"
    )
    testable_rate = 100.0 * n_testable_success / n_testable if n_testable else 0.0
    lines.append(
        f"- 排除格式不兼容后（{n_testable} 个可测试用例）成功率: "
        f"{testable_rate:.1f}%"
    )
    lines.append("")
    lines.append("## 5. 关键发现")
    lines.append("")
    if n_testable > 0:
        lines.append(
            f"- 真实 netlist 用例（{n_testable} 个可测试）端到端成功率 "
            f"{testable_rate:.1f}%，对比程序化 {batch_success_rate:.1f}%"
        )
    if by_cat.get("format_incompatible", 0) > 0:
        lines.append(
            f"- 格式不兼容 {by_cat['format_incompatible']} 个：siepic GDS（229）+ "
            f"align CMOS（部分），反映 PoLaRIS 当前不支持 GDS 直接解析与电子电路格式"
        )
    if by_cat.get("pipeline_failed", 0) > 0:
        lines.append(
            f"- 流水线失败 {by_cat['pipeline_failed']} 个：真实电路端口结构多样，"
            f"默认端口坐标推断可能与实际版图偏差，导致布线 stage 异常"
        )
    if by_cat.get("drc_failed", 0) > 0:
        lines.append(
            f"- DRC 失败 {by_cat['drc_failed']} 个：默认布局参数对真实电路可能产生"
            f"最小间距/最小宽度违规"
        )
    lines.append("")
    lines.append("## 6. 规则依据")
    lines.append("")
    lines.append("- R03 禁止 fall-back: 测试失败即记录根因，不伪造数据")
    lines.append("- R05 Bug 必须修复: 真实板子测试发现的 bug 后续单独修复")
    lines.append("- R02 学术诚信: 所有数据来源可溯源（SiEPIC/gdsfactory/picbench/ALIGN）")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(description="真实板子数据集端到端测试")
    parser.add_argument("--limit", type=int, default=0, help="限制测试数量（0=全部）")
    parser.add_argument("--workers", type=int, default=0, help="并行进程数（0=自动）")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--source", type=str, default="",
                        help="仅测试指定来源（siepic/gdsfactory/picbench/lidar/align/expert_demos）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 枚举全部用例
    all_cases = discover_cases()
    total_dataset = len(all_cases)
    logger.info("数据集总数: %d 个用例", total_dataset)

    # 按来源过滤
    cases = all_cases
    if args.source:
        cases = [c for c in all_cases if c["source"] == args.source]
        logger.info("过滤来源 %s: %d 个用例", args.source, len(cases))

    # 限制数量
    if args.limit > 0:
        cases = cases[:args.limit]
        logger.info("限制: %d 个用例", len(cases))

    # 断点续跑
    completed = load_completed() if args.resume else {}
    if completed:
        logger.info("已完成: %d 个用例（断点续跑）", len(completed))
        cases = [c for c in cases if c["name"] not in completed]

    if not cases:
        logger.info("无待测试用例")
        # 仍生成报告
        results = list(completed.values())
        render_and_save(results, total_dataset, 0.0)
        return 0

    logger.info("待测试: %d 个用例", len(cases))

    # 并行测试
    n_workers = args.workers if args.workers > 0 else min(cpu_count(), 4)
    logger.info("并行进程: %d", n_workers)

    results: dict[str, RealTestResult] = dict(completed)
    total = len(cases)
    t_start = time.perf_counter()

    if n_workers == 1:
        for i, entry in enumerate(cases):
            result = test_single_case(entry)
            results[result.name] = result
            status = "OK" if result.success else "FAIL"
            drc = "Y" if result.drc_passed else "N"
            logger.info(
                "[%4d/%d] %s | %s | drc=%s | loss=%.2f | %.2fs | %s",
                i + 1, total, result.name, status, drc,
                result.total_loss_db, result.elapsed_sec,
                result.failure_category or "",
            )
            if (i + 1) % 10 == 0:
                save_progress(results)
                elapsed = time.perf_counter() - t_start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (total - i - 1) / rate if rate > 0 else 0
                logger.info(
                    "进度: %d/%d (%.1f%%) | 速率: %.1f/s | ETA: %.0fs",
                    i + 1, total, 100 * (i + 1) / total, rate, eta,
                )
    else:
        # R05: maxtasksperchild=30 防 worker 长时间运行后资源累积
        with Pool(n_workers, maxtasksperchild=30) as pool:
            for i, result in enumerate(pool.imap_unordered(test_single_case, cases)):
                results[result.name] = result
                status = "OK" if result.success else "FAIL"
                drc = "Y" if result.drc_passed else "N"
                logger.info(
                    "[%4d/%d] %s | %s | drc=%s | loss=%.2f | %.2fs | %s",
                    i + 1, total, result.name, status, drc,
                    result.total_loss_db, result.elapsed_sec,
                    result.failure_category or "",
                )
                if (i + 1) % 5 == 0:
                    save_progress(results)
                    elapsed = time.perf_counter() - t_start
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    eta = (total - i - 1) / rate if rate > 0 else 0
                    logger.info(
                        "进度: %d/%d (%.1f%%) | 速率: %.1f/s | ETA: %.0fs",
                        i + 1, total, 100 * (i + 1) / total, rate, eta,
                    )

    # 保存最终结果
    save_progress(results)
    final_data = {
        "total": len(results),
        "updated": datetime.now().isoformat(),
        "results": [asdict(r) for r in results.values()],
    }
    RESULTS_FILE.write_text(
        json.dumps(final_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    elapsed_total = time.perf_counter() - t_start
    render_and_save(list(results.values()), total_dataset, elapsed_total)

    # 汇总
    n_success = sum(1 for r in results.values() if r.success)
    n_drc = sum(1 for r in results.values() if r.drc_passed)
    n_total = len(results)
    logger.info("=" * 70)
    logger.info("真实板子测试完成")
    logger.info("  数据集总数: %d", total_dataset)
    logger.info("  实际测试: %d", n_total)
    logger.info("  成功: %d (%.1f%%)", n_success,
                100 * n_success / n_total if n_total else 0)
    logger.info("  DRC通过: %d (%.1f%%)", n_drc,
                100 * n_drc / n_total if n_total else 0)
    logger.info("  总耗时: %.1fs", elapsed_total)
    logger.info("  进度: %s", PROGRESS_FILE)
    logger.info("  报告: %s", REPORT_FILE)
    logger.info("=" * 70)
    return 0


def render_and_save(
    results: list[RealTestResult], total_dataset: int, elapsed_total: float,
) -> None:
    """渲染报告并保存。"""
    report = render_report(results, total_dataset, elapsed_total)
    REPORT_FILE.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
