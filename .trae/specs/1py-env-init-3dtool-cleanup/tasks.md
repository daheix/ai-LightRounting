# Tasks

## 阶段一：诚实核查 + 解阻塞 3dtool clone

- [x] Task 1: 核查 3dtool 实际状态并记录
  - [x] SubTask 1.1: 验证 `3dtool/subrepo/3dtool/` 是否为空目录
  - [x] SubTask 1.2: 验证 token 对 `daheix/3dtool` 返回 401（`curl -sI -H "Authorization: token ${TOKEN}" https://api.github.com/repos/daheix/3dtool`）
  - [x] SubTask 1.3: 验证 token 对 `daheix/ai-LightRounting` 返回 200
  - [x] SubTask 1.4: 在 `操作记录.md` 追加"前次 spec 虚假完成"的诚实核查记录
  - [x] SubTask 1.5: 向用户报告 blocker：需要新 token 才能 clone 3dtool

## 阶段二：git 远端分支可见性 + dev → main 合并

- [x] Task 2: 修改 git fetch refspec 使所有分支可见
  - [x] SubTask 2.1: `git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"`
  - [x] SubTask 2.2: `git fetch --all --prune` 获取远端全部分支
  - [x] SubTask 2.3: 验证 `git branch -a` 显示 `remotes/origin/dev` 和 `remotes/origin/main`

- [x] Task 3: 分析 dev vs main 差异，识别回退 commit
  - [x] SubTask 3.1: `git log --oneline main..origin/dev` 列出 dev 领先的 20+ commits
  - [x] SubTask 3.2: `git log --oneline origin/dev..main` 列出 main 独有的 commit（calibration fix）
  - [x] SubTask 3.3: 逐个审查 dev commits，标记回退/删除功能的 commit（如 `git revert`、删除文件等）
  - [x] SubTask 3.4: 记录审查结果到 `操作记录.md`

- [x] Task 4: 合并 dev → main（保留全功能）
  - [x] SubTask 4.1: `git checkout main` 确认在 main 分支
  - [x] SubTask 4.2: `git merge origin/dev` 合并 dev（若回退 commit 存在，使用 cherry-pick 逐个集成非回退 commit）
  - [x] SubTask 4.3: 验证合并后 main 包含 dev 全部非回退 commits
  - [x] SubTask 4.4: 若 main 独有 commit（calibration fix）不在合并结果中，cherry-pick 补入
  - [x] SubTask 4.5: 验证 `git diff --stat origin/dev main` 仅含 calibration 相关文件差异
  - [x] SubTask 4.6: `git push origin main` 推送合并结果

## 阶段三：磁盘清盘

- [x] Task 5: 删除 `~/.local/share` 冗余工具
  - [x] SubTask 5.1: 核查 `~/.local/share/pipx` 内容，确认是否保留
  - [x] SubTask 5.2: `rm -rf ~/.local/share/mise ~/.local/share/swiftly`
  - [x] SubTask 5.3: 验证 `du -sh ~/.local/share/` < 200M
  - [x] SubTask 5.4: 验证 `python3 --version && pip --version && git --version` 正常

- [x] Task 6: 清理 shell init 中的冗余 PATH 行
  - [x] SubTask 6.1: 检查 `~/.bashrc` / `~/.profile` / `/etc/profile` 中的 mise/swiftly/phpenv/nvm init 行
  - [x] SubTask 6.2: 注释或删除 mise/swiftly 相关 init 行
  - [x] SubTask 6.3: 保留 pyenv 和 python3 相关 PATH（项目必需）
  - [x] SubTask 6.4: 验证新开 shell 不报 "command not found" 错误

## 阶段四：循环日志系统

- [x] Task 7: 创建循环日志工厂 `scripts/logging_config.py`
  - [x] SubTask 7.1: 实现 `get_logger(name, log_dir="/tmp/polaris_logs", max_bytes=10_485_760, backup_count=1)`
  - [x] SubTask 7.2: 基于 `logging.handlers.RotatingFileHandler`，格式 `%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s`
  - [x] SubTask 7.3: 日志目录不可写时 raise RuntimeError（R03 禁止 fall-back）
  - [x] SubTask 7.4: 写入单元测试验证循环轮转（mock 文件大小触发轮转）

## 阶段五：3dtool 环境变量配置脚本

- [x] Task 8: 创建 `scripts/env_setup.sh`
  - [x] SubTask 8.1: 配置 `POLARIS_3DTOOL_HOME=/workspace/3dtool/subrepo/3dtool`
  - [x] SubTask 8.2: 3dtool 已安装时注入 PATH（bin/）、LD_LIBRARY_PATH（lib/）、PYTHONPATH（python/）
  - [x] SubTask 8.3: 3dtool 未安装时 `--check` 模式输出 ERROR 并 exit 1（R03）
  - [x] SubTask 8.4: 创建 `scripts/run_3dtool.sh` 包装 `AppRun` 调用

## 阶段六：新工具分片增量上传

- [x] Task 9: 创建 `scripts/package_3dtool_shards.sh`
  - [x] SubTask 9.1: 扫描 `3dtool/subrepo/3dtool/` 下新增/变更的工具目录
  - [x] SubTask 9.2: tar+gzip+split 打包为 `.part_aa`/`.part_ab`/... 分片（每片 ≤24MB）
  - [x] SubTask 9.3: 更新 `manifest.json` 追加新条目（不重写已有）
  - [x] SubTask 9.4: 仅 git add 新增分片文件，不重新上传已有分片

## 阶段七：保活脚本启动 + 代码提交

- [x] Task 10: 启动保活脚本并验证
  - [x] SubTask 10.1: `nohup bash scripts/keepalive.sh > /tmp/keepalive_stdout.log 2>&1 &`
  - [x] SubTask 10.2: `ps aux | grep keepalive.sh` 确认进程运行
  - [x] SubTask 10.3: 检查 `/tmp/keepalive.log` 有新写入
  - [x] SubTask 10.4: 向用户报告保活脚本已启动

- [x] Task 11: 提交所有变更到 main 分支
  - [x] SubTask 11.1: `git add` 精确文件（spec + tasks + checklist + logging_config.py + env_setup.sh + run_3dtool.sh + package_3dtool_shards.sh + 操作记录.md + .git/config 变更）
  - [x] SubTask 11.2: `git commit -m "feat: 环境初始化+分支合并+清盘+循环日志+3dtool配置框架"`
  - [x] SubTask 11.3: `git push origin main`
  - [x] SubTask 11.4: 更新 `操作记录.md` + `checklist.md` + `tasks.md` 全部勾选

# Task Dependencies

- [Task 2] depends on [Task 1]（先核查再修 git 配置）
- [Task 3] depends on [Task 2]（分支可见后才能分析差异）
- [Task 4] depends on [Task 3]（差异分析完成才能合并）
- [Task 5+6] 可并行（不依赖 git 操作）
- [Task 7] 可并行（不依赖其他任务）
- [Task 8] depends on [Task 1]（依赖 3dtool 状态核查结果）
- [Task 9] depends on [Task 8]（依赖 env_setup.sh 完成）
- [Task 10] 优先级最高，应最先执行
- [Task 11] depends on [Task 4+5+6+7+8+9]（全部完成后提交）
