"""功能清单与实现/ 44 文档 v4→v5.0 路径全量替换（R11 一次性完成）。

策略（与 PoLaRIS功能清单.md 2026-07-17 核对版一致）:
1. 已实现功能引用: src/polaris/x/y.py[:行号] -> modules/.../y.py（去行号，新文件行号必然失效）
2. 规划待建引用（文档自身标注"待建/新增/Phase X"的未来文件）: 按 v5.0 模块目录更新
3. v5.0 已移除功能: 路径替换为 "v5.0 已移除（原 src/polaris/x/y.py）" 诚实标注
映射依据: 2026-2028开发计划/PoLaRIS功能清单.md v5.0 落点 + 文件系统实测。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/workspace")
DOCS = ROOT / "2026-2028开发计划" / "功能清单与实现"

# ============ 文件级映射（.py 精确路径） ============
# 来源: PoLaRIS功能清单.md v5.0 落点（已核对）+ 文件系统实测
FILE_MAP: dict[str, str] = {
    # --- 唯一匹配（文件系统确认） ---
    "src/polaris/data/benchmark_evaluator.py": "modules/nn/src/polaris_nn/data/benchmark_evaluator.py",
    "src/polaris/data/data_loader.py": "modules/nn/src/polaris_nn/data/data_loader.py",
    "src/polaris/data/tilos_benchmark.py": "modules/nn/src/polaris_nn/data/tilos_benchmark.py",
    "src/polaris/data/variant_generator.py": "modules/nn/src/polaris_nn/data/variant_generator.py",
    "src/polaris/data/gds_loader.py": "modules/nn/src/polaris_nn/data/gds_loader.py",
    "src/polaris/engine/waveguide_router.py": "modules/router_advanced/src/polaris_router_advanced/waveguide_router.py",
    "src/polaris/eval/layout_render.py": "modules/gds_tools/src/polaris_gds_tools/layout_render.py",
    "src/polaris/pdk/catalog.py": "modules/pdk/src/polaris_pdk/catalog.py",
    "src/polaris/pdk/optodesigner.py": "modules/pdk_advanced/src/polaris_pdk_advanced/optodesigner.py",
    "src/polaris/pdk/pcell.py": "modules/pdk_advanced/src/polaris_pdk_advanced/pcell.py",
    "src/polaris/pipeline/curvy_router.py": "modules/flow/src/polaris_flow/curvy_router.py",
    "src/polaris/pipeline/__init__.py": "modules/orchestrator/src/polaris_orchestrator/__init__.py",
    "src/polaris/router/bundle_router.py": "modules/router_advanced/src/polaris_router_advanced/bundle_router.py",
    "src/polaris/router/curvy_router.py": "modules/flow/src/polaris_flow/curvy_router.py",
    "src/polaris/router/global_router.py": "modules/router_advanced/src/polaris_router_advanced/global_router.py",
    "src/polaris/router/multilayer.py": "modules/router_advanced/src/polaris_router_advanced/multilayer.py",
    "src/polaris/router/obstacle_grid.py": "modules/router_advanced/src/polaris_router_advanced/obstacle_grid.py",
    "src/polaris/router/opto_electrical.py": "modules/router_advanced/src/polaris_router_advanced/opto_electrical.py",
    "src/polaris/router/path_geometry.py": "modules/router_advanced/src/polaris_router_advanced/path_geometry.py",
    "src/polaris/router/rip_reroute.py": "modules/router_advanced/src/polaris_router_advanced/rip_reroute.py",
    "src/polaris/router/waveguide_router.py": "modules/router_advanced/src/polaris_router_advanced/waveguide_router.py",
    "src/polaris/sim/cascade.py": "modules/circuit/src/polaris_circuit/cascade.py",
    "src/polaris/sim/cascade/smatrix.py": "modules/multiphysics/src/polaris_multiphysics/rcwa/smatrix.py",
    "src/polaris/sim/eqdrc.py": "modules/verify_advanced/src/polaris_verify_advanced/eqdrc.py",
    "src/polaris/sim/graph_lvs.py": "modules/verify_advanced/src/polaris_verify_advanced/graph_lvs.py",
    "src/polaris/sim/hierarchical_drc.py": "modules/verify_advanced/src/polaris_verify_advanced/hierarchical_drc.py",
    "src/polaris/sim/klayout_drc.py": "modules/verify_advanced/src/polaris_verify_advanced/klayout_drc.py",
    "src/polaris/sim/mna_spice.py": "modules/circuit/src/polaris_circuit/mna_spice.py",
    "src/polaris/sim/monte_carlo.py": "modules/yield/src/polaris_yield/monte_carlo.py",
    "src/polaris/sim/rcwa/smatrix.py": "modules/multiphysics/src/polaris_multiphysics/rcwa/smatrix.py",
    "src/polaris/sim/rcwa/solver_1d.py": "modules/multiphysics/src/polaris_multiphysics/rcwa/solver_1d.py",
    "src/polaris/sim/rcwa/solver_2d.py": "modules/multiphysics/src/polaris_multiphysics/rcwa/solver_2d.py",
    "src/polaris/sim/simulator.py": "modules/circuit/src/polaris_circuit/simulator.py",
    "src/polaris/sim/system_level.py": "modules/circuit/src/polaris_circuit/system_level.py",
    "src/polaris/sim/models.py": "modules/circuit/src/polaris_circuit/models.py",
    "src/polaris/trainer/ppo.py": "modules/trainer/src/polaris_trainer/ppo.py",
    "src/polaris/trainer/train_loop.py": "modules/trainer/src/polaris_trainer/train_loop.py",
    # --- 功能清单 v5.0 落点（无匹配项，手动确认） ---
    "src/polaris/engine/alphachip_gnn.py": "modules/place/src/polaris_place/ppo_gnn.py",
    "src/polaris/engine/analytical_placer.py": "modules/place/src/polaris_place/analytical.py",
    "src/polaris/engine/congestion.py": "modules/router_advanced/src/polaris_router_advanced/global_router.py",
    "src/polaris/engine/density_field.py": "modules/place/src/polaris_place/metrics.py",
    "src/polaris/engine/gnn.py": "modules/place/src/polaris_place/ppo_gnn.py",
    "src/polaris/engine/netlist.py": "modules/core/src/polaris_core/specs.py",
    "src/polaris/pdk/device.py": "modules/pdk/src/polaris_pdk/devices.py",
    "src/polaris/pdk/foundry_devices.py": "modules/pdk/src/polaris_pdk/devices.py",
    "src/polaris/pdk/foundry_platforms.py": "modules/pdk/src/polaris_pdk/catalog.py",
    "src/polaris/pdk/gdsfactory_integration.py": "modules/pdk_advanced/src/polaris_pdk_advanced/gdsfactory_bridge.py",
    "src/polaris/pdk/gdsfactory_pdk_bridge.py": "modules/pdk_advanced/src/polaris_pdk_advanced/gdsfactory_bridge.py",
    "src/polaris/pdk/layer_map.py": "modules/verify_advanced/src/polaris_verify_advanced/_layer_map.py",
    "src/polaris/pdk/process_nodes.py": "modules/core/src/polaris_core/specs.py",
    "src/polaris/pdk/siepic_mapping.py": "modules/flow/src/polaris_flow/pdk_device_sampler.py",
    "src/polaris/sim/adjoint/fdtd_adjoint.py": "modules/inverse/src/polaris_inverse/fdtd_jax.py",
    "src/polaris/sim/adjoint/drc_penalty.py": "modules/optimizer/src/polaris_optimizer/density_adjoint.py",
    "src/polaris/sim/adjoint_optimizer.py": "modules/inverse/src/polaris_inverse/adjoint.py",
    "src/polaris/sim/ai_inverse_design.py": "modules/flow/src/polaris_flow/inverse_design.py",
    "src/polaris/sim/autodiff.py": "modules/inverse/src/polaris_inverse/adjoint.py",
    "src/polaris/sim/constraint_checker.py": "modules/flow/src/polaris_flow/stage_verification.py",
    "src/polaris/sim/constraint_types.py": "modules/flow/src/polaris_flow/stage_verification.py",
    "src/polaris/sim/eme_solver.py": "modules/eme/src/polaris_eme/solver.py",
    "src/polaris/sim/fde_grid.py": "modules/fde/src/polaris_fde/solver.py",
    "src/polaris/sim/fde_pml.py": "modules/fde/src/polaris_fde/solver.py",
    "src/polaris/sim/fde_solver.py": "modules/fde/src/polaris_fde/solver.py",
    "src/polaris/sim/fdfd_solver.py": "modules/fdfd/src/polaris_fdfd/solver.py",
    "src/polaris/sim/fdtd_simulator.py": "modules/fdtd/src/polaris_fdtd/solver.py",
    "src/polaris/sim/foundry_runsets.py": "modules/flow/src/polaris_flow/stage_verification.py",
    "src/polaris/sim/interconnect.py": "modules/circuit/src/polaris_circuit/time_domain_circuit.py",
    "src/polaris/sim/jax_backend.py": "modules/circuit/src/polaris_circuit/backend_selector.py",
    "src/polaris/sim/layout_aware.py": "modules/verify_advanced/src/polaris_verify_advanced/calibre_interface.py",
    "src/polaris/sim/lbfgs_optimizer.py": "modules/optimizer/src/polaris_optimizer/lbfgs.py",
    "src/polaris/sim/level_set_solver.py": "modules/inverse/src/polaris_inverse/level_set.py",
    "src/polaris/sim/lumerical_integration.py": "modules/lumerical/src/polaris_lumerical/_lumerical.py",
    "src/polaris/sim/lvs.py": "modules/lvs/src/polaris_lvs/compare.py",
    "src/polaris/sim/multi_objective_optimizer.py": "modules/optimizer/src/polaris_optimizer/nsga.py",
    "src/polaris/sim/quantum_photonics.py": "modules/boson/src/polaris_boson/hom.py",
    "src/polaris/sim/siepic_netlist.py": "modules/flow/src/polaris_flow/pdk_device_sampler.py",
    "src/polaris/sim/subnetwork_decomp.py": "modules/circuit/src/polaris_circuit/cascade.py",
    "src/polaris/sim/topology_optimizer.py": "modules/optimizer/src/polaris_optimizer/topology.py",
    "src/polaris/sim/touchstone.py": "modules/parasitic/src/polaris_parasitic/sparam.py",
    "src/polaris/sim/varfdtd_solver.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/solver.py",
    "src/polaris/sim/verilog_a.py": "modules/parasitic/src/polaris_parasitic/verilog_a_models.py",
    "src/polaris/sim/multiphysics/eo_coupling.py": "modules/multiphysics/src/polaris_multiphysics/coupling/electro_optic.py",
    "src/polaris/sim/multiphysics/modulator_solver.py": "modules/multiphysics/src/polaris_multiphysics/coupling/electro_optic.py",
    "src/polaris/sim/multiphysics/co_simulation.py": "modules/multiphysics/src/polaris_multiphysics/coupling/electro_optic.py",
    "src/polaris/sim/thermo_optic/feedback.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/thermo_optic/cocorullo.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/thermo_optic/compact_model.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/thermo_optic/crosstalk.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/thermo_optic/decay_model.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/thermo_optic/api.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/heat/api.py": "modules/multiphysics/src/polaris_multiphysics/heat/solver.py",
    "src/polaris/sim/heat/assembly.py": "modules/multiphysics/src/polaris_multiphysics/heat/solver.py",
    "src/polaris/sim/heat/mesh.py": "modules/multiphysics/src/polaris_multiphysics/heat/solver.py",
    "src/polaris/sim/heat/radiation.py": "modules/multiphysics/src/polaris_multiphysics/heat/solver.py",
    "src/polaris/sim/heat/boundary.py": "modules/multiphysics/src/polaris_multiphysics/heat/boundary.py",
    "src/polaris/sim/heat/coupling.py": "modules/multiphysics/src/polaris_multiphysics/heat/coupling.py",
    "src/polaris/sim/heat/transient.py": "modules/multiphysics/src/polaris_multiphysics/heat/transient.py",
    "src/polaris/sim/heat/thermo_optic.py": "modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py",
    "src/polaris/sim/rcwa/api.py": "modules/multiphysics/src/polaris_multiphysics/rcwa/__init__.py",
    "src/polaris/sim/fdtd/cpml.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/cpml.py",
    "src/polaris/sim/fdtd/sources.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/sources.py",
    "src/polaris/sim/fdtd/yee_grid.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/yee_grid.py",
    "src/polaris/sim/fdtd/monitors.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/monitor.py",
    "src/polaris/sim/fdtd/boundary.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/cpml.py",
    "src/polaris/sim/fdtd/conformal.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/solver.py",
    "src/polaris/sim/fdtd/leapfrog.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/yee_2d.py",
    "src/polaris/sim/fdtd/materials.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/solver.py",
    "src/polaris/sim/fdtd/postprocess.py": "modules/multiphysics/src/polaris_multiphysics/varfdtd/monitor.py",
    "src/polaris/sim/ddm/solver_1d.py": "modules/multiphysics/src/polaris_multiphysics/ddm/solver.py",
    "src/polaris/sim/ddm/solver_2d.py": "modules/multiphysics/src/polaris_multiphysics/ddm/solver.py",
    "src/polaris/sim/ddm/transient.py": "modules/multiphysics/src/polaris_multiphysics/ddm/solver.py",
    "src/polaris/trainer/bc.py": "modules/trainer/src/polaris_trainer/pretrain.py",
    "src/polaris/trainer/ppo_agent_discrete.py": "modules/trainer/src/polaris_trainer/ppo.py",
    "src/polaris/trainer/ppo_buffers.py": "modules/trainer/src/polaris_trainer/ppo.py",
    "src/polaris/trainer/ppo_networks.py": "modules/trainer/src/polaris_trainer/ppo.py",
    "src/polaris/trainer/ppo_torch.py": "modules/trainer/src/polaris_trainer/ppo.py",
    "src/polaris/web/server.py": "modules/gui/src/polaris_gui/web_server.py",
}

# ============ v5.0 已移除（诚实标注，不映射假路径） ============
REMOVED: dict[str, str] = {
    "src/polaris/engine/floorplan_env.py": "RL 环境并入训练流水线",
    "src/polaris/pdk/vpi_pdk.py": "VPI PDK 桥接未迁移",
    "src/polaris/pdk/gpic.py": "GPIC PDK 未迁移",
    "src/polaris/trainer/reward_shaping.py": "奖励整形未迁移",
    "src/polaris/sim/caphe_time_domain.py": "CAPHE 后端未迁移（时域仿真见 modules/circuit/src/polaris_circuit/time_domain_circuit.py）",
    "src/polaris/pdk/sin/passive.py": "SiN 无源器件库未迁移（热光系数见 modules/multiphysics/src/polaris_multiphysics/coupling/thermo_optic.py）",
    "src/polaris/pdk/soi/heater_pcell.py": "加热器 PCell 未迁移",
    "src/polaris/sim/adjoint/fdfd_adjoint.py": "FDFD adjoint 未迁移（adjoint 见 modules/inverse/src/polaris_inverse/adjoint.py）",
    "src/polaris/eval/gds_xor.py": "GDS XOR 已由 modules/gds_tools/src/polaris_gds_tools/gdsii_diff_tool.py 实现",
    "src/polaris/pdk/layer_remapper.py": "工艺迁移层映像未迁移",
}

# ============ 目录级映射（尾部带 /，按长度降序替换避免前缀冲突） ============
DIR_MAP: dict[str, str] = {
    "src/polaris/sim/thermo_optic/": "modules/multiphysics/src/polaris_multiphysics/coupling/",
    "src/polaris/sim/multiphysics/": "modules/multiphysics/src/polaris_multiphysics/coupling/",
    "src/polaris/sim/rcwa/": "modules/multiphysics/src/polaris_multiphysics/rcwa/",
    "src/polaris/sim/varfdtd/": "modules/multiphysics/src/polaris_multiphysics/varfdtd/",
    "src/polaris/sim/heat/": "modules/multiphysics/src/polaris_multiphysics/heat/",
    "src/polaris/sim/ddm/": "modules/multiphysics/src/polaris_multiphysics/ddm/",
    "src/polaris/sim/fdtd/": "modules/multiphysics/src/polaris_multiphysics/varfdtd/",
    "src/polaris/sim/adjoint/": "modules/inverse/src/polaris_inverse/",
    "src/polaris/sim/fde/": "modules/fde/src/polaris_fde/",
    "src/polaris/sim/fdfd/": "modules/fdfd/src/polaris_fdfd/",
    "src/polaris/sim/eme/": "modules/eme/src/polaris_eme/",
    "src/polaris/sim/bpm/": "modules/bpm/src/polaris_bpm/",
    "src/polaris/multiphysics/": "modules/multiphysics/src/polaris_multiphysics/",
    "src/polaris/quantum/": "modules/quantum_advanced/src/polaris_quantum_advanced/",
    "src/polaris/layout/drc/": "modules/drc/src/polaris_drc/",
    "src/polaris/pdk/soi/": "modules/pdk_advanced/src/polaris_pdk_advanced/",
    "src/polaris/pdk/sin/": "modules/pdk/src/polaris_pdk/",
    "src/polaris/eval/gui/": "modules/gui/src/polaris_gui/",
    "src/polaris/engine/": "modules/place/src/polaris_place/",
    "src/polaris/router/": "modules/router_advanced/src/polaris_router_advanced/",
    "src/polaris/trainer/": "modules/trainer/src/polaris_trainer/",
    "src/polaris/pipeline/": "modules/orchestrator/src/polaris_orchestrator/",
    "src/polaris/data/": "modules/nn/src/polaris_nn/data/",
    "src/polaris/eval/": "modules/gds_tools/src/polaris_gds_tools/",
    "src/polaris/layout/": "modules/gds_tools/src/polaris_gds_tools/",
    "src/polaris/pdk/": "modules/pdk/src/polaris_pdk/",
    "src/polaris/web/": "modules/gui/src/polaris_gui/",
    "src/polaris/gui/": "modules/gui/src/polaris_gui/",
    "src/polaris/viz/": "modules/gds_tools/src/polaris_gds_tools/",
    "src/polaris/api/": "modules/orchestrator/src/polaris_orchestrator/",
    "src/polaris/ai/": "modules/place/src/polaris_place/",
}

# 行号正则: .py:123 或 .py:123-178
LINENO_RE = re.compile(r"(\.py):\d+(?:-\d+)?")

stats = {"file": 0, "removed": 0, "dir": 0, "lineno": 0}
changed_files: list[str] = []

# 按 key 长度降序，确保最长前缀优先
file_items = sorted(FILE_MAP.items(), key=lambda kv: -len(kv[0]))
removed_items = sorted(REMOVED.items(), key=lambda kv: -len(kv[0]))
dir_items = sorted(DIR_MAP.items(), key=lambda kv: -len(kv[0]))

for md in sorted(DOCS.glob("*.md")):
    text = md.read_text(encoding="utf-8")
    orig = text
    # 1. 已移除（先做，避免被目录映射吞掉）
    for old, reason in removed_items:
        if old in text:
            text = text.replace(old, f"v5.0 已移除（原 `{old}`，{reason}）")
            stats["removed"] += 1
    # 2. 文件级映射
    for old, new in file_items:
        if old in text:
            text = text.replace(old, new)
            stats["file"] += 1
    # 3. 目录级映射
    for old, new in dir_items:
        if old in text:
            text = text.replace(old, new)
            stats["dir"] += 1
    # 4. 去行号（仅 modules/ 路径上的 .py:NN）
    def _strip(m: re.Match) -> str:
        stats["lineno"] += 1
        return m.group(1)
    text = LINENO_RE.sub(_strip, text)
    if text != orig:
        md.write_text(text, encoding="utf-8")
        changed_files.append(md.name)

print(f"修改文件数: {len(changed_files)}")
print(f"文件级替换: {stats['file']}  目录级替换: {stats['dir']}  已移除标注: {stats['removed']}  去行号: {stats['lineno']}")
print("修改的文件:")
for f in changed_files:
    print(f"  {f}")
