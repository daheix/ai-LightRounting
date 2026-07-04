# PoLaRIS 真实板子数据集 (real_board)

> 商用版自动布局布线训练教材 + 真实电路回归基准
>
> 创建: 2026-07-04 | 总数: 448 个真实用例 | 版本: 1.0.0

## 目录结构

| 子目录 | 来源 | 数量 | 格式 | 用途 |
|--------|------|------|------|------|
| `siepic/` | [SiEPIC EBeam PDK](https://github.com/SiEPIC/SiEPIC_EBeam_PDK) | 229 | GDSII | 真实版图端到端测试 |
| `gdsfactory/` | [gdsfactory](https://github.com/gdsfactory/gdsfactory) | 89 | YAML/JSON netlist | 网表解析+布局布线 |
| `picbench/` | [picbench](https://github.com/TiagoCavaco/picbench) | 24 | JSON | 基准电路测试 |
| `lidar/` | [ISPD 2025 LiDAR](https://github.com/ALIGN-analoglayout/ALIGN) | 9 | JSON | LiDAR OPA 基准 |
| `align/` | [ALIGN-custom](https://github.com/Chentang2nd/ALIGN-custom) | 56 | JSON | EPIC 基准电路 |
| `expert_demos/` | PoLaRIS 从 SiEPIC 提取 | 11 | JSON (三元组) | BC 训练专家示范 |

## 用途

### 1. 端到端测试基准
对全部 448 个真实用例执行 place→route→sim→drc→gds 流水线，验证商用版本对真实电路的鲁棒性。

### 2. 自动布局布线训练教材
- `expert_demos/` 提供 (网表, 布局, 布线) 三元组，用于 BC 预训练
- `siepic/` GDS 可提取更多专家示范扩展训练集
- `gdsfactory/` + `picbench/` netlist 作为 RL 微调的环境输入

### 3. 商用版本溯源
所有用例标注 GitHub origin URL + license，可溯源到原始开源仓库。

## 索引

详细索引见 `index.json`，每个用例含 name/source/format/path/origin_url/license。

## 许可证遵循

- SiEPIC: LGPL-2.1
- gdsfactory: MIT
- picbench: MIT
- ALIGN: BSD-3-Clause

## 引用

```bibtex
@book{chrostowski2015silicon,
  title={Silicon Photonics Design},
  author={Chrostowski, Lukas and Hochberg, Michael},
  publisher={Cambridge University Press},
  isbn={9781107016838},
  year={2015}
}
@misc{siepic_ebeam_pdk,
  title={SiEPIC EBeam PDK},
  url={https://github.com/SiEPIC/SiEPIC_EBeam_PDK}
}
```
