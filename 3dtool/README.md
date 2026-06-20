# 3dtool — 第三方工具统一管理目录

本目录按商业版本工具管理规范，统一存放 PoLaRIS 项目依赖的所有第三方工具。

## 目录结构

```
3dtool/
├── wheels/          # 离线 wheel 包（沙箱重启一键恢复，70 秒装完）
│   ├── install.sh       # 一键离线安装脚本（核心入口）
│   ├── MANIFEST.txt     # wheel 清单与 SHA256 校验和
│   ├── *.whl            # 小 wheel（<24MB，79 个）
│   └── parts/           # 大 wheel 分卷片段（≤20MB，18 个）
├── layout/          # 版图类工具（GDS 生成/读写/DRC）
├── simulation/      # 仿真类工具（FDTD/S 参数/模式求解）
├── ml/              # 机器学习类工具（PyTorch/Gymnasium/NetworkX）
├── numeric/         # 数值计算类工具（NumPy/SciPy/Shapely）
├── viz/             # 可视化类工具（Matplotlib）
├── serialization/   # 序列化类工具（PyYAML）
└── pycopy/          # 自研复刻工具（pyCopyxx 前缀，规则 3 复刻品）
    ├── pyCopyTorch/     # 复刻 torch（对应 src/polaris/nn）
    ├── pyCopySAX/       # 复刻 sax（对应 src/polaris/sim/cascade.py）
    ├── pyCopySiPANN/    # 复刻 SiPANN（对应 src/polaris/sim/models.py）
    ├── pyCopyKLayout/   # 复刻 klayout DRC（对应 src/polaris/sim/constraint_checker.py）
    ├── pyCopyMEEP/      # 复刻 meep FDTD（预留）
    ├── pyCopyFemwell/   # 复刻 femwell（预留）
    └── pyCopyMeow/      # 复刻 meow（预留）
```

## 快速开始（沙箱重启后必做）

```bash
# 一键离线安装全部依赖（70 秒，无需联网）
bash 3dtool/wheels/install.sh --all

# 仅检查环境
bash 3dtool/wheels/install.sh --check
```

详见 [wheels/README.md](wheels/README.md)。

## 工具分类

### layout/ — 版图类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| gdsfactory | ✅ 已装 8.18.0 | 版图生成/PDK/GDS导出 | `pip install gdsfactory` |
| klayout | ✅ 已装 0.30.9 | DRC/LVS/版图查看 | `pip install klayout` |
| gdstk | ✅ 已装 1.0.0 | 高性能 GDS 读写 | `pip install gdstk` |

### simulation/ — 仿真类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| meep | ⏳ 预留 | FDTD 电磁仿真（项目未使用） | `pip install meep` |
| simphony | ✅ 已装 0.7.3 | 光子电路 S 参数仿真 | `pip install simphony` |
| sax | ✅ 已装 0.14.7 | 光子电路频率域仿真 | `pip install sax` |
| SiPANN | ⚠️ Py3.10-3.13 必装 | 硅光器件模型（依赖 tensorflow，无 Py3.14） | `pip install SiPANN` |
| femwell | ⏳ 预留 | FEM 模式求解器（项目未使用） | `pip install femwell` |
| meow | ⏳ 预留 | 模式求解器（项目未使用） | `pip install meow` |

### ml/ — 机器学习类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| torch | ✅ 已装 2.12.1+cpu | GNN/PPO 神经网络 | `pip install torch` |
| gymnasium | ✅ 已装 1.3.0 | RL 环境 | `pip install gymnasium` |
| networkx | ✅ 已装 3.6.1 | 器件连接图建模 | `pip install networkx` |

### numeric/ — 数值计算类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| numpy | ✅ 已装 2.4.6 | 数值计算 | `pip install numpy` |
| scipy | ✅ 已装 1.17.1 | 优化求解 | `pip install scipy` |
| shapely | ✅ 已装 2.1.2 | 几何运算 | `pip install shapely` |

### viz/ — 可视化类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| matplotlib | ✅ 已装 3.11.0 | 版图渲染/拥塞热力图 | `pip install matplotlib` |

### serialization/ — 序列化类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| pyyaml | ✅ 已装 6.0.3 | 网表/配置序列化 | `pip install pyyaml` |

### dev/ — 开发类工具

| 工具 | 状态 | 用途 | 安装方式 |
|------|------|------|----------|
| pytest | ✅ 已装 9.1.0 | 测试框架 | `pip install pytest` |
| ruff | ✅ 已装 0.15.18 | Lint + Format | `pip install ruff` |
| mypy | ✅ 已装 2.1.0 | 类型检查 | `pip install mypy` |

## pycopy/ — 自研复刻工具

按 `project_rules.md` 规则 3，对于开源但安装困难的工具，用纯 Python 100% 复刻。
复刻品统一存放于 `pycopy/` 目录，加 `pyCopy` 前缀表示是替代品。

| 复刻包 | 对应原工具 | 复刻位置 | 状态 |
|--------|-----------|----------|------|
| pyCopyTorch | torch | src/polaris/nn/ | ✅ 完整复刻（Tensor/autograd/Linear/Adam/Conv2d） |
| pyCopySAX | sax | src/polaris/sim/cascade.py | ✅ 完整复刻（子网络增长算法） |
| pyCopySiPANN | SiPANN | src/polaris/sim/models.py | ✅ 完整复刻（10 个 S 参数模型） |
| pyCopyKLayout | klayout DRC | src/polaris/sim/constraint_checker.py | ✅ 完整复刻（8 种违规检查） |
| pyCopyMEEP | meep FDTD | — | ⏳ 预留（未实现） |
| pyCopyFemwell | femwell | — | ⏳ 预留（未实现） |
| pyCopyMeow | meow | — | ⏳ 预留（未实现） |

## 使用原则

1. **优先直接集成**：能用 pip 安装的开源库，直接集成（规则 2.4）
2. **复刻须 100% 可用**：不好集成的，用纯 Python 复刻完整可用版本（规则 3）
3. **来源须标注**：每个集成的工具或复刻的算法，记录来源 URL（规则 15）
4. **依赖最小化**：核心功能依赖精简，仿真类工具作为补充依赖（规则 2.4）

来源:
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- KLayout: https://www.klayout.de/
- SAX: https://flaport.github.io/sax/
- Simphony: https://simphonyphotonics.readthedocs.io/
- SiPANN: https://sipann.readthedocs.io/
- MEEP: https://meep.readthedocs.io/
- PyTorch: https://pytorch.org/
- Gymnasium: https://gymnasium.farama.org/
