# PyInstaller spec — PoLaRIS v6.0 单文件可执行打包配置
#
# 将 PoLaRIS 打包为单文件可执行程序，包含所有 Python 运行时 + 编译后的 .so 模块。
# 源代码通过 Cython 预编译为 .so，PyInstaller 打包时不包含 .py 源文件。
#
# 来源（R02 学术诚信）:
# - PyInstaller 官方文档: https://pyinstaller.org/en/stable/
# - PyInstaller spec 文件: https://pyinstaller.org/en/stable/spec-files.html
# - 单文件模式: https://pyinstaller.org/en/stable/usage.html#onefile
# - hiddenimports: https://pyinstaller.org/en/stable/when-things-go-wrong.html
# - Cython+PyInstaller 集成: https://github.com/pyinstaller/pyinstaller/issues/4457
#
# 使用方式:
#   pyinstaller polaris_release.spec
#
# 产物: dist/polaris (Linux 单文件可执行)

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
ROOT = Path(SPECPATH).resolve()
# Cython 编译后的副本目录（见 scripts/compile_cython.py）
# build/release/modules/ 中 .py 已替换为 stub，.so 为实际逻辑
MODULES = ROOT / "build" / "release" / "modules"

if not MODULES.exists():
    raise RuntimeError(
        f"Cython 编译副本不存在: {MODULES}\n"
        f"请先运行: python3 scripts/compile_cython.py"
    )

# 收集所有 polaris_* 模块的 hiddenimports
hiddenimports = [
    "polaris_orchestrator",
    "polaris_orchestrator.cli",
    "polaris_orchestrator.flow",
    "polaris_core",
    "polaris_core.specs",
    "polaris_core.device_solver",
    "polaris_circuit",
    "polaris_circuit.cascade",
    "polaris_circuit.models",
    "polaris_circuit.simulator",
    "polaris_circuit.link_budget",
    "polaris_circuit.subnetwork",
    "polaris_circuit.backend_selector",
    "polaris_circuit.system_level",
    "polaris_circuit.mna_spice",
    "polaris_circuit.time_domain_circuit",
    "polaris_place",
    "polaris_place.analytical",
    "polaris_place.ppo_gnn",
    "polaris_place.legalize",
    "polaris_place.metrics",
    "polaris_route",
    "polaris_route.curvy",
    "polaris_router_advanced",
    "polaris_router_advanced.global_router",
    "polaris_router_advanced.curvy_astar_core",
    "polaris_drc",
    "polaris_drc.rules",
    "polaris_drc.engine",
    "polaris_drc.pdk_rulesets",
    "polaris_lvs",
    "polaris_lvs.compare",
    "polaris_inverse",
    "polaris_inverse.adjoint",
    "polaris_inverse.level_set",
    "polaris_optimizer",
    "polaris_optimizer.topology",
    "polaris_optimizer.global_opt",
    "polaris_optimizer.lbfgs",
    "polaris_optimizer.nsga",
    "polaris_optimizer.robust",
    "polaris_optimizer.level_set",
    "polaris_optimizer.shape_adjoint",
    "polaris_fdtd",
    "polaris_fdtd.solver",
    "polaris_fdtd.waveguide",
    "polaris_fde",
    "polaris_fde.solver",
    "polaris_eme",
    "polaris_eme.solver",
    "polaris_eme.eme_2d",
    "polaris_bpm",
    "polaris_bpm.solver",
    "polaris_boson",
    "polaris_boson.hom",
    "polaris_boson.clements",
    "polaris_boson.permanent",
    "polaris_klm",
    "polaris_klm.gates",
    "polaris_quantum_advanced",
    "polaris_quantum_advanced.permanent",
    "polaris_quantum_advanced.boson_sampling",
    "polaris_quantum_advanced.gbs",
    "polaris_quantum_advanced.lossy",
    "polaris_quantum_advanced.numerical",
    "polaris_nn",
    "polaris_nn.data.benchmark_evaluator",
    "polaris_nn.data.tilos_benchmark",
    "polaris_nn.data.apollo_benchmark",
    "polaris_nn.data.lidar_benchmark",
    "polaris_nn.data.data_loader",
    "polaris_nn.data.dataset_generator",
    "polaris_nn.data.variant_generator",
    "polaris_nn.data.expert_layout",
    "polaris_nn.data.gds_loader",
    "polaris_pdk",
    "polaris_pdk.filters",
    "polaris_pdk.catalog",
    "polaris_pdk.devices",
    "polaris_pdk_advanced",
    "polaris_pdk_advanced.gdsfactory_bridge",
    "polaris_pdk_advanced.pdk_model_params",
    "polaris_gds_tools",
    "polaris_gds_tools.layout_render",
    "polaris_gdsio",
    "polaris_gdsio.exporter",
    "polaris_sparam",
    "polaris_pam4",
    "polaris_pam4.signal",
    "polaris_lumerical",
    "polaris_lumerical._cml",
    "polaris_lumerical._cml_fit",
    "polaris_lumerical._backends",
    "polaris_lumerical._cosim",
    "polaris_parasitic",
    "polaris_parasitic.verilog_a_models",
    "polaris_parasitic.verilog_a_spice",
    "polaris_parasitic.verilog_a_differentiable",
    "polaris_multiphysics",
    "polaris_multiphysics.coupling",
    "polaris_multiphysics.rcwa",
    "polaris_multiphysics.varfdtd",
    "polaris_yield",
    "polaris_yield.monte_carlo",
    "polaris_trainer",
    "polaris_trainer.ppo",
    "polaris_trainer.pretrain",
    "polaris_trainer.transfer_learning",
    "polaris_trainer.distributed_rollout",
    "polaris_trainer.checkpoint",
    "polaris_verify_advanced",
    "polaris_verify_advanced.klayout_drc",
    "polaris_verify_advanced.eqdrc",
    "polaris_verify_advanced.lvs_advanced",
    "polaris_verify_advanced.lvs_advanced_types",
    "polaris_gui",
    "polaris_gui.layout_editor",
    "polaris_gui.web_server",
    "polaris_gui.routes",
    "polaris_flow",
    "polaris_flow.curvy_router",
    "polaris_flow.default_simulator",
    "polaris_flow.inverse_design",
    "polaris_flow.stage_input",
    "polaris_flow.stage_verification",
    "polaris_flow.stage_output",
    "polaris_flow.stage_physical",
    "polaris_flow.stage_advanced",
    "polaris_flow.stage_yield",
    "polaris_flow.executors",
    "polaris_flow.training",
    "polaris_flow.pdk_device_sampler",
    "polaris_circuit",
]

# 收集所有模块的 .so 文件作为 binaries
datas = []
binaries = []
# build/release/modules/<m>/src/polaris_<m>/*.so → 打包到 polaris_<m>/ 目录
for so_file in MODULES.rglob("*.so"):
    # 目标目录: so_file 的父目录相对于 modules/<m>/src 的相对路径
    # 例: build/release/modules/circuit/src/polaris_circuit/cascade.cpython-311-x86_64-linux-gnu.so
    #     → 打包到 polaris_circuit/ 目录
    target_dir = so_file.parent.name  # polaris_circuit
    binaries.append((str(so_file), target_dir))

# 也收集 stub .py 文件（仅 __init__.py / cli.py 等保留的入口）
for py_file in MODULES.rglob("*.py"):
    target_dir = py_file.parent.name
    datas.append((str(py_file), target_dir))

a = Analysis(
    ["scripts/polaris_entry.py"],
    pathex=[str(ROOT), str(MODULES)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
              "IPython", "jupyter", "notebook"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="polaris",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
