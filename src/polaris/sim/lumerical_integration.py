"""R31-R33 路标：Ansys Lumerical 全流程对齐模块。

对标 Ansys Lumerical 全流程（MODE Solutions + INTERCONNECT + CHARGE），
提供波导模式求解、光链路系统仿真与电光协同仿真能力，实现 PoLaRIS 与
Lumerical 的多物理场交叉验证。

## 模块组成

1. ``ModeSolver`` — Lumerical MODE Solutions 对齐（波导模式求解器）
2. ``INTERCONNECTSimulator`` — Lumerical INTERCONNECT 对齐（光链路系统仿真）
3. ``CHARGESimulator`` — Lumerical CHARGE 对齐（电光协同仿真）
4. ``LumericalIntegration`` — Lumerical 全流程统一接口

## 拆分说明（facade 模式）

本文件为 facade，对外保持 ``from polaris.sim.lumerical_integration import X``
的导入路径不变。具体实现按物理域拆分到子模块：

- ``lumerical_constants`` — 共享物理常数（CODATA 2018 / SiEPIC PDK）
- ``lumerical_mode`` — MODE Solutions 波导模式求解器（R31）
- ``lumerical_interconnect`` — INTERCONNECT 光链路系统仿真（R32）
- ``lumerical_charge`` — CHARGE 电光协同仿真（R33）
- ``lumerical_integration`` — 全流程统一接口 + 交叉验证（本文件）

## 学术依据

- Ansys Lumerical MODE Solutions: https://www.ansys.com/products/optics/mode
- Ansys Lumerical INTERCONNECT: https://www.ansys.com/products/optics/interconnect
- Ansys Lumerical CHARGE: https://www.ansys.com/products/optics/charge
- Ansys Lumerical 多物理场协同:
  https://optics.ansys.com/hc/en-us/articles/360042414214
- Silvester & Ferrari, "Finite Elements for Electrical Engineers", 1996
- Agrawal, "Fiber-Optic Communication Systems", 4th ed., 2010
- Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., 2007
- Marcatili, Bell Syst. Tech. J. 48, 2071 (1969)

来源:
- Ansys Lumerical: https://www.ansys.com/products/optics
- LFSR PRBS: ITU-T O.150 标准

## 🚫不参与 GPU（R04）

纯 NumPy/SciPy/CPU 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。
"""

from __future__ import annotations

import logging

from polaris.sim.lumerical_charge import CHARGEConfig, CHARGESimulator
from polaris.sim.lumerical_constants import (  # noqa: F401
    _C0,
    _EPS0,
    _EPS_SI,
    _EPS_SIO2,
    _KB,
    _N_SI_INFRARED,
    _N_SILICON,
    _N_SIO2,
    _Q,
)
from polaris.sim.lumerical_interconnect import INTERCONNECTConfig, INTERCONNECTSimulator
from polaris.sim.lumerical_mode import ModeConfig, ModeSolver

# Facade re-export：保持外部 ``from polaris.sim.lumerical_integration import X``
# 的导入路径不变（R03 禁止 fall-back，所有符号真实迁移到子模块）。
__all__ = [
    "CHARGEConfig",
    "CHARGESimulator",
    "INTERCONNECTConfig",
    "INTERCONNECTSimulator",
    "LumericalIntegration",
    "ModeConfig",
    "ModeSolver",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 4. LumericalIntegration — 全流程统一接口
# ---------------------------------------------------------------------------


class LumericalIntegration:
    """Lumerical 全流程统一接口。

    学术依据：Ansys Lumerical 多物理场协同
    URL: https://optics.ansys.com/hc/en-us/articles/360042414214

    整合 MODE + INTERCONNECT + CHARGE 三大求解器：
    1. MODE 求解波导模式 → 提取 n_eff/模式剖面
    2. CHARGE 求解电场 → 提取调制器参数（Δn_eff/带宽）
    3. INTERCONNECT 系统仿真 → BER/眼图/OSNR

    数据流：
        waveguide_config → ModeSolver → n_eff
        modulator_config → CHARGESimulator → Δn_eff, bandwidth
        link_config → INTERCONNECTSimulator → BER, eye_diagram
    """

    def __init__(self) -> None:
        """初始化 Lumerical 全流程接口。"""
        self.mode_solver: ModeSolver | None = None
        self.interconnect_sim: INTERCONNECTSimulator | None = None
        self.charge_sim: CHARGESimulator | None = None

    def full_flow(
        self,
        waveguide_config: dict,
        modulator_config: dict,
        link_config: dict,
    ) -> dict:
        """运行完整 Lumerical 流程。

        学术依据：Ansys Lumerical 端到端多物理场仿真
        URL: https://optics.ansys.com/hc/en-us/articles/360042414214

        Args:
            waveguide_config: 波导配置（含 width/height/core_index/cladding_index）。
            modulator_config: 调制器配置（含 voltage/length/wavelength）。
            link_config: 链路配置（含 osnr/n_bits/modulation）。

        Returns:
            全流程结果字典。
        """
        # 1. MODE 求解波导模式
        # R05 v4.0-FDTD-GRID-P2: (0.05, 0.05) 实为 λ_SiO₂/20 @1.55μm（包层介质波长）
        mode_cfg = ModeConfig(
            wavelength=waveguide_config.get("wavelength", 1.55),
            grid_size=waveguide_config.get("grid_size", (0.05, 0.05)),
            n_modes=waveguide_config.get("n_modes", 4),
            boundary=waveguide_config.get("boundary", "PML"),
            window_size=waveguide_config.get("window_size", (1.6, 1.6)),
        )
        self.mode_solver = ModeSolver(mode_cfg)
        mode_result = self.mode_solver.solve_waveguide(
            width=waveguide_config["width"],
            height=waveguide_config.get("height", 0.22),
            core_index=waveguide_config.get("core_index", _N_SILICON),
            cladding_index=waveguide_config.get("cladding_index", _N_SIO2),
        )
        # 2. CHARGE 求解电光协同
        charge_cfg = CHARGEConfig(
            temperature=modulator_config.get("temperature", 300.0),
            doping_n=modulator_config.get("doping_n", 1e18),
            doping_p=modulator_config.get("doping_p", 1e18),
        )
        self.charge_sim = CHARGESimulator(charge_cfg)
        eo_result = self.charge_sim.electro_optic_simulation(modulator_config)
        # 3. INTERCONNECT 系统仿真
        ic_cfg = INTERCONNECTConfig(
            sample_rate=link_config.get("sample_rate", 1e12),
            bit_rate=link_config.get("bit_rate", 10e9),
            n_bits=link_config.get("n_bits", 128),
            modulation=link_config.get("modulation", "NRZ"),
        )
        self.interconnect_sim = INTERCONNECTSimulator(ic_cfg)
        link_result = self.interconnect_sim.run_link_simulation(link_config)
        return {
            "mode_result": mode_result,
            "eo_result": eo_result,
            "link_result": link_result,
            "waveguide_config": waveguide_config,
            "modulator_config": modulator_config,
            "link_config": link_config,
        }

    def cross_validate(self, polaris_result: dict, lumerical_result: dict) -> dict:
        """交叉验证 PoLaRIS vs Lumerical。

        学术依据：多求解器交叉验证方法论
        URL: https://optics.ansys.com/hc/en-us/articles/360042414214

        比较关键指标：n_eff/BER/bandwidth 的相对误差。

        Args:
            polaris_result: PoLaRIS 仿真结果。
            lumerical_result: Lumerical 仿真结果。

        Returns:
            交叉验证结果字典。
        """
        metrics: dict[str, dict] = {}
        # 比较 n_eff
        if "n_eff" in polaris_result and "n_eff" in lumerical_result:
            p_val = polaris_result["n_eff"]
            l_val = lumerical_result["n_eff"]
            if abs(l_val) > 1e-15:
                rel_err = abs(p_val - l_val) / abs(l_val)
                metrics["n_eff"] = {
                    "polaris": p_val,
                    "lumerical": l_val,
                    "relative_error": float(rel_err),
                    "passed": rel_err < 0.10,  # 10% 容差
                }
        # 比较 BER
        if "ber" in polaris_result and "ber" in lumerical_result:
            p_val = polaris_result["ber"]
            l_val = lumerical_result["ber"]
            # BER 用绝对误差（BER 很小时相对误差不稳定）
            abs_err = abs(p_val - l_val)
            metrics["ber"] = {
                "polaris": p_val,
                "lumerical": l_val,
                "absolute_error": float(abs_err),
                "passed": abs_err < 0.05,
            }
        # 比较 bandwidth
        if "bandwidth" in polaris_result and "bandwidth" in lumerical_result:
            p_val = polaris_result["bandwidth"]
            l_val = lumerical_result["bandwidth"]
            if abs(l_val) > 1e-15:
                rel_err = abs(p_val - l_val) / abs(l_val)
                metrics["bandwidth"] = {
                    "polaris": p_val,
                    "lumerical": l_val,
                    "relative_error": float(rel_err),
                    "passed": rel_err < 0.20,  # 20% 容差
                }
        # 总体通过率
        n_total = len(metrics)
        n_passed = sum(1 for m in metrics.values() if m["passed"])
        overall_pass = n_passed == n_total if n_total > 0 else False
        return {
            "metrics": metrics,
            "n_total": n_total,
            "n_passed": n_passed,
            "overall_pass": overall_pass,
            "alignment_score": float(n_passed / n_total) if n_total > 0 else 0.0,
        }
