"""FDFD 端口 S 参数提取与能量守恒校验（A05 §10 后处理）。

S 参数提取流程（A05 §5.2 步骤 10）：
1. 在每个端口处提取场分布 E_z（沿端口横截面网格线）
2. 与 FDE 模式做重叠积分，得到模式振幅 a_n（入射）/ b_n（出射）
3. 归一化至端口功率，组装 S 矩阵 S_ij = b_n / a_j

能量守恒校验（A05 §11.1 / spec.md S1-C2）：
- TFSF 散射问题 Σ|R|² + Σ|T|² = 1，偏差 ≤ 1e-3
- 失败立即 raise（规则 14，禁止 fall-back）

文献来源（≥5，规则 R02 学术诚信）：
1. Pozar DM, "Microwave Engineering," 4th ed., Wiley (2011), §4.3
   （S 参数归一化）— https://www.wiley.com/en-us/9780470631553
2. Shin W, Fan S, "Choice of the perfectly matched layer boundary
   condition for frequency-domain Maxwell's equations solvers,"
   J. Comput. Phys. 231, 3406-3431 (2012) —
   https://doi.org/10.1016/j.jcp.2012.01.013
3. Lumerical FDTD S 参数提取手册 (Ansys, 2024) —
   https://support.lumerical.com/hc/en-us/articles/360034395234
4. Ansys Lumerical, "Edge Coupler — S-parameter Extraction Methodology"
   (2024) — https://optics.ansys.com/hc/en-us/articles/360042305354
5. Yee K, "Numerical solution of initial boundary value problems
   involving Maxwell's equations in isotropic media," IEEE Trans.
   Antennas Propag. 14, 302-307 (1966) —
   https://doi.org/10.1109/TAP.1966.1138693
6. Taflove A, Hagness SC, "Computational Electrodynamics," 3rd ed.,
   Artech House (2005) — https://doi.org/10.1002/0471654507.erfme149

规则依据：规则 14（能量守恒失败 raise，无 fall-back）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.fde.mode import Mode

__all__ = ["PortSpec", "SParameters", "extract_s_parameters", "verify_energy_conservation"]


@dataclass(frozen=True)
class PortSpec:
    """端口规格（FDFD S 参数提取用）。

    Attributes:
        name: 端口名称（如 'in', 'out', 'thru'）。
        mode: 端口基模（FDE 求解结果，已归一化）。
        line_index: 端口横截面网格索引（垂直于传播方向的网格线）。
        direction: 传播方向 'x+' / 'x-' / 'y+' / 'y-'（指向器件内部为正）。
        sign: 端口方向符号 +1（出射）或 -1（入射），由 direction 推导。
    """

    name: str
    mode: Mode
    line_index: int
    direction: str

    def __post_init__(self) -> None:
        if self.direction not in ("x+", "x-", "y+", "y-"):
            raise ValueError(f"端口方向必须为 'x+'/'x-'/'y+'/'y-'，实际 {self.direction}")
        if self.line_index < 0:
            raise ValueError(f"端口网格索引必须 ≥0，实际 {self.line_index}")

    @property
    def sign(self) -> float:
        """方向符号：'+' 方向传播为 +1，'-' 方向为 -1。"""
        return +1.0 if self.direction.endswith("+") else -1.0


@dataclass
class SParameters:
    """S 参数提取结果。

    Attributes:
        matrix: S 矩阵 (N_ports, N_ports) complex128，S[i,j] = b_i / a_j。
        port_names: 端口名称列表（与矩阵行列对应）。
        a_coefficients: 各端口入射模式振幅 (N_ports,) complex128。
        b_coefficients: 各端口出射模式振幅 (N_ports,) complex128。
        power_in: 入射总功率（W）。
        power_out: 出射总功率（W）。
        energy_conservation: Σ|S|² 行和（每端口能量守恒指标）。
    """

    matrix: np.ndarray
    port_names: list[str]
    a_coefficients: np.ndarray
    b_coefficients: np.ndarray
    power_in: float
    power_out: float
    energy_conservation: np.ndarray


def _mode_amplitude(
    e_z_field: np.ndarray,
    mode: Mode,
    line_index: int,
    direction: str,
    dx: float,
    dy: float,
) -> complex:
    """提取单个端口的模式振幅（重叠积分）。

    重叠积分（A05 §7 模式匹配）：
        a = ∫ E_z,field · E_z,mode* dℓ / ∫ |E_z,mode|² dℓ

    其中积分沿端口横截面线（垂直于传播方向）。

    Args:
        e_z_field: FDFD 求解得到的 E_z 场 (Nx, Ny)。
        mode: FDE 端口基模。
        line_index: 端口网格线索引。
        direction: 'x+'/'x-'/'y+'/'y-'。
        dx, dy: 网格间距（米）。

    Returns:
        复数模式振幅 a（或 b，视入射/出射而定）。
    """
    if direction.startswith("x"):
        # 沿 x 传播，端口横截面在 y 方向（一条 y 线）
        field_line = e_z_field[line_index, :]
        mode_line = mode.ez[line_index, :]
        d_ell = dy
    else:  # y+/y-
        field_line = e_z_field[:, line_index]
        mode_line = mode.ez[:, line_index]
        d_ell = dx
    # 重叠积分：分子 ∫ E_field · E_mode* dℓ
    numerator = np.sum(field_line * np.conj(mode_line)) * d_ell
    # 分母 ∫ |E_mode|² dℓ（归一化因子，避免重复计算）
    denominator = np.sum(np.abs(mode_line) ** 2) * d_ell
    if abs(denominator) < 1e-30:
        raise ValueError(
            f"端口模式 |E_z|² 积分 ≈ 0（line_index={line_index}, "
            f"direction={direction}），无法提取模式振幅"
        )
    return complex(numerator / denominator)


def extract_s_parameters(
    e_z_field: np.ndarray,
    ports: list[PortSpec],
    dx: float,
    dy: float,
) -> SParameters:
    """从 FDFD 求解场提取多端口 S 参数。

    流程：
    1. 对每个端口 j，注入其基模，求解 FDFD 得到 E_z 场
    2. 对每个端口 i，提取模式振幅 b_i
    3. S[i,j] = b_i / a_j（a_j 由 ModeSource 注入幅度决定，单位归一化）

    本函数假设 e_z_field 为单次激励下的求解结果，a_j 已知（=1 单位注入）。
    对多端口器件需多次求解（每次激励一个端口），逐列填充 S 矩阵。

    Args:
        e_z_field: FDFD 求解场 (Nx, Ny) complex128。
        ports: 端口列表（每个端口含 FDE 模式 + 位置 + 方向）。
        dx, dy: 网格间距（米）。

    Returns:
        SParameters 数据类，含 S 矩阵、模式振幅、能量守恒指标。

    Raises:
        ValueError: 端口数为 0 或位置不合法（规则 14）。
    """
    if not ports:
        raise ValueError("端口列表为空，无法提取 S 参数")
    n_ports = len(ports)
    port_names = [p.name for p in ports]
    # 提取所有端口的模式振幅
    amplitudes = np.zeros(n_ports, dtype=np.complex128)
    for i, port in enumerate(ports):
        amplitudes[i] = _mode_amplitude(
            e_z_field, port.mode, port.line_index, port.direction, dx, dy
        )
    # 假设端口 0 为激励端口（a_0 = 1.0，其余 a_i = 0）
    # 输出列向量 b 即为 S 矩阵第 0 列
    a_coeffs = np.zeros(n_ports, dtype=np.complex128)
    a_coeffs[0] = 1.0
    b_coeffs = amplitudes.copy()
    # 单列 S 矩阵（多端口多次激励由调用方逐列填充）
    s_matrix = b_coeffs.reshape(n_ports, 1) / max(abs(a_coeffs[0]), 1e-30)
    # 入射/出射功率（按 1W 归一化模式计算）
    power_in = float(np.sum(np.abs(a_coeffs) ** 2))
    power_out = float(np.sum(np.abs(b_coeffs) ** 2))
    # 能量守恒：每端口 |b_i|² / Σ|a_j|²（行和）
    energy = np.abs(b_coeffs) ** 2
    if power_in > 1e-30:
        energy_conservation = energy / power_in
    else:
        energy_conservation = energy
    return SParameters(
        matrix=s_matrix,
        port_names=port_names,
        a_coefficients=a_coeffs,
        b_coefficients=b_coeffs,
        power_in=power_in,
        power_out=power_out,
        energy_conservation=energy_conservation,
    )


def verify_energy_conservation(
    s_params: SParameters,
    tolerance: float = 1e-3,
) -> float:
    """校验能量守恒 Σ|R|² + Σ|T|² = 1 ± tolerance（A05 §11.1 / spec.md S1-C2）。

    对无源无损耗二端口器件：|S_11|² + |S_21|² = 1（反射 + 透射 = 入射）
    对多端口：Σ_j |S_ij|² = 1（每行能量守恒，互易无损器件）

    Args:
        s_params: S 参数提取结果。
        tolerance: 容差，默认 1e-3（spec.md S1-C2 标准）。

    Returns:
        实际能量守恒值 Σ|S|²（应为 1.0 ± tolerance）。

    Raises:
        ValueError: 能量守恒失败（偏差 > tolerance，规则 14 禁止 fall-back）。
    """
    # 单列情况：检查 |b_0|² + |b_1|² + ... ≈ |a_0|² = 1
    total = float(np.sum(np.abs(s_params.b_coefficients) ** 2))
    deviation = abs(total - s_params.power_in)
    if deviation > tolerance:
        raise ValueError(
            f"能量守恒失败：Σ|b|² = {total:.6e}, Σ|a|² = {s_params.power_in:.6e}, "
            f"偏差 {deviation:.6e} > 容差 {tolerance:.6e}。"
            "可能原因：PML 反射过大 / 网格分辨率不足 / 源位置不当（规则 14，无 fall-back）"
        )
    return total
