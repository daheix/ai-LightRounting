# layout/ — 版图类工具

存放版图生成、GDS 读写、DRC 检查相关的第三方工具说明。

**规则 5.2**：所有工具均为必装依赖，无可选依赖。

## 工具清单

### gdsfactory

- **用途**: 版图生成、PDK、自动布线、GDS/OASIS 导出
- **状态**: ✅ 已装 8.18.0（Python 3.14 下因 pydantic 版本锁定 PDK 激活可能失败）
- **许可**: MIT（✅可商用）
- **来源**: https://gdsfactory.github.io/gdsfactory/
- **安装**: `pip install gdsfactory`
- **项目使用**: `src/polaris/pdk/gdsfactory_integration.py` 生成真实参数化器件 GDS
- **论文**: GDSFactory CLEO 2026 https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
- **兼容性说明**: gdsfactory 8.18.0 锁定 pydantic<2.10，而 pydantic<2.10 的 pydantic-core 无 Python 3.14 wheel。在 Python 3.10-3.13 环境下可正常使用。`is_available()` 会严格检查 PDK 可激活性。

### klayout

- **用途**: DRC 规则检查、LVS、版图查看
- **状态**: ✅ 已装 0.30.9
- **许可**: GPL-3.0+ / 商业双许可（⚠️许可受限，pip wheel 版本可商用，详见 INVENTORY.md）
- **来源**: https://www.klayout.de/
- **安装**: `pip install klayout`
- **项目使用**: `src/polaris/eval/layout_render.py` 调用 `klayout.db` 进行 GDS 导出和 DRC

### gdstk

- **用途**: 高性能 GDS 文件读写（替代 gdspy）
- **状态**: ✅ 已装 1.0.0
- **许可**: BSL-1.0（✅可商用）
- **来源**: https://heitzmann.github.io/gdstk/
- **安装**: `pip install gdstk`
- **项目使用**: gdsfactory 依赖，高性能 GDS 读写

## 复刻品

版图类工具无复刻品。klayout 活跃维护（0.30.9, 2026-06-20），直接用原工具 + 离线 wheel。
