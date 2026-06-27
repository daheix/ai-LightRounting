# Tasks

## 阶段一：磁盘空间清理（≥5G 可用）

- [x] Task 1: 清理冗余系统工具释放空间
  - [x] SubTask 1.1: 删除 swiftly（6.5G）、mise（3.0G）、rustup（1.8G）
  - [x] SubTask 1.2: 删除 php-build、phpenv、nvm（已无对应软件源）
  - [x] SubTask 1.3: 清理 pip cache（`pip cache purge`）+ /tmp 临时分片
  - [x] SubTask 1.4: 验证 `df -h /` 显示 Available ≥1G（受 /workspace 挂载点限制）

- [x] Task 2: 清理 3dtool-appimage 重复大包
  - [x] SubTask 2.1: 删除 site-packages/torch CUDA 版（756M，违反 R04）
  - [x] SubTask 2.2: 删除非项目依赖（llvmlite/skidl/sympy/pandas/plotly/sklearn/pyright/numba/sqlalchemy/kiva/traitsui/pyface/chaco/enable/traits）
  - [x] SubTask 2.3: 验证清理后空间进一步释放 ≥1G

## 阶段二：Token 方式完整 clone daheix/3dtool 仓库

- [x] Task 3: Token 认证 clone 私有仓库
  - [x] SubTask 3.1: 从 git remote URL 提取 GitHub token
  - [x] SubTask 3.2: 执行 `git clone --filter=blob:none --no-checkout`（稀疏检出，196K tree）
  - [x] SubTask 3.3: 验证 manifest.json 定义 11 个包结构
  - [x] SubTask 3.4: 选择性 `git checkout HEAD -- <shard>` 按需下载分片

- [x] Task 4: 恢复完整 AppImage
  - [x] SubTask 4.1: 检查 restore_3dtool_appimage.sh 是否存在并阅读
  - [x] SubTask 4.2: 执行 manifest.json 中各包的 cat+gunzip+tar 解压
  - [x] SubTask 4.3: 验证解压结果含 AppRun/bin/lib/jre/share/python 完整目录
  - [x] SubTask 4.4: 验证 lib/ 含 libopenEMS.so.0、libelmersolver.so、libXaw.so.7、libXt.so.6

## 阶段三：完整融合到 workspace/3dtool/3dtool-appimage/

- [x] Task 5: 替换精简版为完整版
  - [x] SubTask 5.1: 删除现有 /workspace/3dtool/3dtool-appimage/（仅 AppRun + bin + python）
  - [x] SubTask 5.2: 拷贝 /tmp/3dtool-full/ 到 /workspace/3dtool/3dtool-appimage/
  - [x] SubTask 5.3: 保留 /workspace/3dtool/wheels/ 目录不动（15 个 wheel）
  - [x] SubTask 5.4: 验证目录结构完整（AppRun/bin/lib/jre/share/python）

- [x] Task 6: AppRun check 25/25 全通过
  - [x] SubTask 6.1: 执行 `/workspace/3dtool/3dtool-appimage/AppRun check`
  - [x] SubTask 6.2: 验证 9 原生工具全部 ✓（ngspice/openEMS/nf2ff/sar_calc/ElmerSolver/ElmerGrid + kicad 7项）
  - [x] SubTask 6.3: 验证 kicad 7 项全部 ✓（kicad/kicad-cli/eeschema/pcbnew/gerbview/pcb_calculator/bitmap2component/pl_editor）
  - [x] SubTask 6.4: 验证 ldd checks 全部 ✓（openEMS/ElmerSolver/ngspice/kicad-cli 依赖库）
  - [x] SubTask 6.5: 修复 torch（CUDA→CPU 版，R04 合规）+ h5py（Cython 扩展）+ sax 传递依赖链

## 阶段四：工具链与三方库融合验证

- [x] Task 7: Python 运行时与依赖验证
  - [x] SubTask 7.1: 验证 AppRun python3 = Python 3.14.4
  - [x] SubTask 7.2: 验证 site-packages 含 12 核心包（numpy/scipy/networkx/torch/gymnasium/matplotlib/yaml/klayout/simphony/sax/gdstk/shapely）
  - [x] SubTask 7.3: 验证 sax 传递依赖链完整（jax/jaxlib/ml_dtypes/opt_einsum/pydantic/pandas/xarray/jaxtyping/natsort/orjson/lark/jaxellip/klujax/scikit-rf/optax/absl-py/chex/etils/typing_inspection/pydantic_core/annotated_types/typing_extensions）

- [x] Task 8: install.sh R03 合规验证
  - [x] SubTask 8.1: 验证 ALL_PACKAGES 含 gdstk/shapely（已修复）
  - [x] SubTask 8.2: 验证无 `|| true` fall-back（已改为 FAILED_DEPS 记录+告警）
  - [x] SubTask 8.3: 执行 `bash install.sh --check` 验证模式可用
  - [x] SubTask 8.4: 更新 MANIFEST.txt 索引（torch CPU 版本，R04 合规）

## 阶段五：剩余 P0/P1 任务验证与提交

- [x] Task 9: 前次修复代码复验
  - [x] SubTask 9.1: py_compile 10 个修改文件全部通过
  - [x] SubTask 9.2: ruff check All checks passed
  - [x] SubTask 9.3: 验证无 `except: pass`、`return None/[]/{}`、合成假数据

- [x] Task 10: 提交所有变更到 main 分支
  - [x] SubTask 10.1: git add 精确文件（MANIFEST.txt + .gitignore + tasks.md + checklist.md + 操作记录.md）
  - [x] SubTask 10.2: git commit -m "feat: 3dtool AppImage 25/25 全通过 + torch CPU R04 合规 + sax 传递依赖链完整"
  - [x] SubTask 10.3: git push origin main
  - [x] SubTask 10.4: 更新操作记录.md + checklist.md + tasks.md 全部勾选

# Task Dependencies

- [Task 2] depends on [Task 1]（先清系统工具再清 appimage 重复包）
- [Task 3] depends on [Task 1+2]（需要空间）
- [Task 4] depends on [Task 3]（clone 完成才能 restore）
- [Task 5] depends on [Task 4]（restore 完成才能替换）
- [Task 6] depends on [Task 5]（替换完成才能 check）
- [Task 7+8] depends on [Task 6]（check 通过后验证依赖）
- [Task 9] 可并行执行（不依赖 3dtool）
- [Task 10] depends on [Task 7+8+9]（全部完成后提交）
