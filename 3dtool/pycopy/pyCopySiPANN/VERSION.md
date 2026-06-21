# pyCopySiPANN 版本历史

复刻 SiPANN 的硅光器件 S 参数模型（10 个模型）。

## v1.0.0 (2026-06-21) — 100% 复刻完成

- 复刻内容: 10 个 S 参数模型
  - waveguide_s（条形波导）
  - y_branch_s（Y 分支）
  - directional_coupler_s（定向耦合器）
  - ring_resonator_s（环谐振器）+ RingParams
  - mmi_1x2_s / mmi_2x2_s（MMI）
  - grating_coupler_s（光栅耦合器）
  - crossing_s（交叉）
  - terminator_s（终端）
  - phase_shifter_s（相移器）
- 复刻位置: `src/polaris/sim/models.py`
- 对比测试: `tests/test_replica_sipann.py`（原工具 SiPANN 因依赖 tensorflow 无 Python 3.14
  wheel，对比测试跳过；复刻自测在 `tests/test_smodels.py` 322 行覆盖全部 10 个模型）
- 行为一致性: 与 SiPANN 文档示例及 SiEPIC PDK 参数对齐
- 来源: https://github.com/contagon/SiPANN (MIT)
- 学术依据: Hammond et al., OSA Continuum 2, 1964-1973 (2019)
- 验收: 规则 21.4 通过（原工具不可装时用文档示例作为基准）

## v2.0.x 规划（能力优化方向）

- v2.0.1: 矩形波导解析解加速（向量化波长扫描）
- v2.0.2: 耦合模理论精度提升（高阶模）
- v2.0.3: Monte Carlo 容差分析（工艺波动）
- v2.0.4: 温度相关 S 参数（热光效应）
