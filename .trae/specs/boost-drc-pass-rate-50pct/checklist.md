# Checklist

## DENSITY_MIN 规则描述同步
- [x] `modules/drc/src/polaris_drc/rules.py` DENSITY_MIN 规则 description 已移除
      "XXL=0.0001%, XXXL=0.00001%"，改为 "≥10mm 连续缩放
      threshold=100μm²/canvas_area×100"
- [x] `modules/drc/src/polaris_drc/engine.py` 模块 docstring DENSITY_MIN 行已同步
- [x] `modules/drc/src/polaris_drc/checks.py` `density_min_threshold_by_canvas`
      docstring 连续缩放说明清晰（前序已提交）

## DRC 单元测试更新
- [x] `test_density_min_xxl_threshold` 期望值已更新为连续缩放结果
      （50000×50000 → 4e-6%），使用 pytest.approx 安全比较
- [x] `test_density_min_xxxl_threshold` 期望值已更新为连续缩放结果
      （200000×200000 → 2.5e-7%），移除边界离散值断言
- [x] PORT_FACING 4 个测试（correct/wrong/bend_compensate_default/
      perpendicular_bend）全部通过

## DRC 全量单元测试验证
- [x] `python -m pytest modules/drc/tests/ -x` 全绿（55 个 pytest，0.40s）
- [x] 无 TODO/FIXME/HACK 残留（R05）
- [x] 无 fall-back 残留（R03）

## expert_demos DRC 通过率验证
- [x] MZI1 DRC 通过（原 DENSITY_MIN 失败已修复）
- [x] RingResonator DRC 通过
- [x] Ring_series DRC 通过
- [x] mzi_adjustable_splitter DRC 通过
- [x] expert_demos DRC 通过率 ≥ 80%（实测 10/10 = 100%，原 1/10 = 10%）

## 70 个真实板子抽样 DRC 通过率验证
- [x] DRC 通过率 ≥ 50%（实测 35/70 = 50.0%，原 26/70 = 37.1%）
- [x] 剩余失败用例根因已记录（siepic 0/20 + gdsfactory 12/20 +
      picbench 3/20 失败，根因为 BOUNDARY/PORT_ALIGNMENT/NO_OVERLAP）

## 代码提交与操作记录
- [x] `git add` 精确文件（7 个文件，非 git add -A）
- [x] `git commit` 含详细中文 commit message（commit 05b1d414）
- [x] `git push origin main` 成功（无 --force）
- [x] `操作记录.md` 已追加本轮记录（轮次 R360）
- [x] 所有阈值有文献来源（R02 学术诚信）
- [x] bend_compensate 标注 *创新* 并记录底层逻辑
- [x] DENSITY_MIN 连续缩放标注 *创新* 并记录底层逻辑
