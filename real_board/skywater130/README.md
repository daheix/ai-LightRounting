# SkyWater 130nm CMOS PDK (gdsfactory 移植版)

> 来源: https://github.com/gdsfactory/skywater130
>
> 文档: https://gdsfactory.github.io/skywater130/
>
> 许可: MIT (Copyright © 2022 gdsfactory) — 见 `LICENSE`
>
> 文件数: 1808 (全量提取)

## 来源说明

gdsfactory 社区维护的 SkyWater 130nm CMOS 工艺 PDK,把 SkyWater Technology Foundry 公开的 130nm 工艺数据移植到 gdsfactory/KLayout 生态。SkyWater 是 Google 资助的开源晶圆厂,自 2020 年起提供完全开源的 PDK,无需 NDA。

- 工艺: 130nm CMOS,1.8V/3.3V core I/O
- 应用: 模拟/RF/混合信号/数字 IC 设计
- 与 gdsfactory 完整集成 (PCell, routing, DRC)

## 目录内容

- `sky130/` — 主 PDK 目录
  - `sky130--sample-projects/` — 真实示例项目 (含子 LICENSE)
  - 多个 `sky130--*` 子目录 — 各工艺选项 (primitive, primitives, etc.)
- `examples/` — gdsfactory 调用示例
- `notebooks/` — Jupyter 教程
- `docs/` — mkdocs 文档源
- `tests/` — 单元测试
- `LICENSE` (MIT) + `README.md`

## 文件类型分布

- `.gds` (938): 真实 GDSII 版图 (大量标准单元 + 宏单元)
- `.yml` (793): gdsfactory YAML netlist + PDK 配置
- `.py` (52): PCell 实现 + 工具脚本
- `.ipynb` (4): Jupyter 教程
- `.lyt`/`.lyp`/`.lym` (6): KLayout layer/property 配置

## 用途

- 938 个真实 GDS 标准单元版图回归基准 (CMOS 工艺)
- gdsfactory YAML netlist 解析测试 (与光子 PDK 的 YAML 语法相同,可复用解析器)
- 跨工艺 (CMOS 130nm vs SiPh 220nm SOI vs LNOI) 版图风格对比
- 电子/RF 电路扩展 (与 `quantum_rf/` 配合覆盖完整 RF/电子链路)

## 学术诚信 (R02)

SkyWater 130nm PDK 是工业级开源 PDK,其工艺参数来源于 SkyWater Technology 公开文档 (https://skywater-pdk.readthedocs.io/),无任何 NDA 限制。本数据集仅做缓存镜像,所有设计版权归 SkyWater 与 respective designers。

## 引用

```bibtex
@misc{skywater130pdk,
  title={SkyWater 130nm Open Source PDK},
  author={{SkyWater Technology Foundry} and Google LLC},
  year={2020},
  url={https://skywater-pdk.readthedocs.io/}
}
@misc{gdsfactory2022skywater130,
  title={gdsfactory skywater130 PDK port},
  author={gdsfactory community},
  year={2022},
  url={https://github.com/gdsfactory/skywater130}
}
```
