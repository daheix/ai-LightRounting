# Tasks

## 阶段一：磁盘空间清理（≥5G 可用）

- [ ] Task 1: 清理冗余系统工具释放空间
  - [ ] SubTask 1.1: 删除 swiftly（6.5G）、mise（3.0G）、rustup（1.8G）
  - [ ] SubTask 1.2: 删除 php-build、phpenv、nvm（已无对应软件源）
  - [ ] SubTask 1.3: 清理 pip cache（`pip cache purge`）+ /tmp 临时分片
  - [ ] SubTask 1.4: 验证 `df -h /` 显示 Available ≥5G

- [ ] Task 2: 清理 3dtool-appimage 重复大包
  - [ ] SubTask 2.1: 删除 site-packages/torch（756M，已在 wheels/torch-2.12.1.whl）
  - [ ] SubTask 2.2: 删除非项目依赖（llvmlite/skidl/sympy/pandas/plotly/sklearn/pyright/numba）
  - [ ] SubTask 2.3: 验证清理后空间进一步释放 ≥1G

## 阶段二：Token 方式完整 clone daheix/3dtool 仓库

- [ ] Task 3: Token 认证 clone 私有仓库
  - [ ] SubTask 3.1: 从 git remote URL 提取 GitHub token
  - [ ] SubTask 3.2: 执行 `git clone https://x-access-token:${TOKEN}@github.com/daheix/3dtool.git /tmp/3dtool-repo --depth 1`
  - [ ] SubTask 3.3: 验证 /tmp/3dtool-repo/3dtool-appimage-parts/ 含 17 个分片文件
  - [ ] SubTask 3.4: 验证 manifest.json 定义 11 个包结构

- [ ] Task 4: 恢复完整 AppImage
  - [ ] SubTask 4.1: 检查 restore_3dtool_appimage.sh 是否存在并阅读
  - [ ] SubTask 4.2: 执行 restore_3dtool_appimage.sh 合并 17 分片 + 解压
  - [ ] SubTask 4.3: 验证解压结果含 AppRun/bin/lib/jre/share/python 完整目录
  - [ ] SubTask 4.4: 验证 lib/ 含 libopenEMS.so.0、libelmersolver.so、libXaw.so.7、libXt.so.6

## 阶段三：完整融合到 workspace/3dtool/3dtool-appimage/

- [ ] Task 5: 替换精简版为完整版
  - [ ] SubTask 5.1: 删除现有 /workspace/3dtool/3dtool-appimage/（仅 AppRun + bin + python）
  - [ ] SubTask 5.2: 拷贝 /tmp/3dtool-full/ 到 /workspace/3dtool/3dtool-appimage/
  - [ ] SubTask 5.3: 保留 /workspace/3dtool/wheels/ 目录不动（15 个 wheel）
  - [ ] SubTask 5.4: 验证目录结构完整（AppRun/bin/lib/jre/share/python）

- [ ] Task 6: AppRun check 25/25 全通过
  - [ ] SubTask 6.1: 执行 `/workspace/3dtool/3dtool-appimage/AppRun check`
  - [ ] SubTask 6.2: 验证 9 原生工具全部 ✓（ngspice/openEMS/nf2ff/sar_calc/ElmerSolver/ElmerGrid/minisign/zsync2 + python）
  - [ ] SubTask 6.3: 验证 kicad 7 项全部 ✓（kicad/kicad-cli/eeschema/pcbnew/gerbview/pcb_calculator/bitmap2component/pl_editor）
  - [ ] SubTask 6.4: 验证 ldd checks 全部 ✓（openEMS/ElmerSolver/ngspice/kicad-cli 依赖库）

## 阶段四：工具链与三方库融合验证

- [ ] Task 7: Python 运行时与依赖验证
  - [ ] SubTask 7.1: 验证 AppRun python3 = Python 3.14.4
  - [ ] SubTask 7.2: 验证 site-packages 含 12 核心包（numpy/scipy/networkx/torch/gymnasium/matplotlib/yaml/klayout/simphony/sax/gdstk/shapely）
  - [ ] SubTask 7.3: 验证缺失包可从 wheels/ 补充（如 klayout/simphony/sax/gdstk/shapely）

- [ ] Task 8: install.sh R03 合规验证
  - [ ] SubTask 8.1: 验证 ALL_PACKAGES 含 gdstk/shapely（已修复）
  - [ ] SubTask 8.2: 验证无 `|| true` fall-back（已改为 FAILED_DEPS 记录+告警）
  - [ ] SubTask 8.3: 执行 `bash install.sh --check` 验证模式可用
  - [ ] SubTask 8.4: 创建 MANIFEST.txt 索引 wheel 清单

## 阶段五：剩余 P0/P1 任务验证与提交

- [ ] Task 9: 前次修复代码复验
  - [ ] SubTask 9.1: py_compile 8 个修改文件（verilog_a/calibration/gdsfactory_integration/data_loader/multiphysics×3/alpha_chip/simulator/reward_shaping）
  - [ ] SubTask 9.2: ruff check 全部通过
  - [ ] SubTask 9.3: 验证无 `except: pass`、`return None/[]/{}`、合成假数据

- [ ] Task 10: 提交所有变更到 main 分支
  - [ ] SubTask 10.1: git add 精确文件（3dtool/wheels/install.sh + MANIFEST.txt + spec 三件套）
  - [ ] SubTask 10.2: git commit -m "feat: token 方式完整恢复 3dtool 仓库 + install.sh R03 修复"
  - [ ] SubTask 10.3: git push origin main
  - [ ] SubTask 10.4: 更新操作记录.md + checklist.md + tasks.md 全部勾选

# Task Dependencies

- [Task 2] depends on [Task 1]（先清系统工具再清 appimage 重复包）
- [Task 3] depends on [Task 1+2]（需要 ≥5G 空间）
- [Task 4] depends on [Task 3]（clone 完成才能 restore）
- [Task 5] depends on [Task 4]（restore 完成才能替换）
- [Task 6] depends on [Task 5]（替换完成才能 check）
- [Task 7+8] depends on [Task 6]（check 通过后验证依赖）
- [Task 9] 可并行执行（不依赖 3dtool）
- [Task 10] depends on [Task 7+8+9]（全部完成后提交）
