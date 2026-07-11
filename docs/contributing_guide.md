# PoLaRIS 开发贡献指南

> 版本 v6.1 · 2026-07 · 开发者贡献规范
> 依据：R11 V8 工作流 / R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU

PoLaRIS（光弈）是开源 AI 光电子 EDA 引擎，采用 33 子模块 monorepo 架构，MIT 许可。本指南规范开发流程、代码风格、提交规范与协作流程，所有规则均可溯源至项目规则文件（`.trae/rules/`）与工程配置（`pyproject.toml`）。

---

## 第 1 章：开发环境搭建

### 1.1 Python 版本

- **最低要求**：Python ≥ 3.9（来源：`pyproject.toml` → `requires-python = ">=3.9"`）
- **推荐版本**：Python 3.11（来源：`pyproject.toml` → `[tool.ruff] target-version = "py311"` 与 `[tool.mypy] python_version = "3.11"`）
- **已验证支持**：3.9 / 3.10 / 3.11 / 3.12（来源：`pyproject.toml` → `classifiers`）

### 1.2 从源码安装（开发模式）

```bash
git clone https://github.com/daheix/ai-LightRounting.git
cd ai-LightRounting
pip install -e ".[dev]"
```

开发依赖（来源：`pyproject.toml` → `[project.optional-dependencies] dev`）：

| 工具 | 用途 |
|------|------|
| `pytest` | 单元测试与覆盖率 |
| `ruff` | 代码风格静态分析 |
| `mypy` | 静态类型检查 |

> 注：上述三个开发工具在 `pyproject.toml` 中未锁定版本，安装时取最新兼容版本。

### 1.3 运行时依赖

核心依赖（来源：`pyproject.toml` → `[project] dependencies`）：

```
numpy · scipy · networkx · torch · gymnasium · matplotlib
pyyaml · klayout · simphony · sax · gdstk · shapely
```

### 1.4 可选依赖

| 可选组 | 安装命令 | 说明 | 来源 |
|--------|---------|------|------|
| gdsfactory | `pip install -e ".[gdsfactory]"` | gdsfactory ≥ 8.0；因上游 pydantic 锁定，Python 3.14 不可用 | `pyproject.toml` 注释 |
| sipann | `pip install -e ".[sipann]"` | SiPANN；依赖 tensorflow，仅 Python 3.10–3.13 可用 | `pyproject.toml` 注释 |

### 1.5 开发工具链配置

以下配置均直接读取自 `pyproject.toml`，**禁止覆盖**：

**ruff**（`[tool.ruff]`）：
- `line-length = 100`
- `target-version = "py311"`
- 启用规则：`E`（pycodestyle 错误）、`F`（pyflakes）、`W`（pycodestyle 警告）、`I`（isort）、`UP`（pyupgrade）、`B`（flake8-bugbear）
- 忽略：`E501`（行宽由 formatter 控制）
- `__init__.py` / `__init__.pyi` 忽略 `F401`（re-export 模式）

**mypy**（`[tool.mypy]`）：
- `python_version = "3.11"`
- `warn_unused_configs = true`
- `ignore_missing_imports = true`
- `pytest.*` 模块 `follow_imports = "skip"`（pytest 9 源码语法兼容）

**pytest**（`[tool.pytest.ini_options]`）：
- `testpaths = ["tests"]`
- `pythonpath = ["src", "3dtool"]`
- `addopts = "-ra"`
- 标记：`slow`（可用 `-m "not slow"` 跳过慢测试）

### 1.6 验证安装

```bash
python -c "import polaris; print(polaris.__version__)"
pytest --collect-only -q   # 确认测试可被发现
ruff check src/             # 确认 lint 通过
mypy src/                   # 确认类型检查通过
```

---

## 第 2 章：仓库结构

### 2.1 Monorepo 总览

PoLaRIS 采用 33 子模块 monorepo 架构，每个子模块位于 `modules/<name>/src/polaris_<name>/` 下，遵循统一命名规范。

### 2.2 核心目录

| 目录 | 说明 |
|------|------|
| `modules/` | 33 个子模块源码（布局/布线/物理求解/逆向设计/优化器/量子/验证等） |
| `examples/` | 示例电路与使用演示 |
| `docs/` | 项目文档（本指南、API 参考、架构总览、算法手册等） |
| `scripts/` | 运维脚本（自动提交、保活、基准测试、数据生成等） |
| `.trae/rules/` | 项目规则文件（R01–R13，强制执行） |
| `3dtool/` | 3D 工具包（package 发现路径之一，来源：`pyproject.toml` → `pythonpath`） |

### 2.3 子模块清单（33 个）

来源：`/workspace/modules/` 实际目录（排除 `README.md` 与 `_c_abi`）：

```
boson · bpm · circuit · core · drc · eme · fde · fdfd · fdtd · flow
gds_tools · gdsio · gui · inverse · klm · lumerical · lvs · multiphysics
nn · optimizer · orchestrator · pam4 · parasitic · pdk · pdk_advanced
place · quantum_advanced · route · router_advanced · sparam · trainer
verify_advanced · yield
```

按功能域分组：

| 功能域 | 模块 |
|--------|------|
| 核心 | `core` · `orchestrator` · `flow` · `circuit` |
| 布局 | `place` |
| 布线 | `route` · `router_advanced` |
| 物理求解 | `fdtd` · `fde` · `fdfd` · `eme` · `bpm` |
| 逆向设计 | `inverse` |
| 优化器 | `optimizer` |
| 量子光子 | `boson` · `klm` · `quantum_advanced` |
| 验证 | `drc` · `lvs` · `verify_advanced` · `yield` |
| PDK | `pdk` · `pdk_advanced` |
| IO/工具 | `gds_tools` · `gdsio` · `sparam` · `parasitic` · `multiphysics` |
| AI/训练 | `nn` · `trainer` · `pam4` |
| 仿真集成 | `lumerical` |
| 界面 | `gui` |

### 2.4 关键文件

| 文件 | 作用 | 来源 |
|------|------|------|
| `pyproject.toml` | 构建配置、依赖、工具链 | 项目根 |
| `AGENTS.md` | 智能体上下文规则（质量门禁、GPU 战略、监控脚本） | 项目根 |
| `操作记录.md` | 所有操作记录（R07 强制） | 项目根 |
| `.trae/rules/R11-工作流规范.md` | V8 极简工作流完整规则 | `.trae/rules/` |
| `scripts/auto_commit.py` | V8 每 6 分钟自动提交 | `scripts/` |
| `scripts/keepalive.sh` | 每 5 分钟保活防超时 | `scripts/` |

### 2.5 包构建信息

来源：`pyproject.toml`：

- **包名**：`polaris-pnr`
- **版本**：5.0.0
- **构建后端**：`setuptools.build_meta`（`setuptools>=68` + `wheel`）
- **包发现**：`where = ["src", "3dtool"]`，`include = ["polaris*", "pycopy*"]`，`exclude = ["tests*"]`
- **入口点**：`polaris = "polaris.pipeline:main"`
- **仓库**：https://github.com/daheix/ai-LightRounting
- **许可**：MIT

---

## 第 3 章：V8 极简工作流（R11 强制）

> 来源：`.trae/rules/R11-工作流规范.md`、`AGENTS.md` §2

### 3.1 分支策略

- **只用 `main` 分支**，禁止 dev/feature/worktree
- 会话启动时检查：`git branch --show-current`（必须在 main）
- **禁止 force push main**（R382 v2.0，2026-07-06）：
  - force push 会覆盖远程历史，原 commit 成为孤儿对象经 GC 后永久丢失
  - 正确做法：每个小任务单独 `git commit` + `git push`，保留完整可溯源链
- **clone 后必须 fetch 所有远程分支**（R382 v2.0）：
  ```bash
  git fetch origin 'refs/heads/*:refs/remotes/origin/*'
  git branch -a   # 验证所有远程分支可见
  git tag -l      # 应包含 r1-r378-history-backup
  ```

### 3.2 提交规范

每个小任务完成后立即执行：

```bash
git add <精确文件名>   # 禁止 git add -A
git commit -m "<type>: <简述>"
git push origin main   # 禁止 --force
```

**规则要点**：

- 禁止 `git add -A`（会误纳入敏感文件/大文件）
- 禁止 `git push --force` / `git push --force-with-lease`
- 建议避免 `git merge --squash` / `git rebase -i`（会丢失独立 commit 历史，操作记录 hash 不可溯源）
- 无变更时不创建空提交
- `auto_commit.py V8` 每 6 分钟自动兜底提交

### 3.3 commit message 类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 新增 EME Redheffer 星积求解器` |
| `fix:` | Bug 修复 | `fix: 修复 Euler 螺旋曲率半径下溢` |
| `docs:` | 纯文档变更 | `docs: 更新 API 参考第 3 章` |
| `refactor:` | 重构（无行为变更） | `refactor: 提取 DRC 规则公共基类` |
| `test:` | 测试相关 | `test: 补充 FDE 求解器回归测试` |
| `chore:` | 构建/工具链 | `chore: 升级 ruff target-version` |

> **强制**：commit message 类型必须与内容一致。禁止用 `docs:` 标注含代码变更的 commit（来源：R11 §2、`AGENTS.md` §2）。

### 3.4 任务派发前核查（防止重复造轮子）

**必须依次执行**（来源：R11 §3、`AGENTS.md` §3）：

```bash
git log --all --oneline --follow -- <文件>  # 查 git 历史
grep <功能名> 操作记录.md                     # 查操作记录
ls <目标路径>                               # 查现有文件
```

| 核查结果 | 行动 |
|---------|------|
| git 有 commit + 操作记录有 | 跳过，禁止重复实现 |
| git 无 + 操作记录无 | 可以派发 |
| 目标文件存在 | 必须 Read 后再决定 |

### 3.5 会话恢复检查

每次会话启动时执行（来源：R11 §6、`AGENTS.md` §1）：

```bash
git branch --show-current       # 必须在 main
ps aux | grep auto_commit       # 守护进程在运行
ps aux | grep keepalive         # 保活脚本在运行
```

---

## 第 4 章：代码规范

### 4.1 质量门禁

来源：`AGENTS.md` §8

| 指标 | 阈值 |
|------|------|
| 函数长度 | ≤ 80 行 |
| 文件长度 | ≤ 800 行 |
| 圈复杂度 | ≤ 15 |
| 测试覆盖率 | ≥ 90% |

### 4.2 静态分析

来源：`pyproject.toml`

```bash
ruff check src/ modules/        # 风格检查（line-length=100, target py311）
mypy src/                       # 类型检查（python_version=3.11）
```

ruff 启用规则集：`E` / `F` / `W` / `I` / `UP` / `B`（来源：`[tool.ruff.lint] select`）。

### 4.3 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 模块包 | `polaris_<name>` | `polaris_route`、`polaris_fdtd` |
| 类 | PascalCase | `AnalyticalConfig`、`EulerSpiral` |
| 函数/方法 | snake_case | `solve_redheffer`、`run_drc` |
| 常量 | UPPER_SNAKE | `DENSITY_MIN`、`CFL_FACTOR` |
| 私有 | 前缀 `_` | `_parse_netlist` |

### 4.4 文档字符串

- 每个公共函数/类必须含 docstring
- **每个模块 docstring 含 ≥ 5 个文献 URL**（来源：R02 学术诚信）
- 参数/返回值/异常必须标注类型
- 创新点标注 `*创新*` 并记录底层逻辑

### 4.5 禁止残留标记

来源：R05

- 禁止 `TODO` / `FIXME` / `HACK` 残留到提交
- 发现即修，附回归测试

### 4.6 测试规范

来源：`pyproject.toml` → `[tool.pytest.ini_options]`

- 测试目录：`tests/`
- pythonpath：`src`、`3dtool`
- 慢测试标记：`@pytest.mark.slow`，可用 `-m "not slow"` 跳过
- 运行：`pytest -ra`
- 覆盖率：`pytest --cov=polaris --cov-report=term-missing`（需 ≥ 90%）

---

## 第 5 章：学术诚信（R02 强制）

> 来源：`.trae/rules/R02-学术诚信.md`

### 5.1 核心原则

所有参数、公式、算法必须真实可溯源，**禁止编造**。

### 5.2 引用规范

- 引用须标注：**作者、标题、年份、URL/DOI**
- 每个模块 docstring 含 **≥ 5 个文献 URL**
- 优先级：顶会论文 > 大厂官方博客 > 海外社区 > 国内内容（来源：R01）

### 5.3 创新点标注

- 创新点标注 `*创新*`
- 记录底层逻辑与支持理论
- 合理创新需有根据和合理预估

### 5.4 禁止行为

| 禁止 | 说明 |
|------|------|
| 洗稿 | 禁止改写他人成果冒充原创 |
| 选择性引用 | 禁止只引用支持己方结论的文献 |
| 假数据 | 禁止编造实验数据/参数 |
| 凭经验编码 | 禁止凭记忆/经验直接编码，必须先检索（R01） |

### 5.5 权威检索资源

来源：R09 权威检索资源清单

| 类别 | 资源 |
|------|------|
| 学术 | arXiv / IEEE Xplore / ACM DL / SpringerLink / ScienceDirect / USENIX / VLDB |
| 论坛 | Stack Overflow / Hacker News / Reddit / Dev.to / Medium / InfoQ |
| 开源 | GitHub Discussions/Issues / GitLab / Apache / CNCF |
| 标准 | IETF RFC / W3C / OASIS / OpenAPI / ISO-IEC |
| 智库 | Google Research / Meta Eng / AWS Arch / Microsoft / Cloudflare / Netflix |

---

## 第 6 章：禁止 fall-back（R03 强制）

> 来源：`.trae/rules/R03-禁止fall-back.md`、`AGENTS.md` §5

### 6.1 核心原则

**失败即 raise，禁止任何静默兜底和假数据。**

### 6.2 禁止模式

```python
# 禁止：静默吞异常
except Exception:
    pass

# 禁止：返回 None 掩盖错误
def solve():
    try:
        ...
    except Exception:
        return None   # ❌

# 禁止：返回空列表掩盖错误
def get_rules():
    if not loaded:
        return []     # ❌
```

### 6.3 正确模式

```python
# 正确：raise 明确异常
def solve():
    if not config_valid:
        raise ValueError("配置无效：缺少波导宽度参数")

# 正确：业务错误返回告警，由上层处理
```

### 6.4 设计原则

- 跑不通就是业务设计有问题，返回告警即可，由业务层处理
- 禁止用假数据"让程序跑通"
- 公式计算等功能可设计独立接口，仅供特定条件下使用，**不作为 fall-back**
- 禁止 fall-back 导致后续业务无法得到正确结果

---

## 第 7 章：Bug 处理（R05 强制）

> 来源：`.trae/rules/R05-Bug必须修复.md`、`AGENTS.md` §7、R11 §8

### 7.1 核心原则

**发现即修，禁止遗留。**

### 7.2 处理流程

1. **发现 Bug** → 立即修复，不推迟
2. **验证根因** → 禁止只治标，必须定位根本原因
3. **附回归测试** → 防止复发
4. **清理标记** → 禁止 `TODO`/`FIXME`/`HACK` 残留到提交
5. **提交** → `fix: <根因简述>`，push origin main
6. **操作记录** → 追加到 `操作记录.md`（R07）

### 7.3 禁止行为

- 禁止发现问题不处理，直接说"不是我修改的问题"
- 禁止带病提交代码
- 禁止发现不同模块信息不一致而不重新审核查定

---

## 第 8 章：GPU 战略（R04 不可撤销）

> 来源：`.trae/rules/R04-不参与GPU.md`、`AGENTS.md` §9

### 8.1 战略决策

PoLaRIS 项目战略决策：**不参与 GPU 计算**（2026-06-25 项目所有者指示，不可撤销）。

### 8.2 禁止事项

| 禁止 | 说明 |
|------|------|
| GPU 后端 | 禁止 CuPy / CUDA / ROCm / AppleMetal 等所有 GPU 后端 |
| 半精度 | 禁止 FP16 / BF16 半精度 |
| 多卡分布式 | 禁止多卡 GPU 分布式训练/推理 |

### 8.3 实现要求

- 纯 **NumPy / SciPy / JAX(CPU)** 实现
- GPU 相关功能点标记 `🚫不参与`，不计入覆盖率
- 选择最合适的算法和数据结构，优先使用三方库，避免低效率低性能

---

## 第 9 章：操作记录（R07 强制）

> 来源：`.trae/rules/R07-操作记录.md`、R11 §4、`AGENTS.md` §4

### 9.1 记录要求

每个小任务完成后 **5 分钟内**追加到 `操作记录.md`。

### 9.2 记录内容

每条记录必须包含：

- **轮次编号**
- **交付文件**（精确路径）
- **测试结果**（精确数字，禁止模糊描述）
- **创新点**（如有，标注 `*创新*` 及底层逻辑）
- **文献引用**（R02，≥ 5 条 URL）
- **规则依据**
- **无 fall-back 声明**

### 9.3 时间戳格式

来源：R12 时间戳规范

```
### YYYY-MM-DD HH:MM 轮次编号
```

- 禁止遗漏时间戳
- 禁止遗漏关键决策和失败原因

### 9.4 记录示例

来源：`操作记录.md` 实际格式

```markdown
### 2026-07-05 15:30 轮次 R369 - DRC完整性审计综合报告生成

#### 交付文件
`docs/drc_completeness_audit_report.md`（355行，9章节）

#### 测试结果（精确数字）
...

#### 规则依据
- R02 学术诚信: ...
- R03 禁止 fall-back: ...
- R11 V8 工作流: main 分支

#### 无 fall-back 声明
所有数据均从真实代码读取，无任何编造数据。
```

---

## 第 10 章：提交前检查清单

> 综合来源：R02 / R03 / R04 / R05 / R07 / R11 + `AGENTS.md` §8

提交代码前，逐项确认：

- [ ] 代码通过 `ruff check`（line-length=100，规则集 E/F/W/I/UP/B）
- [ ] 代码通过 `mypy`（python_version=3.11）
- [ ] 测试通过 `pytest -ra`
- [ ] 测试覆盖率 ≥ 90%
- [ ] 无 `TODO` / `FIXME` / `HACK` 残留（R05）
- [ ] 函数 ≤ 80 行 / 文件 ≤ 800 行 / 圈复杂度 ≤ 15（`AGENTS.md` §8）
- [ ] docstring 含 ≥ 5 个文献 URL（R02）
- [ ] 创新点标注 `*创新*` 并记录底层逻辑（R02）
- [ ] 无 fall-back（无 `except: pass` / `return None` / `return []`）（R03）
- [ ] 无 GPU 代码（无 CuPy/CUDA/ROCm）（R04）
- [ ] 操作记录已追加到 `操作记录.md`（R07）
- [ ] commit message 类型与内容一致（R11）
- [ ] 精确 `git add <文件名>`（禁止 `git add -A`）（R11）
- [ ] `git push origin main`（禁止 `--force`）（R11）

---

## 第 11 章：监控脚本

> 来源：R11 §5、`AGENTS.md` §1/§11

### 11.1 自动提交脚本

| 脚本 | 轮询 | 功能 |
|------|------|------|
| `scripts/auto_commit.py V8` | 6 分钟 | 检测变更 → 提交 → push origin main |

- 无变更时不创建空提交
- 守护进程 crash → 立即重启并记录

### 11.2 保活脚本

| 脚本 | 轮询 | 功能 |
|------|------|------|
| `scripts/keepalive.sh` | 5 分钟 | touch 文件防超时 |

启动方式（会话第一件事）：

```bash
nohup bash scripts/keepalive.sh > /dev/null 2>&1 &
```

### 11.3 磁盘空间管理

来源：R11 §7、`AGENTS.md` §10

- 日志上限：99MB（RotatingFileHandler，单文件 99MB × 2 备份 = 198MB 总上限）
- 空间不足时删除：swiftly(6.5G) / mise(3.0G) / rustup(1.8G)

### 11.4 禁止 Git LFS

来源：R11 §7、`AGENTS.md` §10.1（2026-07-06 用户指示）

- 禁止 `git lfs install` / `.gitattributes` 配置 LFS filter
- 禁止 `git lfs track` 任何文件类型
- 大文件（< 100MB）直接 `git add` 提交，不使用 LFS
- 单文件硬上限 99MB（低于 GitHub 100MB 硬限制，安全余量 1MB）

---

## 第 12 章：常见问题

### Q1: 为什么不用 GPU？

**A**: R04 战略决策（2026-06-25 项目所有者指示，不可撤销）。PoLaRIS 纯 NumPy/SciPy/JAX(CPU) 实现，禁止 CuPy/CUDA/ROCm/AppleMetal。GPU 相关功能点标记 `🚫不参与`，不计入覆盖率。来源：`.trae/rules/R04-不参与GPU.md`。

### Q2: 为什么只用 main 分支？

**A**: R11 V8 极简工作流强制要求。直接在 main 分支开发，禁止 dev/feature/worktree。每个小任务完成后立即 `git add` → `commit` → `push origin main`，保留完整可溯源链。禁止 force push main（R382 v2.0）。来源：`.trae/rules/R11-工作流规范.md` §1。

### Q3: 如何添加新模块？

**A**: 在 `modules/` 下创建新目录，遵循 `polaris_<name>` 命名规范：

```
modules/<name>/
└── src/
    └── polaris_<name>/
        ├── __init__.py
        └── ...
```

- 模块 docstring 含 ≥ 5 个文献 URL（R02）
- 补充对应测试到 `tests/`
- 追加操作记录到 `操作记录.md`（R07）

### Q4: 如何报告 Bug？

**A**: R05 要求发现即修，禁止遗留。流程：发现 Bug → 验证根因 → 修复 → 附回归测试 → `fix:` 提交 → push origin main → 追加操作记录。禁止只治标，禁止 `TODO`/`FIXME`/`HACK` 残留。来源：`.trae/rules/R05-Bug必须修复.md`。

### Q5: 代码遇到异常该怎么处理？

**A**: R03 禁止 fall-back。失败即 `raise` 明确异常，禁止 `except: pass` / `return None` / `return []`。跑不通就是业务设计有问题，返回告警即可，由业务层处理。禁止用假数据"让程序跑通"。来源：`.trae/rules/R03-禁止fall-back.md`。

### Q6: 公式/参数如何标注来源？

**A**: R02 学术诚信要求所有参数/公式/算法真实可溯源。引用须标注作者、标题、年份、URL/DOI。每个模块 docstring 含 ≥ 5 个文献 URL。创新点标注 `*创新*` 并记录底层逻辑。来源：`.trae/rules/R02-学术诚信.md`。

### Q7: commit message 写错了类型怎么办？

**A**: R11 要求 commit message 类型必须与内容一致。代码变更用 `fix:`/`feat:`/`refactor:`/`test:`，纯文档用 `docs:`。禁止 `docs:` 标注含代码变更的 commit。如已提交错误类型，新建修正 commit（禁止 force push 改写历史）。

### Q8: 如何跳过慢测试？

**A**: 使用 `pytest -m "not slow"` 跳过标记为 `slow` 的测试。标记定义于 `pyproject.toml` → `[tool.pytest.ini_options] markers`。完整运行用 `pytest -ra`。

---

## 规则来源索引

本指南所有规则均可溯源至以下文件：

| 规则 | 来源文件 | 核心内容 |
|------|---------|---------|
| R02 | `.trae/rules/R02-学术诚信.md` | 参数/公式可溯源，≥5 文献 URL，创新标注 `*创新*` |
| R03 | `.trae/rules/R03-禁止fall-back.md` | 失败即 raise，禁止静默兜底与假数据 |
| R04 | `.trae/rules/R04-不参与GPU.md` | 不参与 GPU 计算，纯 CPU 实现 |
| R05 | `.trae/rules/R05-Bug必须修复.md` | 发现即修，附回归测试，禁止 TODO 残留 |
| R07 | `.trae/rules/R07-操作记录.md` | 每任务追加操作记录，含轮次/文件/测试结果 |
| R11 | `.trae/rules/R11-工作流规范.md` | V8 极简工作流（main 分支/精确 add/禁止 force push） |
| R12 | `.trae/rules/R12-时间戳规范.md` | 时间戳格式 `YYYY-MM-DD HH:MM:SS CST` |
| 质量门禁 | `AGENTS.md` §8 | 函数≤80行 / 文件≤800行 / 圈复杂度≤15 / 覆盖率≥90% |
| 工程配置 | `pyproject.toml` | Python ≥3.9 / ruff / mypy / pytest 配置 |

---

> 本指南依据 PoLaRIS 项目规则文件与工程配置编写，所有规则引用均标注来源文件路径，无编造数据。
