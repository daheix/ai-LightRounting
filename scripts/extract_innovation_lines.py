"""提取 26 个待补全文件中的 *创新* 行内容，用于构建精准补遗块。"""
from __future__ import annotations

import ast
from pathlib import Path

FILES = [
    "src/polaris/pdk/awg_ip_materials.py",
    "src/polaris/pdk/gdsfactory_advanced.py",
    "src/polaris/quantum/distributed_ppo.py",
    "src/polaris/rl/rl_integration.py",
    "src/polaris/rl/rl_transformer_policy.py",
    "src/polaris/router/curvy_geometry.py",
    "src/polaris/router/global_router.py",
    "src/polaris/router/obstacle_grid.py",
    "src/polaris/sim/ddm/__init__.py",
    "src/polaris/sim/eme_backend.py",
    "src/polaris/sim/multiphysics/__init__.py",
    "src/polaris/sim/multiphysics/electro_optic.py",
    "src/polaris/sim/perf_optimization_eme.py",
    "src/polaris/sim/perf_optimization_fde.py",
    "src/polaris/sim/perf_optimization_fdtd.py",
    "src/polaris/sim/quantum_cv_qec.py",
    "src/polaris/sim/quantum_cv_qec_cv.py",
    "src/polaris/sim/quantum_cv_qec_noise.py",
    "src/polaris/sim/quantum_cv_qec_qec.py",
    "src/polaris/sim/quantum_klm.py",
    "src/polaris/sim/quantum_lossy.py",
    "src/polaris/sim/quantum_photonics.py",
    "src/polaris/sim/simulator.py",
    "src/polaris/trainer/reward_shaping.py",
    "src/polaris/verification/_drc_geometry.py",
    "src/polaris/verification/yield_advanced.py",
]

for fp in FILES:
    p = Path(fp)
    content = p.read_text(encoding="utf-8")
    print(f"\n=== {fp} ===")
    # 提取 docstring 摘要（首行）
    try:
        tree = ast.parse(content)
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
            ds = tree.body[0].value.value
            first_line = ds.split('\n', 1)[0][:120]
            print(f"doc: {first_line}")
    except SyntaxError as e:
        print(f"SYNTAX FAIL: {e}")
    # 提取 *创新* 行
    for i, line in enumerate(content.splitlines(), 1):
        if "*创新*" in line:
            print(f"  L{i}: {line.strip()[:200]}")
