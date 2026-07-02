"""PoLaRIS v5.0 18 子模块完整端到端流水线（输入 → 处理 → 产出）。

本脚本显式调用全部 18 个子模块，展示新架构下从电路构建到 GDSII 产物的完整过程。
每个子模块按 IPO（Input/Process/Output）三段式标注，便于对照学习。

## 流水线总览（18 子模块全部被调用）

```
[输入]
  1. polaris_core      构建电路 + 校验
  2. polaris_pdk       查询 PDK 平台目录

[处理 - 物理设计]
  3. polaris_place     AI 布局（analytical 解析法）
  4. polaris_route     智能布线（curvy 曲线波导）

[处理 - 7 个仿真子模块全部调用]
  5. polaris_sparam    频域 S 参数（MZI 谐振 + Clements 酉矩阵）
  6. polaris_pam4      PAM4 信号（眼图/BER/SNR）
  7. polaris_fdtd      时域有限差分（3D Yee + PML 全波仿真）
  8. polaris_fde       频域本征模（2D FD 模式求解 → neff + 模场）
  9. polaris_eme       本征模展开（锥形波导模式匹配 + Redheffer 星积）
 10. polaris_bpm       光束传播法（Crank-Nicolson 隐式步进）
 11. polaris_fdfd      频域有限差分（Helmholtz 稀疏求解稳态场）

[处理 - 验证]
 12. polaris_drc       DRC 设计规则检查（12 条 SiEPIC PDK 规则）
 13. polaris_lvs       LVS 网表一致性比对

[处理 - 逆向与量子]
 14. polaris_inverse   逆向设计（JAX jax.grad 自动微分）
 15. polaris_boson     玻色采样（Glynn-Gray permanent + HOM 干涉）
 16. polaris_klm       KLM 线性光学量子门（Ralph 2002 CNOT）

[产出]
 17. polaris_gdsio     GDSII 导出（klayout.db 后端）
 18. polaris_orchestrator  编排层一键复核（9 stage）
```

## 运行

    python examples/full_pipeline_18modules/main.py

## 设计原则
- R03 禁止 fall-back: 任何子模块失败即 raise
- R04 不参与 GPU: 纯 NumPy/SciPy/JAX(CPU)
- R02 学术诚信: 所有参数可溯源

来源（R02 学术诚信，≥5 个文献 URL）:
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref 1993 IEEE JQE（SOI 材料参数）https://ieeexplore.ieee.org/document/1148303
- Yee 1966 IEEE TAP（FDTD）https://doi.org/10.1109/TAP.1966.1138693
- Clements et al., Optica 3(12), 1460 (2016) https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Ralph et al. 2002（KLM CNOT）https://doi.org/10.1103/PhysRevA.65.012324
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# 添加全部 18 子模块到 sys.path
ROOT = Path(__file__).resolve().parents[2]
for m in (
    "core", "pdk", "place", "route",
    "drc", "lvs", "gdsio",
    "sparam", "pam4", "fdtd", "fde", "eme", "bpm", "fdfd",
    "inverse", "boson", "klm",
    "orchestrator",
):
    sys.path.insert(0, str(ROOT / f"modules/{m}/src"))

from polaris_core import make_circuit, make_device, validate_circuit
from polaris_pdk import list_platforms
from polaris_place import place_circuit
from polaris_route import route_circuit
from polaris_sparam import simulate_mzi_sparam, compute_clements_unitary
from polaris_pam4 import simulate_pam4
from polaris_fdtd import simulate_waveguide_fdtd
from polaris_fde import solve_modes
from polaris_eme import solve_eme
from polaris_bpm import solve_bpm
from polaris_fdfd import solve_fdfd
from polaris_drc import run_drc
from polaris_lvs import run_lvs
from polaris_inverse import optimize_waveguide_width
from polaris_boson import boson_sampling, clements_unitary, hom_interference
from polaris_klm import klm_cnot
from polaris_gdsio import export_gds
from polaris_orchestrator import run_eda_flow

OUTPUT_DIR = str(ROOT / "out" / "full_pipeline_18modules")

# SiEPIC EBeam PDK 220nm SOI 材料参数（Soref 1993 @1.55μm）
N_SI = 3.476   # 硅折射率
N_SIO2 = 1.444  # 二氧化硅折射率


def _print_header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _print_step(idx: int, total: int, module: str, desc: str) -> None:
    print(f"\n[{idx}/{total}] polaris_{module}: {desc}")


# =============================================================================
# [输入阶段] 构建电路 + PDK 查询
# =============================================================================
def build_circuit() -> dict:
    """构建 5 器件 MZI 调制器电路（对标 Intel 100G CWDM4 MZM）。

    电路拓扑:
        [GC1] → [MMI1] → [PS1] → [MMI2] → [GC2]
                         ↘──────────────↗
    """
    gc1 = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        params={"insertion_loss_db": 1.9, "peak_wavelength_nm": 1550.0},
    )
    mmi1 = make_device(
        "mmi1", "mmi_1x2", 30, 20,
        ports=[("in", 0, 10, "west"),
               ("out1", 30, 5, "east"), ("out2", 30, 15, "east")],
        params={"insertion_loss_db": 0.4, "split_ratio": 0.48},
    )
    ps1 = make_device(
        "ps1", "phase_shifter", 100, 10,
        ports=[("in", 0, 5, "west"), ("out", 100, 5, "east")],
        params={"neff": 2.4, "pi_voltage": 3.0, "length_um": 100.0},
    )
    mmi2 = make_device(
        "mmi2", "mmi_2x2", 30, 20,
        ports=[("in1", 0, 5, "west"), ("in2", 0, 15, "west"),
               ("out1", 30, 10, "east"), ("out2", 30, 10, "east")],
        params={"insertion_loss_db": 0.5},
    )
    gc2 = make_device(
        "gc2", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        params={"insertion_loss_db": 1.9, "peak_wavelength_nm": 1550.0},
    )
    connections = [
        ["gc1", "out", "mmi1", "in"],
        ["mmi1", "out1", "ps1", "in"],
        ["ps1", "out", "mmi2", "in1"],
        ["mmi1", "out2", "mmi2", "in2"],
        ["mmi2", "out1", "gc2", "in"],
    ]
    return make_circuit(
        "MZI_100G", [gc1, mmi1, ps1, mmi2, gc2], connections,
        canvas_w=500, canvas_h=300,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
    )


# =============================================================================
# 主流水线：18 子模块全调用
# =============================================================================
def run_full_pipeline() -> None:
    """运行 18 子模块完整端到端流水线。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t_total = time.perf_counter()

    _print_header("PoLaRIS v5.0 18 子模块完整端到端流水线")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  材料: SiEPIC EBeam PDK 220nm SOI, λ=1550nm")
    print(f"  电路: 5 器件 MZI 调制器 (GC1→MMI1→PS1→MMI2→GC2)")

    # ---- [输入] 1. polaris_core: 电路构建与校验 ----
    _print_step(1, 18, "core", "电路构建与校验")
    circuit = build_circuit()
    ok = validate_circuit(circuit)
    print(f"  ✓ 电路 {circuit['name']}: {len(circuit['devices'])} 器件, "
          f"{len(circuit['connections'])} 连接, "
          f"画布 {circuit['canvas_w']}×{circuit['canvas_h']}μm")
    print(f"  ✓ validate_circuit → {ok}")

    # ---- [输入] 2. polaris_pdk: PDK 平台目录 ----
    _print_step(2, 18, "pdk", "PDK 平台目录查询")
    platforms = list_platforms()
    print(f"  ✓ 共 {len(platforms)} 个 PDK 平台:")
    for p in platforms:
        print(f"    - {p['platform']:5s} ({p['foundry']:14s}, "
              f"{p['device_count']} 器件)")

    # ---- [处理] 3. polaris_place: AI 布局 ----
    _print_step(3, 18, "place", "AI 布局（analytical 解析法）")
    placement = place_circuit(circuit, mode="analytical")
    print(f"  ✓ HPWL = {placement['hpwl']:.2f} μm  "
          f"mode={placement['placement_mode']}")
    for name, pl in placement["placements"].items():
        print(f"    {name:5s} x={pl['x']:7.2f} y={pl['y']:7.2f} "
              f"w={pl['w']:6.1f} h={pl['h']:6.1f}")

    # ---- [处理] 4. polaris_route: 智能布线 ----
    _print_step(4, 18, "route", "智能布线（curvy 曲线波导）")
    routing = route_circuit(circuit, placement["placements"], mode="curvy")
    print(f"  ✓ 总损耗 = {routing['total_loss_db']:.3f} dB  "
          f"n_paths={len(routing['paths'])}  "
          f"n_bends={routing['n_bends']}  n_crossings={routing['n_crossings']}")

    # ---- [处理] 5. polaris_sparam: 频域 S 参数 ----
    _print_step(5, 18, "sparam", "频域 S 参数（MZI 谐振 + Clements 酉矩阵）")
    mzi = simulate_mzi_sparam()
    print(f"  ✓ MZI 谐振陷波波长 = {mzi['resonant_wavelength_nm']:.2f} nm")
    print(f"    理论消光比 = {mzi['extinction_ratio_db']:.2f} dB, "
          f"实际消光比 = {mzi['extinction_ratio_physical_db']:.2f} dB")
    clements = compute_clements_unitary(n_modes=4)
    print(f"  ✓ Clements 4×4 酉矩阵: is_unitary={clements['is_unitary']}, "
          f"酉性误差={clements['unitarity_error']:.2e}")

    # ---- [处理] 6. polaris_pam4: PAM4 信号仿真 ----
    _print_step(6, 18, "pam4", "PAM4 信号仿真（眼图/BER/SNR）")
    pam4 = simulate_pam4(n_symbols=1000, bit_rate_gbps=100)
    print(f"  ✓ PAM4 ({pam4['n_symbols']} 符号 @ {pam4['bit_rate_gbps']:.0f}Gbps):")
    print(f"    BER = {pam4['ber']:.2e}  SNR = {pam4['snr_db']:.2f} dB")

    # ---- [处理] 7. polaris_fdtd: 时域有限差分 ----
    _print_step(7, 18, "fdtd", "时域有限差分（3D Yee + PML 全波仿真）")
    fdtd = simulate_waveguide_fdtd(dx_um=0.1, n_steps=200)
    print(f"  ✓ FDTD 波导仿真 (dx={fdtd['dx_um']}μm, n_steps={fdtd['n_steps']}):")
    print(f"    T_fdtd = {fdtd['T_fdtd']:.6f}, "
          f"transmission = {fdtd['transmission_db']:.4f} dB, "
          f"PML = {fdtd['pml_enabled']}")

    # ---- [处理] 8. polaris_fde: 频域本征模 ----
    _print_step(8, 18, "fde", "频域本征模（2D FD 模式求解 → neff + 模场）")
    fde = solve_modes(
        width_um=0.5, height_um=0.22, wavelength_um=1.55,
        n_core=N_SI, n_clad=N_SIO2, n_modes=3,
    )
    print(f"  ✓ FDE 模式求解 ({fde['n_modes']} 个导模, "
          f"λ={fde['wavelength_um']}μm):")
    for i, mode in enumerate(fde["modes"]):
        print(f"    mode {i}: neff = {mode['neff']:.6f}")

    # ---- [处理] 9. polaris_eme: 本征模展开 ----
    _print_step(9, 18, "eme", "本征模展开（锥形波导模式匹配 + Redheffer 星积）")
    eme = solve_eme(
        sections=[
            {"width_um": 1.0, "length_um": 5.0,
             "n_core": N_SI, "n_clad": N_SIO2},
            {"width_um": 0.5, "length_um": 5.0,
             "n_core": N_SI, "n_clad": N_SIO2},
        ],
        wavelength_um=1.55,
        n_modes_per_section=2,
    )
    print(f"  ✓ EME 锥形传播 ({eme['n_sections']} 段):")
    print(f"    |T| = {abs(eme['transmission']):.6f}, "
          f"|R| = {abs(eme['reflection']):.2e}")
    for i, s in enumerate(eme["sections_info"]):
        print(f"    section {i}: w={s['width_um']}μm L={s['length_um']}μm "
              f"neff={s['neff']:.6f}")

    # ---- [处理] 10. polaris_bpm: 光束传播法 ----
    _print_step(10, 18, "bpm", "光束传播法（Crank-Nicolson 隐式步进）")
    bpm = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=N_SI, n_clad=N_SIO2,
        dz_um=0.5, dx_um=0.02, pad_um=1.0,
    )
    print(f"  ✓ BPM 光束传播 ({bpm['n_steps']} 步):")
    print(f"    transmission = {bpm['transmission_db']:.4f} dB")

    # ---- [处理] 11. polaris_fdfd: 频域有限差分 ----
    _print_step(11, 18, "fdfd", "频域有限差分（Helmholtz 稀疏求解稳态场）")
    fdfd = solve_fdfd(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=N_SI, n_clad=N_SIO2,
        dx_um=0.05, pad_um=1.0,
    )
    print(f"  ✓ FDFD 稳态场求解 (n_grid={fdfd['n_grid']}):")
    print(f"    transmission = {fdfd['transmission_db']:.4f} dB")

    # ---- [处理] 12. polaris_drc: DRC 设计规则检查 ----
    _print_step(12, 18, "drc", "DRC 设计规则检查（12 条 SiEPIC PDK 规则）")
    drc = run_drc(circuit, placement["placements"])
    print(f"  ✓ DRC: {drc['n_rules']} 条规则, "
          f"通过率 {drc['pass_rate']:.1%} ({drc['n_passed']}/{drc['n_rules']}), "
          f"违规 {drc['n_violations']} 条")

    # ---- [处理] 13. polaris_lvs: LVS 网表一致性比对 ----
    _print_step(13, 18, "lvs", "LVS 网表一致性比对")
    lvs = run_lvs(circuit)
    print(f"  ✓ LVS: is_consistent={lvs['is_consistent']}  "
          f"mismatches={lvs['n_mismatches']}  "
          f"(n_devices={lvs['n_devices']}, n_connections={lvs['n_connections']})")

    # ---- [处理] 14. polaris_inverse: 逆向设计 ----
    _print_step(14, 18, "inverse", "逆向设计（JAX jax.grad 自动微分）")
    t0 = time.perf_counter()
    inverse = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
    inv_t = time.perf_counter() - t0
    print(f"  ✓ 逆向设计 ({inv_t:.1f}s):")
    print(f"    波导宽度 {inverse['initial_width_nm']:.1f} → "
          f"{inverse['optimal_width_nm']:.1f} nm")
    print(f"    FoM 改善 = {inverse['improvement_db']:.2f} dB, "
          f"converged = {inverse['converged']}")

    # ---- [处理] 15. polaris_boson: 玻色采样 ----
    _print_step(15, 18, "boson", "玻色采样（Glynn-Gray permanent + HOM 干涉）")
    # 用 Clements 酉矩阵做 4 模玻色采样
    unitary = clements_unitary(n_modes=4, seed=42)
    bs = boson_sampling(unitary, input_state=[1, 1, 0, 0])
    hom = hom_interference(theta=0.0)
    print(f"  ✓ 玻色采样 (4 模, 输入 |1,1,0,0>):")
    print(f"    prob_sum = {bs['prob_sum']:.6f}, "
          f"n_outputs = {bs['n_outputs']}")
    print(f"  ✓ HOM 双光子干涉 (θ=0):")
    print(f"    dip_depth = {hom['dip_depth']:.2f}, "
          f"coincidence_prob = {hom['coincidence_prob']:.4f}, "
          f"verified = {hom['verified']}")

    # ---- [处理] 16. polaris_klm: KLM 量子门 ----
    _print_step(16, 18, "klm", "KLM 线性光学量子门（Ralph 2002 CNOT）")
    klm = klm_cnot()
    print(f"  ✓ KLM CNOT: success_prob = {klm['success_prob']:.6f} "
          f"(=1/9={1/9:.6f}), verified = {klm['verified']}")

    # ---- [产出] 17. polaris_gdsio: GDSII 导出 ----
    _print_step(17, 18, "gdsio", "GDSII 导出（klayout.db 后端）")
    gds_path = os.path.join(OUTPUT_DIR, "MZI_100G.gds")
    gds = export_gds(circuit, gds_path)
    print(f"  ✓ GDSII 导出: {gds['path']}")
    print(f"    文件大小 = {gds['file_size_bytes']} bytes, "
          f"结构数 = {gds['n_structures']}, "
          f"层数 = {gds['n_layers']}, "
          f"loadable = {gds['loadable']}")

    # ---- [产出] 18. polaris_orchestrator: 编排层一键复核 ----
    _print_step(18, 18, "orchestrator", "编排层一键复核（9 stage 全流程）")
    orch = run_eda_flow(circuit, OUTPUT_DIR)
    print(f"  ✓ orchestrator 9 stage: "
          f"n_success={orch['n_success']}, "
          f"n_failed={orch['n_failed']}, "
          f"n_skipped={orch['n_skipped']}, "
          f"total_duration={orch['total_duration']:.2f}s")
    for s in orch["stages"]:
        mark = "✓" if s["status"] == "success" else "✗"
        print(f"    [{mark}] stage {s['stage_id']} {s['name']:8s} "
              f"{s['status']:8s} ({s['duration']:.2f}s)")

    elapsed = time.perf_counter() - t_total
    _print_header(f"全部完成：18 子模块完整流水线，总耗时 {elapsed:.1f}s")
    print(f"  GDSII 产物: {gds_path}")
    print(f"  子模块调用: 18/18 全部成功")
    print(f"  orchestrator: {orch['n_success']}/9 stage 成功")


if __name__ == "__main__":
    run_full_pipeline()
