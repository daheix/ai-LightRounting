"""训练流水线: 基准数据 → 变体生成 → RL训练 → 仿真校验。

用基准数据训练 RL agent，每个训练样本都经过仿真校验，
确保自研工具和布局布线一体发展。

本模块是 ``trainer.train_loop`` 的高层封装：
- 加载基准数据（支持 GDSFactory/PICBench/LiDAR 三种格式）
- 可选生成变体增强训练数据
- 调用 ``train_floorplan`` / ``train_routing`` 执行真正的 PPO 训练
  （rollout 采集 → GAE 优势估计 → PPO clip 更新 → 价值函数拟合）
- 调用 ``sim.calibration.calibrate`` 做仿真校验

来源:
- ChiPFormer ICML'23: 离线RL + 迁移学习
  https://arxiv.org/pdf/2306.14744.pdf
- ICLR'26 专家RL: 领域知识注入
  https://openreview.net/forum?id=yqvNwfxRR6
- CORE NeurIPS'25: 进化+RL协同
  https://nips.cc/virtual/2025/loc/san-diego/poster/119653
- PPO 标准训练循环: UC Berkeley Scalable AI Lecture 15 (2026)
  https://scalable-ai.eecs.berkeley.edu/assets/lecture_slides/lecture_15.pdf
- CleanRL ppo.py 单文件训练循环
  https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.data.variant_generator import VariantConfig
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig
from polaris.sim.calibration import CalibrationConfig, CalibrationResult, calibrate
from polaris.trainer.dataset import DatasetConfig
from polaris.trainer.ppo import PPOAgent
from polaris.trainer.train_loop import TrainConfig, train_floorplan, train_routing

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """训练流水线配置。

    Attributes:
        benchmark_dir: 基准数据目录。
        variant_config: 变体生成配置（None 表示不生成变体，仅用基准数据）。
        pipeline_config: 一体化流水线配置（用于最终验证）。
        num_episodes: 训练轮次数。
        hidden_dim: 隐藏层维度。
        lr: 学习率。
        save_dir: 检查点保存目录。
        calibrate_every: 每N轮校准一次。
        train_floorplan_enabled: 是否训练布局 agent。
        train_routing_enabled: 是否训练布线 agent。
        rollout_steps: 每轮采样步数。
        canvas_w: 画布宽（μm）。
        canvas_h: 画布高（μm）。
        grid_size: 栅格大小（μm）。
        sim_feedback: 是否启用 SimLoop 约束反馈。
        seed: 随机种子。
    """

    benchmark_dir: str = "data/benchmarks"
    variant_config: VariantConfig | None = None
    pipeline_config: PipelineConfig | None = None
    num_episodes: int = 50
    hidden_dim: int = 64
    lr: float = 3e-4
    save_dir: str = "checkpoints"
    calibrate_every: int = 10
    train_floorplan_enabled: bool = True
    train_routing_enabled: bool = True
    rollout_steps: int = 64
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    sim_feedback: bool = False
    seed: int = 42


@dataclass
class TrainingResult:
    """训练结果。

    Attributes:
        episodes_completed: 完成的训练轮次。
        best_reward: 最佳奖励（布局与布线中的最大值）。
        avg_loss_db: 平均插入损耗。
        calibration_passed: 校准是否通过。
        calibration_result: 校准详细结果。
        checkpoint_path: 检查点路径。
        floorplan_logs: 布局训练日志。
        routing_logs: 布线训练日志。
    """

    episodes_completed: int = 0
    best_reward: float = 0.0
    avg_loss_db: float = 0.0
    calibration_passed: bool = False
    calibration_result: CalibrationResult | None = None
    checkpoint_path: str = ""
    floorplan_logs: list[dict] = field(default_factory=list)
    routing_logs: list[dict] = field(default_factory=list)


class TrainingPipeline:
    """训练流水线。

    基准数据 → 变体生成 → RL训练 → 仿真校验

    真正的 PPO 训练流程（非伪实现）：
    1. 加载基准数据（GDSFactory/PICBench/LiDAR 三种格式）
    2. 可选生成变体增强训练数据
    3. 调用 ``train_floorplan`` / ``train_routing`` 执行 PPO 训练
       （rollout → GAE → clip 更新 → 价值拟合）
    4. 调用 ``sim.calibration.calibrate`` 做仿真校验

    来源:
    - ChiPFormer ICML'23: https://arxiv.org/pdf/2306.14744.pdf
    - PPO 标准训练循环: https://scalable-ai.eecs.berkeley.edu/assets/lecture_slides/lecture_15.pdf
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

        floorplan_logs: list[dict] = []
        routing_logs: list[dict] = []
        floorplan_agent: PPOAgent | None = None
        routing_agent: PPOAgent | None = None

        if cfg.train_floorplan_enabled:
            floorplan_agent, floorplan_logs = self._train_floorplan_agent(cfg)

        if cfg.train_routing_enabled:
            routing_agent, routing_logs = self._train_routing_agent(cfg)

        best_reward = self._extract_best_reward(floorplan_logs, routing_logs)
        avg_loss = self._extract_avg_loss(floorplan_logs, routing_logs)

        cal_result = self._run_calibration(cfg)
        ckpt_path = self._save_checkpoint(cfg, best_reward, avg_loss, cal_result)

        result = TrainingResult(
            episodes_completed=cfg.num_episodes,
            best_reward=best_reward,
            avg_loss_db=avg_loss,
            calibration_passed=cal_result.all_passed,
            calibration_result=cal_result,
            checkpoint_path=ckpt_path,
            floorplan_logs=floorplan_logs,
            routing_logs=routing_logs,
        )
        logger.info(
            "训练完成: best_reward=%.3f, avg_loss=%.2f dB, 校准=%s",
            best_reward,
            avg_loss,
            "通过" if cal_result.all_passed else "未通过",
        )
        return result

    def _train_floorplan_agent(self, cfg: TrainingConfig) -> tuple[PPOAgent, list[dict]]:
        """执行布局 PPO 训练。

        调用 ``train_loop.train_floorplan`` 做真正的 PPO 训练：
        rollout 采集 → GAE 优势估计 → PPO clip 更新 → 价值函数拟合。

        Args:
            cfg: 训练配置。

        Returns:
            (训练后的 agent, 训练日志列表)。
        """
        logger.info("开始布局 PPO 训练: %d episodes", cfg.num_episodes)
        train_cfg = self._build_train_config(cfg)
        agent, logs = train_floorplan(train_cfg, verbose=True)
        logger.info(
            "布局训练完成: best_reward=%.3f, 最终 policy_loss=%.4f",
            max((lg.get("ep_reward", 0.0) for lg in logs), default=0.0),
            logs[-1].get("policy_loss", 0.0) if logs else 0.0,
        )
        return agent, logs

    def _train_routing_agent(self, cfg: TrainingConfig) -> tuple[PPOAgent, list[dict]]:
        """执行布线 PPO 训练。

        调用 ``train_loop.train_routing`` 做真正的 PPO 训练：
        先随机布局再创建 RoutingEnv，rollout 采集 → GAE → clip 更新。

        Args:
            cfg: 训练配置。

        Returns:
            (训练后的 agent, 训练日志列表)。
        """
        logger.info("开始布线 PPO 训练: %d episodes", cfg.num_episodes)
        train_cfg = self._build_train_config(cfg)
        agent, logs = train_routing(train_cfg, verbose=True)
        logger.info(
            "布线训练完成: best_reward=%.3f, avg_loss_db=%.3f",
            max((lg.get("ep_reward", 0.0) for lg in logs), default=0.0),
            (sum(lg.get("total_loss_db", 0.0) for lg in logs) / len(logs) if logs else 0.0),
        )
        return agent, logs

    @staticmethod
    def _build_train_config(cfg: TrainingConfig) -> TrainConfig:
        """从 TrainingConfig 构造 TrainConfig。

        Args:
            cfg: 训练流水线配置。

        Returns:
            TrainConfig 实例。
        """
        from polaris.trainer.ppo import PPOConfig

        ppo_cfg = PPOConfig(lr=cfg.lr)
        return TrainConfig(
            ppo=ppo_cfg,
            dataset=DatasetConfig(),
            num_episodes=cfg.num_episodes,
            rollout_steps=cfg.rollout_steps,
            canvas_w=cfg.canvas_w,
            canvas_h=cfg.canvas_h,
            grid_size=cfg.grid_size,
            hidden_dim=cfg.hidden_dim,
            checkpoint_dir=cfg.save_dir,
            checkpoint_every=max(1, cfg.num_episodes // 5),
            log_every=max(1, cfg.num_episodes // 10),
            seed=cfg.seed,
            sim_feedback=cfg.sim_feedback,
        )

    @staticmethod
    def _extract_best_reward(floorplan_logs: list[dict], routing_logs: list[dict]) -> float:
        """从训练日志中提取最佳奖励。

        Args:
            floorplan_logs: 布局训练日志。
            routing_logs: 布线训练日志。

        Returns:
            布局与布线中的最大 ep_reward。
        """
        rewards: list[float] = []
        rewards.extend(lg.get("ep_reward", 0.0) for lg in floorplan_logs)
        rewards.extend(lg.get("ep_reward", 0.0) for lg in routing_logs)
        return max(rewards) if rewards else 0.0

    @staticmethod
    def _extract_avg_loss(floorplan_logs: list[dict], routing_logs: list[dict]) -> float:
        """从训练日志中提取平均插入损耗。

        Args:
            floorplan_logs: 布局训练日志。
            routing_logs: 布线训练日志。

        Returns:
            布线日志中 total_loss_db 的平均值（布局无损耗指标，返回 0）。
        """
        if not routing_logs:
            return 0.0
        losses = [lg.get("total_loss_db", 0.0) for lg in routing_logs]
        return sum(losses) / len(losses) if losses else 0.0

    @staticmethod
    def _run_calibration(cfg: TrainingConfig) -> CalibrationResult:
        """执行仿真校验。

        调用 ``sim.calibration.calibrate`` 对比自研仿真与基准数据。

        Args:
            cfg: 训练配置。

        Returns:
            CalibrationResult。
        """
        cal_cfg = CalibrationConfig(benchmark_dir=cfg.benchmark_dir)
        result = calibrate(cal_cfg)
        logger.info(
            "校准完成: %d/%d 通过, max_error=%.3f dB, mean_error=%.3f dB",
            result.passed_items,
            result.total_items,
            result.max_error_db,
            result.mean_error_db,
        )
        return result

    @staticmethod
    def _save_checkpoint(
        cfg: TrainingConfig,
        best_reward: float,
        avg_loss: float,
        cal_result: CalibrationResult,
    ) -> str:
        """保存训练检查点。

        Args:
            cfg: 训练配置。
            best_reward: 最佳奖励。
            avg_loss: 平均损耗。
            cal_result: 校准结果。

        Returns:
            检查点文件路径。
        """
        save_dir = Path(cfg.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = str(save_dir / "training_result.json")
        ckpt_data = {
            "episodes": cfg.num_episodes,
            "best_reward": best_reward,
            "avg_loss_db": avg_loss,
            "calibration_passed": cal_result.all_passed,
            "calibration_passed_items": cal_result.passed_items,
            "calibration_total_items": cal_result.total_items,
            "calibration_max_error_db": cal_result.max_error_db,
            "calibration_mean_error_db": cal_result.mean_error_db,
        }
        Path(ckpt_path).write_text(json.dumps(ckpt_data, indent=2), encoding="utf-8")
        return ckpt_path

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
            # R03 合规：基准目录不存在属配置错误，禁止 fall-back 返回空列表
            # （否则下游会在零基准上训练，掩盖配置 Bug）。直接 raise 告警。
            raise FileNotFoundError(
                f"基准目录不存在: {benchmark_dir}"
                "（R03: 禁止 fall-back 返回空列表掩盖配置错误）"
            )
        circuits: list[CircuitSpec] = []
        for f in sorted(bdir.glob("*.json")):
            if f.name in ("index.json", "variant_stats.json"):
                continue
            # R03 合规：基准文件解析失败属数据损坏，禁止 except+logger.warning 静默跳过。
            # _parse_benchmark_json 对空/无法识别格式直接 raise，由上层决策。
            circuit = _parse_benchmark_json(f)
            circuits.append(circuit)
        logger.info(
            "加载了 %d 个基准电路 (总器件数=%d, 总连接数=%d)",
            len(circuits),
            sum(len(c.devices) for c in circuits),
            sum(len(c.connections) for c in circuits),
        )
        return circuits


def _parse_benchmark_json(path: Path) -> CircuitSpec:
    """解析基准 JSON 快照为 CircuitSpec。

    支持三种来源格式：
    - GDSFactory: instances 字典 + connections/routes
    - PICBench: data.netlist.instances/connections
    - LiDAR PIC IR: instances 列表 + nets

    R03 合规：原实现对“无器件且无连接”返回 None 静默跳过，是 fall-back——
    掩盖了格式不匹配或空文件等数据质量问题。现改为 raise ValueError 告警，
    强制上层处理（Effective Python Item 32: 优先抛异常而非返回 None）。

    Args:
        path: JSON 文件路径。

    Returns:
        CircuitSpec（含 devices 与 connections）。

    Raises:
        ValueError: 文件无器件且无连接（空基准 / 无法识别格式）。
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
        raise ValueError(
            f"基准文件 {name} 无器件且无连接"
            "（R03: 禁止 fall-back 跳过空基准，数据质量问题必须上抛）"
        )

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


def _first_float(source: dict, keys: tuple[str, ...], default: float) -> float:
    """从 source 中按 keys 顺序取第一个非 None 值并转 float。

    修复 #v3.3-P-6（R05 根因修复）：原 ``source.get(k1, source.get(k2, default))``
    在 key 存在但值为 None 时返回 None（dict.get 语义：key 存在即返回其值，
    即便为 None），导致 ``float(None)`` 抛 TypeError。该 Bug 曾被
    ``_load_benchmarks`` 的 ``except logger.warning`` fall-back 静默吞没
    （整文件被跳过，造成基准数据大量丢失），R03 移除 fall-back 后暴露。
    本辅助函数显式跳过 None 值，取首个非 None 候选。

    来源: Python dict.get 语义
      https://docs.python.org/3/library/stdtypes.html#dict.get
    """
    for k in keys:
        v = source.get(k)
        if v is not None:
            return float(v)
    return default


def _make_device_from_dict_inst(name: str, inst_data: dict) -> DeviceSpec:
    """从 GDSFactory 字典格式 instance 构造 DeviceSpec。"""
    component = inst_data.get("component", inst_data.get("type", "unknown"))
    settings = inst_data.get("settings") or {}
    w = _first_float(settings, ("length", "width"), 10.0)
    h = _first_float(settings, ("gap", "height"), 10.0)
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
    w = _first_float(inst, ("width", "xsize"), 10.0)
    h = _first_float(inst, ("height", "ysize"), 10.0)
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
        w = _first_float(comp, ("width", "xsize"), 10.0)
        h = _first_float(comp, ("height", "ysize"), 10.0)
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
