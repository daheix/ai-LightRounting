# PoLaRIS 真实板子数据集 (real_board)

> 商用版自动布局布线训练教材 + 真实电路回归基准
>
> 创建: 2026-07-04 | 更新: 2026-07-05 | 总数: **8158 个真实用例** | 版本: 3.0.0
>
> 20 个独立来源 | 覆盖 SiPh / LNOI / SiN / 量子光子 / RF / 模拟电路 / 数字 IC 宏布局 全平台

## 目录结构

### 第一批数据源 (batch 1, 448 个)

| 子目录 | 来源 | 数量 | 格式 | 许可 | 用途 |
|--------|------|------|------|------|------|
| `siepic/` | [SiEPIC EBeam PDK](https://github.com/SiEPIC/SiEPIC_EBeam_PDK) | 229 | GDSII | LGPL-2.1 | 真实版图端到端测试 |
| `gdsfactory/` | [gdsfactory](https://github.com/gdsfactory/gdsfactory) | 89 | YAML/JSON | MIT | 网表解析+布局布线 |
| `picbench/` | [picbench](https://github.com/TiagoCavaco/picbench) (本地缓存) | 24 | JSON | MIT | 基准电路测试 |
| `lidar/` | [ISPD 2025 LiDAR](https://github.com/ALIGN-analoglayout/ALIGN) | 9 | JSON | BSD-3-Clause | LiDAR OPA 基准 |
| `align/` | [ALIGN-custom](https://github.com/Chentang2nd/ALIGN-custom) | 56 | JSON | BSD-3-Clause | EPIC 基准电路 |
| `expert_demos/` | PoLaRIS 从 SiEPIC 提取 | 41 | JSON (三元组) | LGPL-2.1 | BC 训练专家示范 |

### 第二批数据源 (batch 2, 2769 个) — 2026-07-05 新增

| 子目录 | 来源 | 数量 | 格式 | 许可 | 用途 |
|--------|------|------|------|------|------|
| `ubcpdk/` | [gdsfactory/ubc](https://github.com/gdsfactory/ubc) | 526 | GDS/YAML | MIT | UBC SiEPIC PDK 真实版图+netlist |
| `cspdk/` | [gdsfactory/cspdk](https://github.com/gdsfactory/cspdk) | 1165 | GDS/YAML | MIT | CS PDK 组件库 |
| `vtt/` | [gdsfactory/vtt](https://github.com/gdsfactory/vtt) | 31 | GDS/YAML | MIT | VTT 多项目晶圆 PDK |
| `gf_test_data/` | [gdsfactory-test-data](https://github.com/gdsfactory/gdsfactory-test-data) | 359 | GDS | MIT | gdsfactory 测试 GDS 回归基准 |
| `luxtelligence/` | [Luxtelligence/lxt_pdk_gf](https://github.com/Luxtelligence/lxt_pdk_gf) | 105 | GDS/YAML | MIT | LNOI 铌酸锂平台 PDK |
| `siepicfab/` | [SiEPIC/SiEPICfab_Shuksan_PDK](https://github.com/SiEPIC/SiEPICfab_Shuksan_PDK) | 31 | GDS/XML | Apache-2.0 | Shuksan 开源硅光子 PDK |
| `apollo/` | [ScopeX-ASU/APR](https://github.com/ScopeX-ASU/APR) (同源替代) | 11 | YAML/JSON/GDS | MIT | Apollo PIC P&R benchmark |
| `perceval/` | [Quandela/Perceval](https://github.com/Quandela/Perceval) | 276 | JSON/PY | MIT | 量子光子电路示例 |
| `klayout_pcells/` | [KLayoutPhotonicPCells-core](https://github.com/sebastian-goeldi/KLayoutPhotonicPCells-core) | 10 | GDS/PY | MIT | KLayout 光子 PCell 模板 |
| `quantum_rf/` | [gdsfactory/quantum-rf-pdk](https://github.com/gdsfactory/quantum-rf-pdk) | 255 | YAML/GDS | MIT | 量子 RF PDK netlist |

### 第三批数据源 (batch 3, 4938 个) — 2026-07-05 新增

| 子目录 | 来源 | 数量 | 格式 | 许可 | 用途 |
|--------|------|------|------|------|------|
| `siepic_openEBL_2024_10/` | [SiEPIC/openEBL-2024-10](https://github.com/SiEPIC/openEBL-2024-10) | 264 | GDS/OAS/YAML/PY | MIT | openEBL 2024-10 流片真实提交 (213 GDS) |
| `siepic_openEBL_2024_05/` | [SiEPIC/openEBL-2024-05](https://github.com/SiEPIC/openEBL-2024-05) | 244 | GDS/YAML/PY | MIT | openEBL 2024-05 流片真实提交 |
| `skywater130/` | [gdsfactory/skywater130](https://github.com/gdsfactory/skywater130) | 1808 | GDS/YAML | MIT | SkyWater 130nm CMOS PDK (938 GDS) |
| `macroplacement/` | [TILOS-AI-Institute/MacroPlacement](https://github.com/TILOS-AI-Institute/MacroPlacement) | 2622 | Verilog/LEF/DEF/PLC | BSD-3-Clause | ASIC 宏单元布局基准 (Ariane/NVDLA/MemPool/ICCAD04) |

### 任务清单中跳过的数据源 (R03 禁止 fall-back 合规声明)

| 任务原 URL | 状态 | 原因 |
|------------|------|------|
| `gdsfactory/amf` | **跳过** | 仓库不存在 (github.com/gdsfactory/amf 返回 404)。AMF Photonics 是商用 NDA PDK,从未在 GitHub 公开。不伪造数据。 |
| `vitek/ptc-benchmark` | **跳过** | 仓库不存在 (WebSearch 无任何匹配,github.com/vitek/ptc-benchmark 返回 404)。 |
| `TILOS-AI-CAD-Institute/MacroPlacement` | **修正** | 任务拼写错误,实际仓库为 `TILOS-AI-Institute/MacroPlacement` (无 `-CAD-`),已通过 WebSearch + codeload 验证并下载。 |
| `SiEPIC/SiEPIC_openEBL` | **修正** | openEBL 不是单一仓库,而是 `SiEPIC/openEBL-YYYY-MM` 系列流片提交仓库。已下载 2024-05 与 2024-10 两个 run。 |
| `ASU-LOPE-Group/Apollo` | 已有同源替代 | 见 `apollo/` 目录说明 (ICCAD 2025 代码未发布,使用同团队前身 APR 作为基准)。 |

### Apollo 同源替代说明 (R02/R03 合规)

- **任务原 URL**: https://github.com/ScopeX-ASU/Apollo (仓库为空，ICCAD 2025 代码未发布)
- **Apollo 论文**: Zhou, Yang, Gangi, Ren, Huang, Gu, "Apollo: Automated Routing-Informed Placement for Large-Scale Photonic Integrated Circuits", ICCAD 2025, ASU/NVIDIA/RPI. [PDF](https://scopex-asu.github.io/files/publications/PD_ICCAD2025_Gu.pdf)
- **同源替代**: 使用同团队 (ScopeX-ASU) 前身工作 APR (ASP-DAC 2025, arXiv:2410.01260)；APR 仓库实际重定向到 LiDAR 仓库，提取其中 benchmark yml (clements/mrr_weight_bank/multiportmmi/toy_example) 作为 PIC P&R 基准。
- **合规声明**: 不伪造 Apollo 代码，明确标注替代关系与论文溯源。

## 用途

### 1. 端到端测试基准
对全部 **8158 个真实用例**执行 place→route→sim→drc→gds 流水线，验证商用版本对真实电路的鲁棒性。覆盖 20 个独立来源，跨 SiPh/LNOI/SiN/量子/RF/CMOS/ASIC 宏布局 多平台。

### 2. 自动布局布线训练教材
- `expert_demos/` 提供 (网表, 布局, 布线) 三元组，用于 BC 预训练
- `siepic/` + `ubcpdk/` + `cspdk/` + `gf_test_data/` + `siepic_openEBL_2024_*` 提供 2500+ 真实 GDS 版图
- `gdsfactory/` + `quantum_rf/` + `vtt/` + `skywater130/` netlist 作为 RL 微调的环境输入
- `apollo/` + `macroplacement/` benchmark 用于对标 ASU Apollo/APR 与 TILOS Circuit Training 学术 SOTA
- `perceval/` 量子光路用于量子光子电路扩展
- `macroplacement/` 提供 Ariane/NVDLA 等论文标准 benchmark 用于跨域迁移学习

### 3. 商用版本溯源
所有用例标注 GitHub origin URL + license + 作者，可溯源到原始开源仓库。每个用例文件保留 origin_url 溯源信息（见 `index_new_sources.json` 中 files[].origin 字段）。

### 4. 学术对标
- 对标 Apollo/APR (ASU ScopeX) - 学术 PIC PnR SOTA
- 对标 TILOS MacroPlacement / Circuit Training (Google AlphaChip) - 数字 IC 宏布局 SOTA
- 对标 gdsfactory (J. Opt. Microsyst. 2022) - 开源 PDK 生态
- 对标 SiEPIC/UBC (Silicon Photonics Design, CUP 2015) - 学术教学
- 对标 SiEPIC openEBL (SPIE Photonics West 2024) - 真实流片提交
- 对标 SkyWater 130nm PDK - 开源 CMOS 工艺
- 对标 Perceval (Quantum, 2024) - 量子光子计算
- 对标 Luxtelligence LNOI - 铌酸锂商业平台
- 对标 VTT MCP - 多项目晶圆服务

## 索引

- `index.json` - 主索引（合并第一批+第二批+第三批，20 个数据源元信息）
- `index_new_sources.json` - 第二批 10 个新数据源详细索引（每个文件含 name/source/format/path/size/origin）

## 许可证遵循

| 许可 | 数据源 |
|------|--------|
| MIT | gdsfactory, picbench, ubcpdk, cspdk, vtt, gf_test_data, luxtelligence, apollo, perceval, klayout_pcells, quantum_rf, siepic_openEBL_2024_10, siepic_openEBL_2024_05, skywater130 |
| LGPL-2.1 | siepic, expert_demos |
| BSD-3-Clause | lidar, align, macroplacement |
| Apache-2.0 | siepicfab |

## 下载脚本

- `scripts/download_real_circuits.py` - 第一批下载器 (SiEPIC/gdsfactory/ALIGN)
- `scripts/download_new_real_circuits.py` - 第二批下载器 (10 个新光子 PDK 数据源)
- 第三批下载方法: `codeload.github.com/<owner>/<repo>/zip/refs/heads/main` + 选择性提取 (R03 合规)

下载方案：codeload.github.com zip + zipfile 选择性提取（沙箱中 raw.githubusercontent GET 受 SSL 拦截，codeload zip 可用）。

## 引用

```bibtex
@book{chrostowski2015silicon,
  title={Silicon Photonics Design},
  author={Chrostowski, Lukas and Hochberg, Michael},
  publisher={Cambridge University Press},
  isbn={9781107016838},
  year={2015}
}
@article{matres2022gdsfactory,
  title={gdsfactory: An open-source Python driven framework for nanophotonic GDS generation and inspection},
  author={Matres, Joaquin and others},
  journal={J. Opt. Microsyst.},
  volume={2}, number={4}, pages={043501},
  year={2022},
  doi={10.1117/1.JOM.2.4.043501}
}
@inproceedings{chrostowski2024openebl,
  title={SiEPIC openEBL: remote silicon photonic design, fabrication, testing enabled by open-source PDKs and EDA tools},
  author={Chrostowski, Lukas and others},
  booktitle={SPIE Photonics West},
  year={2024},
  doi={10.1117/12.3076810}
}
@inproceedings{zhou2025apollo,
  title={Apollo: Automated Routing-Informed Placement for Large-Scale Photonic Integrated Circuits},
  author={Zhou, Hongjian and Yang, Haoyu and Gangi, Nicholas and Ren, Haoxing and Huang, Zhaoran (Rena) and Gu, Jiaqi},
  booktitle={ICCAD},
  year={2025}
}
@inproceedings{zhou2025apr,
  title={APR: Automated Photonic Integrated Circuit Detailed Routing with Curvy Waveguide and Adaptive Crossing Insertion},
  author={Zhou, Hongjian and Zhu, Keren and Gu, Jiaqi},
  booktitle={ASP-DAC},
  year={2025},
  note={arXiv:2410.01260}
}
@article{heurtel2024perceval,
  title={Perceval: A Platform for Photonic Quantum Computing},
  author={Heurtel, Nicolas and others},
  journal={Quantum},
  volume={8}, pages={1333},
  year={2024},
  doi={10.22331/q-2024-04-26-1333}
}
@inproceedings{ajayi2023macroplacement,
  title={An Open-Source Framework for Estimating Macro Placement Algorithms},
  author={Ajayi, T. and Kahng, A. B. and others},
  booktitle={ISPD},
  year={2023},
  note={arXiv:2302.11014}
}
@article{kahng2025updated,
  title={An Updated Assessment of Reinforcement Learning for Macro Placement},
  author={Kahng, Andrew B. and others},
  journal={IEEE TCAD},
  year={2025},
  note={IEEE Xplore early access Dec 2025, document 11300304}
}
@misc{skywater130pdk,
  title={SkyWater 130nm Open Source PDK},
  author={{SkyWater Technology Foundry} and Google LLC},
  year={2020},
  url={https://skywater-pdk.readthedocs.io/}
}
```
