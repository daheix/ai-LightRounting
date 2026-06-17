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

## 后续规则
（其他规则将随项目推进追加）
