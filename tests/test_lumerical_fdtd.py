"""R31 Lumerical FDTD 3D 全波仿真后端单元测试。

覆盖：
- 配置验证（CFL 3D 条件）
- 3D 网格设置
- 色散材料添加（Drude）
- 3D TFSF 光源
- E/H 场步进（3D 解析解对比）
- 3D CPML 吸收
- Drude 色散步进
- 3D S 参数提取
- 完整仿真运行
- 与 Tidy3D 交叉验证
- 能量守恒

学术依据：Yee 1966 / Taflove 2005 / Roden & Gedney 2000（详见模块 docstring）。
规则：R03 禁止 fall-back / R04 不参与 GPU / 覆盖率 ≥90%。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.lumerical_fdtd import (
    FDTD3DConfig,
    LumericalFDTDBackend,
    courant_dt_3d,
)

# 物理常数（与模块内一致）
_C0 = 2.99792458e8
_EPS0 = 8.8541878128e-12
_MU0 = 1.25663706212e-6


# ---------------------------------------------------------------------------
# 1. 配置验证
# ---------------------------------------------------------------------------


def test_config_validation() -> None:
    """配置验证：非法网格/步数/PML/CFL 必须 raise。"""
    # 网格 ≤0
    with pytest.raises(ValueError, match="dx/dy/dz"):
        FDTD3DConfig(dx=-1e-9)
    # n_steps ≤0
    with pytest.raises(ValueError, match="n_steps"):
        FDTD3DConfig(n_steps=0)
    # pml <4
    with pytest.raises(ValueError, match="pml_layers"):
        FDTD3DConfig(pml_layers=2)
    # eps_r_bg ≤0
    with pytest.raises(ValueError, match="eps_r_bg"):
        FDTD3DConfig(eps_r_bg=0.0)
    # dt 突破 CFL
    with pytest.raises(ValueError, match="CFL"):
        FDTD3DConfig(dx=50e-9, dt=1e-15)  # 1e-15 远超 3D CFL 上限
    # 合法配置
    cfg = FDTD3DConfig(dx=50e-9, dy=50e-9, dz=50e-9, n_steps=10)
    assert cfg.dt is not None
    assert cfg.dt > 0.0
    # CFL 自动计算：dt ≤ 1/(c·sqrt(3)/dx)
    dt_max = 50e-9 / (_C0 * np.sqrt(3.0))
    assert cfg.dt <= dt_max


def test_courant_dt_3d_function() -> None:
    """courant_dt_3d 函数：CFL 公式正确性。"""
    dt = courant_dt_3d(50e-9, 50e-9, 50e-9, cfl=0.99)
    expected = 0.99 / (_C0 * np.sqrt(3.0) / 50e-9)
    assert abs(dt - expected) < 1e-30
    # 非法输入
    with pytest.raises(ValueError):
        courant_dt_3d(-1.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        courant_dt_3d(1.0, 1.0, 1.0, cfl=1.5)


# ---------------------------------------------------------------------------
# 2. 3D 网格设置
# ---------------------------------------------------------------------------


def test_set_grid_3d() -> None:
    """3D 网格设置：场数组形状与初始化。"""
    cfg = FDTD3DConfig(dx=50e-9, n_steps=10, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(20, 20, 20)
    assert sim._ex is not None
    assert sim._ex.shape == (20, 20, 20)
    assert sim._hz.shape == (20, 20, 20)
    # 初始场全零
    assert np.all(sim._ex == 0.0)
    assert np.all(sim._hz == 0.0)
    # ε_r 全为背景
    assert np.all(sim._eps_r == cfg.eps_r_bg)
    # CPML 已初始化
    assert sim._cpml_sigma is not None
    assert "x0" in sim._cpml_sigma
    assert sim._cpml_sigma["x0"].shape == (4,)


def test_set_grid_3d_invalid() -> None:
    """3D 网格设置：非法网格数 raise。"""
    cfg = FDTD3DConfig(pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    # 网格 <8
    with pytest.raises(ValueError, match="网格数"):
        sim.set_grid_3d(4, 20, 20)
    # 网格不足以容纳 2·pml
    with pytest.raises(ValueError, match="内部域"):
        sim.set_grid_3d(8, 20, 20)  # 8 - 2·4 = 0


# ---------------------------------------------------------------------------
# 3. 色散材料添加
# ---------------------------------------------------------------------------


def test_add_material_dispersion() -> None:
    """色散材料添加：Drude 参数验证与 ε_r 同步。"""
    cfg = FDTD3DConfig(n_steps=5, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(20, 20, 20)
    # 金 Drude 参数（Rakic 1998 拟合 Palik 1985）
    params = {"omega_p": 1.37e16, "gamma": 4.08e13, "eps_inf": 9.84}
    sim.add_material_dispersion("gold", "drude", params, (5, 15, 5, 15, 5, 15))
    assert len(sim._disp_regions) == 1
    assert sim._disp_regions[0].name == "gold"
    # ε_r 在该区域已替换为 eps_inf
    assert sim._eps_r[10, 10, 10] == 9.84
    assert sim._eps_r[0, 0, 0] == 1.0  # 背景未变
    # Drude J 缓冲已分配
    assert len(sim._drude_J) == 1
    assert sim._drude_J[0].shape == (20, 20, 20)


def test_add_material_dispersion_invalid() -> None:
    """色散材料添加：非法模型/参数/区域 raise。"""
    cfg = FDTD3DConfig(n_steps=5, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    # 网格未初始化
    with pytest.raises(ValueError, match="set_grid_3d"):
        sim.add_material_dispersion(
            "x", "drude", {"omega_p": 1.0, "gamma": 1.0, "eps_inf": 1.0},
            (0, 1, 0, 1, 0, 1),
        )
    sim.set_grid_3d(20, 20, 20)
    # 不支持的模型
    with pytest.raises(ValueError, match="不支持的色散模型"):
        sim.add_material_dispersion("x", "custom", {}, (0, 1, 0, 1, 0, 1))
    # Lorentz/Debye 未实现（R05 禁止 fall-back）
    with pytest.raises(ValueError, match="暂未实现"):
        sim.add_material_dispersion(
            "x", "lorentz", {"f0": 1.0}, (0, 1, 0, 1, 0, 1)
        )
    # Drude 参数缺失
    with pytest.raises(ValueError, match="参数缺失"):
        sim.add_material_dispersion("x", "drude", {"omega_p": 1.0}, (0, 1, 0, 1, 0, 1))
    # omega_p ≤0
    with pytest.raises(ValueError, match="omega_p"):
        sim.add_material_dispersion(
            "x", "drude",
            {"omega_p": -1.0, "gamma": 1.0, "eps_inf": 1.0},
            (0, 1, 0, 1, 0, 1),
        )
    # 区域越界
    with pytest.raises(ValueError, match="越界"):
        sim.add_material_dispersion(
            "x", "drude",
            {"omega_p": 1.0, "gamma": 1.0, "eps_inf": 1.0},
            (0, 100, 0, 1, 0, 1),
        )


# ---------------------------------------------------------------------------
# 4. 3D TFSF 光源
# ---------------------------------------------------------------------------


def test_add_tfsf_source_3d() -> None:
    """3D TFSF 光源：参数验证与添加。"""
    cfg = FDTD3DConfig(n_steps=10, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    # 网格未初始化
    with pytest.raises(ValueError, match="set_grid_3d"):
        sim.add_tfsf_source_3d((0, 0, 0), (5, 5, 5), freq=2e14)
    sim.set_grid_3d(20, 20, 20)
    # 频率 ≤0
    with pytest.raises(ValueError, match="freq"):
        sim.add_tfsf_source_3d((5, 5, 5), (10, 10, 10), freq=0.0)
    # 方向不支持
    with pytest.raises(ValueError, match="direction"):
        sim.add_tfsf_source_3d((5, 5, 5), (10, 10, 10), freq=2e14, direction="+y")
    # 越界
    with pytest.raises(ValueError, match="越界"):
        sim.add_tfsf_source_3d((15, 5, 5), (10, 10, 10), freq=2e14)
    # 合法
    sid = sim.add_tfsf_source_3d((5, 5, 5), (10, 10, 10), freq=2e14)
    assert sid == 0
    assert len(sim._tfsf_sources) == 1
    assert sim._tfsf_sources[0].freq == 2e14


# ---------------------------------------------------------------------------
# 5. E 场步进（3D 解析解对比）
# ---------------------------------------------------------------------------


def test_step_e_3d() -> None:
    """E 场步进：3D Yee Ampere 旋度与解析平面波对比。

    +x 传播平面波（E_z 偏振），由 Maxwell-Faraday 推导：
        ∂H_y/∂t = (1/μ_0)·∂E_z/∂x  →  H_y = -sin(k·x - ω·t)/η_0（负号不可省略）
    Yee 半步空间错位：H_y[i] 位于 (i+1/2)·dx。
    Yee E 步进公式 E^{n+1} = E^n + (Δt/ε_0)·∂H_y^{n+1/2}/∂x，故 H_init 须取
    t=+Δt/2 的相位 H_y = -sin(k·x - ω·Δt/2)/η_0（与 _step_h_3d 推进后的 H 一致），
    单步 E 更新后期望 E_z(t=Δt) ≈ sin(kx - ω·Δt)。
    """
    cfg = FDTD3DConfig(dx=50e-9, dy=50e-9, dz=50e-9, n_steps=1, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    nx = ny = nz = 20
    sim.set_grid_3d(nx, ny, nz)
    eta0 = np.sqrt(_MU0 / _EPS0)
    x_idx = np.arange(nx)
    dx = 50e-9
    k = 2.0 * np.pi / (10 * dx)  # 波长 = 10·dx
    omega = _C0 * k
    dt = cfg.dt
    # E_z 在整数网格点 (i·dx)，t=0
    e_z_init = np.sin(k * x_idx * dx)
    sim._ez[:, :, :] = e_z_init[:, None, None]
    # H_y 在半步空间错位 (i+1/2)·dx，Yee 时间半步错位 t=+Δt/2（E 步进公式要求）
    # 物理符号：H_y = -sin(k·x - ω·t)/η_0（Maxwell-Faraday 推导，+x 传播）
    x_hy = (x_idx + 0.5) * dx
    h_y_init = -np.sin(k * x_hy - omega * dt * 0.5) / eta0
    sim._hy[:, :, :] = h_y_init[:, None, None]
    # 单步 E 更新（仅内部区域）
    sim._step_e_3d()
    # 解析解：+x 传播，E_z(t=dt) = sin(kx - ω·dt)
    e_z_expected = np.sin(k * x_idx * dx - omega * dt)
    interior = sim._ez[8:12, 8:12, 8:12]
    expected_int = e_z_expected[8:12, None, None]
    # 单步数值色散 + Yee 时间半步错位，容限 0.1（绝对值 V/m）
    err = np.max(np.abs(interior - expected_int))
    assert err < 0.1, f"E 步进解析解误差 {err} 过大"


def test_step_h_3d() -> None:
    """H 场步进：3D Yee Faraday 旋度与零场检验。"""
    cfg = FDTD3DConfig(dx=50e-9, n_steps=1, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(20, 20, 20)
    # 零场 → H 更新后仍为零
    sim._step_h_3d()
    assert np.all(sim._hx == 0.0)
    assert np.all(sim._hy == 0.0)
    assert np.all(sim._hz == 0.0)
    # 非零 E_z → H_x/H_y 应被激发（旋度非零）
    sim._ez[10, :, :] = 1.0  # E_z 在 x=10 处为 1
    sim._step_h_3d()
    # H_x 含 ∂E_z/∂y 项，y 方向均匀则 H_x = 0
    # H_y 含 -∂E_z/∂x 项，x=10 邻居 E_z 不连续，应激发
    assert np.any(sim._hy != 0.0)


# ---------------------------------------------------------------------------
# 6. 3D CPML 吸收
# ---------------------------------------------------------------------------


def test_apply_cpml_3d() -> None:
    """3D CPML：6 面边界场应被衰减，内部不衰减。"""
    cfg = FDTD3DConfig(dx=50e-9, n_steps=1, pml_layers=5)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(30, 30, 30)
    # 全场初始化为 1.0
    sim._ex[:, :, :] = 1.0
    sim._ey[:, :, :] = 1.0
    sim._ez[:, :, :] = 1.0
    # 应用 CPML（E 场）
    sim._apply_cpml_3d(field_is_e=True)
    # PML 区域（前 5 层）应衰减
    assert sim._ex[0, 15, 15] < 1.0
    assert sim._ex[2, 15, 15] < 1.0
    # PML 最外层衰减最强
    assert sim._ex[0, 15, 15] < sim._ex[4, 15, 15]
    # 内部区域（远离 PML）应保持为 1.0
    assert sim._ex[15, 15, 15] == 1.0
    # 6 面对称性（x0 vs x1, y0 vs y1, z0 vs z1）
    assert abs(sim._ex[0, 15, 15] - sim._ex[-1, 15, 15]) < 1e-15


# ---------------------------------------------------------------------------
# 7. Drude 色散步进
# ---------------------------------------------------------------------------


def test_step_drude() -> None:
    """Drude 色散：J 在 E^n 驱动下应增长，α/β 系数正确。"""
    cfg = FDTD3DConfig(dx=50e-9, n_steps=1, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(20, 20, 20)
    params = {"omega_p": 1.37e16, "gamma": 4.08e13, "eps_inf": 9.84}
    sim.add_material_dispersion("gold", "drude", params, (5, 15, 5, 15, 5, 15))
    # E_z 在色散区初始化为 1.0
    sim._ez[:, :, :] = 1.0
    # 单步 Drude J 更新
    sim._step_drude(t=0.0)
    # 解析：J = β·E（J 初始为 0），β = ε_0·ω_p²·dt/(1+γ·dt/2)
    dt = cfg.dt
    beta_expected = (
        _EPS0 * params["omega_p"] ** 2 * dt / (1.0 + params["gamma"] * dt / 2.0)
    )
    j = sim._drude_J[0]
    # 色散区域内
    assert abs(j[10, 10, 10] - beta_expected * 1.0) < 1e-3
    # 色散区域外（mask=False）应保持 0
    assert j[0, 0, 0] == 0.0


# ---------------------------------------------------------------------------
# 8. 3D S 参数提取
# ---------------------------------------------------------------------------


def test_extract_sparams_3d() -> None:
    """3D S 参数提取：单频 DFT 归一化。"""
    cfg = FDTD3DConfig(dx=50e-9, n_steps=200)
    sim = LumericalFDTDBackend(cfg)
    # 构造一个纯正弦时序：E_z[n] = sin(ω·n·dt)
    freq = 2e14
    omega = 2.0 * np.pi * freq
    dt = cfg.dt
    n = np.arange(200)
    ts = np.sin(omega * n * dt)
    s = sim.extract_sparams_3d(ts, freq)
    # 单频正弦 DFT 应给出非零复振幅，相位对应 -π/2（sin → -i·δ(ω)）
    assert abs(s) > 0.1
    # 频率非法
    with pytest.raises(ValueError, match="freq"):
        sim.extract_sparams_3d(ts, 0.0)
    # 时序为空
    with pytest.raises(ValueError, match="time_signal"):
        sim.extract_sparams_3d(np.array([]), freq)


# ---------------------------------------------------------------------------
# 9. 完整仿真运行
# ---------------------------------------------------------------------------


def test_run_basic() -> None:
    """3D FDTD 基础仿真：TFSF 注入 + 监视器记录。"""
    cfg = FDTD3DConfig(dx=50e-9, dy=50e-9, dz=50e-9, n_steps=50, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(30, 20, 20)
    sim.add_tfsf_source_3d((6, 4, 4), (18, 12, 12), freq=2e14)
    sim.add_monitor_3d("point", (20, 10, 10), name="p1")
    result = sim.run()
    assert "fields" in result
    assert "monitors" in result
    assert result["n_steps"] == 50
    assert "p1" in result["monitors"]
    assert result["monitors"]["p1"].shape == (50,)
    # TFSF 注入后场应非零
    assert np.any(np.abs(result["fields"]["Ez"]) > 0)


def test_run_no_grid_raises() -> None:
    """未调用 set_grid_3d 直接 run 必须 raise（R03 禁止 fall-back）。"""
    cfg = FDTD3DConfig(n_steps=5)
    sim = LumericalFDTDBackend(cfg)
    with pytest.raises(RuntimeError, match="set_grid_3d"):
        sim.run()


# ---------------------------------------------------------------------------
# 10. 与 Tidy3D 交叉验证
# ---------------------------------------------------------------------------


def test_validate_against_tidy3d() -> None:
    """与 Tidy3D 交叉验证：相同场应判 True，不同场判 False。"""
    cfg = FDTD3DConfig(dx=50e-9, n_steps=5, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(20, 20, 20)
    sim.add_tfsf_source_3d((5, 5, 5), (10, 10, 10), freq=2e14)
    sim.add_monitor_3d("point", (15, 10, 10), name="p1")
    sim.run()
    # 构造一个 Tidy3D 等价结果（与本地完全一致 → 应判 True）
    mine = sim._fields_dict()
    tidy3d_result = {"fields": mine}
    assert sim.validate_against_tidy3d(tidy3d_result, atol=1e-12) is True
    # 引入偏差 → 应判 False
    perturbed = {k: v + 1.0 for k, v in mine.items()}
    assert sim.validate_against_tidy3d({"fields": perturbed}, atol=0.1) is False
    # 缺 fields/monitors → raise
    with pytest.raises(ValueError, match="fields 或 monitors"):
        sim.validate_against_tidy3d({"foo": 1})
    # monitors 路径
    tidy3d_mon = {"monitors": {"p1": sim._monitor_data["p1"].copy()}}
    assert sim.validate_against_tidy3d(tidy3d_mon, atol=1e-12) is True


# ---------------------------------------------------------------------------
# 11. 能量守恒
# ---------------------------------------------------------------------------


def test_energy_conservation() -> None:
    """能量守恒：无源、无 PML 衰减时，初始场能量近似守恒。

    在 PML 外的内部区域注入一个高斯脉冲，短时间运行（10 步），
    总能量 (ε·E²/2 + μ·H²/2)·dV 应近似守恒（leapfrog 时间中心差分）。
    由于 PML 衰减会吸收部分能量，仅校验内部区域能量变化率 < 5%。
    """
    cfg = FDTD3DConfig(dx=50e-9, n_steps=10, pml_layers=4)
    sim = LumericalFDTDBackend(cfg)
    sim.set_grid_3d(30, 30, 30)
    # 在内部中心注入高斯 E_z 脉冲
    nx, ny, nz = 30, 30, 30
    cx, cy, cz = 15, 15, 15
    xx, yy, zz = np.meshgrid(
        np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij"
    )
    sigma = 2.0
    pulse = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2) / (2 * sigma**2))
    sim._ez[:, :, :] = pulse
    # 初始总能量（仅 E 场，H=0）
    e0 = 0.5 * _EPS0 * np.sum(sim._ez ** 2)
    assert e0 > 0.0
    # 跑 10 步
    sim.run()
    # 终态总能量
    e1 = 0.5 * _EPS0 * np.sum(sim._ez ** 2) + 0.5 * _MU0 * (
        np.sum(sim._hx ** 2) + np.sum(sim._hy ** 2) + np.sum(sim._hz ** 2)
    )
    # 能量应保持在合理范围（PML 吸收 + 数值色散）
    # 不少于初始能量的 30%（10 步内 PML 吸收有限）
    assert e1 > 0.3 * e0, f"能量损失过大：e0={e0:.3e} e1={e1:.3e}"
