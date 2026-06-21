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

### 1.2 代码提交纪律（每 20 分钟一次）
- 实现过程中，每 20 分钟必须向远端 `main` 分支提交一次代码（由 `scripts/auto_merge.py` 后台守护进程自动执行）。
- 提交流程（自动）：
  1. `git add` 相关变更文件（按文件名精确添加，禁止 `git add -A`/`git add .`）
  2. `git commit -m "<type>: <简述>"`，type 遵循 Conventional Commits（feat/fix/docs/refactor/test/chore）
  3. `git push origin main`
  4. 切回开发分支继续开发
- 若 20 分钟内仍在进行复杂改动，先创建一个可编译/可测试的中间状态再提交，保证 `main` 分支始终可用。
- 提交前必须通过本地 lint/typecheck（如 ruff、mypy、pytest 冒烟测试）。
- 禁止 force push 到 `main`；禁止提交含密钥/凭据的文件。
- 没有代码更新和新文件更新时，等待下次上传，不创建空提交。

### 1.3 完整产品流程遵守
- 完整的产品研发流程必须遵守，不得跳过：
  1. 需求与方案检索（本规则 1.1）
  2. 设计（数据结构、接口、模块划分）
  3. 实现（编码 + 每 5 分钟提交）
  4. 测试（单元测试 + 集成测试 + 约束合规测试）
  5. 验证（按 checklist.md 逐项核对）
  6. 文档与来源溯源更新
- 任何阶段不得省略来源标注与测试验证。

## 规则 2：项目目录结构规范（强制）

按商业版本工具管理标准，项目采用 `src layout` + 三方工具统一管理 + 发布制品分离的目录结构。
**所有文件必须放在规定位置，禁止乱放。**

### 2.1 顶层目录结构

```
/workspace/
├── 3dtool/              # 三方工具统一管理（规则 3/4/5）
│   └── wheels/              # 离线 wheel 包（沙箱重启一键恢复，规则 5.1.1）
├── src/                 # 所有自研代码（src layout，规则 5）
├── publish/             # 产品发布制品（规则 6）
├── tests/               # 测试代码（规则 7）
├── scripts/             # 工具脚本（质量门禁/训练/数据提取）
├── data/                # 数据（基准电路/变体数据集）
├── checkpoints/         # 训练检查点
├── docs/                # 项目文档（设计文档/优化日志）
├── .trae/rules/         # 项目规则（本文件）
├── pyproject.toml       # 项目配置（构建/lint/pytest）
├── 操作记录.md           # 操作记录（规则 19）
└── README.md            # 项目概述
```

### 2.2 目录职责与放置规则

| 目录 | 职责 | 放置规则 | 禁止 |
|------|------|----------|------|
| `3dtool/` | 三方工具说明文档 + 自研复刻品 | 按规则 3/4 分类存放 | ❌ 禁止放自研业务代码 |
| `src/polaris/` | 所有自研 Python 包代码 | 按 `data/engine/eval/nn/pdk/pipeline/router/sim/trainer` 分模块 | ❌ 禁止放测试/脚本/数据 |
| `publish/` | 发布给第三方的制品 | `wheels/`（构建包）+ `docs/`（用户文档）+ `examples/`（示例） | ❌ 禁止放源码 |
| `tests/` | 所有测试代码 | `test_<module>.py` 命名 | ❌ 禁止放业务代码 |
| `scripts/` | 工具脚本 | 质量门禁/训练脚本/数据提取 | ❌ 禁止放可被 import 的业务模块 |
| `data/` | 数据文件 | `benchmarks/`（基准）+ `variants/`（变体） | ❌ 禁止放代码 |
| `checkpoints/` | 训练检查点 | 按 `rl_<config>/` 分目录 | ❌ 禁止提交到 git（.gitignore） |
| `docs/` | 项目文档 | 设计文档/优化日志/训练日志 | ❌ 禁止放代码 |

### 2.3 src/polaris/ 内部模块划分

```
src/polaris/
├── data/       # 数据加载与电路规格（CircuitSpec/DeviceSpec/data_loader）
├── engine/     # 布局引擎（FloorplanEnv/GNN/CNN/Netlist/Routability）
├── eval/       # 评估与渲染（layout_render）
├── nn/         # 纯 NumPy 神经网络库（复刻 torch，对应 3dtool/pycopy/pyCopyTorch）
├── pdk/        # 光子器件库（SOI/SiN/InP/LNOI 四平台）
├── pipeline/   # 端到端流水线（IntegratedPipeline/Training）
├── router/     # 布线引擎（WaveguideRouter/RoutingEnv/multilayer/opto_electrical）
├── sim/        # 仿真系统（S参数/级联/约束检查/SimLoop/校准）
└── trainer/    # 训练器（PPO/GNN_PPO/dataset/reward_shaping/train_loop）
```

### 2.4 文件放置强制规则

1. **新代码必须放 `src/polaris/<module>/`**：禁止在项目根目录创建 Python 包
2. **新三方工具说明必须放 `3dtool/<category>/`**：禁止在 src/ 或根目录放工具说明
3. **新复刻品必须放 `3dtool/pycopy/pyCopy<Xxx>/`**：加 `pyCopy` 前缀，禁止放 src/
4. **新测试必须放 `tests/test_<module>.py`**：禁止在 src/ 下放测试
5. **新脚本必须放 `scripts/`**：禁止在 src/ 或根目录放脚本
6. **新数据必须放 `data/`**：禁止在 src/ 或根目录放数据文件
7. **新文档必须放 `docs/` 或 `publish/docs/`**：禁止在 src/ 下放文档

来源:
- Python src layout: https://packaging.python.org/en/latest/discussions/src-layout/
- PEP 8 模块结构: https://peps.python.org/pep-0008/#module-level-dunder-names

## 规则 3：三方工具统一管理规范（强制）

所有第三方工具统一存放在 `3dtool/` 目录，按类别分目录管理。每个工具必须有独立的说明文档。

### 3.1 3dtool/ 目录结构

```
3dtool/
├── README.md              # 三方工具总览
├── wheels/                # 离线 wheel 包（沙箱重启一键恢复，规则 5.1.1）
│   ├── install.sh             # 一键离线安装脚本（核心入口）
│   ├── MANIFEST.txt           # wheel 清单与 SHA256 校验和
│   ├── *.whl                  # 小 wheel（<24MB，直接存放）
│   └── parts/                 # 大 wheel 分卷片段（≤20MB，绕过 GitHub 24MB 限制）
├── layout/                # 版图类工具
├── simulation/            # 仿真类工具
├── ml/                    # 机器学习类工具
├── numeric/               # 数值计算类工具
├── viz/                   # 可视化类工具
├── serialization/         # 序列化类工具
└── pycopy/                # 自研复刻工具（规则 4）
```

### 3.2 三方工具清单与安装状态（实际核查 2026-06-20）

#### layout/ — 版图类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| gdsfactory | ❌ 未装 | — | 版图生成/PDK/GDS导出 | `pip install gdsfactory` | src/polaris/pdk/ 参考 |
| klayout | ✅ 已装 | 0.30.9 | DRC/LVS/版图查看 | `pip install klayout` | src/polaris/eval/layout_render.py |
| gdstk | ❌ 未装 | — | 高性能 GDS 读写 | `pip install gdstk` | gdsfactory 依赖 |

#### simulation/ — 仿真类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| meep | ❌ 未装 | — | FDTD 电磁仿真 | `pip install meep` | 器件级仿真 |
| simphony | ✅ 已装 | 0.7.3 | 光子电路 S 参数仿真 | `pip install simphony` | src/polaris/sim/simulator.py |
| sax | ✅ 已装 | 0.14.7 | 频率域仿真 | `pip install sax` | src/polaris/sim/cascade.py（有 pyCopySAX 复刻） |
| SiPANN | ❌ 未装 | — | 硅光器件模型 | `pip install SiPANN` | src/polaris/sim/models.py（已复刻） |
| femwell | ❌ 未装 | — | FEM 模式求解器 | `pip install femwell` | 模式求解 |
| meow | ❌ 未装 | — | 模式求解器 | `pip install meow` | 模式求解 |

#### ml/ — 机器学习类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| torch | ✅ 已装 | 2.12.1+cpu | GNN/PPO 神经网络 | `pip install torch` | src/polaris/trainer/ppo_torch.py |
| gymnasium | ✅ 已装 | 1.3.0 | RL 环境 | `pip install gymnasium` | src/polaris/engine/floorplan_env.py |
| networkx | ✅ 已装 | 3.6.1 | 图算法 | `pip install networkx` | src/polaris/engine/netlist.py |

#### numeric/ — 数值计算类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| numpy | ✅ 已装 | 2.4.6 | 数值计算 | `pip install numpy` | 全项目核心 |
| scipy | ✅ 已装 | 1.17.1 | 优化求解 | `pip install scipy` | 优化求解 |
| shapely | ❌ 未装 | — | 几何运算 | `pip install shapely` | constraint_checker 用纯 Python 实现 |

#### viz/ — 可视化类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| matplotlib | ✅ 已装 | 3.11.0 | 版图渲染 | `pip install matplotlib` | src/polaris/eval/layout_render.py |

#### serialization/ — 序列化类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| pyyaml | ✅ 已装 | 6.0.3 | 网表/配置序列化 | `pip install pyyaml` | src/polaris/engine/netlist.py 等 |

#### dev/ — 开发类工具

| 工具 | 安装状态 | 版本 | 用途 | 安装命令 | 项目使用位置 |
|------|---------|------|------|----------|-------------|
| pytest | ✅ 已装 | 9.1.0 | 测试框架 | `pip install pytest` | tests/ |
| ruff | ✅ 已装 | 0.15.18 | Lint + Format | `pip install ruff` | 全项目 |
| mypy | ✅ 已装 | 2.1.0 | 类型检查 | `pip install mypy` | src/polaris/ |
| wheel | ✅ 已装 | 0.47.0 | wheel 构建 | `pip install wheel` | 打包 |
| setuptools | ✅ 已装 | 81.0.0 | 构建工具 | `pip install setuptools` | 打包 |

**注**：所有已装工具均已在 `3dtool/wheels/` 离线打包，沙箱重启后执行
`bash 3dtool/wheels/install.sh --all` 一键恢复（70 秒，规则 5.1.1）。
install.sh 统一安装全部依赖（无核心/可选之分），确保环境完整。

### 3.3 工具使用原则

1. **优先直接集成**：能用 pip 安装的开源库，直接集成，不重复造轮子
2. **复刻须 100% 可用**：不好集成的，用纯 Python 复刻完整可用版本（规则 4）
3. **来源须标注**：每个集成的工具记录来源 URL（规则 15）
4. **依赖完整安装**：install.sh 统一安装全部依赖（无核心/可选之分），确保环境完整
5. **不依赖商业工具**：禁止依赖 Lumerical/IPKISS/Tidy3D 等商业软件作为核心功能
6. **说明文档同步**：工具安装状态变更后，必须同步更新 `3dtool/<category>/README.md`

### 3.4 工具说明文档规范

每个三方工具在 `3dtool/<category>/README.md` 中必须包含：
- 工具名称与用途
- 安装状态（✅ 已装 / ❌ 未装）与版本
- 来源 URL
- 安装命令
- 项目中的使用位置（src/polaris/ 具体文件）
- 是否有复刻品兜底（如有，指向 `3dtool/pycopy/pyCopy<Xxx>/`）

## 规则 4：自研复刻工具规范（强制）

对于开源但安装困难的工具，按规则用纯 Python 100% 复刻，复刻品统一存放在 `3dtool/pycopy/`，
加 `pyCopy` 前缀表示是替代品。

### 4.1 复刻触发条件

满足以下任一条件即触发 100% 复刻：
- 该工具为开源但无对应平台的预编译 wheel
- 安装需复杂系统级依赖（如 C++/Fortran 编译链、MPI、CUDA toolkit 非标准路径）
- 在目标运行环境（Linux 沙箱/CI）中 `pip install` 失败或不可用
- 集成成本（编译/配置/调试）高于自行复刻等价实现
- 依赖链过重（如 sax 依赖 jax/jaxlib/optax 等 200+ MB，但项目只用其子网络增长算法）

### 4.2 复刻品目录结构

```
3dtool/pycopy/
├── __init__.py                    # pycopy 包入口
├── README.md                      # 复刻品清单与设计原则
├── pyCopyTorch/__init__.py        # 复刻 torch（重导出 src/polaris/nn）
├── pyCopySAX/__init__.py          # 复刻 sax（重导出 src/polaris/sim/cascade）
├── pyCopySiPANN/__init__.py       # 复刻 SiPANN（重导出 src/polaris/sim/models）
├── pyCopyKLayout/__init__.py      # 复刻 klayout DRC（重导出 src/polaris/sim/constraint_checker）
├── pyCopyMEEP/__init__.py         # 预留（未实现）
├── pyCopyFemwell/__init__.py      # 预留（未实现）
└── pyCopyMeow/__init__.py         # 预留（未实现）
```

### 4.3 复刻品清单（实际状态 2026-06-19）

| 复刻包 | 原工具 | 协议 | 复刻位置（src/） | 状态 | 复刻内容 |
|--------|--------|------|-----------------|------|----------|
| pyCopyTorch | torch | BSD-3-Clause | src/polaris/nn/ | ✅ 完整 | Tensor/autograd/Linear/LayerNorm/ReLU/Sequential/Adam/Conv2d/MaxPool2d |
| pyCopySAX | sax | Apache-2.0 | src/polaris/sim/cascade.py | ✅ 完整 | 子网络增长算法（cascade_circuit） |
| pyCopySiPANN | SiPANN | MIT | src/polaris/sim/models.py | ✅ 完整 | 10 个 S 参数模型（waveguide/y_branch/DC/ring/MMI/GC/crossing/terminator/phase_shifter） |
| pyCopyKLayout | klayout DRC | GPL-2.0 | src/polaris/sim/constraint_checker.py | ✅ 完整 | 8 种违规检查（bend_radius/spacing/loss/crossings/overlap/min_width/coupling_gap） |
| pyCopyMEEP | meep FDTD | GPL-2.0+ | — | ⏳ 预留 | 未实现（项目未使用 FDTD） |
| pyCopyFemwell | femwell | MIT | — | ⏳ 预留 | 未实现（项目未使用 FEM） |
| pyCopyMeow | meow | GPL-3.0 | — | ⏳ 预留 | 未实现（项目未使用模式求解） |

### 4.4 复刻质量要求（100% 一致）

- **逻辑一致**：复刻实现的代码逻辑须与原开源工具 100% 一致，包括算法步骤、边界条件、数值处理顺序
- **行为对比验证**：须编写对比测试，对同一输入断言输出一致（浮点数允许 1e-9 容差）；
  若原工具无法安装，须用原仓库的官方测试用例/文档示例作为基准验证
- **来源标注**：复刻代码须在文件头注明原仓库 URL、协议、commit/版本号
- **接口兼容**：复刻模块须暴露与原工具等价的公开 API（函数名/参数名/返回值）
- **不留半成品**：复刻须覆盖项目实际使用的全部功能子集，禁止只复刻入口而留空实现

### 4.5 复刻品入口重导出规范

`3dtool/pycopy/pyCopy<Xxx>/__init__.py` 必须重导出 src/polaris/ 对应模块的公开 API：

```python
"""pyCopyTorch — torch 纯 NumPy 100% 复刻（规则 4）。

原工具: PyTorch https://pytorch.org/ (BSD-3-Clause)
复刻位置: src/polaris/nn/
"""

from polaris.nn import Tensor, Linear, Adam  # noqa: F401

__all__ = ["Tensor", "Linear", "Adam"]
```

上层代码可通过两种方式访问复刻 API：
```python
# 方式 1：通过复刻包名（推荐，明确表示使用复刻品）
from pycopy.pyCopyTorch import Tensor

# 方式 2：通过 polaris 包（等价）
from polaris.nn import Tensor
```

### 4.6 验证与回归

- 每个复刻模块须附带对比测试（`tests/test_replica_*.py` 或对应模块测试）
- CI 中优先尝试 `pip install` 原工具；安装失败时自动跳过对比测试但保留复刻自测
- 复刻实现须通过 `ruff` + `mypy` 检查

## 规则 5：工具环境安装与使用规范（强制）

**工具的安装和使用是项目正常运行的基础，必须严格遵循本规范。**

### 5.1 环境安装顺序

**沙箱/新环境首选离线安装**（规则 5.1.1），仅当离线 wheel 包不存在或不兼容时
才使用联网 pip 安装。

#### 5.1.1 离线一键安装（沙箱/新环境必用，强制）

**沙箱环境随时重启，pip 安装的工具会全部丢失。** 重新联网下载需 4+ 小时，
项目已将全部依赖打包为离线 wheel，重启后执行一条命令 70 秒恢复：

```bash
# 沙箱重启后必做：一键离线安装全部依赖（首选方案）
bash 3dtool/wheels/install.sh --all

# 仅检查环境（不安装）
bash 3dtool/wheels/install.sh --check

# 仅安装核心依赖
bash 3dtool/wheels/install.sh --core

# 仅安装开发依赖
bash 3dtool/wheels/install.sh --dev
```

**离线 wheel 包结构**（详见 `3dtool/wheels/README.md`）：
- `3dtool/wheels/*.whl`：小 wheel（<24MB，79 个，直接存放）
- `3dtool/wheels/parts/*.part_*`：大 wheel 分卷片段（≤20MB，18 个）
  - torch 184MB → 9 个分片
  - jaxlib 82MB → 5 个分片
  - scipy 34MB → 2 个分片
  - klayout 27MB → 2 个分片
- `install.sh` 自动合并分卷 + gunzip 还原 + pip install --no-index

**为什么分卷**：GitHub 限制单文件 ≤24MB，大 wheel 经 gzip 压缩 + split 分卷后
每个片段 ≤20MB，可正常提交。install.sh 安装时自动还原。

**torch CPU 版本**：打包的是 `torch 2.12.1+cpu`（184MB），非 GPU 版（532MB + 2GB CUDA）。
沙箱通常无 GPU，CPU 版功能完整仅速度较慢。如需 GPU 版本，在有 GPU 的环境执行
`pip install torch`（自动安装 GPU 版本）。

**平台限制**：当前 wheel 仅适用 Linux x86_64 + Python 3.14。其他平台需重新生成：
```bash
pip download --dest 3dtool/wheels/ numpy scipy networkx torch gymnasium matplotlib pyyaml
pip download --dest 3dtool/wheels/ klayout simphony sax
pip download --dest 3dtool/wheels/ pytest ruff mypy wheel setuptools
# 大 wheel 需分卷压缩（>24MB 的文件）
for f in 3dtool/wheels/*.whl; do
  size=$(stat -c%s "$f")
  if [ "$size" -gt 25165824 ]; then
    gzip -c "$f" | split -b 20M - "3dtool/wheels/parts/${f##*/}.gz.part_"
    rm "$f"
  fi
done
```

#### 5.1.2 联网 pip 安装（备用方案，离线包不可用时）

仅当离线 wheel 包不存在、不兼容当前平台、或需安装新工具时使用：

```bash
# 1. 全部依赖（install.sh 离线包不可用时，联网安装）
pip install numpy scipy networkx torch gymnasium matplotlib pyyaml
pip install klayout simphony sax
pip install pytest ruff mypy wheel setuptools

# 2. 安装本项目（开发模式）
pip install -e .
```

**未安装工具说明**（项目未直接使用，无需安装）：
- `gdsfactory`/`gdstk`：版图生成，项目用自研 PDK
- `SiPANN`：硅光器件模型，已有 pyCopySiPANN 完整复刻
- `meep`：FDTD 电磁仿真，项目未使用器件级 FDTD
- `femwell`/`meow`：FEM 模式求解器，项目未使用
- `shapely`：几何运算，constraint_checker 用纯 Python 实现

**重要**：联网安装新工具后，必须同步更新离线 wheel 包（规则 5.5.3）。

### 5.2 工具安装决策矩阵

| 工具 | 是否安装 | 决策依据 |
|------|---------|----------|
| numpy/scipy/networkx/matplotlib/pyyaml | ✅ 必装 | 核心依赖，pip 即用 |
| torch | ✅ 必装 | GNN/PPO 训练核心（CPU 版 2.12.1+cpu，也有 pyCopyTorch 复刻） |
| gymnasium | ✅ 必装 | RL 环境核心 |
| klayout | ✅ 必装 | GDS 导出 + DRC |
| simphony | ✅ 必装 | S 参数仿真 |
| sax | ✅ 必装 | 已离线打包（含 jax/jaxlib/optax 依赖链），也有 pyCopySAX 复刻 |
| pytest/ruff/mypy/wheel/setuptools | ✅ 必装 | 开发工具链 |
| gdsfactory | ❌ 未装 | 版图生成，依赖链中等，项目未直接使用 |
| gdstk | ❌ 未装 | GDS 高性能读写，gdsfactory 依赖 |
| SiPANN | ❌ 未装 | 已有 pyCopySiPANN 完整复刻 |
| meep | ❌ 未装 | FDTD 重型依赖，项目未使用器件级 FDTD |
| femwell/meow | ❌ 未装 | FEM 模式求解器，项目未使用 |
| lygadgets | ❌ 未装 | KLayout 已直接安装，无需 lygadgets 工具链 |
| shapely | ❌ 未装 | constraint_checker 用纯 Python 实现 |

**注**：所有标记 ✅ 必装的工具均已在 `3dtool/wheels/` 离线打包，由 install.sh 统一安装。

### 5.3 工具使用规范

**规则 5.2 强制**：所有依赖均为必装，无可选依赖。代码中直接 import 三方工具，
禁止 try/except 回退（例外：gdsfactory/SiPANN 因上游 Python 3.14 兼容性问题保留兜底）。

1. **三方工具直接 import**：代码中 import 三方工具时直接 import，禁止 try/except 回退
   ```python
   # 正确（规则 5.2 必装依赖）
   import sax as _sax

   # 错误（禁止可选依赖回退）
   # try:
   #     import sax as _sax
   #     _HAS_SAX = True
   # except ImportError:
   #     _sax = None
   ```
2. **复刻品定位**：复刻品（pyCopy*）作为算法学习与对照实现保留，不再作为运行时兜底
3. **核心功能依赖**：核心功能（PDK/布局/布线/训练）直接依赖三方工具，复刻品仅用于算法对照
4. **import 位置**：三方工具的 import 在模块顶部或函数内部直接 import
5. **测试兼容**：测试中直接 import 三方工具；仅 gdsfactory/SiPANN 因上游兼容性问题保留 importorskip

**例外说明**（上游兼容性问题，非项目可控）：
- `gdsfactory`：8.18.0 锁定 pydantic<2.10，pydantic<2.10 的 pydantic-core 无 Python 3.14 wheel
- `SiPANN`：依赖 tensorflow，tensorflow 无 Python 3.14 wheel
- 在 Python 3.10-3.13 环境下两者均为必装

### 5.4 环境验证命令

部署完成后，运行以下命令验证环境：

```bash
# 1. 一键环境检查（推荐，自动检查全部依赖）
bash 3dtool/wheels/install.sh --check

# 2. 验证核心依赖
python -c "import numpy, scipy, networkx, torch, gymnasium, matplotlib, yaml; print('core OK')"

# 3. 验证仿真依赖
python -c "import klayout; print('klayout OK')"
python -c "import simphony; print('simphony OK')"
python -c "import sax; print('sax OK')"

# 4. 验证复刻品
python -c "from pycopy.pyCopyTorch import Tensor; print('pyCopyTorch OK')"
python -c "from pycopy.pyCopySAX import cascade_circuit; print('pyCopySAX OK')"

# 5. 验证项目包
python -c "import polaris; print('polaris OK')"

# 6. 运行测试
python -m pytest tests/ -q --tb=short
```

### 5.5 工具状态同步

- 每次安装/卸载工具后，必须同步更新 `3dtool/<category>/README.md` 的安装状态
- 每次新增复刻品后，必须同步更新 `3dtool/pycopy/README.md` 和本规则 4.3 表格
- 环境变更须在 `操作记录.md` 中记录

### 5.5.1 离线 wheel 包同步（强制）

**每次新增/升级/删除依赖后，必须同步更新离线 wheel 包**，保证沙箱重启后能完整恢复：

1. **新增依赖**：`pip download --dest 3dtool/wheels/ <new_package>`
2. **升级依赖**：删除旧 wheel → `pip download --dest 3dtool/wheels/ <package>` 下载新版本
3. **删除依赖**：`rm 3dtool/wheels/<package>-*.whl`
4. **大 wheel 分卷**：>24MB 的 wheel 必须分卷压缩到 `parts/`（规则 5.1.1）
5. **更新清单**：重新生成 `3dtool/wheels/MANIFEST.txt`（含 SHA256 校验和）
6. **验证安装**：执行 `bash 3dtool/wheels/install.sh --check` 确认完整

**禁止行为**：
- ❌ 禁止提交 >24MB 的 wheel 文件到 git（GitHub 会拒绝）
- ❌ 禁止删除 `parts/` 分卷片段而不删除对应的小 wheel（会导致安装失败）
- ❌ 禁止修改 `install.sh` 的分卷还原逻辑（会导致大 wheel 无法还原）

## 规则 6：发布制品管理规范（强制）

`publish/` 目录存放产品发布给第三方用的制品，与源码分离。

### 6.1 publish/ 目录结构

```
publish/
├── README.md          # 发布说明
├── wheels/            # 构建 wheel 包（polaris 项目自身的发布包，非依赖）
├── docs/              # 发布文档（用户手册/API 参考/安装指南）
└── examples/          # 使用示例代码（4 个示例脚本）
```

**注意区分**：
- `3dtool/wheels/`：存放**第三方依赖**的离线 wheel 包（numpy/torch 等），用于沙箱重启恢复
- `publish/wheels/`：存放**本项目** polaris 的构建 wheel 包，用于发布给第三方安装

### 6.2 发布流程

```bash
# 1. 构建 wheel
python -m build --wheel --outdir publish/wheels/

# 2. 生成文档（TODO: 配置 sphinx/mkdocs）

# 3. 打包示例
cp -r examples/* publish/examples/
```

### 6.3 版本管理

遵循 SemVer 语义化版本：`MAJOR.MINOR.PATCH`
- MAJOR: 不兼容的 API 修改
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的 Bug 修复

当前版本: 0.1.0 (Pre-Alpha)

## 规则 7：工业标准代码质量门禁（强制）

按照工业标准完成代码编写和管理，所有代码必须通过质量门禁检查方可提交。
门禁脚本位于 `scripts/code_quality_gate.py`，CI 与本地提交前必须运行通过。

### 7.1 文件规模硬性限制（触发即必须重构）

| 指标 | 警告阈值 | 硬性上限（触发重构） | 依据 |
|------|----------|----------------------|------|
| 单文件大小 | 80 KB | **120 KB** | 工业实践：大文件降低可读性与可维护性 |
| 单文件有效代码行数 | 500 行 | **800 行** | PEP 8/Google Style：目标 300-500 行/文件 |
| 单函数有效代码行数 | 40 行 | **80 行** | Google Python Style Guide：超过 40 行应考虑拆分 |
| 单函数圈复杂度 (McCabe) | 10 | **15** | McCabe 1976 / NIST ISO 25010：V(G)≤10 为可维护 |
| 单函数参数个数 | 5 | **7** | Google Style：参数过多降低可读性 |
| 单类方法数 | 20 | **30** | 单一职责原则 |
| 嵌套深度 | 4 | **5** | 深嵌套降低可读性，应用卫语句扁平化 |

**硬性上限含义**：超过即触发 CI 门禁失败，必须重构拆分后方可合并。
**警告阈值含义**：CI 输出警告，建议但不阻断。

**测试文件豁免**：`tests/` 目录下的文件和 `test_*.py` 文件默认**不受质量门禁管控**
（测试代码以可读性和覆盖率为优先，函数/复杂度限制放宽）。如需检查测试文件，
使用 `--include-tests` 参数。测试文件仍须通过 ruff lint 和 pytest。

来源：
- Google Python Style Guide 函数长度: https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules.html#id17
- PEP 8 行宽与风格: https://peps.python.org/pep-0008/
- McCabe 圈复杂度: McCabe, "A Complexity Measure", IEEE TSE 1976, https://ieeexplore.ieee.org/document/1702388
- NIST ISO/IEC 25010 可维护性: https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
- 文件行数最佳实践: https://alchemiststudios.ai/articles/python-linting-sop.html

### 7.2 重构触发后的操作流程

当文件/函数超过硬性上限时，必须执行以下流程：

1. **停止新增功能**：在该文件/函数上停止新增功能代码
2. **分析职责**：分析文件/函数承担的职责，识别可拆分的边界
3. **拆分模块**：按单一职责原则拆分为多个子模块/子函数
4. **保持接口兼容**：拆分后通过 `__init__.py` 重导出，保持上层调用不变
5. **更新测试**：拆分后更新对应测试，确保覆盖率不下降
6. **通过门禁**：重新运行 `python scripts/code_quality_gate.py` 确认通过

### 7.3 圈复杂度 (Cyclomatic Complexity) 标准

圈复杂度衡量函数内线性独立路径数，反映测试难度与缺陷风险。

| 等级 | 复杂度范围 | 风险评估 | 处理策略 |
|------|-----------|----------|----------|
| A | 1-5 | 简单，低风险 | 无需处理 |
| B | 6-10 | 适中，可接受 | 正常开发 |
| C | 11-15 | 偏高，需关注 | 建议重构（Extract Method） |
| D-F | 16+ | 高风险，难测试 | **必须重构** |

降低复杂度的重构手法：
- **Extract Method（提取方法）**：将复杂条件分支提取为独立函数
- **Guard Clauses（卫语句）**：用提前返回替代嵌套 if-else
- **Strategy Pattern（策略模式）**：用多态替代 switch/elif 链
- **State Machine（状态机）**：用状态机替代复杂状态判断

来源：
- McCabe 1976 原始论文: https://ieeexplore.ieee.org/document/1702388
- Sourcegraph 复杂度指南: https://sourcegraph.com/blog/cyclomatic-complexity-what-it-is-and-how-to-reduce-it
- Radon 工具文档: https://radon.readthedocs.io/

### 7.4 质量门禁脚本（`scripts/code_quality_gate.py`）

门禁脚本自动检查以下指标，任一硬性上限超标即返回非零退出码：

```bash
# 运行质量门禁（CI 与提交前必做，默认检查 src/polaris/）
python scripts/code_quality_gate.py

# 仅检查特定目录
python scripts/code_quality_gate.py src/polaris/

# 输出 JSON 报告
python scripts/code_quality_gate.py --json > quality_report.json

# 增量模式：仅检查 git 暂存区文件（pre-commit hook 使用）
python scripts/code_quality_gate.py --staged

# 包含测试文件检查（默认排除）
python scripts/code_quality_gate.py --include-tests
```

检查项：
1. 文件大小（KB）与有效代码行数（SLOC，去除空行与注释）
2. 每个函数的有效代码行数
3. 每个函数的圈复杂度（基于 AST 决策节点计数）
4. 函数参数个数
5. 类方法数
6. 嵌套深度

### 7.5 Pre-commit Hook 自动门禁（强制）

**每次 `git commit` 时自动执行质量门禁，不通过则禁止提交。**

安装方法（项目初始化时执行一次）：
```bash
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Hook 执行的检查（仅检查本次暂存的文件，增量检查）：
1. **质量门禁**：`python scripts/code_quality_gate.py --staged`（规则 7）
2. **Ruff lint**：`ruff check <staged_files>`
3. **Ruff format**：`ruff format --check <staged_files>`
4. **Pytest 冒烟测试**：`pytest tests/ -q -x --tb=short`

任一检查失败即阻止提交（exit 1）。

临时跳过（仅紧急情况，不推荐）：`git commit --no-verify`

## 规则 8：Python 编码风格规范（强制）

### 8.1 基础风格标准

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

来源：
- PEP 8: https://peps.python.org/pep-0008/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide
- PEP 257 文档字符串: https://peps.python.org/pep-0257/

### 8.2 强制工具链

```toml
# pyproject.toml 配置（已在项目中）
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
```

提交前必须通过：
```bash
ruff check src/ tests/ 3dtool/          # lint 检查
ruff format --check src/ tests/ 3dtool/ # 格式检查
mypy src/polaris/ --ignore-missing-imports  # 类型检查（可选但推荐）
```

### 8.3 代码组织原则

1. **单一职责**：每个模块/类/函数只做一件事
2. **DRY (Don't Repeat Yourself)**：重复代码提取为公共函数
3. **KISS (Keep It Simple, Stupid)**：优先简单方案，避免过度设计
4. **YAGNI (You Aren't Gonna Need It)**：不实现当前不需要的功能
5. **组合优于继承**：优先用组合而非深层继承链
6. **显式优于隐式**：避免魔法行为，让代码意图清晰

### 8.4 类型注解要求

- 所有公开 API 函数必须有类型注解（参数 + 返回值）
- 内部函数鼓励添加类型注解
- 复杂类型用 `TypeAlias` 或 `Protocol` 定义
- 使用 `from __future__ import annotations` 启用延迟注解求值

来源：PEP 484 类型注解 https://peps.python.org/pep-0484/

## 规则 9：Git 工作流与团队协作规范（强制）

### 9.1 分支策略

采用 **GitHub Flow**（简化版，适合持续部署）：

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 生产就绪代码 | 禁止直接推送，需 CI 通过 + 代码审查 |
| `feature/<name>` | 新功能开发 | 从 `main` 拉出，完成后 PR 合并回 `main` |
| `fix/<name>` | Bug 修复 | 从 `main` 拉出，修复后 PR 合并回 `main` |
| `hotfix/<name>` | 紧急生产修复 | 从 `main` 拉出，优先合并 |

分支命名规范：
- `feature/s-parameter-cascade`
- `fix/euler-bend-first-point`
- `hotfix/grid-index-out-of-bounds`

来源：
- GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow
- Git Best Practices: https://devtoolhub.com/git-best-practices-branching-approvals/

### 9.2 提交规范（Conventional Commits）

提交消息格式：`<type>: <简述>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 重构（不改变功能） |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖变更 |
| `perf` | 性能优化 |
| `style` | 代码格式（不影响功能） |

规范：
- 简述不超过 50 字符，使用祈使句（"添加"而非"添加了"）
- 复杂变更用 HEREDOC 添加正文说明"为什么"
- 一个提交只做一件事，禁止混合不相关变更

来源：Conventional Commits https://www.conventionalcommits.org/

### 9.3 代码审查 (Code Review)

- 所有 PR 必须至少 1 人审查通过方可合并
- PR 描述须包含：变更摘要、变更内容、关联 Issue
- PR 应小而聚焦（建议 < 400 行变更），便于审查
- 审查关注点：正确性、可读性、性能、安全性、测试覆盖
- 禁止自我批准合并自己的 PR

### 9.4 .gitignore 规范

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

**注意**：`3dtool/wheels/*.whl` 和 `3dtool/wheels/parts/*.part_*` **必须提交到 git**，
这是沙箱重启后恢复环境的核心依赖，禁止忽略。

## 规则 10：测试规范（强制）

### 10.1 测试覆盖率标准

| 指标 | 标准 | 说明 |
|------|------|------|
| 行覆盖率 | ≥ 80% | 核心模块（pdk/router/trainer/sim）≥ 90% |
| 分支覆盖率 | ≥ 70% | 关键分支必须覆盖 |
| 测试通过率 | 100% | 禁止提交失败测试 |

### 10.2 测试分层

| 层级 | 范围 | 命名规范 | 工具 |
|------|------|----------|------|
| 单元测试 | 单个函数/类 | `test_<module>.py::Test<Class>::test_<behavior>` | pytest |
| 集成测试 | 模块间交互 | `test_integration.py::test_<flow>` | pytest |
| 端到端测试 | 完整流水线 | `test_sim_loop.py::Test<Flow>::test_<flow>` | pytest |
| 约束合规测试 | 工艺规则验证 | `test_<constraint>.py` | pytest |
| 回归测试 | 复刻模块对比 | `test_replica_<tool>.py` | pytest |

### 10.3 测试编写规范

- 每个公开函数至少有 1 个测试
- 测试函数名描述行为：`test_waveguide_phase`（非 `test_wg_1`）
- 遵循 Arrange-Act-Assert (AAA) 模式
- 使用 `pytest.fixture` 共享测试数据
- 浮点比较用 `np.testing.assert_almost_equal`，指定 `decimal` 容差
- 禁止依赖测试执行顺序，每个测试独立
- 可选依赖测试直接 import 三方工具；仅 gdsfactory/SiPANN 因上游兼容性问题保留 importorskip

来源：pytest 最佳实践 https://docs.pytest.org/en/stable/explanation/goodpractices.html

## 规则 11：文档规范（强制）

### 11.1 文档字符串 (Docstring)

所有公开模块、类、函数必须有文档字符串，遵循 Google 风格：

```python
def function_name(param1: int, param2: str) -> bool:
    """一行简述函数功能。

    可选的多行详细说明。

    Args:
        param1: 参数1的描述。
        param2: 参数2的描述。

    Returns:
        返回值的描述。

    Raises:
        ValueError: 当 param1 为负数时。
    """
```

来源：PEP 257 https://peps.python.org/pep-0257/

### 11.2 来源标注规范

所有集成的工具、复刻的算法、引用的参数必须标注来源：

```python
"""模块说明。

来源:
- 工具名: https://example.com
- 论文: Author et al., "Title", Conference Year, https://doi.org/...
"""
```

### 11.3 文档维护

- `README.md`：项目概述、安装、快速开始
- `3dtool/README.md`：三方工具总览（规则 3）
- `3dtool/wheels/README.md`：离线 wheel 包说明与使用方法（规则 5.1.1）
- `3dtool/wheels/MANIFEST.txt`：wheel 清单与 SHA256 校验和
- `3dtool/<category>/README.md`：分类工具说明（规则 3.4）
- `3dtool/pycopy/README.md`：复刻品清单（规则 4）
- `publish/README.md`：发布说明（规则 6）
- `publish/examples/README.md`：示例清单与运行方式
- `docs/`：架构文档、设计文档、优化日志
- `操作记录.md`：每次会话的操作记录（规则 19）
- 每个规则变更须同步更新本文件

## 规则 12：CI/CD 与自动化（强制）

### 12.1 CI 流水线检查项

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

### 12.2 提交前检查清单

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

## 规则 13：依赖管理规范（强制）

### 13.1 依赖分类

| 类别 | 文件 | 说明 |
|------|------|------|
| 运行依赖 | `pyproject.toml [project.dependencies]` | PDK/布局/布线/训练/仿真必需 |
| 开发依赖 | `pyproject.toml [project.optional-dependencies.dev]` | ruff/pytest/mypy 等 |
| 离线 wheel | `3dtool/wheels/` | 沙箱重启一键恢复（规则 5.1.1） |

### 13.2 依赖原则

1. **完整安装**：install.sh 统一安装全部依赖（无核心/可选之分），确保环境完整
2. **版本锁定**：`pyproject.toml` 中指定最低版本，`3dtool/wheels/` 锁定精确版本
3. **禁止商业依赖**：不依赖 Lumerical/IPKISS/Tidy3D 等商业软件
4. **安全审计**：定期运行 `pip-audit` 检查已知漏洞
5. **许可兼容**：所有依赖须与项目许可证兼容（MIT/Apache/BSD）
6. **复刻保障**：三方工具缺失时必须有 pyCopy 复刻品保障核心功能可用（规则 4）
7. **离线包同步**：新增/升级/删除依赖后必须同步更新 `3dtool/wheels/`（规则 5.5.1）

### 13.3 离线 wheel 包管理

**沙箱环境随时重启，所有 pip 安装的工具会丢失。** 项目将全部依赖打包为离线
wheel 包存放在 `3dtool/wheels/`，重启后执行 `bash 3dtool/wheels/install.sh --all`
即可在 70 秒内恢复（vs 联网下载 4 小时）。

**wheel 包组成**（详见 `3dtool/wheels/README.md`）：
- 运行依赖：numpy/scipy/networkx/torch(CPU)/gymnasium/matplotlib/pyyaml/klayout/simphony/sax
- 开发依赖：pytest/ruff/mypy/wheel/setuptools
- 大 wheel 分卷：>24MB 的 wheel 经 gzip+split 分卷为 ≤20MB 片段（绕过 GitHub 限制）

**torch CPU 版本说明**：打包的是 `torch 2.12.1+cpu`（184MB），非 GPU 版
（532MB + 2GB CUDA 依赖）。沙箱通常无 GPU，CPU 版功能完整仅速度较慢。
如需 GPU 版本，在有 GPU 的环境执行 `pip install torch`。

来源：
- pip-audit https://pypi.org/project/pip-audit/
- pip 离线安装 https://pip.pypa.io/en/stable/topics/repeatable-installs/
- split 分卷 https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html
- torch CPU 版本 https://download.pytorch.org/whl/cpu

## 规则 14：错误处理与日志规范（强制）

### 14.1 异常处理原则

- **不吞异常**：禁止空 `except:` 或 `except Exception: pass`
- **精确捕获**：捕获具体异常类型，而非基类 `Exception`
- **上下文信息**：异常消息包含足够的调试上下文
- **资源释放**：用 `with` 语句或 `try/finally` 确保资源释放
- **边界处理**：在系统边界（用户输入、外部 API）验证并转换异常

```python
# 正确
try:
    result = parse_netlist(path)
except FileNotFoundError as e:
    logger.error("网表文件不存在: %s", path)
    raise FileNotFoundError(f"网表文件不存在: {path}") from e

# 错误
try:
    result = parse_netlist(path)
except:
    pass  # 禁止：吞掉所有异常
```

来源：Google Python Style Guide 异常处理 https://google.github.io/styleguide/pyguide#s2.4-exceptions

### 14.2 日志规范

- 使用 `logging` 模块，禁止 `print()` 用于生产代码
- 日志级别：DEBUG（调试）→ INFO（关键流程）→ WARNING（异常但可处理）→ ERROR（错误）→ CRITICAL（系统级故障）
- 日志格式包含时间、级别、模块、消息
- 敏感信息（密钥/密码）禁止写入日志

```python
import logging
logger = logging.getLogger(__name__)

logger.info("开始布局优化，器件数: %d", n_devices)
logger.warning("波导间距 %.2f μm 低于推荐值 %.2f μm", spacing, min_spacing)
logger.error("DRC 检查失败: %s 共 %d 处违规", rule_name, n_violations)
```

## 规则 15：性能与可维护性规范（推荐）

### 15.1 性能基准

| 操作 | 目标耗时 | 说明 |
|------|----------|------|
| 网表解析（100 器件） | < 100ms | YAML/JSON 解析 |
| A* 布线（单连接） | < 50ms | 网格 100x100 |
| GNN 前向推理 | < 10ms | 单次状态编码 |
| PPO 训练单步 | < 100ms | 单环境步 |
| GDS 导出（100 器件） | < 500ms | 含 DRC |

### 15.2 可维护性检查清单

- [ ] 无重复代码（DRY）
- [ ] 无死代码（未使用的函数/变量/导入）
- [ ] 无魔法数字（常量提取为命名常量）
- [ ] 无深层嵌套（≤ 4 层）
- [ ] 无超长函数（≤ 40 行）
- [ ] 无超长文件（≤ 500 行）
- [ ] 公开 API 有文档字符串
- [ ] 复杂逻辑有注释说明
- [ ] 测试覆盖率达标

## 规则 16：发现 Bug 必须修复纪律（强制）

在执行任何任务的过程中，如果发现了新的 Bug（无论是代码缺陷、逻辑错误、边界条件遗漏，
还是测试暴露的问题），**必须一同解决，禁止带 Bug 提交代码**。

### 16.1 强制要求

1. **发现即记录**：发现 Bug 时，立即在代码注释或任务文档中记录：
   - Bug 描述：什么情况下触发，预期行为 vs 实际行为
   - 根因分析：为什么会产生这个 Bug
   - 修复方案：如何修复，修复了哪些文件
2. **必须修复**：在当前任务提交前必须修复该 Bug，不得留到"以后处理"
3. **必须测试**：修复后必须编写或补充对应的测试用例，验证修复有效
4. **提交备注**：在 commit message 中注明修复了哪些 Bug

### 16.2 Bug 记录格式

在 commit message 或代码注释中记录 Bug 修复：

```
fix: 修复 <模块> 中 <Bug 描述>

Bug: <简述>
根因: <原因分析>
修复: <修复方案>
测试: <新增/修改的测试>
```

### 16.3 禁止行为

- **禁止忽略**：发现 Bug 后不得继续提交而不修复
- **禁止注释掉**：不得用注释掉代码的方式"绕过"Bug
- **禁止 TODO 推迟**：不得用 `# TODO: 修复这个 Bug` 推迟到未来
- **禁止降低标准**：不得为了通过测试而放宽断言容差来"掩盖"Bug

### 16.4 例外情况

仅以下情况允许先提交后修复（但必须在 commit message 中明确标注）：
- Bug 修复需要大量重构，超出当前任务范围 → 创建独立 Issue 跟踪
- Bug 涉及外部依赖升级，无法在当前环境修复 → 记录并创建 Issue
- Bug 为已有遗留问题，与当前任务无关 → 记录但不阻断当前提交

即使例外情况，也必须在 commit message 中写明：
```
注: 发现 <模块> 存在 <Bug 描述>，因 <原因> 暂未修复，已记录 Issue #XXX
```

## 规则 17：开发完成即检门禁纪律（强制）

代码开发完成后，**必须立即**执行代码质量门禁检查，且必须达到 **0 警告 0 错误**方可提交。

### 17.1 强制要求

1. **开发完成即检**：任何代码开发任务（含新功能、Bug 修复、重构、配置变更）完成后，
   必须立即运行质量门禁，禁止"先提交后补检"
2. **0 警告 0 错误硬性标准**：门禁结果必须为 0 警告 0 错误，任一警告或错误均禁止提交
3. **全量检查**：必须对 `src/polaris/` 目录执行全量检查，不得仅检查改动文件
4. **整改优先**：发现警告/错误后必须立即整改，禁止跳过、注释、降级或推迟

### 17.2 检查命令（开发完成后必须执行）

```bash
# 1. 质量门禁（必须 0 警告 0 错误）
python scripts/code_quality_gate.py

# 2. Ruff lint（必须 All checks passed）
ruff check src/ tests/ 3dtool/

# 3. Ruff 格式检查（必须 already formatted）
ruff format --check src/ tests/ 3dtool/

# 4. 测试冒烟（必须全部通过）
python -m pytest tests/ -q --tb=short --continue-on-collection-errors
```

### 17.3 门禁未通过的处理流程

当门禁检查发现警告或错误时，必须执行以下流程：

1. **停止提交**：立即停止 `git commit`/`git push` 操作
2. **分析原因**：逐条分析每个警告/错误的根因
3. **立即整改**：按规则 7.2 的重构流程整改，不得推迟
4. **重新检查**：整改后重新运行全部检查命令，确认 0 警告 0 错误
5. **记录整改**：在 commit message 中注明整改内容

### 17.4 禁止行为

- **禁止跳过门禁**：不得以"临时提交"、"紧急修复"为由跳过门禁检查
- **禁止 `--no-verify`**：不得使用 `git commit --no-verify` 绕过 pre-commit hook
- **禁止降级标准**：不得修改门禁脚本放宽阈值来"通过"检查
- **禁止选择性检查**：不得仅检查改动文件而忽略全量检查
- **禁止带病提交**：不得在门禁未通过的情况下提交代码

### 17.5 例外情况

仅以下情况允许例外（但必须在 commit message 中明确标注并事后补检）：
- 紧急生产故障修复（hotfix），需在 30 分钟内补检
- 文档/注释-only 变更（不涉及代码逻辑），需在下次代码提交时补检

即使例外情况，也必须满足 ruff check 和 pytest 通过。

来源：
- 规则 7 质量门禁脚本: `scripts/code_quality_gate.py`
- 规则 7.5 Pre-commit Hook: `scripts/pre-commit`
- Google Python Style Guide: https://google.github.io/styleguide/pyguide

## 规则 18：学术诚信与引用规范（强制）

本项目为科研型工程，所有算法、参数、数据、方案必须遵守学术诚信。

### 18.1 强制要求

1. **禁止抄袭**：禁止复制他人代码而不标注来源；禁止将他人算法据为己有
2. **来源标注**：所有引用的算法、参数、模型、数据集必须在代码注释或文档中标注：
   - 作者/机构
   - 论文/仓库标题
   - 发表年份
   - URL 或 DOI
3. **复刻须声明**：按规则 4 复刻的开源工具，须在文件头声明原仓库、协议、版本
4. **参数须溯源**：所有物理参数（折射率、损耗、弯曲半径等）须标注来源文献或 PDK
5. **禁止假数据**：禁止编造未经文献或实验验证的参数与实验结果
6. **引用须准确**：引用的论文须实际阅读并理解，禁止仅凭标题臆断内容

### 18.2 引用格式

代码中引用算法或参数时，使用以下格式：

```python
"""模块说明。

来源:
- 论文: Author et al., "Title", Conference/Journal Year, https://doi.org/...
- 仓库: https://github.com/org/repo (协议: MIT)
- 参数: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""
```

### 18.3 禁止行为

- **禁止洗稿**：不得通过变量重命名、格式调整等方式掩盖抄袭
- **禁止选择性引用**：不得只引用支持自己结论的部分而忽略矛盾证据
- **禁止自引堆砌**：不得为提高引用数而过度自引
- **禁止数据造假**：不得伪造实验结果、性能数据、对比基准

### 18.4 检索记录要求

每次方案检索（规则 1.1）须在对应模块或 PR 描述中记录：
- 检索关键词
- 检索到的论文列表（标题、作者、年份、URL）
- 最终采用的方案及理由
- 未采用方案及原因

来源：
- ACM Code of Ethics: https://www.acm.org/code-of-ethics
- IEEE Code of Ethics: https://www.ieee.org/about/corporate/governance/p7-8.html
- 学术诚信指南: https://www.integrity.org/academic-integrity

## 规则 19：操作记录维护纪律（强制）

每次会话/任务执行都必须在 `操作记录.md` 中记录所有修改与聊天总结，保证可追溯。

### 19.1 强制要求

1. **每次会话必记录**：每次与用户的交互会话结束后，必须在 `操作记录.md` 追加一条记录
2. **每项修改必记录**：代码修改、文件新增/删除、配置变更、依赖安装、Bug 修复、重构等每一项操作都要记录
3. **聊天总结必记录**：用户的核心诉求、关键决策、方案讨论结论、未解决问题都要记录
4. **时间戳必记录**：每条记录须包含日期时间（YYYY-MM-DD HH:MM 格式）
5. **提交关联**：每条记录须关联对应的 git commit hash（若有提交）

### 19.2 记录格式

`操作记录.md` 每条记录使用以下格式：

```markdown
## [YYYY-MM-DD HH:MM] 会话主题简述

### 用户诉求
- 用户原话摘要

### 聊天总结
- 关键讨论点
- 方案决策
- 未解决问题

### 修改清单
| 文件 | 操作 | 说明 |
|------|------|------|
| path/to/file.py | 修改 | 修复 XXX |
| path/to/new.py | 新增 | 实现 YYY |

### 验证结果
- 质量门禁: 0 警告 0 错误 / N 警告
- 测试: N passed / N failed
- Ruff: passed / failed

### Git 提交
- commit: <hash>
- 分支: <branch>
```

### 19.3 记录内容要求

每条记录必须包含：
- **用户诉求**：用户本次会话的核心目标（原话摘要）
- **聊天总结**：讨论过程、方案选择、关键决策、未解决问题
- **修改清单**：表格列出每个文件的操作类型（修改/新增/删除）和说明
- **验证结果**：质量门禁、测试、Ruff 的结果
- **Git 提交**：commit hash 和分支名（若有提交）

### 19.4 禁止行为

- **禁止跳过记录**：不得以"临时修改"、"小改动"为由跳过操作记录
- **禁止事后补记**：应在会话结束前即时记录，不得堆积多天后补
- **禁止模糊记录**：不得使用"修改了若干文件"等模糊描述，须精确到文件路径
- **禁止遗漏失败**：测试失败、门禁失败也必须记录，不得只记成功

### 19.5 文件位置

- 操作记录文件固定路径：`操作记录.md`（项目根目录）
- 规则文件路径：`.trae/rules/project_rules.md`（本文件）
- 优化日志路径：`docs/optimization_log.md`（技术优化专项记录）
- 三方工具总览：`3dtool/README.md`（规则 3）
- 复刻品清单：`3dtool/pycopy/README.md`（规则 4）

来源：
- Git 提交最佳实践: https://www.conventionalcommits.org/
- 变更日志规范: https://keepachangelog.com/
- 可追溯性要求: ISO/IEC 25010 维护性

## 规则 20：3dtool 大文件管理规范（强制）

### 20.1 单文件大小限制

- `3dtool/` 目录下**单个文件大小上限为 100 MB**（含 wheel 包、分卷片段、复刻品源码、文档等所有文件）
- 超过 100 MB 的文件必须按以下方式处理：
  1. **wheel 包**：使用 `gzip + split` 分卷为 ≤20 MB 片段存放到 `3dtool/wheels/parts/`（规则 5.1.1）
  2. **数据文件**：拆分为多个小文件，或使用 Git LFS 管理
  3. **模型 checkpoint**：存放至 `checkpoints/` 并加入 `.gitignore`，不提交到 git
  4. **二进制资源**：压缩后仍超 100 MB 的，必须使用外部存储（OSS/S3/HuggingFace Hub）并在 README 标注下载方式

### 20.2 检查命令

```bash
# 检查 3dtool/ 下超过 100MB 的文件
find 3dtool/ -type f -size +100M -exec ls -lh {} \;

# 检查全部超 100MB 文件（不含 .git/）
find . -path ./.git -prune -o -type f -size +100M -print
```

### 20.3 处理流程

1. **新增文件前预估**：下载/生成大文件前先预估大小，超 100 MB 直接走分卷/外部存储
2. **定期巡检**：CI 中执行检查命令，发现超限文件立即告警
3. **历史文件整改**：已存在的超限文件须在下一个版本前完成整改
4. **例外白名单**：仅 `3dtool/wheels/parts/` 下的分卷片段允许 ≤20 MB（更严格），无任何文件可超 100 MB

### 20.4 禁止行为

- ❌ 禁止提交 >100 MB 的文件到 git（GitHub 会拒绝，且克隆/拉取极慢）
- ❌ 禁止用 `git add -A` 一次性添加大量大文件
- ❌ 禁止将模型 checkpoint（`.pt`/`.pth`/`.json` >100 MB）提交到 git
- ❌ 禁止在 `3dtool/` 下存放视频/数据集等非工具类大文件

来源：
- GitHub 文件大小限制: https://docs.github.com/en/repositories/working-with-files/managing-large-files
- Git LFS: https://git-lfs.com/
- split 分卷: https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html

## 规则 21：pyCopy 复刻品版本管理规范（强制）

### 21.1 版本号规则

所有 `3dtool/pycopy/pyCopy<Xxx>/` 复刻品遵循 SemVer 语义化版本：

| 版本阶段 | 含义 | 验收标准 |
|---------|------|---------|
| `v0.x.x` | 开发中 | API 不稳定，禁止用于生产 |
| `v1.0.0` | 100% 复刻完成 | 与原工具行为对比测试 100% 通过（浮点 1e-9 容差），覆盖项目使用的全部功能子集 |
| `v1.0.x` | Bug 修复 | 修复复刻缺陷，不改变 API |
| `v1.x.0` | 功能扩展 | 新增原工具没有但项目需要的功能（须标注"扩展"） |
| `v2.0.x` | 能力优化 | 在 100% 复刻基础上优化性能/精度/易用性，每个能力提升递增 x |
| `v3.0.x` | 重大重写 | 架构级重写（如 NumPy → C 扩展） |

### 21.2 版本文件要求

每个 `pyCopy<Xxx>/` 目录必须包含：

1. `__init__.py`：重导出公开 API，顶部声明 `__version__`
2. `VERSION.md`：版本历史记录，格式如下
3. `README.md`：复刻说明（原工具/协议/复刻位置/对比测试结果）

`VERSION.md` 格式：
```markdown
# pyCopy<Xxx> 版本历史

## v1.0.0 (YYYY-MM-DD) — 100% 复刻完成
- 复刻内容: Tensor/autograd/Linear/Adam/...
- 对比测试: tests/test_replica_<tool>.py 全部通过（N 个用例）
- 行为一致性: 浮点容差 1e-9
- 来源: https://github.com/original/repo (commit abc123, 协议 MIT)

## v2.0.1 (YYYY-MM-DD) — 性能优化
- 优化点: 用 NumPy 向量化替代 for 循环，前向推理提速 3x
- 测试: 对比测试仍 100% 通过
- 基准: 100 样本前向耗时 50ms → 17ms

## v2.0.2 (YYYY-MM-DD) — 精度提升
- 优化点: LayerNorm 数值稳定性（添加 eps 滑动平均）
- 测试: 对比测试容差从 1e-9 收紧到 1e-12
```

### 21.3 v2.0.x 能力优化方向

每个复刻品在 v1.0.0 完成后，按以下方向递增 v2.0.x：

| 复刻品 | v2.0.x 优化方向 |
|--------|----------------|
| pyCopyTorch | 自动混合精度/算子融合/Conv2d im2col 优化/分布式 |
| pyCopySAX | 子网络增长算法并行化/稀疏矩阵/S 参数缓存 |
| pyCopySiPANN | 矩形波导解析解加速/耦合模理论精度提升/Monte Carlo 容差分析 |
| pyCopyKLayout | DRC 规则并行检查/增量 DRC/几何算法空间索引（R-tree） |
| pyCopyMEEP | FDTD Yee 网格/UPML 吸收边界/多波长扫描（预留） |
| pyCopyFemwell | FEM 网格生成/模式求解器（预留） |
| pyCopyMeow | 模式重叠积分/波导截面求解（预留） |

### 21.4 验收流程

新增/升级复刻品必须执行：

1. **100% 行为对比**：`pytest tests/test_replica_<tool>.py -v` 全部通过
2. **门禁检查**：`python scripts/code_quality_gate.py` 0 警告 0 错误
3. **来源标注**：`__init__.py` 头部声明原仓库 URL/协议/commit
4. **版本登记**：更新 `VERSION.md` 和 `3dtool/pycopy/README.md` 清单
5. **操作记录**：在 `操作记录.md` 记录本次复刻/升级

### 21.5 禁止行为

- ❌ 禁止跳过 v1.0.0 直接做 v2.0.x（必须先 100% 复刻验证）
- ❌ 禁止 v2.0.x 改变 v1.0.0 的公开 API（破坏性变更须升 v3.0.0）
- ❌ 禁止复刻品与原工具行为不一致（浮点容差除外）
- ❌ 禁止不写 VERSION.md 就发布版本
- ❌ 禁止用"复刻"名义抄袭而不标注来源

来源：
- SemVer 语义化版本: https://semver.org/
- PyTorch 协议: https://pytorch.org/ (BSD-3-Clause)
- SAX 协议: https://flaport.github.io/sax/ (Apache-2.0)
- SiPANN 协议: https://sipann.readthedocs.io/ (MIT)

## 规则 22：商业交付与差距分析纪律（强制）

### 22.1 强制要求

1. **定期差距分析**：每个里程碑（v1.0/v2.0/v3.0）必须执行一次商业工具差距分析，产出 `docs/commercial_gap_analysis.md`
2. **对标最强商业工具**：必须对比 Lumerical/IPKISS/Tidy3D/Cadence Innovus/Synopsys ICC2 等行业标杆
3. **差距分级**：按 P0（阻断商业交付）/P1（影响竞争力）/P2（长期演进）分级
4. **解决路线图**：每个差距须给出具体解决办法和版本规划
5. **来源真实**：所有商业工具能力数据须来自官方文档/权威评测，禁止编造

### 22.2 MVP 交付标准

MVP（v1.0）必须满足：
- 端到端流水线跑通：网表 → 布局 → 布线 → 仿真 → GDS → DRC → 报告
- 100 次迭代稳定性 ≥ 95%（`scripts/mvp_100_iterations.py`）
- 至少 5 个演示电路全部成功
- 质量门禁 0 警告 0 错误
- 测试通过率 100%

### 22.3 商业级交付标准

商业级（v2.0）必须满足：
- 支持 ≥ 1000 器件规模布局布线
- PDK 覆盖 ≥ 8 个工艺平台
- DRC/LVS 工业链路完整（KLayout 集成）
- 训练良好的模型（PPO 收敛 + BC 预训练 + GNN 状态编码）
- 性能基准达标（规则 15.1）
- 与商业工具差距分析报告显示差距 ≤ 2.0 分（10 分制）

来源：
- 工业级 EDA 标准: https://www.cadence.com/ (Innovus)
- 光子 EDA 评测: https://www.luceda.com/ (IPKISS)

## 参考来源汇总

| 标准 | 来源 URL |
|------|----------|
| Python src layout | https://packaging.python.org/en/latest/discussions/src-layout/ |
| PEP 8 风格指南 | https://peps.python.org/pep-0008/ |
| PEP 257 文档字符串 | https://peps.python.org/pep-0257/ |
| PEP 484 类型注解 | https://peps.python.org/pep-0484/ |
| Google Python Style Guide | https://google.github.io/styleguide/pyguide |
| Google Style 中文版 | https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/ |
| Conventional Commits | https://www.conventionalcommits.org/ |
| McCabe 圈复杂度 (1976) | https://ieeexplore.ieee.org/document/1702388 |
| ISO/IEC 25010 软件质量 | https://iso25000.com/index.php/en/iso-25000-standards/iso-25010 |
| Radon 代码度量工具 | https://radon.readthedocs.io/ |
| Ruff Linter/Formatter | https://docs.astral.sh/ruff/ |
| pytest 最佳实践 | https://docs.pytest.org/en/stable/explanation/goodpractices.html |
| GitHub Flow | https://docs.github.com/en/get-started/quickstart/github-flow |
| Git 分支最佳实践 | https://devtoolhub.com/git-best-practices-branching-approvals/ |
| Python Linting SOP | https://alchemiststudios.ai/articles/python-linting-sop.html |
| Sourcegraph 复杂度指南 | https://sourcegraph.com/blog/cyclomatic-complexity-what-it-is-and-how-to-reduce-it |
| pip 离线安装 | https://pip.pypa.io/en/stable/topics/repeatable-installs/ |
| split 分卷工具 | https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html |
| torch CPU 版本 | https://download.pytorch.org/whl/cpu |
| pip-audit 安全审计 | https://pypi.org/project/pip-audit/ |
| PyTorch | https://pytorch.org/ |
| KLayout | https://www.klayout.de/ |
| GDSFactory | https://gdsfactory.github.io/gdsfactory/ |
| SAX | https://flaport.github.io/sax/ |
| Simphony | https://simphonyphotonics.readthedocs.io/ |
| SiPANN | https://sipann.readthedocs.io/ |
| MEEP | https://meep.readthedocs.io/ |
| Gymnasium | https://gymnasium.farama.org/ |
| NetworkX | https://networkx.org/ |
