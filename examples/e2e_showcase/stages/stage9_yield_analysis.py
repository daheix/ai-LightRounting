"""阶段 9: 蒙特卡洛良率分析（流片前签核）。

工业流程位置：原理图仿真（阶段 3）、版图后仿真（阶段 7）与 DRC/LVS
（阶段 8）全部通过之后、GDS 流片导出（阶段 12）之前。评估工艺偏差对
电路插损规格的影响，预测制造良率——这是工业光子流片前的标准签核
（sign-off）环节。

统计方法来源（R02 学术诚信，≥5 文献 URL）:
- Metropolis & Ulam 1949, "The Monte Carlo Method", J. Am. Stat. Assoc.
  44(247):335-341, https://doi.org/10.1080/01621459.1949.10483310
- Bogaerts et al. 2018, "Layout-Aware Yield Prediction of Photonic
  Circuits", OFC（光子电路版图感知良率预测框架）
  https://fib.intec.ugent.be/download/pub_4125.pdf
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015,
  §9 制造偏差与工艺角, https://www.cambridge.org/9781107083456
- Singhal & Pinel 1981, "Statistical design centering and tolerancing
  using parametric sampling", IEEE TCAS 28(7):692-701
  https://doi.org/10.1109/TCS.1981.1085043
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer, https://doi.org/10.1007/978-0-387-21617-1
- SiEPIC EBeam PDK 器件损耗典型值
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

工艺偏差模型（*创新* 工程估算，底层逻辑记录）:
每器件插入损耗独立高斯涨落：loss_i' = loss_i × (1 + σ·ε_i)，
ε_i ~ N(0,1)，σ = 0.05（1σ = 5%）。

*创新* 标注与依据：
- 底层逻辑：光子 foundry PDK corner 模型通常以 ±3σ 给出器件插损
  工艺角范围；SiEPIC/AMF 等 SOI 平台报道的无源器件插损工艺角
  spread 典型量级为 ±10-15%（3σ）。取 1σ = 5% 对应 3σ = 15%，
  与 foundry corner 报道量级一致（Chrostowski 2015 §9.4）。
- 独立性假设：芯片级随机偏差（线宽粗糙、侧壁散射）在空间上
  弱相关，器件间独立假设为良率文献常用一阶近似
  （Bogaerts 2018 的相关性建模为高阶修正）。
- 该模型为工程估算而非编造数据：σ 可按实际 PDK corner 数据标定。

合规: R02 学术诚信 / R03 禁止 fall-back（失败即 raise）/ R04 不参与 GPU。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from polaris_yield import monte_carlo_simulate

from stages.stage6_routing import _mzi_circuit

_logger = logging.getLogger("e2e_showcase")

# 良率分析参数（与 polaris_flow SimConfig 默认值一致，保证跨模块对齐）
_N_SAMPLES = 10000  # 蒙特卡洛采样数（10000 采样标准误 ~0.5%，Glasserman 2003 §1）
_SIGMA_REL = 0.05  # 器件损耗相对涨落 σ（1σ=5%，3σ=15% 与 foundry corner 一致）
_LOSS_TARGET_DB = 5.0  # MZI 链路插损规格（dB，与 polaris_flow SimConfig 默认一致）
_SEED = 42  # 固定随机种子，保证 showcase 结果可复现


def run(output_dir: Path) -> dict:
    """执行阶段 9: 蒙特卡洛良率分析（流片前签核）。

    以 MZI 演示电路为对象，基于紧凑模型逐器件损耗分解，对每个器件
    损耗施加独立高斯工艺偏差涨落，蒙特卡洛采样估计总插损分布，
    按 5.0 dB 链路规格统计良率。报告写入
    output_dir/reports/yield_report.json。

    Args:
        output_dir: 输出目录（含 reports/ 子目录）。

    Returns:
        阶段执行结果，含 yield_report（良率/损耗分布统计）。
    """
    from polaris_flow.default_simulator import (
        _DefaultSimulator,
        supplement_waveguide_lengths,
    )

    _logger.info(
        "阶段 9 开始: 蒙特卡洛良率分析（%d 采样，σ=%.1f%%，规格 %.2f dB）",
        _N_SAMPLES, _SIGMA_REL * 100, _LOSS_TARGET_DB,
    )
    reports_dir = Path(output_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # MZI 电路逐器件损耗分解（紧凑模型查表，与主流水线同一损耗表）
    circuit = _mzi_circuit()
    supplement_waveguide_lengths(circuit)
    simulator = _DefaultSimulator(mode="table")
    device_losses = simulator.device_loss_breakdown(circuit)
    base_losses = np.array(
        [float(item["loss_db"]) for item in device_losses], dtype=float
    )
    schematic_loss_db = float(np.sum(base_losses))

    def _total_loss(params: np.ndarray) -> float:
        """总插损 = 各器件损耗之和（dB 域级联可加，Pozar §4）。"""
        return float(np.sum(params))

    mc_result = monte_carlo_simulate(
        _total_loss, base_losses,
        n_samples=_N_SAMPLES, sigma=_SIGMA_REL, seed=_SEED,
    )

    samples = np.asarray(mc_result.samples, dtype=float)
    n_pass = int(np.sum(samples <= _LOSS_TARGET_DB))
    yield_estimate = n_pass / _N_SAMPLES

    yield_report = {
        "yield_estimate": float(yield_estimate),
        "n_pass": n_pass,
        "n_samples": _N_SAMPLES,
        "mean_loss_db": float(np.mean(samples)),
        "std_loss_db": float(np.std(samples)),
        "p05_loss_db": float(np.percentile(samples, 5)),
        "p95_loss_db": float(np.percentile(samples, 95)),
        "p99_loss_db": float(np.percentile(samples, 99)),
        "schematic_loss_db": schematic_loss_db,
        "loss_target_db": _LOSS_TARGET_DB,
        "sigma_rel": _SIGMA_REL,
        "n_devices": int(len(base_losses)),
        "seed": _SEED,
        "method": "monte_carlo_per_device_loss",
        "device_losses": device_losses,
    }

    report_path = reports_dir / "yield_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(yield_report, f, ensure_ascii=False, indent=2)

    _logger.info(
        "阶段 9 完成: 良率 %.2f%%（%d/%d 通过），损耗均值 %.4f dB，"
        "99 分位 %.4f dB（规格 %.2f dB）",
        yield_estimate * 100, n_pass, _N_SAMPLES,
        yield_report["mean_loss_db"], yield_report["p99_loss_db"], _LOSS_TARGET_DB,
    )

    return {
        "yield_report": yield_report,
        "report_path": str(report_path),
    }
