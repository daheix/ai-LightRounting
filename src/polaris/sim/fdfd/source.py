"""FDFD 源项生成（A05 §3.2 / §6.2 光源）。

支持 4 类源（覆盖 T16 SimWorks FDFD §3.6 与 Lumerical FDTD 的频域源集）：
- PlaneWaveSource : 平面波（k 沿任意方向，相位面斜入射）
- DipoleSource    : 电偶极子（点源 J_z，Hertzian dipole）
- GaussianBeamSource : 高斯光束（傍轴近似，束腰处振幅分布）
- ModeSource      : 波导模注入（复用 FDE Mode 分布作为源振幅）

源向量 b = -iωμ₀ · diag(s_x s_y) · J_z（含 SC-PML 体积拉伸），见 A05 §5.2。
非 PML 区域 s_x s_y = 1，源向量退化为标准 -iωμ₀ J_z。

文献来源：
- Harrington RF, "Time-Harmonic Electromagnetic Fields," McGraw-Hill (1961).
- Taflove & Hagness 2005 §5（TFSF 与平面波注入）
- Shin & Fan 2012 JCP §3（SC-PML 体积修正）

规则依据：规则 14（参数校验失败即 raise，无 fall-back）/规则 26（纯 CPU）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from polaris.sim.fde.mode import Mode

__all__ = [
    "SourceType",
    "PlaneWaveSource",
    "DipoleSource",
    "GaussianBeamSource",
    "ModeSource",
]


SourceType = Literal["plane_wave", "dipole", "gaussian_beam", "mode"]


@dataclass(frozen=True)
class PlaneWaveSource:
    """平面波源（斜入射，相位面与传播方向垂直）。

    Attributes:
        amplitude: 复振幅 E_0（V/m）。
        kx, ky: 波矢分量（rad/m），须满足 kx²+ky² = (k₀·n_bg)²。
        center: 源中心坐标 (x, y)，单位米（用于幅值权重定位，平面波本身均匀）。
        polarization: 'ez'（TEz）或 'hz'（TMz），FDFD 2D 仅支持 TEz。
    """

    amplitude: complex
    kx: float
    ky: float
    center: tuple[float, float]
    polarization: str = "ez"

    def __post_init__(self) -> None:
        if self.polarization != "ez":
            raise ValueError(f"2D FDFD 仅支持 TEz (ez) 偏振，实际 {self.polarization}")
        if abs(self.amplitude) < 0.0:
            raise ValueError(f"振幅绝对值必须 ≥0，实际 {self.amplitude}")
        if abs(self.kx) + abs(self.ky) < 1e-30:
            raise ValueError("波矢分量全为零，平面波未定义")


@dataclass(frozen=True)
class DipoleSource:
    """电偶极子点源（Hertzian dipole，J_z 点源）。

    Attributes:
        amplitude: 复电流矩 I·dl（A·m）。
        position: 网格索引 (ix, iy)，整数。
        polarization: 'ez'（TEz）。
    """

    amplitude: complex
    position: tuple[int, int]
    polarization: str = "ez"

    def __post_init__(self) -> None:
        if self.polarization != "ez":
            raise ValueError(f"2D FDFD 仅支持 TEz (ez) 偏振，实际 {self.polarization}")
        ix, iy = self.position
        if ix < 0 or iy < 0:
            raise ValueError(f"偶极子位置必须为非负整数，实际 {self.position}")


@dataclass(frozen=True)
class GaussianBeamSource:
    """高斯光束源（傍轴近似，束腰位于 source line）。

    振幅分布：E_z(x) = E_0 · exp(-(x - x_0)² / w_0²)
    其中 w_0 为束腰半径，x_0 为束腰中心。

    Attributes:
        amplitude: 复振幅 E_0（V/m）。
        waist_radius: 束腰半径 w_0（米），>0。
        center: 束腰中心网格索引 (ix_center, iy_line)。
        direction: 传播方向 'x+' / 'x-' / 'y+' / 'y-'。
    """

    amplitude: complex
    waist_radius: float
    center: tuple[int, int]
    direction: str = "y+"

    def __post_init__(self) -> None:
        if self.waist_radius <= 0.0:
            raise ValueError(f"束腰半径必须 >0，实际 {self.waist_radius}")
        if self.direction not in ("x+", "x-", "y+", "y-"):
            raise ValueError(f"方向必须为 'x+'/'x-'/'y+'/'y-'，实际 {self.direction}")


@dataclass(frozen=True)
class ModeSource:
    """波导模注入源（复用 FDE Mode 的场分布）。

    源振幅取自 FDE 模式的 E_z 分量（TEz 假设），按沿传播方向的网格线注入。
    振幅经功率归一化（Mode 已按 1W 归一化），可直接作为 J_z 注入。

    Attributes:
        mode: FDE 求解模式（已归一化）。
        line_index: 注入线网格索引（垂直于传播方向）。
        direction: 传播方向 'x+' / 'x-' / 'y+' / 'y-'。
        amplitude: 注入幅度缩放因子（默认 1.0）。
    """

    mode: Mode
    line_index: int
    direction: str = "y+"
    amplitude: float = 1.0

    def __post_init__(self) -> None:
        if self.line_index < 0:
            raise ValueError(f"注入线索引必须 ≥0，实际 {self.line_index}")
        if self.direction not in ("x+", "x-", "y+", "y-"):
            raise ValueError(f"方向必须为 'x+'/'x-'/'y+'/'y-'，实际 {self.direction}")
        if self.amplitude < 0.0:
            raise ValueError(f"振幅缩放必须 ≥0，实际 {self.amplitude}")


def build_source_vector(
    source: PlaneWaveSource | DipoleSource | GaussianBeamSource | ModeSource,
    shape: tuple[int, int],
    dx: float,
    dy: float,
    origin: tuple[float, float],
    omega: float,
    mu0: float,
    stretch_x: np.ndarray,
    stretch_y: np.ndarray,
) -> np.ndarray:
    """构造源向量 J_z 网格分布 (Nx, Ny)，复数。

    源向量 b = -iωμ₀ · diag(s_x s_y) · J_z（A05 §5.2）。
    本函数返回 J_z 网格（不含 -iωμ₀ 因子，由 solver 组装时统一乘）。

    Args:
        source: 源对象（4 类之一）。
        shape: 网格形状 (Nx, Ny)。
        dx, dy: 网格间距（米）。
        origin: 网格原点 (x0, y0)，米。
        omega: 角频率 ω（rad/s）。
        mu0: 真空磁导率（H/m）。
        stretch_x: PML x 拉伸因子 (Nx,)，供 ModeSource 检测非 PML 区域。
        stretch_y: PML y 拉伸因子 (Ny,)。

    Returns:
        J_z 网格 (Nx, Ny) complex128。

    Raises:
        ValueError: 源位置越界或参数非法（规则 14，无 fall-back）。
    """
    nx, ny = shape
    j_z = np.zeros((nx, ny), dtype=np.complex128)

    if isinstance(source, PlaneWaveSource):
        # 平面波：E_z(x, y) = E_0 · exp(i·(kx·x + ky·y))
        x = origin[0] + (np.arange(nx) + 0.5) * dx
        y = origin[1] + (np.arange(ny) + 0.5) * dy
        xx, yy = np.meshgrid(x, y, indexing="ij")
        # 仅在非 PML 区域注入（避免源在 PML 内被吸收）
        interior = _interior_mask(nx, ny, stretch_x, stretch_y)
        field = source.amplitude * np.exp(1j * (source.kx * xx + source.ky * yy))
        # 平面波注入：在 source line（y = source center）附近一条线作为 J_z
        iy_center = int((source.center[1] - origin[1]) / dy)
        iy_center = max(0, min(ny - 1, iy_center))
        j_z[:, iy_center] = field[:, iy_center] * interior[:, iy_center]

    elif isinstance(source, DipoleSource):
        ix, iy = source.position
        if not (0 <= ix < nx and 0 <= iy < ny):
            raise ValueError(f"偶极子位置 ({ix},{iy}) 越界，网格形状 {shape}")
        # δ 函数近似：将点源均匀分布在单个网格单元内
        # J_z = I·dl / (dx·dy)（保持积分 = I·dl）
        j_z[ix, iy] = source.amplitude / (dx * dy)

    elif isinstance(source, GaussianBeamSource):
        ix_c, iy_line = source.center
        if not (0 <= ix_c < nx and 0 <= iy_line < ny):
            raise ValueError(f"高斯光束中心 ({ix_c},{iy_line}) 越界，网格形状 {shape}")
        x = origin[0] + (np.arange(nx) + 0.5) * dx
        # 高斯分布在垂直于传播方向的方向上
        if source.direction in ("y+", "y-"):
            # 沿 y 传播，束腰在 x 方向
            profile = np.exp(-((x - (origin[0] + (ix_c + 0.5) * dx)) ** 2) / source.waist_radius**2)
            j_z[:, iy_line] = source.amplitude * profile
        else:  # x+/x-
            y = origin[1] + (np.arange(ny) + 0.5) * dy
            profile = np.exp(
                -((y - (origin[1] + (iy_line + 0.5) * dy)) ** 2) / source.waist_radius**2
            )
            j_z[ix_c, :] = source.amplitude * profile

    elif isinstance(source, ModeSource):
        mode = source.mode
        if mode.shape != shape:
            raise ValueError(
                f"FDE 模式形状 {mode.shape} 与 FDFD 网格 {shape} 不匹配，"
                "请用相同 YeeGrid 重新求解 FDE 或插值"
            )
        ix_or_iy = source.line_index
        if source.direction in ("y+", "y-"):
            if not (0 <= ix_or_iy < nx):
                raise ValueError(f"注入线索引 {ix_or_iy} 越界（Nx={nx}），方向 {source.direction}")
            # 沿 y 传播：注入 E_z 在 x = line_index 处
            j_z[ix_or_iy, :] = source.amplitude * mode.ez[ix_or_iy, :]
        else:  # x+/x-
            if not (0 <= ix_or_iy < ny):
                raise ValueError(f"注入线索引 {ix_or_iy} 越界（Ny={ny}），方向 {source.direction}")
            j_z[:, ix_or_iy] = source.amplitude * mode.ez[:, ix_or_iy]

    else:
        raise TypeError(f"未知源类型 {type(source).__name__}")

    return j_z


def _interior_mask(
    nx: int,
    ny: int,
    stretch_x: np.ndarray,
    stretch_y: np.ndarray,
    pml_layers: int = 8,
) -> np.ndarray:
    """构造非 PML 区域掩码 (Nx, Ny)，True = 内部（非 PML）。

    用于平面波源避免在 PML 内注入。
    """
    mask = np.ones((nx, ny), dtype=bool)
    mask[:pml_layers, :] = False
    mask[-pml_layers:, :] = False
    mask[:, :pml_layers] = False
    mask[:, -pml_layers:] = False
    return mask
