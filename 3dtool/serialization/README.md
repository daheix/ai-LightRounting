# serialization/ — 序列化类工具

存放数据序列化相关的第三方工具说明。

## 工具清单

### pyyaml

- **用途**: 网表/配置序列化
- **状态**: ✅ 已装 6.0.3（import 名为 `yaml`）
- **来源**: https://pyyaml.org/
- **安装**: `pip install pyyaml`
- **项目使用**:
  - `src/polaris/engine/netlist.py` — YAML 网表解析
  - `src/polaris/pdk/catalog.py` — PDK 配置
  - `src/polaris/trainer/dataset.py` — 数据集配置
  - `src/polaris/data/data_loader.py` — 数据加载
