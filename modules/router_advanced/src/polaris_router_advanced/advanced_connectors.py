"""R22 路标：OptoDesigner Advanced Connectors Module 对齐模块。

对齐 Synopsys OptoDesigner Advanced Connectors Module，实现欧拉弯曲连接器
（超低损耗）、路径长度定义连接器（等长约束）、相位匹配路由（MZI 臂/差分对）、
RF GSG 电极路由、总线路由、高阶贝塞尔连接器（任意角度多模弯曲）。

## 学术依据

- Hong et al., Photonics Research, Vol. 10, 2021: https://doi.org/10.1364/PRJ.437726
- Yu et al., Photonics Research, Vol. 14, No. 2, 2026: https://doi.org/10.1364/PRJ.574190
- OptoDesigner Advanced Connectors: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
- Ghione & Naldi, IEEE TMTT, Vol. 35, No. 3, 1987: https://doi.org/10.1109/TMTT.1987.1133623
- SiEPIC EBeam PDK (连接器规则), https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- project_rules.md 规则 7.1: 文件 < 600 行
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

# 学术来源 URL 常量（规则 18 学术诚信）
_URL_HONG_2021 = "https://doi.org/10.1364/PRJ.437726"
_URL_YU_2026 = "https://doi.org/10.1364/PRJ.574190"
_URL_OPTODESIGNER_AC = (
    "https://www.synopsys.com/photonic-solutions/optocompiler/"
    "optodesigner/advanced-connectors-module.html"
)
_URL_GHIONE_NALDI_1987 = "https://doi.org/10.1109/TMTT.1987.1133623"


# ---------------------------------------------------------------------------
# 1. 欧拉弯曲连接器（超低损耗）
# ---------------------------------------------------------------------------


@dataclass
class EulerBendConfig:
    """欧拉弯曲配置（超低损耗）。

    学术依据：Hong et al., Photonics Research, Vol. 10, 2021
    URL: https://doi.org/10.1364/PRJ.437726

    欧拉螺旋曲率 κ(s) = s/R_eff，从 0 线性增加到 1/R_eff
    优点：曲率连续，无突变，辐射损耗低

    Attributes:
        radius: 有效弯曲半径（μm）。
        angle: 弯曲角度（度）。
        n_points: 采样点数。
    """

    radius: float = 10.0
    angle: float = 90.0
    n_points: int = 100

    def __post_init__(self) -> None:
        """参数校验（禁止 fall-back 默认值静默修正）。"""
        if self.radius <= 0:
            raise ValueError(f"radius 必须 > 0，得到 {self.radius}")
        if self.angle <= 0:
            raise ValueError(f"angle 必须 > 0，得到 {self.angle}")
        if self.n_points < 2:
            raise ValueError(f"n_points 必须 >= 2，得到 {self.n_points}")


class EulerBend:
    """欧拉弯曲连接器（超低损耗硅光子波导弯曲）。

    学术依据：Hong 2021 Photonics Research
    URL: https://doi.org/10.1364/PRJ.437726

    对称欧拉弯曲：曲率从 0 线性增到 1/R，再从 1/R 线性减到 0，总转角 = angle。
    """

    def __init__(self, config: EulerBendConfig) -> None:
        """初始化欧拉弯曲连接器。"""
        self.config = config

    def compute_path(self) -> list[tuple[float, float]]:
        """计算欧拉螺旋路径。

        对称欧拉弯曲（S 形）：
        - 第一半（0 ≤ s ≤ L_half）：κ = s / (R * L_half)，转角 = angle/2
        - 第二半（L_half ≤ s ≤ 2*L_half）：κ = (2*L_half - s) / (R * L_half)
        - 半弧长 L_half = R * angle_rad（由 ∫κ ds = angle/2 推导）

        Returns:
            路径点列表 [(x, y), ...]（μm）。
        """
        R = self.config.radius
        angle_rad = math.radians(self.config.angle)
        n = self.config.n_points
        # 半弧长：∫₀^(L_half) (s/(R*L_half)) ds = L_half/(2R) = angle_rad/2
        # 所以 L_half = R * angle_rad
        L_half = R * angle_rad
        L_total = 2.0 * L_half
        ds = L_total / (n - 1)
        s_arr = np.linspace(0.0, L_total, n)
        # 曲率数组（对称：先增后减）
        kappa = np.where(
            s_arr <= L_half,
            s_arr / (R * L_half),
            (L_total - s_arr) / (R * L_half),
        )
        # 累积转角 θ(s) = ∫κ ds（梯形积分）
        theta = np.zeros(n)
        for i in range(1, n):
            theta[i] = theta[i - 1] + 0.5 * (kappa[i] + kappa[i - 1]) * ds
        # 累积坐标 x = ∫cos(θ) ds, y = ∫sin(θ) ds
        x = np.zeros(n)
        y = np.zeros(n)
        for i in range(1, n):
            x[i] = x[i - 1] + 0.5 * (
                math.cos(theta[i]) + math.cos(theta[i - 1])
            ) * ds
            y[i] = y[i - 1] + 0.5 * (
                math.sin(theta[i]) + math.sin(theta[i - 1])
            ) * ds
        return [(float(x[i]), float(y[i])) for i in range(n)]

    def compute_length(self) -> float:
        """计算欧拉弯曲路径长度（μm）。总弧长 = 2 * R * angle_rad。"""
        R = self.config.radius
        angle_rad = math.radians(self.config.angle)
        return 2.0 * R * angle_rad

    def compute_loss(self, alpha: float = 0.28) -> float:
        """计算弯曲损耗（dB）。

        传播损耗 0.28 dB/cm（Hong 2021 实测值）
        URL: https://doi.org/10.1364/PRJ.437726

        Raises:
            ValueError: alpha 非正。
        """
        if alpha <= 0:
            raise ValueError(f"alpha 必须 > 0，得到 {alpha}")
        length_cm = self.compute_length() / 1e4  # μm → cm
        return alpha * length_cm


# ---------------------------------------------------------------------------
# 2. 路径长度定义连接器（等长约束）
# ---------------------------------------------------------------------------


class LengthDefinedConnector:
    """路径长度定义连接器（等长约束）。

    学术依据：OptoDesigner Advanced Connectors Module
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html

    功能：给定起止点和目标长度，生成等长波导路径
    应用：MZI 两臂等长、差分对等长
    """

    def __init__(self) -> None:
        """初始化路径长度定义连接器。"""

    def route_equal_length(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        target_length: float,
    ) -> list[tuple[float, float]]:
        """生成指定长度的波导路径（等腰三角形延展）。

        使用等腰三角形延展：路径 start → mid → end，其中
        |start→mid| + |mid→end| = target_length（精确）。
        mid 点在起止点中点沿垂直方向偏移 height。

        Raises:
            ValueError: 目标长度小于直线距离或起终点重合。
        """
        direct = math.hypot(end[0] - start[0], end[1] - start[1])
        if target_length < direct - 1e-6:
            raise ValueError(
                f"target_length {target_length} < 直线距离 {direct:.6f}"
            )
        if target_length <= direct + 1e-6:
            return [start, end]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        norm = math.hypot(dx, dy)
        if norm < 1e-12:
            raise ValueError("起点与终点重合，无法延展路径")
        perp_x = -dy / norm
        perp_y = dx / norm
        # 等腰三角形延展：两腰各 = target_length / 2
        # 底边 = direct，高度 h = sqrt((target/2)^2 - (direct/2)^2)
        half_target = target_length / 2.0
        half_direct = direct / 2.0
        height = math.sqrt(max(half_target ** 2 - half_direct ** 2, 0.0))
        mid_x = (start[0] + end[0]) / 2.0 + perp_x * height
        mid_y = (start[1] + end[1]) / 2.0 + perp_y * height
        return [start, (mid_x, mid_y), end]

    def route_phase_matched(
        self, arms: list[tuple[tuple[float, float], tuple[float, float]]]
    ) -> list[list[tuple[float, float]]]:
        """相位匹配路由（多臂等长）。

        用于 MZI 两臂、Clements 矩阵等长臂等场景。
        所有臂延展至与最长臂相同的长度。

        Raises:
            ValueError: arms 为空或单臂。
        """
        if len(arms) < 2:
            raise ValueError(
                f"相位匹配路由至少需要 2 臂，得到 {len(arms)}"
            )
        direct_lengths = [
            math.hypot(arm[1][0] - arm[0][0], arm[1][1] - arm[0][1])
            for arm in arms
        ]
        target = max(direct_lengths) * 1.1  # 留 10% 余量用于延展
        return [
            self.route_equal_length(arm[0], arm[1], target) for arm in arms
        ]


# ---------------------------------------------------------------------------
# 3. 相位匹配路由
# ---------------------------------------------------------------------------


class PhaseMatchedRouter:
    """相位匹配路由器（MZI 臂、差分对）。

    学术依据：OptoDesigner Advanced Connectors Module
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html

    确保 MZI 两臂光程差 < λ/10（相位匹配）
    """

    def __init__(self, wavelength: float = 1.55, neff: float = 2.4) -> None:
        """初始化相位匹配路由器。

        Args:
            wavelength: 工作波长（μm），默认 1.55（C 波段）。
            neff: 有效折射率，默认 2.4（SiEPIC EBeam PDK strip waveguide 1550nm
                有效折射率典型值，来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK；
                与 sim/device_models.py 和 sim/interconnect_jax.py 统一）。

        Raises:
            ValueError: 参数非正。
        """
        if wavelength <= 0:
            raise ValueError(f"wavelength 必须 > 0，得到 {wavelength}")
        if neff <= 0:
            raise ValueError(f"neff 必须 > 0，得到 {neff}")
        self.wavelength = wavelength
        self.neff = neff
        self._connector = LengthDefinedConnector()

    def route_mzi_arms(
        self,
        arm1_start: tuple[float, float],
        arm1_end: tuple[float, float],
        arm2_start: tuple[float, float],
        arm2_end: tuple[float, float],
    ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        """MZI 两臂等长路由。将两臂延展至相同长度。"""
        arms = [(arm1_start, arm1_end), (arm2_start, arm2_end)]
        paths = self._connector.route_phase_matched(arms)
        return paths[0], paths[1]

    def route_differential_pair(
        self, pairs: list[tuple[tuple[float, float], tuple[float, float]]]
    ) -> list[list[tuple[float, float]]]:
        """差分对等长路由。"""
        return self._connector.route_phase_matched(pairs)

    def compute_phase_mismatch(
        self, path1: list[tuple[float, float]], path2: list[tuple[float, float]]
    ) -> float:
        """计算两路径相位失配（rad）。

        相位失配公式：Δφ = (2π/λ) * neff * ΔL
        其中 ΔL 为光程差（路径长度差），λ 为波长，neff 为有效折射率。
        """
        l1 = _path_length(path1)
        l2 = _path_length(path2)
        delta_l = abs(l1 - l2)
        return (2.0 * math.pi / self.wavelength) * self.neff * delta_l


# ---------------------------------------------------------------------------
# 4. RF GSG 路由（电极布线）
# ---------------------------------------------------------------------------


class RFGSGRouter:
    """RF GSG（Ground-Signal-Ground）电极路由。

    学术依据：OptoDesigner Advanced Connectors Module
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html

    用于调制器电极布线，GSG 三导体共面波导
    """

    def __init__(
        self,
        signal_width: float = 10.0,
        ground_width: float = 20.0,
        gap: float = 5.0,
    ) -> None:
        """初始化 RF GSG 路由器。

        Args:
            signal_width: 信号导体宽度（μm）。
            ground_width: 地导体宽度（μm）。
            gap: 信号与地之间间隙（μm）。

        Raises:
            ValueError: 参数非正。
        """
        if signal_width <= 0:
            raise ValueError(f"signal_width 必须 > 0，得到 {signal_width}")
        if ground_width <= 0:
            raise ValueError(f"ground_width 必须 > 0，得到 {ground_width}")
        if gap <= 0:
            raise ValueError(f"gap 必须 > 0，得到 {gap}")
        self.signal_width = signal_width
        self.ground_width = ground_width
        self.gap = gap

    def route_gsg(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> dict[str, list[tuple[float, float]]]:
        """路由 GSG 电极。

        三导体共面波导：信号导体居中，两侧地导体平行。
        信号导体沿 start→end 直线，地导体在两侧偏移
        (signal_width/2 + gap + ground_width/2)。

        Returns:
            {signal: path, ground1: path, ground2: path}

        Raises:
            ValueError: 起终点重合。
        """
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        norm = math.hypot(dx, dy)
        if norm < 1e-12:
            raise ValueError("起点与终点重合，无法路由 GSG")
        perp_x = -dy / norm
        perp_y = dx / norm
        offset = self.signal_width / 2.0 + self.gap + self.ground_width / 2.0
        signal_path = [start, end]
        ground1_path = [
            (start[0] + perp_x * offset, start[1] + perp_y * offset),
            (end[0] + perp_x * offset, end[1] + perp_y * offset),
        ]
        ground2_path = [
            (start[0] - perp_x * offset, start[1] - perp_y * offset),
            (end[0] - perp_x * offset, end[1] - perp_y * offset),
        ]
        return {
            "signal": signal_path,
            "ground1": ground1_path,
            "ground2": ground2_path,
        }

    def compute_impedance(self) -> float:
        """计算特征阻抗（Ω）。

        共面波导阻抗公式（Ghione & Naldi, IEEE TMTT 1987）
        URL: https://doi.org/10.1109/TMTT.1987.1133623

        Z0 = (30π / sqrt(εeff)) * K(k')/K(k)
        其中 k = W / (W + 2G)，k' = sqrt(1 - k²)
        εeff = (εr + 1) / 2（Si 基底 εr = 11.9 近似）
        K(k')/K(k) 用 Hilberg 近似公式计算
        """
        eps_r = 11.9
        eps_eff = (eps_r + 1.0) / 2.0
        w = self.signal_width
        g = self.gap
        k = w / (w + 2.0 * g)
        ratio = _elliptic_ratio(k)
        return (30.0 * math.pi / math.sqrt(eps_eff)) * ratio


# ---------------------------------------------------------------------------
# 5. 总线路由（Bus Routing）
# ---------------------------------------------------------------------------


class BusRouter:
    """总线路由器（bus routing）。

    学术依据：OptoDesigner Advanced Connectors Module
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html

    用于多器件总线连接（如 Ring bank 总线）
    """

    def __init__(self) -> None:
        """初始化总线路由器。"""

    def route_bus(
        self,
        devices: list[dict[str, Any]],
        bus_type: str = "serial",
    ) -> list[list[tuple[float, float]]]:
        """路由总线连接多个器件。

        Args:
            devices: 器件列表，每个器件含 'in_port' (x, y) 和 'out_port' (x, y)。
            bus_type: 总线类型，serial（串联）/ parallel（并联）。

        Returns:
            路径列表。serial 返回单条总线路径；parallel 返回每器件一条路径。

        Raises:
            ValueError: devices 为空或 bus_type 非法。
        """
        if not devices:
            raise ValueError("devices 不能为空")
        if bus_type not in ("serial", "parallel"):
            raise ValueError(f"bus_type 必须为 serial/parallel，得到 {bus_type}")
        if bus_type == "serial":
            # 串联：路径点 = [in_0, out_0, in_1, out_1, ..., in_{n-1}, out_{n-1}]
            path: list[tuple[float, float]] = []
            for dev in devices:
                path.append(dev["in_port"])
                path.append(dev["out_port"])
            return [path]
        # 并联：每器件独立路径 in → out
        return [[dev["in_port"], dev["out_port"]] for dev in devices]


# ---------------------------------------------------------------------------
# 6. 高阶贝塞尔连接器
# ---------------------------------------------------------------------------


class HighOrderBezierConnector:
    """高阶贝塞尔曲线连接器（任意角度多模弯曲）。

    学术依据：Yu et al., Photonics Research, Vol. 14, No. 2, 2026
    URL: https://doi.org/10.1364/PRJ.574190

    支持任意角度（60°/90°/120°/180°）多模弯曲
    超额损耗 < 0.038dB，串扰 < -30dB
    """

    def __init__(self, order: int = 5) -> None:
        """初始化高阶贝塞尔连接器。

        Args:
            order: 贝塞尔曲线阶数（>= 2）。

        Raises:
            ValueError: order < 2。
        """
        if order < 2:
            raise ValueError(f"order 必须 >= 2，得到 {order}")
        self.order = order

    def compute_control_points(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        start_angle: float,
        end_angle: float,
        order: int,
    ) -> list[tuple[float, float]]:
        """计算控制点。

        控制点沿起止方向均匀分布：P0 = start，P_n = end，
        中间控制点沿起止角度方向插值。

        Returns:
            控制点列表 [(x, y), ...]，长度 = order + 1。
        """
        if order < 2:
            raise ValueError(f"order 必须 >= 2，得到 {order}")
        dist = math.hypot(end[0] - start[0], end[1] - start[1])
        r0 = math.radians(start_angle)
        r1 = math.radians(end_angle)
        step = dist / order
        points: list[tuple[float, float]] = [start]
        for i in range(1, order):
            t = i / order
            base_x = start[0] + t * (end[0] - start[0])
            base_y = start[1] + t * (end[1] - start[1])
            # 沿起止方向偏移（前半段沿 start_angle，后半段沿 end_angle）
            if t < 0.5:
                ang = r0
                offset = step * (0.5 - t) * 2.0
            else:
                ang = r1
                offset = step * (t - 0.5) * 2.0
            points.append((
                base_x + offset * math.cos(ang),
                base_y + offset * math.sin(ang),
            ))
        points.append(end)
        return points

    def compute_path(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        start_angle: float,
        end_angle: float,
    ) -> list[tuple[float, float]]:
        """计算高阶贝塞尔曲线路径。

        n 阶贝塞尔曲线：B(t) = Σ_{i=0}^{n} C(n,i) * (1-t)^(n-i) * t^i * P_i

        Returns:
            路径点列表 [(x, y), ...]（100 个采样点）。
        """
        n = self.order
        cp = self.compute_control_points(start, end, start_angle, end_angle, n)
        cp_arr = np.asarray(cp, dtype=float)
        n_points = 100
        t = np.linspace(0.0, 1.0, n_points)
        path = np.zeros((n_points, 2))
        for i in range(n + 1):
            coeff = math.comb(n, i) * (1.0 - t) ** (n - i) * t ** i
            path += np.outer(coeff, cp_arr[i])
        return [(float(p[0]), float(p[1])) for p in path]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _path_length(path: list[tuple[float, float]]) -> float:
    """计算路径总长度（μm）。"""
    if len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(path)):
        total += math.hypot(
            path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]
        )
    return total


def _elliptic_ratio(k: float) -> float:
    """计算 K(k')/K(k)（第一类完全椭圆积分比值，Hilberg 近似）。

    - 当 0 < k <= 1/√2 时：K(k')/K(k) ≈ (1/π) * ln(2 * (1+√k') / (1-√k'))
    - 当 1/√2 < k < 1 时：K(k')/K(k) ≈ π / ln(2 * (1+√k) / (1-√k'))

    Raises:
        ValueError: k 超出 (0, 1) 范围。
    """
    if not 0.0 < k < 1.0:
        raise ValueError(f"k 必须在 (0, 1) 范围内，得到 {k}")
    k_prime = math.sqrt(1.0 - k * k)
    threshold = 1.0 / math.sqrt(2.0)
    if k <= threshold:
        sqrt_kp = math.sqrt(k_prime)
        return (1.0 / math.pi) * math.log(
            2.0 * (1.0 + sqrt_kp) / (1.0 - sqrt_kp)
        )
    sqrt_k = math.sqrt(k)
    return math.pi / math.log(2.0 * (1.0 + sqrt_k) / (1.0 - sqrt_k))


__all__ = [
    "BusRouter",
    "EulerBend",
    "EulerBendConfig",
    "HighOrderBezierConnector",
    "LengthDefinedConnector",
    "PhaseMatchedRouter",
    "RFGSGRouter",
]
