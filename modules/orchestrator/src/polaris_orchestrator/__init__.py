"""PoLaRIS 编排层（polaris-orchestrator）。

组合 9 个独立子模块（core/pdk/place/route/sparam+pam4/drc/lvs/inverse/quantum）
为完整 EDA 流程，提供稳定 Python API ``run_eda_flow``，一键完成 9 个 stage
（polaris_pdk 在 stage 1 与 stage 7 各用一次）。polaris-verify 已拆分为
polaris-drc + polaris-lvs 两个单一职责子模块（v5.0）。polaris-sim 已拆分为
polaris-sparam + polaris-pam4 + polaris-fdtd + polaris-fde + polaris-eme +
polaris-bpm + polaris-fdfd 七个仿真子模块（v5.0）。

## 稳定 API

- ``run_eda_flow(circuit, output_dir, skip_stages=None, strict=False) -> dict``
  返回 ``{stages, n_success, n_failed, n_skipped, total_duration}``，
  每个 stage dict 含 ``{stage_id, name, status, duration, result, error}``。

## 设计原则

- 编排层允许 stage 失败继续（``strict=False`` 默认，编排策略，非 R03 业务
  fall-back），子模块内部仍禁止 fall-back（上游失败时下游自然 raise）。
- 对外 API 返回 JSON-serializable dict（与各子模块风格一致）。
- 不修改任何子模块代码，仅通过稳定 API 组合调用。

## Stage 顺序（9 个 stage，对应多个子模块）

1. PDK 目录     polaris_pdk.list_platforms
2. 电路验证     polaris_core.validate_circuit
3. AI 布局      polaris_place.place_circuit  mode="analytical"
4. 智能布线     polaris_route.route_circuit
5. 仿真验证     polaris_sparam.simulate_mzi_sparam + compute_clements_unitary
                + polaris_pam4.simulate_pam4
6. DRC / LVS    polaris_drc.run_drc + polaris_lvs.run_lvs
7. GDS 导出     polaris_gdsio.export_gds
8. 逆向设计     polaris_inverse.optimize_waveguide_width  n_iterations=10
9. 量子验证     polaris_quantum.klm_cnot + hom_interference

## 来源（R02 学术诚信，≥5 个文献 URL）

- OpenROAD RTL-to-GDS21 流程: https://github.com/The-OpenROAD-Project/OpenROAD
- TILOS MacroPlacement benchmark:
  https://github.com/TILOS-AI-Institute/MacroPlacement
- gdsfactory 流程编排: https://gdsfactory.github.io/gdsfactory/
- Hamard et al., "Open source photonic integrated circuits",
  Opt Express 2020, https://doi.org/10.1364/OE.391040
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, §10
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
"""

from __future__ import annotations

from polaris_orchestrator.flow import run_eda_flow

__version__ = "5.0.0"

__all__ = [
    "run_eda_flow",
    "__version__",
]
