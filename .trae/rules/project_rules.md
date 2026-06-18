# 项目规则 (Project Rules)

本文件定义了 PoLaRIS（光弈）光电子AI智能布局布线引擎项目的强制开发规则。所有任务执行必须严格遵守。

## 规则 1：方案检索与代码提交纪律（强制）

每一个小任务（SubTask）在动手实现之前与实现过程中，都必须执行以下流程：

### 1.1 方案检索（动手前必做）
- 必须检索各种期刊、论文、白皮书以及各大高校的论文论坛，寻找最合理、最优秀的解决方案。
- 检索来源至少覆盖：
  - 学术期刊与会议：Nature、Nature Photonics、Optics Express、Optics Letters、Light: Advanced Manufacturing、IEEE JSTQE、NeurIPS、ICCAD、DAC、Advanced Optics Photonics
  - 工艺手册与白皮书：IMEC、AMF、AIM Photonics、CompoundTek、IHP、LioniX、NOEIC、三星、台积电等 foundry PDK 与白皮书
  - 高校论文论坛与开放仓库：arXiv、ResearchGate、IEEE Xplore、GitHub（如 Thinklab-SJTU/EDA-AI）、高校课题组主页
  - 技术博客与产业分析：latitudeda.com、iccsz.com、cloud.tencent.com、mdpi.com 等
- 每个方案须记录：来源标题、作者/机构、年份、网址 URL，写入对应模块的 `source` 字段或文档。
- 禁止使用未经检索核实的参数或方案；禁止假数据。

### 1.2 代码提交纪律（每 5 分钟一次）
- 实现过程中，每 5 分钟必须向远端 `main` 分支提交一次代码。
- 提交流程：
  1. `git add` 相关变更文件（按文件名精确添加，禁止 `git add -A`/`git add .`）
  2. `git commit -m "<type>: <简述>"`，type 遵循 Conventional Commits（feat/fix/docs/refactor/test/chore）
  3. `git push origin main`
- 若 5 分钟内仍在进行复杂改动，先创建一个可编译/可测试的中间状态再提交，保证 `main` 分支始终可用。
- 提交前必须通过本地 lint/typecheck（如 ruff、mypy、pytest 冒烟测试）。
- 禁止 force push 到 `main`；禁止提交含密钥/凭据的文件。

### 1.3 完整产品流程遵守
- 完整的产品研发流程必须遵守，不得跳过：
  1. 需求与方案检索（本规则 1.1）
  2. 设计（数据结构、接口、模块划分）
  3. 实现（编码 + 每 5 分钟提交）
  4. 测试（单元测试 + 集成测试 + 约束合规测试）
  5. 验证（按 checklist.md 逐项核对）
  6. 文档与来源溯源更新
- 任何阶段不得省略来源标注与测试验证。

## 规则 2：开源工具最大化集成（强制）

能直接集成的开源工具全部集成进来，不好集成的用 Python 100% 复刻一个可用的。

### 2.1 必须直接集成的开源工具（pip 安装即用）

| 工具 | 用途 | 来源 |
|------|------|------|
| **gdsfactory** | 版图生成、PDK、自动布线、GDS/OASIS 导出 | https://gdsfactory.github.io/gdsfactory/ |
| **klayout** (klayout python) | DRC 规则检查、LVS、版图查看 | https://www.klayout.de/ |
| **networkx** | 器件连接图建模、最短路径、图算法 | https://networkx.org/ |
| **numpy / scipy** | 数值计算、优化求解 | https://numpy.org/ |
| **torch** | GNN/PPO 神经网络、强化学习 | https://pytorch.org/ |
| **gymnasium** | 布局/布线 RL 环境（observation/action/reward） | https://gymnasium.farama.org/ |
| **matplotlib** | 版图渲染、拥塞热力图 | https://matplotlib.org/ |
| **shapely** | 几何运算（多边形、缓冲区、相交检测） | https://shapely.readthedocs.io/ |
| **pyyaml** | 网表/配置序列化 | https://pyyaml.org/ |

### 2.2 可选集成（按需引入）

| 工具 | 用途 | 来源 |
|------|------|------|
| **gdstk** | 高性能 GDS 文件读写（替代 gdspy） | https://heitzmann.github.io/gdstk/ |
| **MEEP** | FDTD 电磁仿真（器件参数验证） | https://meep.readthedocs.io/ |
| **Simphony** | 光子电路 S 参数仿真 | https://simphonyphotonics.readthedocs.io/ |
| **SAX** | 光子电路频率域仿真 | https://flaport.github.io/sax/ |
| **SiPANN** | 硅光器件模型（耦合器、环谐振器） | https://sipann.readthedocs.io/ |
| **femwell** | FEM 模式求解器 | https://helgegehring.github.io/femwell/ |
| **meow** | 模式求解器 | https://github.com/flaport/meow |
| **lygadgets** | KLayout Python 工具链 | https://github.com/atait/lygadgets |
| **SiEPIC-EBeam-PDK** | 开源硅光 PDK（UBC/SiEPIC） | https://github.com/gdsfactory/ubc |
| **cspdk** | Cornerstone 开源 PDK | https://github.com/gdsfactory/cspdk |
| **vtt PDK** | VTT 开源 SiN PDK | https://github.com/gdsfactory/vtt |

### 2.3 需 Python 100% 复刻的工具（无法直接集成时）

以下能力若无合适开源库或集成成本过高，须用纯 Python 100% 复刻一个可用版本：

| 能力 | 复刻方案 | 参考 |
|------|----------|------|
| 波导约束布线器 | A*/Lee 算法 + 弯曲半径/间距/等长约束 | NeurIPS 2022 Cheng et al. https://openreview.net/pdf?id=uNYqDfPEDD8 |
| 光子器件 PDK Lite | dataclass + 真实文献参数（spec.md 已列来源） | 本项目 spec.md |
| GNN 状态编码器 | PyTorch message-passing GNN | R-GCN, Basso et al. NeurIPS 2025 |
| PPO 强化学习 | actor-critic + clip + GAE | Stable-Baselines3 / CleanRL 参考 |
| 拥塞热力图 | numpy 栅格化 + matplotlib | — |
| 网表解析器 | YAML/JSON → networkx 图 | — |
| HPWL 线长估计 | 半周长线长公式 | 经典 EDA 方法 |
| S 弯/弯曲路径生成 | 贝塞尔/欧拉曲线 | 光波导标准方法 |

### 2.4 集成原则
1. **优先直接集成**：能用 pip 安装的开源库，直接集成，不重复造轮子
2. **复刻须 100% 可用**：不好集成的，用纯 Python 复刻一个完整可用的版本，不留半成品
3. **来源须标注**：每个集成的工具或复刻的算法，记录来源 URL
4. **依赖最小化**：核心功能（PDK + 布局 + 布线 + 训练）的依赖须精简，仿真类工具（MEEP/Simphony）作为可选依赖
5. **不依赖商业工具**：禁止依赖 Lumerical/IPKISS/Tidy3D 等商业软件作为核心功能

### 2.5 参考来源
- GDSFactory 论文 (CLEO 2026): https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
- Awesome Photonics: https://github.com/joamatab/awesome_photonics
- Simphony 文档: https://simphonyphotonics.readthedocs.io/en/stable/
- Prefab: Python for photonics: https://docs.prefabphotonics.com/python-for-photonics/

## 规则 3：难安装开源工具的 100% Python 复刻纪律（强制）

对于开源但安装困难（编译依赖重、平台不兼容、无 wheel、需系统级依赖等）的工具，
**必须**用纯 Python 100% 复刻一个可用版本，并满足以下要求：

### 3.1 复刻触发条件
满足以下任一条件即触发 100% 复刻：
- 该工具为开源（MIT/BSD/Apache/GPL 等开源协议）但无对应平台的预编译 wheel
- 安装需复杂系统级依赖（如 C++/Fortran 编译链、MPI、CUDA toolkit 非标准路径）
- 在目标运行环境（Linux 沙箱/CI）中 `pip install` 失败或不可用
- 集成成本（编译/配置/调试）高于自行复刻等价实现

### 3.2 复刻质量要求（100% 一致）
- **逻辑一致**：复刻实现的代码逻辑须与原开源工具 100% 一致，包括算法步骤、
  边界条件、数值处理顺序，不得简化核心算法
- **行为对比验证**：须编写对比测试，对同一输入分别调用原工具（若可临时安装）
  与复刻实现，断言输出一致（浮点数允许 1e-9 容差）；若原工具无法安装，
  须用原仓库的官方测试用例/文档示例作为基准验证复刻正确性
- **来源标注**：复刻代码须在文件头注明原仓库 URL、协议、commit/版本号
- **接口兼容**：复刻模块须暴露与原工具等价的公开 API（函数名/参数名/返回值），
  使上层代码可无缝切换
- **不留半成品**：复刻须覆盖项目实际使用的全部功能子集，禁止只复刻入口而留空实现

### 3.3 复刻范围（按需）
以下能力若对应开源工具安装困难，按本规则 100% 复刻：
| 能力 | 原工具 | 复刻要点 |
|------|--------|----------|
| GDS 读写 | gdstk/gdspy（C++ 扩展难装时） | 纯 Python GDSII 流式写入（record-based） |
| DRC 检查 | klayout（Ruby/原生绑定难装时） | shapely 几何规则检查复刻 |
| 模式求解 | meow/femwell（FEM 依赖重） | 有效折射率法解析求解 |
| S 参数仿真 | SAX/Simphony（依赖链长） | 传输矩阵 + S 参数级联 |

### 3.4 验证与回归
- 每个复刻模块须附带对比测试（`tests/test_replica_*.py`）
- CI 中优先尝试 `pip install` 原工具；安装失败时自动跳过对比测试但保留复刻自测
- 复刻实现须通过 `ruff` + `mypy` 检查

## 规则 4：工业标准代码质量门禁（强制）

按照工业标准完成代码编写和管理，所有代码必须通过质量门禁检查方可提交。
门禁脚本位于 `scripts/code_quality_gate.py`，CI 与本地提交前必须运行通过。

### 4.1 文件规模硬性限制（触发即必须重构）

| 指标 | 警告阈值 | 硬性上限（触发重构） | 依据 |
|------|----------|----------------------|------|
| 单文件大小 | 80 KB | **120 KB** | 工业实践：大文件降低可读性与可维护性 |
| 单文件有效代码行数 | 500 行 | **800 行** | PEP 8/Google Style：目标 300-500 行/文件 |
| 单函数有效代码行数 | 40 行 | **80 行** | Google Python Style Guide：超过 40 行应考虑拆分 |
| 单函数圈复杂度 (McCabe) | 10 | **15** | McCabe 1976 / NIST ISO 25010：V(G)≤10 为可维护 |
| 单函数参数个数 | 5 | **7** | Google Style：参数过多降低可读性 |
| 单类方法数 | 20 | **30** | 单一职责原则 |
| 嵌套深度 | 4 | **5** | 深嵌套降低可读性，应用卫语句扁平化 |

**硬性上限含义**：超过即触发 CI 门禁失败，必须重构拆分后方可合并。
**警告阈值含义**：CI 输出警告，建议但不阻断。

**测试文件豁免**：`tests/` 目录下的文件和 `test_*.py` 文件默认**不受质量门禁管控**
（测试代码以可读性和覆盖率为优先，函数/复杂度限制放宽）。如需检查测试文件，
使用 `--include-tests` 参数。测试文件仍须通过 ruff lint 和 pytest。

来源：
- Google Python Style Guide 函数长度: https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules.html#id17
- PEP 8 行宽与风格: https://peps.python.org/pep-0008/
- McCabe 圈复杂度: McCabe, "A Complexity Measure", IEEE TSE 1976, https://ieeexplore.ieee.org/document/1702388
- NIST ISO/IEC 25010 可维护性: https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
- 文件行数最佳实践: https://alchemiststudios.ai/articles/python-linting-sop.html

### 4.2 重构触发后的操作流程

当文件/函数超过硬性上限时，必须执行以下流程：

1. **停止新增功能**：在该文件/函数上停止新增功能代码
2. **分析职责**：分析文件/函数承担的职责，识别可拆分的边界
3. **拆分模块**：按单一职责原则拆分为多个子模块/子函数
4. **保持接口兼容**：拆分后通过 `__init__.py` 重导出，保持上层调用不变
5. **更新测试**：拆分后更新对应测试，确保覆盖率不下降
6. **通过门禁**：重新运行 `python scripts/code_quality_gate.py` 确认通过

### 4.3 圈复杂度 (Cyclomatic Complexity) 标准

圈复杂度衡量函数内线性独立路径数，反映测试难度与缺陷风险。

| 等级 | 复杂度范围 | 风险评估 | 处理策略 |
|------|-----------|----------|----------|
| A | 1-5 | 简单，低风险 | 无需处理 |
| B | 6-10 | 适中，可接受 | 正常开发 |
| C | 11-15 | 偏高，需关注 | 建议重构（Extract Method） |
| D-F | 16+ | 高风险，难测试 | **必须重构** |

降低复杂度的重构手法：
- **Extract Method（提取方法）**：将复杂条件分支提取为独立函数
- **Guard Clauses（卫语句）**：用提前返回替代嵌套 if-else
- **Strategy Pattern（策略模式）**：用多态替代 switch/elif 链
- **State Machine（状态机）**：用状态机替代复杂状态判断

来源：
- McCabe 1976 原始论文: https://ieeexplore.ieee.org/document/1702388
- Sourcegraph 复杂度指南: https://sourcegraph.com/blog/cyclomatic-complexity-what-it-is-and-how-to-reduce-it
- Radon 工具文档: https://radon.readthedocs.io/

### 4.4 质量门禁脚本（`scripts/code_quality_gate.py`）

门禁脚本自动检查以下指标，任一硬性上限超标即返回非零退出码：

```bash
# 运行质量门禁（CI 与提交前必做）
python scripts/code_quality_gate.py

# 仅检查特定目录
python scripts/code_quality_gate.py polaris/

# 输出 JSON 报告
python scripts/code_quality_gate.py --json > quality_report.json

# 增量模式：仅检查 git 暂存区文件（pre-commit hook 使用）
python scripts/code_quality_gate.py --staged

# 包含测试文件检查（默认排除）
python scripts/code_quality_gate.py --include-tests
```

检查项：
1. 文件大小（KB）与有效代码行数（SLOC，去除空行与注释）
2. 每个函数的有效代码行数
3. 每个函数的圈复杂度（基于 AST 决策节点计数）
4. 函数参数个数
5. 类方法数
6. 嵌套深度

### 4.5 Pre-commit Hook 自动门禁（强制）

**每次 `git commit` 时自动执行质量门禁，不通过则禁止提交。**

安装方法（项目初始化时执行一次）：
```bash
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Hook 执行的检查（仅检查本次暂存的文件，增量检查）：
1. **质量门禁**：`python scripts/code_quality_gate.py --staged`（规则 4）
2. **Ruff lint**：`ruff check <staged_files>`
3. **Ruff format**：`ruff format --check <staged_files>`
4. **Pytest 冒烟测试**：`pytest tests/ -q -x --tb=short`

任一检查失败即阻止提交（exit 1）。

临时跳过（仅紧急情况，不推荐）：`git commit --no-verify`

## 规则 5：Python 编码风格规范（强制）

### 5.1 基础风格标准

遵循 **PEP 8** + **Google Python Style Guide**，以 ruff 为强制执行工具。

| 规范项 | 标准 | 来源 |
|--------|------|------|
| 行宽 | 88 字符（ruff 默认） | PEP 8 / ruff |
| 缩进 | 4 个空格，禁止 Tab | PEP 8 |
| 编码 | UTF-8 | PEP 8 |
| 引号 | 双引号 `"` | ruff format 默认 |
| 导入顺序 | 标准库 → 第三方 → 本地，组内字母序 | Google Style |
| 命名 | `snake_case` 函数/变量，`CamelCase` 类，`UPPER_CASE` 常量 | PEP 8 |
| 文档字符串 | 三双引号 `"""`，含 Args/Returns/Raises 段 | Google Style / PEP 257 |

来源：
- PEP 8: https://peps.python.org/pep-0008/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide
- PEP 257 文档字符串: https://peps.python.org/pep-0257/

### 5.2 强制工具链

```toml
# pyproject.toml 配置（已在项目中）
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "C90"]  # C90 = mccabe 复杂度

[tool.ruff.lint.mccabe]
max-complexity = 15  # 圈复杂度硬性上限

[tool.ruff.lint.pylint]
max-args = 7          # 函数参数上限
max-branches = 15     # 分支数上限
max-returns = 6       # return 语句上限
max-statements = 50   # 语句数上限
```

提交前必须通过：
```bash
ruff check polaris/ tests/          # lint 检查
ruff format --check polaris/ tests/ # 格式检查
mypy polaris/ --ignore-missing-imports  # 类型检查（可选但推荐）
```

### 5.3 代码组织原则

1. **单一职责**：每个模块/类/函数只做一件事
2. **DRY (Don't Repeat Yourself)**：重复代码提取为公共函数
3. **KISS (Keep It Simple, Stupid)**：优先简单方案，避免过度设计
4. **YAGNI (You Aren't Gonna Need It)**：不实现当前不需要的功能
5. **组合优于继承**：优先用组合而非深层继承链
6. **显式优于隐式**：避免魔法行为，让代码意图清晰

### 5.4 类型注解要求

- 所有公开 API 函数必须有类型注解（参数 + 返回值）
- 内部函数鼓励添加类型注解
- 复杂类型用 `TypeAlias` 或 `Protocol` 定义
- 使用 `from __future__ import annotations` 启用延迟注解求值

来源：PEP 484 类型注解 https://peps.python.org/pep-0484/

## 规则 6：Git 工作流与团队协作规范（强制）

### 6.1 分支策略

采用 **GitHub Flow**（简化版，适合持续部署）：

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 生产就绪代码 | 禁止直接推送，需 CI 通过 + 代码审查 |
| `feature/<name>` | 新功能开发 | 从 `main` 拉出，完成后 PR 合并回 `main` |
| `fix/<name>` | Bug 修复 | 从 `main` 拉出，修复后 PR 合并回 `main` |
| `hotfix/<name>` | 紧急生产修复 | 从 `main` 拉出，优先合并 |

分支命名规范：
- `feature/s-parameter-cascade`
- `fix/euler-bend-first-point`
- `hotfix/grid-index-out-of-bounds`

来源：
- GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow
- Git Best Practices: https://devtoolhub.com/git-best-practices-branching-approvals/

### 6.2 提交规范（Conventional Commits）

提交消息格式：`<type>: <简述>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 重构（不改变功能） |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖变更 |
| `perf` | 性能优化 |
| `style` | 代码格式（不影响功能） |

规范：
- 简述不超过 50 字符，使用祈使句（"添加"而非"添加了"）
- 复杂变更用 HEREDOC 添加正文说明"为什么"
- 一个提交只做一件事，禁止混合不相关变更

来源：Conventional Commits https://www.conventionalcommits.org/

### 6.3 代码审查 (Code Review)

- 所有 PR 必须至少 1 人审查通过方可合并
- PR 描述须包含：变更摘要、变更内容、关联 Issue
- PR 应小而聚焦（建议 < 400 行变更），便于审查
- 审查关注点：正确性、可读性、性能、安全性、测试覆盖
- 禁止自我批准合并自己的 PR

### 6.4 .gitignore 规范

必须忽略的文件类型：
- `__pycache__/`、`*.pyc`、`*.pyo`
- `.env`、`*.key`、`credentials.json`（密钥/凭据）
- `venv/`、`.venv/`、`env/`（虚拟环境）
- `dist/`、`build/`、`*.egg-info/`（构建产物）
- `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`
- `*.gds`、`*.oas`（大型版图文件，按需用 LFS）

## 规则 7：测试规范（强制）

### 7.1 测试覆盖率标准

| 指标 | 标准 | 说明 |
|------|------|------|
| 行覆盖率 | ≥ 80% | 核心模块（pdk/router/trainer）≥ 90% |
| 分支覆盖率 | ≥ 70% | 关键分支必须覆盖 |
| 测试通过率 | 100% | 禁止提交失败测试 |

### 7.2 测试分层

| 层级 | 范围 | 命名规范 | 工具 |
|------|------|----------|------|
| 单元测试 | 单个函数/类 | `test_<module>.py::Test<Class>::test_<behavior>` | pytest |
| 集成测试 | 模块间交互 | `test_integration.py::test_<flow>` | pytest |
| 约束合规测试 | 工艺规则验证 | `test_<constraint>.py` | pytest + shapely |
| 回归测试 | 复刻模块对比 | `test_replica_<tool>.py` | pytest |

### 7.3 测试编写规范

- 每个公开函数至少有 1 个测试
- 测试函数名描述行为：`test_waveguide_phase`（非 `test_wg_1`）
- 遵循 Arrange-Act-Assert (AAA) 模式
- 使用 `pytest.fixture` 共享测试数据
- 浮点比较用 `np.testing.assert_almost_equal`，指定 `decimal` 容差
- 禁止依赖测试执行顺序，每个测试独立

来源：pytest 最佳实践 https://docs.pytest.org/en/stable/explanation/goodpractices.html

## 规则 8：文档规范（强制）

### 8.1 文档字符串 (Docstring)

所有公开模块、类、函数必须有文档字符串，遵循 Google 风格：

```python
def function_name(param1: int, param2: str) -> bool:
    """一行简述函数功能。

    可选的多行详细说明。

    Args:
        param1: 参数1的描述。
        param2: 参数2的描述。

    Returns:
        返回值的描述。

    Raises:
        ValueError: 当 param1 为负数时。
    """
```

来源：PEP 257 https://peps.python.org/pep-0257/

### 8.2 来源标注规范

所有集成的工具、复刻的算法、引用的参数必须标注来源：

```python
"""模块说明。

来源:
- 工具名: https://example.com
- 论文: Author et al., "Title", Conference Year, https://doi.org/...
"""
```

### 8.3 文档维护

- README.md：项目概述、安装、快速开始
- 架构文档：模块划分、数据流、接口设计
- 变更日志 (CHANGELOG.md)：记录版本变更
- 每个规则变更须同步更新本文件

## 规则 9：CI/CD 与自动化（强制）

### 9.1 CI 流水线检查项

每次 PR / push 到 main 必须通过：

```yaml
# .github/workflows/ci.yml（示例）
jobs:
  quality-gate:
    steps:
      - run: python scripts/code_quality_gate.py  # 质量门禁
      - run: ruff check polaris/ tests/            # lint
      - run: ruff format --check polaris/ tests/   # 格式
      - run: mypy polaris/ --ignore-missing-imports  # 类型检查
  test:
    steps:
      - run: python -m pytest tests/ -q --tb=short  # 全量测试
```

### 9.2 提交前检查清单

提交代码前必须逐项确认：

- [ ] `ruff check` 通过（0 错误）
- [ ] `ruff format --check` 通过
- [ ] `python scripts/code_quality_gate.py` 通过（0 硬性违规）
- [ ] `pytest tests/ -q` 通过（0 失败）
- [ ] 新增功能有对应测试
- [ ] 公开 API 有文档字符串
- [ ] 集成的工具/算法标注了来源 URL
- [ ] 提交消息符合 Conventional Commits
- [ ] 无密钥/凭据提交

## 规则 10：依赖管理规范（强制）

### 10.1 依赖分类

| 类别 | 文件 | 说明 |
|------|------|------|
| 核心依赖 | `pyproject.toml [project.dependencies]` | PDK/布局/布线/训练必需 |
| 可选依赖 | `pyproject.toml [project.optional-dependencies]` | 仿真类工具（MEEP/Simphony） |
| 开发依赖 | `pyproject.toml [project.optional-dependencies.dev]` | ruff/pytest/mypy 等 |

### 10.2 依赖原则

1. **最小化**：核心功能依赖精简，不引入非必要大型库
2. **版本锁定**：`pyproject.toml` 中指定最低版本，`requirements.txt` 锁定精确版本
3. **禁止商业依赖**：不依赖 Lumerical/IPKISS/Tidy3D 等商业软件
4. **安全审计**：定期运行 `pip-audit` 检查已知漏洞
5. **许可兼容**：所有依赖须与项目许可证兼容（MIT/Apache/BSD）

来源：pip-audit https://pypi.org/project/pip-audit/

## 规则 11：错误处理与日志规范（强制）

### 11.1 异常处理原则

- **不吞异常**：禁止空 `except:` 或 `except Exception: pass`
- **精确捕获**：捕获具体异常类型，而非基类 `Exception`
- **上下文信息**：异常消息包含足够的调试上下文
- **资源释放**：用 `with` 语句或 `try/finally` 确保资源释放
- **边界处理**：在系统边界（用户输入、外部 API）验证并转换异常

```python
# 正确
try:
    result = parse_netlist(path)
except FileNotFoundError as e:
    logger.error("网表文件不存在: %s", path)
    raise FileNotFoundError(f"网表文件不存在: {path}") from e

# 错误
try:
    result = parse_netlist(path)
except:
    pass  # 禁止：吞掉所有异常
```

来源：Google Python Style Guide 异常处理 https://google.github.io/styleguide/pyguide#s2.4-exceptions

### 11.2 日志规范

- 使用 `logging` 模块，禁止 `print()` 用于生产代码
- 日志级别：DEBUG（调试）→ INFO（关键流程）→ WARNING（异常但可处理）→ ERROR（错误）→ CRITICAL（系统级故障）
- 日志格式包含时间、级别、模块、消息
- 敏感信息（密钥/密码）禁止写入日志

```python
import logging
logger = logging.getLogger(__name__)

logger.info("开始布局优化，器件数: %d", n_devices)
logger.warning("波导间距 %.2f μm 低于推荐值 %.2f μm", spacing, min_spacing)
logger.error("DRC 检查失败: %s 共 %d 处违规", rule_name, n_violations)
```

## 规则 12：性能与可维护性规范（推荐）

### 12.1 性能基准

| 操作 | 目标耗时 | 说明 |
|------|----------|------|
| 网表解析（100 器件） | < 100ms | YAML/JSON 解析 |
| A* 布线（单连接） | < 50ms | 网格 100x100 |
| GNN 前向推理 | < 10ms | 单次状态编码 |
| PPO 训练单步 | < 100ms | 单环境步 |
| GDS 导出（100 器件） | < 500ms | 含 DRC |

### 12.2 可维护性检查清单

- [ ] 无重复代码（DRY）
- [ ] 无死代码（未使用的函数/变量/导入）
- [ ] 无魔法数字（常量提取为命名常量）
- [ ] 无深层嵌套（≤ 4 层）
- [ ] 无超长函数（≤ 40 行）
- [ ] 无超长文件（≤ 500 行）
- [ ] 公开 API 有文档字符串
- [ ] 复杂逻辑有注释说明
- [ ] 测试覆盖率达标

## 规则 13：发现 Bug 必须修复纪律（强制）

在执行任何任务的过程中，如果发现了新的 Bug（无论是代码缺陷、逻辑错误、边界条件遗漏，
还是测试暴露的问题），**必须一同解决，禁止带 Bug 提交代码**。

### 13.1 强制要求

1. **发现即记录**：发现 Bug 时，立即在代码注释或任务文档中记录：
   - Bug 描述：什么情况下触发，预期行为 vs 实际行为
   - 根因分析：为什么会产生这个 Bug
   - 修复方案：如何修复，修复了哪些文件
2. **必须修复**：在当前任务提交前必须修复该 Bug，不得留到"以后处理"
3. **必须测试**：修复后必须编写或补充对应的测试用例，验证修复有效
4. **提交备注**：在 commit message 中注明修复了哪些 Bug

### 13.2 Bug 记录格式

在 commit message 或代码注释中记录 Bug 修复：

```
fix: 修复 <模块> 中 <Bug 描述>

Bug: <简述>
根因: <原因分析>
修复: <修复方案>
测试: <新增/修改的测试>
```

### 13.3 禁止行为

- **禁止忽略**：发现 Bug 后不得继续提交而不修复
- **禁止注释掉**：不得用注释掉代码的方式"绕过"Bug
- **禁止 TODO 推迟**：不得用 `# TODO: 修复这个 Bug` 推迟到未来
- **禁止降低标准**：不得为了通过测试而放宽断言容差来"掩盖"Bug

### 13.4 例外情况

仅以下情况允许先提交后修复（但必须在 commit message 中明确标注）：
- Bug 修复需要大量重构，超出当前任务范围 → 创建独立 Issue 跟踪
- Bug 涉及外部依赖升级，无法在当前环境修复 → 记录并创建 Issue
- Bug 为已有遗留问题，与当前任务无关 → 记录但不阻断当前提交

即使例外情况，也必须在 commit message 中写明：
```
注: 发现 <模块> 存在 <Bug 描述>，因 <原因> 暂未修复，已记录 Issue #XXX
```

## 参考来源汇总

| 标准 | 来源 URL |
|------|----------|
| PEP 8 风格指南 | https://peps.python.org/pep-0008/ |
| PEP 257 文档字符串 | https://peps.python.org/pep-0257/ |
| PEP 484 类型注解 | https://peps.python.org/pep-0484/ |
| Google Python Style Guide | https://google.github.io/styleguide/pyguide |
| Google Style 中文版 | https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/ |
| Conventional Commits | https://www.conventionalcommits.org/ |
| McCabe 圈复杂度 (1976) | https://ieeexplore.ieee.org/document/1702388 |
| ISO/IEC 25010 软件质量 | https://iso25000.com/index.php/en/iso-25000-standards/iso-25010 |
| Radon 代码度量工具 | https://radon.readthedocs.io/ |
| Ruff Linter/Formatter | https://docs.astral.sh/ruff/ |
| pytest 最佳实践 | https://docs.pytest.org/en/stable/explanation/goodpractices.html |
| GitHub Flow | https://docs.github.com/en/get-started/quickstart/github-flow |
| Git 分支最佳实践 | https://devtoolhub.com/git-best-practices-branching-approvals/ |
| Python Linting SOP | https://alchemiststudios.ai/articles/python-linting-sop.html |
| Sourcegraph 复杂度指南 | https://sourcegraph.com/blog/cyclomatic-complexity-what-it-is-and-how-to-reduce-it |
