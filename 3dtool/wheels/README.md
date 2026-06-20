# wheels/ — 离线依赖 Wheel 包

存放 PoLaRIS 全部第三方依赖的 wheel 包，支持**沙箱/新环境一键离线安装**，
无需联网下载，秒级恢复完整开发环境。

## 背景

沙箱环境随时重启，pip 安装的第三方工具会全部丢失。重新联网下载安装需 4+ 小时
（torch 单个 532MB）。本目录将所有依赖打包为离线 wheel，重启后执行一个脚本
即可在 70 秒内恢复全部环境。

## 目录结构

```
3dtool/wheels/
├── install.sh              # 一键离线安装脚本（核心入口）
├── MANIFEST.txt            # wheel 清单与 SHA256 校验和
├── *.whl                   # 小 wheel 文件（<24MB，直接存放，83 个）
└── parts/                  # 大 wheel 分卷片段（每个 ≤20MB，18 个）
    ├── torch-*.whl.gz.part_aa    # torch 184MB → 9 个分片
    ├── jaxlib-*.whl.gz.part_*    # jaxlib 82MB → 5 个分片
    ├── scipy-*.whl.gz.part_*     # scipy 34MB → 2 个分片
    └── klayout-*.whl.gz.part_*   # klayout 27MB → 2 个分片
```

## 为什么分卷？

GitHub 限制单个文件不超过 24MB。torch CPU 版 184MB、jaxlib 82MB 等大 wheel
无法直接提交。解决方案：
1. 用 `gzip` 压缩 wheel 文件
2. 用 `split -b 20M` 分卷为多个 ≤20MB 片段
3. `install.sh` 安装时自动 `cat` 合并 + `gunzip` 还原

## 使用方法

### 沙箱重启后一键恢复

```bash
# 在项目根目录执行
bash 3dtool/wheels/install.sh --all
```

约 70 秒完成全部安装（vs 联网下载 4 小时）。

### 仅安装核心依赖

```bash
bash 3dtool/wheels/install.sh --core
# 安装: numpy scipy networkx torch gymnasium matplotlib pyyaml
```

### 仅安装开发依赖

```bash
bash 3dtool/wheels/install.sh --dev
# 安装: pytest ruff mypy
```

### 仅检查环境（不安装）

```bash
bash 3dtool/wheels/install.sh --check
# 输出各依赖安装状态与版本
```

## 依赖清单

### 核心依赖（必装，7 个）

| 包 | 版本 | 用途 | 大小 |
|----|------|------|------|
| numpy | 2.4.6 | 数值计算核心 | 16MB |
| scipy | 1.17.1 | 优化求解 | 34MB（分卷） |
| networkx | 3.6.1 | 图算法 | 2MB |
| torch | 2.12.1+cpu | GNN/PPO 神经网络 | 184MB（分卷） |
| gymnasium | 1.3.0 | RL 环境 | 1MB |
| matplotlib | 3.11.0 | 版图渲染 | 8MB |
| pyyaml | 6.0.3 | 网表序列化 | 1MB |

### 仿真依赖（2 个）

| 包 | 版本 | 用途 | 大小 |
|----|------|------|------|
| klayout | 0.30.9 | GDS 导出 + DRC | 27MB（分卷） |
| simphony | 0.6.0 | S 参数仿真 | 1MB |

### 重型仿真依赖（含完整依赖链，1 个）

| 包 | 版本 | 用途 | 大小 |
|----|------|------|------|
| sax | — | 频率域仿真（含 jax/jaxlib/optax） | 82MB（jaxlib 分卷） |

### 开发依赖（3 个）

| 包 | 版本 | 用途 | 大小 |
|----|------|------|------|
| pytest | 9.1.0 | 测试框架 | 1MB |
| ruff | 0.15.18 | Lint + Format | 12MB |
| mypy | 2.1.0 | 类型检查 | 12MB |

## 重要说明

### torch CPU 版本

本目录打包的是 `torch 2.12.1+cpu`（CPU 版本，184MB），而非 GPU 版本（532MB + 2GB CUDA 依赖）。
原因：
1. 沙箱环境通常无 GPU
2. CPU 版本体积小，分卷后可提交 GitHub
3. 训练与推理功能完整（仅速度较慢）

如需 GPU 版本，请在有 GPU 的环境执行：
```bash
pip install torch  # 自动安装 GPU 版本
```

### sax 完整依赖链

sax 依赖 jax/jaxlib/optax/flax 等（jaxlib 82MB）。本目录已打包完整依赖链，
安装 sax 时会自动安装全部依赖。项目代码中 sax import 失败时回退到
`pyCopySAX` 复刻品（规则 4）。

### 平台限制

本目录 wheel 包仅适用于 **Linux x86_64 + Python 3.14** 环境。
其他平台（macOS/Windows）或其他 Python 版本需重新下载：
```bash
# 重新生成 wheel 包（需联网）
pip download --dest 3dtool/wheels/ numpy scipy networkx torch gymnasium matplotlib pyyaml
pip download --dest 3dtool/wheels/ klayout simphony sax
pip download --dest 3dtool/wheels/ pytest ruff mypy wheel setuptools
```

## 校验完整性

```bash
# 校验所有 wheel 与分片的 SHA256
cd 3dtool/wheels
sha256sum -c MANIFEST.txt
```

## 来源

- pip 离线安装: https://pip.pypa.io/en/stable/topics/repeatable-installs/
- split 分卷: https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html
- torch CPU 版本: https://download.pytorch.org/whl/cpu
