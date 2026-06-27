# Token 方式重新下载 3dtool 仓库并完整融合 Spec

## Why

现有 `3dtool/3dtool-appimage/` 是精简解压版（仅 AppRun + bin + python，缺 lib/kicad/jre/share），AppRun check 25 项中 12 项失败（kicad 全部 7 项 + CSXCAD + libopenEMS + libelmersolver + libXaw + libXt）。用户明确要求"用 tokens 方式重新下载 daheix/3dtool 仓库"作为自仓库使用，替代之前 pip download 替代方案（R03 禁止 fall-back）。同时完成剩余的 P0/P1 任务验证与代码提交。

## What Changes

### 阶段一：磁盘空间清理（≥5G 可用）
- 删除冗余工具：swiftly（6.5G）、mise（3.0G）、rustup（1.8G）、php-build、phpenv、nvm
- 清理 pip cache、__pycache__、临时分片
- 清理 3dtool-appimage 中重复的大包（torch 756M 已在 wheels/，llvmlite/skidl/sympy/pandas/plotly/sklearn 等非项目依赖）
- 验证 df -h ≥5G 可用

### 阶段二：Token 方式完整 clone daheix/3dtool 仓库
- 从 git remote URL 提取 GitHub token（已有：`ghu_pdPIxr6rxhQpOrG7VjLOvVjPM0MaJL01s1wC`）
- 用 `https://x-access-token:${TOKEN}@github.com/daheix/3dtool.git` 认证 clone 到 /tmp/3dtool-repo
- 验证 17 个分片文件完整（3dtool-appimage-parts/manifest.json 11 个包定义）
- 运行 restore_3dtool_appimage.sh 合并分片+解压完整 AppImage 到 /tmp/3dtool-full/
- 验证 AppImage 包含 lib/kicad/jre/share/bin/python 完整结构

### 阶段三：完整融合到 workspace/3dtool/3dtool-appimage/
- 删除现有精简版 3dtool-appimage（仅 AppRun + bin + python）
- 拷贝完整 AppImage 解压结果到 /workspace/3dtool/3dtool-appimage/
- 保留现有 3dtool/wheels/ 目录（15 个 wheel 包）不动
- 验证 AppRun check 25/25 全部通过（含 kicad/openEMS/ElmerSolver 完整库依赖）

### 阶段四：工具链与三方库融合验证
- 验证 AppRun python3 = Python 3.14.4
- 验证 site-packages 含项目 12 核心依赖（numpy/scipy/networkx/torch/gymnasium/matplotlib/yaml/klayout/simphony/sax/gdstk/shapely）
- 验证 install.sh 修复后包含 gdstk/shapely（已修复 fall-back `|| true`）
- 验证 bin/ 含 9 个原生工具（ngspice/openEMS/ElmerSolver/ElmerGrid/nf2ff/sar_calc/minisign/zsync2 + kicad 系列完整 7 个）

### 阶段五：剩余 P0/P1 任务验证与提交
- 验证前次 spec 的 13 个 Task 修复代码仍然有效（py_compile + ruff check）
- 修复 install.sh 的 R03 违规（已做：`|| true` fall-back 改为记录失败+告警）
- 验证 multiphysics 模块（H01/H02）公式正确性
- 验证 alpha_chip.py 架构统一（复用 AlphaChipEdgeGNN + PPOAgent）
- 提交所有变更到 main 分支并推送远端

## Impact

- Affected specs:
  - download-3dtool-and-complete-remaining（前次 spec，标记完成但 3dtool 未真正完整）
  - H01-电光耦合、H02-热光效应、I04-SPICE、D04-奖励、D05-AlphaChip、C05-频域扫描
- Affected code:
  - `3dtool/3dtool-appimage/`（完整恢复，含 lib/kicad/jre/share）
  - `3dtool/wheels/install.sh`（已修复 gdstk/shapely + R03 fall-back）
  - `3dtool/wheels/MANIFEST.txt`（新建，wheel 清单索引）
  - 前次修复的 8 个代码文件（py_compile 复验）

## ADDED Requirements

### Requirement: Token 认证完整 clone 私有 3dtool 仓库
系统 SHALL 使用 GitHub token 认证方式完整 clone `daheix/3dtool` 私有仓库（17 个分片，1.6G），并运行 `restore_3dtool_appimage.sh` 恢复完整 AppImage 工作目录。

#### Scenario: Token 认证 clone 成功
- **WHEN** 执行 `git clone https://x-access-token:${TOKEN}@github.com/daheix/3dtool.git /tmp/3dtool-repo`
- **THEN** 17 个分片文件完整下载到 `/tmp/3dtool-repo/3dtool-appimage-parts/`
- **AND** `manifest.json` 定义 11 个包结构完整

#### Scenario: 完整 AppImage 恢复
- **WHEN** 运行 `restore_3dtool_appimage.sh`
- **THEN** 解压结果含 `AppRun/bin/lib/jre/share/python` 完整目录结构
- **AND** `lib/` 目录含 libopenEMS.so.0、libelmersolver.so、libXaw.so.7、libXt.so.6 等全部依赖库

### Requirement: AppRun check 25/25 全部通过
系统 SHALL 在完整恢复后执行 `AppRun check`，25 项工具自检全部通过（含 kicad 7 项 + CSXCAD + openEMS/ElmerSolver/ngspice 库依赖）。

#### Scenario: 工具自检全通过
- **WHEN** 执行 `/workspace/3dtool/3dtool-appimage/AppRun check`
- **THEN** 输出 25 项全部 ✓，无 ✗ MISSING 或 not found

### Requirement: 磁盘空间 ≥5G 可用
系统 SHALL 在 clone 之前清理冗余工具（swiftly/mise/rustup/php-build/phpenv/nvm）和非项目依赖（llvmlite/skidl/sympy/pandas/plotly/sklearn/pyright），确保 ≥5G 可用空间容纳完整 AppImage（约 3-4G 解压后体积）。

#### Scenario: 空间清理达标
- **WHEN** 执行清理脚本
- **THEN** `df -h /` 显示 Available ≥5G
- **AND** Python 开发工具（python3/pip/git）保持可用

## MODIFIED Requirements

### Requirement: 3dtool-appimage 完整目录结构
`3dtool/3dtool-appimage/` SHALL 包含完整 AppImage 工作目录：AppRun（入口）、bin/（9 原生工具+kicad 7 项）、lib/（全部 .so 依赖库）、jre/（Java 运行时）、share/（kicad 资源）、python/（Python 3.14.4 + site-packages）。

### Requirement: install.sh R03 合规
`3dtool/wheels/install.sh` SHALL 不包含任何 `|| true` 静默吞错 fall-back，传递依赖安装失败必须记录到 FAILED_DEPS 并通过 log_warn 告警。

## REMOVED Requirements

### Requirement: pip download 替代方案
**Reason**: 违反 R03 禁止 fall-back，3dtool-appimage 精简版导致 AppRun check 12/25 失败
**Migration**: 用 token 方式完整 clone daheix/3dtool 仓库恢复完整 AppImage，wheels/ 目录作为补充（专有 Python 包）
