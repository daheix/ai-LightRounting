"""训练数据集合成（Task 14）。

随机生成不同规模/拓扑的光子电路网表，用于训练布局/布线 RL 智能体。
覆盖 MZI 链、滤波器组、WDM、交叉开关等典型光子电路拓扑，并用经典 A*
布线器生成 baseline 解与奖励标注。

方案检索（见项目规则 1.1）：
- NeurIPS 2022 Cheng et al. 策略梯度 + 生成式布线（SJTU+华为）
  来源: https://openreview.net/pdf?id=uNYqDfPEDD8
- ICML 2025 Lee et al. Chip Placement with Diffusion Models：合成网表与放置
  数据集生成方法（逆问题：给定放置反推合理网表更易求解）
  来源: https://openreview.net/forum?id=crCPLUtIuU
- PoLaRIS 框架（Apollo 布局器 + LiDAR 曲线感知 A* 布线器）
  来源: https://arxiv.org/pdf/2507.22301
- Basso et al., NeurIPS 2025 RL+R-GCN 模拟 IC 布局感知 floorplanning 数据集
  来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- gdsfactory 的示例电路网表（MZI、ring filter、WDM）
  来源: https://gdsfactory.github.io/gdsfactory/

网表生成策略：
1. 从器件库按平台随机选器件实例
2. 用随机生成树保证连通性，再追加随机边至目标连接数
3. 每条连接从器件真实端口中随机选取（保证端口名有效，可被布线器解析）
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Any

import yaml

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import (
    Netlist,
    NetlistConnection,
    NetlistInstance,
    instantiate_devices,
    parse_netlist,
)
from polaris.pdk.catalog import DeviceCatalog, build_default_catalog
from polaris.pdk.device import Device
from polaris.router import Route, WaveguideRouter
from polaris.router.waveguide_router import get_platform_constraints

# ---------------------------------------------------------------------------
# 奖励权重（综合面积利用率、总线长、总损耗、交叉数；越小奖励越高）
# ---------------------------------------------------------------------------
_REWARD_AREA = 1.0  # 面积利用率权重（利用率 ∈ [0,1]，越高越好）
_REWARD_LENGTH = 1e-4  # 总线长权重（μm 量级，需小系数）
_REWARD_LOSS = 0.1  # 总损耗权重（dB 量级）
_REWARD_CROSS = 5e-2  # 交叉数权重（整数计数）


# ---------------------------------------------------------------------------
# SubTask 14.1: NetlistGenerator —— 从器件库随机生成训练网表
# ---------------------------------------------------------------------------
class NetlistGenerator:
    """从器件库随机生成训练网表。

    生成流程：按平台从 ``DeviceCatalog`` 随机选取器件实例，用随机生成树
    保证图连通性，再追加随机边至目标连接数；每条连接从器件真实端口中随机
    选取，保证端口名可被 ``WaveguideRouter`` 解析。

    来源：NeurIPS 2022 Cheng et al. 生成式布线训练数据需求；
          ICML 2025 Lee et al. 合成网表数据集生成方法。
    """

    def __init__(self, catalog: DeviceCatalog, seed: int | None = None) -> None:
        self.catalog = catalog
        self.seed = seed

    def generate(
        self, num_devices: int, num_nets: int, platform: str = "SOI"
    ) -> Netlist:
        """生成随机网表。

        Args:
            num_devices: 器件数量（10/100/1000 级）。
            num_nets: 连接数量（>= num_devices-1 时保证连通性）。
            platform: 平台（SOI/SiN/InP/LNOI）。

        Returns:
            含 ``num_devices`` 个实例与至多 ``num_nets`` 条连接的 ``Netlist``。
        """
        if num_devices <= 0:
            raise ValueError("num_devices 须为正整数")
        if num_nets < 0:
            raise ValueError("num_nets 须为非负整数")
        rng = random.Random(self.seed)
        pool = self.catalog.list_by_platform(platform)
        if not pool:
            raise ValueError(f"平台 {platform} 无可用器件")

        # 随机选取 num_devices 个器件（允许重复类型，模拟同类型多实例）
        chosen: list[Device] = [rng.choice(pool) for _ in range(num_devices)]
        inst_ids = [f"{platform.lower()}_{i}" for i in range(num_devices)]
        instances = [
            NetlistInstance(
                instance_id=iid,
                component=dev.name,
                platform=platform,
            )
            for iid, dev in zip(inst_ids, chosen)
        ]
        connections = self._generate_connections(inst_ids, chosen, num_nets, rng)
        name = f"net_{platform}_{num_devices}d_{num_nets}n"
        return Netlist(instances=instances, connections=connections, name=name)

    def generate_batch(self, count: int, sizes: list[int]) -> list[Netlist]:
        """批量生成不同规模网表。

        Args:
            count: 生成网表数量。
            sizes: 器件规模候选列表（如 [10, 50, 100]），按序轮转选取。

        Returns:
            ``count`` 个 ``Netlist``，规模从 ``sizes`` 中轮转选取。
        """
        if count <= 0:
            return []
        if not sizes:
            raise ValueError("sizes 不能为空")
        # 默认平台：优先 SOI，否则取首个已注册平台
        platform = "SOI" if "SOI" in self.catalog.platforms else self.catalog.platforms[0]
        result: list[Netlist] = []
        for i in range(count):
            num_devices = sizes[i % len(sizes)]
            # 连接数：器件数的 1.2 倍，保证连通且有少量冗余边
            num_nets = max(num_devices - 1, int(num_devices * 1.2))
            # 每个网表用独立子种子，保证可复现且互不相同
            sub_seed = (self.seed or 0) + i * 1009 + num_devices
            gen = NetlistGenerator(self.catalog, seed=sub_seed)
            result.append(gen.generate(num_devices, num_nets, platform=platform))
        return result

    # -- 内部方法 --

    def _generate_connections(
        self,
        inst_ids: list[str],
        devices: list[Device],
        num_nets: int,
        rng: random.Random,
    ) -> list[NetlistConnection]:
        """生成连接列表（随机生成树保证连通 + 随机额外边）。"""
        n = len(inst_ids)
        if n < 2 or num_nets <= 0:
            return []
        edges: list[tuple[int, int]] = []
        # 随机生成树：随机排列后，每个节点连到已连通集合中的随机节点
        order = list(range(n))
        rng.shuffle(order)
        tree_budget = min(num_nets, n - 1)  # 生成树最多用 num_nets 条
        connected: set[int] = {order[0]}
        for idx in order[1:]:
            if len(edges) >= tree_budget:
                break
            parent = rng.choice(list(connected))
            edges.append((parent, idx))
            connected.add(idx)
        # 追加随机边至 num_nets（避免重复无序对）
        existing = {(min(a, b), max(a, b)) for a, b in edges}
        max_pairs = n * (n - 1) // 2
        attempts = 0
        max_attempts = num_nets * 10 + 20
        while len(edges) < num_nets and len(existing) < max_pairs and attempts < max_attempts:
            a, b = rng.sample(range(n), 2)
            key = (min(a, b), max(a, b))
            if key not in existing:
                existing.add(key)
                edges.append((a, b))
            attempts += 1
        # 转为 NetlistConnection，从器件真实端口中随机选取
        conns: list[NetlistConnection] = []
        for a, b in edges:
            src_port = self._pick_port(devices[a], rng)
            dst_port = self._pick_port(devices[b], rng)
            conns.append(
                NetlistConnection(
                    src_instance=inst_ids[a],
                    src_port=src_port,
                    dst_instance=inst_ids[b],
                    dst_port=dst_port,
                )
            )
        return conns

    @staticmethod
    def _pick_port(device: Device, rng: random.Random) -> str:
        """从器件真实端口中随机选一个端口名（无端口时回退 'out'）。"""
        if device.ports:
            return rng.choice(device.ports).name
        return "out"


# ---------------------------------------------------------------------------
# SubTask 14.2: BaselineSolver —— 经典布线器生成 baseline 解与奖励
# ---------------------------------------------------------------------------
class BaselineSolver:
    """用经典布线器生成 baseline 解，标注奖励。

    流程：实例化器件 → 行式贪心放置（避免重叠）→ ``WaveguideRouter`` A* 布线
    → 计算指标（总线长/总损耗/交叉数/面积）→ 综合奖励。

    来源：经典 A* 网格布线（Hart, Nilsson & Raphael 1968）；
          PoLaRIS LiDAR 曲线感知 A*（https://arxiv.org/pdf/2507.22301）。
    """

    def __init__(self, router: WaveguideRouter) -> None:
        self.router = router

    def solve(self, netlist: Netlist) -> dict[str, Any]:
        """求解并返回 baseline 解。

        Returns:
            ``{"placements": dict[str, Placement], "routes": list[Route],
            "metrics": {"total_length", "total_loss_db", "num_crossings", "area"},
            "reward": float}``。
        """
        devices = instantiate_devices(netlist)
        placements = self._place(devices)
        routes = self.router.route(netlist, placements)
        metrics = self._compute_metrics(routes, placements)
        reward = self._compute_reward(metrics, devices)
        return {
            "placements": placements,
            "routes": routes,
            "metrics": metrics,
            "reward": reward,
        }

    def _place(self, devices: dict[str, Device]) -> dict[str, Placement]:
        """行式贪心放置：从左到右排列，超出画布宽度则换行（避免重叠）。"""
        # 估算画布尺寸：器件总面积平方根 * 3（留布线空间）
        total_area = 0.0
        for dev in devices.values():
            w, h = dev.footprint()
            total_area += max(w, 1.0) * max(h, 1.0)
        side = math.sqrt(total_area) * 3.0
        canvas = max(side, 500.0)
        margin = 10.0
        spacing = max(self.router.min_spacing, 5.0)
        x = margin
        y = margin
        row_height = 0.0
        placements: dict[str, Placement] = {}
        for inst_id, dev in devices.items():
            w, h = dev.footprint()
            w = max(w, 1.0)
            h = max(h, 1.0)
            if x + w > canvas - margin:
                x = margin
                y += row_height + spacing
                row_height = 0.0
            placements[inst_id] = Placement(
                instance_id=inst_id, device=dev, x=x, y=y, rotation=0
            )
            x += w + spacing
            row_height = max(row_height, h)
        return placements

    @staticmethod
    def _compute_metrics(
        routes: list[Route], placements: dict[str, Placement]
    ) -> dict[str, float]:
        """计算 baseline 指标：总线长、总损耗、交叉数、放置包围盒面积。"""
        total_length = sum(r.length for r in routes)
        total_loss_db = sum(r.loss_db for r in routes)
        num_crossings = sum(r.num_crossings for r in routes)
        if placements:
            xs_min = min(pl.bbox_abs()[0] for pl in placements.values())
            ys_min = min(pl.bbox_abs()[1] for pl in placements.values())
            xs_max = max(pl.bbox_abs()[2] for pl in placements.values())
            ys_max = max(pl.bbox_abs()[3] for pl in placements.values())
            area = (xs_max - xs_min) * (ys_max - ys_min)
        else:
            area = 0.0
        return {
            "total_length": float(total_length),
            "total_loss_db": float(total_loss_db),
            "num_crossings": float(num_crossings),
            "area": float(area),
        }

    @staticmethod
    def _compute_reward(metrics: dict[str, float], devices: dict[str, Device]) -> float:
        """综合奖励：面积利用率越高越好，线长/损耗/交叉越小越好。

        reward = w_area*util - w_len*length - w_loss*loss - w_cross*crossings
        其中 util = 器件总面积 / 放置包围盒面积。
        """
        area = metrics["area"]
        device_area = sum(
            max(w, 1.0) * max(h, 1.0)
            for w, h in (dev.footprint() for dev in devices.values())
        )
        util = device_area / area if area > 0 else 0.0
        reward = (
            _REWARD_AREA * util
            - _REWARD_LENGTH * metrics["total_length"]
            - _REWARD_LOSS * metrics["total_loss_db"]
            - _REWARD_CROSS * metrics["num_crossings"]
        )
        return float(reward)


# ---------------------------------------------------------------------------
# SubTask 14.3: Dataset / DatasetSample —— 训练样本容器与 JSON 序列化
# ---------------------------------------------------------------------------
@dataclass
class DatasetSample:
    """单个训练样本。"""

    netlist: Netlist
    baseline: dict[str, Any]
    reward: float


class Dataset:
    """训练数据集（支持 JSON 序列化往返）。"""

    def __init__(self) -> None:
        self.samples: list[DatasetSample] = []

    def add(self, sample: DatasetSample) -> None:
        """追加一个样本。"""
        self.samples.append(sample)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> DatasetSample:
        return self.samples[idx]

    def save(self, path: str) -> None:
        """序列化为 JSON 文件（网表与 baseline 解完整可重建）。"""
        payload = {"samples": [_sample_to_dict(s) for s in self.samples]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> Dataset:
        """从 JSON 文件加载（重建 Netlist/Placement/Route 对象）。

        重建 placements 时通过默认器件库（``build_default_catalog``）实例化器件，
        因此适用于由内置平台器件生成的数据集。
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        ds = cls()
        for s in data.get("samples", []):
            ds.samples.append(_sample_from_dict(s))
        return ds


# ---------------------------------------------------------------------------
# 序列化辅助函数（Netlist/Placement/Route ↔ JSON 字典）
# ---------------------------------------------------------------------------
def _netlist_to_dict(netlist: Netlist) -> dict[str, Any]:
    """将 Netlist 序列化为 ``parse_netlist`` 可解析的字典。"""
    return {
        "name": netlist.name,
        "instances": {
            inst.instance_id: {
                "component": inst.component,
                "platform": inst.platform,
                "settings": dict(inst.settings),
            }
            for inst in netlist.instances
        },
        "connections": [
            [c.src_instance, c.src_port, c.dst_instance, c.dst_port]
            for c in netlist.connections
        ],
    }


def _placement_to_dict(pl: Placement) -> dict[str, Any]:
    """将 Placement 序列化为字典（器件可由网表 + 默认器件库重建）。"""
    return {"x": pl.x, "y": pl.y, "rotation": pl.rotation}


def _route_to_dict(r: Route) -> dict[str, Any]:
    """将 Route 序列化为字典。"""
    return {
        "net_id": r.net_id,
        "path": [[float(p[0]), float(p[1])] for p in r.path],
        "length": r.length,
        "num_bends": r.num_bends,
        "num_crossings": r.num_crossings,
        "loss_db": r.loss_db,
        "is_equalized": r.is_equalized,
    }


def _sample_to_dict(sample: DatasetSample) -> dict[str, Any]:
    """将 DatasetSample 序列化为 JSON 友好字典。"""
    baseline = sample.baseline
    placements = baseline.get("placements", {})
    routes = baseline.get("routes", [])
    return {
        "netlist": _netlist_to_dict(sample.netlist),
        "baseline": {
            "placements": {
                iid: _placement_to_dict(pl) for iid, pl in placements.items()
            },
            "routes": [_route_to_dict(r) for r in routes],
            "metrics": baseline.get("metrics", {}),
            "reward": baseline.get("reward", 0.0),
        },
        "reward": sample.reward,
    }


def _sample_from_dict(data: dict[str, Any]) -> DatasetSample:
    """从字典重建 DatasetSample（含 Netlist/Placement/Route 对象）。"""
    netlist = parse_netlist(data["netlist"])
    # 重建 placements：用默认器件库实例化器件，再恢复放置坐标
    devices = instantiate_devices(netlist)
    baseline_data = data.get("baseline", {})
    placements: dict[str, Placement] = {}
    for iid, pd in baseline_data.get("placements", {}).items():
        if iid in devices:
            placements[iid] = Placement(
                instance_id=iid,
                device=devices[iid],
                x=float(pd["x"]),
                y=float(pd["y"]),
                rotation=int(pd["rotation"]),
            )
    routes = [
        Route(
            net_id=r["net_id"],
            path=[(float(p[0]), float(p[1])) for p in r["path"]],
            length=float(r["length"]),
            num_bends=int(r["num_bends"]),
            num_crossings=int(r["num_crossings"]),
            loss_db=float(r["loss_db"]),
            is_equalized=bool(r["is_equalized"]),
        )
        for r in baseline_data.get("routes", [])
    ]
    baseline: dict[str, Any] = {
        "placements": placements,
        "routes": routes,
        "metrics": baseline_data.get("metrics", {}),
        "reward": float(baseline_data.get("reward", 0.0)),
    }
    return DatasetSample(
        netlist=netlist,
        baseline=baseline,
        reward=float(data.get("reward", 0.0)),
    )


# ---------------------------------------------------------------------------
# SubTask 14.4: generate_training_dataset —— 生成完整训练数据集
# ---------------------------------------------------------------------------
def generate_training_dataset(
    output_path: str,
    num_samples: int = 100,
    sizes: list[int] | None = None,
    platform: str = "SOI",
    seed: int = 42,
) -> Dataset:
    """生成完整训练数据集并保存为 JSON。

    Args:
        output_path: 输出 JSON 路径。
        num_samples: 样本数量。
        sizes: 器件规模候选列表（默认 [10, 50, 100]），按序轮转选取。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        seed: 随机种子（保证可复现）。

    Returns:
        生成的 ``Dataset``（同时已保存到 ``output_path``）。
    """
    if sizes is None:
        sizes = [10, 50, 100]
    catalog = build_default_catalog()
    cons = get_platform_constraints(platform)
    router = WaveguideRouter(
        grid_size=1.0,
        min_bend_radius=cons["min_bend_radius_um"],
        min_spacing=cons["min_spacing_um"],
    )
    solver = BaselineSolver(router)
    dataset = Dataset()
    for i in range(num_samples):
        num_devices = sizes[i % len(sizes)]
        num_nets = max(num_devices - 1, int(num_devices * 1.2))
        sub_seed = seed + i * 1009 + num_devices
        generator = NetlistGenerator(catalog, seed=sub_seed)
        netlist = generator.generate(num_devices, num_nets, platform=platform)
        baseline = solver.solve(netlist)
        dataset.add(
            DatasetSample(
                netlist=netlist,
                baseline=baseline,
                reward=baseline["reward"],
            )
        )
    dataset.save(output_path)
    return dataset


# ===========================================================================
# 向后兼容：基于字典的网表生成（供 train_loop.py 使用）
# 覆盖 MZI 链、滤波器组、WDM、交叉开关等典型光子电路拓扑。
# 拓扑参考：
# - gdsfactory 的示例电路（MZI、ring filter、WDM）
#   来源: https://gdsfactory.github.io/gdsfactory/
# - Basso et al., NeurIPS 2025 模拟 IC floorplanning 数据集
#   来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
# ===========================================================================
@dataclass
class DatasetConfig:
    """数据集生成配置（向后兼容）。"""

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
            for iid, comp in zip(inst_ids, components)
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


__all__ = [
    "NetlistGenerator",
    "BaselineSolver",
    "DatasetSample",
    "Dataset",
    "generate_training_dataset",
    # 向后兼容
    "DatasetConfig",
    "generate_netlist",
    "generate_dataset",
    "save_dataset",
    "load_dataset",
]
