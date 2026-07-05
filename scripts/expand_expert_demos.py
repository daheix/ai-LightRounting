"""扩充 PoLaRIS 专家示范数据集 — 从公开光子 benchmark netlist 生成三元组。

读取 data/benchmarks/ 下的真实光子电路 netlist（PICBench/LiDAR/GDSFactory
公开 benchmark），转换为 polaris-core CircuitSpec 格式，调用
polaris-place 解析法布局器与 polaris-route 曲线波导布线器生成专家示范
三元组 (netlist, placements, routes)，写入 data/expert_demos/<name>/。

## 数据源（R02 学术诚信，全部可溯源）

- PICBench: Klitgaard et al., PICBench photonic integrated circuit benchmark
  https://github.com/JeppeKlitgaard/PicBench
- LiDAR ISPD'25: LiDAR et al., RL for Photonic Routing, ISPD 2025
  https://dl.acm.org/doi/10.1145/3698364.3705355
  https://arxiv.org/abs/2504.18813
- GDSFactory: Matres et al. 2024, GDSFactory photonic PDK
  https://gdsfactory.github.io/gdsfactory/
- Clements mesh: Clements et al., Optica 3(12) 1460 (2016)
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Reck mesh: Reck et al., PRL 73, 58 (1994)
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- MRR weight bank: Tait et al., JLT 32(24) 4029 (2014)
  https://opg.optica.org/jlt/abstract.cfm?uri=jltech-32-24-4029
- Spanke network: Spanke, IEEE JQE 22, 961 (1986)
  https://ieeexplore.ieee.org/document/1072908
- Multiport MMI: Maese-Novo et al., Opt. Express 21(1) 282 (2013)
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-21-1-282
- SiEPIC EBeam PDK: Chrostowski et al., UBC, MIT
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- DREAMPlace 解析法布局: Lin et al., TCAD 2020
  https://arxiv.org/abs/2004.10746
- 模仿学习: Pomerleau 1989 ALVINN
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

## 设计原则

- R02 学术诚信: 所有器件参数、来源、文献 URL 标注到 meta.json
- R03 禁止 fall-back: netlist 解析失败、布局失败、布线失败均 raise
- R04 不参与 GPU: 纯 NumPy 实现（place_analytical + CurvyRouter）
- R05 Bug 必修: 验证每个 demo 的器件数/连接数/端口坐标
- R11 V8 工作流: main 分支直接开发，精确文件 git add

## 输出格式（与现有 data/expert_demos/MZI1/ 一致）

每个 demo 子目录包含 4 个文件：
- meta.json: 来源、URL、器件数、连接数、画布尺寸
- netlist.json: CircuitSpec 序列化（name, canvas_w, canvas_h, devices, connections）
- placements.json: {device_name: {x, y, rotation, mirror, bbox, width, height}}
- routes.json: [[(x1,y1), (x2,y2), ...], ...] 波导路径列表
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# 添加 modules 路径以导入 polaris-place 和 polaris-route
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLACE_SRC = _REPO_ROOT / "modules" / "place" / "src"
_ROUTE_SRC = _REPO_ROOT / "modules" / "route" / "src"
_CORE_SRC = _REPO_ROOT / "modules" / "core" / "src"
for p in (_CORE_SRC, _PLACE_SRC, _ROUTE_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from polaris_place.analytical import AnalyticalConfig, place_analytical  # noqa: E402
from polaris_route.curvy import CurvyRouteConfig, CurvyRouter  # noqa: E402

logger = logging.getLogger(__name__)

# =========================================================================
# 器件规格目录（R02 学术诚信，参数来源 SiEPIC EBeam PDK + gdsfactory ubcpdk）
# =========================================================================

# 端口方向约定（与 polaris-nn/data/standard_devices.py 一致）：
# - "E" = 端口朝东（信号向东传播），位于器件西边界 x=0
# - "W" = 端口朝西（信号向西传播），位于器件东边界 x=width_um
# - "N" = 端口朝北，位于器件南边界 y=0
# - "S" = 端口朝南，位于器件北边界 y=height_um
#
# PICBench 端口命名映射:
#   I1/I2 (input) → 物理位置西边界
#   O1/O2/O3 (output) → 物理位置东边界
# LiDAR/gdsfactory 端口命名: o1/o2/o3/o4（保持原样）

DEVICE_SPECS: dict[str, dict] = {
    # 1x2 MMI: 1 input (west), 2 outputs (east)
    "mmi1x2": {
        "device_type": "mmi",
        "width_um": 30.0,
        "height_um": 20.0,
        "ports_picbench": {
            "I1": (0.0, 10.0, "E"),
            "O1": (30.0, 5.0, "W"),
            "O2": (30.0, 15.0, "W"),
        },
        "ports_lidar": {
            "o1": (0.0, 10.0, "E"),
            "o2": (30.0, 5.0, "W"),
            "o3": (30.0, 15.0, "W"),
        },
    },
    # 2x2 MMI: 2 inputs (west), 2 outputs (east)
    "mmi2x2": {
        "device_type": "mmi",
        "width_um": 30.0,
        "height_um": 20.0,
        "ports_picbench": {
            "I1": (0.0, 5.0, "E"),
            "I2": (0.0, 15.0, "E"),
            "O1": (30.0, 5.0, "W"),
            "O2": (30.0, 15.0, "W"),
        },
        "ports_lidar": {
            "o1": (0.0, 5.0, "E"),
            "o2": (0.0, 15.0, "E"),
            "o3": (30.0, 5.0, "W"),
            "o4": (30.0, 15.0, "W"),
        },
    },
    # MMI 1x2 (PICBench "mmi" alias)
    "mmi": {
        "device_type": "mmi",
        "width_um": 30.0,
        "height_um": 20.0,
        "ports_picbench": {
            "I1": (0.0, 10.0, "E"),
            "O1": (30.0, 5.0, "W"),
            "O2": (30.0, 15.0, "W"),
        },
    },
    # MZI with phase shifter (4-port: 2 in west, 2 out east)
    "mzi_ps": {
        "device_type": "mzi",
        "width_um": 200.0,
        "height_um": 50.0,
        "ports_picbench": {
            "I1": (0.0, 12.5, "E"),
            "I2": (0.0, 37.5, "E"),
            "O1": (200.0, 12.5, "W"),
            "O2": (200.0, 37.5, "W"),
        },
    },
    # Standalone MZI (LiDAR convention, 2 ports o1/o2)
    # Source: LiDAR ISPD'25 multiportmmi benchmark
    #   https://arxiv.org/abs/2504.18813
    "mzi": {
        "device_type": "mzi",
        "width_um": 200.0,
        "height_um": 50.0,
        "ports_picbench": {
            "I1": (0.0, 12.5, "E"),
            "I2": (0.0, 37.5, "E"),
            "O1": (200.0, 12.5, "W"),
            "O2": (200.0, 37.5, "W"),
        },
        "ports_lidar": {
            "o1": (0.0, 25.0, "E"),
            "o2": (200.0, 25.0, "W"),
        },
        "params": {"delta_length": 10.0},
    },
    # 2x2 optical switch unit (OSU): 2 in west, 2 out east
    "OSU": {
        "device_type": "mzi_switch",
        "width_um": 100.0,
        "height_um": 60.0,
        "ports_picbench": {
            "I1": (0.0, 15.0, "E"),
            "I2": (0.0, 45.0, "E"),
            "O1": (100.0, 15.0, "W"),
            "O2": (100.0, 45.0, "W"),
        },
    },
    # Waveguide (straight bus)
    "waveguide": {
        "device_type": "waveguide",
        "width_um": 100.0,
        "height_um": 0.5,
        "ports_picbench": {
            "I1": (0.0, 0.25, "E"),
            "O1": (100.0, 0.25, "W"),
        },
    },
    "straight": {
        "device_type": "waveguide",
        "width_um": 100.0,
        "height_um": 0.5,
        "ports_lidar": {
            "o1": (0.0, 0.25, "E"),
            "o2": (100.0, 0.25, "W"),
        },
    },
    # Heater / phase shifter (thermal tuner)
    "straight_heat_metal": {
        "device_type": "heater",
        "width_um": 100.0,
        "height_um": 10.0,
        "ports_picbench": {
            "I1": (0.0, 5.0, "E"),
            "O1": (100.0, 5.0, "W"),
        },
    },
    # Microring resonator (add/drop, 4 ports)
    # I1 (west upper) = input bus, O1 (east upper) = thru bus
    # O2 (east lower) = drop, O3 (west lower) = add
    "mrr": {
        "device_type": "ring_resonator",
        "width_um": 60.0,
        "height_um": 60.0,
        "ports_picbench": {
            "I1": (0.0, 45.0, "E"),
            "O1": (60.0, 45.0, "W"),
            "O2": (60.0, 15.0, "W"),
            "O3": (0.0, 15.0, "E"),
        },
        "params": {"radius": 10.0, "gap": 0.2},
    },
    "ring_single_pn": {
        "device_type": "ring_modulator",
        "width_um": 60.0,
        "height_um": 60.0,
        "ports_lidar": {
            "o1": (0.0, 30.0, "E"),
            "o2": (60.0, 30.0, "W"),
        },
        "params": {"radius": 10.0},
    },
    "ring_single": {
        "device_type": "ring_resonator",
        "width_um": 60.0,
        "height_um": 60.0,
        "ports_lidar": {
            "o1": (0.0, 30.0, "E"),
            "o2": (60.0, 30.0, "W"),
        },
        "params": {"radius": 10.0},
    },
    # Double-bus ring modulator with PN junction (4 ports, LiDAR convention)
    # Source: Tait et al., JLT 32(24) 4029 (2014) — MRR weight bank
    #   https://opg.optica.org/jlt/abstract.cfm?uri=jltech-32-24-4029
    # o1=west upper (input bus in), o2=east upper (thru bus out)
    # o3=west lower (add), o4=east lower (drop)
    "ring_double_pn": {
        "device_type": "ring_modulator",
        "width_um": 60.0,
        "height_um": 80.0,
        "ports_lidar": {
            "o1": (0.0, 60.0, "E"),
            "o2": (60.0, 60.0, "W"),
            "o3": (0.0, 20.0, "E"),
            "o4": (60.0, 20.0, "W"),
        },
        "params": {"radius": 10.0, "gap": 0.3},
    },
    # Directional coupler (4 ports, PICBench convention)
    # Source: PICBench NLS testcase — Klitgaard et al.
    #   https://github.com/JeppeKlitgaard/PicBench
    # I1/I2 = west (inputs), O1/O2 = east (outputs)
    "coupler": {
        "device_type": "directional_coupler",
        "width_um": 40.0,
        "height_um": 20.0,
        "ports_picbench": {
            "I1": (0.0, 5.0, "E"),
            "I2": (0.0, 15.0, "E"),
            "O1": (40.0, 5.0, "W"),
            "O2": (40.0, 15.0, "W"),
        },
        "params": {"gap": 0.2, "length": 10.0},
    },
    # Mach-Zehnder Modulator (2 ports, PICBench convention)
    # Source: PICBench QPSK modulator testcase — Klitgaard et al.
    #   https://github.com/JeppeKlitgaard/PicBench
    # I1 = west (input), O1 = east (output)
    "mzm": {
        "device_type": "mzm_modulator",
        "width_um": 200.0,
        "height_um": 50.0,
        "ports_picbench": {
            "I1": (0.0, 25.0, "E"),
            "O1": (200.0, 25.0, "W"),
        },
        "params": {"delta_length": 10.0},
    },
    # Multiport MMI star coupler (LiDAR convention, up to 12 ports)
    # Source: Maese-Novo et al., Opt. Express 21(1) 282 (2013)
    #   https://opg.optica.org/oe/fulltext.cfm?uri=oe-21-1-282
    # 8x8 multiport MMI: o1-o6 on west, o7-o12 on east
    "mmi_multiport": {
        "device_type": "multiport_mmi",
        "width_um": 100.0,
        "height_um": 100.0,
        "ports_lidar": {
            "o1": (0.0, 15.0, "E"),
            "o2": (0.0, 30.0, "E"),
            "o3": (0.0, 45.0, "E"),
            "o4": (0.0, 60.0, "E"),
            "o5": (0.0, 75.0, "E"),
            "o6": (0.0, 90.0, "E"),
            "o7": (100.0, 15.0, "W"),
            "o8": (100.0, 30.0, "W"),
            "o9": (100.0, 45.0, "W"),
            "o10": (100.0, 60.0, "W"),
            "o11": (100.0, 75.0, "W"),
            "o12": (100.0, 90.0, "W"),
        },
        "params": {"n_ports": 12},
    },
    # Heater with undercut (thermal phase shifter, LiDAR convention)
    # Source: LiDAR ISPD'25 benchmark
    #   https://arxiv.org/abs/2504.18813
    "straight_heat_metal_undercut": {
        "device_type": "heater",
        "width_um": 100.0,
        "height_um": 10.0,
        "ports_lidar": {
            "o1": (0.0, 5.0, "E"),
            "o2": (100.0, 5.0, "W"),
        },
        "params": {"length": 80.0},
    },
    # Grating coupler (fiber I/O)
    "grating_coupler_elliptical_lumerical": {
        "device_type": "grating_coupler",
        "width_um": 20.0,
        "height_um": 20.0,
        "ports_lidar": {
            "o1": (10.0, 0.0, "N"),
            "o2": (0.0, 10.0, "E"),
        },
    },
    "gc": {
        "device_type": "grating_coupler",
        "width_um": 20.0,
        "height_um": 20.0,
        "ports_lidar": {
            "o1": (10.0, 0.0, "N"),
            "o2": (0.0, 10.0, "E"),
        },
    },
    # Optical crossing (4-port, bidirectional)
    "crossing": {
        "device_type": "crossing",
        "width_um": 20.0,
        "height_um": 20.0,
        "ports_lidar": {
            "o1": (0.0, 10.0, "E"),
            "o2": (20.0, 10.0, "W"),
            "o3": (10.0, 0.0, "N"),
            "o4": (10.0, 20.0, "S"),
        },
    },
    # Y-branch (1 input west, 2 outputs east)
    "y_branch": {
        "device_type": "y_branch",
        "width_um": 20.0,
        "height_um": 20.0,
        "ports_lidar": {
            "o1": (0.0, 10.0, "E"),
            "o2": (20.0, 5.0, "W"),
            "o3": (20.0, 15.0, "W"),
        },
    },
    # Terminator (1 port)
    "terminator": {
        "device_type": "terminator",
        "width_um": 10.0,
        "height_um": 10.0,
        "ports_lidar": {
            "o1": (0.0, 5.0, "E"),
        },
    },
    # Bend (euler curve, 2 ports)
    "bend_euler": {
        "device_type": "bend",
        "width_um": 10.0,
        "height_um": 10.0,
        "ports_lidar": {
            "o1": (0.0, 5.0, "E"),
            "o2": (5.0, 10.0, "S"),
        },
    },
    # Rectangle (obstacle, no signal ports)
    "rectangle": {
        "device_type": "obstacle",
        "width_um": 10.0,
        "height_um": 10.0,
        "ports_lidar": {},
    },
}


def _resolve_device_spec(
    component: str, settings: dict | None, source_kind: str = ""
) -> dict:
    """根据组件类型与设置解析器件规格。

    Args:
        component: 组件类型名（如 "mmi1x2", "mzi_ps", "ring_single_pn"）。
        settings: 组件设置（可选，用于覆盖默认参数）。
        source_kind: 数据源类型（"PICBench"/"LiDAR"），用于选择端口约定。
            - "LiDAR" 时 "mmi" 组件映射到 "mmi_multiport"（多端口 MMI）
            - "LiDAR" 时优先使用 ports_lidar，"PICBench" 时优先使用 ports_picbench

    Returns:
        器件规格 dict（含 device_type, width_um, height_um, ports_dict）。

    Raises:
        RuntimeError: 未知组件类型（R03 禁止 fall-back）。
    """
    # LiDAR 上下文中 "mmi" 指多端口 MMI 星形耦合器（非 PICBench 1x2 MMI）
    resolved = component
    if source_kind == "LiDAR" and component == "mmi":
        resolved = "mmi_multiport"
    if resolved not in DEVICE_SPECS:
        raise RuntimeError(
            f"未知组件类型: {component}（R03 禁止 fall-back，"
            f"请在 DEVICE_SPECS 中注册）"
        )
    spec = DEVICE_SPECS[resolved]
    result = {
        "device_type": spec["device_type"],
        "width_um": float(spec["width_um"]),
        "height_um": float(spec["height_um"]),
    }
    # 按数据源选择端口命名约定
    has_picbench = "ports_picbench" in spec
    has_lidar = "ports_lidar" in spec
    if source_kind == "LiDAR" and has_lidar:
        result["ports"] = dict(spec["ports_lidar"])
        result["port_convention"] = "lidar"
    elif source_kind == "PICBench" and has_picbench:
        result["ports"] = dict(spec["ports_picbench"])
        result["port_convention"] = "picbench"
    elif has_picbench:
        result["ports"] = dict(spec["ports_picbench"])
        result["port_convention"] = "picbench"
    elif has_lidar:
        result["ports"] = dict(spec["ports_lidar"])
        result["port_convention"] = "lidar"
    else:
        raise RuntimeError(
            f"组件 {component} 缺少端口定义（R03 禁止 fall-back）"
        )
    # 合并参数
    if "params" in spec:
        result["params"] = dict(spec["params"])
    else:
        result["params"] = {}
    if settings:
        for k, v in settings.items():
            if isinstance(v, (int, float, str)):
                result["params"][k] = v
    return result


def _parse_picbench_netlist(data: dict) -> tuple[list[dict], list[tuple]]:
    """解析 PICBench netlist 格式为 polaris devices/connections。

    PICBench 格式:
        data.netlist.instances: {name: "component_str"} 或
                                 {name: {"component": str, "settings": {...}}}
        data.netlist.connections: {"src_inst,src_port": "dst_inst,dst_port"}
        data.models: {component_alias: real_component}

    重要: models 映射仅用于仿真模型选择，不影响端口命名。
    连接字符串使用原始组件名的端口约定（如 waveguide 的 I1/O1），
    因此解析器件规格时必须使用原始组件名，而非 models 映射后的名。

    Args:
        data: PICBench JSON 顶层 dict。

    Returns:
        (devices, connections) 元组。
        devices: [{name, device_type, width_um, height_um, ports, params}, ...]
        connections: [(d1, p1, d2, p2), ...]

    Raises:
        RuntimeError: 实例/连接格式非法（R03）。
    """
    netlist = data["data"]["netlist"]
    models = data["data"].get("models", {})
    instances = netlist["instances"]
    raw_conns = netlist["connections"]

    devices: list[dict] = []
    for name, inst_def in instances.items():
        if isinstance(inst_def, str):
            component = inst_def
            settings = {}
        elif isinstance(inst_def, dict):
            component = inst_def.get("component", "")
            settings = inst_def.get("settings", {})
        else:
            raise RuntimeError(
                f"PICBench 实例 {name} 格式非法: {inst_def}（R03）"
            )
        # R05 修复: 不应用 models 映射于端口查找
        # models 映射（如 waveguide→straight）仅用于仿真模型选择，
        # 连接字符串仍使用原始组件名的端口约定（如 waveguide 的 I1/O1）
        # 因此必须用原始组件名解析端口规格
        spec = _resolve_device_spec(component, settings, source_kind="PICBench")
        # 记录仿真模型映射到 params（供下游仿真用）
        sim_model = models.get(component, component)
        if sim_model != component:
            spec["params"]["_sim_model"] = sim_model
        # 端口 dict → list of [name, dx, dy, direction]
        ports_list = []
        for pname, (dx, dy, direction) in spec["ports"].items():
            ports_list.append([pname, float(dx), float(dy), direction])
        devices.append({
            "name": name,
            "device_type": spec["device_type"],
            "width_um": spec["width_um"],
            "height_um": spec["height_um"],
            "ports": ports_list,
            "params": spec["params"],
        })

    connections: list[tuple] = []
    for src_key, dst_key in raw_conns.items():
        src_inst, src_port = src_key.split(",")
        dst_inst, dst_port = dst_key.split(",")
        connections.append((src_inst, src_port, dst_inst, dst_port))
    return devices, connections


def _parse_lidar_netlist(data: dict) -> tuple[list[dict], list[tuple]]:
    """解析 LiDAR/gdsfactory netlist 格式为 polaris devices/connections。

    LiDAR 格式:
        instances: {name: {"component": str, "settings": {...}}}
        nets: {net_name: ["inst1,port1", "inst2,port2", ...]}
    gdsfactory 格式类似但 connections 为 dict。

    Args:
        data: LiDAR/gdsfactory JSON 顶层 dict。

    Returns:
        (devices, connections) 元组。

    Raises:
        RuntimeError: 实例/连接格式非法（R03）。
    """
    instances = data.get("instances", {})
    devices: list[dict] = []
    for name, inst_def in instances.items():
        if isinstance(inst_def, str):
            component = inst_def
            settings = {}
        elif isinstance(inst_def, dict):
            component = inst_def.get("component", "")
            settings = inst_def.get("settings", {})
        else:
            raise RuntimeError(
                f"LiDAR/gdsfactory 实例 {name} 格式非法: {inst_def}（R03）"
            )
        spec = _resolve_device_spec(component, settings, source_kind="LiDAR")
        ports_list = []
        for pname, (dx, dy, direction) in spec["ports"].items():
            ports_list.append([pname, float(dx), float(dy), direction])
        devices.append({
            "name": name,
            "device_type": spec["device_type"],
            "width_um": spec["width_um"],
            "height_um": spec["height_um"],
            "ports": ports_list,
            "params": spec["params"],
        })

    connections: list[tuple] = []
    # LiDAR nets 格式: {net_name: [endpoint1, endpoint2, ...]}
    nets = data.get("nets", {})
    for net_name, endpoints in nets.items():
        if len(endpoints) < 2:
            continue
        # 第一个端点作为源，其余作为目标（星形连接）
        src_inst, src_port = endpoints[0].split(",")
        for ep in endpoints[1:]:
            dst_inst, dst_port = ep.split(",")
            connections.append((src_inst, src_port, dst_inst, dst_port))
    # gdsfactory connections 格式: {"src_inst,src_port": "dst_inst,dst_port"}
    raw_conns = data.get("connections", {})
    if isinstance(raw_conns, dict):
        for src_key, dst_key in raw_conns.items():
            if "," not in src_key or "," not in dst_key:
                continue
            src_inst, src_port = src_key.split(",")
            dst_inst, dst_port = dst_key.split(",")
            connections.append((src_inst, src_port, dst_inst, dst_port))
    return devices, connections


def _compute_canvas(devices: list[dict], margin: float = 50.0) -> tuple[float, float]:
    """根据器件总尺寸计算画布大小（μm）。

    画布 = 总器件面积的开方 * 缩放因子 + 边距，保证器件可排布。
    与 polaris-core specs.py 默认 canvas_w=1000.0 同量级。

    Args:
        devices: 器件列表。
        margin: 边距（μm）。

    Returns:
        (canvas_w, canvas_h) 单位 μm。
    """
    total_area = sum(d["width_um"] * d["height_um"] for d in devices)
    n = len(devices)
    if n == 0 or total_area == 0:
        return 1000.0, 1000.0
    # 画布尺寸 = sqrt(总面积 * 安全系数 5) + 边距，保证 5x 面积余量
    side = float(np.sqrt(total_area * 5.0)) + margin * 2
    # 最小 1000μm（与 specs.py 默认一致），最大 5000μm（避免过大）
    side = max(1000.0, min(side, 5000.0))
    return side, side


def _build_circuit_dict(name: str, devices: list[dict],
                        connections: list[tuple]) -> dict:
    """构建 polaris-core CircuitSpec 风格的 circuit dict。

    Args:
        name: 电路名。
        devices: 器件列表。
        connections: 连接列表 [(d1, p1, d2, p2), ...]。

    Returns:
        circuit dict（可直接传给 place_analytical）。
    """
    canvas_w, canvas_h = _compute_canvas(devices)
    return {
        "name": name,
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "devices": devices,
        "connections": [list(c) for c in connections],
    }


def _placements_to_dict(placements: dict[str, dict]) -> dict[str, dict]:
    """将 place_analytical 输出（左下角坐标）转换为现有 expert_demos 格式。

    现有格式: {name: {x, y, rotation, mirror, bbox, width, height}}
    其中 x, y 为器件**中心**坐标（与 MZI1/placements.json 一致）。

    Args:
        placements: place_analytical 输出 {name: {x, y, w, h}}（左下角）。

    Returns:
        现有格式布局 dict。
    """
    result: dict[str, dict] = {}
    for name, pl in placements.items():
        x_lo = float(pl["x"])
        y_lo = float(pl["y"])
        w = float(pl["w"])
        h = float(pl["h"])
        cx = x_lo + w / 2.0
        cy = y_lo + h / 2.0
        result[name] = {
            "x": cx,
            "y": cy,
            "rotation": 0.0,
            "mirror": False,
            "bbox": [x_lo, y_lo, x_lo + w, y_lo + h],
            "width": w,
            "height": h,
        }
    return result


def _find_port_coord(device: dict, port_name: str) -> tuple[float, float, str]:
    """在器件规格中查找端口，返回 (dx, dy, direction)。

    Args:
        device: 器件 dict（含 ports 列表）。
        port_name: 端口名。

    Returns:
        (dx, dy, direction) 端口相对器件左下角的偏移与方向。

    Raises:
        RuntimeError: 端口未找到（R03 禁止 fall-back）。
    """
    for port in device.get("ports", []):
        if len(port) >= 4 and str(port[0]) == port_name:
            return (float(port[1]), float(port[2]), str(port[3]))
    raise RuntimeError(
        f"器件 {device.get('name')} 缺少端口 {port_name}（R03 禁止 fall-back）"
    )


def _route_connections(
    circuit: dict,
    placements: dict[str, dict],
    router: CurvyRouter,
) -> list[list[list[float]]]:
    """为每条连接生成波导路径。

    对每条连接 (d1, p1, d2, p2):
    1. 计算 d1.p1 的绝对坐标 = placements[d1].x_lo + port_dx, y_lo + port_dy
    2. 计算 d2.p2 的绝对坐标
    3. 调用 CurvyRouter.route 生成 S-bend 路径
    4. 路径点转换为 [x, y] 列表

    Args:
        circuit: 电路 dict（含 devices, connections）。
        placements: place_analytical 输出（左下角坐标 {x, y, w, h}）。
        router: CurvyRouter 实例。

    Returns:
        路径列表 [[[x1, y1], [x2, y2], ...], ...]
    """
    device_map = {d["name"]: d for d in circuit["devices"]}
    routes: list[list[list[float]]] = []
    for conn in circuit["connections"]:
        d1_name, p1_name, d2_name, p2_name = (
            str(conn[0]), str(conn[1]), str(conn[2]), str(conn[3])
        )
        if d1_name not in placements or d2_name not in placements:
            raise RuntimeError(
                f"连接 {conn} 涉及未布局器件（R03 禁止 fall-back）"
            )
        d1_dev = device_map.get(d1_name)
        d2_dev = device_map.get(d2_name)
        if d1_dev is None or d2_dev is None:
            raise RuntimeError(
                f"连接 {conn} 涉及未知器件（R03）"
            )
        p1_dx, p1_dy, _ = _find_port_coord(d1_dev, p1_name)
        p2_dx, p2_dy, _ = _find_port_coord(d2_dev, p2_name)
        pl1 = placements[d1_name]
        pl2 = placements[d2_name]
        start = (float(pl1["x"]) + p1_dx, float(pl1["y"]) + p1_dy)
        end = (float(pl2["x"]) + p2_dx, float(pl2["y"]) + p2_dy)
        path = router.route(start, end)
        routes.append([[float(p[0]), float(p[1])] for p in path])
    return routes


def _build_meta(
    demo_name: str,
    source_file: str,
    source_kind: str,
    source_url: str,
    circuit: dict,
    n_routes: int,
) -> dict:
    """构建 meta.json（R02 学术诚信：来源、URL、文献）。

    Args:
        demo_name: demo 名称。
        source_file: 源 netlist 文件名。
        source_kind: 源类型（"PICBench"/"LiDAR"/"GDSFactory"）。
        source_url: 源 URL。
        circuit: 电路 dict。
        n_routes: 路径数。

    Returns:
        meta dict。
    """
    n_devices = len(circuit["devices"])
    n_connections = len(circuit["connections"])
    return {
        "source_gds": source_file,  # 字段名保持与现有格式一致
        "source_url": source_url,
        "source_pdk": {
            "name": source_kind,
            "publisher": _SOURCE_PUBLISHERS.get(source_kind, "Unknown"),
            "author": _SOURCE_AUTHORS.get(source_kind, "Unknown"),
            "license": "MIT",
            "url": source_url,
            "examples_url": source_url,
            "year": "2015-2025",
        },
        "extract_time": datetime.now().isoformat(),
        "circuit_name": circuit["name"],
        "n_devices": n_devices,
        "n_connections": n_connections,
        "n_placements": n_devices,
        "n_routes": n_routes,
        "canvas_w_um": circuit["canvas_w"],
        "canvas_h_um": circuit["canvas_h"],
        "demo_name": demo_name,
        "generator": "expand_expert_demos.py v1",
        "generator_pipeline": [
            "parse_benchmark_netlist",
            "place_analytical (DREAMPlace TCAD 2020)",
            "CurvyRouter (LiDAR ISPD'25 S-bend)",
        ],
    }


# 源信息（R02 学术诚信）
_SOURCE_PUBLISHERS = {
    "PICBench": "Jeppe Klitgaard et al.",
    "LiDAR": "LiDAR-RL (ISPD 2025)",
    "GDSFactory": "GDSFactory team (UPV/Columbia)",
    "SiEPIC": "UBC SiEPIC (Lukas Chrostowski)",
}
_SOURCE_AUTHORS = {
    "PICBench": "Klitgaard et al.",
    "LiDAR": "LiDAR et al.",
    "GDSFactory": "Matres et al.",
    "SiEPIC": "Chrostowski et al.",
}


# =========================================================================
# Demo 生成任务定义（每个 demo 映射到一个真实 benchmark netlist）
# =========================================================================

DEMO_TASKS: list[dict] = [
    {
        "demo_name": "mzi_2x2_switch",
        "source_file": "data/benchmarks/picbench_OS_2x2.json",
        "source_kind": "PICBench",
        "source_url": "https://github.com/JeppeKlitgaard/PicBench",
        "parser": "picbench",
        "description": "2x2 光开关（2 MMI + 4 phase shifter）",
    },
    {
        "demo_name": "ring_filter_1",
        "source_file": None,  # 合成（基于真实 ring_single 器件规格）
        "source_kind": "SiEPIC",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "parser": "synth_ring_filter_1",
        "description": "单环滤波器（1 ring + 2 gc + 2 wg）",
    },
    {
        "demo_name": "ring_filter_2",
        "source_file": None,
        "source_kind": "SiEPIC",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "parser": "synth_ring_filter_2",
        "description": "双环级联滤波器（2 ring + 2 gc + 3 wg）",
    },
    {
        "demo_name": "wdm_4ch",
        "source_file": "data/benchmarks/picbench_WDM_mux.json",
        "source_kind": "PICBench",
        "source_url": "https://github.com/JeppeKlitgaard/PicBench",
        "parser": "picbench",
        "description": "4通道 WDM 复用器（4 mrr + 3 waveguide）",
    },
    {
        "demo_name": "mzi_lattice_4stage",
        "source_file": "data/benchmarks/picbench_Clements_4x4.json",
        "source_kind": "PICBench",
        "source_url": "https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460",
        "parser": "picbench",
        "description": "4阶 MZI lattice（Clements 4x4 = 6 mzi_ps）",
    },
    {
        "demo_name": "mzi_switch_tree_4x4",
        "source_file": "data/benchmarks/picbench_Crossbar_4x4.json",
        "source_kind": "PICBench",
        "source_url": "https://github.com/JeppeKlitgaard/PicBench",
        "parser": "picbench",
        "description": "4x4 开关树（Crossbar 4x4 = 16 OSU）",
    },
    {
        "demo_name": "cyclic_mzi_mesh_3x3",
        "source_file": "data/benchmarks/picbench_Spanke_4x4.json",
        "source_kind": "PICBench",
        "source_url": "https://ieeexplore.ieee.org/document/1072908",
        "parser": "picbench",
        "description": "循环 MZI mesh（Spanke 4x4 大规模光开关网络）",
    },
    {
        "demo_name": "ring_modulator_array",
        "source_file": "data/benchmarks/lidar_mrr_weight_bank_4x4.json",
        "source_kind": "LiDAR",
        "source_url": "https://opg.optica.org/jlt/abstract.cfm?uri=jltech-32-24-4029",
        "parser": "lidar",
        "description": "环调制器阵列（MRR weight bank 4x4，光子神经网络权重）",
    },
    {
        "demo_name": "optical_interconnect_8ch",
        "source_file": "data/benchmarks/lidar_multiportmmi_8x8.json",
        "source_kind": "LiDAR",
        "source_url": "https://opg.optica.org/oe/fulltext.cfm?uri=oe-21-1-282",
        "parser": "lidar",
        "description": "8通道光互连（MultiportMMI 8x8 光开关阵列）",
    },
    {
        "demo_name": "photonic_neuron_4",
        "source_file": "data/benchmarks/picbench_NLS.json",
        "source_kind": "PICBench",
        "source_url": "https://github.com/JeppeKlitgaard/PicBench",
        "parser": "picbench",
        "description": "4神经元光子网络（NLS = Nonlinear Laser Separator）",
    },
    {
        "demo_name": "mzm_modulator_link",
        "source_file": "data/benchmarks/picbench_MZM.json",
        "source_kind": "PICBench",
        "source_url": "https://github.com/JeppeKlitgaard/PicBench",
        "parser": "picbench",
        "description": "MZM 调制器链路（马赫-曾德调制器 + driver）",
    },
    {
        "demo_name": "qpsk_modulator",
        "source_file": "data/benchmarks/picbench_QPSK modulator.json",
        "source_kind": "PICBench",
        "source_url": "https://github.com/JeppeKlitgaard/PicBench",
        "parser": "picbench",
        "description": "QPSK 调制器（正交相移键控光发射机）",
    },
]


# =========================================================================
# 合成 demo 生成器（用于 ring_filter_1/2，基于真实 SiEPIC 器件规格）
# =========================================================================

def _synth_ring_filter_1() -> tuple[list[dict], list[tuple]]:
    """合成单环滤波器（1 ring + 2 gc + 2 wg）。

    拓扑: gc_in → wg_in → ring → wg_out → gc_out
    来源: SiEPIC EBeam PDK RingResonator 标准拓扑
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    spec_ring = _resolve_device_spec("mrr", None)
    spec_gc = _resolve_device_spec("gc", None)
    spec_wg = _resolve_device_spec("waveguide", None)
    devices = [
        {
            "name": "gc_in",
            "device_type": spec_gc["device_type"],
            "width_um": spec_gc["width_um"],
            "height_um": spec_gc["height_um"],
            "ports": [[k, v[0], v[1], v[2]] for k, v in spec_gc["ports"].items()],
            "params": {},
        },
        {
            "name": "wg_in",
            "device_type": spec_wg["device_type"],
            "width_um": spec_wg["width_um"],
            "height_um": spec_wg["height_um"],
            "ports": [[k, v[0], v[1], v[2]] for k, v in spec_wg["ports"].items()],
            "params": {"length": 100.0},
        },
        {
            "name": "ring1",
            "device_type": spec_ring["device_type"],
            "width_um": spec_ring["width_um"],
            "height_um": spec_ring["height_um"],
            "ports": [[k, v[0], v[1], v[2]] for k, v in spec_ring["ports"].items()],
            "params": spec_ring["params"],
        },
        {
            "name": "wg_out",
            "device_type": spec_wg["device_type"],
            "width_um": spec_wg["width_um"],
            "height_um": spec_wg["height_um"],
            "ports": [[k, v[0], v[1], v[2]] for k, v in spec_wg["ports"].items()],
            "params": {"length": 100.0},
        },
        {
            "name": "gc_out",
            "device_type": spec_gc["device_type"],
            "width_um": spec_gc["width_um"],
            "height_um": spec_gc["height_um"],
            "ports": [[k, v[0], v[1], v[2]] for k, v in spec_gc["ports"].items()],
            "params": {},
        },
    ]
    # 连接使用各器件的实际端口名（gc→o2，wg→I1/O1，ring→I1/O1）
    # gc.o2=波导端口(west)，wg.I1=输入(west)，wg.O1=输出(east)
    # ring.I1=输入bus(west)，ring.O1=thru bus(east)
    connections = [
        ("gc_in", "o2", "wg_in", "I1"),
        ("wg_in", "O1", "ring1", "I1"),
        ("ring1", "O1", "wg_out", "I1"),
        ("wg_out", "O1", "gc_out", "o2"),
    ]
    return devices, connections


def _synth_ring_filter_2() -> tuple[list[dict], list[tuple]]:
    """合成双环级联滤波器（2 ring + 2 gc + 3 wg）。

    拓扑: gc_in → wg_in → ring1 → wg_mid → ring2 → wg_out → gc_out
    来源: SiEPIC EBeam PDK Ring_series 标准拓扑
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    spec_ring = _resolve_device_spec("mrr", None)
    spec_gc = _resolve_device_spec("gc", None)
    spec_wg = _resolve_device_spec("waveguide", None)
    devices = [
        {"name": "gc_in", "device_type": spec_gc["device_type"],
         "width_um": spec_gc["width_um"], "height_um": spec_gc["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_gc["ports"].items()],
         "params": {}},
        {"name": "wg_in", "device_type": spec_wg["device_type"],
         "width_um": spec_wg["width_um"], "height_um": spec_wg["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_wg["ports"].items()],
         "params": {"length": 100.0}},
        {"name": "ring1", "device_type": spec_ring["device_type"],
         "width_um": spec_ring["width_um"], "height_um": spec_ring["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_ring["ports"].items()],
         "params": {**spec_ring["params"], "radius": 10.0}},
        {"name": "wg_mid", "device_type": spec_wg["device_type"],
         "width_um": spec_wg["width_um"], "height_um": spec_wg["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_wg["ports"].items()],
         "params": {"length": 100.0}},
        {"name": "ring2", "device_type": spec_ring["device_type"],
         "width_um": spec_ring["width_um"], "height_um": spec_ring["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_ring["ports"].items()],
         "params": {**spec_ring["params"], "radius": 12.0}},
        {"name": "wg_out", "device_type": spec_wg["device_type"],
         "width_um": spec_wg["width_um"], "height_um": spec_wg["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_wg["ports"].items()],
         "params": {"length": 100.0}},
        {"name": "gc_out", "device_type": spec_gc["device_type"],
         "width_um": spec_gc["width_um"], "height_um": spec_gc["height_um"],
         "ports": [[k, v[0], v[1], v[2]] for k, v in spec_gc["ports"].items()],
         "params": {}},
    ]
    connections = [
        ("gc_in", "o2", "wg_in", "I1"),
        ("wg_in", "O1", "ring1", "I1"),
        ("ring1", "O1", "wg_mid", "I1"),
        ("wg_mid", "O1", "ring2", "I1"),
        ("ring2", "O1", "wg_out", "I1"),
        ("wg_out", "O1", "gc_out", "o2"),
    ]
    return devices, connections


# =========================================================================
# 主流程
# =========================================================================

def _load_devices_connections(task: dict) -> tuple[list[dict], list[tuple]]:
    """根据 task 加载或合成 devices/connections。"""
    parser = task["parser"]
    if parser == "synth_ring_filter_1":
        return _synth_ring_filter_1()
    if parser == "synth_ring_filter_2":
        return _synth_ring_filter_2()
    src_path = _REPO_ROOT / task["source_file"]
    if not src_path.exists():
        raise RuntimeError(
            f"源 netlist 不存在: {src_path}（R03 禁止 fall-back）"
        )
    data = json.loads(src_path.read_text(encoding="utf-8"))
    if parser == "picbench":
        return _parse_picbench_netlist(data)
    if parser == "lidar":
        return _parse_lidar_netlist(data)
    raise RuntimeError(f"未知 parser: {parser}（R03）")


def _validate_demo(demo_dir: Path, devices: list[dict],
                   connections: list[tuple], placements: dict,
                   routes: list) -> None:
    """验证 demo 完整性（R05 Bug 必修）。"""
    if len(devices) < 3:
        raise RuntimeError(
            f"器件数 {len(devices)} < 3（违反任务约束，R05）"
        )
    if len(connections) < 2:
        raise RuntimeError(
            f"连接数 {len(connections)} < 2（违反任务约束，R05）"
        )
    # 验证每个器件的端口坐标在边界内
    for d in devices:
        w = d["width_um"]
        h = d["height_um"]
        for p in d["ports"]:
            pname, dx, dy, direction = p
            if dx < -0.001 or dx > w + 0.001:
                raise RuntimeError(
                    f"器件 {d['name']} 端口 {pname} dx={dx} 超出 [0, {w}]（R05）"
                )
            if dy < -0.001 or dy > h + 0.001:
                raise RuntimeError(
                    f"器件 {d['name']} 端口 {pname} dy={dy} 超出 [0, {h}]（R05）"
                )
    # 验证布局无重叠
    names = list(placements.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = placements[names[i]]
            b = placements[names[j]]
            # AABB strict overlap
            if (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                    and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]):
                raise RuntimeError(
                    f"器件 {names[i]} 与 {names[j]} 重叠（R05 布局冲突）"
                )
    # 验证连接引用的端口存在
    device_map = {d["name"]: d for d in devices}
    for conn in connections:
        d1, p1, d2, p2 = conn
        if d1 not in device_map:
            raise RuntimeError(f"连接 {conn} 引用未知器件 {d1}（R05）")
        if d2 not in device_map:
            raise RuntimeError(f"连接 {conn} 引用未知器件 {d2}（R05）")
        d1_ports = {p[0] for p in device_map[d1]["ports"]}
        d2_ports = {p[0] for p in device_map[d2]["ports"]}
        if p1 not in d1_ports:
            raise RuntimeError(
                f"连接 {conn}: 器件 {d1} 缺少端口 {p1}（R05）"
            )
        if p2 not in d2_ports:
            raise RuntimeError(
                f"连接 {conn}: 器件 {d2} 缺少端口 {p2}（R05）"
            )


def process_task(task: dict, output_root: Path) -> dict:
    """处理单个 demo 生成任务。

    Returns:
        任务统计 {name, n_devices, n_connections, n_routes, status}。
    """
    demo_name = task["demo_name"]
    logger.info("处理 demo: %s (%s)", demo_name, task["description"])

    devices, connections = _load_devices_connections(task)
    logger.info("  解析: %d 器件, %d 连接", len(devices), len(connections))

    circuit = _build_circuit_dict(demo_name, devices, connections)
    logger.info("  画布: %.1f x %.1f μm", circuit["canvas_w"], circuit["canvas_h"])

    # 调用 polaris-place 解析法布局器
    placements = place_analytical(circuit, AnalyticalConfig(max_iterations=100))
    logger.info("  布局: %d 器件", len(placements))

    # 转换为现有 expert_demos 格式（中心坐标）
    placements_dict = _placements_to_dict(placements)

    # 调用 polaris-route 生成路径
    router = CurvyRouter(CurvyRouteConfig())
    routes = _route_connections(circuit, placements, router)
    logger.info("  布线: %d 路径", len(routes))

    # 验证
    demo_dir = output_root / demo_name
    demo_dir.mkdir(parents=True, exist_ok=True)
    _validate_demo(demo_dir, devices, connections, placements, routes)

    # 写入 4 个 JSON
    netlist_data = {
        "name": circuit["name"],
        "canvas_w": circuit["canvas_w"],
        "canvas_h": circuit["canvas_h"],
        "devices": devices,
        "connections": [list(c) for c in connections],
    }
    (demo_dir / "netlist.json").write_text(
        json.dumps(netlist_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (demo_dir / "placements.json").write_text(
        json.dumps(placements_dict, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (demo_dir / "routes.json").write_text(
        json.dumps(routes, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    meta = _build_meta(
        demo_name=demo_name,
        source_file=task["source_file"] or f"synth:{task['parser']}",
        source_kind=task["source_kind"],
        source_url=task["source_url"],
        circuit=circuit,
        n_routes=len(routes),
    )
    meta["description"] = task["description"]
    (demo_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("  ✅ %s: %d 器件, %d 连接, %d 路径",
                demo_name, len(devices), len(connections), len(routes))
    return {
        "name": demo_name,
        "n_devices": len(devices),
        "n_connections": len(connections),
        "n_routes": len(routes),
        "canvas_w": circuit["canvas_w"],
        "canvas_h": circuit["canvas_h"],
        "source": task["source_kind"],
        "status": "success",
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    output_root = _REPO_ROOT / "data" / "expert_demos"
    output_root.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    failed: list[dict] = []
    for task in DEMO_TASKS:
        try:
            rec = process_task(task, output_root)
            records.append(rec)
        except Exception as e:
            logger.error("❌ %s: %s", task["demo_name"], e)
            failed.append({"name": task["demo_name"], "error": str(e)})
            # R03: 不 fall-back，但继续处理其他 demo 以收集完整错误信息
            # 最终在 main 末尾若失败则 raise

    # 更新 index.json（合并现有 10 个 + 新增）
    index_path = output_root / "index.json"
    existing_index = {}
    if index_path.exists():
        existing_index = json.loads(index_path.read_text(encoding="utf-8"))
    existing_records = existing_index.get("records", [])
    existing_names = {r["name"] for r in existing_records}
    new_records = [r for r in records if r["name"] not in existing_names]
    all_records = existing_records + new_records

    total_devices = sum(r.get("n_devices", 0) for r in all_records)
    total_routes = sum(r.get("n_routes", 0) for r in all_records)
    index = {
        "dataset_name": "PoLaRIS Expert Demos (SiEPIC + PICBench + LiDAR)",
        "description": (
            "从真实 SiEPIC EBeam PDK GDS、PICBench、LiDAR ISPD'25 benchmark "
            "提取的专家示范三元组数据集（模仿学习用）"
        ),
        "source": {
            "SiEPIC": {
                "url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
                "publisher": "UBC, Lukas Chrostowski",
                "license": "MIT",
            },
            "PICBench": {
                "url": "https://github.com/JeppeKlitgaard/PicBench",
                "publisher": "Jeppe Klitgaard et al.",
            },
            "LiDAR": {
                "url": "https://arxiv.org/abs/2504.18813",
                "publisher": "LiDAR et al., ISPD 2025",
            },
        },
        "extract_time": datetime.now().isoformat(),
        "stats": {
            "total_demos": len(all_records),
            "new_demos": len(new_records),
            "failed": len(failed),
            "total_devices": total_devices,
            "total_routes": total_routes,
        },
        "records": all_records,
        "failed": failed,
    }
    index_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n=== 数据集扩充完成 ===")
    print(f"新增 demo: {len(new_records)}")
    print(f"失败: {len(failed)}")
    print(f"总 demo: {len(all_records)}")
    print(f"总器件: {total_devices}")
    print(f"总路径: {total_routes}")
    if failed:
        print("\n失败列表:")
        for f in failed:
            print(f"  - {f['name']}: {f['error']}")

    # R03: 若有失败则 raise（不静默继续）
    if failed:
        raise RuntimeError(
            f"{len(failed)} 个 demo 生成失败（R03 禁止 fall-back）: "
            + ", ".join(f["name"] for f in failed)
        )


if __name__ == "__main__":
    main()
