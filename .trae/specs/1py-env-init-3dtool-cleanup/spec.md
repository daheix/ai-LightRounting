# 1py 环境初始化 + 3dtool 子仓库 + 分支合并 + 清盘 + 循环日志 Spec

## Why

用户要求继续完成上一轮 `redownload-3dtool-via-token` 未真正达成的工作。实际核查发现：前次 spec 声称"3dtool AppImage 25/25 全通过"，但本地 `/workspace/3dtool/subrepo/3dtool/` 是空目录，`3dtool/3dtool-appimage/` 已不存在（违反 R03 禁止 fall-back、R05 Bug 必修）。同时远端 `daheix/3dtool` 私有仓库对当前 token 返回 401 Bad credentials——token 仅对 `daheix/ai-LightRounting` 有权限，无法 clone 3dtool 子仓库。

本 spec 必须诚实处理此 blocker，并完成用户 5 项要求中可执行的部分（分支合并、清盘、循环日志、保活脚本、环境变量配置框架），同时为 3dtool clone 提供明确的解阻塞路径。

## What Changes

### 阶段一：诚实核查 + 解阻塞 3dtool clone（BLOCKER 处理）
- **核查现状**：验证 `3dtool/subrepo/3dtool/` 空目录、token 对 `daheix/3dtool` 返回 401、token 对 `daheix/ai-LightRounting` 可用
- **token 权限验证**：`curl -sI -H "Authorization: token ${TOKEN}" https://api.github.com/repos/daheix/3dtool` 返回 401
- **解阻塞方案**：向用户报告需要新的 token（对 `daheix/3dtool` 有 `Contents: Read` 权限的 fine-grained PAT 或 classic PAT with `repo` scope）
- **不 fall-back**：禁止用 pip download 或精简版 AppImage 假装完成（R03）

### 阶段二：git 远端分支可见性 + dev → main 合并
- **修改 fetch refspec**：`git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"`（当前仅 fetch main，导致 dev 不可见）
- **fetch 所有分支**：`git fetch --all --prune`
- **核查 dev vs main 差异**：dev 领先 main 20+ commits（含 flow/、alphachip_gnn、gui/layout_editor、3dtool submodule 等），main 有 1 个 calibration fix 不在 dev
- **逐个 merge**：先 `git merge origin/dev`（保留 dev 全部功能），再确认 calibration fix 已包含（若 dev 已含则跳过，若 dev 缺失则 cherry-pick main 的 commit）
- **回退不集成**：检查 dev 中是否有"回退"性质的 commit（如删除功能），若有则不集成该 commit
- **禁止直接替换**：使用 merge 保留历史，不使用 reset --hard 或 checkout 覆盖

### 阶段三：磁盘清盘（`~/.local/share` + 冗余工具）
- **删除 `~/.local/share/mise`**（3.0G）：mise 管理的多语言版本（bun/erlang/go/gradle/java/maven/ruby/elixir 等）非项目所需
- **删除 `~/.local/share/swiftly`**（6.5G）：Swift 工具链非项目所需
- **保留 `~/.local/share/pipx`**（154M）：可能含有用 CLI 工具，先核查再决定
- **清理 PATH**：从 `~/.bashrc` / `~/.profile` 中移除 mise/swiftly/phpenv/nvm/pyenv 的 init 行，避免 shell 启动报错
- **验证**：`df -h /` 显示可用空间；`python3 / pip / git` 仍可用

### 阶段四：循环日志系统（10M 上限）
- **创建 `scripts/logging_config.py`**：基于 `logging.handlers.RotatingFileHandler`，maxBytes=10MB，backupCount=1（总上限 ~20MB，单文件 10MB + 1 个备份）
- **日志目录**：`/tmp/polaris_logs/`（沙箱重启自动清理，不占持久空间）
- **集成到现有模块**：提供 `get_logger(name)` 工厂函数，被 `src/polaris/` 各模块复用
- **格式**：`%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s`
- **禁止 fall-back**：日志写入失败必须 raise，禁止静默吞错（R03）

### 阶段五：3dtool 环境变量配置（条件性，依赖阶段一解阻塞）
- **创建 `scripts/env_setup.sh`**：配置 `POLARIS_3DTOOL_HOME=/workspace/3dtool/subrepo/3dtool`
- **PATH 注入**：将 `3dtool-appimage/bin/` 加入 PATH（ngspice/openEMS/ElmerSolver/kicad 等）
- **LD_LIBRARY_PATH**：注入 `3dtool-appimage/lib/`（.so 依赖库）
- **PYTHONPATH**：注入 `3dtool-appimage/python/`（Python 3.14 + site-packages）
- **AppRun 包装**：创建 `scripts/run_3dtool.sh` 包装 `AppRun`，简化工具调用
- **状态**：阶段一未解阻塞前，此阶段脚本可创建但 `--check` 模式必须报告"3dtool 未安装"

### 阶段六：新工具安装流程（分片增量上传）
- **创建 `scripts/package_3dtool_shards.sh`**：将 `3dtool/subrepo/3dtool/` 下的新工具打包为分片压缩包
- **增量上传**：仅打包新增/变更的工具，生成 `.part_aa`/`.part_ab`/... 分片，仅上传新增分片
- **manifest.json 更新**：追加新工具条目，不重写已有条目
- **不整体上传**：禁止每次都重新打包全部工具

### 阶段七：保活脚本启动（AGENTS.md §2 强制）
- **启动 `scripts/keepalive.sh`**：`nohup bash scripts/keepalive.sh > /tmp/keepalive_stdout.log 2>&1 &`
- **验证**：`ps aux | grep keepalive.sh` 确认运行；检查 `/tmp/keepalive.log` 有新写入
- **失败处理**：启动失败立即告警退出（R03）

## Impact

- Affected specs:
  - `redownload-3dtool-via-token`（前次 spec，标记完成但实际未完成——本 spec 修正）
  - `download-3dtool-and-complete-remaining`（更早的 spec，同样未真正完成 3dtool）
- Affected code:
  - `scripts/keepalive.sh`（启动运行）
  - `scripts/logging_config.py`（新建，循环日志）
  - `scripts/env_setup.sh`（新建，环境变量）
  - `scripts/run_3dtool.sh`（新建，AppRun 包装）
  - `scripts/package_3dtool_shards.sh`（新建，分片打包）
  - `3dtool/subrepo/3dtool/`（待解阻塞后 clone）
  - `.git/config`（fetch refspec 修改）
  - `操作记录.md`（追加本轮记录）

## ADDED Requirements

### Requirement: 诚实核查 3dtool 实际状态
系统 SHALL 在 spec 执行前核查 `3dtool/subrepo/3dtool/` 目录是否非空、token 是否可访问 `daheix/3dtool`、`3dtool-appimage/` 是否存在，并诚实记录核查结果到 `操作记录.md`。

#### Scenario: 发现 3dtool 未真正安装
- **WHEN** 执行 `ls -la /workspace/3dtool/subrepo/3dtool/` 显示空目录
- **AND** `git clone https://x-access-token:${TOKEN}@github.com/daheix/3dtool.git` 返回 401
- **THEN** 在 `操作记录.md` 记录"前次 spec 声称完成但实际未完成"
- **AND** 向用户报告需要新 token（对 `daheix/3dtool` 有读权限）
- **AND** 禁止用精简版 AppImage 或 pip download 假装完成（R03）

### Requirement: git 远端全分支可见
系统 SHALL 修改 `remote.origin.fetch` refspec 为 `+refs/heads/*:refs/remotes/origin/*`，使 `git fetch --all` 后能看到远端所有分支（main + dev），不再仅限 main。

#### Scenario: dev 分支可见
- **WHEN** 执行 `git fetch --all --prune && git branch -a`
- **THEN** 输出包含 `remotes/origin/dev` 和 `remotes/origin/main`
- **AND** `git log --oneline main..origin/dev` 显示 20+ commits

### Requirement: dev → main 逐个合并保留全功能
系统 SHALL 使用 `git merge origin/dev`（非 reset/checkout 覆盖）将 dev 的 20+ commits 合并到 main，保留所有功能；若 main 有 dev 缺失的 commit（如 calibration fix），则 cherry-pick 到合并结果。

#### Scenario: 合并成功无冲突
- **WHEN** 执行 `git checkout main && git merge origin/dev`
- **THEN** 合并成功，main 包含 dev 全部 commits
- **AND** `git log --oneline origin/dev..main` 显示 calibration fix 已包含
- **AND** `git diff --stat origin/dev main` 仅显示 calibration 相关文件

#### Scenario: 检测到回退 commit 不集成
- **WHEN** dev 中存在 `git revert` 或删除功能的 commit
- **THEN** 跳过该 commit（通过 cherry-pick 逐个集成非回退 commit）
- **AND** 在 `操作记录.md` 记录跳过的 commit hash 与原因

### Requirement: `~/.local/share` 冗余工具清理
系统 SHALL 删除 `~/.local/share/mise`（3.0G）和 `~/.local/share/swiftly`（6.5G），保留 `pipx`（154M，待核查），并清理 shell init 中的 mise/swiftly 配置行。

#### Scenario: 清理后空间释放
- **WHEN** 执行 `rm -rf ~/.local/share/mise ~/.local/share/swiftly`
- **THEN** `du -sh ~/.local/share/` 从 ~10G 降至 <200M
- **AND** `python3 --version && pip --version && git --version` 全部正常输出
- **AND** 新开 shell 不报 "command not found" 错误

### Requirement: 循环日志 10M 上限
系统 SHALL 提供基于 `RotatingFileHandler` 的日志工厂 `scripts/logging_config.py`，maxBytes=10MB、backupCount=1，日志写入 `/tmp/polaris_logs/`，写入失败必须 raise（R03）。

#### Scenario: 日志循环生效
- **WHEN** 日志文件达到 10MB
- **THEN** 自动轮转为 `.1` 备份，新日志写入新文件
- **AND** 日志目录总大小 ≤ 20MB（10MB 当前 + 10MB 备份）

#### Scenario: 日志写入失败不静默
- **WHEN** 日志目录不可写（权限/磁盘满）
- **THEN** `get_logger()` raise `RuntimeError`，禁止 `except: pass`

### Requirement: 3dtool 环境变量配置脚本
系统 SHALL 提供 `scripts/env_setup.sh`，配置 `POLARIS_3DTOOL_HOME`、`PATH`、`LD_LIBRARY_PATH`、`PYTHONPATH`，使工具链调用 3dtool 自带 Python 3.14 与原生仿真工具（ngspice/openEMS/ElmerSolver/kicad）。

#### Scenario: 3dtool 已安装时配置生效
- **WHEN** `3dtool/subrepo/3dtool/AppRun` 存在且可执行
- **AND** 执行 `source scripts/env_setup.sh`
- **THEN** `which ngspice` 指向 `3dtool-appimage/bin/ngspice`
- **AND** `python3 --version` 输出 Python 3.14.x
- **AND** `python3 -c "import numpy"` 成功

#### Scenario: 3dtool 未安装时告警
- **WHEN** `3dtool/subrepo/3dtool/AppRun` 不存在
- **AND** 执行 `bash scripts/env_setup.sh --check`
- **THEN** 输出 `[ERROR] 3dtool 未安装，请先解阻塞 clone`
- **AND** 退出码非 0，禁止假装配置成功（R03）

### Requirement: 保活脚本启动
系统 SHALL 在 spec 执行第一步启动 `scripts/keepalive.sh`（已存在），每 5 分钟 touch `/tmp/keepalive_marker`，每 17 分钟向 `/tmp/keepalive_message.txt` 写入"做得很好，按照计划继续执行剩余任务。"

#### Scenario: 保活脚本运行
- **WHEN** 执行 `nohup bash scripts/keepalive.sh > /tmp/keepalive_stdout.log 2>&1 &`
- **THEN** `ps aux | grep keepalive.sh` 显示进程
- **AND** 5 分钟后 `/tmp/keepalive_marker` mtime 更新
- **AND** `/tmp/keepalive_message.txt` 内容为指定消息

## MODIFIED Requirements

### Requirement: 3dtool 子仓库 clone（修正前次 spec 的虚假完成）
`3dtool/subrepo/3dtool/` SHALL 通过 token 认证 clone `daheix/3dtool` 私有仓库（commit `cf97abef11cef8a2ab7add80e1b28df667977cb5`），解阻塞后执行 `git submodule update --init --recursive` 或直接 `git clone`。前次 spec 声称"25/25 全通过"但实际为空目录，本 spec 修正此虚假声明。

### Requirement: 新工具分片增量上传
新工具安装到 `3dtool/subrepo/3dtool/` 后，系统 SHALL 仅打包新增/变更工具为分片压缩包（`.part_aa`/`.part_ab`/...），更新 `manifest.json` 追加条目，禁止整体重新打包上传。

## REMOVED Requirements

### Requirement: 前次 spec 的"3dtool AppImage 25/25 全通过"声明
**Reason**: 实际核查 `3dtool/subrepo/3dtool/` 为空目录，`3dtool-appimage/` 不存在，前次 spec 的"25/25 全通过"为虚假声明（违反 R02 学术诚信、R03 禁止 fall-back）
**Migration**: 本 spec 阶段一诚实记录 blocker，阶段五在解阻塞后真正完成 clone 与验证
