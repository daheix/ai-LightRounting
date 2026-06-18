"""训练数据集合成（Task 14）。

随机生成不同规模/拓扑的光子电路网表，用于训练布局/布线 RL 智能体。
覆盖 MZI 链、滤波器组、WDM、交叉开关等典型光子电路拓扑。

拓扑参考：
- gdsfactory 的示例电路（MZI、ring filter、WDM）
  来源: https://gdsfactory.github.io/gdsfactory/
- Basso et al., NeurIPS 2025 模拟 IC floorplanning 数据集
  来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- LiDAR (ISPD 2025) 光子电路自动布线数据集
  来源: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np
import yaml

from polaris.pdk.catalog import build_default_catalog


@dataclass
class DatasetConfig:
    """数据集生成配置。"""

    num_netlists: int = 50
    min_devices: int = 3
    max_devices: int = 12
    platforms: tuple[str, ...] = ("SOI",)
    seed: int = 42
    topology_types: tuple[str, ...] = (
        "chain",
        "tree",
        "mzi_chain",
        "ring_filter",
        "random_mesh",
    )


def _pick_components(catalog, platform: str, n: int, rng: random.Random) -> list[str]:
    """从平台器件中随机挑选 n 个（优先被动器件）。"""
    names = catalog.names(platform=platform)
    passive = [n for n in names if catalog.get(n, platform=platform).category == "passive"]
    pool = passive if len(passive) >= n else names
    if not pool:
        pool = names
    return [rng.choice(pool) for _ in range(n)]


def _make_chain(inst_ids: list[str], catalog, platform, rng) -> list:
    """链式拓扑：d0-d1-d2-..."""
    conns = []
    for i in range(len(inst_ids) - 1):
        conns.append(_random_connection(inst_ids[i], inst_ids[i + 1], catalog, platform, rng))
    return conns


def _make_tree(inst_ids: list[str], catalog, platform, rng) -> list:
    """树形拓扑：以第一个为根。"""
    conns = []
    for i in range(1, len(inst_ids)):
        parent = inst_ids[(i - 1) // 2]
        conns.append(_random_connection(parent, inst_ids[i], catalog, platform, rng))
    return conns


def _make_mzi_chain(inst_ids: list[str], catalog, platform, rng) -> list:
    """MZI 链：每对器件经 MMI 上下臂连接。"""
    conns = []
    for i in range(0, len(inst_ids) - 1, 2):
        a, b = inst_ids[i], inst_ids[i + 1]
        conns.append(_random_connection(a, b, catalog, platform, rng))
        if i + 2 < len(inst_ids):
            conns.append(_random_connection(a, inst_ids[i + 2], catalog, platform, rng))
    return conns


def _make_ring_filter(inst_ids: list[str], catalog, platform, rng) -> list:
    """环滤波器拓扑：串联 + 旁路。"""
    conns = _make_chain(inst_ids, catalog, platform, rng)
    # 添加旁路连接
    for i in range(0, len(inst_ids) - 2, 2):
        conns.append(_random_connection(inst_ids[i], inst_ids[i + 2], catalog, platform, rng))
    return conns


def _make_random_mesh(inst_ids: list[str], catalog, platform, rng) -> list:
    """随机网格拓扑。"""
    conns = []
    n_edges = max(len(inst_ids) - 1, rng.randint(len(inst_ids), 2 * len(inst_ids)))
    for _ in range(n_edges):
        a, b = rng.sample(inst_ids, 2)
        conns.append(_random_connection(a, b, catalog, platform, rng))
    return conns


def _random_connection(src: str, dst: str, catalog, platform, rng) -> list:
    """随机生成一条连接（自动选可用端口）。"""
    dev_src = catalog.get(src, platform=platform) if src in catalog.names(platform) else None
    dev_dst = catalog.get(dst, platform=platform) if dst in catalog.names(platform) else None
    src_port = rng.choice([p.name for p in dev_src.ports]) if dev_src and dev_src.ports else "out"
    dst_port = rng.choice([p.name for p in dev_dst.ports]) if dev_dst and dev_dst.ports else "in"
    return [src, src_port, dst, dst_port]


_TOPOLOGY_BUILDERS = {
    "chain": _make_chain,
    "tree": _make_tree,
    "mzi_chain": _make_mzi_chain,
    "ring_filter": _make_ring_filter,
    "random_mesh": _make_random_mesh,
}


def generate_netlist(
    config: DatasetConfig | None = None,
    idx: int = 0,
) -> dict:
    """生成单个随机网表（字典形式，可 YAML 序列化）。"""
    config = config or DatasetConfig()
    rng = random.Random(config.seed + idx)
    platform = rng.choice(config.platforms)
    catalog = build_default_catalog()
    n_devices = rng.randint(config.min_devices, config.max_devices)
    components = _pick_components(catalog, platform, n_devices, rng)
    inst_ids = [f"{platform.lower()}_{i}" for i in range(n_devices)]
    topology = rng.choice(config.topology_types)
    builder = _TOPOLOGY_BUILDERS[topology]
    connections = builder(inst_ids, catalog, platform, rng)
    return {
        "name": f"net_{idx:04d}_{topology}",
        "platform": platform,
        "topology": topology,
        "instances": {
            iid: {"component": comp, "platform": platform}
            for iid, comp in zip(inst_ids, components, strict=True)
        },
        "connections": connections,
    }


def generate_dataset(
    config: DatasetConfig | None = None,
) -> list[dict]:
    """生成完整数据集（网表字典列表）。"""
    config = config or DatasetConfig()
    return [generate_netlist(config, i) for i in range(config.num_netlists)]


def save_dataset(netlists: list[dict], path: str) -> None:
    """保存数据集为单个 YAML 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"netlists": netlists}, f, allow_unicode=True, sort_keys=False)


def load_dataset(path: str) -> list[dict]:
    """加载数据集。"""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["netlists"]


# ---------------------------------------------------------------------------
# SubTask 14.2: BaselineSolver — 用经典布线器生成 baseline 解，标注奖励
# ---------------------------------------------------------------------------
def _baseline_floorplan(net, devices, canvas_w, canvas_h, grid_size):
    """随机布局（baseline 不学习，仅随机放置），返回放置结果。"""
    from polaris.engine.floorplan_env import FloorplanEnv

    fp_env = FloorplanEnv(
        net,
        devices,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        grid_size=grid_size,
    )
    fp_env.reset()
    for _ in range(len(devices)):
        fp_env.step(fp_env.action_space.sample())
    return fp_env.state.placements


def _baseline_route(net, placements, canvas_w, canvas_h, grid_size):
    """经典 A* 布线，返回 (累计奖励, 指标字典)。"""
    from polaris.router.routing_env import RoutingEnv

    rt_env = RoutingEnv(
        net,
        placements,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        grid_size=grid_size,
    )
    rt_env.reset()
    total_reward = 0.0
    for _ in range(len(net.connections)):
        _, reward, terminated, _, _ = rt_env.step(np.zeros(3, dtype=np.float32))
        total_reward += reward
        if terminated:
            break
    return total_reward, rt_env.total_metrics()


@dataclass
class DatasetSample:
    """单个训练样本（网表 + baseline 解 + 奖励标注）。

    Attributes:
        netlist: 网表字典（YAML 可序列化）。
        baseline_reward: 经典布线器求解的奖励（用作 RL 基线对比）。
        baseline_metrics: baseline 解的指标（总线长/损耗/拥塞等）。
    """

    netlist: dict
    baseline_reward: float = 0.0
    baseline_metrics: dict = field(default_factory=dict)


class BaselineSolver:
    """经典布线器 baseline 解生成器（SubTask 14.2）。

    用 RoutingEnv（内含 A* GridRouter）对网表执行布局+布线，计算奖励作为 RL 基线。
    RL 智能体的奖励可与 baseline 对比，评估学习效果。

    方法参考:
    - LiDAR (ISPD 2025) 经典 A* 光波导布线作为 baseline
      https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - Basso et al., NeurIPS 2025 baseline 解用于奖励对比
      https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
    """

    def __init__(self) -> None:
        pass

    def solve(
        self,
        netlist_dict: dict,
        canvas_w: float = 1000.0,
        canvas_h: float = 1000.0,
        grid_size: float = 10.0,
    ) -> DatasetSample:
        """对单个网表生成 baseline 解并标注奖励。

        Args:
            netlist_dict: 网表字典（YAML 可序列化）。
            canvas_w: 画布宽（μm）。
            canvas_h: 画布高（μm）。
            grid_size: 网格大小（μm）。

        Returns:
            含 baseline 奖励与指标的 ``DatasetSample``。
        """
        from polaris.engine.netlist import load_netlist

        net, devices, _ = load_netlist(netlist_dict)
        placements = _baseline_floorplan(net, devices, canvas_w, canvas_h, grid_size)
        total_reward, metrics = _baseline_route(net, placements, canvas_w, canvas_h, grid_size)
        return DatasetSample(
            netlist=netlist_dict,
            baseline_reward=total_reward,
            baseline_metrics=metrics,
        )


def generate_training_dataset(
    config: DatasetConfig | None = None,
    canvas_w: float = 1000.0,
    canvas_h: float = 1000.0,
    grid_size: float = 10.0,
) -> list[DatasetSample]:
    """生成完整训练数据集（含 baseline 解与奖励标注）。

    对每个生成的网表用 BaselineSolver 求解并标注奖励，
    供 PPO 训练时对比评估。

    Args:
        config: 数据集配置。
        canvas_w: 画布宽（μm）。
        canvas_h: 画布高（μm）。
        grid_size: 网格大小（μm）。

    Returns:
        ``DatasetSample`` 列表。
    """
    config = config or DatasetConfig()
    netlists = generate_dataset(config)
    solver = BaselineSolver()
    samples: list[DatasetSample] = []
    for nl in netlists:
        np.random.seed(config.seed)  # 可复现
        sample = solver.solve(nl, canvas_w, canvas_h, grid_size)
        samples.append(sample)
    return samples
