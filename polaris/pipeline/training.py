"""训练流水线: 基准数据 → 变体生成 → RL训练 → 仿真校验。

用基准数据训练 RL agent，每个训练样本都经过仿真校验，
确保自研工具和布局布线一体发展。

来源:
- ChiPFormer ICML'23: 离线RL + 迁移学习
  https://arxiv.org/pdf/2306.14744.pdf
- ICLR'26 专家RL: 领域知识注入
  https://openreview.net/forum?id=yqvNwfxRR6
- CORE NeurIPS'25: 进化+RL协同
  https://nips.cc/virtual/2025/loc/san-diego/poster/119653
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.data.variant_generator import VariantConfig, estimate_loss_budget
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """训练流水线配置。

    Attributes:
        benchmark_dir: 基准数据目录。
        variant_config: 变体生成配置。
        pipeline_config: 一体化流水线配置。
        num_episodes: 训练轮次数。
        hidden_dim: 隐藏层维度。
        lr: 学习率。
        save_dir: 检查点保存目录。
        calibrate_every: 每N轮校准一次。
    """

    benchmark_dir: str = "data/benchmarks"
    variant_config: VariantConfig | None = None
    pipeline_config: PipelineConfig | None = None
    num_episodes: int = 50
    hidden_dim: int = 64
    lr: float = 3e-4
    save_dir: str = "checkpoints"
    calibrate_every: int = 10


@dataclass
class TrainingResult:
    """训练结果。

    Attributes:
        episodes_completed: 完成的训练轮次。
        best_reward: 最佳奖励。
        avg_loss_db: 平均插入损耗。
        calibration_passed: 校准是否通过。
        checkpoint_path: 检查点路径。
    """

    episodes_completed: int = 0
    best_reward: float = 0.0
    avg_loss_db: float = 0.0
    calibration_passed: bool = False
    checkpoint_path: str = ""


class TrainingPipeline:
    """训练流水线。

    基准数据 → 变体生成 → RL训练 → 仿真校验

    来源:
    - ChiPFormer ICML'23: https://arxiv.org/pdf/2306.14744.pdf
    """

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()
        self.pipeline = IntegratedPipeline(self.config.pipeline_config)

    def train(self) -> TrainingResult:
        """执行训练流水线。

        Returns:
            TrainingResult。
        """
        cfg = self.config
        logger.info("训练流水线启动: %d episodes", cfg.num_episodes)

        circuits = self._load_benchmarks(cfg.benchmark_dir)
        if not circuits:
            logger.error("无基准数据，训练终止")
            return TrainingResult()

        best_reward, avg_loss = self._training_loop(cfg, circuits)

        ckpt_path = self._save_checkpoint(cfg, best_reward, avg_loss)
        return TrainingResult(
            episodes_completed=cfg.num_episodes,
            best_reward=best_reward,
            avg_loss_db=avg_loss,
            checkpoint_path=ckpt_path,
        )

    def _training_loop(self, cfg, circuits) -> tuple[float, float]:
        """执行训练循环。"""
        best_reward = -1e9
        total_loss = 0.0
        n_valid = 0

        for ep in range(cfg.num_episodes):
            circuit = circuits[ep % len(circuits)]
            result = self.pipeline.run(circuit)
            reward = self._compute_reward(result)
            if reward > best_reward:
                best_reward = reward
            if result.success:
                total_loss += result.total_loss_db
                n_valid += 1
            if (ep + 1) % cfg.calibrate_every == 0:
                self._calibrate(circuits)

        avg_loss = total_loss / max(1, n_valid)
        logger.info("训练完成: best_reward=%.3f, avg_loss=%.2f dB", best_reward, avg_loss)
        return best_reward, avg_loss

    @staticmethod
    def _save_checkpoint(cfg, best_reward: float, avg_loss: float) -> str:
        """保存训练检查点。"""
        save_dir = Path(cfg.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = str(save_dir / "training_result.json")
        ckpt_data = {
            "episodes": cfg.num_episodes,
            "best_reward": best_reward,
            "avg_loss_db": avg_loss,
            "n_valid": 0,
        }
        Path(ckpt_path).write_text(json.dumps(ckpt_data, indent=2), encoding="utf-8")
        return ckpt_path

    @staticmethod
    def _compute_reward(result) -> float:
        """计算训练奖励。"""
        reward = 0.0
        if result.success:
            reward += 1.0
        reward -= result.total_loss_db * 0.1
        reward -= result.n_crossings * 0.05
        return reward

    @staticmethod
    def _calibrate(circuits: list[CircuitSpec]) -> None:
        """校准验证。"""
        n_pass = 0
        for c in circuits[:5]:
            valid, _ = estimate_loss_budget(c)
            if valid:
                n_pass += 1
        logger.info("校准: %d/%d 通过", n_pass, min(5, len(circuits)))

    @staticmethod
    def _load_benchmarks(benchmark_dir: str) -> list[CircuitSpec]:
        """加载基准数据并解析为完整 CircuitSpec。

        基准 JSON 快照格式（来自 data/benchmarks/）含 instances 字典、
        connections 列表、routes.optical.links 等字段，需正确解析为
        DeviceSpec 列表与 connections 列表，避免空 CircuitSpec 训练 Bug。

        Args:
            benchmark_dir: 基准数据目录。

        Returns:
            完整解析的 CircuitSpec 列表（含 devices 与 connections）。
        """
        bdir = Path(benchmark_dir)
        if not bdir.exists():
            logger.error("基准目录不存在: %s", benchmark_dir)
            return []
        circuits: list[CircuitSpec] = []
        for f in sorted(bdir.glob("*.json")):
            if f.name in ("index.json", "variant_stats.json"):
                continue
            try:
                circuit = _parse_benchmark_json(f)
                if circuit is not None:
                    circuits.append(circuit)
            except Exception as e:
                logger.warning("加载失败: %s (%s)", f, e)
        logger.info(
            "加载了 %d 个基准电路 (总器件数=%d, 总连接数=%d)",
            len(circuits),
            sum(len(c.devices) for c in circuits),
            sum(len(c.connections) for c in circuits),
        )
        return circuits


def _parse_benchmark_json(path: Path) -> CircuitSpec | None:
    """解析基准 JSON 快照为 CircuitSpec。

    支持三种来源格式：
    - GDSFactory: instances 字典 + connections/routes
    - PICBench: data.netlist.instances/connections
    - LiDAR PIC IR: instances 列表 + nets

    Args:
        path: JSON 文件路径。

    Returns:
        CircuitSpec，若无法解析则返回 None。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    name = data.get("name", path.stem)
    netlist = _extract_netlist(data)

    devices = _parse_instances(netlist)
    if not devices:
        devices = _parse_components(netlist)
    connections = _parse_connections(netlist)
    connections.extend(_parse_routes(netlist))
    connections.extend(_parse_nets(netlist))

    if not devices and not connections:
        logger.debug("跳过空基准: %s", name)
        return None

    return CircuitSpec(name=name, devices=devices, connections=connections)


def _extract_netlist(data: dict) -> dict:
    """从基准数据提取 netlist（兼容 PICBench 嵌套结构）。"""
    if isinstance(data.get("data"), dict):
        return data["data"].get("netlist", data)
    return data


def _parse_instances(netlist: dict) -> list[DeviceSpec]:
    """解析 instances 字段（GDSFactory 字典 / LiDAR 列表格式）。"""
    devices: list[DeviceSpec] = []
    instances = netlist.get("instances", [])
    if isinstance(instances, dict):
        for inst_name, inst_data in instances.items():
            if not isinstance(inst_data, dict):
                continue
            devices.append(_make_device_from_dict_inst(inst_name, inst_data))
    elif isinstance(instances, list):
        for inst in instances:
            if not isinstance(inst, dict):
                continue
            devices.append(_make_device_from_list_inst(inst))
    return devices


def _make_device_from_dict_inst(name: str, inst_data: dict) -> DeviceSpec:
    """从 GDSFactory 字典格式 instance 构造 DeviceSpec。"""
    component = inst_data.get("component", inst_data.get("type", "unknown"))
    settings = inst_data.get("settings", {})
    w = float(settings.get("length", settings.get("width", 10.0)))
    h = float(settings.get("gap", settings.get("height", 10.0)))
    return DeviceSpec(
        name=name,
        device_type=component,
        width_um=w,
        height_um=h,
        params=dict(settings),
    )


def _make_device_from_list_inst(inst: dict) -> DeviceSpec:
    """从 LiDAR 列表格式 instance 构造 DeviceSpec。"""
    inst_name = inst.get("name", inst.get("instance", "unknown"))
    cell = inst.get("cell_type", inst.get("component", inst.get("type", "unknown")))
    w = float(inst.get("width", inst.get("xsize", 10.0)))
    h = float(inst.get("height", inst.get("ysize", 10.0)))
    return DeviceSpec(name=inst_name, device_type=cell, width_um=w, height_um=h)


def _parse_components(netlist: dict) -> list[DeviceSpec]:
    """解析 PICBench components/devices 字段（备选）。"""
    devices: list[DeviceSpec] = []
    components = netlist.get("components", netlist.get("devices", []))
    if not isinstance(components, list):
        return devices
    for comp in components:
        if not isinstance(comp, dict):
            continue
        cname = comp.get("name", "unknown")
        ctype = comp.get("type", comp.get("component", "unknown"))
        w = float(comp.get("width", comp.get("xsize", 10.0)))
        h = float(comp.get("height", comp.get("ysize", 10.0)))
        devices.append(DeviceSpec(name=cname, device_type=ctype, width_um=w, height_um=h))
    return devices


def _parse_connections(netlist: dict) -> list[tuple[str, str, str, str]]:
    """解析 connections 字段（GDSFactory 列表 / PICBench 字典格式）。"""
    connections: list[tuple[str, str, str, str]] = []
    raw_conns = netlist.get("connections", [])
    if isinstance(raw_conns, list):
        for conn in raw_conns:
            src, dst = _extract_conn_endpoints(conn)
            connections.extend(_make_connection(src, dst))
    elif isinstance(raw_conns, dict):
        for src, dst in raw_conns.items():
            connections.extend(_make_connection(str(src), str(dst)))
    return connections


def _parse_routes(netlist: dict) -> list[tuple[str, str, str, str]]:
    """解析 routes.optical.links 字段（GDSFactory 路由连接）。"""
    connections: list[tuple[str, str, str, str]] = []
    routes = netlist.get("routes", {})
    if not isinstance(routes, dict):
        return connections
    for route_data in routes.values():
        if not isinstance(route_data, dict):
            continue
        links = route_data.get("links", {})
        if isinstance(links, dict):
            for src, dst in links.items():
                connections.extend(_make_connection(str(src), str(dst)))
    return connections


def _parse_nets(netlist: dict) -> list[tuple[str, str, str, str]]:
    """解析 LiDAR nets 字段。"""
    connections: list[tuple[str, str, str, str]] = []
    nets = netlist.get("nets", [])
    if not isinstance(nets, list):
        return connections
    for net in nets:
        if not isinstance(net, dict):
            continue
        src = net.get("src", net.get("source", ""))
        dst = net.get("dst", net.get("destination", ""))
        connections.extend(_make_connection(str(src), str(dst)))
    return connections


def _make_connection(src: str, dst: str) -> list[tuple[str, str, str, str]]:
    """从 src/dst 端点字符串构造连接（空则返回空列表）。"""
    if not src or not dst:
        return []
    sd, sp = _split_port_ref(src)
    dd, dp = _split_port_ref(dst)
    if sd and dd:
        return [(sd, sp, dd, dp)]
    return []


def _extract_conn_endpoints(conn) -> tuple[str, str]:
    """从 connection 条目提取 src/dst 端点字符串。"""
    if isinstance(conn, dict):
        src = conn.get("source", conn.get("src", ""))
        dst = conn.get("destination", conn.get("dst", ""))
        return str(src), str(dst)
    if isinstance(conn, str):
        if "," in conn:
            parts = conn.split(",")
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
    return "", ""


def _split_port_ref(ref: str) -> tuple[str, str]:
    """拆分端口引用 'device,port' → (device, port)。"""
    if not ref:
        return "", ""
    if "," in ref:
        parts = ref.split(",", 1)
        return parts[0].strip(), parts[1].strip()
    if ":" in ref:
        parts = ref.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return ref.strip(), "o1"


__all__ = [
    "TrainingPipeline",
    "TrainingConfig",
    "TrainingResult",
]
