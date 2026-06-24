# R05-R36 路标依次完成执行计划（v3）

**计划版本**: v3.0
**创建日期**: 2026-06-22
**计划范围**: R05（当前进行中）→ R36（2029-06），共 32 个路标
**执行原则**: 依次完成，不等待；每个路标完整交付（代码+测试+文档+操作记录+Git提交合并main）
**用户指令**: `/plan 依次完成所有的路标；不需要等待；循环迭代10000轮`

---

## 一、当前状态分析

### 1.1 已完成路标（已合并 main）
- **R01**（2026-07）：sax 频域 S 参数仿真对齐 — commit eec7788 ✅
- **R02**（2026-08）：simphony 光子电路仿真对齐 — commit ce36b42 ✅
- **R03**（2026-09）：S 参数级联优化 — commit 8a78ea0 ✅
- **R04**（2026-10）：子网络增长算法深度优化 — commit 8586ea4 ✅

### 1.2 当前进行中路标
- **R05**（2026-11）：JAX 加速集成 — 5 个文件已创建未提交，未完成测试验证

### 1.3 R05 已完成工作（未跟踪文件）
| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `src/polaris/sim/jax_backend.py` | 已创建 | ~336 | JAX 后端核心（JIT+双后端+GPU+AOT） |
| `src/polaris/sim/autodiff.py` | 已创建 | ~285 | 自动微分（grad/VJP/JVP+有限差分验证+波导优化） |
| `src/polaris/sim/monte_carlo.py` | 已创建 | ~235 | 蒙特卡洛分析（vmap并行+统计+良率） |
| `tests/test_jax_backend.py` | 已创建 | ~214 | JAX 后端测试（8 个测试类） |
| `tests/test_autodiff.py` | 已创建 | ~215 | 自动微分测试（8 个测试类） |

### 1.4 R05 待完成工作
1. 创建 `tests/test_monte_carlo.py` 测试文件
2. 更新 `src/polaris/sim/__init__.py` 添加 R05 导出
3. 运行 R05 测试验证（jax_backend + autodiff + monte_carlo）
4. 运行完整回归测试套件
5. 更新 `操作记录.md`（第 101 轮）
6. Git 提交合并 main

### 1.5 Git 状态
- 当前分支: `trae/solo-agent-QtGqG4-ai-Light`
- main 分支: `8586ea4`（R04 已合并）
- 工作区: 5 个未跟踪文件（R05 交付物）

### 1.6 JAX 环境确认
- JAX 0.10.2 已安装可用（CPU 后端）
- klujax 0.5.0 已安装可用

---

## 二、R05 完成方案（立即执行）

### 2.1 步骤 1：创建 test_monte_carlo.py

**文件**: `/workspace/tests/test_monte_carlo.py`

**测试类设计**（对齐 test_jax_backend.py 风格）:
- `TestMonteCarloSimulate` — 蒙特卡洛仿真基本功能
  - `test_monte_carlo_basic` — 100 采样基本测试
  - `test_monte_carlo_statistics` — 均值/标准差/百分位统计正确性
  - `test_monte_carlo_reproducible` — 相同 seed 结果一致
  - `test_monte_carlo_n_samples` — 不同采样数测试
- `TestSensitivityAnalysis` — 敏感度分析
  - `test_sensitivity_basic` — 基本敏感度计算
  - `test_sensitivity_param_names` — 参数名映射
- `TestYieldAnalysis` — 良率分析
  - `test_yield_basic` — 基本良率计算
  - `test_yield_all_pass` — 全部通过场景
  - `test_yield_all_fail` — 全部失败场景
- `TestWaveguideTransmissionMC` — 波导传输蒙特卡洛
  - `test_waveguide_mc_basic` — 基本功能
- `TestR05MonteCarloIntegration` — 集成测试
  - `test_no_fallback_in_monte_carlo` — AST 检查无 fall-back

**关键约束**:
- 所有 JAX 测试使用 `@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")` 装饰
- 使用 `enable_float64` fixture（autouse）
- 验证 `MonteCarloResult` dataclass 所有字段

### 2.2 步骤 2：更新 __init__.py 添加 R05 导出

**文件**: `/workspace/src/polaris/sim/__init__.py`

**新增导入**（在 R04 导入后添加）:
```python
from polaris.sim.jax_backend import (
    JAXConfig,
    benchmark_jit_vs_numpy,
    cascade_two_port_jax,
    enable_float64,
    get_jax_devices,
    is_jax_available,
    jit_compile,
    set_jax_backend,
    simulate_waveguide_chain_jax,
    waveguide_s_jax,
)
from polaris.sim.autodiff import (
    compute_gradient,
    compute_jvp,
    compute_vjp,
    finite_difference_gradient,
    optimize_waveguide_lengths,
    verify_gradient,
    waveguide_transmission_loss,
)
from polaris.sim.monte_carlo import (
    MonteCarloResult,
    monte_carlo_simulate,
    sensitivity_analysis,
    waveguide_transmission_mc,
    yield_analysis,
)
```

**新增 __all__ 条目**:
```python
# R05 JAX 加速集成（JIT + 自动微分 + 蒙特卡洛 + GPU）
"JAXConfig",
"is_jax_available",
"get_jax_devices",
"enable_float64",
"jit_compile",
"waveguide_s_jax",
"cascade_two_port_jax",
"simulate_waveguide_chain_jax",
"benchmark_jit_vs_numpy",
"set_jax_backend",
"compute_gradient",
"compute_vjp",
"compute_jvp",
"finite_difference_gradient",
"verify_gradient",
"waveguide_transmission_loss",
"optimize_waveguide_lengths",
"MonteCarloResult",
"monte_carlo_simulate",
"sensitivity_analysis",
"yield_analysis",
"waveguide_transmission_mc",
```

### 2.3 步骤 3：运行 R05 测试

**命令**:
```bash
pytest tests/test_jax_backend.py tests/test_autodiff.py tests/test_monte_carlo.py -v --timeout=120
```

**验收标准**:
- 所有测试通过（JAX 不可用时跳过，但 AST 检查类测试必须通过）
- 无 fall-back 兜底（AST 检查）
- 梯度验证误差 < 1e-3（与有限差分一致）
- JIT 编译波导链与 numpy 结果一致（误差 < 1e-10）

### 2.4 步骤 4：完整回归测试

**命令**:
```bash
pytest tests/ -q --tb=short --timeout=120 --ignore=tests/test_tilos_benchmark.py
```

**验收标准**:
- 无新增失败（基线: R04 完成时 2511 passed）
- R05 新增测试全部通过
- 无 fall-back 兜底警告

### 2.5 步骤 5：更新操作记录.md

**追加内容**: 第 101 轮 R05 交付记录
- 用户诉求
- 聊天总结
- 修改清单
- 验证结果
- Git 提交信息

### 2.6 步骤 6：Git 提交合并 main

**流程**:
```bash
git add src/polaris/sim/jax_backend.py src/polaris/sim/autodiff.py src/polaris/sim/monte_carlo.py tests/test_jax_backend.py tests/test_autodiff.py tests/test_monte_carlo.py src/polaris/sim/__init__.py 操作记录.md
git commit -m "feat(sim): R05 路标实际交付 — JAX 加速集成（JIT+自动微分+蒙特卡洛）"
git checkout main && git merge trae/solo-agent-QtGqG4-ai-Light
git push origin main
git checkout trae/solo-agent-QtGqG4-ai-Light
```

---

## 三、R06-R36 依次执行框架

### 3.1 标准路标执行流程（每个路标 7 步）

每个路标（R06-R36）按照以下标准流程执行：

1. **读取路标文档**: `docs/roundmap/R{XX}.md`
2. **技术调研**: 基于 6 大类权威资源（arXiv/IEEE/ACM + Stack Overflow/HN + GitHub + IETF/W3C + Google/Meta/AWS + High Scalability）
3. **代码实现**: 创建/修改 `src/polaris/` 下对应模块
4. **测试编写**: 创建 `tests/test_*.py`，覆盖率 ≥ 90%
5. **更新 __init__.py**: 添加新导出
6. **运行测试**: `pytest tests/test_*.py -v` + 完整回归
7. **交付**: 更新操作记录.md + Git 提交合并 main

### 3.2 阶段 1 收尾（R06）

#### R06（2026-12）：阶段 1 验收 + 综合得分 6.8
**目标**: 阶段 1 整体验收，综合得分 6.8
**核心交付**:
1. sax + simphony 所有核心功能 100% 复刻验收
2. 测试覆盖率 ≥ 90%
3. 大规模电路（10000+ 器件）稳定求解
4. JAX 加速性能达标（JIT 5+ 倍、GPU 50+ 倍）
5. 自动微分支持梯度优化
6. 与 sax/simphony 回归测试误差 < 1e-10
7. 阶段 1 总结报告

**新增文件**:
- `/workspace/tests/test_r06_stage1_acceptance.py` — 阶段 1 验收测试
- `/workspace/docs/stage1_acceptance_report.md` — 阶段 1 总结报告

### 3.3 阶段 2（R07-R12）：KLayout + gdsfactory 对齐

#### R07（2027-01）：KLayout DRC 深度集成
- 追赶对象: KLayout DRC runset
- 核心: 实现 KLayout DRC runner 完整集成，支持 SiEPIC/ehybrid runset
- 综合得分: 6.8 → 6.9

#### R08（2027-02）：KLayout LVS 集成
- 追赶对象: KLayout LVS
- 核心: 实现版图 vs 网表对比
- 综合得分: 6.9 → 7.0

#### R09（2027-03）：gdsfactory PDK 集成
- 追赶对象: gdsfactory PDK
- 核心: 实现 gdsfactory PDK 格式兼容
- 综合得分: 7.0 → 7.1

#### R10（2027-04）：gdsfactory 布线集成
- 追赶对象: gdsfactory routing
- 核心: 实现自动布线算法
- 综合得分: 7.1 → 7.2

#### R11（2027-05）：GDS 导出/导入优化
- 追赶对象: KLayout GDS
- 核心: GDSII 二进制读写优化
- 综合得分: 7.2 → 7.3

#### R12（2027-06）：阶段 2 验收 + 综合得分 7.4
- 阶段 2 整体验收
- 综合得分: 7.3 → 7.4

### 3.4 阶段 3（R13-R18）：Aspic + VPIphotonics 对齐

#### R13（2027-07）：Aspic 电路仿真对齐
- 追赶对象: Aspic
- 核心: 时域仿真
- 综合得分: 7.4 → 7.5

#### R14（2027-08）：Aspic 器件模型对齐
- 追赶对象: Aspic
- 核心: 器件模型库扩展
- 综合得分: 7.5 → 7.6

#### R15（2027-09）：VPIphotonics 系统级仿真
- 追赶对象: VPIphotonics
- 核心: 系统级仿真
- 综合得分: 7.6 → 7.7

#### R16（2027-10）：VPIphotonics PDK 对齐
- 追赶对象: VPIphotonics
- 核心: PDK 集成
- 综合得分: 7.7 → 7.8

#### R17（2027-11）：光电协同仿真
- 追赶对象: VPIphotonics
- 核心: 光电协同
- 综合得分: 7.8 → 7.9

#### R18（2027-12）：阶段 3 验收 + 综合得分 7.9
- 阶段 3 整体验收
- 综合得分: 7.9

### 3.5 阶段 4（R19-R24）：L-Edit + OptoDesigner 对齐

#### R19（2028-01）：L-Edit 版图编辑对齐
- 追赶对象: Siemens L-Edit
- 核心: 版图编辑
- 综合得分: 7.9 → 8.0

#### R20（2028-02）：L-Edit DRC 对齐
- 追赶对象: Siemens L-Edit
- 核心: DRC 规则
- 综合得分: 8.0 → 8.1

#### R21（2028-03）：OptoDesigner 布线对齐
- 追赶对象: Synopsys OptoDesigner
- 核心: 自动布线
- 综合得分: 8.1 → 8.2

#### R22（2028-04）：OptoDesigner PDK 对齐
- 追赶对象: Synopsys OptoDesigner
- 核心: PDK 集成
- 综合得分: 8.2 → 8.3

#### R23（2028-05）：tape-out 流程对齐
- 追赶对象: Synopsys OptoDesigner
- 核心: tape-out 流程
- 综合得分: 8.3 → 8.4

#### R24（2028-06）：阶段 4 验收 + 综合得分 8.4
- 阶段 4 整体验收
- 综合得分: 8.4

### 3.6 阶段 5（R25-R30）：IPKISS + Tidy3D 对齐

#### R25（2028-07）：IPKISS 版图对齐
- 追赶对象: Luceda IPKISS
- 核心: 版图生成
- 综合得分: 8.4 → 8.5

#### R26（2028-08）：IPKISS 仿真对齐
- 追赶对象: Luceda IPKISS
- 核心: 电路仿真
- 综合得分: 8.5 → 8.6

#### R27（2028-09）：Tidy3D FDTD 对齐
- 追赶对象: Tidy3D
- 核心: FDTD 仿真
- 综合得分: 8.6 → 8.7

#### R28（2028-10）：Tidy3D GPU 加速
- 追赶对象: Tidy3D
- 核心: GPU 加速
- 综合得分: 8.7 → 8.8

#### R29（2028-11）：逆向设计对齐
- 追赶对象: Tidy3D
- 核心: 逆向设计
- 综合得分: 8.8 → 8.8

#### R30（2028-12）：阶段 5 验收 + 综合得分 8.8
- 阶段 5 整体验收
- 综合得分: 8.8

### 3.7 阶段 6（R31-R36）：Lumerical + AlphaChip 对齐

#### R31（2029-01）：Lumerical FDTD 对齐
- 追赶对象: Ansys Lumerical
- 核心: FDTD 仿真
- 综合得分: 8.8 → 8.9

#### R32（2029-02）：Lumerical MODE 对齐
- 追赶对象: Ansys Lumerical
- 核心: MODE 仿真
- 综合得分: 8.9 → 9.0

#### R33（2029-03）：Lumerical INTERCONNECT 对齐
- 追赶对象: Ansys Lumerical
- 核心: 电路仿真
- 综合得分: 9.0 → 9.1

#### R34（2029-04）：AlphaChip AI 对齐
- 追赶对象: AlphaChip
- 核心: AI 布局
- 综合得分: 9.1 → 9.1

#### R35（2029-05）：量子光子对齐
- 追赶对象: 量子光子工具
- 核心: 量子光子
- 综合得分: 9.1 → 9.2

#### R36（2029-06）：阶段 6 验收 + 综合得分 9.2
- 阶段 6 整体验收
- 综合得分: 9.2

---

## 四、执行约束与规则

### 4.1 项目规则遵守（22 条强制规则）
1. ✅ 禁止 fall-back 兜底（规则 14.1）— 所有错误必须 raise
2. ✅ 学术诚信（规则 15）— 所有数据来源标注 URL
3. ✅ 创新点标注（规则 15.3）— 标注"创新"+ 逻辑 + 理论 + 案例
4. ✅ 6 分钟标准提交（用户规则）— 每个路标完成后立即提交
5. ✅ 代码上传开发分支，同步 main 分支（用户规则 1）
6. ✅ 单文件版本升级，禁止多 vx 共存（用户规则 3）
7. ✅ 中文回答（用户规则）
8. ✅ 操作记录保存到 `操作记录.md`（用户规则）

### 4.2 质量门禁
- 圈复杂度 ≤ 15
- 函数行数 ≤ 80
- 文件行数 ≤ 800
- 测试覆盖率 ≥ 90%
- 无 `except Exception: pass` 兜底
- 无 TODO/FIXME/XXX/HACK 标记

### 4.3 测试要求
- 每个新模块必须有对应测试文件
- JAX 测试使用 `@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")` 装饰
- AST 检查无 fall-back 兜底
- 与 numpy 版本结果一致（误差 < 1e-10）

### 4.4 Git 提交规范
- 提交信息格式: `feat(sim): R{XX} 路标实际交付 — {简要描述}`
- 每个路标一个提交
- 提交后合并 main 并推送
- 切回开发分支继续开发

---

## 五、验证步骤

### 5.1 R05 验证清单
- [ ] `tests/test_monte_carlo.py` 创建完成
- [ ] `src/polaris/sim/__init__.py` R05 导出添加
- [ ] R05 测试全部通过（jax_backend + autodiff + monte_carlo）
- [ ] 完整回归测试无新增失败
- [ ] 操作记录.md 更新（第 101 轮）
- [ ] Git 提交合并 main

### 5.2 R06-R36 验证清单（每个路标）
- [ ] 读取路标文档 `docs/roundmap/R{XX}.md`
- [ ] 代码实现完成
- [ ] 测试编写完成（覆盖率 ≥ 90%）
- [ ] __init__.py 导出更新
- [ ] 测试全部通过
- [ ] 完整回归测试无新增失败
- [ ] 操作记录.md 更新
- [ ] Git 提交合并 main

---

## 六、假设与决策

### 6.1 假设
1. JAX 0.10.2 在 CPU 后端稳定可用（已验证）
2. klujax 0.5.0 可用（已验证）
3. 现有测试基线 2511 passed 无回归（R04 完成时）
4. 6 大类权威资源可通过 WebSearch 访问
5. 每个路标的技术文档 `docs/roundmap/R{XX}.md` 已存在且可作为实现依据

### 6.2 决策
1. **R05 优先完成**: 当前进行中，必须先完成再进入 R06
2. **标准流程**: 每个路标按 7 步标准流程执行
3. **完整交付**: 每个路标必须完整交付（代码+测试+文档+操作记录+Git提交）
4. **不等待**: 依次完成，不等待用户确认（用户明确指令）
5. **循环迭代**: 完成所有路标后，进入优化循环（性能优化、文档刷新、商业差距分析）

---

## 七、执行顺序总览

```
R05（当前）→ R06 → R07 → R08 → ... → R36 → 优化循环
```

**当前优先级**: R05 完成交付
**后续**: R06-R36 依次完成
**最终**: 综合得分 9.2，对齐并超越商业产品
