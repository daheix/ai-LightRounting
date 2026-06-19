# pycopy/ — 自研复刻工具（pyCopyxx 前缀）

本目录存放按 `project_rules.md` 规则 3 用纯 Python 100% 复刻的开源工具替代品。

## 命名规范

所有复刻包加 `pyCopy` 前缀，表示是原工具的 Python 复刻替代品：

| 复刻包 | 原工具 | 协议 | 复刻位置 |
|--------|--------|------|----------|
| pyCopyTorch | torch | BSD-3-Clause | src/polaris/nn/ |
| pyCopySAX | sax | Apache-2.0 | src/polaris/sim/cascade.py |
| pyCopySiPANN | SiPANN | MIT | src/polaris/sim/models.py |
| pyCopyKLayout | klayout | GPL-2.0 | src/polaris/sim/constraint_checker.py |
| pyCopyMEEP | meep | GPL-2.0+ | 预留（未实现） |
| pyCopyFemwell | femwell | MIT | 预留（未实现） |
| pyCopyMeow | meow | GPL-3.0 | 预留（未实现） |

## 设计原则

1. **逻辑一致**：复刻实现的代码逻辑与原开源工具 100% 一致（规则 3.2）
2. **行为对比验证**：编写对比测试，对同一输入断言输出一致（浮点数 1e-9 容差）
3. **来源标注**：复刻代码注明原仓库 URL、协议、版本号（规则 3.2）
4. **接口兼容**：复刻模块暴露与原工具等价的公开 API
5. **不留半成品**：复刻覆盖项目实际使用的全部功能子集

## 使用方式

复刻代码物理存放于 `src/polaris/` 对应模块中，本目录的 `pyCopyXxx/__init__.py`
作为统一入口重导出，使上层代码可通过 `pyCopyXxx` 包名访问复刻 API。

```python
# 通过复刻包名访问（推荐，明确表示使用复刻品）
from pycopy.pyCopyTorch import Tensor, Linear, Adam

# 通过 polaris 包访问（等价）
from polaris.nn import Tensor, Linear, Adam
```

来源:
- 规则 3: .trae/rules/project_rules.md
- PyTorch: https://pytorch.org/ (BSD-3-Clause)
- SAX: https://flaport.github.io/sax/ (Apache-2.0)
- SiPANN: https://sipann.readthedocs.io/ (MIT)
- KLayout: https://www.klayout.de/ (GPL-2.0)
