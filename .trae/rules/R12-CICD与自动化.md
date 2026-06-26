# 规则 R12：CI/CD 与自动化（强制）

## 12.1 CI 流水线检查项

每次 PR / push 到 main 必须通过：

```yaml
# .github/workflows/ci.yml（示例）
jobs:
  quality-gate:
    steps:
      - run: python scripts/code_quality_gate.py        # 质量门禁
      - run: ruff check src/ tests/ 3dtool/              # lint
      - run: ruff format --check src/ tests/ 3dtool/     # 格式
      - run: mypy src/polaris/ --ignore-missing-imports  # 类型检查
  test:
    steps:
      - run: python -m pytest tests/ -q --tb=short       # 全量测试
```

## 12.2 提交前检查清单

提交代码前必须逐项确认：

- [ ] `ruff check src/ tests/ 3dtool/` 通过（0 错误）
- [ ] `ruff format --check src/ tests/ 3dtool/` 通过
- [ ] `python scripts/code_quality_gate.py` 通过（0 硬性违规）
- [ ] `pytest tests/ -q` 通过（0 失败）
- [ ] 新增功能有对应测试
- [ ] 公开 API 有文档字符串
- [ ] 集成的工具/算法标注了来源 URL
- [ ] 提交消息符合 Conventional Commits
- [ ] 无密钥/凭据提交
- [ ] 文件放置符合规则 2（src/3dtool/publish/tests/scripts/data）
