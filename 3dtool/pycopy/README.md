# pycopy/ — 自研复刻工具（pyCopy 前缀）

本目录存放按 `project_rules.md` 规则 4 用纯 Python 100% 复刻的开源工具替代品。

## 复刻原则（2026-06-21 修订）

**只复刻真正无法安装的工具**，避免过度工程。复刻触发条件（规则 4.1）：
1. 原工具无目标平台的预编译 wheel
2. 原工具依赖链在目标环境不可用（如 tensorflow 无 Python 3.14 wheel）
3. 安装需复杂系统级依赖且无法用离线 wheel 解决

**不满足以上条件的工具直接用原工具**，通过 `3dtool/wheels/install.sh` 离线安装。

## 当前复刻品清单

| 复刻包 | 原工具 | 协议 | 复刻位置 | 复刻原因 | 状态 |
|--------|--------|------|----------|----------|------|
| pyCopySiPANN | SiPANN | MIT | src/polaris/sim/models.py | SiPANN 依赖 tensorflow，tensorflow 无 Python 3.14 wheel | ✅ v1.0.0 |

## 已删除的复刻品（2026-06-21 清理）

以下复刻品因原工具可直接 pip 安装且活跃维护，已删除以避免过度工程：

| 已删除复刻品 | 原工具 | 原工具最新版本 | 原工具最后更新 | 删除原因 |
|-------------|--------|---------------|---------------|----------|
| pyCopyTorch | torch | 2.12.0 | 2026-05-13 | 极度活跃（457 贡献者），直接用原工具 |
| pyCopySAX | sax | 0.15.12 | 2025-07-18 | 活跃维护（flaport 持续），直接用原工具 |
| pyCopyKLayout | klayout | 0.30.9 | 2026-06-20 | 极度活跃（Matthias Kuhn 持续），直接用原工具 |
| pyCopyMEEP | meep | — | — | 预留空包，项目未使用 FDTD |
| pyCopyFemwell | femwell | — | — | 预留空包，项目未使用 FEM |
| pyCopyMeow | meow | — | — | 预留空包，项目未使用模式求解 |

## 使用方式

复刻代码物理存放于 `src/polaris/` 对应模块中，本目录的 `pyCopyXxx/__init__.py`
作为统一入口重导出，使上层代码可通过 `pyCopyXxx` 包名访问复刻 API。

```python
# 通过复刻包名访问（推荐，明确表示使用复刻品）
from pycopy.pyCopySiPANN import waveguide_s, y_branch_s

# 通过 polaris 包访问（等价）
from polaris.sim.models import waveguide_s, y_branch_s
```

## 设计原则

1. **逻辑一致**：复刻实现的代码逻辑与原开源工具 100% 一致（规则 4.4）
2. **行为对比验证**：编写对比测试，对同一输入断言输出一致（浮点数 1e-9 容差）；
   若原工具无法安装，须用原仓库的官方测试用例/文档示例作为基准验证
3. **来源标注**：复刻代码注明原仓库 URL、协议、版本号（规则 4.4）
4. **接口兼容**：复刻模块暴露与原工具等价的公开 API
5. **不留半成品**：复刻覆盖项目实际使用的全部功能子集

来源:
- 规则 4: .trae/rules/project_rules.md
- SiPANN: https://sipann.readthedocs.io/ (MIT)
- Hammond et al., "Accelerating silicon photonic parameter extraction using
  artificial neural networks", OSA Continuum 2, 1964-1973 (2019)
