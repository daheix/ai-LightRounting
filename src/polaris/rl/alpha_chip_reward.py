"""R34-R35 路标：光子布局多目标奖励函数。

本模块从 ``alpha_chip.py`` 拆分而来（facade 模式），提供
``PhotonicPlacementReward``，实现光子布局的多目标奖励计算（线长 /
拥塞 / 交叉数 / 弯曲半径违反 / 波导长度均匀性）。外部 import 路径
保持不变（``from polaris.rl.alpha_chip import
PhotonicPlacementReward``）。

## 学术依据

- AlphaChip 奖励函数（Mirhoseini 2024 Nature）
  https://doi.org/10.1038/s41586-024-07714-9
- DREAMPlace RUDY 拥塞估计: https://arxiv.org/abs/2004.10746
- LiDAR 光学约束（ISPD'25）
- SiEPIC EBeam PDK 弯曲半径标准:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Bogaerts et al., "Silicon nanophotonic waveguide crossings",
  J. Lightwave Technol. 2013, DOI: 10.1109/JLT.2013.2258874
- Liu et al., "Ultralow-loss waveguide crossing for SiP",
  Opt. Express 2019, DOI: 10.1364/OE.27.020886
- Marcuse, "Curvature loss formula for optical fibers",
  J. Opt. Soc. Am. 1976, DOI: 10.1364/JOSA.66.000216
- Yariv & Yeh, "Photonics: Optical Electronics in Modern Communications",
  Oxford 2007, Ch. 4
- Reed et al., "Silicon optical modulators", Nat. Photonics 2010,
  DOI: 10.1038/nphoton.2010.179

## 【创新】光子布局多目标奖励

AlphaChip 原始奖励函数（Mirhoseini 2024 Nature）仅含线长/拥塞/面积，
本模块扩展为光子 IC 专用，增加三项光学约束：
- 交叉数：波导交叉引入插入损耗与串扰
- 弯曲半径违反：弯曲半径过小引入辐射损耗
- 波导长度均匀性：相位匹配要求波导长度均匀

## 来源

- 拆分自: ``src/polaris/rl/alpha_chip.py``（原文件 1096 行 → 拆分后 ≤800 行）
- 路标: R34-R35
- 架构统一: D05 Task 10
"""

from __future__ import annotations

import numpy as np

from polaris.rl.alpha_chip_config import _CANVAS_SIZE, _MIN_BEND_RADIUS


class PhotonicPlacementReward:
    """光子布局奖励函数。

    【创新】光子布局多目标奖励：
    - 线长（HPWL）：经典 EDA 半周长线长估计
    - 拥塞（RUDY）：DREAMPlace 拥塞估计
    - 交叉数（光学约束）：波导交叉引入插入损耗与串扰
    - 弯曲半径违反（光学约束）：弯曲半径过小引入辐射损耗
    - 波导长度均匀性（光学约束）：相位匹配要求波导长度均匀

    学术依据：
    - AlphaChip 奖励函数（Mirhoseini 2024 Nature）
      https://doi.org/10.1038/s41586-024-07714-9
    - DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
    - LiDAR 光学约束（ISPD'25）
    - SiEPIC EBeam PDK 弯曲半径标准: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    def __init__(
        self,
        w_wirelength: float = 1.0,
        w_congestion: float = 1.0,
        w_crossing: float = 2.0,
        w_bend: float = 1.5,
        w_uniformity: float = 0.5,
    ) -> None:
        """初始化奖励函数。

        Args:
            w_wirelength: 线长权重。
            w_congestion: 拥塞权重。
            w_crossing: 交叉数权重（光学约束，权重较高）。
            w_bend: 弯曲违反权重（光学约束）。
            w_uniformity: 均匀性权重（光学约束，相位匹配）。
        """
        self.weights = {
            "wirelength": w_wirelength,
            "congestion": w_congestion,
            "crossing": w_crossing,
            "bend": w_bend,
            "uniformity": w_uniformity,
        }

    def compute(self, placement: dict, circuit: dict) -> dict:
        """计算多目标奖励。

        奖励 = -(w_wl·线长 + w_cong·拥塞 + w_cross·交叉数
                 + w_bend·弯曲违反 + w_uni·均匀性)

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            奖励明细 dict，含 ``reward`` 与各项指标。
        """
        wl = self.compute_wirelength(placement, circuit)
        cong = self.compute_congestion(placement, circuit)
        cross = self.compute_crossing(placement, circuit)
        bend = self.compute_bend_violation(placement, circuit)
        uni = self.compute_uniformity(placement, circuit)
        w = self.weights
        reward = -(
            w["wirelength"] * wl
            + w["congestion"] * cong
            + w["crossing"] * float(cross)
            + w["bend"] * float(bend)
            + w["uniformity"] * uni
        )
        return {
            "reward": float(reward),
            "wirelength": float(wl),
            "congestion": float(cong),
            "crossing": int(cross),
            "bend_violation": int(bend),
            "uniformity": float(uni),
        }

    def compute_wirelength(self, placement: dict, circuit: dict) -> float:
        """计算 HPWL 线长（半周长线长估计）。

        学术依据：经典 EDA 半周长线长估计。
        对每条连接取所有相关端口坐标的 (xmax-xmin)+(ymax-ymin)。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            所有连接的 HPWL 总和（μm）。
        """
        port_pos = self._port_positions(placement, circuit)
        total = 0.0
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                total += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return float(total)

    def compute_congestion(self, placement: dict, circuit: dict) -> float:
        """计算 RUDY 拥塞（Rectangular Uniform wire DensitY）。

        学术依据：DREAMPlace RUDY 拥塞估计
        https://arxiv.org/abs/2004.10746

        对每条连接，在其 bounding box 内均匀分布需求密度，
        累加到拥塞图，返回拥塞图最大值。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            拥塞图最大值（无量纲）。
        """
        port_pos = self._port_positions(placement, circuit)
        grid_h, grid_w = 32, 32
        congestion_map = np.zeros((grid_h, grid_w), dtype=np.float64)
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) < 2:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)
            gi0 = max(0, int(xmin / _CANVAS_SIZE * grid_w))
            gi1 = min(grid_w, int(np.ceil(xmax / _CANVAS_SIZE * grid_w)) + 1)
            gj0 = max(0, int(ymin / _CANVAS_SIZE * grid_h))
            gj1 = min(grid_h, int(np.ceil(ymax / _CANVAS_SIZE * grid_h)) + 1)
            area = max((gi1 - gi0) * (gj1 - gj0), 1)
            congestion_map[gj0:gj1, gi0:gi1] += 1.0 / area
        return float(congestion_map.max())

    def compute_crossing(self, placement: dict, circuit: dict) -> int:
        """计算波导交叉数（光学约束）。

        【创新】光子波导交叉数约束（超出 Mirhoseini 2024 Nature 范围）

        创新逻辑：
        - 电子 IC 金属线交叉仅引入 RC 延迟与串扰，影响较小
        - 光子波导交叉引入插入损耗（~0.1 dB/交叉）与光学串扰，
          直接降低信噪比与器件性能，需在布局阶段最小化交叉数

        支持理论：
        - 波导交叉插入损耗：SiN/Si 波导交叉典型损耗 0.05-0.3 dB
          （来源: Bogaerts et al., "Silicon nanophotonic waveguide crossings",
          J. Lightwave Technol. 2013, DOI: 10.1109/JLT.2013.2258874）
        - 交叉串扰：交叉点处部分光耦合至正交波导，典型串扰 -30~-40 dB
          （来源: Liu et al., "Ultralow-loss waveguide crossing for SiP",
          Opt. Express 2019, DOI: 10.1364/OE.27.020886）
        - AlphaChip 原始奖励函数（Mirhoseini 2024 Nature）仅含线长/拥塞/面积，
          无光学交叉约束项，本模块扩展为光子 IC 专用

        将每条连接视为线段，检测线段对是否相交（CCW 跨立实验）。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            波导交叉数。
        """
        port_pos = self._port_positions(placement, circuit)
        segments: list[list[tuple[float, float]]] = []
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) == 2:
                segments.append(pts)
        count = 0
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                if self._segments_intersect(segments[i], segments[j]):
                    count += 1
        return count

    def compute_bend_violation(self, placement: dict, circuit: dict) -> int:
        """计算弯曲半径违反数（光学约束）。

        【创新】光子波导弯曲半径约束（超出 Mirhoseini 2024 Nature 范围）

        创新逻辑：
        - 电子 IC 金属线弯曲无物理限制（仅 DRC 间距规则）
        - 光子波导弯曲半径过小（< _MIN_BEND_RADIUS）会引入辐射损耗，
          导致光从波导芯泄漏到包层，降低传输效率
        - 需检测器件间距是否满足最小弯曲半径要求，确保布线可行

        支持理论：
        - 弯曲辐射损耗：当弯曲半径 R < 临界半径 R_c 时，损耗急剧增加
          α_bend ∝ exp(-R/R_c)，R_c = a·n_core²/(2·(n_core²-n_clad²)^(3/2))
          （来源: Marcuse, "Curvature loss formula for optical fibers",
          J. Opt. Soc. Am. 1976, DOI: 10.1364/JOSA.66.000216）
        - SiEPIC EBeam PDK 标准最小弯曲半径 r_min = 5 μm（1.55 μm 波长），
          本模块取保守值 20 μm 以确保辐射损耗 < 0.01 dB/turn
          （来源: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
        - AlphaChip 原始奖励函数无弯曲半径约束项，本模块扩展为光子 IC 专用

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            弯曲半径违反数（器件对间距不足数）。
        """
        violations = 0
        devices = circuit["devices"]
        for i in range(len(devices)):
            for j in range(i + 1, len(devices)):
                id_i = devices[i]["id"]
                id_j = devices[j]["id"]
                if id_i not in placement or id_j not in placement:
                    continue
                pi = placement[id_i]
                pj = placement[id_j]
                wi = float(devices[i].get("width", 50))
                hi = float(devices[i].get("height", 30))
                wj = float(devices[j].get("width", 50))
                hj = float(devices[j].get("height", 30))
                ci = (pi["x"] + wi / 2, pi["y"] + hi / 2)
                cj = (pj["x"] + wj / 2, pj["y"] + hj / 2)
                dist = float(np.sqrt((ci[0] - cj[0]) ** 2 + (ci[1] - cj[1]) ** 2))
                gap = dist - max(wi, hi) / 2 - max(wj, hj) / 2
                if gap < _MIN_BEND_RADIUS:
                    violations += 1
        return violations

    def compute_uniformity(self, placement: dict, circuit: dict) -> float:
        """计算波导长度均匀性（光学约束，相位匹配）。

        【创新】光子波导长度均匀性约束（超出 Mirhoseini 2024 Nature 范围）

        创新逻辑：
        - 电子 IC 金属线长度差异仅引入 RC 延迟差异，影响较小
        - 光子干涉仪（如 MZI）要求两臂波导长度匹配（相位匹配），
          波导长度不均匀会导致相位失配，直接降低干涉消光比
        - 用变异系数（CV = std/mean）度量波导长度均匀性，CV 越小越均匀

        支持理论：
        - 相位失配：MZI 两臂长度差 ΔL 引入相位差 Δφ = 2π·n_eff·ΔL/λ，
          消光比 ER = 10·log₁₀((1+cos(Δφ))/(1-cos(Δφ)))，
          ΔL = λ/(4·n_eff) 时消光比降为 0 dB（完全失配）
          （来源: Yariv & Yeh, "Photonics: Optical Electronics in Modern
          Communications", Oxford 2007, Ch. 4 干涉仪原理）
        - 相位匹配要求：典型 MZI 要求 ΔL < λ/(100·n_eff) ≈ 15 nm（1.55 μm），
          对应消光比 > 40 dB
          （来源: Reed et al., "Silicon optical modulators",
          Nat. Photonics 2010, DOI: 10.1038/nphoton.2010.179）
        - AlphaChip 原始奖励函数无波导长度均匀性约束项，本模块扩展为光子 IC 专用

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            波导长度变异系数（越小越均匀，0 表示完全均匀）。
        """
        port_pos = self._port_positions(placement, circuit)
        lengths: list[float] = []
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) == 2:
                length = float(
                    np.sqrt((pts[0][0] - pts[1][0]) ** 2 + (pts[0][1] - pts[1][1]) ** 2)
                )
                lengths.append(length)
        if len(lengths) < 2:
            return 0.0
        mean_len = float(np.mean(lengths))
        if mean_len < 1e-6:
            return 0.0
        return float(np.std(lengths) / mean_len)

    def _port_positions(
        self, placement: dict, circuit: dict
    ) -> dict[tuple[str, str], tuple[float, float]]:
        """计算所有已放置器件端口的绝对坐标。

        端口均匀分布在器件周长上，考虑旋转（绕器件中心）。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            端口坐标 dict，{(inst_id, port_name): (x, y)}。
        """
        positions: dict[tuple[str, str], tuple[float, float]] = {}
        for dev in circuit["devices"]:
            inst_id = dev["id"]
            if inst_id not in placement:
                continue
            p = placement[inst_id]
            x, y, rot = float(p["x"]), float(p["y"]), int(p.get("rotation", 0))
            w = float(dev.get("width", 50))
            h = float(dev.get("height", 30))
            ports = dev.get("ports", [])
            n_ports = len(ports)
            for i, port_name in enumerate(ports):
                px, py = self._compute_port_pos(x, y, w, h, rot, i, n_ports)
                positions[(inst_id, port_name)] = (px, py)
        return positions

    @staticmethod
    def _compute_port_pos(
        x: float,
        y: float,
        w: float,
        h: float,
        rot: int,
        port_idx: int,
        n_ports: int,
    ) -> tuple[float, float]:
        """计算单个端口的绝对坐标。

        端口沿器件周长均匀分布，应用旋转（绕器件中心）。

        Args:
            x: 器件左下角 x。
            y: 器件左下角 y。
            w: 器件宽度。
            h: 器件高度。
            rot: 旋转角度（度，0/90/180/270）。
            port_idx: 端口索引。
            n_ports: 端口总数。

        Returns:
            端口绝对坐标 (px, py)。
        """
        if n_ports == 0:
            return (x + w / 2, y + h / 2)
        perimeter = 2 * (w + h)
        pos_along = (port_idx / n_ports) * perimeter
        # 沿周长计算局部坐标
        if pos_along < w:
            px, py = x + pos_along, y
        elif pos_along < w + h:
            px, py = x + w, y + (pos_along - w)
        elif pos_along < 2 * w + h:
            px, py = x + w - (pos_along - w - h), y + h
        else:
            px, py = x, y + h - (pos_along - 2 * w - h)
        # 应用旋转（绕器件中心）
        if rot != 0:
            cx, cy = x + w / 2, y + h / 2
            angle = float(np.radians(rot))
            dx, dy = px - cx, py - cy
            px = cx + dx * np.cos(angle) - dy * np.sin(angle)
            py = cy + dx * np.sin(angle) + dy * np.cos(angle)
        return (float(px), float(py))

    @staticmethod
    def _segments_intersect(
        s1: list[tuple[float, float]], s2: list[tuple[float, float]]
    ) -> bool:
        """检测两条线段是否相交（CCW 跨立实验）。

        Args:
            s1: 线段 1，[(x1, y1), (x2, y2)]。
            s2: 线段 2，[(x3, y3), (x4, y4)]。

        Returns:
            是否相交。
        """
        (x1, y1), (x2, y2) = s1
        (x3, y3), (x4, y4) = s2

        def _cross(ax: float, ay: float, bx: float, by: float) -> float:
            return ax * by - bx * ay

        d1 = _cross(x4 - x3, y4 - y3, x1 - x3, y1 - y3)
        d2 = _cross(x4 - x3, y4 - y3, x2 - x3, y2 - y3)
        d3 = _cross(x2 - x1, y2 - y1, x3 - x1, y3 - y1)
        d4 = _cross(x2 - x1, y2 - y1, x4 - x1, y4 - y1)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
        return False


__all__ = ["PhotonicPlacementReward"]
