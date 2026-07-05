# Checklist

## DENSITY_MIN 规则描述同步
- [ ] `modules/drc/src/polaris_drc/rules.py` DENSITY_MIN 规则 description 已移除
      "XXL=0.0001%, XXXL=0.00001%"，改为 "≥10mm 连续缩放
      threshold=100μm²/canvas_area×100"
- [ ] `modules/drc/src/polaris_drc/engine.py` 模块 docstring DENSITY_MIN 行已同步
- [ ] `modules/drc/src/polaris_drc/checks.py` `density_min_threshold_by_canvas`
      docstring 连续缩放说明清晰

## DRC 单元测试更新
- [ ] `test_density_min_xxl_threshold` 期望值已更新为连续缩放结果
      （50000×50000 → 4e-6%）
- [ ] `test_density_min_xxxl_threshold` 期望值已更新为连续缩放结果
      （200000×200000 → 2.5e-7%），移除边界离散值断言
- [ ] PORT_FACING 4 个测试（correct/wrong/bend_compensate_default/
      perpendicular_bend）全部通过

## DRC 全量单元测试验证
- [ ] `python -m pytest modules/drc/tests/ -x` 全绿（47+ 个 pytest）
- [ ] 无 TODO/FIXME/HACK 残留（R05）
- [ ] 无 fall-back 残留（R03）

## expert_demos DRC 通过率验证
- [ ] MZI1 DRC 通过（原 DENSITY_MIN 失败已修复）
- [ ] RingResonator DRC 通过
- [ ] Ring_series DRC 通过
- [ ] mzi_adjustable_splitter DRC 通过
- [ ] expert_demos DRC 通过率 ≥ 80%（目标 10/10 = 100%）

## 70 个真实板子抽样 DRC 通过率验证
- [ ] DRC 通过率 ≥ 50%（从 37.1% 提升）
- [ ] 剩余失败用例根因已记录

## 代码提交与操作记录
- [ ] `git add` 精确文件（非 git add -A）
- [ ] `git commit` 含详细中文 commit message
- [ ] `git push origin main` 成功（无 --force）
- [ ] `操作记录.md` 已追加本轮记录（轮次编号、交付文件、测试结果、规则依据）
- [ ] 所有阈值有文献来源（R02 学术诚信）
- [ ] bend_compensate 标注 *创新* 并记录底层逻辑
- [ ] DENSITY_MIN 连续缩放标注 *创新* 并记录底层逻辑
