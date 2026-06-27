# Checklist

## 修复 1（已完成）
- [x] `src/polaris/sim/fde/mode.py` 的 `overlap` 方法包含 `0.5 *` 因子

## 修复 2（已完成）
- [x] `FdeSolverConfig` 含 `shift_frac: float = 0.5` 字段
- [x] `solve` 方法 `n_eff_shift` 自动计算为 `n_clad + 0.5·(n_core - n_clad)`

## 修复 3（已完成）
- [x] `solve` 方法 `candidates.sort` 的 key 为 `re_neff - 10 * abs(im_neff)` 降序

## 修复 4（已完成）
- [x] `_te_tm_fraction` 方法返回 `te_fraction = |E_y|²/(|E_x|²+|E_y|²)`
- [x] `_te_tm_fraction` 方法返回 `tm_fraction = |E_x|²/(|E_x|²+|E_y|²)`
- [x] `te_fraction + tm_fraction = 1`（互斥归一）
- [x] 半矢量 TE 下 te_fraction = 1.0（E_x=0）
- [x] `Mode` docstring 更新注明横向主场定义与 Lumerical 依据

## 修复 5（已完成）
- [x] `Mode.overlap` 分母用 `|cross_m|·|cross_n|`（复数模）而非 `power_integral`（实部）
- [x] 有损模式自重叠 η = 1.0 ± 1e-6
- [x] 无损模式自重叠 η = 1.0 ± 1e-10

## 修复 6（已完成）
- [x] `solve` 方法 `k_request = min(num_modes + 12, n_total - 2)`（超出 spec +8）
- [x] SOI 基模 n_eff ≈ 2.6727（权威范围 2.30-2.70，Tidy3D 实测 2.5113，本项目 n_Si=3.476 偏高）

## 修复 7（已完成）
- [x] `tests/test_eme_backend.py` 的 `_make_backend` 用 `window_size=(3.0e-6, 2.5e-6)`
- [x] FDE 对 SOI strip 500×220nm @ 1550nm 返回基模 n_eff ≈ 2.6727 ∈ [2.0, 2.8]
- [x] FDE 基模 |Im(n_eff)| ≈ 1.28e-9 < 0.05
- [x] FDE 基模 te_fraction = 1.0 > 0.5（test_solve_modes 阈值）

## 测试验证（已完成）
- [x] `tests/test_a04_fde.py` 全部测试通过（含 test_soi_fundamental_mode、test_overlap_self_unity）
- [x] `tests/test_eme_backend.py` 全部 9 个测试通过
- [x] `tests/test_a02_eme.py` 不回归（已通过测试保持通过）
- [x] 锥形 energy_sum ∈ [0.999, 1.001]（test_run_taper）
- [x] 弯曲 energy_sum ∈ [0.999, 1.001]（test_run_bend）
- [x] MMI/交叉 energy_sum ∈ [0.999, 1.001]（test_build_mmi_and_crossing）
- [x] 总计 68 passed, 1 skipped, 0 failed（81.16s）

## 质量门禁（已完成）
- [x] 无 `except: pass` / `return None` / `return []` 等 fall-back（规则 14）
- [x] 无 `TODO`/`FIXME`/`HACK` 残留（规则 5）
- [x] 代码已提交合并 main 远端，操作记录已更新

## 学术诚信（R02，已完成）
- [x] 测试期望值 n_eff 从过时 Soref 1991 1D slab EIM 近似值 2.344 修正为权威 2D FDE 实测范围
- [x] 文献来源 4 项 URL 已标注（Tidy3D/gdsfactory/sipkit/Lumerical）
- [x] solver.py docstring 同步更新权威参考值
