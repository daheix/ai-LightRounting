"""外部数据源加载器。

支持从 LiDAR PIC IR (YAML)、PICBench (YAML/Python)、
GDSFactory (*.pic.yml) 等格式加载光子电路训练数据。

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- PhIDO: https://github.com/JPPhotonics/PhIDO-Release
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from polaris.data.specs import CircuitSpec, DeviceSpec

logger = logging.getLogger(__name__)


def _parse_pic_ir_ports(
    inst: dict,
) -> list[tuple[str, float, float, str]]:
    """解析 PIC IR 实例的端口列表。"""
    ports: list[tuple[str, float, float, str]] = []
    for p in inst.get("ports", []):
        pname = p.get("name", "o1")
        px = float(p.get("x", 0.0))
        py = float(p.get("y", 0.0))
        pdir = p.get("direction", "E")
        ports.append((pname, px, py, pdir))
    return ports


def _parse_pic_ir_nets(
    raw: dict,
) -> list[tuple[str, str, str, str]]:
    """解析 PIC IR 网络连接列表。"""
    connections: list[tuple[str, str, str, str]] = []
    for net in raw.get("nets", []):
        src = net.get("src", net.get("source", ""))
        dst = net.get("dst", net.get("destination", ""))
        if "," in src:
            src_parts = src.split(",")
            dst_parts = dst.split(",")
            if len(src_parts) == 2 and len(dst_parts) == 2:
                connections.append((src_parts[0], src_parts[1], dst_parts[0], dst_parts[1]))
    return connections


def load_pic_ir(path: str | Path) -> CircuitSpec:
    """加载 LiDAR PIC IR 格式 (YAML)。

    PIC IR 是 Apollo/LiDAR 定义的光子电路中间表示格式，
    包含 instances、nets、constraints 等字段。

    来源: https://github.com/ScopeX-ASU/LiDAR

    Args:
        path: PIC IR YAML 文件路径。

    Returns:
        CircuitSpec。
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    devices: list[DeviceSpec] = []

    for inst in raw.get("instances", []):
        name = inst.get("name", "unknown")
        cell = inst.get("cell_type", inst.get("cell", "unknown"))
        w = float(inst.get("width", inst.get("xsize", 10.0)))
        h = float(inst.get("height", inst.get("ysize", 10.0)))
        ports = _parse_pic_ir_ports(inst)
        devices.append(
            DeviceSpec(
                name=name,
                device_type=cell,
                width_um=w,
                height_um=h,
                ports=ports,
            )
        )

    connections = _parse_pic_ir_nets(raw)

    canvas = raw.get("canvas", raw.get("die", {}))
    cw = float(canvas.get("width", canvas.get("xsize", 1000.0)))
    ch = float(canvas.get("height", canvas.get("ysize", 1000.0)))

    return CircuitSpec(
        name=raw.get("name", Path(path).stem),
        devices=devices,
        connections=connections,
        canvas_w=cw,
        canvas_h=ch,
    )


def load_gdsfactory_yaml(path: str | Path) -> CircuitSpec:
    """加载 GDSFactory *.pic.yml 格式。

    GDSFactory YAML 网表格式包含 instances、placements、
    connections、routes、ports 等字段。

    来源: https://gdsfactory.github.io/gdsfactory/

    Args:
        path: GDSFactory YAML 文件路径。

    Returns:
        CircuitSpec。
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    devices: list[DeviceSpec] = []
    connections: list[tuple[str, str, str, str]] = []

    for name, inst in raw.get("instances", {}).items():
        component = inst.get("component", "unknown")
        settings = inst.get("settings", {})
        w = float(settings.get("length", settings.get("width", 10.0)))
        h = float(settings.get("gap", 10.0))
        devices.append(DeviceSpec(name=name, device_type=component, width_um=w, height_um=h))

    for conn in raw.get("connections", []):
        if isinstance(conn, dict):
            src = conn.get("source", conn.get("src", ""))
            dst = conn.get("destination", conn.get("dst", ""))
        elif isinstance(conn, str):
            parts = conn.split(",")
            src = parts[0] if len(parts) >= 1 else ""
            dst = parts[1] if len(parts) >= 2 else ""
        else:
            continue
        src_dev, src_port = _split_port_ref(src)
        dst_dev, dst_port = _split_port_ref(dst)
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))

    return CircuitSpec(
        name=raw.get("name", Path(path).stem),
        devices=devices,
        connections=connections,
    )


def load_picbench(path: str | Path) -> CircuitSpec:
    """加载 PICBench 格式 (YAML/JSON)。

    PICBench 是 HKUST(GZ) 定义的光子电路设计基准，
    包含自然语言描述和仿真就绪网表。

    来源: https://github.com/PICDA/PICBench

    Args:
        path: PICBench YAML/JSON 文件路径。

    Returns:
        CircuitSpec。
    """
    p = Path(path)
    if p.suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    devices: list[DeviceSpec] = []
    connections: list[tuple[str, str, str, str]] = []

    for comp in raw.get("components", raw.get("devices", [])):
        name = comp.get("name", "unknown")
        ctype = comp.get("type", comp.get("component", "unknown"))
        w = float(comp.get("width", comp.get("xsize", 10.0)))
        h = float(comp.get("height", comp.get("ysize", 10.0)))
        devices.append(DeviceSpec(name=name, device_type=ctype, width_um=w, height_um=h))

    for conn in raw.get("connections", raw.get("nets", [])):
        if isinstance(conn, dict):
            src = conn.get("source", conn.get("src", ""))
            dst = conn.get("destination", conn.get("dst", ""))
        elif isinstance(conn, (list, tuple)) and len(conn) >= 2:
            src, dst = conn[0], conn[1]
        else:
            continue
        src_dev, src_port = _split_port_ref(str(src))
        dst_dev, dst_port = _split_port_ref(str(dst))
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))

    return CircuitSpec(
        name=raw.get("name", raw.get("id", p.stem)),
        devices=devices,
        connections=connections,
    )


def load_phido(path: str | Path) -> CircuitSpec:
    """加载 PhIDO 格式 (YAML/JSON)。

    PhIDO 是 U of Toronto/GDSFactory/MIT 定义的
    光子设计自动化测试基准。

    来源: https://github.com/JPPhotonics/PhIDO-Release

    Args:
        path: PhIDO YAML/JSON 文件路径。

    Returns:
        CircuitSpec。
    """
    p = Path(path)
    if p.suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    devices: list[DeviceSpec] = []
    connections: list[tuple[str, str, str, str]] = []

    for inst in raw.get("instances", raw.get("components", [])):
        if isinstance(inst, dict):
            name = inst.get("name", "unknown")
            ctype = inst.get("component", inst.get("type", "unknown"))
            w = float(inst.get("width", inst.get("xsize", 10.0)))
            h = float(inst.get("height", inst.get("ysize", 10.0)))
            devices.append(DeviceSpec(name=name, device_type=ctype, width_um=w, height_um=h))

    for conn in raw.get("connections", raw.get("nets", [])):
        if isinstance(conn, dict):
            src = conn.get("source", conn.get("src", ""))
            dst = conn.get("destination", conn.get("dst", ""))
        else:
            continue
        src_dev, src_port = _split_port_ref(str(src))
        dst_dev, dst_port = _split_port_ref(str(dst))
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))

    return CircuitSpec(
        name=raw.get("name", raw.get("design_id", p.stem)),
        devices=devices,
        connections=connections,
    )


def _split_port_ref(ref: str) -> tuple[str, str]:
    """拆分端口引用 'device,port' → (device, port)。"""
    if "," in ref:
        parts = ref.split(",", 1)
        return parts[0].strip(), parts[1].strip()
    if ":" in ref:
        parts = ref.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return ref.strip(), "o1"


def load_directory(
    path: str | Path,
    fmt: str = "auto",
) -> list[CircuitSpec]:
    """批量加载目录下的所有电路文件。

    Args:
        path: 目录路径。
        fmt: 格式（auto/pic_ir/gdsfactory/picbench/phido）。

    Returns:
        CircuitSpec 列表。
    """
    p = Path(path)
    if not p.exists():
        logger.error("数据目录不存在: %s", path)
        return []

    circuits: list[CircuitSpec] = []
    for fp in sorted(p.glob("*.y*ml")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    for fp in sorted(p.glob("*.json")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    logger.info("从 %s 加载了 %d 个电路", path, len(circuits))
    return circuits


def _load_file(fp: Path, fmt: str) -> CircuitSpec:
    """根据格式加载单个文件。"""
    if fmt == "pic_ir":
        return load_pic_ir(fp)
    if fmt == "gdsfactory":
        return load_gdsfactory_yaml(fp)
    if fmt == "picbench":
        return load_picbench(fp)
    if fmt == "phido":
        return load_phido(fp)
    # auto: 尝试所有格式
    for loader in [load_pic_ir, load_gdsfactory_yaml, load_picbench, load_phido]:
        try:
            return loader(fp)
        except Exception:
            continue
    raise ValueError(f"无法识别文件格式: {fp}")


__all__ = [
    "load_pic_ir",
    "load_gdsfactory_yaml",
    "load_picbench",
    "load_phido",
    "load_directory",
]
