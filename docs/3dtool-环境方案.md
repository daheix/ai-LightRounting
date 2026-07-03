# 3dtool 环境方案 — 统一管理 + 按需拉取 + 三层离线包

> R01 方案检索 · R02 学术诚信 · R03 禁止 fall-back · R04 不参与 GPU
> 创建: 2026-07-03 · 适用: PoLaRIS v5.0 + 3dtool 子仓库

## 一、3dtool 统一管理架构

3dtool 子仓库提供两类资源，PoLaRIS 统一管理：

```
3dtool/（git submodule, sparse-checkout）
├── wheels/              ← Layer 1: 47 个 cp314 离线 wheel（122M，Python 依赖）
├── scripts/             ← 3dtool 工具脚本
├── tools/               ← AppImage 打包脚本
└── 3dtool/appimage-parts/  ← 2.0G AppImage 分片（sparse 排除，按需拉取）
    ├── manifest.json        ← 组件清单（md5+分片信息）
    ├── AppRun.tar.gz        ← 启动器（2.6K）
    ├── bin.tar.gz           ← 30 个工具（55M: kicad/openEMS/ElmerSolver/ngspice）
    ├── lib.tar.gz.part_*    ← .so 共享库（354M, 4 分片）
    ├── python-runtime.tar.gz ← Python 运行时（103M，跳过：沙箱有 pyenv）
    ├── python-site-packages  ← Python 包（735M，跳过：有 wheels）
    ├── kicad-*.tar.gz        ← KiCad 数据（可选）
    └── jre.tar.gz.part_*     ← Java 运行时（可选）
```

### 两类资源对接方式

| 资源类型 | 来源 | 对接方式 | 脚本 |
|---------|------|---------|------|
| Python wheel | 3dtool/wheels/ | pip install --no-index --find-links | all_init_inone.sh 步骤4 |
| AppImage 工具 | 3dtool/appimage-parts/ | git cat-file 按需拉取 + tar 解包 | restore_3dtool_selective.sh |

## 二、*创新*: 按需拉取 + 选择性解包

### 问题

3dtool AppImage 完整 2.0G，但沙箱磁盘只有 40G（已用 39G）。全量拉取磁盘爆。

### 方案

1. sparse-checkout 排除 `appimage-parts/`（工作区不占 2.0G）
2. 用 `git cat-file -p HEAD:3dtool/appimage-parts/<file>` 按需拉取单个 blob
3. 按 manifest.json 选择性解包（跳过不需要的组件）

### 底层理论

git partial clone 的 promisor remote 支持 `git cat-file` 按需拉取任意 blob，sparse-checkout 排除目录不影响 git cat-file 访问该路径的 blob。
参考: [git partial clone 官方文档](https://git-scm.com/docs/partial-clone)

### 组件分层（体积最小化）

| 组件 | 压缩大小 | 解压大小 | PoLaRIS 需要 | 决策 |
|------|---------|---------|-------------|------|
| AppRun | 2.6K | 8K | ✓ 启动器 | 拉取 |
| bin | 55M | 55M | ✓ 30 个工具 | 拉取 |
| lib | 354M | 1.1G | ✓ .so 依赖 | 拉取 |
| python-runtime | 103M | - | ✗ 沙箱有 pyenv | 跳过 |
| python-site-packages | 735M | - | ✗ 有 wheels | 跳过 |
| kicad-3dmodels | 458M | - | 可选 | --with-3dmodels |
| kicad-symbols | 23M | - | 可选 | --with-kicad |
| kicad-footprints | 15M | - | 可选 | --with-kicad |
| kicad-demos | 96M | - | ✗ 示例 | 跳过 |
| kicad-misc | 23M | - | 可选 | --with-kicad |
| jre | 222M | - | 可选 | --with-jre |

### 体积对比

| 配置 | 拉取大小 | 解压大小 | 命令 |
|------|---------|---------|------|
| 完整 | 2.0G | 2.0G+ | `--all` |
| 核心（默认） | 410M | 1.1G | （默认） |
| +KiCad 数据 | 471M | - | `--with-kicad` |
| +3D 模型 | 929M | - | `--with-3dmodels` |
| +JRE | 1151M | - | `--with-jre` |

## 三、3dtool AppImage 工具列表（30 个）

| 工具 | 用途 | PoLaRIS 路标 |
|------|------|-------------|
| kicad | KiCad PCB 设计 | R3 KLayout/gdsfactory |
| kicad-cli | KiCad 命令行 | R3 |
| eeschema | KiCad 原理图 | R3 |
| pcbnew | KiCad PCB 编辑 | R3 |
| gerbview | Gerber 查看 | R3 |
| pcb_calculator | PCB 计算器 | R3 |
| bitmap2component | 位图转封装 | R3 |
| ngspice | SPICE 电路仿真 | R5 Lumerical |
| openEMS | FDTD 电磁仿真 | R4 OptoDesigner |
| nf2ff | 近场转远场 | R4 |
| sar_calc | SAR 计算 | R4 |
| ElmerSolver | 有限元多物理场 | R4 |
| ElmerSolver_mpi | Elmer MPI 并行 | R4 |
| ElmerGrid | Elmer 网格 | R4 |
| python3.11 | Python 3.11 运行时 | 工具内嵌 |

## 四、一键配置环境流程（all_init_inone.sh）

```
[1/7]   检查 main 分支（R11）
[2/7]   source env.sh（JAX CPU 强制 R04 + 3dtool-appimage/bin 加入 PATH）
[3/7]   恢复 3dtool 子仓库（sparse: wheels scripts tools）
[3.5/7] 按需拉取 3dtool AppImage 工具（git cat-file 按需拉 410M 核心）
        *创新*: sparse 排除 2.0G，git cat-file 按需拉取
[4/7]   双离线源安装 wheels（3dtool/wheels + polaris_wheels）
[5/7]   editable 安装 PoLaRIS 33 模块
[6/7]   四重验证（依赖+工具+模块+JAX CPU）
[7/7]   启动守护进程（auto_commit V8 + keepalive）
```

## 五、使用方法

```bash
bash all_init_inone.sh              # 完整初始化（默认）
bash all_init_inone.sh --offline    # 纯离线模式
bash all_init_inone.sh -v           # 详细输出

# 单独恢复 3dtool 工具
bash scripts/restore_3dtool_selective.sh                    # 核心组件（410M）
bash scripts/restore_3dtool_selective.sh --with-kicad       # +KiCad 数据
bash scripts/restore_3dtool_selective.sh --with-3dmodels    # +3D 模型
bash scripts/restore_3dtool_selective.sh --all              # 全部（2.0G）
```

## 六、文献来源（R02 学术诚信）

1. [git partial clone 官方文档](https://git-scm.com/docs/partial-clone) — git cat-file 按需拉取 blob
2. [git sparse-checkout 官方文档](https://git-scm.com/docs/git-sparse-checkout/) — 目录级稀疏检出
3. [pip 官方: Repeatable Installs (wheelhouse)](https://pip.pypa.io/en/stable/topics/repeatable-installs/) — 离线 wheel 安装
4. [CSDN: pip 离线安装包的方法](https://blog.csdn.net/jjj_web/article/details/150113184) — 中文离线安装指南
5. [InfoWorld: Air-gapped Python](http://www.itinfoworld.org/airgapped-python-setting-up-python-without-a-network.html) — 气隙环境配置

## 七、自测结果（R13）

```
3dtool 工具: kicad-cli ✓ ngspice ✓ openEMS ✓ ElmerSolver ✓
3dtool 工具数: 30 个
PoLaRIS 模块: 33/33
离线 wheel: 47
JAX 平台: cpu（R04 合规）
磁盘剩余: 1.1G
```

