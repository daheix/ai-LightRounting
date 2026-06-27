"""R17 光电协同仿真模块测试。

测试覆盖:
1. test_config_validation: 配置验证（合法 + 非法 raise）
2. test_add_modulator: 调制器添加与 device_id 自增
3. test_add_photodetector: 探测器添加
4. test_add_laser: 激光器添加 + 默认偏置
5. test_export_vlsir_spice: VLSIR SPICE 网表导出语法正确性
6. test_generate_verilog_a_modulator: MZM Verilog-A 生成
7. test_generate_verilog_a_pd: 探测器 Verilog-A 生成
8. test_generate_verilog_a_laser: 激光器 Verilog-A 生成
9. test_run_cosim_basic: 基础协同仿真（Laser+MZM+PD 线性链路）
10. test_newton_solve: 牛顿迭代收敛性
11. test_newton_solve_non_convergence: 牛顿不收敛即 raise（R03）
12. test_cocotb_testbench_generation: cocotb 驱动生成
13. test_mzm_transmission_physics: MZM 物理传输验证（V=Vπ 时零点）

来源:
- R17 路标: 光电协同仿真
- Chrostowski 2015 §8.4/§9.2: https://www.cambridge.org/core/books/silicon-photonics-design/
- Coldren & Corzine 1995 §5: https://www.wiley.com/en-us/Diode+Laser+Fundamentals
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from polaris.sim.photoelectric_cosim import (
    CoSimConfig,
    LaserSpec,
    ModulatorSpec,
    PhotoelectricCoSim,
)


# ---------------------------------------------------------------------------
# 辅助: 构建标准链路 Laser+MZM+PD
# ---------------------------------------------------------------------------
def _build_full_link() -> PhotoelectricCoSim:
    """构建 Laser+MZM+PD 完整光电链路仿真器。"""
    cfg = CoSimConfig(timestep=1e-12, total_time=1e-9, input_power_w=1e-3)
    cosim = PhotoelectricCoSim(cfg)
    cosim.add_laser(threshold_current=10e-3, slope_efficiency=0.4)  # 40 mA, 0.4 W/A
    cosim.add_modulator(vpi=2.0, insertion_loss=0.5, bias_v=1.0)     # Vπ=2V
    cosim.add_photodetector(responsivity=0.9, dark_current=10e-9)    # 0.9 A/W
    return cosim


# ---------------------------------------------------------------------------
# 1. 配置验证
# ---------------------------------------------------------------------------
def test_config_validation():
    """合法配置通过，非法配置 raise ValueError（R03 无 fall-back）。"""
    cfg = CoSimConfig(timestep=1e-12, total_time=1e-9)
    assert cfg.timestep == 1e-12
    assert cfg.total_time == 1e-9
    assert cfg.load_resistance == 50.0

    with pytest.raises(ValueError, match="timestep"):
        CoSimConfig(timestep=0.0)
    with pytest.raises(ValueError, match="total_time"):
        CoSimConfig(timestep=1e-9, total_time=1e-12)
    with pytest.raises(ValueError, match="load_resistance"):
        CoSimConfig(load_resistance=-1.0)
    with pytest.raises(ValueError, match="newton_maxiter"):
        CoSimConfig(newton_maxiter=1)


def test_config_input_power_validation():
    """input_power_w 负值 raise。"""
    with pytest.raises(ValueError, match="input_power_w"):
        CoSimConfig(input_power_w=-0.001)


# ---------------------------------------------------------------------------
# 2-4. 器件添加
# ---------------------------------------------------------------------------
def test_add_modulator():
    """调制器添加返回自增 device_id，参数正确写入。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    did = cosim.add_modulator(vpi=3.0, insertion_loss=1.0, bias_v=0.5)
    assert did == 1
    _kind, spec = cosim._lookup(did)
    assert isinstance(spec, ModulatorSpec)
    assert spec.vpi == 3.0
    assert spec.insertion_loss_db == 1.0
    assert spec.bias_v == 0.5


def test_add_photodetector():
    """探测器添加返回自增 device_id。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    did = cosim.add_photodetector(responsivity=0.8, dark_current=5e-9)
    assert did == 1
    # 多个器件 id 连续自增
    did2 = cosim.add_photodetector(responsivity=1.0, dark_current=0.0)
    assert did2 == 2


def test_add_laser():
    """激光器添加，默认偏置 = 2× 阈值（Coldren 1995 §5.4）。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    did = cosim.add_laser(threshold_current=20e-3, slope_efficiency=0.3)
    _kind, spec = cosim._lookup(did)
    assert isinstance(spec, LaserSpec)
    assert spec.threshold_current == 20e-3
    assert spec.bias_current == pytest.approx(40e-3)  # 2× 阈值
    # 非法参数 raise
    with pytest.raises(ValueError, match="threshold_current"):
        cosim.add_laser(threshold_current=0.0, slope_efficiency=0.1)


def test_spec_validation_invalid():
    """器件规格非法参数 raise（R03）。"""
    from polaris.sim.photoelectric_cosim import PhotodetectorSpec

    with pytest.raises(ValueError, match="V_pi"):
        ModulatorSpec(vpi=-1.0, insertion_loss_db=0.0)
    with pytest.raises(ValueError, match="insertion_loss_db"):
        ModulatorSpec(vpi=2.0, insertion_loss_db=-0.5)
    with pytest.raises(ValueError, match="responsivity"):
        PhotodetectorSpec(responsivity=-0.1, dark_current=0.0)
    with pytest.raises(ValueError, match="dark_current"):
        PhotodetectorSpec(responsivity=0.5, dark_current=-1e-9)


# ---------------------------------------------------------------------------
# 5. VLSIR SPICE 网表导出
# ---------------------------------------------------------------------------
def test_export_vlsir_spice(tmp_path: Path):
    """导出 VLSIR SPICE 网表，验证关键语法元素。"""
    cosim = _build_full_link()
    out = cosim.export_vlsir_spice(tmp_path / "link.sp")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    # SPICE 关键语法
    assert text.startswith("*")
    assert ".subckt dev_1" in text  # 激光器子电路
    assert ".subckt dev_2" in text  # 调制器子电路
    assert ".subckt dev_3" in text  # 探测器子电路
    assert ".subckt cosim_top in out" in text
    assert ".ends cosim_top" in text
    assert ".tran" in text
    assert ".end" in text
    assert "Xtop in out cosim_top" in text


# ---------------------------------------------------------------------------
# 6-8. Verilog-A 模型生成
# ---------------------------------------------------------------------------
def test_generate_verilog_a_modulator():
    """MZM Verilog-A 生成，含 cos² 传输与 Vπ 参数。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    did = cosim.add_modulator(vpi=2.5, insertion_loss=0.3, bias_v=1.0)
    code = cosim.generate_verilog_a(did)
    assert "module photonic_mzm_" in code
    assert "vpi = 2.500000e+00" in code
    assert "cos(phi) * cos(phi)" in code  # cos² 传输
    assert "endmodule" in code


def test_generate_verilog_a_pd():
    """探测器 Verilog-A 生成，含响应度与负载电阻。"""
    cosim = PhotoelectricCoSim(CoSimConfig(load_resistance=100.0))
    did = cosim.add_photodetector(responsivity=0.95, dark_current=1e-9)
    code = cosim.generate_verilog_a(did)
    assert "module photonic_pd_" in code
    assert "responsivity = 9.500000e-01" in code
    assert "i_photo = responsivity * p_in + dark_current" in code
    assert "load_resistance = 1.000000e+02" in code


def test_generate_verilog_a_laser():
    """激光器 Verilog-A 生成，含 L-I 阈值特性与速率方程注释。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    did = cosim.add_laser(threshold_current=15e-3, slope_efficiency=0.35)
    code = cosim.generate_verilog_a(did)
    assert "module photonic_laser_" in code
    assert "threshold = 1.500000e-02" in code
    assert "slope_eff * (I(i_in) - threshold)" in code
    assert "dN/dt" in code  # 速率方程注释


def test_generate_verilog_a_unknown_device():
    """未注册 device_id raise KeyError（R03）。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    with pytest.raises(KeyError, match="未注册"):
        cosim.generate_verilog_a(999)


# ---------------------------------------------------------------------------
# 9. 基础协同仿真
# ---------------------------------------------------------------------------
def test_run_cosim_basic():
    """Laser+MZM+PD 完整链路协同仿真，验证时域波形维度与物理一致性。"""
    cosim = _build_full_link()
    result = cosim.run_cosim()
    time = result["time"]
    assert time.shape[0] == int(round(1e-9 / 1e-12)) + 1  # 1001 点
    assert result["rf_voltage"].shape == time.shape
    assert result["optical_power"].shape == time.shape
    assert result["detector_current"].shape == time.shape
    assert result["output_voltage"].shape == time.shape
    # 光功率非负
    assert np.all(result["optical_power"] >= 0.0)
    # 探测器电流 >= 暗电流
    assert np.all(result["detector_current"] >= 10e-9 - 1e-15)
    # 默认正弦激励非全零
    assert np.max(np.abs(result["rf_voltage"])) > 0.5


def test_run_cosim_with_explicit_rf():
    """显式 rf_voltage 数组驱动，验证调制器 cos² 调制作用。"""
    cosim = _build_full_link()
    n = int(round(1e-9 / 1e-12)) + 1
    # 全 Vπ 偏置 → 传输 cos²(π/2)=0（消光）
    rf = np.full(n, 1.0)  # bias_v=1.0, Vπ=2.0 → (1+1)/(2*2)=0.5 → cos²(π/2)=0
    result = cosim.run_cosim(rf_voltage=rf)
    # cos²(π*2/(2*2)) = cos²(π/2) = 0 → 光功率近似 0（含 IL）
    assert np.allclose(result["optical_power"], 0.0, atol=1e-12)


def test_run_cosim_rf_length_mismatch():
    """rf_voltage 长度不匹配 raise ValueError（R03）。"""
    cosim = _build_full_link()
    with pytest.raises(ValueError, match="长度"):
        cosim.run_cosim(rf_voltage=np.zeros(10))


def test_run_cosim_duplicate_device_raises():
    """重复注册同型器件 raise RuntimeError（拓扑约束）。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    cosim.add_modulator(vpi=2.0, insertion_loss=0.0)
    cosim.add_modulator(vpi=3.0, insertion_loss=0.0)
    with pytest.raises(RuntimeError, match="modulator"):
        cosim.run_cosim()


# ---------------------------------------------------------------------------
# 10-11. 牛顿迭代
# ---------------------------------------------------------------------------
def test_newton_solve():
    """牛顿迭代求解 x - cos(x) = 0（已知根 ≈ 0.739085）。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    root = cosim.newton_solve(lambda x: x - math.cos(x), x0=1.0)
    assert root == pytest.approx(0.7390851332151607, abs=1e-9)


def test_newton_solve_with_derivative():
    """带解析导数的牛顿迭代求解 x² - 2 = 0（根 √2）。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    root = cosim.newton_solve(lambda x: x * x - 2.0, x0=1.5, fprime=lambda x: 2.0 * x)
    assert root == pytest.approx(math.sqrt(2.0), abs=1e-10)


def test_newton_solve_non_convergence():
    """不收敛（maxiter 极小 + 严格容差）raise RuntimeError（R03 无 fall-back）。"""
    cosim = PhotoelectricCoSim(CoSimConfig(newton_maxiter=2, newton_tol=1e-30))
    # x²-1 从 1e6 出发，2 次牛顿迭代远未到根 ±1，info.converged=False
    with pytest.raises(RuntimeError):
        cosim.newton_solve(
            lambda x: x * x - 1.0, x0=1.0e6, fprime=lambda x: 2.0 * x
        )


def test_solve_laser_carrier_density():
    """激光器稳态载流子密度牛顿求解，结果物理合理。"""
    cosim = PhotoelectricCoSim(CoSimConfig())
    spec = LaserSpec(threshold_current=10e-3, slope_efficiency=0.4)
    n_star = cosim.solve_laser_carrier_density(current=5e-3, spec=spec)
    # N* 应为正且接近 N_tr 量级（1e24 1/m³）
    assert n_star > 0.0
    assert 1e23 < n_star < 1e25


# ---------------------------------------------------------------------------
# 12. cocotb 测试驱动生成
# ---------------------------------------------------------------------------
def test_cocotb_testbench_generation(tmp_path: Path):
    """生成 cocotb testbench + Makefile，含器件数与时间步。"""
    cosim = _build_full_link()
    tb = cosim.generate_cocotb_testbench(tmp_path / "cocotb")
    assert tb.exists()
    text = tb.read_text(encoding="utf-8")
    assert "import cocotb" in text
    assert "N_DEVICES = 3" in text
    assert "async def test_photoelectric_link" in text
    assert (tmp_path / "cocotb" / "Makefile").exists()


# ---------------------------------------------------------------------------
# 13. MZM 物理传输验证
# ---------------------------------------------------------------------------
def test_mzm_transmission_physics():
    """验证 MZM 传输物理: V=Vπ 时 cos²(π/2)=0（消光），V=0 时最大。"""
    spec = ModulatorSpec(vpi=2.0, insertion_loss_db=0.0, bias_v=0.0)
    # V=0 → cos²(0)=1（满传输）
    t_max = PhotoelectricCoSim.mzm_transmission(0.0, spec)
    assert t_max == pytest.approx(1.0, abs=1e-12)
    # V=Vπ → cos²(π/2)=0（消光点）
    t_min = PhotoelectricCoSim.mzm_transmission(2.0, spec)
    assert t_min == pytest.approx(0.0, abs=1e-12)
    # V=Vπ/2 → cos²(π/4)=0.5（正交点）
    t_quad = PhotoelectricCoSim.mzm_transmission(1.0, spec)
    assert t_quad == pytest.approx(0.5, abs=1e-12)


def test_laser_li_threshold():
    """验证激光器 L-I 阈值特性: 阈值以下 0，阈值以上线性。"""
    spec = LaserSpec(threshold_current=10e-3, slope_efficiency=0.4)
    # 阈值以下
    assert PhotoelectricCoSim.laser_li(5e-3, spec) == pytest.approx(0.0)
    # 阈值点
    assert PhotoelectricCoSim.laser_li(10e-3, spec) == pytest.approx(0.0)
    # 阈值以上: P = 0.4 * (20mA - 10mA) = 4 mW
    assert PhotoelectricCoSim.laser_li(20e-3, spec) == pytest.approx(4e-3, abs=1e-12)
