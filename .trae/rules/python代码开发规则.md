# Python 代码开发规则 (Python Code Development Rules)

> 生效时间：2026-06-25
> 适用项目：PoLaRIS 光电子 AI 布局布线引擎（及所有 Python 子项目）
> 角色定位：**高级软件工程师 + 高级算法工程师** 双重角色协同开发
> 上位规则：`project_rules.md` 规则 14（禁止 fall-back）/ 规则 18（学术诚信）/ 规则 26（GPU 不参与）/ 规则 25（Plan/Spec 自动执行）
> 强制级别：**强制**，与 `project_rules.md` 同级，违反即视为代码不合格

---

## 0. 角色与心智模型

### 0.1 高级软件工程师角色（工程维度）
- **代码即产品**：每一行代码都要经得起 Code Review、单元测试、性能基准、生产事故的四重检验
- **可维护性优先**：代码被阅读的次数远多于被编写的次数，可读性 > 简洁性 > 巧妙性
- **契约即法律**：函数签名、类型注解、docstring 是与调用者的契约，破坏契约等于破坏信任
- **失败即告警**：禁止静默吞异常、禁止 fall-back 假数据（规则 14），失败必须 `raise` 并告警

### 0.2 高级算法工程师角色（算法维度）
- **复杂度意识**：编写任何循环前先问"时间复杂度是多少？能否用更优数据结构降低？"
- **算法选型有据**：选用的算法必须能说出理论依据（论文/教材/权威资源清单），禁止凭感觉
- **数值稳定性**：浮点运算需考虑条件数、舍入误差累积、溢出/下溢，关键路径须做数值稳定性分析
- **向量化优先**：能用 NumPy/JAX 向量化绝不写 Python 循环（性能差 10-200 倍）

### 0.3 决策原则
| 冲突场景 | 优先级顺序 |
|---------|----------|
| 正确性 vs 性能 | 正确性 > 性能（先正确再优化，禁止为性能牺牲正确性） |
| 可读性 vs 简洁性 | 可读性 > 简洁性（团队协作优先） |
| 三方库 vs 自研 | 三方库 > 自研（规则 3.3，不重复造轮子） |
| 通用算法 vs 特化算法 | 先通用后特化（验证正确后再特化优化） |
| CPU 算法 vs GPU 算法 | 仅 CPU（规则 26，GPU 不参与） |

---

## 1. 代码风格与格式（PEP 8 + Ruff 强制）

### 1.1 强制工具链
- **格式化**：`ruff format`（替代 Black，10-100× 速度）
- **Lint**：`ruff check`（替代 flake8/isort/pylint，集成度高）
- **类型检查**：`mypy --strict`（强制严格模式）
- **测试**：`pytest`（含覆盖率 `pytest-cov`，目标 ≥ 85%）

### 1.2 PEP 8 核心规则（强制）
- **缩进**：4 个空格，禁止 Tab
- **行宽**：100 字符（ruff 默认 88，项目放宽至 100）
- **命名**：
  - 函数/变量：`snake_case`（如 `calculate_total_price`）
  - 类：`PascalCase`（如 `WaveguideRouter`）
  - 常量：`UPPER_SNAKE_CASE`（如 `MAX_BEND_RADIUS`）
  - 私有：前缀 `_`（如 `_internal_helper`）
  - 布尔：`is_/has_/should_` 前缀（如 `is_valid`）
- **导入**：标准库 → 三方库 → 本项目，每组内字母序，禁止 `from x import *`
- **空行**：顶层函数/类间 2 行，方法间 1 行

### 1.3 pyproject.toml 强制配置

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "C4", "UP", "SIM", "RUF"]
ignore = ["E501"]  # 行宽由 formatter 控制

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]  # 测试允许 assert

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
addopts = "--strict-markers --cov=polaris --cov-report=term-missing --cov-fail-under=85"
```

来源：
- PEP 8: https://peps.python.org/pep-0008/
- Ruff: https://docs.astral.sh/ruff/
- mypy strict: https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict

---

## 2. 类型注解（强制 PEP 484）

### 2.1 必须注解的位置
- **所有函数**的参数与返回值
- **类属性**与实例变量
- **模块级常量**（类型可推断时可不注）
- **公开 API**（`__all__` 中导出的）

### 2.2 现代 Python 3.10+ 语法
```python
# ✅ 正确：现代联合类型语法
def process(value: int | str | None) -> dict[str, list[float]]: ...

# ❌ 错误：旧式 Optional/Union（Python 3.10+ 禁止）
from typing import Optional, Union
def process(value: Optional[Union[int, str]]) -> Dict[str, List[float]]: ...
```

### 2.3 复杂类型用 TypeAlias / Protocol
```python
from typing import Protocol, TypeAlias

# 类型别名
Vector: TypeAlias = "numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]]"
SMatrix: TypeAlias = "numpy.ndarray[tuple[int, int], numpy.dtype[numpy.complex128]]"

# 结构化类型（鸭子类型）
class Drawable(Protocol):
    def draw(self) -> None: ...
```

来源：PEP 484 https://peps.python.org/pep-0484/

---

## 3. 三方库使用规范（优先商用许可库）

### 3.1 许可证四档分类（与 INVENTORY.md 对齐）

| 档位 | 许可证 | 商用状态 | 代表库 | 使用决策 |
|------|--------|---------|--------|---------|
| ✅ 可直接商用 | MIT / Apache-2.0 / BSD / ISC / BSL-1.0 / PSF / MPL-2.0 / LGPL（动态链接） | 允许 | numpy, scipy, networkx, torch, jax, sax, simphony, matplotlib, pyyaml | **优先使用** |
| ⚠️ 许可受限 | GPL-3.0 / GPLv2+ / AGPL-3.0 | 需法律评估 | klayout, femwell, meep | 仅作开发工具（DRC/仿真器），不打包进发布制品；运行时通过子进程/CLI 调用，避免静态/动态链接传染 |
| 🚫 不可商用 | 商业云服务 / GPU 库（规则 26） | 禁止 | lumerical, vpi, tidy3d（云）, cupy, cuda-python | 禁止作为核心依赖；仅作对照验证（开发期临时使用） |
| ❌ 缺失待复刻 | 无 Py3.14 wheel / 无对应平台 | 复刻 | SiPANN（tensorflow 依赖） | 按规则 4 纯 Python 100% 复刻 |

### 3.2 选库决策树
```
新增功能需要三方库？
├── 是 → 查 INVENTORY.md 是否已在清单
│   ├── 已在 ✅可商用 → 直接 import 使用
│   ├── 已在 ⚠️许可受限 → 评估：能否用子进程隔离？能否用 ✅替代库？
│   │   ├── 能 → 子进程调用 / 替换为 ✅库
│   │   └── 不能 → 提交 spec 评审，法律确认后有限使用
│   ├── 已在 🚫不可商用 → 禁止使用，找替代方案
│   └── 不在清单 → 查 PyPI License 字段
│       ├── MIT/Apache/BSD → 加入 ✅清单后使用，同步更新 INVENTORY.md 与离线 wheel
│       ├── GPL/AGPL → 加入 ⚠️清单，spec 评审
│       └── 商业/不明 → 加入 🚫清单，禁止使用
└── 否 → 自研，放 src/polaris/<module>/
```

### 3.3 禁止事项
- ❌ 禁止 `import GPL 库` 进发布制品（传染整个项目）
- ❌ 禁止 `import 商业库`（如 lumapi）作为核心功能依赖
- ❌ 禁止 `import GPU 库`（cupy/cuda-python/torch+cuda，规则 26）
- ❌ 禁止未经 INVENTORY.md 登记就引入新三方库
- ❌ 禁止重复造轮子（已有 ✅库能解决的问题禁止自研）

来源：
- INVENTORY.md: `3dtool/INVENTORY.md`
- 开源许可证对比: https://opensource.org/licenses
- GPL 传染性: https://www.gnu.org/licenses/gpl-faq.html

---

## 4. 算法与数据结构规范（高效算法强制）

### 4.1 复杂度红线（违反必须说明理由）

| 操作规模 | 时间复杂度上限 | 允许的实现 | 禁止的实现 |
|---------|--------------|----------|----------|
| N ≤ 100 | O(N³) | 三层循环 | — |
| N ≤ 1000 | O(N²) | 双层循环 + 向量化 | O(N³) 暴力 |
| N ≤ 10⁴ | O(N log N) | 排序/二分/分治 | O(N²) 嵌套循环 |
| N ≤ 10⁶ | O(N) | 单次遍历/向量化 | O(N²) |
| N > 10⁶ | O(N) 或 O(log N) | 哈希/二分/向量化 | O(N²) 严禁 |

### 4.2 强制向量化（NumPy/JAX）
```python
# ❌ 禁止：Python 循环逐元素运算（慢 10-200×）
def slow_sum(a: list[float], b: list[float]) -> list[float]:
    return [x + y for x, y in zip(a, b)]

# ✅ 正确：NumPy 向量化
def fast_sum(a: numpy.ndarray, b: numpy.ndarray) -> numpy.ndarray:
    return a + b  # SIMD 加速，C 层循环
```

**向量化规则**：
1. 数值数组运算必须用 `numpy.ndarray`，禁止用 Python `list` 存数值
2. 批量运算必须用向量化/广播，禁止 `for` 循环逐元素
3. 条件运算用布尔掩码 `arr[mask]`，禁止 `if` 分支逐元素
4. 矩阵运算用 `@` 或 `numpy.einsum`，禁止三重循环
5. 可微分场景用 JAX `jax.numpy`（与 NumPy API 兼容，支持 autograd）

### 4.3 数据结构选型表

| 场景 | 推荐数据结构 | 复杂度 | 禁止 |
|------|------------|--------|------|
| 查找/去重 | `set` / `dict` | O(1) 平均 | `list.index()` O(N) |
| 有序唯一 | `dict`（Py3.7+ 保序） | O(1) | `list` 去重 O(N²) |
| 优先队列 | `heapq` / `queue.PriorityQueue` | O(log N) | 排序后 pop O(N log N) |
| 双端操作 | `collections.deque` | O(1) | `list.insert(0)` O(N) |
| 计数 | `collections.Counter` | O(N) | `dict` 手动计数 |
| 图算法 | `networkx.Graph` / `scipy.sparse.csgraph` | — | 自研邻接矩阵 |
| 稀疏矩阵 | `scipy.sparse` (CSR/CSC) | — | 密集 `numpy.ndarray` 存稀疏数据 |
| 空间索引 | `scipy.spatial.KDTree` / `cKDTree` | O(log N) 查询 | O(N²) 两两比较 |
| 几何运算 | `shapely`（BSD，可商用） | — | 纯 Python 几何计算 |

### 4.4 禁止的算法反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|---------|
| 暴力枚举 | O(2^N) 指数爆炸 | 动态规划 / 分支定界 / 启发式 |
| 抵消算法（计算后又撤销） | 浪费算力 | 增量更新 / 差分计算 |
| 嵌套循环查重 | O(N²) | `set`/`dict` O(N) |
| 重复计算 | 指数级重复 | `functools.lru_cache` 记忆化 |
| 全量重建 | O(N) 每次 | 增量维护 O(log N) |
| 深拷贝大对象 | O(N) 内存 | 视图/引用/`copy.copy` |
| 字符串拼接循环 | O(N²) | `"".join(parts)` |
| 排序后查找 | O(N log N) | `set`/`dict` O(1) |

### 4.5 算法选型必须有据（规则 18 学术诚信）
- 每个核心算法实现必须在 docstring 或注释中标注**来源文献**（论文/教材/仓库 URL）
- 复杂度声明必须与实现一致（如声明 O(N log N) 则实现不能是 O(N²)）
- 创新算法必须标注 `*创新*` 并记录底层逻辑、支持理论、案例（规则 18）
- 禁止使用未经检索核实的参数或经验值（规则 1.1）

来源：
- NumPy 向量化: https://numpy.org/doc/stable/user/basics.broadcasting.html
- Python 数据结构复杂度: https://wiki.python.org/moin/TimeComplexity
- SciPy 稀疏矩阵: https://docs.scipy.org/doc/scipy/reference/sparse.html

---

## 5. 函数与模块设计

### 5.1 函数设计原则（SOLID 简化版）
- **单一职责**：一个函数只做一件事，超过 50 行考虑拆分
- **纯函数优先**：无副作用，相同输入必相同输出（便于测试与并行）
- **显式优于隐式**：参数不要用 `**kwargs` 吞一切，明确列出关键参数
- **默认参数禁忌**：禁止用可变对象作默认值（`def f(x=[])` → `def f(x=None)`）

### 5.2 函数签名规范
```python
def calculate_bend_loss(
    radius: float,
    wavelength: float,
    *,
    polarization: str = "TE",
    num_points: int = 1000,
) -> float:
    """计算弯曲波导损耗（dB）。

    基于 Marcuse 弯曲损耗解析公式 [1]，对半径 r 在 [r_min, r_max] 范围
    内数值积分。

    Args:
        radius: 弯曲半径（μm），必须 > 0。
        wavelength: 波长（μm），必须 > 0。
        polarization: 偏振模式，"TE" 或 "TM"。
        num_points: 数值积分采样点数。

    Returns:
        弯曲损耗（dB），非负浮点数。

    Raises:
        ValueError: radius 或 wavelength ≤ 0。
        ValueError: polarization 非 "TE"/"TM"。

    References:
        [1] Marcuse, D. "Curvature loss formula for optical fibers."
            JOSA 66, 216 (1976). https://doi.org/10.1364/JOSA.66.000216
    """
    if radius <= 0:
        raise ValueError(f"radius must be positive, got {radius}")
    # ... 实现 ...
```

### 5.3 模块划分（与 project_rules.md 规则 2.3 对齐）
```
src/polaris/
├── data/       # 数据加载（CircuitSpec/DeviceSpec）
├── engine/     # 布局引擎（FloorplanEnv/GNN/CNN/Netlist）
├── eval/       # 评估渲染（layout_render）
├── nn/         # 纯 NumPy 神经网络库
├── pdk/        # 光子器件库（SOI/SiN/InP/LNOI）
├── pipeline/   # 端到端流水线
├── router/     # 布线引擎
├── sim/        # 仿真系统（S参数/级联/约束）
└── trainer/    # 训练器（PPO/GNN_PPO）
```

来源：
- Google Python Style Guide: https://google.github.io/styleguide/pyguide.html
- PEP 257 Docstring: https://peps.python.org/pep-0257/

---

## 6. 错误处理（禁止 fall-back，规则 14）

### 6.1 强制规则
- **失败即 raise**：业务错误必须 `raise` 明确异常，禁止 `return None` / `return -1` 静默失败
- **禁止 fall-back 假数据**：规则 14，禁止用假数据"让程序跑通"，跑不通就是业务设计有问题
- **禁止裸 `except:`**：必须捕获具体异常类型，`except Exception` 须慎用并记录日志
- **禁止吞异常**：`except: pass` 严禁，至少 `logging.exception` 记录

### 6.2 异常分层
```python
class PolarisError(Exception):
    """PoLaRIS 所有异常的基类。"""

class ValidationError(PolarisError):
    """输入验证失败。"""

class SimulationError(PolarisError):
    """仿真计算失败。"""

class RoutingError(PolarisError):
    """布线失败。"""
```

### 6.3 正确模式
```python
# ✅ 正确：验证失败立即 raise
def route(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    if start == end:
        raise ValidationError(f"start and end must differ, got {start}")
    path = _a_star_search(start, end)
    if path is None:
        raise RoutingError(f"no path found from {start} to {end}")
    return path

# ❌ 错误：fall-back 返回空列表（规则 14 违规）
def route(start, end):
    if start == end:
        return []  # 禁止：调用方无法区分"无需布线"和"布线失败"
    path = _a_star_search(start, end)
    return path if path else []  # 禁止：fall-back 假结果
```

---

## 7. 性能优化规范

### 7.1 优化原则（先正确后优化）
1. **先写正确**：用清晰的实现保证正确性
2. **再测性能**：用 `cProfile` / `timeit` / `pytest-benchmark` 定位瓶颈
3. **后优化瓶颈**：只优化测量出的热点，禁止过早优化
4. **验证等价**：优化前后必须用同一测试集断言输出一致（浮点容差 1e-9）

### 7.2 性能优化手段优先级
| 优先级 | 手段 | 收益 | 复杂度 |
|--------|------|------|--------|
| 1 | 向量化（NumPy/JAX） | 10-200× | 低 |
| 2 | 更优算法/数据结构 | 10-1000× | 中 |
| 3 | 缓存（`lru_cache`） | 2-10× | 低 |
| 4 | 避免重复计算 | 2-10× | 低 |
| 5 | 稀疏矩阵 | 10-100×（稀疏场景） | 中 |
| 6 | Numba JIT（BSD 可商用） | 10-100×（数值循环） | 中 |
| 7 | 多进程（`multiprocessing`） | 核数倍 | 高 |
| 8 | 算法并行化（JAX `vmap`/`pmap`） | 核数倍 | 高 |

### 7.3 禁止的优化
- ❌ 禁止用 Cython/C 扩展（构建复杂，跨平台难，违反"纯 Python"原则）
- ❌ 禁止用 GPU 加速（规则 26）
- ❌ 禁止为性能牺牲正确性（如降低数值精度导致结果错误）
- ❌ 禁止为性能牺牲可读性（除非有 benchmark 证明收益 > 10× 且加注释）

来源：
- Python 性能优化: https://docs.python.org/3/howto/perf_profiling.html
- Numba: https://numba.pydata.org/
- pytest-benchmark: https://pytest-benchmark.readthedocs.io/

---

## 8. 测试规范

### 8.1 测试覆盖要求
- **单元测试**：每个公开函数/类必须有测试，覆盖率 ≥ 85%
- **边界测试**：空输入、单元素、极大/极小值、非法输入
- **数值测试**：浮点结果用 `pytest.approx(expected, rel=1e-9)` 断言
- **回归测试**：bug 修复必须附测试用例防止复发

### 8.2 测试命名与结构
```python
# 文件：tests/test_router.py
import pytest
from polaris.router import WaveguideRouter

class TestWaveguideRouter:
    """WaveguideRouter 单元测试。"""

    @pytest.fixture
    def router(self) -> WaveguideRouter:
        return WaveguideRouter(grid_size=1.0)

    def test_route_straight_line(self, router: WaveguideRouter) -> None:
        """直线布线应返回 2 个转折点。"""
        path = router.route((0, 0), (10, 0))
        assert len(path) == 2
        assert path[0] == (0, 0)
        assert path[-1] == (10, 0)

    def test_route_same_point_raises(self, router: WaveguideRouter) -> None:
        """起点终点相同应 raise ValidationError。"""
        with pytest.raises(ValidationError, match="must differ"):
            router.route((5, 5), (5, 5))
```

### 8.3 禁止的测试反模式
- ❌ 禁止 `assert True`（无意义断言）
- ❌ 禁止测试依赖执行顺序（须相互独立）
- ❌ 禁止测试依赖外部网络/文件系统（用 `tmp_path` fixture）
- ❌ 禁止测试用 `print` 输出（用 `assert` 断言）

来源：pytest https://docs.pytest.org/

---

## 9. 文档与注释

### 9.1 docstring 强制（Google 风格）
- 所有公开函数/类/模块必须有 docstring
- 格式：Google 风格（Args/Returns/Raises/References 段）
- 复杂算法须在 docstring 中说明**算法来源**与**复杂度**

### 9.2 注释原则
- **解释 Why，不解释 What**：代码说"做什么"，注释说"为什么"
- **复杂逻辑必注释**：非显而易见的算法步骤、数值技巧、边界处理
- **TODO 禁止留存**：提交前必须清除所有 TODO/FIXME（规则：禁止做一半留一半）
- **创新点标注**：创新算法用 `# *创新*：...` 标注并记录逻辑（规则 18）

### 9.3 模块文件头规范
```python
"""模块一句话描述。

详细描述：模块职责、核心算法、依赖关系。

References:
    [1] 作者. "标题". 期刊/会议, 年份. URL
    [2] ...
"""
```

---

## 10. 并发与异步

### 10.1 选型
| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| CPU 密集 | `multiprocessing.Pool` | 绕过 GIL |
| I/O 密集 | `asyncio` | 协程轻量 |
| 混合 | 进程池 + 协程 | 各取所长 |
| 数值并行 | JAX `vmap`/`pmap` | 向量化/多核 |

### 10.2 禁止
- ❌ 禁止 `threading` 做 CPU 密集任务（GIL 限制）
- ❌ 禁止全局可变状态（线程安全灾难）
- ❌ 禁止未设超时的网络/锁操作（死锁风险）

---

## 11. 日志与可观测性

### 11.1 强制 `logging`，禁止 `print`
```python
import logging
logger = logging.getLogger(__name__)

# ✅ 正确
logger.info("Routing %d connections", len(connections))
logger.warning("DRC violation at %s: spacing %.2f < %.2f", loc, s, min_s)
logger.error("Simulation failed: %s", exc, exc_info=True)

# ❌ 错误
print("Routing connections...")  # 生产代码禁止 print
```

### 11.2 日志级别
- `DEBUG`：详细诊断（默认不输出）
- `INFO`：关键流程节点（默认输出）
- `WARNING`：可恢复异常（如 DRC 违规）
- `ERROR`：不可恢复异常（如仿真发散）
- `CRITICAL`：系统级故障

---

## 12. 版本控制与提交（对齐 project_rules.md 规则 1.2）

### 12.1 提交频率
- **每个小任务完成立即提交**（用户规则：禁止做一半留一半）
- 自动守护进程每 6 分钟轮询提交（`scripts/auto_commit_daemon.py`）
- 提交前必须通过 `ruff check` + `mypy` + `pytest`（冒烟测试）

### 12.2 Conventional Commits
```
<type>: <简述>

type ∈ feat | fix | docs | refactor | test | chore | perf
```

### 12.3 禁止
- ❌ 禁止 `git add -A` / `git add .`（按文件名精确添加）
- ❌ 禁止提交含密钥/凭据的文件
- ❌ 禁止 force push 到 main
- ❌ 禁止提交未通过 lint/test 的代码

---

## 13. 学术诚信（规则 18 强制）

### 13.1 公式与参数溯源
- 所有物理公式、经验系数、固定参数必须标注来源（论文/手册/PDK）
- 禁止编造 URL，所有引用 URL 必须经 WebSearch 验证存在
- 创新公式标注 `*创新*` 并记录：底层逻辑 + 支持理论 + 案例 + 差异化

### 13.2 算法实现一致性
- 复刻开源算法须与原实现 100% 逻辑一致（规则 4.4）
- 简化实现须标注"简化版"并给出完整版对照
- 禁止用假数据 fall-back 让程序"跑通"（规则 14）

---

## 14. 检查清单（提交前必过）

- [ ] `ruff check .` 通过（0 error）
- [ ] `ruff format --check .` 通过（格式合规）
- [ ] `mypy src/polaris/` 通过（0 error，strict 模式）
- [ ] `pytest` 通过（覆盖率 ≥ 85%）
- [ ] 无 TODO/FIXME/XXX/HACK 残留
- [ ] 无 `print(`（生产代码，日志用 `logging`）
- [ ] 无裸 `except:` / `except: pass`
- [ ] 无 fall-back 假数据（规则 14）
- [ ] 无 GPU 依赖（规则 26）
- [ ] 无 GPL 库直接 import 进发布制品
- [ ] 所有公开函数有 docstring + 类型注解
- [ ] 核心算法标注来源文献（规则 18）
- [ ] 创新点标注 `*创新*` 并记录逻辑（规则 18）
- [ ] 提交信息符合 Conventional Commits

---

## 15. 权威资源参考（持续更新）

### 15.1 Python 官方
- PEP 8 风格指南: https://peps.python.org/pep-0008/
- PEP 484 类型注解: https://peps.python.org/pep-0484/
- PEP 257 Docstring: https://peps.python.org/pep-0257/
- PEP 20 Python 之禅: https://peps.python.org/pep-0020/

### 15.2 工具链
- Ruff (lint+format): https://docs.astral.sh/ruff/
- mypy (type check): https://mypy.readthedocs.io/
- pytest (test): https://docs.pytest.org/
- pyproject.toml 规范: https://packaging.python.org/en/latest/specifications/pyproject-toml/

### 15.3 三方库许可
- MIT License: https://opensource.org/licenses/MIT
- Apache 2.0: https://www.apache.org/licenses/LICENSE-2.0
- GPL FAQ: https://www.gnu.org/licenses/gpl-faq.html
- SPDX 许可证列表: https://spdx.org/licenses/

### 15.4 性能与算法
- NumPy 广播: https://numpy.org/doc/stable/user/basics.broadcasting.html
- SciPy 稀疏矩阵: https://docs.scipy.org/doc/scipy/reference/sparse.html
- Python 复杂度: https://wiki.python.org/moin/TimeComplexity
- Numba JIT: https://numba.pydata.org/

### 15.5 项目内部
- 项目规则: `.trae/rules/project_rules.md`
- 三方库清单: `3dtool/INVENTORY.md`
- 算法公式手册: `3dtool/ALGORITHMS.md`
- 985 功能点算法文档: `2026-2028开发计划/功能清单与实现/`

---

## 修订日志

| 日期 | 版本 | 修订内容 | 作者 |
|------|------|---------|------|
| 2026-06-25 | v1.0 | 初版，15 章节覆盖风格/类型/三方库/算法/函数/错误/性能/测试/文档/并发/日志/提交/诚信/检查清单/资源 | PoLaRIS AI Agent |
