# PoLaRIS 测试指南

> 版本 v6.1 · 2026-07 · pytest 结构、覆盖率、CI 与测试规范
> 数据来源：pyproject.toml / modules/\*/tests/ / R13 交付自测 / AGENTS.md
> 测试基线：1,614 passed / 0 failed / 1 skipped（2026-07-03 实测）

---

## 第 1 章：测试概览

PoLaRIS 采用 pytest 框架构建多层级测试体系，覆盖 33 个子模块的全部公开 API。

### 1.1 核心质量数字

| 指标 | 数值 | 来源 |
|------|------|------|
| 测试 passed | **1,614** | `pytest modules/` 全量运行（2026-07-03） |
| 测试 failed | **0** | 同上 |
| 测试 skipped | 1 | klayout 可选依赖跳过（R03 合规，不伪造） |
| 子模块独立测试套件 | 33 | modules/\*/tests/ 目录扫描 |
| 测试文件数 | 85 | `modules/*/tests/test_*.py` Glob 扫描 |
| 覆盖率门禁 | ≥90% | AGENTS.md §8 质量门禁 |
| TODO / FIXME / HACK 残留 | 0 | R05 强制 |
| fall-back 假数据 | 0 | R03 强制 |
| 文献 URL 溯源 | 3,031 | R02 学术诚信 |

> **数据溯源**：上述数字来自 `docs/architecture_overview.md` §12（行 702-708）及 `docs/设计文档.md`（行 21），均为 2026-07-03 分模块 pytest 实测结果。

### 1.2 测试框架与工具链

| 工具 | 版本约束 | 用途 | 配置来源 |
|------|----------|------|----------|
| pytest | ≥8.0（Python 3.14 兼容） | 测试框架 | pyproject.toml `[tool.pytest.ini_options]` |
| ruff | latest | Lint 检查 | pyproject.toml `[tool.ruff]` |
| mypy | latest | 类型检查 | pyproject.toml `[tool.mypy]` |
| pytest-cov | 按需安装 | 覆盖率报告 | 命令行 `--cov` 参数 |

开发依赖定义于 `pyproject.toml` `[project.optional-dependencies]` dev 段及 `requirements-dev.txt`：

```
# requirements-dev.txt
-r requirements.txt
pytest
ruff
mypy
```

### 1.3 质量门禁体系

PoLaRIS 遵循 R05（Bug 必须修复）/ R03（禁止 fall-back）/ R13（交付自测）构建质量保障：

- **函数长度**：≤80 行 SLOC（`scripts/code_quality_gate.py` 硬性上限）
- **文件长度**：≤800 行 SLOC
- **圈复杂度**：≤15（McCabe，基于 AST 决策节点计数）
- **函数参数**：≤7
- **类方法数**：≤30
- **嵌套深度**：≤5
- **测试覆盖率**：≥90%
- **0 警告 0 错误**才允许提交

门禁脚本：`python scripts/code_quality_gate.py`（任一违规即返回非零退出码）。

---

## 第 2 章：测试目录结构

### 2.1 目录组织

PoLaRIS 采用模块化测试结构，每个子模块拥有独立的 `tests/` 目录：

```
modules/
├── core/
│   └── tests/
│       └── test_specs.py              # 75 个测试
├── place/
│   └── tests/
│       ├── test_place.py              # 45 个测试（含 7 个测试类）
│       └── test_topological_scc.py    # 24 个测试
├── route/
│   └── tests/
│       ├── test_basic.py              # 27 个测试
│       ├── test_curvy.py              # 27 个测试
│       ├── test_drc_aware.py          # 18 个测试
│       └── test_route_ext.py          # 18 个测试
├── drc/
│   └── tests/
│       ├── test_drc.py                # 25 个测试
│       ├── test_drc_engine.py         # 23 个测试
│       ├── test_drc_rules.py          # 34 个测试
│       └── test_p1_drc_rules.py       # 19 个测试
└── ... （共 33 个子模块）
```

### 2.2 完整测试文件清单（85 个）

以下为 `modules/*/tests/test_*.py` 的全部测试文件（Glob 扫描结果）：

| # | 模块 | 测试文件 | 测试数（约） |
|---|------|----------|-------------|
| 1 | core | test_specs.py | 75 |
| 2 | orchestrator | test_orchestrator.py | 25 |
| 3 | flow | test_scheduler.py / test_stages.py / test_workspace.py / test_flow_ext.py | 47 |
| 4 | pdk | test_pdk.py | 40 |
| 5 | pdk_advanced | test_bridge.py / test_pcell.py / test_pdk_advanced_ext.py / test_multi_pdk.py | 43 |
| 6 | gds_tools | test_loader.py / test_gds_tools_ext.py / test_density.py / test_clip.py + conftest.py | 75 |
| 7 | gdsio | test_gdsio.py | 36 |
| 8 | place | test_place.py / test_topological_scc.py | 45 |
| 9 | route | test_basic.py / test_curvy.py / test_drc_aware.py / test_route_ext.py | 72 |
| 10 | router_advanced | test_router_advanced_ext.py / test_bundle.py / test_global_router.py / test_curvy.py | 107 |
| 11 | drc | test_drc.py / test_drc_engine.py / test_drc_rules.py / test_p1_drc_rules.py | 51 |
| 12 | lvs | test_lvs.py | 42 |
| 13 | verify_advanced | test_drc.py / test_verify_advanced_drc.py / test_lvs.py / test_report.py / test_verify_advanced_extra.py | 68 |
| 14 | fdtd | test_fdtd.py | 53 |
| 15 | fde | test_fde.py | 53 |
| 16 | fdfd | test_fdfd.py | 36 |
| 17 | eme | test_eme.py | 52 |
| 18 | bpm | test_bpm.py | 33 |
| 19 | circuit | test_simulator.py / test_mna.py / test_cascade.py / test_circuit_ext.py / test_cross_validation_sax.py | 88 |
| 20 | sparam | test_sparam.py | 40 |
| 21 | inverse | test_adjoint.py / test_adjoint_3d.py / test_fdtd_jax.py / test_level_set.py / test_topology_opt.py / test_inverse_ext.py / test_showcase.py | 56 |
| 22 | optimizer | test_nsga.py / test_topology.py / test_lbfgs.py / test_optimizer_ext.py | 76 |
| 23 | nn | test_nn.py | 48 |
| 24 | trainer | test_ppo.py / test_pretrain.py / test_trainer_ext.py / test_transfer.py / test_d07_enhancement.py | 33 |
| 25 | multiphysics | test_multiphysics.py | 35 |
| 26 | lumerical | test_lumerical.py | 31 |
| 27 | parasitic | test_cap.py / test_cap_ext.py / test_res.py / test_ind.py / test_parasitic_ext.py | 49 |
| 28 | pam4 | test_pam4.py | 30 |
| 29 | yield | test_mc.py / test_importance.py / test_yield_ext.py / test_optimize.py | 49 |
| 30 | quantum_advanced | test_quantum_advanced.py | 42 |
| 31 | boson | test_boson.py | 32 |
| 32 | klm | test_klm.py | 21 |
| 33 | gui | test_layout_editor.py / test_dialogs.py / test_web.py / test_widgets.py / test_d10_api.py / test_gui_ext.py | 30 |

> 来源：`docs/architecture_overview.md` §13 子模块完整矩阵（2026-07-03 扫描）。

### 2.3 命名规范

| 层级 | 规范 | 示例 |
|------|------|------|
| 测试文件 | `test_<模块名>.py` | `test_place.py`、`test_drc_rules.py` |
| 测试类 | `Test<功能域>` | `TestPlaceCircuit`、`TestComputeHpwl` |
| 测试函数 | `test_<被测函数>_<场景>` | `test_place_circuit_analytical_mode` |
| 辅助函数 | `_` 前缀 + 描述性名称 | `_make_mzi_circuit()`、`_check_no_overlap()` |
| 禁止 | `test1` / `test_foo` / `test_temp` | — |

---

## 第 3 章：运行测试

### 3.1 运行全部测试

PoLaRIS 测试分布在 `modules/*/tests/` 下，全量运行命令：

```bash
pytest modules/
```

> **注意**：`pyproject.toml` 中 `testpaths = ["tests"]` 指向相对路径 `tests/`，但项目根目录下无 `tests/` 目录（测试按模块组织在 `modules/*/tests/`）。因此需显式指定 `modules/` 路径。在单个模块目录内运行 `pytest` 时，`testpaths = ["tests"]` 会自动定位到该模块的 `tests/` 子目录。

### 3.2 运行单个模块测试

```bash
# 布局模块
pytest modules/place/tests/

# 布线模块
pytest modules/route/tests/

# DRC 验证模块
pytest modules/drc/tests/

# 电路仿真模块
pytest modules/circuit/tests/
```

也可进入模块目录后直接运行（利用 `testpaths = ["tests"]`）：

```bash
cd modules/place && pytest
```

### 3.3 运行单个测试

按 `文件::类::方法` 或 `文件::函数` 精确定位：

```bash
# 精确到类中的单个方法
pytest modules/place/tests/test_place.py::TestPlaceCircuit::test_place_circuit_analytical_mode

# 精确到模块级函数
pytest modules/place/tests/test_place.py::test_compute_hpwl_single_connection

# 按关键字模糊匹配
pytest modules/drc/tests/ -k "drc_rules"
```

### 3.4 带覆盖率运行

```bash
# 终端报告 + HTML 报告
pytest modules/ --cov=polaris --cov-report=term --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html
```

> `--cov=polaris` 追踪 `src/polaris/` 下所有包的覆盖率。HTML 报告生成在 `htmlcov/` 目录。

### 3.5 快速收集（不执行）

```bash
# 仅收集测试列表，不执行
pytest modules/ --co -q

# 查看测试总数
pytest modules/ --co -q | tail -1
```

### 3.6 标记过滤

pyproject.toml 定义了 `slow` 标记：

```bash
# 排除慢测试
pytest modules/ -m "not slow"

# 仅运行慢测试
pytest modules/ -m "slow"
```

### 3.7 失败时调试

```bash
# 遇到第一个失败即停止
pytest modules/ -x

# 失败后进入 pdb 调试器
pytest modules/ --pdb

# 显示本地变量（失败时）
pytest modules/ -l

# 详细输出
pytest modules/ -v
```

---

## 第 4 章：pytest 配置

以下配置从 `/workspace/pyproject.toml` `[tool.pytest.ini_options]` 真实提取：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "3dtool"]
addopts = "-ra"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

### 4.1 配置项说明

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `testpaths` | `["tests"]` | 默认测试搜索路径（相对 rootdir）。模块内运行时定位到 `modules/<mod>/tests/` |
| `pythonpath` | `["src", "3dtool"]` | 添加到 `sys.path` 的路径，使 `import polaris_*` 可从源码树导入 |
| `addopts` | `"-ra"` | 默认命令行选项：`-r` 显示额外测试摘要，`a` 显示所有非通过结果（except passed） |
| `markers` | `["slow: ..."]` | 自定义标记，用于过滤慢测试 |

### 4.2 源码导入机制

测试文件通过以下方式确保既可从已安装包导入，也可从源码树导入（CI/开发模式）：

```python
# modules/place/tests/test_place.py 中的导入模式
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
for _p in (_SRC, _CORE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_place  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
```

### 4.3 相关 lint / 类型配置

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501"]  # 行宽由 formatter 控制

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]      # re-export 模式，F401 为误报
"__init__.pyi" = ["F401"]

[tool.mypy]
python_version = "3.11"
warn_unused_configs = true
ignore_missing_imports = true
```

---

## 第 5 章：写测试规范

### 5.1 测试结构（AAA 模式）

所有测试遵循 **Arrange-Act-Assert** 三段式结构：

```python
def test_place_circuit_analytical_mode():
    """analytical 模式返回完整结果 dict。"""
    # Arrange — 构造测试数据
    circuit = _make_mzi_circuit()

    # Act — 调用被测函数
    result = place_circuit(circuit, mode="analytical")

    # Assert — 验证结果
    for key in ("placements", "hpwl", "placement_mode", "checkpoint_loaded"):
        assert key in result, f"结果缺少字段: {key}"
    assert result["placement_mode"] == "analytical"
    assert result["checkpoint_loaded"] is False
    assert len(result["placements"]) == 5
```

### 5.2 测试类组织

按功能域分组，使用 `Test` 前缀的类组织相关测试：

```python
class TestComputeHpwl:
    """compute_hpwl 曼哈顿距离求和（Kahng & Lienig IEEE TCAD 2009）。"""

    def test_compute_hpwl_single_connection(self):
        """单连接 HPWL = 两器件中心曼哈顿距离。"""
        ...

    def test_compute_hpwl_multiple_connections(self):
        """多连接 HPWL = 各连接曼哈顿距离之和。"""
        ...

    def test_compute_hpwl_no_connections(self):
        """无连接时 HPWL = 0。"""
        ...
```

### 5.3 命名规范

- **文件**：`test_<模块名>.py`（如 `test_place.py`、`test_drc_rules.py`）
- **类**：`Test<功能域>`（如 `TestPlaceCircuit`、`TestAnalyticalConfig`）
- **函数**：`test_<被测函数>_<场景>`（如 `test_place_circuit_analytical_mode`）
- **描述性名称**：禁止 `test1` / `test_foo` / `test_temp`
- **docstring**：每个测试方法必须有 1 行 docstring 描述预期行为

### 5.4 断言规范

- 使用原生 `assert`，禁止 `unittest.TestCase`
- 每个测试至少 1 个有意义的断言
- 浮点比较使用 `pytest.approx`：

```python
# 正确：浮点近似比较
assert p1[name]["x"] == pytest.approx(p2[name]["x"])

# 正确：带描述性消息
assert 0.0 <= pl["x"] <= canvas_w, f"{name} x 越界: {pl}"

# 正确：精确容差
assert abs(hpwl - expected) < 1e-9
```

### 5.5 错误路径测试（R03 禁止 fall-back）

非法输入必须 `raise`，测试用 `pytest.raises` 验证：

```python
def test_place_circuit_invalid_mode(self):
    """非法 mode 应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="不支持的布局模式"):
        place_circuit(circuit, mode="unknown_mode")

def test_place_circuit_invalid_circuit_dict(self):
    """circuit 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
        place_circuit("not a dict", mode="analytical")
```

### 5.6 测试数据

- **工厂函数**：使用 `_` 前缀工厂函数构造测试数据，保持测试 DRY：

```python
def _make_mzi_circuit() -> dict:
    """构造 5 器件 5 连接 MZI 电路（与验证脚本一致）。"""
    gc = make_device("gc1", "grating_coupler", 20, 20,
                     ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")])
    mmi = make_device("mmi1", "mmi_1x2", 20, 5,
                      ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east"),
                             ("out2", 20, 3.5, "east")])
    # ... 完整 5 器件构造
    return make_circuit("MZI", [gc, mmi, wg1, wg2, mmi2], [...])
```

- **真实数据优先**：断言基于真实物理量（如 HPWL、坐标范围、器件数）
- **禁止 fall-back 测试数据**（R03）：测试失败就报错，不跳过、不伪造
- **可选依赖**：使用 `pytest.importorskip` 跳过（不伪造）：

```python
@pytest.fixture
def klayout_db():
    """klayout.db 模块 fixture（未安装则跳过，不伪造）。"""
    return pytest.importorskip("klayout.db")
```

### 5.7 Fixture 使用

```python
# 使用 tmp_path 创建临时文件
def test_place_ppo_gnn_with_checkpoint(self, tmp_path, monkeypatch):
    ckpt = _make_valid_ppo_checkpoint()
    ckpt_path = tmp_path / "ppo_gnn.json"
    ckpt_path.write_text(json.dumps(ckpt), encoding="utf-8")
    monkeypatch.setenv("POLARIS_PLACE_CHECKPOINT", str(ckpt_path))
    ...

# 使用 monkeypatch 修改环境变量后恢复
def test_place_ppo_gnn_no_checkpoint_raises(self):
    saved = os.environ.pop("POLARIS_PLACE_CHECKPOINT", None)
    os.environ["POLARIS_PLACE_CHECKPOINT"] = "/nonexistent/ppo_gnn.json"
    try:
        with pytest.raises(RuntimeError, match="checkpoint"):
            place_circuit(circuit, mode="ppo_gnn")
    finally:
        os.environ.pop("POLARIS_PLACE_CHECKPOINT", None)
        if saved is not None:
            os.environ["POLARIS_PLACE_CHECKPOINT"] = saved
```

### 5.8 回归测试（R05 Bug 必须修复）

发现 Bug 后必须附回归测试防复发：

```python
def test_place_chain_signal_flow_x_increasing(self):
    """回归测试: 链式电路信号流方向 x 坐标递增（R05 防 BUG 复发）。

    构造 gc1→mmi1→ps1→mmi2→gc2 链式电路，断言 x 严格递增。
    """
    # ... 构造电路 ...
    result = place_circuit(circuit, mode="analytical")
    xs = {name: p["x"] for name, p in result["placements"].items()}
    assert xs["gc1"] < xs["mmi1"] < xs["ps1"], (
        f"gc1={xs['gc1']} mmi1={xs['mmi1']} ps1={xs['ps1']} 顺序错误"
    )
```

### 5.9 文献溯源（R02 学术诚信）

每个测试文件 docstring 必须包含 ≥5 个文献 URL，标注算法/参数来源：

```python
"""polaris-place 子模块深度测试（v5.0）。

来源（R02 学术诚信，≥5 个文献 URL）:
- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020 (Lin et al.): https://arxiv.org/abs/2004.10746
- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
- FFDH 合法化: Coffman et al. SIAM J. Comput. 9(4) 1980
  https://epubs.siam.org/doi/10.1137/0209062
"""
```

---

## 第 6 章：覆盖率

### 6.1 覆盖率门禁

| 指标 | 门禁值 | 来源 |
|------|--------|------|
| 最低覆盖率 | ≥90% | AGENTS.md §8 质量门禁 |
| 不达标处理 | 拒绝合并 | R13 §2 强制自测 |
| 覆盖率工具 | pytest-cov | 命令行 `--cov` 参数 |

> **注意**：`pyproject.toml` 中未配置 `[tool.coverage]` 段。覆盖率通过命令行参数 `--cov=polaris --cov-report=...` 传入，无持久化配置文件。项目根目录存在 `.coverage` 二进制缓存文件（上次运行残留）。

### 6.2 生成覆盖率报告

```bash
# 终端报告 + HTML 报告
pytest modules/ --cov=polaris --cov-report=term --cov-report=html

# 仅终端摘要
pytest modules/ --cov=polaris --cov-report=term-missing

# 查看 HTML 报告（逐行高亮）
open htmlcov/index.html
```

### 6.3 覆盖率报告解读

终端报告示例：

```
Name                              Stmts   Miss  Cover
-----------------------------------------------------
src/polaris/place/__init__.py        12      0   100%
src/polaris/place/analytical.py      85      3    96%
src/polaris/place/ppo_gnn.py        120     12    90%
-----------------------------------------------------
TOTAL                              1614     15    99%
```

- **Stmts**：可执行语句数
- **Miss**：未覆盖语句数
- **Cover**：覆盖率百分比
- **term-missing**：额外显示未覆盖行号

### 6.4 覆盖率不达标处理

覆盖率 < 90% 时：

1. **禁止跳过**（R03）：不允许 `pytest.skip` 或 `@pytest.mark.skip` 来跳过未覆盖路径
2. **补充测试用例**：针对未覆盖的分支/行编写新测试
3. **禁止假数据**（R03）：不允许构造虚假数据让代码"跑通"以提升覆盖率
4. **重新运行**：`pytest modules/ --cov=polaris --cov-report=term-missing` 验证

---

## 第 7 章：CI/CD

### 7.1 CI 检查项

每次 commit 触发以下检查链：

| 检查项 | 工具 | 通过标准 | 失败处理 |
|--------|------|----------|----------|
| 测试通过 | pytest | 0 failed | R05 立即修复 |
| 覆盖率 | pytest-cov | ≥90% | 补充测试用例 |
| Lint 检查 | ruff | 0 errors | 修复代码风格 |
| 类型检查 | mypy | 0 errors | 修复类型标注 |
| 质量门禁 | scripts/code_quality_gate.py | 0 警告 0 错误 | 重构超限函数 |

### 7.2 本地预检

提交前在本地运行完整检查链：

```bash
# 1. 运行全部测试
pytest modules/

# 2. Lint 检查
ruff check src/ modules/

# 3. 类型检查
mypy src/polaris/

# 4. 质量门禁
python scripts/code_quality_gate.py
```

### 7.3 质量门禁脚本

`scripts/code_quality_gate.py` 检查以下指标（来源：AGENTS.md §8）：

| 指标 | 硬性上限 | 警告阈值 |
|------|----------|----------|
| 文件大小 | 120 KB | 80 KB |
| 文件 SLOC | 800 行 | 500 行 |
| 函数 SLOC | 80 行 | 40 行 |
| 圈复杂度 | 15 | 10 |
| 函数参数 | 7 | 5 |
| 类方法数 | 30 | 20 |
| 嵌套深度 | 5 | 4 |

```bash
# 检查 src/polaris/
python scripts/code_quality_gate.py

# 检查指定目录
python scripts/code_quality_gate.py modules/place/src/

# JSON 输出
python scripts/code_quality_gate.py --json

# 仅检查 git 暂存文件
python scripts/code_quality_gate.py --staged
```

> 来源：`scripts/code_quality_gate.py` 行 42-57。学术溯源：Google Python Style Guide / McCabe IEEE TSE 1976 / PEP 8。

---

## 第 8 章：交付自测流程（R13 强制）

> 来源：`.trae/rules/R13-交付自测与迭代规范.md` §2。

任何涉及 Web 服务 / 后端 API / 前端页面的改动，交付前必须按以下 5 步自测：

### 8.1 五步自测流程

| 步骤 | 名称 | 验证内容 | 通过标准 |
|------|------|----------|----------|
| 1 | 构建自测 | 构建无错误 | 零 TypeScript 错误 |
| 2 | 服务启动自测 | 服务成功启动 | 健康检查返回 200 |
| 3 | 核心 API 自测 | curl 实际调用 API | 返回 `success: true` |
| 4 | 端到端自测 | 模拟用户关键操作路径 | 无 500 错误 |
| 5 | Python 子进程自测 | 确认子进程成功启动 | 不报 ModuleNotFoundError |

### 8.2 禁止行为

- **禁止**只启动服务不调用 API 就声称"已启动"
- **禁止**看到 HTTP 200 就声称功能正常（必须验证业务逻辑）
- **禁止**把未自测的结果交给用户验收

### 8.3 违规处理

| 违规 | 处理 |
|------|------|
| 未自测就交付 | 立即回退，补自测后重新交付 |
| 带病提交代码 | 回退提交，修复后重新提交 |

---

## 第 9 章：测试类型分类

### 9.1 单元测试

- **范围**：测试单个函数 / 类的公开 API
- **位置**：`modules/<子模块>/tests/test_<模块>.py`
- **特征**：隔离外部依赖，使用工厂函数构造输入
- **示例**：`test_place.py::TestComputeHpwl::test_compute_hpwl_single_connection`

```python
class TestComputeHpwl:
    """compute_hpwl 曼哈顿距离求和。"""

    def test_compute_hpwl_single_connection(self):
        """单连接 HPWL = 两器件中心曼哈顿距离。"""
        gc = make_device("gc1", "grating_coupler", 20, 20,
                         ports=[("out", 20, 10, "east")])
        mmi = make_device("mmi1", "mmi_1x2", 20, 5,
                          ports=[("in", 0, 2.5, "west")])
        circuit = make_circuit("Link", [gc, mmi],
                               [("gc1", "out", "mmi1", "in")],
                               canvas_w=500, canvas_h=300)
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        expected = abs(110.0 - 10.0) + abs(2.5 - 10.0)  # 107.5
        hpwl = compute_hpwl(circuit, placements)
        assert abs(hpwl - expected) < 1e-9
```

### 9.2 集成测试

- **范围**：测试多模块协作（如 stage3 布局 → stage4 布线）
- **位置**：`modules/*/tests/test_*_ext.py`（扩展测试）及 `examples/e2e_showcase/`
- **特征**：跨模块调用，验证数据流正确传递
- **示例**：`test_route_ext.py`（route + drc 联合验证）、`test_cross_validation_sax.py`（circuit + sparam 交叉验证）

### 9.3 端到端测试

- **范围**：showcase 11 阶段全流程（PDK → 电路 → 布局 → 布线 → 仿真 → DRC/LVS → GDS → 光电协同 → 量子 → 逆向设计 → 交互编辑）
- **位置**：`examples/e2e_showcase/stages/`
- **文件列表**：

| 阶段 | 文件 | 功能 |
|------|------|------|
| Stage 1 | stage1_pdk_catalog.py | PDK 器件目录 |
| Stage 2 | stage2_circuit_spec.py | 电路规格定义 |
| Stage 3 | stage3_ai_placement.py | AI 布局 |
| Stage 4 | stage4_routing.py | 布线 |
| Stage 5 | stage5_simulation.py | 仿真 |
| Stage 6 | stage6_drc_lvs.py | DRC/LVS 验证 |
| Stage 7 | stage7_gds_export.py | GDS 导出 |
| Stage 8 | stage8_opto_electrical.py | 光电协同 |
| Stage 9 | stage9_quantum_photonics.py | 量子光子 |
| Stage 10 | stage10_adjoint_inverse_design.py | 逆向设计 |
| Stage 11 | stage11_interactive_layout_edit.py | 交互编辑 |

- **运行方式**：

```bash
python examples/e2e_showcase/run_showcase.py
```

---

## 第 10 章：常见测试问题

### Q1: 测试失败怎么办？

**A**: 立即修复（R05 Bug 必须修复），附回归测试防复发。禁止 `TODO`/`FIXME`/`HACK` 残留到提交。

```bash
# 定位失败测试
pytest modules/ -x --tb=long

# 修复后验证
pytest modules/place/tests/test_place.py::test_place_chain_signal_flow_x_increasing -v
```

### Q2: 覆盖率不足怎么办？

**A**: 补充测试用例，禁止跳过。分析 `--cov-report=term-missing` 输出的未覆盖行号，针对性编写测试。禁止用假数据"让程序跑通"以提升覆盖率（R03）。

### Q3: 如何测试物理仿真（FDTD/FDE/BPM）？

**A**: 用小网格 + 少步数加速。物理仿真测试使用最小化参数：

```python
# FDTD: 小网格 + 少步数
result = simulate_waveguide_fdtd(
    grid_shape=(32, 32),    # 小网格（非 256×256）
    n_steps=50,             # 少步数（非 10000）
    ...
)

# BPM: 短距离
result = solve_bpm(
    z_steps=20,             # 少步数
    grid_nx=64,             # 小网格
    ...
)
```

### Q4: 如何测试 AI 训练（PPO/GNN）？

**A**: 用 1 step + 小网络。AI 训练测试最小化训练轮次：

```python
# PPO: 1 epoch + 小网络
agent = PPOAgent(
    obs_dim=24,
    action_dim=2,
    hidden_dim=64,          # 小网络
    n_epochs=1,             # 1 轮（非 1000）
    ...
)
```

### Q5: 可选依赖（klayout/gdsfactory）缺失怎么办？

**A**: 使用 `pytest.importorskip` 跳过，不伪造（R03 合规）：

```python
@pytest.fixture
def klayout_db():
    """klayout.db 未安装则跳过本模块所有 klayout 依赖测试。"""
    return pytest.importorskip("klayout.db")
```

### Q6: 测试中如何处理环境变量？

**A**: 使用 `monkeypatch` fixture 自动恢复，或手动 try/finally：

```python
# 方式 1: monkeypatch（推荐，自动恢复）
def test_with_env(self, monkeypatch):
    monkeypatch.setenv("POLARIS_PLACE_CHECKPOINT", "/path/to/ckpt.json")

# 方式 2: 手动 try/finally
def test_with_env(self):
    saved = os.environ.pop("VAR", None)
    os.environ["VAR"] = "test_value"
    try:
        ...
    finally:
        os.environ.pop("VAR", None)
        if saved is not None:
            os.environ["VAR"] = saved
```

### Q7: 测试收集报 ModuleNotFoundError 怎么办？

**A**: 确保所有依赖已安装。运行 `bash init.sh` 完成环境初始化（便携 Python 3.14 + 47 基础 wheel + PoLaRIS 特有 wheel + 33 模块 editable 安装）。`pythonpath = ["src", "3dtool"]` 配置确保源码可导入。

---

## 第 11 章：测试检查清单

提交代码前逐项确认：

- [ ] 新功能有对应测试（每个公开 API 至少 1 个测试）
- [ ] 测试通过 `pytest modules/`（0 failed）
- [ ] 覆盖率 ≥90%（`pytest modules/ --cov=polaris --cov-report=term`）
- [ ] 无 skip（除非有明确理由，如 `pytest.importorskip` 可选依赖）
- [ ] 断言有意义（每个测试至少 1 个非平凡断言）
- [ ] 测试数据真实（R03：禁止 fall-back 假数据）
- [ ] 错误路径有测试（`pytest.raises` 验证 raise 行为）
- [ ] Bug 修复附回归测试（R05：防复发）
- [ ] 测试文件 docstring 含 ≥5 个文献 URL（R02 学术诚信）
- [ ] ruff check 无错误
- [ ] mypy 无错误
- [ ] `python scripts/code_quality_gate.py` 通过（0 警告 0 错误）
- [ ] 函数 ≤80 行 / 文件 ≤800 行 / 圈复杂度 ≤15
- [ ] 无 TODO / FIXME / HACK 残留
- [ ] R13 交付自测通过（涉及 Web/API 时）

---

## 学术诚信声明（R02/R03）

| 数据项 | 数值 | 来源 |
|--------|------|------|
| 测试 passed | 1,614 | `docs/architecture_overview.md` §12（行 702），2026-07-03 pytest 实测 |
| 测试 failed | 0 | 同上 |
| 测试 skipped | 1 | 同上（klayout 可选依赖） |
| 子模块数 | 33 | `modules/` 目录扫描 |
| 测试文件数 | 85 | `modules/*/tests/test_*.py` Glob 扫描 |
| pytest 配置 | testpaths/pythonpath/addopts/markers | `/workspace/pyproject.toml` `[tool.pytest.ini_options]` |
| 覆盖率门禁 | ≥90% | `/workspace/AGENTS.md` §8 |
| 质量门禁阈值 | func≤80/file≤800/complexity≤15 | `/workspace/scripts/code_quality_gate.py` 行 42-57 |
| R13 交付自测流程 | 5 步 | `/workspace/.trae/rules/R13-交付自测与迭代规范.md` §2 |
| 每模块测试数 | 33 行矩阵 | `docs/architecture_overview.md` §13（行 746-780） |

所有数据从项目文件真实提取，禁止编造测试统计。配置从 `pyproject.toml` 真实提取。测试风格从 `modules/place/tests/test_place.py` 真实提取。
