# 规则 R08：Python 编码风格规范（强制）

## 8.1 基础风格标准

遵循 **PEP 8** + **Google Python Style Guide**，以 ruff 为强制执行工具。

| 规范项 | 标准 | 来源 |
|--------|------|------|
| 行宽 | 100 字符（pyproject.toml 配置） | PEP 8 / ruff |
| 缩进 | 4 个空格，禁止 Tab | PEP 8 |
| 编码 | UTF-8 | PEP 8 |
| 引号 | 双引号 `"` | ruff format 默认 |
| 导入顺序 | 标准库 → 第三方 → 本地，组内字母序 | Google Style |
| 命名 | `snake_case` 函数/变量，`CamelCase` 类，`UPPER_CASE` 常量 | PEP 8 |
| 文档字符串 | 三双引号 `"""`，含 Args/Returns/Raises 段 | Google Style / PEP 257 |

来源: PEP 8 https://peps.python.org/pep-0008/ | Google Python Style Guide https://google.github.io/styleguide/pyguide | PEP 257 https://peps.python.org/pep-0257/

## 8.2 强制工具链

```toml
[tool.ruff]
line-length = 100
target-version = "py39"
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
```

提交前必须通过：`ruff check src/ tests/ 3dtool/`（lint）、`ruff format --check src/ tests/ 3dtool/`（格式）、`mypy src/polaris/ --ignore-missing-imports`（类型检查，可选但推荐）。

## 8.3 代码组织原则

1. **单一职责**：每个模块/类/函数只做一件事
2. **DRY**：重复代码提取为公共函数
3. **KISS**：优先简单方案，避免过度设计
4. **YAGNI**：不实现当前不需要的功能
5. **组合优于继承**：优先用组合而非深层继承链
6. **显式优于隐式**：避免魔法行为，让代码意图清晰

## 8.4 类型注解要求

- 所有公开 API 函数必须有类型注解（参数 + 返回值）
- 内部函数鼓励添加类型注解
- 复杂类型用 `TypeAlias` 或 `Protocol` 定义
- 使用 `from __future__ import annotations` 启用延迟注解求值

来源: PEP 484 类型注解 https://peps.python.org/pep-0484/
