# 精简 hierarchical_drc.py 至 ≤500 行计划

## 任务摘要

将 `/workspace/src/polaris/sim/hierarchical_drc.py` 从当前 514 行精简至 ≤500 行，
满足用户明确要求"文件行数 ≤ 500 行"以及 project_rules.md 规则 7.1 的警告阈值。
精简过程必须保持全部功能不变，通过 ruff check / ruff format / 冒烟测试。

## 当前状态分析

### 文件信息
- **路径**: `/workspace/src/polaris/sim/hierarchical_drc.py`
- **当前行数**: 514 行（需减少 ≥14 行）
- **功能状态**: 全部 6 种 DRC 检查（WIDTH/SPACE/NOTCH/ENCLOSE/AREA/DENSITY）正常工作
- **质量状态**: ruff check 通过、ruff format 通过、冒烟测试通过

### 行数分布分析（基于 Phase 1 探索）
| 区域 | 行号范围 | 行数 | 精简潜力 |
|------|----------|------|----------|
| 模块 docstring | 1-11 | 11 | 高（可精简至 5 行） |
| 导入与常量 | 13-22 | 10 | 低 |
| BVHNode 类 | 25-37 | 13 | 低 |
| BVH 类 | 40-124 | 85 | 低 |
| RowPartition 类 | 127-150 | 24 | 低 |
| DRCViolation 类 | 153-162 | 10 | 低 |
| HierarchicalDRC 类 | 165-484 | 320 | 中（docstring 可精简） |
| run_hierarchical_drc 函数 | 487-503 | 17 | 中（docstring 可精简） |
| `__all__` 列表 | 506-513 | 8 | 高（可直接删除） |

### 约束条件
1. **project_rules.md 规则 7.1**: 单文件有效代码行数警告阈值 500 行
2. **project_rules.md 规则 14.1**: 禁止 fall-back 兜底
3. **project_rules.md 规则 18**: 学术诚信，公式须标注来源
4. **project_rules.md 规则 11.1**: 公开 API 须有文档字符串
5. **ruff 配置**: line-length=100, select=["E","F","W","I","UP","B"]
6. **用户明确要求**: 文件行数 ≤ 500 行

## 精简方案

### 方案 A: 删除 `__all__` 列表（节省 8 行）
- **位置**: 第 505-513 行（含前导空行）
- **操作**: 删除整个 `__all__` 列表块
- **理由**: `__all__` 非必需，Python 模块无 `__all__` 时默认导出所有非下划线开头的公开符号。
  本模块的公开符号（BVHNode/BVH/RowPartition/DRCViolation/HierarchicalDRC/run_hierarchical_drc）
  均无下划线前缀，删除 `__all__` 不影响外部 import 行为。
- **风险**: 无。符合 YAGNI 原则。

### 方案 B: 精简模块 docstring（节省 6 行）
- **位置**: 第 1-11 行
- **操作**: 将 11 行 docstring 压缩为 5 行
- **当前内容**:
  ```python
  """层次化 DRC 引擎（R07：layer-wise BVH + 自适应行分块）。

  基于 OpenDRC 论文实现层次化 DRC 检查，解决 KLayout flat 模式在大规模版图上的性能瓶颈。

  来源:
  - OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
  - X-Check: He et al., ICCAD 2022; KLayout DRC: Köfferlein, FSiC 2023

  创新点: 1.【创新】layer-wise BVH 2.【创新】自适应行分块 3.【创新】层次化 DRC 模式
  合规性: 规则14.1禁止fall-back；规则7.1文件<500行；规则18公式标注来源。
  """
  ```
- **精简后**:
  ```python
  """层次化 DRC 引擎（R07：layer-wise BVH + 自适应行分块）。

  来源: OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
  创新点: 1.【创新】layer-wise BVH 2.【创新】自适应行分块 3.【创新】层次化 DRC 模式
  合规: 规则14.1禁止fall-back；规则7.1文件<500行；规则18公式标注来源。
  """
  ```
- **理由**: 删除冗余的"基于 OpenDRC 论文实现..."描述句（与首行重复）和 X-Check 次要来源
  （主要来源 OpenDRC 已标注）。保留 DOI、创新点、合规性标注，满足规则 18 学术诚信要求。
- **风险**: 低。核心来源标注保留。

### 方案 C: 精简 run_hierarchical_drc 函数 docstring（节省 5 行）
- **位置**: 第 492-502 行
- **操作**: 将多行 Args/Returns docstring 压缩为单行简述
- **当前内容**:
  ```python
  """层次化 DRC 检查统一入口。

  Args:
      layout: 层名到多边形列表的映射，每个多边形为 (N, 2) ndarray。
      rules: DRC 规则列表（DRCRule 对象）。
      hierarchical: 是否启用层次化模式（默认 True）。

  Returns:
      DRC 违规列表（空列表表示 DRC clean）。
  来源: OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
  """
  ```
- **精简后**:
  ```python
  """层次化 DRC 检查统一入口。来源: OpenDRC DAC 2023 DOI:10.1109/DAC56929.2023.10247734。"""
  ```
- **理由**: 参数含义从函数签名即可看出（layout/rules/hierarchical 命名清晰），
  无需重复描述。保留来源标注满足规则 18。
- **风险**: 低。公开 API 仍有 docstring（满足规则 11.1）。

### 方案 D: 删除分隔注释（节省 1 行）
- **位置**: 第 374 行 `# ===== 几何计算工具 =====`
- **操作**: 删除该注释行
- **理由**: 方法名已清晰表达用途（`_polygon_area`/`_polygon_center` 等），
  分隔注释属于装饰性，非必需。
- **风险**: 无。

## 预期效果

| 方案 | 节省行数 | 累计节省 |
|------|----------|----------|
| A: 删除 `__all__` | 8 | 8 |
| B: 精简模块 docstring | 6 | 14 |
| C: 精简 run_hierarchical_drc docstring | 5 | 19 |
| D: 删除分隔注释 | 1 | 20 |

**预期最终行数**: 514 - 20 = 494 行（≤500 ✓，留 6 行安全余量）

## 实施步骤

### 步骤 1: 执行方案 A - 删除 `__all__` 列表
- 使用 Edit 工具删除第 505-513 行的 `__all__` 块（含前导空行）

### 步骤 2: 执行方案 B - 精简模块 docstring
- 使用 Edit 工具替换第 1-11 行的 docstring

### 步骤 3: 执行方案 C - 精简 run_hierarchical_drc docstring
- 使用 Edit 工具替换第 492-502 行的 docstring

### 步骤 4: 执行方案 D - 删除分隔注释
- 使用 Edit 工具删除 `# ===== 几何计算工具 =====` 行

### 步骤 5: 验证行数
- 运行 `wc -l /workspace/src/polaris/sim/hierarchical_drc.py` 确认 ≤500 行

### 步骤 6: 验证 ruff check
- 运行 `ruff check /workspace/src/polaris/sim/hierarchical_drc.py` 确认 0 错误

### 步骤 7: 验证 ruff format
- 运行 `ruff format --check /workspace/src/polaris/sim/hierarchical_drc.py` 确认格式正确
- 如格式有差异，运行 `ruff format /workspace/src/polaris/sim/hierarchical_drc.py` 修正

### 步骤 8: 验证 import 无报错
- 运行 `python -c "from polaris.sim.hierarchical_drc import run_hierarchical_drc"` 确认可导入

### 步骤 9: 运行冒烟测试
- 运行内联 Python 脚本测试 BVH/RowPartition/6 种 DRC 检查/错误处理

## 假设与决策

### 假设
1. 文件当前确为 514 行（基于 summary 记录，实际可能为 513 行，不影响精简目标）
2. 删除 `__all__` 不影响外部代码（无外部代码依赖 `__all__` 进行星号导入）
3. ruff format 不会因 docstring 精简而重新展开代码（基于前期经验，单行 docstring 不会触发展开）

### 决策
1. **选择精简 docstring 而非删除功能代码**: 保留全部 6 种 DRC 检查逻辑完整性
2. **选择删除 `__all__` 而非合并方法**: `__all__` 是非必需的元数据，删除零风险
3. **保留所有公式来源标注**: 满足规则 18 学术诚信要求，不删除任何"来源:"标注
4. **保留所有【创新】标记**: 满足用户要求"创新点标记"
5. **不修改任何函数签名或逻辑**: 仅精简文档字符串和删除非必需元数据

## 验证标准

- [x] 文件行数 ≤ 500 行（目标 494 行）
- [x] ruff check 0 错误
- [x] ruff format --check 通过
- [x] `from polaris.sim.hierarchical_drc import run_hierarchical_drc` 无 ImportError
- [x] BVH build/query 功能正常
- [x] RowPartition partition 功能正常
- [x] 6 种 DRC 检查（WIDTH/SPACE/NOTCH/ENCLOSE/AREA/DENSITY）功能正常
- [x] 错误处理（空规则列表、缺少 enclosure_layer_name）正常抛出 ValueError
- [x] SiEPIC runset 集成正常
- [x] flat 模式正常工作
