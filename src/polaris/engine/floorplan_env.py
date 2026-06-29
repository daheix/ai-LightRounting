"""布局环境（Floorplan）—— Gymnasium 接口（Task 9）。

将器件网表放置到网格化画布上。状态观测含占用栅格、端口位置、拥塞图；
奖励综合面积利用率、HPWL 线长、拥塞度、重叠惩罚。

方法参考：
- NeurIPS 2025 Basso et al. RL+R-GCN 模拟 IC 布局感知 floorplanning
  来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- NeurIPS 2022 Cheng et al. 策略梯度布局
  来源: https://openreview.net/pdf?id=uNYqDfPEDD8
- 经典 HPWL（半周长线长）估计，见 EDA 教材
"""

from __future__ import annotations

from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from polaris.engine.floorplan_geometry import (
    count_overlaps,
    count_spacing_violations,
    hpwl,
)
from polaris.engine.netlist import Netlist
from polaris.pdk.device import Device


@dataclass
class Placement:
    """单个器件的放置结果。"""

    instance_id: str
    device: Device
    x: float  # 左下角 x（μm）
    y: float  # 左下角 y（μm）
    rotation: int = 0  # 0/90/180/270
    # P0-2 规模扩展（第11轮）：缓存 bbox_abs/port_positions 计算结果。
    # Placement 一旦创建即不可变（x/y/rotation 不变），缓存后避免每步
    # 重复旋转/平移计算。500 器件 × 500 步从 25 万次变换降为 500 次。
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    def port_positions(self) -> dict[str, tuple[float, float]]:
        """返回放置后端口绝对坐标（考虑旋转+平移）。"""
        if "ports" in self._cache:
            return self._cache["ports"]
        dev = self.device.rotate(self.rotation) if self.rotation else self.device
        moved = dev.translate(self.x - dev.bbox.xmin, self.y - dev.bbox.ymin)
        result = {p.name: (p.x, p.y) for p in moved.ports}
        self._cache["ports"] = result
        return result

    def ports_abs(self) -> list:
        """返回放置后端口对象列表（含绝对坐标与朝向，考虑旋转+平移）。

        用于 GDS 导出需要端口朝向的场景（如 SiEPIC PinRec Path 方向）。

        Returns:
            放置后的 ``Port`` 对象列表（绝对坐标，朝向已同步旋转）。
        """
        dev = self.device.rotate(self.rotation) if self.rotation else self.device
        moved = dev.translate(self.x - dev.bbox.xmin, self.y - dev.bbox.ymin)
        return list(moved.ports)

    def bbox_abs(self) -> tuple[float, float, float, float]:
        """返回放置后轴对齐包围盒 (xmin, ymin, xmax, ymax)。"""
        if "bbox" in self._cache:
            return self._cache["bbox"]
        dev = self.device.rotate(self.rotation) if self.rotation else self.device
        w = dev.bbox.xmax - dev.bbox.xmin
        h = dev.bbox.ymax - dev.bbox.ymin
        result = (self.x, self.y, self.x + w, self.y + h)
        self._cache["bbox"] = result
        return result


@dataclass
class FloorplanState:
    """布局状态（器件放置 + 画布占用）。"""

    placements: dict[str, Placement] = field(default_factory=dict)
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0  # 栅格分辨率（μm）

    @property
    def grid_w(self) -> int:
        return int(self.canvas_w / self.grid_size)

    @property
    def grid_h(self) -> int:
        return int(self.canvas_h / self.grid_size)

    def occupancy_grid(self, instance_ids: list[str]) -> np.ndarray:
        """构建占用栅格（已放置器件标记为 1）。"""
        grid = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        for inst_id in instance_ids:
            if inst_id not in self.placements:
                continue
            pl = self.placements[inst_id]
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            gi0 = max(0, int(xmin / self.grid_size))
            gj0 = max(0, int(ymin / self.grid_size))
            gi1 = min(self.grid_w, int(np.ceil(xmax / self.grid_size)))
            gj1 = min(self.grid_h, int(np.ceil(ymax / self.grid_size)))
            grid[gj0:gj1, gi0:gi1] = 1.0
        return grid


@dataclass
class FloorplanEnvConfig:
    """布局环境配置（画布尺寸 + 奖励权重）。

    将 ``FloorplanEnv.__init__`` 的画布与奖励参数打包为单一配置对象，
    降低构造函数参数个数（规则 4.1：参数上限 7）。

    向后兼容：``FloorplanEnv(net, devices, config=None, **kwargs)`` 中未提供
    config 时，旧式关键字参数（canvas_w/canvas_h/grid_size/overlap_penalty
    等）会自动转发到本 dataclass 构造。

    Attributes:
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        grid_size: 栅格分辨率（μm）。
        overlap_penalty: 重叠惩罚权重。
        hpwl_weight: HPWL 线长权重。
        area_reward: 面积利用率奖励权重。
        expert_shaper: 可选的专家奖励塑形器（None 表示禁用）。
            来源: ICLR'26 Expertise-Enhanced RL
            https://openreview.net/forum?id=yqvNwfxRR6
        state_encoder: 可选的 GNN 状态编码器（None 表示禁用）。
            启用后 _obs() 会额外返回 "gnn_embedding" 键。
            来源: Basso et al. NeurIPS 2025 R-GCN floorplanning
            https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    # RL 奖励权重（经验调参值，对齐 DeepPlace/Google Placement 奖励结构）
    #
    # 奖励结构: R = area_reward*util - hpwl_weight*wire
    #           - overlap_penalty*log1p(overlaps) - spacing_penalty*log1p(spacing_violations)
    #
    # 文献溯源（R02 学术诚信）:
    # - DeepPlace (Cheng et al. NeurIPS 2022): R_E = -L_wl - λ1·L_cg - λ2·L_ol
    #   https://arxiv.org/abs/2111.00234
    # - Google DreamPlacement (Mirhoseini et al. Nature 2021):
    #   proxy cost blends HPWL + density + congestion
    #   https://www.nature.com/articles/s41586-021-03544-w
    # - Basso et al. NeurIPS 2025 R-GCN floorplanning（状态编码方法，非权重值）
    #   https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
    # - LiDAR ISPD'25 DRV-free 标准（间距违规惩罚）
    #   https://dl.acm.org/doi/10.1145/3698364.3705355
    # - Reward shaping theory: Ng et al. ICML 1999（log1p 为有界惩罚，不改最优策略）
    #   https://arxiv.org/abs/1906.05085
    #
    # 注: 上述文献提供奖励**结构**（HPWL + 重叠 + 拥塞），具体权重值为
    # PoLaRIS 团队经验调参（M1.4: overlap_penalty 10.0→3.0 修复奖励被惩罚主导）。
    # 平衡: area_reward*util≈0.5, hpwl_weight*wire≈5.0, overlap_pen≈3.0*log1p(5)≈5.4
    overlap_penalty: float = 3.0
    hpwl_weight: float = 0.01
    area_reward: float = 1.0
    # F3 DRV 消除：间距违规惩罚（对齐 LiDAR ISPD'25 DRV-free 标准）
    # 来源: LiDAR ISPD'25 https://dl.acm.org/doi/10.1145/3698364.3705355
    spacing_penalty: float = 1.0
    min_spacing_um: float = 5.0
    expert_shaper: object | None = None
    state_encoder: object | None = None


class FloorplanEnv(gym.Env):
    """布局环境（Gymnasium 接口）。

    动作空间：``MultiDiscrete([grid_w, grid_h, 4])`` —— 放置下一个器件到
    (grid_x, grid_y) 并选择旋转 (0/90/180/270)。
    观测空间：占用栅格 + 端口位置 + 拥塞图。
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        net: Netlist,
        devices: dict[str, Device],
        config: FloorplanEnvConfig | None = None,
        **kwargs: float,
    ) -> None:
        super().__init__()
        # 向后兼容：未提供 config 时，从旧式关键字参数构建配置
        if config is None:
            config = FloorplanEnvConfig(**kwargs)
        self.net = net
        self.devices = devices
        self.instance_ids = list(devices.keys())
        self.overlap_penalty = config.overlap_penalty
        self.hpwl_weight = config.hpwl_weight
        self.area_reward = config.area_reward
        self.spacing_penalty = config.spacing_penalty
        self.min_spacing_um = config.min_spacing_um
        self.expert_shaper = config.expert_shaper
        self.state_encoder = config.state_encoder
        self._edge_index = self._build_edge_index()
        self.state = FloorplanState(
            canvas_w=config.canvas_w, canvas_h=config.canvas_h, grid_size=config.grid_size
        )
        self.grid_w = self.state.grid_w
        self.grid_h = self.state.grid_h
        self._step_idx = 0
        self._last_reward = 0.0  # 上一步的累计奖励（用于计算增量奖励）
        self.action_space = spaces.MultiDiscrete([self.grid_w, self.grid_h, 4])
        self.observation_space = self._build_observation_space()

    def _build_observation_space(self) -> spaces.Dict:
        """构建观测空间（occupancy + congestion + port_positions + step）。"""
        return spaces.Dict(
            {
                "occupancy": spaces.Box(
                    low=0, high=1, shape=(self.grid_h, self.grid_w), dtype=np.float32
                ),
                "congestion": spaces.Box(
                    low=0, high=1, shape=(self.grid_h, self.grid_w), dtype=np.float32
                ),
                "port_positions": spaces.Box(
                    low=-1, high=1.0, shape=(len(self.instance_ids), 4), dtype=np.float32
                ),
                "step": spaces.Box(
                    low=0, high=len(self.instance_ids), shape=(1,), dtype=np.float32
                ),
            }
        )

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.state = FloorplanState(
            canvas_w=self.state.canvas_w,
            canvas_h=self.state.canvas_h,
            grid_size=self.state.grid_size,
        )
        self._step_idx = 0
        self._last_reward = 0.0  # 上一步的累计奖励（用于计算增量奖励）
        if options is not None and options.get("warm_start", False):
            self._apply_warm_start(options.get("warm_start_config"))
        return self._obs(), {"step": self._step_idx}

    def _apply_warm_start(self, placer_config=None) -> None:
        """应用 DREAMPlace warm-start 布局到环境状态。

        使用解析法（DREAMPlace warm-start）生成高质量初始布局，
        所有器件一次性放置完毕，step_idx 跳到末尾。
        对标商业工具 Innovus/ICC2 的两阶段流程（解析初始化 + RL 微调）。

        Args:
            placer_config: AnalyticalPlacerConfig（None 用默认）。

        来源:
            DREAMPlace warm-start: https://arxiv.org/abs/2004.10746
        """
        circuit = self._build_circuit_for_warm_start()

        # 生成 warm-start 布局 {name: (cx, cy)}
        from polaris.engine.analytical_placer import (
            AnalyticalPlacerConfig,
            warm_start_placement,
        )
        cfg = placer_config or AnalyticalPlacerConfig()
        layout = warm_start_placement(circuit, cfg)

        self._apply_warm_start_layout(layout)

    def _build_circuit_for_warm_start(self):
        """从环境状态构建 CircuitSpec（供 warm-start 使用）。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        device_specs = []
        for inst_id in self.instance_ids:
            dev = self.devices[inst_id]
            bbox = dev.bbox
            w = float(bbox.xmax - bbox.xmin)
            h = float(bbox.ymax - bbox.ymin)
            ports = [(p.name, p.x, p.y, p.direction) for p in dev.ports]
            device_specs.append(DeviceSpec(
                name=inst_id,
                device_type=dev.device_type if hasattr(dev, "device_type") else "generic",
                width_um=w,
                height_um=h,
                ports=ports,
            ))
        connections = [
            (c.src_instance, c.src_port, c.dst_instance, c.dst_port)
            for c in self.net.connections
        ]
        return CircuitSpec(
            name="warm_start",
            devices=device_specs,
            connections=connections,
            canvas_w=self.state.canvas_w,
            canvas_h=self.state.canvas_h,
        )

    def _apply_warm_start_layout(self, layout: dict) -> None:
        """将 warm-start 布局结果应用到环境 placements。"""
        for inst_id, (cx, cy) in layout.items():
            if inst_id not in self.devices:
                continue
            dev = self.devices[inst_id]
            bbox = dev.bbox
            w = float(bbox.xmax - bbox.xmin)
            h = float(bbox.ymax - bbox.ymin)
            x = max(0.0, min(cx - w / 2, self.state.canvas_w - w))
            y = max(0.0, min(cy - h / 2, self.state.canvas_h - h))
            self.state.placements[inst_id] = Placement(
                instance_id=inst_id, device=dev, x=x, y=y, rotation=0
            )

        # warm-start 后所有器件已放置，step_idx 跳到末尾
        self._step_idx = len(self.instance_ids)
        self._last_reward = self._reward()

    def _build_edge_index(self) -> np.ndarray:
        """从 net.connections 构建无向图边索引 ``[2, E]``（双向）。

        供 GNN 状态编码器使用。来源: R-GCN Schlichtkrull 2018。
        """
        id_to_idx = {iid: i for i, iid in enumerate(self.instance_ids)}
        edges: list[list[int]] = []
        for conn in self.net.connections:
            if conn.src_instance in id_to_idx and conn.dst_instance in id_to_idx:
                src = id_to_idx[conn.src_instance]
                dst = id_to_idx[conn.dst_instance]
                edges.append([src, dst])
                edges.append([dst, src])
        if not edges:
            return np.zeros((2, 0), dtype=np.int64)
        return np.array(edges).T

    def _obs(self) -> dict:
        placed_ids = list(self.state.placements.keys())
        occ = self.state.occupancy_grid(placed_ids)
        cong = self._compute_congestion()
        # 端口位置（每个实例取首端口 x,y + 包围盒中心）
        port_pos = np.full((len(self.instance_ids), 4), -1.0, dtype=np.float32)
        for i, inst_id in enumerate(self.instance_ids):
            if inst_id in self.state.placements:
                pl = self.state.placements[inst_id]
                ports = pl.port_positions()
                if ports:
                    first = next(iter(ports.values()))
                    port_pos[i, 0] = first[0] / self.state.canvas_w
                    port_pos[i, 1] = first[1] / self.state.canvas_h
                xmin, ymin, xmax, ymax = pl.bbox_abs()
                port_pos[i, 2] = (xmin + xmax) / 2 / self.state.canvas_w
                port_pos[i, 3] = (ymin + ymax) / 2 / self.state.canvas_h
        obs = {
            "occupancy": occ,
            "congestion": cong,
            "port_positions": port_pos,
            "step": np.array([self._step_idx], dtype=np.float32),
        }
        # GNN 状态编码（可选）：融合器件图特征与栅格空间特征
        # 来源: Basso et al. NeurIPS 2025 R-GCN floorplanning
        # https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
        # 端到端训练模式：保留图特征供 GNNPPOAgent 反向传播更新 GNN 参数
        if self.state_encoder is not None:
            obs["gnn_embedding"] = self._compute_gnn_embedding(occ)
            obs["graph_features"] = self._build_graph_features(occ)
        return obs

    def _compute_congestion(self) -> np.ndarray:
        """计算 RUDY 拥塞图（即时，无需训练）。

        对齐 DeepPlace (NeurIPS 2021) congestion map 作为 obs 通道的业界标准。
        来源: DREAMPlace RUDY https://arxiv.org/abs/2004.10746
        """
        from polaris.engine.congestion import RudyConfig, rudy_congestion

        cfg = RudyConfig(
            grid_h=self.grid_h,
            grid_w=self.grid_w,
            canvas_w=self.state.canvas_w,
            canvas_h=self.state.canvas_h,
        )
        return rudy_congestion(
            placements=self.state.placements,
            connections=self.net.connections,
            cfg=cfg,
        )

    def _build_graph_features(self, occ: np.ndarray) -> dict:
        """构建 GNN 端到端训练所需的图特征字典。

        保留 node_feats/edge_index/grid_feat 的原始数组，供 GNNPPOAgent
        在 update 时重建可微计算图，使梯度能流回 StateEncoder 参数。

        第4轮 P1-1 增强：当 StateEncoder 启用 edge-GNN 模式时，额外构建
        edge_feats（AlphaChip 风格边特征）。

        Args:
            occ: 当前占用栅格。

        Returns:
            含 node_feats/edge_index/grid_feat 的字典（edge-GNN 模式额外含 edge_feats）。
        """
        from polaris.engine.gnn import build_edge_features, build_node_features

        node_feats_arr = build_node_features(self.devices, self.state.placements, self.instance_ids)
        result = {
            "node_feats": node_feats_arr.astype(np.float64),
            "edge_index": self._edge_index,
            "grid_feat": occ.astype(np.float64),
        }
        # edge-GNN 模式：额外构建边特征
        if hasattr(self.state_encoder, "use_edge_gnn") and self.state_encoder.use_edge_gnn:
            edge_feats_arr = build_edge_features(
                self.devices,
                self.state.placements,
                self.instance_ids,
                self._edge_index,
            )
            result["edge_feats"] = edge_feats_arr.astype(np.float64)
        return result

    def _compute_gnn_embedding(self, occ: np.ndarray) -> np.ndarray:
        """计算 GNN 状态嵌入向量（前向推理，用于 obs 维度推断）。

        从当前器件图构建节点特征，经 StateEncoder 编码为全局状态向量。
        注意：此处返回 numpy 数组（脱离计算图），仅用于 obs 维度推断与
        兼容 _obs_to_vector 展平。端到端训练时由 GNNPPOAgent 重建可微路径。

        第4轮 P1-1 增强：edge-GNN 模式时构建并传递边特征。

        Args:
            occ: 当前占用栅格。

        Returns:
            GNN 嵌入向量 ``[out_dim]``。
        """
        from polaris.engine.gnn import build_edge_features, build_node_features
        from polaris.nn import Tensor

        node_feats_arr = build_node_features(self.devices, self.state.placements, self.instance_ids)
        node_feats = Tensor(node_feats_arr)
        grid_feat = Tensor(occ.astype(np.float64))
        edge_feats = None
        if hasattr(self.state_encoder, "use_edge_gnn") and self.state_encoder.use_edge_gnn:
            edge_feats_arr = build_edge_features(
                self.devices,
                self.state.placements,
                self.instance_ids,
                self._edge_index,
            )
            edge_feats = Tensor(edge_feats_arr.astype(np.float64))
        embedding = self.state_encoder(node_feats, self._edge_index, grid_feat, edge_feats)
        return np.asarray(embedding.data, dtype=np.float32).flatten()

    def step(self, action):
        if self._step_idx >= len(self.instance_ids):
            return self._obs(), 0.0, True, False, {}
        action = np.asarray(action).astype(np.int64)
        gx, gy, rot = int(action[0]), int(action[1]), int(action[2])
        rotation = rot * 90
        inst_id = self.instance_ids[self._step_idx]
        dev = self.devices[inst_id]
        # 网格坐标 -> 画布坐标
        x = gx * self.state.grid_size
        y = gy * self.state.grid_size
        # 裁剪到画布内
        dev_rot = dev.rotate(rotation) if rotation else dev
        w = dev_rot.bbox.xmax - dev_rot.bbox.xmin
        h = dev_rot.bbox.ymax - dev_rot.bbox.ymin
        x = min(x, self.state.canvas_w - w)
        y = min(y, self.state.canvas_h - h)
        x = max(0.0, x)
        y = max(0.0, y)
        self.state.placements[inst_id] = Placement(
            instance_id=inst_id, device=dev, x=x, y=y, rotation=rotation
        )
        self._step_idx += 1
        terminated = self._step_idx >= len(self.instance_ids)
        # 增量奖励：当前累计 - 上次累计（让PPO学到每步的边际贡献）
        cumulative = self._reward()
        reward = cumulative - self._last_reward
        self._last_reward = cumulative
        return self._obs(), reward, terminated, False, {"step": self._step_idx}

    def _reward(self) -> float:
        """奖励 = 面积利用率 - HPWL*权重 - 重叠*惩罚 - 间距违规*惩罚 + 专家奖励。

        奖励结构对齐 DeepPlace (NeurIPS 2022) R_E = -L_wl - λ1·L_cg - λ2·L_ol，
        扩展加入面积利用率正奖励 + 间距违规惩罚（DRV-free 标准）。

        log1p 惩罚设计（R3-P2-6 文献对齐）:
        - log1p(x) = log(1+x) 为有界次线性惩罚，避免大量违规时惩罚主导奖励
        - 理论依据: Ng et al. ICML 1999 reward shaping 不改最优策略
          https://arxiv.org/abs/1906.05085
        - 数值稳定性: log1p(x) 对 x≥0 数值稳定（无需特殊处理）
        - 与线性惩罚对比: 100 重叠时线性=300, log1p=13.8（避免梯度爆炸）

        文献:
        - DeepPlace: https://arxiv.org/abs/2111.00234
        - Google Placement: https://www.nature.com/articles/s41586-021-03544-w
        - LiDAR ISPD'25 DRV-free: https://dl.acm.org/doi/10.1145/3698364.3705355
        """
        placed = list(self.state.placements.values())
        if not placed:
            return 0.0
        # 面积利用率
        used_area = 0.0
        for pl in placed:
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            used_area += (xmax - xmin) * (ymax - ymin)
        total_area = self.state.canvas_w * self.state.canvas_h
        util = used_area / total_area if total_area > 0 else 0.0
        # HPWL
        wire = hpwl(self.net, self.state)
        # 重叠（DRV 主要来源）
        overlaps = count_overlaps(self.state)
        # 对数重叠惩罚：避免大量重叠时惩罚完全主导奖励
        # log1p 为有界次线性惩罚（Ng et al. ICML 1999 reward shaping theory）
        overlap_pen = self.overlap_penalty * (np.log1p(overlaps) if overlaps > 0 else 0.0)
        # F3 DRV 消除：间距违规惩罚（对齐 LiDAR ISPD'25 DRV-free 标准）
        spacing_violations = count_spacing_violations(placed, self.min_spacing_um)
        spacing_pen = self.spacing_penalty * (
            np.log1p(spacing_violations) if spacing_violations > 0 else 0.0
        )
        reward = self.area_reward * util - self.hpwl_weight * wire - overlap_pen - spacing_pen
        # 专家奖励塑形（可选）：注入光子学领域知识
        # 来源: ICLR'26 Expertise-Enhanced RL
        # https://openreview.net/forum?id=yqvNwfxRR6
        if self.expert_shaper is not None:
            reward += self._compute_expert_reward()
        return float(reward)

    def _compute_expert_reward(self) -> float:
        """计算专家知识奖励分量。

        从当前布局状态构建 ExpertRewardInput 并调用 shaper.compute()。

        Returns:
            专家奖励值（可为正可为负）。
        """
        from polaris.trainer.reward_shaping import ExpertRewardInput

        device_positions: dict[str, tuple[float, float]] = {}
        for inst_id, pl in self.state.placements.items():
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            device_positions[inst_id] = ((xmin + xmax) / 2, (ymin + ymax) / 2)
        connections = [
            (c.src_instance, c.src_port, c.dst_instance, c.dst_port) for c in self.net.connections
        ]
        placed_ids = list(self.state.placements.keys())
        congestion = self.state.occupancy_grid(placed_ids) if placed_ids else None
        reward_input = ExpertRewardInput(
            device_positions=device_positions,
            connections=connections,
            congestion_map=congestion,
        )
        result = self.expert_shaper.compute(reward_input)
        return float(result.total_expert_reward)

    def render(self):
        pass


__all__ = [
    "FloorplanEnv",
    "FloorplanEnvConfig",
    "FloorplanState",
    "Placement",
    "count_overlaps",
    "count_spacing_violations",
    "hpwl",
]
