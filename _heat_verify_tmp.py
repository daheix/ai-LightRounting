"""A07-HEAT 临时验收脚本（M1/M2/M3 + 耦合冒烟），运行后删除。"""
import sys
sys.path.insert(0, "/workspace/src")

import numpy as np
from polaris.sim.heat import (
    HeatConfig, HeatSolver, solve_heat, BoundaryType, BcSpec,
    heat_to_fde, ddm_to_heat, DDMResult,
)
from polaris.sim.fde.mode import Mode

print("=== M1 解析解对比：1D 平板固定温差 ===")
nx, ny = 50, 1
L = 1.0
dx = L / (nx - 1)
k = np.full((nx, ny), 148.0)
q = np.zeros((nx, ny))
cfg = HeatConfig(
    dx=dx, dy=dx, k_arr=k, q_arr=q,
    bc_dict={
        "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
        "east": BcSpec(type=BoundaryType.DIRICHLET, value=400.0),
    },
)
res = solve_heat(cfg)
x = np.arange(nx) * dx
T_exact = 300.0 + 100.0 * x / L
err = np.max(np.abs(res.temperature[:, 0] - T_exact))
print(f"max|T_num - T_exact| = {err:.3e}")
assert err <= 1e-10, f"M1 失败：误差 {err} > 1e-10"
print("M1 PASS")
print()

print("=== M2 功率守恒：绝热闭域+热源无稳态解 ===")
nx2, ny2 = 10, 10
dx2, dy2 = 1e-6, 1e-6
k2 = np.full((nx2, ny2), 148.0)
total_power = 1.0  # W
q2 = np.full((nx2, ny2), total_power / (dx2 * dy2 * nx2 * ny2))
cfg2 = HeatConfig(
    dx=dx2, dy=dy2, k_arr=k2, q_arr=q2,
    bc_dict={
        "west": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
        "east": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
        "south": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
        "north": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
    },
)
raised = False
try:
    solve_heat(cfg2)
except ValueError as exc:
    raised = True
    print(f"正确 raise ValueError: {exc}")
assert raised, "M2 失败：绝热+热源应 raise"
print("M2 PASS")
print()

print("=== M3 边界类型完整：5 类均可应用 ===")
cfgA = HeatConfig(
    dx=1e-6, dy=1e-6,
    k_arr=np.full((8, 8), 148.0),
    q_arr=np.zeros((8, 8)),
    bc_dict={
        "west": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
        "east": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
        "south": BcSpec(type=BoundaryType.CONVECTIVE, h=1e4, t_amb=300.0),
        "north": BcSpec(type=BoundaryType.RADIATIVE, emissivity=0.8, t_amb=300.0),
    },
)
resA = solve_heat(cfgA)
assert np.all(np.isfinite(resA.temperature)), "M3A 温度场非有限"
print(f"配置A（Dirichlet/Neumann/Convective/Radiative）求解 OK, T range = "
      f"[{resA.temperature.min():.3f}, {resA.temperature.max():.3f}]")

cfgB = HeatConfig(
    dx=1e-6, dy=1e-6,
    k_arr=np.full((8, 8), 148.0),
    q_arr=np.zeros((8, 8)),
    bc_dict={
        "west": BcSpec(type=BoundaryType.PERIODIC),
        "east": BcSpec(type=BoundaryType.PERIODIC),
        "south": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
        "north": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
    },
)
resB = solve_heat(cfgB)
assert np.all(np.isfinite(resB.temperature)), "M3B 温度场非有限"
periodic_err = np.max(np.abs(resB.temperature[0, :] - resB.temperature[-1, :]))
print(f"配置B（Periodic x + Dirichlet y）求解 OK, 周期误差 = {periodic_err:.3e}")
assert periodic_err <= 1e-10, f"周期边界未生效: {periodic_err}"
print("M3 PASS（5 类边界全部应用成功）")
print()

print("=== 耦合冒烟：heat_to_fde / ddm_to_heat ===")
nx3, ny3 = 16, 16
k3 = np.full((nx3, ny3), 148.0)
q3 = np.zeros((nx3, ny3))
cfg3 = HeatConfig(
    dx=1e-6, dy=1e-6, k_arr=k3, q_arr=q3,
    bc_dict={
        "west": BcSpec(type=BoundaryType.DIRICHLET, value=350.0),
        "east": BcSpec(type=BoundaryType.DIRICHLET, value=300.0),
        "south": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
        "north": BcSpec(type=BoundaryType.NEUMANN, value=0.0),
    },
)
res3 = solve_heat(cfg3)
xx, yy = np.meshgrid(np.arange(nx3), np.arange(ny3), indexing="ij")
ex = np.exp(-((xx - 8) ** 2 + (yy - 8) ** 2) / 8.0).astype(complex)
hx = ex.copy()
mode = Mode(
    ex=ex, ey=np.zeros_like(ex), ez=np.zeros_like(ex),
    hx=hx, hy=np.zeros_like(hx), hz=np.zeros_like(hx),
    beta=complex(1e7, 0), n_eff=complex(3.4, 0),
    te_fraction=1.0, tm_fraction=0.0, loss_db_cm=0.0, wavelength=1.55e-6,
)
corr = heat_to_fde(res3, mode)
print(f"heat_to_fde: delta_n_eff = {corr.delta_n_eff:.3e}, dn_dt = {corr.dn_dt}")
assert corr.delta_n_eff > 0, "热光修正方向错误（T>300 应 Δn>0）"

jx = np.full((nx3, ny3), 1e6)
jy = np.zeros((nx3, ny3))
sigma = np.full((nx3, ny3), 1e4)
ddm = DDMResult(current_density_x=jx, current_density_y=jy, conductivity=sigma)
Qjoule = ddm_to_heat(ddm)
expected = (1e6 ** 2) / 1e4
print(f"ddm_to_heat: Q = {Qjoule[0,0]:.3e} W/m^3 (期望 {expected:.3e})")
assert abs(Qjoule[0, 0] - expected) / expected <= 1e-12, "焦耳热计算错误"
print("耦合冒烟 PASS")
print()
print("===== 全部验收通过 =====")
