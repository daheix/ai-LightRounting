# R03-R36 路标依次完成执行计划

**计划版本**: v1.0
**创建日期**: 2026-06-22
**计划范围**: R03（当前进行中）→ R36（2029-06），共 34 个路标
**执行原则**: 依次完成，不等待；每个路标完整交付（代码+测试+文档+操作记录+Git提交合并main）

---

## 一、当前状态分析

### 1.1 已完成路标
- **R01**（2026-07）：sax 频域 S 参数仿真对齐 — 78 个新测试 ✅
- **R02**（2026-08）：simphony 光子电路仿真对齐 — 49 个新测试 ✅

### 1.2 当前进行中路标
- **R03**（2026-09）：S 参数级联优化 — 代码已存在，1 个测试失败 ❌

### 1.3 R03 失败测试根本原因
- **失败测试**: `TestCascadeAdditive::test_cascade_additive_feedback_raises`
- **位置**: `/workspace/tests/test_cascade_backends.py` 第 283-294 行
- **根本原因**: `_check_no_feedback_loops`（`/workspace/src/polaris/sim/cascade_backends.py` 第 581-630 行）使用**无向图 DFS**，跳过父节点，无法检测两节点反馈环（wg1→wg2→wg1）
- **物理语义**: 连接 `[("wg1.out", "wg2.in"), ("wg2.out", "wg1.in")]` 是真实的反馈环路
- **图论语义**: 无向图中 A-B 只算一条边，DFS 跳过父节点后无法发现两节点环

### 1.4 测试基线
- 完整套件：2477 passed, 16 skipped, 1 failed（test_tilos_benchmark 预存失败）
- R03 测试：29 passed, 1 failed（环检测）
- 操作记录：最新第 98 轮（R02 交付）

### 1.5 项目规则合规性
- ✅ 无 `except Exception: pass` 兜底
- ✅ 无 `np.where(..., 1e-15, ...)` 数值兜底
- ✅ 无 TODO/FIXME/XXX/HACK 标记
- ✅ 22 条项目规则全部遵守
- ⚠️ AGENTS.md 不存在（用户规则要求包含）

---

## 二、R03 修复方案（立即执行）

### 2.1 修复目标
将 `_check_no_feedback_loops` 从无向图 DFS 改为**有向图 DFS** 环检测，正确识别两节点反馈环。

### 2.2 具体修改

**文件**: `/workspace/src/polaris/sim/cascade_backends.py`
**函数**: `_check_no_feedback_loops`（第 581-630 行）

**修改内容**:
1. **邻接表构建**（第 598-605 行）: 从双向添加改为单向有向边
   - 旧: `graph[inst1].add(inst2); graph[inst2].add(inst1)`（无向）
   - 新: `graph[inst1].add(inst2)`（有向，inst1→inst2）
   - 物理依据: 连接 `(p1, p2)` 中 p1 是输出端口→p2 是输入端口，信号方向 inst1→inst2

2. **DFS 环检测**（第 610-619 行）: 移除父节点跳过逻辑，改用标准有向图 rec_stack 检测
   - 旧: `has_cycle(node, parent)` 跳过父节点，环长度 ≥ 3
   - 新: `has_cycle(node)` 使用 rec_stack（递归栈）检测有向环，两节点环 A→B→A 可检测

3. **注释更新**（第 587 行）: 从"无向图，环长度 ≥ 3"改为"有向图，反馈环路检测"

### 2.3 验证步骤
1. 运行 `pytest tests/test_cascade_backends.py::TestCascadeAdditive::test_cascade_additive_feedback_raises -v`
2. 运行完整 R03 测试: `pytest tests/test_cascade_backends.py -v`（期望 30 passed）
3. 运行完整测试套件: `pytest tests/ -x --timeout=120`（确认无新增失败）
4. AST 检查无 fall-back: `test_no_fallback_in_cascade_backends` 通过

### 2.4 R03 完成交付清单
- [x] 创建 `cascade_backends.py`（KLU+Redheffer+Additive+Forward-only+auto）
- [x] 修复 `cascade.py` 实例名替换 bug
- [x] 更新 `__init__.py` 导出
- [x] 创建 `test_cascade_backends.py`（30 个测试）
- [x] 修复 4 个测试失败（端口冲突、环检测、KLU一致性、fall-back检测）
- [ ] **修复最后 1 个失败测试**（环检测有向图改造）
- [ ] 完整回归测试
- [ ] 更新操作记录.md（第 99 轮）
- [ ] Git 提交合并 main

---

## 三、R04-R36 依次执行计划

### 3.1 阶段 1 剩余（R04-R06）：sax + simphony 完成

#### R04（2026-10）：子网络增长算法深度优化
**目标**: 综合得分 6.6 → 6.7
**核心交付**:
1. 块三对角矩阵子网络分解算法（块版本 Thomas 算法）
2. Schur 补计算（S = D - C·A⁻¹·B）消去内部端口
3. 基于 DAG（有向无环图）的并行调度
4. 10000+ 器件电路测试

**新增文件**:
- `/workspace/src/polaris/sim/subnetwork_decomp.py` — 块三对角分解 + Schur 补
- `/workspace/src/polaris/sim/dag_scheduler.py` — DAG 并行调度
- `/workspace/tests/test_subnetwork_decomp.py`
- `/workspace/tests/test_dag_scheduler.py`

**验收标准**:
- 10000+ 器件电路求解 < 60 秒
- DAG 并行调度 8 核 CPU 加速 6+ 倍
- 块三对角求解比稠密求解快 100+ 倍
- Schur 补与直接求解对比误差 < 1e-10

#### R05（2026-11）：JAX 加速集成
**目标**: 综合得分 6.7 → 6.8
**核心交付**:
1. 核心数据结构从 numpy 迁移到 jax.numpy（保持 API 兼容）
2. JAX JIT 编译，性能提升 5-20 倍
3. 自动微分（grad/VJP/JVP）支持梯度优化
4. GPU 加速，大规模电路性能提升 50+ 倍
5. 蒙特卡洛分析（vmap 并行）

**新增文件**:
- `/workspace/src/polaris/sim/jax_backend.py` — JAX 后端核心
- `/workspace/src/polaris/sim/autodiff.py` — 自动微分模块
- `/workspace/src/polaris/sim/monte_carlo.py` — 蒙特卡洛分析
- `/workspace/tests/test_jax_backend.py`
- `/workspace/tests/test_autodiff.py`
- `/workspace/tests/test_monte_carlo.py`

**验收标准**:
- JIT 编译性能提升 5+ 倍
- 自动微分通过有限差分验证（误差 < 1e-6）
- 蒙特卡洛分析支持 1000+ 变体
- GPU 加速 50+ 倍（大规模电路）
- numpy/JAX 双后端切换通过测试

#### R06（2026-12）：阶段 1 验收里程碑
**目标**: 综合得分 6.8（阶段 1 终点）
**核心交付**:
1. sax + simphony 所有核心功能 100% 复刻确认
2. 测试覆盖率 ≥ 90%
3. 大规模电路（10000+ 器件）稳定求解
4. JAX 加速性能达标
5. 与 sax/simphony 回归测试误差 < 1e-10
6. 阶段 2（R07-R12）规划

**新增文件**:
- `/workspace/tests/test_stage1_acceptance.py` — 18 项验收清单
- `/workspace/docs/stage1_acceptance_report.md` — 阶段 1 验收报告

**验收标准**（18 项）:
- sax API 兼容性 ≥ 95%
- simphony API 兼容性 ≥ 95%
- 器件模型数量 ≥ 20
- KLU 后端 100%（1000+ 器件电路测试）
- 向量化 Redheffer 星积 5+ 倍加速
- DAG 调度、Schur 补、块三对角求解、并行合并全部 100%
- JAX 双后端、JIT、自动微分、GPU 加速、蒙特卡洛全部达标
- 综合得分 6.8

### 3.2 阶段 2（R07-R12）：KLayout + gdsfactory 对齐
**目标**: 综合得分 6.8 → 7.4
**核心交付**:
- R07: GDS 流读写 + 层映射
- R08: KLayout DRC runset 完整集成
- R09: KLayout LVS 集成
- R10: gdsfactory 组件库对齐
- R11: gdsfactory routing 对齐
- R12: 阶段 2 验收

### 3.3 阶段 3（R13-R18）：Aspic + VPIphotonics 对齐
**目标**: 综合得分 7.4 → 7.9
**核心交付**:
- R13: Aspic 光波导仿真对齐
- R14: Aspic 器件库扩展
- R15: VPIphotonics 传输仿真对齐
- R16: VPIphotonics 模型库扩展
- R17: VPIphotonics 系统级仿真
- R18: 阶段 3 验收

### 3.4 阶段 4（R19-R24）：L-Edit + OptoDesigner 对齐
**目标**: 综合得分 7.9 → 8.4
**核心交付**:
- R19: L-Edit 版图编辑对齐
- R20: L-Edit DRC 集成
- R21: OptoDesigner 光子布局对齐
- R22: OptoDesigner 布线对齐
- R23: OptoDesigner 仿真集成
- R24: 阶段 4 验收

### 3.5 阶段 5（R25-R30）：IPKISS + Tidy3D 对齐
**目标**: 综合得分 8.4 → 8.8
**核心交付**:
- R25: IPKISS 流程对齐
- R26: IPKISS 器件库对齐
- R27: Tidy3D FDTD 仿真对齐
- R28: Tidy3D 优化器集成
- R29: Tidy3D 多物理场仿真
- R30: 阶段 5 验收

### 3.6 阶段 6（R31-R36）：Lumerical + AlphaChip 对齐
**目标**: 综合得分 8.8 → 9.2
**核心交付**:
- R31: Lumerical FDTD 对齐
- R32: Lumerical MODE 对齐
- R33: Lumerical INTERCONNECT 对齐
- R34: AlphaChip 布局对齐
- R35: AlphaChip 布线对齐
- R36: 阶段 6 验收 + 36 月总验收

---

## 四、每个路标的统一执行流程

每个路标（R03-R36）严格按以下流程执行：

### 步骤 1: 路标启动
1. 读取对应路标文档 `/workspace/docs/roundmap/R{XX}.md`
2. 确认交付目标、验收标准、创新点
3. 创建 TodoList 任务

### 步骤 2: 代码实现
1. 按路标文档的"改进计划路线图"实现代码
2. 新增/修改文件严格遵守项目规则（src layout、单文件 ≤800 行、单函数 ≤80 行）
3. 禁止 fall-back 兜底（规则 14.1）
4. 学术诚信：所有公式、参数、阈值标注来源（规则 18）

### 步骤 3: 测试验证
1. 创建对应测试文件 `/workspace/tests/test_{module}.py`
2. 测试覆盖率 ≥ 80%（核心模块 ≥ 90%）
3. 运行 `pytest tests/test_{module}.py -v` 确认全部通过
4. 运行完整测试套件 `pytest tests/ -x --timeout=120` 确认无新增失败

### 步骤 4: 文档更新
1. 更新路标文档 `/workspace/docs/roundmap/R{XX}.md`（标注完成状态）
2. 更新 `/workspace/docs/36-RoundMap.md`（进度状态）
3. 更新 `/workspace/docs/commercial_tools_feature_matrix.md`（得分变化）

### 步骤 5: 操作记录
1. 在 `/workspace/操作记录.md` 末尾追加新一轮记录
2. 记录内容：轮次、日期、路标编号、交付内容、测试结果、Git commit hash

### 步骤 6: Git 提交合并 main
1. `git add` 相关文件
2. `git commit -m "R{XX}: {路标标题}"` （Conventional Commits）
3. `git checkout main && git merge trae/solo-agent-QtGqG4-ai-Light`
4. `git push origin main`
5. `git checkout trae/solo-agent-QtGqG4-ai-Light` 切回开发分支

### 步骤 7: 进入下一路标
1. 标记当前路标 TodoList 为 completed
2. 启动下一路标（步骤 1）

---

## 五、R03 立即执行计划（详细）

### 5.1 修改 `_check_no_feedback_loops`

**文件**: `/workspace/src/polaris/sim/cascade_backends.py`
**位置**: 第 581-630 行

**修改前**（无向图 DFS，跳过父节点）:
```python
def _check_no_feedback_loops(instances, connections):
    # 构建无向图
    graph = defaultdict(set)
    for p1, p2 in connections:
        inst1 = p1.split(".", 1)[0]
        inst2 = p2.split(".", 1)[0]
        if inst1 != inst2:
            graph[inst1].add(inst2)
            graph[inst2].add(inst1)  # 双向（无向）
    
    # DFS 跳过父节点
    def has_cycle(node, parent):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                if has_cycle(neighbor, node):
                    return True
            elif neighbor != parent:  # 跳过父节点
                return True
        return False
```

**修改后**（有向图 DFS，rec_stack 检测）:
```python
def _check_no_feedback_loops(instances, connections):
    # 构建有向图：连接 (p1, p2) 表示信号从 inst1 流向 inst2
    graph = defaultdict(set)
    for p1, p2 in connections:
        inst1 = p1.split(".", 1)[0]
        inst2 = p2.split(".", 1)[0]
        if inst1 != inst2:
            graph[inst1].add(inst2)  # 单向（有向）
    
    # 有向图 DFS 环检测（标准 rec_stack 算法）
    visited = set()
    rec_stack = set()
    
    def has_cycle(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:  # 在递归栈中 = 有向环
                return True
        rec_stack.remove(node)
        return False
```

### 5.2 验证测试
1. `pytest tests/test_cascade_backends.py::TestCascadeAdditive::test_cascade_additive_feedback_raises -v` → 期望 passed
2. `pytest tests/test_cascade_backends.py -v` → 期望 30 passed
3. `pytest tests/test_cascade.py -v` → 确认无回归
4. `pytest tests/ -x --timeout=120 --ignore=tests/test_tilos_benchmark.py` → 确认无新增失败

### 5.3 更新操作记录
在 `/workspace/操作记录.md` 末尾追加第 99 轮记录：
- 路标: R03
- 日期: 2026-06-22
- 交付: S 参数级联优化完成（KLU+Redheffer+Additive+Forward-only+auto）
- 修复: 环检测从无向图改为有向图，正确识别两节点反馈环
- 测试: 30 passed（R03），完整套件无新增失败
- Git commit: {hash}

### 5.4 Git 提交合并
```bash
git add src/polaris/sim/cascade_backends.py tests/test_cascade_backends.py 操作记录.md
git commit -m "R03: S参数级联优化 - KLU后端+Redheffer星积+有向图环检测"
git checkout main && git merge trae/solo-agent-QtGqG4-ai-Light
git push origin main
git checkout trae/solo-agent-QtGqG4-ai-Light
```

---

## 六、假设与决策

### 6.1 假设
1. klujax 0.5.0 已安装可用（前一轮已确认）
2. scipy.sparse.linalg.splu 可用（KLU 等价实现）
3. JAX 已安装（R05 需要）
4. Git 远程仓库配置正确，可 push
5. 测试套件基线：2477 passed, 16 skipped, 1 failed（test_tilos_benchmark 预存）

### 6.2 决策
1. **R03 环检测修复方案**: 选择有向图 DFS（方案 A），因为物理语义上连接 (p1, p2) 是有向的（p1 输出→p2 输入），有向图能正确识别两节点反馈环
2. **每个路标完整交付**: 代码+测试+文档+操作记录+Git提交，不留半成品
3. **依次执行不等待**: R03 完成后立即启动 R04，依此类推
4. **禁止 fall-back**: 所有数值问题显式告警退出，不静默兜底
5. **学术诚信**: 所有公式、参数、阈值标注来源（论文/教材/标准）

### 6.3 风险与缓解
1. **风险**: R03 修复后可能暴露其他隐藏问题
   - **缓解**: 完整回归测试，发现问题立即修复
2. **风险**: R04 块三对角算法实现复杂
   - **缓解**: 参考路标文档的学术论文（Thomas 算法、Schur 补），逐步实现
3. **风险**: R05 JAX 与 numpy 双后端兼容性
   - **缓解**: 保持 API 兼容，使用 set_backend 切换

---

## 七、验证步骤

### 7.1 R03 验证
- [ ] `test_cascade_additive_feedback_raises` 通过
- [ ] R03 测试 30 passed
- [ ] 完整测试套件无新增失败
- [ ] 操作记录更新
- [ ] Git 提交合并 main

### 7.2 R04-R36 验证（每个路标）
- [ ] 路标文档中的验收标准全部通过
- [ ] 新增测试全部通过
- [ ] 完整测试套件无新增失败
- [ ] 操作记录更新
- [ ] Git 提交合并 main
- [ ] 综合得分提升至目标值

### 7.3 阶段验收（R06/R12/R18/R24/R30/R36）
- [ ] 阶段验收清单全部通过
- [ ] 阶段验收报告生成
- [ ] 下一阶段规划完成

---

## 八、执行顺序总览

```
R03（当前）→ R04 → R05 → R06（阶段1验收）
→ R07 → R08 → R09 → R10 → R11 → R12（阶段2验收）
→ R13 → R14 → R15 → R16 → R17 → R18（阶段3验收）
→ R19 → R20 → R21 → R22 → R23 → R24（阶段4验收）
→ R25 → R26 → R27 → R28 → R29 → R30（阶段5验收）
→ R31 → R32 → R33 → R34 → R35 → R36（阶段6总验收）
```

每个路标完整交付后立即进入下一路标，不等待。
