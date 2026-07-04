# Checklist

## gds_loader.py 实现
- [x] `modules/gds_tools/src/polaris_gds_tools/gds_loader.py` 已创建
- [x] klayout.db 读取 GDSII 文件
- [x] 多策略器件识别（instance / DEVREC polygon / 顶层 cell）
- [x] SiEPIC → PoLaRIS 器件名映射表（30+ 项）
- [x] PIN 端口提取与 text→path 匹配
- [x] 跨器件连接推断（容差 15.0μm）
- [x] Spice_param 参数解析
- [x] DCplxTrans 手动变换
- [x] 三个对外 API（load_gds_to_circuit / load_gds_to_circuit_spec / siepic_to_polaris）
- [x] 文件行数 ≤800（R11 质量门禁，实测 715 行）

## __init__.py 导出
- [x] `modules/gds_tools/src/polaris_gds_tools/__init__.py` 已添加导入
- [x] `__all__` 已添加三个新 API

## 测试脚本
- [x] `scripts/test_siepic_gds_loader.py` 已创建
- [x] 默认测 10 个文件（覆盖三种识别策略）
- [x] `--all` 跑全量 229 个
- [x] 退出码策略正确（默认 100%，--all ≥95%）

## test_real_circuits.py siepic 分支
- [x] 移除"模块下线"的 raise
- [x] 改为调用 `load_gds_to_circuit`
- [x] docstring 和 FAILURE_CATEGORIES 已同步更新

## 测试验证
- [x] 默认 10 个文件测试 100% 成功
- [x] 全量 229 个文件测试 100% 成功（3.20s）
- [x] 策略分布 {instance:104, devrec_polygon:68, top_cell:57}
- [x] test_real_circuits.py siepic 分支前 5 个用例验证通过
- [x] 压缩 docstring 后再次运行测试无回归（默认 10 个 100% 成功）

## 规则合规
- [x] R02 学术诚信：GDSII 标准 SEMI P39-0308E + SiEPIC PDK URL 已标注
- [x] R03 禁止 fall-back：PIN text 无匹配 path / 端口未匹配器件均 raise
- [x] R04 不参与 GPU：纯 klayout.db（CPU）实现
- [x] R05 Bug 必修：polaris_nn 实现的 11 个失败用例已修复（多策略识别）
- [x] R11 提交：git add 精确文件 → commit → push origin main（commit 53492a7）
- [x] R07 操作记录：`操作记录.md` 追加轮次 R345B（commit 6b43790）

## 代码提交与操作记录
- [x] `git add` 4 个精确文件
- [x] `git commit -m "feat: 恢复 SiEPIC GDS 解析器（R345），229 个用例 100% 可解析"` (53492a7)
- [x] `git push origin main` (c9acca9..53492a7)
- [x] `操作记录.md` 追加轮次 R345B（含交付文件/测试结果/规则依据，6b43790）
- [x] 无 fall-back 残留（R03）
- [x] 无 TODO/FIXME/HACK 残留（R05）
