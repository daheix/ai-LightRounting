"""EME 求解器（A02 §6，双向本征模展开 + Redheffer 星积级联）。

EME 求解流程（与 Lumerical EME Solver + Analysis 模式对齐）：
1. 阶段一（模式求解，耗时主要部分）：每个 cell 的本地本征模由 FDE 提供
   （已按 1W 功率归一化，A04 §11.2 统一数据结构零成本复用）。
2. 阶段二（S 矩阵级联，毫秒级）：
   - 构造界面 S 矩阵序列：I(0,1), I(1,2), ..., I(N-2,N-1)（A02 §7.3）
   - 构造传播 S 矩阵序列：P(1), P(2), ..., P(N-1)（A02 §7.4）
   - 交替级联：S_global = I(0,1) ★ P(1) ★ I(1,2) ★ P(2) ★ ... ★ I(N-2,N-1) ★ P(N-1)
     （cell 0 为输入参考波导，无传播；cells 1..N-1 各自传播，A02 §8 伪代码）
3. 端口投影：基模激励 a_inc = [1, 0, ..., 0]，提取反射/透射振幅与能量守恒校验。

Analysis 模式（A02 §6 阶段二优势，Lumerical EME Propagate）：
    cell 长度 L_i 可任意扫描，仅需重算 P(i) = diag(exp(i·β_i·L_i)) 并级联，
    无需重算本地模（模式求解结果缓存）。本求解器每次 solve 调用即完整重算，
    Analysis 模式长度扫描可在外层循环调用 build_propagation_smatrix + cascade_redheffer
    实现（毫秒级响应，与 Lumerical Group Span Sweep 行为对齐）。

BlockSMatrix 约定（与 polaris.sim.cascade.smatrix.BlockSMatrix 一致）::

    [b_left ]   [S11  S12] [a_left ]
    [b_right] = [S21  S22] [a_right]

其中 a_left 为左入射前向波（输入端口），a_right 为右入射后向波（输出端口），
b_left 为左出射（反射），b_right 为右出射（透射）。

文献来源（≥5，规则 18 学术诚信）：
1. Gallagher & Felici 2003 SPIE 4987, 69-82（EME Pros and Cons）—
   https://doi.org/10.1117/12.478061
2. Ansys Lumerical MODE-EME solver introduction —
   https://optics.ansys.com/hc/en-us/articles/360034396614
3. SimWorks Eigenmode Expansion (EME) Solver —
   https://www.emsimworks.com/en/solver/EME
4. EMEpy — Open-source eigenmode expansion solver in Python —
   https://emepy.readthedocs.io/en/stable/index.html
5. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
6. Photon Design FIMMPROP EME paper —
   https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
7. Oktay & Magden 2024 arXiv:2407.09847 —
   https://arxiv.org/abs/2407.09847

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.cascade.smatrix import BlockSMatrix, cascade_redheffer
from polaris.sim.eme.interface import build_interface_smatrix
from polaris.sim.eme.propagation import build_propagation_smatrix
from polaris.sim.fde import Mode

__all__ = [
    "EmeCell",
    "EmeConfig",
    "EmeResult",
    "EmeSolver",
    "solve_eme",
]


@dataclass
class EmeCell:
    """EME 单 cell 定义（A02 §4，z 不变截面段）。

    每个 cell 对应一段 z 不变截面波导，由 FDE 求解其本地本征模。
    cell 长度 L 用于传播 S 矩阵 P = diag(exp(i·β·L))（A02 §7.4）。
    cell 0（首个 cell）作为输入参考波导，其长度在级联中不参与传播
    （与 Lumerical EME 输入端口约定一致，A02 §8 伪代码）。

    Attributes:
        length: cell 长度 L（米），用于传播相位累积。非负。
        modes: cell 的本地本征模列表（来自 FDE，已按 1W 功率归一化）。
    """

    length: float
    modes: list[Mode]

    def __post_init__(self) -> None:
        if self.length < 0.0:
            raise ValueError(f"cell 长度必须非负，实际 {self.length}（规则 14）")
        if not self.modes:
            raise ValueError("cell 模式列表不能为空（规则 14：禁止 fall-back）")


@dataclass
class EmeConfig:
    """EME 求解配置（降低函数参数个数，规则 4）。

    Attributes:
        wavelength: 自由空间波长 λ（米）。
        dx: x 方向网格间距（米），用于重叠积分（A02 §7.2）。
        dy: y 方向网格间距（米），用于重叠积分。
        n_modes: 期望的每 cell 模式数 M（用于校验一致性）。
            设为 None 则跳过模式数校验（允许各 cell 模式数不同，但界面 S 矩阵
            要求相邻 cell 模式数一致，会在 build_interface_smatrix 中校验）。
    """

    wavelength: float
    dx: float
    dy: float
    n_modes: int | None = None

    def __post_init__(self) -> None:
        if self.wavelength <= 0.0:
            raise ValueError(f"波长必须为正，实际 {self.wavelength}（规则 14）")
        if self.dx <= 0.0 or self.dy <= 0.0:
            raise ValueError(f"网格间距必须为正，实际 dx={self.dx}, dy={self.dy}")
        if self.n_modes is not None and self.n_modes < 1:
            raise ValueError(f"模式数必须 ≥1，实际 {self.n_modes}")


@dataclass
class EmeResult:
    """EME 求解结果。

    Attributes:
        s_matrix: 全局 S 矩阵（2M×2M 分块，M = 单侧模式数）。
        reflection: 反射振幅向量 (M,)，基模激励下的反射模式系数 b_left = S11·a_inc。
        transmission: 透射振幅向量 (M,)，基模激励下的透射模式系数 a_right = S21·a_inc。
        energy_sum: 能量守恒校验 Σ|reflection|² + Σ|transmission|²，应 ≈1.0
            （M2 验收点：单界面功率守恒偏差 ≤1e-6；功率归一化模式下成立）。
        n_cells: cell 数量 N。
        n_modes: 每 cell 模式数 M。
    """

    s_matrix: BlockSMatrix
    reflection: np.ndarray
    transmission: np.ndarray
    energy_sum: float
    n_cells: int
    n_modes: int


@dataclass
class EmeSolver:
    """EME 求解器（A02 §6，双向本征模展开 + Redheffer 星积级联）。

    两阶段求解（与 Lumerical EME Solver + Analysis 模式对齐）：
    - 阶段一（模式求解）：由 EmeCell.modes 提供（FDE 已求解并功率归一化）。
    - 阶段二（S 矩阵级联）：构造界面 S + 传播 S 序列，Redheffer 星积级联。

    级联顺序（A02 §8 伪代码，cell 0 为输入参考无传播）::

        S_global = I(0,1) ★ P(1) ★ I(1,2) ★ P(2) ★ ... ★ I(N-2,N-1) ★ P(N-1)

    其中 ★ 为 Redheffer 星积（C03 共享内核），I(i,i+1) 为界面 S 矩阵，
    P(i) 为 cell i 内传播 S 矩阵。

    Attributes:
        cells: cell 列表（从输入到输出顺序，cell 0 为输入参考波导）。
        config: 求解配置（波长/网格间距/模式数）。
    """

    cells: list[EmeCell]
    config: EmeConfig

    def __post_init__(self) -> None:
        if not self.cells:
            raise ValueError("cell 列表不能为空（规则 14：禁止 fall-back）")
        # 模式数一致性校验（可选，n_modes 非 None 时启用）
        if self.config.n_modes is not None:
            for i, cell in enumerate(self.cells):
                if len(cell.modes) != self.config.n_modes:
                    raise ValueError(
                        f"cell {i} 模式数 {len(cell.modes)} 与配置 n_modes="
                        f"{self.config.n_modes} 不一致。"
                    )
        # 校验所有 cell 的模式网格形状一致（重叠积分要求同一横向网格）
        shape0 = self.cells[0].modes[0].shape
        for i, cell in enumerate(self.cells):
            for j, mode in enumerate(cell.modes):
                if mode.shape != shape0:
                    raise ValueError(
                        f"cell {i} 模式 {j} 网格形状 {mode.shape} 与首 cell {shape0} 不一致，"
                        "无法计算重叠积分（要求所有 cell 的 FDE 网格相同）。"
                    )

    def solve(self) -> EmeResult:
        """求解 EME 全局 S 矩阵（A02 §6 完整流程）。

        Returns:
            EmeResult（含全局 S 矩阵 + 反射/透射振幅 + 能量守恒校验）。
        """
        n_cells = len(self.cells)
        n_modes = len(self.cells[0].modes)
        dx, dy = self.config.dx, self.config.dy

        # 构造 S 矩阵序列（A02 §8 伪代码）：
        # I(0,1), P(1), I(1,2), P(2), ..., I(N-2,N-1), P(N-1)
        s_list: list[BlockSMatrix] = []
        for i in range(n_cells - 1):
            # 界面 S 矩阵（cell i → cell i+1，切向场连续 + 正交投影，A02 §7.3）
            s_list.append(
                build_interface_smatrix(self.cells[i].modes, self.cells[i + 1].modes, dx, dy)
            )
            # 传播 S 矩阵（cell i+1 内，相位累积 P = diag(exp(i·β·L))，A02 §7.4）
            betas_next = np.array([m.beta for m in self.cells[i + 1].modes], dtype=np.complex128)
            s_list.append(build_propagation_smatrix(betas_next, self.cells[i + 1].length))

        # 单 cell 退化情况：无界面，仅传播（均匀波导段）
        if not s_list:
            betas0 = np.array([m.beta for m in self.cells[0].modes], dtype=np.complex128)
            s_list.append(build_propagation_smatrix(betas0, self.cells[0].length))

        # Redheffer 星积级联（C03 共享内核，数值稳定，避免消逝波指数发散）
        s_global = cascade_redheffer(s_list)

        # 端口投影：基模激励 a_inc = [1, 0, ..., 0]（A02 §7.6 端口 S 参数）
        a_inc = np.zeros(n_modes, dtype=np.complex128)
        a_inc[0] = 1.0
        # 反射振幅 b_left = S11·a_inc，透射振幅 a_right = S21·a_inc
        reflection = s_global.s11 @ a_inc
        transmission = s_global.s21 @ a_inc

        # 能量守恒校验（M2 验收点：功率归一化模式下 Σ|b|² ≈ 1.0）
        energy_sum = float(np.sum(np.abs(reflection) ** 2) + np.sum(np.abs(transmission) ** 2))

        return EmeResult(
            s_matrix=s_global,
            reflection=reflection,
            transmission=transmission,
            energy_sum=energy_sum,
            n_cells=n_cells,
            n_modes=n_modes,
        )


def solve_eme(cells: list[EmeCell], config: EmeConfig) -> EmeResult:
    """便捷入口：求解 EME 全局 S 矩阵（A02 §6）。

    Args:
        cells: cell 列表（从输入到输出顺序，cell 0 为输入参考波导）。
        config: 求解配置（波长/网格间距/模式数）。

    Returns:
        EmeResult（含全局 S 矩阵 + 反射/透射振幅 + 能量守恒校验）。

    Raises:
        ValueError: cell 列表为空、模式数不一致或网格形状不匹配（规则 14）。

    示例::

        from polaris.sim.eme import EmeCell, EmeConfig, solve_eme
        cells = [EmeCell(length=1e-6, modes=modes_0), EmeCell(length=2e-6, modes=modes_1)]
        result = solve_eme(cells, EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8))
        print(f"能量守恒: {result.energy_sum:.6f}")  # ≈1.0
    """
    solver = EmeSolver(cells=cells, config=config)
    return solver.solve()
