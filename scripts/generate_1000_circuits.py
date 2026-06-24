#!/usr/bin/env python3
"""PoLaRIS 1000 电路生成器框架（Task 5）。

为 Task 6-9 提供统一基础：4 平台（SOI/SiN/InP/LNOI）× 5 规模（XS/S/M/L/XL）×
CircuitGenerator 抽象基类 + 序列化校验 + 索引清单。

平台参数来源（公开 PDK，规则 18 学术诚信）：
- SOI (SiEPIC EBeam): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiN (Ligentec): https://www.ligentec.com/
- InP (imec): https://www.imec-int.com/technologies/photonics
- LNOI (HyperLight): https://www.hyperlightcorp.com/

用法:
    python scripts/generate_1000_circuits.py --topology all --scale XS --platform SOI,SiN --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gen_1000")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "generated"

# 合法方向集合（大小写均允许）
VALID_DIRECTIONS = {"N", "S", "E", "W", "n", "s", "e", "w"}


# =============================================================================
# 平台参数配置（来源：公开 PDK，规则 18 学术诚信）
# =============================================================================


@dataclass(frozen=True)
class PlatformConfig:
    """光子平台参数配置。

    Attributes:
        name: 平台名称（SOI/SiN/InP/LNOI）。
        r_min_um: 最小弯曲半径（μm）。
        waveguide_width_um: 波导宽度（μm）。
        wavelength_nm: 工作波长（nm）。
        n_core: 芯层折射率。
        n_clad: 包层折射率。
        loss_db_mm: 波导损耗（dB/mm）。
        source_url: 参数来源 URL。
    """

    name: str
    r_min_um: float
    waveguide_width_um: float
    wavelength_nm: float
    n_core: float
    n_clad: float
    loss_db_mm: float
    source_url: str


# 平台参数集（来源：公开 PDK 文档）
PLATFORMS: dict[str, PlatformConfig] = {
    # SOI: SiEPIC EBeam PDK，220nm SOI 平台
    "SOI": PlatformConfig(
        name="SOI", r_min_um=5.0, waveguide_width_um=0.5, wavelength_nm=1550.0,
        n_core=2.4, n_clad=1.444, loss_db_mm=0.5,
        source_url="https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    ),
    # SiN: Ligentec AN1200 平台
    "SiN": PlatformConfig(
        name="SiN", r_min_um=100.0, waveguide_width_um=1.0, wavelength_nm=1550.0,
        n_core=2.0, n_clad=1.444, loss_db_mm=0.1,
        source_url="https://www.ligentec.com/",
    ),
    # InP: 通用 InP 集成光子平台（imec）
    "InP": PlatformConfig(
        name="InP", r_min_um=250.0, waveguide_width_um=2.0, wavelength_nm=1550.0,
        n_core=3.17, n_clad=3.0, loss_db_mm=1.0,
        source_url="https://www.imec-int.com/technologies/photonics",
    ),
    # LNOI: HyperLight 薄膜铌酸锂平台
    "LNOI": PlatformConfig(
        name="LNOI", r_min_um=50.0, waveguide_width_um=1.5, wavelength_nm=1550.0,
        n_core=2.2, n_clad=1.444, loss_db_mm=0.3,
        source_url="https://www.hyperlightcorp.com/",
    ),
}


# =============================================================================
# 规模配置（对齐 TILOS/Apollo benchmark 规模分布）
# =============================================================================


@dataclass(frozen=True)
class ScaleConfig:
    """电路规模配置。

    Attributes:
        name: 规模名称（XS/S/M/L/XL）。
        min_devices: 最小器件数。
        max_devices: 最大器件数。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
    """

    name: str
    min_devices: int
    max_devices: int
    canvas_w: float
    canvas_h: float


SCALES: dict[str, ScaleConfig] = {
    "XS": ScaleConfig("XS", 3, 5, 200.0, 200.0),
    "S": ScaleConfig("S", 6, 10, 400.0, 400.0),
    "M": ScaleConfig("M", 11, 20, 800.0, 800.0),
    "L": ScaleConfig("L", 21, 50, 1500.0, 1500.0),
    "XL": ScaleConfig("XL", 51, 100, 3000.0, 3000.0),
}


# =============================================================================
# 电路生成器抽象基类
# =============================================================================


class CircuitGenerator(ABC):
    """电路生成器抽象基类。

    所有具体生成器继承此类，实现 generate() 返回电路 JSON dict。
    """

    def __init__(self, topology: str, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        """初始化生成器。

        Args:
            topology: 拓扑名称（如 mzi_array/ring_filter）。
            scale: 规模配置。
            platform: 平台配置。
            seed: 随机种子（用于确定性生成 + 文件编号）。
        """
        self.topology = topology
        self.scale = scale
        self.platform = platform
        self.seed = seed
        self._name_counters: dict[str, int] = {}  # 器件命名计数器（按前缀分组）

    @abstractmethod
    def generate(self) -> dict:
        """生成电路 JSON dict（子类必须实现）。"""

    def _next_device_name(self, prefix: str) -> str:
        """按前缀自动生成器件名（如 dc1/dc2/wg1/wg2）。"""
        count = self._name_counters.get(prefix, 0) + 1
        self._name_counters[prefix] = count
        return f"{prefix}{count}"

    def _make_device(
        self, name: str, dev_type: str, ports: list[list],
        w: float, h: float, params: dict | None = None,
    ) -> dict:
        """构造器件 dict。"""
        return {
            "name": name, "type": dev_type,
            "width_um": float(w), "height_um": float(h),
            "ports": [list(p) for p in ports],
            "params": dict(params) if params else {},
        }

    def _make_connection(self, d1: str, p1: str, d2: str, p2: str) -> list:
        """构造连接 list。"""
        return [d1, p1, d2, p2]

    def _base_circuit_dict(self, name: str, description: str = "") -> dict:
        """构造电路 dict 基础结构。"""
        return {
            "name": name, "description": description,
            "platform": self.platform.name,
            "topology": self.topology, "scale": self.scale.name,
            "canvas_w": float(self.scale.canvas_w),
            "canvas_h": float(self.scale.canvas_h),
            "instances": {}, "devices": [], "connections": [],
            "metadata": {
                "seed": self.seed,
                "platform_source": self.platform.source_url,
                "wavelength_nm": self.platform.wavelength_nm,
                "r_min_um": self.platform.r_min_um,
                "waveguide_width_um": self.platform.waveguide_width_um,
            },
        }


# =============================================================================
# 电路序列化与校验
# =============================================================================


class CircuitSerializer:
    """电路序列化器：校验 + 写入 JSON。"""

    def serialize(self, circuit: dict, output_dir: Path, filename: str) -> Path:
        """序列化电路为 JSON 文件。

        Args:
            circuit: 电路字典。
            output_dir: 输出目录（自动创建）。
            filename: 文件名（含 .json）。

        Returns:
            写入的 JSON 文件路径。
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(
            json.dumps(circuit, indent=2, ensure_ascii=False), encoding="utf-8",
        )
        return output_path

    def validate(self, circuit: dict) -> list[str]:
        """校验电路合法性，返回错误列表（空列表表示合法）。

        校验项：name 非空、canvas_w/h > 0、devices 非空、device 字段完整、
        port direction 合法、connection 引用存在、无重复 device/port name。
        """
        errors: list[str] = []

        # name 非空
        name = circuit.get("name", "")
        if not name or not str(name).strip():
            errors.append("电路 name 为空")

        # canvas_w/canvas_h > 0
        canvas_w = float(circuit.get("canvas_w", 0))
        canvas_h = float(circuit.get("canvas_h", 0))
        if canvas_w <= 0:
            errors.append(f"canvas_w <= 0: {canvas_w}")
        if canvas_h <= 0:
            errors.append(f"canvas_h <= 0: {canvas_h}")

        # devices 列表非空
        devices = circuit.get("devices", [])
        if not devices:
            errors.append("devices 列表为空")
            return errors  # 无器件则后续校验无意义

        device_names: set[str] = set()
        port_index: dict[str, set[str]] = {}

        for i, dev in enumerate(devices):
            prefix = f"devices[{i}]"
            dev_name = dev.get("name", "")
            if not dev_name:
                errors.append(f"{prefix}.name 为空")
            if not dev.get("type"):
                errors.append(f"{prefix}.type 为空")
            if "width_um" not in dev:
                errors.append(f"{prefix} 缺少 width_um")
            if "height_um" not in dev:
                errors.append(f"{prefix} 缺少 height_um")

            # 重复 device name
            if dev_name:
                if dev_name in device_names:
                    errors.append(f"重复 device name: {dev_name}")
                device_names.add(dev_name)
                port_index[dev_name] = set()

            # ports 校验
            ports = dev.get("ports", [])
            if not isinstance(ports, list):
                errors.append(f"{prefix}.ports 不是列表")
                continue

            port_names_seen: set[str] = set()
            for j, port in enumerate(ports):
                pprefix = f"{prefix}.ports[{j}]"
                if not isinstance(port, (list, tuple)) or len(port) < 4:
                    errors.append(f"{pprefix} 格式错误（应为 [name, x, y, direction]）")
                    continue
                pname, pdir = port[0], port[3]
                if not pname:
                    errors.append(f"{pprefix}.name 为空")
                if pname in port_names_seen:
                    errors.append(f"{prefix} 内重复 port name: {pname}")
                port_names_seen.add(pname)
                if dev_name:
                    port_index[dev_name].add(pname)
                if pdir not in VALID_DIRECTIONS:
                    errors.append(f"{pprefix}.direction 非法: {pdir}")

        # connections 校验
        connections = circuit.get("connections", [])
        if not isinstance(connections, list):
            errors.append("connections 不是列表")
        else:
            for k, conn in enumerate(connections):
                cprefix = f"connections[{k}]"
                if not isinstance(conn, (list, tuple)) or len(conn) < 4:
                    errors.append(f"{cprefix} 格式错误（应为 [dev1, port1, dev2, port2]）")
                    continue
                d1, p1, d2, p2 = conn[0], conn[1], conn[2], conn[3]
                if d1 not in device_names:
                    errors.append(f"{cprefix} 引用不存在的 device: {d1}")
                if d2 not in device_names:
                    errors.append(f"{cprefix} 引用不存在的 device: {d2}")
                if d1 in port_index and p1 not in port_index[d1]:
                    errors.append(f"{cprefix} 引用 {d1} 上不存在的 port: {p1}")
                if d2 in port_index and p2 not in port_index[d2]:
                    errors.append(f"{cprefix} 引用 {d2} 上不存在的 port: {p2}")

        return errors


# =============================================================================
# 电路索引清单
# =============================================================================


class CircuitIndex:
    """电路索引清单管理器。"""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add(
        self, circuit_path: Path, topology: str, scale: str,
        platform: str, n_devices: int, name: str,
    ) -> None:
        """添加电路到索引。"""
        try:
            rel = circuit_path.relative_to(DEFAULT_OUTPUT_DIR)
            path_str = str(rel)
        except ValueError:
            path_str = str(circuit_path)
        self.entries.append({
            "path": path_str, "topology": topology, "scale": scale,
            "platform": platform, "n_devices": n_devices, "name": name,
        })

    def save(self, output_path: Path) -> Path:
        """保存索引为 JSON。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        index_data = {"total": len(self.entries), "circuits": self.entries}
        output_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8",
        )
        return output_path


# =============================================================================
# 示例生成器 1: MZI 阵列
# =============================================================================


class MZIArrayGenerator(CircuitGenerator):
    """MZI 阵列生成器。

    器件组成：2 个 DC（directional coupler）+ 2 个 waveguide（上下臂）+ 1 个 detector。
    参数来源: SiEPIC EBeam PDK（DC gap=0.2μm, coupling_length=20μm）。
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="mzi_array", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成 MZI 阵列电路。"""
        name = f"mzi_array_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(name, f"MZI 阵列 ({self.scale.name}/{self.platform.name})")

        # 器件参数（来源: SiEPIC EBeam PDK）
        dc_params = {"gap_um": 0.2, "coupling_length_um": 20.0, "source": "SiEPIC EBeam PDK"}
        wg_params = {
            "width_um": self.platform.waveguide_width_um, "length_um": 50.0,
            "source": self.platform.source_url,
        }
        det_params = {"responsivity_A_W": 0.8, "source": "SiEPIC EBeam PDK"}

        # DC 端口: in1(W), in2(W), out1(E), out2(E)
        dc_ports = [["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
                    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"]]
        # waveguide 端口: in(W), out(E)
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]
        # detector 端口: in(W)
        det_ports = [["in", 0.0, 10.0, "W"]]

        dc1 = self._next_device_name("dc")
        dc2 = self._next_device_name("dc")
        wg1 = self._next_device_name("wg")
        wg2 = self._next_device_name("wg")
        det1 = self._next_device_name("det")

        circuit["devices"] = [
            self._make_device(dc1, "directional_coupler", dc_ports, 30.0, 10.0, dc_params),
            self._make_device(dc2, "directional_coupler", dc_ports, 30.0, 10.0, dc_params),
            self._make_device(wg1, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params),
            self._make_device(wg2, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params),
            self._make_device(det1, "photodetector", det_ports, 20.0, 20.0, det_params),
        ]
        # 连接: dc1 -> wg1/wg2 -> dc2 -> det1
        circuit["connections"] = [
            self._make_connection(dc1, "out1", wg1, "in"),
            self._make_connection(dc1, "out2", wg2, "in"),
            self._make_connection(wg1, "out", dc2, "in1"),
            self._make_connection(wg2, "out", dc2, "in2"),
            self._make_connection(dc2, "out1", det1, "in"),
        ]
        return circuit


# =============================================================================
# 示例生成器 2: Ring 滤波器
# =============================================================================


class RingFilterGenerator(CircuitGenerator):
    """Ring 滤波器生成器。

    器件组成：1 个 ring + 2 个 waveguide（through bus + drop bus）+ 1 个 detector。
    参数来源: SiEPIC EBeam PDK / HyperLight LNOI（Ring radius=platform.r_min_um）。
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="ring_filter", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成 Ring 滤波器电路。"""
        name = f"ring_filter_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(name, f"Ring 滤波器 ({self.scale.name}/{self.platform.name})")

        # 器件参数
        ring_params = {
            "radius_um": self.platform.r_min_um, "gap_um": 0.2,
            "source": self.platform.source_url,
        }
        wg_params = {
            "width_um": self.platform.waveguide_width_um, "length_um": 30.0,
            "source": self.platform.source_url,
        }
        det_params = {"responsivity_A_W": 0.8, "source": self.platform.source_url}

        # Ring 端口: in(W), through(E), drop(E), add(W)
        ring_ports = [["in", 0.0, 0.0, "W"], ["through", 10.0, 0.0, "E"],
                      ["drop", 10.0, 11.0, "E"], ["add", 0.0, 11.0, "W"]]
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 30.0, 0.0, "E"]]
        det_ports = [["in", 0.0, 10.0, "W"]]

        ring1 = self._next_device_name("ring")
        wg1 = self._next_device_name("wg")
        wg2 = self._next_device_name("wg")
        det1 = self._next_device_name("det")

        circuit["devices"] = [
            self._make_device(ring1, "ring_resonator", ring_ports, 10.0, 11.0, ring_params),
            self._make_device(wg1, "strip_waveguide", wg_ports, 30.0, 0.5, wg_params),
            self._make_device(wg2, "strip_waveguide", wg_ports, 30.0, 0.5, wg_params),
            self._make_device(det1, "photodetector", det_ports, 20.0, 20.0, det_params),
        ]
        # 连接: ring.through -> wg1 -> det1; ring.drop -> wg2
        circuit["connections"] = [
            self._make_connection(ring1, "through", wg1, "in"),
            self._make_connection(wg1, "out", det1, "in"),
            self._make_connection(ring1, "drop", wg2, "in"),
        ]
        return circuit


# =============================================================================
# 生成器注册表
# =============================================================================


GENERATORS: dict[str, type[CircuitGenerator]] = {
    "mzi_array": MZIArrayGenerator,
    "ring_filter": RingFilterGenerator,
}


# =============================================================================
# 主入口
# =============================================================================


def parse_list_arg(arg: str, valid_set: dict) -> list[str]:
    """解析逗号分隔列表参数，支持 'all'。"""
    if arg.strip().lower() == "all":
        return list(valid_set.keys())
    items = [x.strip() for x in arg.split(",") if x.strip()]
    invalid = [x for x in items if x not in valid_set]
    if invalid:
        raise ValueError(f"非法值: {invalid}，合法值: {list(valid_set.keys())}")
    return items


def main() -> int:
    """主入口。返回 0 成功，1 失败。"""
    parser = argparse.ArgumentParser(description="PoLaRIS 1000 电路生成器框架")
    parser.add_argument("--topology", type=str, default="all",
                        help="拓扑名（mzi_array/ring_filter/all）")
    parser.add_argument("--scale", type=str, default="XS",
                        help="规模（XS/S/M/L/XL，默认 XS）")
    parser.add_argument("--platform", type=str, default="SOI",
                        help="平台（SOI/SiN/InP/LNOI，逗号分隔，默认 SOI）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help=f"输出目录（默认 {DEFAULT_OUTPUT_DIR}）")
    args = parser.parse_args()

    # 解析拓扑
    try:
        topologies = parse_list_arg(args.topology, GENERATORS)
    except ValueError as e:
        logger.error("%s", e)
        return 1
    # 解析平台
    try:
        platforms = parse_list_arg(args.platform, PLATFORMS)
    except ValueError as e:
        logger.error("%s", e)
        return 1
    # 校验规模
    if args.scale not in SCALES:
        logger.error("非法规模: %s，合法值: %s", args.scale, list(SCALES.keys()))
        return 1
    scale = SCALES[args.scale]

    serializer = CircuitSerializer()
    index = CircuitIndex()
    total = 0
    failed = 0

    for topology in topologies:
        gen_cls = GENERATORS[topology]
        for platform_name in platforms:
            platform = PLATFORMS[platform_name]
            gen = gen_cls(scale=scale, platform=platform, seed=args.seed)
            circuit = gen.generate()

            # 校验（规则 14.1：禁止 fall-back，校验失败必须告警）
            errors = serializer.validate(circuit)
            if errors:
                logger.error("电路 %s 校验失败:", circuit.get("name", "?"))
                for e in errors:
                    logger.error("  - %s", e)
                failed += 1
                continue

            # 序列化
            output_dir = args.output_dir / topology / scale.name / platform_name
            filename = f"{circuit['name']}.json"
            path = serializer.serialize(circuit, output_dir, filename)

            index.add(circuit_path=path, topology=topology, scale=scale.name,
                      platform=platform_name, n_devices=len(circuit["devices"]),
                      name=circuit["name"])
            total += 1
            logger.info("生成: %s (%d 器件)",
                        path.relative_to(PROJECT_ROOT), len(circuit["devices"]))

    # 保存索引
    index_path = index.save(args.output_dir / "index.json")
    logger.info("索引: %s (%d 电路)", index_path.relative_to(PROJECT_ROOT), total)

    if failed > 0:
        logger.error("生成失败: %d 个电路", failed)
        return 1

    logger.info("完成: 生成 %d 个电路", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
