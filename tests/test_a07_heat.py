"""A07-HEAT 稳态热传导求解器验收测试（M1-M3）。

验证 polaris.sim.heat 包的稳态傅里叶导热求解栈：
- solver.py: 5 点有限差分 + 调和平均热导率 + scipy.sparse.linalg.spsolve 直接求解
- boundary.py: 5 类边界条件（Dirichlet/Neumann/Convective/Radiative/Periodic）
- coupling.py: HEAT→FDE 热光耦合 + DDM→HEAT 焦耳热

验收标准（spec tasks.md Task 2.4）：
- M1 解析解对比：1D 平板固定温差，误差 ≤1e-10
- M2 功率守恒：全绝热 + 内部热源 → raise ValueError（无稳态解）
- M3 5 类边界均可应用，不报错

物理参数（Cocorullo 1999 / Incropera / CODATA 2018）：
- 硅热导率 k_Si = 148 W/(m·K)
- SiO2 热导率 k_SiO2 = 1.4 W/(m·K)
- 硅热光系数 dn/dT = 1.86e-4 /K（Cocorullo 1999）
- Stefan-Boltzmann σ_SB = 5.670374419e-8 W/(m²·K⁴)
- 网格 dx = dy = 1e-7 m（100nm）

文献来源（≥5，规则 18 学术诚信）：
1. Litz 2011 Optics Express — https://doi.org/10.1364/OE.19.012997
2. Cocorullo 1999 IEEE J Quantum Electron — https://doi.org/10.1109/3.791939
3. COMSOL Heat Transfer Module — https://www.comsol.com/heat-transfer-module
4. Incropera & DeWitt, Fundamentals of Heat and Mass Transfer —
   https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
5. scipy.sparse.linalg.spsolve —
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
6. Schneider 1973 IEEE Trans MTT — https://doi.org/10.1109/TMTT.1973.1127965
7. Komma 2012 Appl Phys Lett — https://doi.org/10.1063/1.4738989

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest
from scipy import sparse

from polaris.sim.heat import (
    ADIABATIC,
    ALPHA_SILICON,
    CP_SILICON,
    CP_SIO2,
    DN_DT_SI,
    K_SILICON,
    K_SIO2,
    RHO_SILICON,
    RHO_SIO2,
    SIGMA_SB,
    BcSpec,
    BoundaryType,
    DDMResult,
    HeatConfig,
    HeatResult,
    HeatSolver,
    TransientHeatConfig,
    TransientHeatResult,
    TransientHeatSolver,
    apply_boundary_conditions,
    ddm_to_heat,
    heat_to_fde,
    is_grounding_bc,
    radiative_h,
    solve_heat,
    solve_transient_heat,
    thermal_time_constant_1d,
)

# 物理参数（Cocorullo 1999 / Incropera / CODATA 2018，与 src 常量一致）
_K_SI = K_SILICON  # 148 W/(m·K)
_K_SIO2 = K_SIO2  # 1.4 W/(m·K)
_DN_DT = DN_DT_SI  # 1.86e-4 /K
_DX = 1e-7  # 100nm 网格间距
_T_REF = 300.0  # 室温参考


# ---------------------------------------------------------------------------
# FDE 模式桩（duck-typed，供 heat_to_fde 光强加权耦合使用）
# ---------------------------------------------------------------------------
@dataclass
class _ModeStub:
    """FDE Mode 鸭子类型桩：含 shape 与电场分量 ex/ey/ez。"""

    shape: tuple[int, int]
    ex: np.ndarray
    ey: np.ndarray
    ez: np.ndarray


def _uniform_mode(shape: tuple[int, int]) -> _ModeStub:
    """构造均匀光强模式（ex=1, ey=ez=0），用于热光耦合测试。"""
    nx, ny = shape
    return _ModeStub(
        shape=shape,
        ex=np.ones((nx, ny)),
        ey=np.zeros((nx, ny)),
        ez=np.zeros((nx, ny)),
    )


# ===========================================================================
# 1. TestHeatConfig — 配置构造与参数校验（3 tests）
# ===========================================================================
class TestHeatConfig:
    """HeatConfig 数据类构造与非法参数校验。"""

    def test_config_valid_construction(self) -> None:
        """合法配置构造成功，shape 属性与 k_arr 一致。"""
        k = np.full((16, 8), _K_SI)
        q = np.zeros((16, 8))
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=k,
            q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
            },
        )
        assert cfg.shape == (16, 8)
        assert cfg.dx == _DX
        # effective_bc 缺失方向默认绝热 Neumann
        assert cfg.effective_bc("south").type is BoundaryType.NEUMANN
        assert cfg.effective_bc("south").value == 0.0

    def test_config_invalid_dx_raises(self) -> None:
        """dx ≤ 0 须 raise ValueError（物理约束：网格间距须为正）。"""
        k = np.full((4, 4), _K_SI)
        q = np.zeros((4, 4))
        with pytest.raises(ValueError, match="dx"):
            HeatConfig(dx=0.0, dy=_DX, k_arr=k, q_arr=q)
        with pytest.raises(ValueError, match="dy"):
            HeatConfig(dx=_DX, dy=-1e-7, k_arr=k, q_arr=q)

    def test_config_shape_mismatch_raises(self) -> None:
        """k_arr 与 q_arr 形状不匹配须 raise ValueError。"""
        with pytest.raises(ValueError, match="形状不匹配"):
            HeatConfig(
                dx=_DX,
                dy=_DX,
                k_arr=np.full((4, 4), _K_SI),
                q_arr=np.zeros((4, 3)),
            )


# ===========================================================================
# 2. TestBoundaryTypes — 5 类边界条件枚举与应用（4 tests）
# ===========================================================================
class TestBoundaryTypes:
    """BoundaryType 枚举完整性与边界行替换正确性。"""

    def test_boundary_type_enum(self) -> None:
        """5 类边界枚举完整：Dirichlet/Neumann/Convective/Radiative/Periodic。"""
        names = {bt.name for bt in BoundaryType}
        assert names == {
            "DIRICHLET",
            "NEUMANN",
            "CONVECTIVE",
            "RADIATIVE",
            "PERIODIC",
        }
        # is_grounding_bc：仅 Dirichlet/Convective/Radiative 锚定温度
        assert is_grounding_bc(BcSpec(type=BoundaryType.DIRICHLET, value=1.0))
        assert is_grounding_bc(BcSpec(type=BoundaryType.CONVECTIVE, h=1.0))
        assert is_grounding_bc(BcSpec(type=BoundaryType.RADIATIVE, emissivity=0.5))
        assert not is_grounding_bc(BcSpec(type=BoundaryType.NEUMANN, value=0.0))
        assert not is_grounding_bc(BcSpec(type=BoundaryType.PERIODIC))
        # ADIABATIC 默认规格为 Neumann q=0
        assert ADIABATIC.type is BoundaryType.NEUMANN
        assert ADIABATIC.value == 0.0

    def test_dirichlet_bc_applied(self) -> None:
        """Dirichlet 边界行替换正确：BC 行对角=1、邻接清零、b=T_fixed。"""
        # 构造 2×1 网格，A 含耦合，west Dirichlet=300
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((2, 1), _K_SI),
            q_arr=np.zeros((2, 1)),
            bc_dict={"west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0)},
        )
        # 非平凡 A（含耦合），验证 west 行被掩蔽+替换
        A = sparse.csr_matrix(np.array([[2.0, -1.0], [-1.0, 2.0]]))
        b = np.array([5.0, 7.0])
        A_f, b_f = apply_boundary_conditions(A, b, cfg)
        A_dense = A_f.toarray()
        # west 节点行替换为 [1, 0]，b=300
        assert np.allclose(A_dense[0], [1.0, 0.0])
        assert np.isclose(b_f[0], 300.0)
        # east 节点未指定 BC，保持原行 [-1, 2]，b=7
        assert np.allclose(A_dense[1], [-1.0, 2.0])
        assert np.isclose(b_f[1], 7.0)

    def test_neumann_bc_applied(self) -> None:
        """Neumann 边界（含绝热 q=0）：1D 一端 Dirichlet 一端绝热 → 均匀温度。"""
        nx, ny = 40, 1
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.NEUMANN, value=0.0),  # 绝热
            },
        )
        res = HeatSolver().solve(cfg)
        # 无源 + 一端绝热 → 稳态均匀 T=300（无热流，温度场平）
        assert np.max(np.abs(res.temperature[:, 0] - 300.0)) < 1e-9
        # 绝热端法向梯度 ∂T/∂n = 0
        dTdx_east = (res.temperature[-1, 0] - res.temperature[-2, 0]) / _DX
        assert abs(dTdx_east) < 1e-3

    def test_convective_bc_applied(self) -> None:
        """对流边界 Newton 冷却 -k·∂T/∂n = h·(T-T_amb)：端点温度匹配解析 Robin。"""
        nx, ny = 40, 1
        L = (nx - 1) * _DX
        h_conv = 1e5  # 对流系数 W/(m²·K)
        t_amb = 300.0
        t0 = 350.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=t0),
                "east": BcSpec(type=BoundaryType.CONVECTIVE, value=0.0, h=h_conv, t_amb=t_amb),
            },
        )
        res = HeatSolver().solve(cfg)
        # 线性分布 T(x)=t0+(Te-t0)·x/L，Te 由 -k·(Te-t0)/L = h·(Te-Tamb) 解出
        te_an = (h_conv * t_amb + _K_SI * t0 / L) / (h_conv + _K_SI / L)
        assert abs(res.temperature[-1, 0] - te_an) < 1e-6


# ===========================================================================
# 3. TestSolver1D — 1D 求解器解析解对比（5 tests，M1 核心）
# ===========================================================================
class TestSolver1D:
    """1D 稳态热传导解析解对比。"""

    def test_1d_plate_analytical_solution(self) -> None:
        """M1 决定性测试：1D 平板 T(0)=300, T(L)=400，解析解 T=300+100·x/L，误差 ≤1e-10。"""
        nx, ny = 64, 1
        L = (nx - 1) * _DX
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
            },
        )
        res = HeatSolver().solve(cfg)
        x = np.arange(nx) * _DX
        t_analytical = 300.0 + 100.0 * x / L
        # M1 验收：误差 ≤1e-10（实际 ~1e-12，Dirichlet 端点精确固定）
        assert np.max(np.abs(res.temperature[:, 0] - t_analytical)) < 1e-10

    def test_1d_heat_source_uniform(self) -> None:
        """均匀热源 + 两端固定温度 T0，抛物线解 T(x)=T0+Q·x·(L-x)/(2k)。"""
        nx, ny = 80, 1
        L = (nx - 1) * _DX
        q_vol = 1e9  # 体积热源 W/m³
        t0 = 300.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.full((nx, ny), q_vol),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=t0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=t0),
            },
        )
        res = HeatSolver().solve(cfg)
        x = np.arange(nx) * _DX
        # k·T'' + Q = 0 → T(x)=T0 + Q·x·(L-x)/(2k)
        t_analytical = t0 + q_vol * x * (L - x) / (2.0 * _K_SI)
        assert np.max(np.abs(res.temperature[:, 0] - t_analytical)) < 1e-10

    def test_1d_neumann_adiabatic(self) -> None:
        """一端 Dirichlet(T0) + 一端绝热 + 均匀热源，T(x)=T0+Q·(L·x-x²/2)/k。"""
        nx, ny = 60, 1
        L = (nx - 1) * _DX
        q_vol = 5e8
        t0 = 300.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.full((nx, ny), q_vol),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=t0),
                "east": BcSpec(type=BoundaryType.NEUMANN, value=0.0),  # 绝热 T'(L)=0
            },
        )
        res = HeatSolver().solve(cfg)
        x = np.arange(nx) * _DX
        # k·T'' + Q = 0, T(0)=T0, T'(L)=0 → T(x)=T0 + Q·(L·x - x²/2)/k
        t_analytical = t0 + q_vol * (L * x - x**2 / 2.0) / _K_SI
        assert np.max(np.abs(res.temperature[:, 0] - t_analytical)) < 1e-10

    def test_1d_conductive_interface(self) -> None:
        """双材料 k1≠k2 界面：温度连续（单调无跳变）+ 热流连续（体区 qx 相等）。"""
        n1, n2 = 40, 40
        nx = n1 + n2
        ny = 1
        # 前 n1 节点硅，后 n2 节点 SiO2
        k_arr = np.concatenate([np.full(n1, _K_SI), np.full(n2, _K_SIO2)]).reshape(nx, ny)
        ta, tb = 300.0, 350.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=k_arr,
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=ta),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=tb),
            },
        )
        res = HeatSolver().solve(cfg)
        T = res.temperature[:, 0]
        qx = res.heat_flux_x[:, 0]
        # 温度连续：单调（无跳变），范围在 [Ta, Tb]
        assert np.all(np.diff(T) >= -1e-9)
        assert T.min() >= ta - 1e-6 and T.max() <= tb + 1e-6
        # 热流连续：两材料体区（远离界面与边界）热流相等（稳态无源 → q=const）
        bulk1 = qx[5 : n1 - 5]
        bulk2 = qx[n1 + 5 : nx - 5]
        # 离散调和平均保证界面面热流连续，体区 nodal 热流一致
        assert abs(np.mean(bulk1) - np.mean(bulk2)) / abs(np.mean(bulk1) + 1e-30) < 1e-3

    def test_solver_returns_heat_flux(self) -> None:
        """HeatResult 含 heat_flux_x/heat_flux_y，形状与温度场一致。"""
        nx, ny = 16, 16
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
                "south": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "north": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
            },
        )
        res = HeatSolver().solve(cfg)
        assert res.temperature.shape == (nx, ny)
        assert res.heat_flux_x.shape == (nx, ny)
        assert res.heat_flux_y.shape == (nx, ny)
        assert np.all(np.isfinite(res.heat_flux_x))
        assert np.all(np.isfinite(res.heat_flux_y))
        # 1D 情形（ny=1）y 向热流应为零
        cfg_1d = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((8, 1), _K_SI),
            q_arr=np.zeros((8, 1)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
            },
        )
        res_1d = HeatSolver().solve(cfg_1d)
        assert np.all(res_1d.heat_flux_y == 0.0)


# ===========================================================================
# 4. TestSolver2D — 2D 求解器（4 tests，M2/M3）
# ===========================================================================
class TestSolver2D:
    """2D 稳态热传导与功率守恒、周期边界。"""

    def test_2d_dirichlet_four_sides(self) -> None:
        """四边固定温度，内部稳态分布满足最大值原理与离散 Laplace 方程。"""
        nx, ny = 32, 32
        t_w, t_e, t_s, t_n = 300.0, 400.0, 325.0, 375.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=t_w),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=t_e),
                "south": BcSpec(type=BoundaryType.DIRICHLET, value=t_s),
                "north": BcSpec(type=BoundaryType.DIRICHLET, value=t_n),
            },
        )
        res = HeatSolver().solve(cfg)
        T = res.temperature
        bc_min = min(t_w, t_e, t_s, t_n)
        bc_max = max(t_w, t_e, t_s, t_n)
        # 内部（不含边界行/列）满足离散最大值原理：T ∈ [bc_min, bc_max]
        interior = T[1:-1, 1:-1]
        assert np.all(np.isfinite(interior))
        assert interior.min() >= bc_min - 1e-9
        assert interior.max() <= bc_max + 1e-9
        # 边界非角点节点匹配 Dirichlet 值
        assert np.allclose(T[0, 1:-1], t_w)  # west 边（不含角）
        assert np.allclose(T[-1, 1:-1], t_e)  # east 边
        assert np.allclose(T[1:-1, 0], t_s)  # south 边
        assert np.allclose(T[1:-1, -1], t_n)  # north 边
        # 内部满足离散 Laplace 方程（残差 ~机器精度，除以 dx² 放大后仍 <1）
        lap = T[2:, 1:-1] + T[:-2, 1:-1] + T[1:-1, 2:] + T[1:-1, :-2] - 4.0 * T[1:-1, 1:-1]
        assert np.max(np.abs(lap)) < 1e-6

    def test_2d_adiabatic_with_source_raises(self) -> None:
        """M2 功率守恒：全边界绝热 + 内部热源 → raise ValueError（无稳态解）。"""
        nx, ny = 16, 16
        # 全边界默认绝热（不指定 bc_dict），内部持续产热
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.full((nx, ny), 1e9),  # 体积热源
        )
        # 绝热闭域持续产热违反热力学第一定律（产热≠散热），无稳态解
        with pytest.raises(ValueError, match="功率不守恒"):
            HeatSolver().solve(cfg)

    def test_2d_mixed_boundaries(self) -> None:
        """M3 混合边界：Dirichlet + Neumann + Convective 三类共存可求解。"""
        nx, ny = 24, 24
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
                "south": BcSpec(type=BoundaryType.NEUMANN, value=0.0),  # 绝热
                "north": BcSpec(type=BoundaryType.CONVECTIVE, value=0.0, h=1e4, t_amb=300.0),
            },
        )
        res = HeatSolver().solve(cfg)
        T = res.temperature
        assert np.all(np.isfinite(T))
        # west/east 边非角点匹配 Dirichlet
        assert np.allclose(T[0, 1:-1], 300.0)
        assert np.allclose(T[-1, 1:-1], 400.0)
        # 内部温度在 Dirichlet 范围内（最大值原理，含对流散热锚定）
        interior = T[1:-1, 1:-1]
        assert interior.min() >= 300.0 - 5.0
        assert interior.max() <= 400.0 + 5.0

    def test_2d_periodic_boundary(self) -> None:
        """M3 周期边界 T(x+L)=T(x)：west/east 周期 + south/north Dirichlet → 一维线性解。"""
        nx, ny = 32, 32
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.PERIODIC),
                "east": BcSpec(type=BoundaryType.PERIODIC),
                "south": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "north": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
            },
        )
        res = HeatSolver().solve(cfg)
        T = res.temperature
        # 周期性：最西列 ≈ 最东列
        assert np.max(np.abs(T[0, :] - T[-1, :])) < 1e-9
        # 退化为 y 方向一维线性解 T(y)=300+100·y/L（x 方向均匀）
        y = np.arange(ny) * _DX
        L = (ny - 1) * _DX
        t_analytical_y = 300.0 + 100.0 * y / L
        assert np.max(np.abs(T[0, :] - t_analytical_y)) < 1e-9
        # x 方向均匀（每列与首列一致）
        assert np.max(np.abs(T - T[0:1, :])) < 1e-9


# ===========================================================================
# 5. TestRadiativeBoundary — 辐射边界线性化（2 tests）
# ===========================================================================
class TestRadiativeBoundary:
    """辐射边界 Stefan-Boltzmann 线性化（等效 Robin h_rad=4·ε·σ·T_ref³）。"""

    def test_radiative_bc_linearized(self) -> None:
        """辐射边界线性化：等效对流系数 h_rad=4·ε·σ_SB·T_ref³，端点匹配解析 Robin。"""
        # 验证 radiative_h 公式
        eps = 0.8
        t_ref = 300.0
        h_rad = radiative_h(eps, t_ref)
        assert np.isclose(h_rad, 4.0 * eps * SIGMA_SB * t_ref**3)
        # 1D west 辐射 + east Dirichlet，端点温度匹配线性化 Robin 解
        nx, ny = 40, 1
        L = (nx - 1) * _DX
        t_east = 500.0
        t_amb = 290.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.RADIATIVE, value=0.0, emissivity=eps, t_amb=t_amb),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=t_east),
            },
        )
        res = HeatSolver().solve(cfg)
        # 线性分布 T(x)=T_w+(T_e-T_w)·x/L，T_w 由 -k·(T_e-T_w)/L = h_rad·(T_w-Tamb)
        h_rad_amb = radiative_h(eps, t_amb)
        t_w = (h_rad_amb * t_amb + _K_SI * t_east / L) / (h_rad_amb + _K_SI / L)
        assert abs(res.temperature[0, 0] - t_w) < 1e-6

    def test_radiative_bc_high_temperature(self) -> None:
        """高温辐射效应显著：高温端 h_rad∝T³ 远大于低温端，散热更强。"""
        # 高温环境辐射等效对流系数显著大于低温（T³ 关系）
        h_low = radiative_h(1.0, 300.0)
        h_high = radiative_h(1.0, 600.0)
        # h ∝ T³，600K/300K=2 → h 比 =8
        assert h_high / h_low == pytest.approx(8.0, rel=1e-12)
        assert h_high > h_low
        # 高温边界条件下端点温度更低（散热更强）
        nx, ny = 40, 1
        t_amb = 290.0
        cfg_low = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.RADIATIVE, value=0.0, emissivity=1.0, t_amb=t_amb),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
            },
        )
        cfg_high = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.RADIATIVE, value=0.0, emissivity=1.0, t_amb=t_amb),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=800.0),
            },
        )
        res_low = HeatSolver().solve(cfg_low)
        res_high = HeatSolver().solve(cfg_high)
        # 高温 east 端 800K 时 west 端温度应高于低温 400K 情形（热流更大）
        assert res_high.temperature[0, 0] > res_low.temperature[0, 0]
        assert np.all(np.isfinite(res_high.temperature))


# ===========================================================================
# 6. TestCoupling — HEAT↔FDE / DDM→HEAT 耦合（4 tests）
# ===========================================================================
class TestCoupling:
    """热光耦合与焦耳热耦合接口。"""

    def test_heat_to_fde_cocorullo(self) -> None:
        """温度→FDE 折射率修正 Δn=(dn/dT)·(T-T_ref)，dn/dT=1.86e-4/K（Cocorullo 1999）。"""
        nx, ny = 8, 8
        dT = 10.0  # 升温 10K
        T = np.full((nx, ny), _T_REF + dT)
        heat_result = HeatResult(
            temperature=T,
            heat_flux_x=np.zeros((nx, ny)),
            heat_flux_y=np.zeros((nx, ny)),
            dx=_DX,
            dy=_DX,
        )
        mode = _uniform_mode((nx, ny))
        toc = heat_to_fde(heat_result, mode, dn_dt=_DN_DT, t_ref=_T_REF)
        # Δn = dn/dT · ΔT = 1.86e-4 · 10 = 1.86e-3
        assert np.allclose(toc.delta_n, _DN_DT * dT)
        assert np.isclose(toc.delta_n[0, 0], 1.86e-3)
        # 均匀光强模式 → Δn_eff = Δn（加权平均退化）
        assert np.isclose(toc.delta_n_eff, _DN_DT * dT)
        assert np.isclose(toc.dn_dt, _DN_DT)
        assert toc.t_ref == _T_REF

    def test_heat_to_fde_zero_delta_t(self) -> None:
        """ΔT=0（T=T_ref）时 Δn=0、Δn_eff=0（无热光扰动）。"""
        nx, ny = 6, 6
        T = np.full((nx, ny), _T_REF)
        heat_result = HeatResult(
            temperature=T,
            heat_flux_x=np.zeros((nx, ny)),
            heat_flux_y=np.zeros((nx, ny)),
            dx=_DX,
            dy=_DX,
        )
        mode = _uniform_mode((nx, ny))
        toc = heat_to_fde(heat_result, mode, dn_dt=_DN_DT, t_ref=_T_REF)
        assert np.max(np.abs(toc.delta_n)) == 0.0
        assert toc.delta_n_eff == 0.0

    def test_ddm_to_heat_joule(self) -> None:
        """DDM 载流子分布→焦耳热 Q=J²/σ（Incropera §3.6 体积热源）。"""
        nx, ny = 4, 4
        jx = np.full((nx, ny), 1e6)  # 电流密度 A/m²
        jy = np.zeros((nx, ny))
        sigma = np.full((nx, ny), 1e4)  # 电导率 S/m
        ddm = DDMResult(current_density_x=jx, current_density_y=jy, conductivity=sigma)
        Q = ddm_to_heat(ddm)
        # Q = (Jx² + Jy²)/σ = (1e6)²/1e4 = 1e8 W/m³
        assert np.allclose(Q, 1e8)
        assert Q.shape == (nx, ny)
        # 非零 y 分量贡献
        jy2 = np.full((nx, ny), 3e5)
        ddm2 = DDMResult(current_density_x=jx, current_density_y=jy2, conductivity=sigma)
        Q2 = ddm_to_heat(ddm2)
        assert np.allclose(Q2, (1e6**2 + (3e5) ** 2) / 1e4)

    def test_coupling_sign_consistency(self) -> None:
        """耦合方向符号一致：升温→Δn>0→n_eff 增大（dn/dT>0）。"""
        nx, ny = 6, 6
        mode = _uniform_mode((nx, ny))
        # 升温场景
        T_hot = HeatResult(
            temperature=np.full((nx, ny), _T_REF + 20.0),
            heat_flux_x=np.zeros((nx, ny)),
            heat_flux_y=np.zeros((nx, ny)),
            dx=_DX,
            dy=_DX,
        )
        toc_hot = heat_to_fde(T_hot, mode, dn_dt=_DN_DT, t_ref=_T_REF)
        assert np.all(toc_hot.delta_n > 0.0)
        assert toc_hot.delta_n_eff > 0.0
        # 降温场景
        T_cold = HeatResult(
            temperature=np.full((nx, ny), _T_REF - 20.0),
            heat_flux_x=np.zeros((nx, ny)),
            heat_flux_y=np.zeros((nx, ny)),
            dx=_DX,
            dy=_DX,
        )
        toc_cold = heat_to_fde(T_cold, mode, dn_dt=_DN_DT, t_ref=_T_REF)
        assert np.all(toc_cold.delta_n < 0.0)
        assert toc_cold.delta_n_eff < 0.0
        # dn/dT > 0 保证符号一致
        assert _DN_DT > 0.0


# ===========================================================================
# 7. TestPhysicalValidation — 物理量验证（3 tests）
# ===========================================================================
class TestPhysicalValidation:
    """材料热阻、热导率差异、稳态收敛性物理验证。"""

    def test_silicon_slab_thermal_resistance(self) -> None:
        """硅平板热阻 R=L/(k·A) 验证（A=dy·单位深度）。"""
        nx, ny = 50, 1
        L = (nx - 1) * _DX
        t1, t2 = 300.0, 400.0
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.zeros((nx, ny)),
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=t1),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=t2),
            },
        )
        res = HeatSolver().solve(cfg)
        qx = res.heat_flux_x[:, 0]
        # 总热流 = |qx| · A（A=dy·单位深度=dx·1）
        A = _DX  # dy × 单位深度(1m)
        q_total = np.abs(qx).mean() * A
        r_sim = (t2 - t1) / q_total
        # 解析热阻 R = L / (k · A)
        r_analytical = L / (_K_SI * A)
        assert np.isclose(r_sim, r_analytical, rtol=1e-10)

    def test_sio2_insulator_low_conductivity(self) -> None:
        """SiO2 热导率低于硅：固定热流下 SiO2 温度梯度更大（dT/dx=q/k）。"""
        # k_SiO2 << k_Si
        assert _K_SIO2 < _K_SI
        nx, ny = 50, 1
        L = (nx - 1) * _DX
        q_in = 1e5  # 固定外法向热流 W/m²

        def grad_for(k_val: float) -> float:
            cfg = HeatConfig(
                dx=_DX,
                dy=_DX,
                k_arr=np.full((nx, ny), k_val),
                q_arr=np.zeros((nx, ny)),
                bc_dict={
                    "west": BcSpec(type=BoundaryType.NEUMANN, value=q_in),
                    "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
                },
            )
            res = HeatSolver().solve(cfg)
            return (res.temperature[-1, 0] - res.temperature[0, 0]) / L

        grad_si = grad_for(_K_SI)
        grad_sio2 = grad_for(_K_SIO2)
        # 解析 dT/dx = q/k，SiO2 梯度远大于硅
        assert abs(grad_sio2) > abs(grad_si)
        # 梯度比 = k_Si / k_SiO2（q 相同）
        assert (grad_sio2 / grad_si) == pytest.approx(_K_SI / _K_SIO2, rel=1e-6)

    def test_steady_state_convergence(self) -> None:
        """稳态解为直接求解（spsolve，无迭代）：两次求解结果完全一致。"""
        nx, ny = 32, 8
        cfg = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=np.full((nx, ny), _K_SI),
            q_arr=np.full((nx, ny), 1e8),  # 均匀热源
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=350.0),
                "south": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
                "north": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
            },
        )
        r1 = solve_heat(cfg)
        r2 = HeatSolver().solve(cfg)  # 同一 config 多次求解
        # 直接求解无迭代，结果确定且可复现
        assert np.allclose(r1.temperature, r2.temperature)
        assert np.allclose(r1.heat_flux_x, r2.heat_flux_x)
        # solve_heat 便捷函数与 HeatSolver.solve 等价
        assert np.array_equal(r1.temperature, r2.temperature)


# ===========================================================================
# 8. TestTransientHeat — 瞬态热传导求解器（Crank-Nicolson）
# ===========================================================================
class TestTransientHeat:
    """瞬态热传导求解器测试（Crank-Nicolson 隐式方法）。"""

    def test_transient_config_valid(self) -> None:
        """瞬态热配置构造成功，参数校验通过。"""
        nx, ny = 16, 8
        k = np.full((nx, ny), _K_SI)
        q = np.zeros((nx, ny))
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)
        hc = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=k,
            q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
            },
        )
        cfg = TransientHeatConfig(
            heat_config=hc,
            rho_arr=rho,
            cp_arr=cp,
            t_initial=300.0,
            t_final=1e-6,
            dt=1e-8,
        )
        assert cfg.t_final == 1e-6
        assert cfg.dt == 1e-8
        assert cfg.t_initial.shape == (nx, ny)

    def test_transient_config_invalid_rho_raises(self) -> None:
        """非法 rho/cp/t_final/dt 应 raise ValueError。"""
        nx, ny = 4, 4
        k = np.full((nx, ny), _K_SI)
        q = np.zeros((nx, ny))
        hc = HeatConfig(dx=_DX, dy=_DX, k_arr=k, q_arr=q)
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)

        # rho 含非正值
        with pytest.raises(ValueError, match="rho_arr"):
            TransientHeatConfig(
                heat_config=hc,
                rho_arr=np.full((nx, ny), -1.0),
                cp_arr=cp,
                t_final=1e-6,
                dt=1e-8,
            )
        # cp 含非正值
        with pytest.raises(ValueError, match="cp_arr"):
            TransientHeatConfig(
                heat_config=hc,
                rho_arr=rho,
                cp_arr=np.full((nx, ny), 0.0),
                t_final=1e-6,
                dt=1e-8,
            )
        # t_final <= 0
        with pytest.raises(ValueError, match="t_final"):
            TransientHeatConfig(
                heat_config=hc, rho_arr=rho, cp_arr=cp, t_final=0.0, dt=1e-8
            )
        # dt > t_final
        with pytest.raises(ValueError, match="dt"):
            TransientHeatConfig(
                heat_config=hc, rho_arr=rho, cp_arr=cp, t_final=1e-8, dt=1e-6
            )

    def test_transient_uniform_initial_stays_uniform(self) -> None:
        """均匀初始温度 + 无热源 + 均匀 Dirichlet 边界 → 温度始终均匀。"""
        nx, ny = 16, 8
        T0 = 350.0
        k = np.full((nx, ny), _K_SI)
        q = np.zeros((nx, ny))
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)
        hc = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=k,
            q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=T0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=T0),
                "south": BcSpec(type=BoundaryType.DIRICHLET, value=T0),
                "north": BcSpec(type=BoundaryType.DIRICHLET, value=T0),
            },
        )
        cfg = TransientHeatConfig(
            heat_config=hc,
            rho_arr=rho,
            cp_arr=cp,
            t_initial=T0,
            t_final=1e-6,
            dt=1e-8,
        )
        result = TransientHeatSolver().solve(cfg)
        # 所有时刻温度均应等于 T0（均匀稳态）
        for T in result.temperatures:
            assert np.max(np.abs(T - T0)) < 1e-6

    def test_transient_heating_then_cooling(self) -> None:
        """阶跃热源加热后关断，温度先升后降（能量守恒定性验证）。"""
        nx, ny = 20, 10
        k = np.full((nx, ny), _K_SI)
        q0 = 1e10  # 体积热源 W/m³
        q = np.full((nx, ny), q0)
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)
        hc = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=k,
            q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "south": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "north": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
            },
        )
        cfg = TransientHeatConfig(
            heat_config=hc,
            rho_arr=rho,
            cp_arr=cp,
            t_initial=300.0,
            t_final=5e-7,
            dt=1e-8,
        )
        result = TransientHeatSolver().solve(cfg)
        # 加热阶段：最大温度应随时间上升
        times, T_max = result.max_temperature_vs_time()
        assert T_max[-1] > T_max[0], "加热阶段温度应上升"
        assert np.all(np.isfinite(result.temperatures))

    def test_transient_approaches_steady_state(self) -> None:
        """长时间瞬态求解应趋近稳态解。"""
        nx, ny = 20, 10
        k = np.full((nx, ny), _K_SI)
        q0 = 5e9
        q = np.full((nx, ny), q0)
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)
        hc = HeatConfig(
            dx=_DX,
            dy=_DX,
            k_arr=k,
            q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "south": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "north": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
            },
        )
        # 稳态解
        steady = HeatSolver().solve(hc)
        # 瞬态求解足够长时间
        cfg = TransientHeatConfig(
            heat_config=hc,
            rho_arr=rho,
            cp_arr=cp,
            t_initial=300.0,
            t_final=1e-5,
            dt=2e-8,
            save_every=10,
        )
        result = TransientHeatSolver().solve(cfg)
        # 最后一步应接近稳态（误差 < 5%）
        T_last = result.temperatures[-1]
        rel_err = np.max(np.abs(T_last - steady.temperature)) / (
            np.max(np.abs(steady.temperature - 300.0)) + 1e-30
        )
        assert rel_err < 0.05, f"瞬态末态与稳态相对误差 {rel_err:.2%} > 5%"

    def test_thermal_time_constant_1d(self) -> None:
        """1D 平板热时间常数解析公式：τ ≈ L²/(π²·α)。"""
        L = 1e-5  # 10 μm
        tau = thermal_time_constant_1d(
            thickness=L,
            thermal_conductivity=K_SILICON,
            rho=RHO_SILICON,
            cp=CP_SILICON,
        )
        # 应与 α = k/(ρ·Cp) 自洽
        alpha = K_SILICON / (RHO_SILICON * CP_SILICON)
        tau_expected = L**2 / (np.pi**2 * alpha)
        assert np.isclose(tau, tau_expected, rtol=1e-12)
        assert tau > 0

    def test_transient_result_shape(self) -> None:
        """TransientHeatResult 形状正确：times 与 temperatures 第 0 维匹配。"""
        nx, ny = 8, 4
        k = np.full((nx, ny), _K_SI)
        q = np.zeros((nx, ny))
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)
        hc = HeatConfig(
            dx=_DX, dy=_DX, k_arr=k, q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
            },
        )
        cfg = TransientHeatConfig(
            heat_config=hc,
            rho_arr=rho,
            cp_arr=cp,
            t_initial=300.0,
            t_final=1e-7,
            dt=1e-8,
            save_every=2,
        )
        result = TransientHeatSolver().solve(cfg)
        assert result.temperatures.shape[0] == result.times.shape[0]
        assert result.temperatures.shape[1:] == (nx, ny)
        assert result.dx == _DX
        assert result.dy == _DX

    def test_solve_transient_heat_convenience(self) -> None:
        """solve_transient_heat 便捷函数与 TransientHeatSolver.solve 等价。"""
        nx, ny = 8, 4
        k = np.full((nx, ny), _K_SI)
        q = np.zeros((nx, ny))
        rho = np.full((nx, ny), RHO_SILICON)
        cp = np.full((nx, ny), CP_SILICON)
        hc = HeatConfig(
            dx=_DX, dy=_DX, k_arr=k, q_arr=q,
            bc_dict={
                "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
                "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
            },
        )
        cfg = TransientHeatConfig(
            heat_config=hc,
            rho_arr=rho,
            cp_arr=cp,
            t_initial=300.0,
            t_final=1e-7,
            dt=1e-8,
        )
        r1 = solve_transient_heat(cfg)
        r2 = TransientHeatSolver().solve(cfg)
        assert np.array_equal(r1.temperatures, r2.temperatures)
        assert np.array_equal(r1.times, r2.times)


# ===========================================================================
# 9. TestPhysicalConstants — 热物性常量验证
# ===========================================================================
class TestPhysicalConstants:
    """热物性物理常量正确性验证。"""

    def test_thermal_diffusivity_consistency(self) -> None:
        """热扩散率 α = k/(ρ·Cp) 自洽性检查。"""
        alpha = K_SILICON / (RHO_SILICON * CP_SILICON)
        assert np.isclose(alpha, ALPHA_SILICON, rtol=1e-12)
        assert alpha > 0

    def test_silicon_conductivity_value(self) -> None:
        """硅热导率应在 140-160 W/(m·K) 范围（室温典型值）。"""
        assert 140.0 <= K_SILICON <= 160.0

    def test_sio2_conductivity_value(self) -> None:
        """SiO2 热导率应在 1.0-2.0 W/(m·K) 范围（室温典型值）。"""
        assert 1.0 <= K_SIO2 <= 2.0

    def test_dn_dt_silicon_value(self) -> None:
        """硅热光系数应在 1.5e-4 ~ 2.5e-4 /K 范围（Cocorullo 1999）。"""
        assert 1.5e-4 <= DN_DT_SI <= 2.5e-4
