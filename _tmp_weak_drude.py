"""快速测试：弱 Drude（omega_p=1e15）验证 ADE 是否工作。

弱 Drude: eps_eff ≈ 9.16 + 0.02i, R ≈ 0.253（接近 eps_inf Fresnel 0.267）
若 FDTD 给 R≈0.253，则 ADE 对弱效应正确。
若 FDTD 给 R≈0.267，则 ADE 完全不工作。
"""
import time
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, DftMonitor, DrudeParams, FdtdConfig, FdtdSolver,
    ContinuousWave, TfsfBox, YeeGridFdtd, courant_dt,
)

C0 = 2.99792458e8
F0 = C0 / 1.55e-6
OMEGA0 = 2 * np.pi * F0


def dft_windowed(ts, dt, freq, n_start, n_end):
    n = np.arange(n_start, n_end)
    return np.sum(ts[n_start:n_end] * np.exp(-1j * 2 * np.pi * freq * n * dt)) / (n_end - n_start)


def test_weak_drude():
    """弱 Drude 测试。"""
    dx = dy = 8e-9
    nx, ny = 400, 80
    dt = courant_dt(dx, dy, cfl=0.49)
    v_step = C0 * dt /