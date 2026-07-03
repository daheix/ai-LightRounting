# 3dtool 环境方案 — 三层离线包体系

> R01 方案检索 · R02 学术诚信 · R03 禁止 fall-back · R04 不参与 GPU
> 创建: 2026-07-03 · 适用: PoLaRIS v5.0 + 3dtool 子仓库

## 一、问题背景

沙箱环境特性：
1. 每次重启后 site-packages 全部丢失（Python 依赖需重装）
2. 网络不稳定（在线安装可能失败）
3. 3dtool 仓库含 2.0G AppImage 分片（全量 clone 磁盘爆）
4. git submodule 标准命令会全量拉取（需 sparse-checkout 跳过大文件）

## 二、方案设计（三层离线包体系）

### Layer 1: 3dtool/wheels/ — 通用 Python wheel（3dtool 维护）

- 数量: 47 个 cp314 wheel（Python 3.14 专用）
- 大小: 122M
- 内容: numpy/scipy/matplotlib/pydantic/pytest/ruff/mypy/openpyxl/reportlab/rtree/shapely 等
- 维护: daheix/3dtool 仓库（子仓库，sparse-checkout 拉取）

### Layer 2: polaris_wheels/ — PoLaRIS 特有 wheel（主仓库维护）

- 数量: 43 个 cp314 wheel
- 大小: 218M
- 内容: jax/jaxlib/sax/klayout/gymnasium/jaxtyping/jaxellip/klujax 及其全部依赖
- 维护: PoLaRIS 主仓库（git 跟踪）
- 生成命令: `pip download --dest polaris_wheels --only-binary=:all: jax[cpu] jaxlib[cpu] sax klayout gymnasium`

### Layer 3: requirements-pinned.txt — 版本锁定

- 数量: 69 个包（pip freeze 生成 + 清洗）
- 作用: 锁定精确版本，确保可重复安装
- 参考: [pip 官方 Repeatable Installs](https://pip.pypa.io/en/stable/topics/repeatable-installs/)

### 合计覆盖

| 离线源 | wheel 数 | 大小 | 覆盖范围 |
|--------|---------|------|---------|
| 3dtool/wheels/ | 47 | 122M | 通用 Python 包 |
| polaris_wheels/ | 43 | 218M | PoLaRIS 特有（jax/sax/klayout/gymnasium） |
| **合计** | **90** | **340M** | **PoLaRIS 全部依赖** |

## 三、一键配置环境流程（all_init_inone.sh）

```
[1/7] 检查 main 分支（R11）
[2/7] source env.sh（JAX CPU 强制 R04）
[3/7] 恢复 3dtool 子仓库（sparse: wheels scripts tools，跳过 2.0G 分片）
[4/7] 双离线源安装 wheels（3dtool/wheels + polaris_wheels + requirements-pinned.txt）
      ├── 4a: 升级 pip/setuptools/wheel
      ├── 4b: 纯离线安装（--no-index --find-links 双源 -r requirements-pinned.txt）
      └── 4c: 在线补装（兜底，--offline 模式跳过）
[5/7] editable 安装 PoLaRIS 33 模块
[6/7] 四重验证（依赖+工具+模块+JAX CPU）
[7/7] 启动守护进程（auto_commit V8 + keepalive）
```

### 使用方法

```bash
bash all_init_inone.sh              # 完整初始化（默认离线优先+在线兜底）
bash all_init_inone.sh --offline    # 纯离线模式（网络不好时用，不在线补装）
bash all_init_inone.sh -v           # 详细输出
bash all_init_inone.sh --no-daemon  # 不启动守护进程
bash all_init_inone.sh --force      # 强制重新安装
```

## 四、网络不好时的保证

### 场景1: 完全断网

```bash
bash all_init_inone.sh --offline --no-daemon
```

- 3dtool 子仓库: 从 git submodule 恢复（需 git 协议，不走 PyPI）
- Python 依赖: 纯离线安装（90 个 wheel，340M）
- PoLaRIS 模块: editable 安装（本地代码）
- **无需任何 PyPI 网络**

### 场景2: 网络不稳定

```bash
bash all_init_inone.sh  # 默认模式
```

- 优先离线安装（90 个 wheel）
- 在线补装失败不致命（离线源已覆盖）
- 不会因网络问题中断

### 场景3: 首次配置（有网络）

```bash
bash all_init_inone.sh  # 离线+在线补装
```

- 离线安装全部 90 个 wheel
- 在线补装确保最新（jax[cpu]/sax/klayout/gymnasium）

## 五、3dtool 子仓库对接

### 5.1 子仓库管理（标准 git submodule）

```bash
# .gitmodules（公开 URL，可提交）
[submodule "3dtool"]
    path = 3dtool
    url = https://github.com/daheix/3dtool.git
    branch = main
    sparse = true

# .git/config（带 token，本地不提交）
git config submodule.3dtool.url "https://x-access-token:TOKEN@github.com/daheix/3dtool"
```

### 5.2 sparse-checkout（跳过 2.0G 分片）

```bash
git sparse-checkout init --cone
git sparse-checkout set wheels scripts tools
# 跳过: 3dtool/appimage-parts/（2.0G AppImage 分片）
```

### 5.3 3dtool 各目录用途

| 目录 | 用途 | PoLaRIS 是否使用 |
|------|------|-----------------|
| `wheels/` | 47 个 cp314 离线 wheel | ✓ 离线安装源 |
| `scripts/` | 3dtool 工具脚本 | ✓ PATH 加入 |
| `tools/` | AppImage 打包脚本 | 参考 |
| `3dtool/appimage-parts/` | 2.0G AppImage 分片 | ✗ 跳过（sparse 排除） |
| `src/` | 3dtool 源码 | ✗ 不使用 |
| `examples/` | 3dtool 示例 | ✗ 不使用 |

## 六、方案对比（业界最佳实践）

| 方案 | 来源 | 优点 | 缺点 | 本项目采用 |
|------|------|------|------|-----------|
| pip wheel + wheelhouse | [pip 官方](https://pip.pypa.io/en/stable/topics/repeatable-installs/) | 官方推荐，简单 | 单源 | ✓ 双源改进 |
| pip download + --no-index | [CSDN](https://blog.csdn.net/jjj_web/article/details/150113184) | 跨平台 | 需手动管理 | ✓ 用 requirements-pinned.txt |
| devpi 私有索引 | devpi.org | 企业级 | 太重 | ✗ 不适用 |
| pypioffline 镜像 | [PyPI](https://pypi.org/project/pypioffline/) | 全量镜像 | 672k 包太重 | ✗ 不适用 |
| Docker 容器化 | [InfoWorld](http://www.itinfoworld.org/airgapped-python-setting-up-python-without-a-network.html) | 隔离性好 | 需 Docker | ✗ 沙箱无 Docker |

**本项目创新点（*创新*）**：双离线源 + sparse-checkout + requirements-pinned.txt 三层组合
- 创新逻辑: 3dtool/wheels（子仓库维护通用包）+ polaris_wheels（主仓库维护特有包）分层管理，避免单仓库膨胀
- 底层理论: pip `--find-links` 支持多源（[pip 文档](https://pip.pypa.io/en/stable/cli/pip_install/#install-find-links)），自动从多源解析最优版本
- 案例支持: 沙箱重启模拟测试，纯离线 90 wheel 安装成功，33/33 模块，75 测试通过

## 七、文献来源（R02 学术诚信）

1. [pip 官方: Repeatable Installs (wheelhouse 模式)](https://pip.pypa.io/en/stable/topics/repeatable-installs/) — pip 官方离线安装文档
2. [CSDN: pip 离线安装包的方法](https://blog.csdn.net/jjj_web/article/details/150113184) — 中文离线安装完整指南
3. [InfoWorld: Air-gapped Python](http://www.itinfoworld.org/airgapped-python-setting-up-python-without-a-network.html) — 气隙环境 Python 配置
4. [Qiita: Pythonパッケージをオフライン環境に持ち込む](https://qiita.com/Moge800/items/f06120d5795d7c16f287) — 离线环境 wheel 批量安装
5. [PyPI: pypioffline](https://pypi.org/project/pypioffline/) — PyPI 本地镜像工具
6. [pip 官方: pip install --find-links](https://pip.pypa.io/en/stable/cli/pip_install/#install-find-links) — 多源 find-links 文档

## 八、自测结果（R13）

### 测试1: 纯离线模式（模拟断网）

```bash
rm -rf 3dtool .git/modules/3dtool /tmp/.polaris_installed
pip uninstall -y jax jaxlib sax klayout gymnasium numpy scipy matplotlib pydantic pytest ruff mypy
bash all_init_inone.sh --offline --no-daemon
```

结果:
- 3dtool 自动恢复（3fada06, 47 wheel, 122M）✓
- polaris_wheels 离线安装（43 wheel, 218M）✓
- 33/33 模块安装成功 ✓
- 75 测试通过 ✓
- JAX CPU 合规（R04）✓
- 无任何错误 ✓

### 测试2: 工具验证

```bash
python -m pytest --version   # pytest 9.0.3 ✓
python -m ruff --version     # ruff 0.15.11 ✓
python -c "import polaris_core, jax, sax, klayout, gymnasium"  # 全部导入成功 ✓
```

## 九、维护指南

### 9.1 更新 polaris_wheels/（新增依赖时）

```bash
# 1. 安装新依赖
pip install <new-package>

# 2. 下载 wheel
pip download --dest polaris_wheels --only-binary=:all: <new-package>

# 3. 更新 requirements-pinned.txt
pip freeze | grep <new-package> >> requirements-pinned.txt

# 4. 提交
git add polaris_wheels/ requirements-pinned.txt
git commit -m "deps: 新增 <new-package> 离线 wheel"
```

### 9.2 更新 3dtool/wheels/（3dtool 仓库维护）

```bash
cd 3dtool
git pull origin main
cd ..
git add 3dtool
git commit -m "chore: 更新 3dtool 子仓库（新 wheel）"
```

### 9.3 沙箱重启后恢复

```bash
bash all_init_inone.sh  # 一条命令搞定
```
