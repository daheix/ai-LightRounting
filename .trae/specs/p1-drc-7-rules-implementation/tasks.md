# Tasks — P1 DRC 7 条规则缺失修复（R383）

## 阶段一：数据模型扩展（rules.py）

- [ ] Task 1: CheckType 枚举新增 7 个类型
  - SEPARATION / ENCLOSURE / EXTENSION / EXCLUSION
  - ANGLE_LIMIT / WAVEGUIDE_TAPER_ANGLE / SINGLEMODE_WIDTH
- [ ] Task 2: DRCRule dataclass 新增 2 字段（layer_pair / limit_max，默认 None）
- [ ] Task 3: DEFAULT_DRC_RULES 追加 7 条规则定义（含文献 description）

## 阶段二：4 条跨层规则实现（新建 engine_cross_layer.py）

- [ ] Task 4: 创建 CrossLayerRulesMixin（含 docstring ≥5 文献 URL）
- [ ] Task 5: 实现 _check_separation（跨层间距 1.0μm）
- [ ] Task 6: 实现 _check_enclosure（包围 0.5μm，VIAC 被 M1 包围）
- [ ] Task 7: 实现 _check_extension（延伸 0.2μm）
- [ ] Task 8: 实现 _check_exclusion（禁止层重叠 0.0μm）

## 阶段三：3 条波导级规则实现（追加 engine_waveguide.py）

- [ ] Task 9: 实现 _check_angle_limit（路径段角度 [45°, 135°]）
- [ ] Task 10: 实现 _check_waveguide_taper_angle（锥形半顶角 ≤10°，atan 公式）
- [ ] Task 11: 实现 _check_singlemode_width（波导宽度 ≤1.0μm，V 参数推导）

## 阶段四：引擎集成（engine.py）

- [ ] Task 12: DRCEngine 继承 CrossLayerRulesMixin
- [ ] Task 13: _dispatch 字典注册 7 个新 CheckType → 检查方法

## 阶段五：R05 Bug 修复

- [ ] Task 14: drc_curvilinear_18rules.py MW1_max_width_single_mode 1.05→1.0
- [ ] Task 15: 修正相关 docstring 标注 V 参数推导依据

## 阶段六：回归测试 + 文档更新

- [ ] Task 16: 创建 test_p1_drc_rules.py（7 条规则 × 2 用例 = 14 测试）
- [ ] Task 17: py_compile + ruff check 全通过
- [ ] Task 18: pytest 运行回归测试全通过
- [ ] Task 19: 更新 docs/drc_rules_audit.md 覆盖率 48%→100%
- [ ] Task 20: 更新 docs/final_defect_audit_report_2026_07.md P1 缺失 7→0
- [ ] Task 21: 更新操作记录.md + git commit + push

# Task Dependencies
- Task 2 depends on Task 1（字段引用枚举）
- Task 3 depends on Task 1+2（规则定义用枚举+字段）
- Task 4-8 depends on Task 1+2（Mixin 引用枚举+字段）
- Task 9-11 depends on Task 1+2
- Task 12-13 depends on Task 4-11（dispatch 引用方法）
- Task 14-15 独立（R05 Bug 修复）
- Task 16 depends on Task 1-15
- Task 17-18 depends on Task 16
- Task 19-21 depends on Task 18
