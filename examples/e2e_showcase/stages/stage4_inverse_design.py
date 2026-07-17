"""阶段 4: Adjoint 逆向设计。

使用 polaris-inverse 子模块的 JAX 可微分 FDTD + jax.grad 自动微分优化波导宽度，
演示光子逆向设计能力（对标 lumopt / Lumerical 逆向设计）。

PoLaRIS v5.0 迁移说明:
    旧 v4 自实现 FDTD 网格构建、FoM 函数、jax.grad 梯度计算、优化循环、
    动量优化器等全部代码。v5.0 已将 Adjoint 逆向设计能力封装为
    polaris-inverse 子模块的稳定 API:
      ``optimize_waveguide_width(n_iterations=50, learning_rate=0.5) -> dict``
    本 stage 改为直接调用该 API，删除全部自实现优化循环代码。

核心创新（polaris-inverse 子模块实现）:
- *创新* 用 jax.grad 自动计算 FoM 对波导宽度参数的梯度，
  替代 lumopt 手动推导伴随方程（adjoint equation）。
- 支持理论: Mahau 2024 arXiv:2412.12360 验证了 JAX 可微 FDTD 的可行性；
  Hughes 2018 ACS Photonics 证明 autograd = adjoint。
- 梯度计算开销与参数数无关（链式法则 + 反向模式 AD = 伴随方法，
  Giles & Pierce 2000 SIAM Review 数学等价）。
- heavy-ball 动量优化器（Polyak 1964），抑制梯度符号交替震荡；
  梯度裁剪 [-1,1] 防 NaN 爆炸。

公式来源（R02 学术诚信）:
- Yee 1966 IEEE TAP "Numerical solution of initial boundary value problems
  involving Maxwell's equations in isotropic media"
  https://doi.org/10.1109/TAP.1966.1138693
- Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method"
- Mahau 2024 arXiv:2412.12360 "Differentiable FDTD for inverse design"
  https://arxiv.org/abs/2412.12360
- lumopt: https://github.com/chriskeraly/lumopt
- Jensen & Sigmund 2011 "Topology optimization for nano-photonics"
  https://doi.org/10.1002/lpor.201000014
- Polyak 1964 "Some methods of speeding up the convergence of iteration methods"
- Gedney 1996 IEEE TAP（单轴各向异性 PML）
  https://doi.org/10.1109/8.546249
- Hughes 2018 ACS Photonics（autograd = adjoint）
  https://arxiv.org/abs/1811.01255
- Giles & Pierce 2000 SIAM Review "An Introduction to the Adjoint Approach"
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from polaris_inverse import optimize_waveguide_width

_logger = logging.getLogger("e2e_showcase")

# 优化参数
# showcase 演示迭代数: 5 步（非 polaris-inverse 默认 50 步）。
# 工程决策原因（非 R03 fall-back，真实 JAX 计算）:
#   1. JAX JIT 编译 FDTD+grad 内核开销 ~10s，每迭代 ~0.5-1s；
#      50 步在 showcase 120s 超时内无法完成（实测超时 EXIT=124）。
#   2. 实测 n=5 已收敛 (converged=True, improvement=+0.13dB)，
#      网格小 (24×12×8, dx=200nm) 收敛快。
#   3. polaris-inverse 默认 n_iterations=50 用于生产级（Jensen & Sigmund 2011），
#      showcase 演示用 5 步足够展示 JAX 可微 FDTD 逆向设计能力。
# 注: 旧版 n=10 FoM 恶化 -0.72dB 的优化器震荡 bug 已于 2026-07-03 修复
#     （best-checkpoint 追踪，见 polaris_inverse.adjoint），现 n≥10 亦
#     improvement_db >= 0。showcase 仍用 n=5 因 showcase 超时约束 + 已收敛。
# 来源: Jensen & Sigmund 2011 拓扑优化典型参数；lumopt 商业工具通常 50-200 次迭代
_N_ITERATIONS = 5
_LEARNING_RATE = 0.5


def run(output_dir: Path) -> dict:
    """执行阶段 4: Adjoint 逆向设计。

    使用 polaris-inverse ``optimize_waveguide_width`` 执行 JAX 可微分 FDTD +
    jax.grad 自动微分优化波导宽度，演示光子逆向设计能力（对标 lumopt）。

    流程:
    1. 调用 polaris_inverse.optimize_waveguide_width(n_iterations, learning_rate)
    2. 子模块内部执行: 构建 YeeGrid3D 网格 + DifferentiableFDTD 求解器 →
       定义 FoM(width) = 监视器时域信号峰值 → jax.grad 自动计算 dFoM/dwidth
       （*创新*，替代手动伴随方程）→ heavy-ball 动量梯度上升优化 width
    3. 保存优化历史到 JSON
    4. 返回优化结果摘要

    学术诚信说明:
        - *创新* 点: 用 jax.grad 自动微分替代 lumopt 手动推导伴随方程。
        - 支持理论: Mahau 2024 arXiv:2412.12360 验证了 JAX 可微 FDTD 可行性；
          Hughes 2018 ACS Photonics 证明 autograd = adjoint。
        - 本实现为 showcase 演示，网格较小（24×12×8, dx=200nm），迭代 5 步
          （适配 120s 超时；polaris-inverse 默认 50 步用于生产级），
          非生产级逆向设计（生产级需 100+ 迭代 + 更大网格）。

    Args:
        output_dir: 输出目录。

    Returns:
        阶段执行结果，含:
        - method: 优化方法描述
        - initial_width_nm/optimal_width_nm: 初始/优化波导半宽度 (nm)
        - initial_fom/final_fom: 初始/最终 FoM
        - improvement_db: FoM 改善量 (dB)
        - fom_history: FoM 历史
        - converged: 是否收敛
        - iterations: 迭代次数

    Raises:
        RuntimeError: JAX 不可用或优化过程出现 NaN（R03 禁止 fall-back）。
    """
    _logger.info(
        "阶段 4 开始: Adjoint 逆向设计（polaris-inverse, JAX 可微分 FDTD）"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # 调用 polaris-inverse 子模块执行 Adjoint 逆向设计
    # *创新* jax.grad 自动微分替代 lumopt 手动伴随方程（polaris-inverse 内部实现）
    result = optimize_waveguide_width(
        n_iterations=_N_ITERATIONS,
        learning_rate=_LEARNING_RATE,
    )

    _logger.info(
        "Adjoint 优化完成: 初始 FoM=%.6e → 最终 FoM=%.6e, 改善 %.2f dB, 收敛=%s",
        result["initial_fom"],
        result["final_fom"],
        result["improvement_db"],
        result["converged"],
    )
    _logger.info(
        "波导半宽度: %.4f → %.4f nm",
        result["initial_width_nm"],
        result["optimal_width_nm"],
    )

    # 保存优化历史到 JSON
    history_path = output_dir / "adjoint_optimization_history.json"
    history_data = {
        "method": (
            "JAX jax.grad 自动微分（*创新*，替代 lumopt 手动伴随方程）"
            "— polaris-inverse 子模块"
        ),
        "initial_width_nm": result["initial_width_nm"],
        "optimal_width_nm": result["optimal_width_nm"],
        "initial_fom": result["initial_fom"],
        "final_fom": result["final_fom"],
        "improvement_db": result["improvement_db"],
        "fom_history": result["fom_history"],
        "iterations": result["iterations"],
        "converged": result["converged"],
        "n_iterations_requested": _N_ITERATIONS,
        "learning_rate": _LEARNING_RATE,
        "sources": [
            "Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693",
            "Mahau 2024 arXiv:2412.12360",
            "lumopt https://github.com/chriskeraly/lumopt",
            "Jensen & Sigmund 2011 https://doi.org/10.1002/lpor.201000014",
            "Polyak 1964 heavy-ball method",
            "Hughes 2018 ACS Photonics https://arxiv.org/abs/1811.01255",
            "Giles & Pierce 2000 SIAM Review (adjoint approach)",
        ],
    }
    history_path.write_text(
        json.dumps(history_data, indent=2), encoding="utf-8"
    )
    _logger.info("优化历史保存: %s", history_path.name)

    _logger.info(
        "阶段 4 完成: Adjoint 逆向设计, FoM 改善 %.2f dB, 收敛=%s",
        result["improvement_db"],
        result["converged"],
    )

    return {
        "method": history_data["method"],
        "initial_width_nm": result["initial_width_nm"],
        "optimal_width_nm": result["optimal_width_nm"],
        "initial_fom": result["initial_fom"],
        "final_fom": result["final_fom"],
        "improvement_db": result["improvement_db"],
        "fom_history": result["fom_history"],
        "converged": result["converged"],
        "iterations": result["iterations"],
    }
