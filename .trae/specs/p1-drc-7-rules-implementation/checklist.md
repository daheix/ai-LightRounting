# Checklist — P1 DRC 7 条规则缺失修复（R383）

## 代码质量门禁
- [ ] 函数 ≤80 行（所有新方法）
- [ ] 文件 ≤800 行（engine_waveguide.py 追加后不超标）
- [ ] 圈复杂度 ≤15
- [ ] 无 TODO/FIXME/HACK 残留
- [ ] 无 `except: pass` / `return None` / `return []` fall-back

## R02 学术诚信
- [ ] 每个新模块 docstring ≥5 文献 URL
- [ ] 所有阈值可溯源（SiEPIC/gdsfactory/KLayout/FluxCore/Snyder&Milburn）
- [ ] 创新点标注 *创新* 并记录底层逻辑
- [ ] R05 Bug 1.05→1.0 附 V 参数推导

## R03 禁止 fall-back
- [ ] 层字段缺失时跳过（合法物理含义，非业务错误）
- [ ] 配置非法时 raise VerifyError（非静默返回空）
- [ ] 锥形长度 ≤0 时 raise
- [ ] 无伪造默认值

## R04 不参与 GPU
- [ ] 纯 NumPy 实现，无 CuPy/CUDA

## 规则阈值核查
- [ ] SEPARATION 1.0μm（gdsfactory HEATER-M1）
- [ ] ENCLOSURE 0.5μm（SiEPIC VIAC-M1_ENCLOSURE）
- [ ] EXTENSION 0.2μm（drc_curvilinear_18rules EX1_layer_extension）
- [ ] EXCLUSION 0.0μm（零容忍）
- [ ] ANGLE_LIMIT [45°, 135°]（FluxCore）
- [ ] WAVEGUIDE_TAPER_ANGLE 10°（drc_curvilinear_18rules CV3，Milton & Burns 1987）
- [ ] SINGLEMODE_WIDTH 1.0μm（V 参数推导，Snyder & Love 1983）

## 测试覆盖
- [ ] 7 条规则各 1 个 pass 用例
- [ ] 7 条规则各 1 个 violation 用例
- [ ] V 参数推导数值验证测试（1.0μm）
- [ ] py_compile 全通过
- [ ] ruff check All checks passed
- [ ] pytest 全通过

## 文档更新
- [ ] docs/drc_rules_audit.md 覆盖率 48%→100%（25/25）
- [ ] docs/final_defect_audit_report_2026_07.md P1 缺失 7→0
- [ ] 操作记录.md R383 追加完成
- [ ] commit message 类型与内容一致（feat: add P1 DRC rules）

## 提交（R11 V8）
- [ ] git add 精确文件（禁止 -A）
- [ ] git commit -m "feat: 补齐 7 条 P1 DRC 规则 (覆盖率 72%→100%)"
- [ ] git push origin main（禁止 --force）
