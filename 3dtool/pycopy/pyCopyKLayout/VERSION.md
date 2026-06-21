# pyCopyKLayout 版本历史

复刻 KLayout 的 DRC 规则检查功能（8 种违规检查）。

## v1.0.0 (2026-06-21) — 100% 复刻完成

- 复刻内容: 8 种 DRC 规则检查
  - check_bend_radius（弯曲半径）
  - check_spacing（间距）
  - check_insertion_loss（插入损耗）
  - check_crossings（交叉）
  - check_overlap（重叠）
  - check_min_width（最小宽度）
  - check_coupling_gap（耦合间隙）
  - ConstraintChecker（统一检查器）+ ConstraintConfig + Violation + ViolationType
- 复刻位置: `src/polaris/sim/constraint_checker.py`
- 对比测试: `tests/test_replica_klayout.py` 6 个用例全部通过
  - TestSpacingCheck::test_spacing_ok / test_spacing_violation
  - TestOverlapCheck::test_no_overlap / test_overlap_detected
  - TestMinWidthCheck::test_width_ok / test_width_violation
- 行为一致性: 与 KLayout DRC 规则定义对齐
- 来源: https://www.klayout.de/ (GPL-2.0, KLayout 0.30.x DRC 引擎)
- 设计规则依据: SiEPIC EBeam PDK
- 验收: 规则 21.4 全部通过

## v2.0.x 规划（能力优化方向）

- v2.0.1: DRC 规则并行检查（多规则并发）
- v2.0.2: 增量 DRC（仅检查变更区域）
- v2.0.3: 几何算法空间索引（R-tree 加速重叠检测）
- v2.0.4: 自定义 DRC 规则脚本支持（类 KLayout Ruby DRC）
