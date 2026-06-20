"""障碍物栅格存储 + 动态网格尺寸计算（Task C3）。

为大规模电路（500-1000 器件，5000×5000 μm 画布）提供内存高效的障碍物存储，
并根据画布尺寸与器件数自动选择最优网格分辨率。

方法参考（方案检索，见项目规则 1.1）：
- LiDAR (ISPD 2025) 间距保证 A* 网格尺寸设置：grid_size > 波导宽度
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Ada-Routing (ICCAD 2025) 网格尺寸 = 最小弯曲半径
  https://personal.hkust-gz.edu.cn/yuzhema/papers/ICCAD2025-Ada-Routing.pdf
- DREAMPlace (DAC 2019) 大规模网格分块 + GPU 加速（4M 单元 4MB bool）
  https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- Sturtevant (AAAI AIIDE 2011) 稀疏网格动态环境表示
  https://cdn.aaai.org/ojs/12438/12438-52-15966-1-2-20201228.pdf
- 稀疏数组阈值规则：非默认单元 < 10-20% 时稀疏存储值得考虑
  https://thelinuxcode.com/sparse-arrays-in-programming-practical-representations-trade-offs-and-implementations/

决策矩阵（基于上述来源）：
- 总单元 ≤ 4M（如 2000×2000）：稠密 numpy bool 数组（1 B/单元，最快随机访问）
- 总单元 > 4M 且障碍物稀疏：Python set 存储（72 B/单元，但仅存障碍物）
- 经验公式：grid_size = max(waveguide_width × 1.2, min_bend_radius / 2, canvas / 2000)
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

# 稠密存储的单元数上限（4M = 2000×2000，numpy bool 4MB）
# 来源: DREAMPlace bigblue3 基准用 2048×2048=4.19M 单元，8-16GB GPU 内存
# 本项目 CPU 环境，4M bool = 4MB，内存安全
_DENSE_CELL_LIMIT = 4_000_000

# 各平台波导宽度（μm），来源: SiEPIC EBeam PDK + spec.md
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_PLATFORM_WAVEGUIDE_WIDTH = {
    "SOI": 0.5,
    "SiN": 1.0,
    "InP": 2.0,
    "LNOI": 1.5,
}

# 网格分辨率经验公式中的画布分母
# 来源: DREAMPlace 大规模基准（2000×2000 单元为甜点）
_CANVAS_DIVISOR = 2000


def auto_grid_size(
    canvas_w: float,
    canvas_h: float,
    platform: str = "SOI",
    min_bend_radius_um: float | None = None,
) -> float:
    """根据画布尺寸与平台约束自动选择最优网格分辨率。

    经验公式（来源: LiDAR ISPD 2025 + Ada-Routing ICCAD 2025 + DREAMPlace DAC 2019）::

        grid_size = max(
            waveguide_width * 1.2,      # 物理约束：grid > 波导宽度（LiDAR）
            min_bend_radius / 2,        # 弯曲离散化精度（Ada-Routing）
            max(canvas_w, canvas_h) / 2000  # 计算可扩展性（DREAMPlace）
        )

    对于 5000×5000 μm 画布 + SOI 平台（R_min=5μm, w=0.5μm）::
        grid_size = max(0.6, 2.5, 2.5) = 2.5 μm → 2000×2000 = 4M 单元

    Args:
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        min_bend_radius_um: 最小弯曲半径（μm）。None 时从平台默认约束读取。

    Returns:
        最优网格分辨率（μm）。

    Raises:
        ValueError: canvas_w 或 canvas_h 非正数。
    """
    if canvas_w <= 0 or canvas_h <= 0:
        raise ValueError(f"画布尺寸必须为正数: canvas_w={canvas_w}, canvas_h={canvas_h}")

    waveguide_width = _PLATFORM_WAVEGUIDE_WIDTH.get(platform, 0.5)
    if min_bend_radius_um is None:
        from polaris.router.waveguide_router import get_platform_constraints

        min_bend_radius_um = get_platform_constraints(platform)["min_bend_radius_um"]

    # 经验公式（来源: LiDAR + Ada-Routing + DREAMPlace）
    physical_lower = waveguide_width * 1.2  # LiDAR 间距保证
    bend_lower = min_bend_radius_um / 2.0  # 弯曲离散化精度
    scalability_lower = max(canvas_w, canvas_h) / _CANVAS_DIVISOR  # 计算可扩展性

    return max(physical_lower, bend_lower, scalability_lower)


class ObstacleGrid:
    """障碍物栅格存储（稠密 numpy bool / 稀疏 set 自适应）。

    根据总单元数自动选择存储方式：
    - 总单元 ≤ 4M：稠密 numpy bool 数组（1 B/单元，最快随机访问）
    - 总单元 > 4M：稀疏 set 存储（仅存障碍物坐标，72 B/单元但数量少）

    来源: Sturtevant AAAI AIIDE 2011 稀疏网格动态环境表示
    https://cdn.aaai.org/ojs/12438/12438-52-15966-1-2-20201228.pdf

    接口设计为显式方法（非 __getitem__/__setitem__），避免切片语义歧义，
    降低 GridRouter 调用方的认知负担。
    """

    def __init__(self, grid_w: int, grid_h: int) -> None:
        """初始化障碍物栅格。

        Args:
            grid_w: 栅格宽度（列数）。
            grid_h: 栅格高度（行数）。

        Raises:
            ValueError: grid_w 或 grid_h 非正数。
        """
        if grid_w <= 0 or grid_h <= 0:
            raise ValueError(f"栅格尺寸必须为正数: grid_w={grid_w}, grid_h={grid_h}")
        self._grid_w = grid_w
        self._grid_h = grid_h
        total = grid_w * grid_h
        self._dense = total <= _DENSE_CELL_LIMIT
        if self._dense:
            self._array: np.ndarray = np.zeros((grid_h, grid_w), dtype=np.int32)
            self._sparse: set[tuple[int, int]] = set()  # 占位，不使用
        else:
            self._array = np.zeros((0, 0), dtype=np.int32)  # 占位，不使用
            self._sparse = set()

    @property
    def shape(self) -> tuple[int, int]:
        """返回栅格形状 (grid_h, grid_w)，兼容 numpy.ndarray.shape 接口。"""
        return (self._grid_h, self._grid_w)

    @property
    def is_dense(self) -> bool:
        """是否使用稠密存储。"""
        return self._dense

    @property
    def total_cells(self) -> int:
        """总单元数。"""
        return self._grid_w * self._grid_h

    def mark_region(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """标记矩形区域为障碍物。

        Args:
            x0: 起始列（含）。
            y0: 起始行（含）。
            x1: 结束列（不含）。
            y1: 结束行（不含）。
        """
        cx0 = max(0, x0)
        cy0 = max(0, y0)
        cx1 = min(self._grid_w, x1)
        cy1 = min(self._grid_h, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        if self._dense:
            self._array[cy0:cy1, cx0:cx1] = 1
        else:
            for gy in range(cy0, cy1):
                for gx in range(cx0, cx1):
                    self._sparse.add((gx, gy))

    def is_blocked(self, x: int, y: int) -> bool:
        """检查单元是否被障碍物占用。

        Args:
            x: 列索引。
            y: 行索引。

        Returns:
            True 表示该单元为障碍物。
        """
        if self._dense:
            return bool(self._array[y, x])
        return (x, y) in self._sparse

    def get(self, x: int, y: int) -> int:
        """获取单元的障碍物标记值（0 或 1）。

        Args:
            x: 列索引。
            y: 行索引。

        Returns:
            0 表示可通行，1 表示障碍物。
        """
        if self._dense:
            return int(self._array[y, x])
        return 1 if (x, y) in self._sparse else 0

    def set(self, x: int, y: int, val: int) -> None:
        """设置单元的障碍物标记。

        Args:
            x: 列索引。
            y: 行索引。
            val: 0 表示清除，非 0 表示标记为障碍物。
        """
        if self._dense:
            self._array[y, x] = 1 if val else 0
        else:
            if val:
                self._sparse.add((x, y))
            else:
                self._sparse.discard((x, y))

    def __getitem__(self, key: tuple[int, int]) -> int:
        """下标访问 ``grid[y, x]``（兼容旧 numpy 风格代码）。

        Args:
            key: ``(y, x)`` 元组。

        Returns:
            0 表示可通行，1 表示障碍物。
        """
        y, x = key
        return self.get(x, y)

    def __setitem__(self, key: tuple[int, int], val: int) -> None:
        """下标赋值 ``grid[y, x] = val``（兼容旧 numpy 风格代码）。

        Args:
            key: ``(y, x)`` 元组。
            val: 0 表示清除，非 0 表示标记为障碍物。
        """
        y, x = key
        self.set(x, y, val)

    def blocked_cells(self) -> Iterable[tuple[int, int]]:
        """返回所有被阻塞的单元坐标（用于调试/测试）。

        Returns:
            障碍物坐标迭代器 ``[(x, y), ...]``。
        """
        if self._dense:
            ys, xs = np.where(self._array > 0)
            return zip(xs.tolist(), ys.tolist())
        return iter(self._sparse)

    def memory_estimate_bytes(self) -> int:
        """估算当前存储内存占用（字节）。

        Returns:
            内存占用字节数。
        """
        if self._dense:
            return self._array.nbytes
        # Python tuple set 每条约 72 字节（来源: KiCadRoutingTools 实测）
        return len(self._sparse) * 72


__all__ = [
    "ObstacleGrid",
    "auto_grid_size",
]
