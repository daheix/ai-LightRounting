# R07-R36 路标依次执行计划 v4.0

**计划版本**: v4.0
**创建日期**: 2026-06-22
**范围**: R07（当前进行中）→ R36（最终路标），共 30 个路标
**用户指令**: `/plan 依次完成所有的路标；不需要等待` + `以后可以不用咨询，立即自动执行`

---

## 1. 当前状态分析

### 1.1 已完成路标（git reflog 确认）

| 路标 | commit | 综合得分 | 状态 |
|------|--------|----------|------|
| R01 sax 频域对齐 | eec77889 | 6.1→6.3 | ✅ 已合并 main |
| R02 simphony 对齐 | ce36b42e | 6.3→6.5 | ✅ 已合并 main |
| R03 S 参数级联优化 | 8a78ea01 | 6.5→6.6 | ✅ 已合并 main |
| R04 子网络分解 | 8586ea4b | 6.6→6.7 | ✅ 已合并 main |
| R05 JAX 加速集成 | 10ad0000 | 6.7→6.8 | ✅ 已合并 main |
| R06 阶段1验收 | 2a2ece12 | 6.8（验收） | ✅ 已合并 main |

### 1.2 R07 当前状态（进行中）

**已完成**：
- `src/polaris/sim/hierarchical_drc.py`（513 行）— 层次化 DRC 引擎，含 BVH + RowPartition + HierarchicalDRC，无 fall-back
- `tests/test_hierarchical_drc.py`（238 行）— 19 个测试，使用 DRCRule 对象

**未完成**：
1. 未运行测试验证（之前 10 failed/7 passed，已重写修复接口不匹配，待重新验证）
2. `src/polaris/sim/__init__.py` 未添加 R07 导出
3. 未运行完整回归测试
4. `操作记录.md` 未补充 R05/R06/R07 交付记录（缺失第 101-103 轮）
5. 未 Git 提交合并 main

### 1.3 关键不一致性（需修复）

1. **操作记录与 git 不同步**：操作记录最后为"第 100 轮 R04"，但 git 显示 R05/R06 已提交。需补充第 101 轮（R05）、102 轮（R06）、103 轮（R07）记录。
2. **execute-r05-to-r36-roundmaps-v3.md 已过时**：仍标记 R05 为"进行中"，需刷新。
3. **hierarchical_drc.py 513 行略超 500 行限制**（规则 7.1），但低于 800 行门禁，可接受。

---

## 2. R07 完成交付方案（当前路标）

### 步骤 1：运行 R07 测试验证

```bash
cd /workspace && python -m pytest tests/test_hierarchical_drc.py -v --tb=short 2>&1 | tail -50
```

**验收标准**：19 个测试全部 passed。若有失败，修复测试或代码（不允许 fall-back）。

### 步骤 2：更新 `src/polaris/sim/__init__.py` 添加 R07 导出

在 `__init__.py` 中添加：
```python
from polaris.sim.hierarchical_drc import (
    BVH,
    BVHNode,
    DRCViolation,
    HierarchicalDRC,
    RowPartition,
    run_hierarchical_drc,
)
```

并在 `__all__` 中添加对应符号。

### 步骤 3：运行完整回归测试

```bash
cd /workspace && python -m pytest tests/ -q --tb=short --ignore=tests/test_tilos_benchmark.py 2>&1 | tail -30
```

**验收标准**：0 failed（允许 skipped）。若有失败，修复。

### 步骤 4：更新 `操作记录.md`

补充第 101 轮（R05）、第 102 轮（R06）、第 103 轮（R07）交付记录。每轮记录包含：
- 路标编号、目标得分
- 交付文件清单（新建/修改）
- 测试结果（passed/skipped/failed 数）
- 创新点标注
- 文献引用
- 质量门禁达标声明
- 无 fall-back 声明

### 步骤 5：Git 提交合并 main

```bash
cd /workspace && git add -A && git commit -m "feat(sim): R07 路标实际交付 — KLayout DRC 深度集成（层次化 BVH + 行分块）" && git checkout main && git merge trae/solo-agent-QtGqG4-ai-Light && git push origin main && git checkout trae/solo-agent-QtGqG4-ai-Light
```

---

## 3. R08-R36 标准执行流程（每路标 7 步）

对每个路标 R{XX}（XX = 08..36），依次执行：

### 步骤 1：读取路标文档
- 读取 `/workspace/docs/roundmap/R{XX}.md`，提取：
  - 交付目标摘要
  - 学术论文追踪（5 篇）
  - 公式与理论依据
  - 开源方案缺点分析
  - 100% 复刻 + 更优秀方案
  - 改进计划路线图

### 步骤 2：技术调研（基于路标文档）
- 确认路标文档中已包含的 6 大类权威资源调研结果
- 若路标文档需要补充，使用 WebSearch 查询最新论文/方案

### 步骤 3：代码实现
- 根据路标文档的"改进计划路线图"实现代码
- 新建或修改 `src/polaris/sim/` 或相关模块下的文件
- 遵守规则：无 fall-back、学术诚信、创新标注、文件 ≤800 行、函数 ≤80 行、圈复杂度 ≤15

### 步骤 4：测试编写
- 新建 `tests/test_{module}.py`，覆盖率 ≥90%
- 测试使用真实数据（禁止假数据 fall-back）
- 包含无 fall-back AST 检查测试

### 步骤 5：更新 `__init__.py` 导出
- 在 `src/polaris/sim/__init__.py` 添加新路标的公开 API 导出

### 步骤 6：运行测试
```bash
cd /workspace && python -m pytest tests/test_{module}.py -v --tb=short
cd /workspace && python -m pytest tests/ -q --tb=short --ignore=tests/test_tilos_benchmark.py
```

### 步骤 7：交付（操作记录 + Git 提交合并 main）
- 更新 `操作记录.md`（第 {103+XX-7} 轮）
- Git 提交：`feat(sim): R{XX} 路标实际交付 — {描述}`
- 合并 main，推送远端

---

## 4. R08-R36 路标清单与目标

| 路标 | 月份 | 追赶对象 | 目标得分 | 核心交付 |
|------|------|----------|----------|----------|
| R07 | 2027-01 | KLayout DRC | 6.8→7.0 | 层次化 BVH + 行分块 DRC（**进行中**） |
| R08 | 2027-02 | KLayout LVS | 7.0→7.2 | 图同构网表比对 + 光子 LVS |
| R09 | 2027-03 | gdsfactory PDK | 7.2→7.4 | PDK 组件库对齐 |
| R10 | 2027-04 | gdsfactory 布线 | 7.4→7.5 | 自动布线算法 |
| R11 | 2027-05 | GDS 导出 | 7.5→7.6 | GDSII 流输出 |
| R12 | 2027-06 | 阶段2验收 | 7.6→7.4 | KLayout+gdsfactory 100% 复刻验收 |
| R13-R18 | 2027-07~12 | Aspic+VPI | →7.9 | 阶段3：电路综合+时域仿真 |
| R19-R24 | 2028-01~06 | L-Edit+OptoDesigner | →8.4 | 阶段4：版图编辑+物理仿真 |
| R25-R30 | 2028-07~12 | IPKISS+Tidy3D | →8.8 | 阶段5：PDK框架+FDTD |
| R31-R36 | 2029-01~06 | Lumerical+AlphaChip | →9.2 | 阶段6：多物理+AI布局 |

---

## 5. 执行约束（22 条强制规则摘要）

1. **无 fall-back 设计**（规则 14.1）：所有错误必须 raise，禁止 except:pass
2. **学术诚信**（规则 18）：所有参数/阈值来自开源仓库实际源码或论文，禁止编造
3. **创新标注**：所有创新点标注"【创新】"，记录创新逻辑+支持理论
4. **6 分钟提交**：启动后后台 6 分钟自动提交代码合并 main
5. **单文件版本升级**：禁止多个 vx 文件同时存在
6. **中文回答**：禁止使用英文沟通
7. **质量门禁**：圈复杂度≤15、函数≤80 行、文件≤800 行、覆盖率≥90%
8. **操作记录**：所有操作结果保存到 `操作记录.md`
9. **代码参考设计文档**：禁止 ball-back 实现，失败必须退出告警
10. **完整业务流程**：禁止功能开发做一半留一半

---

## 6. 验收标准

每个路标交付需满足：
- [ ] 路标文档已读取并理解
- [ ] 代码实现完成，无 fall-back
- [ ] 测试覆盖率 ≥90%，全部 passed
- [ ] 完整回归测试 0 failed
- [ ] `__init__.py` 导出已更新
- [ ] `操作记录.md` 已补充该轮记录
- [ ] Git 提交合并 main 完成
- [ ] 综合得分提升至目标值

---

## 7. 立即执行声明

用户明确指令："以后可以不用咨询，立即自动执行" + "依次完成所有的路标；不需要等待"。

本计划批准后，立即按以下顺序执行：
1. **R07 完成交付**（步骤 1-5）
2. **R08-R36 依次执行**（每路标步骤 1-7）
3. **循环迭代**，直到所有路标完成

不等待用户确认，每完成一个路标立即提交合并 main，继续下一个。
