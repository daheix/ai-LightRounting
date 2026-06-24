# PoLaRIS 端到端 Demo Showcase

PoLaRIS 光电子 AI 布局布线引擎端到端演示，串联 9 个阶段：
PDK 目录 → 电路规格 → AI 布局 → 智能布线 → 仿真 → DRC/LVS → GDS → 光电协同 → 量子光子。

## 9 阶段流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    PoLaRIS 端到端 Demo Showcase                  │
└─────────────────────────────────────────────────────────────────┘

  [阶段1] PDK 器件目录展示
    │   SOI / SiN / InP / LNOI 四平台 PDK 遍历
    ▼
  [阶段2] 电路规格定义
    │   MZI / Clements 4x4 / 量子玻色采样 3 电路
    ▼
  [阶段3] AI 布局
    │   Edge-GNN + PPO 布局，HPWL 指标计算
    ▼
  [阶段4] 智能布线
    │   弹性连接器 + Euler 曲线波导布线
    ▼
  [阶段5] 仿真验证
    │   MZI S 参数扫描 / Clements 酉性 / PAM4 眼图
    ▼
  [阶段6] DRC/LVS 验证
    │   SiEPIC DRC 规则检查 / 网表一致性比对
    ▼
  [阶段7] GDS 导出
    │   GDSII 文件生成与完整性验证
    ▼
  [阶段8] 光电协同
    │   Verilog-A 紧凑模型 / SPICE 联合仿真 / PAM4 眼图
    ▼
  [阶段9] 量子光子验证
    │   玻色采样 / HOM 干涉 / KLM 量子门
    ▼
  汇总报告 (reports/report.md)
```

## 快速开始

```bash
cd /workspace

# 全流程运行（默认输出到 out/e2e_showcase/）
python examples/e2e_showcase/run_showcase.py

# 运行结束后查看汇总报告
cat out/e2e_showcase/reports/report.md
```

## 运行方式

### 全流程运行

```bash
python examples/e2e_showcase/run_showcase.py
```

运行全部 9 个阶段，生成结构化日志与 Markdown 汇总报告。

### 单阶段运行

```bash
# 仅运行阶段 5（仿真验证）
python examples/e2e_showcase/run_showcase.py --stage 5
```

`--stage` 参数取值范围 1-9，对应上表中的 9 个阶段。

### 指定输出目录

```bash
python examples/e2e_showcase/run_showcase.py --output-dir /tmp/my_showcase
```

### 跳过报告生成

```bash
python examples/e2e_showcase/run_showcase.py --no-report
```

仅运行阶段，不生成 Markdown 汇总报告（JSONL 日志仍会生成）。

## 输出目录结构

```
out/e2e_showcase/
├── logs/
│   └── showcase.jsonl          # 结构化阶段日志（JSONL 格式）
├── gds/
│   ├── MZI.gds                 # MZI 干涉仪 GDSII 版图
│   ├── Clements_4x4.gds        # Clements 4x4 光矩阵 GDSII
│   ├── Quantum_BosonSampling.gds
│   └── mzi_layout.gds          # DRC/LVS 用 MZI 布局
├── verilog_a/
│   ├── waveguide.va            # 波导 Verilog-A 紧凑模型
│   ├── mmi_1x2.va              # MMI 1x2 紧凑模型
│   ├── ring_resonator.va       # 环谐振器紧凑模型
│   ├── modulator.va            # 调制器紧凑模型
│   └── detector.va             # 探测器紧凑模型
├── spice/
│   └── cosim.cir               # Ngspice 联合仿真网表
└── reports/
    ├── report.md               # Markdown 汇总报告
    ├── mzi_s_param.csv         # MZI S 参数扫描数据
    ├── clements_unitary.json   # Clements 酉矩阵
    ├── pam4_eye.json           # PAM4 眼图数据
    ├── drc_lvs_report.json     # DRC/LVS 检查报告
    ├── boson_sampling_dist.json # 玻色采样概率分布
    ├── hom_interference.json   # HOM 干涉结果
    ├── klm_verification.json   # KLM 量子门验证
    └── boson_sampling_unitary.json
```

## 关键指标说明

汇总报告中的关键指标从各阶段 JSONL 日志的 `outputs` 字段提取：

| 阶段 | 指标名 | 说明 | 单位 |
|------|--------|------|------|
| 1 | total_device_count | 四平台 PDK 器件总数 | 个 |
| 1 | platform_count | PDK 平台数量 | 个 |
| 2 | circuit_count | 演示电路数量 | 个 |
| 2 | total_n_devices | 电路器件总数 | 个 |
| 3 | placement_mode | 布局模式（rl/analytical） | - |
| 3 | total_hpwl | 半周长线长总和 | μm |
| 4 | total_loss_db | 总插入损耗 | dB |
| 4 | total_crossings | 波导交叉数 | 个 |
| 4 | total_bends | 波导弯曲数 | 个 |
| 5 | resonant_wavelength_nm | MZI 谐振波长 | nm |
| 5 | extinction_ratio_db | MZI 消光比 | dB |
| 5 | pam4_ber | PAM4 误码率 | - |
| 5 | pam4_snr_db | PAM4 信噪比 | dB |
| 6 | drc_pass_rate | DRC 规则通过率 | - |
| 6 | lvs_consistent | LVS 网表一致性 | - |
| 7 | gds_files | GDS 文件数量 | 个 |
| 8 | verilog_a_models | Verilog-A 模型数量 | 个 |
| 9 | boson_sampling_prob_sum | 玻色采样概率总和（=1.0 为守恒） | - |
| 9 | hom_verified | HOM 干涉验证通过 | - |
| 9 | klm_cnot_success_prob | KLM CNOT 门成功率（理论值 0.25） | - |

## 汇总报告结构

`reports/report.md` 包含以下章节：

1. **阶段执行状态** — 9 阶段状态表（阶段/名称/状态/耗时/错误）
2. **关键指标汇总** — 从各阶段 outputs 提取的关键指标表
3. **9 阶段执行时间线** — ASCII 条形图可视化各阶段耗时
4. **产物文件清单** — 扫描 output_dir 下所有产物文件（名称/大小/路径）
5. **汇总** — 总阶段数/成功/失败/总耗时
6. **学术诚信声明** — 所有公式与参数来源

## 学术诚信声明

本演示所有数据均来自真实物理仿真，无 fall-back 假数据。
所有公式与参数来源如下：

1. MZI 传输率: Saleh & Teich, "Photonics", 2019
2. PAM4 BER: Shafik et al., IEEE CommSurveys 2016,
   https://ieeexplore.ieee.org/document/7545186
3. 玻色采样: Aaronson & Arkhipov, STOC 2011,
   https://arxiv.org/abs/0910.4698
4. HOM 干涉: Hong, Ou, Mandel, PRL 1987,
   https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
5. KLM 方案: Knill, Laflamme, Milburn, Nature 2001,
   https://www.nature.com/articles/35051009
6. Clements 分解: Clements et al., Optica 2016,
   https://doi.org/10.1364/OPTICA.3.001460
7. HPWL: Kahng & Lienig, IEEE TCAD 2009,
   https://ieeexplore.ieee.org/document/4685534
8. 弯曲波导布线: LiDAR ISPD 2025,
   https://dl.acm.org/doi/10.1145/3698364.3705355
9. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
10. Ligentec SiN PDK: https://www.ligentec.com/
11. HyperLight LNOI PDK: https://hyperlightphotonics.com/
12. Pattern Project InP PDK: https://www.patternproject.com/
13. Verilog-A 紧凑模型: Ansys Lumerical CML Compiler,
    https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
14. GDSII 规范: https://en.wikipedia.org/wiki/GDSII
15. KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc_runsets.html

## 模块结构

```
examples/e2e_showcase/
├── __init__.py              # 包初始化
├── run_showcase.py          # 主入口（参数解析、阶段调度）
├── logging_config.py        # 日志配置（控制台彩色 + JSONL）
├── report_generator.py      # 汇总报告生成器
└── stages/
    ├── __init__.py
    ├── stage1_pdk_catalog.py      # PDK 器件目录展示
    ├── stage2_circuit_spec.py     # 电路规格定义
    ├── stage3_ai_placement.py     # AI 布局
    ├── stage4_routing.py          # 智能布线
    ├── stage5_simulation.py       # 仿真验证
    ├── stage6_drc_lvs.py          # DRC/LVS 验证
    ├── stage7_gds_export.py       # GDS 导出
    ├── stage8_opto_electrical.py  # 光电协同
    └── stage9_quantum_photonics.py # 量子光子验证
```
