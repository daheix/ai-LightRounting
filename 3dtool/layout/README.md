# layout/ — 版图类工具

存放版图生成、GDS 读写、DRC 检查相关的第三方工具说明。

## 工具清单

### gdsfactory

- **用途**: 版图生成、PDK、自动布线、GDS/OASIS 导出
- **状态**: ❌ 未安装
- **来源**: https://gdsfactory.github.io/gdsfactory/
- **安装**: `pip install gdsfactory`
- **项目使用**: `src/polaris/pdk/` 参考 gdsfactory PDK 结构
- **论文**: GDSFactory CLEO 2026 https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf

### klayout

- **用途**: DRC 规则检查、LVS、版图查看
- **状态**: ✅ 已装 0.30.9
- **来源**: https://www.klayout.de/
- **安装**: `pip install klayout`
- **项目使用**: `src/polaris/eval/layout_render.py` 调用 `klayout.db` 进行 GDS 导出和 DRC

### gdstk

- **用途**: 高性能 GDS 文件读写（替代 gdspy）
- **状态**: ❌ 未安装
- **来源**: https://heitzmann.github.io/gdstk/
- **安装**: `pip install gdstk`
- **项目使用**: 可选，gdsfactory 依赖

## 复刻品

版图类工具的复刻品位于 `../pycopy/pyCopyKLayout/`，复刻 klayout 的 DRC 检查功能。
