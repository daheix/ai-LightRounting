# 规则 R09：Git 工作流与团队协作规范（强制）— 代码审查与 .gitignore

## 9.3 代码审查 (Code Review)

- 所有 PR 必须至少 1 人审查通过方可合并
- PR 描述须包含：变更摘要、变更内容、关联 Issue
- PR 应小而聚焦（建议 < 400 行变更），便于审查
- 审查关注点：正确性、可读性、性能、安全性、测试覆盖
- 禁止自我批准合并自己的 PR

## 9.4 .gitignore 规范

必须忽略的文件类型：
- `__pycache__/`、`*.pyc`、`*.pyo`
- `.env`、`*.key`、`credentials.json`（密钥/凭据）
- `venv/`、`.venv/`、`env/`（虚拟环境）
- `dist/`、`build/`、`*.egg-info/`（构建产物）
- `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`
- `*.gds`、`*.oas`（大型版图文件，按需用 LFS）
- `checkpoints/`（训练检查点，体积大）
- `3dtool/wheels/.tmp_restore/`（离线安装临时还原目录，install.sh 运行时生成）
- `.idea/`、`.vscode/`、`*.swp`、`*.swo`（IDE 文件）

**注意**：`3dtool/wheels/*.whl` 和 `3dtool/wheels/parts/*.part_*` **必须提交到 git**，这是沙箱重启后恢复环境的核心依赖，禁止忽略。
