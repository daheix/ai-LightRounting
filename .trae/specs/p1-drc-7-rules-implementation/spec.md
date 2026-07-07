# P1 DRC 7 条规则缺失修复 Spec（R383）

## Why

PoLaRIS DRC 规则覆盖率 72%（18/25），P0 已补齐 6 条，P1 仍缺 7 条
（来源: docs/final_defect_audit_report_2026_07.md:179）。Tape-out sign-off
不可发布（docs/LR商用版测试报告_20260704.md:105）。综合得分 8.67/10 距
9.20 目标差 -0.53，DRC 完整性是核心阻断项之一。

本 spec 补齐 7 条 P1 DRC 规则，将覆盖率从 72% 提升至 100%（25/25），
对齐 SiEPIC EBeam PDK / gdsfactory / KLayout / FluxCore 商业 EDA 水平。

## What Changes

### 阶段一：数据模型扩展（rules.py）
- CheckType 枚举新增 7 个类型: SEPARATION / ENCLOSURE / EXTENSION /
  EXCLUSION / ANGLE_LIMIT / WAVEGUIDE_TAPER_ANGLE / SINGLEMODE_WIDTH
- DRCRule dataclass 新增 2 个字段（frozen=True，带默认值）:
  - `layer_pair: str | None = None`（跨层规则的配对层名）
  - `limit_max: float | None = None`（双限规则上限，如 ANGLE_LIMIT [45°,135°]）
- DEFAULT_DRC_RULES 追加 7 条规则定义（含文献溯源 description）

### 阶段二：4 条跨层规则实现（新建 engine_cross_layer.py）
- CrossLayerRulesMixin: SEPARATION / ENCLOSURE / EXTENSION / EXCLUSION
- 基于器件层抽象 + device.params.layer 字段读取层信息
- 复用 checks.py 的 aabb / aabb_distance / aabb_overlap 几何工具
- R03 禁止 fall-back: 层字段缺失时跳过（合法：未声明层=无跨层约束），
  但配置非法时 raise VerifyError

### 阶段三：3 条波导级规则实现（追加到 engine_waveguide.py）
- ANGLE_LIMIT: device.params.path_angle ∈ [45°, 135°]
- WAVEGUIDE_TAPER_ANGLE: atan(Δwidth/2/L) ≤ 10°（Milton & Burns 1987）
- SINGLEMODE_WIDTH: device.params.width_um ≤ 1.0μm（V 参数推导，修正 1.05μm Bug）

### 阶段四：引擎集成（engine.py）
- DRCEngine 继承 CrossLayerRulesMixin
- _dispatch 字典注册 7 个新 CheckType → 检查方法映射

### 阶段五：R05 Bug 修复
- drc_curvilinear_18rules.py:221 MW1_max_width_single_mode 1.05μm → 1.0μm
- 附 V 参数推导回归测试（Snyder & Love 1983 §13.5）

### 阶段六：回归测试 + 文档更新
- 7 条规则各 2 个测试用例（pass + violation）
- 更新 docs/drc_rules_audit.md 覆盖率 48%→100%
- 更新 docs/final_defect_audit_report_2026_07.md P1 缺失 7→0

## Impact

- Affected code:
  - `modules/drc/src/polaris_drc/rules.py`（CheckType +7, DRCRule +2 字段, DEFAULT_DRC_RULES +7）
  - `modules/drc/src/polaris_drc/engine_cross_layer.py`（新建，4 条跨层规则 Mixin）
  - `modules/drc/src/polaris_drc/engine_waveguide.py`（+3 条波导级规则）
  - `modules/drc/src/polaris_drc/engine.py`（_dispatch +7, 继承 CrossLayerRulesMixin）
  - `modules/verify_advanced/src/polaris_verify_advanced/drc_curvilinear_18rules.py`（R05 Bug 1.05→1.0）
  - `modules/drc/tests/test_p1_drc_rules.py`（新建，回归测试）
- Affected docs:
  - `docs/drc_rules_audit.md`（覆盖率 48%→100%）
  - `docs/final_defect_audit_report_2026_07.md`（P1 缺失 7→0）
  - `操作记录.md`（R383 追加）

## ADDED Requirements

### Requirement: 7 条 P1 DRC 规则检查逻辑
系统 SHALL 实现 7 条 P1 DRC 规则的完整检查逻辑，每条规则含可溯源阈值、
文献 URL、R03 合规的异常处理。

#### Scenario: SEPARATION 跨层间距违规
- WHEN 两器件分属不同层（layer_a / layer_b）且 AABB 间距 < 1.0μm
- THEN 报 SEPARATION 违规，message 含层名+间距+位置

#### Scenario: ENCLOSURE 包围违规
- WHEN 内层器件（如 VIAC）未被外层器件（如 M1_HEATER）完全包围，包围量 < 0.5μm
- THEN 报 ENCLOSURE 违规

#### Scenario: SINGLEMODE_WIDTH 违规
- WHEN device.params.width_um > 1.0μm（V 参数单模上限）
- THEN 报 SINGLEMODE_WIDTH 违规，message 含 V 参数推导依据

### Requirement: R05 Bug 修复 MW1_max_width_single_mode
系统 SHALL 将 drc_curvilinear_18rules.py 的 MW1_max_width_single_mode
从 1.05μm 修正为 1.0μm（V 参数严格推导值，Snyder & Love 1983 §13.5）。

#### Scenario: V 参数推导验证
- WHEN λ=1.55μm, n_core=3.476, n_clad=1.444, V_cutoff=2.405
- THEN W_max = 2×2.405×1.55 / (2π×√(3.476²-1.444²)) ≈ 1.00μm

## MODIFIED Requirements

### Requirement: DRC 规则覆盖率 100%
DRC 规则覆盖率 SHALL 从 72%（18/25）提升至 100%（25/25），P1 缺失从 7 条降至 0 条。

## 文献溯源（R02 学术诚信）

1. SiEPIC EBeam PDK — https://github.com/SiEPIC/SiEPIC_EBeam_PDK
2. gdsfactory DRC notebook — http://raw.githubusercontent.com/gdsfactory/gdsfactory-photonics-training/main/notebooks/11_drc.ipynb
3. KLayout DRC Runsets — https://www.klayout.org/doc-qt5/manual/drc_runsets.html
4. FluxCore DRC — https://www.fluxcoredynamics.com/docs/design-rules
5. Snyder & Love 1983 "Optical Waveguide Theory" §13.5（V 参数 2.405）— https://link.springer.com/book/10.1007/978-94-009-6875-2
6. Milton & Burns 1987 JLT（绝热锥形）— https://opg.optica.org/jlt/abstract.cfm?uri=jl-5-8-1079
7. Chrostowski & Hochberg 2015 CUP §4.3 — https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
8. Soref 1991 IEEE JQE（SOI 单模条形波导）— https://doi.org/10.1109/3.84143
9. Vlasov & McNab 2004 Opt. Express（SOI 单模损耗）— https://opg.optica.org/oe/abstract.cfm?uri=oe-12-8-1622
10. Synopsys OptoDesigner DRC Module — https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html

## 规则依据
- R01 方案检索 / R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修
- R04 不参与 GPU（纯 NumPy）/ R11 V8 工作流 / R13 §1 Spec 无需审批
